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
| Local providers (`providers/ollama.py`, `providers/mlx.py`) | ✅ built (Ollama proven interface) |
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

# 3. see which panel models you already have pulled
ollama serve &                             # if not already running
circuchain models --installed              # cross-checks configs/models.yaml vs `ollama list`
```

## The local model panel

`configs/models.yaml` defines a 10-model open-weights panel spanning three orthogonal factors so
the paper can make *causal* claims, not just a leaderboard:

- **C1** reasoning toggle on one base — `qwen3:14b` with `/think` on vs off
- **C2** reasoning-SFT natural experiment — `llama3.3:70b` vs `deepseek-r1:70b` (same base ± R1 distill)
- **C3** pure scale ladder — `qwen3` 1.7b → 4b → 8b → 14b → 32b

Pull what you're missing with the `ollama pull` lines `circuchain models --installed` prints.

## Pipeline (once the generator/runner stages are built — see ENGINEERING_PLAN.md)

```bash
make generate     # procedurally sample + dual-verify (SymPy==NGSPICE) N>=500 contract-varied instances
make verify
make run BACKEND=mlx      # run the panel (resumable, cached; MLX for official numbers, Ollama for the receipt)
make grade                # deterministic extract + numeric + compliance + T6 trace
make analyze              # McNemar paired tests, mixed-effects ORs, tables + figures
# or: make all
make smoke                # tiny end-to-end run on one small model
```

Every model call is content-addressed and cached (keyed on weight SHA + prompt + params), so a
multi-day M5 run **resumes** after a crash instead of restarting.
