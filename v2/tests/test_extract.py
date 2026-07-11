"""Golden cases for the deterministic answer extractor."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circuchain.grade.extract import extract, parse_answer_line  # noqa: E402

WANTED = ("i1", "i2", "vx", "i_sh", "v_r1")


def test_clean_answer_line():
    text = "reasoning...\nANSWER: i1=0.002, i2=-6.5e-3, vx=92.0, i_sh=0.004, v_r1=-12.5"
    pred, mode = extract(text, WANTED)
    assert mode == "answer_line"
    assert pred["i1"] == 0.002 and pred["i2"] == -6.5e-3 and pred["v_r1"] == -12.5


def test_last_answer_line_wins():
    text = "ANSWER: i1=1, i2=2, vx=3, i_sh=4, v_r1=5\nwait, recompute...\n" \
           "ANSWER: i1=9, i2=8, vx=7, i_sh=6, v_r1=5"
    pred, _ = extract(text, WANTED)
    assert pred["i1"] == 9 and pred["vx"] == 7


def test_units_converted_or_rejected():
    line = "ANSWER: i1=2mA, i2=3 A, vx=1.5V, i_sh=7uA, v_r1=2kV"
    d = parse_answer_line(line)
    assert abs(d["i1"] - 0.002) < 1e-12 and d["i2"] == 3.0 and d["vx"] == 1.5
    assert abs(d["i_sh"] - 7e-6) < 1e-15 and d["v_r1"] == 2000.0
    # unrecognized unit token -> pair rejected, not misparsed
    assert "i9" not in parse_answer_line("ANSWER: i9=3 furlongs")


def test_case_insensitive_names_and_markdown():
    text = "**ANSWER**: I1=-0.5, I2=0.25, VX=10, I_SH=0.1, V_R1=-3"
    pred, mode = extract(text, WANTED)
    assert mode == "answer_line" and pred["i1"] == -0.5 and pred["v_r1"] == -3


def test_fallback_scan():
    text = ("After solving the mesh equations we find i1 = -2.4e-3 A and i2 = 1.2e-3 A.\n"
            "The node voltage vx = 4.7 V. Also i_sh = 0.0012 A and v_r1 = 9.1 V. Done.")
    pred, mode = extract(text, WANTED)
    assert mode == "fallback"
    assert pred["i1"] == -2.4e-3 and pred["vx"] == 4.7 and pred["v_r1"] == 9.1


def test_missing_vars_are_none():
    pred, mode = extract("ANSWER: i1=1.0", WANTED)
    assert pred["i1"] == 1.0 and pred["i2"] is None and mode in ("answer_line", "answer_line+fallback")


def test_no_answer_at_all():
    pred, mode = extract("I cannot solve this.", WANTED)
    assert mode == "none" and all(v is None for v in pred.values())



def test_chained_equals_takes_final_value():
    # weak models write the expression then evaluate it; the LAST number is the answer
    line = "ANSWER: i1=0.002, i_ds=-0.651*0.00200= -0.00130, v_r2=0.00200*778.0= 1.556"
    d = parse_answer_line(line)
    assert d["i1"] == 0.002
    assert abs(d["i_ds"] - (-0.00130)) < 1e-12
    assert abs(d["v_r2"] - 1.556) < 1e-12


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
