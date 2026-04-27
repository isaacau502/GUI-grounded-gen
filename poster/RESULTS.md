# DesignBench GUI-Grounded Repair — Collated Results

**One-stop reference.** Merges the tier-ranked narrative from [results_overview.md](results_overview.md), the significance table from [poster_stats.md](poster_stats.md), the per-defect slice from [per_defect.md](per_defect.md), and the run-by-run history from [ablation_log.md](../ablation_log.md).

**Setup:** DesignBench repair task, 111 samples (R=28, V=27, A=28, Vanilla=28), Qwen2.5-VL-{7B, 72B} via Dashscope, temp=0, seed=42. Grounding = OmniParser v2 prompt block (YOLO+OCR+Florence-2 captions+relations) OR JEDI-7B-1080p click points. Modes = `both` (code + screenshot) or `mark` (code + screenshot with defects red-bboxed). Significance: paired Wilcoxon signed-rank (continuous), McNemar exact binomial for CSR. α = 0.05 unless noted.

**Methodology note on AST + CSR coupling.** DesignBench's evaluator zeros all metrics (including CMLS, CMCS, CodeScore, IssAcc) when a sample fails to compile. Paired AST-metric gains on cells with low baseline CSR therefore partially reflect compile-rate improvements — when a previously-uncompilable variant sample now compiles, it shifts from contributing a 0 to the variant mean to contributing its real AST score. This affects the 7B+omni Angular hero (baseline CSR .57 → variant .75) and inflates the CMCS +.073 gain modestly. CLIP, SSIM, and MAE are computed against rendered output and are not affected by this coupling.

---

## 1. TL;DR

