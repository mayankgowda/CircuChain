"""Pure-Fraction exact line-integral engine — independent solver route #3.

Deliberately shares NO code or library with the SymPy routes: 2-D polynomials are
dicts {(i, j): Fraction} for coeff * x^i y^j, composition onto a segment is binomial
expansion, and integration is the power rule. Everything is exact rational arithmetic,
so agreement with SymPy is required to be EXACT (==), not within tolerance.

Sign conventions produced here are the canonical/textbook frame:
    work along A->B        W  = ∫ P dx + Q dy      (work done BY the field)
    flux across A->B       Fl = ∫ P dy - Q dx      (right normal of travel direction;
                                                    outward when the closed curve is CCW)
"""
from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import Dict, List, Sequence, Tuple

Poly2 = Dict[Tuple[int, int], Fraction]          # (i, j) -> coeff of x^i y^j
Point = Tuple[Fraction, Fraction]


def poly2_from_ints(terms: Dict[Tuple[int, int], int]) -> Poly2:
    return {ij: Fraction(c) for ij, c in terms.items() if c != 0}


def poly2_eval(p: Poly2, x: Fraction, y: Fraction) -> Fraction:
    return sum((c * x**i * y**j for (i, j), c in p.items()), Fraction(0))


def _compose_on_segment(p: Poly2, a: Point, b: Point) -> List[Fraction]:
    """p(x(t), y(t)) as 1-D coeffs [c0, c1, ...] for x = ax + t*dx, y = ay + t*dy."""
    ax, ay = a
    dx, dy = b[0] - a[0], b[1] - a[1]
    out: List[Fraction] = [Fraction(0)] * (max((i + j for i, j in p), default=0) + 1)
    for (i, j), c in p.items():
        # (ax + dx t)^i = sum_m C(i,m) ax^(i-m) dx^m t^m ; likewise for y^j
        xs = [comb(i, m) * ax ** (i - m) * dx ** m for m in range(i + 1)]
        ys = [comb(j, n) * ay ** (j - n) * dy ** n for n in range(j + 1)]
        for m, xc in enumerate(xs):
            for n, yc in enumerate(ys):
                out[m + n] += c * xc * yc
    return out


def _integrate01(coeffs: Sequence[Fraction]) -> Fraction:
    """∫_0^1 sum c_k t^k dt = sum c_k / (k+1)."""
    return sum((c / (k + 1) for k, c in enumerate(coeffs)), Fraction(0))


def segment_work(p: Poly2, q: Poly2, a: Point, b: Point) -> Fraction:
    """∫_{A->B} P dx + Q dy, exact."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    return dx * _integrate01(_compose_on_segment(p, a, b)) + \
        dy * _integrate01(_compose_on_segment(q, a, b))


def segment_flux(p: Poly2, q: Poly2, a: Point, b: Point) -> Fraction:
    """∫_{A->B} P dy - Q dx (right-normal flux), exact."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    return dy * _integrate01(_compose_on_segment(p, a, b)) - \
        dx * _integrate01(_compose_on_segment(q, a, b))


def polygon_edge_works(p: Poly2, q: Poly2, verts: Sequence[Point]) -> List[Fraction]:
    """Per-edge work along V_i -> V_{i+1} (the CCW traversal when verts are CCW)."""
    n = len(verts)
    return [segment_work(p, q, verts[i], verts[(i + 1) % n]) for i in range(n)]


def polygon_flux(p: Poly2, q: Poly2, verts: Sequence[Point]) -> Fraction:
    """Total outward flux for a CCW-ordered polygon."""
    n = len(verts)
    return sum((segment_flux(p, q, verts[i], verts[(i + 1) % n]) for i in range(n)),
               Fraction(0))


def shoelace2(verts: Sequence[Point]) -> Fraction:
    """Twice the signed area (positive for CCW ordering)."""
    n = len(verts)
    s = Fraction(0)
    for i in range(n):
        (x1, y1), (x2, y2) = verts[i], verts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s
