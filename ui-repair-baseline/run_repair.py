#!/usr/bin/env python3
"""
DesignBench Repair Task — Local Runner + Evaluator

Usage:
    # Install dependencies first (one-time):
    pip install anthropic openai google-generativeai selenium opencv-python \
        scikit-image pillow numpy scipy openai-clip ftfy tqdm requests retry \
        imageio pydantic httpx python-dotenv torch torchvision

    # Install npm AST parsers (one-time), run from repo root:
    npm install @babel/parser @vue/compiler-dom parse5 --prefix external/DesignBench

    # Run:
    python run_repair.py                    # 2 samples per framework (quick test)
    python run_repair.py --full             # all samples, all frameworks
    python run_repair.py --frameworks react vue --samples 5
    python run_repair.py --eval-only        # skip LLM, just evaluate existing results
"""

print("[boot] Script starting...", flush=True)
import sys
import os
import argparse
import subprocess
import time
import signal
print("[boot] Stdlib imports done.", flush=True)

# ── Paths ─────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DESIGNBENCH_ROOT = os.environ.get("DESIGNBENCH_ROOT") or os.path.join(REPO_ROOT, "external", "DesignBench")
CODE_DIR = os.path.join(DESIGNBENCH_ROOT, "code")
EVALUATOR_DIR = os.path.join(CODE_DIR, "evaluator")

sys.path.insert(0, CODE_DIR)
sys.path.insert(0, EVALUATOR_DIR)
print("[boot] Paths set.", flush=True)

# The runner uses relative paths like "data/repair/react/1/1.json"
# but local data is at "data/DesignRepair/react/1/1.json".
# chdir to DesignBench root and create symlinks so both paths work.
os.chdir(DESIGNBENCH_ROOT)

# Create symlinks: data/repair -> data/DesignRepair, etc.
SYMLINKS = {
    "data/repair": "data/DesignRepair",
    "data/generation": "data/DesignGeneration",
    "data/edit": "data/DesignEdit",
    "data/compile": "data/DesignCompile",
}
for link, target in SYMLINKS.items():
    # Remove broken symlinks (e.g., from a tarball originating on another machine)
    if os.path.islink(link) and not os.path.exists(link):
        os.unlink(link)
    if os.path.exists(target) and not os.path.lexists(link):
        os.symlink(os.path.abspath(target), link)

print("[boot] Symlinks done. Loading env...", flush=True)
# Load env vars
from dotenv import load_dotenv
load_dotenv(os.path.join(DESIGNBENCH_ROOT, ".env"))
# Also load from repo root
load_dotenv(os.path.join(REPO_ROOT, ".env"))
print("[boot] Env loaded. Ready.", flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Run DesignBench repair task")
    parser.add_argument("--model", default="qwen2.5-vl-7b-instruct",
                        help="Model name (default: qwen2.5-vl-7b-instruct)")
    parser.add_argument("--frameworks", nargs="+", default=["react", "vue", "angular", "vanilla"],
                        choices=["react", "vue", "angular", "vanilla"],
                        help="Frameworks to run (default: all)")
    parser.add_argument("--mode", default="both", choices=["both", "code", "image"],
                        help="Input mode (default: both)")
    parser.add_argument("--samples", type=int, default=2,
                        help="Number of samples per framework (default: 2)")
    parser.add_argument("--full", action="store_true",
                        help="Run all samples (overrides --samples)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Max parallel workers for LLM calls (default: 5)")
    parser.add_argument("--eval-only", action="store_true",
                        help="Skip LLM generation, only evaluate existing results")
    parser.add_argument("--no-eval", action="store_true",
                        help="Only run LLM generation, skip evaluation")
    parser.add_argument("--llm-judge", action="store_true",
                        help="Also run MLLM-Judge evaluation (requires GPT-4o API key)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Pre-flight check only — show config, verify paths, don't run anything")
    return parser.parse_args()


# Sample counts per framework for repair task
REPAIR_COUNTS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}

FRAMEWORK_MAP = {
    "react": "Framework.REACT",
    "vue": "Framework.VUE",
    "angular": "Framework.ANGULAR",
    "vanilla": "Framework.VANILLA",
}


