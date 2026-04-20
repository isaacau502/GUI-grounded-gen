"""Pre-compute JEDI-7B click coordinates for all DesignBench repair screenshots.

For each (framework, web_number) repair sample, reads the sample JSON to
extract the list of design issues (`issue` field — can be a string or a list
of strings). For every issue, runs JEDI with a defect-type-aware click query
and stores the parsed (x, y) in a single JSON cache.

Downstream `run_repair_grounded_jedi.py` reads this cache and injects the
(issue, click_point) pairs as natural language into Qwen's repair prompt.

Run on Colab (JEDI-only runtime). Then rclone the output to local.

Output:
    /content/drive/MyDrive/omniparser-test/jedi_cache.json
    {
      "react/1": {
        "original_size": [w, h],
        "issues": [
          {"issue_type": "occlusion", "point": [685, 308],
           "parse_success": true, "raw_output": "pyautogui.click(x=..."},
          ...
        ]
      },
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

from grounding.jedi import JEDI
from grounding.prompts import CLICK_ELEMENT, format_query

# Paths on Colab; override with env vars for local runs.
DESIGNBENCH_ROOT = os.environ.get(
    "DESIGNBENCH_ROOT",
    "/content/drive/MyDrive/DesignBench" if os.path.exists("/content/drive") else str(REPO / "external/DesignBench"),
)
JEDI_WEIGHTS = os.environ.get(
    "JEDI_WEIGHTS",
    "/content/drive/MyDrive/jedi-weights",
)
OUT_PATH = os.environ.get(
    "GROUNDING_CACHE",
    "/content/drive/MyDrive/omniparser-test/jedi_cache.json",
)

# Repair sample counts per framework (from DesignBench runner).
REPAIR_COUNTS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}


def iter_samples():
    for fw, n in REPAIR_COUNTS.items():
        for i in range(1, n + 1):
            sample_dir = Path(DESIGNBENCH_ROOT) / "data" / "DesignRepair" / fw / str(i)
            png = sample_dir / f"{i}.png"
            meta = sample_dir / f"{i}.json"
            if png.exists() and meta.exists():
                yield fw, i, png, meta


def load_issues(meta_path: Path) -> list:
    """Return a list[str] of issue types from a sample JSON.

    The DesignBench schema stores `issue` as either a string (single defect)
    or a list of strings (multiple defects). Normalize to a list.
    """
    with open(meta_path) as f:
        meta = json.load(f)
    issue = meta.get("issue", [])
    if isinstance(issue, str):
        return [issue]
    if isinstance(issue, list):
        return [str(x) for x in issue]
    return []


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    # Resume if partial cache exists.
    cache = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            cache = json.load(f)
        print(f"Resuming from {OUT_PATH} ({len(cache)} entries).")

    # Allow weights_dir via env var; JEDI class accepts HF repo ids. We pass
    # the env path through as-is (JEDI caches under HF_HOME or reads a local
    # snapshot directly).
    jedi_model = os.environ.get("JEDI_MODEL", "xlangai/Jedi-7B-1080p")
    if os.path.isdir(JEDI_WEIGHTS):
        # Use a local snapshot path if provided; otherwise rely on HF cache.
        jedi_model = JEDI_WEIGHTS

    jedi = JEDI(model_path=jedi_model)
    print(f"JEDI loaded from {jedi_model}.")

    samples = list(iter_samples())
    print(f"Processing {len(samples)} samples.")

    t0 = time.time()
    for idx, (fw, i, png, meta) in enumerate(samples, 1):
        key = f"{fw}/{i}"
        if key in cache and "issues" in cache[key]:
            continue

        issues = load_issues(meta)
        if not issues:
            cache[key] = {"original_size": None, "issues": []}
            continue

        issue_results = []
        orig_size = None
        try:
            for issue_type in issues:
                query = format_query(CLICK_ELEMENT, issue_type=issue_type)
                res = jedi.query(str(png), query)
                orig_size = list(res["original_size"])
                point = res["point"]
                issue_results.append({
                    "issue_type": issue_type,
                    "point": list(point) if point is not None else None,
                    "parse_success": bool(res["parse_success"]),
                    "raw_output": res["raw_output"],
                })
            cache[key] = {
                "original_size": orig_size,
                "issues": issue_results,
            }
        except Exception as e:
            cache[key] = {"error": str(e), "issues": issue_results,
                          "original_size": orig_size}
            print(f"  [{idx}/{len(samples)}] {key} FAILED: {e}")
            continue

        if idx % 5 == 0 or idx == len(samples):
            with open(OUT_PATH, "w") as f:
                json.dump(cache, f)
            elapsed = time.time() - t0
            rate = idx / elapsed
            eta = (len(samples) - idx) / rate if rate > 0 else 0
            n_ok = sum(1 for r in cache[key].get("issues", []) if r.get("parse_success"))
            n_tot = len(cache[key].get("issues", []))
            print(f"  [{idx}/{len(samples)}] {key}  parsed={n_ok}/{n_tot}  "
                  f"elapsed={elapsed:.0f}s  eta={eta:.0f}s")

    with open(OUT_PATH, "w") as f:
        json.dump(cache, f)
    print(f"\nDone. {len(cache)} entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
