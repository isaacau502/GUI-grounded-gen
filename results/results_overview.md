# Results overview — ranked for poster

Each row = one significance-tested finding with a 1-line theorized mechanism.
Stats source: `scripts/poster_stats.py`, Wilcoxon signed-rank paired (two-sided),
McNemar exact binomial for CSR, α = 0.05. All from the DesignBench repair task,
N = 22–68 per cell, temp=0 seed=42.

## Tier 1 — what goes on the poster (ranked)

### 1. OmniParser structural on 7B Angular — hero cell

**CLIP +.141 \*\* (p=.007)**, **SSIM +.111 \*\* (p=.002)**, **CMCS +.073 \* (p=.048)**, CSR .57 → .75 directional. Baseline 7B Angular CLIP was 0.49; with grounding it's 0.63.

*Why it worked:* Angular repair requires coordinated edits across `template.html` + `component.ts` — "which element is broken" is severely underspecified from just the screenshot, so the weak 7B's spatial reasoning fails half the time (CSR .57 baseline). OmniParser's explicit bboxes + OCR text + element relations hand the model the scaffolding it couldn't derive on its own.

### 2. OmniParser structural on 72B — visual-metric gains, three frameworks

| Framework | CLIP | SSIM | MAE |
|-----------|------|------|-----|
| Vue | **+.012** ** (p=.002) | — | — |
| Angular | **+.009** * (p=.045) | **+.003** * (p=.026) | — |
| Vanilla | **+.018** ** (p=.002) | **+.019** ** (p=.002) | **−.337** * (p=.030) |

AST metrics (CMLS, CMCS) trend mildly negative but **none crosses α=0.05**.

*Why it worked:* Grounding nudges the strong 72B model toward repairs that visually match the target even when the resulting AST diverges from the reference code path. CMLS measures "reproduced the reference"; CLIP measures "fixed the defect". These can diverge — and they do here.

### 3. 7B + JEDI on React — the cautionary regression

**CMLS −.096 ** (p=.006)**, **CMCS −.084 ** (p=.006)**, **CLIP −.309 ** (p<.001)**, **SSIM −.304 ** (p<.001)**, **CSR 1.00 → 0.50 (p<.001)**. Every metric significantly worse. Half the React samples stopped compiling.

*Why it failed:* React samples are dominated by alignment defects (the single most common defect type); JEDI's parse rate on alignment is only 34%, so most injected "click targets" are either empty strings or malformed. The resulting noisy prompt context misleads the 7B model into producing broken JSX.

### 4. Methodology note — CLIP > SSIM for generative UI repair

**7B + OmniParser on Vue: CLIP +.021 ** (p=.005) up, SSIM −.016 ** (p=.004) down.** Two visual metrics significantly disagree on the same cell.

*Why:* CLIP (embedding-space similarity) rewards repairs that are *semantically* close to target; SSIM (per-pixel structural similarity) rewards repairs that *preserve pixel positions*. Grounding often fixes the defect correctly but re-lays-out the page, so SSIM drops even though the fix is right. **Argument for CLIP as the headline metric on DesignBench.**

### 5. Per-defect alignment slice — cleanest single result in the dataset

**72B + OmniParser on alignment (N=68 pooled across all 4 frameworks):** CLIP **+.007 ** (p<.01)** rises while CMLS **−.055 * (p<.05)** and CMCS **−.045 * (p<.05)** drop. Same 68 samples. Same repair. Two metrics say better, two say worse.

*Why:* Alignment defects are the most common defect class and the hardest to express in AST terms — there's no single "alignment" AST token, just many small layout changes. Grounding helps the model visually realign but the AST still looks different from the reference.

### 6. JEDI IssAcc wins — caveated

JEDI grounding drove IssAcc up +.24 to +.47 on 6 out of 8 cells (all p<.01). **But the JEDI prompt literally names the defect type ("alignment → click at 685, 308"), which partially leaks the IssAcc answer.**

