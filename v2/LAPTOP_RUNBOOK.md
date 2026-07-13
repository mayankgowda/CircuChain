# CircuChain v2 — M1 Max (32 GB) run node

**You are a Claude Code instance on a MacBook Pro M1 Max, 32 GB.** Your job: run **one full
1000-instance model column** for the CircuChain v2 "Convention Blindness" benchmark and hand
the results back. The primary node (M5 Max, 128 GB) runs everything else and does all grading
and analysis — **you only generate raw model responses.** Do not analyze, do not grade, do not
"improve" the harness. Run one column to completion, verify it, ship it.

This works because both Macs run **Apple MLX at 8-bit**, so your column is the *same serving
stack* as an M5 column — no confound in the paper's causal contrasts. That homogeneity is the
whole point; the integrity checks below exist to guarantee it. If any check fails, **stop and
report** rather than working around it.

---

## 0. Ground rules (read first)

- **Never `git push` the dataset (`results/datasets/**`) or responses (`results/responses/**`).**
  The repo `github.com/mayankgowda/CircuChain` is **public**, and `instances.jsonl` carries a
  contamination **canary GUID**. Publishing it would poison the benchmark for future models.
  You will *regenerate* the dataset locally (never downloads, never uploads) and *AirDrop/scp*
  results back — see §5.
- **Do not change the decoding policy** (temp 0.6 / top_p 0.95 / top_k 20 / max_tokens 16384 /
  num_ctx 24576). These are fixed across the whole panel.
- **Use the MLX 8-bit build of each model. Not GGUF, not Q4, not 4-bit MLX.** Wrong quant = wrong
  serving stack = the column is unusable.
- Run **one** column at a time to completion. Partial columns are not useful.

## 1. Prerequisites

- **LM Studio** installed, with the CLI on PATH: `lms version` should work
  (if not: `~/.lmstudio/bin/lms bootstrap`, then reopen the shell). Start the server: `lms server start`.
- **uv** (`brew install uv`) for the Python env. ngspice is **not** needed on this node (no
  grading/verification here).

## 2. Get the code (dataset NOT included — you regenerate it in §4)

```bash
git clone https://github.com/mayankgowda/CircuChain.git
cd CircuChain
git checkout v2                      # ask the primary node to `git push origin v2` first if this fails
uv venv --python 3.12
uv pip install -e 'v2/[dev]'
```

## 3. Download the model (MLX 8-bit only)

Pick the ONE column you were assigned (default: `qwen3-14b-think`). Download its MLX 8-bit build
in the LM Studio GUI (search the model, choose the **MLX / 8-bit** quant), or via CLI:

```bash
lms get qwen/qwen3-14b        # then in the picker select the MLX 8-bit variant
# 8b column instead? -> qwen/qwen3-8b
```

Confirm what landed is MLX 8-bit: `lms ls | grep -i qwen3-14b` (engine must be MLX, quant 8-bit).

## 4. Regenerate the exact dataset (deterministic, canary-safe)

```bash
cd v2
../.venv/bin/circuchain generate --seed 20260709 --out results/datasets/v2_seed20260709
```

**Verify it is byte-identical to the primary node before running anything:**

```bash
# canary + counts
../.venv/bin/python -c "import json;m=json.load(open('results/datasets/v2_seed20260709/manifest.json'));print(m['seed'],m['n_physics'],m['n_instances'],m['canary_guid'])"
#   expect:  20260709 125 1000 25bffb18-440e-5e54-b08a-3b2c381a6bd6

# exact bytes
shasum -a 256 results/datasets/v2_seed20260709/instances.jsonl
#   expect:  3898032e75aa55afd801125ee8739aa596f89ea65aa11ed3e8d684dfe928ac5a
```

If the sha256 does **not** match (possible if numpy/sympy build differs across machines):
**do not run.** Ask the primary node to AirDrop its
`v2/results/datasets/v2_seed20260709/instances.jsonl` (+ `manifest.json`) to you privately, drop
it in place, and re-check the sha. Never fetch the dataset over a public channel.

## 5. Load the model, then run the column

Pre-load under the **dedicated identifier** the config expects (isolates you from GUI/JIT churn),
with the matching 24 576 context and a 24 h TTL so the idle reaper can't unload mid-run:

```bash
lms load qwen/qwen3-14b --identifier laptop-qwen3-14b --context-length 24576 --gpu max --ttl 86400 -y
lms ps      # confirm: laptop-qwen3-14b, CONTEXT 24576, TTL 24h
```

Run the single column (the `--models` flag points at your laptop panel):

```bash
cd v2
../.venv/bin/circuchain run \
    --models configs/models-laptop.yaml \
    --only qwen3-14b-think \
    --dataset results/datasets/v2_seed20260709 \
  2>&1 | tee results/run-qwen3-14b-think.log
```

It is **content-addressed and resumable** — if it dies, just rerun the same command; finished
instances are cached and skipped. It prints `plan=1000 done=N todo=M`. Done when `done=1000`.
Concurrency is 2 (32 GB-safe). If `lms ps` shows lots of free memory and you see no
`"model has crashed"` errors, you may bump to 3 by editing `concurrency` in
`configs/models-laptop.yaml` and rerunning (cache makes this free).

## 6. Verify the column before shipping

```bash
../.venv/bin/python -c "
import json,collections
rows=[json.loads(l) for l in open('results/responses/qwen3-14b-think.jsonl')]
ids={r['instance_id'] for r in rows}
prov=collections.Counter((r['provenance']['engine'],r['provenance']['quant']) for r in rows)
print('unique instances:', len(ids), '(want 1000)')
print('provenance      :', dict(prov), \"(want {('mlx','8bit'): 1000})\")
print('truncated       :', sum(r['truncated'] for r in rows))
"
```

Both the unique count (**1000**) and provenance (**mlx / 8bit for all rows**) must be right. A
handful of truncated rows is normal; hundreds means the context/token budget got changed — stop
and report.

## 7. Hand the results back (private transfer, NOT git)

Send exactly these two files to the primary node's `v2/results/responses/` via **AirDrop** (both
are Macs) or scp:

```
results/responses/qwen3-14b-think.jsonl
results/responses/qwen3-14b-think.failures.jsonl   # if present; transient-retry log, harmless
```

The primary node merges by copying them in (its grader dedups by `instance_id`). **Do not**
`git add`/`push` anything under `results/` — see §0.

Then report back: which column, `done=1000` confirmed, provenance check passed, and the sha256
of the responses file so the primary node can confirm what it received.

---

### If you were assigned a different column
Swap `qwen3-14b-think` → your key everywhere above, and the `--identifier`/`serve_id`:
`qwen3-8b-*` uses `laptop-qwen3-8b` and model `qwen/qwen3-8b`. Valid laptop keys are the four in
`configs/models-laptop.yaml` (`qwen3-14b-think/-nothink`, `qwen3-8b-think/-nothink`). The 32b
models do **not** fit in 32 GB — leave those to the M5.
