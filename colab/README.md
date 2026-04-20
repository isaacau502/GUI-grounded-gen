# Colab Runners

Thin wrappers that clone the repo and delegate to scripts. Keep logic in Python modules — notebooks are just entry points.

## Notebooks

**JEDI and OmniParser live in separate notebooks.** Their dependency trees conflict (vllm needs `transformers>=4.56`, Florence-2 in OmniParser needs `transformers==4.49`), so we can't load both in the same kernel.

- [`jedi_smoke.ipynb`](./jedi_smoke.ipynb) — JEDI-7B grounding smoke test.
  - Deps: `vllm`, `qwen-vl-utils`, latest `transformers`.
  - Run: load weights, query JEDI on a sample screenshot, visualize click.
  - Cells 4-6 are the reference implementation lifted into `grounding/jedi.py`.
- [`omniparser_smoke.ipynb`](./omniparser_smoke.ipynb) — OmniParser v1/v2/structural smoke test.
  - Deps: `transformers==4.49.0`, `Pillow<11`, `easyocr`, `safetensors`, `ultralytics`. **No vllm.**
  - Run: invokes `scripts/prod_omniparser.py`, which loops 3 variants × 5 DesignBench samples, saves JSON + annotated PNGs to `/content/drive/MyDrive/omniparser-test/`.

## Prereqs

- **HuggingFace account** with read token at huggingface.co/settings/tokens (for gated models)
- **Colab Pro** (A100 priority; fallback is V100/T4)
- **VS Code** with the **Google Colab** extension (or browser Colab UI)

## Setup (one-time per notebook)

1. Open the notebook in VS Code → "Connect to Colab" kernel → pick A100 runtime.
2. Run cell 1 (bootstrap) — mounts Drive, clones repo, installs deps. **After first run, restart runtime** once (force-reinstall needs it) then re-run cell 1.
3. Cell 2 (HF token) — paste token via `getpass`.
4. Cell 3 (weight download) — idempotent, skips if already cached in Drive.

## Orchestration

Both notebooks write results to `/content/drive/MyDrive/` subdirectories, so they can share caches:

```
/content/drive/MyDrive/
├── jedi-weights/                 # JEDI-7B (~14GB, one-time download)
├── omniparser-weights/           # OmniParser v2 (~1.3GB, one-time download)
├── designbench-samples/          # 5 test screenshots (uploaded via rclone)
├── jedi-smoke-out/               # JEDI viz PNGs
└── omniparser-test/              # OmniParser JSON + annotated PNGs per variant
```

**Workflow for a full grounding run:**
1. Open `jedi_smoke.ipynb` → run cells → JEDI produces click coords per sample → save as JSON to Drive.
2. Open `omniparser_smoke.ipynb` (separate runtime) → run cells → OmniParser produces element lists per sample → save as JSON to Drive.
3. (Future) an `eval.ipynb` reads both JSON caches, injects grounding into Qwen72B repair prompts, computes DesignBench metrics.

## Weight cache

Weights persist in Drive across runtimes:
- `/content/drive/MyDrive/jedi-weights/` (~14GB)
- `/content/drive/MyDrive/omniparser-weights/` (~1.3GB — `icon_detect/` + `icon_caption_florence/`)

Re-running the weight-download cell skips if already cached.

## Why two notebooks?

Florence-2 (OmniParser's caption model) uses `trust_remote_code=True` to pull Microsoft's custom Python. That code was written for `transformers==4.49.0` in mid-2024 and hasn't been updated. `transformers>=4.50` breaks multiple internal APIs Florence-2 depends on (`_supports_sdpa`, `past_key_values` indexing, `additional_special_tokens`, weight tying).

`vllm` (used by JEDI for fast inference) requires `transformers>=4.56` since vllm 0.8.3. Older vllm 0.8.2 accepts `transformers 4.49` but has a worker-crash bug on Qwen2.5-VL/JEDI. So: **no single transformers version satisfies both stacks**.

Splitting into two notebooks is cleaner than maintaining a 200-line patch stack for Florence-2 compatibility. Each notebook has its own pinned env, both stacks work, orchestration is serial JSON passes through Drive.

See `plans/giggly-snuggling-wand.md` for the full investigation.

## Fallback: browser Colab UI

If the VS Code Colab extension misbehaves, both notebooks also work in browser Colab (upload via Drive or open via GitHub). Commits happen from your local Mac regardless.
