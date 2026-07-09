I have enough current data. Here is the feasibility analysis.

---

# CircuChain v2 — Local Inference Feasibility on Apple M5

**Verdict: Feasible and, in fact, a good strategic fit — but only on an M5 *Max* (ideally 128 GB). The entire 10-model × N=500 solver sweep is a ~3.5–6 day single-machine batch job; the sole real bottleneck is *dense 70B models emitting long chain-of-thought*, which you should engineer around by putting your top reasoning tier on a sparse MoE.**

> **Confidence key used throughout:** ✅ well-sourced · ⚠️ extrapolated (M3/M4 → M5, or from partial data) · 🔮 model/spec is H1-2026 and past my Jan-2026 cutoff — **verify before citing in the paper.**

---

## 0. Gating hardware assumption (read this first)

The whole budget hinges on *which* M5 the author actually has, because unified-memory capacity sets the model ceiling and bandwidth sets the speed. ✅ from Apple/Wikipedia/Notebookcheck:

| Chip | GPU cores | Unified-mem options | Peak mem bandwidth | LLM ceiling (4-bit) |
|---|---|---|---|---|
| **M5 (base)** | 10 | up to **32 GB** | **~153 GB/s** | comfortably ≤14B; one 30B-A3B MoE is *tight*; no dense 70B |
| **M5 Pro** | up to ~16 | up to **64 GB** | up to **~307 GB/s** | dense 32B fine; dense 70B-4bit *tight* (~40 GB weights + KV + OS); no gpt-oss-120b |
| **M5 Max** | 32 / 40 | up to **128 GB** | **460** (32c) / **614 GB/s** (40c) | everything incl. gpt-oss-120b, Llama 4 Scout, dense 70B |
| **M5 Ultra** 🔮 | ~two-Max | rumored 96–256 GB | rumored >600 GB/s | not shipping as of 2026-07; **do not plan around it** |

**Recommendation:** target an **M5 Max, 40-core GPU, 128 GB** (614 GB/s). It is the only config that runs the full scale ladder *and* the sparse-80B/120B tier without swapping. A 64 GB M5 Pro is a viable "everything except the 120B-class MoE" fallback. A 32 GB base M5 forces you to drop the 70B tier entirely — publishable, but you lose the most interesting large-scale reasoning point. If it's a laptop (MacBook Pro) rather than a Mac Studio, ⚠️ expect ~5–15% sustained-clock throttling over multi-day runs; a Studio (or aggressive cooling) sustains full clocks.

Note also that a reasoning model generating 3–8k CoT tokens needs KV cache on top of weights (⚠️ ~1–5 GB depending on size/GQA/context), so budget weights **+ KV + ~12 GB for macOS**.

---

## (a) Recommended local inference stack: **MLX-primary, llama.cpp/Ollama as fallback + provenance anchor**

**Use `mlx-lm` as the primary scored-run engine, with a thin backend abstraction so any model can also run through llama.cpp/GGUF.**

Why MLX is the right default (✅):
- **Fastest on Apple Silicon** — MLX is roughly **2–3× Ollama and ~1.5× llama.cpp** for single-stream decode, and it's the *only* runtime that exploits the M5's per-core **Neural Accelerators**. Apple's own M5 write-up measured **~1.19–1.27× faster token generation and up to ~4× faster time-to-first-token vs M4** — the TTFT win comes precisely from those matrix units, and it matters because your prompts (topology + values + convention contract + method) are prefill-heavy.
- **Python-native harness integration** — trivial to set `temp=0`, pin a seed, cap `max_tokens`, and capture *both* the `<think>` trace and the final answer per call (essential for your T6 reasoning-trace taxonomy).
- **Native quant support** for 4-bit, 8-bit, and **MXFP4** (needed for gpt-oss).
- **Convergence bonus** (🔮 2026-03): Ollama announced it is *switching its Apple-Silicon backend to MLX*, and its MLX runner already covers the Llama, Qwen3/3.5, and Gemma 3 families — so "Ollama for convenience, MLX for the official numbers" is one ecosystem, not two.

