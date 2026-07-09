I've mapped the repo end-to-end (dataset schema, the 5 hardcoded topology solvers + SymPy `EquationVerifier` in the notebook, the async `BaseModelHandler` family, `grade_problem()`'s coarse sign logic, the GPT-5 judge, and the template-locked SPICE scripts). Here is the engineering plan.

---

# CircuChain v2 — Repo Engineering Plan (M5-local, reproducible)

## 0. Grounding: what exists today (and what it becomes)

| v1 asset (path) | What it is | v2 disposition |
|---|---|---|
| `data/circuchain_full_dataset - final.json` | 50 instances `{id, values, prompt, ground_truth:{mesh_currents, node_voltages, verifier_map}}` | **Freeze** as provenance; v2 regenerates procedurally |
| `data/graded_master_dataset.json` | 500 rows = 5 models × (50×2 methods) `{Model,ID,Type,Method,Grade,Details,Prompt,Response,GroundTruth}` | **Freeze**; v2 emits a superset schema with contract fields |
| `data/extracted_values_using_gpt4o/` | GPT-4o-parsed `{...,extracted_values:{i1..,vx..}}` | **Retire** GPT-4o extraction → deterministic regex extractor |
| `scripts/circuchain_engine.ipynb` cells 0–5 | `EquationVerifier` (SymPy) + `solve_probN_kvl/kcl` + `prompt_probN` + `check_probN` | **Port** into `circuchain/topologies/` (this is the reusable IP) |
| cell 12 | `BaseModelHandler`/OpenAI/Anthropic/Gemini/OpenRouter + `run_benchmark` (asyncio.Semaphore, forks KVL/KCL) | **Port + generalize** into `providers/` + `run.py` |
| cell 16 | `grade_problem()` — 5% tol + coarse `ERR_SIGN` (|pred|≈|truth|) | **Replace** with contract-based deterministic grader |
| cells 14/17/18 | GPT-5 judge + Sonnet audit | **Demote** to optional off-critical-path audit |
| `scripts/ngspice_circuit_generator.py`, `verify_and_export_json.py` | Template-locked per-topology `.cir` emitters + ngspice runner (uses `V_sense` current sensors) | **Port + generalize** into `topologies/*` + `verify.py` |

`ngspice` is already at `/opt/homebrew/bin/ngspice`. Everything under `data/` and `scripts/` stays byte-for-byte for provenance; all new code lands in a clean `v2/` tree.

---

## 1. Proposed directory layout

Keep v1 intact; add one self-contained `v2/` root holding an installable `circuchain` package.

