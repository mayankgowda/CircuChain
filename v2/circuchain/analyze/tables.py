"""Turn graded rows into the paper's tables.

Outputs (per invocation, into <out>/):
  cell_rates.csv     per model x cell x regime: n, dichotomy counts, completion/compliance
                     rates with Wilson CIs, mag-correct rate, sign|mag rate
  factor_pairs.csv   per model x factor (ccw/act/top) x outcome definition: matched-pair
                     concordance, McNemar exact p, discordant odds ratio
  analysis.json      everything, machine-readable

Two outcome definitions per factor pair (both reported; the conditioned one is primary):
  final_correct      row graded CORRECT (magnitude AND sign right on every var)
  sign_given_mag     sign_compliant, evaluated only on pairs where BOTH sides are
                     magnitude_correct (competence intact -> isolates pure convention effect)
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Dict, List

from .stats import mcnemar_exact, paired_counts, wilson_ci

FLIP_CELLS = ("ccw", "act", "top")


def _load_graded(graded_dir: str) -> List[dict]:
    rows = []
    for fname in sorted(os.listdir(graded_dir)):
        if fname.endswith(".jsonl") and not fname.endswith(".failures.jsonl"):
            with open(os.path.join(graded_dir, fname)) as f:
                rows += [json.loads(line) for line in f]
    return rows


def _rate(k: int, n: int) -> dict:
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "rate": (k / n if n else float("nan")),
            "wilson_lo": lo, "wilson_hi": hi}


def analyze_graded(graded_dir: str, out_dir: str) -> dict:
    rows = _load_graded(graded_dir)
    os.makedirs(out_dir, exist_ok=True)

    # ---------------- per model x cell x regime rates ----------------
    cell_stats: dict = {}
    by_mcr: dict = defaultdict(list)
    for r in rows:
        by_mcr[(r["model"], r["cell"], r["regime"])].append(r)
        by_mcr[(r["model"], r["cell"], "all")].append(r)
    for key, rs in sorted(by_mcr.items()):
        n = len(rs)
        completed = [r for r in rs if not r.get("truncated")]
        mag_ok = [r for r in rs if r.get("magnitude_correct")]
        cell_stats["|".join(key)] = {
            "n": n,
            "dichotomy": {lab: sum(1 for r in rs if r["dichotomy"] == lab)
                          for lab in ("CORRECT", "COMPLIANCE", "COMPETENCE")},
            "completed_within_budget": _rate(len(completed), n),
            "final_correct": _rate(sum(1 for r in rs if r["dichotomy"] == "CORRECT"), n),
            "magnitude_correct": _rate(len(mag_ok), n),
            "sign_compliant_given_mag": _rate(
                sum(1 for r in mag_ok if r.get("sign_compliant")), len(mag_ok)),
            "extraction_issues": sum(1 for r in rs
                                     if r.get("extraction_mode") in ("fallback", "none")),
        }

    # ---------------- per model x factor matched pairs ----------------
    # index rows by (model, physics_id, method) -> {cell: row}
    idx: dict = defaultdict(dict)
    for r in rows:
        idx[(r["model"], r["physics_id"], r["method"])][r["cell"]] = r

    factor_stats: dict = {}
    models = sorted({r["model"] for r in rows})
    for model in models:
        for flip in FLIP_CELLS:
            pairs_fc, pairs_sgm = [], []
            for (m, _pid, _meth), cells in idx.items():
                if m != model or "dflt" not in cells or flip not in cells:
                    continue
                d, f = cells["dflt"], cells[flip]
                pairs_fc.append((d["dichotomy"] == "CORRECT", f["dichotomy"] == "CORRECT"))
                if d.get("magnitude_correct") and f.get("magnitude_correct"):
                    pairs_sgm.append((bool(d.get("sign_compliant")),
                                      bool(f.get("sign_compliant"))))
            for outcome, pairs in (("final_correct", pairs_fc),
                                   ("sign_given_mag", pairs_sgm)):
                counts = paired_counts(pairs)
                factor_stats[f"{model}|{flip}|{outcome}"] = {
                    "n_pairs": len(pairs), **counts,
                    "mcnemar": mcnemar_exact(counts["b"], counts["c"]),
                    "rate_default": _rate(counts["both_ok"] + counts["b"], len(pairs)),
                    "rate_flipped": _rate(counts["both_ok"] + counts["c"], len(pairs)),
                }

    # ---------------- variable-level convention analysis ----------------
    # Subtask-level outcomes conjoin 5-8 variables and hit floor effects on weak models.
    # At the variable level: among vars whose MAGNITUDE was right, what share carries the
    # wrong sign — and of those, how many match the competing convention exactly?
    var_level: dict = {}
    by_mc: dict = defaultdict(lambda: Counter())
    for r in rows:
        for _var, lab in r["var_labels"].items():
            by_mc[(r["model"], r["cell"])][lab] += 1
    for (model, cell), c in sorted(by_mc.items()):
        mag_ok = c["PASS"] + c["ERR_SIGN_CONVENTION"] + c["ERR_SIGN_INCOHERENT"]
        var_level[f"{model}|{cell}"] = {
            "n_vars": sum(c.values()),
            "labels": dict(c),
            "var_mag_correct": _rate(mag_ok, sum(c.values())),
            "convention_blind_given_mag": _rate(c["ERR_SIGN_CONVENTION"], mag_ok),
            "sign_wrong_given_mag": _rate(
                c["ERR_SIGN_CONVENTION"] + c["ERR_SIGN_INCOHERENT"], mag_ok),
        }

    # ---------------- write ----------------
    with open(os.path.join(out_dir, "cell_rates.csv"), "w") as f:
        f.write("model,cell,regime,n,correct,compliance,competence,completed_rate,"
                "final_correct_rate,mag_correct_rate,sign_given_mag_rate,extract_issues\n")
        for key, s in cell_stats.items():
            m, c, reg = key.split("|")
            f.write(f"{m},{c},{reg},{s['n']},{s['dichotomy']['CORRECT']},"
                    f"{s['dichotomy']['COMPLIANCE']},{s['dichotomy']['COMPETENCE']},"
                    f"{s['completed_within_budget']['rate']:.4f},"
                    f"{s['final_correct']['rate']:.4f},{s['magnitude_correct']['rate']:.4f},"
                    f"{s['sign_compliant_given_mag']['rate']:.4f},{s['extraction_issues']}\n")

    with open(os.path.join(out_dir, "factor_pairs.csv"), "w") as f:
        f.write("model,factor,outcome,n_pairs,both_ok,b_dflt_only,c_flip_only,both_bad,"
                "odds_ratio,mcnemar_p,rate_default,rate_flipped\n")
        for key, s in factor_stats.items():
            m, flip, outcome = key.split("|")
            mc = s["mcnemar"]
            f.write(f"{m},{flip},{outcome},{s['n_pairs']},{s['both_ok']},{s['b']},{s['c']},"
                    f"{s['both_bad']},{mc['odds_ratio']:.4g},{mc['p']:.4g},"
                    f"{s['rate_default']['rate']:.4f},{s['rate_flipped']['rate']:.4f}\n")

    with open(os.path.join(out_dir, "var_level.csv"), "w") as f:
        f.write("model,cell,n_vars,var_mag_correct,convention_blind_given_mag,"
                "sign_wrong_given_mag,cb_wilson_lo,cb_wilson_hi\n")
        for key, s in var_level.items():
            m, c = key.split("|")
            cb = s["convention_blind_given_mag"]
            f.write(f"{m},{c},{s['n_vars']},{s['var_mag_correct']['rate']:.4f},"
                    f"{cb['rate']:.4f},{s['sign_wrong_given_mag']['rate']:.4f},"
                    f"{cb['wilson_lo']:.4f},{cb['wilson_hi']:.4f}\n")

    summary = {"n_rows": len(rows), "models": models,
               "cell_rates": cell_stats, "factor_pairs": factor_stats,
               "var_level": var_level}
    with open(os.path.join(out_dir, "analysis.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def format_factor_table(summary: dict) -> str:
    lines = []
    hdr = (f"{'model':<20}{'factor':<7}{'outcome':<16}{'pairs':>6}{'b':>5}{'c':>5}"
           f"{'OR':>9}{'p':>10}{'dflt':>7}{'flip':>7}")
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for key in sorted(summary["factor_pairs"]):
        m, flip, outcome = key.split("|")
        s = summary["factor_pairs"][key]
        mc = s["mcnemar"]
        or_s = ("inf" if mc["odds_ratio"] == float("inf")
                else "nan" if mc["odds_ratio"] != mc["odds_ratio"]
                else f"{mc['odds_ratio']:.2f}")
        lines.append(f"{m:<20}{flip:<7}{outcome:<16}{s['n_pairs']:>6}{s['b']:>5}{s['c']:>5}"
                     f"{or_s:>9}{mc['p']:>10.3g}"
                     f"{s['rate_default']['rate']:>7.2f}{s['rate_flipped']['rate']:>7.2f}")
    return "\n".join(lines)
