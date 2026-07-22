"""Fire-and-forget gemma-4-31b + gpt-oss-120b via Together's Batch API (50% off, <=24h).

Together's two contour anchors are serverless, so batch gets the 50% discount and runs with
everything closed. Contract differs slightly from OpenAI's: upload at /v1/files/upload with
purpose=batch-api, JSONL lines are {custom_id, body} (no method/url), create at /v1/batches,
status values are UPPERCASE. One batch PER MODEL so each maps to a clean responses/<key>.jsonl.

Decoding policy MATCHES the live/smoke runs exactly (temp 0.6, top_p 0.95, top_k 20,
max_tokens 16384) so batched rows are interchangeable with any live rows. Resume-safe: skips
ids already in the response file (e.g. gemma's 100 smoke rows -> batch submits the other 900).

  submit : build + upload + create one batch per model, save state
  status : print each batch's state + request counts
  fetch  : download completed output into responses/<key>.jsonl (grader-ready) + failures

Needs TOGETHER_API_KEY in v2/.env (already present for the live runs).
"""
import argparse
import json
import os
import sys

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
API = "https://api.together.ai/v1"

# The two Together serverless anchors, with params identical to configs/models_contour.yaml.
MODELS = [
    {"key": "gemma4-31b-api", "model_id": "google/gemma-4-31B-it", "max_tokens": 16384},
    {"key": "gpt-oss-120b-api", "model_id": "openai/gpt-oss-120b", "max_tokens": 16384},
]
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}


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


def _client(key: str) -> httpx.Client:
    return httpx.Client(base_url=API, headers={"Authorization": f"Bearer {key}"},
                        timeout=httpx.Timeout(connect=15, read=120, write=120, pool=60))


def _statepath(out_dir: str) -> str:
    return os.path.join(out_dir, "batch", "together_batch_state.json")


def cmd_submit(a) -> None:
    key = _key()
    ds = os.path.join(V2, a.dataset)
    man = json.load(open(os.path.join(ds, "manifest.json")))
    sysp = man.get("system_prompt") or ""
    insts = [json.loads(l) for l in open(os.path.join(ds, "instances.jsonl"))]
    out_dir = os.path.join(V2, a.out)
    os.makedirs(os.path.join(out_dir, "batch"), exist_ok=True)

    state = {"out": a.out, "dataset": a.dataset, "batches": {}}
    with _client(key) as c:
        for m in MODELS:
            done = set()
            rp = os.path.join(out_dir, "responses", f"{m['key']}.jsonl")
            if os.path.exists(rp):
                done = {json.loads(l)["instance_id"] for l in open(rp)}
            todo = [i for i in insts if i["id"] not in done]
            if a.limit:
                todo = todo[:a.limit]
            if not todo:
                print(f"[{m['key']}] nothing to submit (all {len(insts)} already present)")
                continue

            jp = os.path.join(out_dir, "batch", f"together_input_{m['key']}.jsonl")
            with open(jp, "w") as f:
                for i in todo:
                    body = {"model": m["model_id"],
                            "messages": [{"role": "system", "content": sysp},
                                         {"role": "user", "content": i["prompt"]}],
                            "max_tokens": m["max_tokens"], **SAMPLING}
                    f.write(json.dumps({"custom_id": i["id"], "body": body}) + "\n")

            with open(jp, "rb") as fh:
                up = c.post("/files/upload",
                            data={"purpose": "batch-api",
                                  "file_name": os.path.basename(jp)},
                            files={"file": (os.path.basename(jp), fh, "application/jsonl")})
            up.raise_for_status()
            file_id = up.json()["id"]
            br = c.post("/batches", json={"input_file_id": file_id,
                                          "endpoint": "/v1/chat/completions"})
            br.raise_for_status()
            batch = br.json()
            # create-response shape varies; the durable join key is input_file_id, so if the
            # id isn't where we expect, resolve it by matching the batch list on input_file_id.
            bid = batch.get("id") or batch.get("batch_id") or (batch.get("data") or {}).get("id")
            if not bid:
                lst = c.get("/batches").json()
                lst = lst if isinstance(lst, list) else lst.get("data", [])
                match = next((b for b in lst if b.get("input_file_id") == file_id), None)
                bid = match.get("id") if match else None
            state["batches"][m["key"]] = {"batch_id": bid, "input_file_id": file_id,
                                          "model_id": m["model_id"], "n_submitted": len(todo)}
            print(f"[{m['key']}] batch {bid}  ({len(todo)} requests, "
                  f"status={batch.get('status')})")

    json.dump(state, open(_statepath(out_dir), "w"), indent=2)
    print(f"\nstate saved -> {_statepath(out_dir)}")
    print("Come back:  .venv/bin/python v2/scripts/batch_together.py status   (then fetch)")


