"""Run DesignBench repair with OmniParser grounding injected into the prompt.

Wraps `ui-repair-baseline/run_repair.py`. Before delegating to the baseline
runner, monkeypatches:

  1. `prompt.repair_prompt.get_design_repair_prompt` — appends the cached
     grounding `prompt_block` for the current sample to the returned prompt.
  2. `runner.main.Runner.run_repair` — sets a thread-local (framework, web_number)
     before each sample so the patched prompt function knows which grounding
     entry to read.

Results land in `ui-repair-baseline/external/DesignBench/results/repair/` like
the baseline, but under a different model_filename so they don't collide.
We tag the model name with `+omni` to keep outputs separate.

Usage:
    # Pre-req: grounding cache built on Colab, rclone'd to:
    #   grounding_cache.json in repo root (or set GROUNDING_CACHE env var).

    python scripts/run_repair_grounded.py --samples 2
    python scripts/run_repair_grounded.py --samples 2 --frameworks react
    python scripts/run_repair_grounded.py --full
"""

import argparse
import json
import os
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DESIGNBENCH = REPO / "external" / "DesignBench"
BASELINE_DIR = REPO / "ui-repair-baseline"

sys.path.insert(0, str(DESIGNBENCH / "code"))
sys.path.insert(0, str(DESIGNBENCH / "code" / "evaluator"))
sys.path.insert(0, str(BASELINE_DIR))

# ─── Load grounding cache ─────────────────────────────────────────────
CACHE_PATH = Path(os.environ.get("GROUNDING_CACHE", REPO / "grounding_cache.json"))
if not CACHE_PATH.exists():
    sys.exit(f"Grounding cache missing: {CACHE_PATH}. Build it with scripts/build_grounding_cache.py on Colab, then rclone to local.")

with open(CACHE_PATH) as f:
    GROUNDING_CACHE = json.load(f)

print(f"Loaded grounding for {len(GROUNDING_CACHE)} samples from {CACHE_PATH}.")

# ─── Thread-local current sample (framework, web_number) ──────────────
_tls = threading.local()


def _set_current(framework_value: str, web_number: int):
    _tls.key = f"{framework_value}/{web_number}"


def _get_grounding() -> str:
    key = getattr(_tls, "key", None)
    if not key or key not in GROUNDING_CACHE:
        return ""
    entry = GROUNDING_CACHE[key]
    if "error" in entry:
        return ""
    return entry.get("prompt_block", "")


# ─── Monkeypatch get_design_repair_prompt ─────────────────────────────
from prompt import repair_prompt  # noqa: E402

_orig_get_prompt = repair_prompt.get_design_repair_prompt


def _patched_get_prompt(output_framework, mode, code):
    system_prompt, prompt = _orig_get_prompt(output_framework=output_framework, mode=mode, code=code)
    block = _get_grounding()
    if block:
        prompt = (
            prompt
            + "\n\n"
            + "Here is an automated parse of UI elements detected in the screenshot "
              "(bounding boxes + captions). Use this as a spatial reference when "
              "reasoning about which regions contain defects.\n\n"
            + block
        )
    return system_prompt, prompt


repair_prompt.get_design_repair_prompt = _patched_get_prompt
# `runner.main` imports the symbol at module load, so patch there too.
import runner.main as runner_main  # noqa: E402
runner_main.get_design_repair_prompt = _patched_get_prompt


# ─── Monkeypatch Runner.run_repair to set TLS before each call ────────
_orig_run_repair = runner_main.Runner.run_repair


def _patched_run_repair(self, args):
    task, web_number, output_framework, mode = args
    _set_current(self.framework.value, web_number)
    return _orig_run_repair(self, args)


runner_main.Runner.run_repair = _patched_run_repair

# ─── Rename output model_filename so we don't stomp the baseline ──────
_orig_init = runner_main.Runner.__init__


