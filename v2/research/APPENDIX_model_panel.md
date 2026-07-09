The landscape has moved since the Jan-2026 cutoff in ways that materially improve the panel. Two findings reshape the design: **Qwen3.5** shipped as a full single-generation size ladder (Apache-2.0, Feb–Mar 2026) — a near-perfect clean scaling family — and **Qwen3-Next-80B-A3B** ships as separate **-Instruct** and **-Thinking** checkpoints off the same base, which is the cleanest reasoning-tuning ablation you can buy. Frontier ceiling is now GPT-5.5/5.6, Claude Opus 4.8, Gemini 3.1/3.5 Pro. Here is the design doc.

---

# CircuChain v2 — Model Panel & Experimental Factor Design

*Compiled 2026-07-09. Marker key: ✅ confirmed live this session · ⚠️ extrapolated / needs re-measure on the actual M5 · 🔮 H1-2026 release past my training cutoff, corroborated by ≥1 live source but verify the exact checkpoint before you freeze the panel.*

## 0. Design principle

v1's fatal weakness was that its model comparison was a **cross-vendor leaderboard** (GPT-5 vs Opus vs o4-mini) — correlational, confounded, and underpowered. v2's panel is built as a **factorial ablation** so the paper can say *what causes* the compliance-competence trade-off, not just *that* it exists. Three orthogonal factors, each with at least one **clean controlled contrast** (same base or same family, one thing varied):

| Factor | What varies | What's held fixed | Clean contrast |
|---|---|---|---|
| **F1 Reasoning-tuning** | ± long-CoT post-training | base weights, params, pretrain data | C1, C2 |
| **F2 Scale** | parameter count | family, generation, training recipe | C3 |
| **F3 Openness / frontier ceiling** | open-local → open-frontier → closed | task, grader | tier structure |

---

## 1. The panel (13 primary + 2 optional = up to 15)

### Tier A — Local open-weights on M5 Max 128 GB (the causal core, 10 models)

**Scale ladder — Qwen3.5 dense family** 🔮 *(released as a size-matched set Feb 24–Mar 2 2026, Apache-2.0, HF+ModelScope; run all four rungs in one fixed inference mode so the only thing that changes is parameter count):*

| # | Model | Params | Role tag | ~4-bit RAM / decode ⚠️ |
|---|---|---|---|---|
| 1 | **Qwen3.5-2B** | 2B (dense) | `SCALE-L1` | ~1.5 GB / ~140 tok/s |
| 2 | **Qwen3.5-4B** | 4B (dense) | `SCALE-L2` | ~2.5 GB / ~120 tok/s |
| 3 | **Qwen3.5-9B** | 9B (dense) | `SCALE-L3` | ~5.5 GB / ~95 tok/s |
| 4 | **Qwen3.5-27B** | 27B (dense) | `SCALE-L4` / Qwen anchor | ~16 GB / ~35 tok/s |

**Reasoning-tuning pair A (top open reasoner tier, MoE)** ✅ *both checkpoints confirmed on HF:*

| # | Model | Params (total/active) | Role tag |
|---|---|---|---|
| 5 | **Qwen3-Next-80B-A3B-Instruct** | 80B / 3B | `REASON-OFF` (control) |
| 6 | **Qwen3-Next-80B-A3B-Thinking** | 80B / 3B | `REASON-ON` |

**Reasoning-tuning pair B (70B dense, independent lineage)** ✅:

