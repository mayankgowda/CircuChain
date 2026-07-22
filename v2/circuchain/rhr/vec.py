"""Exact Fraction 3-vector arithmetic — two independent cross-product implementations.

Route C (component formulas) and route D (Levi-Civita summation) share no code path;
route D also provides the INDEPENDENT PHYSICAL REALIZATION of the left-handed convention
for transform validation: cross_lc with sign=-1 IS the left-hand rule (epsilon -> -epsilon),
not a negation shortcut.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence, Tuple

Vec = Tuple[Fraction, Fraction, Fraction]


def vec(x, y, z) -> Vec:
    return (Fraction(x), Fraction(y), Fraction(z))


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(k, a: Vec) -> Vec:
    k = Fraction(k)
    return (k * a[0], k * a[1], k * a[2])


def dot(a: Vec, b: Vec) -> Fraction:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec, b: Vec) -> Vec:
    """Route C: textbook component formulas (right-handed)."""
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


# Levi-Civita symbol as an explicit permutation table (route D's only ingredient)
_EPS = {(0, 1, 2): 1, (1, 2, 0): 1, (2, 0, 1): 1,
        (0, 2, 1): -1, (2, 1, 0): -1, (1, 0, 2): -1}


def cross_lc(a: Vec, b: Vec, sign: int = 1) -> Vec:
    """Route D: epsilon_ijk summation. sign=+1 right-handed; sign=-1 IS the left-hand rule."""
    out: List[Fraction] = [Fraction(0), Fraction(0), Fraction(0)]
    for (i, j, k), e in _EPS.items():
        out[k] += sign * e * a[i] * b[j]
    return (out[0], out[1], out[2])


def vsum(vs: Sequence[Vec]) -> Vec:
    t = (Fraction(0), Fraction(0), Fraction(0))
    for v in vs:
        t = add(t, v)
    return t
