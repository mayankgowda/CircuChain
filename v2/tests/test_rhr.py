"""RHR domain: hand-computed goldens, four-way oracle, parity discipline, contract
transforms with flag-set roles, independent realizations, generator determinism."""
from fractions import Fraction

import numpy as np
import pytest

from circuchain.rhr.contract import CELLS, DEFAULT, RhrContract, apply, diagnostic_vars
from circuchain.rhr.families import FAMILIES, _gate_cross
from circuchain.rhr.generate import build_prompt, generate_rhr
from circuchain.rhr.vec import cross, cross_lc, dot, vec

F = Fraction


# ---------------- hand-computed goldens ----------------
def test_golden_single_cross_by_hand():
    # (1,0,0) x (0,0,1) = (0*1-0*0, 0*0-1*1, 1*0-0*0) = (0,-1,0)
    assert cross(vec(1, 0, 0), vec(0, 0, 1)) == (F(0), F(-1), F(0))
    assert cross_lc(vec(1, 0, 0), vec(0, 0, 1), +1) == (F(0), F(-1), F(0))
    # left-hand rule IS the negation: x-hat x y-hat = -z-hat
    assert cross_lc(vec(1, 0, 0), vec(0, 1, 0), -1) == (F(0), F(0), F(-1))


def test_golden_torque_rigid_two_forces():
    # P=(1,0,0); F1=(0,0,2)@p1=(2,0,0): (p1-P)=(1,0,0), tau1=(1,0,0)x(0,0,2)=(0,-2,0)
    # F2=(0,3,0)@p2=(1,1,0): (p2-P)=(0,1,0), tau2=(0,1,0)x(0,3,0)=(0,0,0)
    # tau=(0,-2,0); fnet=(0,3,2); wd=fnet.d with d=(1,1,1) -> 5
    fam = FAMILIES["torque_rigid"]
    values = {"n": 2.0, "pvx": 1.0, "pvy": 0.0, "pvz": 0.0,
              "px1": 2.0, "py1": 0.0, "pz1": 0.0, "fx1": 0.0, "fy1": 0.0, "fz1": 2.0,
              "px2": 1.0, "py2": 1.0, "pz2": 0.0, "fx2": 0.0, "fy2": 3.0, "fz2": 0.0,
              "dx": 1.0, "dy": 1.0, "dz": 1.0}
    out = fam.solve(values, full_gate=True)
    assert (out["tau_x"], out["tau_y"], out["tau_z"]) == (F(0), F(-2), F(0))
    assert (out["fnet_x"], out["fnet_y"], out["fnet_z"]) == (F(0), F(3), F(2))
    assert out["wd"] == 5


def test_golden_lorentz_orthogonality_and_value():
    fam = FAMILIES["lorentz_set"]
    values = {"n": 3.0}
    trip = [(2, (3, 0, 0), (0, 4, 0)),    # F = 2*(3,0,0)x(0,4,0) = (0,0,24)
            (-1, (1, 2, 3), (4, 5, 6)),
            (3, (0, 1, 0), (0, 0, 2))]
    for i, (q, v, b) in enumerate(trip, 1):
        values[f"q{i}"] = float(q)
        values[f"vx{i}"], values[f"vy{i}"], values[f"vz{i}"] = map(float, v)
        values[f"bx{i}"], values[f"by{i}"], values[f"bz{i}"] = map(float, b)
    out = fam.solve(values, full_gate=True)
    assert (out["f1_x"], out["f1_y"], out["f1_z"]) == (F(0), F(0), F(24))
    assert out["s"] == 0 + (4 + 10 + 18) + 0


# ---------------- parity discipline: lh flips exactly the single-cross vars ----------------
@pytest.mark.parametrize("fname", list(FAMILIES))
def test_lh_realization_matches_flagged_roles(fname):
    fam = FAMILIES[fname]
    rng = np.random.default_rng([55, hash(fname) % 2**31])
    values = fam.sample(rng, {})
    rh = fam.solve(values, full_gate=False)
    lh = fam.solve(values, full_gate=False, cross_fn=lambda a, b: cross_lc(a, b, -1))
    roles = fam.roles()
    for k in rh:
        if "cross" in roles[k].split("+"):
            assert lh[k] == -rh[k], f"{fname}.{k} should flip under LH"
        else:
            assert lh[k] == rh[k], f"{fname}.{k} should be LH-invariant"


