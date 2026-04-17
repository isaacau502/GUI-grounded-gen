# 7-Day Workplan — 2 People, Poster@D3 + Paper@D7

**Team**: Isaac (compute) + Alice (analysis).
**Budget**: ~10h/person/day.
**Structure**: 3-day MVP sprint → poster → 4-day expansion + paper.

---

## Milestones

| Day | Milestone | Artifact |
|-----|-----------|----------|
| D1 | Pipeline works end-to-end on 5 samples | `results/repair-grounded/` populated for smoke set; winning prompt format chosen |
| D2 | Full 111-sample run complete; baseline comparison tables | `results/compare.json`, preliminary metrics, qualitative picks |
| D3 | **Poster submitted** | `poster.pdf` |
| D4 | Expansion experiment launched; paper results section drafted | Expansion run in flight; `sections/results.tex` first pass |
| D5 | Expansion complete; all paper body sections drafted | `paper.tex` compiles rough |
| D6 | Paper cross-reviewed and revised | `paper.tex` v2 |
| D7 | **Paper submitted** | `paper.pdf` |

---

## Pre-sprint prep (before D1, ~2h each)

### Both
- Shared/individual Colab Pro agreed
- `.env` with `QWEN_API_KEY` shared securely
- GitHub collaborators set
- Branches: `isaac/approach1`, `alice/analysis`; merge targets: `main` at D3 and D7

### Isaac
- JEDI-7B weights downloaded to Drive (14GB, overnight)
- Confirmed Colab loads JEDI in one test cell (no inference yet)

### Alice
- Deep-read `ui-repair-baseline/baseline_reproduction_results.tex` + `error_analysis.py`
- Poster template picked (CMU style or ACL poster template)
- Ablation matrix sketched on paper

---

# Phase 1 — MVP Sprint (D1–D3)

## Day 1 — Pipeline online

**Deliverable**: end-to-end run works on 5 samples per framework (20 total). Grounding JSON cached. Prompt format chosen.

### Isaac — chunks

| Chunk | Time | Done when |
|-------|------|-----------|
| **C1. JEDI wrapper** — adapt `xlang-ai/OSWorld-G/demo.py` into `grounding/jedi.py`; class with `query(image, instruction) -> {point, raw_output, parse_success}` | 2h | Running on 1 test screenshot returns a click point |
| **C2. Batch grounding** — `grounding/batch.py`; iterate DesignBench samples, query JEDI per issue, cache `grounding/cache/{fw}_{i}.json` | 1h | Runs on 5 samples/framework without crash; JSON files exist |
| **C3. Prompt A/B** — test 3 grounding-block formats on 1 sample: `(a)` pixel coords, `(b)` normalized (0.27, 0.31), `(c)` quadrant language ("upper-left region"). Eyeball which makes Qwen actually attend. | 2h | Winning format chosen; logged to plan |
| **C4. Repair pipeline** — `pipeline/prompts.py` injects winning grounding format into DesignBench repair prompt; `pipeline/run.py` calls Qwen72B on 5 samples/framework | 2h | 20 repair outputs saved to `results/repair-grounded/` |
| **C5. Commit + EOD sync** | 0.5h | Pushed to `isaac/approach1` |

### Alice — chunks

| Chunk | Time | Done when |
|-------|------|-----------|
| **A1. Baseline eval walkthrough** — read `ui-repair-baseline/run_repair.py` `run_evaluation`; understand how `evaluate_repair` produces each metric | 2h | Can verbally describe the CSR/CMLS/CMCS/CLIP pipeline |
| **A2. Ablation matrix + poster skeleton** — decide: what conditions to compare, what lives on the poster (headline, figures, results table, method, qualitative example) | 2h | 1-page ablation matrix doc; poster wireframe sketched |
| **A3. `analysis/compare.py`** — reusable script: takes two results dirs, outputs a markdown table of CSR/CMLS/CMCS/CLIP per framework + overall | 2h | Run on baseline alone produces same numbers as `baseline_reproduction_results.tex` |
| **A4. Gallery overlay** — extend `ui-repair-baseline/gallery.py` to draw click points from grounding JSON on screenshots | 2h | 5 samples render with overlay |
| **A5. Commit + EOD sync** | 0.5h | Pushed to `alice/analysis` |

