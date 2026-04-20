"""OmniParser-v2 + OCR + structural relations (Approach #4).

Design principle:
  Do NOT interpret. Extract structure; let the downstream VLM interpret.

Contrast with prior ablations:
  - omniparser.py:   single point per issue via keyword matching
                     -> fails on whole-area, text-content, property defects
  - omniparser2.py:  flat element list, no matching
                     -> misses relationships between elements
  - omniparser3.py:  element list + defect-specific flags (low_contrast,
                     overlaps). Flags are interpretations: they assume we
                     know which signals matter for which defects.
  - omniparser_structural.py (this):
                     element list + pairwise geometric relations + raw
                     image stats as numbers (not flags). No per-defect
                     logic. Representation is defect-agnostic; the VLM
                     decides what matters.

Rationale:
  UI defects aren't a discrete set. Any hand-engineered signal is a proxy
  tuned to specific defect categories. A representation that exposes
  structure (containment, adjacency, alignment, size ratios) applies
  uniformly to any UI and lets the VLM identify deviations from design
  intent using its existing vision-understanding capability.

Output schema:
    {
        "original_size":   (w, h),
        "num_elements":    int,
        "num_yolo":        int,
        "num_ocr":         int,
        "elements":        list[dict],  # raw, no flags
        "relations":       list[dict],  # pairwise geometric facts
        "image_stats":     dict,        # raw numbers, no flags
        "prompt_block":    str,         # structural description for Qwen
    }

Relations are purely geometric:
    - contains(A, B): A's bbox fully contains B's
    - adjacent(A, B): A and B touch or near-touch (< gap_threshold)
    - aligned(A, B, axis): A and B share an edge or center line (within tol)
    - size_ratio(A, B): ratio of larger to smaller bbox area

No relation implies a defect. Relations are facts about the layout.
"""

import os


