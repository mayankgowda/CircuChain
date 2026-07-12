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
import subprocess
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
                    out_dir: str, concurrency: int = 1, progress=print,
                    cache_dir: str | None = None) -> Dict[str, int]:
    """Run one model over the instance plan. Returns counters."""
    cfg = {**defaults, **model_cfg}
    # Loaded-ness is asserted ONCE below. The per-request assert reads /api/v0/models state,
    # which flaps to "not-loaded" under parallel generation and killed real requests.
    cfg["require_loaded"] = False
    # Dedicated serving identifier: GUI activity and JIT loading churn instances under the
    # bare model id (rogue 8192/1h instances, orphaned `id:2` suffixes). A custom identifier
    # is untouchable by both. `load_id` stays the real model id for lms load commands.
    load_id = cfg["model_id"]
    if cfg.get("serve_id"):
        cfg = {**cfg, "model_id": cfg["serve_id"]}
    provider = build_provider(cfg)
    model_key = cfg.get("key", load_id)

    gp = GenParams(
        temperature=float(cfg.get("temperature", 0.0)),
        seed=int(cfg.get("seed", 20260709)),
        max_tokens=int(cfg.get("max_tokens", 8192)),
        num_ctx=int(cfg.get("num_ctx", 8192)),
        think=cfg.get("think"),
        top_p=(float(cfg["top_p"]) if cfg.get("top_p") is not None else None),
        top_k=(int(cfg["top_k"]) if cfg.get("top_k") is not None else None),
    )

    # Ensure the serving instance exists before issuing the plan. Instances get evicted while
    # queued behind another column (observed: a sequential C2 pair died at handoff because the
    # second model was flushed hours earlier), so a column START must load, not just assert.
    if hasattr(provider, "assert_loaded"):
        try:
            provider.assert_loaded(gp.num_ctx)
        except Exception:  # noqa: BLE001
            serve = cfg["model_id"]
            progress(f"[{model_key}] not loaded at column start — loading {load_id} as {serve}")
            load_cmd = ["lms", "load", load_id, "--context-length", str(gp.num_ctx),
                        "--gpu", "max", "--ttl", "86400", "-y"]
            if serve != load_id:
                load_cmd += ["--identifier", serve]
            subprocess.run(load_cmd, capture_output=True, timeout=300)
            provider.assert_loaded(gp.num_ctx)     # still fails fast if the load didn't stick

    cache = CompletionCache(cache_dir or os.path.join(out_dir, "cache"))
    responses_path = os.path.join(out_dir, "responses", f"{model_key}.jsonl")
    os.makedirs(os.path.dirname(responses_path), exist_ok=True)

    done = _done_ids(responses_path)
    todo = [inst for inst in instances if inst["id"] not in done]
    counters = {"planned": len(instances), "resumed": len(done), "run": 0, "cache_hits": 0}
    progress(f"[{model_key}] plan={len(instances)} done={len(done)} todo={len(todo)} "
             f"concurrency={concurrency}")

    fingerprint = provider.fingerprint()      # once — not one HTTP GET per instance
    is_local = cfg.get("backend", "lmstudio") == "lmstudio"
    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    reload_lock = asyncio.Lock()
    health = {"consecutive_failures": 0}

    failures_path = os.path.join(out_dir, "responses", f"{model_key}.failures.jsonl")

    async def _reload_model() -> None:
        """LM Studio evicts models under GUI/memory pressure, JIT + CLI loads race to mint
        SUFFIXED instances (`id:2`), wedged engines emit "Compute error" INTERMITTENTLY, and
        `lms` CLI calls can HANG against a busy daemon (a hung reload once held the lock while
        313 requests burned). Hence: hard subprocess timeouts, captured output, and a body that
        can never raise — a failed reload is logged and retried at the next threshold."""
        async def _run(*cmd: str) -> str:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
                return (out or b"").decode(errors="ignore")[-300:]
            except asyncio.TimeoutError:
                proc.kill()
                return f"TIMEOUT after 120s: {' '.join(cmd)}"

        serve = cfg["model_id"]
        try:
            progress(f"[{model_key}] model unhealthy — clean reload of {load_id} as {serve}")
            out1 = await _run("lms", "unload", serve)
            await asyncio.sleep(1)
            load_cmd = ["lms", "load", load_id, "--context-length", str(gp.num_ctx),
                        "--gpu", "max", "--ttl", "86400", "-y"]
            if serve != load_id:
                load_cmd += ["--identifier", serve]
            out2 = await _run(*load_cmd)
            progress(f"[{model_key}] reload done: {out2.strip().splitlines()[-1] if out2.strip() else out1.strip()[-80:]}")
        except Exception as e:  # noqa: BLE001
            progress(f"[{model_key}] reload attempt failed (will retry at next threshold): {e}")
        finally:
            health["last_reload_at"] = asyncio.get_event_loop().time()

    async def one(inst: dict) -> None:
        key = cache_key(model_key, fingerprint, SYSTEM_PROMPT, inst["prompt"], gp)
        comp = cache.get(model_key, key)
        if comp is None:
            last_err = None
            for attempt in range(4):          # transient-flake armor for multi-day sweeps
                try:
                    async with sem:
                        # circuit breaker: checked at EXECUTION time (inside the semaphore),
                        # not at gather-scheduling time when counters are still zero
                        if counters.get("failed", 0) > max(20, 0.3 * len(instances)):
                            raise RuntimeError(
                                f"[{model_key}] aborting: failure rate exceeded 30% of plan")
                        comp = await provider.generate(SYSTEM_PROMPT, inst["prompt"], gp)
                    health["consecutive_failures"] = 0
                    break
                except RuntimeError as e:
                    if "failure rate exceeded" in str(e):
                        raise
                    last_err = e
                    health["consecutive_failures"] += 1
                    health["since_reload"] = health.get("since_reload", 0) + 1
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    health["consecutive_failures"] += 1
                    health["since_reload"] = health.get("since_reload", 0) + 1
                if comp is None:
                    # LOCAL only: reload the evicted/wedged instance. API failures (429/5xx)
                    # are handled by the backoff below — `lms load` would be nonsensical.
                    if is_local:
                        now = asyncio.get_event_loop().time()
                        due = (health["consecutive_failures"] >= 4
                               or health.get("since_reload", 0) >= 10)
                        cooled = now - health.get("last_reload_at", 0) > 60
                        if due and cooled and not reload_lock.locked():
                            async with reload_lock:
                                if (health["consecutive_failures"] >= 4
                                        or health.get("since_reload", 0) >= 10):
                                    await _reload_model()
                                    health["consecutive_failures"] = 0
                                    health["since_reload"] = 0
                    await asyncio.sleep(2 * 3 ** attempt)
            if comp is None:
                # record and skip — the id stays out of responses, so resume retries it later
                async with write_lock:
                    with open(failures_path, "a") as f:
                        f.write(json.dumps({"instance_id": inst["id"],
                                            "error": str(last_err)[:500]}) + "\n")
                counters["failed"] = counters.get("failed", 0) + 1
                progress(f"[{model_key}] FAILED {inst['id']}: {str(last_err)[:160]}")
                return
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

    # Outer convergence passes: eviction waves (GUI activity, download indexing, memory
    # pressure) can outpace per-request reloads and drain a plan into retryable failures.
    # Re-sweep the failed remainder until done or a pass makes no progress (max 6 passes).
    remaining = todo
    for sweep_pass in range(6):
        if not remaining:
            break
        if sweep_pass > 0:
            progress(f"[{model_key}] pass {sweep_pass + 1}: retrying {len(remaining)} "
                     f"failed/incomplete instances after 120s settle")
            await asyncio.sleep(120)
            await _reload_model()
        before = _done_ids(responses_path)
        counters["failed"] = 0
        health["consecutive_failures"] = 0
        health["since_reload"] = 0
        try:
            await asyncio.gather(*(one(i) for i in remaining))
        except RuntimeError as e:
            progress(f"[{model_key}] pass aborted: {e}")
        after = _done_ids(responses_path)
        remaining = [i for i in remaining if i["id"] not in after]
        if len(after) == len(before) and remaining:
            progress(f"[{model_key}] no progress this pass ({len(remaining)} left) — giving up; "
                     f"re-run to resume")
            break
    return counters


def run_panel(models_cfg: dict, dataset_dir: str, out_dir: str, progress=print) -> dict:
    """Run every enabled model in the config over the dataset. Synchronous entry point."""
    defaults = models_cfg.get("defaults", {})
    instances = load_instances(dataset_dir)
    results = {}
    for m in models_cfg.get("models", []):
        if not m.get("enabled", True):
            continue
        conc = int(m.get("concurrency", defaults.get("concurrency", 1)))
        results[m.get("key", m["model_id"])] = asyncio.run(
            run_model(m, defaults, instances, out_dir, concurrency=conc, progress=progress))
    return results
