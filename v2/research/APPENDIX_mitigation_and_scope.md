I have enough grounding in the actual repo (signed `verifier_map` contract, `gen_spice_probX` + `.op` NGSPICE path, `parse_log_universal`, the explicit "GLOBAL CIRCUIT CONVENTIONS" block in every prompt, and the `Grade`/`Details` + Compliance/Competence schema). Here is the design doc.

---

# CircuChain v2 — Prescriptive & Scope-Expansion Half (T5 / T7 / T9)
### Design doc, tuned for a fully-local Apple-M5 open-model pipeline

**Repo hooks this design reuses (verified in-repo today):**
- `ground_truth.verifier_map` — the signed `{i1,i2,i3,vx,vy}` → float contract. This is the object every mitigation and every new domain extends.
- `gen_spice_probN()` + `.op` + `parse_log_universal()` in `scripts/verify_and_export_json.py` — the NGSPICE dual-verifier, including the zero-volt `V_sense_iN` branch-current trick and `F_dep`/`E_dep` dependent sources.
- Every prompt already ships an explicit `--- GLOBAL CIRCUIT CONVENTIONS ---` block (clockwise mesh, ground-referenced nodal, PSC, dependent-source inference). **This block is the literal "convention contract"** that T1 manipulates and that every T5 mitigation targets.
- Grading schema `{Model, ID, Type, Method, Grade, Details}` with the Compliance={SIGN,METHOD} / Competence={PHYSICS,CALC,HALLUC} dichotomy.

**One cross-cutting dependency:** everything below assumes the v1.5/T2 **deterministic rule-based compliance grader** exists — the thing that replaces the coarse `ERR_SIGN` magnitude-match with a contract-derived expected sign per variable. It is the shared spine: it produces the *feedback message* in the verifier loop (T5-ii), the *reward signal proxy* for SFT eval (T5-iv), and the *sign oracle* in every new domain (T7/T9). Build it first.

---

## A. MITIGATION TOOLKIT (T5)

### Ranking (impact-per-effort × M5 feasibility)

| Rank | Intervention | Abs. impact | Effort | M5 feasibility | Verdict |
|---|---|---|---|---|---|
| **1** | **(ii) Symbolic verifier-in-the-loop** (1 guided retry, violation surfaced) | **High** | Med (reuses NGSPICE/SymPy + T2 grader) | ✅ Full — CPU-only oracle, local models | **MUST-HAVE — flagship** |
| **2** | **(i) Self-verification / convention-restatement prompting** | Low–Med | **Near-zero** (prompt templates) | ✅ Full | **MUST-HAVE — baseline + ablation floor** |
| **3** | **(iv) Small-model convention-aware LoRA SFT** | **High (potential)** | High (corpus + train + eval) | ✅ Full — MLX-LM LoRA on 4B/8B | **NICE-TO-HAVE for v2.0 / MUST-HAVE for expanded version** |
| **4** | **(iii) Constrained / structured decoding** (forced convention field) | Low–Med (mixed; format-tax risk) | Med–High (per-engine grammar plumbing) | ⚠️ Feasible but engine-specific | **NICE-TO-HAVE — appendix ablation** |

The ordering is deliberate: **the loop (ii) and the prompt (i) together already tell the whole prescriptive story** — "is Convention Blindness a blind spot you can nudge away, or a capability ceiling?" — at low/medium cost. SFT (iv) is the strongest *prescription* but is time-expensive and belongs to the T11 recipe; constrained decoding (iii) is a mechanism probe with real format-tax downside.

---

### (i) Self-verification / convention-restatement prompting — MUST-HAVE · ✅ M5-trivial

Pure prompt intervention, three variants, zero new infrastructure:

- **C1 · Restate-then-solve (single pass):** prepend a required section — *"Before solving, restate in one line each binding convention you will obey: mesh direction, reference node, method required. Then solve."* Forces the "never-mentioned" trace class to become "mentioned."
- **C2 · Solve-then-verify-then-revise (two pass):** after the answer, a required self-audit — *"For each reported value, state whether its sign is consistent with the declared convention; if not, correct it."* Targets "mentioned-then-ignored / mentioned-then-misapplied."
- **C3 · Combined** (restate + self-audit).

