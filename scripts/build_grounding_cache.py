"""Pre-compute OmniParser v2 grounding for all DesignBench repair screenshots.

Runs OmniParserList over every (framework, web_number) repair sample and
saves a single JSON cache. Downstream `run_repair_grounded.py` reads this
cache and injects the `prompt_block` field into Qwen's repair prompt.

Run on Colab (OmniParser-only runtime). Then rclone the output to local.

Output:
    /content/drive/MyDrive/omniparser-test/grounding_cache.json
    {
      "react/1":   { "prompt_block": "...", "num_elements": N, "elements": [...] },
      "react/2":   { ... },
      ...
    }
"""

import json
import os
import sys
import time
from pathlib import Path

# Allow running on Colab (repo mounted at /content/GUI-grounded-gen) or local.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from grounding.omniparser2 import OmniParserList

# Paths on Colab; override with env vars for local runs.
DESIGNBENCH_ROOT = os.environ.get(
    "DESIGNBENCH_ROOT",
    "/content/drive/MyDrive/DesignBench" if os.path.exists("/content/drive") else str(REPO / "external/DesignBench"),
)
OMNI_WEIGHTS = os.environ.get(
    "OMNI_WEIGHTS",
    "/content/drive/MyDrive/omniparser-weights",
)
OUT_PATH = os.environ.get(
    "GROUNDING_CACHE",
    "/content/drive/MyDrive/omniparser-test/grounding_cache.json",
)

# Repair sample counts per framework (from DesignBench runner).
REPAIR_COUNTS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}


def iter_samples():
    for fw, n in REPAIR_COUNTS.items():
        for i in range(1, n + 1):
            png = Path(DESIGNBENCH_ROOT) / "data" / "DesignRepair" / fw / str(i) / f"{i}.png"
            if png.exists():
                yield fw, i, png


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    # Resume if partial cache exists.
    cache = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            cache = json.load(f)
        print(f"Resuming from {OUT_PATH} ({len(cache)} entries).")

    parser = OmniParserList(weights_dir=OMNI_WEIGHTS)
    print("OmniParser loaded.")

    samples = list(iter_samples())
    print(f"Processing {len(samples)} samples.")

    t0 = time.time()
    for idx, (fw, i, png) in enumerate(samples, 1):
        key = f"{fw}/{i}"
        if key in cache:
            continue
        try:
            result = parser.parse(str(png))
            # Drop large fields we don't need in the cache; keep prompt_block + elements.
            cache[key] = {
                "prompt_block": result["prompt_block"],
                "num_elements": result["num_elements"],
                "original_size": result["original_size"],
                "elements": result["elements"],
            }
        except Exception as e:
            cache[key] = {"error": str(e)}
            print(f"  [{idx}/{len(samples)}] {key} FAILED: {e}")
            continue

        if idx % 5 == 0 or idx == len(samples):
            with open(OUT_PATH, "w") as f:
                json.dump(cache, f)
            elapsed = time.time() - t0
            rate = idx / elapsed
            eta = (len(samples) - idx) / rate if rate > 0 else 0
            print(f"  [{idx}/{len(samples)}] {key}  n_elements={cache[key].get('num_elements', '?')}  "
                  f"elapsed={elapsed:.0f}s  eta={eta:.0f}s")

    with open(OUT_PATH, "w") as f:
        json.dump(cache, f)
    print(f"\nDone. {len(cache)} entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
