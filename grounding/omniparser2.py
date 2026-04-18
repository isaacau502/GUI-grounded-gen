"""OmniParser-v2 wrapper, element-list variant (Ablation #2).

Difference from omniparser.py:
  - omniparser.py picks ONE best-match element per issue_type via keyword
    matching against captions. Produces a single (x, y) point.
  - omniparser2.py exposes ALL detected elements with bboxes + captions.
    No matching heuristic. The repair model (Qwen) sees the full element
    list and reasons about which elements are involved in each defect.

Rationale:
  Keyword matching over Florence-2 captions fails on whole-area defects
  (overflow, z_order, misalignment) because OmniParser is trained for
  interactable-element detection — it detects individual buttons/icons
  inside a broken section but not the section itself. Rather than force
  a single-point localization that cannot represent area-scale issues,
  we pass the full parsed element list to Qwen and let it do spatial
  reasoning directly.

Output schema (deliberately diverges from JEDI schema):
    {
        "original_size":    (w, h),
        "num_elements":     int,
        "elements":         list[dict],   # every detected element
        "prompt_block":     str,          # formatted for direct prompt injection
    }

Each element:
    {
        "id":         int,                 # 0-indexed, stable for references
        "bbox":       [x1, y1, x2, y2],    # absolute pixels
        "bbox_norm":  [x1, y1, x2, y2],    # 0..1
        "center":     [cx, cy],            # absolute pixels
        "size":       [w, h],              # absolute pixels
        "area":       int,                 # w * h, useful for size priors
        "confidence": float,
        "caption":    str,
    }

Usage:
    from grounding.omniparser2 import OmniParserList
    parser = OmniParserList(weights_dir="...")
    result = parser.parse("/path/to/screenshot.png")
    # pass result["prompt_block"] into the Qwen repair prompt
"""

import os