```
CircuChain/                              # repo root (unchanged remote)
├── README.md                           # LEAVE; append a "## v2 (local M5 harness)" section
├── data/                               # FROZEN v1 artifacts (provenance) — do not edit
├── scripts/                            # FROZEN v1 scripts + notebook (provenance)
│
└── v2/                                 # everything new lives here
    ├── pyproject.toml                  # installable pkg + pinned deps + entry point `circuchain`
    ├── requirements.txt                # pip fallback (pinned, hashless)
    ├── requirements-api.txt            # optional: openai, anthropic (frontier ceiling only)
    ├── Makefile                        # one target per pipeline stage + `make all`, `make smoke`
    ├── README.md                       # v2 quickstart (clone → ollama pull → make all)
    ├── .env.example                    # OPENAI_API_KEY / ANTHROPIC_API_KEY (optional)
    │
    ├── configs/
    │   ├── models.yaml                 # the local model panel + params + quant + role-axis tags
    │   ├── contracts.yaml              # convention-contract dimensions + Latin-square design (T1)
    │   ├── dataset.yaml                # topologies, regimes, N, seeds, tolerances
    │   ├── run.yaml                    # concurrency, caching, max_tokens caps, backend order
    │   └── smoke.yaml                  # tiny subset: 4 instances × 1 tiny model (CI/laptop)
    │
    ├── circuchain/                     # the package (import circuchain)
    │   ├── __init__.py
    │   ├── schema.py                   # dataclasses: Instance, Contract, Completion, GradeRow
    │   ├── contract.py                 # ConventionContract + deterministic sign transforms (T1 core)
    │   ├── topologies/
    │   │   ├── __init__.py             # TOPOLOGY_REGISTRY: name -> Topology
    │   │   ├── base.py                 # Topology ABC: sample/solve_kvl/solve_kcl/netlist/prompt
    │   │   ├── supermesh.py            # ported from solve_prob1_* + gen_spice_prob1 + prompt_prob1
    │   │   ├── opposing_t.py           # prob2
    │   │   ├── wheatstone.py           # prob3
    │   │   ├── ladder.py               # prob4
    │   │   └── vcvs.py                 # prob5
    │   ├── analytic.py                 # SymPy EquationVerifier (ported cell 0) + dual-check helpers
    │   ├── generate.py                 # procedural generator: regimes × contracts × seeds → instances
    │   ├── verify.py                   # NGSPICE(.op) + SymPy dual verification (ported/generalized)
    │   ├── providers/
    │   │   ├── __init__.py             # build_provider(cfg) factory
    │   │   ├── base.py                 # Provider ABC (uniform async generate())
    │   │   ├── ollama.py               # /api/chat adapter (localhost:11434) + /api/tags enumerate
    │   │   ├── mlx.py                  # mlx_lm adapter (in-process, thread executor)
    │   │   ├── openai_api.py           # optional frontier ceiling (ports v1 OpenAIHandler)
    │   │   └── anthropic_api.py        # optional frontier ceiling (ports v1 AnthropicHandler)
    │   ├── cache.py                    # content-addressed response cache + provenance sidecars
    │   ├── run.py                      # runner: model × instance × method → cached completions
    │   ├── grade/
    │   │   ├── extract.py              # DETERMINISTIC regex answer extractor (replaces GPT-4o)
    │   │   ├── numeric.py              # tolerance grader (refactor of grade_problem)
    │   │   ├── compliance.py           # RULE-BASED contract compliance grader (headline)
    │   │   ├── trace.py                # T6 deterministic reasoning-trace taxonomy on <think>
    │   │   └── judge.py                # OPTIONAL LLM judge (audit only, off critical path)
    │   ├── analyze/
    │   │   ├── stats.py                # McNemar paired tests, Wilson CIs, bootstrap
    │   │   ├── tables.py               # accuracy / compliance-vs-competence tables → csv
    │   │   └── figures.py              # matplotlib figures → results/figures/
    │   └── cli.py                      # `circuchain generate|verify|run|grade|analyze`
    │
    ├── tests/
    │   ├── test_analytic_vs_spice.py   # every generated instance: SymPy == NGSPICE (tol)
    │   ├── test_contract_transforms.py # flip-mesh negates i; ref-node shifts v; PSC flips sign
    │   ├── test_extract.py             # regex extractor golden cases
    │   └── test_compliance_grader.py   # synthetic pred sets → known compliance labels
    │
    └── results/                        # all generated outputs (git-ignored except manifests)
        ├── datasets/                   # generated instances + verifier maps (versioned by seed)
        │   └── v2_seed{SEED}/instances.jsonl
        ├── verification/               # per-instance ngspice logs + dual-check report
        ├── cache/                      # content-addressed raw completions (resumable)
        │   └── {model}/{sha256}.json
        ├── responses/                  # per-model run JSONL (append-only, resumable)
        ├── graded/                     # graded rows JSONL (numeric + compliance)
        ├── tables/                     # *.csv for the paper
        ├── figures/                    # *.pdf/*.png
        └── manifests/                  # run_manifest.json (git SHA, model SHAs, versions, seeds)
```

---

## 2. Local model runner architecture

### 2.1 Uniform provider interface (matches the existing async pattern)

`v1`'s `BaseModelHandler.generate(prompt, system_msg)` is the seed; v2 widens it to carry sampling params, seeds, and to split the reasoning `<think>` trace from the final answer (needed for T6).

