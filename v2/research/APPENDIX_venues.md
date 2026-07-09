# CircuChain v2 — Venue & Deadline Map (2026–2027 Cycle)

*Compiled 2026-07-09. Deadlines marked **[CONFIRMED]** were verified live against official CFP/dates pages this session; **[EST.]** are projected from the prior cycle and must be re-checked when the next CFP posts.*

## The one fact that reshapes everything

The two most natural homes for this paper — **NeurIPS 2026 Evaluations & Datasets track** (May 6, 2026) and **COLM 2026** (Mar 31, 2026) — **have already closed.** As of today, every top-tier deadline that thematically fits is either (a) already past, or (b) too soon to run the M5 experiments (AAAI/EAAI, ~3 weeks out). The real decision is between **ICLR 2027 (Sep 24, 2026)** as the earliest credible top-tier shot, **TMLR (rolling)** to remove the deadline/brand gamble, and **waiting for the 2027 ideal-fit venues** (COLM 2027, NeurIPS 2027 ED) with a workshop paper bridging the gap.

---

## Venue-by-venue

| Venue | Next deadline | Tier | Accept-rate | Fit (1–5) | One-line why |
|---|---|---|---|---|---|
| **NeurIPS 2026 Eval & Datasets** | May 4/6 2026 — **PAST** | Top | ~30–33% | 5 | Literally re-scoped in 2026 to treat *evaluation as a scientific object* — the paper's exact thesis. But gone until NeurIPS 2027. |
| **ICLR 2027** | Abstract **Sep 19**, paper **Sep 24 2026** [CONFIRMED] | Top | ~31–33% | 4 | Benchmarks + reasoning-eval land well; earliest top-tier deadline that fits the experiment window. |
| **COLM 2026** | Mar 31 2026 — **PAST** | Strong→Top | ~28–30% | 5 | Dedicated LLM venue, indie-friendly; ideal fit but closed. Next is COLM 2027. |
| **COLM 2027** | ~Mar 2027 [EST.] | Strong→Top | ~28–30% | 5 | Best thematic home available on the 2027 calendar; friendlier to non-brand-name authors than NeurIPS/ICLR. |
| **AAAI-27 (main)** | Abstract **Jul 21**, paper **Jul 28 2026** [CONFIRMED] | Strong | ~23–25% | 3 | Broad AI audience, but ~3 weeks out = no time for M5 runs; 7pp (+refs) is tight for a benchmark. |
| **EAAI-27 (education track)** | ~Jul–Sep 2026 [EST. — verify] | Mid/Workshop | higher, niche | 3 | Fits *only if* you lead with the tutoring/education angle (T12); symposium, low ML prestige. |
| **EMNLP 2026 (ARR May)** | May 25 2026 — **PAST** | Strong | ~20–25% | 3 | NLP framing is a stretch for a circuits paper; also closed. |
| **ARR Aug 2026 cycle** | **Aug 3 2026** [CONFIRMED] → commits to **EACL 2027** (commit Oct 11) | Strong | ~20–25% | 3 | Open and near-term, but *ACL venues frame this as NLP, not eval; weaker fit + longer path. |
| **NAACL 2026** | **Not running in 2026** [CONFIRMED — absent from ARR venue list] | — | — | — | Skipped this cycle; disregard until NAACL 2027. |
| **TMLR** | **Rolling — any day** [CONFIRMED] | Strong (journal) | no fixed rate; merit-gated | 4 | Reviews on correctness/claims not novelty/hype; **no brand bias, no deadline** — structurally ideal for an independent author. |
| **NeurIPS 2027 ED track** | ~May 2027 [EST.] | Top | ~30–33% | 5 | The ideal home, one cycle later; buys time to add the causal-contract test (T1) + mitigations (T5). |
| **NeurIPS 2026 workshops** (MATH-AI, eval/trustworthy-ML) | ~Sep 2026 [EST. — CFPs post Aug–Sep] | Workshop | ~50–70%, often non-archival | 4 | Fast, low-risk visibility + expert feedback before a main-conf submission; MATH-AI explicitly wants reasoning-benchmark work. |
| **ICLR 2027 workshops** | ~Feb 2027 [EST.] | Workshop | ~50–70% | 4 | Same role as above, later in the calendar. |
| **IEEE T-Education / FIE / EDUCON / ICALT** | rolling / ~Jan–Feb 2027 [EST.] | Mid (education) | ~30–45% | 2 | **Anti-recommend.** Wrong audience: this is an ML-eval contribution, not a pedagogy study; buries the ML novelty. |
| **EDA venues (DAC / ICCAD / DATE / ISCAS)** | varies | Strong (in EDA) | ~20–25% | 1 | **Anti-recommend.** They care about circuit *design automation*; the paper is about LLM behavior, not EDA. Total audience mismatch. |

---

## Gotchas that matter for this specific paper

- **NeurIPS ED track / all NeurIPS tracks:** double-blind by default; a benchmark/generator is a "reusable executable artifact" → **code + data submission is mandatory**, not optional. Your procedural generator + rule-based grader must be release-ready.
- **ICLR 2027:** double-blind, OpenReview (public rebuttals), 9-page main + appendix. Notification **Jan 22, 2027** — camera-ready well before the Apr 2027 meeting in Brazil.
- **AAAI-27:** **7 pages main content, max 9 with references only** — a hard squeeze for a 5-topology benchmark with tables; supplementary/code due **Jul 31, 2026**. Two-phase review (Phase-1 desk rejects ~Sep 24).
- **EAAI-27:** the dates surfaced (Jul 21/28) may be conflated with the AAAI main track — historically EAAI runs later (Sep–Nov). **Verify on the EAAI-27 call page before relying on it.** Also requires in-person presentation.
- **ARR path (EMNLP/EACL/ACL):** binding venue declaration at submission; the Aug 3 cycle only reaches **EACL 2027**, and reviewers will read a circuits paper as out-of-scope NLP. Weakest fit-per-effort of the credible options.
- **TMLR:** no "acceptance rate" in the conference sense — decision is "are the claims supported?" Your **rule-based deterministic grader + NGSPICE/SymPy dual verification** is exactly what TMLR reviewers reward, and it neutralizes the judge-dependence critique before they raise it. Downside: journal, so less "conference buzz."
- **All of them:** the v1 headline (N=100, LLM judge at κ≈0.57) will be attacked. v2 must ship the **N≥500 procedural generator + McNemar paired tests + deterministic compliance grader** *before* any of these submissions, or the same reviewers who'd accept it will reject it.

