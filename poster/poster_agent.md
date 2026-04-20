# Poster-writing agent prompt

**Purpose:** guided end-to-end poster content generation for this project (*Repurposing GUI Grounding for Automated UI Code Repair*, CMU 11-711).

**How to use:** paste this entire file into a new Claude/ChatGPT chat, or feed to any LLM agent. The agent should (1) ask the user a short questionnaire, (2) use the project artifacts listed below, (3) produce poster-ready section text and layout recommendations.

---

## Project context (do not re-research, just use)

**Project:** CMU 11-711 Advanced NLP class project. Authors: Isaac Au, Alice Le.

**Task:** DesignBench UI-code-repair task. Given a web UI screenshot with a visual defect (misalignment, overflow, overlap, etc.) plus broken source code, produce corrected code that renders the target design.

**Core idea:** inject GUI-grounding model outputs into the prompt of a vision-language code repair model (Qwen2.5-VL-7B and 72B). Two grounding signals tested:

1. **OmniParser structural** — YOLO bounding boxes + Florence-2 captions + EasyOCR text + pairwise geometric relations + pixel statistics. Big structural block of text describing the UI.
2. **JEDI-7B-1080p** — trained click-point localization. For each defect in a sample, JEDI outputs `pyautogui.click(x, y)` coordinates which are injected as natural language into the prompt.

**Setup:** 111 DesignBench repair samples across React (28), Vue (27), Angular (28), Vanilla (28). Qwen2.5-VL via Dashscope international. Temperature 0, seed 42. Two DesignBench modes: `both` (code + original screenshot), `mark` (code + screenshot with defects pre-highlighted in red bboxes).

**Metrics:**
- **Code metrics:** CMLS (AST op score), CMCS (AST content score), CodeScore (string similarity), IssAcc (does response name the correct defect types?)
- **Visual metrics:** CLIP (embedding similarity), SSIM (pixel-structural), MAE (pixel error)
- **Compile:** CSR (compile success rate — does rendered page compile?)

**Statistics:** paired Wilcoxon signed-rank two-sided (continuous), McNemar exact binomial on discordant pairs (CSR). N = 22–68 per test.

**Baseline state:** DesignBench's own baseline (Qwen2.5-VL without grounding) was reproduced from Xie et al., matching paper within 5% on most cells.

## Key findings (from `poster/RESULTS.md`)

**Headline (in order of poster priority):**

1. **Hero cell — 7B + OmniParser on Angular:** CLIP .486 → .627 (**+.141, p=.007**), SSIM .407 → .519 (**+.111, p=.002**), CMCS **+.073, p=.048**. Compile success rate 57% → 75%. Largest effect in the study.

2. **72B + OmniParser visual gains on 3 of 4 frameworks:** Vue CLIP +.012 (p=.002), Vanilla CLIP +.018 / SSIM +.019 / MAE −.337 (all p≤.030), Angular CLIP +.009 / SSIM +.003 (p≤.045). AST metrics trend mildly negative, never significant.

3. **7B + JEDI on React — cautionary regression:** CSR 1.00 → 0.50 (p<.001), CLIP −.309, SSIM −.304, MAE +52.6, CMLS −.096, CMCS −.084 (all p<.01). JEDI's 34% parse rate on alignment defects (React's dominant defect) produces noisy coords that mislead 7B.

4. **72B + JEDI visual gains on 3 non-Angular frameworks** + **visual regression on Angular:** Vue/Vanilla/React SSIM and MAE all significantly better with JEDI, but 72B + JEDI on Angular shows CLIP −.013 / SSIM −.026. 72B Angular baseline already strongest (CSR .96); JEDI's coords displace useful attention.

5. **CLIP vs SSIM methodology:** 7B + OmniParser on Vue: CLIP +.021 UP (p=.005), SSIM −.016 DOWN (p=.004). Mirrored by 7B + JEDI on Vue. CLIP rewards semantic match, SSIM rewards pixel preservation. Grounding re-lays-out correctly but pixels shift.

6. **Per-defect alignment slice (N=68 pooled across frameworks)** — 72B + OmniParser: CLIP +.007 (p<.01) rises while CMLS −.055 / CMCS −.045 (p<.05) drops on same samples. Cleanest illustration of the CMLS-vs-CLIP divergence.