```python
# circuchain/providers/base.py
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class GenParams:
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 8192        # hard cap on CoT tail (budget control)
    num_ctx: int = 8192
    stop: list[str] = field(default_factory=list)
    think: bool | None = None     # request/allow a reasoning channel if the model has one

@dataclass
class Completion:
    text: str                     # final answer body (think stripped)
    think: str = ""               # reasoning trace if any (for grade/trace.py)
    raw: str = ""                 # unmodified provider payload
    usage: dict = field(default_factory=dict)     # prompt/eval token counts
    provenance: dict = field(default_factory=dict) # model_id, weight_sha, quant, backend, versions

class Provider(ABC):
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model_id = cfg["model_id"]
    @abstractmethod
    async def generate(self, system: str, user: str, params: GenParams) -> Completion: ...
    @abstractmethod
    def fingerprint(self) -> dict: ...   # weight_sha/quant/backend/lib versions → provenance
```

A single factory keeps callers backend-agnostic:

```python
# circuchain/providers/__init__.py
def build_provider(cfg: dict) -> Provider:
    return {"ollama": OllamaProvider, "mlx": MLXProvider,
            "openai": OpenAIProvider, "anthropic": AnthropicProvider}[cfg["backend"]](cfg)
```

### 2.2 Ollama adapter (`/api/chat`, temp=0, seed, think-block handling)

```python
# circuchain/providers/ollama.py
import httpx, re, hashlib
from .base import Provider, GenParams, Completion

_THINK = re.compile(r"<think>(.*?)</think>\s*", re.S | re.I)

class OllamaProvider(Provider):
    def __init__(self, cfg, host="http://localhost:11434"):
        super().__init__(cfg)
        self.host = cfg.get("host", host)

    async def generate(self, system, user, params: GenParams) -> Completion:
        payload = {
            "model": self.model_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,                 # one-shot; simpler + deterministic to log
            "options": {                     # temp=0 lives under options in Ollama
                "temperature": params.temperature,
                "seed": params.seed,
                "num_predict": params.max_tokens,
                "num_ctx": params.num_ctx,
                "stop": params.stop,
            },
        }
        # Newer Ollama exposes a first-class thinking channel; older models embed <think>…</think>.
        if params.think is not None:
            payload["think"] = params.think
        async with httpx.AsyncClient(timeout=None) as c:
            r = await c.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        msg = data["message"]
        content, think = msg.get("content", ""), msg.get("thinking", "")
        if not think:                         # fall back to inline <think> extraction
            m = _THINK.search(content)
            if m:
                think, content = m.group(1), _THINK.sub("", content, count=1)
        return Completion(
            text=content.strip(), think=think.strip(), raw=r.text,
            usage={"prompt": data.get("prompt_eval_count"), "eval": data.get("eval_count")},
            provenance=self.fingerprint(),
        )

    def fingerprint(self) -> dict:
        # /api/show returns digest + details (quant, family, param size) — pin it for reproducibility
        info = httpx.get(f"{self.host}/api/show", json={"model": self.model_id}).json()
        return {"backend": "ollama", "model_id": self.model_id,
                "weight_sha": info.get("digest") or _digest_from_show(info),
                "quant": info.get("details", {}).get("quantization_level"),
                "family": info.get("details", {}).get("family")}

    @staticmethod
    def list_installed(host="http://localhost:11434") -> list[dict]:
        # ENUMERATE what the author actually has downloaded
        tags = httpx.get(f"{host}/api/tags").json()["models"]
        return [{"name": m["name"], "size": m["size"],
                 "quant": m["details"]["quantization_level"],
                 "family": m["details"]["family"], "digest": m["digest"]} for m in tags]
```

`OllamaProvider.list_installed()` backs a CLI helper (`circuchain models --installed`) that cross-checks `configs/models.yaml` against `GET /api/tags` and warns on any configured model that isn't pulled — so a multi-day run never dies at hour 40 on a missing weight.

The **MLX adapter** mirrors this in-process (no HTTP): it lazily `from mlx_lm import load, generate`, caches the loaded model, runs the blocking `generate` under `asyncio.to_thread` (same trick v1 used for the synchronous Gemini SDK), sets `temp=0` greedy + `mx.random.seed(params.seed)`, and derives `weight_sha` from the HF snapshot commit hash. MLX is the "official numbers" engine; Ollama is the convenience/enumeration path; keeping both behind `Provider` gives the reviewer-facing "gaps reproduce on two engines" receipt.

