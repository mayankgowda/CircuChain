#!/usr/bin/env bash
# CircuChain V3 contour — run the local qwen3 ladder unattended, ONE MODEL AT A TIME.
#
# Explicitly loads each size, runs BOTH its columns (nothink then think), then UNLOADS it
# before the next size — so exactly one model is resident at any moment (never all at once).
# This sidesteps the runner's subprocess self-load (which does not inherit PATH under nohup).
#
# Concurrency is the STABILITY-VALIDATED optimum for this M5 + MLX (in models_rhr.yaml):
#   nothink -> conc 4 (LM Studio serves PARALLEL 4; more just queues server-side)
#   think   -> conc 2 (v2 proved conc 3/4 cascades MLX crashes + reload churn = net slower)
# Order: 8b -> 4b -> 1.7b. Every column is resumable; safe to Ctrl-C / re-run.
set -uo pipefail
cd "$(dirname "$0")/.."                                      # v2/
export PATH="$HOME/.lmstudio/bin:$PATH"
PY=../.venv/bin/python
DS=results/rhr/datasets/v3rhrxhard_seed20260724
OUT=results/rhr_xhard
LOG=results/contour/logs
CTX=24576
PLAN=750
mkdir -p "$LOG"

# size -> (model_id, serve_id); columns derived as qwen3-<size>-{nothink,think}
SIZES=(8b 4b 1.7b)

run_col () {   # $1 = column key
    local key="$1" f n
    f="$OUT/responses/$key.jsonl"
    n=0; [[ -f $f ]] && n=$(wc -l < "$f" | tr -d ' ')
    if [[ $n -ge $PLAN ]]; then echo "  SKIP $key (already $n/$PLAN)"; return; fi
    echo "  RUN  $key ($n/$PLAN) $(date +%H:%M:%S)"
    "$PY" -m circuchain.cli run --models configs/models_rhr.yaml \
        --dataset "$DS" --out "$OUT" --only "$key" > "$LOG/$key.log" 2>&1
    n=$(wc -l < "$f" 2>/dev/null | tr -d ' ' || echo 0)
    echo "  DONE $key -> $n/$PLAN $(date +%H:%M:%S)"
}

for sz in "${SIZES[@]}"; do
    mid="qwen/qwen3-$sz"; serve="sweep-qwen3-$sz"
    echo "=== SIZE $sz : load $mid @ $CTX $(date +%H:%M:%S) ==="
    lms load "$mid" --context-length "$CTX" --gpu max --ttl 86400 -y --identifier "$serve" \
        > "$LOG/load_$sz.log" 2>&1
    if ! lms ps 2>/dev/null | grep -q "$serve"; then
        echo "  LOAD FAILED for $serve — see $LOG/load_$sz.log; stopping."; exit 1
    fi
    run_col "qwen3-$sz-nothink"
    run_col "qwen3-$sz-think"
    echo "=== SIZE $sz : unload $serve $(date +%H:%M:%S) ==="
    lms unload "$serve" > /dev/null 2>&1 || true
done
echo "=== LADDER COMPLETE $(date +%H:%M:%S) ==="
