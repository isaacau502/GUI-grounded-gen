# Colab Prep Plan — JEDI Grounding Runner (VS Code + Google Colab extension)

**Window:** Tonight, ~2-3h wall clock
**Goal:** Prove JEDI-7B loads + responds on a Colab Pro A100 runtime, weights cached in Drive, smoke-tested coord rescale working. Day 1 grounding code plugs straight into a ready runner.

**Execution model:** VS Code locally with the **Google Colab extension** installed. Open `colab/jedi_smoke.ipynb` in VS Code, select "Connect to Colab" kernel, sign in with the Google account that has Colab Pro. Edit cells in VS Code, execute on A100, commit the `.ipynb` locally.

**Hardware assumption:** Colab Pro → A100 40GB primary. Pro gives priority, not guarantee — cell 4 has a dtype hedge for V100/T4 fallback.

**Non-goal tonight:** full `grounding/jedi.py` module, real batch runs, prompt A/B — those are Day 1 per [workplan.md](workplan.md).

---

## Deliverables

1. HuggingFace token stashed (1Password + Colab user secrets as `HF_TOKEN`)
2. `drive/MyDrive/jedi-weights/` populated with `xlangai/Jedi-7B-1080p`
3. `drive/MyDrive/omniparser-weights/` populated with OmniParser v2 (fallback)
4. `colab/jedi_smoke.ipynb` committed — single notebook that bootstraps, downloads, loads, and smoke-tests
5. `colab/README.md` — how to connect VS Code kernel to Colab, how to run the notebook
6. One DesignBench screenshot chosen with a manually annotated target bbox (for programmatic smoke check)
7. Go/no-go decision on JEDI before Day 1 kickoff

---

## Notebook structure (`colab/jedi_smoke.ipynb`)

One notebook, cells in order:

1. **Bootstrap** — mount Drive, clone/pull repo into `/content/GUI-grounded-gen`, `pip install vllm qwen-vl-utils huggingface_hub matplotlib pillow`
2. **Token** — load HF token from Colab user secrets (`from google.colab import userdata; os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")`)
3. **Weight download** — two-step for speed: `HF_HUB_ENABLE_HF_TRANSFER=1 snapshot_download` to `/content/jedi-weights` (local SSD, ~100 MB/s), then `!cp -r` to `/content/drive/MyDrive/jedi-weights`. Same for OmniParser. `resume_download=True`, idempotent.
4. **JEDI load** — detect GPU, pick dtype, vLLM `LLM(model="/content/drive/MyDrive/jedi-weights", dtype=dtype, gpu_memory_utilization=0.9, max_model_len=8192)` — `dtype = "bfloat16" if "A100" in gpu or "H100" in gpu else "float16"`
5. **Smoke query** — load the chosen DesignBench screenshot, apply `smart_resize`, run `computer_use` tool-call template with a query targeting the annotated element (e.g., "Click the 'Sign up' button")
6. **Coord rescale + bbox check** — inverse `smart_resize` → original pixel coord, assert click is inside annotated bbox, PIL draw red dot + bbox rect, save `/content/drive/MyDrive/jedi-smoke-out/smoke.png` (persists across runtime disconnects), display inline
7. **Decision log** — markdown cell: what worked, what didn't, go/no-go for Day 1

Commit with outputs stripped (VS Code: `Notebook: Clear All Outputs`) — keeps diffs readable and scrubs any token leaks.

---

## Chunks

### C0: HF token + VS Code Colab extension (15 min, hard time-box 30 min)
- Generate read token at huggingface.co/settings/tokens
- Accept JEDI model license (`xlangai/Jedi-7B-1080p`) — confirm not gated, or accept if it is
- Save token to Colab user secrets as `HF_TOKEN`, backup in 1Password
- Install **Google Colab** extension in VS Code
- Sign in with the Google account that has Colab Pro
- Open a blank `.ipynb` in VS Code, select "Connect to Colab" kernel, choose A100 runtime
- Run `!nvidia-smi` — should see A100 (if V100 or T4 shows up, noted — cell 4 dtype hedge handles it)
- **Confirm file mode:** `.ipynb` edits save to the local repo (not Colab runtime filesystem). If extension forces remote-only mode, adjust commit flow in C4.
- **Done when:** VS Code notebook cell shows GPU in output, `.ipynb` lives in local repo
- **Hard stop:** If not working in 30 min, fall back to browser Colab UI tonight, port cells into `.ipynb` committed locally. Don't burn 90 min on wiring.

### C0.5: Pre-check — HF model card + bbox annotation (5 min, do on Mac)
- Open huggingface.co/xlangai/Jedi-7B-1080p, read the "Usage" section
- Confirm inference format: `computer_use` tool-call template vs. custom chat format
- Note vLLM version the card recommends
- Note any special preprocessing beyond `smart_resize`
- Pick one DesignBench screenshot from your local `external/DesignBench/data/DesignRepair/...`, open in macOS Preview → Tools → Show Inspector for pixel coords. Annotate a clear element bbox (e.g., "Sign up" button at `(x1, y1, x2, y2) = (120, 340, 280, 380)`). Write coords + target description + relative repo path into a comment at the top of cell 5.
- **Done when:** template format confirmed, bbox written down, screenshot path noted
- **Why this matters:** if template format is wrong, smoke fails for the wrong reason and you debug for an hour. If bbox isn't pre-chosen, go/no-go is eyeball-driven.

