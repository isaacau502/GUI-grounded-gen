"""Run DesignBench repair with BOTH OmniParser and JEDI grounding injected.

Wraps `ui-repair-baseline/run_repair.py`. Before delegating to the baseline
runner, monkeypatches:

  1. `prompt.repair_prompt.get_design_repair_prompt` — appends the JEDI
     click-point block (from `jedi_cache.json`) followed by the OmniParser
     structural block (from `grounding_structural_cache.json`). JEDI first,
     then OmniParser; each block keeps its own self-introducing header,
     separated by `\\n\\n`.
  2. `runner.main.Runner.run_repair` — sets a thread-local (framework,
     web_number) before each sample so the patched prompt function knows
     which entries to read from each cache.

Tags model_filename with `+hybrid` so results don't collide with baseline,
the OmniParser variant, or the JEDI variant.

Usage:
    python scripts/run_repair_grounded_hybrid.py --samples 2
    python scripts/run_repair_grounded_hybrid.py --samples 2 --frameworks react
    python scripts/run_repair_grounded_hybrid.py --full
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

# --- Load both grounding caches ---------------------------------------
OMNI_CACHE_PATH = Path(os.environ.get("OMNI_CACHE", REPO / "grounding_structural_cache.json"))
JEDI_CACHE_PATH = Path(os.environ.get("JEDI_CACHE", REPO / "jedi_cache.json"))

if not OMNI_CACHE_PATH.exists():
    sys.exit(
        f"OmniParser grounding cache missing: {OMNI_CACHE_PATH}. "
        f"Build it with scripts/build_grounding_cache.py on Colab, then rclone to local."
    )
if not JEDI_CACHE_PATH.exists():
    sys.exit(
        f"JEDI grounding cache missing: {JEDI_CACHE_PATH}. "
        f"Build it with scripts/build_jedi_cache.py on Colab, then rclone to local."
    )

with open(OMNI_CACHE_PATH) as f:
    OMNI_CACHE = json.load(f)
with open(JEDI_CACHE_PATH) as f:
    JEDI_CACHE = json.load(f)

print(
    f"Loaded OmniParser grounding for {len(OMNI_CACHE)} samples from {OMNI_CACHE_PATH}, "
    f"JEDI for {len(JEDI_CACHE)} samples from {JEDI_CACHE_PATH}."
)

# --- Thread-local current sample (framework, web_number) --------------
_tls = threading.local()


def _set_current(framework_value: str, web_number: int):
    _tls.key = f"{framework_value}/{web_number}"


def _get_omni_block() -> str:
    """Return OmniParser block (intro + structural prompt_block) or ''."""
    key = getattr(_tls, "key", None)
    if not key or key not in OMNI_CACHE:
        return ""
    entry = OMNI_CACHE[key]
    if "error" in entry:
        return ""
    block = entry.get("prompt_block", "")
    if not block:
        return ""
    return (
        "Here is an automated parse of UI elements detected in the screenshot "
        "(bounding boxes + captions). Use this as a spatial reference when "
        "reasoning about which regions contain defects.\n\n"
        + block
    )


def _format_jedi_block(entry: dict) -> str:
    """Render cached (issue, click_point) pairs as a natural-language block.

    Mirrors scripts/run_repair_grounded_jedi.py:_format_grounding_block.
    """
    issues = entry.get("issues", [])
    if not issues:
        return ""
    lines = [
        "An automated grounding model identified click targets for each design issue:"
    ]
    any_point = False
    for item in issues:
        issue_type = item.get("issue_type", "unknown")
        point = item.get("point")
        if point is not None and item.get("parse_success"):
            x, y = int(point[0]), int(point[1])
            lines.append(f'- "{issue_type}" — click at (x={x}, y={y})')
            any_point = True
        else:
            lines.append(f'- "{issue_type}" — (no reliable click point detected)')
    if not any_point:
        return ""
    return "\n".join(lines)


def _get_jedi_block() -> str:
    key = getattr(_tls, "key", None)
    if not key or key not in JEDI_CACHE:
        return ""
    entry = JEDI_CACHE[key]
    if "error" in entry and not entry.get("issues"):
        return ""
    return _format_jedi_block(entry)


# --- Monkeypatch get_design_repair_prompt -----------------------------
from prompt import repair_prompt  # noqa: E402

_orig_get_prompt = repair_prompt.get_design_repair_prompt


def _patched_get_prompt(output_framework, mode, code):
    system_prompt, prompt = _orig_get_prompt(output_framework=output_framework, mode=mode, code=code)
    jedi_block = _get_jedi_block()
    omni_block = _get_omni_block()
    if jedi_block:
        prompt = prompt + "\n\n" + jedi_block
    if omni_block:
        prompt = prompt + "\n\n" + omni_block
    return system_prompt, prompt


repair_prompt.get_design_repair_prompt = _patched_get_prompt
# `runner.main` imports the symbol at module load, so patch there too.
import runner.main as runner_main  # noqa: E402
runner_main.get_design_repair_prompt = _patched_get_prompt


# --- Monkeypatch Runner.run_repair to set TLS before each call --------
_orig_run_repair = runner_main.Runner.run_repair


def _patched_run_repair(self, args):
    task, web_number, output_framework, mode = args
    _set_current(self.framework.value, web_number)
    return _orig_run_repair(self, args)


runner_main.Runner.run_repair = _patched_run_repair

# --- Rename output model_filename so we don't stomp other variants ----
_orig_init = runner_main.Runner.__init__


def _patched_init(self, model_name, framework, stream=True, print_content=False, *a, **kw):
    _orig_init(self, model_name, framework, stream=stream, print_content=print_content, *a, **kw)
    # Tag the filename so hybrid runs don't collide with baseline / +omni / +jedi.
    self.model_filename = f"{self.model_filename}+hybrid"


runner_main.Runner.__init__ = _patched_init

print("Monkeypatches applied: get_design_repair_prompt + Runner.run_repair + Runner.__init__.")


# --- Delegate to baseline run_repair.py via its CLI -------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-vl-7b-instruct")
    ap.add_argument("--frameworks", nargs="+", default=["react", "vue", "angular", "vanilla"],
                    choices=["react", "vue", "angular", "vanilla"])
    ap.add_argument("--mode", default="both", choices=["both", "code", "image", "mark"])
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
    mode_enum = {"both": Mode.BOTH, "code": Mode.CODE, "image": Mode.IMAGE, "mark": Mode.MARK}
    counts = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}

    for fw_name in args.frameworks:
        fw = fw_enum[fw_name]
        max_sample = counts[fw_name] if args.full else args.samples
        rng = (1, max_sample + 1)

        print(f"\n{'='*60}\nGROUNDED-HYBRID {args.model} on {fw_name} (samples {rng[0]}-{rng[1]-1})\n{'='*60}")
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
    tagged_model = f"{args.model}+hybrid"
    compile_fws = [fw for fw in args.frameworks if fw != "vanilla"]
    evaluate_repair(models=[tagged_model], frame_works=args.frameworks,
                    modes=[args.mode], llm_judge_flag=False)
    for fw in compile_fws:
        collect_compile_information(task_name=CfgTask.REPAIR,
                                    frame_work=fw,
                                    implemented_framework_or_mode=args.mode)

    print(f"\nHybrid-grounded run complete. Compare:")
    print(f"  baseline: results/repair/.../{args.model}/")
    print(f"  grounded: results/repair/.../{tagged_model}/")


if __name__ == "__main__":
    main()