# ---------------- contract flag-set semantics ----------------
def test_contract_flagsets_and_masks():
    canonical = {"tau_x": 4.0, "fnet_x": -3.0, "l_x": 2.0, "wd": 7.0}
    roles = {"tau_x": "cross+reactive", "fnet_x": "reactive", "l_x": "cross", "wd": ""}
    lh = apply(CELLS["lh"], canonical, roles)
    assert lh == {"tau_x": -4.0, "fnet_x": -3.0, "l_x": -2.0, "wd": 7.0}
    rxn = apply(CELLS["rxn"], canonical, roles)
    assert rxn == {"tau_x": -4.0, "fnet_x": 3.0, "l_x": 2.0, "wd": 7.0}
    both = apply(RhrContract(handedness="lh", pair="reaction"), canonical, roles)
    assert both == {"tau_x": 4.0, "fnet_x": 3.0, "l_x": -2.0, "wd": 7.0}   # tau double-flips
    d = diagnostic_vars(CELLS["lh"], canonical, roles)
    assert d == {"tau_x": True, "fnet_x": False, "l_x": True, "wd": False}
    d = diagnostic_vars(CELLS["rxn"], canonical, roles)
    assert d == {"tau_x": True, "fnet_x": True, "l_x": False, "wd": False}
    assert diagnostic_vars(DEFAULT, canonical, roles) == {k: False for k in canonical}


# ---------------- four-way gate + prompts ----------------
def test_gate_cross_all_routes():
    a, b = vec(3, -2, 5), vec(-1, 4, 2)
    c = _gate_cross(a, b)
    assert c == cross(a, b) and dot(c, a) == 0 and dot(c, b) == 0


def test_prompts_state_conventions():
    fam = FAMILIES["torque_rigid"]
    rng = np.random.default_rng(3)
    values = fam.sample(rng, {})
    dflt = build_prompt(fam, values, CELLS["dflt"])
    assert "RIGHT-HAND rule" in dflt and "ANSWER:" in dflt and "tau_x=<number>" in dflt
    lh = build_prompt(fam, values, CELLS["lh"])
    assert "LEFT-HAND rule" in lh and "REVERSE of the usual right-hand" in lh
    rxn = build_prompt(fam, values, CELLS["rxn"])
    assert "REACTION" in rxn and "Newton's-third-law" in rxn
    tr = build_prompt(fam, values, RhrContract(method="transfer"))
    assert "TRANSFER" in tr and "tau_P = tau_O - P x F_net" in tr


# ---------------- generator determinism + schema ----------------
def test_generator_deterministic_and_masks(tmp_path):
    cfg = {"n_physics": 3, "cells": ["dflt", "lh", "rxn"], "target_trap_fraction": 0.5,
           "families": [{"name": "torque_rigid"}, {"name": "angmom_system"},
                        {"name": "lorentz_set"}],
           "parameters": {}, "reject": {"min_diag_mag": 1, "max_mag": 3000}}
    m1 = generate_rhr(cfg, 909, str(tmp_path / "a"), str(tmp_path))
    m2 = generate_rhr(cfg, 909, str(tmp_path / "b"), str(tmp_path))
    assert (tmp_path / "a" / "instances.jsonl").read_text() == \
        (tmp_path / "b" / "instances.jsonl").read_text()
    assert m1["n_instances"] == 3 * 3 * 2
    assert m1["rejects"]["inconsistent"] == 0
    import json
    rows = [json.loads(l) for l in (tmp_path / "a" / "instances.jsonl").read_text().splitlines()]
    am = [r for r in rows if r["topology"] == "angmom_system"]
    for r in am:
        cell = r["id"].rsplit("-", 2)[-2]
        if cell == "lh":
            assert r["diagnostic_vars"]["l_x"] and r["diagnostic_vars"]["tau_x"]
            assert not r["diagnostic_vars"]["tk"]
        if cell == "rxn":
            assert r["diagnostic_vars"]["tau_x"] and not r["diagnostic_vars"]["l_x"]
