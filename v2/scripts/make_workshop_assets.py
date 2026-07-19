"""Assets for the COLM Efficient-Reasoning workshop paper.

Produces paper/workshop/generated/:
  wmacros.tex        numbers (reasoning-economics + reuse of frozen headline stats)
  table_trunc.tex    per-scale think-mode truncation/compute table body
  fig_invariance.pdf/png   reversion-vs-competence scatter (the flat band)
  fig_gpt5_effort.pdf/png  GPT-5 reasoning-effort ladder: completion vs cost

GPT-5 effort-ladder provenance (measured 2026-07-17, this repo):
  default effort : 119-row run, usage.cost mean $0.0826/row, 119/119 truncated
                   (archived scratchpad/gpt5-api.ALL-TRUNCATED-8k.jsonl)
  low effort     : 248-row pilot (results/responses/gpt5-api.jsonl)
  minimal effort : single documented probe (reasoning_tokens=0, WRONG answer,
                   $0.0146) — marked as probe, not a run, in the paper text.
"""
import json
import os
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
T = os.path.join(V2, "results", "tables")
OUT = os.path.join(V2, "paper", "workshop", "generated")
os.makedirs(OUT, exist_ok=True)

a = json.load(open(os.path.join(T, "analysis.json")))
gs = json.load(open(os.path.join(V2, "results", "graded", "summary.json")))

FAMILY = {
    "gemma4-31b-api": "Gemma", "gpt-oss-120b-api": "GPT-OSS", "gpt5-api": "GPT-5",
    "deepseek-v3-api": "DeepSeek", "llama33-70b-api": "Llama",
    "qwen25-72b-api": "Qwen2.5", "qwen25-32b": "Qwen2.5", "qwen25-7b-instruct": "Qwen2.5",
}
for s in ("1.7b", "4b", "8b", "14b", "32b"):
    FAMILY[f"qwen3-{s}-think"] = "Qwen3(think)"
    FAMILY[f"qwen3-{s}-nothink"] = "Qwen3"
COLORS = {"Gemma": "#d1495b", "GPT-OSS": "#edae49", "GPT-5": "#00798c",
          "DeepSeek": "#66a182", "Llama": "#8d5a97", "Qwen2.5": "#8c8c8c",
          "Qwen3": "#b8b8ff", "Qwen3(think)": "#3d5a80"}


def mag_of(m):
    n = magw = 0
    for cell in ("dflt", "ccw", "act", "top"):
        s = a["cell_rates"].get(f"{m}|{cell}|all")
        if s:
            n += s["n"]; magw += s["magnitude_correct"]["rate"] * s["n"]
    return magw / n if n else 0


# ---------------- figure 1: the flat band ----------------
pts = []
for key, s in a["var_level_diagnostic"].items():
    m, c = key.split("|")
    cb = s["convention_blind_given_mag"]
    if c == "ccw" and cb["n"] >= 20 and not m.endswith("-ctl"):
        pts.append((m, mag_of(m) * 100, cb["rate"] * 100,
                    cb["wilson_lo"] * 100, cb["wilson_hi"] * 100))
rates = [p[2] for p in pts]
mean_rate = sum(rates) / len(rates)

fig, ax = plt.subplots(figsize=(7.2, 3.6))
seen = set()
for m, x, y, lo, hi in pts:
    fam = FAMILY.get(m, "?")
    ax.errorbar(max(x, 0.09), y, yerr=[[max(0, y - lo)], [max(0, hi - y)]],
                fmt="o", ms=6, capsize=2.5, color=COLORS.get(fam, "k"),
                label=fam if fam not in seen else None, lw=1)
    seen.add(fam)
ax.axhline(mean_rate, color="black", lw=1, ls="--", alpha=0.7)
ax.text(0.11, mean_rate + 1.5, f"mean {mean_rate:.0f}%", fontsize=8)
ax.axhspan(min(rates), max(rates), color="gray", alpha=0.10)
ax.set_xscale("log")
ax.set_xlabel("task competence: magnitude-correct rate (%, log scale)")
ax.set_ylabel("reversion to trained frame (%)\n(diagnostic vars, magnitude correct)")
ax.set_ylim(0, 100)
# no in-figure title: the caption carries it in the paper
ax.legend(fontsize=7, ncol=4, loc="lower right", framealpha=0.9)
ax.grid(alpha=0.25)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"fig_invariance.{ext}"), dpi=170)
plt.close(fig)