def symlink_results():
    """Symlink runner output into evaluator expected paths."""
    # Runner saves to results/repair/, evaluator reads from data/DesignRepair/RepairResults/
    task_map = {
        "repair": "DesignRepair/RepairResults",
        "generation": "DesignGeneration/GenerationResults",
        "edit": "DesignEdit/EditResults",
    }
    for task, eval_subdir in task_map.items():
        results_dir = os.path.join(DESIGNBENCH_ROOT, "results", task)
        target_dir = os.path.join(DESIGNBENCH_ROOT, "data", eval_subdir)
        if os.path.exists(results_dir):
            # Clear broken symlinks from cross-machine tarballs
            if os.path.islink(target_dir) and not os.path.exists(target_dir):
                os.unlink(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            for item in os.listdir(results_dir):
                src = os.path.join(results_dir, item)
                dst = os.path.join(target_dir, item)
                if os.path.isdir(src):
                    if os.path.islink(dst):
                        continue  # already symlinked
                    elif os.path.isdir(dst):
                        # Dir already exists (from previous runs) — symlink subdirs
                        for sub in os.listdir(src):
                            sub_src = os.path.join(src, sub)
                            sub_dst = os.path.join(dst, sub)
                            if os.path.isdir(sub_src) and not os.path.exists(sub_dst):
                                os.symlink(sub_src, sub_dst)
                    else:
                        os.symlink(src, dst)


def start_dev_servers(frameworks):
    """Start dev servers for non-vanilla frameworks. Returns list of processes."""
    servers = []
    server_configs = {
        "react": ("web/my-react-app", "npm run dev", 3000),
        "vue": ("web/my-vue-app", "npm run dev", 5173),
        "angular": ("web/my-angular-app", "ng serve", 4200),
    }

    for fw in frameworks:
        # Skip vanilla (no server needed) and angular (run_angular_app starts its own ng serve per sample)
        if fw in ("vanilla", "angular") or fw not in server_configs:
            continue
        app_dir, cmd, port = server_configs[fw]
        app_path = os.path.join(DESIGNBENCH_ROOT, app_dir)

        # Check if server already running
        r = subprocess.run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}",
                          shell=True, capture_output=True, text=True)
        if r.stdout.strip() in ("200", "404"):
            print(f"  [{fw}] Already running on port {port}")
            continue

        print(f"  [{fw}] Starting on port {port}...")
        proc = subprocess.Popen(
            cmd, shell=True, cwd=app_path,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        servers.append((fw, proc, port))

    if servers:
        print("  Waiting for servers to start...")
        time.sleep(15)
        for fw, proc, port in servers:
            r = subprocess.run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}",
                              shell=True, capture_output=True, text=True)
            status = r.stdout.strip()
            icon = "OK" if status in ("200", "404") else "FAIL"
            print(f"  [{icon}] {fw} http://localhost:{port} (status {status})")

    return servers


def stop_dev_servers(servers):
    """Stop dev servers."""
    for fw, proc, port in servers:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_generation(args):
    """Run LLM repair generation."""
    from runner.main import Runner
    from utils import Framework, Task, Mode

    fw_enum = {
        "react": Framework.REACT,
        "vue": Framework.VUE,
        "angular": Framework.ANGULAR,
        "vanilla": Framework.VANILLA,
    }
    mode_enum = {"both": Mode.BOTH, "code": Mode.CODE, "image": Mode.IMAGE}

    for fw_name in args.frameworks:
        fw = fw_enum[fw_name]
        max_sample = REPAIR_COUNTS[fw_name] if args.full else args.samples
        exec_range = (1, max_sample + 1)

        print(f"\n{'='*60}", flush=True)
        print(f"Running {args.model} on {fw_name} repair (samples {exec_range[0]}-{exec_range[1]-1})", flush=True)
        print(f"{'='*60}", flush=True)

        print(f"[checkpoint] Creating runner for {fw_name}...", flush=True)
        runner = Runner(args.model, framework=fw, stream=True, print_content=False)
        print(f"[checkpoint] Runner created. Starting LLM calls...", flush=True)
        runner.run(
            task=Task.REPAIR,
            output_framework=fw,
            mode=mode_enum[args.mode],
            max_workers=args.workers,
            execution_range=exec_range,
        )
        print(f"[checkpoint] {fw_name} generation done.", flush=True)


