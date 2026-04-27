# Consistency audit
Date: 2026-04-27

Scope: cross-doc audit of the project narrative as it stands between the
delivered poster and the start of paper drafting. Two LaTeX files are
treated as gold-standard project narrative; everything newer is checked
against them, then against each other.

---

## Gold-standard narrative (from the LaTeX)

### `report_plan.tex` — project proposal (pre-experiments)
- **Central question:** can spatial/semantic understanding from GUI grounding
  models trained for navigation transfer to identifying and correcting
  visual defects in machine-generated frontend code?
- **Pipeline:** screenshot → GUI grounding model (JEDI-7B or **OmniParser
  v2**) → structured output → concatenated with HTML/CSS source code →
  code-generation LLM (**Qwen2.5-VL-7B**) → corrected code.
- **Three approaches:** (1) zero-shot grounding transfer, (2) **LoRA
  fine-tuning** on UI defect data, (3) **multimodal RAG** with Material
  Design guidelines.
- **Two baselines:** B1 no-grounding, B2 text-only RAG.
- **Three evaluation constructs:** visual fidelity, design-convention
  adherence, **component completeness** (penalize repairs that remove
  other UI components while fixing the target defect).
- **Independent evaluation of grounding step:** defect-detection precision
  and recall against annotated ground-truth defect locations on a sampled
  subset.
- **Human correlation study:** small-scale, to validate metric/human
  alignment.
- **Framing label:** "GUI grounding as visual critic."

### `ui-repair-baseline/baseline_reproduction_results.tex` — Milestone 2 (post-baseline reproduction)
- **Reproduction successful**, 72B within 5% on Angular CMLS/CMCS, CLIP
  consistent across all conditions.
- **7B failure modes:** 75% React compile fail, 43% Angular; mean IssAcc
  0.27; correlation between IssAcc and CMCS is **0.117**.
- **Three lessons:**
  1. CMLS/CMCS don't capture visual correctness → propose CLIP supplement.
  2. 7B can't compile reliably for framework projects → 7B unsuitable as
     generator → use 72B as generator.
  3. Defect identification and code localization compound → motivates GUI
     grounding.
- **Two strengths preserved:** (a) DesignBench prompt elicits plausible
  `[REASONING]` that any new approach must preserve, (b) single-pass
  baseline simplicity must be matched or earned by added complexity.
- **Refined proposal:** generator switches from 7B to **72B**; grounding
  step kept at 7B scale. Stage 1 zero-shot grounding, Stage 2 LoRA
  fine-tuning. RAG positioned as a "further extension" if grounding
  shows promise. Set-of-marks and visual-diff guidance listed as
  alternatives if grounding fails.
- **Vue 7B CSR discrepancy** attributed to **regional Dashscope endpoint
  drift** (China vs international).
- **Sample illustrations:** sample_11 (7B identification failure — empties
  sidebar), sample_13 (72B localization failure — single-column rewrite),
  sample_14 (7B perfect AST scores but full-width stretch).

---

## Per-document story summaries

- **report_plan.tex** — "We propose three approaches (zero-shot, LoRA,
  RAG) to repurpose GUI grounding as a *visual critic* for UI repair on
  Qwen2.5-VL-7B."
- **ui-repair-baseline/baseline_reproduction_results.tex** — "We
  reproduced DesignBench and refined the proposal: 72B generator with
  7B-scale grounding, two-stage plan (zero-shot then LoRA), RAG as
  optional extension."
- **ablation_log.md** — "Three clean wins, two nulls, one regression
  …" (top, stale) → **"All runs complete: 27 significant gains, 12
  regressions"** (bottom, current). Internally inconsistent.
- **results_summary.md** — "Grounding helps both sizes on different axes;
  72B wins visual, 7B+omni wins multi-metric on Angular. JEDI variant not
  run yet." (Pre-JEDI snapshot, never updated.)
- **poster/RESULTS.md** — "Structural GUI grounding reliably improves
  UI-repair quality; pattern depends on model size × framework. Hero,
  cross-fw, cautionary, methodology, per-defect, IssAcc-leakage caveat."
