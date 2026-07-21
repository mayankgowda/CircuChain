#!/usr/bin/env bash
# CircuChain V3 (contour domain) — local qwen3 ladder runner, ONE MODEL AT A TIME.
#
#   ./scripts/run_contour_ladder.sh              show per-column progress + suggest next
#   ./scripts/run_contour_ladder.sh <model-key>  run that column to completion
#
# Safe to Ctrl-C and re-run any time: the runner resumes from the responses file
# (append-only JSONL diff), and completed requests are never re-issued or re-billed
# (content-addressed cache). Think columns run at concurrency 2 + 24k ctx — the
# durable-stability policy from v2. Do NOT raise concurrency.
#
# Recommended order (pairs share one serving instance; smallest first for quick wins):
#   qwen3-1.7b-nothink  qwen3-1.7b-think
#   qwen3-4b-nothink    qwen3-4b-think
#   qwen3-8b-nothink    qwen3-8b-think
set -euo pipefail
cd "$(dirname "$0")/.."                                   # v2/
PY=../.venv/bin/python
DS=results/contour/datasets/v3contour_seed20260720
OUT=results/contour
LADDER=(qwen3-1.7b-nothink qwen3-1.7b-think qwen3-4b-nothink qwen3-4b-think
        qwen3-8b-nothink qwen3-8b-think)
PLAN=1000

if ! curl -s --max-time 3 localhost:1234/api/v0/models >/dev/null; then
    echo "LM Studio server is not reachable. Start it first:   lms server start"
    exit 1
fi

if [[ $# -eq 0 ]]; then
    echo "contour ladder status (plan = $PLAN per column):"
    next=""
    for k in "${LADDER[@]}"; do
        f="$OUT/responses/$k.jsonl"
        n=0; [[ -f $f ]] && n=$(wc -l < "$f" | tr -d ' ')
        mark=" "; [[ $n -ge $PLAN ]] && mark="DONE"
        printf "  %-22s %4d/%d  %s\n" "$k" "$n" "$PLAN" "$mark"
        if [[ -z $next && $n -lt $PLAN ]]; then next=$k; fi
    done
    if [[ -n $next ]]; then
        echo
        echo "next up:   ./scripts/run_contour_ladder.sh $next"
    else
        echo
        echo "ladder complete — tell Claude to grade + analyze."
    fi
    exit 0
fi

key="$1"
if [[ ! " ${LADDER[*]} " == *" $key "* ]]; then
    echo "unknown ladder key '$key'. One of: ${LADDER[*]}"
    exit 1
fi
echo ">>> running $key (resumable; Ctrl-C is always safe)"
exec "$PY" -m circuchain.cli run \
    --models configs/models_contour.yaml \
    --dataset "$DS" --out "$OUT" --only "$key"
