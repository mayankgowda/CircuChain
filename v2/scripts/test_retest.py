"""V2-3 test-retest reliability: k independent samples per instance (cache bypassed).

The panel's objection: single-sample decoding at temp 0.6 (with MLX ignoring seed)
means no per-item reliability estimate — is a "convention-blind" item stably blind, or
a coin flip? This script draws k fresh samples per instance from the SAME decoding
policy for gemma-4-31b (the most competent model, via Together) on the pilot subset's
dflt + ccw cells, grades each sample deterministically, and reports:

  * per-sample rates (magnitude-correct, sign-compliant|mag, conv-blind|mag)
    -> between-sample SD  (how much does the HEADLINE move under resampling?)
  * per-item stability   (fraction of items unanimous across k samples)

Writes results/tables/test_retest_raw.jsonl (every sample) + test_retest.json.
Usage:  .venv/bin/python v2/scripts/test_retest.py [k]
"""
import asyncio
import json
import os
import sys

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, V2)

from circuchain.grade.extract import extract          # noqa: E402
from circuchain.grade.compliance import grade_subtask  # noqa: E402

DATASET = os.path.join(V2, "results", "datasets", "v2_pilot248", "instances.jsonl")
RAW_OUT = os.path.join(V2, "results", "tables", "test_retest_raw.jsonl")
SUM_OUT = os.path.join(V2, "results", "tables", "test_retest.json")

MODEL = "google/gemma-4-31B-it"
BASE = "https://api.together.xyz/v1"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
CONC = 12
GEN = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "max_tokens": 16384}


def _load_env() -> str:
    for line in open(os.path.join(V2, ".env")):
        line = line.strip()
        if line.startswith("TOGETHER_API_KEY="):
            return line.partition("=")[2].strip().strip('"').strip("'")
    raise SystemExit("TOGETHER_API_KEY not in v2/.env")


async def one(client: httpx.AsyncClient, sem: asyncio.Semaphore, key: str,
              inst: dict, sample_idx: int, out_f) -> dict | None:
    payload = {"model": MODEL, "stream": False,
               "messages": [{"role": "user", "content": inst["prompt"]}], **GEN}
    async with sem:
        for attempt in range(4):
            try:
                r = await client.post(f"{BASE}/chat/completions", json=payload,
                                      headers={"Authorization": f"Bearer {key}"})
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
                text = r.json()["choices"][0]["message"]["content"] or ""
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    print(f"  FAIL {inst['id']} s{sample_idx}: {e}")
                    return None
                await asyncio.sleep(3 * (attempt + 1))
    wanted = tuple(inst["expected_under_contract"].keys())
    pred, mode = extract(text, wanted)
    g = grade_subtask(pred, inst["expected_under_contract"], inst["expected_under_default"])
    row = {"instance_id": inst["id"], "sample": sample_idx,
           "cell": inst["id"].rsplit("-", 2)[-2],
           "dichotomy": g.label, "magnitude_correct": g.magnitude_correct,
           "sign_compliant": g.sign_compliant, "var_labels": g.var_labels,
           "extract_mode": mode}
    out_f.write(json.dumps(row) + "\n")
    out_f.flush()
    return row


async def main() -> None:
    key = _load_env()
    insts = [json.loads(l) for l in open(DATASET)]
    subset = [r for r in insts if r["id"].rsplit("-", 2)[-2] in ("dflt", "ccw")]
    print(f"test-retest: {len(subset)} instances x k={K} samples on {MODEL}")

    done = set()
    if os.path.exists(RAW_OUT):                      # resumable
        for l in open(RAW_OUT):
            r = json.loads(l)
            done.add((r["instance_id"], r["sample"]))

    sem = asyncio.Semaphore(CONC)
    timeout = httpx.Timeout(connect=15, read=600, write=60, pool=60)
    rows = []
    with open(RAW_OUT, "a") as out_f:
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [one(client, sem, key, inst, s, out_f)
                     for inst in subset for s in range(K)
                     if (inst["id"], s) not in done]
            print(f"  {len(tasks)} calls to make ({len(done)} cached)")
            rows = [r for r in await asyncio.gather(*tasks) if r]

    # ---- summarize from the FULL raw file (including prior runs) ----
    allrows = [json.loads(l) for l in open(RAW_OUT)]
    by_item: dict = {}
    for r in allrows:
        by_item.setdefault((r["instance_id"], r["cell"]), {})[r["sample"]] = r

    def rates(sample_idx: int) -> dict:
        rs = [v[sample_idx] for v in by_item.values() if sample_idx in v]
        ccw = [r for r in rs if r["cell"] == "ccw"]
        mag = [r for r in ccw if r["magnitude_correct"]]
        blind = [r for r in mag if not r["sign_compliant"]]
        return {"n": len(rs),
                "mag_correct_ccw": len(mag) / len(ccw) if ccw else None,
                "conv_blind_given_mag_ccw": len(blind) / len(mag) if mag else None}

    per_sample = [rates(s) for s in range(K)]
    import statistics as st
    blind_rates = [p["conv_blind_given_mag_ccw"] for p in per_sample
                   if p["conv_blind_given_mag_ccw"] is not None]
    unanimity = 0
    complete = 0
    for v in by_item.values():
        if len(v) == K:
            complete += 1
            outcomes = {(r["magnitude_correct"], r["sign_compliant"]) for r in v.values()}
            unanimity += (len(outcomes) == 1)

    summary = {
        "model": MODEL, "k": K, "n_items": len(by_item),
        "per_sample_rates": per_sample,
        "conv_blind_ccw_mean": st.mean(blind_rates) if blind_rates else None,
        "conv_blind_ccw_sd": st.stdev(blind_rates) if len(blind_rates) > 1 else None,
        "items_with_all_k": complete,
        "item_unanimity_rate": unanimity / complete if complete else None,
    }
    with open(SUM_OUT, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