### 2.3 Model registry / `configs/models.yaml`

```yaml
# configs/models.yaml — the local panel; each entry is one column in every results table
defaults:
  backend: ollama            # MLX for the official run: set backend: mlx per-model or via --backend
  temperature: 0.0
  seed: 20260709
  max_tokens: 8192
  num_ctx: 8192

models:
  - key: qwen3-4b-think
    model_id: "qwen3:4b"          # ollama tag (or HF repo id when backend: mlx)
    role_axis: reasoning          # reasoning | base  → drives the compliance×competence split
    scale_tier: 4b
    family: qwen
    quant: q4_K_M
    think: true
    enabled: true
  - key: llama31-8b
    model_id: "llama3.1:8b-instruct-q4_K_M"
    role_axis: base
    scale_tier: 8b
    family: llama
    think: false
  - key: ds-r1-qwen-8b
    model_id: "deepseek-r1:8b"
    role_axis: reasoning
    scale_tier: 8b
    family: deepseek-distill
    think: true
  - key: qwen3-14b
    model_id: "qwen3:14b"
    role_axis: reasoning
    scale_tier: 14b
    family: qwen
    think: true                   # pairs with a think:false sibling for the reasoning-toggle control
  - key: phi4-14b
    model_id: "phi4:14b"
    role_axis: base
    scale_tier: 14b
    family: phi
  - key: qwen3-30b-a3b-think
    model_id: "qwen3:30b-a3b"
    role_axis: reasoning
    scale_tier: 30b-moe
    family: qwen
    think: true
  - key: gpt-oss-20b
    model_id: "gpt-oss:20b"
    role_axis: reasoning
    scale_tier: 20b-moe
    quant: mxfp4
    family: openai-oss
    think: true
  - key: gemma3-27b
    model_id: "gemma3:27b"
    role_axis: base
    scale_tier: 27b
    family: gemma
  - key: llama33-70b
    model_id: "llama3.3:70b-instruct-q4_K_M"   # base half of the 70B natural experiment
    role_axis: base
    scale_tier: 70b
    family: llama
  # top reasoning tier — verify availability live; MoE keeps decode cheap
  - key: qwen3-next-80b-a3b
    model_id: "qwen3-next:80b-a3b"
    role_axis: reasoning
    scale_tier: 80b-moe
    family: qwen
    think: true
    enabled: false               # flip on once pulled; fallback: gpt-oss-120b or ds-r1-llama-70b

# optional frontier ceiling (needs API keys; adds 2–3 columns, ~$150–300 total)
api_models:
  - {key: gpt-5, backend: openai, model_id: gpt-5, role_axis: reasoning, enabled: false}
  - {key: opus-4-5, backend: anthropic, model_id: claude-opus-4-5-20251101, role_axis: reasoning, enabled: false}
```

The `role_axis` tag is what makes the compliance-vs-competence trade-off analyzable per axis, and the `think` flag on paired Qwen3 entries encodes the within-model reasoning-toggle natural experiment.

---

## 3. The pipeline as a reproducible CLI

### 3.1 T1 causal contract — the piece that reshapes generate/grade

This is the scientific centerpiece and the reason the grader can be deterministic. A `ConventionContract` is a set of orthogonal convention dimensions; each maps to a **pure sign/offset transform** on the canonical (contract-neutral) verifier map produced by the analytic solver. Same physics, different contract ⇒ different *correct signed answer*, computed in closed form and cross-checked in SymPy.