def run_evaluation(args):
    """Run evaluation using DesignBench's own evaluate_repair + collect_compile_information."""
    import json

    # Set re_calculate before importing evaluator
    import evaluator.main
    evaluator.main.re_calculate = False

    from evaluator.main import evaluate_repair
    from evaluator.compile import collect_compile_information
    from config import Task

    symlink_results()

    # Ensure res dir exists
    res_dir = os.path.join(DESIGNBENCH_ROOT, "code", "evaluator", "res", "DesignRepair")
    os.makedirs(res_dir, exist_ok=True)

    # Change to evaluator dir so relative res/ paths work
    os.chdir(os.path.join(DESIGNBENCH_ROOT, "code", "evaluator"))

    models = [args.model]
    compile_frameworks = [fw for fw in args.frameworks if fw != "vanilla"]
    modes = [args.mode]

    # ── Step 1: Run evaluate_repair (metrics: CMLS, CMCS, CLIP, SSIM, MAE, IssueAcc) ──
    print(f"\n{'='*60}")
    print("Step 1: Running evaluate_repair...")
    print(f"{'='*60}")
    evaluate_repair(models=models, frame_works=args.frameworks, modes=modes, llm_judge_flag=False)

    # ── Step 2: LLM Judge (optional) ──
    if args.llm_judge:
        print(f"\n{'='*60}")
        print("Step 2: Running MLLM-Judge evaluation...")
        print(f"{'='*60}")
        evaluate_repair(models=models, frame_works=args.frameworks, modes=modes, llm_judge_flag=True)

    # ── Step 3: Collect compile information (CSR) ──
    print(f"\n{'='*60}")
    print("Step 3: Collecting compile information (CSR)...")
    print(f"{'='*60}")
    for fw in compile_frameworks:
        for mode in modes:
            collect_compile_information(
                task_name=Task.REPAIR,
                frame_work=fw,
                implemented_framework_or_mode=mode
            )

    # ── Step 4: Read results and print summary ──
    print(f"\n{'='*70}")
    print(f"SUMMARY — DesignBench Repair Task (model: {args.model})")
    print(f"{'='*70}")
    has_llm = args.llm_judge
    header = f"{'Framework':<10} {'N':>4} {'CSR':>7} {'CMLS':>7} {'CMCS':>7}"
    if has_llm:
        header += f" {'LLM-J':>7}"
    print(header)
    print("-" * len(header))

    for fw in args.frameworks:
        res_path = os.path.join(res_dir, f"{fw}_{args.mode}.json")
        if not os.path.exists(res_path):
            print(f"{fw:<10} -- no results file at {res_path}")
            continue

        with open(res_path, "r") as f:
            results = json.load(f)

        if args.model not in results:
            print(f"{fw:<10} -- model {args.model} not in results")
            continue

        model_results = results[args.model]
        n = len(model_results)

        # CSR: count samples without compile errors
        compile_success = 0
        cmls_total = 0
        cmcs_total = 0
        llm_total = 0
        for sample_id, m in model_results.items():
            compile_err = m.get("compile_error", "NULL")
            if compile_err == "NULL":
                compile_success += 1
            cmls_total += m.get("ast_code_op_score", 0)
            cmcs_total += m.get("ast_code_content_weighted_score", 0)
            if has_llm:
                llm_total += m.get("llm score", 0)

        csr = compile_success / n if n > 0 else 0
        cmls = cmls_total / n if n > 0 else 0
        cmcs = cmcs_total / n if n > 0 else 0

        row = f"{fw:<10} {n:>4} {csr:>7.4f} {cmls:>7.4f} {cmcs:>7.4f}"
        if has_llm:
            llm_avg = llm_total / n if n > 0 else 0
            row += f" {llm_avg:>7.4f}"
        print(row)