### EOD sync (15 min)
- Isaac reports grounding JSON schema (shape of `annotations`)
- Alice confirms `compare.py` and gallery accept it
- **Go/no-go call**: if JEDI click points land on defective elements (Isaac eyeball), proceed. If garbage, decide morning-of-D2 pivot to OmniParser.

---

## Day 2 — Full run + numbers

**Deliverable**: 111-sample grounded run complete, baseline-vs-grounded comparison table, headline claim locked.

### Isaac — chunks

| Chunk | Time | Done when |
|-------|------|-----------|
| **C6. Launch full grounded run** — `pipeline/run.py` on all 111 samples, `workers=5`. Runs in background. | 0.5h + 2h wait | All 111 samples in `results/repair-grounded/` |
| **C7. Run evaluation** — reuse `ui-repair-baseline/run_repair.py --eval-only` pointed at grounded results dir | 1h | `evaluator/res/DesignRepair/*_both.json` populated for grounded condition |
| **C8. Debug what broke** — inspect parse failures, compile failures, missing samples | 2h | All 111 samples accounted for |
| **C9. Method section draft** — `sections/method.tex`: grounding pipeline, prompt design, JEDI wrapper. Write while details are fresh. | 3h | ~2 pages of prose |
| **C10. Commit** | 0.5h | Pushed |

### Alice — chunks

| Chunk | Time | Done when |
|-------|------|-----------|
| **A6. Initial metrics** — as Isaac's results land, run `analysis/compare.py` baseline vs. grounded; produce table | 1h | Table lives in a shared place |
| **A7. Per-defect + per-framework breakdown** — slice results by DesignBench's 6 defect types and by framework | 2h | Two additional tables |
| **A8. Qualitative example selection** — 3-4 cases: one clear win, one null, one confusing, one failure. Use gallery overlays. | 2h | Each case has: before/after screenshots, metrics, 2-sentence caption |
| **A9. Poster content draft** — fill wireframe with real numbers, figures, headline claim | 4h | Poster 80% populated (missing only polish) |
| **A10. Commit** | 0.5h | Pushed |

### Syncs
- **Midday** (10 min): numbers gut-check — is direction clear?
- **EOD** (30 min): lock poster headline claim. Write it down.

---

## Day 3 — Poster

**Deliverable**: `poster.pdf` submitted. Both rehearsed.

### Both — chunks

| Chunk | Time | Owner | Done when |
|-------|------|-------|-----------|
| **P1. Finalize numbers + figures** — double-check all tables, re-render figures at poster resolution | 2h | Alice leads, Isaac checks | All numbers in one place, no "TBD" |
| **P2. Pipeline diagram** — clean ASCII or vector diagram of the grounding → repair flow | 1.5h | Isaac | Vector file exported |
| **P3. Write prelim discussion** — 150-word blurb: what worked, what didn't, what's next | 1h | Both | Copy block drafted |
| **P4. Poster layout** — assemble in chosen tool | 3h | Alice leads, Isaac feeds content | Posters renders correctly at final size |
| **P5. Rehearsal** — 2-min walkthrough + 30-sec elevator. Run twice. | 1.5h | Both | Both can deliver without script |
| **P6. Export + submit + deep breath** | 0.5h | Alice | Submitted |

---

# Phase 2 — Expansion + Paper (D4–D7)

## Day 4 — Expansion launch + paper body starts

**Deliverable**: expansion experiment in flight. Results section first pass.

