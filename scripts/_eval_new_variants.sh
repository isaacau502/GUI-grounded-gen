#!/bin/bash
# After mark + JEDI generation finishes, run AST-only eval for all new variants.
# Waits until both PID logs show generation completion.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate anlp_gen

log() { echo "[$(date +%T)] $*"; }

# Wait until no run_repair_grounded* or ui-repair-baseline/run_repair.py processes are active.
log "Waiting for mark + JEDI generation jobs to finish..."
until ! pgrep -f "run_repair_grounded.*\.py|ui-repair-baseline/run_repair\.py" >/dev/null; do
    sleep 60
done
log "Generation jobs complete."

# Six new (model, mode) combos to eval:
# 1. qwen2.5-vl-72b-instruct+jedi  both
# 2. qwen2.5-vl-7b-instruct+jedi   both
# 3. qwen2.5-vl-72b-instruct       mark (baseline)
# 4. qwen2.5-vl-7b-instruct        mark (baseline)
# 5. qwen2.5-vl-72b-instruct+omni  mark
# 6. qwen2.5-vl-7b-instruct+omni   mark

EVAL_CONFIGS=(
    "qwen2.5-vl-72b-instruct+jedi:both"
    "qwen2.5-vl-7b-instruct+jedi:both"
    "qwen2.5-vl-72b-instruct:mark"
    "qwen2.5-vl-7b-instruct:mark"
    "qwen2.5-vl-72b-instruct+omni:mark"
    "qwen2.5-vl-7b-instruct+omni:mark"
)

for cfg in "${EVAL_CONFIGS[@]}"; do
    model="${cfg%%:*}"
    mode="${cfg##*:}"
    log "Eval: model=$model mode=$mode"
    python scripts/resilient_eval.py \
        --model "$model" --mode "$mode" --skip-render \
        --frameworks react vue angular vanilla 2>&1 | tail -5
done

log "Copying eval jsons..."
cp external/DesignBench/code/evaluator/res/DesignRepair/*_both.json results/eval/ 2>/dev/null || true
cp external/DesignBench/code/evaluator/res/DesignRepair/*_mark.json results/eval/ 2>/dev/null || true

log "Running stats on all variants..."
python scripts/stats_test.py 2>&1 | tee /tmp/stats_all.log

log "DONE. Check /tmp/stats_all.log for summary."
