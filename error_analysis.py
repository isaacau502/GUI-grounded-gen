#!/usr/bin/env python3
"""DesignBench Repair Task — Error Analysis

Reads evaluation JSONs and ground truth data, categorizes failures,
cross-references with issue types, and prints a structured analysis.

Usage:
    python error_analysis.py
    python error_analysis.py --model qwen2.5-vl-7b-instruct
    python error_analysis.py --framework react
"""

import json
import os
import sys
import argparse
from collections import defaultdict

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESIGNBENCH_ROOT = os.path.join(SCRIPT_DIR, "external", "DesignBench")
EVAL_DIR = os.path.join(DESIGNBENCH_ROOT, "code", "evaluator", "res", "DesignRepair")
DATA_DIR = os.path.join(DESIGNBENCH_ROOT, "data", "DesignRepair")
RESULTS_DIR = os.path.join(DESIGNBENCH_ROOT, "results", "repair")

ALL_MODELS = ["qwen2.5-vl-72b-instruct", "qwen2.5-vl-7b-instruct"]
ALL_FRAMEWORKS = {"react": 28, "vue": 27, "angular": 28, "vanilla": 28}
EXT_MAP = {"react": "jsx", "vue": "vue", "angular": "angular", "vanilla": "html"}
MODE = "both"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_eval_results(frameworks, models):
    """Load evaluation JSONs. Returns {fw: {model: {sample_id: metrics_dict}}}"""
    results = {}
    for fw in frameworks:
        path = os.path.join(EVAL_DIR, f"{fw}_{MODE}.json")
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping {fw}")
            continue
        with open(path) as f:
            data = json.load(f)
        results[fw] = {}
        for model in models:
            if model in data:
                results[fw][model] = data[model]
    return results


def load_issue_types(frameworks):
    """Load ground truth issue types. Returns {fw: {sample_id: [issue_strings]}}"""
    issues = {}
    for fw in frameworks:
        issues[fw] = {}
        fw_dir = os.path.join(DATA_DIR, fw)
        if not os.path.isdir(fw_dir):
            continue
        for sid in os.listdir(fw_dir):
            rpath = os.path.join(fw_dir, sid, "repaired.json")
            if not os.path.exists(rpath):
                continue
            with open(rpath) as f:
                d = json.load(f)
            raw = d.get("Display issues", [])
            if isinstance(raw, str):
                raw = [raw]
            issues[fw][sid] = raw
    return issues


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------

def categorize(m):
    """Categorize a sample's metrics dict into a failure type."""
    compile_err = m.get("compile_error", "NULL")
    if compile_err != "NULL":
        return "compile_fail"

    cmls = m.get("ast_code_op_score", 0)
    cmcs = m.get("ast_code_content_weighted_score", 0)
    clip = m.get("clip_similarity", 0)

    if cmls < 0.1:
        return "wrong_location"
    if cmcs < 0.1:
        return "wrong_content"
    if clip < 0.5:
        return "visual_mismatch"
    return "success"


CATEGORY_LABELS = {
    "compile_fail": "Compile Fail",
    "wrong_location": "Wrong Location (CMLS<0.1)",
    "wrong_content": "Wrong Content (CMCS<0.1)",
    "visual_mismatch": "Visual Mismatch (CLIP<0.5)",
    "success": "Success",
}
CATEGORY_ORDER = ["compile_fail", "wrong_location", "wrong_content", "visual_mismatch", "success"]


def get_paths(fw, model, sid):
    """Return dict of file paths for manual inspection."""
    ext = EXT_MAP[fw]
    base = f"{fw}_{sid}_{model}_{fw}_{MODE}"
    return {
        "generated_code": os.path.join(RESULTS_DIR, f"{fw}-{fw}", model, f"{base}.{ext}"),
        "generated_screenshot": os.path.join(RESULTS_DIR, f"{fw}-{fw}", model, f"{base}.png"),
        "ground_truth": os.path.join(DATA_DIR, fw, sid, "repaired.json"),
        "gt_screenshot": os.path.join(DATA_DIR, fw, sid, "repaired.png"),
        "broken_screenshot": os.path.join(DATA_DIR, fw, sid, f"{sid}.png"),
    }


# ---------------------------------------------------------------------------
# Section 1: Failure Categorization
# ---------------------------------------------------------------------------

def print_failure_breakdown(results, models):
    print("=" * 70)
    print("SECTION 1: Failure Categorization")
    print("=" * 70)

    for model in models:
        print(f"\n  Model: {model}")
        print(f"  {'Framework':<10s}  {'CompFail':>9s}  {'WrongLoc':>9s}  {'WrongCnt':>9s}  {'VisMis':>9s}  {'Success':>9s}")
        print(f"  {'-'*60}")

        for fw, data in results.items():
            if model not in data:
                continue
            counts = defaultdict(int)
            total = len(data[model])
            for sid, m in data[model].items():
                counts[categorize(m)] += 1

            parts = []
            for cat in CATEGORY_ORDER:
                c = counts[cat]
                pct = c / total * 100 if total else 0
                parts.append(f"{c:2d} ({pct:4.0f}%)")
            print(f"  {fw:<10s}  {'  '.join(parts)}")