### Morning sync (both, 1h)
- Review poster feedback from advisors/peers
- **Decide expansion** based on what poster revealed:
  - **E1. OmniParser ablation** (~8h total) — rerun pipeline with OmniParser grounding instead of JEDI
  - **E2. Prompt format sweep** (~12h total) — 3-5 formats, full 111-sample run each
  - **E3. LoRA attempt** (~20h total, stretch) — fine-tune grounding model on synthetic defects
- Default: **E1 or E2**. Pick E3 only if Phase 1 ended clean with time to spare.

### Isaac

| Chunk | Time | Done when |
|-------|------|-----------|
| **C11. Expansion setup** — add OmniParser wrapper OR prompt variants OR LoRA training pipeline | 3h | Ready to launch |
| **C12. Launch expansion run** — background | 0.5h + hours of wait | Running |
| **C13. Expand Method section** — now covers both approaches + ablation design | 2h | Method section ~3 pages |
| **C14. Failure-mode taxonomy** — categorize the failures from Phase 1 across defect types | 3h | Taxonomy doc produced |

### Alice

| Chunk | Time | Done when |
|-------|------|-----------|
| **A11. Paper scaffolding** — create `paper/main.tex` with `\input{}`s for sections/; migrate poster content into `sections/` | 2h | Compiles |
| **A12. Draft §6 Results** — expand poster numbers into full prose, add per-framework/per-defect tables | 4h | ~3 pages |
| **A13. Update §2 Related Work** — include references surfaced by poster feedback | 2h | Revised |
| **A14. Commit** | 0.5h | Pushed |

---

## Day 5 — Expansion done, all body sections drafted

**Deliverable**: paper compiles with all body sections in rough draft. Expansion results integrated.

### Isaac

| Chunk | Time | Done when |
|-------|------|-----------|
| **C15. Expansion eval** — run metrics on expansion results | 2h | Expansion table exists |
| **C16. Integrate expansion into Method + Experiments** — sections updated to reflect both conditions | 3h | Sections reflect new results |
| **C17. Figures polish** — pipeline diagram v2 (now with expansion), results figures at paper quality | 3h | Figures submission-ready |
| **C18. Commit** | 0.5h | Pushed |

### Alice

| Chunk | Time | Done when |
|-------|------|-----------|
| **A15. §7 Error Analysis** — deep dive: per-defect-type, per-framework, failure mode categories from Isaac's D4 taxonomy | 3h | ~2 pages |
| **A16. §8 Discussion + Limitations** — honest framing of what worked, what didn't, threats to validity | 2h | ~1.5 pages |
| **A17. §9 Conclusion + Future Work** — tie back to hypothesis; frame cut scope (LoRA, RAG, OmniParser if not done) | 1h | ~0.5 page |
| **A18. §1 Introduction rewrite** — update with actual findings (was speculation before) | 2h | ~1 page |
| **A19. Commit** | 0.5h | Pushed |

### EOD sync (30 min)
- Review all tables one last time for consistency
- Lock final headline claim (may have shifted from poster)

---

## Day 6 — Cross-review + revise

**Deliverable**: paper v2 after cross-review pass.

### Both (morning, 4h solo)

| Chunk | Time | Owner | Done when |
|-------|------|-------|-----------|
| **R1. Draft abstract** — after all results locked | 1h | Either (Alice leads) | 150-word abstract |
| **R2. Consistency sweep** — same numbers across all tables, all citations resolved, no "TBD" | 2h | Alice | No orphan citations, no TBD |
| **R3. Pipeline correctness review** — Isaac re-reads Method to ensure it matches actual code | 1h | Isaac | No discrepancies |

### Both (afternoon, 6h)

| Chunk | Time | Owner | Done when |
|-------|------|-------|-----------|
| **R4. Cross-review** — Isaac reads all Alice's sections; Alice reads Isaac's. Comments in margin or GitHub. | 2h | Both | Full read-through done |
| **R5. Apply feedback** | 3h | Both | All comments addressed or triaged |
| **R6. Commit v2** | 1h | Both | Pushed |

