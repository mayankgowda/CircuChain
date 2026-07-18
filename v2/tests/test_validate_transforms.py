"""Tests for the independent convention-transform validation (v2 methods-hole fix)."""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuchain.validate_transforms import relabel_ground, validate_physics  # noqa: E402

DATASET = os.path.join(os.path.dirname(__file__), "..",
                       "results", "datasets", "v2_seed20260709", "instances.jsonl")

PASSED = 0


def ok(name: str) -> None:
    global PASSED
    PASSED += 1
    print(f"PASS {name}")


def test_relabel_swaps_only_node_tokens():
    net = "* t\nV1 1 0 DC 30.9\nR1 1 1s 778.0\nVsense_i1 1s 2 DC 0\nFdep 3 3d Vsense_i1 -0.651\n.op\n.end\n"
    out = relabel_ground(net, "1")
    assert "V1 0 1 DC 30.9" in out            # nodes swapped
    assert "R1 0 1s 778.0" in out             # exact-match only: 1s untouched
    assert "Vsense_i1 1s 2 DC 0" in out       # value token 0 untouched (slot-limited)
    assert "Fdep 3 3d Vsense_i1 -0.651" in out  # F: token 3 is a source NAME, untouched
    ok("relabel_swaps_only_node_tokens")


def _load_physics(want_topos):
    by = defaultdict(dict)
    vals = {}
    with open(DATASET) as f:
        for line in f:
            r = json.loads(line)
            cell = r["id"].rsplit("-", 2)[-2]
            by[r["physics_id"]].setdefault(cell, r)
            vals[r["physics_id"]] = (r["topology"], r["values"])
    picked = {}
    for pid, (t, v) in vals.items():
        if t in want_topos and t not in picked and len(by[pid]) == 4:
            picked[t] = (pid, v, by[pid])
    return picked


def test_validate_passes_on_real_physics():
    # supermesh (dependent source) + wheatstone (RAW_DERIVED un-sensed mesh currents)
    picked = _load_physics({"supermesh", "wheatstone"})
    for topo, (pid, v, cells) in picked.items():
        errs = validate_physics(topo, v, cells)
        assert not errs, f"{pid}: {errs[:3]}"
    ok("validate_passes_on_real_physics")


def test_validator_catches_corruption():
    # poison the stored ccw expectation of a mesh var -> the raw-derivation check must fire
    picked = _load_physics({"supermesh"})
    pid, v, cells = picked["supermesh"]
    import copy
    bad = copy.deepcopy(cells)
    mv = "i1"
    bad["ccw"]["expected_under_contract"][mv] *= -1.0   # un-flip the flip
    errs = validate_physics("supermesh", v, bad)
    assert any(e.startswith("ccw i1") for e in errs), errs
    ok("validator_catches_corruption")


if __name__ == "__main__":
    test_relabel_swaps_only_node_tokens()
    test_validate_passes_on_real_physics()
    test_validator_catches_corruption()
    print(f"\n{PASSED}/3 passed")
