"""Compare DesignBench UI-repair eval JSONs across baseline + grounded variants.

Reads per-framework evaluator outputs from
``external/DesignBench/code/evaluator/res/DesignRepair/{framework}_{mode}.json``
and produces a markdown summary with per-framework tables plus a combined
"averages across frameworks" table at the top.

Each eval JSON is shaped as::

    {
      "<model_key>": {
        "<sample_id>": {
          "MAE": float,
          "clip_similarity": float,
          "structure_similarity": float,
          "code_score": float,
          "issue accuracy": float,
          "ast_code_op_score": float,
          "ast_code_content_score": float,
          "ast_code_content_weighted_score": float,
          "compile_success": bool,
          "parse_error": bool,
          "compile_error": str,
        },
        ...
      },
      ...
    }

We aggregate per-model by averaging numeric metrics across samples. Compile
success rate (CSR) is derived from the ``compile_success`` booleans (and any
``*_csr*`` / ``*compile*`` sidecar files if present).

Metric direction (baked in): MAE is lower-better; everything else
(CLIP, SSIM, CMLS, CMCS, IssueAcc, CSR, code scores) is higher-better.

Usage::

    python scripts/compare_results.py \\
        --baseline qwen2.5-vl-7b-instruct \\
        --variants qwen2.5-vl-7b-instruct+omni qwen2.5-vl-7b-instruct+jedi \\
        --mode both \\
        --frameworks react vue angular vanilla \\
        --output results_summary.md
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Metric direction: True => higher-is-better, False => lower-is-better.
# Unknown numeric keys default to higher-is-better (matches CLIP/SSIM/CMLS/CMCS/
# IssueAcc/CSR and code-score family). MAE is the known lower-better metric.
# ---------------------------------------------------------------------------
METRIC_DIRECTION: dict[str, bool] = {
    "MAE": False,
    "mae": False,
    "clip_similarity": True,
    "structure_similarity": True,
    "code_score": True,
    "issue accuracy": True,
    "issue_accuracy": True,
    "IssueAcc": True,
    "ast_code_op_score": True,
    "ast_code_content_score": True,
    "ast_code_content_weighted_score": True,
    "CMLS": True,
    "CMCS": True,
    "CLIP": True,
    "SSIM": True,
    "CSR": True,
    "compile_success_rate": True,
}

# Display name mapping so the output table uses DesignBench-standard labels.
METRIC_DISPLAY: dict[str, str] = {
    "clip_similarity": "CLIP",
    "structure_similarity": "SSIM",
    "ast_code_op_score": "CMLS",  # code-level structural (op) score
    "ast_code_content_score": "CMCS",  # code-level content score
    "ast_code_content_weighted_score": "CMLS*CMCS",
    "issue accuracy": "IssueAcc",
    "code_score": "CodeScore",
    "compile_success_rate": "CSR",
    "MAE": "MAE",
}

# Keys in per-sample dicts that are not numeric metrics.
NON_METRIC_KEYS = {"compile_error", "parse_error", "compile_success"}


def is_higher_better(metric: str) -> bool:
    return METRIC_DIRECTION.get(metric, True)


def display_name(metric: str) -> str:
    return METRIC_DISPLAY.get(metric, metric)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def aggregate_model(
    samples: dict[str, dict[str, Any]],
) -> tuple[dict[str, float], int, int]:
    """Average numeric per-sample metrics for one model.

    Returns (metric_means, n_samples, n_with_issue).
    - metric_means includes a synthetic ``compile_success_rate`` from the
      boolean ``compile_success`` field when present.
    - n_with_issue counts samples where ``issue accuracy`` > 0 (samples that
      actually had an issue that was graded). Falls back to total sample count
      if the field is absent.
    """
    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}
    compile_successes = 0
    compile_total = 0
    n_with_issue = 0
    has_issue_acc = False

    for _sid, sample in samples.items():
        if not isinstance(sample, dict):
            continue
        for k, v in sample.items():
            if k in NON_METRIC_KEYS:
                if k == "compile_success":
                    compile_total += 1
                    if bool(v):
                        compile_successes += 1
                continue
            if isinstance(v, bool):
                continue  # skip accidental bools
            if isinstance(v, (int, float)):
                metric_sums[k] = metric_sums.get(k, 0.0) + float(v)
                metric_counts[k] = metric_counts.get(k, 0) + 1
            # nested dicts / strings are ignored
        if "issue accuracy" in sample:
            has_issue_acc = True
            try:
                if float(sample["issue accuracy"]) > 0:
                    n_with_issue += 1
            except (TypeError, ValueError):
                pass

    means: dict[str, float] = {
        k: metric_sums[k] / metric_counts[k] for k in metric_sums if metric_counts[k]
    }
    if compile_total > 0:
        means["compile_success_rate"] = compile_successes / compile_total

    n_samples = len(samples)
    if not has_issue_acc:
        n_with_issue = n_samples
    return means, n_samples, n_with_issue


def load_eval_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        warnings.warn(f"missing eval file: {path}", stacklevel=2)
        return None
    try:
        with path.open("r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        warnings.warn(f"failed to load {path}: {e}", stacklevel=2)
        return None


def load_csr_sidecar(dir_path: Path, framework: str) -> dict[str, float] | None:
    """Look for per-framework CSR sidecar files like ``{framework}_csr.json`` or
    anything matching ``*csr*`` / ``*compile*`` for the framework. Returns
    ``{model_key: csr}`` if found."""
    candidates: list[Path] = []
    for pattern in (f"{framework}_csr.json", f"{framework}_compile*.json"):
        candidates.extend(dir_path.glob(pattern))
    # Also catch generic ones that are keyed by framework internally.
    for pattern in ("*csr*.json", "*compile*.json"):
        for p in dir_path.glob(pattern):
            if p not in candidates:
                candidates.append(p)
    for path in candidates:
        try:
            with path.open("r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        # Accept either {model: csr} or {framework: {model: csr}}.
        if isinstance(data, dict):
            if framework in data and isinstance(data[framework], dict):
                return {k: float(v) for k, v in data[framework].items() if isinstance(v, (int, float))}
            if all(isinstance(v, (int, float)) for v in data.values()):
                return {k: float(v) for k, v in data.items()}
    return None


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def fmt_value(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    if metric == "MAE":
        return f"{value:.3f}"
    # Percent-ish metrics are bounded in [0, 1] in DesignBench output.
    return f"{value:.4f}"


def fmt_delta(metric: str, baseline: float | None, variant: float | None) -> str:
    if baseline is None or variant is None:
        return "—"
    delta = variant - baseline
    if baseline == 0:
        pct_str = "inf%" if delta != 0 else "0.00%"
    else:
        pct_str = f"{(delta / abs(baseline)) * 100:+.2f}%"
    sign = "+" if delta >= 0 else ""
    if metric == "MAE":
        return f"{sign}{delta:.3f} ({pct_str})"
    return f"{sign}{delta:.4f} ({pct_str})"


def variant_wins(metric: str, baseline: float | None, variant: float | None) -> bool:
    """True if variant beats baseline by >1% relative in the right direction."""
    if baseline is None or variant is None:
        return False
    if baseline == 0:
        # Can't compute relative change; require an absolute improvement in
        # the right direction and bail out conservatively.
        if is_higher_better(metric):
            return variant > 0
        return variant < 0
    rel = (variant - baseline) / abs(baseline)
    if is_higher_better(metric):
        return rel > 0.01
    # lower-better
    return rel < -0.01


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------
def render_framework_table(
    framework: str,
    baseline_key: str,
    variants: list[str],
    per_model: dict[str, dict[str, float]],
    n_samples: dict[str, int],
    n_with_issue: dict[str, int],
) -> str:
    """Render a single-framework markdown table: rows=metrics, cols=models+deltas."""
    # Metric column order: prefer a canonical ordering where known.
    preferred = [
        "MAE",
        "clip_similarity",
        "structure_similarity",
        "ast_code_op_score",
        "ast_code_content_score",
        "ast_code_content_weighted_score",
        "issue accuracy",
        "code_score",
        "compile_success_rate",
    ]
    present: list[str] = []
    for m in preferred:
        if any(m in per_model.get(k, {}) for k in [baseline_key, *variants]):
            present.append(m)
    # Append any other numeric metrics not in preferred.
    extras: set[str] = set()
    for k in [baseline_key, *variants]:
        extras.update(per_model.get(k, {}).keys())
    for m in sorted(extras - set(present)):
        present.append(m)

    lines: list[str] = []
    lines.append(f"## {framework}")
    # Header: samples-with-issue line.
    meta_bits = []
    for k in [baseline_key, *variants]:
        if k in per_model:
            meta_bits.append(
                f"{k}: n={n_samples.get(k, 0)}, with_issue={n_with_issue.get(k, 0)}"
            )
    if meta_bits:
        lines.append("")
        lines.append("_" + " | ".join(meta_bits) + "_")

    # Columns: Metric | baseline | variant | Δ | ... for each variant.
    header_cols = ["Metric", f"{baseline_key} (baseline)"]
    for v in variants:
        header_cols.extend([v, f"Δ vs baseline ({v})"])
    lines.append("")
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

    for metric in present:
        base_val = per_model.get(baseline_key, {}).get(metric)
        row = [f"{display_name(metric)} ({'↑' if is_higher_better(metric) else '↓'})"]
        row.append(fmt_value(metric, base_val))
        for v in variants:
            var_val = per_model.get(v, {}).get(metric)
            cell = fmt_value(metric, var_val)
            if variant_wins(metric, base_val, var_val):
                cell = f"**{cell}**"
            row.append(cell)
            row.append(fmt_delta(metric, base_val, var_val))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_average_table(
    baseline_key: str,
    variants: list[str],
    per_framework: dict[str, dict[str, dict[str, float]]],
    frameworks: list[str],
) -> str:
    """Average each metric across frameworks for each model, then render."""
    avg_per_model: dict[str, dict[str, float]] = {}
    for model in [baseline_key, *variants]:
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for fw in frameworks:
            model_metrics = per_framework.get(fw, {}).get(model, {})
            for m, v in model_metrics.items():
                totals[m] = totals.get(m, 0.0) + v
                counts[m] = counts.get(m, 0) + 1
        avg_per_model[model] = {m: totals[m] / counts[m] for m in totals if counts[m]}

    # Build metric list.
    preferred = [
        "MAE",
        "clip_similarity",
        "structure_similarity",
        "ast_code_op_score",
        "ast_code_content_score",
        "ast_code_content_weighted_score",
        "issue accuracy",
        "code_score",
        "compile_success_rate",
    ]
    present: list[str] = []
    for m in preferred:
        if any(m in avg_per_model.get(k, {}) for k in [baseline_key, *variants]):
            present.append(m)
    extras: set[str] = set()
    for k in [baseline_key, *variants]:
        extras.update(avg_per_model.get(k, {}).keys())
    for m in sorted(extras - set(present)):
        present.append(m)

    lines: list[str] = []
    lines.append("## Averages across frameworks")
    lines.append("")
    lines.append(
        "_Per-model metrics were first averaged within each framework, then "
        "averaged across the frameworks present in this run._"
    )
    header_cols = ["Metric", f"{baseline_key} (baseline)"]
    for v in variants:
        header_cols.extend([v, f"Δ vs baseline ({v})"])
    lines.append("")
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")
    for metric in present:
        base_val = avg_per_model.get(baseline_key, {}).get(metric)
        row = [f"{display_name(metric)} ({'↑' if is_higher_better(metric) else '↓'})"]
        row.append(fmt_value(metric, base_val))
        for v in variants:
            var_val = avg_per_model.get(v, {}).get(metric)
            cell = fmt_value(metric, var_val)
            if variant_wins(metric, base_val, var_val):
                cell = f"**{cell}**"
            row.append(cell)
            row.append(fmt_delta(metric, base_val, var_val))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="Baseline model key (e.g. qwen2.5-vl-7b-instruct).")
    parser.add_argument(
        "--variants",
        nargs="+",
        required=True,
        help="Variant model keys (e.g. qwen2.5-vl-7b-instruct+omni qwen2.5-vl-7b-instruct+jedi).",
    )
    parser.add_argument("--mode", default="both", help="DesignBench mode suffix (default: both).")
    parser.add_argument(
        "--frameworks",
        nargs="+",
        default=["react", "vue", "angular", "vanilla"],
        help="Frameworks to compare.",
    )
    parser.add_argument("--output", default="results_summary.md", help="Output markdown path.")
    parser.add_argument(
        "--results-dir",
        default="external/DesignBench/code/evaluator/res/DesignRepair",
        help="Directory with per-framework eval JSONs.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repo root (defaults to parent of this script's dir).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parent.parent
    results_dir = (repo_root / args.results_dir).resolve()

    per_framework: dict[str, dict[str, dict[str, float]]] = {}
    n_samples_fw: dict[str, dict[str, int]] = {}
    n_with_issue_fw: dict[str, dict[str, int]] = {}
    frameworks_present: list[str] = []

    for framework in args.frameworks:
        path = results_dir / f"{framework}_{args.mode}.json"
        data = load_eval_json(path)
        if data is None:
            continue
        if args.baseline not in data:
            raise SystemExit(
                f"error: baseline key '{args.baseline}' missing from {path}. "
                f"Available keys: {list(data.keys())}"
            )

        per_model: dict[str, dict[str, float]] = {}
        n_samples: dict[str, int] = {}
        n_with_issue: dict[str, int] = {}

        base_means, base_n, base_issue = aggregate_model(data[args.baseline])
        per_model[args.baseline] = base_means
        n_samples[args.baseline] = base_n
        n_with_issue[args.baseline] = base_issue

        for variant in args.variants:
            if variant not in data:
                warnings.warn(
                    f"variant '{variant}' missing from {path.name}; skipping for this framework",
                    stacklevel=2,
                )
                continue
            v_means, v_n, v_issue = aggregate_model(data[variant])
            per_model[variant] = v_means
            n_samples[variant] = v_n
            n_with_issue[variant] = v_issue

        # Merge in CSR sidecar if it exists and the eval JSON didn't already
        # supply a per-sample compile_success boolean.
        sidecar = load_csr_sidecar(results_dir, framework)
        if sidecar:
            for model_key, csr in sidecar.items():
                if model_key in per_model and "compile_success_rate" not in per_model[model_key]:
                    per_model[model_key]["compile_success_rate"] = csr

        per_framework[framework] = per_model
        n_samples_fw[framework] = n_samples
        n_with_issue_fw[framework] = n_with_issue
        frameworks_present.append(framework)

    if not frameworks_present:
        raise SystemExit(f"error: no eval JSONs found in {results_dir}")

    out_lines: list[str] = []
    out_lines.append("# DesignBench UI-Repair results: baseline vs grounded variants")
    out_lines.append("")
    out_lines.append(f"- Baseline: `{args.baseline}`")
    out_lines.append(f"- Variants: " + ", ".join(f"`{v}`" for v in args.variants))
    out_lines.append(f"- Mode: `{args.mode}`")
    out_lines.append(f"- Frameworks: " + ", ".join(f"`{f}`" for f in frameworks_present))
    out_lines.append("")
    out_lines.append(
        "Metric directions: MAE is lower-better (↓); CLIP, SSIM, CMLS, CMCS, "
        "IssueAcc, CodeScore, CSR are higher-better (↑). A variant cell is "
        "**bolded** when it beats the baseline by more than 1% relative in the "
        "favorable direction."
    )
    out_lines.append("")

    # Averages table at the top.
    out_lines.append(
        render_average_table(args.baseline, args.variants, per_framework, frameworks_present)
    )
    out_lines.append("")

    for framework in frameworks_present:
        out_lines.append(
            render_framework_table(
                framework,
                args.baseline,
                args.variants,
                per_framework[framework],
                n_samples_fw[framework],
                n_with_issue_fw[framework],
            )
        )
        out_lines.append("")

    output_path = (repo_root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"wrote {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