---

## Day 7 — Polish + submit

**Deliverable**: `paper.pdf` submitted.

| Chunk | Time | Owner | Done when |
|-------|------|-------|-----------|
| **S1. Remaining fixes** — typos, figure captions, inline math | 3h | Both | Clean read |
| **S2. Formatting** — confirm against submission template (ACL, etc.); page limit, citation style | 2h | Alice | Compiles cleanly against template |
| **S3. Full read-aloud** — both read aloud, catch awkward prose | 1.5h | Both | Both satisfied |
| **S4. Final compile** — `pdflatex` + `bibtex` + `pdflatex` × 2 | 0.5h | Either | `paper.pdf` produced |
| **S5. Submit** | 0.5h | Alice | Confirmation received |
| **S6. Merge to main, tag `v1.0-submission`** | 0.5h | Isaac | `main` has final state |

---

## Cut list (apply bottom-up if behind)

### Phase 1 cuts
1. Second prompt format in A/B (just ship coords-only)
2. Multi-framework gallery overlays (pick one framework)
3. Per-framework poster breakdown (aggregate only)

### Phase 2 cuts
1. Expansion experiment (ship paper with Phase 1 results + honest future-work framing)
2. Per-defect-type analysis in paper (aggregate tables only)
3. §1 rewrite (leave placeholder + fill in §6 references later)

### Never cut
- Full 111-sample run (baseline vs. grounded)
- Poster with a real headline claim
- Paper with all required sections + compiles cleanly

---

## Merge conflict prevention

- Dirs split cleanly:
  - Isaac: `grounding/`, `pipeline/`, `ui-repair-baseline/run_repair.py`
  - Alice: `analysis/`, `ui-repair-baseline/gallery.py`, `ui-repair-baseline/error_analysis.py`
- Paper: one `.tex` per section under `sections/`; `paper.tex` just has `\input{}`s
- Git: merge feature branches to `main` at D3 and D7

---

## Risks + mitigations

| Risk | Phase | Mitigation |
|------|-------|------------|
| JEDI output garbage on UI | D1 | EOD go/no-go; pivot to OmniParser morning D2 (~4h cost) |
| Qwen ignores grounding coords | D1 | Prompt A/B catches before full run; fallback: natural-language format |
| Colab disconnect mid-batch | D1–D2 | `skip_existing=True`; resumable |
| IssAcc contaminated on grounded | D2 | Exclude from comparison tables, note in limitations |
| Poster null result | D3 | "Null still informs future work"; use expansion to explore why |
| Expansion experiment fails | D4–D5 | Cut it; paper ships with Phase 1 alone |
| Paper gaps at D6 | D7 | Skip polish, fill gaps first |

---

## Sync cadence

| When | What | Duration |
|------|------|----------|
| D1 EOD | JEDI go/no-go | 15m |
| D2 midday | Numbers gut-check | 10m |
| D2 EOD | Lock poster headline | 30m |
| D3 EOD | Poster milestone | — |
| D4 AM | Pick expansion | 1h |
| D5 EOD | Lock paper headline | 30m |
| D6 PM | Cross-review | 2h |
| D7 EOD | Submit | — |

Everything else: async.

---

## Definition of done

### D3 (Poster)
- [ ] Full 111-sample Approach 1 run complete
- [ ] Baseline vs. grounded comparison table produced
- [ ] Poster: pipeline diagram, results table, 1 qualitative example, headline claim
- [ ] Poster rehearsed + submitted

### D7 (Paper)
- [ ] One expansion experiment completed + reported (or explicitly cut with documented reason)
- [ ] 3+ qualitative failure examples documented
- [ ] All sections: abstract, intro, related work, method, experiments, results, error analysis, discussion, limitations, conclusion, future work
- [ ] Paper compiles cleanly under submission template
- [ ] All code on `main` with tag `v1.0-submission`
