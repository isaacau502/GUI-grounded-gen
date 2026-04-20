"""Prod all three OmniParser variants on 5 DesignBench samples (one per
defect type) and dump JSON results + annotated screenshots.

Variants tested:
  v1 (omniparser.py)              : single-point keyword match
  v2 (omniparser2.py)             : full element list, no matching
  structural (omniparser_structural.py) : YOLO + OCR + geometric relations + image stats

Outputs to /content/drive/MyDrive/omniparser-test/:
  {variant}_{issue}_result.json   : full parser output (serializable subset)
  {variant}_{issue}_annotated.png : bboxes drawn on original screenshot

Run on Colab only (needs GPU for YOLO + Florence-2).

Usage (Colab cell):
    !bash colab/jedi_smoke.ipynb cell 1  # or inline: mount Drive, git pull
    !python scripts/prod_omniparser.py
"""

import json
import os
import sys
import traceback
from pathlib import Path

# Colab path (edit if running elsewhere)
REPO_DIR = "/content/GUI-grounded-gen"
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

WEIGHTS_DIR = "/content/drive/MyDrive/omniparser-weights"
OUT_DIR = "/content/drive/MyDrive/omniparser-test"

# Samples we already uploaded via rclone (note nested .png/ dir because
# rclone copy treated dest as dir, not file)
SAMPLES = [
    ("alignment",   "/content/drive/MyDrive/designbench-samples/angular-12-alignment.png/12.png"),
    ("crowding",    "/content/drive/MyDrive/designbench-samples/react-3-crowding.png/3.png"),
    ("occlusion",   "/content/drive/MyDrive/designbench-samples/angular-10-occlusion.png/10.png"),
    ("overflow",    "/content/drive/MyDrive/designbench-samples/angular-26-overflow.png/26.png"),
    ("contrast",    "/content/drive/MyDrive/designbench-samples/angular-9-contrast.png/9.png"),
]


def draw_elements(img, elements, label_color=(255, 0, 0), width=3):
    """Draw all element bboxes on a copy of img. Returns new image."""
    from PIL import ImageDraw, ImageFont
    viz = img.copy()
    draw = ImageDraw.Draw(viz)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    for el in elements:
        x1, y1, x2, y2 = el["bbox"]
        draw.rectangle([x1, y1, x2, y2], outline=label_color, width=width)
        label = f'[{el.get("id", "?")}] {el.get("caption", "")[:40]}'
        draw.text((x1 + 2, max(0, y1 - 12)), label, fill=label_color, font=font)
    return viz


def draw_point(img, point, radius=20, color=(255, 0, 0)):
    """Draw a circle at a click point on a copy of img."""
    from PIL import ImageDraw
    viz = img.copy()
    draw = ImageDraw.Draw(viz)
    x, y = point
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline=color, width=5,
    )
    # Crosshair
    draw.line([(x - radius - 10, y), (x - radius + 3, y)], fill=color, width=3)
    draw.line([(x + radius - 3, y), (x + radius + 10, y)], fill=color, width=3)
    draw.line([(x, y - radius - 10), (x, y - radius + 3)], fill=color, width=3)
    draw.line([(x, y + radius - 3), (x, y + radius + 10)], fill=color, width=3)
    return viz


