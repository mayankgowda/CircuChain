"""Independent validation of expected_under_contract for the contour dataset (V3 analogue
of circuchain.validate_transforms — same closes-the-methods-hole logic).

Each convention transform is INDEPENDENTLY REALIZED, not re-applied:
    cw   : every edge re-integrated along the actually-reversed traversal (V_{i+1} -> V_i)
    wrk  : every edge re-integrated with the actually-negated field (-F)
    inw  : flux re-integrated with the actually-left (inward-for-CCW) normal ∫ Q dx - P dy
    green: the Green's-theorem double integrals re-run against the stored canonical
    diag : the stored diagnostic masks recomputed from stored expected/default numbers
    round: values -> (verts, P, Q) reconstruction re-solved and checked vs stored canonical

Stored floats are float(Fraction) exactly-rounded values, so agreement is checked at
1e-9 relative — far below the 5% grading tolerance, far above float rounding.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict, List

from .curves import unflatten_values
from .fieldpoly import polygon_edge_works, polygon_flux
from .solvers import (inward_normal_flux, negated_field_works,
                      reversed_traversal_works, sympy_green)

REL_TOL = 1e-9
CHECKS = ("cw_reversed_traversal", "wrk_negated_field", "inw_left_normal",
          "green_reverify", "diag_mask_recompute", "values_roundtrip")


def _close(a: float, b: float, tol: float = REL_TOL) -> bool:
    return abs(a - b) <= max(tol, tol * max(abs(a), abs(b)))


def validate_dataset(dataset_dir: str, out_path: str) -> dict:
    by_phys: Dict[str, Dict[str, dict]] = defaultdict(dict)
    with open(os.path.join(dataset_dir, "instances.jsonl")) as f:
        for line in f:
            row = json.loads(line)
            cell = row["id"].rsplit("-", 2)[-2]
            if row["contract"]["method"] == "param_direct":     # one row per cell suffices
                by_phys[row["physics_id"]][cell] = row

    results: List[dict] = []
    for pid, cells in sorted(by_phys.items()):
        errs: List[str] = []
        base = cells["dflt"]
        verts, p, q = unflatten_values(base["values"])
        canonical = base["canonical"]
        n = len(verts)

        # values_roundtrip: reconstructed physics re-solved == stored canonical
        works = polygon_edge_works(p, q, verts)
        wtot = sum(works)
        phi = polygon_flux(p, q, verts)
        for i, w in enumerate(works):
            if not _close(float(w), canonical[f"e{i+1}"]):
                errs.append(f"values_roundtrip: e{i+1} {float(w)} != {canonical[f'e{i+1}']}")
        if not _close(float(wtot), canonical["wtot"]) or not _close(float(phi), canonical["phi"]):
            errs.append("values_roundtrip: totals mismatch")

        # cw: reversed traversal actually integrated  (skipped if the dataset omits the cell)
        if "cw" in cells:
            rev = reversed_traversal_works(p, q, verts)
            exp_cw = cells["cw"]["expected_under_contract"]
            for i, w in enumerate(rev):
                if not _close(float(w), exp_cw[f"e{i+1}"]):
                    errs.append(f"cw_reversed_traversal: e{i+1} {float(w)} != {exp_cw[f'e{i+1}']}")
            if not _close(float(sum(rev)), exp_cw["wtot"]):
                errs.append("cw_reversed_traversal: wtot mismatch")
            if not _close(exp_cw["phi"], canonical["phi"]):
                errs.append("cw_reversed_traversal: phi must be orientation-invariant")

        # wrk: negated field actually integrated
        if "wrk" in cells:
            neg = negated_field_works(p, q, verts)
            exp_wrk = cells["wrk"]["expected_under_contract"]
            for i, w in enumerate(neg):
                if not _close(float(w), exp_wrk[f"e{i+1}"]):
                    errs.append(f"wrk_negated_field: e{i+1} {float(w)} != {exp_wrk[f'e{i+1}']}")
            if not _close(float(sum(neg)), exp_wrk["wtot"]):
                errs.append("wrk_negated_field: wtot mismatch")

        # inw: left-normal flux actually integrated
        if "inw" in cells:
            exp_inw = cells["inw"]["expected_under_contract"]
            if not _close(float(inward_normal_flux(p, q, verts)), exp_inw["phi"]):
                errs.append("inw_left_normal: phi mismatch")
            for i in range(n):
                if not _close(exp_inw[f"e{i+1}"], canonical[f"e{i+1}"]):
                    errs.append(f"inw_left_normal: e{i+1} must be normal-invariant")

        # green_reverify: independent re-run of the Green totals
        g = sympy_green(p, q, verts)
        if not _close(float(g["curl"]), canonical["wtot"]) or not _close(float(g["div"]), canonical["phi"]):
            errs.append("green_reverify: totals mismatch")

        # diag_mask_recompute from stored numbers
        for cell_code, row in cells.items():
            exp, dfl, mask = (row["expected_under_contract"], row["expected_under_default"],
                              row["diagnostic_vars"])
            for k in exp:
                want = abs(exp[k]) > 1e-9 and abs(dfl[k]) > 1e-9 and (exp[k] > 0) != (dfl[k] > 0)
                if bool(mask[k]) != want:
                    errs.append(f"diag_mask_recompute: {cell_code}/{k} stored {mask[k]} != {want}")

        results.append({"physics_id": pid, "status": "FAIL" if errs else "PASS",
                        "errors": errs})

    summary = {
        "n_physics": len(results),
        "n_pass": sum(r["status"] == "PASS" for r in results),
        "n_fail": sum(r["status"] == "FAIL" for r in results),
        "checks": list(CHECKS),
        "rel_tol": REL_TOL,
        "results": results,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary
