"""OmniParser-v2 + OCR + image-level features (Ablation #3).

Difference from omniparser2.py:
  - omniparser2.py:  YOLO icon detection + Florence-2 captioning only.
                     Misses pure-text regions (OmniParser is trained for
                     interactable elements) and whole-page property defects
                     like low contrast.
  - omniparser3.py:  three sources merged into one element list:
                       1. YOLO icon detection + Florence-2 captions (as before)
                       2. OCR text regions (EasyOCR)            -> catches pure text,
                                                                    including overlapping text
                       3. Image-level luminance features         -> catches whole-page
                                                                    low-contrast / blank defects

  Each element has a "source" field ("yolo" | "ocr") so downstream code and
  the prompt block can distinguish them. Co-located elements from different
  sources are strong signals (e.g., two OCR boxes at the same bbox -> text
  overlap).

Additional output keys:
    - "image_features": dict with mean_luminance, std_luminance, dark_fraction,
                       light_fraction, histogram_spread
    - "overlaps":        list of (id_a, id_b, iou) for element pairs with
                        IoU > threshold. Useful signal for text_overlap defects.

Usage:
    from grounding.omniparser3 import OmniParserAugmented
    parser = OmniParserAugmented(weights_dir="...", use_ocr=True)
    result = parser.parse("/path/to/screenshot.png")
    # result["prompt_block"] is ready to inject into Qwen repair prompt
"""

import os


