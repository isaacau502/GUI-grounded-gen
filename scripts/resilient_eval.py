"""Resilient wrapper around DesignBench's evaluator.

The baseline evaluator crashes if a rendered .png is missing (Image.open
raises FileNotFoundError). Angular renders are flaky — ~1/28 successfully
rendered for us. We want partial-but-comparable metrics, not a crash.

This wrapper:
  1. Starts dev servers (react + vue).
  2. Iterates (framework, web_number) per sample.
  3. Calls get_repair_metric, catches any exception, records zero visual
     metrics but still returns AST/code metrics where possible.
  4. Writes per-framework JSON output matching DesignBench's format.

Usage:
    python scripts/resilient_eval.py \
        --model qwen2.5-vl-72b-instruct+omni \
        --frameworks react vue angular vanilla \
        --mode both
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DESIGNBENCH = REPO / "external" / "DesignBench"
BASELINE = REPO / "ui-repair-baseline"

sys.path.insert(0, str(DESIGNBENCH / "code"))
sys.path.insert(0, str(DESIGNBENCH / "code" / "evaluator"))
sys.path.insert(0, str(BASELINE))

os.chdir(DESIGNBENCH)

# Symlinks identical to baseline run_repair.py
SYMLINKS = {
    "data/repair": "data/DesignRepair",
    "data/generation": "data/DesignGeneration",
    "data/edit": "data/DesignEdit",
    "data/compile": "data/DesignCompile",
}
for link, target in SYMLINKS.items():
    if os.path.islink(link) and not os.path.exists(link):
        os.unlink(link)
    if os.path.exists(target) and not os.path.lexists(link):
        os.symlink(os.path.abspath(target), link)


def symlink_results():
    results_dir = os.path.join(DESIGNBENCH, "results", "repair")
    target_dir = os.path.join(DESIGNBENCH, "data", "DesignRepair", "RepairResults")
    os.makedirs(target_dir, exist_ok=True)
    for item in os.listdir(results_dir):
        src = os.path.join(results_dir, item)
        dst = os.path.join(target_dir, item)
        if os.path.isdir(src):
            if os.path.islink(dst):
                continue
            elif os.path.isdir(dst):
                for sub in os.listdir(src):
                    sub_src = os.path.join(src, sub)
                    sub_dst = os.path.join(dst, sub)
                    if os.path.isdir(sub_src) and not os.path.exists(sub_dst):
                        os.symlink(sub_src, sub_dst)
            else:
                os.symlink(src, dst)


REPAIR_COUNTS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}


def zero_metrics():
    return {
        "MAE": 0,
        "clip_similarity": 0,
        "structure_similarity": 0,
        "issue accuracy": 0,
        "code_score": 0,
        "ast_code_op_score": 0,
        "ast_code_content_score": 0,
        "ast_code_content_weighted_score": 0,
        "compile_success": False,
    }


def compute_ast_only(framework, web_number, model_name, mode):
    """Fallback when render fails: compute AST metrics from code files alone."""
    from evaluator.main import folder_dic, format_dic  # type: ignore
    from config import Task  # type: ignore
    from evaluator.metric_ast import ast_code_similarity  # type: ignore
    from evaluator.metric import code_similarity  # type: ignore
    from evaluator.metric_utils import validate_issue, remove_comments  # type: ignore

    prediction_path = folder_dic[Task.REPAIR]
    fmt = format_dic[framework]
    gen_code_path = f"{prediction_path}RepairResults/{framework}-{framework}/{model_name}/{framework}_{web_number}_{model_name}_{framework}_{mode}.{fmt}"
    gen_json_path = gen_code_path.replace(f".{fmt}", ".json")
    ref_code_path = f"{prediction_path}{framework}/{web_number}/repaired.{fmt}"
    config_path = f"{prediction_path}{framework}/{web_number}/{web_number}.json"

    if not os.path.exists(gen_code_path) or not os.path.exists(ref_code_path):
        return zero_metrics()

    with open(config_path) as f:
        config = json.loads(f.read())
    src_code = config["component_jsx"] if framework == "react" else config["code"]

    with open(ref_code_path) as f:
        ref_code = f.read()
    with open(gen_code_path) as f:
        gen_code = f.read()

    if framework == "angular":
        # Angular compares both .angular (html) and .ts separately, avg the scores.
        src_ang = src_code["html"] if isinstance(src_code, dict) else src_code
        ang_score = code_similarity(src_code=src_ang, reference_code=ref_code, generated_code=gen_code)
        ang_op, ang_cs, ang_pe = ast_code_similarity(src_code=src_ang, reference_code=ref_code,
                                                    generated_code=gen_code, framework="vanilla")

        ts_src = src_code["ts"] if isinstance(src_code, dict) else ""
        ts_ref_path = ref_code_path.replace(".angular", ".ts")
        ts_gen_path = gen_code_path.replace(".angular", ".ts")
        if os.path.exists(ts_ref_path) and os.path.exists(ts_gen_path):
            with open(ts_ref_path) as f:
                ts_ref = f.read()
            with open(ts_gen_path) as f:
                ts_gen = f.read()
            ts_score = code_similarity(src_code=ts_src, reference_code=ts_ref, generated_code=ts_gen)
            ts_op, ts_cs, ts_pe = ast_code_similarity(src_code=ts_src, reference_code=ts_ref,
                                                      generated_code=ts_gen, framework="angular")
        else:
            ts_score, ts_op, ts_cs, ts_pe = 0, 0, 0, True

        code_score = 0.5 * ang_score + 0.5 * ts_score
        op_score = 0.5 * ang_op + 0.5 * ts_op
        cs_score = 0.5 * ang_cs + 0.5 * ts_cs
        parse_error = ang_pe or ts_pe
    else:
        if framework == "react":
            src_code = remove_comments(src_code)
            ref_code = remove_comments(ref_code)
            gen_code = remove_comments(gen_code)
        code_score = code_similarity(src_code=src_code, reference_code=ref_code, generated_code=gen_code)
        op_score, cs_score, parse_error = ast_code_similarity(
            src_code=src_code, reference_code=ref_code, generated_code=gen_code, framework=framework,
        )

    issue_flag = validate_issue(res_path=gen_json_path, config_path=config_path)

    return {
        "MAE": 0,
        "clip_similarity": 0,
        "structure_similarity": 0,
        "code_score": code_score,
        "issue accuracy": issue_flag,
        "ast_code_op_score": op_score,
        "ast_code_content_score": cs_score,
        "ast_code_content_weighted_score": op_score * cs_score,
        "compile_success": False,  # unknown — render didn't succeed here
        "parse_error": parse_error,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--frameworks", nargs="+", default=["react", "vue", "angular", "vanilla"])
    ap.add_argument("--mode", default="both")
    ap.add_argument("--skip-render", action="store_true",
                    help="Skip render attempt, only compute AST/code metrics.")
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(DESIGNBENCH / ".env")
    load_dotenv(REPO / ".env")

    symlink_results()

    # Start dev servers if not skipping render
    servers = []
    if not args.skip_render:
        from run_repair import start_dev_servers  # type: ignore
        servers = start_dev_servers(args.frameworks)

    try:
        import evaluator.main  # type: ignore
        evaluator.main.re_calculate = False
        from evaluator.main import get_repair_metric  # type: ignore

        res_dir = DESIGNBENCH / "code" / "evaluator" / "res" / "DesignRepair"
        res_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(DESIGNBENCH / "code" / "evaluator")

        for fw in args.frameworks:
            out_path = res_dir / f"{fw}_{args.mode}.json"
            existing = {}
            if out_path.exists():
                with open(out_path) as f:
                    existing = json.load(f)

            existing.setdefault(args.model, {})

            n = REPAIR_COUNTS[fw]
            for i in range(1, n + 1):
                if str(i) in existing[args.model]:
                    continue
                try:
                    if args.skip_render:
                        metrics = compute_ast_only(fw, str(i), args.model, args.mode)
                    else:
                        metrics = get_repair_metric(web_name=str(i), model_name=args.model,
                                                    framework=fw, mode=args.mode, llm_judge_flag=False)
                except Exception as e:
                    print(f"[{fw}/{i}] render/metric path failed: {type(e).__name__}: {e}")
                    print(f"  -> falling back to AST-only")
                    try:
                        metrics = compute_ast_only(fw, str(i), args.model, args.mode)
                    except Exception as e2:
                        print(f"  -> AST fallback also failed: {e2}; recording zeros")
                        traceback.print_exc()
                        metrics = zero_metrics()

                existing[args.model][str(i)] = metrics
                with open(out_path, "w") as f:
                    json.dump(existing, f, indent=2)
                print(f"  [{fw}/{i}] {metrics.get('compile_success', False)=} "
                      f"clip={metrics.get('clip_similarity', 0):.2f} "
                      f"cmls={metrics.get('ast_code_op_score', 0):.2f}")

            print(f"[{fw}] done. Wrote {out_path}")

    finally:
        if servers:
            from run_repair import stop_dev_servers  # type: ignore
            stop_dev_servers(servers)


if __name__ == "__main__":
    main()