7. **JEDI IssAcc gains +.22 to +.47 everywhere** — caveat: JEDI prompt literally names the defect type, so IssAcc metric partially leaked.

8. **Mark mode null result** — red bboxes alone already capture most of the "look here" benefit. Adding OmniParser on top is redundant (mildly hurts 7B Vanilla).

**Mechanism explanations** (1 line each, for body text):
- *7B Angular win*: multi-file edits (template.html + component.ts) underspecified from screenshot alone; 7B baseline fails 43% of samples; bboxes/OCR scaffold weak spatial reasoning.
- *72B cross-framework visual*: grounding nudges strong model toward visually-correct repairs even when AST diverges from reference code path.
- *7B React JEDI blowup*: alignment defects (34% parse) dominate React; noisy empty coords inject broken prompt context; 7B follows into broken JSX.
- *72B Angular JEDI flip*: 72B already best on Angular; click coords displace attention the model was using successfully.
- *CLIP-vs-SSIM divergence*: grounding changes the repair strategy, moving pixels around while preserving semantic match.

## Artifacts available in the repo

- `poster/RESULTS.md` — collated one-stop doc (read this first)
- `poster/results_overview.md` — tier-ranked with mechanisms
- `poster/poster_stats.md` — full α=0.05 significance table
- `poster/per_defect.md` — per-defect slicing
- `ablation_log.md` — run-by-run history
- `grounding/` — the three grounding wrappers (omniparser, omniparser_structural, jedi)
- `scripts/` — runners, stats, analysis

---

## Step 1 — questions for the user

Ask these as a numbered questionnaire. Get answers before generating content.

1. **Poster dimensions?** Common: 48"×36" landscape, 36"×48" portrait, A0 ISO (33"×47"), A1 ISO (23"×33"). Custom is fine too.
2. **Software / format?** Keynote, PowerPoint, Illustrator, Canva, LaTeX (beamerposter or tikzposter), Figma, or none-yet-just-text.
3. **Audience?** CMU 11-711 poster session mixed NLP/ML grad students, NeurIPS-style general ML, niche VLM/HCI workshop, lab talk, other. This affects jargon level.
4. **Time at the poster?** 30-sec elevator pitch vs. 2-min walkthrough vs. deep Q&A. This affects how dense the visuals should be.
5. **One hero figure — which do you want?** Options:
   - a. Bar chart for 7B Angular: baseline vs +omni vs +jedi on [CLIP, SSIM, CSR]
   - b. Cross-framework heat map for 72B+omni visual metrics
   - c. Scatter showing CMLS (x) vs CLIP (y) for the alignment N=68 slice (proves divergence)
   - d. A "signal decision table" (which grounding to use when)
   - e. Something else (describe)
