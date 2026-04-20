# poster/ — self-contained resources for writing the poster

All the synthesis + narrative + stats artifacts needed to write the
DesignBench grounded-repair poster, in one directory.

## What's here

### Drive the process
- **[poster_agent.md](poster_agent.md)** — feed this to any LLM.
  14-question questionnaire, then generates poster-ready sections,
  figure specs, layout grid, and presentation script. Project context
  baked in, no need to re-research.
- **[poster_draft_v1.md](poster_draft_v1.md)** — first-pass poster
  content generated using default answers. Paste-ready into PowerPoint /
  Keynote / Figma / LaTeX. 10 panels + presentation notes + Q&A.

### The synthesis
- **[RESULTS.md](RESULTS.md)** — **read this first.** Collated one-stop
  reference. Merges everything below into a single document.
- **[results_overview.md](results_overview.md)** — tier-ranked findings
  (Tier 1 = poster headline, Tier 2 = body text, Tier 3 = only if asked),
  each with a 1-line theorized mechanism.
- **[poster_stats.md](poster_stats.md)** — full α=0.05 significance
  table. 27 significant gains, 12 significant regressions, 12 marginals
  (0.05 ≤ p < 0.10). Sorted by p-value.
- **[per_defect.md](per_defect.md)** — per-defect-type slicing of all
  findings. Shows where grounding helps which defect type.

### Context
- **[ablation_log.md](ablation_log.md)** — copy of the project-root
  ablation log. Full run-by-run history of every experimental
  configuration with commits. Project root holds the canonical copy;
  this is the snapshot the poster was built from.

## What's NOT here (but relevant)

- **`../results/eval/*.json`** — raw DesignBench eval JSONs (per-framework
  per-sample metrics). Keep those in `results/eval/` because scripts
  write there and they're not poster-ready.
- **`../scripts/`** — the runners + stats analysis + render orchestrators.
  Listed in RESULTS.md §9 (Reproducibility).
- **`../grounding/`** — the grounding wrappers (omniparser.py, omniparser2.py,
  omniparser_structural.py, jedi.py).
- **`../ablation_log.md`** — canonical live log. `poster/ablation_log.md`
  is a snapshot.

## Workflow

1. **For a fresh poster draft:** paste `poster_agent.md` into a new
   Claude/ChatGPT chat. It will ask the 14 questions, then output
   poster-ready content.
2. **For a quick copy-paste:** use `poster_draft_v1.md` as-is and tweak.
3. **For deep reference while writing:** `RESULTS.md` has the one-stop
   collation. `poster_stats.md` has the defensible numbers.
4. **For a figure:** figure specs (data source + style + axis labels +
   size hint) are inline in `poster_draft_v1.md` and at the end of
   `poster_agent.md` Step 2 section C.

## Key numbers to memorize for Q&A

- **Hero:** Qwen2.5-VL-7B on Angular with OmniParser → CLIP +.141
  (p=.007), SSIM +.111 (p=.002), CSR 57% → 75%.
- **Cross-framework 72B:** OmniParser gives visual-metric gains on 3 of
  4 frameworks, all p ≤ .045. AST trends down, never significant.
- **Cautionary:** 7B + JEDI on React → CSR 1.00 → 0.50 (p<.001).
- **Methodology:** CLIP +.021 ** up, SSIM −.016 ** down on 7B Vue
  with either grounding → CLIP > SSIM.
- **N:** 28 per framework-model cell; 68 for the pooled alignment-defect
  slice (which is the cleanest CMLS-vs-CLIP divergence illustration).
- **Stat method:** paired Wilcoxon signed-rank (continuous), McNemar
  exact binomial (CSR), α = 0.05.

## Commit this was built from

See `ablation_log.md` for the full timeline. The poster snapshot is from
commit following `4255d67` (poster/ created) + `9a3e728` (RESULTS.md
added) + any subsequent stats refresh.
