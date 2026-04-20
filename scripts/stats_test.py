"""Paired significance tests: baseline vs +omni per (framework, metric).

Wilcoxon signed-rank (non-parametric, appropriate for bounded [0,1] metrics)
+ bootstrap 95% CI on mean paired difference.

Usage:
    python scripts/stats_test.py
"""

import json
import os
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "external" / "DesignBench" / "code" / "evaluator" / "res" / "DesignRepair"

METRICS = [
    ("ast_code_op_score", "CMLS"),
    ("ast_code_content_weighted_score", "CMCS"),
    ("issue accuracy", "IssAcc"),
    ("code_score", "CodeScore"),
    ("clip_similarity", "CLIP"),
    ("structure_similarity", "SSIM"),
    ("MAE", "MAE"),
]

FRAMEWORKS = ["react", "vue", "angular", "vanilla"]


def paired_samples(data, baseline, variant, metric_key):
    """Return paired arrays b, v for samples present in both."""
    b_d = data.get(baseline, {})
    v_d = data.get(variant, {})
    common = sorted(set(b_d.keys()) & set(v_d.keys()), key=int)
    b = np.array([b_d[k].get(metric_key, 0.0) for k in common], dtype=float)
    v = np.array([v_d[k].get(metric_key, 0.0) for k in common], dtype=float)
    return b, v, common


def bootstrap_mean_diff_ci(b, v, n_boot=5000, alpha=0.05):
    diff = v - b
    n = len(diff)
    rng = np.random.default_rng(42)
    boot = np.array([diff[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo = np.quantile(boot, alpha / 2)
    hi = np.quantile(boot, 1 - alpha / 2)
    return diff.mean(), lo, hi


def pretty_p(p):
    if p < 0.001: return "<0.001"
    if p < 0.01:  return f"{p:.3f}"
    return f"{p:.3f}"


def sig_star(p):
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "."
    return " "


def csr_test(data, baseline_key, variant_key):
    """McNemar-style test on per-sample compile_success (binary).

    Returns (base_csr, var_csr, n, b_not_v, v_not_b, two_sided_p)."""
    from scipy.stats import binomtest
    b_d = data.get(baseline_key, {})
    v_d = data.get(variant_key, {})
    common = sorted(set(b_d.keys()) & set(v_d.keys()), key=int)
    b = np.array([1 if b_d[k].get("compile_success") else 0 for k in common])
    v = np.array([1 if v_d[k].get("compile_success") else 0 for k in common])
    n = len(b)
    # Discordant pairs
    b_only = int(((b == 1) & (v == 0)).sum())  # baseline compiled, variant didn't
    v_only = int(((b == 0) & (v == 1)).sum())  # variant compiled, baseline didn't
    discordant = b_only + v_only
    if discordant == 0:
        return b.mean(), v.mean(), n, b_only, v_only, 1.0
    # Exact binomial test on v_only out of discordant (null p=0.5)
    res = binomtest(v_only, discordant, 0.5, alternative="two-sided")
    return b.mean(), v.mean(), n, b_only, v_only, res.pvalue


def run(label, baseline_key, variant_key):
    print(f"\n=== {label}: {baseline_key} vs {variant_key} ===")
    print(f"{'fw':9s} {'metric':10s} {'N':>3s} {'base':>7s} {'+omni':>7s} "
          f"{'mean_d':>8s} {'95%CI':>18s} {'W_p':>8s} {'sig':>4s}")
    for fw in FRAMEWORKS:
        p = RES / f"{fw}_both.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        for mkey, mlabel in METRICS:
            b, v, keys = paired_samples(data, baseline_key, variant_key, mkey)
            if len(b) == 0:
                continue
            # Skip if all values are 0 (metric not computed, e.g. no render)
            if b.sum() == 0 and v.sum() == 0:
                continue
            mean_b, mean_v = b.mean(), v.mean()
            md, lo, hi = bootstrap_mean_diff_ci(b, v)
            try:
                stat, pval = wilcoxon(v, b, zero_method="pratt", alternative="two-sided")
            except ValueError:
                pval = 1.0
            print(f"{fw:9s} {mlabel:10s} {len(b):>3d} "
                  f"{mean_b:>7.3f} {mean_v:>7.3f} "
                  f"{md:>+8.3f} [{lo:>+.3f},{hi:>+.3f}] "
                  f"{pretty_p(pval):>8s} {sig_star(pval):>4s}")

        # CSR via McNemar-style exact binomial on discordant pairs
        try:
            base_csr, var_csr, n, bo, vo, pval = csr_test(data, baseline_key, variant_key)
            print(f"{fw:9s} {'CSR':10s} {n:>3d} "
                  f"{base_csr:>7.3f} {var_csr:>7.3f} "
                  f"{var_csr-base_csr:>+8.3f} "
                  f"  [B_only={bo}, V_only={vo}] "
                  f"{pretty_p(pval):>8s} {sig_star(pval):>4s}")
        except Exception as e:
            print(f"{fw:9s} CSR test failed: {e}")


def main():
    # 7B: does grounding help?
    run("7B", "qwen2.5-vl-7b-instruct", "qwen2.5-vl-7b-instruct+omni")
    # 72B: does grounding hurt?
    run("72B", "qwen2.5-vl-72b-instruct", "qwen2.5-vl-72b-instruct+omni")
    print("\nLegend: sig = ** p<0.01, * p<0.05, . p<0.10")
    print("Wilcoxon signed-rank (two-sided), 95% CI from paired-diff bootstrap (5000 reps).")


if __name__ == "__main__":
    main()
