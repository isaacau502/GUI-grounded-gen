# Ablations not done (backlog)

Reference list of experiments we have NOT run. Sorted by priority-per-effort. Cost estimates assume the grounded repair harness we already built.

## Tier 1 — poster/paper-ready additions

### 1. Hybrid OmniParser + JEDI grounding
- **Why:** Complementary strengths on 7B Angular (omni = visual, JEDI = AST + IssAcc). Combining them might beat either alone.
- **Work:** New runner that merges both cache injections into one prompt. Tag output `+hybrid`.
- **Cost:** ~1 hr gen + eval. Hero cell only.
- **Risk:** Low. Worst case = same as best individual.
- **Paper value:** High. Could produce a new Tier 1 finding.

### 2. Anonymized-defect-label JEDI
- **Why:** Cleans the IssAcc leakage confound. Current JEDI IssAcc gains (+.277, +.331) are 70–95% attributable to the prompt naming defect types. An anonymized variant measures the clean lift.
- **Work:** Fork `run_repair_grounded_jedi.py` to inject `defect_A` / `defect_B` instead of the real type names. One re-run of the JEDI ablation.
- **Cost:** ~1 hr gen + eval.
- **Risk:** Low. Either result (leakage confirmed or surprise residual gain) is publishable.

### 3. Filtered JEDI cache (only-parsed clicks)
- **Why:** Tests whether the 7B React catastrophic regression (CSR 1.00 → 0.50) is signal-driven or noise-driven. If removing the 55% failed-parse entries from the cache flips 7B React to neutral, the failure mode is fixable.
- **Work:** Filter `jedi_cache.json` to drop `parse_success=false` entries. Re-run 7B+jedi on React (or all frameworks).
- **Cost:** ~45 min.
- **Risk:** Low. Either result is interesting.

### 4. Mark-mode visual-metric render
- **Why:** Fills CLIP/SSIM/MAE/CSR cells for the 8 mark-mode variants (currently AST-only via `--skip-render`). Makes the mark-mode null result defensible in a paper.
- **Work:** Re-run `resilient_eval.py` without `--skip-render` for 7B/72B × +omni × mark cells.
- **Cost:** ~2 hrs (Angular is slow).

### 5. Reference-vs-broken diff grounding
- **Why:** Baseline memo flagged this as highest-leverage new experiment. DesignBench provides both the broken and target screenshots; grounding the *element diff* between them is more targeted than either full-image grounding.
- **Work:** New cache builder that runs OmniParser on both screenshots and computes which elements appeared/moved/disappeared; new runner to inject the diff block.
- **Cost:** ~2 hrs.
- **Paper value:** High. Novel grounding strategy not in the original proposal.

## Tier 2 — methodology ablations (for paper appendix)

### 6. Trimmed OmniParser variants
- Three variants to isolate which substrate matters:
  - **Elements-only** (drop OCR + relations + pixel stats)
  - **Relations-only** (drop elements + OCR + pixel stats)
  - **OCR-only** (drop elements + relations + pixel stats)
- **Why:** Explains *what about structural grounding* drives the 7B Angular win. The prompt block is dense; maybe only one substrate matters.
- **Work:** Modify the structural prompt_block formatter; rerun 3 times.
- **Cost:** ~3 hrs total (3 × ~1 hr per variant).

### 7. OmniParser v1 (keyword-match → single click point)
- **Why:** Already built in `grounding/omniparser.py` but never tested. Returns a single click point per issue via keyword matching on captions. Cheaper prompt than structural.
- **Work:** Write cache builder + runner.
- **Cost:** ~2 hrs.

### 8. OmniParser v2 (elements + captions only, no relations)
- **Why:** Already in `grounding/omniparser2.py`. Middle ground between v1 (single point) and structural (full block). Relations might be the load-bearing piece — v2 tests that.
- **Work:** Same as v1 — write cache builder + runner.
- **Cost:** ~2 hrs.

### 9. JEDI × mark mode
- **Why:** Completes the signal × mode matrix (8 missing cells).
- **Work:** Runner already supports `--mode mark`. Just flip the flag and re-eval.
- **Cost:** ~30 min gen + ~1 hr optional render.
- **Priority:** Low — mark+omni was already mostly null, mark+jedi likely similar.

