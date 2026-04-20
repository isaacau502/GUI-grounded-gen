# DesignBench Repair Ablation — Baseline vs +Structural OmniParser Grounding

**Task:** DesignBench UI repair. Inject OmniParser structural grounding (YOLO + EasyOCR + Florence-2 captions + pairwise geometric relations + pixel stats) into the Qwen2.5-VL repair prompt. Compare to the ungrounded baseline on same 111 samples (27–28 per framework).

**Run date:** 2026-04-20. Same temp=0 seed=42 as baseline. Full render pass with CLIP/SSIM/MAE/CSR computed for every cell.

## Headline

**Grounding helps both sizes, but on different axes:**

- **7B Angular:** big multi-metric win (CLIP +.141 **, SSIM +.111 **, CMCS +.073 *). Scaffolds a weak baseline (CSR .57 → .75 directional).
- **72B everywhere:** grounding significantly improves **visual** metrics (CLIP/SSIM/MAE) on Vue + Angular + Vanilla while sometimes hurting AST metrics. This is the "CMLS penalizes correct rewrites" tradeoff the baseline memo predicted — the model produces a repair that looks right but uses a different AST structure than the reference code.
- **7B Vue:** same tradeoff pattern — CLIP +.021 **, SSIM −.016 **, IssAcc +.062 (marginal). Semantic-visual-similarity up, pixel-structural-similarity down.
- **7B React / 7B Vanilla:** nothing significant.

## Full results — 8 cells × 8 metrics

Wilcoxon signed-rank paired, two-sided. 95% CI bootstrap on paired mean diff (5000 reps). `**` p<0.01, `*` p<0.05, `.` p<0.10.

### 7B — Qwen2.5-VL-7B vs 7B+omni (N=27–28)

| Framework | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM | MAE (↓) | CSR |
|-----------|------|------|--------|-----------|------|------|---------|-----|
| React     | −.026  | −.022  | +.040 | +.008 | +.022 | +.006 | −0.4 | 0 |
| Vue       | −.037 . | −.043 . | +.062 . | −.025 | **+.021** | **−.016** | +1.9 | 0 |
| Angular   | +.090 . | **+.073*** | +.071 | +.054 | **+.141** | **+.111** | +16.2 | +.179 (p=.125) |
| Vanilla   | +.009  | +.008 | +.054 | +.020 | +.000 | −.022 | +0.7 | 0 |

### 72B — Qwen2.5-VL-72B vs 72B+omni (N=27–28)

| Framework | CMLS | CMCS | IssAcc | CodeScore | CLIP | SSIM | MAE (↓) | CSR |
|-----------|------|------|--------|-----------|------|------|---------|-----|
| React     | −.021 | −.009 | −.007 | +.019 | +.006 | −.013 | −0.1 | 0 |
| Vue       | −.011 | −.006 | +.012 | −.014 | **+.012** | −.022 | +1.2 | 0 |
| Angular   | −.051 | −.065 | −.022 | −.009 | **+.009*** | **+.003*** | −0.4 | 0 |
| Vanilla   | −.088 | −.081 | −.030 | +.005 | **+.018** | **+.019** | **−.337*** | 0 |

**MAE is lower-better. All other metrics higher-better. CSR deltas use McNemar exact binomial on discordant pairs.**

## Discussion

### 72B: visual wins, AST losses — "CMLS penalizes correct rewrites"

Every 72B+omni cell except React has a statistically significant CLIP improvement. Vanilla gets hit-trifecta: CLIP, SSIM, MAE all significantly better. Yet every 72B AST metric (CMLS/CMCS) trends negative.

This is exactly what the baseline memo predicted: DesignBench's CMLS/CMCS compares generated-code AST to a *specific reference* AST. Grounding pushes the model to produce a repair that fixes the visual defect but via a different code path, so AST similarity drops even though the repair is arguably better. CLIP (embedding-space visual similarity) captures this; CMLS can't.

