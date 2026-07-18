"""Independent validation of the convention transforms (v2 methods-hole fix).

The panel's strongest methodological objection: the 4-way oracle certifies only the
DEFAULT-frame canonical answer, while the dependent variable of the whole study —
``expected_under_contract`` (and the ``diagnostic_vars`` mask) — comes from a single
code path (contract.apply). A simulator cannot "run counter-clockwise", so that path
was unvalidated. This module closes the hole with three independent checks, anchored
in raw NGSPICE observables and the stored instance records rather than in
contract.apply or the numpy canonical solution:

  (A) PHYSICAL re-grounding (ref_node=top).  The netlist's ground is RELABELED so the
      top-reference node becomes SPICE node 0, and ngspice is re-run. Node voltages
      read directly from that second run must equal the stored expected_under_contract
      of the `top` cell. Two zero-code invariants ride along:
        * the old bottom rail must read  -V(top)  of the original run (SPICE vs SPICE),
        * every sensed branch current and element-voltage difference must be UNCHANGED
          (potentials are reference-dependent; currents and differences are not).

  (B) Frame re-derivation from raw branch observables (mesh_dir=ccw, psc=active).
      These are definitional frame choices — no simulator can realize them — but their
      transforms are re-derived here from the RAW ngspice sensor currents / node
      voltages plus the reference-direction semantics stated in the prompt text:
      reversing a loop orientation or a stated arrow/polarity negates exactly that
      quantity. The check compares stored expected_under_contract against ±raw
      observables, never touching contract.apply or the numpy solution.

  (C) Diagnostic-mask consistency. The stored diagnostic_vars flag must equal
      "expected_under_contract and expected_under_default have opposite (nonzero)
      signs", recomputed directly from the stored numbers of each instance record.

Run over every physics x cell in the dataset:  `circuchain validate-transforms`.
Writes <dataset>/../..//tables/transform_validation.json and exits nonzero on any FAIL.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict, List, Mapping, Tuple

from .analytic import resolve_target
from .topologies import get_topology
from .verify import run_ngspice

REL_TOL = 1e-4          # stored-expectation vs SPICE gate (same as verify.py)
RUN2RUN_TOL = 5e-4      # SPICE-run vs SPICE-run invariants: both sides carry the log's
                        # ~5-significant-digit printing, so their rel error can reach ~1e-4 each
ABS_FLOOR = 1e-9
SIGN_EPS = 1e-9         # matches contract.diagnostic_vars

# node-token positions per element letter (first char of the element name)
_NODE_SLOTS = {
    "r": (1, 2), "v": (1, 2), "i": (1, 2), "c": (1, 2), "l": (1, 2),
    "e": (1, 2, 3, 4), "g": (1, 2, 3, 4),      # VCVS / VCCS: out+ out- ctrl+ ctrl-
    "f": (1, 2), "h": (1, 2),                  # CCCS / CCVS: token 3 is a SOURCE NAME
}


def _close(a: float, b: float, rel: float = REL_TOL, abs_floor: float = ABS_FLOOR) -> bool:
    return abs(a - b) <= max(abs_floor, rel * max(abs(a), abs(b)))


def relabel_ground(netlist: str, top_node: str) -> str:
    """Swap SPICE node labels `0` <-> `top_node` at node positions only.

    Element-name tokens, controlling-source names (F/H token 3), values, and directives
    are never touched; node names are matched EXACTLY (so `1s` survives a 1<->0 swap).
    """
    swap = {"0": top_node, top_node: "0"}
    out_lines: List[str] = []
    for line in netlist.splitlines():
        s = line.strip()
        if not s or s.startswith("*") or s.startswith("."):
            out_lines.append(line)
            continue
        toks = s.split()
        slots = _NODE_SLOTS.get(toks[0][0].lower(), ())
        for idx in slots:
            if idx < len(toks) and toks[idx] in swap:
                toks[idx] = swap[toks[idx]]
        out_lines.append(" ".join(toks))
    return "\n".join(out_lines) + "\n"


def _node_of(target) -> str:
    """'v(3)' -> '3' (only for plain node-voltage targets)."""
    t = str(target)
    assert t.startswith("v(") and t.endswith(")"), t
    return t[2:-1]


# Un-sensed variables, re-derived from raw node potentials + given component values.
# Geometry transcribed from each topology's components_block (an authority independent of
# the numpy solvers): entry = (node_plus, node_minus, R_key)  ->  (V+ - V-) / R.
RAW_DERIVED: Dict[str, Dict[str, Tuple[str, str, str]]] = {
    "wheatstone": {
        "i2": ("1", "3", "R_RT"),   # top-triangle mesh current == current through R_RT (1->3)
        "i3": ("3", "0", "R_RB"),   # bottom-triangle mesh current == current through R_RB (3->0)
    },
}


def _make_reader(raw: Mapping[str, float], values: Mapping[str, float],
                 mapping: Mapping[str, str] | None = None):
    """Build (node, value) readers over one ngspice raw map, optionally under a ground swap.

    `mapping` translates ORIGINAL node names to the labels they carry in this run
    (identity for the canonical run; {top<->0} for the re-grounded run). Sensor
    currents i(...) keep their element names in both runs. v(0) reads literal 0.
    """
    m = dict(mapping or {})

    def node(orig: str) -> float:
        label = m.get(orig, orig)
        if label == "0":
            return 0.0
        return resolve_target(raw, f"v({label})")

    def value(topology: str, var: str, targets: Mapping) -> float:
        drv = RAW_DERIVED.get(topology, {}).get(var)
        if drv is not None:
            np_, nm_, rk = drv
            return (node(np_) - node(nm_)) / values[rk]
        key = targets[var]
        if isinstance(key, tuple):                       # ("diff", "v(a)", "v(b)")
            _, a, b = key
            return node(_node_of(a)) - node(_node_of(b))
        if isinstance(key, str) and key.startswith("v("):
            return node(_node_of(key))
        return resolve_target(raw, key)                  # sensor current — name survives relabel

    return node, value


def validate_physics(topology: str, values: Mapping[str, float],
                     cells: Mapping[str, dict]) -> List[str]:
    """Validate one physics instance. `cells` maps cell code -> instance record
    (needs expected_under_contract / expected_under_default / diagnostic_vars / roles).
    Returns a list of failure strings (empty == PASS)."""
    topo = get_topology(topology)
    targets = topo.spice_targets()
    errs: List[str] = []

    mesh_vars = set(topo.mesh_vars)
    node_vars = set(topo.node_vars)
    branch_vars = set(topo.branch_vars)
    element_vars = set(topo.element_vars)
    requested = topo.requested_vars()

    raw = run_ngspice(topo.netlist(values))
    node1, rawv = _make_reader(raw, values)
    rawv = (lambda f: (lambda var: f(topology, var, targets)))(rawv)

    exp_dflt = cells["dflt"]["expected_under_default"]

    # ---- baseline: raw SPICE reproduces the default-frame expectations ----
    for var in requested:
        if not _close(rawv(var), exp_dflt[var]):
            errs.append(f"dflt {var}: spice {rawv(var):.9g} != stored {exp_dflt[var]:.9g}")

    # ---- (B) ccw: mesh currents negate, everything else unchanged — vs RAW ----
    exp = cells["ccw"]["expected_under_contract"]
    for var in requested:
        want = -rawv(var) if var in mesh_vars else rawv(var)
        if not _close(exp[var], want):
            errs.append(f"ccw {var}: stored {exp[var]:.9g} != raw-derived {want:.9g}")

    # ---- (B) act: branch currents + element voltages negate, others unchanged ----
    exp = cells["act"]["expected_under_contract"]
    for var in requested:
        want = -rawv(var) if var in (branch_vars | element_vars) else rawv(var)
        if not _close(exp[var], want):
            errs.append(f"act {var}: stored {exp[var]:.9g} != raw-derived {want:.9g}")

    # ---- (A) top: PHYSICAL re-grounded netlist ----
    top_node = _node_of(targets["v_top"])
    raw2 = run_ngspice(relabel_ground(topo.netlist(values), top_node))
    swap = {top_node: "0", "0": top_node}
    node2, raw2v = _make_reader(raw2, values, swap)
    raw2v = (lambda f: (lambda var: f(topology, var, targets)))(raw2v)

    exp = cells["top"]["expected_under_contract"]
    for var in requested:
        if var in node_vars:
            got = raw2v(var)           # potential read directly under the NEW physical ground
            if not _close(exp[var], got):
                errs.append(f"top {var}: stored {exp[var]:.9g} != re-grounded spice {got:.9g}")
        else:
            # currents / element-voltage differences are reference-independent:
            # unchanged vs raw AND equal to the stored top-cell expectation
            if not _close(raw2v(var), rawv(var), rel=RUN2RUN_TOL):
                errs.append(f"top invariant {var}: re-grounded {raw2v(var):.9g} != raw {rawv(var):.9g}")
            if not _close(exp[var], rawv(var)):
                errs.append(f"top {var}: stored {exp[var]:.9g} != raw {rawv(var):.9g}")

    # zero-code invariant: the old bottom rail must sit at -V(top) of the original run
    old_ground_now = node2("0")        # original ground, read in the re-grounded run
    if not _close(old_ground_now, -node1(top_node), rel=RUN2RUN_TOL):
        errs.append(f"top ground-swap invariant: v_new(old ground)={old_ground_now:.9g} "
                    f"!= -v_raw(top)={-node1(top_node):.9g}")

    # ---- (C) diagnostic-mask consistency, straight from stored numbers ----
    for cell, inst in cells.items():
        expc = inst["expected_under_contract"]
        expd = inst["expected_under_default"]
        for var, flag in inst["diagnostic_vars"].items():
            a, b = expc[var], expd[var]
            want = (abs(a) > SIGN_EPS and abs(b) > SIGN_EPS and (a > 0) != (b > 0))
            if bool(flag) != want:
                errs.append(f"diag {cell} {var}: stored {flag} != recomputed {want}")

    return errs


def validate_dataset(dataset_dir: str, out_path: str | None = None) -> dict:
    """Validate every unique physics in the dataset. Returns (and writes) the summary."""
    by_physics: Dict[str, Dict[str, dict]] = defaultdict(dict)
    values: Dict[str, Tuple[str, dict]] = {}
    with open(os.path.join(dataset_dir, "instances.jsonl")) as f:
        for line in f:
            row = json.loads(line)
            cell = row["id"].rsplit("-", 2)[-2]           # ...-<cell>-<method>
            # one record per cell is enough (kvl/kcl share expectations)
            by_physics[row["physics_id"]].setdefault(cell, row)
            values[row["physics_id"]] = (row["topology"], row["values"])

    results, n_fail = [], 0
    for pid in sorted(by_physics):
        topo, vals = values[pid]
        errs = validate_physics(topo, vals, by_physics[pid])
        if errs:
            n_fail += 1
        results.append({"physics_id": pid, "status": "FAIL" if errs else "PASS", "errors": errs})

    summary = {
        "n_physics": len(results), "n_pass": len(results) - n_fail, "n_fail": n_fail,
        "checks": ["dflt==spice", "ccw==±raw", "act==±raw",
                   "top==re-grounded-spice + invariants", "diag-mask recomputation"],
        "rel_tol": REL_TOL,
        "results": results,
    }
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
    return summary
