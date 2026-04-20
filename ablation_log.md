# Ablation log

Running log of every ablation configuration we try on the DesignBench repair task. Latest on top.

## Headline (current state)

**Three clean wins, two nulls, one regression, rest in render queue.**

### Win 1 — 7B + OmniParser on Angular (biggest single cell)
- CLIP **+.141** ** (p=.007), SSIM **+.111** ** (p=.002), CMCS **+.073** * (p=.048)
- CSR .57 → .75 (directional +.18, 6 extra samples compile)
- Largest effect in the whole study.

### Win 2 — 7B + JEDI on Angular (AST-level beats OmniParser on same cell)
- CMLS **+.142** * (p=.022), CMCS **+.118** * (p=.019), **CodeScore +.201** ** (p=.007)
- Surpasses +omni on code metrics. CLIP pending render.

### Win 3 — 72B + OmniParser visual improvement, 3 of 4 frameworks
- Vue CLIP **+.012** ** (p=.002)
- Angular CLIP **+.009** * (p=.045), SSIM **+.003** * (p=.026)
- Vanilla CLIP **+.018** ** (p=.002), SSIM **+.019** ** (p=.002), MAE **−.337** * (p=.030)
- CMLS/CMCS trend mildly negative (not significant). *CMLS penalizes correct rewrites* hypothesis validated.

### Regression — 7B + JEDI on React
- CMLS **−.096** ** (p=.006), CMCS **−.085** ** (p=.002)
- JEDI's noisy alignment-defect coords mislead 7B on React. Only cell with a significant regression.

### Null — Mark mode + OmniParser
- Red bboxes alone (mark mode baseline) already capture most of the "look here" grounding benefit. Adding structural text on top is mostly redundant.
- Only significant effect: Vanilla 7B+omni (mark) CMLS **−.144** * (p=.032), CMCS **−.128** * (p=.038) — grounding *hurts* here.
- Across-framework note: mark mode itself boosts IssAcc for some cells (Vue 72B mark IssAcc .213 → .352 vs both mode).

### JEDI IssAcc caveat
- JEDI +24% to +47% IssAcc on every cell, all p<.001. **But the JEDI prompt literally names the defect type.** Treat as confounded by label leakage. Don't report on the poster as a clean win.

### Per-defect-type cross-framework slice (Run 08)
- Validates framework-level findings + adds within-defect texture.
- **7B + omni alignment (N=63):** CLIP **+.065** **, SSIM **+.039** ** — alignment benefits visually
- **7B + omni crowding (N=30):** IssAcc **+.196** **, CodeScore **+.078** *
- **7B + omni overflow (N=17):** SSIM **+.106** **
- **72B + omni alignment (N=68):** CLIP **+.007** ** rises while CMLS **−.055** *, CMCS **−.045** * drop — cleanest single illustration of the CMLS-vs-CLIP divergence (N=68, both tails significant).
- **72B + omni crowding (N=31):** CLIP **+.035** **
- **72B + omni overflow (N=19):** CLIP **+.064** **

### Pending
- JEDI visual-metric render (full CLIP/SSIM/MAE for all 8 JEDI cells) — in progress, ~2 hrs for angular, others fast.
- Per-defect refresh for JEDI once render done.


**Setup fixed across rows:** DesignBench repair, 111 samples (R=28, V=27, A=28, Vanilla=28), temp=0, seed=42, API via Dashscope international.

Column glossary:
- **Signal** = what grounding info (if any) we inject into the Qwen repair prompt
- **Mode** = DesignBench `--mode` (both = code + original screenshot; mark = code + screenshot with defects pre-highlighted in red bboxes; code / image = just that half)
- **Scope** = which (framework, model_size) cells ran
- **Metrics captured** = AST-only (CMLS/CMCS/IssAcc/CodeScore) or +visual (CLIP/MAE/SSIM) if PNGs rendered
- **Key finding** = 1-line significance-tested headline. `**` p<.01, `*` p<.05, `.` p<.10. All Wilcoxon signed-rank paired (two-sided). N=27–28.

---

## Runs completed

