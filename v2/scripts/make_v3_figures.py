"""Paper figures from paper_stats.json (deterministic, no hand-typed numbers)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
S = json.load(open(os.path.join(V2, "results", "paper_v3", "paper_stats.json")))
OUT = os.path.join(V2, "results", "paper_v3", "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 200})

# ---- Fig 1: entrenchment gradient (8 conventions) ----
E = S["entrenchment"]; T = S["entrenchment_tiers"]
order = sorted(E, key=lambda c: (T[c], E[c]["rate"]))
labels = {"ccw": "mesh dir (circ)", "act": "passive sign (circ)", "top": "ref node (circ)",
          "cw": "orientation (cont)", "wrk": "work sign (cont)", "inw": "flux normal (cont)",
          "lh": "handedness (RHR)", "rxn": "reaction (RHR)"}
colors = {0: "#4878CF", 1: "#EE854A", 2: "#D65F5F"}
fig, ax = plt.subplots(figsize=(5.2, 2.9))
for i, c in enumerate(order):
    r = E[c]["rate"] * 100
    lo, hi = [x * 100 for x in E[c]["wilson"]]
    ax.errorbar(i, r, yerr=[[r - lo], [hi - r]], fmt="o", color=colors[T[c]], capsize=3)
    ax.annotate(labels[c], (i, r), textcoords="offset points", xytext=(0, 7),
                ha="center", fontsize=7.5)
ax.set_xticks(range(len(order)))
ax.set_xticklabels([f"tier {T[c]}" for c in order], fontsize=7.5)
ax.set_ylabel("reversion to trained frame (%)")
ax.set_ylim(-4, 100)
ax.set_title("Frontier low-strain reversion vs. reversal-pedagogy tier "
             f"(weighted-logistic z = {S['trend_tier']['z']:.1f})", fontsize=8.5)
handles = [plt.Line2D([0], [0], marker="o", ls="", color=colors[t],
                      label=f"tier {t}: {d}") for t, d in
           ((0, "reversal taught as operation"), (1, "taught as error/partial"),
            (2, "reversal absent"))]
ax.legend(handles=handles, fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(f"{OUT}/fig_entrenchment.pdf"); plt.close(fig)

# ---- Fig 2: dose-response + matched-transform control ----
fig, ax = plt.subplots(figsize=(4.4, 2.9))
for m, mark in (("gpt-oss-120b-api", "o"), ("gpt5-api", "s"), ("gemma4-31b-api", "^")):
    xs, cw, wk = [], [], []
    for tier, blk in (("easy", "contour_easy"), ("hard", "contour_hard")):
        d = S[blk][m]
        xs.append((1 - d["mag"]["rate"]) * 100)
        cw.append(d["cw"]["rate"] * 100)
        wk.append(d["wrk"]["rate"] * 100)
    ax.plot(xs, cw, marker=mark, color="#D65F5F", label=f"{m.split('-')[0]} cw")
    ax.plot(xs, wk, marker=mark, ls="--", color="#4878CF", alpha=0.7)
ax.set_xlabel("competence strain (100 − magnitude-correct %)")
ax.set_ylabel("reversion (%)")
ax.set_title("Load reactivates the prior — matched transform (dashed) does not",
             fontsize=8.5)
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_dose.pdf"); plt.close(fig)

# ---- Fig 3: C1 dissociation, 5 rungs ----
sizes = ["1.7b", "4b", "8b", "14b", "32b"]
fig, ax = plt.subplots(figsize=(4.4, 2.9))
for mode, color in (("nothink", "#777777"), ("think", "#2E7D32")):
    mags = [S["contour_easy"][f"qwen3-{s}-{mode}"]["mag"]["rate"] * 100 for s in sizes]
    revs = [S["contour_easy"][f"qwen3-{s}-{mode}"]["cw"]["rate"] * 100 for s in sizes]
    ax.plot(sizes, mags, marker="o", color=color, label=f"{mode}: competence")
    ax.plot(sizes, revs, marker="x", ls=":", color=color, label=f"{mode}: reversion")
ax.set_ylabel("%"); ax.set_ylim(0, 100)
ax.set_title("Reasoning buys competence, not compliance (contour, Qwen3)", fontsize=8.5)
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_c1.pdf"); plt.close(fig)

# ---- Fig 4: k-shot dose curves ----
fig, ax = plt.subplots(figsize=(4.0, 2.9))
for m, mark in (("gemma4-31b-api", "^"), ("gpt-oss-120b-api", "o"), ("gpt5-api", "s")):
    d = S["intervention"][m]
    ks, rs = [], []
    for k, key in ((0, "shot0"), (1, "shot1"), (3, "shot3")):
        if d.get(key) and d[key]["n"]:
            ks.append(k); rs.append(d[key]["rate"] * 100)
    ax.plot(ks, rs, marker=mark, label=m.split("-")[0])
ax.set_xticks([0, 1, 3]); ax.set_xlabel("worked CCW examples in context")
ax.set_ylabel("reversion (%)"); ax.set_ylim(0, 100)
ax.set_title("In-context demonstrations barely move the prior", fontsize=8.5)
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_kshot.pdf"); plt.close(fig)

print("4 figures ->", OUT)
