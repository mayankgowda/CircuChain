"""Independent validation of expected_under_contract for the RHR dataset.

Each convention transform is INDEPENDENTLY REALIZED, not re-applied:
    lh  : the whole physics re-solved with the LEFT-HAND rule actually substituted —
          cross_lc(sign=-1), i.e. epsilon -> -epsilon. Not a negation shortcut.
    rxn : the actual REACTION system re-solved — applied forces/charges negated at the
          SOURCE (F_i -> -F_i, G_i -> -G_i, q_i -> -q_i), invariants checked unchanged.
    diag: stored diagnostic masks recomputed from stored numbers.
    round: values -> re-solve == stored canonical.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict, List

from .families import FAMILIES
from .vec import cross_lc

REL_TOL = 1e-9
CHECKS = ("lh_levi_civita_flip", "rxn_negated_sources", "diag_mask_recompute",
          "values_roundtrip")

_NEGATE_KEYS = {
    "torque_rigid": ("fx", "fy", "fz"),
    "angmom_system": ("gx", "gy", "gz"),
    "lorentz_set": ("q",),
}
# variables whose rxn value must EQUAL canonical (no reaction partner / defined invariant)
_RXN_INVARIANT = {
    "torque_rigid": ("wd",),
    "angmom_system": ("l_x", "l_y", "l_z", "tk"),
    "lorentz_set": ("s",),
}


def _close(a: float, b: float, tol: float = REL_TOL) -> bool:
    return abs(a - b) <= max(tol, tol * max(abs(a), abs(b)))


def validate_dataset(dataset_dir: str, out_path: str) -> dict:
    by_phys: Dict[str, Dict[str, dict]] = defaultdict(dict)
    with open(os.path.join(dataset_dir, "instances.jsonl")) as f:
        for line in f:
            row = json.loads(line)
            cell = row["id"].rsplit("-", 2)[-2]
            if cell not in by_phys[row["physics_id"]]:
                by_phys[row["physics_id"]][cell] = row

    results: List[dict] = []
    for pid, cells in sorted(by_phys.items()):
        errs: List[str] = []
        base = cells["dflt"]
        fam = FAMILIES[base["topology"]]
        values = base["values"]
        canonical = base["canonical"]

        # values_roundtrip
        rt = fam.solve(values, full_gate=False)
        for k, v in rt.items():
            if not _close(float(v), canonical[k]):
                errs.append(f"values_roundtrip: {k} {float(v)} != {canonical[k]}")

        # lh: actually re-solved with the left-hand rule (epsilon -> -epsilon)
        if "lh" in cells:
            lh = fam.solve(values, full_gate=False,
                           cross_fn=lambda a, b: cross_lc(a, b, -1))
            exp = cells["lh"]["expected_under_contract"]
            for k in exp:
                if not _close(float(lh[k]), exp[k]):
                    errs.append(f"lh_levi_civita_flip: {k} {float(lh[k])} != {exp[k]}")

        # rxn: actually re-solved with negated sources
        if "rxn" in cells:
            neg = dict(values)
            for k in list(neg):
                if any(k.startswith(pfx) and k[len(pfx):].isdigit()
                       for pfx in _NEGATE_KEYS[base["topology"]]):
                    neg[k] = -neg[k]
            rx = fam.solve(neg, full_gate=False)
            exp = cells["rxn"]["expected_under_contract"]
            inv = _RXN_INVARIANT[base["topology"]]
            for k in exp:
                want = canonical[k] if k in inv else float(rx[k])
                if not _close(want, exp[k]):
                    errs.append(f"rxn_negated_sources: {k} {want} != {exp[k]}")

        # diag_mask_recompute
        for cell_code, row in cells.items():
            e, d, m = (row["expected_under_contract"], row["expected_under_default"],
                       row["diagnostic_vars"])
            for k in e:
                want = abs(e[k]) > 1e-9 and abs(d[k]) > 1e-9 and (e[k] > 0) != (d[k] > 0)
                if bool(m[k]) != want:
                    errs.append(f"diag_mask_recompute: {cell_code}/{k}")

        results.append({"physics_id": pid, "status": "FAIL" if errs else "PASS",
                        "errors": errs})

    summary = {"n_physics": len(results),
               "n_pass": sum(r["status"] == "PASS" for r in results),
               "n_fail": sum(r["status"] == "FAIL" for r in results),
               "checks": list(CHECKS), "rel_tol": REL_TOL, "results": results}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary
