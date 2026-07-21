"""Contour domain: golden hand-computed cases, four-way oracle agreement, contract
transforms, transform-validation identities, generator determinism + prompt content."""
from fractions import Fraction

import numpy as np
import pytest

from circuchain.contour.contract import (CELLS, DEFAULT, ROLE_FLUX, ROLE_WORK,
                                         ContourContract, apply, diagnostic_vars)
from circuchain.contour.curves import (ear_clip, flatten_values, poly_str, sample_verts,
                                       unflatten_values)
from circuchain.contour.fieldpoly import (poly2_from_ints, polygon_edge_works,
                                          polygon_flux, shoelace2)
from circuchain.contour.generate import build_prompt, generate_contour
from circuchain.contour.solvers import (inward_normal_flux, negated_field_works,
                                        reversed_traversal_works, solve_polygon,
                                        sympy_green)

F = Fraction
RECT = [(F(0), F(0)), (F(2), F(0)), (F(2), F(1)), (F(0), F(1))]   # (0,0)-(2,1), CCW


# ---------------- golden, fully hand-derived ----------------
def test_golden_rectangle_hand_computed():
    # F = (3x + 2y, x - y): curl = 1 - 2 = -1 -> wtot = -area = -2
    #                       div  = 3 - 1 =  2 -> phi  = 2*area = 4
    # e1 (0,0)->(2,0): dy=0, y=0:   ∫0..2 3x dx           =  6
    # e2 (2,0)->(2,1): dx=0, x=2:   ∫0..1 (2 - y) dy      =  3/2
    # e3 (2,1)->(0,1): dy=0, y=1:   ∫2..0 (3x + 2) dx     = -10
    # e4 (0,1)->(0,0): dx=0, x=0:   ∫1..0 (-y) dy         =  1/2
    p = poly2_from_ints({(1, 0): 3, (0, 1): 2})
    q = poly2_from_ints({(1, 0): 1, (0, 1): -1})
    out = solve_polygon(RECT, p, q, full_gate=True)
    assert out["e1"] == 6 and out["e2"] == F(3, 2)
    assert out["e3"] == -10 and out["e4"] == F(1, 2)
    assert out["wtot"] == -2 and out["phi"] == 4


def test_golden_pure_rotation_and_pure_source():
    tri = [(F(0), F(0)), (F(2), F(0)), (F(0), F(2))]              # area 2
    rot = {(0, 1): F(-1)}, {(1, 0): F(1)}                         # F=(-y, x): curl 2, div 0
    out = solve_polygon(tri, *rot, full_gate=True)
    assert out["wtot"] == 4 and out["phi"] == 0
    src = {(1, 0): F(1)}, {(0, 1): F(1)}                          # F=(x, y): curl 0, div 2
    out = solve_polygon(tri, *src, full_gate=True)
    assert out["wtot"] == 0 and out["phi"] == 4


# ---------------- four-way agreement on random samples, all families ----------------
@pytest.mark.parametrize("family", ["rectangle", "triangle", "quadrilateral",
                                    "lshape", "pentagon"])
def test_four_way_agreement(family):
    rng = np.random.default_rng([1234, hash(family) % 2**31])
    for _ in range(3):
        verts = sample_verts(family, rng)
        p = poly2_from_ints({(1, 0): int(rng.integers(-5, 6)) or 2,
                             (0, 2): int(rng.integers(-5, 6)) or 3,
                             (0, 0): int(rng.integers(-5, 6)) or 1})
        q = poly2_from_ints({(0, 1): int(rng.integers(-5, 6)) or -2,
                             (2, 0): int(rng.integers(-5, 6)) or 4,
                             (1, 1): int(rng.integers(-5, 6)) or 1})
        solve_polygon(verts, p, q, full_gate=True)     # raises on any route disagreement


def test_ear_clip_lshape_area_conservation():
    verts = [(F(0), F(0)), (F(3), F(0)), (F(3), F(1)), (F(1), F(1)),
             (F(1), F(3)), (F(0), F(3))]
    tris = ear_clip(verts)
    assert len(tris) == 4                                          # n - 2
    assert sum(shoelace2(list(t)) for t in tris) == shoelace2(verts) == 2 * 5