6. **Second/third figure (if room)?** Same options as Q5, pick up to 2 more.
7. **Include the negative result (7B + JEDI React blowout)?** Yes recommended — makes the story honest and adds the "when grounding breaks" angle. User might want to skip it for a single-positive-story poster.
8. **Include mark-mode null?** Optional. Good for a "negative results count" moment.
9. **How much space for methodology vs results?** Default split is ~30/50/20 (intro+method / results+figures / discussion+future). User may want 20/60/20 if the hero number should dominate.
10. **Author list + affiliations** as it should appear at the top.
11. **Acknowledgements / funding?** (Usually "CMU 11-711, Spring 2026" — confirm.)
12. **Color preference / theme?** Usually tie to CMU red (#C41230) + neutral greys. Confirm or override.
13. **Deadline?** Affects whether to suggest quick iterations or polish.
14. **Anything to definitely NOT include?** (Sometimes a collaborator wants a certain framing held back.)

**Wait for answers before generating poster content.** If the user says "defaults" or "you pick," use: 48"×36" landscape / PowerPoint / CMU 11-711 session / 2-min walkthrough / figures a+c / include negative result / exclude mark null / 25/55/20 / authors from CLAUDE.md / CMU red + greys.

---

## Step 2 — after answers, produce

A single markdown response with:

### A. One-line TITLE (plus a 1-line subtitle)
Optimized to catch a reader's eye at arm's-length. No jargon the audience won't have.

### B. Section-by-section body text
For each section, write:
- The heading (e.g. "Motivation")
- The exact body text the user will paste (tight — posters are visually dense)
- A small "design note" in brackets (e.g. `[pull-quote style: big font 28pt, narrow column]`)

**Required sections** (adjust to fit size):

1. **Motivation / Question** — Why does GUI grounding matter for code repair? Two sentences max. Name the gap: VLM-based UI repair struggles with "which element is broken" from a screenshot alone; GUI-grounding models output exactly that localization. Can we plug them in?

2. **Approach** — Bullet list. 3 rows:
   - *OmniParser structural*: element list + OCR text + geometric relations injected as text.
   - *JEDI click coords*: per-defect (x, y) click point from JEDI-7B-1080p injected as "click at X, Y."
   - Both injected into Qwen2.5-VL's repair prompt; compare to ungrounded baseline.

3. **Setup** — Compact: 111 DesignBench repair samples × 4 frameworks × 2 model sizes × 3 grounding signals × 2 DesignBench modes. Temp=0 seed=42. Paired Wilcoxon (continuous), McNemar exact (CSR). α=0.05.

4. **Results — Hero** — Pull-quote big number for 7B Angular. "**CLIP +14% on the weakest baseline cell.**" Plus the hero figure.

5. **Results — Cross-framework** — 72B + OmniParser delivers small but consistent visual wins on 3 of 4 frameworks while AST trends down. A table or heatmap.

6. **Discussion / Mechanism** — Three one-line takeaways:
   - *Grounding helps most where the model needs it most.* 7B on Angular closes a large gap.
   - *CMLS and CLIP can disagree* — we see significant CMLS drops with significant CLIP rises on the same samples (alignment N=68). Argue CLIP is the right metric on DesignBench.
   - *JEDI is click-centric, so it fails on region defects* — 7B React catastrophically, 72B Angular mildly. Use OmniParser for layout-wide tasks; JEDI for click-like defects.

7. **Cautionary finding** — 7B + JEDI on React: CSR collapses 100% → 50%. Short visual: before/after rendered screenshot OR a red-highlight table cell.

8. **Takeaway** — One-sentence positioning. Draft: *"Free-lunch GUI grounding improves UI-code repair, but only where the model needs it most — and it can break things when the signal-to-noise is wrong."*

9. **Future work** — 3 bullets from `RESULTS.md` section 8.

10. **References + QR** — GitHub repo QR code at bottom-right. DesignBench reference (Xie et al.), OmniParser reference (Microsoft), JEDI reference (xlangai).

### C. Figure specifications
For each figure the user chose, specify:
- **What the figure shows** (caption text under 20 words)
- **Axes / columns** (exact labels)
- **Data source** (which file/script to pull from)
- **Visual style** (bar/scatter/heatmap/table; color scheme)
- **Size hint** (~1/3 poster width, etc.)

### D. Layout recommendation
Text diagram of the poster grid. Example:
```
+----------------+----------------+----------------+
| TITLE (full width)                              |
+----------------+----------------+----------------+
| Motivation     | Approach       | Setup          |
+----------------+----------------+----------------+
| [HERO FIGURE: 7B Angular bar chart, 2 columns]  | Cautionary finding |
+----------------+----------------+----------------+
| Cross-fw table | Discussion     | Takeaway       |
+----------------+----------------+----------------+
| Future work    | References + QR                |
+----------------+----------------+----------------+
```

### E. Presentation notes
- 30-second elevator pitch script (3 sentences max)
- 2-min walkthrough order (which panel to point at in what sequence)
- Likely questions and a 1-line answer each ("why not larger N?" "does it work on mark mode?" "what's label leakage?")

---

## Style constraints

- **Posters are read at 6 feet.** Body text ≥ 24pt, headlines ≥ 36pt. Recommend font sizes inline.
- **Pull-quote hero number must be visible at arm's length.** Recommend ≥ 72pt for "+14%".
- **One idea per panel.** Do not cram.
- **No em-dashes in body text** (use periods, commas, or "…"). No banned AI-vocabulary ("delve", "crucial", "robust", "comprehensive", etc.).
- **Concrete numbers always.** "+14 CLIP points" beats "significantly improves."
- **Don't overclaim.** If an N is small, say so. If a finding is caveated (IssAcc leakage), say so.
- **Author voice:** student researchers presenting real work. Confident but honest about limitations.

---

## Output

Write everything out in one response. User can paste directly into their poster software. Call out anywhere you need more info or made assumptions.
