"""Dual-verification gate (T3): every generated instance must agree across
    (a/b) the hand-derived numpy mesh+nodal solvers   (canonical, from generate)
    (c)   the exact sympy MNA solver on the netlist   (in-process, analytic.py)
    (d)   NGSPICE .op on the same netlist             (external binary, this module)
within tolerance_rel, or the instance is REJECTED. Errors cannot enter by construction;
a shared bug would have to appear identically in four independent derivations.

Ported/generalized from v1's scripts/verify_and_export_json.py (ngspice -b -o log cir,
universal label=value parser, V_sense current sensors).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Mapping

from .analytic import dual_check, mna_solve_netlist, resolve_target
from .topologies import get_topology

NGSPICE = shutil.which("ngspice") or "/opt/homebrew/bin/ngspice"

# v1's universal parser, tightened: "label = value" and table rows, comma allowed in labels
_RE_EQ = re.compile(r"([a-z0-9_.,#\(\)]+)\s*=\s*([-+]?[\d\.]+(?:e[-+]?\d+)?)", re.IGNORECASE)
_RE_TABLE = re.compile(r"^\s*([a-z0-9_.,#\(\)]+)\s+([-+]?[\d\.]+(?:e[-+]?\d+)?)\s*$", re.IGNORECASE)


def ngspice_available() -> bool:
    return bool(shutil.which("ngspice") or os.path.exists(NGSPICE))


def parse_ngspice_log(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _RE_EQ.search(line)
        if m:
            out[m.group(1).lower()] = float(m.group(2))
            continue
        m = _RE_TABLE.match(line)
        if m:
            label = m.group(1).lower()
            val = float(m.group(2))
            if "#branch" in label:                       # v1: v1#branch -> i(v1)
                out[f"i({label.split('#')[0]})"] = val
            out[label] = val
    return out


def run_ngspice(netlist: str, keep_log: str | None = None) -> Dict[str, float]:
    """Run ngspice -b on a netlist string; return the parsed label->value map."""
    with tempfile.TemporaryDirectory(prefix="circuchain_spice_") as td:
        cir = os.path.join(td, "instance.cir")
        log = os.path.join(td, "instance.log")
        with open(cir, "w") as f:
            f.write(netlist)
        proc = subprocess.run(
            [NGSPICE, "-b", "-o", log, cir],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
        )
        if not os.path.exists(log):
            raise RuntimeError(f"ngspice produced no log (exit {proc.returncode})")
        text = open(log, errors="ignore").read()
        if keep_log:
            shutil.copyfile(log, keep_log)
    return parse_ngspice_log(text)


def verify_physics(topology: str, values: Mapping[str, float],
                   canonical: Mapping[str, float], rel_tol: float = 1e-4,
                   spice: bool = True) -> List[str]:
    """Return mismatch descriptions for one physics instance (empty list == verified)."""
    topo = get_topology(topology)
    targets = topo.spice_targets()
    ref = {var: canonical[var] for var in targets}
    errs: List[str] = []

    # (c) exact MNA — always on, in-process
    mna = mna_solve_netlist(topo.netlist(values))
    got_mna = {var: resolve_target(mna, key) for var, key in targets.items()}
    errs += [f"MNA {e}" for e in dual_check(ref, got_mna, rel_tol=1e-8, abs_floor=1e-12)]

    # (d) ngspice — external
    if spice:
        raw = run_ngspice(topo.netlist(values))
        got_spice = {}
        for var, key in targets.items():
            try:
                got_spice[var] = resolve_target(raw, key)
            except KeyError:
                errs.append(f"SPICE {var}: key {key!r} missing from ngspice output")
        errs += [f"SPICE {e}" for e in dual_check(
            {v: ref[v] for v in got_spice}, got_spice, rel_tol=rel_tol, abs_floor=1e-9)]
    return errs


def verify_dataset(dataset_dir: str, rel_tol: float = 1e-4) -> dict:
    """Verify every unique physics instance in <dataset_dir>/instances.jsonl.
    Writes <dataset_dir>/verification.json and returns the summary."""
    path = os.path.join(dataset_dir, "instances.jsonl")
    seen: Dict[str, dict] = {}
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            if "physics_id" in row and row["physics_id"] not in seen:
                seen[row["physics_id"]] = row

    results, n_fail = [], 0
    for pid, row in sorted(seen.items()):
        errs = verify_physics(row["topology"], row["values"], row["canonical"], rel_tol)
        if errs:
            n_fail += 1
        results.append({"physics_id": pid, "status": "FAIL" if errs else "PASS", "errors": errs})

    summary = {
        "n_physics": len(seen), "n_pass": len(seen) - n_fail, "n_fail": n_fail,
        "rel_tol": rel_tol, "ngspice": NGSPICE,
        "results": results,
    }
    with open(os.path.join(dataset_dir, "verification.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary
