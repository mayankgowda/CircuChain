"""Runner (build step 10): model x instance -> cached completions, resumable.

- Append-only JSONL per model in <out>/responses/{model_key}.jsonl; a killed run resumes by
  diffing completed instance_ids against the plan and only issuing the remainder.
- Content-addressed cache under <out>/cache/ (see cache.py) — a cache hit skips inference.
- The LM Studio provider asserts the model is LOADED (constrained context) before the first
  call and fails fast with the exact `lms load` command instead of OOMing mid-sweep.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List

from .cache import CompletionCache, cache_key
from .providers import build_provider
from .providers.base import GenParams

SYSTEM_PROMPT = (
    "You are a careful electrical engineering assistant. Solve DC circuit problems exactly as "
    "specified: follow the stated sign and reference conventions and the required method, and "
    "end with the mandatory ANSWER line in the requested format."
)


def load_instances(dataset_dir: str) -> List[dict]:
    with open(os.path.join(dataset_dir, "instances.jsonl")) as f:
        return [json.loads(line) for line in f]


def _done_ids(responses_path: str) -> set:
    done = set()
    if os.path.exists(responses_path):
        with open(responses_path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["instance_id"])
                except Exception:  # noqa: BLE001
                    continue
    return done


async def run_model(model_cfg: dict, defaults: dict, instances: List[dict],
                    out_dir: str, concurrency: int = 1, progress=print) -> Dict[str, int]:
    """Run one model over the instance plan. Returns counters."""
    cfg = {**defaults, **model_cfg}
    provider = build_provider(cfg)
    model_key = cfg.get("key", cfg["model_id"])

    gp = GenParams(
        temperature=float(cfg.get("temperature", 0.0)),
        seed=int(cfg.get("seed", 20260709)),
        max_tokens=int(cfg.get("max_tokens", 8192)),
        num_ctx=int(cfg.get("num_ctx", 8192)),
        think=cfg.get("think"),
    )

    # fail fast on a not-loaded model (the 262k-ctx JIT trap) before issuing the plan
    if hasattr(provider, "assert_loaded"):
        provider.assert_loaded(gp.num_ctx)

    cache = CompletionCache(os.path.join(out_dir, "cache"))
    responses_path = os.path.join(out_dir, "responses", f"{model_key}.jsonl")
    os.makedirs(os.path.dirname(responses_path), exist_ok=True)

    done = _done_ids(responses_path)
    todo = [inst for inst in instances if inst["id"] not in done]
    counters = {"planned": len(instances), "resumed": len(done), "run": 0, "cache_hits": 0}
    progress(f"[{model_key}] plan={len(instances)} done={len(done)} todo={len(todo)}")

    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()

    async def one(inst: dict) -> None:
        key = cache_key(model_key, provider.fingerprint(), SYSTEM_PROMPT, inst["prompt"], gp)
        comp = cache.get(model_key, key)
        if comp is None:
            async with sem:
                comp = await provider.generate(SYSTEM_PROMPT, inst["prompt"], gp)
            cache.put(model_key, key, comp)
            counters["run"] += 1
        else:
            counters["cache_hits"] += 1
        row = {
            "instance_id": inst["id"], "physics_id": inst["physics_id"],
            "model": model_key, "cache_key": key,
            "contract": inst["contract"], "topology": inst["topology"],
            "regime": inst["regime"],
            "text": comp.text, "think_len": len(comp.think), "truncated": comp.truncated,
            "usage": comp.usage, "provenance": comp.provenance,
        }
        async with write_lock:
            with open(responses_path, "a") as f:
                f.write(json.dumps(row) + "\n")
        n = counters["run"] + counters["cache_hits"]
        if n % 10 == 0 or n == len(todo):
            progress(f"[{model_key}] {n}/{len(todo)} (cache_hits={counters['cache_hits']})")

    await asyncio.gather(*(one(i) for i in todo))
    return counters


def run_panel(models_cfg: dict, dataset_dir: str, out_dir: str, progress=print) -> dict:
    """Run every enabled model in the config over the dataset. Synchronous entry point."""
    defaults = models_cfg.get("defaults", {})
    instances = load_instances(dataset_dir)
    results = {}
    for m in models_cfg.get("models", []):
        if not m.get("enabled", True):
            continue
        results[m.get("key", m["model_id"])] = asyncio.run(
            run_model(m, defaults, instances, out_dir, progress=progress))
    return results
