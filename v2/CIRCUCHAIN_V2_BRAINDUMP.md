# CircuChain v2 — Definitive Internal Strategy (Brain-Dump)

**Author:** Mayank Ravishankara · **Date:** 2026-07-09 · **Status:** the single document to build from · **Repo:** `/Users/mayankgowda/CircuChain-Benchmark`

---

> ### ✅ STATUS UPDATE (2026-07-09) — GNG-1 ALREADY PASSED, before any new inference
>
> The Week-3 credibility checkpoint is **already green**. The deterministic rule-based compliance
> grader (`v2/circuchain/grade/compliance.py`) was built and run on the frozen 500 v1 log rows
> (`v2/scripts/regrade_v1_logs.py`, reproducible in ~2 s, CPU-only):
>
> - **Rule-vs-judge Cohen's κ = 0.944** (3-way) / **0.866** (compliance-vs-competence among failures),
>   vs v1's judge-audit κ ≈ 0.57. Agreement 96.6%. **Target was ≥ 0.80 → cleared decisively.**
> - **The Compliance–Competence Trade-off survives deterministic grading and sharpens:**
>   GPT-5 = 34% compliance / **0%** competence error; Opus 4.5 = 2% compliance / 33% competence; o4-mini = 24% / 19%.
> - **The #1 reviewer blocker is pre-answered by data:** within the *magnitude-correct* subset (physics solved),
>   GPT-5 is sign-compliant only **66%** of the time vs Opus **97%** and o4-mini **70%**. The compliance
>   gradient exists *inside* the competent set — it is not an artifact of a competence gate.
>
> Interpretation: the single most attackable number in v1 (a κ≈0.57 judge carrying the headline) is
> replaced by a deterministic grader that reproduces the judge at κ≈0.94, and the thesis holds. The
> whole v2 is de-risked at the design stage. One honest caveat: the v1 *predictions* were parsed by a
> GPT-4o extractor (a weak, near-deterministic dependence that §4.2 replaces with a regex extractor).
> Full numbers: `v2/results/regrade_v1/regrade_summary.json`.

---

## 1. TL;DR and VERDICT

**GO — narrowed and reframed.** Build one **standalone causal paper** on the v1 repo — reuse the infrastructure (SymPy/NGSPICE dual verifier, 5 topologies, async runner ≈ 2–3 months of sunk engineering), **discard the "v2 of a preprint" framing**. Scope is the causal core: **T1 (causal convention-contract manipulation) + T2 (procedural generator, N≥500) + T3 (10-model open-weights panel) + T4 (deterministic rule-based compliance grader) + T6 (deterministic reasoning-trace taxonomy)**, plus **T9 (cross-domain statics probe) if a week of slack survives**. Everything runs **free and fully reproducibly on a local Apple M5 Max (128 GB)** — that constraint is the paper's single biggest differentiating asset, not a limitation. **Primary venue: TMLR** (rolling, affiliation-blind, artifact-rewarding — structurally built for an unbranded independent, ~55–70% conversion on a solid submission). **Stretch: ICLR 2027** (abstract Sep 19 / paper **Sep 24, 2026**) behind a hard **Sep-10 quality gate**. Cut all mitigation/SFT/domain-expansion (T5, T7, T11) to a 2027 expanded version. Expected value: **~85% chance of a peer-reviewed, citable publication + a used open artifact within 9 months** via the TMLR backstop — a real O-1 "brick" for ~4 months of zero-dollar local work.

**One-sentence thesis of v2:** *Convention Blindness — an LLM overriding an explicit, machine-checkable user convention in favor of its training prior — is a **causally-identifiable, per-factor-quantifiable, deterministically-graded** failure mode that is **distinct from both physical-reasoning competence and generic instruction-following** and **recurs across domains**, demonstrated at statistical power entirely on free, reproducible, open-weights local compute.*

**The one non-negotiable:** scope discipline. The moment T5-SFT, T7-AC/op-amp, or human audits get pulled into *this* cycle, the timeline blows past the ICLR window and the marginal standing-per-week collapses. This is the only path to NO-GO.

---

## 2. THE v2 THESIS AND POSITIONING

### 2.1 How v2 reframes v1

v1 was a **diagnostic observation** on N=100 with an LLM judge at κ≈0.57: "GPT-5 has ~0% competence / 34% compliance error; Opus has 7% compliance / 28% competence — there's a trade-off." Three fatal, reviewer-obvious weaknesses: underpowered (66% vs 65% CIs overlap completely), judge-dependent, and — most damning — **Convention Blindness was never tested causally** (Traps varied *parameters*, never the *convention contract itself*).

v2 converts each weakness into a designed strength:

| v1 weakness | v2 move | What it buys |
|---|---|---|
| N=100, no separation | Procedural generator, **N≥500 physics × 2 methods**, paired McNemar | Powered to detect ≥5 pp model gaps; the top-pair *indistinguishability* becomes a **designed finding**, not a failure |
| LLM judge κ≈0.57 carries the dichotomy | **Deterministic rule-based grader**: compliance never touches an LLM | Kills the judge-dependence critique; produces a κ≥0.8-vs-judge credibility result *before any inference* |
| Convention Blindness never causal | **T1: same physics, varied contract** (mesh dir, PSC, ref node, naming, method) as a factorial/fractional design | The unclaimed whitespace; per-factor causal odds ratios v1 could not compute |
| Cross-vendor leaderboard (confounded) | **Controlled contrasts**: same-base ±reasoning-SFT; within-family scale ladder | *Causal* attribution of the trade-off, not correlation |

The narrative arc: **from "we observed a trade-off in 5 closed models" → "we causally isolate which convention factors each model violates, prove it is not a scoring artifact or generic instruction-following, and show it is a model-level trait that generalizes beyond circuits — on a fully open, reproducible pipeline."**

### 2.2 The whitespace it claims

The niche is **still open** (core-thesis scoop risk **2.5/5**), sitting at an unclaimed intersection of three converging-but-not-yet-arrived literatures:
1. **Circuit benchmarks** (CIRCUIT, MMCircuitEval, AMSbench, **2512.10159**) optimize *answer/design accuracy*, never rule-obedience.
2. **Instruction-following / reasoning-regression** (IFEval, ConInstruct, "Format Tax," "When Built-in Thinking Helps and Hurts") is *domain-agnostic* and never grounds in a domain where obeying the instruction **flips the correct number's sign**.
3. **Causal-faithfulness** (RFEval) intervenes on the *reasoning trace*, not on the *constraint*.

**CircuChain's defensible position is the intersection:** a domain with a *machine-checkable, sign-carrying ground truth* + a *causally-manipulable convention contract* + a *deterministic compliance grader*. **Plant the flag on T1 + T9.** The most dangerous near-neighbor — **arXiv 2512.10159** (Gemini 2.5 Pro + ngspice loop, which independently names "incorrect current-direction assumptions") — is a *single-model accuracy engine*, not a diagnostic benchmark; the differentiation paragraph must be pre-written (see §6).

### 2.3 Open-source-on-M5 as strategic asset (lead with this in the abstract)

Reframe local compute as **three genuine strengths**, never apologize for it:
1. **Zero-cost scale:** N≥500 × 10 models × k repeats would cost thousands via API and hit rate limits. Locally it's free and unlimited — *this is why v2 can afford the statistical power that kills v1's #1 critique.* A branded lab paying per-token often can't be bothered.
2. **Reproducibility receipt:** full weight-SHA + seed + `<think>`-trace provenance, cross-checked on **two engines (MLX + llama.cpp/GGUF)**. Exactly what TMLR and NeurIPS-ED reward and what a closed-API paper *cannot* offer.
3. **Open-weights-only natural experiments:** `Llama-3.3-70B` vs its `R1-Distill-Llama-70B` (same base, ±reasoning-SFT) and the Qwen3.5 think-on/off scale ladder are **controlled causal contrasts you physically cannot run on closed APIs.** The constraint hands you a *stronger causal design* than v1's cross-vendor leaderboard. **Put this in the abstract.**

---

## 3. WHAT IS NEW vs v1

Scope for **this cycle** is the causal core. The red-team (§6) surfaced three design-hardening items that are cheap but **existential to the thesis** — they are promoted to MUST-HAVE and marked ★.

| Tag | Addition | Scope | One-line scientific payoff |
|---|---|---|---|
| **T2** | Procedural generator (`TopologySpec`), N≥500, dual-verified, regime tags *by code* | **MUST** | Statistical power; "Trap" becomes a reproducible predicate on `values`, not a hand label |
| **T4** | Deterministic rule-based compliance grader (contract-derived signed expected value) | **MUST** | Kills judge-dependence; compliance dichotomy is 100% deterministic |
| **T1** | Causal convention-contract manipulation (5 factors, factorial + fractional + OA) | **MUST** | The unclaimed whitespace; per-factor causal ORs — the ICLR-caliber claim |
| **T3** | 10-model local open-weights panel, reasoning/base axis, 2 natural experiments | **MUST** | Controlled causal contrasts; free scale on M5 |
| **T6** | Deterministic reasoning-trace taxonomy (never-mentioned / mentioned-then-ignored / -misapplied / arithmetic-slip) | **MUST** | Turns "Convention Blindness" from a label into a measured failure-locus distribution per model |
| **★H1** | **Joint 2×2 (magnitude-correct × sign-compliant) reporting per model** | **MUST (new)** | Neutralizes the grader's magnitude-gate confound — the #1 reviewer blocker |
| **★H2** | **Capability-floor transform check** (isolated "convert i₂ CW→CCW") + **instructed-vs-uninstructed** same-physics control | **MUST (new)** | Proves the compliance axis measures *disobedience*, not arithmetic difficulty or convention-unfamiliarity |
| **★H3** | **Discriminant-validity slice** (generic IFEval-style compliance vs convention compliance) | **MUST-lite (new)** | Proves "convention compliance" *dissociates* from generic instruction-following (not ρ≈0.9 redundant) |
| **T9** | Cross-domain statics free-body probe (~40 instances, same grader) | **NICE → promote if slack** | Converts "circuits benchmark" → "general LLM trait"; insulates against a circuits-only scooper |
| **Tier-C** | Closed frontier ceiling (GPT-5.5/5.6, Opus 4.8, Gemini 3.x), ~$150–300 | **NICE** | v1 lineage continuity; "does the trade-off survive frontier scale?" — generalization only, never a headline number |
| T5 | Mitigation toolkit (verifier-loop C4, restate C1, LoRA SFT) | **CUT → 2027** | Prescription; verifier-loop partially pre-empted by 2512.10159 |
| T7 | AC/phasor + op-amp domain surfaces | **CUT → 2027** | New convention surfaces (j-sign, virtual-short) |
| T11 | Convention-aware fine-tuned checkpoint | **CUT → 2027** | The released-checkpoint recipe |

