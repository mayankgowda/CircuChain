# V2 positioning notes (V2-5)

## 1. Relationship to our own v1 (MUST be explicit in the paper)

**v1 = arXiv:2602.15037** — "CircuChain: Disentangling Competence and Compliance in LLM
Circuit Analysis" (Mayank Ravishankara). 100 tasks/model, 5 topologies, counterbalanced
pairs; headline: *Compliance-Competence Divergence* (strongest models near-perfect physics,
frequent convention violations; weaker models worse physics, better adherence).

v2 must cite v1 in the first paragraph of related work and state the delta plainly —
otherwise reviewers find it and read salami-slicing. The honest delta is large:

| axis | v1 | v2 |
|---|---|---|
| instances | 100/model | 1000/model (procedural, seed-reproducible) |
| topologies | 5 | 7 (adds supernode, VCCS ladder) |
| oracle | hand-checked | 4-way agreement (numpy mesh == nodal == exact SymPy MNA == NGSPICE), zero rejects |
| transform validity | asserted | independently validated (physical re-grounded SPICE run; 125/125) |
| design | counterbalanced pairs | within-physics single-factor matched pairs -> exact McNemar |
| panel | few models | 17 columns, 7 families incl. GPT-5, gemma-4, gpt-oss-120b, DeepSeek-V3 |
| causal contrasts | none | C1 reasoning toggle closed at 4 scales (reasoning does NOT reduce blindness) |
| controls | none | positive controls (86-97% compliance on matched non-convention instructions) |
| stats | rates | bootstrap OR CIs, BH q-values, k=5 test-retest (rate SD 4.7pp; item unanimity 40%) |
| headline | divergence exists | ccw reversion INVARIANT at ~63-81% across 7 families and a 790x competence range; empty-c-cell signature (b~450 vs c~13) |

v1's "strongest models violate most" refines under v2's larger lens: the *rate* of
convention blindness is roughly constant everywhere; competence determines only whether
the blindness is *visible* at the subtask level. State this as a refinement of v1, not a
contradiction: v1 measured divergence; v2 shows the mechanism-side invariance.

## 2. Prior-work deltas (the three the reviewers will check)

- **Inverse IFEval (arXiv:2509.04292)** — names the phenomenon class ("models fail to
  unlearn stubborn training conventions"). Delta: our oracle is sign-exact and LLM-free;
  our design is within-problem causal (McNemar), not rubric-scored; we add the
  competence/compliance 2x2, the invariance result, positive controls, and the
  reasoning-toggle null.
- **Wu et al., "Reasoning or Reciting?" (NAACL 2024)** — default-vs-counterfactual
  matched pairs (bases, chess, etc.). Delta: their counterfactual worlds change the
  *task semantics*; our convention flips leave physics identical and move only the
  *reporting frame*, isolating pure instruction-vs-prior conflict with a verifiable
  numeric oracle; plus the empty-c-cell asymmetry and cross-family invariance.
- **Semantic-override / sycophancy literature** — models revert to pretrained defaults
  despite local redefinition. Delta: quantified reversion RATE with CIs across 7
  families; specificity controls showing the failure is convention-specific.

## 3. Frequency probe — is clockwise actually the dominant trained prior? (yes)

Standard instructional sources state clockwise as THE convention for mesh analysis:
- All About Circuits textbook (Mesh Current Method): standard convention, assume CW.
- LibreTexts (Fiore, AC Circuit Analysis 6.3; Kuphaldt-derived Workforce 10.3): loops
  drawn with a clockwise reference "as a matter of consistency"; "usual practice".
- CircuitBread (Lessons in Electric Circuits): same.
- Wikipedia (Mesh analysis): describes the same CW-loop practice.
The corpus asymmetry is one-sided: sources that *state* a direction overwhelmingly state
CW; we found no instructional source prescribing CCW as the default. (Cite as qualitative
corpus evidence; avoid fabricating counts.)

Sources:
- https://www.allaboutcircuits.com/textbook/direct-current/chpt-10/mesh-current-method/
- https://eng.libretexts.org/Bookshelves/Electrical_Engineering/Electronics/AC_Electrical_Circuit_Analysis%3A_A_Practical_Approach_(Fiore)/06%3A_Nodal_and_Mesh_Analysis/6.3%3A_Mesh_Analysis
- https://workforce.libretexts.org/Bookshelves/Electronics_Technology/Electric_Circuits_I_-_Direct_Current_(Kuphaldt)/10:_DC_Network_Analysis/10.03:_Mesh_Current_Method_and_Analysis
- https://www.circuitbread.com/textbooks/lessons-in-electric-circuits-volume-i-dc/dc-network-analysis/mesh-current-method
- https://en.wikipedia.org/wiki/Mesh_analysis
- https://arxiv.org/abs/2602.15037  (v1)