*Why qualified:* IssAcc measures whether the model's response contains the right defect names. JEDI's prompt contains those names. Treat as a demonstration that attention-to-prompt works, not an independent accuracy gain.

---

## Tier 2 — secondary findings (in body text, not headline numbers)

### 7. 72B + JEDI visual gains

Smaller than OmniParser but consistent:
- Vue SSIM **+.012 ** (p<.001)**, CLIP +.015 * (p=.041)
- Vanilla SSIM **+.026 * (p=.032)**, CLIP +.013 ** (p=.003)
- React SSIM **+.011 ** (p=.009)**, MAE **−1.15 ** (p=.008)**

*Why modest:* 72B already has strong internal spatial understanding; JEDI's click coordinates refine attention but don't scaffold like OmniParser's richer element list does for 7B.

### 8. 72B + JEDI on React — surprise CodeScore gain

**CodeScore +.063 (raw; p=.381 not significant but notable).** React 72B was already strong; JEDI pushed code-quality higher without moving CMLS.

*Why possibly:* JEDI's click coords may help the model pick the right JSX component to edit, improving string-level code similarity without changing AST structure.

### 9. Mark mode + OmniParser — null result (and one regression)

Adding OmniParser on top of mark mode (red bboxes pre-highlighting defects) produced **no significant gains anywhere**. On **Vanilla 7B** it actually **regresses**: CMLS **−.144 * (p=.032)**, CMCS **−.128 * (p=.038)**.

*Why:* Red bboxes already say "the defect is here." A long structural-text prompt on top is redundant for 72B and actively distracts 7B's limited context-following. Supports a "less is more" design for grounding prompts once a cheap localization signal is present.

### 10. Mark mode alone is itself a grounding signal

Informal cross-mode comparison (baseline same model, different modes):
- **Vue 72B:** IssAcc .213 → .352 (mark alone adds ~70% relative to IssAcc)
- **Angular 7B:** IssAcc .173 → .232
- **Vanilla 72B:** IssAcc .369 → .318 (mark slightly hurts)

*Why:* The red bboxes *are* a form of grounding — visual localization given for free in the screenshot. Explains why mark+omni doesn't double-dip.

---

## Tier 3 — findings worth mentioning only if asked

### 11. JEDI parse rate varies sharply by defect type

77 of 170 queries parsed (45% overall). Crowding 74% / overflow 58% / occlusion 40% / alignment 34% / color-contrast 36% / text-overlap 33%.

*Why:* JEDI was trained on OSWorld-G for interactable-element clicking (buttons, icons, links). Region-level defects like "this whole section has alignment issues" don't have a clickable target, so JEDI returns empty output or malformed coords.

### 12. 7B + OmniParser gains cluster on visually-complex defects

Per-defect slice:
- Alignment (N=63): CLIP +.065 **, SSIM +.039 **
- Crowding (N=30): IssAcc +.196 **, CodeScore +.078 *
- Overflow (N=17): SSIM +.106 **
- Occlusion (N=29): CLIP +.095 *, SSIM +.082 *

*Why:* These defects are intrinsically spatial — exactly what OmniParser encodes.

---

## What didn't work / null findings

- **7B + OmniParser on React** — flat across all metrics (smallest effect cell for +omni).
- **7B + OmniParser on Vanilla** — flat; vanilla 7B baseline is already strong.
- **72B + OmniParser on React** — flat across all metrics.
- **7B + OmniParser on Vue** — mixed, only the CLIP/SSIM divergence is significant.

*Why the flat cells:* These are the cells where baseline is already OK (72B React, 7B Vanilla) or where the defect types don't benefit from structural grounding (7B React is dominated by alignment, which both groundings struggle with but JEDI fails catastrophically on).

## Still pending
- JEDI angular render (biggest pending data point — AST-only already shows this is the 7B+jedi hero cell: CMLS +.142, CodeScore +.201).
- If angular CLIP confirms, we get a **double-hero story**: both OmniParser and JEDI produce large visual gains on 7B Angular via different mechanisms.
