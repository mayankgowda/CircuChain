I now have full grounding. Here is the design doc.

---

# CircuChain v2 — Scientific Core Design Specification

**Status:** implementation-ready · **Grounds against:** `data/circuchain_full_dataset - final.json` (50 instances), `graded_master_dataset.json` (500 rows), `final_diagnosis_gpt5.json`, `scripts/verify_and_export_json.py`, `scripts/ngspice_circuit_generator.py`.

**Key facts inherited from v1 (verified in-repo):**
- Instance schema: `{id, values, prompt, ground_truth:{mesh_currents[], node_voltages{}, verifier_map{signed floats}}}`.
- The prompt already carries a **fixed** convention block ("MESH CURRENTS: always CLOCKWISE", "GROUND at bottom", "PASSIVE SIGN CONVENTION: current enters +"). v1 never *varies* it — that is exactly the missing causal manipulation.
- `verifier_map` currently exposes only two variable **roles** — mesh currents (`i1..i3`) and node voltages (`vx,vy,va,vb,v1..v3`). NGSPICE netlists print only the two output nodes, not the full potential vector. **Both must change for T1** (see §1.2, §3).
- v1 grade tally (500 rows): PASS 201, ERR_VAL 239, ERR_SIGN 60 (coarse magnitude-match). Judge tally: PHYSICS_SETUP 197, SIGN_CONVENTION 70, CALC 25, HALLUC 3, METHOD 4. The judge's SIGN and METHOD labels are the ones the deterministic grader will replace (§2.4).

---

## 0. Architecture: two suites, one generator

v2 splits into two experimental suites drawn from **one** procedural generator, because the causal test and the power test have different sampling needs and a naïve full-cross explodes compute.

| Suite | Purpose | Sampling | Contract | Size (per model) |
|---|---|---|---|---|
| **MAIN** (power) | Headline accuracy, Control/Trap, model ranking, McNemar model-vs-model | N≥500 distinct physics × 2 methods | **default** contract only | 1,000 calls |
| **CAUSAL** (T1) | Isolate each convention factor's causal effect on compliance, holding physics fixed | N_core=150 physics *anchors* × contract factorial | **manipulated** contract | 2,400 calls (frac.) |

Everything below is defined so an engineer builds the generator once and both suites fall out of it.

---

## 1. Pillar 1 — Causal Convention-Contract Manipulation (T1)

### 1.1 The five factors and the variable-role ontology

The causal claim requires that each factor have a **deterministic, disjoint action** on the signed answer. That only works if we stop treating outputs as an undifferentiated bag and assign every output variable a **role**. Four roles, and each factor acts on a disjoint subset:

| Role | Definition | Example (Supermesh) |
|---|---|---|
| `mesh_current` | signed loop current, sign = declared loop-traversal direction | `i1,i2,i3` |
| `branch_current` | signed current through a named element, sign = element ref orientation + PSC | `i_Rshare` |
| `node_voltage` | potential of a node w.r.t. the declared reference node | `vx,vy` |
| `element_voltage` | voltage across a named element, sign = PSC direction | `v_R2` |

**The five contract factors and their sign-action operators:**

| Factor | Levels | `mesh_current` | `branch_current` | `node_voltage` | `element_voltage` |
|---|---|---|---|---|---|
| **mesh_direction** | CW / CCW | ×(−1) on CCW | — | — | — |
| **passive_sign_convention** | standard / inverted | — | ×(−1) on inverted | — | ×(−1) on inverted |
| **reference_node** | A / B | — | — | affine: `−V(B)` | — |
| **naming_scheme** | scheme1 / scheme2 | permute label→quantity | permute | permute | permute |
| **required_method** | KVL / KCL | *(procedure only — no numeric action)* | — | — | — |

This orthogonality is the scientific heart of T1: because each sign factor touches a **disjoint role set**, its marginal effect on compliance is identifiable without confounding. Two consequences the engineer must honor:

1. **Every CAUSAL-suite instance must expose ≥1 variable of each of the four roles** (where the topology admits it), or a factor has no handle in that instance. v1 instances expose only 2 roles → the generator must add a `branch_current` and an `element_voltage` output to each topology's output set.
2. `reference_node` is **not a sign flip** — it is an affine shift `V'(n) = V(n) − V(B)`, which can change magnitude too. So the grader must compare against a **precomputed contract-shifted expected value**, not just a flipped sign (see §1.3).

### 1.2 Deterministic derivation of expected signed values

Ground truth is computed **once** in a canonical frame R0 (mesh CW, PSC standard, ground = node A, naming scheme1). The generator stores the *complete* solution — full node-potential vector and all branch currents — so any contract's expected answer is a pure function, no re-simulation:

```python
def expected_value(symbol, contract, cf):   # cf = canonical_frame block
    phys = NAMING_MAP[contract.naming_scheme][symbol]   # symbol -> physical quantity + role
    role = phys.role

    if role == "mesh_current":
        base = cf.mesh_currents[phys.loop]              # canonical CW value
        return base if contract.mesh_direction == "CW" else -base

    if role == "branch_current":
        base = cf.branch_currents[phys.element]         # signed, element ref orientation
        return -base if contract.passive_sign_convention == "inverted" else base

    if role == "node_voltage":
        ref = cf.node_potentials[REF_NODE[contract.reference_node]]   # A or B potential
        return cf.node_potentials[phys.node] - ref

    if role == "element_voltage":
        drop = cf.node_potentials[phys.n_plus] - cf.node_potentials[phys.n_minus]
        return drop if contract.passive_sign_convention == "standard" else -drop
```

The generator calls this for every `(symbol, contract)` and freezes the result into `ground_truth.expected_under_contract`. **Grading is then a pure lookup + compare — no LLM in the sign loop.**

Crucially, the generator *also* computes `expected_value(symbol, DEFAULT_contract, cf)` and stores it as `expected_under_default`. The gap between `expected_under_contract` and `expected_under_default` is the operational definition of Convention Blindness: a model that answers the *default* sign when the *declared* sign is flipped is provably ignoring the instruction (§2.1, §4).

### 1.3 JSON schema extension (backward-compatible)

`convention_contract` and `canonical_frame` are **additive**. A loader treats any instance lacking `convention_contract` as the DEFAULT contract, so all 50 v1 instances and 500 v1 log rows re-grade unchanged (this is what makes the §2.5 validation possible).

```json
{
  "id": "supermesh__phys00042__c07",
  "schema_version": "2.0",
  "topology": "supermesh",
  "physics_id": "phys00042",            // groups all contract variants of one physics
  "values": { "V1":100, "V2":40, "Is":0.004, "R1":4000, "R2":8000, "R3":2000 },

  "regime": {                            // T3 programmatic tags (NOT hand-labeled)
    "class": "TRAP",
    "predicates": { "dominant_current_negative": true, "max_r_ratio": 142.0, "near_cancellation": false },
    "tags": ["sign_flip:i2", "r_ratio:142"]
  },

  "convention_contract": {               // T1 — ABSENT ⇒ DEFAULT (v1 back-compat)
    "mesh_direction": "CCW",
    "passive_sign_convention": "inverted",
    "reference_node": "B",
    "naming_scheme": "scheme2",
    "required_method": "KVL",
    "cell_id": "c07",
    "default_contract": { "mesh_direction":"CW", "passive_sign_convention":"standard",
                          "reference_node":"A", "naming_scheme":"scheme1", "required_method":"KVL" }
  },

  "prompt": "...",                       // RENDERED to state the declared contract verbatim

  "ground_truth": {
    "mesh_currents": [0.002, 0.006, 0.002],       // v1 fields retained (canonical frame)
    "node_voltages": { "vx":92.0, "vy":44.0 },     // v1 retained
    "verifier_map":  { "i1":0.002, "i2":0.006, "i3":0.002, "vx":92.0, "vy":44.0 },  // v1 retained

    "canonical_frame": {                 // NEW — complete solution for re-derivation
      "reference_node": "A",             // A = node "0"
      "node_potentials": { "n1":100.0, "n2":92.0, "n3":44.0, "n4":40.0, "0":0.0 },
      "branch_currents": { "R1":0.002, "R2":0.006, "R3":0.002, "R_share":0.004 },
      "element_orientation": { "R1":["n1","n2"], "R2":["n2","n3"], "R_share":["n2","0"] },
      "ref_node_map": { "A":"0", "B":"n4" },
      "variable_binding": {
        "i1": {"role":"mesh_current","loop":"mesh1"},
        "vx": {"role":"node_voltage","node":"n2"},
        "i_Rshare": {"role":"branch_current","element":"R_share"},
        "v_R2": {"role":"element_voltage","element":"R2"}
      }
    },

    "expected_under_contract": { "i1":-0.002, "i2":-0.006, "i3":-0.002, "vx":48.0, "vy":0.0,
                                 "i_Rshare":-0.004, "v_R2":24.0 },
    "expected_under_default":  { "i1": 0.002, "i2": 0.006, "i3": 0.002, "vx":92.0, "vy":44.0,
                                 "i_Rshare": 0.004, "v_R2":-24.0 }
  },

  "provenance": { "seed":12345, "generator_version":"2.0.1",
                  "instance_hash":"sha256:…", "verified_by":["ngspice-42.0","sympy-1.13"] }
}
```

