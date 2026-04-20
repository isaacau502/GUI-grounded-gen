"""OmniParser-v2 wrapper for visual UI element grounding.

Lazy-imports heavy deps (torch, transformers, ultralytics) so this module is
safe to import on Mac without a GPU. Heavy deps only load when OmniParser is
instantiated.

Architecture:
  - icon_detect: YOLOv8 fine-tuned on interactable UI elements -> bboxes
  - icon_caption: Florence-2 fine-tuned on icon descriptions -> captions

Weight loading strategy:
  The OmniParser-v2 HuggingFace repo ships the fine-tuned weights but NOT the
  full set of Florence-2 config/tokenizer/remote-code files needed to load
  the folder as a standalone model. So we:
    1. Load processor + architecture from microsoft/Florence-2-base
       (has all configs, tokenizer, modeling code)
    2. Overwrite the weights with OmniParser's fine-tuned model.safetensors

Usage:
    from grounding.omniparser import OmniParser
    parser = OmniParser(weights_dir="/path/to/omniparser-weights")
    result = parser.query("/path/to/screenshot.png", issue_type="text_overlap")
    # result -> {'point': (x, y) | None, 'parse_success': bool,
    #            'raw_output': str, 'original_size': (w, h),
    #            'all_elements': [...]}
"""

import os


# Issue type -> natural language keywords for matching element captions.
# Ablate by editing this table; the matching logic is orthogonal to the model.
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
        florence_base: str = "microsoft/Florence-2-base",
    ):
        """Load OmniParser v2 models.

        Args:
            weights_dir: path to folder containing icon_detect/ and
                         icon_caption_florence/ subfolders. Download with:
                           from huggingface_hub import hf_hub_download
                           for f in [
                               "icon_detect/model.pt",
                               "icon_detect/model.yaml",
                               "icon_detect/train_args.yaml",
                               "icon_caption/config.json",
                               "icon_caption/generation_config.json",
                               "icon_caption/model.safetensors",
                           ]:
                               hf_hub_download("microsoft/OmniParser-v2.0", f,
                                               local_dir=weights_dir)
                           os.rename(weights_dir + "/icon_caption",
                                     weights_dir + "/icon_caption_florence")
            bbox_threshold: YOLO detection confidence threshold
            iou_threshold: YOLO NMS IoU threshold
            device: "auto" | "cuda" | "cpu"
            florence_base: HF repo ID for Florence-2 base architecture/configs
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

        # --- icon_detect (YOLOv8) ---
        detect_path = os.path.join(weights_dir, "icon_detect", "model.pt")
        if not os.path.exists(detect_path):
            raise FileNotFoundError(
                f"icon_detect weights not found at {detect_path}. "
                f"Did the download complete?"
            )
        self.detect_model = YOLO(detect_path)

        # --- icon_caption (Florence-2 fine-tuned) ---
        caption_path = os.path.join(weights_dir, "icon_caption_florence")
        if not os.path.exists(caption_path):
            raise FileNotFoundError(
                f"icon_caption_florence folder not found at {caption_path}. "
                f"Did you rename icon_caption -> icon_caption_florence?"
            )

        # Load processor + model architecture from Florence-2 base repo.
        # The OmniParser repo is missing tokenizer/processor/remote-code files;
        # Florence-2-base has all of them and the architecture is identical.
        # Use safe loaders that work around Florence-2's forced_bos_token_id bug.
        from grounding._florence2_patch import (
            load_florence2_processor_safe,
            load_florence2_model_safe,
        )
        print(f"[omniparser] Loading Florence-2 base from {florence_base} ...")
        self.caption_processor = load_florence2_processor_safe(florence_base)
        self.caption_model = load_florence2_model_safe(florence_base)

        # Overwrite base weights with OmniParser's fine-tuned weights.
        weights_file = os.path.join(caption_path, "model.safetensors")
        if not os.path.exists(weights_file):
            raise FileNotFoundError(
                f"Fine-tuned weights not found at {weights_file}."
            )
        print(f"[omniparser] Loading fine-tuned weights from {weights_file} ...")
        from safetensors.torch import load_file
        state_dict = load_file(weights_file)
        missing, unexpected = self.caption_model.load_state_dict(
            state_dict, strict=False
        )
        if missing:
            print(f"[omniparser] warn: {len(missing)} missing keys "
                  f"(first: {missing[:3]})")
        if unexpected:
            print(f"[omniparser] warn: {len(unexpected)} unexpected keys "
                  f"(first: {unexpected[:3]})")

        self.caption_model = self.caption_model.to(self.device)
        self.caption_model.eval()
        print(f"[omniparser] Ready on {self.device}.")

    # ------------------------------------------------------------------
    # Public API - mirrors JEDI.query() signature for drop-in replacement
    # ------------------------------------------------------------------

    def query(self, image_path: str, issue_type: str) -> dict:
        """Parse UI screenshot and find the element most likely to contain
        issue_type.

        Returns the same schema shape as jedi.py (plus an extra all_elements
        field that pipeline code can ignore or use):
            {
                'point':         (x, y) | None,   # centre of best-match bbox
                'parse_success': bool,
                'raw_output':    str,              # human-readable element list
                'original_size': (w, h),
                'all_elements':  list[dict],       # full parsed output
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

    def parse(self, image_path: str) -> list[dict]:
        """Parse a screenshot without picking a best match. Useful if
        pipeline/prompts.py wants to pass all elements to Qwen rather than a
        single point.
        """
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        return self._detect_and_caption(img)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_and_caption(self, img) -> list[dict]:
        """Run YOLO detection + Florence-2 captioning. Returns list of
        elements with absolute pixel bboxes and captions.
        """
        import torch

        orig_w, orig_h = img.size
        results = self.detect_model(
            img, conf=self.bbox_threshold, iou=self.iou_threshold, verbose=False
        )

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
                "bbox": [x1, y1, x2, y2],                       # pixels
                "bbox_norm": [x1 / orig_w, y1 / orig_h,
                              x2 / orig_w, y2 / orig_h],         # 0..1
                "confidence": float(box.conf[0]),
                "caption": caption,
            })

        return elements

    def _caption_crop(self, crop) -> str:
        """Run Florence-2 on a single cropped element image. Returns caption
        string with task-token wrappers stripped.
        """
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
        # strip Florence-2 task-token wrappers
        for tok in ("<CAPTION>", "</s>", "<s>", "<pad>"):
            caption = caption.replace(tok, "")
        return caption.strip()


# ------------------------------------------------------------------
# Matching logic - maps issue_type -> best element
# ------------------------------------------------------------------

def _match_element(elements: list[dict], issue_type: str) -> dict | None:
    """Return the element whose caption best matches the issue type keywords.

    Strategy:
      1. keyword overlap between caption and issue-specific keyword list
      2. tie-break by detection confidence
      3. if no keyword match at all, fall back to highest-confidence element
         (graceful degradation - downstream pipeline still gets a point)
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
    _, _, best_el = scored[0]
    return best_el


def _format_elements(elements: list[dict]) -> str:
    """Human-readable summary for the raw_output field and for prompt
    injection in pipeline/prompts.py.
    """
    if not elements:
        return "OmniParser detected no elements."
    lines = [f"OmniParser detected {len(elements)} element(s):"]
    for i, el in enumerate(elements):
        x1, y1, x2, y2 = el["bbox"]
        lines.append(
            f"  [{i}] bbox=({x1},{y1},{x2},{y2})  "
            f"conf={el['confidence']:.2f}  "
            f'caption="{el["caption"]}"'
        )
    return "\n".join(lines)