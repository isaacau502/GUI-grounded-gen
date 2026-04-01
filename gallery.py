#!/usr/bin/env python3
"""Generate a side-by-side HTML gallery comparing ground truth vs generated repair results."""

import os
import json



DESIGNBENCH_ROOT = "/home/isaacau/gui-g-gen/external/DesignBench"
MODELS = ["qwen2.5-vl-72b-instruct", "qwen2.5-vl-7b-instruct"]
FRAMEWORKS = {
    "react": {"ext": "jsx", "count": 28},
    "vue": {"ext": "vue", "count": 27},
    "angular": {"ext": "angular", "count": 28},
    "vanilla": {"ext": "html", "count": 28},
}
MODE = "both"
OUTPUT = "/home/isaacau/gui-g-gen/gallery.html"


def img_to_data_uri(path):
    if not os.path.exists(path):
        return None
    import base64
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


def load_metrics(fw, mode, model):
    res_path = os.path.join(DESIGNBENCH_ROOT, "code", "evaluator", "res", "DesignRepair", f"{fw}_{mode}.json")
    if not os.path.exists(res_path):
        return {}
    with open(res_path) as f:
        data = json.load(f)
    return data.get(model, {})


def build_gallery():
    rows = []

    for fw, info in FRAMEWORKS.items():
        for model in MODELS:
            metrics = load_metrics(fw, MODE, model)
            for i in range(1, info["count"] + 1):
                sid = str(i)

                # Broken input screenshot ({id}.png) and ground truth repaired (repaired.png)
                broken_img = os.path.join(DESIGNBENCH_ROOT, "data", "DesignRepair", fw, sid, f"{sid}.png")
                gt_img = os.path.join(DESIGNBENCH_ROOT, "data", "DesignRepair", fw, sid, "repaired.png")
                # Generated screenshot
                gen_img = os.path.join(
                    DESIGNBENCH_ROOT, "results", "repair", f"{fw}-{fw}", model,
                    f"{fw}_{i}_{model}_{fw}_{MODE}.png"
                )
                # Generated code
                gen_code = os.path.join(
                    DESIGNBENCH_ROOT, "results", "repair", f"{fw}-{fw}", model,
                    f"{fw}_{i}_{model}_{fw}_{MODE}.{info['ext']}"
                )

                m = metrics.get(sid, {})
                compile_error = m.get("compile_error", "NULL")
                csr_pass = compile_error == "NULL"
                clip = m.get("clip_similarity", "—")
                ssim = m.get("structure_similarity", "—")
                cmls = m.get("ast_code_op_score", "—")
                cmcs = m.get("ast_code_content_weighted_score", "—")
                issue_acc = m.get("issue accuracy", "—")

                if isinstance(clip, float):
                    clip = f"{clip:.3f}"
                if isinstance(ssim, float):
                    ssim = f"{ssim:.3f}"
                if isinstance(cmls, float):
                    cmls = f"{cmls:.4f}"
                if isinstance(cmcs, float):
                    cmcs = f"{cmcs:.4f}"
                if isinstance(issue_acc, float):
                    issue_acc = f"{issue_acc:.2f}"

                # Read code snippet (first 50 lines)
                code_preview = ""
                if os.path.exists(gen_code):
                    with open(gen_code, "r", errors="replace") as f:
                        lines = f.readlines()[:50]
                        code_preview = "".join(lines)
                        if len(lines) == 50:
                            code_preview += "\n... (truncated)"

                broken_uri = img_to_data_uri(broken_img)
                gt_uri = img_to_data_uri(gt_img)
                gen_uri = img_to_data_uri(gen_img)

                rows.append({
                    "fw": fw,
                    "model": model,
                    "sample": i,
                    "csr_pass": csr_pass,
                    "broken_uri": broken_uri,
                    "gt_uri": gt_uri,
                    "gen_uri": gen_uri,
                    "clip": clip,
                    "ssim": ssim,
                    "cmls": cmls,
                    "cmcs": cmcs,
                    "issue_acc": issue_acc,
                    "code": code_preview,
                })

    # Build HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DesignBench Repair — Gallery</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