### C1: Scaffold `jedi_smoke.ipynb` — bootstrap + token cells (20 min)
- Create `colab/jedi_smoke.ipynb` in VS Code
- Cell 1 (bootstrap): Drive mount + repo clone + pip install
- Cell 2 (token): load `HF_TOKEN` from Colab userdata, sanity-check with `HfApi().whoami()`
- Run both, confirm clean
- **Done when:** bootstrap idempotent (re-run doesn't break), token loaded

### C2: Weight download cell (25-40 min, mostly wait)
- Cell 3: `os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"` + `pip install hf_transfer` for xet fast path
- `snapshot_download` both models to `/content/jedi-weights` and `/content/omniparser-weights` (local SSD, much faster than Drive)
- Then `!cp -r /content/jedi-weights /content/drive/MyDrive/jedi-weights` (same for OmniParser) — one-time persistence cost
- `resume_download=True`, idempotent on re-run
- Kick off, let it run. Work on C3 draft while waiting.
- **Done when:** both dirs exist in Drive, sizes match (JEDI ~14GB, OmniParser ~8GB)
- **Risk:** Colab disconnect mid-download. Cell is idempotent; local SSD lost on disconnect but HF transfer resumes from Drive state.

### C3: JEDI load + smoke query cells (45 min)
- Cell 4 (load): detect GPU with `torch.cuda.get_device_name(0)`, pick `dtype = "bfloat16" if "A100" in gpu or "H100" in gpu else "float16"`, vLLM load from Drive at `gpu_memory_utilization=0.9, max_model_len=8192`
- Cell 5 (smoke): load chosen DesignBench screenshot, preprocess with `smart_resize`, run `computer_use` template with the query matching the annotated bbox
- Cell 6 (rescale + bbox check): inverse smart_resize → original coord, `assert bbox.contains(coord)`, PIL draw red dot + green bbox rect, save to `/content/drive/MyDrive/jedi-smoke-out/smoke.png` (persists across disconnects), inline display
- **Done when:** assert passes (click is inside the annotated bbox), visual sanity check confirms
- **This is the smoke test that replaces a unit test** per research code bar

### C4: README + commit (20 min)
- Strip outputs from notebook (VS Code: `Notebook: Clear All Outputs`)
- Add `colab/out/` to `.gitignore` (binary artifacts don't belong in git)
- Write `colab/README.md`:
  - Prereqs: HF token, Colab Pro account, VS Code + Google Colab extension
  - Connect VS Code → Colab kernel (install extension, sign in, pick A100)
  - Run notebook top-to-bottom
  - Expected: assert passes, red dot inside green bbox, console prints coord
  - Where smoke output lives: `/content/drive/MyDrive/jedi-smoke-out/smoke.png`
  - Fallback if JEDI fails: pivot to OmniParser cell (stub for now)
- From local Mac (not Colab runtime): `git add colab/ .gitignore && git commit -m "colab prep: jedi smoke notebook" && git push`
- **Done when:** pushed, Alice can pull and inspect

### C5: Go/no-go (10 min)
- If C3 assert passes → **go**, Day 1 builds `grounding/jedi.py` by lifting cells 4-6 into a `.py` module
- If JEDI output is garbage or vLLM keeps crashing → **pivot to OmniParser** Day 1
- Write decision into Cell 7 (decision log markdown) and commit

---

## Time budget

| Chunk | Min |
|---|---|
| C0 token + Colab extension | 15 (hard stop 30) |
| C0.5 HF card + bbox annotation (on Mac) | 5 |
| C1 bootstrap + token cells | 20 |
| C2 weight download (hf_transfer + local→Drive) | 35 |
| C3 load + smoke cells | 45 |
| C4 README + commit | 20 |
| C5 decision | 10 |
| **Total** | **~2h30m** |

C2 is mostly wall-clock wait. Draft C3 cells in VS Code while it runs.

---

## Risks

- **Google Colab VS Code extension auth loop / mismatch** — hard time-box C0 at 30 min, fall back to browser Colab if broken. Not a blocker.
- **Runtime disconnects kill kernel** — cells are idempotent, re-run from top; weights persist in Drive, smoke output persists in Drive
- **vLLM install breaks on Colab CUDA** — pin to version from JEDI official repo README (checked in C0.5)
- **JEDI gated on HF** — accept license in C0; if blocked, OmniParser only
- **smart_resize coord rescale wrong** — C3 bbox assert catches it; debug before Day 1
- **JEDI's `computer_use` template differs from Qwen2.5-VL's** — caught in C0.5 pre-check
- **Colab Pro falls back to V100/T4 during high demand** — cell 4 GPU-detect + dtype hedge handles it; bf16 on A100, fp16 otherwise

---

## Why VS Code over browser Colab UI

- Same editor Alice uses on Mac — less tool sprawl
- Notebooks edited alongside repo files, not in a separate browser tab
- Copilot/CC autocomplete in the notebook
- `git diff` still works on `.ipynb` (outputs stripped)
- Terminal + notebook in one window

## What this unblocks for Day 1

- `grounding/jedi.py` lifts cells 4-6 directly — same code, wrapped in a function
- Weight path stable (Drive mount), no re-download per session
- Coord rescale validated with a programmatic bbox check, not vibes
- Go/no-go on JEDI vs OmniParser locked before Day 1 coding starts
