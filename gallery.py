#!/usr/bin/env python3
"""Generate a side-by-side HTML gallery comparing ground truth vs generated repair results."""

import os
import json
import shutil



DESIGNBENCH_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "external", "DesignBench")
MODELS = ["qwen2.5-vl-72b-instruct", "qwen2.5-vl-7b-instruct"]
FRAMEWORKS = {
    "react": {"ext": "jsx", "count": 28},
    "vue": {"ext": "vue", "count": 27},
    "angular": {"ext": "angular", "count": 28},
    "vanilla": {"ext": "html", "count": 28},
}
MODE = "both"
SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_gallery_site")
OUTPUT = os.path.join(SITE_DIR, "index.html")
IMG_DIR = os.path.join(SITE_DIR, "images")


def copy_img(src_path, dest_name):
    """Copy image to IMG_DIR and return relative path, or None if missing."""
    if not os.path.exists(src_path):
        return None
    dest = os.path.join(IMG_DIR, dest_name)
    shutil.copy2(src_path, dest)
    return f"images/{dest_name}"


def load_metrics(fw, mode, model):
    res_path = os.path.join(DESIGNBENCH_ROOT, "code", "evaluator", "res", "DesignRepair", f"{fw}_{mode}.json")
    if not os.path.exists(res_path):
        return {}
    with open(res_path) as f:
        data = json.load(f)
    return data.get(model, {})


def build_gallery():
    os.makedirs(IMG_DIR, exist_ok=True)
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
                clip_raw = m.get("clip_similarity", 0)
                ssim_raw = m.get("structure_similarity", 0)
                cmls_raw = m.get("ast_code_op_score", 0)
                cmcs_raw = m.get("ast_code_content_weighted_score", 0)
                issacc_raw = m.get("issue accuracy", 0)
                clip = f"{clip_raw:.3f}" if isinstance(clip_raw, float) else "—"
                ssim = f"{ssim_raw:.3f}" if isinstance(ssim_raw, float) else "—"
                cmls = f"{cmls_raw:.4f}" if isinstance(cmls_raw, float) else "—"
                cmcs = f"{cmcs_raw:.4f}" if isinstance(cmcs_raw, float) else "—"
                issue_acc = f"{issacc_raw:.2f}" if isinstance(issacc_raw, float) else "—"

                # Read code snippet (first 50 lines)
                code_preview = ""
                if os.path.exists(gen_code):
                    with open(gen_code, "r", errors="replace") as f:
                        lines = f.readlines()[:50]
                        code_preview = "".join(lines)
                        if len(lines) == 50:
                            code_preview += "\n... (truncated)"

                broken_uri = copy_img(broken_img, f"{fw}_{sid}_broken.png")
                gt_uri = copy_img(gt_img, f"{fw}_{sid}_gt.png")
                gen_uri = copy_img(gen_img, f"{fw}_{i}_{model}_gen.png")

                rows.append({
                    "fw": fw,
                    "model": model,
                    "sample": i,
                    "csr_pass": csr_pass,
                    "broken_uri": broken_uri,
                    "gt_uri": gt_uri,
                    "gen_uri": gen_uri,
                    "clip": clip, "clip_raw": float(clip_raw) if isinstance(clip_raw, (int, float)) else 0,
                    "ssim": ssim, "ssim_raw": float(ssim_raw) if isinstance(ssim_raw, (int, float)) else 0,
                    "cmls": cmls, "cmls_raw": float(cmls_raw) if isinstance(cmls_raw, (int, float)) else 0,
                    "cmcs": cmcs, "cmcs_raw": float(cmcs_raw) if isinstance(cmcs_raw, (int, float)) else 0,
                    "issue_acc": issue_acc, "issacc_raw": float(issacc_raw) if isinstance(issacc_raw, (int, float)) else 0,
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
  <div>
    <label>Sort:</label>
    <select id="sort-metric">
      <option value="none">Default</option>
      <option value="clip">CLIP</option>
      <option value="ssim">SSIM</option>
      <option value="cmls">CMLS</option>
      <option value="cmcs">CMCS</option>
      <option value="issacc">IssAcc</option>
    </select>
    <select id="sort-dir">
      <option value="desc">High → Low</option>
      <option value="asc">Low → High</option>
    </select>
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
<div class="card" data-fw="{r['fw']}" data-model="{r['model']}" data-sample="{r['sample']}" data-csr="{'pass' if r['csr_pass'] else 'fail'}" data-clip="{r['clip_raw']}" data-ssim="{r['ssim_raw']}" data-cmls="{r['cmls_raw']}" data-cmcs="{r['cmcs_raw']}" data-issacc="{r['issacc_raw']}">
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
const gallery = document.getElementById('gallery');
const cards = Array.from(document.querySelectorAll('.card'));
const fwF = document.getElementById('fw-filter');
const mF = document.getElementById('model-filter');
const sF = document.getElementById('sample-filter');
const sortM = document.getElementById('sort-metric');
const sortD = document.getElementById('sort-dir');
const countEl = document.getElementById('count');

function update() {
  // Sort
  const metric = sortM.value;
  const asc = sortD.value === 'asc';
  if (metric !== 'none') {
    cards.sort((a, b) => {
      const av = parseFloat(a.dataset[metric]) || 0;
      const bv = parseFloat(b.dataset[metric]) || 0;
      return asc ? av - bv : bv - av;
    });
    cards.forEach(c => gallery.appendChild(c));
  }

  // Filter
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

[fwF, mF, sF, sortM, sortD].forEach(el => el.addEventListener('change', update));
update();
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