---

## Recommendation

**Primary target — ICLR 2027 (abstract Sep 19, paper Sep 24, 2026).**
It is the single earliest top-tier deadline that both (a) fits the paper thematically (reasoning + benchmarks + a light-alignment/mitigation angle) and (b) is reachable within the stated 2–4-month M5 experiment window. Reviewers there will accept "runs entirely on local open-weights" as a *reproducibility strength*, not a limitation. The T1 causal convention-contract manipulation is the one addition that turns this from "diagnostic benchmark v1.5" into an ICLR-caliber causal claim — prioritize it.

**Backup — TMLR (submit whenever results are locked, ~Oct–Nov 2026).**
This is the risk-adjusted hedge and, honestly, the smartest fit for an *independent researcher without a lab brand*: TMLR judges the artifact, not the affiliation, and there is no deadline to miss. If the ICLR run slips or the September crunch compromises quality, roll straight into TMLR with no lost time. A TMLR acceptance is a citable, archival, credibility-building result — and you can still spin a workshop version for visibility.

**Stretch — NeurIPS 2027 Evaluations & Datasets track (~May 2027).**
The genuinely ideal home: a track explicitly re-scoped around evaluation-as-science, at the highest-prestige venue, with ~10 months to layer in mitigations (T5), the mechanistic reasoning-trace taxonomy (T6), and domain expansion (T7). This is where "CircuChain" becomes a flagship rather than a note. Use the intervening months and a **NeurIPS 2026 workshop paper (~Sep deadline, e.g. MATH-AI)** to get early expert feedback and a citable stake in the ground.

### Why this shape (accounting for your three constraints)
1. **Benchmark-heavy:** ICLR, NeurIPS-ED, COLM, and TMLR all actively want benchmark/eval contributions and require the code release you'll produce anyway; the AAAI 7-page cap and the ACL "NLP" framing both fight the paper — hence they're not primary.
2. **Needs M5 experiment time:** AAAI/EAAI (~3 weeks out) are effectively unreachable at quality; ICLR's Sep 24 aligns almost exactly with a July-start, 2–3-month local run; TMLR removes the clock entirely.
3. **Independent, no big-lab brand:** TMLR (merit-gated, affiliation-blind) and COLM (community-friendly to LLM-eval work) are the two venues where brand matters least; the free, local, fully-reproducible M5 pipeline is your differentiator — lead with it.

### Concrete timeline
- **Now → mid-Aug 2026:** freeze v2 scope; build procedural generator (N≥500) + deterministic rule-based compliance grader + wider local model panel; wire NGSPICE + SymPy dual verification into CI.
- **mid-Aug → mid-Sep 2026:** run the full local sweep on M5; add the **T1 causal convention-contract Latin square** (the missing causal test) and paired McNemar analysis.
- **Earliest credible top-tier submission:** **ICLR 2027, Sep 24, 2026** — tight but real if experiments start immediately. If quality isn't there by ~Sep 10, **do not force it.**
- **Best risk-adjusted plan:** ship a **NeurIPS 2026 workshop short paper (~Sep)** for feedback → submit the full paper to **TMLR (Oct–Nov)** *or* **ICLR 2027** if ready → position the expanded version (mitigations + domain expansion) for **NeurIPS 2027 ED (May 2027)** or **COLM 2027 (Mar 2027)**.

---

### Sources
- [NeurIPS 2026 Evaluations & Datasets CFP](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets) · [NeurIPS 2026 Dates](https://neurips.cc/Conferences/2026/Dates) · [NeurIPS 2026 Call for Workshops](https://neurips.cc/Conferences/2026/CallForWorkshops)
- [ICLR 2026/2027 Dates](https://iclr.cc/Conferences/2026/Dates) · [ICLR 2027 (AI Deadlines)](https://mlciv.com/ai-deadlines/conference/?id=iclr27)
- [COLM 2026 Key Dates](https://colmweb.org/dates.html) · [COLM 2026 CFP](https://colmweb.org/cfp.html)
- [AAAI-27 main](https://aaai.org/conference/aaai/aaai-27/) · [AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/) · [EAAI-27 Call](https://aaai.org/conference/aaai/aaai-27/eaai-27-call/)
- [EMNLP 2026 Call for Main Conference Papers](https://2026.emnlp.org/calls/main_conference_papers/) · [ACL Rolling Review — Dates and Venues](https://aclrollingreview.org/dates)
- [TMLR (JMLR)](http://jmlr.org/tmlr/) · [TMLR on OpenReview](https://openreview.net/group?id=TMLR)
- [MATH-AI Workshop (NeurIPS)](https://mathai2024.github.io/cfp/)

*Flag for live re-check before acting: EAAI-27 exact dates; COLM 2027 and NeurIPS 2027 ED deadlines (not yet posted); NeurIPS/ICLR 2026–27 workshop CFP dates.*