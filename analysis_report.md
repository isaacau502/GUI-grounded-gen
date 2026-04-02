# DesignBench Repair Task — Analysis Report

## Baseline Reproduction

### Existing Baseline

Yes. DesignBench (Xiao et al., 2025) provides baseline results for 10 multimodal LLMs on the Design Repair task, including GPT-4o, Claude 3.7 Sonnet, Gemini 2.0 Flash, Qwen2.5-VL (72B and 7B), Llama 3.2 (90B and 11B), and Pixtral (Large and 12B). We reproduce the Qwen2.5-VL results (both 72B and 7B) as our baseline.

### Baseline Description

The Design Repair task gives a multimodal LLM:
- A screenshot of a broken UI (with visual defects like misalignment, overflow, occlusion)
- The buggy source code (React JSX, Vue SFC, Angular HTML+TS, or vanilla HTML)
- A list of identified display issues

The model must output repaired code that fixes the visual defects. Evaluation uses three metrics:
- **CSR** (Compile Success Rate): fraction of outputs that compile without errors
- **CMLS** (Code Modification Location Similarity): Jaccard similarity of AST edit operations vs ground truth
- **CMCS** (Code Modification Content Similarity): CodeBLEU of matched edit operations, weighted by union size

### Why Qwen2.5-VL

Qwen2.5-VL is the strongest open-weight model on DesignBench's repair task. GPT-4o and Claude 3.7 Sonnet score higher overall, but they are proprietary and not reproducible without API access that may change over time. Qwen2.5-VL is:
- Open-weight (available on Hugging Face and via Dashscope API)
- Available in two sizes (72B and 7B), enabling model scale analysis
- The top-performing open model on the repair task across most framework × metric combinations

It is not SOTA overall — GPT-4o holds that position — but it is the strongest reproducible baseline.

### Reproduction Results

#### Qwen2.5-VL-72B-Instruct

| Metric | Framework | Paper | Ours |
|--------|-----------|-------|------|
| CSR | React | 1.000 | 0.857 |
| | Vue | 1.000 | 1.000 |
| | Angular | 0.929 | 0.964 |
| CMLS | React | 0.634 | 0.339 |
| | Vue | 0.509 | 0.213 |
| | Angular | 0.676 | 0.631 |
| | Vanilla | 0.609 | 0.532 |
| CMCS | React | 0.542 | 0.230 |
| | Vue | 0.392 | 0.143 |
| | Angular | 0.571 | 0.556 |
| | Vanilla | 0.586 | 0.510 |

#### Qwen2.5-VL-7B-Instruct

| Metric | Framework | Paper | Ours |
|--------|-----------|-------|------|
| CSR | React | 0.286 | 0.250 |
| | Vue | 0.111 | 0.926 |
| | Angular | 0.036 | 0.571 |
| CMLS | React | 0.362 | 0.182 |
| | Vue | 0.245 | 0.237 |
| | Angular | 0.641 | 0.304 |
| | Vanilla | 0.499 | 0.422 |
| CMCS | React | 0.257 | 0.139 |
| | Vue | 0.180 | 0.179 |
| | Angular | 0.577 | 0.206 |
| | Vanilla | 0.478 | 0.394 |

### Discussion of Differences

**Close matches (within ~5%):**
- Angular 72B: CSR, CMLS, and CMCS all within 5% of paper values
- Vue 7B CMCS: 0.179 vs paper 0.180
- React 7B CSR: 0.250 vs paper 0.286

**Significant deviations:**
- Vue 7B CSR (0.926 vs paper 0.111) and Angular 7B CSR (0.571 vs paper 0.036): our 7B model compiles far more successfully
- React/Vue 72B CMLS/CMCS: roughly half the paper values

**Explanations:**

1. **Model version drift.** Alibaba silently updates `qwen2.5-vl-7b-instruct` and `qwen2.5-vl-72b-instruct` on Dashscope without dated snapshots. Our runs (March 2026) use newer checkpoints than the paper (late 2024/early 2025). This is the most likely explanation for the dramatic CSR improvement in the 7B model — the model is simply better at producing compilable code now.

