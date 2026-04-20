# Complete significance report — all results (α = 0.05)

Wilcoxon signed-rank paired, two-sided, for continuous metrics. 
McNemar-style exact binomial on discordant pairs for CSR. 
**Every cell from the ablation panel is reported**, grouped by significance level. Use this as the one-stop source for bar-chart/heatmap data including non-significant cells.

Total cells: 149. Significant gains: 27. Significant regressions: 12. Marginal (0.05 ≤ p < 0.10): 12. Not significant (p ≥ 0.10): 98.

Sig marker legend: `**` p<0.01, `*` p<0.05, `.` p<0.10.

## Significant gains (N=27)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p | sig |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 72B jedi both | vue | SSIM | 27 | 0.807 | 0.819 | +0.012 | <0.001 | ** |
| 2 | 7B jedi both | react | MAE | 28 | 97.965 | 45.373 | -52.592 | <0.001 | ** |
| 3 | 7B jedi both | vue | IssAcc | 27 | 0.210 | 0.679 | +0.469 | <0.001 | ** |
| 4 | 72B jedi both | react | IssAcc | 28 | 0.395 | 0.665 | +0.270 | <0.001 | ** |
| 5 | 72B jedi both | vue | IssAcc | 27 | 0.213 | 0.654 | +0.441 | <0.001 | ** |
| 6 | 72B jedi both | vanilla | IssAcc | 28 | 0.369 | 0.607 | +0.238 | 0.001 | ** |
| 7 | 72B omni both | vue | CLIP | 27 | 0.796 | 0.808 | +0.012 | 0.002 | ** |
| 8 | 7B omni both | angular | SSIM | 28 | 0.407 | 0.519 | +0.111 | 0.002 | ** |
| 9 | 72B omni both | vanilla | CLIP | 28 | 0.791 | 0.809 | +0.018 | 0.002 | ** |
| 10 | 72B omni both | vanilla | SSIM | 28 | 0.794 | 0.813 | +0.019 | 0.002 | ** |
| 11 | 7B jedi both | vanilla | IssAcc | 28 | 0.345 | 0.655 | +0.310 | 0.003 | ** |
| 12 | 72B jedi both | vanilla | CLIP | 28 | 0.791 | 0.804 | +0.013 | 0.003 | ** |
| 13 | 72B jedi both | angular | IssAcc | 28 | 0.379 | 0.604 | +0.225 | 0.004 | ** |
| 14 | 72B jedi both | angular | MAE | 28 | 88.076 | 85.034 | -3.043 | 0.005 | ** |
| 15 | 7B omni both | vue | CLIP | 27 | 0.785 | 0.807 | +0.021 | 0.005 | ** |
| 16 | 7B jedi both | angular | IssAcc | 28 | 0.173 | 0.429 | +0.256 | 0.005 | ** |
| 17 | 7B omni both | angular | CLIP | 28 | 0.486 | 0.627 | +0.141 | 0.007 | ** |
| 18 | 72B jedi both | react | MAE | 28 | 86.196 | 85.046 | -1.150 | 0.008 | ** |
| 19 | 72B jedi both | vue | MAE | 27 | 82.327 | 82.076 | -0.251 | 0.008 | ** |
| 20 | 72B jedi both | react | SSIM | 28 | 0.749 | 0.759 | +0.011 | 0.009 | ** |
| 21 | 72B omni both | angular | SSIM | 28 | 0.691 | 0.694 | +0.003 | 0.026 | * |
| 22 | 72B omni both | vanilla | MAE | 28 | 80.226 | 79.889 | -0.337 | 0.030 | * |
| 23 | 72B jedi both | vanilla | SSIM | 28 | 0.794 | 0.820 | +0.026 | 0.032 | * |
| 24 | 72B jedi both | vue | CLIP | 27 | 0.796 | 0.811 | +0.015 | 0.041 | * |
| 25 | 7B jedi both | vue | CLIP | 27 | 0.785 | 0.798 | +0.012 | 0.044 | * |
| 26 | 72B omni both | angular | CLIP | 28 | 0.821 | 0.829 | +0.009 | 0.045 | * |
| 27 | 7B omni both | angular | CMCS | 28 | 0.206 | 0.279 | +0.073 | 0.048 | * |

