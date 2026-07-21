"""Fire-and-forget GPT-5 runs via OpenAI's Batch API (50% off, <=24h, usually hours).

This is the ONLY way to run GPT-5 with everything closed: our normal runner is a live
local process (dies when the machine sleeps / Claude closes), whereas a batch lives on
OpenAI's side. OpenRouter has no batch API, so this talks to OpenAI directly and needs
OPENAI_API_KEY in v2/.env (never printed, never committed).

  submit : build batch JSONL from a contour dataset, upload, create the batch, save state
  status : print the batch's current state + request counts
  fetch  : download completed output, write results/<domain>/responses/<key>.jsonl in the
           SAME schema the grader expects (so `circuchain grade` just works), + failures

Typical use:
  .venv/bin/python v2/scripts/batch_openai.py submit         # now; prints a batch id
  # ... close everything ...
  .venv/bin/python v2/scripts/batch_openai.py fetch          # tomorrow (or rerun status)

GPT-5 params: reasoning_effort=low (the v2-proven config: minimal answers wrong, default
truncates), max_completion_tokens=16384 (generous — contour derivations run long and batch
is half price anyway). No temperature/top_p/top_k: GPT-5 reasoning models reject them.
"""
import argparse
import json
import os
import sys

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
API = "https://api.openai.com/v1"


def _key() -> str:
    # mirror cli._load_dotenv so this runs standalone (Claude closed)
    path = os.path.join(V2, ".env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        sys.exit("OPENAI_API_KEY not found. Add it to v2/.env as:  OPENAI_API_KEY=sk-...\n"
                 "(OpenRouter cannot batch; GPT-5 batch requires a native OpenAI key.)")
    return k


def _client(key: str) -> httpx.Client:
    return httpx.Client(base_url=API, headers={"Authorization": f"Bearer {key}"},
                        timeout=httpx.Timeout(connect=15, read=120, write=120, pool=60))


def _statepath(out_dir: str) -> str:
    return os.path.join(out_dir, "batch", "gpt5_batch_state.json")