- **poster/results_overview.md** — Same as RESULTS.md, tier-ranked with
  one-line mechanisms per finding.
- **poster/poster_stats.md** — Full α=0.05 table: 27 gains / 12
  regressions / 12 marginals / 98 n.s. = 149 cells. (No inline IssAcc
  leakage flag.)
- **poster/per_defect.md** — Per-defect-pooled deltas across all four
  frameworks; spatial defects benefit most from omni-7B.
- **poster/table.md** — Pooled-N=111 significance table. Flags JEDI
  IssAcc leakage and 7B+JEDI compile-rate regression inline.
- **poster/poster_draft_v1.md** — 10-panel draft with Hero, Cross-fw,
  Methodology, Cautionary (Panel 7, included), Takeaway. Q&A keeps
  cautionary acknowledgement.
- **poster/poster_content.md** — More detailed expansion of v1; explicitly
  notes (§18) that the rendered poster *omits* the 7B+JEDI React row and
  *softens* 72B+JEDI Angular to neutral for an "all-optimistic framing."
- **poster/poster.html** — Final rendered poster. **No cautionary
  panel.** Hero is 7B Angular. Takeaway: "7B is scaffolding. 72B is
  refinement. Grounding helps most where the model is weakest."
- **poster/poster_agent.md** — Prompt-template for poster-generation;
  bakes in the full RESULTS.md narrative as project context. Itself not
  a narrative artifact, but its summary of "key findings" is consistent
  with RESULTS.md.
- **poster/README.md** — Index of poster artifacts. Consistent.
- **todo-ablations.md** — Backlog. Mostly tracks future work consistent
  with RESULTS.md "future work" section, plus separately re-introduces
  the LoRA/RAG/set-of-marks/visual-diff/critic-repair items dropped from
  the proposal.

---

## Inconsistencies and contradictions

### HIGH severity

