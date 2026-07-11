"""Known-answer tests for the analysis stage (Wilson, exact McNemar, pairing logic)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.analyze.stats import wilson_ci, mcnemar_exact, paired_counts  # noqa: E402
from circuchain.analyze.tables import analyze_graded  # noqa: E402


def test_wilson_known_values():
    lo, hi = wilson_ci(8, 10)
    assert abs(lo - 0.4902) < 5e-3 and abs(hi - 0.9433) < 5e-3   # standard reference values
    assert wilson_ci(0, 10)[0] == 0.0 and wilson_ci(10, 10)[1] > 1 - 1e-12


def test_mcnemar_exact_known_values():
    # b=9, c=1 -> two-sided exact p = 2*(C(10,0)+C(10,1))/2^10 = 22/1024
    r = mcnemar_exact(9, 1)
    assert abs(r["p"] - 22 / 1024) < 1e-12 and r["odds_ratio"] == 9.0
    assert mcnemar_exact(0, 0)["p"] == 1.0
    assert mcnemar_exact(5, 0)["odds_ratio"] == float("inf")
    # symmetric discordance -> p == 1
    assert mcnemar_exact(3, 3)["p"] == 1.0


def test_paired_counts():
    c = paired_counts([(True, True), (True, False), (True, False), (False, True),
                       (False, False)])
    assert c == {"both_ok": 1, "b": 2, "c": 1, "both_bad": 1}


def _row(model, pid, method, cell, dich, mag, sign, trunc=False):
    return {"model": model, "instance_id": f"{pid}-{cell}-{method.lower()}",
            "physics_id": pid, "topology": pid.split("-")[0], "regime": "control",
            "contract": {"method": method}, "cell": cell, "method": method,
            "dichotomy": dich, "magnitude_correct": mag, "sign_compliant": sign,
            "joint_cell": "", "var_labels": {}, "n_sign_convention": 0,
            "extraction_mode": "answer_line", "truncated": trunc, "think_len": 0}


def test_analyze_graded_pairs_and_rates():
    """Synthetic model: perfectly compliant under DEFAULT, convention-blind under ccw."""
    rows = []
    for i in range(6):
        pid = f"supermesh-{i:04d}"
        for method in ("mesh_kvl", "nodal_kcl"):
            rows.append(_row("toy", pid, method, "dflt", "CORRECT", True, True))
            # blind under ccw on 5 of 6 physics; compliant on one
            blind = i < 5
            rows.append(_row("toy", pid, method, "ccw",
                             "COMPLIANCE" if blind else "CORRECT", True, not blind))
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "toy.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        out = os.path.join(td, "tables")
        s = analyze_graded(td, out)
        fp = s["factor_pairs"]["toy|ccw|final_correct"]
        assert fp["n_pairs"] == 12 and fp["b"] == 10 and fp["c"] == 0
        assert fp["mcnemar"]["odds_ratio"] == float("inf")
        assert fp["mcnemar"]["p"] < 0.01                     # 2/2^10
        sgm = s["factor_pairs"]["toy|ccw|sign_given_mag"]
        assert sgm["n_pairs"] == 12 and sgm["b"] == 10       # pure convention effect isolated
        cr = s["cell_rates"]["toy|ccw|all"]
        assert cr["n"] == 12 and cr["dichotomy"]["COMPLIANCE"] == 10
        assert os.path.exists(os.path.join(out, "factor_pairs.csv"))
        assert os.path.exists(os.path.join(out, "cell_rates.csv"))


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
