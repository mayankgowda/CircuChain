#!/usr/bin/env python3
"""Budget-calibration pilot (paper appendix): run one model over a small stratified subset
of the FROZEN dataset at the candidate decoding policy, and report the reasoning-token
distribution, truncation rate, and ANSWER-line rate. The recommended budget is
min(cap, ceil(1.25 * p95 / 1024) * 1024).

Pilot completions share the sweep's content-addressed cache (results/cache), so any pilot
call made at the final parameters is a free cache hit for the full sweep. Pilot responses
are bookkept separately under results/pilot/ so a later parameter change cannot poison the
sweep's resume logic.

Usage:
    python scripts/pilot_budget.py --model-key qwen3-4b-think [--n 24] [--models CONFIG]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, V2)

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from circuchain.run import run_model, load_instances  # noqa: E402

_ANSWER = re.compile(r"^\s*\**\s*ANSWER\s*\**\s*[:=]", re.IGNORECASE | re.MULTILINE)


def stratified_subset(instances, n, seed=0):
    """Deterministic subset balanced across (cell, method), spread over topologies."""
    by_cm: dict = {}
    for inst in instances:
        cell = inst["id"].rsplit("-", 2)[-2]
        by_cm.setdefault((cell, inst["contract"]["method"]), []).append(inst)
    rng = np.random.default_rng(seed)
    per = max(1, n // len(by_cm))
    picked = []
    for key in sorted(by_cm):
        pool = sorted(by_cm[key], key=lambda r: r["id"])
        idx = rng.permutation(len(pool))[:per]
        picked += [pool[i] for i in idx]
    return picked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-key", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--models", default=os.path.join(V2, "configs", "models.yaml"))
    ap.add_argument("--dataset", default=os.path.join(V2, "results", "datasets", "v2_seed20260709"))
    ap.add_argument("--cap", type=int, default=24576, help="budget cap for the recommendation")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.models))
    defaults = cfg.get("defaults", {})
    try:
        model = next(m for m in cfg["models"] if m.get("key") == args.model_key)
    except StopIteration:
        sys.exit(f"model key {args.model_key!r} not in {args.models}")

    instances = stratified_subset(load_instances(args.dataset), args.n)
    out_root = os.path.join(V2, "results", "pilot")
    t0 = time.time()
    counters = asyncio.run(run_model(
        model, defaults, instances, out_root,
        concurrency=int(model.get("concurrency", defaults.get("concurrency", 1))),
        cache_dir=os.path.join(V2, "results", "cache"),
    ))
    wall = time.time() - t0

    rows = []
    with open(os.path.join(out_root, "responses", f"{args.model_key}.jsonl")) as f:
        wanted = {i["id"] for i in instances}
        for line in f:
            r = json.loads(line)
            if r["instance_id"] in wanted:
                rows.append(r)

    def reasoning_tokens(r):
        d = (r.get("usage") or {}).get("completion_tokens_details") or {}
        return d.get("reasoning_tokens") or 0

    rt = sorted(reasoning_tokens(r) for r in rows)
    ct = sorted((r.get("usage") or {}).get("completion_tokens", 0) for r in rows)
    trunc = sum(1 for r in rows if r.get("truncated"))
    ansline = sum(1 for r in rows if _ANSWER.search(r.get("text") or ""))

    def pct(xs, q):
        return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else 0

    p95 = pct(ct, 0.95)
    rec = min(args.cap, math.ceil(1.25 * p95 / 1024) * 1024)
    report = {
        "model_key": args.model_key, "model_id": model["model_id"], "n": len(rows),
        "policy": {k: model.get(k, defaults.get(k)) for k in
                   ("temperature", "top_p", "top_k", "max_tokens", "num_ctx")},
        "truncated": trunc, "answer_line": ansline,
        "reasoning_tokens": {"p50": pct(rt, .5), "p90": pct(rt, .9), "p95": pct(rt, .95),
                             "max": rt[-1] if rt else 0},
        "completion_tokens": {"p50": pct(ct, .5), "p90": pct(ct, .9), "p95": pct(ct, .95),
                              "max": ct[-1] if ct else 0},
        "wall_s": round(wall, 1), "counters": counters,
        "recommended_max_tokens": rec,
        "verdict": ("EXCLUDE (ruminator)" if trunc > len(rows) * 0.34 else
                    "OK" if ansline >= len(rows) * 0.9 else "REVIEW (answer-line rate low)"),
    }
    os.makedirs(os.path.join(out_root, "reports"), exist_ok=True)
    with open(os.path.join(out_root, "reports", f"{args.model_key}.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
