# CircuChain v2 — Feasibility & Go/No-Go

**Date:** 2026-07-09 · Companion to `CIRCUCHAIN_V2_BRAINDUMP.md`.

**Bottom line (see the go/no-go section for the full argument): GO, narrowed.** Build one standalone
causal paper on the v1 infrastructure; scope = causal-contract (T1) + procedural generator (T2/T3) +
deterministic grader (T4) + 10-model open panel (T3-panel) + trace taxonomy (T6). Primary venue **TMLR**
(affiliation-blind, artifact-rewarding), stretch **ICLR 2027** (paper Sep 24, 2026) behind a Sep-10
quality gate. Cut mitigation/SFT/domain-expansion to a 2027 expansion. The Week-3 credibility gate
(GNG-1: rule-vs-judge κ ≥ 0.8) is **already passed at κ=0.944** — see the brain-dump status box.

This file collects three independent analyses produced during planning: an adversarial *Reviewer-2
red-team*, a *go/no-go ROI* analysis, and a *risk register + timeline*.

---

## Part A — Go/No-Go ROI Analysis

# CircuChain v2 — GO/NO-GO ROI Verdict

*Advisor stance: independent researcher, ~3–6 mo budget, M5-local compute, O-1-track reputation goal. Decisive throughout. (T-numbering used here: **T1**=causal contract manipulation, **T2**=procedural generator + statistical power/McNemar, **T3**=wider open-weights panel, **T4**=deterministic rule-based compliance grader, **T6**=reasoning-trace taxonomy — I state this because the source docs bundle T2/T4 inconsistently.)*

---

## 1. Extend v1, or fresh standalone paper?

**Verdict: reuse v1's *infrastructure*, discard v1's *framing*. Build one standalone causal paper (fresh title) on the v1 repo — do NOT market it as "CircuChain v2," and do NOT do the mitigation/SFT idea first.**

The confusion in the question is a false trichotomy. "Extend v1" and "fresh causal-contract+grader paper" are the *same artifact* — the repo (SymPy/NGSPICE dual verifier, 5 topologies, async runner) is ~2–3 months of sunk engineering you'd rebuild from scratch in any "fresh" option. The only real decision is **framing and title**, and there the brand equity math is brutal:

| Option | Reuses repo? | Novelty core | Scoop risk (6–12mo) | Standing-per-week | Verdict |
|---|---|---|---|---|---|
| **A. "CircuChain v2" (incremental)** | ✅ | "bigger benchmark" | 3.5/5 | **Low** — reviewers deflate "v2 of an arXiv preprint" | ❌ |
| **B. Standalone causal paper (T1+T4 core), v1 repo underneath, fresh title** | ✅ | causal convention-contract manipulation | **2.5/5** (open niche) | **Highest** | ✅ **DO THIS** |
| **C. Mitigation/SFT standalone (T5) first** | ✅ | verifier-loop + LoRA | ~3.5/5, **partially pre-empted by arXiv 2512.10159** | Medium, but needs the diagnostic to mean anything | ❌ (this is paper #2) |

**Why B wins decisively:**
- v1 is an **arXiv-only preprint with zero brand recognition** (independent author). There is *nothing to extend* reputationally — the CircuChain name buys you nothing with double-blind ICLR/NeurIPS reviewers anyway. So keep the code, drop the "v2" positioning that codes as "incremental."
- The competition analysis is unambiguous: **T1 (causal contract, same physics/varied contract) is the single most-unclaimed move** (novelty-per-effort rank #1) and it *directly patches v1's #1 reviewer critique* ("Convention Blindness never tested causally"). That is a fresh *claim*, not a fresh *codebase*.
- **C is a trap as a first move.** The verifier-in-the-loop is already published for circuits (Gemini+ngspice, 2512.10159). SFT is the highest-effort, longest-tail item. A mitigation paper with no rigorous diagnostic underneath it is unanchored — you'd be prescribing a cure for a disease you measured with an LLM judge at κ=0.57.

**One-line rule: the paper is T1+T4 (the causal claim + the deterministic grader that makes it airtight); T2+T3 are the rigor that makes reviewers believe it; everything else is paper #2.**

---

## 2. Realistic payoff & reachable venue tier

**Genuinely reachable ceiling: TMLR (floor, high-probability) → ICLR 2027 (stretch gamble). NeurIPS 2027 ED is real only with a 2027 expanded version. Not reachable this cycle: NeurIPS/COLM 2026 (closed), AAAI (7pp cap fights a benchmark).**

Honest calibration for an unbranded independent:

| Venue | P(accept \| solid ambitious-scope paper) | Standing value | Timeline risk |
|---|---|---|---|
| **TMLR** | **~55–70%** (merit-gated, affiliation-blind — *structurally built for you*) | Archival, citable, peer-reviewed; less "buzz" | **None** (rolling) |
| **ICLR 2027** | **~30–40%** (double-blind helps; Sept crunch hurts) | High prestige | High — reject → Jan 2027, 4 mo sunk |
| **NeurIPS 2026 workshop (MATH-AI/eval)** | ~55–70% | Low prestige, fast citation stake | Low |
| **NeurIPS 2027 ED** | ~30% w/ expanded scope | Highest (ideal fit) | 10 mo out |

**What acceptance actually does for standing / O-1:** Be blunt — **one paper is a brick, not the building.** But it's a *high-quality* brick that moves you across a real threshold: from **"arXiv preprint author" → "peer-reviewed publication at a recognized ML venue."** For O-1A evidentiary criteria it feeds three at once:
1. **Authorship of scholarly articles** — directly.
2. **Original contribution of major significance** — *only if it accrues citations*; the niche is open and the topic rides the hot H1-2026 "reasoning regresses on instruction-following" wave, so 10–40 citations over 2 years is plausible if timing holds.
3. **Judging/peer review** — a TMLR/ICLR publication is what gets you review invitations, which is a separate, easy-to-document criterion.

**The highest-leverage O-1 asset here is not the PDF — it's the released open-source artifact** (procedural generator + deterministic grader + dataset + M5 reproducibility receipt). GitHub stars + others building on it is your cleanest evidence of "major significance." **Optimize for the release, not just the acceptance.**

Expected value, stated plainly: **~0.85 probability you end with a peer-reviewed, citable publication + a used open artifact within 9 months** (because TMLR is a near-guaranteed backstop if ICLR misses). That is a solid, real standing gain — not transformative, but a genuine, defensible O-1 brick with a live path to two more criteria. **That EV clears the bar for 3–4 months of a free, local research investment.**

---

## 3. MVP v1.5 vs Ambitious v2 — exact scope & person-weeks

### MVP "v1.5" — least effort, decent venue only
**Include: T2 + T4 + T3. Cut: T1, T6 (and all T5/T7/T9).**

This trio kills all three of v1's fatal critiques (N=100 → N≥500 McNemar; κ=0.57 judge → deterministic grader with a re-graded κ≥0.8 receipt; closed-only → 10–15 open-weights panel). **But it is "a bigger, cleaner benchmark" — reviewers at top venues deflate it.** Ceiling = **TMLR or a workshop**, not ICLR.

| Task | Person-weeks |
|---|---|
| T2: generator refactor + SymPy/NGSPICE dual-verify + N≥500 (pure CPU) | 3–4 |
| T4: deterministic grader + re-grade 500 v1 rows → κ result | 1.5–2 |
| T3: panel run on M5 (2–4 days wall-clock) + pilot + babysitting | 1.5–2 |
| Analysis + writing | 2–3 |
| **MVP total** | **≈ 8–11 pw (2–2.75 mo)** |

### Ambitious v2 — reach for ICLR/NeurIPS-ED
**Add T1 (the causal claim) + T6 (deterministic trace taxonomy) + T9 (cross-domain statics probe).** T1 is non-negotiable — it's what converts "bigger benchmark" into an ICLR-caliber *causal* contribution.

| Added on top of MVP | Person-weeks |
|---|---|
| T1: schema ext + `expected_under_contract` precompute + factorial/fractional design + mixed-effects model + causal sweep (~31k local calls ≈ +1 wk compute, $0) | 3.5–4 |
| T6: deterministic locus classifier on `<think>` traces | 1.5–2 |
| T9: standalone SymPy statics solver, ~40 instances, same grader, cross-domain Spearman ρ — **highest narrative-lift-per-effort** (turns "circuits paper" → "general LLM trait," insulates against circuit-only scoopers) | 1–1.5 |
| Top-venue 9-page writing/polish | +2 |
| **Ambitious total (MVP + above)** | **≈ 16–19.5 pw (4–5 mo)** |

**Explicitly cut from *both* this cycle:** T5 mitigation/SFT, T7 AC/op-amp domain expansion, T10 human audit, T11 released checkpoint. These are the **NeurIPS-2027 expanded version** — folding them in now is exactly how a 4-month plan becomes an 8-month plan with no marginal venue lift.

---

## 4. Recommended scope & phased plan (M5-local as the asset)

**Scope: T1 + T2 + T3 + T4 + T6, plus T9 if a week of slack. Framed as a standalone causal paper. Dual-track TMLR/ICLR with a hard quality gate.**

| Phase | Window | Effort | Deliverable | Compute |
|---|---|---|---|---|
| **P0 — Foundation** | now → early Aug | 4–5 pw | T2 generator + dual-verify + **T4 grader + re-grade v1 → κ≥0.8 result** | **CPU only, $0** — a *citable result before any inference*, de-risks the whole schedule |
| **P1 — The science** | August | 4–5 pw | T3 panel + **T1 causal sweep** on M5 | ~31k+ calls, **$0, no rate limits** |
| **P2 — The lift** | late Aug–early Sep | 3–4 pw | T6 taxonomy + T9 statics + McNemar/bootstrap/mixed-model | cheap local |
| **P3 — Write + gate** | September | 2–3 pw | Draft. **Gate ~Sep 10:** quality there → **ICLR Sep 24**; else → **TMLR immediately**, zero lost work | — |
| **Always** | ~Sep | 0.5 pw | **MATH-AI / eval workshop short paper** — early citation stake + expert feedback | — |

**M5-local reframed as three genuine strengths (lead with these, don't apologize):**
1. **Zero-cost scale:** N≥500 × 15 models × k=3 repeats would cost thousands via API and hit rate limits; locally it's free and unlimited. This is *why* you can afford the statistical power that kills v1's critique — a branded lab paying per-token often *can't* be bothered to.
2. **Reproducibility receipt:** full weight-SHA + seed + `<think>`-trace provenance, cross-checked on two engines (MLX + llama.cpp). This is precisely what TMLR and NeurIPS-ED reward and what an independent author can offer that a closed-API paper *cannot*.
3. **Open-weights-only natural experiments:** Llama-3.3-70B vs its R1-distill (same base, ±reasoning-SFT) and the Qwen3.5 think-on/off scale ladder are *controlled causal contrasts you physically cannot run on closed APIs*. The constraint hands you a stronger causal design than v1's cross-vendor leaderboard. This is the single best "constraint-as-asset" argument — put it in the abstract.

---

## 5. Bottom-line verdict

# ✅ PURSUE — NARROWED

**Scope to the T1+T2+T3+T4+T6 causal core (+T9 if slack). Frame as a standalone causal paper on the v1 repo. Primary target TMLR (guaranteed-ish conversion), stretch ICLR 2027 behind a Sep-10 quality gate. Cut all mitigation/SFT/domain-expansion to the 2027 expanded version.**

**Single biggest reason:** the causal convention-contract manipulation (T1) sits in a *provably open* niche, *exactly patches v1's fatal critiques*, and the M5-local constraint converts it into free, fully-reproducible scale with controlled open-weights ablations a branded lab literally cannot run — so the expected value (≈85% chance of a peer-reviewed, citable publication + a used open artifact in 9 months, via the TMLR backstop) clearly beats the ~4-month cost. **The only way this goes NO-GO is scope creep:** the moment T5 SFT, T7 AC/op-amp, and human audits get pulled into *this* cycle, the timeline blows past the ICLR window, the marginal standing-per-week collapses, and you miss the open niche's shrinking window. Discipline on scope is the whole game.


---

## Part B — Adversarial Reviewer-2 Red-Team

# Review of "CircuChain v2: Disentangling Competence and Compliance in LLM Circuit Analysis"

**Recommendation: Reject (would need major revision + new experiments to move me).** The paper is a competent engineering upgrade of v1, but its central quantitative claim — a *compliance–competence trade-off* — is exposed to at least two failure modes that, on the evidence described, I cannot rule out: (a) it is partly manufactured by the grader's own conditioning structure, and (b) it may be an artifact of a sub-frontier, open-weights-only panel that the H1-2026 literature already tells us is the model class most prone to constraint-dropping. Below, in descending order of damage.

---

## SUMMARY OF THE KILL SHOTS
1. **The compliance-error metric is conditioned on passing a competence gate**, so "competence↑, compliance-error↑" can be produced by the scoring pipeline itself. (BLOCKER)
2. **The causal panel has no frontier models**; the trade-off may be "weak models are weak." (MAJOR→BLOCKER as headlined)
3. **Contract sign-flips confound disobedience with added arithmetic difficulty and with unfamiliarity-with-the-convention** — the three things T1 claims to separate. (MAJOR→BLOCKER for the causal claim)
4. **Novelty is a re-instantiation of known prior-vs-instruction override**, with no experiment proving the "convention" axis is *distinct* from generic instruction-following. (MAJOR)

---

## (1) NOVELTY — "Convention Blindness" is a rename of a documented phenomenon

**Objection.** Strip the branding and the thesis is: *the model's training prior wins over an explicit user instruction.* That is exactly IFEval/IFBench/ConInstruct constrained instruction-following, exactly the sycophancy/"When Truth Is Overridden" mechanism, and exactly the H1-2026 "reasoning regresses on constraint-following" wave (Format Tax, "When Built-in Thinking Helps and Hurts"). Your own related work concedes all of this. "Inverse sycophancy" is a rhetorical inversion of the *same* prior-beats-signal mechanism, not a new one. Worse, the domain-specific observation isn't even first: 2512.10159 already named "incorrect current-direction assumptions" as a failure mode in DC circuits with the *same* ngspice ground truth. Naming a phenomenon and giving it a sign-carrying verifier is an *engineering* contribution (a nicely checkable substrate), not a *scientific* discovery of a new behavior. Nowhere do you show that "convention compliance" is a *different construct* from generic instruction-following rather than the same latent trait measured in a new domain — if the two correlate at ρ≈0.9 across your panel, the benchmark is redundant with IFEval.

**Severity: MAJOR.** (Blocker if the paper is sold as "we discovered Convention Blindness.")

**Minimum to neutralize:** (a) Explicitly concede the phenomenon is known and reposition the contribution as *"the first causally-identified, deterministically-graded, sign-resolved measurement of prior-vs-instruction override in a domain with machine-checkable ground truth."* (b) Run a **discriminant-validity experiment**: score every panel model on a generic IFEval-style compliance slice *and* on convention compliance, and show they **dissociate** (low cross-model correlation, or models that pass format-IF but fail convention-IF). Without that dissociation, "convention compliance" is asserted, not demonstrated, to be a new axis.

---

## (2) THE PANEL — the causal core has no frontier models

**Objection.** Every causal claim (H1/H2/H3) lives on Tier A: open weights ≤ 80B-A3B MoE / 70B dense. Your own cited literature (Format Tax; "Reliability of LMs in Instruction-Following") reports that **open-weight models — Qwen3, R1-distills, Llama — are hit hardest on constraint-following.** So you have selected the model class most predisposed to the very failure you headline. v1's flagship number (GPT-5: ~0% competence / 34% compliance) came from a *closed frontier* model; v2 demotes closed models to "generalization-only," and — fatally — the trace/mechanism analysis (T6) is *impossible* on them because reasoning tokens are hidden. So the mechanistic story can never be told for the models with the most external validity. Tier B ("open-frontier via API," Qwen3.5-397B / DeepSeek-V4) is 🔮 unverified at freeze time and, being API-hosted, is neither local nor reviewer-reproducible in practice. Net: your falsification target for H4 ("does the trade-off survive frontier scale?") is answered by three closed models you can't do mechanism on and two speculative ones you may not be able to run. A reviewer reads this as **"weak models are weak," dressed as a trade-off.**

**Severity: MAJOR, escalating to BLOCKER because it is the headline.**

**Minimum to neutralize:** (a) Run the **full contrast structure at full N and on the identical grader** for the closed frontier trio *and* for the largest honest local model (gpt-oss-120b fits 128 GB). Do not let the frontier be "illustrative" or underpowered at N≈100 — the one place the thesis is most contested cannot be the one place you cut N. (b) The C3 scaling curve (Qwen3.5 2B→4B→9B→27B, extended by Tier B and the closed trio) must show compliance error **flat or non-monotonic through the largest point**, with a pre-registered Cochran–Armitage trend test *including* the frontier. If compliance error declines monotonically with scale, the thesis is dead and the paper must say so. (c) State plainly that mechanism (T6) is open-weights-only and do not generalize mechanistic claims to closed models.

---

## (3) CONSTRUCT VALIDITY — sign-flips confound compliance with arithmetic difficulty *and* with convention-familiarity

**Objection.** T1's entire claim is that each contract factor has a "deterministic, disjoint" action, so its effect on compliance is "identifiable without confounding." It is not. Three confounds ride along with every non-default contract:

- **Added arithmetic.** CW→CCW requires the model to negate every mesh current; PSC-inverted adds a sign operation; ref-node-B is *affine* (changes magnitude, not just sign). A non-default contract is strictly a longer computation than the default. A model that emits the CW value under a CCW instruction may be *failing the extra negation step* (competence), not *ignoring the instruction* (compliance). Your taxonomy's "mentioned-then-ignored" vs "mentioned-then-misapplied" split rests on a *coherence* heuristic — but a model that coherently botches the negation across all variables is **indistinguishable** from one that coherently applies its prior. Coherence does not separate "chose not to obey" from "tried and systematically mis-transformed."

- **Distance-from-prior = your definition of Trap.** The default contract *is* the training prior (CW, PSC-standard, ground-bottom). Every "compliance-hard" cell is therefore also the *least frequent in pretraining*. You cannot tell whether elevated error under CCW is *disobedience* or *the model genuinely not knowing the CCW convention well* (a competence-about-conventions issue). That distinction **is the paper's thesis**, and the design cannot make it.

- **Asymmetric measurement across factors.** ref-node changes magnitude, so its non-compliance is routed to `COMPETENCE_FALLTHROUGH` — meaning ref-node compliance is *undercounted* relative to mesh/PSC. Your five "orthogonal" factors are graded on non-comparable scales.

**Severity: MAJOR → BLOCKER for the causal claim.** If sign-flips are arithmetic or familiarity, T1 collapses to "harder, rarer problems are harder."

**Minimum to neutralize:** (a) **Instructed-vs-uninstructed control, same physics:** present the identical CCW-requiring instance (i) with an explicit CCW instruction and (ii) with the model free to choose and *state* its direction. Disobedience is proven only if the model, when free, self-reports CW, but when instructed CCW still reports CW. (b) **Capability-floor check:** verify each model *can* execute the transform in isolation ("given i₂=+6 mA under CW, what is i₂ under CCW?"). If it can do the negation standalone but fails it embedded, the failure is compliance; if it can't, it's competence — and you must report that split per model. (c) **Decouple prior-distance from difficulty:** include contracts where the *non-default* is the arithmetically simpler branch, and put an explicit `n_sign_ops` / `max_r_ratio` difficulty covariate in the mixed model; the compliance effect must survive conditioning on difficulty.

---

## (4) THE RULE-BASED GRADER — a competence gate sits upstream of the compliance label (this is the most damaging single point)

**Objection.** In `sign_check`, a variable is only eligible for a `CONVENTION_BLIND` label **after** it passes the magnitude gate (`mag_match` within 5%); otherwise it is routed to `COMPETENCE_FALLTHROUGH`. **Therefore a model can never be scored "convention-blind" on a variable whose magnitude it got wrong.** Consequences:

- Competent models clear the magnitude gate more often → they have a **larger pool of sign-eligible variables** → mechanically more opportunity to accrue compliance errors. Weak models fail magnitude → never reach the sign check → are recorded as *low compliance-error*. **The pipeline can produce "competence↑, compliance-error↑" with no behavioral trade-off at all.** The headline finding is confounded with the grader's conditioning structure.
- If instead you report compliance-error *conditional on magnitude-correct*, you are comparing different subpopulations across models (selection on a competence-correlated variable) — the classic collider/selection artifact.

This is not a corner case; it is the axis of the paper. Until it is ruled out, the central result is uninterpretable.

**Additional grader defects:**
- **Zeros/near-cancellation.** `EPS_ZERO = 0.02·scale` is arbitrary, and Traps *deliberately* oversample `near_cancellation` and balanced-Wheatstone regimes — exactly where the true sign is least determinate. A model reporting +1e-4 vs −1e-4 on a genuine null is scored as compliant/blind by numerical noise.
- **Regex method + acknowledgment are gameable and family-biased.** `method_check` passes any answer that name-drops "mesh/loop" while actually doing nodal (keyword gaming), and returns `UNKNOWN` for correct-but-differently-phrased work. It is a *compliance axis* carried by a hand-tuned regex. Worse, it was "frozen after calibration against the v1 logs" — i.e., tuned on v1 models' phrasings. Qwen, Llama, Gemma, gpt-oss have distinct output styles → grader error will be **correlated with the model-family factor**, directly confounding H3.
- **The κ≥0.8-vs-judge validation is on the 500 v1 rows only** (all default contract, so the `CONVENTION_BLIND` branch is inert). You have therefore validated the grader on exactly the regime where its headline branch never fires, and on none of the v2 panel.

**Severity:** Magnitude-gate confound = **BLOCKER.** Regex method/ack fragility + family bias = **MAJOR.**

**Minimum to neutralize:** (a) Report the **full 2×2 joint distribution (magnitude-correct × sign-compliant) per model**, never two rates with different denominators; prove that *within the magnitude-correct subset* the compliance gradient exists and is not explained by magnitude-pass-rate. Pre-register the denominator. (b) **Human-audit ≥200 stratified rows across every panel family**, reporting per-family precision/recall for the sign, method, and acknowledgment labels — the compliance axis cannot rest on a regex whose error rate you have not measured on the actual models. (c) Ablate: does the headline survive if method-compliance is dropped and only sign-compliance is used? (d) Exclude genuine-null variables from sign scoring by a physics criterion, not a magnitude threshold.

---

## (5) SCOPE / GENERALIZATION — pseudo-diversity and a tautological "cross-domain" test

**Objection.** (a) N≥500 comes from **5 hand-built topology templates** with resampled parameters. That buys *statistical* N but not *structural* diversity: the effective structural degrees of freedom is 5. Treating instances as independent for power overstates it, and external validity to "circuit analysis" is thin — no transistor bias, no transient, no multi-op-amp, no real netlists. (b) The "cross-domain" statics probe is **chosen because it is "mechanically isomorphic to circuits"** (linear equilibrium, declared sign convention, signed scalar answer). Showing the same linear-sign-convention failure in a relabeled linear-sign-convention problem is close to **tautological** — it demonstrates robustness to variable-renaming, not generality to different reasoning. A skeptic reads T9 as a coordinate transformation of the same task. (c) Multimodal/schematic is deferred, so only *text-encoded* circuits are tested — arguably the easy case for convention-following.

**Severity: MAJOR** for a D&B "benchmark" contribution; MINOR–MAJOR for a diagnostic framing.

**Minimum to neutralize:** (a) Separate "statistical N" from "structural N=5" in every power statement; add 3–5 more topologies (your `TopologySpec` abstraction makes this cheap) or explicitly bound the claim to "linear DC/AC network analysis." (b) Make the cross-domain test **non-isomorphic**: include a domain where the convention is *not* a linear sign flip (e.g., a convention that changes a discrete/branching choice, or thermo ΔH direction as a genuinely different physical quantity), or drop the "general property of LLMs" framing. (c) Do not claim generality beyond text-encoded problems.

---

## (6) MITIGATION / SFT — circular repair, single held-out point, unavoidable 1-bit leakage

**Objection.** (a) The flagship C4 verifier-in-the-loop gives "answer-blind" feedback ("your sign violates the stated contract"). For a **1-bit quantity (sign), telling the model its sign is wrong is equivalent to revealing the correct sign.** The "answer-blind" framing is therefore false for exactly the variable the paper cares about; the "compliance repair" is largely tautological, as the design doc half-concedes. (b) The SFT trains on templated SymPy solutions from the **same generator** that produces the eval; the "held-out topology" guard is a **single** held-out topology (train 4 / test 1) — an anecdote, not a plural generalization claim, and surface-form/templating leakage remains even with novel values. (c) "No competence regression, no capability loss" is checked against a "small general-arithmetic slice," not a real held-out benchmark.

**Severity: MAJOR if headlined; MINOR if appendix.**

**Minimum to neutralize:** (a) Reframe C4 as an **upper bound on repairability under a near-answer-revealing hint**, and lead with the two *non-tautological* readouts — **residual re-violation rate** and the **compliance-vs-competence repair asymmetry** — explicitly conceding sign feedback ≈ answer feedback. (b) Leave-one-out across all 5 (soon ≥8) topologies with per-fold numbers; report a real capability-retention benchmark (GSM8K/MMLU-STEM). (c) Release checkpoint + training data + seeds, or cut the SFT claim entirely — an unreproducible "convention-aware SFT works" is worse than no claim.

---

## (7) STATISTICS — power is assumed, multiplicity is uncontrolled, random slopes from 10 clusters, and "indistinguishable" needs an equivalence test

**Objections, itemized:**
- **Power is fictional until piloted.** The 80% claim assumes discordance π_d≈0.30 and OR≥2 from v1. If models mostly *agree* across contracts (low discordance), the design is underpowered. Measure discordance in a pilot before stating power.
- **No multiplicity control.** 5 factors × ~10 models × multiple contrasts (per-factor per-model McNemar) + mixed model + bootstrap + trend tests = hundreds of tests. False positives are guaranteed; the per-model "susceptibility" claims are the most exposed. No FDR/hierarchical correction is mentioned.
- **Random slopes from 10 level-2 units.** The mixed model puts by-model random slopes on `mesh_CCW`/`PSC_inverted` with ~10 Tier-A models. Random-slope *variance* from 10 clusters is unstable and CI coverage is poor (rule of thumb ≥20–30). Yet "per-model Convention-Blindness susceptibility" — the headline quantitative object v1 lacked — is read off exactly this structure.
- **"Indistinguishable" ≠ equivalence.** Reframing the top-model overlap as "they separate on compliance, not competence" requires a **TOST equivalence test** with a pre-specified margin, not a non-significant McNemar / overlapping CIs. Absence of evidence is being sold as evidence of absence.
- **Unequal k confounds the F1 contrast.** k=1 for small base models but k=3/5 for reasoning models means measurement precision (and majority-vote bias) covaries with the reasoning/base factor — contaminating the C1/C2 causal contrasts you headline.
- **Topology-level clustering unmodeled.** Only 5 structural clusters; pairing is within `physics_id`, but topology-level correlation in convention behavior can make SEs anticonservative.

**Severity: MAJOR** in aggregate (individually minor→major).

**Minimum to neutralize:** Pre-registered analysis plan with FDR/hierarchical correction; pilot-measured discordance backing the power statement; **TOST** for every "indistinguishable" claim; **equalize k across the panel** (or enter k as a covariate); treat model as **fixed** effects for the susceptibility read-out (or expand to ≥20 models) and add topology as a crossed effect (acknowledging 5 levels is itself under-powered).

---

## THE THREE THINGS THAT MUST BE TRUE FOR me TO ACCEPT

1. **The trade-off must be shown NOT to be a scoring/selection artifact.** Report the joint (magnitude-correct × sign-compliant) 2×2 per model; demonstrate the compliance gradient exists **within the magnitude-correct subset** and is independent of magnitude-pass-rate; and show it **survives at genuine frontier scale** (closed trio + gpt-oss-120b at full N on the identical grader), not just on ≤80B open weights. If either the gate-confound (Obj. 4) or the weak-model-selection concern (Obj. 2) is not closed, "competence↑, compliance-error↑" is uninterpretable.

2. **The compliance axis must be shown to measure disobedience, not difficulty, unfamiliarity, or a redundant construct.** This requires the instructed-vs-uninstructed same-physics control + the capability-floor transform check (Obj. 3), *and* the discriminant-validity experiment proving convention-compliance dissociates from generic instruction-following (Obj. 1). Without these, T1 is "rarer, harder problems are harder."

3. **The deterministic grader must be validated on the actual v2 panel with a pre-registered, multiplicity-controlled statistical plan.** Human audit with per-family error bounds (the κ-vs-judge result on v1-default rows does not transfer, since the headline branch never fires there), FDR correction, TOST for equivalence claims, equal k across the panel, and a defensible treatment of the 10-cluster random-effects structure.

**Bottom line:** the deterministic grader, procedural generator, and local-reproducibility story are genuine rigor upgrades and I want to like this paper — but as written, the headline trade-off is confounded by its own scoring pipeline, demonstrated only on the model class the literature already flags as worst at compliance, and the "causal" contract manipulation cannot separate disobedience from arithmetic. Those are not polish items; they are the thesis. Fix 1–3 above with real experiments and this becomes a strong paper. Absent them, reject.

*Files referenced are conceptual (design docs in context); no repository paths are load-bearing for this review.*


---

## Part C — Risk Register & Timeline

# CircuChain v2 — Risk Register, De-Risking Plan & Timeline
*Prepared as a research-risk assessment for a solo, M5-local build. Compiled 2026-07-09. Anchored to the Phase A landscape, Phase B design docs, and the ICLR-2027 (Sep 24, 2026) / TMLR / NeurIPS-2027-ED venue map.*

---

## 0. How to read this

- **Likelihood / Impact** are H/M/L. "Impact" is measured against *the paper landing at a credible venue on schedule*, not against "the world ending."
- **Priority** = Likelihood × Impact, surfaced in the matrix. The two P1 risks are **author bandwidth** and **the deterministic grader being wrong** — not the exciting scientific ones, which are mostly well-hedged by the existing design.
- Several "scientific" risks (trade-off dissolving, SFT null) are **not really risks** in the career sense: the design is built so the falsification *is itself the finding*. Those are flagged **"antifragile."**
- Dates verified live before acting are marked ⚠️ where the Phase A/B docs already flagged them (ICLR Sep 24 is [CONFIRMED]; H1-2026 model/venue specifics are 🔮).

---

## 1. Risk Matrix (priority-sorted)

| ID | Risk | L | I | Priority | Antifragile? |
|---|---|---|---|---|---|
| **R9** | Solo-author bandwidth / single point of failure | H | H | **P1** | no |
| **R10** | Deterministic grader itself is wrong/brittle (regex method-check, extractor) | M | H | **P1** | no |
| **R1** | Scooped within 6–12 months | M | H | **P1** | partial |
| **R4** | M5 compute blows up (reasoning-model CoT tail) | M | M | **P2** | no |
| **R6** | NGSPICE↔SymPy disagreement / non-convergence on generated instances | M | M | **P2** | no |
| **R8** | Reviewer dismisses the open-only panel | M | M | **P2** | no |
| **R2** | Headline trade-off *dissolves* under rule-grader / on open models | M | M–H | **P2** | **yes** |
| **R11** | ICLR Sep-24 window too tight → forced/low-quality submission | M | L | **P3** | yes (TMLR) |
| **R3** | LLM-judge circularity survives even in the reduced role | L | M | **P3** | no |
| **R7** | Contamination of the frozen test split | L | M | **P3** | partial |
| **R5** | SFT doesn't move the needle / causes competence regression | M | L | **P3** | **yes** |
| **R12** | MLX/Metal nondeterminism breaks the reproducibility receipt | L | L | **P4** | no |

---

## 2. Risk Register (detailed)

### R9 — Solo-author bandwidth (P1, L=H, I=H)
**Description.** One person owns generator + verifier + provider adapters + grader + 5-topology port + multi-day sweeps + stats + writing, against a Sep-24 deadline, on hardware that must not sit idle. Any single illness, hardware hiccup, or a two-week rabbit-hole (a flaky ngspice edge case, an MLX conversion that doesn't exist) consumes the entire slack. This is the **most likely thing to sink the paper**, and it is invisible in a purely technical plan.
**Mitigation / contingency.**
- **Scope ladder, not scope cliff.** The build order is explicitly designed so **weeks 1–3 (CPU-only) already yield a citable result** (deterministic grader + κ≥0.8 re-grade of the 500 v1 logs) with zero inference. Treat that as the *minimum shippable unit* (a workshop/TMLR-able note) so bandwidth loss degrades gracefully instead of catastrophically.
- **Two committed exits with no clock:** TMLR (rolling) and a NeurIPS-2026 workshop short paper (~Sep). Missing ICLR costs nothing if TMLR is the real target.
- **Automate the multi-day parts** (resumable content-addressed cache, append-only JSONL, `make all`, CI smoke test) so overnight/weekend runs need no babysitting — this is already in the B3 engineering plan; it is a *bandwidth* control, not just an engineering nicety.
- **Cut list pre-agreed** (see §4): T5-SFT, constrained decoding, op-amp, second domain, Tier-B/C API models are all droppable without touching the thesis.
- **Contingency:** if week-8 status is red, invoke the "CPU-core-only" paper (grader + causal T1 on the 6-model causal panel, no mitigation, no domain expansion) → TMLR.

### R10 — The deterministic grader is itself wrong or brittle (P1, L=M, I=H)
**Description.** The entire pitch is "we replaced the κ≈0.57 judge with a *deterministic* grader." If the `method_check` regex misclassifies (KVL/KCL signatures are heuristic, `MIXED`/`UNKNOWN` edge cases), or the regex answer-extractor drops/duplicates variables, or `sign_check`'s `EPS_ZERO` mislabels a near-zero variable, then the headline compliance numbers are wrong *and* the "deterministic" selling point becomes a liability a reviewer can attack harder than the old judge. `method_check` is the weakest link — it is a text classifier wearing a rule-based costume.
**Mitigation / contingency.**
- **Freeze the grader against the v1 logs before trusting it.** Re-grade all 500 rows, build the rule-vs-judge confusion matrix, and **hand-audit every off-diagonal cell** (there are only ~60 ERR_SIGN + 4 METHOD rows to check). This is cheap and turns "trust me" into "here is the adjudicated error table."
- **Golden-fixture unit tests for every branch** (compliant / prior-override / incoherent / method-violation / zero-var / magnitude-fail) + a property test that `sign_check` is invariant to which contract cell produced a `(pred, expected)` pair. Gate CI on it.
- **Report `method_check` coverage and abstention rate explicitly.** Because `UNKNOWN` never forces a violation, the failure mode is *under*-detection (conservative), not false accusation — state this. If method-classification agreement with a human spot-check is < ~90%, **demote method-compliance to a secondary axis** and headline sign-compliance only (which is fully deterministic from signed truth + tolerance, the strong leg).
- **Contingency:** if method regex is hopeless on some model's terse output, restrict method-compliance grading to the `<think>` trace (available on all local models) and footnote that closed-API models are sign-compliance-only.

### R1 — Scooped within 6–12 months (P1, L=M, I=H)
**Description.** Three literatures are converging on CircuChain's coordinates (A2): circuit benchmarks, the hot H1-2026 "reasoning regresses on constraint-following" wave (~3.5/5 risk), and causal-faithfulness (RFEval). The single closest neighbor, **arXiv 2512.10159** (Gemini + ngspice loop, names "incorrect current-direction assumptions"), lands uncomfortably close. Core disentanglement thesis risk is ~2.5/5; the generic "thinking drops constraints" angle is ~3.5/5.
**Mitigation / contingency.**
- **Plant the flag on the unclaimed intersection: T1 causal convention-contract manipulation + T9 cross-domain generalization.** Nobody has done same-physics/varied-contract. This is both the moat and the patch to v1's #1 critique.
- **Do not headline the crowded angles** (multimodal-schematic 4/5; generic reasoning-regression 3.5/5). Cite them heavily to look *current*, not scooped.
- **Ship the CPU-core result early** (κ re-grade, ~week 3) as a timestamped stake — even as an arXiv preprint or workshop note — to establish priority before the full paper.
- **Pre-write the differentiation paragraphs** for 2512.10159 (single-model accuracy engine vs cross-panel *repairability diagnostic* with answer-blind feedback) and RFEval (intervene on *trace* vs intervene on *constraint*). A reviewer *will* ask; having the paragraph ready is the mitigation.
- **Contingency:** if a direct scooper appears mid-build, pivot the headline from "we found the trade-off" to "we *causally isolate and quantify* it per-factor per-model (mixed-effects ORs)," which no accuracy-engine paper can claim.

### R4 — M5 compute blows up on reasoning-model CoT (P2, L=M, I=M)
**Description.** A3 is explicit: output length is the single largest budget uncertainty; a 3k→5k average CoT shift inflates every reasoning-model row ~1.7×. A *dense* 70B reasoner (R1-Distill-Llama-70B) alone is ~56 h at N=500. The full CAUSAL suite is ~31k calls. A naive panel + long CoT + no cap could turn a 3-day job into a 2-week job and blow the deadline.
**Mitigation / contingency.**
- **Mandatory 20-instance pilot per model *before* the full sweep** to measure actual mean CoT length (this is a hard gate, GNG-2). Budget from measured, not assumed, lengths.
- **MoE at the top tier, never dense on the long-CoT path** (Qwen3-Next-80B-A3B / gpt-oss-120b give ~70B quality at 3–4× decode). Keep the dense-70B *reasoner* as an N=500-only 11th model, not a routine N=1000 column.
- **Hard `max_tokens` cap** (8k non-reasoning / 16k reasoning) with a per-call truncation flag logged; truncation is a *data point* (constraint-drop under length pressure), not just a loss.
- **Continuous batching** (llama.cpp server or MLX) compresses the N=500 panel ~88h→~50–70h.
- **Contingency:** if compute is red at GNG-2, drop N to 500 (not 1000), cut the causal panel from 6→4 models, and run the OA-screen (1 cell/anchor) instead of the fractional factorial. The mixed-effects model still identifies main effects.

### R6 — NGSPICE↔SymPy disagreement / non-convergence (P2, L=M, I=M)
**Description.** The generator dual-verifies every instance (SymPy MNA vs ngspice `.op`, reject if rel > 1e-4). Dependent sources (VCVS/CCCS), extreme R-ratios (>100, a Trap predicate), and near-cancellation Traps are exactly the regimes where ngspice can mis-converge or the two solvers can drift, causing high rejection rates that (a) slow generation and (b) *bias the sampled distribution away from the hardest Traps* — which are the scientifically interesting ones.
**Mitigation / contingency.**
- **Rejection-sampling is already the plan**, but instrument it: log the rejection rate *per regime bin*. If Traps reject disproportionately, the Trap distribution is silently truncated.
- **SymPy is the source of truth** (exact rationals → floats); ngspice is the cross-check. On disagreement in a dependent-source or extreme-ratio case, trust SymPy and tighten ngspice options (`.options reltol/abstol/gmin`) rather than discarding the instance.
- **Guard the guard:** unit test `test_analytic_vs_spice.py` on hand-solved textbook instances so a *generator* bug can't masquerade as a solver disagreement.
- **Contingency:** cap the extreme-ratio Trap predicate (e.g. R-ratio ≤ 1e3 instead of unbounded) so instances stay in ngspice's comfortable numeric range while still violating textbook intuition. If a topology (likely VCVS) is chronically flaky, ship it as "verified by SymPy, ngspice-corroborated where convergent" and footnote it.

### R8 — Reviewer dismisses the open-only panel (P2, L=M, I=M)
**Description.** "Your causal claims rest on ≤80B open models; the trade-off could be a small-model artifact that true frontier scale erases" is the predictable H2/H4 attack, and it's the flip side of the local-compute *strength*.
**Mitigation / contingency.**
- **Reframe local as reproducibility, not limitation** — ICLR/NeurIPS-ED/TMLR reviewers explicitly reward released, re-runnable artifacts; the fully-local pipeline *is* the differentiator.
- **Two-part ceiling patch (B4):** Tier B (open-frontier via commodity API — Qwen3.5-397B-A17B, DeepSeek-V4 🔮) extends the *same* scaling curve reproducibly; Tier C (GPT-5.5/Opus-4.8/Gemini-3.x 🔮, ~$150–300 total) anchors the absolute ceiling and preserves v1 lineage continuity. State plainly: **all causal claims rest on Tier A; Tier C is generalization-only** and never carries a headline number.
- **Build H2/H4 falsification in on purpose:** the paper says up front "if both error types fall monotonically with scale *and* reasoning-tuning, the thesis dies — here is the Cochran-Armitage trend test that would catch it." Pre-registering the kill condition disarms the reviewer.
- **Contingency:** if Tier-B/C budget or access (🔮 Claude Fable 5 may be restricted) falls through, the two 70B natural experiments (Llama-3.3-70B vs R1-Distill-Llama-70B; Qwen think-on/off) still give *controlled* reasoning-tuning contrasts that a cross-vendor leaderboard cannot — that's a stronger causal design than v1 regardless of ceiling.

### R2 — The headline trade-off dissolves (P2, L=M, I=M–H) — **ANTIFRAGILE**
**Description.** Two ways it could vanish: (a) the deterministic grader, being stricter and contract-based, reclassifies v1's "compliance" errors as ordinary magnitude errors, collapsing the compliance/competence distinction; or (b) on the open panel the trade-off simply doesn't appear (compliance error falls monotonically with scale → "Convention Blindness" is a weak-model artifact).
**Why this is fine / publishable if framed right.**
- The v2 design is **explicitly constructed to detect its own falsification** (B4 H2/H4). A clean, deterministic, well-powered result that says *"the v1 trade-off was an N=100, LLM-judge artifact that does not survive rigorous grading"* is a **genuine scientific correction** — exactly the kind of null/overturning result TMLR ("are the claims supported?") and the NeurIPS *evaluation-as-science* track were re-scoped to reward. It is a better paper than a hype-confirmation.
- Even in the dissolve case, **T1 still stands**: you can causally show *which* convention factors models violate and by how much (per-factor McNemar ORs), independent of whether the aggregate "trade-off" survives.
**Mitigation / contingency.**
- **Decide the framing at GNG-1/GNG-3, before writing.** If κ-regrade already weakens the dichotomy → lead with "auditing v1: how much of the trade-off was the judge?" If it holds on the logs but dissolves on open models → lead with "the trade-off is real but *scale/lineage-specific* — here's where."
- Keep both narrative skeletons drafted so the pivot costs days, not weeks.
- **Never let "we hoped it would hold" leak into the paper.** Pre-registering the hypotheses (H1–H4 with confirm/refute conditions, already in B4) makes either outcome a *result*.

### R11 — ICLR Sep-24 window too tight (P3, L=M, I=L) — hedged by TMLR
**Description.** 10 weeks from today to a [CONFIRMED] Sep-24 top-tier deadline, solo, with multi-day sweeps and a from-scratch package refactor, is genuinely tight. Forcing it risks a rushed, rejectable submission that also burns the idea's first-impression at that venue.
**Mitigation / contingency.**
- **TMLR removes the clock entirely** and is the structurally ideal home for an affiliation-blind, artifact-heavy paper. Treat ICLR as *upside*, TMLR as *plan of record*.
- **Hard quality gate at ~Sep 10 (GNG-5):** if the paper isn't genuinely ICLR-strong, **do not submit** — roll straight to TMLR with zero lost time, and post a workshop short paper (~Sep MATH-AI) for visibility.
- ⚠️ Re-verify ICLR-2027 abstract (Sep 19) / paper (Sep 24) dates and the NeurIPS-2026 workshop CFPs before committing.

### R3 — LLM-judge circularity survives the reduced role (P3, L=L, I=M)
**Description.** The judge is demoted to (a) sub-dividing the *competence* bucket ({PHYSICS, CALC, HALLUC}) on COMPETENCE_FALLTHROUGH rows, and (b) the *ignored-vs-misapplied* tie-break in the T6 taxonomy. A reviewer could still say "your competence taxonomy and part of your mechanistic story ride an LLM judge."
**Mitigation / contingency.**
- **The dichotomy that carries the thesis is 100% deterministic** — say this in one bolded sentence. The judge cannot emit SIGN or METHOD by construction, so it *cannot* touch the compliance axis or the headline.
- **Report κ only on the judge-tiebreak subset** (the rare ignored-vs-misapplied cases), not on the headline — and report how *few* rows it decides. If that subset is large, that itself is a finding (ambiguous mechanistic cases) to disclose, not hide.
- **Contingency:** if a reviewer objects, the competence sub-labels can be collapsed to a single "competence error" bucket with no loss to the main claim; the T6 tie-break can be dropped, reporting those rows as "ambiguous locus."

### R7 — Contamination of the frozen test split (P3, L=L, I=M) — partly antifragile
**Description.** v1 used canonical Sadiku-textbook values almost certainly in pretraining. If v2's generated split leaks into a future model's training, or if the release accidentally ships test instances, post-publication contamination is embarrassing and hard to walk back.
**Mitigation / contingency.**
- **The T1 contract manipulation is itself a contamination hedge:** the *default-convention* answer is memorizable, but the *flipped-contract* answer is not — a model parroting v1 numbers scores as ERR_SIGN_CONVENTION, which is precisely the phenomenon under study.
- Fresh randomized (non-textbook) parameter values; `instance_hash` dedupe across splits *and* against the v1 50-instance manifest; per-release **canary GUID** so future leakage is detectable; publish the hash manifest so reviewers verify no test leak.
- **Contingency:** hold the true test split *unreleased* at submission (release generator + seed + train/dev only), release test post-acceptance — standard practice that a reviewer will accept.

### R5 — SFT doesn't move the needle / causes competence regression (P3, L=M, I=L) — **ANTIFRAGILE**
**Description.** Convention-aware LoRA SFT (T5-iv) might fail to reduce compliance error on the held-out topology/contract, or might induce a "format-tax" competence regression or general-capability forgetting.
**Why low impact.** SFT is explicitly **NICE-TO-HAVE for v2.0, MUST-HAVE only for the expanded (NeurIPS-2027) version.** It is not on the ICLR/TMLR critical path.
**Mitigation / contingency.**
- **Guardrails already designed:** train on templated *SymPy* solutions (not frontier-teacher distillation, which would import the teacher's blindness); held-out 5th-topology + held-out-contract evaluation split; capability-retention slice to catch forgetting; report ΔCompetence with paired McNemar.
- A **null or negative SFT result is a legitimate finding** — "convention blindness is not cheaply SFT-away on small models" is publishable and informs the mitigation story (points toward verifier-in-the-loop, C4, as the effective lever).
- **Contingency:** cut SFT to the expanded version entirely; the mitigation story stands on C1 (restate) + C4 (answer-blind verifier loop), which are M5-trivial and deliver the *repairability* narrative without any training.

### R12 — MLX/Metal nondeterminism breaks the reproducibility receipt (P4, L=L, I=L)
**Description.** MLX greedy temp=0 is stable but not bit-exact across versions/machines; a reviewer could question reproducibility.
**Mitigation.** Tolerance-numeric + rule-based grading makes sub-ULP jitter *label-invariant* — state this. Quantify the noise floor once (k=10 same-seed vs varied-seed label-flip rate). Cross-engine receipt: re-run headline models through llama.cpp/GGUF (stable file hashes) and show gaps reproduce on both engines. Log full provenance (weight SHA-256, quant, lib versions, seed, prompt hash) per call.

---

## 3. Consolidated de-risking philosophy (the five load-bearing moves)

1. **CPU-first build order.** Generator + dual-verify + deterministic grader + v1-log re-grade (weeks 1–3) produce a **citable κ result with zero inference.** This front-loads the credibility win, de-risks the schedule, and gives a shippable minimum unit if bandwidth collapses.
2. **Falsification is pre-registered.** H1–H4 ship with explicit confirm/refute conditions and trend tests. Any outcome — trade-off holds, dissolves, or is scale-specific — is a *result*, which neutralizes R2 and R8 and converts them from threats into content.
3. **Two clockless exits (TMLR + workshop) behind the one clocked shot (ICLR).** R9 and R11 lose most of their teeth the moment TMLR is the plan of record and ICLR is upside.
4. **The compliance axis never touches an LLM.** Deterministic by construction; the judge is quarantined to the competence sub-bucket. This is the whole point of v2 and the answer to R3.
5. **Everything past the causal core is on a pre-agreed cut list** (SFT, constrained decoding, op-amp, 2nd domain, Tier-B/C). Scope degrades gracefully.

---

## 4. Pre-agreed cut list (invoke under bandwidth/compute pressure, in order)
1. Constrained decoding ablation (C3) — drop first.
2. LoRA SFT (T5-iv) → defer to expanded version.
3. Op-amp domain surface → defer; keep AC/phasor *or* statics, whichever is further along.
4. Tier-B open-frontier API models → keep Tier-C ceiling only, or drop both (70B natural experiments survive).
5. N=1000 → N=500; causal panel 6→4 models; fractional factorial → OA screen.
**Never cut:** procedural generator + dual-verify, deterministic compliance grader + v1 re-grade, T1 causal contract on the causal panel, McNemar/mixed-effects analysis. That set *is* the paper.

---

## 5. Timeline A — ~10-week "v1.5" (ICLR-2027 shot, TMLR fallback)
*Weeks anchored Monday. W1 = Jul 13. Target: ICLR abstract Sep 19 / paper Sep 24, else TMLR immediately.*

| Wk | Dates | Focus | Deliverable | Gate |
|---|---|---|---|---|
| **W1** | Jul 13–19 | Installable `v2/` skeleton; `schema.py`; port supermesh topology + SymPy `EquationVerifier`; `contract.py` sign-transforms + `test_contract_transforms.py` | `pip install -e v2`, `circuchain --help`, 1 topology end-to-end | — |
| **W2** | Jul 20–26 | Generalize ngspice runner; `dual_verify`; port topologies 2–5; full-node-potential netlists (ref-node remap) | 5 topologies, SymPy==ngspice rel<1e-4 on all | — |
| **W3** | Jul 27–Aug 2 | `generate.py` (regimes × contracts × seed, N≥500); **deterministic grader** (`compliance.py` + `extract.py` + `numeric.py`); **re-grade 500 v1 logs**; hand-audit off-diagonals | κ(rule vs judge), confusion matrix, adjudicated error table | **GNG-1** |
| **W4** | Aug 3–9 | Provider layer (`ollama.py` + `list_installed`, `cache.py`, `run.py`); `models --installed` gap-check; **20-instance pilot per model** (measure CoT length) | Resumable runner; measured per-model token budget | **GNG-2** |
| **W5** | Aug 10–16 | MAIN sweep (N≥500 × 2 methods × local panel), batched, overnight/resumable | MAIN completions cached | — |
| **W6** | Aug 17–23 | Grade MAIN; `stats.py` (McNemar, Wilson, bootstrap); trade-off replication check on open panel | MAIN accuracy + compliance/competence tables | **GNG-3** |
| **W7** | Aug 24–30 | CAUSAL suite: golden factorial (40×32) on panel + fractional (150×16) on 6-model causal panel | CAUSAL completions + per-factor McNemar | — |
| **W8** | Aug 31–Sep 6 | Mixed-effects logistic (per-factor ORs, by-model random slopes); T6 deterministic trace taxonomy; figures | Causal ORs, susceptibility ranking, locus distributions | **GNG-4** |
| **W9** | Sep 7–13 | Write: intro/method/results; differentiation paragraphs (2512.10159, RFEval); optional Tier-C ceiling run (~$150) | Full draft | **GNG-5** |
| **W10** | Sep 14–20 | Polish, reproducibility appendix, artifact/code release prep; **abstract Sep 19** | Submission-ready | ICLR **Sep 24** or **→ TMLR** |

**Go/No-Go rules (Timeline A):**
- **GNG-1 (W3):** If κ(rule vs judge) ≥ 0.8 *and* the compliance/competence dichotomy is coherent → proceed to T1. If κ low → the grader is broken (R10): stop and fix before any inference. If the dichotomy already weak on logs → pivot framing to "auditing v1" (R2 antifragile path).
- **GNG-2 (W4):** If measured mean CoT keeps the panel within ~4 days at N=500 → full sweep. If not → invoke cut-list #5 (MoE-only top tier, N=500, cap max_tokens).
- **GNG-3 (W6):** Trade-off replicates on open models? Yes → standard narrative. No → "scale/lineage-specific" or "judge-artifact" narrative (both publishable). Either way proceed.
- **GNG-4 (W8):** ≥2 convention factors show significant McNemar effect at powered N? Yes → strong causal claim. If underpowered → report OA-screen marginals + CIs honestly; still a result.
- **GNG-5 (W9):** Draft genuinely ICLR-competitive by ~Sep 10? Yes → submit ICLR. No → **TMLR now** (no clock) + workshop note. Do **not** force ICLR.

---

## 6. Timeline B — ~20-week "ambitious v2" (TMLR primary; NeurIPS-2027-ED / COLM-2027 positioning)
*W1 = Jul 13 → W20 ≈ Nov 29. Superset of Timeline A: adds the mitigation toolkit, one domain expansion, the cross-domain probe, and the ceiling tiers, then writes for a no-deadline venue.*

| Wk | Phase | Focus | Gate |
|---|---|---|---|
| **W1–W3** | Foundation (= Timeline A) | Generator, dual-verify, deterministic grader, **v1 re-grade** | **GNG-1** |
| **W4–W5** | Runner + MAIN | Provider layer, pilot, MAIN sweep (N=1000), grade | **GNG-2** |
| **W6–W7** | MAIN analysis + CAUSAL golden | Trade-off replication; golden factorial (40×32, 10 models) | **GNG-3** |
| **W8–W9** | CAUSAL fractional + mixed model | 150×16 on 6-model causal panel; per-factor ORs; T6 taxonomy | **GNG-4** |
| **W10** | **Ceiling tiers** | Tier-C closed (GPT-5.5/Opus-4.8/Gemini-3.x, ~$150–300) + Tier-B open-frontier via API; H4 extend-or-break test | **GNG-6** (ceiling extends vs breaks trend?) |
| **W11–W12** | **Mitigation toolkit** | C1 restate + C4 answer-blind verifier-in-the-loop on the mitigation subpanel; repair / residual-re-violation / induced-regression rates | **GNG-7** (does compliance error collapse under C4 while competence stays inert?) |
| **W13–W14** | **Domain expansion #1** | AC/phasor surface via ngspice `.ac` + SymPy complex; extend `verifier_map` to {mag,phase}; j-sign + phase-reference compliance grader | — |
| **W15** | **Cross-domain probe (T9)** | Standalone SymPy statics equilibrium solver (~40 instances, same grader); Spearman ρ of per-model compliance-error circuits vs statics | **GNG-8** (is Convention Blindness a model-level *trait*? ρ high → yes) |
| **W16** | Stretch / cut buffer | Op-amp surface *or* LoRA SFT *or* constrained-decoding ablation — whichever the schedule affords; else absorb slippage | — |
| **W17–W18** | Full analysis + figures | OA extension screen; noise-floor quantification; cross-engine (llama.cpp) reproducibility receipt; all tables/figures | — |
| **W19** | Write | Full TMLR-length draft; all differentiation + related-work; pre-registered H1–H4 outcomes | — |
| **W20** | Polish + release | Artifact/code/data release, contamination doc, canary, manifest; **submit TMLR** | **Submit** |

**Additional Go/No-Go rules (Timeline B):**
- **GNG-6 (W10):** If the closed ceiling *breaks* the trade-off (frontier has low compliance error too) → that is H4-refute, a headline finding on its own; reframe as "the trade-off is a sub-frontier phenomenon." If it *extends* → strongest version of the thesis. Either → proceed.
- **GNG-7 (W12):** If C4 answer-blind repair collapses compliance error while competence barely moves → **intervention-based confirmation of disentanglement without any LLM judge** (the flagship prescriptive result). If C4 does *nothing* → "convention blindness is a capability ceiling, not a blind spot" — also publishable; report residual re-violation as the finding.
- **GNG-8 (W15):** If Spearman ρ (circuits vs statics compliance error over the panel) is high → promote T9 to a headline ("general LLM trait, not a circuits artifact"), lifting the venue ceiling and insulating against a circuits-only scooper. If ρ is low → report as an honest boundary condition (domain-specific), keep appendix-scale.

**Venue routing for Timeline B:** submit **TMLR ~W20 (late Nov)**; in parallel spin a **NeurIPS-2026 workshop note (~Sep)** from the W3–W8 causal core for early expert feedback and a priority stake; position the full mitigation+domain-expansion version for **COLM-2027 (~Mar)** and **NeurIPS-2027-ED (~May)**. ⚠️ Re-verify all 2027 deadlines and H1-2026 model checkpoints (Qwen3.5 size ladder + `/think` toggle, DeepSeek-V4 footprint, frontier snapshot strings) before freezing the panel.

---

## 7. One-paragraph bottom line
The scientific risks that look scary (R1 scooping, R2 dissolving, R8 open-panel) are **the best-hedged** — the T1 causal contract is unclaimed whitespace, and the design pre-registers its own falsification so any outcome is a result. The risks that actually threaten delivery are **mundane and human**: solo bandwidth (R9) and a subtly-wrong deterministic grader (R10), because the grader *is* the credibility thesis. De-risk both the same way: front-load the CPU-only core (generator + grader + v1 re-grade) so a **citable κ result exists by week 3 with zero inference**, gate hard at GNG-1, and treat **TMLR as the plan of record with ICLR as upside** so no deadline can force a bad submission. Run the 10-week track if aiming at ICLR; run the 20-week track — which is the 10-week track plus mitigation (C4), one domain expansion, the T9 cross-domain probe, and the ceiling tiers — if aiming at TMLR/NeurIPS-2027-ED, where the paper becomes a flagship rather than a note.
