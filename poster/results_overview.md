# Results overview — ranked for poster

Each row = one significance-tested finding with a 1-line theorized mechanism.
Stats source: `scripts/poster_stats.py`, Wilcoxon signed-rank paired (two-sided),
McNemar exact binomial for CSR, α = 0.05. All from DesignBench repair,
N = 22–68 per cell, temp=0 seed=42. **Full render complete as of 2026-04-20.**

Summary: **27 significant gains, 12 significant regressions.**

---

## Tier 1 — poster headlines (ranked)

### 1. OmniParser structural on 7B Angular — hero cell

**CLIP +.141 ** (p=.007)**, **SSIM +.111 ** (p=.002)**, **CMCS +.073 * (p=.048)**. CSR .57 → .75 (6 extra samples compile, McNemar p=.125 directional).

Baseline 7B Angular: CLIP .486, SSIM .407, CSR 57%. With grounding: CLIP .627, SSIM .519, CSR 75%.

*Why:* Angular repair requires coordinated edits across `template.html` + `component.ts`; "which element is broken" is severely underspecified from screenshot alone. 7B's spatial reasoning fails on 43% of samples without help. OmniParser's bboxes + OCR + element relations supply the scaffolding.

### 2. OmniParser on 72B — visual-metric gains, 3 of 4 frameworks

| Framework | CLIP | SSIM | MAE |
|-----------|------|------|-----|
| Vue | **+.012 ** (p=.002)** | — | — |
| Angular | **+.009 * (p=.045)** | **+.003 * (p=.026)** | — |
| Vanilla | **+.018 ** (p=.002)** | **+.019 ** (p=.002)** | **−.337 * (p=.030)** |

AST (CMLS, CMCS) trends mildly negative, never significant.

*Why:* Grounding nudges the strong 72B toward repairs that visually match the target even when the AST diverges from reference. CMLS measures "reproduced the reference"; CLIP measures "fixed the defect." These can diverge.

### 3. JEDI on 7B React — cautionary regression (all metrics blown out)

**CSR 1.00 → 0.50 (p<.001)**, **CLIP −.309 (p<.001)**, **SSIM −.304 (p<.001)**, **MAE +52.6 (p<.001)**, **CMLS −.096 (p=.006)**, **CMCS −.084 (p=.006)**. Half the React samples stopped compiling.

*Why:* React samples are dominated by alignment defects (34% of all queries); JEDI's parse rate on alignment is 34% (worst across defect types). Most injected "click targets" for React are empty strings or malformed coords. The resulting noisy prompt context misleads 7B into producing broken JSX.

### 4. JEDI on 72B — small but consistent visual gains on 3 non-Angular frameworks

| Framework | CLIP | SSIM | MAE |
|-----------|------|------|-----|
| Vue | **+.015 * (p=.041)** | **+.012 ** (p<.001)** | **−.251 ** (p=.008)** |
| Vanilla | **+.013 ** (p=.003)** | **+.026 * (p=.032)** | — |
| React | — | **+.011 ** (p=.009)** | **−1.15 ** (p=.008)** |

*Why:* JEDI's click coordinates focus the 72B model's attention on the defect region, producing small consistent improvements. Smaller effect than OmniParser on 7B because 72B already has strong internal spatial understanding — grounding refines rather than scaffolds.

### 5. JEDI on 72B Angular — the flip — visual regression

**CLIP −.013 ** (p=.005)**, **SSIM −.026 * (p=.020)**. IssAcc +.225 ** (p=.004) but *caveated by leakage*. CMLS/CMCS flat.

*Why:* On Angular — where 72B was already strongest (CMLS .63, CLIP .82, CSR .96) — JEDI's click coordinates pull attention toward the defect but the model was already handling Angular well; the additional "click here" prompt displaces attention the model was using for accurate rendering, so visual fidelity drops.

### 6. Methodology note — CLIP > SSIM for generative UI repair

**7B + OmniParser on Vue: CLIP +.021 ** (p=.005) up, SSIM −.016 ** (p=.004) down.** Two visual metrics significantly disagree on the same cell.

Plus: **7B + JEDI on Vue: CLIP +.012 * (p=.044) up, SSIM −.043 * (p=.025) down, MAE +4.78 * (p=.025) worse.** Same pattern with different grounding.

*Why:* CLIP (embedding similarity) rewards semantic match; SSIM (per-pixel structural) rewards pixel-position preservation. Grounding often fixes the defect correctly but re-lays-out the page, so SSIM drops even though the fix is right. **Argument for CLIP as the headline metric on DesignBench.**