**Explicitly cut from both timeline tracks this cycle:** T5-SFT, constrained decoding, op-amp, AC/phasor, human-expert audit, Tier-B open-frontier API. These *are* the NeurIPS-2027 expanded version.

---

## 4. EXPERIMENTAL DESIGN

*Full engineering specs live in the B1/B3 appendices; this is the committed, concrete core. Schema is additive and backward-compatible with all 50 v1 instances + 500 v1 log rows.*

### 4.1 T1 — Causal convention-contract manipulation

**Five orthogonal factors, each acting on a disjoint variable-role set** (this orthogonality is the scientific heart — each factor's marginal effect on compliance is identifiable without confounding):

| Factor | Levels | Sign-action |
|---|---|---|
| `mesh_direction` | CW / CCW | ×(−1) on `mesh_current` roles |
| `passive_sign_convention` | standard / inverted | ×(−1) on `branch_current`, `element_voltage` |
| `reference_node` | A / B | **affine** `V'(n)=V(n)−V(B)` on `node_voltage` (changes magnitude too) |
| `naming_scheme` | scheme1 / scheme2 | permute label→quantity |
| `required_method` | KVL / KCL | procedure only, no numeric action (graded structurally) |

**Ground truth computed once** in a canonical frame R0; every contract's expected signed answer is a **pure function** (no re-simulation). The generator freezes both `expected_under_contract` and `expected_under_default` per instance — **the gap between them is the operational definition of Convention Blindness** and the input to the entire T6 taxonomy.

**Load-bearing schema requirements (an engineer must not skip):**
- Every CAUSAL instance must expose **≥1 variable of each of the four roles** (`mesh_current`, `branch_current`, `node_voltage`, `element_voltage`) or a factor has no handle → each v1 topology gains a `branch_current` + `element_voltage` output.
- NGSPICE netlists must `.print` the **full node-potential vector** (not just the two output nodes) or reference-node remap is impossible.

**Design (three-part, to keep compute sane):**
- **(a) GOLDEN full factorial:** `N_gold=40` anchors × **32 cells** (2⁴ sign factors × 2 methods) = 1,280 calls/model, full 10-model panel → all main effects + 2-way interactions.
- **(b) CAUSAL fractional:** `N_core=150` anchors × **2⁴⁻¹ res-IV** (D=ABC, 8 cells) × 2 methods = 16 cells → 2,400 calls/model, **6-model causal panel** (incl. both natural experiments) → ≥600 within-model pairs/factor.
- **(c) OA screen:** `N_ext=300` anchors via balanced orthogonal array OA(16,4,2,2), 1 cell/anchor → variance-balanced population marginals cheaply.

Unit of pairing = `physics_id`: every factor contrast is a **within-physics, within-model matched pair.**

### 4.2 T4 — Deterministic compliance grader (`grade/compliance.py`)

Because we compute both the contract-correct and the default-prior answer, sign-compliance is a **table lookup**, not an LLM judgment:

```
sign_check(pred, symbol, inst):
  mag_match within TAU=0.05?  no → COMPETENCE_FALLTHROUGH (defer to judge, competence only)
  |pred| < EPS_ZERO·scale?         → SIGN_AMBIGUOUS (true-zero var, excluded)
  sign(pred)==sign(expected_contract)                       → COMPLIANT
  sign(expected_contract)≠sign(default) & pred matches default → CONVENTION_BLIND  (prior override)
  else                                                       → SIGN_INCOHERENT
```

Only variables where `sign(contract)≠sign(default)` are **diagnostic**. Method-compliance via a conservative structural classifier (`UNKNOWN` never forces a violation). **The LLM judge is hard-restricted to `{PHYSICS, CALC, HALLUC}` on `COMPETENCE_FALLTHROUGH` rows only — it can never emit SIGN or METHOD.** The compliance/competence dichotomy that carries the thesis is 100% deterministic.

**★ Grader-hardening (the #1 blocker fix):** the naïve pipeline can *manufacture* "competence↑ → compliance-error↑" because a variable is only sign-eligible **after** clearing the magnitude gate — competent models have a larger sign-eligible pool. **Mandatory mitigation: report the full 2×2 joint (magnitude-correct × sign-compliant) per model, pre-register the denominator, and demonstrate the compliance gradient exists *within the magnitude-correct subset* and is not explained by magnitude-pass-rate.** Exclude genuine-null variables by a *physics* criterion, not the `EPS_ZERO` threshold.

**Validation artifact (credibility result, lands before any new inference) — ✅ DONE 2026-07-09, κ=0.944 (see status box at top):** re-grade the **500 v1 log rows** (all DEFAULT contract → `CONVENTION_BLIND` branch inert, reduces to signed-frame magnitude-match). Produce rule-vs-judge confusion matrix + **Cohen's κ (target ≥0.8 vs v1's judge-vs-judge κ≈0.57)** + hand-audited adjudicated error table for every off-diagonal cell (~60 ERR_SIGN + 4 METHOD rows — cheap). This flips "your dichotomy rests on a κ≈0.57 judge" into "our dichotomy is deterministic and we *measured* the old judge's error against it." **Caveat to state plainly:** this validates the grader on the regime where its headline branch never fires; the v2 panel gets a **human audit of ≥200 stratified rows across all families** with per-family precision/recall for sign/method/ack labels.

### 4.3 T3 — Procedural generator (`generator/`)

Refactor template-locked `gen_spice_probN()` into a `TopologySpec` abstraction (5 v1 topologies port directly + gain `branch_current`/`element_voltage` outputs). Parameters: resistors `loguniform(1e2,1e5)`Ω; V-sources `uniform(−100,100)`V (sign allowed, drives sign-flip Traps); I-sources `uniform(−10,10)`mA; dependent gains `uniform(−4,4)`; snap to 3 sig-figs. **Regime tagging by code** (`dominant_current_negative`, `max_r_ratio>100`, `near_cancellation`, `dependent_dominates`), rejection-sampled to ~1:1 Control:Trap. **Dual-verify** every instance: SymPy MNA (exact rationals, source of truth) vs NGSPICE `.op` (reject if rel>1e-4). Contamination guard: `instance_hash` dedupe across splits + against v1's 50-instance manifest, per-release canary GUID, published hash manifest, **test split held unreleased at submission**.

### 4.4 T6 — Mechanistic trace taxonomy

Primarily deterministic — consumes `convention_acknowledgment` flags × `sign_check` pattern × magnitude match:

| Locus | Signature |
|---|---|
| `never_mentioned` | ack[F]=False AND sign wrong on F-diagnostic vars |
| `mentioned_then_ignored` | ack[F]=True AND all F-signs = CONVENTION_BLIND (coherently matched *default*) |
| `mentioned_then_misapplied` | ack[F]=True AND signs = SIGN_INCOHERENT |
| `arithmetic_sign_slip` | magnitudes correct AND exactly one var's sign wrong, not systematic |

The single ambiguous decision (ignored vs misapplied under partial coherence) uses the LLM judge **as a tie-break only**; report κ on that sub-decision alone. Ties to the natural experiments: does reasoning-SFT shift mass `never_mentioned → mentioned_then_ignored` (model now *notices* the rule but still discards it)? On local models the full `<think>` trace is captured (high recall); on v1 API logs T6 is a lower bound — state explicitly.

### 4.5 ★ Construct-validity controls (fold into T1)

The red-team's strongest attack: sign-flips confound compliance with (a) added arithmetic and (b) distance-from-prior/unfamiliarity. **Two cheap controls neutralize it:**
- **Capability-floor transform check:** ask each model the isolated transform ("given i₂=+6 mA under CW, what is it under CCW?"). Can-do-standalone-but-fails-embedded = compliance; can't-do = competence. Report the split per model.
- **Instructed-vs-uninstructed same-physics:** present the identical instance (i) with explicit CCW instruction, (ii) free to choose *and state* its direction. Disobedience is proven only if the model, when free, self-reports CW but, when instructed CCW, still reports CW.
- Enter `n_sign_ops` / `max_r_ratio` as **difficulty covariates** in the mixed model; the compliance effect must survive conditioning on difficulty.

### 4.6 Statistics (pre-registered)

- **McNemar paired** per factor per model (continuity-corrected; exact binomial for small discordant `b+c`), and for Control vs Trap within matched `physics_id`.
- **Cluster bootstrap** (resample `physics_id`, B=10,000) percentile CIs on every factor Δ.
- **Mixed-effects logistic:** `compliance_pass ~ mesh_CCW + PSC_inverted + ref_B + naming2 + method_KCL + trap + n_sign_ops + (1|physics_id) + (1+mesh_CCW+PSC_inverted|model)` → per-factor ORs + by-model random slopes (**per-model susceptibility** — the object v1 lacked).
- **Power:** target detect OR≥2 (≥15 pp compliance swing) at 80%, α=0.05; N_core=150 → ≥600 pairs/factor → >0.9 power at ψ=2, ~0.8 at ψ=1.5. **Pilot-measure discordance first** — the 80% is fictional until π_d is measured.
- **★ Rigor patches from red-team:** FDR/hierarchical correction for the hundreds of tests; **TOST equivalence** (pre-specified margin) for every "top models indistinguishable" claim; **equalize k across the panel or enter k as a covariate** (unequal k confounds the reasoning/base factor); treat model as **fixed effects** for susceptibility read-out (10 clusters is too few for stable random slopes) or expand the panel; report **structural N=5 separately from statistical N≥500** in every power statement.
- **Falsification pre-registered:** Cochran-Armitage trend test across the scale ladder — *if compliance error falls monotonically with both scale and reasoning-tuning, the thesis dies and the paper says so.* The design is explicitly built to catch this.

---

## 5. M5-LOCAL EXECUTION PLAN

### 5.1 Hardware & inference stack

**Target: M5 Max, 40-core GPU, 128 GB (614 GB/s)** — the only config that runs the full scale ladder *and* the sparse-80B/120B tier without swapping. Stack: **MLX-primary** (`mlx-lm`, ~2–3× Ollama decode, only runtime exploiting M5 Neural Accelerators, ~4× faster TTFT vs M4 on prefill-heavy prompts) for the **official numbers**; **Ollama/llama.cpp-GGUF** for convenience, model enumeration, and the **cross-engine reproducibility receipt** (stable file hashes → "headline gaps reproduce on both engines"). Rule: **never put a *dense* large model on the long-CoT path** — sparse MoE at the top (80B-A3B, ~3B active) buys ~70B quality at 3–4× decode speed.

### 5.2 The committed 10-model local panel (Tier A — the causal core)

*🔮 = H1-2026 release, verify checkpoint live before freezing; fallbacks listed.*

| # | Model | Params (tot/act) | Role tag | Contrast |
|---|---|---|---|---|
| 1 | Qwen3.5-2B 🔮 | 2B | `SCALE-L1` | C3 scale ladder |
| 2 | Qwen3.5-4B 🔮 | 4B | `SCALE-L2` | C3 |
| 3 | Qwen3.5-9B 🔮 | 9B | `SCALE-L3` | C3 |
| 4 | Qwen3.5-27B 🔮 | 27B | `SCALE-L4` | C3 |
| 5 | Qwen3-Next-80B-A3B-**Instruct** ✅ | 80B/3B | `REASON-OFF` | **C1** |
| 6 | Qwen3-Next-80B-A3B-**Thinking** ✅ | 80B/3B | `REASON-ON` | **C1** |
| 7 | Llama-3.3-70B-Instruct ✅ | 70B | `BASE-70B` | **C2** |
| 8 | DeepSeek-R1-Distill-Llama-70B ✅ | 70B | `REASON-70B` | **C2** |
| 9 | gpt-oss-20b (MXFP4) ✅ | 21B/3.6B | `REASON-oss` | lineage |
| 10 | Gemma-3-27B-it ✅ | 27B | `BASE-Gemma` | lineage |

**Fallbacks:** scale ladder → Qwen3 dense (1.7B/4B/8B/14B/32B, all ✅); top reasoner → gpt-oss-120b (fits 128 GB) or DeepSeek-R1-Distill-Qwen-32B; no MLX conversion → GGUF/llama.cpp. **Clean contrasts:** C1 (#5 vs #6, same base ± Instruct/Thinking), C2 (#7 vs #8, same base ± R1-SFT, different lineage — rules out "Qwen artifact"), C3 (#1→#4, pure param scaling, dense, one recipe). **Optional Tier-C ceiling** (GPT-5.5/5.6, Opus 4.8, Gemini 3.x, ~$150–300, generalization-only, T6-impossible so excluded from mechanism).

### 5.3 Throughput / wall-clock budget

Work unit = N instances × 2 methods = 2N calls/model. **Output length is the dominant variable** (non-reasoning ~450 tok; reasoning CoT ~3,000, heavy tail to 8k+). MoE-topped 10-model panel at N=500 ≈ **88 GPU-h ≈ 3.7 days** single-stream; **~50–70 h (~2–3 days) with continuous batching**; ~7 days at N=1000. CAUSAL suite ≈ **31k calls** total (~1 week local, $0). **Hard gate:** 20-instance pilot per model *before* the full sweep to measure actual CoT length (a 3k→5k shift inflates every reasoning row ~1.7×); `max_tokens` cap 8k (non-reasoning) / 16k (reasoning) with a per-call **truncation flag** logged (truncation is a data point — constraint-drop under length pressure).

### 5.4 Repo structure (self-contained `v2/` tree; v1 frozen for provenance)

```
v2/
├── pyproject.toml  Makefile  configs/{models,contracts,dataset,run,smoke}.yaml
├── circuchain/
│   ├── schema.py  contract.py            # T1 sign transforms — highest-novelty, get right early
│   ├── topologies/{base,supermesh,opposing_t,wheatstone,ladder,vcvs}.py
│   ├── analytic.py  generate.py  verify.py   # SymPy MNA + dual-verify
│   ├── providers/{base,ollama,mlx,openai_api,anthropic_api}.py
│   ├── cache.py  run.py                  # content-addressed cache, append-only JSONL, RESUMABLE
│   ├── grade/{extract,numeric,compliance,trace,judge}.py
│   └── analyze/{stats,tables,figures}.py
└── tests/{test_contract_transforms,test_analytic_vs_spice,test_compliance_grader,test_extract}.py
```

**CLI:** `circuchain generate | verify | run | grade | analyze | judge`, wired via `Makefile` (`make all`, `make smoke`). **Determinism/resumability (mandatory for multi-day runs):** seeds everywhere (recorded in `run_manifest.json`); content-addressed cache keyed on `sha256(model_key + weight_sha + quant + backend + system + user + genparams)` so a killed run resumes by diffing completed `(instance_id, method)` pairs — no restart-from-zero at hour 50. Provenance sidecar per call (weight SHA-256, quant, lib versions, seed, prompt hash, `<think>` + final answer, tokens, truncation flag, wall-clock). CI smoke-tests 20 instances on both engines per commit.

---

## 6. FEASIBILITY AND RISK

### 6.1 The four reviewer kill-shots and how the plan neutralizes each

*(from the adversarial Reviewer-2 pass — these are folded into the design, not waved away)*

1. **"The compliance metric is conditioned on passing a competence gate → the trade-off is a scoring artifact." (BLOCKER)** → **★H1:** report the full 2×2 joint (magnitude-correct × sign-compliant) per model; pre-register the denominator; prove the compliance gradient exists *within the magnitude-correct subset* and is independent of magnitude-pass-rate. This is analysis, not new experiments — cheap and mandatory.
2. **"Causal panel has no frontier models → 'weak models are weak.'" (BLOCKER as headlined)** → State plainly all causal claims rest on **Tier A (fully controlled/released)**; run **gpt-oss-120b** (fits 128 GB) as the largest honest local point; run the closed trio at **full N on the identical grader** (not N≈100), and pre-register the Cochran-Armitage trend test *including* the frontier. If compliance error declines monotonically with scale, the paper says the thesis is dead — falsification built in.
3. **"Sign-flips confound compliance with arithmetic difficulty and convention-unfamiliarity." (BLOCKER for causal claim)** → **★H2:** capability-floor transform check + instructed-vs-uninstructed same-physics control + `n_sign_ops`/`max_r_ratio` difficulty covariates in the mixed model. The compliance effect must survive conditioning on difficulty.
4. **"'Convention Blindness' is a rename of known prior-vs-instruction override; no proof it's distinct from generic IF." (MAJOR)** → **★H3 discriminant validity:** score every model on a generic IFEval-style slice *and* on convention compliance; show they **dissociate** (low cross-model correlation / models that pass format-IF but fail convention-IF). Reposition the contribution honestly as *"the first causally-identified, deterministically-graded, sign-resolved measurement of prior-vs-instruction override in a domain with machine-checkable ground truth"* — and pre-write the differentiation paragraphs vs **2512.10159** (single-model accuracy engine vs cross-panel diagnostic) and **RFEval** (intervene on trace vs on constraint).

Also address: **regex method/ack family-bias** → human-audit per-family precision/recall; if method-agreement <90%, **demote method to a secondary axis and headline sign-compliance only** (fully deterministic). **Structural N=5** → report separately from statistical N; the `TopologySpec` abstraction makes adding 3–5 topologies cheap if time allows, else bound the claim to "linear DC/AC network analysis."

### 6.2 Top risks + de-risking (the two P1s are mundane, not scientific)

| Risk | P | Mitigation |
|---|---|---|
| **R9 Solo bandwidth** | P1 | CPU-only core (weeks 1–3) is a shippable minimum unit; TMLR + workshop are clockless exits; pre-agreed cut list; automated resumable runs |
| **R10 Grader wrong/brittle** | P1 | Freeze against v1 logs + hand-audit off-diagonals + golden-fixture unit tests per branch + property test (sign_check invariant to contract cell); demote method to secondary if <90% agreement |
| **R1 Scooped (2512.10159, IF-wave)** | P1 | Flag on T1+T9 whitespace; ship CPU-core κ result early as timestamped stake; pre-written differentiation paragraphs |
| **R4 CoT compute blowup** | P2 | Mandatory 20-instance pilot (hard gate); MoE-only top tier; max_tokens cap + truncation flag; batching |
| **R6 SymPy↔NGSPICE disagree** | P2 | SymPy = source of truth; instrument rejection rate per regime bin; cap extreme R-ratio Traps to ngspice's comfortable range |
| **R2 Trade-off dissolves** | P2 **antifragile** | Falsification pre-registered → a clean "the v1 trade-off was an N=100/judge artifact" is a *genuine correction* TMLR/NeurIPS-ED reward; T1 per-factor ORs stand regardless |

**The scientific risks that look scary are the best-hedged** (whitespace is open, falsification is pre-registered so any outcome is a result). **The risks that actually threaten delivery are mundane and human:** bandwidth (R9) and a subtly-wrong grader (R10) — because the grader *is* the credibility thesis. De-risk both by front-loading the CPU-only core so a citable κ result exists by week 3 with zero inference.

### 6.3 Go/No-Go checkpoints

- **GNG-1 (W3):** κ(rule-vs-judge) ≥0.8 AND dichotomy coherent → proceed to T1. κ low → grader broken, stop and fix before any inference. Dichotomy already weak on logs → pivot to "auditing v1" framing.
- **GNG-2 (W4):** measured mean CoT keeps panel within ~4 days at N=500 → full sweep, else invoke cut-list #5.
- **GNG-3 (W6):** trade-off replicates on open models? Either answer is publishable; proceed.
- **GNG-4 (W8):** ≥2 convention factors show significant McNemar at powered N → strong causal claim.
- **GNG-5 (W9):** draft genuinely ICLR-competitive by ~Sep 10? Yes → ICLR Sep 24. No → **TMLR now**, zero lost work. Do not force ICLR.

---

## 7. VENUE AND TIMELINE

### 7.1 Venue decision

| Venue | Next deadline | P(accept) | Role |
|---|---|---|---|
| **TMLR** | Rolling — any day | ~55–70% | **PLAN OF RECORD** — merit-gated, affiliation-blind, artifact-rewarding; no clock |
| **ICLR 2027** | Abstract **Sep 19**, paper **Sep 24, 2026** [CONFIRMED] | ~30–40% | **UPSIDE** behind Sep-10 quality gate |
| **NeurIPS 2026 workshop** (MATH-AI / eval) | ~Sep 2026 [verify CFP] | ~55–70% | Early citation stake + expert feedback from the W3–W8 causal core |
| **NeurIPS 2027 ED / COLM 2027** | ~May / ~Mar 2027 | ~30% | **STRETCH** for the expanded (T5+T7+T9) version — the ideal home |

**Dead this cycle:** NeurIPS 2026 ED (closed May 6), COLM 2026 (closed Mar 31), AAAI-27 (7pp cap fights a benchmark, ~3 weeks out), all ACL venues (frame a circuits paper as out-of-scope NLP). ⚠️ Re-verify ICLR-2027 dates, NeurIPS/ICLR workshop CFPs, COLM/NeurIPS-2027 deadlines before committing.

### 7.2 Timeline A — ~10-week v1.5 fast-path (ICLR shot, TMLR fallback); W1 = Jul 13

| Wk | Dates | Deliverable | Gate |
|---|---|---|---|
| W1 | Jul 13–19 | Installable `v2/` skeleton; `schema.py`; port supermesh + SymPy verifier; `contract.py` + `test_contract_transforms.py` | — |
| W2 | Jul 20–26 | Generalize ngspice runner; `dual_verify`; port topologies 2–5; full-node-potential netlists | — |
| W3 | Jul 27–Aug 2 | `generate.py` (N≥500); **deterministic grader**; **re-grade 500 v1 logs → κ + adjudicated error table** | **GNG-1** |
| W4 | Aug 3–9 | Provider layer + cache + resumable runner; `models --installed` gap-check; **20-instance pilot/model** | **GNG-2** |
| W5 | Aug 10–16 | MAIN sweep (N≥500 × 2 methods × panel), batched, overnight | — |
| W6 | Aug 17–23 | Grade MAIN; `stats.py`; **2×2 joint per model**; trade-off replication check | **GNG-3** |
| W7 | Aug 24–30 | CAUSAL golden (40×32) + fractional (150×16, 6-model panel); per-factor McNemar; **capability-floor + instructed-vs-uninstructed controls** | — |
| W8 | Aug 31–Sep 6 | Mixed-effects ORs + by-model susceptibility; T6 taxonomy; **discriminant-validity slice**; figures | **GNG-4** |
| W9 | Sep 7–13 | Write intro/method/results; differentiation paragraphs; optional Tier-C ceiling run | **GNG-5** |
| W10 | Sep 14–20 | Polish, reproducibility appendix, artifact release prep; **abstract Sep 19** | ICLR **Sep 24** or **→ TMLR** |

### 7.3 Timeline B — ~20-week ambitious version (TMLR primary; NeurIPS-2027-ED / COLM-2027 positioning)

Superset of A: W1–W9 identical, then **W10** Tier-C+B ceiling (H4 extend-or-break), **W11–W12** mitigation toolkit (C1 restate + C4 answer-blind verifier-loop), **W13–W14** AC/phasor surface, **W15** T9 statics cross-domain probe (Spearman ρ circuits-vs-statics), **W16** stretch buffer (op-amp *or* LoRA SFT), **W17–W18** full analysis + cross-engine receipt + noise-floor, **W19** write, **W20** submit TMLR (~late Nov). Additional gates: GNG-6 (ceiling extends/breaks trade-off), GNG-7 (C4 collapses compliance while competence inert = intervention-based confirmation of disentanglement without any LLM judge), GNG-8 (high ρ → promote T9 to headline "general LLM trait").

**Committed routing:** run **Timeline A** (aim ICLR, TMLR backstop). If the Sep-10 gate misses, submit TMLR immediately and roll the mitigation+domain-expansion additions into Timeline B for TMLR/NeurIPS-2027-ED. In parallel, spin a **NeurIPS-2026 workshop note (~Sep)** from the W3–W8 causal core for an early priority stake.

---

## 8. IMMEDIATE NEXT ACTIONS (this week — W1)

1. **Stand up the installable `v2/` skeleton.** `pyproject.toml` (pinned `httpx, pyyaml, numpy, sympy, pandas, scipy, matplotlib, typer, pytest`; extras `[mlx]`, `[api]`), `circuchain/__init__.py`, `configs/smoke.yaml`, console entry `circuchain`. Acceptance: `pip install -e v2/` and `circuchain --help` work. v1 `data/` + `scripts/` stay byte-for-byte frozen.
2. **Port the SymPy `EquationVerifier` + supermesh topology end-to-end** from `scripts/circuchain_engine.ipynb` (cells 0–1) into `circuchain/analytic.py` + `circuchain/topologies/{base,supermesh}.py`. Acceptance: one topology samples → solves KVL/KCL → emits prompt.
3. **Write `circuchain/contract.py` (the T1 sign transforms) + `tests/test_contract_transforms.py`.** This is the highest-novelty module — get it right first. Unit-test flip-mesh negates mesh currents, PSC flips branch/element signs, ref-node is affine on voltages, against the ported supermesh instance.
4. **Draft `grade/compliance.py` (`sign_check` + magnitude-gate + CONVENTION_BLIND branch) and re-grade the 500 v1 log rows** (`data/graded_master_dataset.json`). This is *the* first citable result — CPU-only, no inference. Acceptance: rule-vs-judge confusion matrix + Cohen's κ printed; hand-audit the ~64 off-diagonal ERR_SIGN/METHOD rows into an adjudicated error table. **Target κ≥0.8.**
5. **Implement the ★2×2 joint report (magnitude-correct × sign-compliant) as a first-class grader output** now, not later — it is the answer to the #1 reviewer blocker and must be baked into the schema from day one.
6. **Verify-live the H1-2026 unknowns** before freezing the panel (WebSearch): Qwen3.5 exact size ladder + license + whether dense rungs keep a `/think` toggle (decides the C4 factorial); Qwen3-Next-80B-A3B Instruct/Thinking MLX conversions on HF; gpt-oss-120b fit at 128 GB; current frontier snapshot strings (GPT-5.5/5.6, Opus 4.8, Gemini 3.x) + reasoning-effort API. Confirm ICLR-2027 Sep 19/24 dates and the NeurIPS-2026 workshop CFP timing.
7. **Confirm the M5 hardware config and enumerate installed models:** run `ollama list` / check MLX weights; write the first cut of `configs/models.yaml` mapping the 10-model panel to what's actually downloaded, and note gaps to pull. The whole compute budget hinges on M5 Max 128 GB — verify it's a Max, not base/Pro.
8. **Set the scope tripwire in writing:** T5-SFT, constrained decoding, op-amp, AC/phasor, human audit, Tier-B API are *cut for this cycle* — pin the cut list where you'll see it, because scope creep is the only path to NO-GO.

**Files you'll touch first:** `/Users/mayankgowda/CircuChain-Benchmark/v2/pyproject.toml`, `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/contract.py`, `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/topologies/supermesh.py`, `/Users/mayankgowda/CircuChain-Benchmark/v2/circuchain/grade/compliance.py`. Source material to port: `/Users/mayankgowda/CircuChain-Benchmark/scripts/circuchain_engine.ipynb` (cells 0–5, 12, 16), `/Users/mayankgowda/CircuChain-Benchmark/scripts/ngspice_circuit_generator.py`, `/Users/mayankgowda/CircuChain-Benchmark/scripts/verify_and_export_json.py`. Re-grade input: `/Users/mayankgowda/CircuChain-Benchmark/data/graded_master_dataset.json`.