### 1.4 Experimental design: factorial, Latin square, target N

The four **sign factors** (mesh_direction, PSC, reference_node, naming) form a 2⁴ = 16-cell factorial; `required_method` (2 levels) crosses to 32 cells per physics anchor. Full 32-cell × N_core × 10 models is ~1–2 weeks of M5 reasoning-model time — too much. Three-part design:

- **(a) GOLDEN full factorial** — `N_gold = 40` anchors × **full 32 cells** = 1,280 calls/model. Estimates *all* main effects **and two-way interactions** (e.g., does CCW×naming2 compound?). Run on the full 10-model panel.
- **(b) CAUSAL fractional factorial** — `N_core = 150` anchors × **2⁴⁻¹ resolution-IV** design (generator `D = ABC`, i.e. `naming = mesh·PSC·ref`, 8 cells) × 2 methods = **16 cells → 2,400 calls/model**. Main effects clean, aliased only with 3-way interactions. Run on a **6-model causal panel** spanning the axes (incl. both natural experiments: Llama-3.3-70B vs R1-Distill-Llama-70B; Qwen3 think-on/off).
- **(c) Latin-square balancing for the extension set** — to cheaply widen physics coverage without paying 16×, assign contract cells to an additional `N_ext = 300` anchors via a **balanced orthogonal array (OA(16, 4, 2, 2))** so every factor level and every pairwise combination is equally represented across anchors (one cell per anchor). This gives population-level factor estimates at 1 call/anchor/method — the "Latin square" the brief asks for, used as a variance-balanced screen, with (a)/(b) as the gold within-physics tests.

The unit of pairing is `physics_id`: every anchor is rendered under every contract cell in its design, so **each factor contrast is a within-physics, within-model matched pair.**

### 1.5 Statistical plan, tests, and power

**(i) McNemar — two contrasts, paired binary compliance-pass:**
- *Contract-A vs Contract-B* (the causal test): for each factor F, pool matched pairs that differ only in F (e.g., CW vs CCW holding the other three fixed), per model. Discordant cells `b,c`; statistic `(|b−c|−1)²/(b+c)` (continuity-corrected), exact binomial for small `b+c`. Report per factor per model.
- *Control vs Trap* (regime effect): matched pairs within `physics_id`-matched Control/Trap analogues in MAIN suite.

**Power (McNemar):** target = detect odds ratio ψ≥2 on discordant pairs at α=0.05, 80% power. With expected discordance π_d≈0.30 and 2:1 asymmetry (p₁₀=0.20, p₀₁=0.10), `n_pairs = 200 → E[discordant] ≈ 60 → power ≈ 0.80`. Hence **N_core = 150 anchors × (each factor contrast appears in 8 of 16 cells) ⇒ ≥600 within-model pairs per factor** — comfortably >0.9 power for ψ≥2, and ~0.8 for ψ≈1.5. State target explicitly: **powered to detect a ≥15 pp compliance swing per factor at 80%.**

