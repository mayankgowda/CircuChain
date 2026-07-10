"""The dual-verification gate: numpy solvers == exact MNA == NGSPICE on sampled instances
of every topology. Skips (exit 0 with a notice) if ngspice is not installed."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.topologies import TOPOLOGY_REGISTRY  # noqa: E402
from circuchain.verify import ngspice_available, verify_physics  # noqa: E402

PARAMS = {"resistor": {"low": 1e2, "high": 1e5}, "voltage_source": {"low": -100, "high": 100},
          "current_source": {"low": -10, "high": 10}, "dependent_gain": {"low": -4, "high": 4},
          "round_sig_figs": 3}


def test_spice_agrees_on_sampled_instances_every_topology():
    if not ngspice_available():
        print("NOTICE: ngspice not found; skipping SPICE gate test")
        return
    rng = np.random.default_rng(424242)
    bad = []
    for name, topo in sorted(TOPOLOGY_REGISTRY.items()):
        done = 0
        while done < 2:                       # 2 verified samples per topology
            values = topo.sample(rng, PARAMS)
            try:
                canonical = topo.solve(values)
            except Exception:                 # rejected sample — draw again
                continue
            errs = verify_physics(name, values, canonical, rel_tol=1e-4)
            bad += [f"{name}: {e}" for e in errs]
            done += 1
    assert not bad, "SPICE/MNA disagreements:\n" + "\n".join(bad)


def test_spice_agrees_on_v1_golden_values():
    if not ngspice_available():
        print("NOTICE: ngspice not found; skipping SPICE golden test")
        return
    from circuchain.topologies import get_topology
    cases = [
        ("supermesh", {"V1": 100, "V2": 40, "Is": 0.004, "k": 2,
                       "R1": 4000, "R2": 8000, "R3": 2000}),
        ("opposing_t", {"V1": 28, "V2": 7, "R1": 4, "R2": 1, "R_share": 2}),
        ("vcvs", {"V1": 3, "R1": 100, "R_share": 200, "R2": 300, "k": 5}),
        ("ladder", {"V": 52.0, **{f"R{i}": 10000.0 for i in range(1, 7)}}),
        ("wheatstone", {"V": 24, "R_LT": 150, "R_LB": 300, "R_RT": 50,
                        "R_RB": 250, "R_Br": 100}),
        ("supernode", {"Vs": 10, "Vf": 2, "R1": 1, "R2": 1, "R3": 1}),
        ("vccs_ladder", {"V1": 10, "g_mS": 1000.0, "R1": 1, "R2": 1, "R3": 1, "R4": 1}),
    ]
    bad = []
    for name, values in cases:
        canonical = get_topology(name).solve(values)
        errs = verify_physics(name, values, canonical, rel_tol=1e-4)
        bad += [f"{name}: {e}" for e in errs]
    assert not bad, "SPICE golden disagreements:\n" + "\n".join(bad)


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
