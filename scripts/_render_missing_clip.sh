#!/bin/bash
# Render-and-eval the missing CLIP cells (angular + vanilla for 72B+omni, and react/vue/angular/vanilla for 7B+omni).
# Note: React + Vue 72B+omni already have CLIP. This script fills the gap.
# Angular is slow (~2.5 min/sample via per-sample ng serve); vanilla is fast (direct HTML render).
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate anlp_gen

log() { echo "[$(date +%T)] $*"; }

# Vanilla first — fast, no dev server
log "Render + eval: 72B+omni vanilla"
python scripts/resilient_eval.py --mode both \
    --model qwen2.5-vl-72b-instruct+omni --frameworks vanilla 2>&1 | tail -5 | tee -a /tmp/render_clip.log

log "Render + eval: 7B+omni vanilla"
python scripts/resilient_eval.py --mode both \
    --model qwen2.5-vl-7b-instruct+omni --frameworks vanilla 2>&1 | tail -5 | tee -a /tmp/render_clip.log

# React/vue: needs persistent dev servers (resilient_eval starts them)
log "Render + eval: 7B+omni react + vue"
python scripts/resilient_eval.py --mode both \
    --model qwen2.5-vl-7b-instruct+omni --frameworks react vue 2>&1 | tail -5 | tee -a /tmp/render_clip.log

# Angular last — slowest
log "Render + eval: 72B+omni angular"
python scripts/resilient_eval.py --mode both \
    --model qwen2.5-vl-72b-instruct+omni --frameworks angular 2>&1 | tail -5 | tee -a /tmp/render_clip.log

log "Render + eval: 7B+omni angular"
python scripts/resilient_eval.py --mode both \
    --model qwen2.5-vl-7b-instruct+omni --frameworks angular 2>&1 | tail -5 | tee -a /tmp/render_clip.log

log "Copying eval jsons to results/eval/"
cp external/DesignBench/code/evaluator/res/DesignRepair/*_both.json results/eval/

log "DONE — CLIP cells filled."
