# GUI-grounded-gen

**Repurposing GUI grounding models as visual critics for automated UI code repair.**

CMU 11-711 project — Alice Le, Isaac Au.

## The idea

LLMs produce syntactically valid frontend code but the rendered output often contains visual defects (misalignment, overflow, poor contrast). GUI grounding models trained for web navigation — [JEDI](https://huggingface.co/xlangai/Jedi-7B-1080p), OmniParser — already understand spatial layout and element structure from screenshots. We test whether that understanding transfers to **identifying and repairing visual defects**.

Three planned approaches (see [`report_plan.tex`](report_plan.tex)):

1. **Zero-shot grounding transfer** — use JEDI/OmniParser as-is alongside Qwen2.5-VL-72B for code generation
2. **LoRA fine-tuning** — adapt the grounding model to UI defect data
3. **Multimodal RAG** — augment with retrieved Material Design guidelines

## Repository layout

```
GUI-grounded-gen/
├── report_plan.tex              # Project proposal
│
├── ui-repair-baseline/          # ✅ Baseline reproduction (complete)
│   ├── run_repair.py            #    Qwen2.5-VL on DesignBench repair
│   ├── gallery.py               #    Side-by-side visual comparison
│   ├── error_analysis.py        #    Failure-pattern analysis
│   ├── baseline_reproduction_results.tex
│   └── README.md                #    Baseline-specific docs
│
├── grounding/                   # 🚧 Grounding model wrappers (Approach 1)
│   └── jedi.py
├── pipeline/                    # 🚧 End-to-end repair pipeline
├── colab/                       # 🚧 Thin Colab runners (heavy compute)
│
├── external/                    # DesignBench clone (gitignored)
├── requirements.txt             # Shared Python deps
└── requirements-colab.txt       # Colab-only GPU deps
```

## Current status

- **Baseline**: Qwen2.5-VL-72B and 7B reproduced on DesignBench repair (111 samples across React/Vue/Angular/Vanilla). 72B matches paper within 5% on Angular; 7B shows compile failure patterns that motivate the grounding approach. Details in [`ui-repair-baseline/baseline_reproduction_results.tex`](ui-repair-baseline/baseline_reproduction_results.tex).
- **Approaches 1–3**: in progress.

## Compute split

**Local (Mac)**: write code, small-scale tests, inspect gallery outputs.
**Colab (A100/L4)**: grounding model inference, full 111-sample benchmark runs, LoRA fine-tuning.

Code lives in Python modules (`grounding/`, `pipeline/`) so the same entrypoints run in both environments. Colab notebooks in [`colab/`](colab/) are thin wrappers that `git clone` and delegate to scripts.

## Setup

```bash
# Clone DesignBench (for baseline reproduction)
git clone https://github.com/WebPAI/DesignBench.git external/DesignBench

# Python deps
pip install -r requirements.txt

# Baseline-specific setup (npm parsers, web apps)
cd ui-repair-baseline && bash setup_local.sh
```

See [`ui-repair-baseline/README.md`](ui-repair-baseline/README.md) for detailed baseline instructions.
