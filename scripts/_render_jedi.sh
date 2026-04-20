#!/bin/bash
# Render JEDI-grounded outputs for all 8 cells (7B+jedi, 72B+jedi × 4fw).
# Fast frameworks first (vanilla, react, vue), angular last (slow).
# Clears stale AST-only entries first so resilient_eval actually renders.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate anlp_gen

log() { echo "[$(date +%T)] $*"; }

# Clear AST-only entries from prior JEDI eval so render pass actually runs
python -c "
import json
for fw in ['react','vue','angular','vanilla']:
    p = f'external/DesignBench/code/evaluator/res/DesignRepair/{fw}_both.json'
    d = json.load(open(p))
    cleared = []
    for k in ['qwen2.5-vl-72b-instruct+jedi', 'qwen2.5-vl-7b-instruct+jedi']:
        if k in d:
            del d[k]
            cleared.append(k)
    if cleared:
        json.dump(d, open(p,'w'), indent=2)
        print(f'cleared {fw}: {cleared}')
"

# Vanilla first (no dev server needed)
for model in qwen2.5-vl-72b-instruct+jedi qwen2.5-vl-7b-instruct+jedi; do
    log "Render eval: $model vanilla"
    python scripts/resilient_eval.py --mode both --model "$model" --frameworks vanilla 2>&1 | tail -3
done

# React + Vue (persistent dev servers in resilient_eval)
for model in qwen2.5-vl-72b-instruct+jedi qwen2.5-vl-7b-instruct+jedi; do
    log "Render eval: $model react + vue"
    python scripts/resilient_eval.py --mode both --model "$model" --frameworks react vue 2>&1 | tail -3
done

# Angular last (per-sample ng serve, slow)
for model in qwen2.5-vl-72b-instruct+jedi qwen2.5-vl-7b-instruct+jedi; do
    log "Render eval: $model angular"
    python scripts/resilient_eval.py --mode both --model "$model" --frameworks angular 2>&1 | tail -3
done

log "Copying eval jsons..."
cp external/DesignBench/code/evaluator/res/DesignRepair/*_both.json results/eval/

log "Running full stats panel..."
python scripts/stats_test.py 2>&1 | tee /tmp/stats_with_jedi_clip.log

log "DONE. Stats at /tmp/stats_with_jedi_clip.log"
