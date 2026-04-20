# Per-defect-type slicing of DesignBench grounding ablation

Each row pools samples by defect type across all 4 frameworks. 
Multi-defect samples count once per defect. Bold = p<0.01, `*` = p<0.05, `.` = p<0.10. 
MAE omitted (lower-better; see stats_test.py for raw). 
All-zero cells (metric not rendered) dropped from pairing.

## OmniParser structural, both mode — 7B

**qwen2.5-vl-7b-instruct** vs **qwen2.5-vl-7b-instruct+omni** (mode=both)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 63 | -0.010 | -0.013 | +0.059 . | +0.019 | +0.065 ** | +0.039 ** |
| crowding | 30 | -0.001 | -0.010 | +0.196 ** | +0.078 * | +0.020 | -0.007 |
| occlusion | 29 | +0.013 | +0.002 | +0.002 | +0.078 | +0.095 * | +0.082 * |
| overflow | 17 | +0.020 | +0.002 | +0.250 . | -0.018 | +0.157 . | +0.106 ** |
| color and contrast | 11 | +0.088 | +0.098 | +0.125 | +0.119 | +0.089 | -0.037 |
| text overlap | 3 | +0.025 | +0.017 | -0.100 | +0.032 | +0.102 | +0.051 |
| disorder | 8 | -0.052 | -0.024 | -0.077 | +0.006 | +0.056 | +0.060 |

## OmniParser structural, both mode — 72B

**qwen2.5-vl-72b-instruct** vs **qwen2.5-vl-72b-instruct+omni** (mode=both)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 68 | -0.055 * | -0.045 * | -0.019 | -0.031 | +0.007 ** | -0.014 |
| crowding | 31 | -0.043 | -0.044 | -0.016 | +0.025 | +0.035 ** | +0.037 |
| occlusion | 30 | -0.037 | -0.036 | -0.039 | +0.016 | +0.011 * | -0.024 |
| overflow | 19 | -0.009 | -0.010 | +0.042 | -0.005 | +0.064 ** | +0.047 |
| color and contrast | 11 | -0.025 | -0.019 | -0.003 | +0.003 | +0.013 | +0.059 * |
| text overlap | 3 | -0.103 | -0.079 | -0.011 | +0.038 | +0.012 | -0.019 |
| disorder | 8 | -0.022 | -0.018 | -0.047 | +0.011 | +0.014 | -0.010 |

## JEDI click-points, both mode — 7B

**qwen2.5-vl-7b-instruct** vs **qwen2.5-vl-7b-instruct+jedi** (mode=both)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 65 | +0.015 | +0.028 | +0.083 | +0.063 | -0.055 | -0.089 |
| crowding | 29 | +0.057 | +0.072 | +0.512 ** | +0.036 | -0.046 | -0.107 |
| occlusion | 28 | +0.062 | +0.055 | +0.402 ** | +0.102 | -0.016 | -0.031 |
| overflow | 16 | +0.088 | +0.089 | +0.556 ** | +0.012 | +0.038 | -0.080 |
| color and contrast | 11 | -0.156 | -0.129 | +0.452 | +0.090 | -0.039 | -0.056 |
| text overlap | 3 | -0.008 | -0.006 | -0.333 | -0.036 | -0.344 | -0.485 |
| disorder | 8 | -0.114 | -0.071 | +0.028 | -0.010 | -0.116 | -0.180 |

## JEDI click-points, both mode — 72B

**qwen2.5-vl-72b-instruct** vs **qwen2.5-vl-72b-instruct+jedi** (mode=both)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 67 | -0.003 | +0.005 | +0.230 ** | +0.006 | +0.001 ** | -0.002 ** |
| crowding | 30 | -0.045 | -0.034 | +0.633 ** | -0.004 | +0.005 | +0.026 ** |
| occlusion | 30 | +0.027 | +0.026 | +0.335 ** | -0.002 | +0.012 * | +0.008 * |
| overflow | 18 | +0.018 | +0.037 | +0.571 ** | +0.049 | +0.003 | -0.006 |
| color and contrast | 11 | -0.028 | -0.024 | +0.277 . | +0.036 | +0.025 * | +0.042 ** |
| text overlap | 3 | -0.006 | +0.003 | +0.139 | +0.011 | +0.032 | -0.004 |
| disorder | 8 | -0.002 | +0.001 | +0.217 | -0.005 | +0.004 | -0.001 |

## OmniParser on mark mode — 7B

**qwen2.5-vl-7b-instruct** vs **qwen2.5-vl-7b-instruct+omni** (mode=mark)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 67 | +0.010 | -0.000 | +0.128 . | -0.011 | — | — |
| crowding | 30 | -0.047 | -0.052 | +0.108 | -0.042 | — | — |
| occlusion | 29 | +0.060 | +0.044 | -0.125 | +0.038 | — | — |
| overflow | 19 | +0.000 | +0.003 | +0.115 | -0.062 | — | — |
| color and contrast | 11 | -0.028 | -0.069 | -0.133 | -0.023 | — | — |
| text overlap | 3 | +0.002 | +0.002 | -0.267 | +0.012 | — | — |
| disorder | 8 | -0.028 | -0.025 | -0.179 | -0.088 | — | — |

## OmniParser on mark mode — 72B

**qwen2.5-vl-72b-instruct** vs **qwen2.5-vl-72b-instruct+omni** (mode=mark)

| defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|---|---|---|---|---|---|---|---|
| alignment | 68 | -0.008 | -0.006 | +0.013 | -0.000 | — | — |
| crowding | 31 | -0.052 | -0.040 * | +0.004 | -0.011 | — | — |
| occlusion | 30 | -0.018 | -0.022 | +0.030 | +0.032 | — | — |
| overflow | 19 | -0.020 | -0.035 | -0.042 | -0.031 | — | — |
| color and contrast | 11 | +0.016 | -0.017 | -0.030 | -0.072 | — | — |
| text overlap | 3 | -0.001 | +0.005 | +0.178 | +0.044 | — | — |
| disorder | 8 | +0.024 | +0.012 | +0.075 | +0.029 | — | — |
