# Colab Runners

Thin wrappers that clone the repo and delegate to scripts. Keep logic in Python modules — notebooks are just entry points.

## Active notebook

- [`jedi_smoke.ipynb`](./jedi_smoke.ipynb) — JEDI-7B grounding smoke test. Load weights, run one click query on one DesignBench screenshot, verify the coord lands in an annotated bbox. Day 1 `grounding/jedi.py` lifts cells 4-6 directly.

## Prereqs

- **HuggingFace account** with read token at huggingface.co/settings/tokens
- **Colab Pro** (A100 priority; Pro fallback is V100/T4, handled by dtype hedge in cell 4)
- **VS Code** with the **Google Colab** extension installed

## Setup (one time)

1. In Colab, open Secrets (key icon, left sidebar) and add `HF_TOKEN` = your token
2. Accept the JEDI license at huggingface.co/xlangai/Jedi-7B-1080p (if gated)
3. In VS Code, install the **Google Colab** extension, sign in with the Google account that has Pro
4. Open `colab/jedi_smoke.ipynb` in VS Code, select "Connect to Colab" kernel, pick A100 runtime

## Running the smoke

Before running cells: pick one DesignBench screenshot locally and annotate a target bbox. See the comment at top of cell 5 in the notebook for the format.

Run cells top-to-bottom. Expected result:
- Cell 4 prints GPU name + dtype chosen
- Cell 5 prints raw JEDI output (a tool call with a coord)
- Cell 6 prints the parsed coord, asserts it's inside the bbox, saves `smoke.png` to `/content/drive/MyDrive/jedi-smoke-out/`

If the assert passes, JEDI is viable. If it crashes or the click is outside the bbox, debug before Day 1.

## Weight cache

Weights persist at:
- `/content/drive/MyDrive/jedi-weights/` (~14GB)
- `/content/drive/MyDrive/omniparser-weights/` (~8GB, fallback)

Re-running cell 3 skips download if already cached.

## Fallback: browser Colab UI

If the VS Code Colab extension doesn't connect cleanly within ~30 min, run `jedi_smoke.ipynb` in browser Colab instead (upload via Drive or re-open via GitHub). Commits happen from your local Mac regardless.