```python
# circuchain/contract.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ConventionContract:
    mesh_dir: str        # "cw" | "ccw"        → ccw negates every mesh current
    psc: str             # "passive" | "active"→ active flips branch-current signs
    ref_node: str        # "bottom" | "top"    → top ref subtracts a fixed node from all voltages
    method: str          # "mesh_kvl" | "nodal_kcl"  (compliance dimension, not a sign map)

DEFAULT = ConventionContract("cw", "passive", "bottom", "mesh_kvl")  # v1's implicit textbook prior

def apply(contract: ConventionContract, canonical: dict, meta: dict) -> dict:
    """canonical = neutral signed verifier_map from the analytic solver.
       Returns the answer a COMPLIANT solver must produce under `contract`."""
    out = dict(canonical)
    if contract.mesh_dir == "ccw":
        for k in meta["mesh_current_keys"]:      # i1,i2,i3
            out[k] = -out[k]
    if contract.psc == "active":
        for k in meta["branch_current_keys"]:
            out[k] = -out[k]
    if contract.ref_node == "top":
        vref = canonical[meta["top_ref_key"]]
        for k in meta["node_voltage_keys"]:      # vx,vy,...
            out[k] = out[k] - vref
    return out                                   # method has no sign map; graded structurally
```

The Latin square in `configs/contracts.yaml` crosses `{mesh_dir, psc, ref_node, method}` against `{5 topologies} × {control, trap regimes}` so every physics instance appears under multiple contracts and every contract appears across physics — the balanced design v1 never had.

### 3.2 Deterministic compliance grader (kills the judge dependency)

Because we can compute **both** the contract-correct answer *and* the default-prior answer, sign-convention compliance becomes a table lookup, not an LLM judgment:

```python
# circuchain/grade/compliance.py
def classify(pred: dict, expected: dict, default: dict, meta, tol=0.05) -> dict:
    labels = {}
    for var, exp in expected.items():
        p = pred.get(var)
        if p is None:                               labels[var] = "ERR_MISSING"; continue
        if _close(p, exp, tol):                     labels[var] = "PASS"; continue          # compliant+competent
        if default[var] != exp and _close(p, default[var], tol):
            labels[var] = "ERR_SIGN_CONVENTION"     # right physics, WRONG contract → Convention Blindness
        elif _close(abs(p), abs(exp), tol):
            labels[var] = "ERR_SIGN_AMBIG"          # magnitude ok, sign matches neither reference
        else:
            labels[var] = "ERR_VAL"                 # competence failure (magnitude wrong)
        labels[var] and None
    return _reduce(labels)   # → {PASS, ERR_SIGN_CONVENTION, ERR_VAL, ...} + per-var detail
```

This is the crucial upgrade over v1's `grade_problem()`, whose `ERR_SIGN` fired on any `|pred|≈|truth|` coincidence with no notion of *which* contract the model followed. Here the label is decided by matching the prediction against the **specific competing convention**, so "the model obeyed its training prior instead of my instruction" is a rule, not a GPT-5 opinion. Method compliance (`mesh_kvl` vs `nodal_kcl`) is graded by a conservative deterministic structural classifier in `trace.py` (regex for mesh/loop-current vs node-voltage equation markers); the LLM judge in `judge.py` is retained *only* as an optional audit cross-check on that one weaker signal, never on the critical path or the headline number.

### 3.3 Stages, one command each

```
circuchain generate  --config configs/dataset.yaml --seed 20260709   # → results/datasets/v2_seed20260709/instances.jsonl
circuchain verify    --dataset results/datasets/v2_seed20260709      # NGSPICE + SymPy dual-check → verification/
circuchain run       --models configs/models.yaml --backend mlx      # → results/cache/ + results/responses/*.jsonl (RESUMABLE)
circuchain grade     --responses results/responses                   # deterministic extract+numeric+compliance → results/graded/
circuchain analyze   --graded results/graded                         # McNemar + Wilson CIs → results/tables/ + figures/
circuchain judge     --graded results/graded --model <local|api>     # OPTIONAL audit, off critical path
```

`Makefile` wires them:

```makefile
SEED ?= 20260709
DS   := results/datasets/v2_seed$(SEED)

generate: ; circuchain generate --config configs/dataset.yaml --seed $(SEED)
verify:   generate ; circuchain verify --dataset $(DS)
run:      verify ; circuchain run --models configs/models.yaml --backend $(BACKEND)
grade:    run ; circuchain grade --responses results/responses
analyze:  grade ; circuchain analyze --graded results/graded
all:      analyze
smoke:    ; circuchain generate --config configs/smoke.yaml --seed 1 && \
            circuchain verify --dataset results/datasets/v2_seed1 && \
            circuchain run --models configs/smoke.yaml && \
            circuchain grade --responses results/responses && \
            circuchain analyze --graded results/graded
```

