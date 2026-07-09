#!/usr/bin/env python3
"""GNG-1 / Week-3 credibility result — CPU-only, zero inference.

Re-grade the 500 v1 log rows with the DETERMINISTIC rule-based compliance grader and compare
head-to-head against the v1 GPT-5 LLM judge. Produces:
  * per-model accuracy + compliance/competence decomposition (rule vs judge)
  * the rule-vs-judge confusion matrix + Cohen's kappa  (target >= 0.8; v1's judge-audit was ~0.57)
  * the 2x2 joint (magnitude-correct x sign-compliant) per model  -- the #1 reviewer-blocker fix
Outputs go to v2/results/regrade_v1/.

Run:  python v2/scripts/regrade_v1_logs.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

# make `circuchain` importable without installing the package
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
from circuchain.grade.compliance import grade_subtask, cohen_kappa, CORRECT, COMPLIANCE, COMPETENCE  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(HERE, "..", "results", "regrade_v1")
os.makedirs(OUT, exist_ok=True)

# v1 extracted-value files -> canonical model display names
NAME = {
    "extracted_gpt-5": "gpt-5",
    "extracted_gpt-4o": "gpt-4o",
    "extracted_gpt-4o-mini": "GPT-4o Mini",
    "extracted_o4-mini": "o4-mini",
    "extracted_claude-opus-4-5-20251101 (1)": "Claude Opus 4.5",
}
MODELS = ["GPT-4o Mini", "gpt-4o", "o4-mini", "Claude Opus 4.5", "gpt-5"]

JUDGE_DICH = {
    "CORRECT": CORRECT,
    "ERR_SIGN_CONVENTION": COMPLIANCE, "ERR_METHOD_VIOLATION": COMPLIANCE,
    "ERR_PHYSICS_SETUP": COMPETENCE, "ERR_CALCULATION": COMPETENCE,
    "ERR_HALLUCINATION": COMPETENCE, "NO_RESPONSE": COMPETENCE,
}


def load_judge():
    lut = {}
    for e in json.load(open(os.path.join(DATA, "final_diagnosis_gpt5.json"))):
        diag = e.get("Diagnosis")
        cat = diag.get("category") if isinstance(diag, dict) else diag
        lut[(e["Model"], e["ID"], e["Method"])] = cat
    return lut


def main():
    judge = load_judge()
    rows = []
    for fp in glob.glob(os.path.join(DATA, "extracted_values_using_gpt4o", "*.json")):
        base = os.path.basename(fp).replace(".json", "")
        model = NAME.get(base) or NAME.get(base.split(" (")[0]) or base
        for e in json.load(open(fp)):
            truth = e["ground_truth"]["verifier_map"]           # signed, DEFAULT-contract answer
            pred = e.get("extracted_values") or {}
            # v1 re-grade mode: default == expected (only the declared textbook contract exists)
            g = grade_subtask(pred, truth, default_map=None)
            jcat = judge.get((model, e["id"], e.get("method")))
            rows.append({
                "model": model, "id": e["id"], "method": e.get("method"),
                "regime": "TRAP" if "Trap" in e["id"] else "CONTROL",
                "rule": g.label, "mag_ok": g.magnitude_correct, "sign_ok": g.sign_compliant,
                "joint": g.joint_cell,
                "judge": jcat, "judge_dich": JUDGE_DICH.get(jcat) if jcat else None,
            })

    # ---- per-model table ----
    per_model = []
    for m in MODELS:
        mr = [r for r in rows if r["model"] == m]
        n = len(mr)
        if not n:
            continue
        rec = {
            "model": m, "n": n,
            "rule_acc": sum(r["rule"] == CORRECT for r in mr) / n,
            "judge_acc": sum(r["judge"] == "CORRECT" for r in mr) / n,
            "rule_compliance": sum(r["rule"] == COMPLIANCE for r in mr) / n,
            "rule_competence": sum(r["rule"] == COMPETENCE for r in mr) / n,
            "judge_compliance": sum(r["judge_dich"] == COMPLIANCE for r in mr) / n,
            "judge_competence": sum(r["judge_dich"] == COMPETENCE for r in mr) / n,
            # 2x2 joint: among magnitude-correct subtasks, share that are sign-compliant
            "mag_correct_rate": sum(r["mag_ok"] for r in mr) / n,
            "sign_compliant_given_mag": (
                sum(r["mag_ok"] and r["sign_ok"] for r in mr) / max(1, sum(r["mag_ok"] for r in mr))
            ),
        }
        per_model.append(rec)

    # ---- rule vs judge agreement ----
    matched = [r for r in rows if r["judge_dich"] is not None]
    dich_pairs = [(r["rule"], r["judge_dich"]) for r in matched]
    kappa_dich = cohen_kappa(dich_pairs)
    agree_dich = sum(a == b for a, b in dich_pairs) / len(dich_pairs)
    fail_pairs = [(r["rule"], r["judge_dich"]) for r in matched
                  if r["rule"] != CORRECT and r["judge_dich"] != CORRECT]
    kappa_fail = cohen_kappa(fail_pairs)
    agree_fail = sum(a == b for a, b in fail_pairs) / len(fail_pairs) if fail_pairs else float("nan")

    cats = [CORRECT, COMPLIANCE, COMPETENCE]
    confusion = {rc: {jc: sum(1 for r in matched if r["rule"] == rc and r["judge_dich"] == jc)
                      for jc in cats} for rc in cats}
    offdiag = [{"rule": rc, "judge": jc, "n": confusion[rc][jc]}
               for rc in cats for jc in cats if rc != jc and confusion[rc][jc]]

    summary = {
        "n_subtasks": len(rows), "n_matched_to_judge": len(matched),
        "kappa_3way": kappa_dich, "agreement_3way": agree_dich,
        "kappa_failures_only": kappa_fail, "agreement_failures_only": agree_fail,
        "confusion_rule_rows_judge_cols": confusion,
        "off_diagonal": offdiag,
        "per_model": per_model,
    }
    json.dump(summary, open(os.path.join(OUT, "regrade_summary.json"), "w"), indent=2)

    # ---- pretty print ----
    print(f"Subtasks graded: {len(rows)}   matched to judge: {len(matched)}\n")
    hdr = (f"{'Model':<18}{'N':>4}{'RuleAcc':>8}{'JudgeAcc':>9}"
           f"{'R-Compl':>9}{'R-Compet':>9}{'J-Compl':>9}{'J-Compet':>9}{'Sign|Mag':>9}")
    print(hdr); print("-" * len(hdr))
    for r in per_model:
        print(f"{r['model']:<18}{r['n']:>4}{r['rule_acc']*100:>7.1f}%{r['judge_acc']*100:>8.1f}%"
              f"{r['rule_compliance']*100:>8.1f}%{r['rule_competence']*100:>8.1f}%"
              f"{r['judge_compliance']*100:>8.1f}%{r['judge_competence']*100:>8.1f}%"
              f"{r['sign_compliant_given_mag']*100:>8.1f}%")
    print(f"\nRULE vs JUDGE  3-way: agreement={agree_dich*100:.1f}%  Cohen kappa={kappa_dich:.3f}"
          f"  (target >= 0.80; v1 judge-audit was ~0.57)")
    print(f"RULE vs JUDGE  failures-only compliance/competence: "
          f"agreement={agree_fail*100:.1f}%  kappa={kappa_fail:.3f}")
    print("\nConfusion (rows=RULE, cols=JUDGE):")
    print(f"{'':>12}" + "".join(f"{c:>12}" for c in cats))
    for rc in cats:
        print(f"{rc:>12}" + "".join(f"{confusion[rc][jc]:>12}" for jc in cats))
    gate = "PASS" if kappa_dich >= 0.80 else "FAIL"
    print(f"\nGNG-1 gate (kappa >= 0.80): {gate}")
    print(f"\nWrote {os.path.join(OUT, 'regrade_summary.json')}")


if __name__ == "__main__":
    main()