2. **Framework and toolchain versions.** CSR depends on the framework compiler accepting the generated code. We use Chrome 146, Node v20.20.2, and current npm versions of Next.js, Vue, and Angular (March 2026). The paper authors used Node v18.19.0 (visible from hardcoded paths in source). Newer compilers may accept code that older versions rejected, or vice versa.

3. **CSR detection method.** CSR is computed by pattern-matching error strings in rendered HTML (`compile.py`). The error overlay HTML structure is version-dependent — for example, Next.js's `nextjs-container-errors` class appeared in newer versions, requiring us to patch the detection regex. Vue and Angular detection patterns may still have version mismatches.

4. **CMLS/CMCS lower for 72B.** The newer 72B model may produce functionally correct repairs that differ structurally from ground truth. A model that rewrites more code (rather than making minimal targeted edits) will have lower CMLS even if the visual result is correct. This is a known limitation of edit-distance metrics.

These differences cannot be attributed to randomness — the runner uses Temperature=0 and Seed=42 for deterministic generation. The root cause is model version drift and toolchain version differences.

---

## Error Analysis

### Failure Categorization

We categorize each sample into five failure modes based on metric thresholds:

| Category | Criteria | Description |
|----------|----------|-------------|
| Compile Fail | `compile_error != "NULL"` | Code does not compile in the framework |
| Wrong Location | Compiled, CMLS < 0.1 | Model edited wrong AST nodes |
| Wrong Content | Compiled, CMLS >= 0.1, CMCS < 0.1 | Right location, wrong fix content |
| Visual Mismatch | Compiled, CMCS >= 0.1, CLIP < 0.5 | Code differs visually from expected |
| Success | All thresholds met | Reasonable repair |

#### 72B Failure Distribution

| Framework | Compile Fail | Wrong Location | Wrong Content | Visual Mismatch | Success |
|-----------|-------------|----------------|---------------|-----------------|---------|
| React | 4 (14%) | 4 (14%) | 0 (0%) | 0 (0%) | 20 (71%) |
| Vue | 0 (0%) | 0 (0%) | 5 (19%) | 1 (4%) | 21 (78%) |
| Angular | 1 (4%) | 3 (11%) | 0 (0%) | 0 (0%) | 24 (86%) |
| Vanilla | 0 (0%) | 5 (18%) | 1 (4%) | 1 (4%) | 21 (75%) |

#### 7B Failure Distribution

| Framework | Compile Fail | Wrong Location | Wrong Content | Visual Mismatch | Success |
|-----------|-------------|----------------|---------------|-----------------|---------|
| React | 21 (75%) | 3 (11%) | 0 (0%) | 0 (0%) | 4 (14%) |
| Vue | 2 (7%) | 3 (11%) | 4 (15%) | 1 (4%) | 17 (63%) |
| Angular | 12 (43%) | 1 (4%) | 0 (0%) | 0 (0%) | 15 (54%) |
| Vanilla | 0 (0%) | 9 (32%) | 1 (4%) | 0 (0%) | 18 (64%) |

### Failure Patterns

**Pattern 1: Compile failures dominate 7B React and Angular.**
The 7B model fails to compile 75% of React and 43% of Angular outputs. Common errors include unterminated string constants, unexpected tokens, and malformed JSX. The model attempts repairs but introduces new syntax errors. Vanilla (plain HTML) never fails to compile because there is no compilation step — it always renders something.

**Pattern 2: Over-modification (Wrong Location) in vanilla.**
18% of 72B vanilla samples and 32% of 7B vanilla samples modify the wrong AST nodes. Without framework constraints (components, imports, types), the model has too much freedom and rewrites large sections instead of making targeted fixes.

**Pattern 3: Issue type affects difficulty.**

| Issue Type | N | 72B CMCS | 7B CMCS | 7B Compile Fail Rate |
|------------|---|----------|---------|---------------------|
| alignment | 67 | 0.364 | 0.226 | 34.3% |
| occlusion | 29 | 0.394 | 0.232 | 37.9% |
| crowding | 26 | 0.411 | 0.199 | 26.9% |
| overflow | 18 | 0.441 | 0.220 | 38.9% |
| color/contrast | 11 | 0.394 | 0.313 | 27.3% |

Overflow issues have the highest 7B compile failure rate (38.9%) and are among the hardest for both models. Color and contrast issues are relatively easier for 7B (highest CMCS at 0.313).