def _patched_init(self, model_name, framework, stream=True, print_content=False, *a, **kw):
    _orig_init(self, model_name, framework, stream=stream, print_content=print_content, *a, **kw)
    # Tag the filename so grounded runs don't collide with baseline results.
    self.model_filename = f"{self.model_filename}+omni"


runner_main.Runner.__init__ = _patched_init

print("Monkeypatches applied: get_design_repair_prompt + Runner.run_repair + Runner.__init__.")


# ─── Delegate to baseline run_repair.py via its CLI ───────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-vl-7b-instruct")
    ap.add_argument("--frameworks", nargs="+", default=["react", "vue", "angular", "vanilla"],
                    choices=["react", "vue", "angular", "vanilla"])
    ap.add_argument("--mode", default="both", choices=["both", "code", "image"])
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--no-eval", action="store_true")
    args = ap.parse_args()

    # Mirror baseline's path setup.
    os.chdir(DESIGNBENCH)

    # Create the same symlinks baseline creates.
    symlinks = {
        "data/repair": "data/DesignRepair",
        "data/generation": "data/DesignGeneration",
        "data/edit": "data/DesignEdit",
        "data/compile": "data/DesignCompile",
    }
    for link, target in symlinks.items():
        if os.path.islink(link) and not os.path.exists(link):
            os.unlink(link)
        if os.path.exists(target) and not os.path.lexists(link):
            os.symlink(os.path.abspath(target), link)

    from dotenv import load_dotenv
    load_dotenv(DESIGNBENCH / ".env")
    load_dotenv(REPO / ".env")

    # Run generation.
    from utils import Framework, Task, Mode  # type: ignore

    fw_enum = {
        "react": Framework.REACT,
        "vue": Framework.VUE,
        "angular": Framework.ANGULAR,
        "vanilla": Framework.VANILLA,
    }
    mode_enum = {"both": Mode.BOTH, "code": Mode.CODE, "image": Mode.IMAGE}
    counts = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}

    for fw_name in args.frameworks:
        fw = fw_enum[fw_name]
        max_sample = counts[fw_name] if args.full else args.samples
        rng = (1, max_sample + 1)

        print(f"\n{'='*60}\nGROUNDED {args.model} on {fw_name} (samples {rng[0]}-{rng[1]-1})\n{'='*60}")
        runner = runner_main.Runner(args.model, framework=fw, stream=True, print_content=False)
        runner.run(
            task=Task.REPAIR,
            output_framework=fw,
            mode=mode_enum[args.mode],
            max_workers=args.workers,
            execution_range=rng,
        )

    if args.no_eval:
        return

    # Delegate eval to baseline's evaluator with our tagged model name.
    import evaluator.main  # type: ignore
    evaluator.main.re_calculate = False
    from evaluator.main import evaluate_repair  # type: ignore
    from evaluator.compile import collect_compile_information  # type: ignore
    from config import Task as CfgTask  # type: ignore

    # Symlink results/repair into the path the evaluator reads from.
    results_dir = DESIGNBENCH / "results" / "repair"
    target_dir = DESIGNBENCH / "data" / "DesignRepair" / "RepairResults"
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in os.listdir(results_dir):
        src = results_dir / item
        dst = target_dir / item
        if src.is_dir() and not dst.exists():
            os.symlink(src.resolve(), dst)

    os.chdir(DESIGNBENCH / "code" / "evaluator")
    tagged_model = f"{args.model}+omni"
    compile_fws = [fw for fw in args.frameworks if fw != "vanilla"]
    evaluate_repair(models=[tagged_model], frame_works=args.frameworks,
                    modes=[args.mode], llm_judge_flag=False)
    for fw in compile_fws:
        collect_compile_information(task_name=CfgTask.REPAIR,
                                    frame_work=fw,
                                    implemented_framework_or_mode=args.mode)

    print(f"\nGrounded run complete. Compare:")
    print(f"  baseline: results/repair/.../{args.model}/")
    print(f"  grounded: results/repair/.../{tagged_model}/")


if __name__ == "__main__":
    main()
