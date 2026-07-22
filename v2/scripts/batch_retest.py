"""k=5 test-retest of the hard-tier headline number (gemma cw-cell) via Together Batch.

v2's rigor pattern applied to the new headline: resample the SAME instances k times under
the SAME decoding policy and report the across-rep mean/SD of the reversion rate (claim =
"the rate is stable", not "items are deterministic"). Rep 1 = the existing hard-batch rows;
this submits reps 2..K as one batch (custom_id "<instance_id>::rep<k>").

  submit : build + upload + create the batch
  fetch  : write results/contour_hard/retest/rep<k>.jsonl (grader-consumable rows)
  analyze: per-rep reversion rate on magnitude-correct diagnostic vars -> mean/SD table

Cost: ~750 rows x ~12k tok x Together gemma serverless x 0.5 batch discount ~= $2-3.
"""
import argparse
import json
import os
import sys

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
API = "https://api.together.ai/v1"
MODEL_ID = "google/gemma-4-31B-it"
KEY_NAME = "gemma4-31b-api"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "max_tokens": 16384}
K = 5


def _key() -> str:
    path = os.path.join(V2, ".env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    k = os.environ.get("TOGETHER_API_KEY")
    if not k:
        sys.exit("TOGETHER_API_KEY not found in v2/.env")
    return k


def _client(key):
    return httpx.Client(base_url=API, headers={"Authorization": f"Bearer {key}"},
                        timeout=httpx.Timeout(connect=15, read=180, write=180, pool=60))


def _paths(a):
    out = os.path.join(V2, a.out)
    return out, os.path.join(out, "retest"), os.path.join(out, "retest", "state.json")


def cmd_submit(a):
    key = _key()
    ds = os.path.join(V2, a.dataset)
    man = json.load(open(os.path.join(ds, "manifest.json")))
    sysp = man["system_prompt"]
    cw = [json.loads(l) for l in open(os.path.join(ds, "instances.jsonl"))
          if json.loads(l)["id"].rsplit("-", 2)[-2] == "cw"]
    out, rdir, sp = _paths(a)
    os.makedirs(rdir, exist_ok=True)
    jp = os.path.join(rdir, "input.jsonl")
    with open(jp, "w") as f:
        for rep in range(2, K + 1):
            for i in cw:
                body = {"model": MODEL_ID,
                        "messages": [{"role": "system", "content": sysp},
                                     {"role": "user", "content": i["prompt"]}], **SAMPLING}
                f.write(json.dumps({"custom_id": f"{i['id']}::rep{rep}", "body": body}) + "\n")
    n = len(cw) * (K - 1)
    with _client(key) as c:
        with open(jp, "rb") as fh:
            up = c.post("/files/upload", data={"purpose": "batch-api",
                                               "file_name": "retest_input.jsonl"},
                        files={"file": ("retest_input.jsonl", fh, "application/jsonl")})
        up.raise_for_status()
        fid = up.json()["id"]
        br = c.post("/batches", json={"input_file_id": fid, "endpoint": "/v1/chat/completions"})
        br.raise_for_status()
        b = br.json()
        bid = b.get("id") or (b.get("data") or {}).get("id")
        if not bid:
            lst = c.get("/batches").json()
            lst = lst if isinstance(lst, list) else lst.get("data", [])
            bid = next((x["id"] for x in lst if x.get("input_file_id") == fid), None)
    json.dump({"batch_id": bid, "input_file_id": fid, "n": n}, open(sp, "w"), indent=2)
    print(f"retest batch {bid}: {n} requests ({len(cw)} cw instances x reps 2..{K})")


def cmd_fetch(a):
    key = _key()
    out, rdir, sp = _paths(a)
    st = json.load(open(sp))
    with _client(key) as c:
        b = c.get(f"/batches/{st['batch_id']}").json()
        if b.get("status") != "COMPLETED" or not b.get("output_file_id"):
            print(f"status={b.get('status')} — not ready")
            return
        content = c.get(f"/files/{b['output_file_id']}/content")
        content.raise_for_status()
    per_rep = {}
    for line in content.text.strip().splitlines():
        rec = json.loads(line)
        cid = rec.get("custom_id", "")
        if "::rep" not in cid:
            continue
        iid, rep = cid.split("::rep")
        resp = rec.get("response") or {}
        body = resp.get("body") or resp
        choice = (body.get("choices") or [{}])[0] if isinstance(body, dict) else {}
        text = (choice.get("message") or {}).get("content") or ""
        per_rep.setdefault(rep, []).append(
            {"instance_id": iid, "model": f"{KEY_NAME}-rep{rep}", "text": text,
             "truncated": choice.get("finish_reason") == "length",
             "usage": body.get("usage", {}) if isinstance(body, dict) else {}})
    for rep, rows in sorted(per_rep.items()):
        p = os.path.join(rdir, f"rep{rep}.jsonl")
        with open(p, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"rep{rep}: {len(rows)} rows -> {p}")


def cmd_analyze(a):
    from circuchain.grade.extract import extract
    from circuchain.grade.compliance import grade_variable, V_PASS, V_SIGN_CONVENTION
    out, rdir, _ = _paths(a)
    ds = os.path.join(V2, a.dataset)
    inst = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ds, "instances.jsonl"))}
    # rep1 = the original hard-batch response file, filtered to cw
    reps = {}
    orig = os.path.join(out, "responses", f"{KEY_NAME}.jsonl")
    reps["1"] = [json.loads(l) for l in open(orig)
                 if json.loads(l)["instance_id"].rsplit("-", 2)[-2] == "cw"]
    for f in sorted(os.listdir(rdir)):
        if f.startswith("rep") and f.endswith(".jsonl"):
            reps[f[3:-6]] = [json.loads(l) for l in open(os.path.join(rdir, f))]
    rates = {}
    for rep, rows in sorted(reps.items()):
        comply = revert = 0
        for r in rows:
            i = inst.get(r["instance_id"])
            if not i or not r.get("text"):
                continue
            wanted = tuple(i["expected_under_contract"].keys())
            pred, _ = extract(r["text"], wanted)
            for var in wanted:
                if not i["diagnostic_vars"].get(var):
                    continue
                lab = grade_variable(pred.get(var), i["expected_under_contract"][var],
                                     i["expected_under_default"][var])
                if lab == V_PASS:
                    comply += 1
                elif lab == V_SIGN_CONVENTION:
                    revert += 1
        t = comply + revert
        rates[rep] = {"revert": revert, "n": t, "rate": revert / t if t else None}
        print(f"rep{rep}: revert {revert}/{t} = {revert/t*100 if t else 0:.1f}%")
    vals = [v["rate"] for v in rates.values() if v["rate"] is not None]
    mean = sum(vals) / len(vals)
    sd = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 1 else 0
    print(f"\nk={len(vals)} retest: mean {mean*100:.1f}%  SD {sd*100:.1f}pp")
    json.dump({"k": len(vals), "per_rep": rates, "mean": mean, "sd": sd},
              open(os.path.join(out, "tables", "retest_gemma_hard_cw.json"), "w"), indent=2)
    print(f"wrote {os.path.join(a.out, 'tables', 'retest_gemma_hard_cw.json')}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("submit", "fetch", "analyze"):
        p = sub.add_parser(n)
        p.add_argument("--out", default="results/contour_hard")
        p.add_argument("--dataset", default="results/contour_hard/datasets/v3contourhard_seed20260721")
    a = ap.parse_args()
    {"submit": cmd_submit, "fetch": cmd_fetch, "analyze": cmd_analyze}[a.cmd](a)


if __name__ == "__main__":
    main()
