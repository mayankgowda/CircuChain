"""Paper figures from analysis.json (build step 13, final piece).

Scope-independent: plots whatever models are present, so it regenerates as columns land.
Two figures, both saved as PDF (vector, for LaTeX) + PNG (preview):
  fig_convention_blindness — per-model convention-blind rate on the sign-DIAGNOSTIC vars,
                             grouped by contract cell, with Wilson 95% CIs. The headline.
  fig_factor_effect_sizes  — per-model McNemar odds ratio per factor (log scale) with the
                             exact-test p annotated. Shows the ccw-universal / act-top-varies gradient.
No LLM, no network; matplotlib only.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")            # headless
import matplotlib.pyplot as plt  # noqa: E402

CELLS = ["dflt", "ccw", "act", "top"]
FLIPS = ["ccw", "act", "top"]
CELL_LABEL = {"dflt": "default", "ccw": "mesh-dir (ccw)", "act": "passive-sign (act)",
              "top": "ref-node (top)"}


def _competent_models(analysis: dict, min_mag: float = 0.30) -> List[str]:
    """Models with enough magnitude-correct answers for the sign analysis to mean anything."""
    out = []
    for m in analysis["models"]:
        key = f"{m}|ccw"
        vl = analysis["var_level_diagnostic"].get(key) or analysis["var_level"].get(key)
        if vl and vl["var_mag_correct"]["rate"] >= min_mag:
            out.append(m)
    return out or analysis["models"]


def fig_convention_blindness(analysis: dict, out_dir: str) -> None:
    vld = analysis["var_level_diagnostic"] or analysis["var_level"]
    models = _competent_models(analysis)
    fig, ax = plt.subplots(figsize=(1.6 + 1.8 * len(models), 4.2))
    width = 0.8 / len(CELLS)
    colors = {"dflt": "#8c8c8c", "ccw": "#d1495b", "act": "#edae49", "top": "#66a182"}
    for ci, cell in enumerate(CELLS):
        rates, los, his = [], [], []
        for m in models:
            s = vld.get(f"{m}|{cell}")
            r = s["convention_blind_given_mag"] if s else {"rate": 0, "wilson_lo": 0, "wilson_hi": 0}
            rates.append(r["rate"] * 100)
            # Wilson CIs are asymmetric and can bracket the point estimate on one side;
            # clamp error-bar lengths to >= 0 for display.
            los.append(max(0.0, (r["rate"] - r["wilson_lo"]) * 100))
            his.append(max(0.0, (r["wilson_hi"] - r["rate"]) * 100))
        x = [i + ci * width for i in range(len(models))]
        ax.bar(x, rates, width, yerr=[los, his], capsize=3, label=CELL_LABEL[cell],
               color=colors[cell], edgecolor="black", linewidth=0.4)
    ax.set_xticks([i + width * 1.5 for i in range(len(models))])
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("convention-blind rate (%)\n(sign-diagnostic vars, given correct magnitude)")
    ax.set_title("Convention Blindness by contract: the model reverts to its trained prior\n"
                 "when instructed to use a non-default sign convention")
    ax.legend(title="contract cell", fontsize=8, ncol=2)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out_dir, f"fig_convention_blindness.{ext}"), dpi=150)
    plt.close(fig)


def fig_factor_effect_sizes(analysis: dict, out_dir: str) -> None:
    fp = analysis["factor_pairs"]
    models = _competent_models(analysis)
    fig, ax = plt.subplots(figsize=(1.6 + 1.6 * len(models), 4.2))
    width = 0.8 / len(FLIPS)
    colors = {"ccw": "#d1495b", "act": "#edae49", "top": "#66a182"}
    cap = 200.0                                        # clip inf/huge ORs for display
    for fi, flip in enumerate(FLIPS):
        ors, labels = [], []
        for m in models:
            s = fp.get(f"{m}|{flip}|final_correct")
            orv = s["mcnemar"]["odds_ratio"] if s else float("nan")
            p = s["mcnemar"]["p"] if s else float("nan")
            disp = cap if (orv == float("inf") or (orv == orv and orv > cap)) else orv
            ors.append(disp if disp and disp == disp and disp > 0 else 0.01)
            labels.append("" if p != p else ("***" if p < 1e-3 else "**" if p < 1e-2
                                             else "*" if p < 0.05 else "ns"))
        x = [i + fi * width for i in range(len(models))]
        bars = ax.bar(x, ors, width, label=CELL_LABEL[flip], color=colors[flip],
                      edgecolor="black", linewidth=0.4)
        for b, lab in zip(bars, labels):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.05, lab,
                    ha="center", va="bottom", fontsize=8)
    ax.set_yscale("log")
    ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks([i + width for i in range(len(models))])
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("McNemar odds ratio (log)\ncorrect@default vs wrong@flip")
    ax.set_title("Per-factor effect size (paired within-physics): mesh-direction is universal,\n"
                 "passive-sign / reference-node are model-specific   (*** p<1e-3, ** <1e-2, * <.05)")
    ax.legend(title="factor", fontsize=8)
    ax.grid(axis="y", alpha=0.3, which="both")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out_dir, f"fig_factor_effect_sizes.{ext}"), dpi=150)
    plt.close(fig)


def make_figures(analysis_json: str, out_dir: str) -> List[str]:
    analysis = json.load(open(analysis_json))
    os.makedirs(out_dir, exist_ok=True)
    fig_convention_blindness(analysis, out_dir)
    fig_factor_effect_sizes(analysis, out_dir)
    return [os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir)) if f.startswith("fig_")]