class OmniParserList:
    """OmniParser wrapper that returns all detected elements, no matching."""

    def __init__(
        self,
        weights_dir: str = "weights",
        bbox_threshold: float = 0.05,
        iou_threshold: float = 0.1,
        device: str = "auto",
        florence_base: str = "microsoft/Florence-2-base",
    ):
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
            raise FileNotFoundError(f"icon_detect weights not found at {detect_path}")
        self.detect_model = YOLO(detect_path)

        # --- icon_caption (Florence-2 fine-tuned) ---
        caption_path = os.path.join(weights_dir, "icon_caption_florence")
        if not os.path.exists(caption_path):
            raise FileNotFoundError(
                f"icon_caption_florence not found at {caption_path}"
            )

        print(f"[omniparser2] Loading Florence-2 base from {florence_base} ...")
        self.caption_processor = AutoProcessor.from_pretrained(
            florence_base, trust_remote_code=True
        )
        self.caption_model = AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )

        weights_file = os.path.join(caption_path, "model.safetensors")
        if not os.path.exists(weights_file):
            raise FileNotFoundError(f"Fine-tuned weights not found at {weights_file}")
        print(f"[omniparser2] Loading fine-tuned weights from {weights_file} ...")
        from safetensors.torch import load_file
        state_dict = load_file(weights_file)
        missing, unexpected = self.caption_model.load_state_dict(
            state_dict, strict=False
        )
        if missing:
            print(f"[omniparser2] warn: {len(missing)} missing keys "
                  f"(first: {missing[:3]})")
        if unexpected:
            print(f"[omniparser2] warn: {len(unexpected)} unexpected keys "
                  f"(first: {unexpected[:3]})")

        self.caption_model = self.caption_model.to(self.device)
        self.caption_model.eval()
        print(f"[omniparser2] Ready on {self.device}.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        image_path: str,
        sort_by: str = "reading_order",
        max_elements: int | None = None,
        min_area: int = 0,
    ) -> dict:
        """Parse screenshot into a list of all detected UI elements.

        Args:
            image_path: path to screenshot
            sort_by: "reading_order" (top-to-bottom, left-to-right),
                     "area_desc" (largest first), or "confidence_desc"
            max_elements: truncate to top-N after sorting (useful for
                          prompt token budget)
            min_area: skip elements smaller than this many pixels^2

        Returns dict with keys: original_size, num_elements, elements,
        prompt_block.
        """
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        elements = self._detect_and_caption(img)

        # Filter
        if min_area > 0:
            elements = [e for e in elements if e["area"] >= min_area]

        # Sort
        elements = _sort_elements(elements, sort_by)

        # Truncate
        if max_elements is not None and len(elements) > max_elements:
            elements = elements[:max_elements]

        # Re-assign stable ids after filter/sort/truncate
        for i, el in enumerate(elements):
            el["id"] = i

        prompt_block = format_prompt_block(elements, (orig_w, orig_h))

        return {
            "original_size": (orig_w, orig_h),
            "num_elements":  len(elements),
            "elements":      elements,
            "prompt_block":  prompt_block,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _detect_and_caption(self, img) -> list[dict]:
        orig_w, orig_h = img.size
        results = self.detect_model(
            img, conf=self.bbox_threshold, iou=self.iou_threshold, verbose=False
        )

        elements = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img.crop((x1, y1, x2, y2))
            caption = self._caption_crop(crop)

            w = x2 - x1
            h = y2 - y1
            elements.append({
                "id":         -1,  # assigned after sort
                "bbox":       [x1, y1, x2, y2],
                "bbox_norm":  [x1 / orig_w, y1 / orig_h,
                               x2 / orig_w, y2 / orig_h],
                "center":     [x1 + w // 2, y1 + h // 2],
                "size":       [w, h],
                "area":       w * h,
                "confidence": float(box.conf[0]),
                "caption":    caption,
            })

        return elements

    def _caption_crop(self, crop) -> str:
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
        for tok in ("<CAPTION>", "</s>", "<s>", "<pad>"):
            caption = caption.replace(tok, "")
        return caption.strip()


# ------------------------------------------------------------------
# Sorting strategies — exposed for ablation
# ------------------------------------------------------------------

def _sort_elements(elements: list[dict], strategy: str) -> list[dict]:
    if strategy == "reading_order":
        # Top-to-bottom, then left-to-right, with a y-bucket to group
        # elements on the same "row". Bucket size = 30px (tunable).
        return sorted(
            elements,
            key=lambda e: (e["bbox"][1] // 30, e["bbox"][0])
        )
    if strategy == "area_desc":
        return sorted(elements, key=lambda e: e["area"], reverse=True)
    if strategy == "confidence_desc":
        return sorted(elements, key=lambda e: e["confidence"], reverse=True)
    raise ValueError(f"unknown sort strategy: {strategy}")


# ------------------------------------------------------------------
# Prompt formatting — this is the main surface for Qwen integration
# ------------------------------------------------------------------

def format_prompt_block(elements: list[dict], image_size: tuple) -> str:
    """Format the element list for direct injection into a repair prompt.

    Format was chosen for token efficiency + parseability:
      - One element per line (Qwen attends better to line-per-item than prose)
      - bbox as [x1,y1,x2,y2] (matches what Qwen2.5-VL was trained on)
      - caption in quotes
      - image size stated once at the top for normalization context
    """
    if not elements:
        return "OmniParser detected no elements on this screenshot."

    w, h = image_size
    lines = [
        f"VISUAL GROUNDING (from OmniParser-v2):",
        f"Image size: {w}x{h} pixels.",
        f"Detected {len(elements)} UI element(s), listed in reading order:",
        "",
    ]
    for el in elements:
        x1, y1, x2, y2 = el["bbox"]
        lines.append(
            f'  [{el["id"]}] bbox=[{x1},{y1},{x2},{y2}] '
            f'size={el["size"][0]}x{el["size"][1]} '
            f'caption="{el["caption"]}"'
        )
    lines.append("")
    lines.append(
        "Use these bboxes to identify which elements are involved in each "
        "reported defect, then fix the corresponding code. Note that "
        "area-scale defects (overflow, z-order, misalignment) may involve "
        "multiple elements or the region between them."
    )
    return "\n".join(lines)


def format_prompt_block_compact(elements: list[dict], image_size: tuple) -> str:
    """Alternative format: ultra-compact, one line per element, no prose.

    Use when token budget matters (many elements, large screenshot).
    """
    if not elements:
        return "OmniParser: no elements detected."
    w, h = image_size
    lines = [f"OmniParser elements ({w}x{h}):"]
    for el in elements:
        x1, y1, x2, y2 = el["bbox"]
        lines.append(f'{el["id"]}:[{x1},{y1},{x2},{y2}] "{el["caption"]}"')
    return "\n".join(lines)
