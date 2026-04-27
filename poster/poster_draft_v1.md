# Poster draft v1 — GUI-grounded UI code repair

**Defaults assumed** (override any you want):
- 48"×36" landscape, PowerPoint
- Audience: CMU 11-711 poster session (mixed NLP/ML grad)
- Hero figure: 7B Angular bar chart (CLIP / SSIM / CSR: baseline vs +omni vs +jedi)
- Secondary figure: CMLS-vs-CLIP scatter on alignment N=68
- Include the 7B+JEDI React regression as a cautionary panel
- Exclude mark-mode null (optional)
- Colors: CMU red (#C41230) + neutral grays
- Authors: Isaac Au, Alice Le (CMU 11-711, Spring 2026)

---

## Title
**Repurposing GUI Grounding for Automated UI Code Repair**
*Small models benefit more, and visual metrics tell a different story than AST*

[design: 72pt title, 32pt subtitle, CMU red accent on "GUI Grounding"]

---

## Panel 1 — Motivation
**The question.**

Vision-language models now produce web UI code from a screenshot, but they struggle to *repair* broken pages. The hard part is localization: "which element is broken?" isn't always obvious from pixels, and the model silently guesses.

GUI-grounding models (OmniParser, JEDI) were trained to localize exactly this. Can we pipe their outputs into the repair model's prompt for free improvement?

[design: 24pt body, narrow column, icon of a broken UI + arrow]

---

## Panel 2 — Approach
**Two grounding signals, one repair model.**

- **OmniParser v2** → element bboxes, captions, OCR text, and geometric relations injected as a text block into the prompt.
- **JEDI click-points** → per-defect `(x, y)` coordinates from JEDI-7B, injected as "click at X, Y" natural language.
- Both compared to the ungrounded Qwen2.5-VL baseline across **two model sizes** (7B, 72B) and **four web frameworks** (React, Vue, Angular, Vanilla).

[design: three-panel icon strip. One per bullet.]

---

## Panel 3 — Setup
**DesignBench repair × 111 samples × 2 sizes × 3 signals.**

- Models: Qwen2.5-VL-{7B, 72B} via Dashscope
- Samples: 111 (R=28 / V=27 / A=28 / Vanilla=28), `both` mode (code + screenshot)
- Metrics: CMLS, CMCS, CodeScore, IssAcc (code); CLIP, SSIM, MAE (visual); CSR (compile rate)
- Significance: paired Wilcoxon signed-rank (continuous), McNemar exact binomial (CSR), α = 0.05

[design: small table, dense]

---

## Panel 4 — HERO RESULT
**Qwen2.5-VL-7B × Angular × OmniParser:**

### **CLIP +29%** relative (0.49 → 0.63, p=.007)
### **SSIM +27%** relative (0.41 → 0.52, p=.002)
### **Compile rate 57% → 75%**

[design: pull-quote panel. 72pt numbers in CMU red. This is the visual anchor.]

### Figure 1: 7B Angular bar chart
Three grouped bars (baseline / +omni / +jedi), four metrics (CLIP, SSIM, CMCS, CSR).

*Caption:* "Structural GUI grounding closes half the 7B → 72B Angular gap on visual metrics."

*Data source:* `results/eval/angular_both.json` + `scripts/poster_stats.py`
*Style:* grouped bar chart, CMU red for +omni, slate grey for +jedi, neutral beige for baseline.
*Size hint:* full 2-column width, ~12" × 6".

---

## Panel 5 — Cross-framework
**72B also benefits — on a different axis.**

Structural grounding produces small but consistent **visual-metric** gains on Vue, Angular, Vanilla (all p ≤ .045). AST metrics (CMLS, CMCS) trend mildly negative but never significant.

| Framework | CLIP Δ | SSIM Δ | MAE Δ |
|-----------|--------|--------|-------|
| Vue | **+.012 ** | — | — |
| Angular | **+.009 *** | **+.003 *** | — |
| Vanilla | **+.018 ** | **+.019 ** | **−.337 *** |
| React | +.006 | — | — |

*Why AST ↓ while visual ↑:* grounding pushes the 72B model toward repairs that *visually match* the target through different code paths than the reference. CMLS penalizes creativity. **CLIP is the right DesignBench metric.**

[design: tabular + asterisk bracket + 1-line highlight under.]

---

## Panel 6 — Methodology finding
**CLIP and SSIM can disagree.** On 7B Vue with either grounding:
- CLIP **+.021 ** (up)
- SSIM **−.016 ** (down)

CLIP rewards semantic similarity to the target. SSIM rewards pixel preservation. Grounding often re-lays-out the page *correctly* — fix is right, pixels shifted.

### Figure 2: alignment slice divergence (N=68 pooled)
Scatter: CMLS Δ (x-axis) vs CLIP Δ (y-axis), one point per sample, color by framework.

*Caption:* "Same 68 alignment samples: CMLS drops (p=.03), CLIP rises (p=.007). Visual-metric-based evaluation matters."

*Data source:* `results/eval/*_both.json`, filter by `issue == "alignment"`, compute per-sample Δ for 72B + omni.
*Style:* scatter, quadrant lines at 0,0, different color per framework, regression line.
*Size hint:* 1-column width, ~6" × 6".

---

## Panel 7 — Cautionary finding
**JEDI breaks 7B on React.**

| Metric | Baseline | +JEDI | p |
|--------|----------|-------|----|
| Compile rate | 100% | **50%** | <.001 |
| CLIP | 0.63 | **0.32** | <.001 |
| SSIM | 0.67 | **0.36** | <.001 |

JEDI was trained for interactable-element clicking. React samples are dominated by *alignment* defects, where JEDI's parse rate is only 34%. Noisy/empty coords injected into the prompt mislead 7B into generating broken JSX.

*Lesson:* grounding quality must match the defect distribution. JEDI ≠ drop-in universal grounding.

[design: red-highlighted box, warning icon, two columns]

---

## Panel 8 — Takeaway
### **Free-lunch GUI grounding works** — but only where the model needs it most.

- Small models on hard frameworks: **big multi-metric wins**.
- Strong models: **smaller, framework-dependent visual gains**.
- Wrong-signal mismatch (JEDI × region defects): **can actively harm**.
- DesignBench's primary code metric systematically undercounts correct repairs. **Report CLIP.**

[design: 48pt heading, 28pt bullets. Centered.]

---

## Panel 9 — Future work
- **Hybrid** OmniParser + JEDI on 7B Angular (complementary strengths).
- **Filter JEDI cache** to only parsed clicks — avoid the React regression.
- **Reference-vs-broken diff grounding** — OmniParser only the *changed* elements between broken and target screenshots.
- **Anonymize JEDI prompt defect names** — remove the IssAcc label-leakage confound.
- **UICrit / WebSight** for external validity beyond DesignBench.

[design: 24pt bullets, narrow column.]

---

## Panel 10 — References + repo
- **DesignBench:** Xie et al. 2024. *DesignBench: a Framework for Benchmarking Web Design Generation and Repair.*
- **OmniParser:** Microsoft Research, OmniParser V2.0.
- **JEDI-7B-1080p:** xlangai, trained on OSWorld-G.
- **Code + data:** [github.com/isaacau502/GUI-grounded-gen](https://github.com/isaacau502/GUI-grounded-gen) `[QR CODE]`

[design: 18pt body, QR code 3" × 3" bottom-right.]

---

## Presentation notes

### 30-second elevator pitch
> "We plugged GUI-grounding model outputs into a code-repair VLM's prompt and ran it on DesignBench. Big result: on the weakest cell — 7B fixing Angular pages — we get **+14 CLIP points** and the compile rate jumps from 57% to 75%. The story also holds on the strong 72B, but only on visual metrics — the AST-based code similarity score disagrees, which turns out to be DesignBench's metric penalizing correct-but-different rewrites."

### 2-minute walkthrough order
1. *Motivation* (Panel 1) — 15s: "VLMs miss localization."
2. *Approach* (Panel 2) — 15s: "Two grounding signals."
3. *Hero* (Panel 4) — 30s: "+14 CLIP on 7B Angular. This is the big one."
4. *Cross-framework* (Panel 5) — 20s: "72B benefits on visuals too, though AST disagrees."
5. *Methodology finding* (Panel 6) — 15s: "CLIP and SSIM can tell different stories."
6. *Cautionary* (Panel 7) — 15s: "When grounding goes wrong."
7. *Takeaway* (Panel 8) — 10s.

### Likely Q&A (1-line answers)
- **"Why N=28 per cell?"** — DesignBench is fixed-size. We compensate with paired tests + bootstrap CI.
- **"Is IssAcc legit?"** — Partially leaky for JEDI (prompt names defects). We flag this in results and down-weight it.
- **"Why does 72B regress on AST?"** — Grounding changes how the model fixes the defect; AST diverges from reference even when the fix is correct. CLIP confirms visual correctness.
- **"Does it work on mark mode (red bboxes)?"** — Null or mild regression. The red bboxes already carry the "look here" signal; adding structural text on top is redundant.
- **"Did you try hybrid signals?"** — Not yet; flagged as top future work given complementary strengths on 7B Angular.
- **"Why 7B over 72B?"** — 7B has more headroom on hard frameworks (57% baseline CSR on Angular). Grounding is a bigger relative lift.

---

## Design checklist

- [ ] Title visible from 6 feet (≥72pt)
- [ ] Body ≥24pt
- [ ] Hero numbers ≥48pt, CMU red
- [ ] Each panel = one idea
- [ ] Concrete numbers everywhere, no hedging
- [ ] Negative finding included (Panel 7)
- [ ] QR to repo, bottom right
- [ ] Acknowledgements: CMU 11-711 Spring 2026
