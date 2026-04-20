# Ablation log

Running log of every ablation configuration we try on the DesignBench repair task. Latest on top.

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
- **Scope:** react, vue, angular, vanilla
- **Metrics captured:** Full metrics after render pass (AST + CLIP/SSIM/MAE/CSR). Note: DesignBench zeros *all* metrics on compile-fail samples, so AST numbers post-render are lower than AST-only estimates. This is the apples-to-apples baseline methodology.
- **Finding (post-render, apples-to-apples):**
  - **Angular: LARGE WIN across multiple axes**
    - CLIP +.141 ** (p=.007) — much better visual match to target
    - SSIM +.111 ** (p=.002)
    - CMCS +.073 * (p=.048)
    - CMLS +.090 . (p=.069) — marginal
    - CSR +.179 (McNemar p=.125) — directional big jump (.57 → .75) but not significant at this N because only 7 discordant pairs
  - Vue: still marginal tradeoff (N=28 didn't move much) — IssAcc +.062 (p=.074), CMLS −.037 (p=.079)
  - Vanilla: nothing significant
  - React: render data N=7 (many samples failed compile for 7B+omni); held for re-render
- **Commits:** `5ec2828` (harness), `eab17e8` (eval), `e2eb9f0` (stats)
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

## Planned / queued (in this session)

| # | Signal | Mode | Scope | Status |
|---|--------|------|-------|--------|
| 03 | none (baseline) | mark | 7B + 72B × 4 fw | Queued — no existing baseline mark run to compare against |
| 04 | structural omni | mark | 7B + 72B × 4 fw | Queued — compares to #03 |
| 05 | none (baseline) | both | (re-eval with render) | Fill missing CLIP for 72B angular/vanilla + all 7B+omni cells |
| 06 | JEDI click-points | both | 7B + 72B × 4 fw | Blocked on Colab GPU (vllm) |

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