## Significant regressions (N=12)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p | sig |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 7B jedi both | react | CSR | 28 | 1.000 | 0.500 | -0.500 | <0.001 | ** |
| 2 | 7B jedi both | react | CLIP | 28 | 0.632 | 0.322 | -0.309 | <0.001 | ** |
| 3 | 7B jedi both | react | SSIM | 28 | 0.668 | 0.364 | -0.304 | <0.001 | ** |
| 4 | 7B omni both | vue | SSIM | 27 | 0.799 | 0.783 | -0.016 | 0.004 | ** |
| 5 | 72B jedi both | angular | CLIP | 28 | 0.821 | 0.808 | -0.013 | 0.005 | ** |
| 6 | 7B jedi both | react | CMCS | 28 | 0.139 | 0.055 | -0.084 | 0.006 | ** |
| 7 | 7B jedi both | react | CMLS | 28 | 0.182 | 0.085 | -0.096 | 0.006 | ** |
| 8 | 72B jedi both | angular | SSIM | 28 | 0.691 | 0.665 | -0.026 | 0.020 | * |
| 9 | 7B jedi both | vue | SSIM | 27 | 0.799 | 0.756 | -0.043 | 0.025 | * |
| 10 | 7B jedi both | vue | MAE | 27 | 82.239 | 87.014 | +4.775 | 0.025 | * |
| 11 | 7B omni mark | vanilla | CMLS | 28 | 0.417 | 0.274 | -0.144 | 0.032 | * |
| 12 | 7B omni mark | vanilla | CMCS | 28 | 0.388 | 0.261 | -0.128 | 0.038 | * |

## Marginal (0.05 ≤ p < 0.10, N=12)

| Comparison | Framework | Metric | N | Baseline | Variant | Δ | p | direction |
|---|---|---|---|---|---|---|---|---|
| 72B omni mark | vue | CMCS | 27 | 0.162 | 0.135 | -0.027 | 0.052 | ↓ (worse) |
| 7B jedi both | angular | CLIP | 28 | 0.486 | 0.595 | +0.109 | 0.059 | ↑ (better) |
| 7B jedi both | react | CodeScore | 28 | 0.046 | 0.018 | -0.028 | 0.068 | ↓ (worse) |
| 7B omni both | angular | CMLS | 28 | 0.304 | 0.394 | +0.090 | 0.069 | ↑ (better) |
| 72B jedi both | vue | CodeScore | 27 | 0.107 | 0.091 | -0.016 | 0.069 | ↓ (worse) |
| 7B omni both | vue | CMCS | 27 | 0.179 | 0.136 | -0.043 | 0.072 | ↓ (worse) |
| 7B omni both | vue | IssAcc | 27 | 0.210 | 0.272 | +0.062 | 0.074 | ↑ (better) |
| 72B jedi both | angular | CodeScore | 28 | 0.564 | 0.561 | -0.003 | 0.077 | ↓ (worse) |
| 72B jedi both | vanilla | MAE | 28 | 80.226 | 79.848 | -0.378 | 0.077 | ↑ (better) |
| 7B omni both | vue | CMLS | 27 | 0.237 | 0.200 | -0.037 | 0.079 | ↓ (worse) |
| 7B omni mark | vue | CMCS | 27 | 0.177 | 0.135 | -0.042 | 0.086 | ↓ (worse) |
| 7B jedi both | angular | SSIM | 28 | 0.407 | 0.472 | +0.064 | 0.097 | ↑ (better) |

## Not significant (p ≥ 0.10, N=98)

Included for completeness — every remaining cell from the ablation panel. Direction column shows whether the effect trended in the variant's favor, but none of these cross α=0.10.