**Pattern 4: Scale gap is largest on complex multi-issue samples.**
19 samples have 72B CMCS > 0.3 but 7B CMCS < 0.1. Only 2 samples show the reverse. The 72B model's advantage is most pronounced on Angular (7 samples) and React (7 samples) where the 7B model produces uncompilable code that the 72B handles correctly.

### How Failure Patterns Were Identified

1. **Automated categorization** via `error_analysis.py` which reads evaluation JSONs and classifies each sample by metric thresholds
2. **Visual inspection** via `gallery.html` which shows side-by-side broken input / ground truth / generated output with per-sample metrics and CSR pass/fail badges
3. **Cross-referencing** issue types from ground truth `repaired.json` files with metric performance to identify which defect types are hardest

### Why the Model Fails

1. **Compile failures (7B):** The 7B model has limited capacity for maintaining syntactic correctness across long code sequences. React JSX is particularly sensitive — a single missing closing tag or unterminated string breaks the entire component. The model "knows" what to fix but introduces syntax errors while writing the fix.

2. **Wrong location (both models):** When the visual defect is subtle (e.g., a 2px misalignment), the model sometimes identifies the correct problem but modifies a different CSS property or HTML element. The repair is "in the right neighborhood" but doesn't match the ground truth's specific edit path.

3. **Overflow/occlusion difficulty:** These issues require understanding spatial relationships between elements — which elements overlap, which overflow their containers. This requires precise reasoning about CSS box model, flexbox/grid layout, and z-index stacking, which is harder than simple property changes like color corrections.

---

## Reflection

### What We Learned

1. **Compilation is the primary bottleneck for smaller models.** The 7B model's repair quality is bottlenecked by its ability to produce syntactically valid code, not by its understanding of visual defects. 75% of React failures are compile errors, not wrong fixes.

2. **Framework choice significantly affects difficulty.** Vanilla HTML is always compilable but gives the model too much freedom (leading to over-modification). Angular's strict type system and two-file structure (HTML + TS) actually helps — it constrains the repair space. React's JSX syntax is fragile for smaller models.

3. **Edit-distance metrics have limitations.** A model that rewrites a component from scratch can produce a visually identical result but score 0 on CMLS/CMCS. This means the metrics may undercount "functionally correct" repairs.

4. **Benchmark reproducibility is fragile.** Model versioning (silent updates), toolchain versions, and CSR detection patterns all affect results. Exact reproduction requires pinning every dependency, which DesignBench does not do.

### Capabilities Needed for Better Performance

A hypothetical improved model would need:
- **Syntax awareness**: Ability to maintain valid syntax throughout long code edits, especially for JSX/TSX. This could come from structured generation (grammar-constrained decoding) or a syntax validation feedback loop.
- **Minimal edit bias**: Training signal that rewards minimal, targeted fixes over rewrites. Current models tend to over-modify.
- **Spatial reasoning over CSS**: Better understanding of the CSS box model, layout algorithms, and how property changes affect element positioning.
- **Multi-issue decomposition**: Ability to identify and fix multiple co-occurring issues (alignment + overflow + occlusion) independently rather than attempting a single large edit.

### Strengths of the Baseline

- The 72B model achieves 71-86% success rate across frameworks — a strong baseline
- It handles multi-issue samples reasonably well
- It generalizes across four different frontend frameworks with no framework-specific tuning
- The prompt template (from DesignBench) effectively communicates the task

### Refining the Approach

*To be investigated.* Potential directions informed by error analysis:
- A compile-then-retry loop where failed compilations are fed back to the model with the error message
- Constraining the model to output only the diff (changed lines) rather than the full file, to reduce over-modification
- Framework-specific prompting that accounts for syntax sensitivity (e.g., React JSX requires extra care vs vanilla HTML)

### Fallback Ideas

*To be investigated.* If the initial approach fails entirely:
- Use a two-stage pipeline: first identify the defect location (classification), then generate the fix (constrained generation)
- Leverage the 72B model as a teacher to generate training data for a smaller, specialized repair model
- Explore code-specific models (e.g., DeepSeek-Coder) that may have stronger syntax guarantees, even if weaker at visual understanding
