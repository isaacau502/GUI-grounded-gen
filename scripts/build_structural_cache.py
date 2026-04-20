"""Pre-compute OmniParser structural grounding for all DesignBench repair screenshots.

Uses OmniParserStructural (YOLO + EasyOCR + pairwise relations + Florence-2
captions) rather than v2. Structural's prompt_block is richer for layout
defects since it includes OCR text + geometric relations.

Outputs:
    grounding_structural_cache.json
    {
      "react/1": { "prompt_block": "...", "num_elements": N, ... },
      ...
    }

Run locally (CPU/MPS, ~30s/sample, ~50 min for 111).
"""

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from grounding.omniparser_structural import OmniParserStructural

DESIGNBENCH_ROOT = os.environ.get(
    "DESIGNBENCH_ROOT",
    str(REPO / "external" / "DesignBench"),
)
OMNI_WEIGHTS = os.environ.get("OMNI_WEIGHTS", str(REPO / "omniparser-weights"))
OUT_PATH = Path(os.environ.get(
    "GROUNDING_CACHE",
    str(REPO / "grounding_structural_cache.json"),
))

REPAIR_COUNTS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}


def iter_samples():
    for fw, n in REPAIR_COUNTS.items():
        for i in range(1, n + 1):
            png = Path(DESIGNBENCH_ROOT) / "data" / "DesignRepair" / fw / str(i) / f"{i}.png"
            if png.exists():
                yield fw, i, png


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if OUT_PATH.exists():
        with open(OUT_PATH) as f:
            cache = json.load(f)
        print(f"Resuming from {OUT_PATH} ({len(cache)} entries).")

    parser = OmniParserStructural(weights_dir=OMNI_WEIGHTS)

    samples = list(iter_samples())
    print(f"Processing {len(samples)} samples.")

    t0 = time.time()
    for idx, (fw, i, png) in enumerate(samples, 1):
        key = f"{fw}/{i}"
        if key in cache:
            continue
        try:
            result = parser.parse(str(png))
            # Keep the prompt_block + element count + size. Drop bulky per-element list
            # to keep cache small (full elements recoverable from re-running if needed).
            cache[key] = {
                "prompt_block": result["prompt_block"],
                "num_elements": result["num_elements"],
                "num_yolo": result.get("num_yolo"),
                "num_ocr": result.get("num_ocr"),
                "original_size": result["original_size"],
            }
        except Exception as e:
            cache[key] = {"error": repr(e)}
            print(f"  [{idx}/{len(samples)}] {key} FAILED: {e}")
            continue

        if idx % 3 == 0 or idx == len(samples):
            with open(OUT_PATH, "w") as f:
                json.dump(cache, f)
            elapsed = time.time() - t0
            rate = idx / elapsed
            eta = (len(samples) - idx) / rate if rate > 0 else 0
            print(f"  [{idx}/{len(samples)}] {key}  n={cache[key].get('num_elements', '?')}  "
                  f"elapsed={elapsed:.0f}s  eta={eta:.0f}s")

    with open(OUT_PATH, "w") as f:
        json.dump(cache, f)
    print(f"\nDone. {len(cache)} entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