The one real caveat for a *reproducibility* benchmark (⚠️): **MLX has framework-level floating-point nondeterminism** — greedy temp=0 is stable in practice but not bit-exact-guaranteed across versions/machines. Mitigations that make this a non-issue for CircuChain:
1. Your v2 grading is **numeric-with-tolerance + a rule-based deterministic compliance grader**, so sub-ULP sampling jitter does not flip labels.
2. **Log full provenance per call**: model + weight-file SHA, quant, `mlx`/`mlx-lm` version, seed, prompt hash, backend.
3. **Ship a second path through llama.cpp/GGUF** for the headline models. GGUF files have stable hashes and port across machines, giving reviewers a portable determinism check ("headline gaps reproduce on both engines"). Use llama.cpp/Ollama also as the **fallback for any architecture `mlx-lm` doesn't yet support**.

Net: **both engines, MLX for speed and the official run, llama.cpp/GGUF for portability + a reproducibility receipt.** This directly answers the reviewer critique that v1 was judge-dependent and closed-model-dependent.

---

## (b) Realistic runnable open models on M5 Max, mapped to the paper's axes

Tokens/sec are **decode throughput on M5 Max, 4-bit, single stream** — ⚠️ extrapolated from M4 Max real-world numbers + Apple's ~1.2× M5 generation uplift + published M5-Max benchmark tables (some of which reference not-yet-verified 🔮 model names, so treat ±30%). Prefill/TTFT is much faster and not the constraint. "CoT" = emits a parseable thinking trace.

| Tier | Model | Params (total / active) | Axis | Quant | ~RAM | ~tok/s (decode) | CoT | Notes |
|---|---|---|---|---|---|---|---|---|
| **~3–4B** | **Qwen3-4B-Thinking-2507** | 4B | reasoning | 4-bit | ~2.5 GB | **120–150** | ✅ `<think>` | best tiny reasoner |
| | Qwen3-4B (non-think mode) | 4B | base/instruct | 4-bit | ~2.5 GB | 120–150 | opt | same weights, thinking off |
| | Gemma 3 4B | 4B | base (multimodal) | 4-bit | ~3 GB | ~120 | ✗ | family diversity |
| | Phi-4-mini (3.8B) | 3.8B | base | 4-bit | ~2.5 GB | ~120 | ✗ | |
| | SmolLM3-3B ✅ | 3B | base (has think mode) | 4-bit | ~2 GB | ~150 | opt | |
| **~7–9B** | **DeepSeek-R1-Distill-Qwen-7B / -Llama-8B** | 7–8B | reasoning | 4-bit | ~5 GB | **90–120** | ✅ `<think>` | distinct lineage |
| | Qwen3-8B | 8B | hybrid (reasoning-capable) | 4-bit | ~5 GB | 90–110 | ✅ | thinking toggle |
| | **Llama-3.1-8B-Instruct** | 8B | base/non-reasoning | 4-bit | ~5 GB | 100–130 | ✗ | clean base control |
| **~14B** | **Qwen3-14B** | 14B | hybrid reasoning | 4-bit | ~8.5 GB | **55–65** | ✅ | best within-model reasoning toggle |
| | DeepSeek-R1-Distill-Qwen-14B | 14B | reasoning | 4-bit | ~8.5 GB | 55–65 | ✅ | |
| | Phi-4 (14B) | 14B | base/non-reasoning | 4-bit | ~8.5 GB | 55–65 | ✗ | strong non-reasoning point |
| | Phi-4-reasoning (14B) ✅ | 14B | reasoning | 4-bit | ~8.5 GB | 55–65 | ✅ | reasoning sibling of Phi-4 |
| **~30–32B** | **Qwen3-30B-A3B-Thinking-2507** (MoE) | 30B / **3B** | reasoning | 4-bit | ~17 GB | **70–90** | ✅ | **best value large reasoner** (MoE → cheap decode) |
| | Qwen3-32B (dense) | 32B | hybrid reasoning | 4-bit | ~19 GB | 28–38 | ✅ | dense = slower |
| | DeepSeek-R1-Distill-Qwen-32B | 32B | reasoning | 4-bit | ~19 GB | 28–38 | ✅ | |
| | **gpt-oss-20b** (MoE) | 21B / ~3.6B | reasoning (o3-mini-class) | **MXFP4** | ~13 GB | 55–70 | ✅ harmony channels | OpenAI-lineage open reasoner |
| | Gemma 3 27B | 27B | base/non-reasoning | 4-bit | ~16 GB | 30–40 | ✗ | family diversity, multimodal |
| | Mistral Small 3.2 24B / **Magistral Small** | 24B | base / **reasoning** | 4-bit | ~14 GB | 38–48 | ✗ / ✅ | Magistral = reasoning sibling |
| **~70B** | **DeepSeek-R1-Distill-Llama-70B** (dense) | 70B | reasoning | 4-bit | ~40 GB | **12–18** | ✅ `<think>` | **the bottleneck** (dense × long CoT) |
| | **Llama-3.3-70B-Instruct** (dense) | 70B | base/non-reasoning | 4-bit | ~40 GB | 12–18 | ✗ | *same base as the distill above* → natural experiment |
| | **Qwen3-Next-80B-A3B** (MoE) 🔮 | 80B / **3B** | reasoning/instruct | 4-bit | ~45 GB | **40–60** | ✅ | **recommended top tier** — ~70B-class quality at MoE speed |
| | gpt-oss-120b (MoE) | 117B / ~5.1B | reasoning | MXFP4 | ~64 GB | 40–60 | ✅ | needs 96–128 GB |
| | Llama 4 Scout (MoE) | 109B / 17B | base multimodal | 4-bit | ~60 GB | 30–50 | ✗ | needs 96–128 GB |

