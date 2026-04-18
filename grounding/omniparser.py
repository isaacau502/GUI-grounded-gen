"""OmniParser-v2 wrapper for visual UI element grounding.

Lazy-imports heavy deps (torch, transformers, ultralytics) so this module is
safe to import on Mac without a GPU. Heavy deps only load when OmniParser is
instantiated.

Architecture:
  - icon_detect: YOLOv8 fine-tuned on interactable UI elements → bboxes
  - icon_caption: Florence-2 fine-tuned on icon descriptions → captions

Usage:
    from grounding.omniparser import OmniParser
    parser = OmniParser()  # loads weights (~10s on A100)
    result = parser.query("/content/samples/1.png", issue_type="text_overlap")
    # result -> {'point': (x, y) | None, 'parse_success': bool,
    #            'raw_output': str, 'original_size': (w, h),
    #            'all_elements': [...]}
"""

import os
import io
import base64


# Issue type → natural language keywords for matching element captions
_ISSUE_KEYWORDS = {
    "text_overlap":     ["text", "label", "heading", "paragraph", "overflow", "overlap"],
    "misalignment":     ["button", "icon", "image", "container", "panel", "card"],
    "color_contrast":   ["text", "label", "button", "background"],
    "overflow":         ["container", "div", "panel", "scroll", "overflow", "content"],
    "missing_element":  ["button", "icon", "image", "link"],
    "z_order":          ["modal", "dropdown", "popup", "overlay", "menu"],
}
_DEFAULT_KEYWORDS = ["element", "component", "widget"]


class OmniParser:
    def __init__(
        self,
        weights_dir: str = "weights",
        bbox_threshold: float = 0.05,
        iou_threshold: float = 0.1,
        device: str = "auto",
    ):
        """Load OmniParser v2 models.

        weights_dir: path to folder containing icon_detect/ and
                     icon_caption_florence/ subfolders.
                     Download with:
                       huggingface-cli download microsoft/OmniParser-v2.0 \\
                         icon_detect/{train_args.yaml,model.pt,model.yaml} \\
                         icon_caption/{config.json,generation_config.json,model.safetensors} \\
                         --local-dir weights
                       mv weights/icon_caption weights/icon_caption_florence
        """
        import torch
        from ultralytics import YOLO
        from transformers import AutoProcessor, AutoModelForCausalLM

        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.bbox_threshold = bbox_threshold
        self.iou_threshold = iou_threshold

        detect_path = os.path.join(weights_dir, "icon_detect", "model.pt")
        caption_path = os.path.join(weights_dir, "icon_caption_florence")

        self.detect_model = YOLO(detect_path)

        self.caption_processor = AutoProcessor.from_pretrained(
            caption_path, trust_remote_code=True
        )
        self.caption_model = AutoModelForCausalLM.from_pretrained(
            caption_path, trust_remote_code=True
        ).to(self.device)
        self.caption_model.eval()

    # ------------------------------------------------------------------
    # Public API — mirrors JEDI.query() signature for drop-in replacement
    # ------------------------------------------------------------------

    def query(self, image_path: str, issue_type: str) -> dict:
        """Parse UI screenshot and find the element most likely to contain issue_type.

        Returns the same schema as jedi.py:
        {
            'point':         (x, y) | None,   # centre of best-match bbox, original pixels
            'parse_success': bool,
            'raw_output':    str,              # human-readable summary of all detected elements
            'original_size': (w, h),
            'all_elements':  list[dict],       # full parsed output for richer prompt use
        }
        """
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        elements = self._detect_and_caption(img)

        best = _match_element(elements, issue_type)
        point = None
        if best is not None:
            cx = int((best["bbox"][0] + best["bbox"][2]) / 2)
            cy = int((best["bbox"][1] + best["bbox"][3]) / 2)
            point = (cx, cy)

        raw_output = _format_elements(elements)

        return {
            "point": point,
            "parse_success": point is not None,
            "raw_output": raw_output,
            "original_size": (orig_w, orig_h),
            "all_elements": elements,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_and_caption(self, img) -> list[dict]:
        """Run YOLO detection + Florence-2 captioning. Returns list of elements."""
        import torch
        from PIL import Image

        orig_w, orig_h = img.size
        results = self.detect_model(img, conf=self.bbox_threshold, iou=self.iou_threshold)

        elements = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            # clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img.crop((x1, y1, x2, y2))
            caption = self._caption_crop(crop)

            elements.append({
                "bbox": [x1, y1, x2, y2],                  # absolute pixels
                "bbox_norm": [x1/orig_w, y1/orig_h,
                              x2/orig_w, y2/orig_h],        # normalised [0,1]
                "confidence": float(box.conf[0]),
                "caption": caption,
            })

        return elements

    def _caption_crop(self, crop) -> str:
        """Run Florence-2 on a single cropped element image."""
        import torch

        prompt = "<CAPTION>"
        inputs = self.caption_processor(
            text=prompt, images=crop, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            generated_ids = self.caption_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=64,
                num_beams=3,
            )
        caption = self.caption_processor.batch_decode(
            generated_ids, skip_special_tokens=False
        )[0]
        # strip Florence-2 task token wrapper
        caption = caption.replace("<CAPTION>", "").replace("</s>", "").strip()
        return caption


# ------------------------------------------------------------------
# Matching logic — maps issue_type → best element
# ------------------------------------------------------------------

def _match_element(elements: list[dict], issue_type: str) -> dict | None:
    """Return the element whose caption best matches the issue type keywords.

    Strategy:
      1. keyword overlap between caption and issue-specific keyword list
      2. tie-break by detection confidence
      3. if no keyword match at all, fall back to highest-confidence element
    """
    if not elements:
        return None

    keywords = _ISSUE_KEYWORDS.get(issue_type.lower(), _DEFAULT_KEYWORDS)

    scored = []
    for el in elements:
        cap_lower = el["caption"].lower()
        score = sum(1 for kw in keywords if kw in cap_lower)
        scored.append((score, el["confidence"], el))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_score, _, best_el = scored[0]

    # If zero keyword matches, return highest-confidence element anyway
    # (graceful degradation — same policy as JEDI parse_success=False path)
    return best_el


def _format_elements(elements: list[dict]) -> str:
    """Human-readable summary for raw_output field and prompt injection."""
    if not elements:
        return "OmniParser detected no elements."
    lines = [f"OmniParser detected {len(elements)} element(s):"]
    for i, el in enumerate(elements):
        x1, y1, x2, y2 = el["bbox"]
        lines.append(
            f"  [{i}] bbox=({x1},{y1},{x2},{y2})  "
            f"conf={el['confidence']:.2f}  caption=\"{el['caption']}\""
        )
    return "\n".join(lines)