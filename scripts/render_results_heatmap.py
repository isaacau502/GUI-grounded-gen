"""Render the pooled results table as a color-coded heatmap PNG.

Rows: 4 grounding variants. Cols: 5 metrics. Cell color conveys gain/regression
and significance magnitude. No legend needed — green dominates if grounding
helps, red cells pop out as regressions.

Output: poster/results_heatmap.png
"""

from pathlib import Path
import json
import numpy as np
from scipy.stats import wilcoxon, binomtest
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "external/DesignBench/code/evaluator/res/DesignRepair"
FW = ["react", "vue", "angular", "vanilla"]

# (metric_key, display_name, positive_is_good)
METRICS = [
    ("ast_code_op_score", "CMLS", True),
    ("clip_similarity", "CLIP", True),
    ("structure_similarity", "SSIM", True),
    ("issue accuracy", "IssAcc", True),
    ("__csr__", "CSR", True),  # special-cased
]

VARIANTS = [
    ("7B + omni", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni"),
    ("72B + omni", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni"),
    ("72B + jedi", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+jedi"),
    ("7B + jedi", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+jedi"),
]


def pool_metric(base_key, var_key, metric):
    """Return (baseline mean, variant mean, delta, p-value, N)."""
    b_vals, v_vals = [], []
    for fw in FW:
        p = EVAL / f"{fw}_both.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        if base_key not in d or var_key not in d:
            continue
        bd, vd = d[base_key], d[var_key]
        for s in sorted(set(bd.keys()) & set(vd.keys()), key=int):
            if metric == "__csr__":
                b_vals.append(1 if bd[s].get("compile_success") else 0)
                v_vals.append(1 if vd[s].get("compile_success") else 0)
            else:
                b_vals.append(bd[s].get(metric, 0.0))
                v_vals.append(vd[s].get(metric, 0.0))
    b = np.array(b_vals, dtype=float)
    v = np.array(v_vals, dtype=float)
    if len(b) == 0:
        return None
    if metric == "__csr__":
        b_int = b.astype(int)
        v_int = v.astype(int)
        bo = int(((b_int == 1) & (v_int == 0)).sum())
        vo = int(((b_int == 0) & (v_int == 1)).sum())
        disc = bo + vo
        pval = 1.0 if disc == 0 else binomtest(vo, disc, 0.5, alternative="two-sided").pvalue
    else:
        # drop both-zero
        mask = ~((b == 0) & (v == 0))
        b, v = b[mask], v[mask]
        if len(b) == 0:
            return None
        try:
            _, pval = wilcoxon(v, b, zero_method="pratt", alternative="two-sided")
        except ValueError:
            pval = 1.0
    return b.mean(), v.mean(), v.mean() - b.mean(), pval, len(b)


def cell_color(delta, pval, positive_good):
    """Return RGB. Green = gain, red = regression, gray = ns.

    Saturation scaled by significance (p<.01 saturated, p<.05 medium, else desaturated).
    Hue: green if (positive_good XOR delta<0) is False, else red.
    """
    goodness = delta if positive_good else -delta
    if pval >= 0.10:
        # not significant — gray
        return (0.92, 0.92, 0.92)
    # intensity by significance
    if pval < 0.01:
        sat = 0.55
    elif pval < 0.05:
        sat = 0.35
    else:  # 0.05 - 0.10
        sat = 0.20
    if goodness > 0:
        # green
        return (1 - sat, 1 - sat * 0.3, 1 - sat)
    else:
        return (1 - sat * 0.3, 1 - sat, 1 - sat)


def sig_marker(pval):
    if pval < 0.01: return "**"
    if pval < 0.05: return "*"
    if pval < 0.10: return "."
    return ""


def main():
    n_rows = len(VARIANTS)
    n_cols = len(METRICS)
    cell_w, cell_h = 1.6, 0.9

    fig_w = cell_w * n_cols + 2.2  # extra for row labels
    fig_h = cell_h * n_rows + 0.8  # extra for col labels

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=220)
    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.invert_yaxis()
    ax.set_aspect("auto")
    ax.axis("off")

    # col headers
    for ci, (_, name, _) in enumerate(METRICS):
        ax.text(ci + 0.5, -0.35, name, ha="center", va="center",
                fontsize=16, fontweight="bold")

    # row labels + cells
    for ri, (label, base_key, var_key) in enumerate(VARIANTS):
        ax.text(-0.15, ri + 0.5, label, ha="right", va="center",
                fontsize=14, fontweight="bold")
        for ci, (mkey, mname, pos_good) in enumerate(METRICS):
            res = pool_metric(base_key, var_key, mkey)
            if res is None:
                ax.add_patch(plt.Rectangle((ci, ri), 1, 1,
                                           facecolor=(0.96, 0.96, 0.96),
                                           edgecolor="white", linewidth=2))
                continue
            b_mean, v_mean, delta, pval, n = res
            color = cell_color(delta, pval, pos_good)
            ax.add_patch(plt.Rectangle((ci, ri), 1, 1,
                                       facecolor=color,
                                       edgecolor="white", linewidth=2))
            # delta text inside cell
            sign = "+" if delta >= 0 else "\u2212"
            dtxt = f"{sign}{abs(delta):.3f}"
            marker = sig_marker(pval)
            txt_color = "black" if (color[0] + color[1] + color[2]) / 3 > 0.65 else "white"
            ax.text(ci + 0.5, ri + 0.5, f"{dtxt}{marker}",
                    ha="center", va="center",
                    fontsize=13, fontweight="bold", color=txt_color)

    # subtle gridlines
    for ci in range(n_cols + 1):
        ax.plot([ci, ci], [0, n_rows], color="white", linewidth=2)
    for ri in range(n_rows + 1):
        ax.plot([0, n_cols], [ri, ri], color="white", linewidth=2)

    # title / sub
    plt.figtext(0.5, 1.0, "Grounding effect on DesignBench repair · Pooled N=111",
                ha="center", fontsize=13, fontweight="bold")

    plt.subplots_adjust(left=0.20, right=0.98, top=0.90, bottom=0.04)

    out = REPO / "poster" / "results_heatmap.png"
    fig.savefig(out, bbox_inches="tight", dpi=220)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