| # | Model | Params | Role tag |
|---|---|---|---|
| 7 | **Llama-3.3-70B-Instruct** | 70B (dense) | `BASE-70B` |
| 8 | **DeepSeek-R1-Distill-Llama-70B** | 70B (dense) | `REASON-70B` (SFT of #7's base) |

**Lineage-diversity anchors** ✅:

| # | Model | Params | Role tag |
|---|---|---|---|
| 9 | **gpt-oss-20b** (MXFP4) | 21B / ~3.6B | `REASON-oss` (OpenAI open lineage) |
| 10 | **Gemma-3-27B-it** | 27B (dense) | `BASE-Gemma` (Google lineage; capability-matched to #4) |

### Tier B — Open-frontier via cheap API (optional, 2 models — reproducible frontier scale)

These are **open-weight** but too large for 128 GB locally, so run them through a commodity inference API (Together / Fireworks / DeepInfra). They preserve reproducibility (anyone can re-host the weights) while extending the curve past the local ceiling:

| # | Model | Params | Role tag |
|---|---|---|---|
| 14 | **Qwen3.5-397B-A17B** 🔮 | 397B / 17B | `OPEN-FRONTIER` — extends the **same** Qwen3.5 scaling curve to near-frontier |
| 15 | **DeepSeek-V4** 🔮 (MIT) | ~284B-class MoE | `OPEN-FRONTIER` — independent lineage reasoner |

### Tier C — Closed frontier ceiling (3 models — v1 continuity + absolute ceiling)

| # | Model | Role tag | v1 lineage continuity |
|---|---|---|---|
| 11 | **GPT-5.5** 🔮 (or GPT-5.6 "Sol" preview) | `CLOSED-ceiling` | v1 used GPT-5 |
| 12 | **Claude Opus 4.8** 🔮 | `CLOSED-ceiling` | v1 used Opus 4.5 |
| 13 | **Gemini 3.1 Pro** 🔮 (or 3.5 Pro when GA) | `CLOSED-ceiling` | third independent lineage |

**Fallbacks if a 🔮 checkpoint isn't runnable at freeze time:** scale ladder → Qwen3 dense (1.7B/4B/8B/14B/32B, all ✅); top reasoner → gpt-oss-120b (needs the 128 GB) or DeepSeek-R1-Distill-Qwen-32B; if Qwen3.5 lacks MLX conversions, pull GGUF and run Tier A through llama.cpp.

---

## 2. The clean controlled contrasts (this is what a reviewer looks for)

- **C1 — Reasoning-tuning at fixed base/params (MoE):** #5 vs #6. Same pretrained base, same 80B/3B, differ *only* in Instruct vs Thinking post-training. Isolates F1 with zero capacity confound.
- **C2 — Reasoning-tuning at fixed base (dense, different lineage):** #7 vs #8. Llama-3.3-70B base with vs without R1 reasoning-distillation SFT. Replicates C1 in a second family → rules out "it's a Qwen artifact."
- **C3 — Pure parameter scaling at fixed generation/recipe:** #1→#2→#3→#4. One family, one training run's data/recipe, dense throughout (no MoE confound), only param count moves. This is the cleanest scaling test in the open-weights world right now *because Qwen3.5 shipped the sizes simultaneously.*
- **C4 (bonus, if Qwen3.5 retains the hybrid `/think` toggle 🔮) — within-model reasoning switch across the whole ladder:** run rungs #1–#4 think-on and think-off → a **scale × reasoning 4×2 factorial** from one weight set. On the closed tier, the analogous switch is **reasoning-effort high vs minimal** on GPT-5.5 / Gemini 3.x.

Contrasts C1 and C2 are the headline causal claims; C3 grounds the scaling story; C4 (if available) is the strongest single figure in the paper.

---

## 3. Hypotheses and confirm/refute conditions

Grading uses the v2 **deterministic rule-based compliance grader** + tolerance-numeric competence grader (no LLM judge). Primary test statistic: **McNemar paired test** on per-subtask error labels within each contrast; report separately for **compliance error rate** (SIGN + METHOD contract violations) and **competence error rate** (PHYSICS + CALC + HALLUC).

**H1 — The trade-off is *driven by reasoning-tuning*.**
Prediction: within C1 and C2, the reasoning variant shows **↓ competence error, ↑ (or flat) compliance error** vs its non-reasoning twin. This is the direct in-domain test of the H1-2026 "thinking regresses on constraint-following" wave (Format Tax / "When Built-in Thinking Helps and Hurts").
- *Confirms v1 story* if both pairs move down-and-right on the (compliance-err, competence-err) plane.
- *Refutes* if reasoning-tuning improves **both** axes → convention-blindness is just a capability gap, not a trade-off.

**H2 — Competence scales, compliance does not.**
Prediction: along C3, competence error falls ~monotonically with params while compliance error is **flat or rising**. Mirrors v1's signature (GPT-5 ~0% competence / 34% compliance).
- *Confirms* if the two curves diverge (scale buys physics, not obedience).
- *Refutes the whole thesis* if compliance error **also** falls monotonically with scale — then "Convention Blindness" is a small-model artifact scale erases, and CircuChain's central claim collapses. **The design is explicitly built to detect this failure mode.** (Report the McNemar and a monotonic-trend test, e.g. Cochran-Armitage, across rungs.)

**H3 — Universality vs recipe-specificity (RLHF/lineage).**
Compare the trade-off's presence across Qwen, Llama, DeepSeek, Gemma, OpenAI-oss (Tier A) at matched capability.
- *Strong general claim* if the down-right trade-off appears in **every** lineage and in the closed tier → it's a property of instruction-tuned LLMs, not one vendor's RLHF.
- *Weaker, still-publishable claim* if it's lineage-specific → convention-blindness is a post-training-recipe artifact (name which recipes).

**H4 — Does the trade-off survive at frontier scale? (open-vs-closed).**
Prediction: Tier C (and Tier B) sit at the **extreme high-competence / high-compliance-error corner**, extending — not breaking — the Pareto frontier the open ladder traces.
- *Confirms* if frontier models push competence error → ~0 while compliance error stays elevated (GPT-5's 34% in v1).
- *Refutes* if frontier models have **low compliance error too** → the trade-off was an N=100, small-model fluke; v1's headline doesn't generalize. Tier B (open-frontier) disambiguates whether any "frontier fix" is a scale effect or a closed-lab-secret-sauce effect.

**One-line summary of the falsification target:** if *both* error types fall monotonically with *both* scale and reasoning-tuning, the trade-off dissolves into "weak models are weak" and the paper's thesis dies — every contrast above is positioned to catch that.

---

## 4. Sampling / seed / repeat / reproducibility protocol

**Decoding.**
- **temp = 0 (greedy)** on every model that supports it via `mlx-lm --temp 0` / llama.cpp `--temp 0`. For any model that degenerates into CoT loops at greedy (some R1-distills do), fall back to **temp 0.2, top-p 0.95** and flag those rows; never mix within a contrast.
- Closed APIs: temp 0 where permitted, **reasoning-effort fixed and logged**, and pin the dated snapshot string (e.g. `gpt-5.5-2026-mm-dd`) because closed endpoints drift silently between runs.
- **`max_tokens` cap:** 8,192 (non-reasoning) / 16,384 (reasoning), with a **truncation flag** logged per call. Run a **20-instance pilot per model first** to measure *actual* mean CoT length — output length is the single largest wall-clock and variance driver (a 3k→5k CoT shift inflates every reasoning row ~1.7×).

**Repeats (k).**
- k = 1 for the cheap non-reasoning small models (#1–#3, #10) — near-deterministic under greedy.
- **k = 3** for all reasoning models (#6, #8, #9, think-mode rungs) and all Tier B/C models — bounds CoT-length variance; report **mean ± 95% CI** and a **majority-vote label** per subtask.
- **k = 5** for the two headline causal pairs (C1: #5/#6, C2: #7/#8) — tightens the CI on the McNemar deltas that carry the paper.

**Handling Metal/MLX non-determinism.**
- MLX greedy is stable in practice but **not bit-exact** across versions/machines. This is harmless here because grading is **tolerance-numeric + rule-based deterministic** → sub-ULP jitter cannot flip a label.
- **Quantify the noise floor once:** pick one reasoning model, run k=10 same-seed vs k=10 varied-seed, and report the label-flip rate as the benchmark's intrinsic noise floor (this pre-empts "is your effect bigger than your jitter?").
- **Cross-engine determinism receipt:** re-run the headline models through **llama.cpp/GGUF** (stable file hashes, portable across machines) and show the headline gaps reproduce on both engines — this directly answers v1's "closed/judge-dependent" critique.

**Provenance logged per call** (committed to the release repo): model id + **weight-file SHA-256**, quant, `mlx`/`mlx-lm`/`llama.cpp` version, backend, seed, sampler params, prompt hash, raw `<think>` trace + final answer, token counts, truncation flag, wall-clock. **CI** re-runs a 20-instance smoke test through both engines on every commit.

---

## 5. Honest limitation of a mostly-open panel — and how the ceiling patches it

**The gap:** the largest models that fit M5 Max 128 GB top out around **80B-A3B / 122B-A10B MoE and 70B dense**. No trillion-parameter *open* model runs locally, so **Tier A alone cannot tell you whether the trade-off survives at true frontier scale** — it's conceivable the very largest models finally break convention-blindness, and a local-only panel would never see it. That is exactly the "small-model artifact" objection a reviewer will raise against H2/H4.

**The two-part patch:**
1. **Tier B (open-frontier via commodity API)** — Qwen3.5-397B-A17B and DeepSeek-V4 give **reproducible frontier scale**: open weights anyone can re-host, extending the *same* Qwen3.5 scaling curve past the local ceiling. This separates a genuine scale effect from a closed-lab-secret-sauce effect — the crucial disambiguation for H4.
2. **Tier C (closed frontier)** — GPT-5.5/5.6, Opus 4.8, Gemini 3.x anchor the absolute top of the competence axis and preserve **direct lineage continuity with v1** (GPT-5, Opus, Gemini). They are the "ceiling line on every plot," *not* part of the causal core.

**Stated plainly in the paper:** all causal claims (H1, H2, H3) rest on **Tier A**, where weights, quant, seeds, and traces are fully controlled and released. **Tier C is generalization-only**, and carries three honest caveats: (a) closed checkpoints are moving targets that may have changed since v1; (b) hidden reasoning tokens make the T6 trace taxonomy impossible on them, so they're excluded from any mechanistic analysis; (c) they're non-reproducible, so they never carry a headline number — only the "does the frontier extend or break the trend" verdict. Tier B is the bridge that keeps a frontier-scale claim reproducible.

---

## Verify-live before freezing the panel
- 🔮 **Qwen3.5** exact size list, license, and whether the dense rungs retain a hybrid `/think` toggle (decides whether C4 factorial is available). Also whether **Qwen3.6** (surfaced in June-2026 sources) has superseded it with a comparable simultaneous size ladder — if so, promote 3.6 to the scale family. HF: `Qwen/Qwen3.5-*`.
- 🔮 **DeepSeek-V4** real memory footprint at 4-bit (one source claims "best on 64 GB," which is inconsistent with 284B total — confirm it's Tier-B-API, not Tier-A-local).
- 🔮 Current **frontier snapshot strings + reasoning-effort API** for GPT-5.5/5.6, Opus 4.8, Gemini 3.1/3.5 Pro, and whether any (e.g. Claude Fable 5) is access-restricted.
- ⚠️ **Re-measure all tok/s and RAM on the actual M5** before quoting; MLX conversions (`mlx-community/*`) exist for each Tier-A model, else route through GGUF/llama.cpp.

**Sources:** [Qwen3-Next-80B-A3B-Thinking (HF)](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Thinking) · [Qwen3-Next-80B-A3B-Instruct (HF)](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) · [Qwen 3.5 open-weights guide](https://codersera.com/blog/qwen-3-5-complete-guide-2026/) · [Qwen (Wikipedia)](https://en.wikipedia.org/wiki/Qwen) · [LM Council benchmarks Jul 2026](https://lmcouncil.ai/benchmarks) · [llm-stats AI updates Jul 2026](https://llm-stats.com/llm-updates) · [Anthropic Claude Sonnet 5 / Opus 4.8 (TechCrunch)](https://techcrunch.com/2026/06/30/anthropic-launches-claude-sonnet-5-as-a-cheaper-way-to-run-agents/) · [Ollama June 2026 top open models](https://www.promptquorum.com/local-llms/top-open-source-models-ollama) · [Apple Silicon LLMs / MLX 2026](https://codersera.com/blog/apple-silicon-llms-complete-guide-2026/)