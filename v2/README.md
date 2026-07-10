# CircuChain v2 — local (Apple M5) harness

v2 turns the v1 diagnostic into a **causal, statistically-powered, deterministically-graded**
benchmark for *Convention Blindness* that runs **entirely on local open-weights** — zero API cost,
fully reproducible. The v1 artifacts under `../data` and `../scripts` are frozen for provenance.

**Read first:** [`CIRCUCHAIN_V2_BRAINDUMP.md`](CIRCUCHAIN_V2_BRAINDUMP.md) (strategy + verdict),
[`FEASIBILITY.md`](FEASIBILITY.md) (go/no-go + risk), [`ENGINEERING_PLAN.md`](ENGINEERING_PLAN.md)
(the file-by-file build order).

## Status

| Piece | State |
|---|---|
| Deterministic compliance grader (`circuchain/grade/compliance.py`) | ✅ built + tested |
| v1 log re-grade → rule-vs-judge κ (`scripts/regrade_v1_logs.py`) | ✅ **runs today, κ=0.944** |
| T1 convention-contract transforms (`circuchain/contract.py`) | ✅ built + tested |
| Local providers (`providers/lmstudio.py` ← primary, `ollama.py`, `mlx.py`) | ✅ built, API-validated |
| Schema, configs, CLI skeleton | ✅ built |
| Procedural generator, topologies, verify, run, analyze | ⏳ stubs — see build order |

## Quickstart (what to run the minute you clone onto the M5)

```bash
# 0. deps — core is pure Python; no GPU needed for the headline result
cd v2
python3 -m pip install -e '.[dev]'        # or: pip install -r requirements.txt
brew install ngspice                       # ground-truth verifier (already at /opt/homebrew/bin)

# 1. THE credibility result — CPU-only, no model inference, ~2 seconds:
python3 scripts/regrade_v1_logs.py         # -> rule-vs-judge Cohen's kappa (target >=0.80)
#    (also: make regrade)

# 2. unit tests
make test                                  # contract transforms + grader, 14 cases

# 3. see which models you have, and which causal contrasts they can support
lms server start                           # LM Studio's OpenAI-compatible API on :1234
circuchain models --installed              # cross-checks configs/models.yaml vs `lms ls`
```

## The local model panel (served by LM Studio)

`configs/models.yaml` defines an open-weights panel spanning three orthogonal factors so the paper
can make *causal* claims, not just a leaderboard. `circuchain models --installed` prints a
**contrast-coverage report** telling you which are satisfiable with what you've downloaded:

- **C1** reasoning toggle on one base — `qwen/qwen3.6-27b` with `/think` vs `/no_think` (same
  weights, zero confounds — the cleanest contrast in the panel)
- **C2** reasoning-SFT natural experiment — an Instruct base vs its reasoning-distilled sibling
- **C3** pure scale ladder — one family across 1.7b → 4b → 8b → 14b → 27b

> ### ⚠️ The LM Studio context-length trap
> LM Studio's JIT loader defaults to a model's **full** `max_context_length` (often 262,144) and
> reserves a KV cache to match — it will refuse to load with *"requires approximately 86.30 GB of
> memory."* **Always pre-load with a constrained context** before a sweep:
> ```bash
> lms load qwen/qwen3.6-27b --context-length 8192 --gpu max -y   # or: make load MODEL=...
> ```
> The provider calls `assert_loaded()` and fails fast with this exact command rather than letting a
> multi-day run die on an OOM at hour 40. `num_ctx` in the config must match what you loaded with.

LM Studio reports each model's `compatibility_type` (**gguf** vs **mlx**) — recorded in the
provenance sidecar as the `engine` tag. Running the same model under both runtimes is exactly the
**cross-engine reproducibility receipt** the paper wants. Note LM Studio exposes no weight digest,
so provenance is the tuple `(publisher, arch, quantization, engine, loaded_context_length)`.

## Pipeline (once the generator/runner stages are built — see ENGINEERING_PLAN.md)

```bash
make generate     # procedurally sample + dual-verify (SymPy==NGSPICE) N>=500 contract-varied instances
make verify
make load MODEL=qwen/qwen3.6-27b   # pre-load with a constrained context (see the trap above)
make run                  # run the panel (resumable, cached); BACKEND=lmstudio by default
make grade                # deterministic extract + numeric + compliance + T6 trace
make analyze              # McNemar paired tests, mixed-effects ORs, tables + figures
# or: make all
make smoke                # tiny end-to-end run on one small model
```

Every model call is content-addressed and cached (keyed on weight SHA + prompt + params), so a
multi-day M5 run **resumes** after a crash instead of restarting.