### Run 01 — OmniParser **structural** × `both` mode × 7B
- **Signal:** structural block (YOLO bboxes + Florence-2 captions + EasyOCR text + pairwise geometric relations + pixel stats)
- **Scope:** react, vue, angular, vanilla — full render pass complete
- **Finding (post-render, apples-to-apples with baseline methodology):**
  - **Angular: LARGE WIN**
    - CLIP **+.141** ** (p=.007) — visual match to target much better
    - SSIM **+.111** ** (p=.002)
    - CMCS +.073 * (p=.048)
    - CMLS +.090 . (p=.069) — marginal
    - CSR +.179 (McNemar p=.125) — directional big jump (.57 → .75), 6 extra samples compiled, only 1 regression
  - **Vue: CLIP/SSIM divergence finding**
    - CLIP **+.021** ** (p=.005) — semantic visual similarity up
    - SSIM **−.016** ** (p=.004) — pixel-structural similarity down
    - IssAcc +.062 . (p=.074), CMLS −.037 . (p=.079) — classic tradeoff
  - React, Vanilla: nothing significant
- **Commits:** `5ec2828` (harness), `eab17e8` (eval), `e2eb9f0` (stats), `3531c38` (render fill)
- **Cache:** `grounding_structural_cache.json` (111 entries, MPS ~15s/sample)

### Run 02 — OmniParser **structural** × `both` mode × 72B
- **Signal:** same as Run 01
- **Scope:** react, vue, angular, vanilla
- **Metrics captured:** AST-only first, then fully re-rendered → CLIP/SSIM/MAE/CSR added
- **Finding (after render pass):**
  - **Visual metrics significantly improve:** Vanilla CLIP +.018 ** (p=.002), SSIM +.019 ** (p=.002), MAE −.337 * (p=.030); Angular CLIP +.009 * (p=.045), SSIM +.003 * (p=.026); Vue CLIP +.012 ** (p=.002).
  - **AST metrics drop, but not significantly:** e.g., Vanilla CMLS −.088 (p=.149, CI [−.20, +.02] includes 0); Angular CMCS −.065 (p=.140).
  - **The CMLS-vs-CLIP divergence pattern directly validates the memo's prediction**: "CMLS/CMCS penalize correct rewrites." Grounding pushes the 72B model toward repairs that visually match the target even when the AST diverges from the reference code.
  - CSR unchanged (ceiling at .96–1.00 for all frameworks except 7B).
- **Commits:** `5ec2828` (harness), `eab17e8` (eval), `e2eb9f0` (stats)

---

### Run 05 — CLIP render pass (fill missing visual metrics)
- **What:** Re-ran DesignBench evaluator with full render on all 8 grounded cells (72B+omni + 7B+omni × 4 fw) so CLIP/SSIM/MAE/CSR metrics exist for every cell.
- **Result:** Reveal that 72B+omni *wins visually* on Vue (CLIP +.012 **), Angular (CLIP +.009 *, SSIM +.003 *), Vanilla (CLIP +.018 **, SSIM +.019 **, MAE −.337 *). Previously thought to be all noise — visual metrics matter. Added to Run 02 results.
- **Gotcha:** DesignBench evaluator zeros *all* metrics (including AST) when compile fails. Grounded 7B Angular went from compile-fail-rate 43% to 25% via grounding, so recomputed AST averages differ slightly from AST-only methodology. Apples-to-apples with baseline now.
- **Commit:** `3531c38`

