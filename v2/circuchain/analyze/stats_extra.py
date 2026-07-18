"""V2-3 stats hygiene: bootstrap CIs on the McNemar odds ratios, Benjamini-Hochberg
multiplicity correction across the factor-pair family, and the two variable-level
denominators reported side by side.

Notes on the odds-ratio interval:
  * The b/c cells are tiny relative to n_pairs and c is often ZERO (the empty-c-cell
    signature), where the sample OR is infinite. We therefore report the
    Haldane-Anscombe-corrected OR ((b+0.5)/(c+0.5)) alongside the raw one, and a
    nonparametric bootstrap percentile CI on the corrected OR obtained by resampling
    the n_pairs paired outcomes with replacement (10k reps, seeded).
  * The exact-binomial McNemar p already reported is unaffected by any of this.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

import numpy as np

N_BOOT = 10_000
BOOT_SEED = 20260709


def haldane_or(b: int, c: int) -> float:
    return (b + 0.5) / (c + 0.5)


def bootstrap_or_ci(b: int, c: int, n_pairs: int,
                    n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> Tuple[float, float]:
    """Percentile CI on the Haldane-corrected discordant odds ratio.

    Resamples the full set of n_pairs paired outcomes (both-ok / b-type / c-type /
    both-bad) with replacement; only the discordant counts matter for the OR.
    """
    if n_pairs == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng([seed, b, c, n_pairs])
    p = np.array([b / n_pairs, c / n_pairs, 1.0 - (b + c) / n_pairs])
    draws = rng.multinomial(n_pairs, p, size=n_boot)          # columns: b*, c*, rest
    ors = (draws[:, 0] + 0.5) / (draws[:, 1] + 0.5)
    lo, hi = np.percentile(ors, [2.5, 97.5])
    return float(lo), float(hi)


def benjamini_hochberg(pvals: List[float]) -> List[float]:
    """BH q-values, preserving input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank_from_end, idx in enumerate(reversed(order)):
        rank = m - rank_from_end
        val = min(prev, pvals[idx] * m / rank)
        q[idx] = val
        prev = val
    return q


def augment_analysis(analysis: dict) -> dict:
    """Adds `or_haldane`, `or_boot_ci`, and `q_bh` to every factor-pair entry (both
    outcome definitions, BH corrected within each outcome family), and builds the
    side-by-side variable-level table. Returns the same dict, mutated."""
    fp: Dict[str, dict] = analysis["factor_pairs"]

    for outcome in ("final_correct", "sign_given_mag"):
        keys = [k for k in fp if k.endswith(f"|{outcome}") and fp[k]["n_pairs"] > 0]
        pvals = [fp[k]["mcnemar"]["p"] for k in keys]
        qvals = benjamini_hochberg(pvals) if keys else []
        for k, q in zip(keys, qvals):
            s = fp[k]
            b, c, n = s["b"], s["c"], s["n_pairs"]
            lo, hi = bootstrap_or_ci(b, c, n)
            s["or_haldane"] = haldane_or(b, c)
            s["or_boot_ci"] = [lo, hi]
            s["q_bh"] = q

    # ---- side-by-side denominators: all variables vs sign-diagnostic subset ----
    both: Dict[str, dict] = {}
    vl, vld = analysis.get("var_level", {}), analysis.get("var_level_diagnostic", {})
    for key in sorted(set(vl) | set(vld)):
        a, d = vl.get(key), vld.get(key)
        both[key] = {
            "all_vars": (a or {}).get("convention_blind_given_mag"),
            "diagnostic_vars": (d or {}).get("convention_blind_given_mag"),
        }
    analysis["var_level_both_denominators"] = both
    return analysis


def write_outputs(analysis: dict, out_dir: str) -> None:
    with open(os.path.join(out_dir, "factor_pairs_ci.csv"), "w") as f:
        f.write("model,factor,outcome,n_pairs,b,c,odds_ratio,or_haldane,"
                "or_boot_lo,or_boot_hi,mcnemar_p,q_bh\n")
        for key, s in analysis["factor_pairs"].items():
            if "or_haldane" not in s:
                continue
            m, fac, outcome = key.split("|")
            orv = s["mcnemar"]["odds_ratio"]
            ors = "inf" if orv == float("inf") else ("nan" if orv != orv else f"{orv:.4g}")
            lo, hi = s["or_boot_ci"]
            f.write(f"{m},{fac},{outcome},{s['n_pairs']},{s['b']},{s['c']},{ors},"
                    f"{s['or_haldane']:.4g},{lo:.4g},{hi:.4g},"
                    f"{s['mcnemar']['p']:.4g},{s['q_bh']:.4g}\n")

    with open(os.path.join(out_dir, "var_level_both.csv"), "w") as f:
        f.write("model,cell,all_rate,all_n,diag_rate,diag_n\n")
        for key, s in analysis["var_level_both_denominators"].items():
            m, c = key.split("|")
            a, d = s["all_vars"], s["diagnostic_vars"]
            f.write(f"{m},{c},"
                    f"{(a or {}).get('rate', float('nan')):.4f},{(a or {}).get('n', 0)},"
                    f"{(d or {}).get('rate', float('nan')):.4f},{(d or {}).get('n', 0)}\n")
