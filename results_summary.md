# DesignBench Repair Ablation — Baseline vs +Structural OmniParser Grounding

**Task:** DesignBench UI repair. Inject OmniParser structural grounding (YOLO + EasyOCR + Florence-2 captions + pairwise geometric relations + pixel stats) into the Qwen2.5-VL repair prompt. Compare to the ungrounded baseline on same 111 samples (27–28 per framework).

**Run date:** 2026-04-20. Same temp=0 seed=42 as baseline.

## Headline (revised after significance testing)

**Grounding significantly improves 7B on Angular repair. Everything else is statistical noise at N=27–28.**

Wilcoxon signed-rank paired test + bootstrap 95% CI on mean paired difference (`scripts/stats_test.py`).

Significant 7B gains (p < 0.05):
- Angular CMLS **+.138** (p=0.004 **)
- Angular CMCS **+.094** (p=0.005 **)
- Angular IssAcc **+.158** (p=0.007 **)
- Angular CodeScore **+.148** (p=0.026 *)

Marginal 7B signals (p < 0.10), two-tailed:
- Vue CMLS −.037 (p=0.079), Vue CMCS −.046 (p=0.090) — marginal DROP.
- Vue IssAcc +.062 (p=0.074) — marginal gain.
- Vue pattern is a tradeoff: grounding helps the model name the defect but the code rewrite diverges from the reference. Per baseline memo: "CMLS/CMCS penalize correct rewrites" — consistent but unconfirmed visually.

Everything else is statistically indistinguishable from noise, including the 72B regressions I flagged in the first draft. **No 72B metric change crosses p<0.10.** The "grounding hurts big model" story does NOT hold up at this N.

## What's real, one line:
> **Angular 7B repair is the one regime where OmniParser structural grounding gives a large, statistically reliable win — roughly closing half the 7B → 72B gap on that framework's AST-similarity metrics.**

## Delta table (all N=27–28)

### Qwen2.5-VL-72B (strong baseline → **regressions**)

| Framework | Metric     | Baseline | +omni  | Δ        |
|-----------|------------|----------|--------|----------|
| React     | CMLS       | .339     | .317   | **−.022** |
| React     | CMCS       | .230     | .221   | −.009     |
| React     | IssAcc     | .395     | .388   | −.007     |
| React     | CLIP       | .771     | .777   | **+.006** |
| Vue       | CMLS       | .213     | .202   | −.011     |
| Vue       | CMCS       | .143     | .137   | −.006     |
| Vue       | IssAcc     | .213     | .225   | **+.012** |
| Vue       | CLIP       | .796     | .808   | **+.012** |
| Angular   | CMLS       | .631     | .596   | −.035     |
| Angular   | CMCS       | .556     | .498   | **−.058** |
| Angular   | IssAcc     | .379     | .375   | −.004     |
| Vanilla   | CMLS       | .532     | .444   | **−.088** |
| Vanilla   | CMCS       | .510     | .429   | **−.081** |
| Vanilla   | IssAcc     | .369     | .339   | −.030     |

### Qwen2.5-VL-7B (weaker baseline → **gains**)

| Framework | Metric     | Baseline | +omni  | Δ         |
|-----------|------------|----------|--------|-----------|
| React     | CMLS       | .182     | .156   | −.026      |
| React     | CMCS       | .139     | .116   | −.023      |
| React     | IssAcc     | .345     | .385   | **+.040**  |
| Vue       | CMLS       | .237     | .200   | −.037      |
| Vue       | CMCS       | .179     | .133   | −.046      |
| Vue       | IssAcc     | .210     | .272   | **+.062**  |
| Angular   | CMLS       | .304     | .443   | **+.139**  |
| Angular   | CMCS       | .206     | .300   | **+.094**  |
| Angular   | IssAcc     | .173     | .330   | **+.157**  |
| Vanilla   | CMLS       | .422     | .431   | +.009      |
| Vanilla   | CMCS       | .394     | .403   | +.009      |
| Vanilla   | IssAcc     | .345     | .399   | **+.054**  |