### 3.4 Determinism, caching, resumability (mandatory for a multi-day M5 run)

- **Seeds everywhere.** Generator seed → parameter sampling + Latin-square assignment. Provider seed → Ollama `options.seed` / `mx.random.seed`. Greedy `temperature=0`. All seeds recorded in `results/manifests/run_manifest.json`.
- **Content-addressed cache.** Key = `sha256(model_key + weight_sha + quant + backend + system + user + genparams)`. `run.py` checks `results/cache/{model}/{key}.json` before every call; a hit skips inference. Because the key includes `weight_sha`, re-pulling a different quant correctly invalidates.
- **Append-only JSONL** per model in `results/responses/{model}.jsonl` — a killed run resumes by diffing completed `(instance_id, method)` pairs against the plan and only issuing the remainder. No "restart from zero" after a crash on hour 50.
- **Provenance sidecar** per completion (model_id, weight_sha, quant, backend, `mlx`/`ollama`/lib versions, seed, prompt hash) — the reproducibility receipt reviewers at ICLR/NeurIPS-ED/TMLR require for an executable artifact.

```python
# circuchain/cache.py (core)
def key(model_key, prov, system, user, gp) -> str:
    h = hashlib.sha256()
    for part in (model_key, prov["weight_sha"], prov.get("quant",""), prov["backend"],
                 system, user, json.dumps(gp.__dict__, sort_keys=True)):
        h.update(str(part).encode())
    return h.hexdigest()
```

---

## 4. Reproducibility & packaging

