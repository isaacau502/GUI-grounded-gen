# Poster pooled significance table

Drop-in table for the poster's results section. All numbers pooled across all 4 frameworks (React 28, Vue 27, Angular 28, Vanilla 28), N = 111 per row. Source: `results/eval/*_both.json`. Reproduce: `python scripts/stats_test.py` then pool inline.

Paired Wilcoxon signed-rank (two-sided) for continuous metrics. McNemar exact binomial on discordant pairs for CSR. Signs set so positive = improvement (MAE flipped).

---

## Version A — expanded (recommended for a wide panel)

**Pooled across 4 frameworks · N = 111**

| Variant | CMLS | CLIP | SSIM | IssAcc | CSR |
|---------|------|------|------|--------|-----|
| **7B + omni** | +.010 | **+.049 \*\*** | **+.021 \*\*** | **+.081 \*** | +.045 |
| **72B + omni** | −.043 . | **+.011 \*\*** | −.003 | −.015 | — |
| **72B + jedi** | −.005 | **+.004 \*\*** | **+.006 \*\*** | +.331 \*\* ✱ | −.009 |
| **7B + jedi** | +.012 | −.050 | −.081 | +.277 \*\* ✱ | **−.099 \*** ⚠ |

**Legend.** `**` p<0.01, `*` p<0.05, `.` p<0.10. ✱ prompt leakage (see below). ⚠ significant regression.

**Caption.**
> Paired Wilcoxon (CLIP, SSIM, IssAcc, CMLS); McNemar exact binomial on discordant pairs (CSR). Signs on CMLS / MAE flipped so positive = improvement. **✱** JEDI grounding prompt names the defect types verbatim, partially leaking the IssAcc metric's answer. **⚠** 7B + JEDI loses 11 samples of compile success (17 baseline-only, 6 variant-only).

---

## Version B — compact (side panel, 4 cols)

**Pooled N = 111**

| | CLIP | SSIM | CSR |
|---|---|---|---|
| 7B + omni | **+.049 \*\*** | **+.021 \*\*** | +.045 |
| 72B + omni | **+.011 \*\*** | −.003 | — |
| 72B + jedi | **+.004 \*\*** | **+.006 \*\*** | −.009 |
| 7B + jedi | −.050 | −.081 | **−.099 \*** ⚠ |

---

## Version C — headline only (single-row callout)

**Pooled across 4 frameworks (N = 111): Qwen2.5-VL-7B + OmniParser gains CLIP +.049 (p<0.01) and SSIM +.021 (p<0.01).**

Plus cautionary: **Qwen-7B + JEDI loses 9.9 percentage points of compile rate (p=.035).**

---

## Per-metric interpretation

### CLIP (visual similarity, higher = better)
Every grounding cell except 7B+JEDI improves CLIP significantly at N=111. The 7B+omni +.049 absolute = **+6.9 % relative** is the only meaningfully large effect. 72B effects are small (+.004 to +.011 absolute, 0.5% to 1.4% relative) but directionally consistent.

### SSIM (pixel-structural similarity, higher = better)
Follows CLIP direction on 7B+omni and 72B+jedi (both p<.01). 72B+omni flat. 7B+jedi trending down but not significant pooled.

### CMLS / CMCS (AST edit similarity to reference)
Never significantly positive. 72B+omni marginally declining (CMLS p=.056). **This is the "CMLS penalizes correct rewrites" finding — AST-based metric does not reward visually correct repairs that use different code paths than the reference.**

### IssAcc (correct defect-type identification)
7B+omni +.081 (p=.015) is clean — OmniParser prompt does not name defect types. JEDI's +.28 and +.33 are partially leakage: JEDI grounding block literally contains the defect type strings.

### CSR (compile success rate)
7B+omni directional gain (+4.5 pp, p=.125 not sig). 72B cells at ceiling (both .99+). 7B+JEDI significant regression (−9.9 pp, p=.035) — 17 samples compiled baseline but not grounded, only 6 the other way.

### MAE
Omitted from the main table. 7B+JEDI shows MAE −9.1 (p<.001) which looks like a win, but it's an **artifact**: DesignBench sets MAE=0 for samples that failed to compile, so the CSR drop pulls MAE toward zero spuriously.

---

## Hero-cell reference (for the bar chart companion)

Biggest-effect single cell in the study. These are the numbers on the hero bar chart, NOT pooled.

**Qwen2.5-VL-7B × Angular × +OmniParser · N = 28**

| Metric | Baseline | +omni | Δ | p |
|--------|----------|-------|---|---|
| CLIP | 0.486 | 0.627 | **+.141** | .007 \*\* |
| SSIM | 0.407 | 0.519 | **+.111** | .002 \*\* |
| CMCS | 0.206 | 0.279 | **+.073** | .048 \* |
| CMLS | 0.304 | 0.394 | +.090 | .069 . |
| CSR | 0.571 | 0.750 | +.179 | .125 (McNemar) |

**+29% CLIP relative / +27% SSIM relative / 6 extra samples compile.**

---

## How to use

- If the poster has space for a 5-column table next to the bar chart: use **Version A**.
- If it's a narrow side panel: use **Version B**.
- If you only have room for a single-line callout under the hero chart: use **Version C**.

All three cite the same data. Pick one and drop into the poster.