h1 { margin-bottom: 8px; color: #f0f6fc; }
.controls { position: sticky; top: 0; background: #161b22; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; z-index: 100; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; border: 1px solid #30363d; }
.controls label { font-size: 13px; color: #8b949e; }
.controls select { background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 12px; overflow: hidden; }
.card-header { padding: 10px 16px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
.card-header h3 { font-size: 14px; color: #f0f6fc; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #1f6feb33; color: #58a6ff; }
.csr-pass { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #23863533; color: #3fb950; }
.csr-fail { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #da363333; color: #f85149; }
.images { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px; background: #30363d; }
.img-col { background: #0d1117; padding: 8px; text-align: center; }
.img-col img { max-width: 100%; max-height: 400px; border-radius: 4px; }
.img-col .label { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
.no-img { color: #484f58; font-size: 12px; padding: 40px; }
.metrics { padding: 10px 16px; display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; }
.metric { display: flex; flex-direction: column; align-items: center; }
.metric .val { font-weight: 600; color: #f0f6fc; font-size: 14px; }
.metric .key { color: #8b949e; font-size: 10px; }
details { padding: 0 16px 10px; }
summary { font-size: 12px; color: #8b949e; cursor: pointer; padding: 4px 0; }
pre { background: #0d1117; padding: 10px; border-radius: 4px; font-size: 11px; overflow-x: auto; max-height: 300px; color: #c9d1d9; margin-top: 4px; }
.hidden { display: none; }
.count { font-size: 13px; color: #8b949e; }
</style>
</head>
<body>
<h1>DesignBench Repair Gallery</h1>
<div class="controls">
  <div>
    <label>Framework:</label>
    <select id="fw-filter">
      <option value="all">All</option>
      <option value="react">React</option>
      <option value="vue">Vue</option>
      <option value="angular">Angular</option>
      <option value="vanilla">Vanilla</option>
    </select>
  </div>
  <div>
    <label>Model:</label>
    <select id="model-filter">
      <option value="all">All</option>
"""
    for m in MODELS:
        html += f'      <option value="{m}">{m}</option>\n'
    html += """    </select>
  </div>
  <div>
    <label>Sample:</label>
    <select id="sample-filter">
      <option value="all">All</option>
"""
    for i in range(1, 29):
        html += f'      <option value="{i}">{i}</option>\n'
    html += """    </select>
  </div>
  <span class="count" id="count"></span>
</div>
<div id="gallery">
"""

    for r in rows:
        broken_img_tag = f'<img src="{r["broken_uri"]}" loading="lazy">' if r["broken_uri"] else '<div class="no-img">No broken img</div>'
        gt_img_tag = f'<img src="{r["gt_uri"]}" loading="lazy">' if r["gt_uri"] else '<div class="no-img">No ground truth</div>'
        gen_img_tag = f'<img src="{r["gen_uri"]}" loading="lazy">' if r["gen_uri"] else '<div class="no-img">No screenshot</div>'
        escaped_code = r["code"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        csr_class = "csr-pass" if r["csr_pass"] else "csr-fail"
        csr_label = "CSR: PASS" if r["csr_pass"] else "CSR: FAIL"

        html += f"""
<div class="card" data-fw="{r['fw']}" data-model="{r['model']}" data-sample="{r['sample']}" data-csr="{'pass' if r['csr_pass'] else 'fail'}">
  <div class="card-header">
    <h3>{r['fw']} / sample {r['sample']}</h3>
    <div><span class="{csr_class}">{csr_label}</span> <span class="badge">{r['model'].split('-instruct')[0]}</span></div>
  </div>
  <div class="images">
    <div class="img-col"><div class="label">Broken (Input)</div>{broken_img_tag}</div>
    <div class="img-col"><div class="label">Ground Truth (Repaired)</div>{gt_img_tag}</div>
    <div class="img-col"><div class="label">Generated</div>{gen_img_tag}</div>
  </div>
  <div class="metrics">
    <div class="metric"><span class="val">{r['clip']}</span><span class="key">CLIP</span></div>
    <div class="metric"><span class="val">{r['ssim']}</span><span class="key">SSIM</span></div>
    <div class="metric"><span class="val">{r['cmls']}</span><span class="key">CMLS</span></div>
    <div class="metric"><span class="val">{r['cmcs']}</span><span class="key">CMCS</span></div>
    <div class="metric"><span class="val">{r['issue_acc']}</span><span class="key">IssAcc</span></div>
  </div>
  <details><summary>View code</summary><pre>{escaped_code}</pre></details>
</div>
"""

    html += """
</div>
<script>
const cards = document.querySelectorAll('.card');
const fwF = document.getElementById('fw-filter');
const mF = document.getElementById('model-filter');
const sF = document.getElementById('sample-filter');
const countEl = document.getElementById('count');

function filter() {
  let shown = 0;
  cards.forEach(c => {
    const fwOk = fwF.value === 'all' || c.dataset.fw === fwF.value;
    const mOk = mF.value === 'all' || c.dataset.model === mF.value;
    const sOk = sF.value === 'all' || c.dataset.sample === sF.value;
    const show = fwOk && mOk && sOk;
    c.classList.toggle('hidden', !show);
    if (show) shown++;
  });
  countEl.textContent = shown + ' / ' + cards.length;
}

fwF.addEventListener('change', filter);
mF.addEventListener('change', filter);
sF.addEventListener('change', filter);
filter();
</script>
</body>
</html>
"""

    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"Gallery written to {OUTPUT}")
    print(f"Total cards: {len(rows)}")


if __name__ == "__main__":
    build_gallery()