def _load_state(a) -> dict:
    sp = _statepath(os.path.join(V2, a.out))
    if not os.path.exists(sp):
        sys.exit(f"no batch state at {sp} — run `submit` first.")
    return json.load(open(sp))


def cmd_status(a) -> None:
    key = _key()
    st = _load_state(a)
    with _client(key) as c:
        for mkey, b in st["batches"].items():
            r = c.get(f"/batches/{b['batch_id']}")
            if r.status_code != 200:
                print(f"[{mkey}] {b['batch_id']}: HTTP {r.status_code} {r.text[:150]}")
                continue
            d = r.json()
            rc = d.get("request_counts") or {}
            outf = d.get("output_file_id")
            print(f"[{mkey}] {b['batch_id']}: {d.get('status')}  "
                  f"counts={rc}  {'output READY' if outf else ''}")


def cmd_fetch(a) -> None:
    key = _key()
    st = _load_state(a)
    out_dir = os.path.join(V2, a.out)
    ds = os.path.join(V2, st["dataset"])
    insts = {json.loads(l)["id"]: json.loads(l)
             for l in open(os.path.join(ds, "instances.jsonl"))}
    with _client(key) as c:
        for mkey, b in st["batches"].items():
            d = c.get(f"/batches/{b['batch_id']}").json()
            outf = d.get("output_file_id")
            if d.get("status") != "COMPLETED" or not outf:
                print(f"[{mkey}] status={d.get('status')} counts={d.get('request_counts')} "
                      f"— not ready, try later")
                continue
            content = c.get(f"/files/{outf}/content")
            content.raise_for_status()
            os.makedirs(os.path.join(out_dir, "responses"), exist_ok=True)
            rp = os.path.join(out_dir, "responses", f"{mkey}.jsonl")
            fp = os.path.join(out_dir, "responses", f"{mkey}.failures.jsonl")
            existing = ({json.loads(l)["instance_id"] for l in open(rp)}
                        if os.path.exists(rp) else set())
            n_ok = n_fail = 0
            with open(rp, "a") as fout, open(fp, "a") as ferr:
                for line in content.text.strip().splitlines():
                    rec = json.loads(line)
                    cid = rec.get("custom_id")
                    if cid in existing:
                        continue
                    resp = rec.get("response") or {}
                    body = resp.get("body") or resp     # tolerate either nesting
                    choice = (body.get("choices") or [{}])[0] if isinstance(body, dict) else {}
                    text = (choice.get("message") or {}).get("content") or ""
                    if rec.get("error") or not text:
                        ferr.write(json.dumps({"instance_id": cid,
                                               "error": str(rec.get("error") or resp)[:500]}) + "\n")
                        n_fail += 1
                        continue
                    usage = body.get("usage", {}) if isinstance(body, dict) else {}
                    inst = insts.get(cid, {})
                    row = {"instance_id": cid, "physics_id": inst.get("physics_id"),
                           "model": mkey, "cache_key": f"batch:{b['batch_id']}",
                           "contract": inst.get("contract"), "topology": inst.get("topology"),
                           "regime": inst.get("regime"), "text": text,
                           "think_len": 0,
                           "truncated": choice.get("finish_reason") == "length",
                           "usage": usage,
                           "provenance": {"model_id": b["model_id"], "backend": "together_batch"}}
                    fout.write(json.dumps(row) + "\n")
                    n_ok += 1
            print(f"[{mkey}] wrote {n_ok} -> {rp}" + (f"  ({n_fail} failures)" if n_fail else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="gemma+gpt-oss via Together Batch API (50% off).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "status", "fetch"):
        p = sub.add_parser(name)
        p.add_argument("--out", default="results/contour")
        p.add_argument("--dataset", default="results/contour/datasets/v3contour_seed20260720")
        if name == "submit":
            p.add_argument("--limit", type=int, default=0, help="cap N per model (0 = all)")
    a = ap.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()