### 10. Defect-type-conditioned grounding prompts
- **Why:** Vary the grounding block format per `issue` type. Example: `text_overlap` → emphasize OCR bboxes; `alignment` → emphasize aligned_* relations; `color_contrast` → emphasize pixel stats.
- **Work:** New prompt formatter dispatcher on issue type.
- **Cost:** ~3 hrs.

### 11. Baseline mark vs grounding both (cross-mode comparison)
- **Why:** Honest comparison of "our grounding vs. DesignBench's built-in red-bbox localization." Currently we compare grounding vs. no grounding in same mode; comparing across modes tests whether our grounding has value beyond free bboxes.
- **Work:** Analysis only — no new generation. Just pair mark-baseline samples against both-+omni samples.
- **Cost:** ~1 hr analysis.
- **Risk:** Story-weakening if we lose on some cells.

## Tier 3 — new dimensions (require full re-ablation)

### 12. 3B model scale
- **Why:** Strengthens "grounding helps small models more" claim. If 3B benefits even more than 7B, the size-dependent effect is a clean trend.
- **Cost:** ~4 hrs (full gen + eval + render).

### 13. Cross-model critic-repair (72B critic + 7B repair)
- **Why:** Tests whether decomposing "diagnosis" (strong model) + "fix" (cheap model) outperforms a single strong model. Practical deployment angle.
- **Work:** 3-stage runner: 72B produces `[ISSUES]`, 7B receives issues + produces `[CODE]`.
- **Cost:** ~4 hrs.

### 14. Same-model 3-stage critic-repair (Qwen critiques, then Qwen repairs)
- **Why:** Tests whether forcing the model to commit to a diagnosis before editing improves repair quality. Independent of model-size decomposition.
- **Cost:** ~3 hrs.

### 15. Fine-tuning the grounding model
- **Why:** Approach 2 from the original proposal. Fine-tune JEDI or OmniParser on UI-defect-aware grounding data. Bridges the gap between navigation-trained grounding and defect-detection.
- **Work:** Need defect grounding dataset. Neither exists publicly; would have to synthesize from DesignBench.
- **Cost:** multi-day.
- **Risk:** High overfitting risk (same benchmark for train + test).

### 16. Fine-tuning Qwen with grounding signal
- **Why:** Original Approach 2. Train Qwen to natively consume OmniParser/JEDI outputs rather than stuffing them in the prompt.
- **Work:** LoRA fine-tune on grounded-repair pairs.
- **Cost:** multi-day. Needs GPU + training data.

### 17. RAG approach
- **Why:** Approach 3 from the original proposal. Retrieve design guidelines (Material Design, etc.) at inference time to augment Qwen's repair context.
- **Work:** Build guideline index, add retrieval to the runner.
- **Cost:** ~1-2 days.

### 18. Second benchmark (UICrit / WebSight)
- **Why:** External validity. Only DesignBench tested so far. Generalization claim requires more than one benchmark.
- **Cost:** Full ablation re-run. Multi-day.

### 19. Set-of-marks prompting
- **Why:** Alternative to grounding. Overlay numbered visual markers on the screenshot as lightweight spatial anchors.
- **Cost:** ~2 hrs.

### 20. Visual-diff guidance
- **Why:** Fallback from original proposal. Render the broken output, compute pixel-level diffs against reference, feed diff regions to Qwen as hints. Different angle on the visual-to-code gap.
- **Cost:** ~3 hrs.

## Summary — what to run next (ranked)

| Rank | Experiment | Cost | Paper value |
|------|------------|------|-------------|
| 1 | Hybrid OmniParser + JEDI | ~1 hr | High |
| 2 | Anonymized JEDI | ~1 hr | High |
| 3 | Filtered JEDI cache | ~45 min | Medium |
| 4 | Mark-mode visual render | ~2 hrs | Medium |
| 5 | Reference-vs-broken diff | ~2 hrs | High |
| 6 | Trimmed OmniParser (3 variants) | ~3 hrs | Medium |
| 7 | 3B scale | ~4 hrs | Medium |
| 8 | Critic-repair (cross-model or same-model) | ~3-4 hrs | High |

Anything below this line is multi-day and probably not worth chasing unless pivoting to a paper submission.
