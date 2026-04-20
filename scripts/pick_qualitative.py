"""Help pick a qualitative example for the poster.

For a given (framework, model, grounding_signal) cell, rank samples by
CLIP-gain over baseline and emit an HTML browser showing 4 images per
candidate (broken input | reference target | baseline repair | grounded
repair) side by side. Open in a browser, eyeball, pick the one that
reads best at poster distance.

Usage:
    python scripts/pick_qualitative.py \
        --framework angular --size 7b --variant omni --topk 10

    # for the failure case (compile-fail emphasis):
    python scripts/pick_qualitative.py \
        --framework react --size 7b --variant jedi --topk 10 --rank worst

Output: poster/qualitative_picks_{framework}_{size}_{variant}.html
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "external/DesignBench/code/evaluator/res/DesignRepair"
DATA = REPO / "external/DesignBench/data/DesignRepair"
RESULTS = REPO / "external/DesignBench/results/repair"


def model_name(size, variant):
    s = "7b" if size == "7b" else "72b"
    base = f"qwen2.5-vl-{s}-instruct"
    if variant == "baseline":
        return base
    return f"{base}+{variant}"


def sample_paths(framework, size, variant, sample_id):
    """Absolute paths to the 4 images for a given sample."""
    ext = {"react": "jsx", "vue": "vue", "angular": "angular", "vanilla": "html"}[framework]
    baseline_model = model_name(size, "baseline")
    variant_model = model_name(size, variant)
    sample_dir = DATA / framework / str(sample_id)
    baseline_dir = RESULTS / f"{framework}-{framework}" / baseline_model
    variant_dir = RESULTS / f"{framework}-{framework}" / variant_model

    return {
        "broken": sample_dir / f"{sample_id}.png",
        "reference": sample_dir / "repaired.png",
        "baseline": baseline_dir / f"{framework}_{sample_id}_{baseline_model}_{framework}_both.png",
        "variant": variant_dir / f"{framework}_{sample_id}_{variant_model}_{framework}_both.png",
        "config": sample_dir / f"{sample_id}.json",
    }


def issue_of(sample_id, framework):
    """Return the defect label(s) as a display string."""
    cfg_path = DATA / framework / str(sample_id) / f"{sample_id}.json"
    if not cfg_path.exists():
        return "?"
    cfg = json.loads(cfg_path.read_text())
    issue = cfg.get("issue", [])
    if isinstance(issue, str):
        return issue
    if isinstance(issue, list):
        return ", ".join(issue)
    return "?"


def rank_candidates(framework, size, variant, rank_by="clip_gain", metric="clip_similarity"):
    """Return [(sample_id, baseline_val, variant_val, delta)] sorted descending by delta.

    rank_by: 'clip_gain' (variant - baseline, descending = best improvements first)
             'clip_loss' (baseline - variant, descending = biggest regressions first)
    """
    assert rank_by in ("clip_gain", "clip_loss")

    p = EVAL / f"{framework}_both.json"
    data = json.loads(p.read_text())

    base_key = model_name(size, "baseline")
    var_key = model_name(size, variant)

    if base_key not in data or var_key not in data:
        return []

    b = data[base_key]
    v = data[var_key]
    common = set(b.keys()) & set(v.keys())

    rows = []
    for s in common:
        b_val = b[s].get(metric, 0.0)
        v_val = v[s].get(metric, 0.0)
        # For the failure case we want the biggest regressions, so we want
        # baseline compiled but variant didn't (or variant_val much worse).
        delta = v_val - b_val
        rows.append((s, b_val, v_val, delta,
                     b[s].get("compile_success", False),
                     v[s].get("compile_success", False),
                     issue_of(s, framework)))

    if rank_by == "clip_gain":
        rows.sort(key=lambda r: -r[3])
    else:
        rows.sort(key=lambda r: r[3])  # ascending = most negative first

    return rows


def make_html(framework, size, variant, rows, topk, out_path, rank_by):
    """Emit an HTML page with up to topk rows, each showing all 4 images."""
    header = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Qualitative candidates: {framework} × {size} × {variant}</title>
<style>
  body {{ font-family: sans-serif; max-width: 1600px; margin: 20px auto; padding: 10px; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 18px; margin-top: 30px; border-bottom: 2px solid #333; padding-bottom: 4px; }}
  .row {{ display: flex; gap: 10px; margin-bottom: 24px; align-items: flex-start; }}
  .col {{ flex: 1; text-align: center; }}
  .col img {{
    width: 100%; max-height: 400px; object-fit: contain;
    border: 1px solid #ccc; background: #fafafa;
  }}
  .col .label {{ font-size: 13px; font-weight: bold; margin-top: 4px; }}
  .col.missing img {{ content: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><rect fill="%23eee" width="100" height="60"/><text x="50" y="30" text-anchor="middle" dominant-baseline="middle" fill="%23999" font-size="10">COMPILE FAIL</text></svg>'); }}
  .meta {{ font-size: 12px; color: #555; }}
  .gain-good {{ color: #1a7f37; font-weight: bold; }}
  .gain-bad {{ color: #a00; font-weight: bold; }}
</style>
</head>
<body>
<h1>Qualitative candidates: <code>{framework}</code> × Qwen2.5-VL-<code>{size}</code> × <code>+{variant}</code></h1>
<p class="meta">Ranked by CLIP {'gain' if rank_by == 'clip_gain' else 'loss'} (variant minus baseline). Top {topk} shown.</p>
<p class="meta">Column order: <b>broken input</b> | <b>reference target</b> | <b>baseline repair</b> | <b>+{variant} repair</b>.</p>
"""
    body = []
    for i, (sid, b_val, v_val, delta, b_ok, v_ok, issue) in enumerate(rows[:topk], 1):
        paths = sample_paths(framework, size, variant, sid)
        good = delta > 0
        cls = "gain-good" if good else "gain-bad"
        sign = "+" if delta >= 0 else ""
        body.append(f"""\
<h2>#{i} — sample <code>{sid}</code> · issue: <code>{issue}</code></h2>
<div class="meta">
  CLIP baseline={b_val:.3f} → variant={v_val:.3f} <span class="{cls}">({sign}{delta:.3f})</span> ·
  compile: baseline={b_ok}, variant={v_ok}
</div>
<div class="row">
  <div class="col"><img src="{paths['broken']}"/><div class="label">BROKEN INPUT</div></div>
  <div class="col"><img src="{paths['reference']}"/><div class="label">REFERENCE TARGET</div></div>
  <div class="col {'missing' if not b_ok else ''}"><img src="{paths['baseline']}"/><div class="label">BASELINE REPAIR</div></div>
  <div class="col {'missing' if not v_ok else ''}"><img src="{paths['variant']}"/><div class="label">+{variant.upper()} REPAIR</div></div>
</div>
""")

    html = header + "\n".join(body) + "\n</body></html>\n"
    out_path.write_text(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--framework", default="angular",
                    choices=["react", "vue", "angular", "vanilla"])
    ap.add_argument("--size", default="7b", choices=["7b", "72b"])
    ap.add_argument("--variant", default="omni", choices=["omni", "jedi"])
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--metric", default="clip_similarity",
                    help="metric used for ranking (default clip_similarity)")
    ap.add_argument("--rank", default="best",
                    choices=["best", "worst"],
                    help="'best' = largest gain (for success case); "
                         "'worst' = largest regression (for failure case)")
    args = ap.parse_args()

    rank_by = "clip_gain" if args.rank == "best" else "clip_loss"
    rows = rank_candidates(args.framework, args.size, args.variant,
                           rank_by=rank_by, metric=args.metric)

    if not rows:
        print(f"No data for {args.framework} × {args.size} × {args.variant}")
        return

    out_dir = REPO / "poster"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"qualitative_picks_{args.framework}_{args.size}_{args.variant}_{args.rank}.html"
    make_html(args.framework, args.size, args.variant, rows, args.topk, out_path, rank_by)

    print(f"Wrote {out_path}")
    print(f"Top {args.topk} candidates by {args.metric} {rank_by}:")
    print(f"  {'rank':>4} {'id':>4} {'issue':<40} {'base':>7} {'var':>7} {'delta':>8}  compile(b|v)")
    for i, r in enumerate(rows[:args.topk], 1):
        sid, b_val, v_val, delta, b_ok, v_ok, issue = r
        print(f"  {i:>4} {sid:>4} {issue:<40} {b_val:>7.3f} {v_val:>7.3f} "
              f"{delta:>+8.3f}  {int(b_ok)}|{int(v_ok)}")

    print(f"\nOpen in browser: file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