# ---------------- contract transforms ----------------
def test_contract_transforms_and_masks():
    canonical = {"e1": 6.0, "e2": 1.5, "e3": -10.0, "e4": 0.5, "wtot": -2.0, "phi": 4.0}
    roles = {k: (ROLE_FLUX if k == "phi" else ROLE_WORK) for k in canonical}
    cw = apply(CELLS["cw"], canonical, roles)
    assert cw["e1"] == -6.0 and cw["wtot"] == 2.0 and cw["phi"] == 4.0
    wrk = apply(CELLS["wrk"], canonical, roles)
    assert wrk == cw                       # the matched-transform pair: identical demand
    inw = apply(CELLS["inw"], canonical, roles)
    assert inw["phi"] == -4.0 and inw["e1"] == 6.0
    # cw+against double-flip cancels (XOR)
    both = apply(ContourContract(orientation="cw", work_sign="against"), canonical, roles)
    assert both["e1"] == 6.0 and both["phi"] == 4.0
    d = diagnostic_vars(CELLS["cw"], canonical, roles)
    assert d == {"e1": True, "e2": True, "e3": True, "e4": True, "wtot": True, "phi": False}
    d = diagnostic_vars(CELLS["inw"], canonical, roles)
    assert d == {"e1": False, "e2": False, "e3": False, "e4": False, "wtot": False,
                 "phi": True}
    assert diagnostic_vars(DEFAULT, canonical, roles) == {k: False for k in canonical}


# ---------------- transform validation identities ----------------
def test_independent_realizations_match_transforms():
    p = poly2_from_ints({(1, 0): 3, (0, 1): 2})
    q = poly2_from_ints({(1, 0): 1, (0, 1): -1})
    works = polygon_edge_works(p, q, RECT)
    rev = reversed_traversal_works(p, q, RECT)
    assert rev == [-w for w in works]                  # actually re-integrated, not negated
    neg = negated_field_works(p, q, RECT)
    assert neg == [-w for w in works]
    assert inward_normal_flux(p, q, RECT) == -polygon_flux(p, q, RECT)
    g = sympy_green(p, q, RECT)
    assert g["curl"] == sum(works) and g["div"] == polygon_flux(p, q, RECT)


# ---------------- values round-trip + prompt ----------------
def test_values_roundtrip_lossless():
    p = poly2_from_ints({(2, 0): -7, (1, 1): 3, (0, 0): 9})
    q = poly2_from_ints({(0, 2): 5, (1, 0): -1})
    v = flatten_values(RECT, p, q)
    verts2, p2, q2 = unflatten_values(v)
    assert verts2 == RECT and p2 == p and q2 == q


def test_prompt_states_conventions():
    p = poly2_from_ints({(1, 0): 3, (0, 1): 2})
    q = poly2_from_ints({(1, 0): 1, (0, 1): -1})
    dflt = build_prompt(RECT, p, q, CELLS["dflt"])
    assert "COUNTERCLOCKWISE" in dflt and "work done BY the field" in dflt
    assert "outward flux" in dflt and "ANSWER:" in dflt
    assert "e1=<number>" in dflt and "wtot=<number>" in dflt and "phi=<number>" in dflt
    cw = build_prompt(RECT, p, q, CELLS["cw"])
    assert "CLOCKWISE" in cw and "REVERSE of the usual counterclockwise" in cw
    wrk = build_prompt(RECT, p, q, CELLS["wrk"])
    assert "AGAINST" in wrk
    inw = build_prompt(RECT, p, q, CELLS["inw"])
    assert "INWARD" in inw
    green = build_prompt(RECT, p, q, ContourContract(method="green_thm"))
    assert "GREEN'S THEOREM" in green
    assert poly_str(p) == "3*x + 2*y"