# ---------------------------------------------------------------------------
# Section 2: Issue Type Breakdown
# ---------------------------------------------------------------------------

def print_issue_type_analysis(results, issues, models):
    print("\n" + "=" * 70)
    print("SECTION 2: Performance by Issue Type")
    print("=" * 70)

    for model in models:
        print(f"\n  Model: {model}")
        print(f"  {'Issue Type':<20s}  {'N':>4s}  {'CMLS':>6s}  {'CMCS':>6s}  {'CLIP':>6s}  {'IssAcc':>6s}  {'CmpFail':>7s}")
        print(f"  {'-'*62}")

        # Collect per-issue-type metrics
        by_issue = defaultdict(lambda: {"cmls": [], "cmcs": [], "clip": [], "issacc": [], "compile_fail": 0, "n": 0})

        for fw, fw_issues in issues.items():
            if fw not in results or model not in results[fw]:
                continue
            for sid, issue_list in fw_issues.items():
                if sid not in results[fw][model]:
                    continue
                m = results[fw][model][sid]
                for issue in issue_list:
                    entry = by_issue[issue]
                    entry["n"] += 1
                    entry["cmls"].append(m.get("ast_code_op_score", 0))
                    entry["cmcs"].append(m.get("ast_code_content_weighted_score", 0))
                    entry["clip"].append(m.get("clip_similarity", 0))
                    entry["issacc"].append(m.get("issue accuracy", 0))
                    if m.get("compile_error", "NULL") != "NULL":
                        entry["compile_fail"] += 1

        for issue in sorted(by_issue.keys(), key=lambda x: -by_issue[x]["n"]):
            e = by_issue[issue]
            n = e["n"]
            cmls = np.mean(e["cmls"]) if e["cmls"] else 0
            cmcs = np.mean(e["cmcs"]) if e["cmcs"] else 0
            clip = np.mean(e["clip"]) if e["clip"] else 0
            issacc = np.mean(e["issacc"]) if e["issacc"] else 0
            cfail = e["compile_fail"] / n * 100 if n else 0
            print(f"  {issue:<20s}  {n:4d}  {cmls:6.3f}  {cmcs:6.3f}  {clip:6.3f}  {issacc:6.3f}  {cfail:5.1f}%")


# ---------------------------------------------------------------------------
# Section 3: Worst Samples
# ---------------------------------------------------------------------------

def print_worst_samples(results, issues, models):
    print("\n" + "=" * 70)
    print("SECTION 3: Worst Samples (lowest CMCS)")
    print("=" * 70)

    for model in models:
        print(f"\n  Model: {model}")

        all_samples = []
        for fw, data in results.items():
            if model not in data:
                continue
            for sid, m in data[model].items():
                issue_list = issues.get(fw, {}).get(sid, ["unknown"])
                all_samples.append((fw, sid, m, issue_list))

        all_samples.sort(key=lambda x: x[2].get("ast_code_content_weighted_score", 0))

        print(f"  {'Rank':<5s}  {'FW/ID':<15s}  {'CMCS':>6s}  {'CMLS':>6s}  {'CLIP':>6s}  {'CSR':>5s}  Issues")
        print(f"  {'-'*70}")
        for i, (fw, sid, m, issue_list) in enumerate(all_samples[:10]):
            cmcs = m.get("ast_code_content_weighted_score", 0)
            cmls = m.get("ast_code_op_score", 0)
            clip = m.get("clip_similarity", 0)
            comp = "FAIL" if m.get("compile_error", "NULL") != "NULL" else "PASS"
            issues_str = ", ".join(issue_list)
            print(f"  {i+1:<5d}  {fw}/{sid:<10s}  {cmcs:6.4f}  {cmls:6.4f}  {clip:6.3f}  {comp:>5s}  {issues_str}")


# ---------------------------------------------------------------------------
# Section 4: 7B vs 72B Comparison
# ---------------------------------------------------------------------------