def preflight(args):
    """Pre-flight checks — verify config, paths, API keys, existing results."""
    import shutil

    print(f"\n{'='*60}")
    print("PRE-FLIGHT CHECK")
    print(f"{'='*60}")

    # Model & task config
    print(f"\n-- Config --")
    print(f"  Model:       {args.model}")
    print(f"  Task:        repair")
    print(f"  Mode:        {args.mode}")
    print(f"  Frameworks:  {', '.join(args.frameworks)}")
    for fw in args.frameworks:
        n = REPAIR_COUNTS[fw] if args.full else args.samples
        print(f"    {fw}: samples 1-{n}")
    print(f"  Workers:     {args.workers}")
    print(f"  Eval only:   {args.eval_only}")
    print(f"  LLM judge:   {args.llm_judge}")

    # Paths
    print(f"\n-- Paths --")
    paths = {
        "DesignBench root": DESIGNBENCH_ROOT,
        "Code dir": CODE_DIR,
        "Evaluator dir": EVALUATOR_DIR,
        "Data dir": os.path.join(DESIGNBENCH_ROOT, "data"),
        "Results dir": os.path.join(DESIGNBENCH_ROOT, "results"),
    }
    for name, p in paths.items():
        ok = "OK" if os.path.exists(p) else "MISSING"
        print(f"  [{ok}] {name}: {p}")

    # Data availability — always check full dataset regardless of --samples/--full
    print(f"\n-- Dataset (full repair subset) --")
    fmt = {"react": "jsx", "vue": "vue", "angular": "angular", "vanilla": "html"}
    all_fws = ["react", "vue", "angular", "vanilla"]
    for fw in all_fws:
        n = REPAIR_COUNTS[fw]
        found = 0
        missing = []
        for i in range(1, n + 1):
            json_path = os.path.join(DESIGNBENCH_ROOT, "data", "DesignRepair", fw, str(i), f"{i}.json")
            if os.path.exists(json_path):
                found += 1
            else:
                missing.append(i)
        ok = "OK" if found == n else "WARN"
        tag = " <-- selected" if fw in args.frameworks else ""
        print(f"  [{ok}] {fw}: {found}/{n} input samples{tag}")
        if missing:
            print(f"        missing: {missing}")

    # Existing results — always check full dataset
    print(f"\n-- Existing Results (full repair subset) --")
    for fw in all_fws:
        n = REPAIR_COUNTS[fw]
        found = 0
        for i in range(1, n + 1):
            result_path = os.path.join(
                DESIGNBENCH_ROOT, "results", "repair", f"{fw}-{fw}",
                args.model.split("/")[-1],
                f"{fw}_{i}_{args.model.split('/')[-1]}_{fw}_{args.mode}.{fmt[fw]}"
            )
            if os.path.exists(result_path):
                found += 1
        tag = " <-- selected" if fw in args.frameworks else ""
        will_run = REPAIR_COUNTS[fw] if (args.full and fw in args.frameworks) else (args.samples if fw in args.frameworks else 0)
        skip_note = f" (will skip {found}, run {max(0, will_run - found)} new)" if fw in args.frameworks else ""
        print(f"  {fw}: {found}/{n} generated{tag}{skip_note}")

    # Output location
    print(f"\n-- Output Location --")
    for fw in args.frameworks:
        out_dir = os.path.join(DESIGNBENCH_ROOT, "results", "repair", f"{fw}-{fw}", args.model.split("/")[-1])
        print(f"  {fw}: {out_dir}")

    # API key
    print(f"\n-- API Key --")
    qwen_key = os.environ.get("QWEN_API_KEY", "")
    if qwen_key:
        print(f"  [OK] QWEN_API_KEY set ({qwen_key[:8]}...{qwen_key[-4:]})")
    else:
        print(f"  [MISSING] QWEN_API_KEY not set")

    if args.llm_judge:
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            print(f"  [OK] OPENAI_API_KEY set ({openai_key[:8]}...)")
        else:
            print(f"  [MISSING] OPENAI_API_KEY not set (needed for LLM judge)")

    # Metrics
    print(f"\n-- Metrics --")
    metrics = [
        ("CSR",        "Compile Success Rate (binary)", True),
        ("CodeSim",    "Jaccard line similarity", True),
        ("CMLS",       "Code Modification Location Similarity (AST op matching)", True),
        ("CMCS",       "Code Modification Content Similarity (CMLS x CodeBLEU)", True),
        ("CLIP",       "CLIP visual similarity", True),
        ("SSIM",       "Structural similarity", True),
        ("MAE",        "Mean Absolute Error (pixel)", True),
        ("IssueAcc",   "Issue type accuracy", True),
        ("MLLM-Judge", "GPT-4o visual judge score", args.llm_judge),
    ]
    for name, desc, enabled in metrics:
        status = "ON" if enabled else "OFF"
        print(f"  [{status:>3}] {name:<12} {desc}")

    # Tools
    print(f"\n-- Tools --")
    for tool in ["ng", "node", "npm", "google-chrome"]:
        path = shutil.which(tool)
        ok = "OK" if path else "MISSING"
        print(f"  [{ok}] {tool}: {path or 'not found'}")

    print(f"\n{'='*60}")
    print("Pre-flight complete. Remove --dry-run to execute.")
    print(f"{'='*60}")


def main():
    args = parse_args()

    print(f"Model:      {args.model}")
    print(f"Frameworks: {', '.join(args.frameworks)}")
    print(f"Mode:       {args.mode}")
    print(f"Samples:    {'all' if args.full else args.samples}")

    if args.dry_run:
        preflight(args)
        return

    # ── Run LLM generation ────────────────────────────────────────
    if not args.eval_only:
        print("[checkpoint] Starting LLM generation phase...", flush=True)
        run_generation(args)
        print("[checkpoint] LLM generation phase complete.", flush=True)

    # ── Start dev servers + evaluate ──────────────────────────────
    if not args.no_eval:
        print("\n[checkpoint] Starting dev servers...", flush=True)
        servers = start_dev_servers(args.frameworks)

        try:
            run_evaluation(args)
        finally:
            if servers:
                print("\nStopping dev servers...")
                stop_dev_servers(servers)

    print("\nDone.")


if __name__ == "__main__":
    main()