class OmniParserAugmented:
    """OmniParser + OCR + image-level features."""

    def __init__(
        self,
        weights_dir: str = "weights",
        bbox_threshold: float = 0.01,       # LOWER than omniparser2 default
        iou_threshold: float = 0.3,          # HIGHER - keep overlaps
        device: str = "auto",
        florence_base: str = "microsoft/Florence-2-base",
        use_ocr: bool = True,
        ocr_languages: list[str] = None,
        min_ocr_confidence: float = 0.3,
    ):
        """Load OmniParser + OCR.

        Args:
            bbox_threshold: YOLO detection confidence. Lowered to 0.01 (from
                0.05) because for defect detection we want recall over precision.
            iou_threshold: YOLO NMS. Raised to 0.3 (from 0.1) so overlapping
                detections are kept — overlap itself is a defect signal.
            use_ocr: if True, run EasyOCR in addition to YOLO. EasyOCR is
                ~100MB and loads ~5s on GPU.
            ocr_languages: default ['en']. Add others like ['en', 'es'] if
                multilingual screenshots are in scope.
            min_ocr_confidence: drop OCR results below this threshold.
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
        self.min_ocr_confidence = min_ocr_confidence
        self.use_ocr = use_ocr

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

        print(f"[omniparser3] Loading Florence-2 base from {florence_base} ...")
        self.caption_processor = AutoProcessor.from_pretrained(
            florence_base, trust_remote_code=True
        )
        self.caption_model = AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )

        weights_file = os.path.join(caption_path, "model.safetensors")
        print(f"[omniparser3] Loading fine-tuned weights ...")
        from safetensors.torch import load_file
        state_dict = load_file(weights_file)
        missing, unexpected = self.caption_model.load_state_dict(
            state_dict, strict=False
        )
        if missing:
            print(f"[omniparser3] warn: {len(missing)} missing keys")
        if unexpected:
            print(f"[omniparser3] warn: {len(unexpected)} unexpected keys")

        self.caption_model = self.caption_model.to(self.device)
        self.caption_model.eval()

        # --- OCR ---
        self.ocr_reader = None
        if use_ocr:
            print(f"[omniparser3] Loading EasyOCR ...")
            import easyocr
            langs = ocr_languages or ["en"]
            self.ocr_reader = easyocr.Reader(
                langs, gpu=(self.device == "cuda"), verbose=False,
            )

        print(f"[omniparser3] Ready on {self.device}.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        image_path: str,
        sort_by: str = "reading_order",
        max_elements: int | None = None,
        min_area: int = 0,
        compute_overlaps: bool = True,
        compute_features: bool = True,
    ) -> dict:
        """Parse image with YOLO + OCR + image features.

        Returns:
            {
                "original_size":    (w, h),
                "num_elements":     int,
                "num_yolo":         int,
                "num_ocr":          int,
                "elements":         list[dict],     # merged, sorted
                "image_features":   dict,           # luminance stats
                "overlaps":         list[dict],     # element pairs with high IoU
                "prompt_block":     str,            # ready for Qwen
            }
        """
        from PIL import Image
        import numpy as np

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        img_np = np.array(img)

        # --- Source 1: YOLO + Florence-2 ---
        yolo_elements = self._detect_and_caption_yolo(img)

        # --- Source 2: OCR ---
        ocr_elements = []
        if self.use_ocr and self.ocr_reader is not None:
            ocr_elements = self._run_ocr(img_np, orig_w, orig_h)

        # Merge
        elements = yolo_elements + ocr_elements

        # Filter by area
        if min_area > 0:
            elements = [e for e in elements if e["area"] >= min_area]

        # Sort
        elements = _sort_elements(elements, sort_by)

        # Truncate
        if max_elements is not None and len(elements) > max_elements:
            elements = elements[:max_elements]

        # Stable ids
        for i, el in enumerate(elements):
            el["id"] = i

        # --- Source 3: image-level features ---
        image_features = {}
        if compute_features:
            image_features = _compute_image_features(img_np)

        # --- Derived signals: element overlaps ---
        overlaps = []
        if compute_overlaps:
            overlaps = _compute_overlaps(elements)

        prompt_block = format_prompt_block(
            elements, (orig_w, orig_h), image_features, overlaps,
        )

        return {
            "original_size":  (orig_w, orig_h),
            "num_elements":   len(elements),
            "num_yolo":       sum(1 for e in elements if e["source"] == "yolo"),
            "num_ocr":        sum(1 for e in elements if e["source"] == "ocr"),
            "elements":       elements,
            "image_features": image_features,
            "overlaps":       overlaps,
            "prompt_block":   prompt_block,
        }

    # ------------------------------------------------------------------
    # Internal detectors
    # ------------------------------------------------------------------

    def _detect_and_caption_yolo(self, img) -> list[dict]:
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

            w, h = x2 - x1, y2 - y1
            elements.append({
                "id":         -1,
                "source":     "yolo",
                "bbox":       [x1, y1, x2, y2],
                "bbox_norm":  [x1 / orig_w, y1 / orig_h,
                               x2 / orig_w, y2 / orig_h],
                "center":     [x1 + w // 2, y1 + h // 2],
                "size":       [w, h],
                "area":       w * h,
                "confidence": float(box.conf[0]),
                "caption":    caption,
                "text":       None,
            })
        return elements

    def _caption_crop(self, crop) -> str:
        import torch
        inputs = self.caption_processor(
            text="<CAPTION>", images=crop, return_tensors="pt"
        ).to(self.device)
        with torch.no_grad():
            ids = self.caption_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=64, num_beams=3,
            )
        caption = self.caption_processor.batch_decode(
            ids, skip_special_tokens=False
        )[0]
        for tok in ("<CAPTION>", "</s>", "<s>", "<pad>"):
            caption = caption.replace(tok, "")
        return caption.strip()

    def _run_ocr(self, img_np, orig_w, orig_h) -> list[dict]:
        """Run EasyOCR. Each detection becomes an element with source='ocr'."""
        results = self.ocr_reader.readtext(img_np)

        elements = []
        for bbox_4pt, text, conf in results:
            if conf < self.min_ocr_confidence:
                continue
            # EasyOCR returns [[x,y], [x,y], [x,y], [x,y]] - 4 corner points
            xs = [p[0] for p in bbox_4pt]
            ys = [p[1] for p in bbox_4pt]
            x1, y1 = int(min(xs)), int(min(ys))
            x2, y2 = int(max(xs)), int(max(ys))
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            w, h = x2 - x1, y2 - y1
            # Truncate long strings in caption for prompt readability
            display_text = text if len(text) <= 60 else text[:57] + "..."
            elements.append({
                "id":         -1,
                "source":     "ocr",
                "bbox":       [x1, y1, x2, y2],
                "bbox_norm":  [x1 / orig_w, y1 / orig_h,
                               x2 / orig_w, y2 / orig_h],
                "center":     [x1 + w // 2, y1 + h // 2],
                "size":       [w, h],
                "area":       w * h,
                "confidence": float(conf),
                "caption":    f'text: "{display_text}"',
                "text":       text,
            })
        return elements


# ------------------------------------------------------------------
# Sorting (same as omniparser2)
# ------------------------------------------------------------------

def _sort_elements(elements: list[dict], strategy: str) -> list[dict]:
    if strategy == "reading_order":
        return sorted(elements, key=lambda e: (e["bbox"][1] // 30, e["bbox"][0]))
    if strategy == "area_desc":
        return sorted(elements, key=lambda e: e["area"], reverse=True)
    if strategy == "confidence_desc":
        return sorted(elements, key=lambda e: e["confidence"], reverse=True)
    if strategy == "source_then_reading":
        # OCR first, then YOLO. Within each, reading order.
        return sorted(elements,
                      key=lambda e: (0 if e["source"] == "ocr" else 1,
                                     e["bbox"][1] // 30, e["bbox"][0]))
    raise ValueError(f"unknown sort strategy: {strategy}")


# ------------------------------------------------------------------
# Image-level features (catches low-contrast / blank-area defects)
# ------------------------------------------------------------------

def _compute_image_features(img_np) -> dict:
    """Summary stats over the whole image. Cheap to compute, very informative
    for whole-page property defects.
    """
    import numpy as np

    # Grayscale
    if img_np.ndim == 3:
        gray = np.mean(img_np, axis=2)
    else:
        gray = img_np

    mean_lum = float(gray.mean())
    std_lum  = float(gray.std())
    return {
        "mean_luminance":    round(mean_lum, 1),
        "std_luminance":     round(std_lum, 1),
        "histogram_spread":  float(gray.max() - gray.min()),
        "dark_fraction":     round(float((gray < 50).mean()), 3),
        "light_fraction":    round(float((gray > 200).mean()), 3),
        "low_contrast_flag": bool(std_lum < 30),    # heuristic threshold
        "near_monochrome_flag": bool(
            (gray < 50).mean() > 0.6 or (gray > 200).mean() > 0.6
        ),
    }


# ------------------------------------------------------------------
# Overlap detection (catches text_overlap defects)
# ------------------------------------------------------------------

def _compute_overlaps(elements: list[dict], iou_threshold: float = 0.3) -> list[dict]:
    """Find element pairs whose bboxes have IoU > threshold.
    High overlap between distinct elements is a strong signal for overlap defects.
    """
    overlaps = []
    for i, a in enumerate(elements):
        for j in range(i + 1, len(elements)):
            b = elements[j]
            iou = _bbox_iou(a["bbox"], b["bbox"])
            if iou >= iou_threshold:
                overlaps.append({
                    "id_a": a["id"], "id_b": b["id"],
                    "iou": round(iou, 3),
                    "source_a": a["source"], "source_b": b["source"],
                })
    return overlaps


def _bbox_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    intersection = iw * ih
    if intersection == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return intersection / (area_a + area_b - intersection)


# ------------------------------------------------------------------
# Prompt formatting
# ------------------------------------------------------------------

def format_prompt_block(
    elements: list[dict],
    image_size: tuple,
    image_features: dict,
    overlaps: list[dict],
) -> str:
    """Three sections: image-level features, element list, overlap signals."""
    w, h = image_size
    lines = [
        f"VISUAL GROUNDING (from OmniParser-v2 + EasyOCR):",
        f"Image size: {w}x{h} pixels.",
    ]

    # --- Image-level features (only show if flags are interesting) ---
    if image_features:
        flags = []
        if image_features.get("low_contrast_flag"):
            flags.append(
                f"LOW CONTRAST DETECTED "
                f"(std_luminance={image_features['std_luminance']:.0f}, "
                f"normal range 40-80 for typical web pages)"
            )
        if image_features.get("near_monochrome_flag"):
            dark = image_features.get('dark_fraction', 0)
            light = image_features.get('light_fraction', 0)
            flags.append(
                f"NEAR-MONOCHROME: dark_fraction={dark:.0%}, "
                f"light_fraction={light:.0%}"
            )
        if flags:
            lines.append("")
            lines.append("Image-level warnings:")
            for flag in flags:
                lines.append(f"  * {flag}")
        lines.append(
            f"Stats: mean_luminance={image_features['mean_luminance']:.0f}, "
            f"std_luminance={image_features['std_luminance']:.0f}, "
            f"dark_fraction={image_features['dark_fraction']:.0%}, "
            f"light_fraction={image_features['light_fraction']:.0%}"
        )

    # --- Element list ---
    if not elements:
        lines.append("")
        lines.append("No UI elements or text regions detected.")
    else:
        n_yolo = sum(1 for e in elements if e["source"] == "yolo")
        n_ocr = sum(1 for e in elements if e["source"] == "ocr")
        lines.append("")
        lines.append(
            f"Detected {len(elements)} element(s): {n_yolo} interactive "
            f"(YOLO) + {n_ocr} text (OCR), listed in reading order:"
        )
        lines.append("")
        for el in elements:
            x1, y1, x2, y2 = el["bbox"]
            src_tag = "[YOLO]" if el["source"] == "yolo" else "[OCR ]"
            lines.append(
                f'  {src_tag} [{el["id"]}] bbox=[{x1},{y1},{x2},{y2}] '
                f'size={el["size"][0]}x{el["size"][1]} '
                f'caption={el["caption"]}'
            )

    # --- Overlap signals ---
    if overlaps:
        lines.append("")
        lines.append(
            f"OVERLAP SIGNALS: {len(overlaps)} element pair(s) with IoU>0.3. "
            f"High overlap between distinct elements often indicates a "
            f"text_overlap or misalignment defect:"
        )
        for ov in overlaps[:10]:  # cap at 10 for prompt budget
            lines.append(
                f'  * element [{ov["id_a"]}] ({ov["source_a"]}) '
                f'overlaps element [{ov["id_b"]}] ({ov["source_b"]}) '
                f'with IoU={ov["iou"]:.2f}'
            )
        if len(overlaps) > 10:
            lines.append(f'  ... ({len(overlaps) - 10} more overlaps)')

    lines.append("")
    lines.append(
        "Use these signals to identify which elements (or image-level "
        "properties) are involved in each reported defect. Note: "
        "text_overlap often shows up as overlapping bboxes; low_contrast "
        "often shows up as low std_luminance; whole-area defects may not "
        "map to any single element."
    )
    return "\n".join(lines)