- **`pyproject.toml`** (PEP 621) with pinned deps: `httpx`, `pyyaml`, `numpy`, `sympy`, `pandas`, `scipy` (McNemar/Wilson), `matplotlib`, `typer` (CLI), `pytest`. Extras: `[mlx]` → `mlx-lm`; `[api]` → `openai`, `anthropic`. Console entry point `circuchain = circuchain.cli:app`. Pin exact versions and commit a lockfile; **do not** pin `mlx-lm` too hard (fast-moving) but record the resolved version in the manifest.
- **NGSPICE install note (macOS/brew)** in `v2/README.md`: `brew install ngspice` (already present at `/opt/homebrew/bin/ngspice`); `circuchain verify` shells out exactly as v1's `verify_and_export_json.py` did (`ngspice -b -o log cir`) and fails loudly if the binary is absent.
- **Ollama/MLX setup note**: `brew install ollama && ollama serve`; `ollama pull` the panel; MLX weights via `huggingface-cli download`. `circuchain models --installed` prints the `GET /api/tags` inventory and flags gaps vs `models.yaml`.
- **Env for optional API keys**: `.env.example` → `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`; loaded only when an `api_models` entry is `enabled` (mirrors v1's `os.getenv` guard). The local panel needs **zero** keys.
- **Smoke test** (`configs/smoke.yaml`): 4 instances × `qwen3-4b` × both methods, runs in minutes on a laptop and in CI; `make smoke` is the first thing the author runs post-clone.
- **Contamination guard** (call it out in the README + a `docs/contamination.md`): (1) v1 used canonical textbook (Sadiku) parameter values that are almost certainly in pretraining — v2's generator samples **fresh randomized regimes** and **never ships raw instances that match v1**; (2) each release is seed-stamped and the *raw generated prompts are held out of any training corpus*; (3) embed a canary string per generated dataset so future leakage is detectable; (4) because local open-weights may have ingested the v1 arXiv paper, the T1 contract manipulation is itself a contamination hedge — the *default-convention* answer is memorizable, but the *flipped-contract* answer is not, so a model parroting v1 numbers scores as `ERR_SIGN_CONVENTION`, which is exactly the phenomenon under study.

---

## 5. File-by-file: new vs refactor vs leave, in build order

**LEAVE untouched (provenance):** everything in `data/`, `scripts/*.py`, `scripts/circuchain_engine.ipynb`. Only edit: append a v2 section to the root `README.md`.

**PORT (lift logic out of the notebook/scripts, don't rewrite from scratch):** the SymPy `EquationVerifier` (cell 0), the five `solve_probN_kvl/kcl` + `prompt_probN` + `check_probN` (cells 1–5), the SPICE emitters (`ngspice_circuit_generator.py` / `verify_and_export_json.py`), the `BaseModelHandler` family + `run_benchmark` (cell 12).

**Build order** (each step is independently testable; the author can start at #1 immediately):

1. **`v2/pyproject.toml` + `circuchain/__init__.py` + `configs/smoke.yaml`** — installable skeleton so `pip install -e v2/` and `circuchain --help` work day one.
2. **`circuchain/schema.py`** — the dataclasses every module shares (`Instance`, `Contract`, `Completion`, `GradeRow`); locks the data contract first.
3. **`circuchain/topologies/base.py` + `supermesh.py`** — port `solve_prob1_*`/`prompt_prob1`/`gen_spice_prob1`. Do one topology end-to-end before the other four.
4. **`circuchain/analytic.py`** — port `EquationVerifier`; add `dual_check(analytic, spice)` used by both verify and tests.
5. **`circuchain/contract.py` + `tests/test_contract_transforms.py`** — the T1 sign transforms; unit-test flip-mesh/ref-node/PSC against the supermesh instance. **This is the highest-novelty module — get it right early.**
6. **`circuchain/verify.py` + `tests/test_analytic_vs_spice.py`** — generalize the ngspice runner; assert SymPy == NGSPICE on every generated instance (the dual-verification gate).
7. **Port topologies 2–5** (`opposing_t/wheatstone/ladder/vcvs.py`) now that the pattern + tests exist.
8. **`circuchain/generate.py` + `configs/dataset.yaml` + `configs/contracts.yaml`** — procedural generator: regimes × Latin-square contracts × seed → `instances.jsonl` (N≥500). Gate every instance through `verify.py`.
9. **`circuchain/providers/base.py` + `ollama.py`** — uniform interface + the primary local adapter + `list_installed`. Smoke-call one model.
10. **`circuchain/cache.py` + `circuchain/run.py`** — content-addressed cache, append-only JSONL, resume logic. Port `run_benchmark`'s KVL/KCL fork + semaphore.
11. **`circuchain/grade/extract.py` + `numeric.py`** — deterministic regex extractor (retire GPT-4o) + refactor `grade_problem`. `tests/test_extract.py` with golden cases.
12. **`circuchain/grade/compliance.py` + `trace.py` + `tests/test_compliance_grader.py`** — the rule-based contract grader + T6 trace taxonomy. **The headline deliverable.**
13. **`circuchain/analyze/stats.py` + `tables.py` + `figures.py`** — McNemar (control/trap, contract-A/B), Wilson CIs, compliance-vs-competence tables/figures.
14. **`circuchain/providers/mlx.py`** — the "official numbers" engine + cross-engine reproducibility check (can lag until the panel is finalized).
15. **`circuchain/cli.py` + `Makefile` + `configs/models.yaml` + `configs/run.yaml`** — wire the five stages into one command each and `make all`/`make smoke`.
16. **`circuchain/providers/openai_api.py` + `anthropic_api.py` + `grade/judge.py`** — optional frontier ceiling + optional audit judge, both off the critical path, built last.

Steps 1–8 give a fully verified N≥500 contract-varied dataset with zero model inference; 9–13 give the local runner + deterministic graders + paired stats (the reviewer-critique-killing core); 14–16 are polish, scale-engine, and the optional API ceiling.

**Key file paths the author will touch first:** `/Users/mayankgowda/CircuChain-Benchmark/v2/pyproject.toml`, `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/contract.py`, `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/topologies/supermesh.py` (ported from `scripts/circuchain_engine.ipynb` cell 1), `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/providers/ollama.py`, and `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/grade/compliance.py`.