### 7. Per-defect alignment slice — cleanest single result in the dataset

**72B + OmniParser on alignment (N=68 pooled across all 4 frameworks):** CLIP **+.007 ** (p<.01)** rises while CMLS **−.055 * (p<.05)** and CMCS **−.045 * (p<.05)** drop. Same 68 samples. Same repair. Two metrics say better, two say worse.

*Why:* Alignment defects are the most common defect class and hardest to express in AST terms — no single "alignment" AST token, just many small layout changes. Grounding helps visual realignment but the AST still looks different from the reference.

### 8. JEDI IssAcc gains — caveated

JEDI drove IssAcc +.22 to +.47 on 6 of 8 cells (all p<.01). **Caveat:** The JEDI prompt literally names the defect type ("alignment → click at 685, 308"). IssAcc measures whether the response contains those names. Partial leakage.

*Why qualified:* Can be cited as "grounding focuses model attention on named defect types" but not as a clean accuracy gain.

---

## Tier 2 — secondary findings (body text)

### 9. OmniParser on 7B Angular beats JEDI on same cell (multi-metric)

After full render, 7B Angular with each grounding (vs baseline):

| Metric | Baseline | +omni | +jedi |
|--------|----------|-------|-------|
| CLIP | .486 | **.627** (+.141 **) | .595 (+.109 marginal) |
| SSIM | .407 | **.519** (+.111 **) | .472 (+.064 marginal) |
| CMCS | .206 | **.279** (+.073 *) | .289 (+.083 ns) |
| IssAcc (caveat) | .173 | .244 | **.429** (+.256 **) |
| CSR | .571 | .750 (+.18 directional) | .679 (+.11 ns) |

*Why:* OmniParser's spatial element list addresses Angular's multi-file edit problem directly; JEDI's click-point scaffolding is more helpful for single-element clicks (buttons, icons) than for cross-file-coordinated repairs.

### 10. Mark mode + OmniParser — null result (with one regression)

Adding OmniParser on top of mark mode (red bboxes pre-highlighting defects) produced **no significant gains anywhere**. On **Vanilla 7B** it **regresses**: CMLS **−.144 * (p=.032)**, CMCS **−.128 * (p=.038)**.

*Why:* Red bboxes already say "the defect is here." Long structural-text prompt on top is redundant for 72B and actively distracts 7B's limited context-following. Supports a "less is more" design for grounding prompts once a cheap localization signal is present.

### 11. Mark mode alone is itself a grounding signal

- Vue 72B: IssAcc .213 → .352 with mark alone
- Angular 7B: IssAcc .173 → .232
- Vanilla 72B: IssAcc .369 → .318 (slight hurt)

*Why:* Red bboxes *are* a grounding signal. Explains why mark+omni doesn't double-dip.

---

## Tier 3 — only-if-asked

### 12. JEDI parse rate skew by defect type

77 of 170 queries parsed (45% overall). Crowding 74% / overflow 58% / occlusion 40% / alignment 34% / color-contrast 36% / text-overlap 33%.

*Why:* JEDI was trained for interactable-element clicking, not region-level defect localization.

### 13. 7B + OmniParser clustering on visually-complex defects

- Alignment (N=63): CLIP +.065 **, SSIM +.039 **
- Crowding (N=30): IssAcc +.196 **, CodeScore +.078 *
- Overflow (N=17): SSIM +.106 **
- Occlusion (N=29): CLIP +.095 *, SSIM +.082 *

*Why:* These defects are intrinsically spatial — exactly what OmniParser encodes.

---

## Grounding method comparison — when to use which

| Condition | OmniParser | JEDI |
|-----------|------------|------|
| Weak small model (7B) on hard framework (Angular) | **STRONG visual + SSIM + CSR** | modest positive (not significant after render) |
| Strong 72B on any framework except Angular | **Consistent CLIP gain** | **Consistent visual gain, smaller than omni** |
| 72B Angular | Small CLIP gain | **Visual regression** + IssAcc leakage |
| Framework dominated by alignment defects (React) | Safe | **Dangerous** — can blow out all metrics |
| On top of red-bbox mark mode | Redundant / mildly harmful | Not tested on mark mode |

## What didn't work

- 7B + omni on React, 7B + omni on Vanilla: flat
- 72B + omni on React: flat
- Everything on mark mode: null or regression

*Why flat cells:* Baseline already OK (72B React, 7B Vanilla), or defect types don't benefit from structural grounding (React dominated by alignment where both groundings struggle, JEDI catastrophically).