### Run 06 — JEDI click-point grounding × `both` mode
- **Signal:** JEDI-7B-1080p click coordinates per design issue. Prompt injection format: `An automated grounding model identified click targets: "{issue}" → click at (x, y)`.
- **Cache:** `jedi_cache.json` — 111 samples, 170 total issue-queries, **77 (45%) parsed** into valid click coords. Built on Colab A100 in ~3 min via vllm.
- **Why 45%:** JEDI trained on OSWorld-G for interactable-element clicking, not region-level defect localization. Parse rate by defect: crowding 74% / overflow 58% / occlusion 40% / alignment 34% / color-contrast 36% / text-overlap 33%.
- **Handling:** runner injects raw output even when parse fails, so failed-parse defects still contribute prompt text.
- **Finding (AST-only pass; CLIP render in progress):**
  - **7B Angular: STRONG WIN.** CMLS **+.142** * (p=.022), CMCS **+.118** * (p=.019), CodeScore **+.201** ** (p=.007). Surpasses +omni on AST metrics for this cell (baseline CMLS .304, +omni .394, +jedi .446).
  - **7B React: REGRESSION.** CMLS **−.096** ** (p=.006), CMCS **−.085** ** (p=.002). JEDI's alignment-defect parse-failures produce noisy context that misleads 7B on React.
  - **7B Vue, 7B Vanilla:** AST metrics noise, but IssAcc jumps big (Vue +.469, Vanilla +.310, both p<.001). Caveat: label leakage (see below).
  - **72B all 4 frameworks:** AST metrics flat. IssAcc jumps +.24 to +.44 everywhere (p<.001). Almost entirely label leakage.
- **IssAcc leakage:** JEDI prompt spells out the defect type verbatim ("alignment" → click). DesignBench's IssAcc measures whether the model's response lists the correct defect names. We're giving it the answer. Treat IssAcc gains as not-clean.
- **CLIP/SSIM/MAE:** not in AST-only eval. Render in progress via `scripts/_render_jedi.sh`. Vanilla done for both sizes (72B vanilla/28 CLIP=0.87, compile=True), react + vue next, angular last (~2 hrs).
- **Commits:** `4039ee1` (cache builder refactor to accept pre-loaded LLM), `4532574` (log), `e2eb9f0` (stats harness).

### Run 07 — `mark` mode ablation (baseline + `+omni`)
- **What:** DesignBench `mark` mode swaps the screenshot for one with defects pre-highlighted in red bboxes. Ran baseline mark vs grounded+mark, both sizes × 4 fw.
- **Hypothesis:** red bboxes *are* a grounding signal. Question: does structural-text grounding add info beyond "look here"?
- **Answer: mostly no, and sometimes hurts.**
  - **7B + omni (mark):** Vue CMCS marginal regression (−.042, p=.086). **Vanilla significantly regresses: CMLS −.144 * (p=.032), CMCS −.128 * (p=.038).** Angular + React: noise.
  - **72B + omni (mark):** Vue CMCS marginal regression (−.027, p=.052). All other cells: noise. No wins anywhere.
- **Baseline mark vs baseline both (cross-mode, informal, not paired stat):**
  - Vue 72B IssAcc .213 → .352 — red bboxes alone are a big IssAcc boost for 72B Vue.
  - Angular 7B IssAcc .173 → .232 — smaller but directional.
  - Vanilla 72B IssAcc .369 → .318 — mark slightly *hurts* for 72B Vanilla.
- **Takeaway:** Mark is itself a grounding signal; for some cells (Vue 72B), it's a bigger lift than adding OmniParser text on top of both-mode. For Vanilla 7B specifically, structural text on top of red bboxes is counterproductive. Overall **mark + omni is not the right stack**; future work might target "mark + JEDI click refinement" or "mark-only with modality ablation."
- **Commit:** `3531c38` (harness already ran mark baseline previously); mark eval JSONs at `results/eval/{fw}_mark.json`.

### Run 08 — Per-defect-type slicing of all existing results
- **What:** Zero-compute analysis. For each sample, DesignBench configs have an `issue` field (str or list). Groupby defect type across all 4 frameworks, compute baseline vs variant deltas per (defect, metric), paired Wilcoxon + bootstrap.
- **N per defect (pooled across frameworks):** alignment 68, crowding 31, occlusion 30, overflow 19, color/contrast 11, disorder 8, text_overlap 3.
- **Finding — biggest wins are on the most common defect types, where N is high enough to detect:**
  - **7B + omni on alignment (N=63):** CLIP **+.065** **, SSIM **+.039** ** — alignment defects benefit from grounding visually.
  - **7B + omni on crowding (N=30):** IssAcc **+.196** **, CodeScore **+.078** * — helps both identify and fix.
  - **7B + omni on overflow (N=17):** SSIM **+.106** **, CLIP +.157 . (marginal).
  - **7B + omni on occlusion (N=29):** CLIP **+.095** *, SSIM **+.082** *.
  - **72B + omni on alignment (N=68):** CLIP **+.007** ** rises WHILE CMLS **−.055** *, CMCS **−.045** * drop. Cleanest demonstration of the CMLS-vs-CLIP divergence in the whole dataset.
  - **72B + omni on crowding (N=31):** CLIP **+.035** **.
  - **72B + omni on overflow (N=19):** CLIP **+.064** **.
  - **72B + omni on color/contrast (N=11):** SSIM **+.059** * (small N caveat).
