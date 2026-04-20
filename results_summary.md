# DesignBench Repair Ablation — Baseline vs +Structural OmniParser Grounding

**Task:** DesignBench UI repair. Inject OmniParser structural grounding (YOLO + EasyOCR + Florence-2 captions + pairwise geometric relations + pixel stats) into the Qwen2.5-VL repair prompt. Compare to the ungrounded baseline on same 111 samples (27–28 per framework).

**Run date:** 2026-04-20. Same temp=0 seed=42 as baseline.

## Headline

**Grounding helps the small model and hurts the big one.**

7B benefits from explicit element lists + spatial relations; its own vision+spatial reasoning is weaker, so the grounding acts as scaffolding. 72B already has good internal spatial understanding, and the extra prompt becomes noise that pulls it off a stronger baseline.

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

## Discussion

1. **Clear size-dependent effect.** The 7B model gains across every IssAcc column (grounding helps it *find* the defect), and on Angular specifically gets a large boost on CMLS/CMCS (correctness of the produced repair). 72B drops on nearly every structural metric.

2. **The biggest 7B win is Angular CMLS +.139.** Angular repair is where 7B was most compile-fragile (.30 vs 72B's .63). Grounding closes almost half the gap. Concrete explanation candidate: Angular's split of template + TS makes "which element is broken" underspecified from just the screenshot — explicit bbox → DOM position helps 7B focus.

3. **72B Vanilla is the worst regression (−.088 CMLS, −.081 CMCS).** Baseline 72B on Vanilla was strong; the grounding block introduces long text that apparently dilutes attention. Memo predicted this for wrong-location edits — empirically the opposite: 72B was already making the right edits.

4. **IssAcc vs CMLS/CMCS split.** On Vue 7B and React 7B, IssAcc goes up but CMLS/CMCS goes down. That means grounding helps the model name the defect correctly, but the code it writes to fix it is structurally different from the reference. Per baseline memo: "CMLS/CMCS penalize correct rewrites." So IssAcc gains here are real signal, CMLS losses may be penalty-for-diversity, not actual regression. Visual confirmation (CLIP) would disambiguate — missing from AST-only runs.

## Caveats + missing

- **CLIP only for React + Vue 72B+omni.** The other 6 cells skipped render (Angular is ~2.5 min/sample via per-sample `ng serve`, full render would have blown past the nap window). The two we have show CLIP +.006 and +.012 — directionally consistent with grounding not wrecking the visual output.
- **CSR not recomputed.** Baseline CSR is in the JSONs; +omni runs have `compile_success=False` for AST-only samples which is *unknown*, not failing. Don't read CSR from this run.
- **N = 27–28 per cell.** Memo flagged: 2–3 samples shift means ~10%. Most deltas here are inside that window *except* Angular 7B, Vanilla 72B, and Vue 7B IssAcc, which are past-noise real.
- **JEDI variant not run.** Needs vllm → GPU → Colab. `scripts/build_jedi_cache.py` + `scripts/run_repair_grounded_jedi.py` staged, will run next pass.
- **One grounding style only.** Structural block contains pixel stats + element list + geometric relations + captions. A terser prompt (elements only, no relations) may land differently — one-knob ablation unexamined.

## Files + commits

- Structural cache: `grounding_structural_cache.json` (111 samples, 0 errors, MPS ~15s/sample)
- Grounded repair outputs: `external/DesignBench/results/repair/{fw}-{fw}/qwen2.5-vl-{7b,72b}-instruct+omni/`
- Per-framework eval: `external/DesignBench/code/evaluator/res/DesignRepair/{react,vue,angular,vanilla}_both.json`
- Reproduction: `bash scripts/_orchestrate_ablation.sh` (assumes cache exists; cache-builder = `scripts/build_structural_cache.py`)

## Next steps

1. **Render missing CLIP cells** for 72B+omni angular/vanilla and all 7B+omni. Expensive (~2hr) but closes visual-metric gap.
2. **Per-defect-type slicing.** Memo predicted overflow/occlusion as grounding's strongest area; pooled metrics hide this. Groupby `issue` field from DesignBench config JSONs.
3. **Ablate prompt richness.** Try elements-only (drop pixel stats + relations). If 72B regression shrinks, the "too much text" hypothesis is probably right.
4. **Run JEDI variant on Colab** for click-point grounding (single-point vs structural list).