# ---------------- figure 2: GPT-5 effort ladder ----------------
# provenance in module docstring
ladder = [
    ("minimal\n(probe)", 0.0146, 100, "answers instantly:\nWRONG (prior-driven)"),
    ("low\n(248-run)", 18.43 / 248, (248 - 144) / 248 * 100, "solves traps exactly\nwhen it completes"),
    ("default\n(119-run)", 0.0826, 0.0, "reasoning consumes the\nentire budget: no answers"),
]
fig, ax1 = plt.subplots(figsize=(5.4, 3.3))
xs = range(len(ladder))
comp = [l[2] for l in ladder]
cost = [l[1] * 100 for l in ladder]      # cents/row
b1 = ax1.bar([x - 0.18 for x in xs], comp, width=0.36, color="#3d5a80",
             label="completions within budget (%)")
ax1.set_ylabel("completes within budget (%)", color="#3d5a80")
ax1.set_ylim(0, 110)
ax2 = ax1.twinx()
b2 = ax2.bar([x + 0.18 for x in xs], cost, width=0.36, color="#d1495b",
             label="cost (¢/instance)")
ax2.set_ylabel("cost (US cents / instance)", color="#d1495b")
ax2.set_ylim(0, 11)
ax1.set_xticks(list(xs))
ax1.set_xticklabels([l[0] for l in ladder], fontsize=8)
for x, l in zip(xs, ladder):
    ax1.annotate(l[3], (x, 101), ha="center", fontsize=6.5, va="bottom")
ax1.set_ylim(0, 135)
ax1.set_title("GPT-5 reasoning-effort ladder on CircuChain v2", fontsize=10)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"fig_gpt5_effort.{ext}"), dpi=170)
plt.close(fig)

# ---------------- truncation table (think ladder economics) ----------------
rows = []
for size in ("1.7b", "4b", "8b", "14b", "32b"):
    line = [size]
    for mode in ("nothink", "think"):
        m = f"qwen3-{size}-{mode}"
        pm = gs["per_model"].get(m, {})
        n = sum(pm.get(k, 0) for k in ("CORRECT", "COMPLIANCE", "COMPETENCE")) or 1000
        tr = pm.get("truncated", None)
        # fall back: compute truncation from graded rows
        if tr is None:
            tr = 0
            p = os.path.join(V2, "results", "graded", f"{m}.jsonl")
            if os.path.exists(p):
                for l in open(p):
                    tr += bool(json.loads(l).get("truncated"))
        mag = mag_of(m) * 100
        line.append((mag, tr))
    (magn, trn), (magt, trt) = line[1], line[2]
    rows.append(f"{size} & {magn:.1f}\\% & {trn} & {magt:.1f}\\% & {trt} \\\\")
with open(os.path.join(OUT, "table_trunc.tex"), "w") as f:
    f.write("% AUTO-GENERATED\n" + "\n".join(rows) + "\n")

# ---------------- macros ----------------
mac = []
mac.append(f"\\newcommand{{\\WMeanRev}}{{{mean_rate:.1f}}}")
mac.append(f"\\newcommand{{\\WBandMin}}{{{min(rates):.0f}}}")
mac.append(f"\\newcommand{{\\WBandMax}}{{{max(rates):.0f}}}")
mac.append(f"\\newcommand{{\\WNCols}}{{{len(pts)}}}")
gpt5 = a["factor_pairs"]["gpt5-api|ccw|final_correct"]
mac.append(f"\\newcommand{{\\WGptFiveB}}{{{gpt5['b']}}}")
mac.append(f"\\newcommand{{\\WGptFiveC}}{{{gpt5['c']}}}")
B = C = 0
for k, s in a["factor_pairs"].items():
    if k.endswith("|ccw|final_correct"):
        B += s["b"]; C += s["c"]
mac.append(f"\\newcommand{{\\WAggB}}{{{B}}}")
mac.append(f"\\newcommand{{\\WAggC}}{{{C}}}")
mac.append("\\newcommand{\\WGptFiveDefaultCost}{8.3}")   # cents/row, 119-row run
mac.append("\\newcommand{\\WGptFiveLowCost}{7.4}")
mac.append("\\newcommand{\\WGptFiveMinCost}{1.5}")
mac.append(f"\\newcommand{{\\WGptFiveLowTrunc}}{{{144}}}")
with open(os.path.join(OUT, "wmacros.tex"), "w") as f:
    f.write("% AUTO-GENERATED by scripts/make_workshop_assets.py\n" + "\n".join(mac) + "\n")

print(f"wrote wmacros ({len(mac)}), table_trunc, fig_invariance, fig_gpt5_effort -> {OUT}")
print(f"band: {min(rates):.1f}-{max(rates):.1f}, mean {mean_rate:.1f}, cols {len(pts)}")