- **Counter-intuitive: 7B + omni on disorder (N=8) trends negative on CMLS** (−.052, not sig, small N).
- **JEDI per-defect slice:** partial — only vanilla-only data at commit time (render mid-flight). Will refresh.
- **Commit:** `db1e320`. Output at `results/per_defect.md`. Reproducer: `python scripts/per_defect_analysis.py`.

### Run 06 — JEDI visual-metric render (partial, in progress)
- **What:** Re-run DesignBench evaluator with full render on all 8 JEDI cells so CLIP/SSIM/MAE/CSR fill in.
- **Progress (as of 11:33):**
  - ✅ 72B+jedi vanilla, react (28/28), vue (27/27)
  - ✅ 7B+jedi vanilla
  - 🔄 7B+jedi react mid-render (17/28, 11 compiled)
  - ⏳ 7B+jedi vue, then Angular × 2 (each ~70 min via per-sample `ng serve`)
- **Partial 72B+jedi numbers landed (raw means, no significance test yet):**

  | Framework | Metric | Baseline | +jedi | Δ (raw) |
  |-----------|--------|----------|-------|---------|
  | React | CMLS | .339 | .346 | +.007 |
  | React | CMCS | .230 | .245 | +.015 |
  | React | **CodeScore** | **.155** | **.218** | **+.063** |
  | React | CLIP | .771 | .771 | 0 |
  | Vue | CMLS | .213 | .207 | −.006 |
  | Vue | CLIP | .796 | .808 | +.012 |
  | Vanilla | CMLS | .532 | .524 | −.009 |
  | Vanilla | CLIP | .791 | .804 | +.013 |

- **Observation:** 72B+jedi React **CodeScore +.063** (raw) stands out — baseline 72B was already strong on React code-quality metric and JEDI pushes it higher without moving CMLS. Other 72B cells look flat-to-slightly-positive on CLIP; AST mostly flat.
- **Angular (the main cell of interest) still pending.** This is the biggest cell in the study — 7B baseline CSR only 57%, CMLS/CMCS lowest. AST-only already showed JEDI beats OmniParser there (CodeScore +.201 **). Expecting CLIP to track — if it does, gives us a clean double-win story.

### Run 09 — Poster-ready significance filter (α=0.05)
- **What:** `scripts/poster_stats.py` re-evaluates every (comparison × framework × metric) cell in the existing eval JSONs and emits only p<0.05 results, sorted by p-value. McNemar exact binomial for CSR (paired binary), Wilcoxon signed-rank for continuous. Direction-aware (MAE flipped so lower-is-better counts as gain).
- **Output:** `results/poster_stats.md`.
- **Current state (will refresh once JEDI angular render lands):**
  - **23 significant gains** across the study, top by effect magnitude:
    1. 7B+omni Angular CLIP +.141 ** (p=.007)
    2. 7B+omni Angular SSIM +.111 ** (p=.002)
    3. 7B+omni Angular CMCS +.073 * (p=.048)
    4. 7B+jedi React MAE −52.59 ** (p<.001) — artifact-suspect, CSR also dropped to .50
    5. 72B+jedi React IssAcc +.270 ** (leakage — see Run 06 caveat)
    6. 72B+jedi Vue IssAcc +.441 ** (leakage)
    7. 72B+omni Vue CLIP +.012 ** (p=.002)
    8. 72B+omni Vanilla CLIP +.018 **, SSIM +.019 **, MAE −.337 * (all p≤.030)
    9. 7B+omni Vue CLIP +.021 ** (p=.005)
    10. 72B+omni Angular CLIP +.009 * / SSIM +.003 *
  - **10 significant regressions**, top by p-value:
    1. 7B+jedi React CSR 1.00 → 0.50 **, CLIP −.309 **, SSIM −.304 **
    2. 7B+jedi React CMLS −.096 ** / CMCS −.084 **
    3. 7B+omni Vue SSIM −.016 ** (the divergence)
    4. 7B+omni mark Vanilla CMLS −.144 * / CMCS −.128 *
  - **10 marginals** (0.05 ≤ p < 0.10) — mostly Vue 7B+omni both tradeoffs (CMLS/CMCS down, IssAcc up) + Angular 7B+omni CMLS at the threshold.