🔮 **Newer-than-cutoff releases to verify live before committing:** Qwen3-Next-80B-A3B (Sept 2025, likely real), Qwen3.5 (reported open-weights Feb 2026), and anything labeled "Qwen 3.6 / Qwen 4 / Gemma 4 / Phi-5 / Llama 5" that appears on benchmark-aggregator sites — several of those look like SEO-extrapolated future models and **should not be cited without a HuggingFace/official confirmation.** Confirmed-real as of my cutoff: the whole Qwen3 lineup incl. Thinking-2507 variants, DeepSeek-R1 distills (Jan 2025), Llama 3.3 / Llama 4 Scout & Maverick (Apr 2025), gpt-oss-20b/120b (Aug 2025, MXFP4), Gemma 3, Phi-4 / Phi-4-reasoning, Mistral Small 3.x + Magistral.

**Two "natural experiments" this table hands you for free — worth foregrounding in v2:**
1. **DeepSeek-R1-Distill-Llama-70B vs Llama-3.3-70B-Instruct** — literally the same base weights, differing only by reasoning SFT. A clean causal probe of whether reasoning-tuning *changes* Convention-Blindness at fixed capacity.
2. **Qwen3 thinking-on vs thinking-off** (4B/8B/14B/32B) — a within-model reasoning toggle at four scales.
These give you a reasoning×base contrast that is *controlled*, not just correlational — much stronger than v1's cross-vendor comparison.

---

## (c) Throughput + wall-clock budget

**Work unit.** N instances × 2 methods (Mesh/KVL, Nodal/KCL) = **2N scored calls per model**. So N=500 → **1,000 calls/model**; N=1000 → **2,000 calls/model**. On one M5, **GPU-hours ≈ wall-clock hours** (single GPU), reduced by batching (below).

**The dominant variable is output length, not input.** ⚠️ Central estimates: prompts ~400–800 input tokens (fast prefill); **non-reasoning output ~300–600 tok** (call it 450); **reasoning CoT ~2,000–4,000 tok** (call it 3,000, heavy tail to 8k+). Per-call time ≈ output_tokens / decode_tok_s + ~1.5 s overhead.

**Per-model wall-clock at N=500 (1,000 calls), single stream, no batching:**

| Model (role) | tok/s | out tok | s/call | **hours @ N=500** |
|---|---|---|---|---|
| Qwen3-4B-Thinking (reason) | 130 | 3000 | 24.6 | **6.8** |
| Llama-3.1-8B (base) | 110 | 450 | 5.6 | 1.6 |
| DS-R1-Distill-Qwen-8B (reason) | 100 | 3000 | 31.5 | 8.8 |
| Qwen3-14B (reason) | 60 | 3000 | 51.5 | 14.3 |
| Phi-4-14B (base) | 60 | 450 | 9.0 | 2.5 |
| gpt-oss-20b (reason) | 65 | 3000 | 47.6 | 13.2 |
| Qwen3-30B-A3B-Thinking · MoE (reason) | 80 | 3000 | 39.0 | 10.8 |
| Gemma-3-27B (base) | 35 | 450 | 14.4 | 4.0 |
| Qwen3-Next-80B-A3B · MoE (reason) 🔮 | 50 | 3000 | 61.5 | 17.1 |
| Llama-3.3-70B (base, short output) | 15 | 450 | 31.5 | 8.8 |
| **Total (this 10-model panel)** | | | | **≈ 88 GPU-h ≈ 3.7 days** |