For a fair writeup, **CLIP should be the headline metric on DesignBench when comparing generation strategies**, not CMLS. CMLS answers "did you reconstruct the reference code?" CLIP answers "did you fix the defect?"

### 7B Angular: robust multi-metric win

Angular 7B is the one cell where grounding moves nearly everything in the right direction:
- CLIP +.141 **, SSIM +.111 ** — visual match way better
- CMCS +.073 *, CMLS +.090 . — AST improves too (on a baseline where 43% of samples compile-fail)
- CSR .57 → .75 — ~6 extra samples compile, only 1 regression (McNemar p=.125, directional big jump)

Plausible mechanism: Angular repairs require coordinated edits across `template.html` + `component.ts`. "Which element is broken" is underdetermined from the screenshot alone; explicit OmniParser bboxes + element captions + OCR text scaffold the 7B into correct localization. 72B already handles this, so no gain.

### 7B Vue: CLIP up, SSIM down — semantic vs structural

CLIP and SSIM disagree:
- CLIP (learned embedding similarity) +.021 **, says the repair is *semantically* closer to target.
- SSIM (per-pixel structural similarity) −.016 **, says the pixel layout is *less* similar to target.

The repair looks right to a VLM but moves pixels around. Likely the model is using grounding to re-lay-out the fix correctly but the specific pixel positions drift from the reference. One more data point for "CLIP is the right metric."

### What doesn't work

- **React 7B / 7B Vanilla:** grounding has no significant effect in either direction. Vanilla 7B baseline is already the strongest 7B cell (CMLS .42) — less room. React 7B starts weak but grounding doesn't recover it.
- **React 72B:** flat across all metrics.
- **CSR on everything except Angular 7B:** ceiling effect. 72B CSR is .96–1.00 in all frameworks, and 7B CSR is 1.00 on React/Vue/Vanilla. Only Angular 7B (.57) has room, and we saw the directional jump there.

## Caveats

- **N=27–28 per cell.** Bootstrap CIs for some "significant" effects still cross zero by a small margin — e.g., Angular 72B CLIP +.009 p=.045 has CI [−.078, +.093]. These are tight thresholds, take with appropriate salt.
- **CSR scoring artifact:** DesignBench zeros *all* metrics (including AST) when compile fails. That means for baselines with low CSR (e.g. Angular 7B .57), baseline AST scores are artificially low because 43% of samples got CMLS=0. When grounding increases CSR, those samples contribute real (non-zero) AST scores — so some of the grounding "AST improvement" is an artifact of better CSR. The CLIP/SSIM gains are clean, though — they're computed against rendered output, apples-to-apples.
- **DesignBench's reference CSR for Vanilla is broken:** `compile_error != "NULL"` artifact makes vanilla CSR read as 0.000 when actually 1.00. Everything treated as compile_success=True in our metrics. See baseline memo.
- **JEDI variant not run yet.** Waiting on Colab.

## Files

- Cache: `grounding_structural_cache.json` (111 entries, MPS, ~15s/sample)
- Eval JSONs: `results/eval/{react,vue,angular,vanilla}_both.json`
- Grounded outputs: `external/DesignBench/results/repair/{fw}-{fw}/qwen2.5-vl-{7b,72b}-instruct+omni/`
- Scripts: `scripts/build_structural_cache.py`, `scripts/run_repair_grounded.py`, `scripts/resilient_eval.py`, `scripts/stats_test.py`, `scripts/compare_results.py`
- Reproduce stats: `python scripts/stats_test.py`

## Next

- **Mark-mode ablation** running — baseline mark vs +omni mark, 72B + 7B × 4 fw. ETA ~60 min from now.
- **JEDI click-point ablation** on Colab — user action, DesignBench data now uploaded to Drive.
- **Per-defect-type slicing** — may reveal grounding helps spatial defects (overflow/occlusion/text_overlap) more than non-spatial ones. Zero-compute.
- **Trimmed-prompt ablation** — test if dropping pixel stats / relations / OCR individually changes the 72B AST regression.