class OmniParserStructural:
    """OmniParser + OCR + structural relations, no defect-specific logic."""

    def __init__(
        self,
        weights_dir: str = "weights",
        bbox_threshold: float = 0.01,
        iou_threshold: float = 0.3,
        device: str = "auto",
        florence_base: str = "microsoft/Florence-2-base",
        use_ocr: bool = True,
        ocr_languages: list[str] = None,
        min_ocr_confidence: float = 0.3,
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
        self.min_ocr_confidence = min_ocr_confidence
        self.use_ocr = use_ocr

        # YOLO
        detect_path = os.path.join(weights_dir, "icon_detect", "model.pt")
        if not os.path.exists(detect_path):
            raise FileNotFoundError(f"icon_detect weights not found at {detect_path}")
        self.detect_model = YOLO(detect_path)

        # Florence-2
        caption_path = os.path.join(weights_dir, "icon_caption_florence")
        if not os.path.exists(caption_path):
            raise FileNotFoundError(
                f"icon_caption_florence not found at {caption_path}"
            )
        print(f"[structural] Loading Florence-2 base from {florence_base} ...")
        self.caption_processor = AutoProcessor.from_pretrained(
            florence_base, trust_remote_code=True
        )
        self.caption_model = AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )
        from safetensors.torch import load_file
        weights_file = os.path.join(caption_path, "model.safetensors")
        state_dict = load_file(weights_file)
        missing, unexpected = self.caption_model.load_state_dict(
            state_dict, strict=False
        )
        if missing:
            print(f"[structural] warn: {len(missing)} missing keys")
        self.caption_model = self.caption_model.to(self.device)
        self.caption_model.eval()

        # OCR
        self.ocr_reader = None
        if use_ocr:
            print(f"[structural] Loading EasyOCR ...")
            import easyocr
            langs = ocr_languages or ["en"]
            self.ocr_reader = easyocr.Reader(
                langs, gpu=(self.device == "cuda"), verbose=False,
            )

        print(f"[structural] Ready on {self.device}.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        image_path: str,
        sort_by: str = "reading_order",
        max_elements: int | None = None,
        min_area: int = 0,
        relation_config: dict | None = None,
    ) -> dict:
        """Parse image and compute structural representation.

        relation_config: optional overrides for relation thresholds:
            {
                "adjacency_gap_px":    5,      # max gap to count as adjacent
                "alignment_tolerance": 3,      # pixel tolerance for edge alignment
                "containment_margin":  5,      # pixel slack for containment
                "min_overlap_iou":     0.1,    # min IoU to report partial overlap
            }
        """
        from PIL import Image
        import numpy as np

        cfg = {
            "adjacency_gap_px":    5,
            "alignment_tolerance": 3,
            "containment_margin":  5,
            "min_overlap_iou":     0.1,
        }
        if relation_config:
            cfg.update(relation_config)

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        img_np = np.array(img)

        # Raw element extraction (no interpretation)
        yolo_els = self._detect_and_caption_yolo(img)
        ocr_els = []
        if self.use_ocr and self.ocr_reader is not None:
            ocr_els = self._run_ocr(img_np, orig_w, orig_h)
        elements = yolo_els + ocr_els

        if min_area > 0:
            elements = [e for e in elements if e["area"] >= min_area]
        elements = _sort_elements(elements, sort_by)
        if max_elements is not None and len(elements) > max_elements:
            elements = elements[:max_elements]
        for i, el in enumerate(elements):
            el["id"] = i

        # Relations (all purely geometric)
        relations = _compute_relations(elements, cfg)

        # Image stats (raw numbers only, no interpretive flags)
        image_stats = _compute_image_stats(img_np)

        prompt_block = format_prompt_block(
            elements, relations, image_stats, (orig_w, orig_h),
        )

        return {
            "original_size":  (orig_w, orig_h),
            "num_elements":   len(elements),
            "num_yolo":       sum(1 for e in elements if e["source"] == "yolo"),
            "num_ocr":        sum(1 for e in elements if e["source"] == "ocr"),
            "elements":       elements,
            "relations":      relations,
            "image_stats":    image_stats,
            "prompt_block":   prompt_block,
        }

    # ------------------------------------------------------------------
    # Detectors (same as omniparser3)
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
                "bbox_norm":  [x1/orig_w, y1/orig_h, x2/orig_w, y2/orig_h],
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
        results = self.ocr_reader.readtext(img_np)
        elements = []
        for bbox_4pt, text, conf in results:
            if conf < self.min_ocr_confidence:
                continue
            xs = [p[0] for p in bbox_4pt]
            ys = [p[1] for p in bbox_4pt]
            x1, y1 = int(min(xs)), int(min(ys))
            x2, y2 = int(max(xs)), int(max(ys))
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            w, h = x2 - x1, y2 - y1
            display = text if len(text) <= 60 else text[:57] + "..."
            elements.append({
                "id":         -1,
                "source":     "ocr",
                "bbox":       [x1, y1, x2, y2],
                "bbox_norm":  [x1/orig_w, y1/orig_h, x2/orig_w, y2/orig_h],
                "center":     [x1 + w // 2, y1 + h // 2],
                "size":       [w, h],
                "area":       w * h,
                "confidence": float(conf),
                "caption":    f'text: "{display}"',
                "text":       text,
            })
        return elements


# ==================================================================
# Geometric relations — these are the structural signal
# ==================================================================

def _compute_relations(elements: list[dict], cfg: dict) -> list[dict]:
    """Compute pairwise geometric relations for every element pair.

    Relations are FACTS, not defect signals. The VLM decides which relations
    indicate defects in context.

    Relation types:
        contains          — A's bbox fully contains B's (with margin)
        overlaps_partial  — A and B partially overlap (IoU > threshold,
                            neither contains the other)
        adjacent_horiz    — A and B share a vertical range and are
                            within gap_px horizontally
        adjacent_vert     — A and B share a horizontal range and are
                            within gap_px vertically
        aligned_left      — A and B share a left edge within tolerance
        aligned_right     — same for right edge
        aligned_top       — same for top edge
        aligned_bottom    — same for bottom edge
        aligned_center_x  — A and B share horizontal center within tolerance
        aligned_center_y  — same for vertical center
    """
    relations = []
    for i, a in enumerate(elements):
        for j, b in enumerate(elements):
            if i >= j:
                continue
            rels = _pairwise_relations(a, b, cfg)
            for r in rels:
                relations.append({
                    "id_a": a["id"],
                    "id_b": b["id"],
                    "type": r["type"],
                    **r.get("extra", {}),
                })
    return relations


def _pairwise_relations(a: dict, b: dict, cfg: dict) -> list[dict]:
    """All relations between element a and element b."""
    rels = []

    ax1, ay1, ax2, ay2 = a["bbox"]
    bx1, by1, bx2, by2 = b["bbox"]
    margin = cfg["containment_margin"]
    tol = cfg["alignment_tolerance"]
    gap = cfg["adjacency_gap_px"]

    # Containment
    if (ax1 - margin <= bx1 and ay1 - margin <= by1 and
            bx2 <= ax2 + margin and by2 <= ay2 + margin):
        rels.append({"type": "contains", "extra": {"outer": a["id"], "inner": b["id"]}})
    elif (bx1 - margin <= ax1 and by1 - margin <= ay1 and
            ax2 <= bx2 + margin and ay2 <= by2 + margin):
        rels.append({"type": "contains", "extra": {"outer": b["id"], "inner": a["id"]}})
    else:
        # Partial overlap (only if not contained)
        iou = _bbox_iou(a["bbox"], b["bbox"])
        if iou >= cfg["min_overlap_iou"]:
            rels.append({"type": "overlaps_partial",
                        "extra": {"iou": round(iou, 3)}})

    # Adjacency — only if no overlap
    if not rels or rels[0]["type"] not in ("contains", "overlaps_partial"):
        # Horizontal adjacency: y-ranges overlap, x-gap small
        y_overlap = min(ay2, by2) - max(ay1, by1)
        if y_overlap > 5:
            if 0 <= bx1 - ax2 <= gap:
                rels.append({"type": "adjacent_horiz",
                            "extra": {"left": a["id"], "right": b["id"],
                                      "gap_px": bx1 - ax2}})
            elif 0 <= ax1 - bx2 <= gap:
                rels.append({"type": "adjacent_horiz",
                            "extra": {"left": b["id"], "right": a["id"],
                                      "gap_px": ax1 - bx2}})
        # Vertical adjacency: x-ranges overlap, y-gap small
        x_overlap = min(ax2, bx2) - max(ax1, bx1)
        if x_overlap > 5:
            if 0 <= by1 - ay2 <= gap:
                rels.append({"type": "adjacent_vert",
                            "extra": {"top": a["id"], "bottom": b["id"],
                                      "gap_px": by1 - ay2}})
            elif 0 <= ay1 - by2 <= gap:
                rels.append({"type": "adjacent_vert",
                            "extra": {"top": b["id"], "bottom": a["id"],
                                      "gap_px": ay1 - by2}})

    # Alignment — agnostic to overlap/adjacency status
    if abs(ax1 - bx1) <= tol:
        rels.append({"type": "aligned_left", "extra": {"x": (ax1 + bx1) // 2}})
    if abs(ax2 - bx2) <= tol:
        rels.append({"type": "aligned_right", "extra": {"x": (ax2 + bx2) // 2}})
    if abs(ay1 - by1) <= tol:
        rels.append({"type": "aligned_top", "extra": {"y": (ay1 + by1) // 2}})
    if abs(ay2 - by2) <= tol:
        rels.append({"type": "aligned_bottom", "extra": {"y": (ay2 + by2) // 2}})
    a_cx = (ax1 + ax2) // 2
    b_cx = (bx1 + bx2) // 2
    if abs(a_cx - b_cx) <= tol:
        rels.append({"type": "aligned_center_x", "extra": {"x": (a_cx + b_cx) // 2}})
    a_cy = (ay1 + ay2) // 2
    b_cy = (by1 + by2) // 2
    if abs(a_cy - b_cy) <= tol:
        rels.append({"type": "aligned_center_y", "extra": {"y": (a_cy + b_cy) // 2}})

    return rels


def _bbox_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


# ==================================================================
# Image stats — raw numbers, no interpretive flags
# ==================================================================

def _compute_image_stats(img_np) -> dict:
    """Raw pixel statistics. No thresholds, no flags. Let VLM interpret."""
    import numpy as np
    if img_np.ndim == 3:
        gray = np.mean(img_np, axis=2)
        r = img_np[..., 0].mean(); g = img_np[..., 1].mean(); b = img_np[..., 2].mean()
    else:
        gray = img_np
        r = g = b = float(gray.mean())

    return {
        "luminance_mean":  round(float(gray.mean()), 1),
        "luminance_std":   round(float(gray.std()), 1),
        "luminance_min":   int(gray.min()),
        "luminance_max":   int(gray.max()),
        "mean_rgb":        [round(float(r), 1), round(float(g), 1), round(float(b), 1)],
        "pixels_below_50":  round(float((gray < 50).mean()), 3),
        "pixels_above_200": round(float((gray > 200).mean()), 3),
        "pixels_50_to_200": round(float(((gray >= 50) & (gray <= 200)).mean()), 3),
    }


# ==================================================================
# Sorting
# ==================================================================

def _sort_elements(elements, strategy):
    if strategy == "reading_order":
        return sorted(elements, key=lambda e: (e["bbox"][1] // 30, e["bbox"][0]))
    if strategy == "area_desc":
        return sorted(elements, key=lambda e: e["area"], reverse=True)
    if strategy == "confidence_desc":
        return sorted(elements, key=lambda e: e["confidence"], reverse=True)
    raise ValueError(f"unknown sort: {strategy}")


# ==================================================================
# Prompt formatting — pure structure, no interpretation
# ==================================================================

def format_prompt_block(
    elements: list[dict],
    relations: list[dict],
    image_stats: dict,
    image_size: tuple,
) -> str:
    """Structural description of the UI. No defect-specific language.

    Three sections:
      1. Image-level pixel statistics (raw numbers)
      2. Detected elements (bbox, caption, source, confidence)
      3. Geometric relations between element pairs

    The VLM reads this alongside the screenshot and determines which
    structural facts correspond to reported defects.
    """
    w, h = image_size
    lines = [
        "UI STRUCTURAL REPRESENTATION",
        f"Image: {w}x{h} pixels.",
        "",
    ]

    # --- Pixel statistics ---
    lines.append("Pixel statistics (0-255 scale):")
    lines.append(
        f"  luminance: mean={image_stats['luminance_mean']}, "
        f"std={image_stats['luminance_std']}, "
        f"range=[{image_stats['luminance_min']},{image_stats['luminance_max']}]"
    )
    lines.append(f"  mean RGB: {image_stats['mean_rgb']}")
    lines.append(
        f"  pixel distribution: "
        f"{image_stats['pixels_below_50']:.0%} dark (<50), "
        f"{image_stats['pixels_50_to_200']:.0%} mid, "
        f"{image_stats['pixels_above_200']:.0%} light (>200)"
    )
    lines.append("")

    # --- Elements ---
    if not elements:
        lines.append("No elements detected.")
    else:
        n_yolo = sum(1 for e in elements if e["source"] == "yolo")
        n_ocr = sum(1 for e in elements if e["source"] == "ocr")
        lines.append(
            f"Elements: {len(elements)} total "
            f"({n_yolo} from YOLO icon detection, {n_ocr} from OCR text detection)"
        )
        for el in elements:
            x1, y1, x2, y2 = el["bbox"]
            src = "YOLO" if el["source"] == "yolo" else "OCR "
            lines.append(
                f'  [{el["id"]:3d}] {src} bbox=[{x1},{y1},{x2},{y2}] '
                f'size={el["size"][0]}x{el["size"][1]} '
                f'conf={el["confidence"]:.2f} '
                f'caption={el["caption"]}'
            )

    # --- Relations ---
    if relations:
        lines.append("")
        # Group relations by type for readability
        by_type = {}
        for r in relations:
            by_type.setdefault(r["type"], []).append(r)

        lines.append(f"Geometric relations: {len(relations)} total")
        # Meaningful order: containment, overlap, adjacency, alignment
        order = ["contains", "overlaps_partial",
                 "adjacent_horiz", "adjacent_vert",
                 "aligned_left", "aligned_right",
                 "aligned_top", "aligned_bottom",
                 "aligned_center_x", "aligned_center_y"]
        for rel_type in order:
            if rel_type not in by_type:
                continue
            rels = by_type[rel_type]
            lines.append(f"  {rel_type} ({len(rels)}):")
            for r in rels[:20]:  # cap at 20 per type for prompt budget
                if rel_type == "contains":
                    lines.append(f"    [{r['outer']}] contains [{r['inner']}]")
                elif rel_type == "overlaps_partial":
                    lines.append(
                        f"    [{r['id_a']}] and [{r['id_b']}] overlap "
                        f"(IoU={r['iou']})"
                    )
                elif rel_type == "adjacent_horiz":
                    lines.append(
                        f"    [{r['left']}] adjacent to [{r['right']}] "
                        f"(gap={r['gap_px']}px horizontal)"
                    )
                elif rel_type == "adjacent_vert":
                    lines.append(
                        f"    [{r['top']}] adjacent to [{r['bottom']}] "
                        f"(gap={r['gap_px']}px vertical)"
                    )
                elif rel_type.startswith("aligned_"):
                    axis = "x" if "x" in r else "y"
                    lines.append(
                        f"    [{r['id_a']}] and [{r['id_b']}] "
                        f"{rel_type} at {axis}={r.get(axis, '?')}"
                    )
            if len(rels) > 20:
                lines.append(f"    ... ({len(rels) - 20} more)")

    lines.append("")
    lines.append(
        "This is a structural description. Combined with the screenshot "
        "and source code, identify which structural facts correspond to "
        "the reported defects, then repair the code."
    )
    return "\n".join(lines)