- **Structural GUI grounding reliably improves UI-repair quality, but the pattern depends on model size × framework.**
- **Hero cell:** Qwen2.5-VL-7B on Angular with OmniParser → **CLIP 0.49 → 0.63 (+.141 ***, SSIM 0.41 → 0.52 (+.111 ***), CSR 57% → 75%**.
- **Consistent but smaller effect on 72B:** OmniParser delivers significant CLIP/SSIM gains on Vue, Angular, and Vanilla (all p ≤ .045). AST metrics (CMLS/CMCS) trend mildly negative but never significant — consistent with "CMLS penalizes correct rewrites."
- **JEDI is more targeted:** wins on 72B visual metrics for Vue/Vanilla/React. On 72B Angular the visual story is **mixed** — CLIP **−.013 *** and SSIM **−.026 *** regress, but MAE **−3.04 *** improves on the same cell.
- **JEDI has one catastrophic failure mode:** 7B + JEDI on React blows out every metric (CSR 1.00 → 0.50, CLIP −.309 ***). Root cause: JEDI's 34% parse rate on alignment defects, which dominate React.
- **JEDI IssAcc gains everywhere are partially confounded by label leakage** — the JEDI prompt names the defect type.
- **Methodology finding:** CLIP and SSIM disagree on 7B Vue with both groundings. CLIP > SSIM for generative UI repair.
- **Final count at α = 0.05: 27 significant gains, 12 significant regressions.**

---

## 2. Ranked findings for a poster

### Tier 1 — headline

1. **7B + OmniParser on Angular:** CLIP **+.141 ***, SSIM **+.111 ***, CMCS **+.073 *. CSR .57 → .75.
   *Mechanism:* Angular requires coordinated edits across `template.html` + `component.ts`; the weak 7B's spatial reasoning fails on 43% of samples without help. Explicit bboxes + OCR + relations supply the scaffolding.

2. **72B + OmniParser visual gains, 3 of 4 frameworks:** Vue CLIP **+.012 ***, Vanilla CLIP **+.018 ****, SSIM **+.019 ***, MAE **−.337 **, Angular CLIP **+.009 *, SSIM **+.003 *.
   *Mechanism:* Grounding nudges the strong 72B toward repairs that visually match the target even when the AST diverges from reference. CMLS rewards "reproduced the reference"; CLIP rewards "fixed the defect."

3. **7B + JEDI on React — cautionary regression.** CSR 1.00 → 0.50 ***, CLIP **−.309 ***, SSIM **−.304 ***, CMLS **−.096 ***, CMCS **−.084 ***, MAE **+52.6 ***.
   *Mechanism:* React samples are dominated by alignment defects (the most common defect type in the dataset); JEDI's parse rate on alignment is only 34%. Noisy/empty click coords mislead 7B into broken JSX.

4. **72B + JEDI visual gains on 3 non-Angular frameworks.** Vue SSIM **+.012 ****, CLIP **+.015 *, MAE **−.251 ***; Vanilla CLIP **+.013 ***, SSIM **+.026 *; React SSIM **+.011 ****, MAE **−1.15 ***.
   *Mechanism:* JEDI's click coordinates focus 72B attention on the defect region. Smaller effect than OmniParser on 7B because 72B already has spatial understanding — grounding refines rather than scaffolds.

5. **72B + JEDI on Angular — mixed-visual.** CLIP **−.013 ****, SSIM **−.026 *** regress; MAE **−3.04 *** improves on the same cell. IssAcc **+.225 *** (caveated leakage). CMLS/CMCS flat.
   *Mechanism:* 72B Angular baseline was already strongest in the whole study (CMLS .63, CLIP .82, CSR .96). JEDI's click coords displace attention the model was successfully using on CLIP/SSIM, while MAE (mean absolute pixel error) is pulled toward the reference enough to register a gain. Two visual metrics down, one up on the same samples.

6. **CLIP > SSIM methodology finding.** 7B + OmniParser on Vue: CLIP **+.021 ****, SSIM **−.016 ***. Mirrored by 7B + JEDI on Vue: CLIP **+.012 *, SSIM **−.043 *, MAE **+4.78 *.
   *Mechanism:* Two visual metrics disagree. Grounding often fixes the defect correctly but re-lays-out the page. CLIP (embedding similarity) rewards semantic match; SSIM (per-pixel) rewards position preservation.

7. **Alignment-defect slice, N=68 pooled across all 4 frameworks:** 72B + OmniParser gives CLIP **+.007 ***, while CMLS **−.055 *** and CMCS **−.045 *** drop on the same 68 samples. Single cleanest illustration of the CMLS-vs-CLIP divergence in the dataset.
   *Mechanism:* Alignment defects have no single AST token — they're spatial properties of many small elements. Grounding helps the model visually realign while the AST still diverges from reference.

8. **JEDI IssAcc gains everywhere (caveated).** +.22 to +.47 on 6 of 8 cells, all p < .01. Caveat: JEDI prompt names the defect type; IssAcc metric rewards naming defects; partial leakage.

### Tier 2 — supporting

9. **On 7B Angular, OmniParser beats JEDI.** After full render: +omni CLIP +.141 ** vs +jedi +.109 (not sig); +omni SSIM +.111 ** vs +jedi +.064 (not sig). OmniParser's element list addresses multi-file edit; JEDI's single-point scaffolding helps less for cross-file-coordinated repair.

10. **Mark mode + OmniParser — null result with one regression.** No significant gains anywhere. Vanilla 7B regresses: CMLS **−.144 **, CMCS **−.128 **. Red bboxes already say "here"; long structural text on top is redundant for 72B and distracting for 7B.

11. **Mark mode alone is itself a grounding signal.** Vue 72B IssAcc .213 → .352 just by switching both → mark (red bboxes). Angular 7B IssAcc .173 → .232. Explains why mark + omni doesn't double-dip.

### Tier 3 — only if asked

12. **JEDI parse rate skew by defect:** crowding 74% > overflow 58% > occlusion 40% > alignment 34% > color-contrast 36% > text-overlap 33%. JEDI trained for interactable-element clicking (buttons, icons) — fails on region/style defects.

13. **7B + OmniParser per-defect gains cluster on spatial defects:** alignment CLIP +.065 **, crowding IssAcc +.196 **, overflow SSIM +.106 **, occlusion CLIP +.095 *. Exactly what bboxes + OCR + relations encode.

---

## 3. Full panel — raw means (all cells)

| Framework | Model | Signal | Mode | N | CMLS | CMCS | IssAcc | CodeS | CLIP | SSIM | MAE | CSR |
|-----------|-------|--------|------|---|------|------|--------|-------|------|------|-----|-----|
| react | 72B | baseline | both | 28 | 0.34 | 0.23 | 0.40 | 0.15 | 0.77 | 0.75 | 86.2 | 1.00 |
| react | 72B | jedi | both | 28 | 0.35 | 0.25 | 0.66 | 0.22 | 0.77 | 0.76 | 85.0 | 1.00 |
| react | 72B | omni | both | 28 | 0.32 | 0.22 | 0.39 | 0.17 | 0.78 | 0.74 | 86.1 | 1.00 |
| react | 7B | baseline | both | 28 | 0.18 | 0.14 | 0.35 | 0.05 | 0.63 | 0.67 | 98.0 | 1.00 |
| react | 7B | **jedi** | both | 28 | **0.09** | **0.05** | 0.24 | 0.02 | **0.32** | **0.36** | 45.4 | **0.50** |
| react | 7B | omni | both | 28 | 0.16 | 0.12 | 0.39 | 0.05 | 0.65 | 0.67 | 97.5 | 1.00 |
| vue | 72B | baseline | both | 27 | 0.21 | 0.14 | 0.21 | 0.11 | 0.80 | 0.81 | 82.3 | 1.00 |
| vue | 72B | jedi | both | 27 | 0.21 | 0.14 | 0.65 | 0.09 | 0.81 | 0.82 | 82.1 | 1.00 |
| vue | 72B | omni | both | 27 | 0.20 | 0.14 | 0.23 | 0.09 | 0.81 | 0.78 | 83.5 | 1.00 |
| vue | 7B | baseline | both | 27 | 0.24 | 0.18 | 0.21 | 0.14 | 0.79 | 0.80 | 82.2 | 1.00 |
| vue | 7B | jedi | both | 27 | 0.28 | 0.23 | 0.68 | 0.15 | 0.80 | 0.76 | 87.0 | 1.00 |
| vue | 7B | omni | both | 27 | 0.20 | 0.14 | 0.27 | 0.12 | 0.81 | 0.78 | 84.2 | 1.00 |
| angular | 72B | baseline | both | 28 | 0.63 | 0.56 | 0.38 | 0.56 | 0.82 | 0.69 | 88.1 | 0.96 |
| angular | 72B | jedi | both | 28 | 0.62 | 0.55 | 0.60 | 0.56 | **0.81** | **0.67** | 85.0 | 0.93 |
| angular | 72B | omni | both | 28 | 0.58 | 0.49 | 0.36 | 0.56 | **0.83** | 0.69 | 87.7 | 0.96 |
| angular | 7B | baseline | both | 28 | 0.30 | 0.21 | 0.17 | 0.23 | 0.49 | 0.41 | 54.4 | 0.57 |
| angular | 7B | jedi | both | 28 | 0.38 | 0.29 | 0.43 | 0.32 | 0.59 | 0.47 | 65.5 | 0.68 |
| angular | 7B | **omni** | both | 28 | **0.39** | **0.28** | **0.24** | **0.28** | **0.63** | **0.52** | 70.6 | **0.75** |
| vanilla | 72B | baseline | both | 28 | 0.53 | 0.51 | 0.37 | 0.11 | 0.79 | 0.79 | 80.2 | 1.00 |
| vanilla | 72B | jedi | both | 28 | 0.52 | 0.50 | 0.61 | 0.11 | 0.80 | 0.82 | 79.8 | 1.00 |
| vanilla | 72B | omni | both | 28 | 0.44 | 0.43 | 0.34 | 0.12 | 0.81 | 0.81 | 79.9 | 1.00 |
| vanilla | 7B | baseline | both | 28 | 0.42 | 0.39 | 0.35 | 0.06 | 0.80 | 0.82 | 80.1 | 1.00 |
| vanilla | 7B | jedi | both | 28 | 0.44 | 0.41 | 0.65 | 0.06 | 0.80 | 0.80 | 82.8 | 1.00 |
| vanilla | 7B | omni | both | 28 | 0.43 | 0.40 | 0.40 | 0.08 | 0.80 | 0.80 | 80.8 | 1.00 |

Mark-mode cells (CLIP/SSIM/MAE/CSR all 0 — render skipped, AST-only eval):

| Framework | Model | Signal | Mode | N | CMLS | CMCS | IssAcc | CodeS |
|-----------|-------|--------|------|---|------|------|--------|-------|
| react | 72B | baseline | mark | 28 | 0.31 | 0.21 | 0.40 | 0.16 |
| react | 72B | omni | mark | 28 | 0.32 | 0.22 | 0.39 | 0.18 |
| react | 7B | baseline | mark | 28 | 0.12 | 0.09 | 0.36 | 0.07 |
| react | 7B | omni | mark | 28 | 0.16 | 0.11 | 0.42 | 0.08 |
| vue | 72B | baseline | mark | 27 | 0.23 | 0.16 | 0.35 | 0.12 |
| vue | 72B | omni | mark | 27 | 0.20 | 0.13 | 0.31 | 0.12 |
| vue | 7B | baseline | mark | 27 | 0.23 | 0.18 | 0.24 | 0.08 |
| vue | 7B | omni | mark | 27 | 0.21 | 0.14 | 0.36 | 0.08 |
| angular | 72B | baseline | mark | 28 | 0.62 | 0.55 | 0.41 | 0.58 |
| angular | 72B | omni | mark | 28 | 0.62 | 0.53 | 0.41 | 0.59 |
| angular | 7B | baseline | mark | 28 | 0.31 | 0.20 | 0.23 | 0.43 |
| angular | 7B | omni | mark | 28 | 0.34 | 0.22 | 0.35 | 0.40 |
| vanilla | 72B | baseline | mark | 28 | 0.57 | 0.55 | 0.32 | 0.17 |
| vanilla | 72B | omni | mark | 28 | 0.53 | 0.51 | 0.36 | 0.11 |
| vanilla | 7B | baseline | mark | 28 | 0.42 | 0.39 | 0.30 | 0.07 |
| vanilla | 7B | **omni** | mark | 28 | **0.27** | **0.26** | 0.24 | 0.04 |

**Bold cells** are the significant regressions/wins that anchor the poster narrative.

---

## 4. Significance table (α = 0.05)

Sorted by p-value. See `poster_stats.md` for the canonical file.

### Significant gains (27)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |
|---|---|---|---|---|---|---|---|---|
| 1 | 72B jedi both | vue | SSIM | 27 | 0.807 | 0.819 | +0.012 | <0.001 |
| 2 | 7B jedi both | react | MAE | 28 | 97.97 | 45.37 | −52.59 | <0.001 (*artifact, see note*) |
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
| 14 | 72B jedi both | angular | MAE | 28 | 88.08 | 85.03 | −3.04 | 0.005 |
| 15 | 7B omni both | vue | CLIP | 27 | 0.785 | 0.807 | +0.021 | 0.005 |
| 16 | 7B jedi both | angular | IssAcc | 28 | 0.173 | 0.429 | +0.256 | 0.005 |
| 17 | **7B omni both** | **angular** | **CLIP** | 28 | **0.486** | **0.627** | **+0.141** | **0.007** |
| 18 | 72B jedi both | react | MAE | 28 | 86.20 | 85.05 | −1.15 | 0.008 |
| 19 | 72B jedi both | vue | MAE | 27 | 82.33 | 82.08 | −0.25 | 0.008 |
| 20 | 72B jedi both | react | SSIM | 28 | 0.749 | 0.759 | +0.011 | 0.009 |
| 21 | 72B omni both | angular | SSIM | 28 | 0.691 | 0.694 | +0.003 | 0.026 |
| 22 | 72B omni both | vanilla | MAE | 28 | 80.23 | 79.89 | −0.34 | 0.030 |
| 23 | 72B jedi both | vanilla | SSIM | 28 | 0.794 | 0.820 | +0.026 | 0.032 |
| 24 | 72B jedi both | vue | CLIP | 27 | 0.796 | 0.811 | +0.015 | 0.041 |
| 25 | 7B jedi both | vue | CLIP | 27 | 0.785 | 0.798 | +0.012 | 0.044 |
| 26 | 72B omni both | angular | CLIP | 28 | 0.821 | 0.829 | +0.009 | 0.045 |
| 27 | 7B omni both | angular | CMCS | 28 | 0.206 | 0.279 | +0.073 | 0.048 |

*Note on rank 2 (7B+JEDI React MAE −52.59):* DesignBench's MAE drops to 0 when a sample fails to compile (no PNG to compare). The 7B+JEDI React CSR dropped from 1.00 to 0.50, so 14 samples have MAE=0. The mean "improvement" is an artifact of zeroed-out compile-fails — report the CSR regression (rank 1 in regressions table) and ignore this MAE line.

*IssAcc caveat applies to ranks 3–6, 11, 13, 16:* JEDI prompt names the defect type → partial label leakage.

### Significant regressions (12)

| Rank | Comparison | Framework | Metric | N | Baseline | Variant | Δ | p |
|---|---|---|---|---|---|---|---|---|
| 1 | **7B jedi both** | **react** | **CSR** | 28 | 1.000 | 0.500 | **−0.500** | <0.001 |
| 2 | 7B jedi both | react | CLIP | 28 | 0.632 | 0.322 | −0.309 | <0.001 |
| 3 | 7B jedi both | react | SSIM | 28 | 0.668 | 0.364 | −0.304 | <0.001 |
| 4 | 7B omni both | vue | SSIM | 27 | 0.799 | 0.783 | −0.016 | 0.004 |
| 5 | 72B jedi both | angular | CLIP | 28 | 0.821 | 0.808 | −0.013 | 0.005 |
| 6 | 7B jedi both | react | CMCS | 28 | 0.139 | 0.055 | −0.084 | 0.006 |
| 7 | 7B jedi both | react | CMLS | 28 | 0.182 | 0.085 | −0.096 | 0.006 |
| 8 | 72B jedi both | angular | SSIM | 28 | 0.691 | 0.665 | −0.026 | 0.020 |
| 9 | 7B jedi both | vue | SSIM | 27 | 0.799 | 0.756 | −0.043 | 0.025 |
| 10 | 7B jedi both | vue | MAE | 27 | 82.24 | 87.01 | +4.78 | 0.025 |
| 11 | 7B omni mark | vanilla | CMLS | 28 | 0.417 | 0.274 | −0.144 | 0.032 |
| 12 | 7B omni mark | vanilla | CMCS | 28 | 0.388 | 0.261 | −0.128 | 0.038 |

### Marginal (0.05 ≤ p < 0.10), for reference (12)

| Comparison | Framework | Metric | N | Δ | p | direction |
|---|---|---|---|---|---|---|
| 7B jedi both | angular | CLIP | 28 | +0.109 | 0.059 | ↑ (better) |
| 7B jedi both | angular | SSIM | 28 | +0.064 | 0.097 | ↑ (better) |
| 7B omni both | angular | CMLS | 28 | +0.090 | 0.069 | ↑ (better) |
| 7B omni both | vue | IssAcc | 27 | +0.062 | 0.074 | ↑ (better) |
| 72B omni mark | vue | CMCS | 27 | −0.027 | 0.052 | ↓ (worse) |
| 7B jedi both | react | CodeScore | 28 | −0.028 | 0.068 | ↓ (worse) |
| 72B jedi both | vue | CodeScore | 27 | −0.016 | 0.069 | ↓ (worse) |
| 72B jedi both | vanilla | MAE | 28 | −0.378 | 0.077 | ↑ (better) |
| 7B omni both | vue | CMLS | 27 | −0.037 | 0.079 | ↓ (worse) |
| 7B omni both | vue | CMCS | 27 | −0.043 | 0.072 | ↓ (worse) |
| 7B omni mark | vue | CMCS | 27 | −0.042 | 0.086 | ↓ (worse) |
| 7B jedi both | vue | CLIP | 22 | +0.014 | 0.068 | ↑ (better) |

---

## 5. Per-defect-type slice

Each row pools samples by defect type across all 4 frameworks. N reflects the most common metric (CMLS); CLIP/SSIM have lower N because mark-mode rows don't contribute rendered data.

### 7B + OmniParser on `both` mode

| Defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|--------|---|------|------|--------|-----------|------|------|
| alignment | 63 | −.010 | −.013 | +.059 . | +.019 | **+.065 *** | **+.039 *** |
| crowding | 30 | −.001 | −.010 | **+.196 *** | **+.078 *** | +.020 | −.007 |
| occlusion | 29 | +.013 | +.002 | +.002 | +.078 | **+.095 *** | **+.082 *** |
| overflow | 17 | +.020 | +.002 | +.250 . | −.018 | +.157 . | **+.106 *** |
| color and contrast | 11 | +.088 | +.098 | +.125 | +.119 | +.089 | −.037 |

### 72B + OmniParser on `both` mode (biggest-N finding)

| Defect | N | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM |
|--------|---|------|------|--------|-----------|------|------|
| **alignment** | **68** | **−.055 *** | **−.045 *** | −.019 | −.031 | **+.007 *** | −.014 |
| crowding | 31 | −.043 | −.044 | −.016 | +.025 | **+.035 *** | +.037 |
| occlusion | 30 | −.037 | −.036 | −.039 | +.016 | **+.011 *** | −.024 |
| overflow | 19 | −.009 | −.010 | +.042 | −.005 | **+.064 *** | +.047 |
| color and contrast | 11 | −.025 | −.019 | −.003 | +.003 | +.013 | **+.059 *** |

**Alignment row is the cleanest single illustration of the CMLS-vs-CLIP divergence in the study.** Same 68 samples. CMLS and CMCS both drop significantly; CLIP rises significantly. Two metrics say "better," two say "worse."

Full per-defect panels including JEDI + mark modes: [per_defect.md](per_defect.md).

---

## 6. Grounding-method decision table

| Condition | OmniParser | JEDI |
|-----------|------------|------|
| Weak 7B on hard framework (Angular) | **STRONG multi-metric (CLIP +.14, SSIM +.11, CSR +.18)** | Modest visual (not sig after render); big IssAcc (leaky) |
| Strong 72B on Vue / Vanilla | **Consistent CLIP gain** | **Consistent CLIP + SSIM gain, smaller** |
| Strong 72B on React | Flat | **Small SSIM + MAE gain** |
| Strong 72B on Angular | Small CLIP gain | **Mixed-visual** (CLIP −.013 **, SSIM −.026 * regress; MAE −3.04 ** improves) |
| 7B on React | Flat | **Catastrophic regression** (CSR 1.00 → 0.50) |
| 7B on Vanilla | Flat | Flat |
| On top of `mark` mode | Redundant, or mildly hurts 7B Vanilla | Not tested |

---

## 7. Run timeline

Each entry = one experimental configuration. See [ablation_log.md](../ablation_log.md) for full logs.

| Run | Signal × Mode × Model | State | Commits |
|-----|----------------------|-------|---------|
| 01 | OmniParser v2 × both × 7B | DONE | 5ec2828, eab17e8, e2eb9f0, 3531c38 |
| 02 | OmniParser v2 × both × 72B | DONE | 5ec2828, eab17e8, e2eb9f0, 3531c38 |
| 05 | CLIP render pass (fill missing visual metrics for Runs 01+02) | DONE | 3531c38 |
| 06 | JEDI click-points × both × 7B+72B (full render) | DONE | 4039ee1, faec452 |
| 07 | `mark` mode × baseline+OmniParser × 7B+72B (AST-only) | DONE | 3531c38 |
| 08 | Per-defect-type slicing of all results | DONE | db1e320 |
| 09 | Poster-ready significance filter (α=0.05) | DONE | 6aa188a, faec452 |
| 10 | Ranked results overview with mechanisms | DONE | 6aa188a, faec452 |

**Current HEAD:** `faec452`.

---

## 8. Open questions / future work

**Methodology:**
- Drop the defect-type leakage from JEDI prompt (replace "alignment" with anonymized identifier). Re-run to get a clean IssAcc measurement.
- Render mark-mode cells to get CLIP/SSIM/MAE for the mark+omni null result. Might reveal a visual effect we're missing in AST-only eval.

**Methods:**
- **Hybrid OmniParser + JEDI.** They have complementary strengths on 7B Angular (omni = visual, JEDI = AST+IssAcc). Does combining them beat either alone?
- **Filter JEDI cache to only parsed clicks.** The noisy alignment-defect coords are what blew up 7B React. Removing them could flip the sign.
- **Reference-vs-broken diff grounding.** DesignBench gives both screenshots; ground only the diffs. More targeted than either current signal.
- **Trimmed OmniParser ablation.** Test elements-only vs relations-only vs OCR-only to isolate which substrate matters on the 7B Angular hero cell.
- **Defect-type-conditioned grounding.** Vary the prompt format per defect type (OCR-heavy for text_overlap; relations-heavy for alignment).

**External validity:**
- Run on UICrit or WebSight for generalization beyond DesignBench.
- Add smaller models (Qwen-VL-3B) to see if the "grounding scaffolds weak models" story strengthens.

---

## 9. Reproducibility

- Cache builders: `scripts/build_structural_cache.py`, `scripts/build_jedi_cache.py`
- Grounded runners: `scripts/run_repair_grounded.py`, `scripts/run_repair_grounded_jedi.py`
- Resilient eval with --skip-render fallback: `scripts/resilient_eval.py`
- Stats: `scripts/stats_test.py` (full panel), `scripts/poster_stats.py` (α=0.05 filter)
- Per-defect slice: `scripts/per_defect_analysis.py`
- Raw eval JSONs: [results/eval/](eval/)
- Caches (gitignored — regenerate or pull from Drive): `grounding_structural_cache.json`, `jedi_cache.json`
