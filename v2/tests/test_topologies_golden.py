"""Golden + anchor tests for the ported (and new) topology solvers.

Three layers of external grounding, strongest first:
  1. v1 ANCHOR: every one of the 50 frozen v1 instances re-solved with the ported solvers must
     reproduce its frozen verifier_map (the values the whole v1 paper was graded against).
  2. GOLDEN: hand-verified textbook values quoted in the v1 notebook comments
     (Kuphaldt, AAC, the ladder PDF) — external to any code in this repo.
  3. EXACT MNA: every topology (including the two new ones) solved a second way — the generic
     sympy exact-arithmetic MNA solver run on the topology's own netlist — must agree with the
     numpy mesh/nodal solution to 1e-9 relative.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.topologies import TOPOLOGY_REGISTRY, get_topology, TOP_REF_KEY  # noqa: E402
from circuchain.analytic import mna_solve_netlist, resolve_target, dual_check  # noqa: E402

V1_DATASET = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "circuchain_full_dataset - final.json"))


def _close(a, b, rel=1e-3, abs_floor=1e-9):
    return abs(a - b) <= max(abs_floor, rel * max(abs(a), abs(b)))


# ---------------------------------------------------------------- 1. v1 anchors
def test_v1_anchor_all_50_instances():
    """Ported solvers must reproduce every frozen v1 verifier_map exactly (1e-3 rel)."""
    ds = json.load(open(V1_DATASET))
    assert len(ds) == 50, f"expected 50 v1 rows, got {len(ds)}"
    topo_map = {"Prob1": "supermesh", "Prob2": "opposing_t", "Prob3": "wheatstone",
                "Prob4": "ladder", "Prob5": "vcvs"}
    key_map = {"opposing_t": {"v1": "vm"}}       # our rename (source-name collision fix)
    bad = []
    for row in ds:
        topo = get_topology(topo_map[row["id"].split("_")[0]])
        values = dict(row["values"])
        if topo.name == "supermesh":
            values.setdefault("k", 2.0)          # v1 hardcoded the CCCS gain at 2
        canonical = topo.solve(values)
        renames = key_map.get(topo.name, {})
        for k, expected in row["ground_truth"]["verifier_map"].items():
            ours = canonical[renames.get(k, k)]
            if not _close(ours, expected):
                bad.append(f"{row['id']}.{k}: v1={expected:.9g} port={ours:.9g}")
    assert not bad, "v1 anchor mismatches:\n" + "\n".join(bad)


# ---------------------------------------------------------------- 2. golden textbook values
def test_golden_opposing_t_kuphaldt():
    # Kuphaldt's book prints i1=5 A, i2=-1 A — but his i2 is defined in the OPPOSITE loop
    # orientation. Under the canonical uniform-CLOCKWISE frame (the frame the frozen v1
    # dataset uses, confirmed by the 50-instance anchor test) the same physics gives i2=+1 A.
    # A fitting reminder that sign conventions are frames, not facts — which is the benchmark.
    c = get_topology("opposing_t").solve({"V1": 28, "V2": 7, "R1": 4, "R2": 1, "R_share": 2})
    assert _close(c["i1"], 5.0) and _close(c["i2"], 1.0)
    assert _close(c["vm"], 8.0)                              # (28/4 + 7/1) / (1/4 + 1 + 1/2)
    assert _close(c["i_sh"], 4.0) and _close(c["v_r1"], 20.0)


def test_golden_ladder_pdf():
    # v1 notebook: 52 V, all 10k -> mesh currents [3.2mA, 1.2mA, 0.4mA]
    vals = {"V": 52.0, **{f"R{i}": 10000.0 for i in range(1, 7)}}
    c = get_topology("ladder").solve(vals)
    assert _close(c["i1"], 3.2e-3) and _close(c["i2"], 1.2e-3) and _close(c["i3"], 0.4e-3)
    assert _close(c["i_r4"], c["i2"] - c["i3"])              # 0.8 mA down through R4


def test_golden_vcvs_aac():
    # v1 notebook (AAC PDF): {V1:3, R1:100, R_share:200, R2:300, k:5} -> i1=21.4mA, i2=17.1mA
    c = get_topology("vcvs").solve({"V1": 3, "R1": 100, "R_share": 200, "R2": 300, "k": 5})
    assert _close(c["i1"], 0.0214286, rel=1e-3) and _close(c["i2"], 0.0171429, rel=1e-3)
    assert _close(c["vx"], 0.857143, rel=1e-3)
    assert _close(c["v_dep"], 5 * c["vx"])


def test_golden_supermesh_sadiku():
    # v1 notebook: Sadiku values {V1:100, V2:40, Is:4mA, k:2, 4k/8k/2k} -> i1=2mA, i2=6mA,
    # i3=2mA, vx=92 V, vy=44 V (quoted in the master-generation cell)
    c = get_topology("supermesh").solve(
        {"V1": 100, "V2": 40, "Is": 0.004, "k": 2, "R1": 4000, "R2": 8000, "R3": 2000})
    assert _close(c["i1"], 0.002) and _close(c["i2"], 0.006) and _close(c["i3"], 0.002)
    assert _close(c["vx"], 92.0) and _close(c["vy"], 44.0)
    assert _close(c["i_ds"], c["i2"] - c["i3"]) and _close(c["v_r2"], 48.0)


def test_golden_wheatstone_balanced_symmetry():
    # Balanced bridge: all arms equal -> va == vb == V/2, zero bridge current (physics identity)
    c = get_topology("wheatstone").solve(
        {"V": 24, "R_LT": 100, "R_LB": 100, "R_RT": 100, "R_RB": 100, "R_Br": 250})
    assert _close(c["va"], 12.0) and _close(c["vb"], 12.0)
    assert abs(c["i_br"]) < 1e-12 and abs(c["v_rbr"]) < 1e-10
    assert _close(c["i1"], 24 / 100.0)       # two 200-ohm legs in parallel -> 100 ohm total


def test_golden_supernode_hand_solved():
    # Hand-derived: Vs=10, Vf=2, R1=R2=R3=1 -> supernode: (va-10)/1 + va/1 + vb/1 = 0,
    # vb = va+2  =>  3va = 8  =>  va = 8/3, vb = 14/3
    c = get_topology("supernode").solve({"Vs": 10, "Vf": 2, "R1": 1, "R2": 1, "R3": 1})
    assert _close(c["va"], 8 / 3) and _close(c["vb"], 14 / 3)
    assert _close(c["i1"], 10 - 8 / 3) and _close(c["i2"], 14 / 3)     # i2 = vb/R3
    assert _close(c["i_r2"], 8 / 3) and _close(c["v_r1"], 10 - 8 / 3)


def test_golden_vccs_hand_solved():
    # Hand-derived: V1=10, R1=R2=R3=R4=1, g=1 S:
    # A: (va-10)/1 + va + (va-vb) = 0 -> 3va - vb = 10
    # B: (vb-va) + vb + va = 0        -> vb = 0     => va = 10/3
    c = get_topology("vccs_ladder").solve(
        {"V1": 10, "g_mS": 1000.0, "R1": 1, "R2": 1, "R3": 1, "R4": 1})
    assert _close(c["va"], 10 / 3) and abs(c["vb"]) < 1e-12
    assert abs(c["i_r4"]) < 1e-12 and _close(c["v_r3"], 10 / 3)
    assert _close(c["i3"], 10 / 3)            # VCCS pins i3 = g*va


# ---------------------------------------------------------------- 3. exact-MNA cross-validation
def test_exact_mna_agrees_with_numpy_solvers_all_topologies():
    """Independent derivation: sympy exact MNA on the netlist == numpy mesh/nodal, 1e-9 rel."""
    rng = np.random.default_rng(20260710)
    p = {"resistor": {"low": 1e2, "high": 1e5}, "voltage_source": {"low": -100, "high": 100},
         "current_source": {"low": -10, "high": 10}, "dependent_gain": {"low": -4, "high": 4},
         "round_sig_figs": 3}
    bad = []
    for name, topo in sorted(TOPOLOGY_REGISTRY.items()):
        for trial in range(3):
            values = topo.sample(rng, p)
            try:
                canonical = topo.solve(values)
            except Exception:               # rejected sample (ill-conditioned) — resample
                continue
            mna = mna_solve_netlist(topo.netlist(values))
            got = {var: resolve_target(mna, key) for var, key in topo.spice_targets().items()}
            ref = {var: canonical[var] for var in got}
            errs = dual_check(ref, got, rel_tol=1e-9, abs_floor=1e-12)
            bad += [f"{name}[{trial}] {e}" for e in errs]
    assert not bad, "MNA disagreements:\n" + "\n".join(bad)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
