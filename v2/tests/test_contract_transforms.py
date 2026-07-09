"""Unit tests for the T1 sign transforms — the highest-novelty module. Get these right first."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.contract import (  # noqa: E402
    ConventionContract, DEFAULT, apply, diagnostic_vars,
    ROLE_MESH_CURRENT, ROLE_BRANCH_CURRENT, ROLE_NODE_VOLTAGE, ROLE_ELEMENT_VOLTAGE,
)

# A canonical (DEFAULT-frame) answer resembling the v1 supermesh instance, plus extra roles.
CANON = {"i1": 0.002, "i2": 0.006, "i3": -0.002, "vx": 92.0, "vy": 44.0, "ib": 0.004, "ve": 12.0}
ROLES = {
    "i1": ROLE_MESH_CURRENT, "i2": ROLE_MESH_CURRENT, "i3": ROLE_MESH_CURRENT,
    "vx": ROLE_NODE_VOLTAGE, "vy": ROLE_NODE_VOLTAGE,
    "ib": ROLE_BRANCH_CURRENT, "ve": ROLE_ELEMENT_VOLTAGE,
}
TOP_REF = "vx"


def test_default_is_identity():
    assert apply(DEFAULT, CANON, ROLES, TOP_REF) == CANON


def test_ccw_negates_only_mesh_currents():
    out = apply(ConventionContract(mesh_dir="ccw"), CANON, ROLES, TOP_REF)
    assert out["i1"] == -CANON["i1"] and out["i2"] == -CANON["i2"] and out["i3"] == -CANON["i3"]
    # non-mesh-current roles untouched
    assert out["vx"] == CANON["vx"] and out["ib"] == CANON["ib"] and out["ve"] == CANON["ve"]


def test_active_psc_negates_branch_and_element_only():
    out = apply(ConventionContract(psc="active"), CANON, ROLES, TOP_REF)
    assert out["ib"] == -CANON["ib"] and out["ve"] == -CANON["ve"]
    assert out["i1"] == CANON["i1"] and out["vx"] == CANON["vx"]


def test_top_ref_is_affine_on_node_voltages():
    out = apply(ConventionContract(ref_node="top"), CANON, ROLES, TOP_REF)
    vref = CANON[TOP_REF]
    assert out["vx"] == CANON["vx"] - vref            # == 0, the new reference
    assert out["vy"] == CANON["vy"] - vref
    assert out["i1"] == CANON["i1"]                    # currents unaffected


def test_top_ref_requires_key():
    try:
        apply(ConventionContract(ref_node="top"), CANON, ROLES, top_ref_key=None)
    except ValueError:
        return
    raise AssertionError("expected ValueError when top_ref_key missing")


def test_factors_compose_independently():
    c = ConventionContract(mesh_dir="ccw", psc="active", ref_node="top")
    out = apply(c, CANON, ROLES, TOP_REF)
    assert out["i1"] == -CANON["i1"]                   # mesh flip
    assert out["ib"] == -CANON["ib"]                   # psc flip
    assert out["vy"] == CANON["vy"] - CANON[TOP_REF]   # ref shift


def test_diagnostic_vars_flags_sign_disagreements():
    d = diagnostic_vars(ConventionContract(mesh_dir="ccw"), CANON, ROLES, TOP_REF)
    # mesh currents flip sign vs default -> diagnostic; voltages/branch don't -> not diagnostic
    assert d["i1"] is True and d["i2"] is True and d["i3"] is True
    assert d["vx"] is False and d["ib"] is False


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
