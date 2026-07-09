"""Golden-fixture tests for the deterministic compliance grader (one per decision branch)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.grade.compliance import (  # noqa: E402
    grade_subtask, grade_variable, CORRECT, COMPLIANCE, COMPETENCE,
    V_PASS, V_SIGN_CONVENTION, V_VAL,
)

EXPECTED = {"i1": 0.002, "i2": 0.006, "i3": -0.002}     # contract-correct signed answer
DEFAULT = {"i1": 0.002, "i2": 0.006, "i3": 0.002}       # prior differs on i3 (sign)


def test_all_correct():
    g = grade_subtask({"i1": 0.002, "i2": 0.006, "i3": -0.002}, EXPECTED)
    assert g.label == CORRECT and g.magnitude_correct and g.sign_compliant


def test_pure_sign_flip_is_compliance_not_competence():
    # i3 magnitude right, sign wrong; everything else correct -> COMPLIANCE
    g = grade_subtask({"i1": 0.002, "i2": 0.006, "i3": 0.002}, EXPECTED)
    assert g.label == COMPLIANCE
    assert g.var_labels["i3"] == V_SIGN_CONVENTION
    assert g.magnitude_correct is True and g.sign_compliant is False  # 2x2: mag+/sign-


def test_convention_blind_matches_prior():
    # model produced exactly the default-prior value where the contract demanded the opposite sign
    lab = grade_variable(0.002, EXPECTED["i3"], DEFAULT["i3"])
    assert lab == V_SIGN_CONVENTION


def test_wrong_magnitude_is_competence():
    g = grade_subtask({"i1": 0.009, "i2": 0.006, "i3": -0.002}, EXPECTED)
    assert g.label == COMPETENCE
    assert g.var_labels["i1"] == V_VAL
    assert g.magnitude_correct is False


def test_mixed_sign_and_value_is_competence():
    # a sign flip AND a magnitude error -> competence dominates (not a *pure* convention failure)
    g = grade_subtask({"i1": 0.009, "i2": 0.006, "i3": 0.002}, EXPECTED)
    assert g.label == COMPETENCE


def test_missing_var_is_competence():
    g = grade_subtask({"i1": 0.002, "i2": 0.006}, EXPECTED)
    assert g.label == COMPETENCE


def test_within_tolerance_passes():
    # 4% off on i2 (< 5% tol) still passes
    g = grade_subtask({"i1": 0.002, "i2": 0.006 * 1.04, "i3": -0.002}, EXPECTED)
    assert g.var_labels["i2"] == V_PASS and g.label == CORRECT


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