Double it for **N=1000 → ≈ 175 GPU-h ≈ 7.3 days.**

**The bottleneck, quantified.** Notice the 70B *base* model is cheap (~9 h) because its output is short. The pain is **dense-70B × long CoT**: swapping the MoE top tier for **DeepSeek-R1-Distill-Llama-70B** (dense, 15 tok/s, 3,000 CoT tokens) costs **~56 h for that one model at N=500** — more than half the entire rest of the panel. A dense-32B reasoner (Qwen3-32B, ~32 tok/s) is the second-worst at ~26 h. **Rule: never put a *dense* large model on the long-CoT path.** Sparse MoE at the top (80B-A3B / gpt-oss-120b, ~3–5B active) buys ~70B-class quality at 3–4× the decode speed.

**Levers that shrink the wall-clock (⚠️ magnitudes approximate):**
- **Batched / continuous-batching decode** — the single biggest lever. Running 8–16 prompts concurrently amortizes weight-bandwidth and can lift *aggregate* throughput **~2–3×** on the small/mid tiers (less on the 70B, which is already pure-bandwidth-bound). Realistically compresses the N=500 panel from ~88 h to **~50–70 h (~2–3 days)**. Note MLX batching is younger than vLLM's; llama.cpp's server has mature continuous batching if you need it.
- **Hard `max_tokens` cap** (e.g., 8192) bounds the CoT tail — and **run a 20-instance pilot first** to measure *actual* average output length per model, because a shift from 3,000 → 5,000 avg CoT multiplies every reasoning-model row by ~1.7×. Output-length is the largest single uncertainty in this whole budget.
- Skip 8-bit; 4-bit/MXFP4 is production-quality and roughly halves bandwidth pressure vs 8-bit.

**Bottom line for (c):** one M5 Max runs the full local sweep in **~2–4 days at N=500** and **~4–8 days at N=1000** (with batching), *provided the top reasoning tier is MoE*. Dense-70B reasoning pushes N=500 toward ~6 days on its own. Zero marginal dollar cost, no rate limits — exactly the "free scale" the v2 thesis wants.

---

## (d) Recommended local panel + frontier API ceiling

### Recommended 10-model local panel (max scientific coverage, sane compute)
Spans all five scale tiers × the reasoning/base axis, diversifies model families (Qwen, Llama, DeepSeek-distill, Phi, Gemma, OpenAI-oss), and embeds the two natural experiments. MoE at the top keeps it inside the ~2–4 day / N=500 budget above.

**Reasoning axis (6):**
1. Qwen3-4B-Thinking-2507 — small reasoner
2. DeepSeek-R1-Distill-Qwen-8B — mid reasoner, independent lineage
3. Qwen3-14B (thinking) — pairs with #? as toggle control
4. gpt-oss-20b (MXFP4) — OpenAI-lineage open reasoner
5. Qwen3-30B-A3B-Thinking (MoE) — large reasoner, cheap decode
6. **Qwen3-Next-80B-A3B (MoE)** 🔮 — top reasoner *(fallback if unavailable: gpt-oss-120b if 128 GB, else DeepSeek-R1-Distill-Qwen-32B)*

**Base / non-reasoning axis (4):**
7. Llama-3.1-8B-Instruct — 8B base control
8. Phi-4-14B — 14B base control
9. Gemma-3-27B-it — ~27B base, distinct family
10. **Llama-3.3-70B-Instruct** — 70B base *and* the controlled counterpart to the R1-Distill-Llama-70B reasoner

