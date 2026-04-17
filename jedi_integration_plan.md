# JEDI Integration Plan — Approach 1

**Goal**: Integrate JEDI-7B (a computer-use agent model) as a visual defect localizer in a DesignBench UI code repair pipeline, without touching the working baseline.

**Hypothesis**: Computer-use agent methods (trained on navigation: "click X to do Y") transfer to defect localization ("click the element with defect type X").

---

## Key facts driving the design

1. **JEDI is not a detector.** It takes `(image, natural_language_instruction)` and returns *one click coordinate*, not a list of bboxes. It uses a `computer_use` tool-call template.
2. **JEDI uses vLLM**, not plain transformers. Canonical inference code is `demo.py` in [xlang-ai/OSWorld-G](https://github.com/xlang-ai/OSWorld-G).
3. **DesignBench provides oracle issue types** in `data/DesignRepair/{fw}/{i}/{i}.json`. We use these as the query source rather than predicting them — isolates the transfer question to localization.
4. **Grounding is deterministic**: run once, cache output, all downstream work runs without GPU.

---

## Two-environment architecture

```
┌──────────────────────────┐          ┌──────────────────────────┐
│ COLAB (GPU, one-time)    │          │ LOCAL MAC                │
│                          │          │                          │
│ grounding/batch.py       │          │ pipeline/run.py          │
│   ├─ Load JEDI via vLLM  │          │   ├─ Read grounding JSON │
│   ├─ For each sample:    │  writes  │   ├─ Build prompt        │
│   │   For each issue:    │ ────────►│   ├─ Call Qwen72B API    │
│   │     JEDI(img, query) │  reads   │   └─ Save repair output  │
│   └─ Save JSON to repo   │          │                          │
│                          │          │ ui-repair-baseline/      │
│                          │          │   run eval as usual      │
└──────────────────────────┘          └──────────────────────────┘
```

**Rationale**: avoids mixing Python-vLLM-GPU environment with Node-DesignBench-evaluation environment. They share state via committed JSON files, not live calls.

---

## Directory additions

```
GUI-grounded-gen/
├── grounding/
│   ├── __init__.py          # (exists, stub)
│   ├── jedi.py              # JEDI wrapper class (vLLM + tool-call parsing)
│   ├── batch.py             # Batch inference over DesignBench
│   └── cache/               # Output: {fw}_{i}_grounding.json (committed)
├── pipeline/
│   ├── __init__.py          # (exists, stub)
│   ├── prompts.py           # Extended repair prompt with grounding section
│   └── run.py               # End-to-end: JSON → Qwen72B → save
└── colab/
    └── run_jedi_batch.ipynb # Thin notebook: git clone + install + run batch.py
```

Untouched: `ui-repair-baseline/` (baseline results are already committed and working).

---

## Data flow per sample

### Inputs (from DesignBench)
- `data/DesignRepair/{fw}/{i}/{i}.png` — broken UI screenshot
- `data/DesignRepair/{fw}/{i}/{i}.json` — contains `issues` array (oracle defect types)
- Source code — in the same JSON or as separate file depending on framework

### Stage 1 — Grounding (Colab, GPU)

```python
for sample in designbench_samples:
    issues = sample["issues"]  # e.g., ["text_overlap", "misalignment"]
    annotations = []
    for issue in issues:
        query = f"click the element with {issue['type']}"
        result = jedi.query(sample.image_path, query)
        annotations.append({
            "issue_type": issue["type"],
            "issue_description": issue["description"],
            "query": query,
            "point": result["point"],           # (x, y) or None
            "parse_success": result["parse_success"],
            "raw_output": result["raw_output"],
        })
    save_json(f"grounding/cache/{fw}_{sample.id}.json", {
        "framework": fw,
        "sample_id": sample.id,
        "image_size": (w, h),
        "annotations": annotations,
    })
```

### Stage 2 — Repair (Local, Qwen API)

```python
for sample in designbench_samples:
    grounding = load_json(f"grounding/cache/{fw}_{sample.id}.json")
    system, user = build_grounded_repair_prompt(
        screenshot=sample.image_path,
        source_code=sample.code,
        grounding=grounding,
        existing_prompt_template=designbench_repair_prompt,
    )
    response = qwen_api.complete(system, user, image=sample.image_path)
    save_repair_output(response, fw, sample.id, mode="grounded")
```

### Stage 3 — Evaluation (Local, unchanged)

Reuses existing `ui-repair-baseline/run_repair.py --eval-only` against the new results directory.

---

## JSON schemas

### Grounding cache (`grounding/cache/react_11.json`)

```json
{
  "framework": "react",
  "sample_id": 11,
  "image_path": "data/DesignRepair/react/11/11.png",
  "image_size": [1920, 1080],
  "annotations": [
    {
      "issue_type": "text_overlap",
      "issue_description": "Text content overlaps with adjacent elements",
      "query": "click the element with text overlap",
      "point": [512, 340],
      "parse_success": true,
      "raw_output": "<tool_call>{\"name\":\"computer_use\",\"arguments\":{\"action\":\"left_click\",\"coordinate\":[512,340]}}</tool_call>"
    }
  ]
}
```

### Prompt augmentation

Inserted into the existing DesignBench `repair_prompt.py` template, between the source code block and the instructions:

```
VISUAL GROUNDING (from GUI grounding model):
The following defects were localized on the screenshot by a UI grounding
model. Each annotation gives the approximate pixel location of a defect.
Use these as hints for which element to fix and where.

  - text_overlap near pixel (512, 340)
  - misalignment near pixel (128, 200)

Image dimensions: 1920x1080.
```

---

## Module interfaces

```python
# grounding/jedi.py
class JEDI:
    def __init__(self, model_path: str = "xlangai/Jedi-7B-1080p"):
        """Load model via vLLM. One-time (~60s startup)."""

    def query(self, image_path: str, instruction: str) -> dict:
        """Single inference call.
        Returns {
            'point': (x, y) | None,       # parsed click coordinate, original image space
            'raw_output': str,             # raw tool-call text
            'parse_success': bool,         # whether coordinate parse succeeded
            'original_size': (w, h),
            'resized_size': (w, h),        # smart_resize output
        }
        """

# grounding/batch.py
def run_batch(
    designbench_root: str,
    output_dir: str,
    frameworks: list[str] = ["react", "vue", "angular", "vanilla"],
    max_samples: int | None = None,
    query_template: str = "click the element with {issue_type}",
    skip_existing: bool = True,
) -> None:
    """Iterate all samples, run JEDI per issue, save JSON."""

# pipeline/prompts.py
def build_grounded_repair_prompt(
    framework: str,
    source_code: str,
    grounding: dict,
    existing_issues: list[dict],
) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) ready for Qwen API."""

# pipeline/run.py
def run_grounded_repair(
    grounding_cache_dir: str = "grounding/cache",
    output_dir: str = "results/repair-grounded",
    model: str = "qwen2.5-vl-72b-instruct",
    frameworks: list[str] = None,
    max_samples: int | None = None,
    workers: int = 5,
) -> None:
    """Full pipeline. Parallel worker pattern from baseline run_repair.py."""
```

---

## Design decisions (locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Issue source for JEDI queries | **Oracle** (use DesignBench's ground-truth issue types) | Isolates the localization transfer question. "Given we know what's wrong, can JEDI find where?" |
| Query template | `"click the element with {issue_type}"` | Closest to JEDI's training distribution (computer_use verbs). Ablate if time permits. |
| One call per issue vs one per sample | **Per issue** | Yields multiple coordinates, one per known defect. |
| Grounding cache location | **Committed to repo** (`grounding/cache/`) | <1MB total, reproducible, no Drive sync pain. |
| Parse failure handling | **Include issue without coordinate** | Graceful degradation — Qwen still gets the issue type, just without pixel hint. |
| Generation model | **Qwen2.5-VL-72B** | Baseline shows 7B has compile failures that would mask grounding effects. |
| Coord rescale verification | **Visual inspection during smoke test** (step 4) | Overlay click points on screenshots; if coords are wrong, eyeball catches it immediately. No separate test. |
| IssAcc reporting on grounded condition | **Do not report** (paper notes methodological limitation) | Grounded prompt leaks oracle issue labels → Qwen can trivially copy them to `[ISSUES]` → artificially perfect IssAcc, not comparable to baseline. |
| Prompt format iteration | **1h A/B test on Day 1 (coords / normalized / natural-language)** | Whether Qwen attends to pixel coords at all is unknown. Cheap to find out before launching a 2h full run. |

---

## Implementation order (~4.5 hours Day 1)

1. `grounding/jedi.py` — wrapper, adapted from xlang-ai/OSWorld-G `demo.py` — 60 min
2. `grounding/batch.py` — loop over DesignBench samples, save JSON — 30 min
3. `colab/run_jedi_batch.ipynb` — thin notebook: clone repo, pip install, run batch.py — 15 min
4. **Smoke test** on Colab: 5 samples × 4 frameworks. Overlay click points on screenshots, eyeball whether they land on defective elements. This is the verification — if coords are garbage (wrong rescale, wrong model behavior, etc.) you see it here. — 60 min
5. **Prompt format A/B** — test 3 grounding-block variants on 1 sample, pick winner — 60 min
   - Variant 1: `"text_overlap near pixel (512, 340)"`
   - Variant 2: `"text_overlap near normalized (0.27, 0.31)"`
   - Variant 3: `"text_overlap in upper-left region"` (quadrant inference)
6. `pipeline/prompts.py` — extend repair prompt with winning format — 30 min
7. `pipeline/run.py` — Qwen integration — 45 min
8. End-to-end run on one sample, inspect repaired output — 15 min

Checkpoints:
- **After step 4**: if JEDI coordinates look nonsensical on UI screenshots (trained on OS/desktop, not web pages; or rescale bug), pivot to a different query phrasing or cut losses to OmniParser on Day 2 morning.
- **After step 5**: if none of the 3 prompt formats cause Qwen to meaningfully attend to the grounding, flag as methodological null result — still a valid paper finding.

---

## Risks + mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| JEDI produces garbage on defect queries (trained on functional, not diagnostic, queries) | Medium-high | Day 1 step 4 smoke test. If bad, try alternate query phrasings before pivoting. |
| vLLM install fails on Colab | Low | Fallback to plain transformers (slower but works) |
| Click points fall outside image bounds | Low | Clip to image, flag in JSON |
| Qwen ignores the grounding coordinates in the prompt | Medium | Ablate with/without; if ignored, make prompt more forceful ("the defect IS at...") |
| Coordinate rescaling bug (resized vs original space) | Medium | Unit test: pick known sample, verify coord lands on expected element |
| Tool-call parse failures (malformed output) | Low-medium | Regex fallback; log parse failures; graceful degrade |

---

## Evaluation plan

Reuse DesignBench's existing metrics:
- **CSR** (compile success rate)
- **CMLS** (AST edit location similarity)
- **CMCS** (CMLS × CodeBLEU)
- **CLIP** (rendered output similarity)
- ~~**IssAcc**~~ — **NOT reported on grounded condition** due to oracle issue leakage via the grounding prompt. Paper notes this as methodological limitation.

**Primary comparison**: grounding-augmented Qwen72B vs. baseline Qwen72B (no grounding). Same samples, same evaluation pipeline.

**Secondary analysis** (Day 2):
- Per defect-type breakdown — does grounding help more for spatial defects (overflow, occlusion) than property defects (color, contrast)?
- Per framework breakdown
- Correlation between JEDI parse success and downstream repair quality

---

## What this plan explicitly does NOT do

- Does not modify the baseline (`ui-repair-baseline/`)
- Does not train or fine-tune JEDI
- Does not construct a RAG knowledge base
- Does not predict issue types (uses oracle)
- Does not compare JEDI vs. OmniParser (single-model study)
- Does not run on anything other than DesignBench repair split

These are explicit scope cuts for the 3-day sprint. Framed in the paper's Future Work.

---

## Definition of done for this plan

- [ ] `grounding/jedi.py` loads JEDI on Colab, produces a click point for a test image
- [ ] Smoke test visual inspection: click points land on defective elements for 5 samples × 4 frameworks
- [ ] `grounding/batch.py` processes all 111 DesignBench samples, outputs JSON files
- [ ] Prompt format A/B tested on 1 sample, winning variant chosen
- [ ] `pipeline/prompts.py` uses chosen grounding format
- [ ] `pipeline/run.py` processes one sample end-to-end, saves repair output
- [ ] Full 111-sample grounded run completed
- [ ] CSR, CMLS, CMCS, CLIP computed and compared against baseline (IssAcc excluded per methodology)
- [ ] Results feed into the paper's Results section
