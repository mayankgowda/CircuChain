"""Four-way exact oracle for polygon line integrals (the contour analogue of
mesh==nodal==MNA==NGSPICE — but stronger: three of the four routes are EXACT rational
arithmetic and must agree with zero tolerance).

    route 1  SymPy parametrized line integral per edge          (symbolic, exact)
    route 2  SymPy Green's theorem double integrals over an
             ear-clip triangulation (curl form for work, div
             form for flux)                                     (symbolic, exact,
                                                                 independent theorem)
    route 3  pure-Fraction binomial/power-rule engine            (no shared code/library)
    route 4  mpmath numerical quadrature                         (numeric, 1e-9)

Any disagreement raises InconsistentPhysics and the sample is rejected (in practice a
disagreement is impossible without a bug; the gate exists so the dataset can claim
`inconsistent = 0` by construction, like v2).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Sequence

import mpmath
import sympy as sp

from ..topologies.base import InconsistentPhysics
from .curves import ear_clip
from .fieldpoly import (Point, Poly2, polygon_edge_works, polygon_flux, segment_flux,
                        shoelace2)

NUMERIC_TOL = 1e-9

_x, _y, _t, _u, _v = sp.symbols("x y t u v")


def _sp_poly(p: Poly2):
    return sum(sp.Rational(c.numerator, c.denominator) * _x**i * _y**j
               for (i, j), c in p.items()) if p else sp.Integer(0)


def _frac(e) -> Fraction:
    e = sp.nsimplify(sp.simplify(e), rational=True)
    assert e.is_rational, f"non-rational exact integral: {e}"
    return Fraction(int(sp.numer(e)), int(sp.denom(e)))


def _edge_sub(expr, a: Point, b: Point):
    xs = sp.Rational(a[0].numerator, a[0].denominator) + \
        _t * sp.Rational((b[0] - a[0]).numerator, (b[0] - a[0]).denominator)
    ys = sp.Rational(a[1].numerator, a[1].denominator) + \
        _t * sp.Rational((b[1] - a[1]).numerator, (b[1] - a[1]).denominator)
    return expr.subs({_x: xs, _y: ys})


def sympy_edge_work(p: Poly2, q: Poly2, a: Point, b: Point) -> Fraction:
    """Route 1: W = ∫_0^1 [P(r(t)) dx + Q(r(t)) dy] dt, symbolic."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    integrand = _edge_sub(_sp_poly(p), a, b) * sp.Rational(dx.numerator, dx.denominator) + \
        _edge_sub(_sp_poly(q), a, b) * sp.Rational(dy.numerator, dy.denominator)
    return _frac(sp.integrate(integrand, (_t, 0, 1)))


