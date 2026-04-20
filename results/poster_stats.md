# Poster-ready significance report (α = 0.05)

Wilcoxon signed-rank paired, two-sided, for continuous metrics. 
McNemar-style exact binomial on discordant pairs for CSR. 
Filter: p < 0.05. Rows sorted by p-value ascending (lowest p first).

## Significant gains (N=27)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |
|---|---|---|---|---|---|---|---|---|
| 1 | 72B jedi both | vue | SSIM | 27 | 0.807 | 0.819 | +0.012 | <0.001 |
| 2 | 7B jedi both | react | MAE | 28 | 97.965 | 45.373 | -52.592 | <0.001 |
| 3 | 7B jedi both | vue | IssAcc | 27 | 0.210 | 0.679 | +0.469 | <0.001 |
| 4 | 72B jedi both | react | IssAcc | 28 | 0.395 | 0.665 | +0.270 | <0.001 |
| 5 | 72B jedi both | vue | IssAcc | 27 | 0.213 | 0.654 | +0.441 | <0.001 |
| 6 | 72B jedi both | vanilla | IssAcc | 28 | 0.369 | 0.607 | +0.238 | 0.001 |
| 7 | 72B omni both | vue | CLIP | 27 | 0.796 | 0.808 | +0.012 | 0.002 |
| 8 | 7B omni both | angular | SSIM | 28 | 0.407 | 0.519 | +0.111 | 0.002 |
| 9 | 72B omni both | vanilla | CLIP | 28 | 0.791 | 0.809 | +0.018 | 0.002 |
| 10 | 72B omni both | vanilla | SSIM | 28 | 0.794 | 0.813 | +0.019 | 0.002 |
| 11 | 7B jedi both | vanilla | IssAcc | 28 | 0.345 | 0.655 | +0.310 | 0.003 |
| 12 | 72B jedi both | vanilla | CLIP | 28 | 0.791 | 0.804 | +0.013 | 0.003 |
| 13 | 72B jedi both | angular | IssAcc | 28 | 0.379 | 0.604 | +0.225 | 0.004 |
| 14 | 72B jedi both | angular | MAE | 28 | 88.076 | 85.034 | -3.043 | 0.005 |
| 15 | 7B omni both | vue | CLIP | 27 | 0.785 | 0.807 | +0.021 | 0.005 |
| 16 | 7B jedi both | angular | IssAcc | 28 | 0.173 | 0.429 | +0.256 | 0.005 |
| 17 | 7B omni both | angular | CLIP | 28 | 0.486 | 0.627 | +0.141 | 0.007 |
| 18 | 72B jedi both | react | MAE | 28 | 86.196 | 85.046 | -1.150 | 0.008 |
| 19 | 72B jedi both | vue | MAE | 27 | 82.327 | 82.076 | -0.251 | 0.008 |
| 20 | 72B jedi both | react | SSIM | 28 | 0.749 | 0.759 | +0.011 | 0.009 |
| 21 | 72B omni both | angular | SSIM | 28 | 0.691 | 0.694 | +0.003 | 0.026 |
| 22 | 72B omni both | vanilla | MAE | 28 | 80.226 | 79.889 | -0.337 | 0.030 |
| 23 | 72B jedi both | vanilla | SSIM | 28 | 0.794 | 0.820 | +0.026 | 0.032 |
| 24 | 72B jedi both | vue | CLIP | 27 | 0.796 | 0.811 | +0.015 | 0.041 |
| 25 | 7B jedi both | vue | CLIP | 27 | 0.785 | 0.798 | +0.012 | 0.044 |
| 26 | 72B omni both | angular | CLIP | 28 | 0.821 | 0.829 | +0.009 | 0.045 |
| 27 | 7B omni both | angular | CMCS | 28 | 0.206 | 0.279 | +0.073 | 0.048 |

## Significant regressions (N=12)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |
|---|---|---|---|---|---|---|---|---|
| 1 | 7B jedi both | react | CSR | 28 | 1.000 | 0.500 | -0.500 | <0.001 |
| 2 | 7B jedi both | react | CLIP | 28 | 0.632 | 0.322 | -0.309 | <0.001 |
| 3 | 7B jedi both | react | SSIM | 28 | 0.668 | 0.364 | -0.304 | <0.001 |
| 4 | 7B omni both | vue | SSIM | 27 | 0.799 | 0.783 | -0.016 | 0.004 |
| 5 | 72B jedi both | angular | CLIP | 28 | 0.821 | 0.808 | -0.013 | 0.005 |
| 6 | 7B jedi both | react | CMCS | 28 | 0.139 | 0.055 | -0.084 | 0.006 |
| 7 | 7B jedi both | react | CMLS | 28 | 0.182 | 0.085 | -0.096 | 0.006 |
| 8 | 72B jedi both | angular | SSIM | 28 | 0.691 | 0.665 | -0.026 | 0.020 |
| 9 | 7B jedi both | vue | SSIM | 27 | 0.799 | 0.756 | -0.043 | 0.025 |
| 10 | 7B jedi both | vue | MAE | 27 | 82.239 | 87.014 | +4.775 | 0.025 |
| 11 | 7B omni mark | vanilla | CMLS | 28 | 0.417 | 0.274 | -0.144 | 0.032 |
| 12 | 7B omni mark | vanilla | CMCS | 28 | 0.388 | 0.261 | -0.128 | 0.038 |

## Marginal (0.05 ≤ p < 0.10) — for reference (N=12)

| Comparison | Framework | Metric | N | Δ | p | direction |
|---|---|---|---|---|---|---|
| 72B omni mark | vue | CMCS | 27 | -0.027 | 0.052 | ↓ (worse) |
| 7B jedi both | angular | CLIP | 28 | +0.109 | 0.059 | ↑ (better) |
| 7B jedi both | react | CodeScore | 28 | -0.028 | 0.068 | ↓ (worse) |
| 7B omni both | angular | CMLS | 28 | +0.090 | 0.069 | ↑ (better) |
| 72B jedi both | vue | CodeScore | 27 | -0.016 | 0.069 | ↓ (worse) |
| 7B omni both | vue | CMCS | 27 | -0.043 | 0.072 | ↓ (worse) |
| 7B omni both | vue | IssAcc | 27 | +0.062 | 0.074 | ↑ (better) |
| 72B jedi both | angular | CodeScore | 28 | -0.003 | 0.077 | ↓ (worse) |
| 72B jedi both | vanilla | MAE | 28 | -0.378 | 0.077 | ↑ (better) |
| 7B omni both | vue | CMLS | 27 | -0.037 | 0.079 | ↓ (worse) |
| 7B omni mark | vue | CMCS | 27 | -0.042 | 0.086 | ↓ (worse) |
| 7B jedi both | angular | SSIM | 28 | +0.064 | 0.097 | ↑ (better) |