**Budget note on the 70B pair:** if you want the *dense-70B reasoner* (R1-Distill-Llama-70B) as a scientific point, add it as an **11th model run only at N=500** (~56 h) rather than N=1000; keep the MoE-80B as the routine top tier. The Llama-3.3-70B *base* (short output, ~9 h) is cheap and worth keeping for the natural experiment. On a 32 GB base M5, drop both 70B-class models and cap the top tier at the 30B-A3B MoE.

### Frontier closed models for a "ceiling" (add 2–3 via API)
For continuity with v1 (which used GPT-5, Claude Opus 4.5, o4-mini) and lineage diversity:
- **GPT-5** (direct v1 continuity, current top scorer)
- **Claude Opus 4.5** (v1's #2) — 🔮 use the newest Opus if a refresh shipped in H1-2026; verify
- **Gemini 2.5 Pro / 3 Pro** 🔮 — a third independent lineage; verify which is current

**Rough cost** (⚠️ pricing needs live verification; reasoning-token billing is the swing factor). Per model per full run ≈ (2N calls) × (~600 input + ~3,000 visible output + billed hidden-reasoning tokens, est. ~5,000 effective output). At representative frontier reasoning rates (~$2/M input, ~$10/M output):

| | input cost | output/reasoning cost | **≈ per model** |
|---|---|---|---|
| **N=500** (1,000 calls) | ~$1.2 | ~$50 | **~$50** |
| **N=1000** (2,000 calls) | ~$2.4 | ~$100 | **~$100** |

So **3 frontier models ≈ $150 (N=500) to $300 (N=1000)**, plus a small buffer for retries — call it **a few hundred dollars total**, and effectively **$0 for the LLM judge** since v2 replaces the judge with a rule-based grader. This is the cheap, high-value part of the study: the frontier trio is the "ceiling" line on every plot, the local panel is the science.

---

## Consolidated uncertainty flags
- ⚠️ **All tok/s are M5-Max extrapolations** (M4-Max real data × Apple's ~1.2× M5 generation uplift + aggregator tables); treat as ±30%, and re-measure on the actual machine before quoting in the paper.
- ⚠️ **Output-token length is the biggest budget risk** — a 3,000→5,000 avg CoT shift inflates every reasoning row ~1.7×. Pilot-measure it.
- 🔮 **Verify H1-2026 model existence/names** (Qwen3-Next / Qwen3.5, and reject unverified "Qwen4/Gemma4/Phi-5/Llama5" aggregator entries) and **frontier API prices + current Opus/Gemini versions** — all past my Jan-2026 cutoff.
- 🔮 **M5 Ultra is not shipping** as of 2026-07; plan around **M5 Max 128 GB**.
- ⚠️ **MLX nondeterminism** is real but harmless here given tolerance-based + rule-based grading; mitigate with logged provenance and a llama.cpp/GGUF cross-check.
- ⚠️ **Sustained thermals** on a MacBook (vs Mac Studio) may cost 5–15% over multi-day runs.

**Sources:** [Apple M5 newsroom](https://www.apple.com/newsroom/2025/10/apple-unleashes-m5-the-next-big-leap-in-ai-performance-for-apple-silicon/) · [Apple M5 (Wikipedia)](https://en.wikipedia.org/wiki/Apple_M5) · [Apple M5 Pro/Max newsroom](https://www.apple.com/uk/newsroom/2026/03/apple-debuts-m5-pro-and-m5-max-to-supercharge-the-most-demanding-pro-workflows/) · [Apple ML Research: LLMs with MLX on M5](https://machinelearning.apple.com/research/exploring-llms-mlx-m5) · [MLX vs llama.cpp on Apple Silicon](https://yage.ai/share/mlx-apple-silicon-en-20260331.html) · [Comparative study MLX/Ollama/llama.cpp (arXiv 2511.05502)](https://arxiv.org/pdf/2511.05502) · [Apple Silicon LLM benchmarks by chip](https://llmcheck.net/benchmarks) · [Qwen3 report](https://arxiv.org/pdf/2505.09388) / [Qwen3 repo](https://github.com/QwenLM/Qwen3) · [DeepSeek-R1 Distill](https://deepseekai.guide/models/deepseek-r1-distill/) · [Llama 4 blog](https://ai.meta.com/blog/llama-4-multimodal-intelligence/) · [Introducing gpt-oss](https://openai.com/index/introducing-gpt-oss/)