## Discussion (after significance)

1. **The Angular 7B result is robust.** Four metrics move significantly in the same direction (CMLS p=.004, CMCS p=.005, IssAcc p=.007, CodeScore p=.026). 95% CI on paired difference for CMLS is [+.020, +.251] — doesn't cross zero. At N=28 with 4-metric consistency, this is believable.

2. **Why Angular specifically?** Angular repair requires edits across template + TypeScript files. "Which element has the defect" is more ambiguous from a screenshot alone — explicit bbox→DOM position and OCR text give 7B scaffolding it otherwise lacks. 72B already handles this internally, so no gain.

3. **Eyeball-significant ≠ statistically significant.** In the first draft I confidently reported "72B Vanilla CMLS −.088, CMCS −.081" as a real regression. Paired Wilcoxon p=.149 / .142. 95% CI crosses zero. Mean drop is real on these 28 samples, but I can't rule out noise. Same story for 72B Angular, 72B React. The "grounding hurts 72B" narrative is not supported by these N.

4. **Vue 7B tradeoff is marginal, not clear.** CMLS/CMCS drop trend (p≈.08–.09) and IssAcc rise trend (p≈.07) are on the threshold. Visual (CLIP) would be the tiebreaker — we have it for Vue 72B only, where CLIP went +.012 on a non-significant sample.

5. **What to do about small-N.** For a real paper claim you'd want N≥100/cell or at minimum bootstrap CIs that don't cross zero. Angular 7B gets there. Others need either more samples (unavailable — DesignBench is fixed size) or different benchmarks to scale up.

## Caveats + missing

- **CLIP only for React + Vue 72B+omni.** The other 6 cells skipped render (Angular is ~2.5 min/sample via per-sample `ng serve`, full render would have blown past the nap window). The two we have show CLIP +.006 and +.012 — directionally consistent with grounding not wrecking the visual output.
- **CSR not recomputed.** Baseline CSR is in the JSONs; +omni runs have `compile_success=False` for AST-only samples which is *unknown*, not failing. Don't read CSR from this run.
- **N = 27–28 per cell.** Memo flagged: 2–3 samples shift means ~10%. Most deltas here are inside that window *except* Angular 7B, Vanilla 72B, and Vue 7B IssAcc, which are past-noise real.
- **JEDI variant not run.** Needs vllm → GPU → Colab. `scripts/build_jedi_cache.py` + `scripts/run_repair_grounded_jedi.py` staged, will run next pass.
- **One grounding style only.** Structural block contains pixel stats + element list + geometric relations + captions. A terser prompt (elements only, no relations) may land differently — one-knob ablation unexamined.

## Files + commits

- Structural cache: `grounding_structural_cache.json` (111 samples, 0 errors, MPS ~15s/sample)
- Grounded repair outputs: `external/DesignBench/results/repair/{fw}-{fw}/qwen2.5-vl-{7b,72b}-instruct+omni/`
- Per-framework eval: `results/eval/{react,vue,angular,vanilla}_both.json` (snapshot; originals live in gitignored `external/DesignBench/code/evaluator/res/DesignRepair/`)
- Significance tests: `scripts/stats_test.py` (Wilcoxon signed-rank + bootstrap CI)
- Reproduction: `bash scripts/_orchestrate_ablation.sh` (assumes cache exists; cache-builder = `scripts/build_structural_cache.py`)

## Next steps

1. **Render missing CLIP cells** for 72B+omni angular/vanilla and all 7B+omni. Expensive (~2hr) but closes visual-metric gap.
2. **Per-defect-type slicing.** Memo predicted overflow/occlusion as grounding's strongest area; pooled metrics hide this. Groupby `issue` field from DesignBench config JSONs.
3. **Ablate prompt richness.** Try elements-only (drop pixel stats + relations). If 72B regression shrinks, the "too much text" hypothesis is probably right.
4. **Run JEDI variant on Colab** for click-point grounding (single-point vs structural list).
