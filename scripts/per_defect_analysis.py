"""Per-defect-type slicing of existing eval results.

For each sample, DesignBench's config JSON has an `issue` field (string or list of
defect types). Group eval-JSON per-sample metrics by defect type, compute
baseline vs variant deltas, paired Wilcoxon, bootstrap CI. Multi-defect samples
count once per defect they contain.

Output: markdown table per (grounding_variant, defect_type) cross product.
"""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import wilcoxon

REPO = Path(__file__).resolve().parent.parent
DESIGNBENCH = REPO / "external" / "DesignBench"
RES = DESIGNBENCH / "code" / "evaluator" / "res" / "DesignRepair"

FRAMEWORKS = ["react", "vue", "angular", "vanilla"]
METRICS = [
    ("ast_code_op_score", "CMLS"),
    ("ast_code_content_weighted_score", "CMCS"),
    ("issue accuracy", "IssAcc"),
    ("code_score", "CodeScore"),
    ("clip_similarity", "CLIP"),
    ("structure_similarity", "SSIM"),
]
DEFECT_TYPES = [
    "alignment", "crowding", "occlusion", "overflow",
    "color and contrast", "text overlap", "disorder",
]


def load_issues():
    """Map (fw, web_number) → list[str] of defect types."""
    out = {}
    for fw in FRAMEWORKS:
        for i in range(1, 29):
            meta = DESIGNBENCH / "data" / "DesignRepair" / fw / str(i) / f"{i}.json"
            if not meta.exists():
                continue
            with open(meta) as f:
                d = json.load(f)
            iss = d.get("issue", [])
            if isinstance(iss, str):
                iss = [iss]
            out[(fw, str(i))] = iss
    return out


def load_eval(fw, mode):
    p = RES / f"{fw}_{mode}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def per_defect_deltas(baseline_key, variant_key, mode="both"):
    """Return dict: defect_type → list of (baseline_metric, variant_metric) tuples per metric."""
    issues_map = load_issues()

    # per_defect[defect_type][metric_key] = list of (base, var) pairs
    per_defect = defaultdict(lambda: defaultdict(list))

    for fw in FRAMEWORKS:
        data = load_eval(fw, mode)
        if baseline_key not in data or variant_key not in data:
            continue
        b = data[baseline_key]
        v = data[variant_key]
        common = set(b.keys()) & set(v.keys())
        for sid in sorted(common, key=int):
            defects = issues_map.get((fw, sid), [])
            if not defects:
                continue
            for defect in defects:
                for mkey, mlabel in METRICS:
                    bm = b[sid].get(mkey, 0)
                    vm = v[sid].get(mkey, 0)
                    per_defect[defect][mkey].append((bm, vm))
    return per_defect


def run_comparison(label, baseline_key, variant_key, mode, lines):
    pd = per_defect_deltas(baseline_key, variant_key, mode)
    lines.append(f"\n## {label}\n")
    lines.append(f"**{baseline_key}** vs **{variant_key}** (mode={mode})\n")
    header = "| defect | N | " + " | ".join(m[1] for m in METRICS) + " |"
    sep = "|---|---|" + "|".join(["---"] * len(METRICS)) + "|"
    lines.append(header)
    lines.append(sep)
    for defect in DEFECT_TYPES:
        if defect not in pd:
            continue
        row_cells = [defect]
        n_any = 0
        for mkey, mlabel in METRICS:
            pairs = pd[defect].get(mkey, [])
            pairs = [(b, v) for b, v in pairs if not (b == 0 and v == 0)]  # skip all-zero
            if len(pairs) == 0:
                row_cells.append("—")
                continue
            n_any = max(n_any, len(pairs))
            b_arr = np.array([p[0] for p in pairs])
            v_arr = np.array([p[1] for p in pairs])
            md = v_arr.mean() - b_arr.mean()
            try:
                _, p = wilcoxon(v_arr, b_arr, zero_method="pratt", alternative="two-sided")
            except ValueError:
                p = 1.0
            star = "**" if p < 0.01 else ("*" if p < 0.05 else ("." if p < 0.10 else ""))
            sign = "+" if md >= 0 else ""
            row_cells.append(f"{sign}{md:.3f} {star}".strip())
        row_cells.insert(1, str(n_any))
        lines.append("| " + " | ".join(row_cells) + " |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="results/per_defect.md")
    args = ap.parse_args()

    lines = ["# Per-defect-type slicing of DesignBench grounding ablation", ""]
    lines.append("Each row pools samples by defect type across all 4 frameworks. ")
    lines.append("Multi-defect samples count once per defect. Bold = p<0.01, `*` = p<0.05, `.` = p<0.10. ")
    lines.append("MAE omitted (lower-better; see stats_test.py for raw). ")
    lines.append("All-zero cells (metric not rendered) dropped from pairing.")

    # OmniParser, both mode
    run_comparison(
        "OmniParser structural, both mode — 7B",
        "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni", "both", lines,
    )
    run_comparison(
        "OmniParser structural, both mode — 72B",
        "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni", "both", lines,
    )

    # JEDI, both mode
    run_comparison(
        "JEDI click-points, both mode — 7B",
        "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+jedi", "both", lines,
    )
    run_comparison(
        "JEDI click-points, both mode — 72B",
        "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+jedi", "both", lines,
    )

    # OmniParser on mark mode
    run_comparison(
        "OmniParser on mark mode — 7B",
        "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni", "mark", lines,
    )
    run_comparison(
        "OmniParser on mark mode — 72B",
        "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni", "mark", lines,
    )

    out_path = REPO / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    print()
    for line in lines[:80]:
        print(line)


if __name__ == "__main__":
    main()
