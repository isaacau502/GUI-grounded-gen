"""Render OmniParser / JEDI grounding overlays on top of broken screenshots.

For the hero qualitative panel: we want to show what the grounding model
"saw" so the viewer connects the bboxes to the repair. This takes the
cached grounding output and renders it as an annotated PNG next to the
original screenshot.

Output: poster/grounding_overlays/{framework}_{size}_{variant}_{sample_id}.png
"""

import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "external/DesignBench/data/DesignRepair"
OUT_DIR = REPO / "poster/grounding_overlays"

# Regex for structural-cache prompt_block bbox lines:
#   [  0] YOLO bbox=[219,106,937,617] size=718x511 conf=0.13 caption=An image or profile view
BBOX_RE = re.compile(
    r"\[\s*(\d+)\s*\]\s+(YOLO|OCR)\s+bbox=\[(\d+),(\d+),(\d+),(\d+)\].*?caption=(.*?)(?=\s*(?:\[\s*\d|$|\n))",
    re.DOTALL,
)

YOLO_COLOR = (220, 20, 60, 180)   # crimson
OCR_COLOR = (30, 144, 255, 180)   # dodger blue
JEDI_COLOR = (50, 200, 50, 220)   # green for click points


def parse_structural_bboxes(prompt_block):
    """Parse a structural prompt_block into a list of dicts."""
    out = []
    # Match only the element list block — strip after "Geometric relations:"
    body = prompt_block.split("Geometric relations:")[0]
    for match in re.finditer(
        r"\[\s*(\d+)\s*\]\s+(YOLO|OCR)\s+bbox=\[(\d+),(\d+),(\d+),(\d+)\]\s+size=\S+\s+conf=\S+\s+caption=(.+?)(?=\n|$)",
        body,
    ):
        idx, tag, x1, y1, x2, y2, caption = match.groups()
        out.append({
            "id": int(idx),
            "tag": tag,
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "caption": caption.strip(),
        })
    return out


def render_omniparser_overlay(screenshot_path, bboxes, out_path,
                              min_conf_area=0, show_captions=True):
    """Draw bboxes + optional captions on top of the broken screenshot."""
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18
        )
    except OSError:
        font = ImageFont.load_default()

    for el in bboxes:
        x1, y1, x2, y2 = el["bbox"]
        color = YOLO_COLOR if el["tag"] == "YOLO" else OCR_COLOR

        # translucent filled rect for the element
        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)

        # label block (ID + tag)
        label = f"{el['id']}:{el['tag']}"
        tbw = draw.textlength(label, font=font)
        draw.rectangle(
            [x1, max(0, y1 - 26), x1 + tbw + 8, y1],
            fill=color,
        )
        draw.text((x1 + 4, y1 - 22), label, fill="white", font=font)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(out_path)
    return out_path


def render_jedi_overlay(screenshot_path, points, out_path):
    """Draw JEDI click points on top of the broken screenshot.

    points: list of {issue_type, point: [x, y], parse_success: bool}
    """
    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22
        )
    except OSError:
        font = ImageFont.load_default()

    for p in points:
        if not p.get("parse_success") or p.get("point") is None:
            continue
        x, y = p["point"]
        r = 18
        # crosshair + disk
        draw.ellipse([x - r, y - r, x + r, y + r], outline=JEDI_COLOR, width=5)
        draw.line([x - r, y, x + r, y], fill=JEDI_COLOR, width=3)
        draw.line([x, y - r, x, y + r], fill=JEDI_COLOR, width=3)
        # label above
        label = p.get("issue_type", "?")
        tbw = draw.textlength(label, font=font)
        lx = min(x + r + 4, img.width - tbw - 8)
        ly = max(0, y - 40)
        draw.rectangle([lx, ly, lx + tbw + 8, ly + 28], fill=JEDI_COLOR)
        draw.text((lx + 4, ly + 4), label, fill="white", font=font)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(out_path)
    return out_path


def render_overlay(framework, sample_id, variant="omni"):
    """Top-level: render overlay for one sample, given the variant."""
    screenshot = DATA / framework / str(sample_id) / f"{sample_id}.png"
    if not screenshot.exists():
        raise FileNotFoundError(f"No screenshot: {screenshot}")

    out_path = OUT_DIR / f"{framework}_{variant}_{sample_id}.png"

    if variant == "omni":
        cache = json.loads((REPO / "grounding_structural_cache.json").read_text())
        key = f"{framework}/{sample_id}"
        entry = cache.get(key)
        if not entry:
            raise KeyError(f"No cache entry: {key}")
        bboxes = parse_structural_bboxes(entry["prompt_block"])
        return render_omniparser_overlay(screenshot, bboxes, out_path)
    elif variant == "jedi":
        cache = json.loads((REPO / "jedi_cache.json").read_text())
        key = f"{framework}/{sample_id}"
        entry = cache.get(key)
        if not entry:
            raise KeyError(f"No cache entry: {key}")
        points = entry.get("issues", [])
        return render_jedi_overlay(screenshot, points, out_path)
    else:
        raise ValueError(f"Unknown variant: {variant}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--framework", default="angular")
    ap.add_argument("--variant", default="omni", choices=["omni", "jedi"])
    ap.add_argument("--samples", nargs="+", type=int, default=[3, 11, 13, 15, 17])
    args = ap.parse_args()

    for sid in args.samples:
        try:
            out = render_overlay(args.framework, sid, args.variant)
            print(f"OK  {out}")
        except Exception as e:
            print(f"FAIL {args.framework}/{sid}: {e}")


if __name__ == "__main__":
    main()