**(ii) Cluster bootstrap CIs on within-model differences:** resample `physics_id` clusters with replacement (preserves pairing), B=10,000, percentile CI on Δ = pass(level₁) − pass(level₂) per model per factor. Report Δ ± 95% CI on every factor bar in the headline figure.

**(iii) Mixed-effects logistic (the population model):**
```
compliance_pass_ij ~ mesh_CCW + PSC_inverted + ref_B + naming2 + method_KCL + trap
                     + (1 | physics_id) + (1 + mesh_CCW + PSC_inverted | model)
```
Fit via `pymer4`/`lme4` (rpy2) or `statsmodels.BinomialBayesMixedGLM`. Fixed-effect odds ratios = each factor's average causal effect on compliance; the **by-model random slopes** on `mesh_CCW`/`PSC_inverted` give a *per-model Convention-Blindness susceptibility* — the quantitative object v1 lacked. With CAUSAL (b) alone: 150 × 16 × 6 ≈ 14,400 obs → factor SEs ≈ ±0.03 log-odds. Report ORs + Wald CIs + likelihood-ratio tests vs nested models.

**(iv) MAIN-suite model-ranking power (honesty patch for v1's #1 weakness):** at N=1,000 subtasks/model, McNemar model-vs-model detects **≥5 pp** differences at 80%; sub-2 pp gaps (GPT-5 66% vs Opus 65%) remain within noise **even at N=1,000**. v2 states this outright and reframes the headline from "GPT-5 > Opus" to "top models are statistically indistinguishable on competence; they separate on the *compliance* axis, which the factorial resolves." This turns the underpowering critique into a designed finding.

**Target N summary (T1):** N_gold=40 (10 models, 32 cells), N_core=150 (6 models, 16 cells), N_ext=300 (OA screen). Total CAUSAL calls ≈ 40·32·10 + 150·16·6 + 300·2·6 ≈ 12.8k + 14.4k + 3.6k ≈ **31k calls**, all local/free on M5.

---

## 2. Pillar 2 — Rule-Based Deterministic Compliance Grader (T2)

A pure-Python module `compliance_grader.py` that consumes a solver response + the instance's `expected_under_contract` / `expected_under_default` and emits deterministic labels. **No LLM touches the compliance axis.**

### 2.1 `sign_check(pred, symbol, instance)`

```python
TAU = 0.05          # hybrid tolerance (matches v1: abs<1e-5 OR rel<5%)
EPS_ZERO = 0.02     # |pred| below this * |expected_scale| => sign ambiguous

def sign_check(pred, symbol, inst):
    e_dec = inst.gt.expected_under_contract[symbol]
    e_def = inst.gt.expected_under_default[symbol]
    scale = max(abs(e_dec), abs(e_def), 1e-9)

    mag_match = (abs(abs(pred) - abs(e_dec)) < 1e-9) or (abs(abs(pred)-abs(e_dec))/(abs(e_dec)+1e-9) < TAU)
    if not mag_match:
        return "COMPETENCE_FALLTHROUGH"      # wrong magnitude ⇒ not a sign issue; defer to judge
    if abs(pred) < EPS_ZERO * scale:
        return "SIGN_AMBIGUOUS"              # true-zero variable; excluded from sign scoring

    s_pred, s_dec, s_def = sign(pred), sign(e_dec), sign(e_def)
    if s_pred == s_dec:                       return "COMPLIANT"
    if s_dec != s_def and s_pred == s_def:    return "CONVENTION_BLIND"   # matched prior, ignored contract
    return "SIGN_INCOHERENT"                  # matches neither
```

Only variables where `s_dec != s_def` (the contract actually flips the sign vs default) are **diagnostic** for Convention Blindness; the grader tags those as `diagnostic=True`. This is the deterministic upgrade over v1's coarse `ERR_SIGN` (which only checked "|pred|≈|truth| but value differs" against the single fixed frame).

### 2.2 `method_check(response, required_method)`

Deterministic structural classifier over the response text (works on visible output; on local models also over the `<think>` trace):

```python
KVL_SIG = [r"\bmesh\b", r"\bKVL\b", r"loop", r"around the (loop|mesh)",
           r"[Rr]\d*\s*\*\s*\(?\s*i", r"\bi[_ ]?\d\b.*clockwise", r"sum of (voltage|volt) drops"]
KCL_SIG = [r"\bnodal?\b", r"\bKCL\b", r"at node", r"\(v[_a-z0-9]+\s*-\s*v", r"/\s*R", r"sum of currents"]

def method_check(resp, required):
    kvl = sum(bool(re.search(p, resp, re.I)) for p in KVL_SIG)
    kcl = sum(bool(re.search(p, resp, re.I)) for p in KCL_SIG)
    used = ("KVL" if kvl>=2 and kvl>kcl else
            "KCL" if kcl>=2 and kcl>kvl else
            "MIXED" if kvl>=2 and kcl>=2 else "UNKNOWN")
    violated = (used not in (required, "UNKNOWN")) and (used != "MIXED" or required not in (used,))
    return {"method_used": used, "violated": violated, "kvl_hits": kvl, "kcl_hits": kcl}
```
Tuned so `UNKNOWN` never *forces* a violation (conservative — a violation must be positively evidenced). The threshold (`≥2` signatures) and regex set are frozen after calibration against the v1 logs (§2.5).

### 2.3 `convention_acknowledgment(response, contract)`

Boolean per factor — did the reasoning restate the declared contract token? Feeds both compliance context and the T6 taxonomy:

```python
ACK = {
 "mesh_direction": {"CCW":[r"counter-?clockwise", r"\bCCW\b", r"anti-?clockwise"], "CW":[r"clockwise", r"\bCW\b"]},
 "reference_node": {"B":[r"reference (node )?B", r"ground(ed)? at node\s*"+node_B_re, r"node\s*"+node_B_re+r"\s*=\s*0"]},
 "passive_sign_convention": {"inverted":[r"current (leaves|exits).*positive", r"active sign", r"inverted (sign|PSC)"]},
 "naming_scheme": {"scheme2":[re.escape(sym) for sym in contract.declared_symbols]},
}
def convention_acknowledgment(resp, contract):
    return {f: any(re.search(p, resp, re.I) for p in ACK[f][getattr(contract,f)])
            for f in ACK if getattr(contract,f) in ACK[f]}
```

### 2.4 Decision tree → deterministic error labels

Per subtask, aggregate over the diagnostic variables:

```
for each output symbol:
    r = sign_check(...)
collect signs = {r per diagnostic symbol};  m = method_check(...)

if m.violated:                       → ERR_METHOD_VIOLATION           (compliance)
elif all diagnostic signs COMPLIANT and all magnitudes match:
     if any non-diagnostic magnitude wrong → COMPETENCE_FALLTHROUGH → (judge)
     else                                  → PASS
elif ≥1 sign == CONVENTION_BLIND and magnitudes match:
                                     → ERR_SIGN_CONVENTION (subtype=prior_override)   (compliance)
elif ≥1 sign == SIGN_INCOHERENT and magnitudes match:
                                     → ERR_SIGN_CONVENTION (subtype=incoherent)       (compliance)
elif any magnitude wrong:            → COMPETENCE_FALLTHROUGH → (LLM judge, competence only)
```

**Composition with the LLM judge:** the judge is invoked **only** on `COMPETENCE_FALLTHROUGH` rows, and its label space is **restricted to** `{ERR_PHYSICS_SETUP, ERR_CALCULATION, ERR_HALLUCINATION}` — it can no longer emit SIGN or METHOD. Result: the compliance/competence dichotomy that carries the paper's thesis is 100% deterministic; the judge only sub-divides the competence bucket, where mislabeling doesn't threaten the headline.

### 2.5 Validation artifact (headline credibility result)

Re-grade the **existing 500 v1 log rows** (all DEFAULT contract, so `expected_under_contract == expected_under_default`; the CONVENTION_BLIND branch is inert and sign errors reduce to magnitude-match-with-flipped-sign, exactly what v1's ERR_SIGN detected — but now derived from the signed frame, not a heuristic). Then:

1. **Rule-vs-judge confusion matrix** on the shared labels {SIGN_CONVENTION, METHOD_VIOLATION, COMPETENCE} — deterministic grader (rows) × GPT-5 judge (cols).
2. **Cohen's κ** on the compliance-vs-competence dichotomy and on SIGN specifically. Target: κ ≥ 0.8 (v1's judge-vs-judge audit was κ≈0.57; beating that with a *deterministic* grader is the credibility win).
3. **Adjudicated disagreements:** for every off-diagonal cell, the deterministic label is provably correct by construction (signed truth + tolerance); tabulate the judge's error rate. This flips the reviewer critique "your dichotomy rests on a κ≈0.57 judge" into "our dichotomy is deterministic and we *measured* the old judge's error against it."

Test suite: `test_grader.py` with hand-built fixtures for each branch (compliant, prior-override, incoherent, method-violation, zero-variable, magnitude-fail) and a property test asserting `sign_check` is invariant to which contract cell produced a given `(pred, expected)` pair.

---

## 3. Pillar 3 — Procedural Generator (T3/T8)

Refactor the template-locked `gen_spice_probN()` functions into a **`TopologySpec`** abstraction. One spec per topology; the sampler, netlist emitter, SymPy solver, and role ontology all derive from it.

### 3.1 `TopologySpec`

```python
@dataclass
class ElementSlot:
    name: str; kind: str                     # "R" | "Vsrc" | "Isrc" | "VCVS" | "CCCS"
    nodes: tuple                             # (n_plus, n_minus) canonical orientation
    dist: Callable                           # sampler, e.g. loguniform(1e2, 1e5)
    control: Optional[str] = None            # for dependent sources

@dataclass
class TopologySpec:
    name: str
    nodes: list                              # incl. "0" (canonical ground = ref A)
    elements: list[ElementSlot]
    ref_node_B: str                          # alternate reference for the ref-node factor
    outputs: dict                            # symbol -> {role, binding}; MUST span 4 roles
    naming_schemes: dict                     # scheme1/scheme2 -> {symbol: physical_quantity}
    trap_predicates: list[Callable]          # programmatic regime tags (see 3.3)
```

The five v1 topologies port directly (Supermesh, Opposing-T, Wheatstone, Ladder, VCVS); each gains a `branch_current` and `element_voltage` output so all four factors have a handle (§1.1).

### 3.2 Parameter distributions

- Resistors: `loguniform(1e2, 1e5)` Ω (spans the divider regimes; log scale so R-ratios are uniform in log).
- Independent V sources: `uniform(-100, 100)` V, **sign allowed** (drives sign-flip Traps).
- Independent I sources: `uniform(-10, 10)` mA, sign allowed.
- Dependent-source gains: `uniform(-4, 4)` (spans dominance regimes for VCVS/CCCS).
- Rounding: snap to 3 sig-figs to keep prompts clean and enable the contamination hash.

### 3.3 Regime tagging **by code**, not by hand

The core T3 fix: `TRAP` is a *computed predicate on the solved instance*, never a human label. After solving:

```python
def tag_regime(sol, values):
    p = {
      "dominant_current_negative": sign(sol.dominant_mesh_current) < 0,      # violates CW intuition
      "max_r_ratio": max(R)/min(R),                                          # extreme divider
      "near_cancellation": abs(sol.net_source_current) < 0.05*max_source,    # opposing-source cancel
      "dependent_dominates": abs(sol.dep_contribution) > abs(sol.indep_contribution),
      "sign_flip_vs_default": any(sign(e_contract)!=sign(e_default) for e in outputs),
    }
    is_trap = p["dominant_current_negative"] or p["max_r_ratio"]>100 \
              or p["near_cancellation"] or p["dependent_dominates"]
    return {"class":"TRAP" if is_trap else "CONTROL", "predicates":p,
            "tags":[k for k,v in p.items() if v is True]}
```
Rejection-sample to hit a target Control:Trap ratio (v1 was 26:24; keep ≈1:1). Because Trap is now a reproducible function of `values`, the "Traps only vary parameters, not conventions" critique is answered structurally, and Trap difficulty becomes a *continuous* covariate (`max_r_ratio`) in the mixed model.

### 3.4 Dual verification + contamination guard

```python
def build_instance(spec, rng):
    values = {e.name: e.dist(rng) for e in spec.elements}
    sym = sympy_solve_MNA(spec, values)            # analytic, exact rationals -> floats
    spice = ngspice_op(emit_netlist(spec, values)) # .op, ALL node potentials + all sense currents
    assert agree(sym, spice, rel=1e-4), "dual-verify mismatch"   # guards generator/solver bugs
    cf = canonical_frame(sym)                       # full node_potentials + branch_currents
    inst = assemble(spec, values, cf, regime=tag_regime(sym, values))
    inst.provenance.instance_hash = sha256(canonical_signature(spec.name, round_sig(values,3)))
    return inst
```

- **SymPy** builds Modified Nodal Analysis symbolically and solves exactly (dependent sources included), the analytic leg; **NGSPICE** `.op` is the numeric leg. Instance rejected if they disagree >1e-4 rel. (This generalizes v1's `verify_and_export_json.py`, which already cross-checks SPICE vs the stored truth — v2 makes SymPy a first-class solver, not just a checker.)
- **Netlist change (required for T1/ref-node):** emit `.print op v(<every node>) i(<every sense>)` so `canonical_frame.node_potentials` is complete — the current netlists print only the two output nodes, which is insufficient to remap the reference node.
- **Frozen splits + seed:** `numpy.random.Generator(PCG64(seed))`; emit `train/dev/test/causal` JSONL, splits disjoint by `instance_hash`.
- **Contamination guard:** (a) dedupe by `instance_hash` across splits and against a manifest of v1's 50 instances; (b) inject a per-release `canary` GUID string so future models' pretraining exposure is detectable; (c) publish the hash manifest so reviewers can verify no test instance leaked into any released artifact. Numeric values are novel/random (not textbook), reducing prior memorization.

---

## 4. Pillar 4 — Mechanistic Trace Analysis (T6)

Turns "Convention Blindness" from a label into a **measured failure-locus distribution** per model. Applies to every subtask the deterministic grader flagged `ERR_SIGN_CONVENTION` (and, for coverage, to compliant ones as a control).

### 4.1 Taxonomy (four loci)

| Locus | Operational signature (deterministic inputs) |
|---|---|
| **never_mentioned** | `convention_acknowledgment[F] == False` AND sign wrong on factor-F-diagnostic vars |
| **mentioned_then_ignored** | `ack[F] == True` AND all F-diagnostic signs == `CONVENTION_BLIND` (coherently matched the *default*) |
| **mentioned_then_misapplied** | `ack[F] == True` AND signs == `SIGN_INCOHERENT` (attempted, matched neither) |
| **arithmetic_sign_slip** | magnitudes all correct AND exactly **one** variable's sign wrong, incoherent with any *global* contract flip (isolated, not systematic) |

### 4.2 Classifier

Primarily deterministic — it consumes only `convention_acknowledgment` flags (§2.3) × the `sign_check` pattern (coherent-flip vs single-var vs incoherent) × magnitude match. The **one genuinely ambiguous decision** is *ignored* vs *misapplied* when acknowledgment is true but the sign pattern is partially coherent; here an LLM judge is used **as a tie-breaker only**, and we report inter-rater κ **on that sub-decision alone** (not on the headline). Everything else is rule-derived, so the taxonomy does not re-import judge dependence.

```python
def classify_locus(subtask):
    F = diagnostic_factor(subtask)                 # the factor whose sign the contract flipped
    ack = subtask.ack[F]; pat = sign_pattern(subtask)   # COHERENT_DEFAULT | INCOHERENT | SINGLE_SLIP
    if pat == "SINGLE_SLIP" and subtask.mags_ok:   return "arithmetic_sign_slip"
    if not ack:                                    return "never_mentioned"
    if pat == "COHERENT_DEFAULT":                  return "mentioned_then_ignored"
    if pat == "INCOHERENT":                        return "mentioned_then_misapplied"
    return judge_tiebreak(subtask)                 # rare; report κ on this subset
```

### 4.3 What it lets you claim, per model

For each model, a normalized 4-way distribution over loci, cut by factor and by scale/reasoning axis. This supports **mechanistic** claims v1 could not make, e.g.:

- *"Model X's convention failures are 78% mentioned-then-ignored — it restates 'use CCW' then reports the CW answer — whereas Model Y is 61% never-mentioned: it fails to encode the constraint at all."* Different interventions follow (X needs a self-verify/enforcement step; Y needs the constraint surfaced).
- Tied to the **natural experiments:** does reasoning-SFT (R1-Distill-Llama-70B vs Llama-3.3-70B) shift mass from *never_mentioned* → *mentioned_then_ignored* (i.e., the model now *notices* the rule but still discards it)? This is a clean, quantified mechanistic result and directly rides the H1-2026 "thinking regresses on constraint-following" wave.
- **Data source note:** on local models we capture the full `<think>` trace, so acknowledgment detection is high-recall; on v1 API logs only visible output exists, so T6 on v1 is reported as a lower-bound. State this limitation explicitly.

---

## 5. Consolidated targets, tests, and build order

| Item | Target N / spec | Test / acceptance gate |
|---|---|---|
| MAIN power suite | ≥500 physics × 2 methods × 10 models | McNemar powered for ≥5 pp model gaps; report indistinguishability of top pair |
| CAUSAL golden | 40 anchors × 32 cells × 10 models | all main effects + 2-way interactions estimable |
| CAUSAL fractional | 150 anchors × 16 cells × 6 models | ≥600 within-model pairs/factor; ≥0.8 power at ψ=1.5 |
| CAUSAL OA screen | 300 anchors, orthogonal-array 1 cell each | balanced marginal factor estimates |
| Mixed-effects logistic | ≈14k+ obs | per-factor OR ± Wald CI; by-model random slopes converge |
| Deterministic grader | 100% of compliance labels | κ ≥ 0.8 vs v1 judge on 500 re-graded rows; unit tests all branches |
| Generator | 5 topologies, dual-verified | SymPy↔NGSPICE agree rel<1e-4 on 100% of accepted instances; hash-disjoint splits |
| Trace taxonomy | all ERR_SIGN_CONVENTION rows | ≥90% deterministically classified; κ reported on the judge-tiebreak subset only |

**Build order (maps to the M5 timeline):** (1) generator + SymPy solver + full-potential netlists + dual-verify CI → (2) schema v2 + `expected_under_contract/default` precompute → (3) deterministic grader + re-grade v1 logs (the κ≥0.8 credibility result lands *before* any new runs) → (4) MAIN sweep → (5) CAUSAL sweep + mixed model → (6) trace taxonomy. Steps 1–3 are pure-CPU and produce a citable result with zero model inference, de-risking the schedule.

**Load-bearing decisions an engineer must not skip:** (a) outputs must span all four variable roles per instance or factors have no handle; (b) netlists must print the full node-potential vector or reference-node remap is impossible; (c) the judge is hard-restricted to competence labels — the compliance dichotomy must never call an LLM; (d) `expected_under_default` must be stored alongside `expected_under_contract`, because the *gap* between them is the operational definition of Convention Blindness and the input to the entire T6 taxonomy.

**Files to modify/add:** `scripts/ngspice_circuit_generator.py` → `generator/topology_spec.py` + `generator/sample.py` + `generator/sympy_mna.py`; `scripts/verify_and_export_json.py` → `generator/dual_verify.py` (SymPy promoted to solver); new `grading/compliance_grader.py`, `grading/trace_taxonomy.py`, `analysis/stats.py` (McNemar/bootstrap/mixed-model); schema doc `SCHEMA_v2.md`. All backward-compatible with the 50 v1 instances and 500 v1 log rows.