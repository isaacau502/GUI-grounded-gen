#!/bin/bash
# Run mark-mode ablation: baseline + grounded, 72B + 7B, all 4 frameworks.
# Then AST-only eval on all 4 cells.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate anlp_gen
export GROUNDING_CACHE="$REPO/grounding_structural_cache.json"

log() { echo "[$(date +%T)] $*"; }

# ── Baseline mark, 72B ──
log "Baseline mark: 72B..."
python ui-repair-baseline/run_repair.py --full --no-eval \
    --model qwen2.5-vl-72b-instruct --mode mark \
    --frameworks react vue angular vanilla 2>&1 | tee /tmp/base_mark_72b.log

# ── Baseline mark, 7B ──
log "Baseline mark: 7B..."
python ui-repair-baseline/run_repair.py --full --no-eval \
    --model qwen2.5-vl-7b-instruct --mode mark \
    --frameworks react vue angular vanilla 2>&1 | tee /tmp/base_mark_7b.log

# ── Grounded mark, 72B ──
log "Grounded mark: 72B..."
python scripts/run_repair_grounded.py --full --no-eval \
    --model qwen2.5-vl-72b-instruct --mode mark \
    --frameworks react vue angular vanilla 2>&1 | tee /tmp/omni_mark_72b.log

# ── Grounded mark, 7B ──
log "Grounded mark: 7B..."
python scripts/run_repair_grounded.py --full --no-eval \
    --model qwen2.5-vl-7b-instruct --mode mark \
    --frameworks react vue angular vanilla 2>&1 | tee /tmp/omni_mark_7b.log

# ── Eval all 4 mark cells, AST-only ──
log "Eval: baseline 72b mark"
python scripts/resilient_eval.py --mode mark --skip-render \
    --model qwen2.5-vl-72b-instruct \
    --frameworks react vue angular vanilla

log "Eval: baseline 7b mark"
python scripts/resilient_eval.py --mode mark --skip-render \
    --model qwen2.5-vl-7b-instruct \
    --frameworks react vue angular vanilla

log "Eval: omni 72b mark"
python scripts/resilient_eval.py --mode mark --skip-render \
    --model qwen2.5-vl-72b-instruct+omni \
    --frameworks react vue angular vanilla

log "Eval: omni 7b mark"
python scripts/resilient_eval.py --mode mark --skip-render \
    --model qwen2.5-vl-7b-instruct+omni \
    --frameworks react vue angular vanilla

log "Copying updated eval jsons to results/eval/"
cp external/DesignBench/code/evaluator/res/DesignRepair/*_mark.json results/eval/ 2>/dev/null || true
cp external/DesignBench/code/evaluator/res/DesignRepair/*_both.json results/eval/ 2>/dev/null || true

log "DONE."
