"""Pool all frameworks and both grounding signals; rank top N candidates.

Use when you want to cherry-pick the visually strongest samples across
the whole panel for one model size, regardless of framework or signal.

Output: poster/qualitative_picks_ALL_{size}_top{N}.html
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "external/DesignBench/code/evaluator/res/DesignRepair"
DATA = REPO / "external/DesignBench/data/DesignRepair"
RESULTS = REPO / "external/DesignBench/results/repair"

FRAMEWORKS = ["react", "vue", "angular", "vanilla"]
VARIANTS = ["omni", "jedi"]


def model_name(size, variant):
    s = "7b" if size == "7b" else "72b"
    base = f"qwen2.5-vl-{s}-instruct"
    if variant == "baseline":
        return base
    return f"{base}+{variant}"


def issue_of(sample_id, framework):
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


def pool_candidates(size, metric="clip_similarity", require_both_compile=True):
    """Return pooled [(framework, variant, sample_id, base_val, var_val, delta, issue)] sorted desc."""
    rows = []
    base_key = model_name(size, "baseline")

    for fw in FRAMEWORKS:
        p = EVAL / f"{fw}_both.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        if base_key not in data:
            continue
        b = data[base_key]

        for variant in VARIANTS:
            var_key = model_name(size, variant)
            if var_key not in data:
                continue
            v = data[var_key]

            for s in set(b.keys()) & set(v.keys()):
                b_ok = b[s].get("compile_success", False)
                v_ok = v[s].get("compile_success", False)
                if require_both_compile and not (b_ok and v_ok):
                    continue
                b_val = b[s].get(metric, 0.0)
                v_val = v[s].get(metric, 0.0)
                if b_val == 0 and v_val == 0:
                    continue  # metric not computed
                delta = v_val - b_val
                rows.append({
                    "framework": fw,
                    "variant": variant,
                    "sample_id": s,
                    "base": b_val,
                    "var": v_val,
                    "delta": delta,
                    "b_ok": b_ok,
                    "v_ok": v_ok,
                    "issue": issue_of(s, fw),
                })

    rows.sort(key=lambda r: -r["delta"])
    return rows


def sample_paths(fw, size, variant, sample_id):
    base_m = model_name(size, "baseline")
    var_m = model_name(size, variant)
    rel_data = f"../external/DesignBench/data/DesignRepair/{fw}/{sample_id}"
    rel_base = f"../external/DesignBench/results/repair/{fw}-{fw}/{base_m}"
    rel_var = f"../external/DesignBench/results/repair/{fw}-{fw}/{var_m}"
    return {
        "broken": f"{rel_data}/{sample_id}.png",
        "reference": f"{rel_data}/repaired.png",
        "grounding": f"grounding_overlays/{fw}_{variant}_{sample_id}.png",
        "baseline": f"{rel_base}/{fw}_{sample_id}_{base_m}_{fw}_both.png",
        "variant": f"{rel_var}/{fw}_{sample_id}_{var_m}_{fw}_both.png",
    }


def make_html(size, rows, topk, out_path):
    header = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Pooled candidates: Qwen-{size}</title>
<style>
  body {{ font-family: sans-serif; max-width: 1800px; margin: 20px auto; padding: 10px; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 16px; margin-top: 26px; border-bottom: 1.5px solid #333; padding-bottom: 4px; }}
  .row {{ display: flex; gap: 8px; margin-bottom: 16px; align-items: flex-start; }}
  .col {{ flex: 1; text-align: center; }}
  .col img {{
    width: 100%; max-height: 320px; object-fit: contain;
    border: 1px solid #ccc; background: #fafafa;
  }}
  .col .label {{ font-size: 11px; font-weight: bold; margin-top: 4px; }}
  .col.missing img {{ content: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><rect fill="%23eee" width="100" height="60"/><text x="50" y="30" text-anchor="middle" dominant-baseline="middle" fill="%23999" font-size="10">COMPILE FAIL</text></svg>'); }}
  .meta {{ font-size: 11px; color: #555; }}
  .tag-omni {{ background: #d0eecf; padding: 1px 6px; border-radius: 3px; font-weight: bold; }}
  .tag-jedi {{ background: #ffe4b5; padding: 1px 6px; border-radius: 3px; font-weight: bold; }}
  .gain {{ color: #1a7f37; font-weight: bold; }}
</style>
</head>
<body>
<h1>Pooled top-{topk} qualitative candidates: Qwen2.5-VL-<code>{size}</code></h1>
<p class="meta">All 4 frameworks × both grounding variants (+omni, +jedi) pooled. Ranked by CLIP gain. Both-compile only.</p>
<p class="meta">Column order: broken | grounding output | reference | baseline repair | grounded repair.</p>
"""
    body = []
    for i, r in enumerate(rows[:topk], 1):
        paths = sample_paths(r["framework"], size, r["variant"], r["sample_id"])
        tag_cls = f"tag-{r['variant']}"
        body.append(f"""\
<h2>#{i} — <span class="{tag_cls}">{r['variant']}</span> <code>{r['framework']}/{r['sample_id']}</code> · issue: <code>{r['issue']}</code></h2>
<div class="meta">
  CLIP base={r['base']:.3f} → var={r['var']:.3f} <span class="gain">(+{r['delta']:.3f})</span> · both compiled
</div>
<div class="row">
  <div class="col"><img src="{paths['broken']}"/><div class="label">BROKEN</div></div>
  <div class="col"><img src="{paths['grounding']}"/><div class="label">{r['variant'].upper()} OUTPUT</div></div>
  <div class="col"><img src="{paths['reference']}"/><div class="label">TARGET</div></div>
  <div class="col"><img src="{paths['baseline']}"/><div class="label">BASELINE</div></div>
  <div class="col"><img src="{paths['variant']}"/><div class="label">+{r['variant'].upper()}</div></div>
</div>
""")

    html = header + "\n".join(body) + "\n</body></html>\n"
    out_path.write_text(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="7b", choices=["7b", "72b"])
    ap.add_argument("--topk", type=int, default=30)
    args = ap.parse_args()

    rows = pool_candidates(args.size)
    out_dir = REPO / "poster"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"qualitative_picks_ALL_{args.size}_top{args.topk}.html"
    make_html(args.size, rows, args.topk, out_path)

    print(f"Wrote {out_path}")
    print(f"Top {args.topk} candidates for Qwen-{args.size} (pooled across frameworks + variants):")
    print(f"  {'rank':>4} {'fw':<8} {'variant':<6} {'id':>4} "
          f"{'issue':<36} {'base':>6} {'var':>6} {'delta':>8}")
    for i, r in enumerate(rows[:args.topk], 1):
        print(f"  {i:>4} {r['framework']:<8} {r['variant']:<6} {r['sample_id']:>4} "
              f"{r['issue']:<36} {r['base']:>6.3f} {r['var']:>6.3f} +{r['delta']:>.3f}")

    print(f"\nOpen: file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