- **[ablation_log.md:5–48 vs ablation_log.md:143–212]** Internal
  contradiction. The top-level **"Headline (current state)"** section
  presents pre-render JEDI numbers as live findings — including
  *"Win 2 — 7B + JEDI on Angular: CMLS +.142 *, CMCS +.118 *,
  CodeScore +.201 ** … CLIP pending render"*. The Run 06 (COMPLETE)
  block lower in the same file states explicitly:
  *"7B + JEDI Angular mostly neutral after render … AST metrics not
  significant. The AST-only pre-render numbers (CMLS +.142, CodeScore
  +.201) shrank once compile-failed samples contributed zeros."*
  The bottom of the file says **"All runs complete. 27 significant
  gains, 12 significant regressions"**, contradicting the top's
  *"23 significant gains"* (in Run 09's text). **Recommend:** rewrite
  the top "Headline" section against the post-render state, and remove
  or strikethrough the stale Win 2 block.

- **[results_summary.md:78–94]** Stale. Says *"JEDI variant not run
  yet. Waiting on Colab."* and *"Mark-mode ablation running … ETA
  ~60 min from now."* Both have since completed. The doc is dated
  2026-04-20 but predates the JEDI render; it omits the cautionary
  7B+JEDI React regression entirely, so a reader of just this file
  would miss the project's most-cited cautionary finding.
  **Recommend:** delete or move into `poster/` with a date-stamp
  banner — keeping it in the repo root suggests it is the canonical
  results doc.

- **[poster/poster.html: missing cautionary panel]** vs
  **[ablation_log.md, RESULTS.md, results_overview.md, poster_draft_v1.md
  Panel 7, poster_content.md §18]**. Every text-stage doc treats the
  7B+JEDI React regression (CSR 1.00 → 0.50, CLIP −.309) as a Tier-1
  cautionary finding. The rendered poster removes it; the takeaway
  strip says only *"Grounding helps most where the model is weakest, and
  CLIP is the metric to trust."* The poster is internally consistent —
  poster_content.md §18 acknowledges the editorial omission — but the
  paper inherits the obligation to put the cautionary back.
  **Recommend:** the paper must include the 7B+JEDI React cell or its
  absence will read as cherry-picking.

- **[poster/poster_content.md §3.2 ("OmniParser v2"), §4 setup table
  ("OmniParser v2"), §10, §14 References] vs [grounding signal as
  actually run]** The poster claims *"OmniParser v2"* as the grounding
  method. The actual grounding signal is **"OmniParser structural"** —
  a custom prompt block built on top of v2 weights that combines YOLO
  bboxes + Florence-2 captions + EasyOCR + pairwise geometric relations
  + pixel statistics. The repo distinguishes them: `grounding/omniparser2.py`
  is the v2 wrapper, `grounding/omniparser_structural.py` is the
  structural wrapper, and `todo-ablations.md` item #8 lists "OmniParser
  v2 (elements + captions only, no relations)" as a *separate, not-yet-run*
  ablation. **Recommend:** in the paper, name the actual signal
  consistently — either "OmniParser-structural prompt block" or
  "structural grounding (built on OmniParser v2 weights)" — and reserve
  "OmniParser v2" for the standalone wrapper.

- **[poster/RESULTS.md Tier 1 #5, results_overview.md #5,
  poster_content.md §7 72B JEDI table] vs [poster_stats.md rank 14]**
  The narrative summarizes 72B+JEDI on Angular as a *"visual
  regression"* (CLIP −.013 **, SSIM −.026 *). poster_stats.md rank 14
  reports the *same cell* with **MAE −3.04 **(p=.005), a significant
  *gain* (lower MAE = better). poster_content.md §7 prints all three
  but doesn't reconcile. The tidy "visual regression" framing is wrong:
  two visual metrics regress, one improves, on the same samples.
  **Recommend:** describe the cell as a *split-visual* or *mixed-visual*
  outcome, not a clean regression — and explore whether MAE goes the
  other way because of a different sensitivity to the kind of
  attention-displacement the docs hypothesize.

- **[poster_content.md §6 Hero panel "+.073 CMCS, p=.048"] vs
  [ablation_log.md Run 05]**  The hero CMCS gain on 7B+omni Angular is
  reported without acknowledging the **CSR-zeroing artifact** that Run 05
  flagged: *"DesignBench evaluator zeros all metrics (including AST)
  when compile fails. Grounded 7B Angular went from compile-fail-rate
  43% to 25% via grounding, so recomputed AST averages differ slightly
  from AST-only methodology."* That is to say, part of the +.073 CMCS
  gain comes from previously-zero (compile-failed) samples now compiling
  and contributing real AST scores. results_summary.md "Caveats" called
  this out explicitly; the poster docs (RESULTS.md, results_overview.md,
  poster_content.md) do not. **Recommend:** in the paper, either cite
  CMCS conditional-on-compile, or footnote that the +.073 CMCS gain on
  the 7B Angular hero is partially CSR-driven.

### MEDIUM severity (narrative drift / stale claims)

- **[report_plan.tex Approaches 2–3, baseline_reproduction_results.tex
  "Refined Proposal"] vs [poster narrative]** The **LoRA fine-tuning**
  approach (Approach 2 in proposal, Stage 2 in milestone 2) and
  **multimodal RAG** approach (Approach 3 in proposal, "extension" in
  milestone 2) **never ran**. The poster does not acknowledge these as
  scoped-out; the takeaway is framed as if zero-shot prompt scaffolding
  was the plan all along. todo-ablations.md items 15–17 list them as
  "Tier 3 — multi-day, probably not worth chasing unless pivoting to a
  paper submission." **Recommend:** the paper explicitly state that the
  proposal's three-approach plan was reduced to zero-shot only, and why
  (compute budget, scope), so the absence of LoRA/RAG results does not
  read as silently dropped commitments.

- **[report_plan.tex §"Refined Proposal" alternatives]** Set-of-marks
  prompting and visual-diff guidance were both explicitly named as
  fallbacks if zero-shot grounding failed. Neither ran. They linger in
  todo-ablations.md (#19, #20) but are not surfaced in the poster.
  **Recommend:** brief mention in paper Future Work; no reframing
  needed.

- **[report_plan.tex §"Proposed Evaluation"]**
  - "Defect detection precision and recall against annotated ground-truth
    defect locations on a sampled subset" — never run. No grounding-step
    independent evaluation appears anywhere in the poster.
  - "Small-scale human correlation study" — never run.
  - "Component completeness" metric (preserve all UI components after
    repair) — never operationalized. The sample_11 *"empties the
    sidebar"* failure case in milestone 2 is exactly the kind of
    regression this metric was designed to catch, but no metric counts
    "missing component" anywhere in the results.
  **Recommend:** drop these from the paper unless reintroduced; if
  retaining, reframe as future work.

- **[report_plan.tex §3.1 Approach 1: "Qwen2.5-VL-7B" as code-generation
  LLM] vs [actual: 7B and 72B both run as generator]** Proposal says
  generator is 7B; milestone 2 refines to 72B-as-generator with 7B-scale
  grounding; actual experiments run **both** 7B and 72B as generators.
  Milestone 2 acknowledged the pivot but no later doc closes the loop
  on running 7B as generator anyway. **Recommend:** the paper note that
  7B was *also* run as a generator (despite milestone 2 ruling it out)
  precisely *because* its compile failures provided the strongest
  grounding-helps-weak-models signal. This is implicit in
  poster_content.md §4 footnote ("7B is the stress-test for the
  grounding signal") but stated as if self-evident.

- **[report_plan.tex Abstract: "GUI grounding models … as visual
  critics"] vs [poster.html title: "Repurposing GUI Grounding as Prompt
  Scaffolding for UI Code Repair"]** The "visual critic" framing is
  abandoned in favor of "prompt scaffolding." The two are subtly
  different — "critic" implies critique-then-repair stages; "scaffolding"
  implies single-pass prompt augmentation. The current pipeline is the
  latter (poster_content.md §3 Design principle: *"grounding is
  additive. The baseline prompt is untouched"*). **Recommend:** the
  paper should explicitly state the framing pivot — visual critic was
  the original positioning, but the actual implementation is closer to
  prompt scaffolding because there is no critique-then-repair decomposition.

- **[poster/results_overview.md Tier 2 #11: mark-mode IssAcc deltas
  including Vanilla 72B (.369 → .318)] vs [RESULTS.md Tier 2 #11: omits
  the Vanilla 72B negative]** RESULTS.md drops the one mark-mode cell
  where IssAcc decreases when listing "mark mode is itself a grounding
  signal." Selective. **Recommend:** consolidate.

- **[poster_content.md §5 Baseline Reproduction] vs
  [baseline_reproduction_results.tex Section "Reproduction Results"]**
  The poster summary attributes the Vue 7B CSR gap to *"likely regional
  Dashscope endpoint drift (China vs international)"*. The LaTeX is
  more cautious: *"the most plausible remaining explanation … we cannot
  verify this independently"*. No contradiction in fact, but the poster
  has dropped the unverifiable hedge. **Recommend:** the paper retains
  the "we cannot verify this independently" hedge.

- **[ablation_log.md Run 05 caveat about Vanilla CSR detection] vs
  [results_summary.md Caveats]** results_summary.md flags
  *"DesignBench's reference CSR for Vanilla is broken: compile_error
  != 'NULL' artifact makes vanilla CSR read as 0.000 when actually 1.00."*
  This patch detail is missing from RESULTS.md and the poster.
  **Recommend:** if the paper reports Vanilla CSR as 1.00, footnote
  the detection-code patch.

### LOW severity (terminology / phrasing)

- **[Author order]** LaTeX files: Alice Le first, Isaac Au second.
  Poster.html, poster_content.md, README, memory: Isaac Au first, Alice
  Le second. Decide an order for the paper and apply consistently.

- **[poster_stats.md significant-gains table] vs [JEDI IssAcc leakage
  caveat]** poster_stats.md doesn't visually flag IssAcc rows for the
  leakage caveat in the table itself; the caveat appears only in
  RESULTS.md and table.md. A reader of poster_stats.md alone would not
  notice IssAcc rows are confounded. **Recommend:** add an in-table
  marker to poster_stats.md.

- **[Mark-mode regressions in poster_stats.md ranks 11–12: 7B+omni
  Vanilla CMLS −.144 / CMCS −.128]** are listed alongside `both`-mode
  cells without flagging that mark-mode evaluations are AST-only (no
  CLIP/SSIM/MAE were rendered). RESULTS.md §3 makes this clear in the
  raw-means table (separate sub-table); poster_stats.md does not.

- **["Ablation" used loosely]** Sometimes "the JEDI ablation" (whole
  experiment), sometimes "trimmed OmniParser ablation" (one variable
  varied). Acceptable for a research log; in the paper, prefer
  "experiment" / "configuration" for the former and reserve "ablation"
  for the latter.

- **[ablation_log.md:235 todo block: "OmniParser v2 (elements +
  captions only, no relations)"]** uses "OmniParser v2" to mean a
  *specific lighter prompt format*, while poster_content.md uses
  "OmniParser v2" to mean *the model behind the structural prompt*.
  Symptom of the structural-vs-v2 terminology confusion above.

- **[poster.html eyebrow "r = 0.12"] vs [LaTeX milestone 2 "0.117"]**
  Rounding only; both report the same correlation. Pick one form.

- **[poster_draft_v1.md: "+29% relative CLIP"] vs [poster.html: "+.141"]**
  Both true, used in different docs. Decide which is the paper hero
  and apply consistently. Paper convention typically prefers absolute
  Δ on a [0,1]-bounded metric.

- **[poster_agent.md: lingering reference to old "Grounded Critic
  with Multimodal RAG Augmentation" labels in §"Project context"]** —
  acceptable as historical context for the prompt template; but if the
  prompt is reused, update so the LLM doesn't generate mixed framing.

- **[Pooled defect counts]** Per-defect pooled N's exceed 111 because
  multi-defect samples count once per defect (per_defect.md header).
  Surface this footnote in the paper if the per-defect table is included.

---

## Hypotheses dropped or silently changed

- **"Two grounding model alternatives: JEDI-7B *and OmniParser v2*"**
  introduced in `report_plan.tex` and `baseline_reproduction_results.tex`,
  *partially* delivered: JEDI-7B-1080p ran cleanly; OmniParser v2 was
  *not* run as a standalone signal — what ran was OmniParser-structural,
  a custom prompt block on top of v2 weights. todo-ablations.md #8 still
  flags "OmniParser v2 (elements + captions only, no relations)" as a
  separate not-yet-run ablation, confirming the v2-vs-structural
  distinction is real but is collapsed in the poster's writing.

- **"Approach 2: LoRA fine-tuning on UI defect data"** — committed in
  `report_plan.tex` and again in `baseline_reproduction_results.tex` as
  "Stage 2." Never run. Acknowledged only as Tier-3 future work in
  todo-ablations.md (#15, #16). No paper-narrative doc explicitly
  acknowledges this scope reduction.

- **"Approach 3: Multimodal RAG with Material Design guidelines"** —
  committed in `report_plan.tex`, kept as "extension" in
  `baseline_reproduction_results.tex` ("If grounding shows promise…").
  Never run. Acknowledged only as todo-ablations.md #17.

- **"Set-of-marks prompting"** alternative — named in
  `baseline_reproduction_results.tex` "Refined Proposal." Never run.
  todo-ablations.md #19.

- **"Visual-diff guidance"** alternative — named in
  `baseline_reproduction_results.tex` "Refined Proposal." Never run.
  todo-ablations.md #20.

- **"Defect detection precision and recall against annotated ground-truth"
  on the grounding step independently** — named in `report_plan.tex`
  evaluation. Never run. Not even on todo-ablations.md.

- **"Small-scale human correlation study"** — named in `report_plan.tex`
  evaluation. Never run. Not on todo-ablations.md.

- **"Component completeness" as an evaluation construct** — named in
  `report_plan.tex` evaluation alongside visual fidelity and
  design-convention adherence. Never operationalized. The motivating
  failure case (sample_11, sidebar emptied) is preserved in milestone 2
  but the metric-to-catch-it isn't.

- **"Generator model: Qwen2.5-VL-7B"** in `report_plan.tex` → revised
  to **"72B as generator"** in `baseline_reproduction_results.tex`. The
  ablation actually runs *both* 7B and 72B as generators. The revision
  is acknowledged in milestone 2; the revision-of-the-revision (running
  7B anyway) is not explicitly noted.

- **Framing: "GUI grounding as visual critic"** → **"GUI grounding as
  prompt scaffolding"**. Old text persists in the LaTeX; new framing
  appears in the poster. Subtle but real semantic shift (critic implies
  critique-then-repair stages, which the implementation does not do).

- **Hypothesis: "7B + JEDI on Angular is a strong AST win"** appeared
  pre-render in ablation_log.md "Headline" (Win 2). Refuted post-render
  in the same file. The Headline never updated.

---

## Consolidated headline finding

**What the weighted evidence — data + most-recent docs — supports:**

> Zero-shot prompt-augmentation with structural GUI grounding
> (OmniParser-structural) reliably improves UI repair on the
> *visual* metrics (CLIP, SSIM, MAE) on the DesignBench repair
> task. The largest single effect is on the weakest baseline cell
> (Qwen2.5-VL-7B × Angular: CLIP +.141, SSIM +.111, p ≤ .007), where
> grounding behaves as scaffolding for a model that lacks the spatial
> reasoning to handle multi-file framework repair. On the strong
> 72B generator, grounding produces smaller but consistent visual
> gains across 3 of 4 frameworks, while AST-overlap metrics (CMLS,
> CMCS) drift mildly negative — symptomatic of the metric, not the
> repair, because grounding shifts repair strategy off the
> reference code path while preserving the visual fix. The signal
> shape matters: a click-point grounding (JEDI) that mismatches a
> framework's defect distribution can blow out compile rate (7B ×
> React: CSR 1.00 → 0.50). All findings are within a single
> benchmark (DesignBench, N = 111) and a single grounding pipeline
> (zero-shot, no fine-tuning, no RAG); LoRA, multimodal RAG,
> set-of-marks, and visual-diff alternatives from the original
> proposal were not executed.

**What the docs *say* the headline is, ranked from most-to-least
faithful to the data:**

1. **poster/RESULTS.md TL;DR + results_overview.md Tier-1 ranking** —
   most faithful. Includes the cautionary, the methodology finding,
   and the per-defect pattern.
2. **poster_content.md** — faithful, with explicit acknowledgement
   (§18) that the rendered poster softens the negatives.
3. **poster.html** — selectively positive; cautionary panel removed.
   Headline message ("scaffolding vs refinement") is supported by the
   data shown but the cell with the most extreme JEDI failure is
   absent.
4. **ablation_log.md (top Headline section)** — stale; reports
   pre-render JEDI numbers as live.
5. **results_summary.md** — pre-JEDI snapshot, missing the cautionary
   entirely.

**The paper's headline should:**
- Lead with the 7B Angular hero in absolute terms (+.141 CLIP), not
  relative ("+29%"), to match the [0,1] metric convention.
- State the mixed-visual story on 72B (CLIP/SSIM up, AST trends down,
  one cell with sign-flipped MAE-vs-CLIP).
- Include the 7B+JEDI React cautionary as a Tier-1 finding.
- Disclose the IssAcc leakage caveat at first mention of any IssAcc
  number.
- Disclose the CSR-zeroing-AST artifact when reporting the +.073 CMCS
  gain on the hero.
- Acknowledge the dropped LoRA/RAG/SOM/diff-grounding scope.
- Use one terminology consistently: "OmniParser-structural" (or
  "structural grounding") for the actual signal, not "OmniParser v2".
- Reframe "visual critic" → "prompt scaffolding" with one explicit
  pivot sentence, so readers of the proposal/milestone 2 are not
  confused.