def cmd_submit(a) -> None:
    key = _key()
    ds = os.path.join(V2, a.dataset)
    man = json.load(open(os.path.join(ds, "manifest.json")))
    sys_prompt = man.get("system_prompt") or ""
    insts = [json.loads(l) for l in open(os.path.join(ds, "instances.jsonl"))]
    out_dir = os.path.join(V2, a.out)
    os.makedirs(os.path.join(out_dir, "batch"), exist_ok=True)

    # already-done ids (resume: never re-submit what the live runner already produced)
    done = set()
    rp = os.path.join(out_dir, "responses", f"{a.key}.jsonl")
    if os.path.exists(rp):
        done = {json.loads(l)["instance_id"] for l in open(rp)}
    todo = [i for i in insts if i["id"] not in done]
    if a.limit:
        todo = todo[:a.limit]
    if not todo:
        print(f"nothing to submit — all {len(insts)} instances already in {rp}")
        return

    jsonl_path = os.path.join(out_dir, "batch", "gpt5_input.jsonl")
    with open(jsonl_path, "w") as f:
        for i in todo:
            body = {
                "model": a.model,
                "messages": [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": i["prompt"]}],
                "reasoning_effort": a.effort,
                "max_completion_tokens": a.max_tokens,
            }
            f.write(json.dumps({"custom_id": i["id"], "method": "POST",
                                "url": "/v1/chat/completions", "body": body}) + "\n")
    size_mb = os.path.getsize(jsonl_path) / 1e6
    print(f"built {len(todo)} requests ({size_mb:.1f} MB) -> {jsonl_path}")

    with _client(key) as c:
        with open(jsonl_path, "rb") as fh:
            up = c.post("/files", data={"purpose": "batch"},
                        files={"file": ("gpt5_input.jsonl", fh, "application/jsonl")})
        up.raise_for_status()
        file_id = up.json()["id"]
        print(f"uploaded input file: {file_id}")
        br = c.post("/batches", json={"input_file_id": file_id,
                                      "endpoint": "/v1/chat/completions",
                                      "completion_window": "24h",
                                      "metadata": {"project": "circuchain-v3-contour",
                                                   "column": a.key}})
        br.raise_for_status()
        batch = br.json()

    state = {"batch_id": batch["id"], "input_file_id": file_id, "key": a.key,
             "out": a.out, "dataset": a.dataset, "model": a.model, "effort": a.effort,
             "n_submitted": len(todo)}
    json.dump(state, open(_statepath(out_dir), "w"), indent=2)
    print(f"\nBATCH CREATED: {batch['id']}  status={batch['status']}")
    print(f"state saved -> {_statepath(out_dir)}")
    print(f"\nEstimated cost: ~{len(todo)} rows x ~7-11c/row x 0.5 (batch) "
          f"= roughly ${len(todo)*0.09*0.5:.0f} (GPT-5@{a.effort}, actual billed per usage).")
    print("Come back later:  .venv/bin/python v2/scripts/batch_openai.py status   (then fetch)")


def _load_state(a) -> dict:
    out_dir = os.path.join(V2, a.out)
    sp = _statepath(out_dir)
    if not os.path.exists(sp):
        sys.exit(f"no batch state at {sp} — run `submit` first.")
    return json.load(open(sp))


def cmd_status(a) -> None:
    key = _key()
    st = _load_state(a)
    with _client(key) as c:
        r = c.get(f"/batches/{st['batch_id']}")
        r.raise_for_status()
        b = r.json()
    rc = b.get("request_counts", {})
    print(f"batch {st['batch_id']}")
    print(f"  status: {b['status']}")
    print(f"  requests: total={rc.get('total')} completed={rc.get('completed')} "
          f"failed={rc.get('failed')}")
    if b.get("output_file_id"):
        print(f"  output_file_id: {b['output_file_id']}  -> ready to `fetch`")
    if b.get("error_file_id"):
        print(f"  error_file_id: {b['error_file_id']}")


def cmd_fetch(a) -> None:
    key = _key()
    st = _load_state(a)
    out_dir = os.path.join(V2, a.out)
    ds = os.path.join(V2, st["dataset"])
    insts = {json.loads(l)["id"]: json.loads(l)
             for l in open(os.path.join(ds, "instances.jsonl"))}
    with _client(key) as c:
        b = c.get(f"/batches/{st['batch_id']}").json()
        if b["status"] != "completed":
            print(f"batch status = {b['status']} (not completed yet). Request counts: "
                  f"{b.get('request_counts')}. Try again later.")
            if not b.get("output_file_id"):
                return
        out = c.get(f"/files/{b['output_file_id']}/content")
        out.raise_for_status()
        lines = out.text.strip().splitlines()

    os.makedirs(os.path.join(out_dir, "responses"), exist_ok=True)
    rp = os.path.join(out_dir, "responses", f"{st['key']}.jsonl")
    fp = os.path.join(out_dir, "responses", f"{st['key']}.failures.jsonl")
    existing = set()
    if os.path.exists(rp):
        existing = {json.loads(l)["instance_id"] for l in open(rp)}

    n_ok = n_fail = 0
    with open(rp, "a") as fout, open(fp, "a") as ferr:
        for line in lines:
            rec = json.loads(line)
            cid = rec.get("custom_id")
            if cid in existing:
                continue
            resp = rec.get("response") or {}
            if rec.get("error") or resp.get("status_code", 200) >= 400:
                ferr.write(json.dumps({"instance_id": cid,
                                       "error": str(rec.get("error") or resp)[:500]}) + "\n")
                n_fail += 1
                continue
            body = resp.get("body", {})
            choice = (body.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            usage = body.get("usage", {})
            rtoks = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
            inst = insts.get(cid, {})
            row = {
                "instance_id": cid, "physics_id": inst.get("physics_id"),
                "model": st["key"], "cache_key": f"batch:{st['batch_id']}",
                "contract": inst.get("contract"), "topology": inst.get("topology"),
                "regime": inst.get("regime"),
                "text": text, "think_len": rtoks,
                "truncated": choice.get("finish_reason") == "length",
                "usage": usage,
                "provenance": {"model_id": body.get("model", st["model"]),
                               "backend": "openai_batch", "effort": st["effort"]},
            }
            fout.write(json.dumps(row) + "\n")
            n_ok += 1
    print(f"wrote {n_ok} results -> {rp}" + (f"  ({n_fail} failures -> {fp})" if n_fail else ""))
    print(f"now grade:  .venv/bin/python -m circuchain.cli grade "
          f"--responses {st['out']}/responses --dataset {st['dataset']} "
          f"--out {st['out']}/graded")


def main() -> None:
    ap = argparse.ArgumentParser(description="GPT-5 via OpenAI Batch API (50% off).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "status", "fetch"):
        p = sub.add_parser(name)
        p.add_argument("--key", default="gpt5-api", help="response-column key (file name)")
        p.add_argument("--out", default="results/contour", help="output root")
        p.add_argument("--dataset", default="results/contour/datasets/v3contour_seed20260720")
        if name == "submit":
            p.add_argument("--model", default="gpt-5")
            p.add_argument("--effort", default="low", choices=["minimal", "low", "medium", "high"])
            p.add_argument("--max-tokens", type=int, default=16384, dest="max_tokens")
            p.add_argument("--limit", type=int, default=0, help="cap N (0 = all)")
    a = ap.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()