def to_jsonable(obj):
    """Convert tuples/PIL Images/numpy types to JSON-serializable forms."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # PIL images are not serializable — drop
    if hasattr(obj, "save") and hasattr(obj, "size"):
        return f"<PIL.Image {obj.size}>"
    return obj


# ------------------------------------------------------------------
# v1 runner
# ------------------------------------------------------------------
def run_v1(parser, issue, img_path, out_dir):
    from PIL import Image
    result = parser.query(img_path, issue_type=issue)
    img = Image.open(img_path).convert("RGB")

    # Annotate: all detected elements in blue + click point in red
    viz = img
    if "all_elements" in result and result["all_elements"]:
        viz = draw_elements(viz, result["all_elements"], label_color=(0, 120, 255), width=2)
    if result.get("point"):
        viz = draw_point(viz, result["point"], color=(255, 0, 0))

    viz.save(os.path.join(out_dir, f"v1_{issue}_annotated.png"))
    with open(os.path.join(out_dir, f"v1_{issue}_result.json"), "w") as f:
        json.dump(to_jsonable(result), f, indent=2)
    print(f"  v1 [{issue}] point={result.get('point')}  "
          f"num_elements={len(result.get('all_elements', []))}  "
          f"parse_success={result.get('parse_success')}")


# ------------------------------------------------------------------
# v2 runner
# ------------------------------------------------------------------
def run_v2(parser, issue, img_path, out_dir):
    from PIL import Image
    result = parser.parse(img_path)
    img = Image.open(img_path).convert("RGB")

    viz = draw_elements(img, result["elements"], label_color=(0, 200, 0), width=2)
    viz.save(os.path.join(out_dir, f"v2_{issue}_annotated.png"))

    # Dump full JSON incl. prompt_block
    with open(os.path.join(out_dir, f"v2_{issue}_result.json"), "w") as f:
        json.dump(to_jsonable(result), f, indent=2)
    print(f"  v2 [{issue}] num_elements={result['num_elements']}")
    print(f"     first 200 chars of prompt_block: {result['prompt_block'][:200]}")


# ------------------------------------------------------------------
# structural runner
# ------------------------------------------------------------------
def run_structural(parser, issue, img_path, out_dir):
    from PIL import Image
    result = parser.parse(img_path)
    img = Image.open(img_path).convert("RGB")

    viz = draw_elements(img, result["elements"], label_color=(200, 0, 200), width=2)
    viz.save(os.path.join(out_dir, f"structural_{issue}_annotated.png"))

    with open(os.path.join(out_dir, f"structural_{issue}_result.json"), "w") as f:
        json.dump(to_jsonable(result), f, indent=2)
    print(f"  structural [{issue}] "
          f"num_yolo={result['num_yolo']}  num_ocr={result['num_ocr']}  "
          f"num_relations={len(result['relations'])}  "
          f"luminance_mean={result['image_stats']['luminance_mean']}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Sanity check samples
    missing = [p for _, p in SAMPLES if not os.path.exists(p)]
    if missing:
        print("Missing samples:")
        for p in missing:
            print(f"  {p}")
        print("Fix paths in SAMPLES or re-upload via rclone.")
        return

    # Import variants — done lazily so one broken variant doesn't kill others
    from grounding.omniparser import OmniParser
    from grounding.omniparser2 import OmniParserList
    from grounding.omniparser_structural import OmniParserStructural

    print("=" * 60)
    print("Loading v1 (OmniParser)...")
    print("=" * 60)
    try:
        v1 = OmniParser(weights_dir=WEIGHTS_DIR)
        print("\n--- v1 results ---")
        for issue, path in SAMPLES:
            try:
                run_v1(v1, issue, path, OUT_DIR)
            except Exception:
                print(f"  v1 [{issue}] FAILED:")
                traceback.print_exc()
        del v1
        import gc, torch
        gc.collect(); torch.cuda.empty_cache()
    except Exception:
        print("v1 LOAD FAILED:")
        traceback.print_exc()

    print()
    print("=" * 60)
    print("Loading v2 (OmniParserList)...")
    print("=" * 60)
    try:
        v2 = OmniParserList(weights_dir=WEIGHTS_DIR)
        print("\n--- v2 results ---")
        for issue, path in SAMPLES:
            try:
                run_v2(v2, issue, path, OUT_DIR)
            except Exception:
                print(f"  v2 [{issue}] FAILED:")
                traceback.print_exc()
        del v2
        import gc, torch
        gc.collect(); torch.cuda.empty_cache()
    except Exception:
        print("v2 LOAD FAILED:")
        traceback.print_exc()

    print()
    print("=" * 60)
    print("Loading structural (OmniParserStructural)...")
    print("=" * 60)
    try:
        sp = OmniParserStructural(weights_dir=WEIGHTS_DIR)
        print("\n--- structural results ---")
        for issue, path in SAMPLES:
            try:
                run_structural(sp, issue, path, OUT_DIR)
            except Exception:
                print(f"  structural [{issue}] FAILED:")
                traceback.print_exc()
        del sp
        import gc, torch
        gc.collect(); torch.cuda.empty_cache()
    except Exception:
        print("structural LOAD FAILED:")
        traceback.print_exc()

    print(f"\nDone. Outputs in {OUT_DIR}/")
    print("Inspect annotated .png files in Drive to eyeball quality.")


if __name__ == "__main__":
    main()
