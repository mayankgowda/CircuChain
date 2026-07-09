I now have comprehensive coverage. Here is the competitive-landscape and scooping-risk assessment.

---

# CircuChain v2 — Competitive Landscape & Scooping-Risk Assessment
*Scoping analysis as of 2026-07-09. Verification flags are marked ⚠️ where a claim rests on a search snippet I did not open directly, or on a venue/date that should be confirmed before you cite it.*

## Bottom line up front

- **The core niche is still OPEN.** No one has published the specific thing CircuChain is: *disentangling instruction-compliance from physics-competence by manipulating the convention contract while holding the physics fixed.* The surrounding literature is converging fast, but from three different directions that no single paper has yet joined.
- **Overall 6–12 month scooping risk: 2.5 / 5** for the core disentanglement thesis; **~3.5/5** for the generic "reasoning models drop constraints" angle (hot in H1 2026, but domain-agnostic); **~4/5** for the multimodal-schematic track (crowded — do NOT make it central).
- **One genuinely direct neighbor exists** that v1 appears to have missed and v2 *must* cite: **arXiv 2512.10159** (Gemini 2.5 Pro + ngspice verification loop for DC circuit solving) — same domain, same ground-truth tool, and it independently names "incorrect current-direction assumptions" as a failure mode. It does **not** scoop the thesis (it's an engineering/mitigation pipeline on one model), but it lands uncomfortably close.
- **Clearest whitespace to plant the flag: T1 (causal convention-contract manipulation) + T9 (cross-domain convention blindness).** Everything else is either table-stakes (T2/T3) or partially pre-empted (T5's verifier-in-loop, T7's multimodal).

---

## Bucket 1 — LLM + circuit / EDA / electronics benchmarks

| Work (arXiv / venue) | What it does | Overlap with CircuChain | Threat |
|---|---|---|---|
| **CIRCUIT** — 2502.07980 | 510 analog-circuit QA pairs, unit-test grouping; GPT-4o 48% final-answer / 27% unit-test | Same "circuit reasoning benchmark" genre; numeric grading | **Adjacent.** Answer-correctness only; no compliance axis. v1 already cites. Not a threat. |
| **MMCircuitEval** — 2507.19525, ICCAD 2025 ⚠️venue | 3,614 multimodal EDA QA across design stages; metadata tags "logical reasoning / numerical computation" and difficulty | Circuit benchmark; multimodal; has a *method/ability* metadata axis | **Adjacent/Partial.** Broad EDA coverage but no compliance-vs-competence split, no convention manipulation. v1 cites. |
| **AMSbench** — 2505.24138 | MLLM benchmark for AMS circuits: schematic perception, analysis, design | Circuit analysis benchmark | **Adjacent.** Perception-heavy, no instruction-conformance axis. Likely v1-missed → cite. |
| **Enhancing LLMs for End-to-End Circuit Analysis** — 2512.10159 | Gemini 2.5 Pro pipeline: YOLO source-detection + **ngspice verification loop** + HITL; 79.5%→97.6% on 83 problems; names two failure modes: source-polarity recognition & **"incorrect current-direction assumptions"** | **Highest overlap in this bucket.** Same DC domain (KVL/KCL/nodal/mesh), **same ngspice ground truth**, and independently identifies the *sign/direction* failure that is CircuChain's centerpiece | **PARTIAL threat / must-cite.** Does NOT scoop the thesis: it's a single-model mitigation engine, not a diagnostic benchmark; no compliance/competence disentanglement, no convention-contract manipulation, no deterministic compliance grader, no model panel. But a reviewer will ask "how is this different?" — you need a crisp paragraph. |
| **Benchmarking LLMs on Homework Assessment in Circuit Analysis** — 2506.06390 (Springer IJAIED / ScienceDirect) ⚠️ + **Enhancing LLMs for Automated HW Assessment** — 2511.18221 | LLMs as *graders* of 283 handwritten student circuit solutions; scores **completeness / METHOD / final-answer / arithmetic / units**; models incl. Llama-3-70B | Circuit domain **and an explicit "method" adherence metric** — conceptually adjacent to compliance | **Partial/adjacent.** Different task (LLM-as-assessor, not solver-under-convention), but proves "method compliance" is already on the community's radar in circuits. Must-cite for v2 framing. |
| Masala-CHAI (2411.14299), SPICEAssistant (2507.10639), AnalogCoder, AnalogMaster, TopoSizing, AMS agent papers | SPICE-netlist datasets & agentic analog-design/sizing tools | Same electronics domain, tooling only | **Not competing.** Design-automation, not reasoning-diagnosis. Optional one-line cite for breadth. |

**Read on bucket 1:** the EDA-benchmark space is busy but is optimizing for *answer accuracy / design automation / multimodal perception*. None of them separate "did it get the physics right" from "did it obey my rules." 2512.10159 is the one to watch and cite; the homework-assessment pair is the sleeper you should acknowledge.

---

## Bucket 2 — the deeper novelty axis (constraint-following, prior-override, judge reliability, causal eval)

| Work (arXiv / venue) | What it does | Overlap | Threat |
|---|---|---|---|
| **IFEval / IFBench / AgentIF (2505.16944) / ConInstruct (2511.14342) / SciIF (2601.04770) / "Deconstructing Instruction-Following" (2601.18554) / PACIFIC (2512.10713)** | Rule-based, programmatically-verifiable instruction-following benchmarks; ConInstruct adds conflict detection/resolution; PACIFIC/VerIF stress deterministic rule-based grading | The **method** (deterministic rule-based compliance grading) that v1.5 plans to adopt | **Framing threat, not scooping.** These establish that "rule-based IF grader" is *not itself novel* — so v2 cannot sell the deterministic grader as the contribution. Sell it as *defensibility*; sell the **domain (physics conventions where the correct number flips sign)** as the novelty. Cite PACIFIC/VerIF as the methodological lineage. |
| **"Who is In Charge? Role Conflicts in Instruction Following" (2510.01228)** + **"Reasoning Up the Instruction Ladder" (2511.04694)** + **Many-Tier Instruction Hierarchy (2604.09443)** ⚠️ | Models obey social cues (authority/consensus) over the actual instruction hierarchy | Instruction-priority-under-conflict | **Adjacent.** Their conflict is *social/role* (system vs user); CircuChain's is *prior vs explicit convention* with a provably-correct answer. Distinct — cite to position. |
| **"When Truth Is Overridden: Internal Origins of Sycophancy" (2508.02087)** + **"Challenging the Evaluator: Sycophancy" (EMNLP-2025 findings)** ⚠️ | Models override learned facts to agree with the user (sycophancy) | Prior-vs-instruction override mechanism | **Adjacent + rhetorically useful.** CircuChain's "Convention Blindness" is essentially **inverse sycophancy**: the model overrides a *correct* user instruction to satisfy its *training prior* — the opposite failure. That inversion is a clean, quotable differentiator. Cite and name it. |
| **"When Built-in Thinking Helps and Hurts: Constraint-Level Error Shifts in IF" (2606.09662)** + **"The Format Tax" (2604.03616)** + **"Capacity, Not Format" (2606.09410)** + **"Reliability of LMs in Instruction-Following" (2512.14754)** + **"One Token Away from Collapse" (2604.13006)** | H1-2026 burst showing **reasoning/thinking modes regress on constraint-following**; open-weight models (Qwen3, DeepSeek-R1 distills, Llama) hit hardest | Directly overlaps v2's **reasoning-vs-base axis (T3)** and the **"mentioned-then-ignored" trace category (T6)** | **This is the hottest / highest-velocity zone → risk ~3.5/5.** They're domain-agnostic; none touch physics conventions. Your moat is *circuits + causal contract + signed ground truth*. But move quickly on T3/T6 and cite these heavily so you look current rather than scooped. |
| **FaithCoT-Bench (2510.04040)** + **RFEval (2602.17053)** + **"Faithfulness Metrics Don't Measure Faithfulness" (2605.25052)** | CoT-faithfulness benchmarks; **RFEval uses output-level counterfactual interventions** to test whether stated reasoning *causally drives* the answer (12 open LRMs, math/code) | RFEval is the closest **methodological** analog to T1's causal design | **Partial/methodological threat.** Crucial distinction: RFEval intervenes on the **reasoning trace**; T1 intervenes on the **convention/constraint** while holding physics fixed. Different intervention target → still novel, but you MUST cite RFEval and draw the line explicitly, or a reviewer will conflate them. |
| **"Reliability without Validity" (2606.19544)** + **"Judging the Judges" (2604.23178)** + **"One Token to Fool LLM-as-a-Judge" (2507.08794)** | Systematic LLM-judge critiques: "kappa deflation," judges average Fleiss κ≈0.3, position/verbosity bias, trivially foolable | Directly targets v1's weakness (judge at κ≈0.57) | **Ammunition, not threat.** These *justify* v2 dropping the LLM judge for a deterministic grader. Cite them as the motivation. Your v1 κ≈0.57 is actually *above* the field's typical judges — worth noting. |
| **PhysReason (2502.12054, ACL 2025 ⚠️)** + ABench-Physics, PhysUniBench, HiPhO, PhysicsArena | Physics reasoning benchmarks with **step-level** assessment (PSAS-S) | Adjacent domain (physics), step-faithful grading | **Adjacent.** General physics correctness with step scoring; **none manipulate conventions or separate compliance from competence.** Cite PhysReason as the closest physics-reasoning neighbor and to argue the convention axis is unaddressed there. |
| **Neuro-Symbolic Verification on IF (2601.17789)** ⚠️ | Formal/symbolic verification of instruction-following | Symbolic verifier-in-the-loop ↔ your SymPy/ngspice dual verifier + T5 | **Adjacent.** Reinforces that symbolic verification is a live idea; cite for T5. |

---

## Verdict on the niche

**Is the niche still open? — Yes, with a shrinking window.** Three literatures are converging on CircuChain's coordinates but none has arrived:
1. **Circuit benchmarks** (bucket 1) optimize answer/design accuracy, not rule-obedience.
2. **Instruction-following / reasoning-regression** work (bucket 2, hot in H1 2026) is domain-agnostic and never grounds in a domain where obeying the instruction *changes the correct number's sign*.
3. **Causal-faithfulness** work (RFEval) intervenes on the reasoning trace, not on the constraint.

CircuChain's defensible position is the **intersection**: a domain with a *machine-checkable, sign-carrying ground truth* + a *causally manipulable convention contract* + a *deterministic compliance grader*. That intersection is unclaimed.

**Scooping risk (next 6–12 months):**
- Core disentanglement thesis: **2.5/5** — non-obvious combination, but all ingredients are on the shelf.
- Reasoning-vs-base / constraint-drop angle (if that's your headline): **3.5/5** — crowded and fast.
- Multimodal-schematic track (if central): **4/5** — MMCircuitEval, AMSbench, 2512.10159 already own it.

**Where to plant the flag (whitespace, in priority order):**
1. **Causal convention-contract manipulation (T1)** — nobody has done a same-physics / varied-contract intervention. This is the single strongest, most unclaimed move and it directly patches v1's biggest reviewer critique ("Convention Blindness never tested causally").
2. **Cross-domain Convention Blindness (T9)** — reframes the paper from "a circuits benchmark" to "a general LLM-behavior finding," which both raises venue ceiling and *insulates you from a circuits-only scooper*.

---

## Ranking the v2 ideas by novelty-per-effort (given what already exists)

*Interpreting T2 = statistical-power/procedural-generator/deterministic-grader foundation; T3 = wider model panel incl. open-weights + reasoning/base axis, per your v1.5 plan.*

| Rank | Idea | Novelty now | Effort | Why |
|---|---|---|---|---|
| **1** | **T1 — causal convention-contract Latin square** | **Very high** (unclaimed) | Low–Med (generator emits contract variants cheaply) | Directly plugs v1's #1 hole; the one thing no competitor has. Differentiate hard from RFEval (intervene on *constraint*, not *trace*). |
| **2** | **T9 — cross-domain convention blindness (statics/thermo sign conventions)** | **High** | Med (simple per-domain sign verifiers) | Turns a niche circuits paper into a general finding; hedges against circuit-only scoopers; strong venue lift. |
| **3** | **T6 — reasoning-trace taxonomy** (never-mentioned / mentioned-then-ignored / mentioned-then-misapplied / arithmetic-slip) | Med–High **in-domain** | Low (annotate traces) | Cheap, pairs with T1, and rides the hot 2606.09662 / format-tax wave. **Caveat:** build a *deterministic* trace classifier or you re-import the judge-dependence you're trying to kill. |
| **4** | **T2 — statistical power + deterministic grader** | Low (method is well-trodden: PACIFIC/VerIF/IFEval) | Low–Med | Not a headline, but *essential*: kills the N=100 and judge-κ critiques in one move. Sell as rigor, not novelty. |
| **5** | **T3 — wider panel, open-weights, reasoning/base axis** | Low alone, but **timely** | Low (local M5/Ollama = free scale) | Perfectly aligned with your hard local-compute constraint AND the H1-2026 "reasoning regresses on IF" wave. High value, modest novelty. |
| **6** | **T7 — domain expansion** | Med — but **split it** | High | Do **AC/phasor conventions** (reference phasor, j-sign — genuinely underexplored convention playground). **Avoid leading with multimodal-schematic** — 4/5 crowded. |
| **7** | **T5 — mitigation toolkit** | Med, **partially pre-empted** | High (esp. SFT) | Verifier-in-the-loop is *already done for circuits by 2512.10159 (ngspice loop)*. Fresh sub-part is convention-aware SFT (your T11), but that's the expensive end. Do it late, or as a stretch. |

**Practical recommendation:** headline v2 on **T1 + T9** (the causal, cross-domain convention story), *supported by* T2/T3 (rigor + panel that the local-M5 setup makes free), *seasoned with* T6 (deterministic trace taxonomy). Treat T7-AC and T5-SFT as stretch/appendix so a reviewer can't dismiss the paper as "just a bigger benchmark."

---

## Must-cite papers v1 appears to have missed
*(v1's related-work, per 2602.15037v1, lists only CIRCUIT, MMCircuitEval, and generic sycophancy/instruction-tuning.)*

**Critical (direct neighbors):**
- **2512.10159** — End-to-End Circuit Analysis w/ ngspice loop (same domain + tool + names the direction-sign failure). *Non-negotiable.*
- **2506.06390** (Springer IJAIED) & **2511.18221** — Circuit-analysis homework assessment with an explicit "method" metric.
- **2505.24138** — AMSbench.

**Framing / positioning (bucket 2):**
- **2511.14342** ConInstruct; **2505.16944** AgentIF; IFBench/SciIF (2601.04770); PACIFIC (2512.10713) / VerIF (2506.09942) — deterministic-grader lineage.
- **2510.01228** Role Conflicts; **2508.02087** "When Truth Is Overridden" (frame Convention Blindness as *inverse sycophancy*).
- **2606.09662** "When Built-in Thinking Helps and Hurts"; **2604.03616** "The Format Tax"; **2512.14754** IF-reliability — to look current on reasoning-vs-constraint.
- **2602.17053** RFEval; **2510.04040** FaithCoT-Bench — causal/faithfulness lineage (differentiate T1 from these).
- **2606.19544** "Reliability without Validity" + **2507.08794** "One Token to Fool LLM-as-a-Judge" — motivation for dropping the LLM judge.
- **2502.12054** PhysReason — closest physics-reasoning neighbor.

---

## Claims to verify live before you rely on them
- ⚠️ **Venue/date attributions from search snippets**: MMCircuitEval = "ICCAD 2025"; PhysReason = "ACL 2025"; the sycophancy-evaluator paper = "EMNLP 2025 findings"; 2506.06390 Springer IJAIED publication status. Confirm on the paper PDFs.
- ⚠️ **H1-2026 arXiv IDs I read only via snippet** (not opened directly): 2606.09662, 2604.03616, 2606.09410, 2512.14754, 2601.18554, 2512.10713, 2601.04770, 2601.17789, 2604.09443, 2604.23178, 2605.25052, 2604.13006. Titles/abstracts are from live search today, but confirm exact scope/claims before citing.
- ⚠️ **Directly verified by me** (opened): 2512.10159 (competitor), 2602.15037 (CircuChain v1 itself — confirmed on arXiv, author "Mayank Ravishankara," generated 2026-01-29), 2602.17053 (RFEval). These three you can trust from this pass.
- ⚠️ **"Convention Blindness" term availability**: my searches surfaced *Action-Boundary / Contextual / Algorithmic / Temporal / (implicit) Constraint* "blindness," but **not** "Convention Blindness" in the physics/sign sense — the term appears **unclaimed**, which is good, but do a final exact-phrase check before you build the v2 title around it.