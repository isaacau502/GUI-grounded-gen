# Setup Prompt for Claude

Paste this into a fresh Claude Code session on a Mac that has the repo cloned and a DesignBench tarball ready. Claude will walk through the full eval-stack setup.

---

## PROMPT

```
You are helping me set up the DesignBench evaluation stack on my Mac for
a CMU course project (GUI-grounded-gen). I have:

- The repo cloned at: /Users/<USER>/path/to/GUI-grounded-gen
- A tarball of the pre-patched DesignBench repo (built on a Linux box):
  <PATH_TO_TARBALL>
- A Qwen API key (I'll paste when asked)
- conda already installed; my target env is `anlp_gen`

Your job: walk me through every step from tarball extraction to a working
`run_repair.py --eval-only` that reproduces baseline numbers. Execute
commands with the Bash tool where safe. Ask before doing anything
system-wide (sudo, global package installs). Assume macOS Apple Silicon
(arm64).

Order of operations:

1. Extract the tarball to `external/DesignBench/` (the repo's .gitignore
   excludes /external). Warn me if the tarball structure would cause
   double-nesting (e.g., archive contains `external/DesignBench/` as
   top-level — extract into repo root, not into `external/`).

2. Install Node via nvm (user-space, no sudo):
     curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
     source ~/.zshrc
     nvm install 20.19
     nvm use 20.19
   Verify with `node --version` in a fresh shell.

3. Activate conda env `anlp_gen` and install Python deps:
     conda activate anlp_gen
     pip install opencv-python scikit-image scikit-learn pillow numpy scipy \
                 openai-clip ftfy retry imageio tqdm httpx pydantic selenium \
                 chromedriver-binary-auto openai python-dotenv
   Verify: `python -c "import cv2, numpy, PIL, skimage, sklearn, clip"`.

4. Patch `external/DesignBench/code/evaluator/config.py`:
   - Replace Linux `DesignBench_Path` with the Mac absolute path to
     `external/DesignBench/` (trailing slash required).
   - Fix the `code/prompting/key.json` typo to `code/prompt/key.json`.

   Use sed -i '' (macOS syntax). Verify with
   `grep -n "DesignBench_Path\|key_path" config.py`.

5. Patch `external/DesignBench/code/evaluator/metric_ast.py`:
   - The tarball has the Linux node path baked in.
     Replace it with the Mac node path (output of `which node`).
   - Auto-detect current value, swap.
   Verify with `grep "/bin/node" metric_ast.py`.

6. npm installs — run these sequentially (each ~1–3 min):
     cd external/DesignBench
     npm install single-file-cli                      # creates root package.json
     cd code/evaluator && npm install && mkdir -p res tmp && cd ../..
     cd web/my-react-app && npm install && cd ../..
     cd web/my-vue-app && npm install && cd ../..
     cd web/my-angular-app && npm install && cd ../..
     npm install -g @angular/cli                      # user-space thanks to nvm

   Do NOT run `npm install` at DesignBench root without the
   `single-file-cli` arg — there's no package.json there.

7. API key setup:
   - Ask me for the Qwen API key.
   - Write it to `<repo-root>/.env` as:
       QWEN_API_KEY="<key>"
   - Update `external/DesignBench/code/prompt/key.json`: set the `qwen`
     field to the key (preserve other fields).
   - Confirm .env is in .gitignore.

8. Dry-run verification:
     cd ui-repair-baseline
     python run_repair.py --dry-run
   Expect: all `[OK]` except `[MISSING] google-chrome` (that's fine on
   Mac; Selenium talks to Chrome.app via chromedriver).

9. End-to-end eval test (no API call, runs on cached outputs):
     python run_repair.py --eval-only --samples 2 --frameworks vanilla
   Expected output ballpark:
     Vanilla 7B: CSR ~1.00, CMLS ~0.42, CMCS ~0.39
   These should match the baseline numbers in
   ui-repair-baseline/baseline_reproduction_results.tex Table 2.

Known gotchas (handle without asking):

- Tarball may contain broken symlinks pointing at original machine's
  /home/<user>/... paths. The run_repair.py code already handles this
  with islink-and-not-exists checks. If you see FileExistsError on
  makedirs, a symlink is broken — fix by unlinking before makedirs.

- Python 3.14 (in anlp_gen) is very new. Most wheels exist; if a pip
  install fails with "no wheel for 3.14", try pip install --pre or
  fall back to a 3.11 env.

- DO NOT run `npm install` at DesignBench root without args.

- DO NOT commit external/DesignBench/, .env, or the Qwen key anywhere.

- When running bash commands that depend on nvm, explicitly source it:
    export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && <your command>
  (Bash tool shells don't source .zshrc interactively.)

- Conda env activation in bash tool: `source /Users/<USER>/miniconda3/etc/profile.d/conda.sh && conda activate anlp_gen`

At the end, summarize: what's installed, what's patched, what files were
created. Flag anything I should manually verify.
```

---

## Notes for the human using this prompt

- Replace `<USER>` with your macOS username and `<PATH_TO_TARBALL>` with the actual tarball path.
- The prompt assumes the repo was cloned with its current state (symlink fixes in `run_repair.py`, `.gitignore` including `.env`).
- Total setup time: ~20–30 min wall clock (10 min of installs, rest is waiting).
- If you don't have the pre-patched tarball, substitute step 1 with:
  `git clone https://github.com/WebPAI/DesignBench.git external/DesignBench`
  and expect to manually apply the DesignBench-internal patches the baseline reproduction required (React CSR regex, etc.).