**Hypothesis:** modest compliance-error reduction, **near-zero competence movement** (self-critique doesn't fix arithmetic or mis-set-up physics). H1-2026 literature (2606.09662 "When Built-in Thinking Helps and Hurts"; the "Format Tax" line) warns self-verification can *regress* constraint-following in reasoning models — so **measure both axes and watch for a competence penalty** (the "format tax"). Its true role is the **cheap floor** the loop and SFT must beat.

**M5:** identical inference cost to baseline (C1) or 2× (C2). No code beyond prompt templates.

---

### (ii) Symbolic verifier-in-the-loop — MUST-HAVE, flagship · ✅ M5-full

**Loop:** model proposes → deterministic compliance grader + NGSPICE `.op`/SymPy check contract compliance → if a violation is found, surface **only the violation class, not the answer** → allow **exactly one** guided retry → re-grade.

**Feedback-leakage design (the scientifically load-bearing choice) — two sub-modes:**
- **C4 · Compliance-only feedback:** reveal only the convention violation, e.g. *"You reported i2 = +6 mA. Under the required CLOCKWISE mesh convention the sign is inconsistent; your magnitude may be correct but the sign violates the stated contract. Revise."* Or for method: *"You solved by nodal analysis; the task required mesh/KVL. Redo with the required method."* **Never reveals the ground-truth number.**
- **C5 · Magnitude-hint feedback (optional, stronger):** additionally reveal `|truth|` for off-magnitude values but not the sign — a more "applied" repair signal that begins to probe competence repair too.

**Why this is the headline, and how it differs from the numeric mitigation loops already in the literature (2512.10159, Gemini+ngspice):** that work is a *single-model accuracy engine*. Ours is a **diagnostic probe of repairability**: run C4 across the full 10-model panel and measure whether a compliance failure is a *blind spot* (fixed the instant it's pointed at) versus whether a competence failure is a *capability ceiling* (survives the same targeted nudge). The clean predicted result — **compliance error collapses under C4 while competence error barely moves** — is a *second, independent confirmation of the disentanglement thesis*, obtained by intervention rather than by an LLM judge. Cite and differentiate 2512.10159 explicitly in one paragraph.

**Careful framing note:** C4's compliance "repair" is partly tautological (you told the model its sign was wrong). The interesting, non-tautological readouts are (a) **residual re-violation rate** — models that *still* fail after being told — and (b) the **compliance-repair vs competence-repair contrast under the same kind of hint**. Report both; do not headline raw repair rate alone.

**M5:** NGSPICE `.op` and SymPy are instant CPU-side; the only added cost is one extra generation per still-failing item (≤ 2× inference in the worst case). Fully local.

---

### (iii) Constrained / structured decoding — NICE-TO-HAVE · ⚠️ M5-feasible, engine-specific

Force a schema that makes the convention declaration **in-band and machine-checkable, adjacent to the answer**:

```json
{ "mesh_direction":"clockwise", "reference_node":"...", "method_used":"mesh",
  "answers": { "i1": {"sign":"-","magnitude": 0.006}, ... } }
```

- **MLX path:** Outlines / guidance structured generation; **llama.cpp path:** GBNF grammar. Both exist on Apple Silicon.
- **Reasoning-model caveat:** you want *free-form `<think>`* then a *constrained final block* — schema-constrain only the answer segment, or you strangle the CoT. Feasible but fiddly, and it fractures the clean MLX-primary / llama.cpp-fallback split because grammars are engine-specific.

**Hypothesis:** forcing an explicit per-variable `sign` field narrows the mention→application gap but risks the **"format tax"** competence regression (2604.03616; "Capacity, Not Format" 2606.09410). Its value is as a **mechanism ablation** ("does forcing an in-band sign commitment reduce mentioned-then-ignored?"), not a deployable fix. Appendix-tier.

---

### (iv) Small-model convention-aware LoRA SFT — NICE-TO-HAVE (v2.0) / MUST-HAVE (expanded) · ✅ M5-full

**Is LoRA SFT feasible on one M5?** Yes, comfortably. `mlx_lm.lora` (MLX-LM's first-class LoRA/QLoRA trainer) fine-tunes **Qwen3-4B** on a 32 GB base M5 and **Qwen3-8B** on an M5 Max (4-bit base + bf16 adapters) in **hours, not days**, for a few-thousand-example, 1–3-epoch run. Zero marginal dollar cost.

**Corpus — generated free by the repo's own pipeline (this is the elegant part):**
- Sample instances from the T2 procedural generator; solve each with the **SymPy analytic solver** to get the signed, contract-correct answer; emit a **templated worked solution** (deterministic, showing the convention being applied to fix the sign).
- **Crucially include contract variants** (flipped mesh direction, alternate reference node, anti-PSC, method-required toggles — the T1 Latin-square variants) so the model learns to **condition its signs on the stated contract**, not default to a training prior.
- **Anti-leakage guardrails (this is a train-on-synthetic-data setup):**
  1. **Templated SymPy ground-truth solutions, NOT teacher-model distillation** — distilling a frontier model would import *its* convention blindness.
  2. **Held-out generalization split:** train on 4 topologies + a subset of contract variants; **evaluate on the 5th held-out topology and held-out contract variants.** Compliance drop *there* proves "obey the stated contract," not memorization.
  3. **Competence-neutrality guard:** competence-error must not rise; add a **capability-retention check** (small general-arithmetic/reasoning slice) to rule out catastrophic forgetting.

**Experimental claim (crisp):** *Convention-aware LoRA SFT on a small open model reduces compliance-error — including on held-out topologies and held-out contract variants — with no competence regression and no general-capability loss.* That is the prescriptive win and the natural centerpiece of the expanded (NeurIPS-2027) version / the T11 released checkpoint.

---

### Mitigation study — experimental matrix

**Models (representative subset, not all 10 — bounds the sweep):** Qwen3-4B-Thinking (small reasoner + SFT target), Llama-3.1-8B-Instruct (small base control), Qwen3-14B (mid reasoner, thinking-toggle control), Qwen3-30B-A3B-Thinking (large MoE reasoner), Llama-3.3-70B-Instruct (70B base) — optionally add DS-R1-Distill-Llama-70B for the same-base natural experiment.

**Test set:** one **fixed, stratified subsample** of the N≥500 pool — e.g. **N=150 instances × 2 methods = 300 subtasks**, balanced across 5 topologies × Control/Trap and **seeded with the T1 contract-variant traps**. Fixed items → valid **paired McNemar** across all conditions. Trim to N=100 for the reasoning-heavy conditions if wall-clock bites.

| Condition | Applies to | Extra inference | Primary question |
|---|---|---|---|
| **C0** Baseline (v2 standard prompt) | all | 1× | reference |
| **C1** Restate-then-solve | all | 1× | does forced *mention* help? |
| **C2** Self-verify-revise | all | 2× | does self-*audit* help? |
| **C3** Constrained decoding | all (engine-permitting) | 1× | does in-band sign commitment help? (format-tax cost?) |
| **C4** Loop, compliance-only feedback | all | ≤2× | is the failure a *blind spot*? |
| **C5** Loop, magnitude-hint (optional) | all | ≤2× | does competence repair too? |
| **C6** SFT model vs its own C0 | SFT'd 4B/8B | 1× | durable, weights-level fix? |

**Per-cell metrics:** overall pass; **compliance-error rate**; **competence-error rate**; and vs C0 — **ΔCompliance, ΔCompetence with paired McNemar**. For C2/C4/C5 also report **repair rate**, **residual re-violation rate**, and **induced-regression rate** (baseline-correct items broken = the format-tax cost).

**Headline result structure:** *Compliance error is cheaply and increasingly repairable (C1 modest → C4 large → C6 durable) while competence error is largely inert under the same interventions* → intervention-based confirmation that the two axes are mechanistically distinct, and that Convention Blindness is a **correctable behavior, not a capability ceiling.**

---

## B. DOMAIN EXPANSION (T7) — two highest-leverage new convention surfaces

**Chosen: AC/phasor (j-sign + phase reference) and ideal op-amp (virtual-short + inverting sign).** Both are genuinely *new convention surfaces* (not just new topologies), both are covered by the existing NGSPICE+SymPy dual verifier, **and neither needs a vision model** — so the entire text-only local panel (and the controlled reasoning/base axis) carries over intact. Schematic-image is explicitly **deferred** (A2: 4/5 scoop risk; it would shrink the panel to Qwen-VL/Gemma-3-multimodal and break the reasoning/base control). Diode is noted as a weaker third option.

### B1. AC / phasor — MUST-HAVE · ✅ M5-full, no vision

**Why it is a rich NEW convention surface:**
- **The j-sign is the convention.** `Z_L = +jωL`, `Z_C = −j/(ωC)` — a model trained on mixed time-conventions (`e^{+jωt}` vs `e^{−jωt}`) will flip the imaginary sign of every reactance. This is the DC sign flip reincarnated in the complex plane.
- **Phase reference** (which source/branch is the 0° reference) is the *direct analog of the reference-node choice in nodal DC* — the T1 convention-contract manipulation ports straight over.
- **Leading/lagging & angle sign:** a phase of −30° vs +30° is exactly the mesh-current sign trap, but now on a **complex-valued ground truth** where both magnitude and phase carry a convention-dependent sign.

**Ground truth / verification:** NGSPICE **`.ac lin 1 f f`** returns complex node voltages and (via the existing zero-volt `V_sense` trick) complex branch currents — magnitude & phase at the test frequency. Dual-verify with **SymPy complex algebra** (`I`, `Abs`, `arg`). `verifier_map` extends cleanly from signed floats to **`{re, im}` or `{mag, phase}` per variable**; the deterministic compliance grader gains a *phase-sign* and *j-sign* check. NGSPICE `.ac` fully covers it.

**Generalization lift:** proves Convention Blindness is **not a DC/mesh artifact** — it recurs in a different mathematical setting (frequency domain, complex numbers) under a *different* convention (j-sign, phase reference). Strong within-circuits generalization and a novel, under-explored sign axis (A2 flags AC/phasor as "genuinely underexplored convention playground").

### B2. Ideal op-amp — virtual-short + inverting/non-inverting sign — MUST-HAVE (or strong NICE-TO-HAVE) · ✅ M5-full, no vision

**Why it is a rich NEW convention surface — and a *different flavor* of compliance:**
- **The virtual short is an assumption contract:** "ideal op-amp, V+ = V−, infinite input impedance, linear region, ignore rails." A model that silently treats it as finite-gain, or **imposes saturation from its prior**, violates a *stated idealization instruction*. This introduces **assumption-compliance** alongside sign-compliance — a genuinely new compliance axis ("idealization blindness").
- **Inverting sign is the canonical trap:** gain `−Rf/Rin` (inverting) vs `+(1+Rf/Rin)` (non-inverting). The output-sign relative to input polarity is a signed ground truth the model must read from topology + contract, not from a prior.
- **Rail convention as an explicit knob:** "assume ideal, no rails" vs "clip at ±Vsat" is a manipulable contract flag — did the model honor "ideal," or hallucinate saturation?

**Ground truth / verification:** model the ideal op-amp in NGSPICE as a **high-gain VCVS** (`E` source, gain ≈ 1e6) or a standard ideal-op-amp `.subckt`; **`.op`** gives node voltages. Solve the **virtual-short node equations analytically in SymPy**; both agree at the ideal limit. **NGSPICE `.op` covers it with the existing `E_dep`-style VCVS machinery already in `gen_spice_prob5` — minimal new plumbing.**

**Generalization lift:** adds an *assumption/idealization* contract on top of a sign convention, broadening "Convention Blindness" from "sign convention" to "any declared engineering idealization the prior wants to override." Distinct compliance flavor → stronger, less circuits-specific claim.

**Why op-amp over diode:** the diode reverse-bias "assume-forward-conducting" prior is a real *prior-override* example, but it is a **regime/state assumption, not a declarable, flip-by-instruction convention**, so it doesn't port the T1 manipulation; and its SymPy dual is a nonlinear Shockley-equation root-find that muddies the clean analytic verification. Keep **diode as a NICE-TO-HAVE third surface** (`.op` covers it natively; good for a "mild-nonlinear" stress cell) and **schematic-image as a deferred stretch** (the only candidate needing vision; crowded; shrinks the panel).

**Vision requirement summary:** AC ❌ none · op-amp ❌ none · diode ❌ none · schematic-image ✅ requires vision (deferred).

---

## C. CROSS-DOMAIN GENERALIZATION (T9)

### Chosen domain: **statics free-body sign convention** — NICE-TO-HAVE (promote to MUST-HAVE if schedule allows) · ✅ M5-trivial, no simulator, no vision

**Why statics over thermo ΔH:** statics is **mechanically isomorphic to circuits** — linear equilibrium equations (ΣF=0, ΣM=0 ↔ KVL/KCL), a **declared positive-direction convention** (CCW-positive moment / rightward-positive force ↔ clockwise mesh), signed scalar answers, and a machine-checkable analytic ground truth with **no simulator dependency**. That structural isomorphism makes the reviewer-facing "*same failure mode, different domain*" argument tight and legible. The T1 convention-contract manipulation ports directly (flip positive-moment direction, change reference point, flip reaction-sign convention = same physics, different contract), and free-body sign errors are textbook-documented (face validity). Thermo ΔH is a fine **backup / second domain** (reverse-reaction flips the sign; Hess's-law ground truth) if they want n=2 cross-domain points, but the equilibrium-equation isomorphism makes statics the decisive first pick.

**Minimal-but-decisive design:**
- **~40 instances**, 2–3 topology families (simply-supported beam with point loads; single-pivot moment balance; one truss-joint equilibrium), each shipping a declared sign convention + reference point, **Control/Trap counterbalanced** — Trap = load geometry that drives a reaction **negative** under the declared convention (the exact analog of negative mesh currents under clockwise).
- **Ground truth:** a ~50-line **SymPy/NumPy equilibrium solver** (ΣFx=ΣFy=ΣM=0) — deterministic, instant, fully local, **no NGSPICE**. Reuse the same deterministic compliance grader: contract implies each reaction's **sign**; grade **compliance (sign matches declared convention) separately from competence (magnitude correct)**, identical to circuits.
- **Run the *same* model panel** on circuits and statics.

**The decisive statistic:** compute each model's **compliance-error rate in circuits vs statics** and test the **cross-model correlation (Spearman ρ over the ~10-model panel)**, plus an item-level within-model agreement check. **If models that are convention-blind in circuits are also convention-blind in statics (high ρ), Convention Blindness is a model-level *trait*, not a circuits artifact** — which elevates the paper from "a circuits benchmark" to "a general property of how LLMs handle declared engineering conventions," and **insulates against a circuits-only scooper** (A2 whitespace #2). The correlation needs *panel breadth* (10 models) more than per-domain N — hence "small but decisive": keep it appendix-scale, spend the budget on model coverage, not instance count.

**M5:** pure-Python solver + text-model inference on the existing panel; the cheapest high-narrative-lift item in the entire prescriptive half. **This is why it's a promote-to-MUST-HAVE candidate:** a few days of work converts the venue ceiling from "circuits eval" to "general LLM-behavior finding."

---

## Priority roll-up & timeline mapping

| Item | Tag | M5 | Ships in |
|---|---|---|---|
| T5-ii Verifier-in-the-loop (C4) | **MUST** | ✅ full | **v2.0 (ICLR Sep-2026)** — flagship prescription |
| T5-i Restate / self-verify prompting | **MUST** | ✅ trivial | v2.0 — baseline floor + ablation |
| T7 AC/phasor surface | **MUST** | ✅ full | v2.0 — generalization within circuits |
| T7 Op-amp surface | **MUST / strong-NICE** | ✅ full | v2.0 if time; else first expanded add |
| T9 Statics cross-domain probe | **NICE → promote to MUST** | ✅ trivial | v2.0 if a week of slack — highest narrative-lift-per-effort |
| T5-iv Convention-aware LoRA SFT | **NICE (v2.0) / MUST (expanded)** | ✅ full | **Expanded (NeurIPS-2027)** — the T11 recipe + checkpoint |
| T5-iii Constrained decoding | **NICE** | ⚠️ engine-specific | v2.0 appendix ablation, or drop |
| T7 Diode / schematic-image | **NICE / deferred** | diode ✅ / image needs vision | Expanded only; image only if a multimodal track is deliberately added |

**Build order:** (0) deterministic compliance grader [T2, prerequisite] → (1) verifier-in-the-loop C4 + restate/self-verify C1/C2 → (2) AC + op-amp surfaces via `.ac`/`.op` extensions to `gen_spice_probN` + `verifier_map` → (3) statics probe (standalone SymPy solver, same grader) → (4) constrained-decoding ablation → (5) LoRA SFT for the expanded version.

**Two things a reviewer will demand you pre-empt:** (a) cite and crisply differentiate **2512.10159** (Gemini + ngspice loop) from T5-ii — theirs is a single-model accuracy engine, ours is a cross-panel *repairability diagnostic* with answer-blind feedback; (b) keep the verifier's retry feedback **strictly answer-blind** (violation class only) or the loop result is dismissed as leakage. Both are handled in the C4 design above.