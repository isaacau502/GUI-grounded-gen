#!/bin/bash
# Orchestrate the full grounded ablation once the structural cache is ready.
#   1. Wait for grounding_structural_cache.json to hit >=100 entries
#   2. Run grounded repair (72B + 7B) on all samples
#   3. Run evaluator via baseline's --eval-only path
#   4. Produce comparison markdown tables
#
# All output lands in repo root or /tmp/*.log.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"

source ~/miniconda3/etc/profile.d/conda.sh
conda activate anlp_gen

export GROUNDING_CACHE="$REPO/grounding_structural_cache.json"

echo "[orch] ($(date +%T)) Waiting for cache to reach 100 entries..."
until [ -f "$GROUNDING_CACHE" ] && \
      [ "$(python -c "import json; print(len(json.load(open('$GROUNDING_CACHE'))))" 2>/dev/null || echo 0)" -ge 100 ]; do
    sleep 60
done
N=$(python -c "import json; print(len(json.load(open('$GROUNDING_CACHE'))))")
echo "[orch] ($(date +%T)) Cache has $N entries. Proceeding."

# ── Grounded repair: 72B first (it's the strong baseline, most informative) ──
echo "[orch] ($(date +%T)) Starting grounded 72B repair on 111 samples..."
time python scripts/run_repair_grounded.py \
    --model qwen2.5-vl-72b-instruct --full --no-eval \
    2>&1 | tee /tmp/grounded_repair_72b.log
echo "[orch] ($(date +%T)) 72B grounded repair done."

# ── Grounded repair: 7B ──
echo "[orch] ($(date +%T)) Starting grounded 7B repair on 111 samples..."
time python scripts/run_repair_grounded.py \
    --model qwen2.5-vl-7b-instruct --full --no-eval \
    2>&1 | tee /tmp/grounded_repair_7b.log
echo "[orch] ($(date +%T)) 7B grounded repair done."

# ── Eval via baseline's --eval-only path (handles symlinks + metric_ast + CSR) ──
echo "[orch] ($(date +%T)) Running evaluator for 72B+omni..."
time python ui-repair-baseline/run_repair.py --eval-only \
    --model qwen2.5-vl-72b-instruct+omni \
    --frameworks react vue angular vanilla \
    --mode both 2>&1 | tee /tmp/eval_72b_omni.log

echo "[orch] ($(date +%T)) Running evaluator for 7B+omni..."
time python ui-repair-baseline/run_repair.py --eval-only \
    --model qwen2.5-vl-7b-instruct+omni \
    --frameworks react vue angular vanilla \
    --mode both 2>&1 | tee /tmp/eval_7b_omni.log

# ── Comparison tables ──
cd "$REPO"
echo "[orch] ($(date +%T)) Writing comparison tables..."
python scripts/compare_results.py \
    --baseline qwen2.5-vl-72b-instruct \
    --variants qwen2.5-vl-72b-instruct+omni \
    --mode both --frameworks react vue angular vanilla \
    --output results_summary_72b.md 2>&1 | tee /tmp/compare_72b.log

python scripts/compare_results.py \
    --baseline qwen2.5-vl-7b-instruct \
    --variants qwen2.5-vl-7b-instruct+omni \
    --mode both --frameworks react vue angular vanilla \
    --output results_summary_7b.md 2>&1 | tee /tmp/compare_7b.log

echo "[orch] ($(date +%T)) DONE."
echo "  ⇒ results_summary_72b.md"
echo "  ⇒ results_summary_7b.md"