def print_model_comparison(results):
    if len(ALL_MODELS) < 2:
        return

    m72b = ALL_MODELS[0]
    m7b = ALL_MODELS[1]

    print("\n" + "=" * 70)
    print(f"SECTION 4: {m72b} vs {m7b}")
    print("=" * 70)

    print(f"\n  72B succeeds (CMCS>0.3) but 7B fails (CMCS<0.1):")
    print(f"  {'FW/ID':<15s}  {'72B CMCS':>9s}  {'7B CMCS':>9s}  {'72B CLIP':>9s}  {'7B CLIP':>9s}")
    print(f"  {'-'*55}")
    count_72_wins = 0
    for fw, data in results.items():
        if m72b not in data or m7b not in data:
            continue
        for sid in data[m72b]:
            if sid not in data[m7b]:
                continue
            cmcs_72 = data[m72b][sid].get("ast_code_content_weighted_score", 0)
            cmcs_7 = data[m7b][sid].get("ast_code_content_weighted_score", 0)
            if cmcs_72 > 0.3 and cmcs_7 < 0.1:
                clip_72 = data[m72b][sid].get("clip_similarity", 0)
                clip_7 = data[m7b][sid].get("clip_similarity", 0)
                print(f"  {fw}/{sid:<10s}  {cmcs_72:9.4f}  {cmcs_7:9.4f}  {clip_72:9.3f}  {clip_7:9.3f}")
                count_72_wins += 1
    print(f"  Total: {count_72_wins} samples")

    print(f"\n  7B succeeds (CMCS>0.3) but 72B fails (CMCS<0.1):")
    print(f"  {'FW/ID':<15s}  {'72B CMCS':>9s}  {'7B CMCS':>9s}  {'72B CLIP':>9s}  {'7B CLIP':>9s}")
    print(f"  {'-'*55}")
    count_7_wins = 0
    for fw, data in results.items():
        if m72b not in data or m7b not in data:
            continue
        for sid in data[m72b]:
            if sid not in data[m7b]:
                continue
            cmcs_72 = data[m72b][sid].get("ast_code_content_weighted_score", 0)
            cmcs_7 = data[m7b][sid].get("ast_code_content_weighted_score", 0)
            if cmcs_7 > 0.3 and cmcs_72 < 0.1:
                clip_72 = data[m72b][sid].get("clip_similarity", 0)
                clip_7 = data[m7b][sid].get("clip_similarity", 0)
                print(f"  {fw}/{sid:<10s}  {cmcs_72:9.4f}  {cmcs_7:9.4f}  {clip_72:9.3f}  {clip_7:9.3f}")
                count_7_wins += 1
    print(f"  Total: {count_7_wins} samples")


# ---------------------------------------------------------------------------
# Section 5: Manual Inspection Paths
# ---------------------------------------------------------------------------

def print_inspection_paths(results, models):
    print("\n" + "=" * 70)
    print("SECTION 5: Files for Manual Inspection")
    print("=" * 70)

    for model in models:
        for cat in ["compile_fail", "wrong_location", "wrong_content"]:
            samples = []
            for fw, data in results.items():
                if model not in data:
                    continue
                for sid, m in data[model].items():
                    if categorize(m) == cat:
                        samples.append((fw, sid, m))

            if not samples:
                continue

            print(f"\n  [{model}] {CATEGORY_LABELS[cat]} ({len(samples)} samples)")
            print(f"  {'-'*60}")

            for fw, sid, m in samples:
                paths = get_paths(fw, model, sid)
                cmls = m.get("ast_code_op_score", 0)
                cmcs = m.get("ast_code_content_weighted_score", 0)
                print(f"\n    {fw}/sample {sid}  (CMLS={cmls:.4f}  CMCS={cmcs:.4f})")
                print(f"      Generated code:  file://{paths['generated_code']}")
                print(f"      Generated img:   file://{paths['generated_screenshot']}")
                print(f"      Ground truth:    file://{paths['ground_truth']}")
                print(f"      GT screenshot:   file://{paths['gt_screenshot']}")
                print(f"      Broken input:    file://{paths['broken_screenshot']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="DesignBench Repair — Error Analysis")
    parser.add_argument("--model", type=str, help="Analyze specific model only")
    parser.add_argument("--framework", type=str, help="Analyze specific framework only")
    parser.add_argument("--no-paths", action="store_true", help="Skip Section 5 (file paths)")
    return parser.parse_args()


def main():
    args = parse_args()

    models = [args.model] if args.model else ALL_MODELS
    frameworks = [args.framework] if args.framework else list(ALL_FRAMEWORKS.keys())

    print("Loading evaluation results...")
    results = load_eval_results(frameworks, models)
    print("Loading ground truth issue types...")
    issues = load_issue_types(frameworks)

    # Count what we loaded
    total = sum(len(data.get(m, {})) for fw, data in results.items() for m in models)
    print(f"Loaded {total} evaluated samples across {len(results)} frameworks.\n")

    print_failure_breakdown(results, models)
    print_issue_type_analysis(results, issues, models)
    print_worst_samples(results, issues, models)
    print_model_comparison(results)

    if not args.no_paths:
        print_inspection_paths(results, models)

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
