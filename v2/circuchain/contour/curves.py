"""Polygonal curve families + exact ear-clipping triangulation.

Five families (the topology axis of this domain): rectangle, triangle, convex
quadrilateral, L-shaped rectilinear hexagon (non-convex!), convex pentagon. All vertices
are small lattice points; every polygon is stored in CCW order (asserted by exact
shoelace), so route-2 Green integration over the ear-clip triangles carries the correct
positive orientation.

Values flattening: Instance.values must be Dict[str, float]; a physics sample is fully
described by the vertex coordinates (vx1, vy1, ...) and the field coefficients
(p_ij / q_ij for x^i y^j). Reconstruction back to exact Fractions is lossless because
every stored value is a small integer.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Mapping, Sequence, Tuple

from .fieldpoly import Point, Poly2, shoelace2

FAMILIES = ("rectangle", "triangle", "quadrilateral", "lshape", "pentagon",
            "hexagon", "staircase")   # hexagon/staircase: the hard-tier families


# ---------------- exact geometry primitives ----------------
def _cross(o: Point, a: Point, b: Point) -> Fraction:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _point_in_tri(pt: Point, a: Point, b: Point, c: Point) -> bool:
    """Strictly-inside-or-on-edge test via exact signed areas (CCW triangle)."""
    d1, d2, d3 = _cross(a, b, pt), _cross(b, c, pt), _cross(c, a, pt)
    return d1 >= 0 and d2 >= 0 and d3 >= 0


def ear_clip(verts: Sequence[Point]) -> List[Tuple[Point, Point, Point]]:
    """Triangulate a simple CCW polygon into CCW triangles (exact arithmetic)."""
    v = list(verts)
    assert shoelace2(v) > 0, "ear_clip requires CCW ordering"
    tris: List[Tuple[Point, Point, Point]] = []
    guard = 0
    while len(v) > 3:
        guard += 1
        assert guard < 10000, "ear_clip failed to converge (non-simple polygon?)"
        n = len(v)
        clipped = False
        for i in range(n):
            a, b, c = v[(i - 1) % n], v[i], v[(i + 1) % n]
            if _cross(a, b, c) <= 0:            # reflex or degenerate corner -> not an ear
                continue
            if any(_point_in_tri(p, a, b, c) for j, p in enumerate(v)
                   if j not in ((i - 1) % n, i, (i + 1) % n)):
                continue
            tris.append((a, b, c))
            del v[i]
            clipped = True
            break
        assert clipped, "no ear found (non-simple polygon?)"
    tris.append((v[0], v[1], v[2]))
    assert all(_cross(*t) > 0 for t in tris)
    # conservation check: triangle areas must sum to the polygon area, exactly
    assert sum(_cross(*t) for t in tris) == shoelace2(verts)
    return tris


# ---------------- sampling ----------------
def _lattice(rng, lo: int, hi: int) -> int:
    return int(rng.integers(lo, hi + 1))


def sample_verts(family: str, rng) -> List[Point]:
    """Draw one CCW lattice polygon of the given family (retry until valid)."""
    F = Fraction
    for _ in range(200):
        if family == "rectangle":
            x0, y0 = _lattice(rng, -6, 3), _lattice(rng, -6, 3)
            x1, y1 = x0 + _lattice(rng, 1, 6), y0 + _lattice(rng, 1, 6)
            return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]
        if family == "triangle":
            pts = [(F(_lattice(rng, -6, 6)), F(_lattice(rng, -6, 6))) for _ in range(3)]
            a2 = shoelace2(pts)
            if a2 == 0 or abs(a2) < 4:                      # area >= 2
                continue
            return pts if a2 > 0 else pts[::-1]
        if family == "lshape":
            x0 = _lattice(rng, -6, 1); x1 = x0 + _lattice(rng, 1, 3)
            x2 = x1 + _lattice(rng, 1, 3)
            y0 = _lattice(rng, -6, 1); y1 = y0 + _lattice(rng, 1, 3)
            y2 = y1 + _lattice(rng, 1, 3)
            return [(F(x0), F(y0)), (F(x2), F(y0)), (F(x2), F(y1)),
                    (F(x1), F(y1)), (F(x1), F(y2)), (F(x0), F(y2))]
        if family == "staircase":
            # rectilinear octagon (two-notch staircase): 8 edges, two reflex corners
            xs = [_lattice(rng, -8, -3)]
            for _ in range(3):
                xs.append(xs[-1] + _lattice(rng, 1, 3))
            ys = [_lattice(rng, -8, -3)]
            for _ in range(3):
                ys.append(ys[-1] + _lattice(rng, 1, 3))
            x0, x1, x2, x3 = xs
            y0, y1, y2, y3 = ys
            return [(F(x0), F(y0)), (F(x3), F(y0)), (F(x3), F(y1)), (F(x2), F(y1)),
                    (F(x2), F(y2)), (F(x1), F(y2)), (F(x1), F(y3)), (F(x0), F(y3))]
        # convex k-gon via exact convex-hull-of-k check
        K = {"quadrilateral": 4, "pentagon": 5, "hexagon": 6}[family]
        span = 8 if K == 6 else 6
        pts = {(_lattice(rng, -span, span), _lattice(rng, -span, span)) for _ in range(K)}
        if len(pts) < K:
            continue
        hull = _convex_hull([(F(x), F(y)) for x, y in pts])
        if len(hull) != K or shoelace2(hull) < {4: 4, 5: 6, 6: 8}[K]:
            continue
        return hull
    raise RuntimeError(f"could not sample a valid {family}")


def _convex_hull(pts: List[Point]) -> List[Point]:
    """Andrew monotone chain, exact; returns CCW hull without collinear points."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def half(seq):
        h: List[Point] = []
        for p in seq:
            while len(h) >= 2 and _cross(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h
    lower, upper = half(pts), half(pts[::-1])
    return lower[:-1] + upper[:-1]


# ---------------- values flattening (Instance.values round-trip) ----------------
def flatten_values(verts: Sequence[Point], p: Poly2, q: Poly2) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for i, (x, y) in enumerate(verts, 1):
        out[f"vx{i}"], out[f"vy{i}"] = float(x), float(y)
    for name, poly in (("p", p), ("q", q)):
        for (i, j), c in sorted(poly.items()):
            out[f"{name}_{i}{j}"] = float(c)
    return out


def unflatten_values(values: Mapping[str, float]) -> Tuple[List[Point], Poly2, Poly2]:
    """Lossless reconstruction (every stored value is a small integer)."""
    verts: List[Point] = []
    i = 1
    while f"vx{i}" in values:
        verts.append((Fraction(round(values[f"vx{i}"])), Fraction(round(values[f"vy{i}"]))))
        i += 1
    p: Poly2 = {}
    q: Poly2 = {}
    for k, v in values.items():
        if k[0] in "pq" and "_" in k:
            name, ij = k.split("_")
            (p if name == "p" else q)[(int(ij[0]), int(ij[1]))] = Fraction(round(v))
    return verts, p, q


def poly_str(p: Poly2) -> str:
    """Human-readable polynomial, canonical term order, e.g. '3*x^2 - 2*x*y + y - 5'."""
    if not p:
        return "0"
    def mono(i: int, j: int) -> str:
        xs = "" if i == 0 else ("x" if i == 1 else f"x^{i}")
        ys = "" if j == 0 else ("y" if j == 1 else f"y^{j}")
        return "*".join(t for t in (xs, ys) if t)
    parts: List[str] = []
    for (i, j), c in sorted(p.items(), key=lambda kv: (-(kv[0][0] + kv[0][1]), -kv[0][0])):
        m = mono(i, j)
        mag = abs(int(c))
        body = f"{mag}*{m}" if (m and mag != 1) else (m if m else str(mag))
        parts.append(("- " if c < 0 else "+ ") + body)
    s = " ".join(parts)
    return s[2:] if s.startswith("+ ") else ("-" + s[2:])
