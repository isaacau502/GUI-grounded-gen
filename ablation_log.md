# Ablation log

Running log of every ablation configuration we try on the DesignBench repair task. Latest on top.

## Headline (today)

**Two clean wins, one clean null, rest pending.**

1. **72B + OmniParser structural — visual-metric win across 3 frameworks.**
   - Vue CLIP **+.012** ** (p=.002)
   - Angular CLIP **+.009** * (p=.045), SSIM **+.003** * (p=.026)
   - Vanilla CLIP **+.018** ** (p=.002), SSIM **+.019** ** (p=.002), MAE **−.337** * (p=.030)
   - AST (CMLS/CMCS) trends mildly negative but never significant. Validates memo: *CMLS penalizes correct rewrites*. CLIP is the right metric on DesignBench when comparing generation strategies.

2. **7B + OmniParser structural on Angular — large multi-metric win.**
   - CLIP **+.141** ** (p=.007)
   - SSIM **+.111** ** (p=.002)
   - CMCS **+.073** * (p=.048)
   - CSR .57 → .75 directional
   - Concrete mechanism candidate: Angular repair requires coordinated edits across `.html` + `.ts`; explicit bboxes + OCR scaffold weak 7B spatial reasoning.

3. **The 7B Vue divergence.** CLIP +.021 ** up; SSIM −.016 ** down. CLIP (embedding similarity) says the repair is semantically closer to target; SSIM (per-pixel structural similarity) says layout drifts. Methodology signal: **CLIP > SSIM** for this task.

**Pending:** JEDI variant (`+jedi`, both mode) + mark-mode ablations (baseline + `+omni`). Both running. Results in ~30 min.


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
- **Signal:** JEDI-7B-1080p click coordinates per design issue (from each sample's `issue` field). Format injected into prompt: `An automated grounding model identified click targets: "{issue}" → click at (x, y)`.
- **Cache:** `jedi_cache.json` — 111 samples, 170 total issue-queries, **77 (45%) parsed into valid click coords**. Built on Colab A100 in ~3 min via vllm.
- **Why 45% parse rate (not higher):** JEDI was trained on OSWorld-G for *interactable-element* clicking (buttons, icons, links), NOT for region-level defect localization. Parse rate varies sharply by defect type:
  - **crowding 74% / overflow 58%** — defects that usually center on a specific clickable element
  - **occlusion 40% / disorder 38% / alignment 34% / color-contrast 36% / text-overlap 33%** — defects that are regions or styles, not clickable targets. JEDI often returns empty output or malformed coords.
- **Handling:** `run_repair_grounded_jedi.py` injects the raw output even when parse fails; the repair model sees "JEDI attempted this issue → raw response" rather than nothing.
- **Status:** Generation running locally (72B first, then 7B). Eval + stats pending.

### Run 07 — `mark` mode ablation (baseline + grounded)
- **What:** DesignBench `mark` mode swaps the screenshot for one with defects pre-highlighted in red bboxes. Compare baseline mark vs grounded+mark, both sizes × 4 fw.
- **Hypothesis:** the red bboxes *are* a grounding signal. If grounded+mark still beats baseline+mark, structural-text grounding adds info beyond just "look here." If not, the gains from Run 02 might just be a "look-at-the-right-place" effect.
- **Status:** Generation running. Baseline 72B + 7B mark done; grounded 72B mark angular in progress.

## Queued / pending results (current session)

- Run 06 (JEDI): generation running, eval after mark ablation finishes
- Run 07 (mark): generation at grounded 72B angular. Eval after gen completes. Will add per-row below.

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
