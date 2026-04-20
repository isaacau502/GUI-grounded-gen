"""Ranked, poster-ready significance report (alpha = 0.05).

Filters out noise and presents only p<0.05 results, sorted by effect magnitude.
Sourced from the eval JSONs in external/DesignBench/code/evaluator/res/DesignRepair/.

Outputs:
  - markdown table of significant gains (variant > baseline)
  - markdown table of significant regressions (variant < baseline)
  - marginal (0.05 <= p < 0.10) section noted separately

Usage: python scripts/poster_stats.py
"""

import json
import argparse
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon, binomtest

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "external" / "DesignBench" / "code" / "evaluator" / "res" / "DesignRepair"

FRAMEWORKS = ["react", "vue", "angular", "vanilla"]

METRICS = [
    # (key, label, direction: 'up'=higher better, 'down'=lower better)
    ("ast_code_op_score", "CMLS", "up"),
    ("ast_code_content_weighted_score", "CMCS", "up"),
    ("issue accuracy", "IssAcc", "up"),
    ("code_score", "CodeScore", "up"),
    ("clip_similarity", "CLIP", "up"),
    ("structure_similarity", "SSIM", "up"),
    ("MAE", "MAE", "down"),
]

COMPARISONS = [
    ("7B omni both", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni", "both"),
    ("72B omni both", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni", "both"),
    ("7B jedi both", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+jedi", "both"),
    ("72B jedi both", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+jedi", "both"),
    ("7B omni mark", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni", "mark"),
    ("72B omni mark", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni", "mark"),
]

ALPHA = 0.05


def paired(data, base, var, key):
    if base not in data or var not in data:
        return None, None
    b_d, v_d = data[base], data[var]
    common = sorted(set(b_d.keys()) & set(v_d.keys()), key=int)
    b = np.array([b_d[k].get(key, 0.0) for k in common], dtype=float)
    v = np.array([v_d[k].get(key, 0.0) for k in common], dtype=float)
    return b, v


def csr_paired(data, base, var):
    if base not in data or var not in data:
        return None, None, None
    common = sorted(set(data[base].keys()) & set(data[var].keys()), key=int)
    b = np.array([1 if data[base][k].get("compile_success") else 0 for k in common])
    v = np.array([1 if data[var][k].get("compile_success") else 0 for k in common])
    return b, v, common


def test_continuous(b, v):
    """Returns (mean_diff, p). For Wilcoxon paired."""
    try:
        _, p = wilcoxon(v, b, zero_method="pratt", alternative="two-sided")
    except ValueError:
        p = 1.0
    return float(v.mean() - b.mean()), float(p)


def test_csr(b, v):
    """McNemar-style exact binomial on discordant pairs."""
    b_only = int(((b == 1) & (v == 0)).sum())
    v_only = int(((b == 0) & (v == 1)).sum())
    disc = b_only + v_only
    if disc == 0:
        return float(v.mean() - b.mean()), 1.0, b_only, v_only
    res = binomtest(v_only, disc, 0.5, alternative="two-sided")
    return float(v.mean() - b.mean()), float(res.pvalue), b_only, v_only


def gather():
    """Return list of dicts for every (comparison × framework × metric) with stats."""
    rows = []
    for cmp_label, base, var, mode in COMPARISONS:
        for fw in FRAMEWORKS:
            p = RES / f"{fw}_{mode}.json"
            if not p.exists():
                continue
            data = json.loads(p.read_text())

            # Continuous metrics
            for key, mlabel, direction in METRICS:
                b, v = paired(data, base, var, key)
                if b is None or len(b) == 0:
                    continue
                # Skip all-zero cells (metric not rendered)
                if b.sum() == 0 and v.sum() == 0:
                    continue
                md, p_val = test_continuous(b, v)
                # Direction-aware "goodness": for down-is-better metrics, flip sign of goodness
                goodness = md if direction == "up" else -md
                rows.append({
                    "comparison": cmp_label,
                    "framework": fw,
                    "metric": mlabel,
                    "n": len(b),
                    "baseline": float(b.mean()),
                    "variant": float(v.mean()),
                    "delta": md,
                    "goodness": goodness,
                    "p": p_val,
                    "direction": direction,
                })

            # CSR (McNemar exact binomial)
            b, v, common = csr_paired(data, base, var)
            if b is None or len(b) == 0:
                continue
            # Skip if no variance (both all-1 or all-0)
            if len(set(b.tolist() + v.tolist())) < 2:
                continue
            md, p_val, b_only, v_only = test_csr(b, v)
            rows.append({
                "comparison": cmp_label,
                "framework": fw,
                "metric": "CSR",
                "n": len(b),
                "baseline": float(b.mean()),
                "variant": float(v.mean()),
                "delta": md,
                "goodness": md,
                "p": p_val,
                "direction": "up",
                "discordant": f"B_only={b_only} V_only={v_only}",
            })
    return rows


def fmt_val(v, metric):
    if metric == "MAE":
        return f"{v:+.3f}"
    if metric == "CSR":
        return f"{v:+.3f}"
    return f"{v:+.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=ALPHA)
    ap.add_argument("--output", default="poster/poster_stats.md")
    args = ap.parse_args()

    rows = gather()
    wins = [r for r in rows if r["p"] < args.alpha and r["goodness"] > 0]
    regr = [r for r in rows if r["p"] < args.alpha and r["goodness"] < 0]
    marginal = [r for r in rows if args.alpha <= r["p"] < 0.10]

    wins.sort(key=lambda r: r["p"])
    regr.sort(key=lambda r: r["p"])
    marginal.sort(key=lambda r: r["p"])

    lines = [
        f"# Poster-ready significance report (α = {args.alpha})",
        "",
        "Wilcoxon signed-rank paired, two-sided, for continuous metrics. ",
        "McNemar-style exact binomial on discordant pairs for CSR. ",
        f"Filter: p < {args.alpha}. Rows sorted by p-value ascending (lowest p first).",
        "",
        f"## Significant gains (N={len(wins)})",
        "",
        "| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(wins, 1):
        delta_str = fmt_val(r["delta"], r["metric"])
        p_str = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
        lines.append(
            f"| {i} | {r['comparison']} | {r['framework']} | {r['metric']} | "
            f"{r['n']} | {r['baseline']:.3f} | {r['variant']:.3f} | {delta_str} | {p_str} |"
        )

    lines += [
        "",
        f"## Significant regressions (N={len(regr)})",
        "",
        "| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(regr, 1):
        delta_str = fmt_val(r["delta"], r["metric"])
        p_str = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
        lines.append(
            f"| {i} | {r['comparison']} | {r['framework']} | {r['metric']} | "
            f"{r['n']} | {r['baseline']:.3f} | {r['variant']:.3f} | {delta_str} | {p_str} |"
        )

    lines += [
        "",
        f"## Marginal (0.05 ≤ p < 0.10) — for reference (N={len(marginal)})",
        "",
        "| Comparison | Framework | Metric | N | Δ | p | direction |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in marginal:
        delta_str = fmt_val(r["delta"], r["metric"])
        direction = "↑ (better)" if r["goodness"] > 0 else "↓ (worse)"
        lines.append(
            f"| {r['comparison']} | {r['framework']} | {r['metric']} | "
            f"{r['n']} | {delta_str} | {r['p']:.3f} | {direction} |"
        )

    out_path = REPO / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    print()
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