# ---------------- generator: determinism + schema + gate ----------------
def test_generator_small_run_deterministic(tmp_path):
    cfg = {"n_physics": 5, "methods": ["PARAM", "GREEN"], "target_trap_fraction": 0.5,
           "families": [{"name": "rectangle"}, {"name": "triangle"}, {"name": "lshape"}],
           "field": {"degree2_prob": 0.7, "n_terms": [2, 4], "coeff_range": [-9, 9]},
           "reject": {"min_edge_mag": 0.25, "min_total_mag": 0.5, "max_mag": 5000}}
    m1 = generate_contour(cfg, 777, str(tmp_path / "a"), str(tmp_path))
    m2 = generate_contour(cfg, 777, str(tmp_path / "b"), str(tmp_path))
    assert m1["n_instances"] == 5 * 4 * 2 == 40
    assert m1["rejects"]["inconsistent"] == 0
    a = (tmp_path / "a" / "instances.jsonl").read_text()
    b = (tmp_path / "b" / "instances.jsonl").read_text()
    assert a == b                                       # byte-identical determinism
    import json
    rows = [json.loads(l) for l in a.splitlines()]
    r = rows[0]
    assert r["id"].rsplit("-", 2)[-2] == "dflt"         # grade-side cell parse works
    assert set(r["expected_under_contract"]) == set(r["canonical"])
    assert r["contract"]["method"] in ("param_direct", "green_thm")
    cw_rows = [x for x in rows if x["id"].rsplit("-", 2)[-2] == "cw"]
    assert all(x["diagnostic_vars"]["wtot"] for x in cw_rows)
    assert all(not x["diagnostic_vars"]["phi"] for x in cw_rows)
    assert all(x["diagnostic_vars"]["phi"] and not x["diagnostic_vars"]["wtot"]
               for x in rows if x["id"].rsplit("-", 2)[-2] == "inw")


# ---------------- hard-tier families + degree-3/4 fields ----------------
@pytest.mark.parametrize("family", ["hexagon", "staircase"])
def test_hard_families_four_way(family):
    rng = np.random.default_rng([99, hash(family) % 2**31])
    for _ in range(2):
        verts = sample_verts(family, rng)
        assert shoelace2(verts) > 0
        p = poly2_from_ints({(3, 0): 2, (1, 2): -3, (0, 1): 5})     # degree 3
        q = poly2_from_ints({(2, 2): 1, (4, 0): -2, (1, 0): 7})     # degree 4
        solve_polygon(verts, p, q, full_gate=True)


def test_staircase_geometry_and_rotation_golden():
    rng = np.random.default_rng(7)
    verts = sample_verts("staircase", rng)
    assert len(verts) == 8
    tris = ear_clip(verts)
    assert sum(shoelace2(list(t)) for t in tris) == shoelace2(verts)
    rot = poly2_from_ints({(0, 1): -1}), poly2_from_ints({(1, 0): 1})   # F=(-y,x)
    out = solve_polygon(verts, *rot, full_gate=True)
    assert out["wtot"] == 2 * (shoelace2(verts) / 2) and out["phi"] == 0


def test_generator_cells_filter_and_degree_dist(tmp_path):
    cfg = {"n_physics": 2, "methods": ["PARAM"], "cells": ["dflt", "cw", "wrk"],
           "target_trap_fraction": 0.5,
           "families": [{"name": "hexagon"}, {"name": "staircase"}],
           "field": {"degree_dist": {3: 0.5, 4: 0.5}, "n_terms": [3, 6],
                     "coeff_range": [-9, 9]},
           "reject": {"min_edge_mag": 0.5, "min_total_mag": 1.0, "max_mag": 200000}}
    m = generate_contour(cfg, 4242, str(tmp_path / "h"), str(tmp_path))
    assert m["n_instances"] == 2 * 3 * 1
    assert m["cells"] == ["dflt", "cw", "wrk"]
    import json
    rows = [json.loads(l) for l in (tmp_path / "h" / "instances.jsonl").read_text().splitlines()]
    assert {r["id"].rsplit("-", 2)[-2] for r in rows} == {"dflt", "cw", "wrk"}
    deg = max(int(k.split("_")[1][0]) + int(k.split("_")[1][1])
              for r in rows for k in r["values"] if k[0] in "pq" and "_" in k)
    assert deg >= 3
