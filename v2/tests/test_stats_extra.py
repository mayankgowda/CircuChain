"""Tests for V2-3 stats hygiene (bootstrap OR CIs + Benjamini-Hochberg)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuchain.analyze.stats_extra import (  # noqa: E402
    benjamini_hochberg, bootstrap_or_ci, haldane_or)

PASSED = 0


def ok(name):
    global PASSED
    PASSED += 1
    print(f"PASS {name}")


def test_haldane():
    assert haldane_or(10, 0) == 10.5 / 0.5
    assert abs(haldane_or(63, 1) - 63.5 / 1.5) < 1e-12
    ok("haldane")


def test_bh_known():
    # classic worked example: sorted p * m / rank with monotonicity enforcement
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    assert abs(q[3] - 0.02) < 1e-12          # 0.005*4/1
    assert abs(q[0] - 0.02) < 1e-12          # 0.01*4/2
    assert abs(q[1] - 0.04) < 1e-12          # 0.04*4/4
    assert abs(q[2] - 0.04) < 1e-12          # min(0.03*4/3, next)=0.04
    assert all(qq <= 1.0 for qq in q)
    ok("bh_known")


def test_bootstrap_ci_brackets_effect():
    lo, hi = bootstrap_or_ci(179, 3, 250)
    assert 1.0 < lo < haldane_or(179, 3) < hi          # strong effect: CI above 1
    lo0, hi0 = bootstrap_or_ci(5, 5, 250)
    assert lo0 < 1.0 < hi0                              # null-ish effect: CI spans 1
    # determinism (seeded)
    assert bootstrap_or_ci(63, 1, 250) == bootstrap_or_ci(63, 1, 250)
    ok("bootstrap_ci_brackets_effect")


if __name__ == "__main__":
    test_haldane()
    test_bh_known()
    test_bootstrap_ci_brackets_effect()
    print(f"\n{PASSED}/3 passed")