| Comparison | Framework | Metric | N | Baseline | Variant | Δ | p | direction |
|---|---|---|---|---|---|---|---|---|
| 72B jedi both | angular | CMCS | 28 | 0.556 | 0.547 | -0.009 | 0.925 | ↓ |
| 72B jedi both | angular | CMLS | 28 | 0.631 | 0.619 | -0.011 | 0.723 | ↓ |
| 72B jedi both | angular | CSR | 28 | 0.964 | 0.929 | -0.036 | 1.000 | ↓ |
| 72B jedi both | react | CLIP | 28 | 0.771 | 0.771 | -0.000 | 0.479 | ↓ |
| 72B jedi both | react | CMCS | 28 | 0.230 | 0.246 | +0.015 | 0.817 | ↑ |
| 72B jedi both | react | CMLS | 28 | 0.339 | 0.346 | +0.007 | 0.905 | ↑ |
| 72B jedi both | react | CodeScore | 28 | 0.155 | 0.218 | +0.063 | 0.381 | ↑ |
| 72B jedi both | vanilla | CMCS | 28 | 0.510 | 0.503 | -0.007 | 0.431 | ↓ |
| 72B jedi both | vanilla | CMLS | 28 | 0.532 | 0.524 | -0.009 | 0.168 | ↓ |
| 72B jedi both | vanilla | CodeScore | 28 | 0.113 | 0.111 | -0.002 | 0.295 | ↓ |
| 72B jedi both | vue | CMCS | 27 | 0.143 | 0.141 | -0.002 | 0.294 | ↓ |
| 72B jedi both | vue | CMLS | 27 | 0.213 | 0.207 | -0.006 | 0.146 | ↓ |
| 72B omni both | angular | CMCS | 28 | 0.556 | 0.491 | -0.065 | 0.140 | ↓ |
| 72B omni both | angular | CMLS | 28 | 0.631 | 0.580 | -0.051 | 0.223 | ↓ |
| 72B omni both | angular | CSR | 28 | 0.964 | 0.964 | +0.000 | 1.000 | — |
| 72B omni both | angular | CodeScore | 28 | 0.564 | 0.555 | -0.009 | 0.773 | ↓ |
| 72B omni both | angular | IssAcc | 28 | 0.379 | 0.357 | -0.022 | 0.499 | ↓ |
| 72B omni both | angular | MAE | 28 | 88.076 | 87.689 | -0.387 | 0.157 | ↑ |
| 72B omni both | react | CLIP | 28 | 0.771 | 0.777 | +0.006 | 0.582 | ↑ |
| 72B omni both | react | CMCS | 28 | 0.230 | 0.221 | -0.009 | 0.681 | ↓ |
| 72B omni both | react | CMLS | 28 | 0.339 | 0.317 | -0.021 | 0.430 | ↓ |
| 72B omni both | react | CodeScore | 28 | 0.155 | 0.174 | +0.019 | 0.560 | ↑ |
| 72B omni both | react | IssAcc | 28 | 0.395 | 0.388 | -0.007 | 0.668 | ↓ |
| 72B omni both | react | MAE | 28 | 86.196 | 86.088 | -0.108 | 0.178 | ↑ |
| 72B omni both | react | SSIM | 28 | 0.749 | 0.735 | -0.013 | 0.109 | ↓ |
| 72B omni both | vanilla | CMCS | 28 | 0.510 | 0.429 | -0.081 | 0.136 | ↓ |
| 72B omni both | vanilla | CMLS | 28 | 0.532 | 0.444 | -0.088 | 0.149 | ↓ |
| 72B omni both | vanilla | CodeScore | 28 | 0.113 | 0.118 | +0.005 | 0.616 | ↑ |
| 72B omni both | vanilla | IssAcc | 28 | 0.369 | 0.339 | -0.030 | 0.157 | ↓ |
| 72B omni both | vue | CMCS | 27 | 0.143 | 0.137 | -0.006 | 0.394 | ↓ |
| 72B omni both | vue | CMLS | 27 | 0.213 | 0.202 | -0.011 | 0.734 | ↓ |
| 72B omni both | vue | CodeScore | 27 | 0.107 | 0.093 | -0.014 | 0.283 | ↓ |
| 72B omni both | vue | IssAcc | 27 | 0.213 | 0.225 | +0.012 | 0.198 | ↑ |
| 72B omni both | vue | MAE | 27 | 82.327 | 83.524 | +1.197 | 0.361 | ↓ |
| 72B omni both | vue | SSIM | 27 | 0.807 | 0.785 | -0.022 | 0.530 | ↓ |
| 72B omni mark | angular | CMCS | 28 | 0.547 | 0.530 | -0.017 | 0.832 | ↓ |
| 72B omni mark | angular | CMLS | 28 | 0.624 | 0.622 | -0.002 | 0.823 | ↓ |
| 72B omni mark | angular | CodeScore | 28 | 0.579 | 0.591 | +0.013 | 0.437 | ↑ |
| 72B omni mark | angular | IssAcc | 28 | 0.406 | 0.410 | +0.004 | 0.979 | ↑ |
| 72B omni mark | react | CMCS | 28 | 0.209 | 0.218 | +0.009 | 0.872 | ↑ |
| 72B omni mark | react | CMLS | 28 | 0.306 | 0.318 | +0.012 | 0.556 | ↑ |
| 72B omni mark | react | CodeScore | 28 | 0.159 | 0.178 | +0.019 | 0.917 | ↑ |
| 72B omni mark | react | IssAcc | 28 | 0.400 | 0.392 | -0.008 | 0.975 | ↓ |
| 72B omni mark | vanilla | CMCS | 28 | 0.553 | 0.513 | -0.040 | 0.179 | ↓ |
| 72B omni mark | vanilla | CMLS | 28 | 0.571 | 0.535 | -0.036 | 0.317 | ↓ |
| 72B omni mark | vanilla | CodeScore | 28 | 0.169 | 0.114 | -0.055 | 0.651 | ↓ |
| 72B omni mark | vanilla | IssAcc | 28 | 0.318 | 0.363 | +0.045 | 0.114 | ↑ |
| 72B omni mark | vue | CMLS | 27 | 0.228 | 0.201 | -0.027 | 0.220 | ↓ |
| 72B omni mark | vue | CodeScore | 27 | 0.123 | 0.124 | +0.001 | 0.941 | ↑ |
| 72B omni mark | vue | IssAcc | 27 | 0.352 | 0.315 | -0.037 | 0.192 | ↓ |
| 7B jedi both | angular | CMCS | 28 | 0.206 | 0.289 | +0.083 | 0.154 | ↑ |
| 7B jedi both | angular | CMLS | 28 | 0.304 | 0.378 | +0.074 | 0.173 | ↑ |
| 7B jedi both | angular | CSR | 28 | 0.571 | 0.679 | +0.107 | 0.508 | ↑ |
| 7B jedi both | angular | CodeScore | 28 | 0.230 | 0.317 | +0.088 | 0.292 | ↑ |
| 7B jedi both | angular | MAE | 28 | 54.364 | 65.498 | +11.133 | 0.429 | ↓ |
| 7B jedi both | react | IssAcc | 28 | 0.345 | 0.238 | -0.107 | 0.181 | ↓ |
| 7B jedi both | vanilla | CLIP | 28 | 0.796 | 0.796 | -0.000 | 0.186 | ↓ |
| 7B jedi both | vanilla | CMCS | 28 | 0.394 | 0.412 | +0.018 | 0.599 | ↑ |
| 7B jedi both | vanilla | CMLS | 28 | 0.422 | 0.440 | +0.018 | 0.486 | ↑ |
| 7B jedi both | vanilla | CodeScore | 28 | 0.056 | 0.056 | -0.000 | 0.332 | ↓ |
| 7B jedi both | vanilla | MAE | 28 | 80.096 | 82.845 | +2.749 | 0.614 | ↓ |
| 7B jedi both | vanilla | SSIM | 28 | 0.823 | 0.801 | -0.022 | 0.973 | ↓ |
| 7B jedi both | vue | CMCS | 27 | 0.179 | 0.231 | +0.052 | 0.307 | ↑ |
| 7B jedi both | vue | CMLS | 27 | 0.237 | 0.285 | +0.048 | 0.749 | ↑ |
| 7B jedi both | vue | CodeScore | 27 | 0.140 | 0.149 | +0.009 | 0.878 | ↑ |
| 7B omni both | angular | CSR | 28 | 0.571 | 0.750 | +0.179 | 0.125 | ↑ |
| 7B omni both | angular | CodeScore | 28 | 0.230 | 0.284 | +0.054 | 0.603 | ↑ |
| 7B omni both | angular | IssAcc | 28 | 0.173 | 0.244 | +0.071 | 0.195 | ↑ |
| 7B omni both | angular | MAE | 28 | 54.364 | 70.550 | +16.186 | 0.122 | ↓ |
| 7B omni both | react | CLIP | 28 | 0.632 | 0.654 | +0.022 | 0.522 | ↑ |
| 7B omni both | react | CMCS | 28 | 0.139 | 0.117 | -0.022 | 0.991 | ↓ |
| 7B omni both | react | CMLS | 28 | 0.182 | 0.156 | -0.026 | 0.719 | ↓ |
| 7B omni both | react | CodeScore | 28 | 0.046 | 0.054 | +0.008 | 0.476 | ↑ |
| 7B omni both | react | IssAcc | 28 | 0.345 | 0.385 | +0.040 | 0.673 | ↑ |
| 7B omni both | react | MAE | 28 | 97.965 | 97.541 | -0.424 | 0.567 | ↑ |
| 7B omni both | react | SSIM | 28 | 0.668 | 0.673 | +0.006 | 0.598 | ↑ |
| 7B omni both | vanilla | CLIP | 28 | 0.796 | 0.796 | -0.000 | 0.614 | ↓ |
| 7B omni both | vanilla | CMCS | 28 | 0.394 | 0.402 | +0.008 | 0.972 | ↑ |
| 7B omni both | vanilla | CMLS | 28 | 0.422 | 0.431 | +0.009 | 0.879 | ↑ |
| 7B omni both | vanilla | CodeScore | 28 | 0.056 | 0.076 | +0.020 | 0.215 | ↑ |
| 7B omni both | vanilla | IssAcc | 28 | 0.345 | 0.399 | +0.054 | 0.186 | ↑ |
| 7B omni both | vanilla | MAE | 28 | 80.096 | 80.825 | +0.729 | 0.537 | ↓ |
| 7B omni both | vanilla | SSIM | 28 | 0.823 | 0.802 | -0.022 | 0.479 | ↓ |
| 7B omni both | vue | CodeScore | 27 | 0.140 | 0.115 | -0.025 | 0.466 | ↓ |
| 7B omni both | vue | MAE | 27 | 82.239 | 84.188 | +1.948 | 0.106 | ↓ |
| 7B omni mark | angular | CMCS | 28 | 0.200 | 0.221 | +0.020 | 0.964 | ↑ |
| 7B omni mark | angular | CMLS | 28 | 0.312 | 0.338 | +0.026 | 0.900 | ↑ |
| 7B omni mark | angular | CodeScore | 28 | 0.427 | 0.397 | -0.030 | 0.356 | ↓ |
| 7B omni mark | angular | IssAcc | 28 | 0.232 | 0.351 | +0.119 | 0.125 | ↑ |
| 7B omni mark | react | CMCS | 28 | 0.088 | 0.114 | +0.026 | 0.523 | ↑ |
| 7B omni mark | react | CMLS | 28 | 0.122 | 0.157 | +0.035 | 0.476 | ↑ |
| 7B omni mark | react | CodeScore | 28 | 0.069 | 0.076 | +0.007 | 0.573 | ↑ |
| 7B omni mark | react | IssAcc | 28 | 0.364 | 0.422 | +0.058 | 0.469 | ↑ |
| 7B omni mark | vanilla | CodeScore | 28 | 0.069 | 0.041 | -0.028 | 0.173 | ↓ |
| 7B omni mark | vanilla | IssAcc | 28 | 0.304 | 0.238 | -0.065 | 0.333 | ↓ |
| 7B omni mark | vue | CMLS | 27 | 0.226 | 0.208 | -0.018 | 0.406 | ↓ |
| 7B omni mark | vue | CodeScore | 27 | 0.083 | 0.078 | -0.005 | 0.907 | ↓ |
| 7B omni mark | vue | IssAcc | 27 | 0.241 | 0.364 | +0.123 | 0.193 | ↑ |