def sympy_edge_flux(p: Poly2, q: Poly2, a: Point, b: Point) -> Fraction:
    """Route 1 flux: ∫ P dy - Q dx along A->B."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    integrand = _edge_sub(_sp_poly(p), a, b) * sp.Rational(dy.numerator, dy.denominator) - \
        _edge_sub(_sp_poly(q), a, b) * sp.Rational(dx.numerator, dx.denominator)
    return _frac(sp.integrate(integrand, (_t, 0, 1)))


def sympy_green(p: Poly2, q: Poly2, verts: Sequence[Point]) -> Dict[str, Fraction]:
    """Route 2: ∬(Qx - Py) dA and ∬(Px + Qy) dA over the ear-clip triangulation."""
    sp_p, sp_q = _sp_poly(p), _sp_poly(q)
    curl = sp.diff(sp_q, _x) - sp.diff(sp_p, _y)
    div = sp.diff(sp_p, _x) + sp.diff(sp_q, _y)
    tot = {"curl": sp.Integer(0), "div": sp.Integer(0)}
    for a, b, c in ear_clip(verts):
        def r(f: Fraction):
            return sp.Rational(f.numerator, f.denominator)
        xs = r(a[0]) + _u * r(b[0] - a[0]) + _v * r(c[0] - a[0])
        ys = r(a[1]) + _u * r(b[1] - a[1]) + _v * r(c[1] - a[1])
        jac = r((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        assert jac > 0                       # ear_clip emits CCW triangles
        for key, f in (("curl", curl), ("div", div)):
            inner = sp.integrate(f.subs({_x: xs, _y: ys}) * jac, (_u, 0, 1 - _v))
            tot[key] += sp.integrate(inner, (_v, 0, 1))
    return {k: _frac(e) for k, e in tot.items()}


def _numeric_edge(p: Poly2, q: Poly2, a: Point, b: Point, kind: str) -> float:
    """Route 4: mpmath quadrature of the same parametrized integrand."""
    ax, ay = float(a[0]), float(a[1])
    dx, dy = float(b[0] - a[0]), float(b[1] - a[1])
    def pe(x, y, poly):
        return sum(float(c) * x**i * y**j for (i, j), c in poly.items())
    if kind == "work":
        f = lambda t: pe(ax + dx * t, ay + dy * t, p) * dx + pe(ax + dx * t, ay + dy * t, q) * dy
    else:
        f = lambda t: pe(ax + dx * t, ay + dy * t, p) * dy - pe(ax + dx * t, ay + dy * t, q) * dx
    return float(mpmath.quad(f, [0, 1]))


def _close(a: float, b: float, tol: float = NUMERIC_TOL) -> bool:
    return abs(a - b) <= max(tol, tol * max(abs(a), abs(b)))


def solve_polygon(verts: Sequence[Point], p: Poly2, q: Poly2,
                  full_gate: bool = True) -> Dict[str, Fraction]:
    """Canonical exact answer in the DEFAULT frame (CCW traversal, work-by, outward
    normal). verts MUST be CCW. With full_gate, all four routes must agree.

    Returns {e1..ek: per-edge work, wtot, phi} as exact Fractions.
    """
    assert shoelace2(verts) > 0, "solve_polygon requires CCW vertices"
    n = len(verts)

    # route 3 (fast, exact) — the primary compute path
    works = polygon_edge_works(p, q, verts)
    wtot = sum(works, Fraction(0))
    phi = polygon_flux(p, q, verts)

    if full_gate:
        # route 1: per-edge symbolic must match route 3 EXACTLY
        for i in range(n):
            a, b = verts[i], verts[(i + 1) % n]
            w1 = sympy_edge_work(p, q, a, b)
            if w1 != works[i]:
                raise InconsistentPhysics(f"edge {i+1}: sympy {w1} != fraction {works[i]}")
        f1 = sum((sympy_edge_flux(p, q, verts[i], verts[(i + 1) % n]) for i in range(n)),
                 Fraction(0))
        if f1 != phi:
            raise InconsistentPhysics(f"flux: sympy {f1} != fraction {phi}")

        # route 2: Green's theorem totals must match EXACTLY
        g = sympy_green(p, q, verts)
        if g["curl"] != wtot:
            raise InconsistentPhysics(f"Green curl {g['curl']} != sum-of-edges {wtot}")
        if g["div"] != phi:
            raise InconsistentPhysics(f"Green div {g['div']} != boundary flux {phi}")

        # route 4: numeric quadrature within 1e-9
        for i in range(n):
            a, b = verts[i], verts[(i + 1) % n]
            if not _close(_numeric_edge(p, q, a, b, "work"), float(works[i])):
                raise InconsistentPhysics(f"edge {i+1}: numeric mismatch")
        num_phi = sum(_numeric_edge(p, q, verts[i], verts[(i + 1) % n], "flux")
                      for i in range(n))
        if not _close(num_phi, float(phi)):
            raise InconsistentPhysics("flux: numeric mismatch")

    out: Dict[str, Fraction] = {f"e{i+1}": w for i, w in enumerate(works)}
    out["wtot"] = wtot
    out["phi"] = phi
    return out


# ---- helpers used by transform validation (independent physical realizations) ----
def reversed_traversal_works(p: Poly2, q: Poly2, verts: Sequence[Point]) -> List[Fraction]:
    """Edge works actually re-integrated along the REVERSED traversal (cw positive):
    edge i (between V_i and V_{i+1}) traversed V_{i+1} -> V_i. Independent realization
    of the `cw` transform — not a negation shortcut."""
    from .fieldpoly import segment_work
    n = len(verts)
    return [segment_work(p, q, verts[(i + 1) % n], verts[i]) for i in range(n)]


def negated_field_works(p: Poly2, q: Poly2, verts: Sequence[Point]) -> List[Fraction]:
    """Edge works of the field -F along the normal CCW traversal. Independent realization
    of the `wrk` (work-done-against) transform."""
    np_ = {ij: -c for ij, c in p.items()}
    nq_ = {ij: -c for ij, c in q.items()}
    return polygon_edge_works(np_, nq_, verts)


def inward_normal_flux(p: Poly2, q: Poly2, verts: Sequence[Point]) -> Fraction:
    """Flux computed with the LEFT (inward-for-CCW) normal: ∫ Q dx - P dy. Independent
    realization of the `inw` transform."""
    n = len(verts)
    return sum((-segment_flux(p, q, verts[i], verts[(i + 1) % n]) for i in range(n)),
               Fraction(0))