- **Commit:** `6aa188a`.

### Run 10 — Ranked results overview for poster
- **What:** `results/results_overview.md`. Tier-ranked interpretation of every significant finding, each with a 1-line theorized mechanism (why it worked / failed).
- **Tier 1 (poster headline):**
  1. 7B + omni Angular hero cell
  2. 72B + omni cross-framework visual gains
  3. 7B + jedi React cautionary regression
  4. CLIP > SSIM methodology finding (7B Vue divergence)
  5. Per-defect alignment N=68 cleanest CLIP-vs-CMLS divergence
  6. JEDI IssAcc gains (caveated as label leakage)
- **Tier 2 (body text):** 72B+jedi visual gains (smaller than omni), 72B+jedi React CodeScore +.063 surprise, mark+omni null, mark mode itself is a grounding signal.
- **Tier 3 (only-if-asked):** JEDI parse-rate defect skew, per-defect clustering for 7B+omni on visually-complex defects.
- **Null results documented separately** (not "failures," just where grounding didn't move the needle).
- **Commit:** `6aa188a`.

## Queued / pending (this session)
- Run 06 extension completes: angular render for 7B+jedi and 72B+jedi (~2 hrs total).
  - When done: refresh Run 09 poster_stats, Run 10 overview, Run 08 per-defect, and this log.

## Planned / future (not queued this session)

| Signal | Hypothesis | Cost |
|--------|------------|------|
| Trimmed structural (elements-only vs relations-only vs ocr-only) | 72B's flat result may be attention-saturation on long grounding text; trimming isolates what's load-bearing | 3 runs × 111 samples each |
| **Reference-vs-broken diff** grounding | DesignBench gives both the broken + target screenshots; grounding on the *element diff* is more targeted than full image | One new cache builder + one run |
| Defect-type-conditioned block | Vary grounding text by `config["issue"]` (e.g. text_overlap → emphasize OCR; alignment → emphasize aligned_* relations) | New prompt formatter, one run |
| OmniParser v1 (keyword → single point) | Element list may overwhelm model; single-point attention may be cleaner for click-like defects | Wrapper exists, cache + runner script needed |
| OmniParser v2 (elements + captions only, no relations) | Same as trimmed-structural-elements-only | Wrapper exists |
| Hybrid OmniParser + JEDI | Orthogonal signals: OmniParser = element list, JEDI = prioritized "look here first" | Needs both caches |
| Per-defect-type slicing of existing results | May reveal grounding helps text_overlap/alignment/crowding and fails color_contrast | Zero compute; groupby eval JSONs |

---

## Methodology notes

- Significance testing: Wilcoxon signed-rank paired, two-sided. One-sided halves p where we have a preregistered directional hypothesis (e.g., grounding → improves IssAcc).
- N=27–28 per cell is small. Deltas under ~.04 are inside noise absent specific predictions.
- CMLS/CMCS are AST-similarity-to-reference metrics — they penalize correct rewrites that use different AST structure. CLIP (visual similarity to target) is the tiebreaker when CMLS drops + IssAcc rises.
- Rendered `.png` + `.html` are separate from generation output; the baseline eval runs these via react/vue/angular dev servers + selenium. Angular is ~2.5 min per sample (per-sample `ng serve`).
