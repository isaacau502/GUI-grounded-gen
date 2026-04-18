"""Batch grounding over all DesignBench samples using OmniParser-v2.

Run on Colab (GPU). Outputs one JSON per sample to grounding/cache/.
Same schema as the JEDI plan so pipeline/run.py needs no changes.

Usage:
    python -m grounding.batch \\
        --designbench_root /content/drive/MyDrive/DesignBench \\
        --weights_dir /content/drive/MyDrive/omniparser_weights \\
        --output_dir grounding/cache \\
        --frameworks react vue angular vanilla \\
        --max_samples 5        # smoke test; remove for full run
"""

import argparse
import json
import os
from pathlib import Path


def load_samples(designbench_root: str, frameworks: list[str], max_samples: int | None):
    samples = []
    for fw in frameworks:
        fw_dir = Path(designbench_root) / "data" / "DesignRepair" / fw
        if not fw_dir.exists():
            print(f"[warn] {fw_dir} not found, skipping")
            continue
        ids = sorted(
            int(p.name) for p in fw_dir.iterdir()
            if p.is_dir() and p.name.isdigit()
        )
        if max_samples:
            ids = ids[:max_samples]
        for sid in ids:
            sample_dir = fw_dir / str(sid)
            json_path = sample_dir / f"{sid}.json"
            img_path = sample_dir / f"{sid}.png"
            if not json_path.exists() or not img_path.exists():
                continue
            with open(json_path) as f:
                meta = json.load(f)
            samples.append({
                "framework": fw,
                "sample_id": sid,
                "image_path": str(img_path),
                "issues": meta.get("issues", []),
                "image_size": None,  # filled during grounding
            })
    return samples


def run_batch(
    designbench_root: str,
    weights_dir: str,
    output_dir: str,
    frameworks: list[str] = None,
    max_samples: int | None = None,
    bbox_threshold: float = 0.05,
    iou_threshold: float = 0.1,
    skip_existing: bool = True,
):
    from grounding.omniparser import OmniParser
    from PIL import Image

    frameworks = frameworks or ["react", "vue", "angular", "vanilla"]
    os.makedirs(output_dir, exist_ok=True)

    print(f"[batch] Loading OmniParser from {weights_dir} ...")
    parser = OmniParser(
        weights_dir=weights_dir,
        bbox_threshold=bbox_threshold,
        iou_threshold=iou_threshold,
    )
    print("[batch] Model loaded.")

    samples = load_samples(designbench_root, frameworks, max_samples)
    print(f"[batch] {len(samples)} samples to process.")

    for i, sample in enumerate(samples):
        fw = sample["framework"]
        sid = sample["sample_id"]
        out_path = Path(output_dir) / f"{fw}_{sid}_grounding.json"

        if skip_existing and out_path.exists():
            print(f"[{i+1}/{len(samples)}] {fw}/{sid} — skip (cached)")
            continue

        img = Image.open(sample["image_path"])
        orig_w, orig_h = img.size

        annotations = []
        for issue in sample["issues"]:
            issue_type = issue.get("type", "unknown")
            issue_desc = issue.get("description", "")

            result = parser.query(sample["image_path"], issue_type)

            annotations.append({
                "issue_type": issue_type,
                "issue_description": issue_desc,
                "query": issue_type,           # OmniParser needs no query string
                "point": result["point"],
                "parse_success": result["parse_success"],
                "raw_output": result["raw_output"],
                # extra vs JEDI — richer for prompt use, ignored by pipeline if absent
                "all_elements": result["all_elements"],
            })

        output = {
            "framework": fw,
            "sample_id": sid,
            "image_path": sample["image_path"],
            "image_size": [orig_w, orig_h],
            "annotations": annotations,
        }

        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

        n_success = sum(1 for a in annotations if a["parse_success"])
        print(f"[{i+1}/{len(samples)}] {fw}/{sid} — "
              f"{n_success}/{len(annotations)} issues located → {out_path.name}")

    print("[batch] Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--designbench_root", required=True)
    ap.add_argument("--weights_dir", required=True)
    ap.add_argument("--output_dir", default="grounding/cache")
    ap.add_argument("--frameworks", nargs="+",
                    default=["react", "vue", "angular", "vanilla"])
    ap.add_argument("--max_samples", type=int, default=None)
    ap.add_argument("--bbox_threshold", type=float, default=0.05)
    ap.add_argument("--iou_threshold", type=float, default=0.1)
    ap.add_argument("--no_skip", action="store_true")
    args = ap.parse_args()

    run_batch(
        designbench_root=args.designbench_root,
        weights_dir=args.weights_dir,
        output_dir=args.output_dir,
        frameworks=args.frameworks,
        max_samples=args.max_samples,
        bbox_threshold=args.bbox_threshold,
        iou_threshold=args.iou_threshold,
        skip_existing=not args.no_skip,
    )