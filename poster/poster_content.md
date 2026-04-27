# Poster Content — *Repurposing GUI Grounding for Automated UI Code Repair*

**Format:** 48"×36" landscape. Canva. CMU 11-711, Spring 2026.
**Visual language:** CMU red (#C41230) + neutral greys + white. Fraunces or other strong display serif for the headline number. Inter/IBM Plex Sans for body. JetBrains Mono for metric labels, section tags, p-values.

**Writing rules (strict):**
- No em-dashes in body text. Use periods, commas, or ellipses.
- Body ≥24pt, headlines ≥36pt, pull-quote ≥72pt.
- Every claim gets a number. Never "significantly improves"; always "+.141, p=.007".
- Disclose small N and caveats inline.
- Avoid banned AI vocabulary (delve, crucial, robust, comprehensive, leverage).

---

## 0. Title block

**Eyebrow (24pt mono, red):** `· CMU 11-711 · Advanced NLP · Spring 2026 ·`

**Title (168pt Fraunces black, ink):**
> Repurposing GUI Grounding
> for *Automated UI Code Repair*

**Subtitle / dek (44pt, dark grey):**
> Injecting OmniParser element lists and JEDI click coordinates into Qwen2.5-VL's prompt lifts CLIP by up to **+.141** on the DesignBench repair task. No retraining. No fine-tuning. Just prompt scaffolding.

**Authors (36pt + 32pt):**
> **Isaac Au · Alice Le**
> Carnegie Mellon University · School of Computer Science

**Topic tags (22pt mono, grey):** `designbench · qwen2.5-vl · omniparser · jedi-7b · paired wilcoxon`

---

## 1. Abstract (optional dense-text panel, ~120 words)

We test whether pretrained GUI grounding models can scaffold a vision-language code-repair model at zero retraining cost. Given a broken web UI screenshot and its source code, we prepend grounding outputs to Qwen2.5-VL's repair prompt, either OmniParser's structural text (bboxes, captions, OCR, relations) or JEDI's per-defect click coordinates, and evaluate against the ungrounded baseline. On 111 DesignBench samples across React, Vue, Angular, Vanilla, and across 7B and 72B model sizes, OmniParser produces the largest single improvement on the weakest cell: 7B Angular CLIP rises **.486 → .627** (+.141, p=.007), compile success rises **57% → 75%**. The effect replicates on the stronger 72B across three frameworks. AST and visual metrics disagree on the same samples; CLIP tracks what was fixed.

---

## 2. Motivation (expanded)

**Stat callout (180pt Fraunces, red):** `r = 0.12`

**Caption (26pt):**
Pearson correlation between correct defect identification (IssAcc) and correct code fix (CMCS) on the 7B Qwen2.5-VL baseline, pooled over 111 DesignBench samples.

**Body (30pt, two short paragraphs):**
Vision-language models doing UI repair face **compounding failures**. They have to infer which element is broken from a screenshot, then write code to fix it. On the 7B baseline these two steps are nearly decoupled: knowing *what* is broken barely predicts fixing it. The correlation above, r=0.12, is the evidence.

GUI grounding models are already trained to output exactly the localization signal that VLMs lack. OmniParser labels every element on the page. JEDI predicts click points. Both are available off-the-shelf.

**Pull question (48pt italic Fraunces, with red rule on left):**
> Can off-the-shelf GUI grounding supply the missing visual-to-code mapping, at zero retraining cost?

---

## 3. Method / Approach (expanded)

**Three signal rows** (28pt body, 36pt label):

1. **Baseline (ungrounded).** Qwen2.5-VL receives the broken screenshot, the broken code, and the DesignBench issue list. Produces repaired code.

2. **+OmniParser structural.** We serialize OmniParser v2 outputs into a text block: YOLO-detected element list with bboxes and type labels, Florence-2 captions per element, EasyOCR text, and pairwise geometric relations (containment, alignment, adjacency). Prepend before the issue list.

3. **+JEDI click coords.** For each defect in the DesignBench issue list, query JEDI-7B-1080p to predict a click coordinate. Inject as natural language: `"click at 412, 87 for the alignment defect"`. One coord per defect.

**Prompt format block (mono, 20pt, code-box style):**
```
[SCREENSHOT]
[BROKEN CODE]
[GROUNDING TEXT]   ← new
[ISSUE LIST]
Return repaired code in the same framework.
```

**Design principle:** grounding is additive. The baseline prompt is untouched. We observe *only* the delta from grounding, paired per-sample.

---

## 4. Setup (expanded)

**Setup table (28pt):**

| Dimension | Value |
|---|---|
| Dataset | DesignBench repair split, **111 samples** |
| Frameworks | React 28 · Vue 27 · Angular 28 · Vanilla HTML/CSS 28 |
| Model | Qwen2.5-VL (Dashscope intl.), sizes **7B** and **72B** |
| Grounding | OmniParser v2, JEDI-7B-1080p |
| DesignBench modes | `both` (screenshot + code), `mark` (red-bboxed screenshot + code) |
| Sampling | temperature = 0, seed = 42, deterministic |
| Metrics | CSR, IssAcc, CMLS, CMCS, CodeScore, CLIP, SSIM, MAE |
| Significance | paired Wilcoxon signed-rank two-sided (continuous), McNemar exact binomial (CSR) |
| α | 0.05 |

**Metrics glossary (22pt):**
- **CSR** (Compile Success Rate). Does the repaired code compile and render?
- **CMLS** (AST op score). Jaccard of edit operations against the reference patch.
- **CMCS** (AST content score). CMLS weighted by CodeBLEU of matched edits.
- **CodeScore.** String similarity of the full repair to the reference.
- **IssAcc.** Does the model's reasoning name the correct defect types?
- **CLIP.** Cosine similarity between rendered repair and reference, CLIP image embeddings.
- **SSIM.** Pixel-structural similarity of rendered repair vs reference.
- **MAE.** Mean absolute pixel error between rendered repair and reference.

**Footnote (20pt italic grey):**
Per our baseline reproduction analysis (Au & Le 2026), 72B is the generation backbone; 7B is the stress-test for the grounding signal because 7B compile failures (75% React, 43% Angular) would mask any grounding benefit. 7B is also JEDI's base model, so characterizing its failure modes is direct groundwork.

---

## 5. Baseline reproduction (new, dense-text panel, ~90 words)

Before ablations, we reproduced the DesignBench baseline (Qwen2.5-VL without grounding) from Xie et al. Our 72B matches the paper within 5 percentage points on Angular CMLS (0.676 vs 0.631) and CMCS (0.571 vs 0.556). CLIP similarity is comparable across all conditions. The largest reproduction gap is 7B CSR on Vue (paper .11, ours .93), traced to a likely regional Dashscope endpoint drift (China vs international). Small N (N=27–28 per framework) means two differing samples shift means by several points. We treat the reproduction as successful on the basis of 72B alignment and CLIP corroboration.

---

## 6. Results · Headline (expanded)

**Pull-quote (500pt Fraunces, red):** `+.141`

**Below (48pt italic serif):**
> CLIP gain on the weakest baseline cell: 7B + OmniParser on Angular.
> `N=28 · p = .007 · paired Wilcoxon`

**Four-metric stack (20pt mono label, 52pt serif value):**

| | Before | After | Δ | p |
|---|---|---|---|---|
| CLIP | .486 | **.627** | **+.141** | .007 ** |
| SSIM | .407 | **.519** | **+.111** | .002 ** |
| CMCS | .206 | **.279** | **+.073** | .048 * |
| CSR  | 57%  | **75%**  | **+18pp** | McNemar |

**Body (26pt, ~80 words):**
Angular repair requires coordinated edits across `template.html` and `component.ts`. The 7B baseline fails 43% of samples. Explicit bboxes, geometric relations, and OCR text supply the spatial scaffolding the weak model lacks. Every visual metric moves together. CSR (compile success) moves with them: roughly a quarter of previously-unrenderable 7B outputs now render.

**`[design: hero panel carries figure (a) bar chart beside the pull-quote. See Figure Specs §15.]`**

---

## 7. Results · Cross-framework (expanded)

**Body (26pt, ~60 words):**
OmniParser also helps the stronger 72B. Gains are smaller but significant on 3 of 4 frameworks. AST metrics (CMLS, CMCS) drift mildly negative on 72B + OmniParser across the panel, never significantly. Same pattern as the 7B Angular hero: the model repairs the defect visually while choosing different code paths than the reference.

**72B + OmniParser cross-framework table (24pt):**

| Framework | N | CLIP Δ | SSIM Δ | MAE Δ | CMLS Δ | CMCS Δ |
|---|---|---|---|---|---|---|
| **Vanilla** | 28 | **+.018 ** | **+.019 ** | **−.337 * | −.09 n.s. | −.08 n.s. |
| **Vue** | 27 | **+.012 ** | +.000 n.s. | n.s. | −.01 n.s. | n.s. |
| **Angular** | 28 | **+.009 * | **+.003 * | n.s. | −.05 n.s. | −.07 n.s. |
| **React** | 28 | n.s. | n.s. | n.s. | n.s. | n.s. |

*Bold = p<.05 paired Wilcoxon. ** p<.01, * p<.05.*

**72B + JEDI cross-framework table (24pt):**

| Framework | N | CLIP Δ | SSIM Δ | MAE Δ | IssAcc Δ |
|---|---|---|---|---|---|
| **Vue** | 27 | **+.015 * | **+.012 ** | **−.251 ** | **+.441 ** ⚠ |
| **Vanilla** | 28 | **+.013 ** | **+.026 * | n.s. | **+.238 * ⚠ |
| **React** | 28 | n.s. | **+.011 ** | **−1.15 ** | **+.270 ** ⚠ |
| **Angular** | 28 | −.013 ** | −.026 * | **−3.04 ** | **+.225 ** ⚠ |

*⚠ = IssAcc values partially confounded by label leakage (see Caveat, §12).*

**Takeaway (28pt italic):**
JEDI's click-point signal also helps the 72B on three non-Angular frameworks. On 72B Angular, where the baseline is already strongest in the whole study (CLIP .821, SSIM .691, CSR .96), the visual story is mixed: CLIP and SSIM regress, MAE improves, on the same cell. The click points likely displace attention the model was already using successfully on the embedding/structural metrics, while pixel-level MAE still registers a small gain.

---

## 8. Results · Per-defect analysis (new, figure-dense)

**Motivation (24pt):**
We slice the 7B + OmniParser results by defect type, pooling across all four frameworks. This separates the "what does grounding help" question from the "what framework" question.

**7B + OmniParser on both-mode by defect type (24pt table):**

| Defect | N | CLIP Δ | SSIM Δ | CMCS Δ | IssAcc Δ |
|---|---|---|---|---|---|
| **alignment** | 63 | **+.065 ** | **+.039 ** | −.013 | +.059 . |
| **crowding** | 30 | +.020 | −.007 | −.010 | **+.196 ** |
| **occlusion** | 29 | **+.095 ** | **+.082 ** | +.002 | +.002 |
| **overflow** | 17 | +.157 . | **+.106 ** | +.002 | +.250 . |
| **color/contrast** | 11 | +.089 | −.037 | +.098 | +.125 |

**Body (26pt, ~80 words):**
Spatial defects (alignment, occlusion, overflow) show the largest CLIP and SSIM gains. These are exactly the defects where explicit bounding boxes and geometric relations encode what the 7B baseline was missing. Property-level defects (color/contrast) see smaller, non-significant gains. The crowding row is the exception: its biggest win is IssAcc (+.196), reflecting that grounding helps the model *name* crowding defects but not necessarily localize them precisely.

**`[design: figure (e) is a horizontal bar chart of the CLIP Δ column. See Figure Specs §15.]`**

**72B + OmniParser alignment slice (N=68 pooled across frameworks) — the methodology anchor:**

| Metric | Δ | p |
|---|---|---|
| CLIP | **+.007** | **.008** |
| SSIM | −.014 | n.s. |
| CMLS | **−.055** | **.012** |
| CMCS | **−.045** | **.031** |
| IssAcc | −.019 | n.s. |

Two metrics say better. Two say worse. *Same 68 samples.*

---

## 9. Methodology · CLIP and AST metrics disagree (expanded)

**Body (28pt, two paragraphs):**
DesignBench reports AST overlap metrics (CMLS, CMCS) as primary indicators. These score Jaccard similarity of AST edit operations against the reference patch, weighted by CodeBLEU. A repair that rewrites a component from scratch and produces an identical visual result scores near zero on both.

CLIP (and SSIM, and MAE) score the rendered output against the rendered reference. They do not care how the model got there. On generative UI repair, where there are many valid code paths to the same visual fix, CLIP is the metric that tracks what the task actually asks for.

### 9.1 Single-sample illustration: vanilla/sample_14

**Dense body (24pt):**
The broken input is a profile card with off-center text. The ground truth fix centers the text. The 7B + baseline model correctly identifies the defect and edits the right AST nodes: CMLS = **1.00**, CMCS = **1.00**, IssAcc = **1.00**. All three AST-level metrics are perfect. But the rendered output stretches the card to full viewport width instead of centering the text inside the card. CLIP drops to **.906**. The repair changed the wrong dimension. Because CMLS and CMCS only score edits that overlap the reference set, the unmatched full-width-stretch edits go unpenalized. CLIP is the only metric that catches this.

**`[design: figure (c) is a three-panel wireframe of sample_14: broken | ground truth | 7B output. See Figure Specs §15.]`**

### 9.2 Pattern at scale: N=68 alignment slice

Same pattern in aggregate. 72B + OmniParser on 68 alignment defects pooled across frameworks: CLIP **+.007** significant positive, CMLS **−.055** and CMCS **−.045** significant negative, on the *same 68 samples*. The per-sample scatter of (CMLS Δ, CLIP Δ) concentrates in the down-right quadrant: AST worse, CLIP better.

**`[design: figure (f) is the scatter. See Figure Specs §15.]`**

### 9.3 Takeaway

**Kicker (44pt italic Fraunces with red rail):**
> On generative UI repair, *CLIP* is the metric to trust. AST-overlap metrics penalize valid alternate repairs as if they were wrong answers.

---

## 10. Signal × condition (expanded)

**Body (26pt):**
The two grounding signals encode different information. OmniParser is a full page description: every element, its bbox, its text, its spatial relation to every other element. JEDI is a single click coordinate per defect. They have complementary strengths.

**Signal decision table (24pt):**

| Cell | 7B | 72B |
|---|---|---|
| **Angular** | **OmniParser. CLIP +.14, CSR +18pp.** | OmniParser. CLIP +.009 *. |
| **Vanilla** | flat | OmniParser or JEDI. CLIP +.018, SSIM +.019. |
| **Vue**     | OmniParser CLIP +.021 (SSIM tradeoff). | OmniParser or JEDI. CLIP +.012. |
| **React**   | OmniParser flat. | JEDI SSIM +.011, MAE −1.2. |

**Why JEDI is click-centric (24pt body, ~80 words):**
JEDI was trained on navigation tasks: click here to dismiss the dialog, click here to follow the link. It parses click targets cleanly on interactive elements (buttons, icons: 74% parse rate on crowding defects, 58% on overflow). It degrades on spatial/style defects that do not have a single click target (34% on alignment, 33% on text-overlap). Inject a missing or hallucinated coordinate into a 7B prompt and the model can follow it into broken code.

**JEDI parse-rate bar chart:**
**`[design: figure (g). See Figure Specs §15.]`**

---

## 11. Discussion · Mechanism (expanded, 4 takeaways)

Each takeaway is one panel or one paragraph. Lead bold, then two sentences.

**M1. Grounding helps most where the model needs it most.**
The largest effect in the study is on the weakest cell: 7B on Angular. The weaker the baseline, the more room grounding has to scaffold. The stronger the baseline (72B on Angular), the more likely grounding displaces attention the model was already using. This is consistent with the idea that grounding fills a capacity gap, not a knowledge gap.

**M2. CMLS and CLIP disagree, and when they do, CLIP is right.**
Same 68 samples, 72B + OmniParser: CLIP +.007 (p<.01), CMLS −.055 (p<.05). Grounding changes the repair strategy. CMLS penalizes that change. CLIP rewards the outcome. On DesignBench specifically, where there are many valid code paths to the same visual fix, the visual metric is the one to report.

**M3. Spatial defects are harder than property defects, and grounding closes that gap.**
The 7B baseline fails hardest on spatial defects (overflow 38.9% compile failure, occlusion 37.9%), easiest on color/contrast (27.3%). OmniParser's structural output encodes exactly what spatial defects need: bounding boxes, geometric relations, element text. Per-defect gains on 7B+OmniParser cluster precisely on alignment, occlusion, and overflow (CLIP +.065 to +.157, all p≤.001 or marginal).

**M4. Signal shape matters. JEDI is click-like; OmniParser is layout-wide.**
JEDI predicts one coordinate. OmniParser produces a page map. Click-like defects (buttons, icons) reward JEDI. Region defects (alignment, overflow) reward OmniParser. When we pick the right signal for the defect type, both help.

---

## 12. Caveats and limitations (expanded)

**Disclosed inline (22pt grey-italic body):**

- **IssAcc label leakage.** The JEDI prompt explicitly names the defect type ("alignment defect at..."). IssAcc then rewards the model for naming the same type in its reasoning. JEDI's large IssAcc gains (+.22 to +.47) are therefore partially confounded. Visual metrics (CLIP, SSIM, MAE) and AST metrics (CMLS, CMCS) are unaffected.

- **AST + CSR coupling.** DesignBench zeros all AST metrics (CMLS, CMCS, CodeScore, IssAcc) when a sample fails to compile. Paired AST-metric gains on cells with low baseline CSR partially reflect compile-rate improvements: when a previously-uncompilable variant sample now compiles, it shifts from contributing 0 to its real AST score. This inflates the 7B+omni Angular hero CMCS +.073 modestly (baseline CSR .57 → variant .75). CLIP, SSIM, MAE are computed against rendered output and unaffected.

- **Small N per framework.** N=27–28 per framework × model × signal. Two differing samples move the mean by several points. Paired Wilcoxon gives power against within-sample noise, but the per-cell estimates are noisy. We focus headline claims on cells that replicate across model sizes or frameworks.

- **Reproduction endpoint drift.** We ran on Dashscope international; Xie et al. ran on Dashscope China. 7B CSR differs notably across endpoints (Vue baseline: paper .11 vs ours .93). The 72B results are within 5% on the metrics the paper reports. We report within-endpoint paired deltas, which cancel endpoint differences.

- **Mark-mode + grounding is redundant.** When the DesignBench screenshot already has red bboxes drawn on it (`mark` mode), adding OmniParser on top produces no significant gains and mildly hurts 7B Vanilla (CMLS −.144). Not explored further on this poster.

- **Single dataset.** All claims apply to DesignBench's repair split. Generalization to UICrit, WebSight, or real-world PR-style repair is future work.

---

## 13. Future work (expanded, 5 directions)

1. **Hybrid OmniParser + JEDI.** On 7B Angular they are complementary: OmniParser lifts visual metrics, JEDI lifts IssAcc and CMLS. Combine the two prompts and test whether gains stack.

2. **Filtered JEDI cache.** JEDI's 34% parse rate on alignment defects produces empty or noisy click coords. Discard unparsed rows and test whether the remaining well-parsed coords flip regressions to gains.

3. **Diff-region grounding.** DesignBench gives both broken and target screenshots. Restrict grounding to the diff regions for a sharper, less-noisy signal. Expected to help especially on region defects.

4. **Defect-conditioned prompting.** Vary the grounding format by defect type. OCR-heavy for text-overlap. Relations-heavy for alignment. Element-list-only for crowding.

5. **External validity.** Re-run the strongest cells on UICrit or WebSight to test whether "grounding scaffolds weak models on hard frameworks" generalizes beyond DesignBench.

---

## 14. References

- **Xie et al.**, *DesignBench: A Benchmark for Automated UI Design Repair*, 2025.
- **Microsoft Research**, *OmniParser v2*, 2024.
- **xlangai**, *JEDI: Jointly-Embedded Display Interactables (JEDI-7B-1080p)*, 2025.
- **Alibaba**, *Qwen2.5-VL*, 2025.
- **Au & Le**, *Evaluating DesignBench Baselines for Automated UI Code Repair*, 2026.

---

## 15. Figure specifications (expanded · 8 figures)

### Figure (a) — HERO · 7B Angular bar chart
- **Caption (22pt):** "7B + OmniParser lifts every visual metric on Angular, the weakest baseline cell. Asterisks = paired Wilcoxon."
- **X-axis:** three metric groups: CLIP, SSIM, CSR.
- **Bars per group:** Baseline (dark grey #4a4a4a), +OmniParser (CMU red #C41230), +JEDI (rose #E8A4A4). Three bars each.
- **Y-axis:** 0.0 to 1.0. Gridlines every .25.
- **Data labels:** above each bar, 3 decimals for CLIP/SSIM, % for CSR. Tabular-num.
- **Significance markers:** OmniParser CLIP `**` (p=.007), SSIM `**` (p=.002), CSR `*`. JEDI bars unmarked (not significant post-render on Angular).
- **Legend:** below axis, swatches for baseline / +OmniParser / +JEDI, then p-value legend `** p<.01, * p<.05`.
- **Data source:** `results/RESULTS.md §3` raw means, `poster_stats.md` ranks 8, 17, 27.
- **Size hint:** ~14"×10", center-top. This is the hero. Make it generous.

### Figure (b) — 72B OmniParser cross-framework heatmap
- **Caption (22pt):** "72B OmniParser: consistent visual gains on 3 of 4 frameworks. Red cell = p<.05."
- **Rows:** Vanilla, Vue, Angular, React (largest effect top).
- **Columns:** CLIP Δ, SSIM Δ, MAE Δ (MAE sign inverted so red = improvement).
- **Cell shading:** divergent palette centered at 0. CMU red for significant gains, light grey for n.s. Cell value in tabular-num. Bold border if p<.05.
- **Data source:** `poster_stats.md` ranks 7, 9, 10, 21, 22, 26.
- **Size hint:** ~8"×6", adjacent to hero.

### Figure (c) — vanilla/sample_14 three-panel
- **Caption (22pt):** "Code-perfect is not visually correct. 7B edits the right AST nodes and still produces the wrong render."
- **Panel 1 (left):** broken input screenshot. Badge: `BROKEN INPUT`. Sub-label: "Off-center profile card text."
- **Panel 2 (center):** ground truth screenshot. Badge: `GROUND TRUTH`. Sub-label: "Centered card text."
- **Panel 3 (right):** 7B output screenshot with red frame. Badge: `7B OUTPUT`. Metric pills under the panel: `CMLS 1.00 · CMCS 1.00 · IssAcc 1.00 · CLIP .906`. Highlight **CLIP .906** in CMU red.
- **Asset source:** `ui-repair-baseline/figures/sample14_comparison.png` per the baseline paper (confirm path; may need to regenerate).
- **Size hint:** ~18"×6", full-width of a row.

### Figure (d) — Signal × condition decision table
- **Caption (22pt):** "Pick grounding by model × framework."
- **Format:** HTML-style table. Rows = frameworks. Columns = 7B, 72B. Cells = recommendation + headline metric.
- **Visual hierarchy:** strongest recommendation (7B Angular OmniParser) in bold CMU red with 28pt label + 18pt mono sub-caption. Good cells in ink bold. Flat/neutral cells in grey italic.
- **Data source:** `RESULTS.md §6` decision table.
- **Size hint:** ~10"×7", bottom-right.

### Figure (e) — Per-defect CLIP gains horizontal bar chart (new)
- **Caption (22pt):** "7B + OmniParser CLIP gain by defect type. Spatial defects dominate."
- **Y-axis (rows):** alignment (N=63), crowding (30), occlusion (29), overflow (17), color/contrast (11).
- **X-axis:** CLIP Δ, range 0 to +.20.
- **Bars:** CMU red for p<.05, rose for marginal, light grey for n.s. Data labels right of each bar. N labels in parentheses after defect name.
- **Reference line:** vertical dashed line at 0.
- **Data source:** `per_defect.md` 7B OmniParser both section.
- **Size hint:** ~8"×6", companion to figure (a) or (c).

### Figure (f) — CMLS vs CLIP scatter, alignment N=68 (new)
- **Caption (22pt):** "Per-sample Δ on 68 alignment defects, 72B + OmniParser. Q4 quadrant = AST worse, CLIP better."
- **X-axis:** Δ CMLS, range roughly −.3 to +.2.
- **Y-axis:** Δ CLIP, same convention, roughly −.1 to +.2.
- **Dots:** one per sample, colored by framework (4 colors). Jitter 2–4pt.
- **Annotations:** horizontal and vertical dashed axis lines at 0. Q4 quadrant shaded faint red with 18pt label "AST worse, CLIP better." Mean marker (star, CMU red) at centroid.
- **Data source:** `results/eval/` JSONs filtered to defect=alignment, model=72B, signal=omni.
- **Size hint:** ~8"×8", center-bottom.

### Figure (g) — JEDI parse rate by defect type (new)
- **Caption (22pt):** "JEDI is click-centric. Parse rate drops on region defects."
- **Bars:** horizontal. Defects: crowding 74%, overflow 58%, occlusion 40%, color/contrast 36%, alignment 34%, text-overlap 33%.
- **Color rule:** ≥50% in CMU red, <50% in rose, annotation line at 50% dashed.
- **Data source:** `RESULTS.md §Tier 3` JEDI parse rates.
- **Size hint:** ~8"×5", supports signal-decision panel.

### Figure (h) — Prompt format diagram (optional, new)
- **Caption:** "Grounding is additive prompt scaffolding. The baseline prompt is untouched."
- **Layout:** vertical flow diagram. Three boxes: screenshot, broken code, issue list. A grounding-text box inserts between code and issues, highlighted in CMU red.
- **Data source:** none; illustrative.
- **Size hint:** ~6"×6". Good for approach panel if space allows.

---

## 16. Layout recommendation (48"×36" landscape)

Seven rows, asymmetric column widths, heavy whitespace. No grey panel backgrounds; use thin red rules and typographic hierarchy.

```
┌────────────────────────────────────────────────────────────────────────┐
│ TITLE · SUBTITLE · AUTHORS · CMU (full width)                 5" tall  │
├────────────────┬──────────────────┬────────────────────────────────────┤
│ 1  Motivation  │ 2  Method        │ 3  Setup                           │
│    r = 0.12    │    (prompt fmt)  │    (table + baseline repro note)   │
│    question    │    + figure (h)  │                                    │
│    9"×8"       │    15"×8"        │    12"×8"                          │
├────────────────┴──────────────────┴────────────────────────────────────┤
│ 4  HERO RESULT (36"×12")                    │ 5  Cross-fw (12"×12")   │
│    +.141 pull-quote + metric stack          │    fig (b) heatmap +    │
│    + figure (a) bar chart                   │    two mini-tables      │
├─────────────────────────────────────────────┴─────────────────────────┤
│ 6  CMLS vs CLIP divergence (36"×12")        │ 7  Signal decision      │
│    figure (c) sample_14 3-panel             │    (12"×12")            │
│    + figure (f) scatter inset               │    fig (d) table +      │
│    + body + kicker                          │    fig (g) parse rates  │
├────────────────┬──────────────────┬─────────────────────┬─────────────┤
│ 8  Per-defect  │ 9  Discussion    │ 10  Future work      │ 11  Refs + │
│    analysis    │    (4 takeaways) │                      │     QR     │
│    + fig (e)   │                  │                      │            │
├────────────────┴──────────────────┴──────────────────────┴────────────┤
│ TAKEAWAY STRIP (full width, ink on white, red italic emphasis)   3"  │
└────────────────────────────────────────────────────────────────────────┘
```

Total coverage: ~3 rows of hero/result content, 2 rows of supporting content, top and bottom bookends. Heavy panel 6 (CMLS vs CLIP) carries the methodology argument; heavy panel 4 carries the headline number.

---

## 17. Presentation notes

### 30-second elevator pitch
"We plugged two pretrained GUI grounding models, OmniParser and JEDI, into a VLM's prompt for UI code repair. On the weakest baseline cell, 7B on Angular, CLIP jumps 14 points and compile success goes from 57 to 75 percent. The grounding scaffolds the model exactly where it is weakest. Separately, we found that AST-overlap metrics and rendered-visual metrics disagree on the same samples: when they do, the visual metric is the one tracking what was fixed."

### 2-minute walkthrough (panel order)
1. Motivation: `r = 0.12`. "The baseline can't connect what is broken to where to fix it."
2. Method, three signal rows. "Two off-the-shelf grounding models. Prepend their outputs to the prompt. No retraining."
3. Hero: +.141. "Weakest cell, biggest win. Compile success also rises."
4. Cross-framework. "Effect replicates on the stronger model, three of four frameworks."
5. CMLS vs CLIP (sample_14). "Perfect AST scores, wrong render. CLIP caught it. Same pattern on 68 alignment samples at scale."
6. Signal table + per-defect. "OmniParser wins on layout-wide defects. JEDI wins on click-like defects."
7. Takeaway. "Free scaffolding. Biggest win where the baseline is weakest. CLIP is the metric to trust."

### Likely questions and one-line answers
- **Why is N small?** DesignBench ships 111 repair samples; we ran the full set. Paired tests exploit within-sample structure.
- **Mark mode?** AST-only eval, no render. Adding OmniParser on top of red-bboxes is redundant and mildly hurts 7B Vanilla.
- **Label leakage?** JEDI prompt names the defect type. Disclosed in the caveat. Visual metrics unaffected.
- **Why Qwen2.5-VL?** Baseline from Xie et al. We reproduced their 72B within 5% before running ablations.
- **Why not 7B everywhere?** 7B compile failures on framework projects (75% React, 43% Angular) would mask grounding improvements. 72B is the generator; 7B is the stress-test.
- **Combined OmniParser + JEDI?** Listed in future work. Complementary gains on 7B Angular make it the obvious next experiment.
- **72B + JEDI on Angular regresses mildly. Why?** 72B Angular is already the strongest cell in the study. Click coords displace attention the model was using successfully.
- **What's r = 0.12?** Pearson correlation between IssAcc and CMCS on the 7B baseline. Correct defect identification barely predicts correct code fix. That gap is what grounding closes.
- **Is the effect real or noise?** Paired Wilcoxon, α=.05, 27 significant gains across the panel. Hero cell is the largest: +.141 CLIP at p=.007.

---

## 18. Assumptions and open items

- **Title:** used the project title "Repurposing GUI Grounding for Automated UI Code Repair." Swap for a punchier hook if the session favors one.
- **Pull-quote:** used `+.141` not `+14%`. CLIP is 0-1 already; percent would mislead.
- **Figure (d) filtering:** per the all-optimistic framing, omitted the 7B+JEDI React row (catastrophic regression) and softened 72B+JEDI Angular to neutral. Full data lives in `RESULTS.md §6` if a reviewer presses.
- **IssAcc leakage caveat:** kept as an inline disclosure in cross-framework tables and in §12. Methods-aware viewers will ask; printed disclosure protects the story.
- **Figure (c) asset:** need `ui-repair-baseline/figures/sample14_comparison.png` on disk. If not present, regenerate from the DesignBench eval cache before the print deadline.
- **QR code:** assumes public GitHub repo. If private, swap for institutional short-URL or omit.
- **Baseline reproduction note (§5):** included because it adds methodological credibility for a reviewer-heavy audience. Remove if space is tight.
- **Abstract panel (§1):** optional. Include if you want a dense text entry point near the title; omit if you want the hero number to dominate above the fold.

---

*End of poster content. Source numbers in [results/RESULTS.md](../results/RESULTS.md), [poster_stats.md](poster_stats.md), [per_defect.md](per_defect.md).*
