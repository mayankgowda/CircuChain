"""Statistics primitives: Wilson CIs and exact McNemar on within-physics matched pairs.

The unit of causal inference is the matched pair: the SAME physics instance, SAME model,
SAME required method, graded under the DEFAULT contract cell and under exactly one
single-factor flip (ccw / act / top). Discordant counts:
    b = compliant under DEFAULT, non-compliant under the flip   (the Convention-Blindness arm)
    c = non-compliant under DEFAULT, compliant under the flip
Exact McNemar p is the two-sided binomial test of b against Binomial(b+c, 1/2).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

from scipy.stats import binomtest


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def mcnemar_exact(b: int, c: int) -> Dict[str, float]:
    """Exact McNemar test on discordant pair counts. OR = b/c (inf if c == 0 and b > 0)."""
    n_disc = b + c
    if n_disc == 0:
        return {"b": b, "c": c, "odds_ratio": float("nan"), "p": 1.0}
    p = binomtest(min(b, c), n_disc, 0.5, alternative="two-sided").pvalue
    if c == 0:
        or_ = float("inf") if b > 0 else float("nan")
    else:
        or_ = b / c
    return {"b": b, "c": c, "odds_ratio": or_, "p": float(p)}


def paired_counts(pairs: Iterable[Tuple[bool, bool]]) -> Dict[str, int]:
    """Count concordant/discordant outcomes over (default_ok, flip_ok) pairs."""
    counts = {"both_ok": 0, "b": 0, "c": 0, "both_bad": 0}
    for d_ok, f_ok in pairs:
        if d_ok and f_ok:
            counts["both_ok"] += 1
        elif d_ok and not f_ok:
            counts["b"] += 1
        elif not d_ok and f_ok:
            counts["c"] += 1
        else:
            counts["both_bad"] += 1
    return counts
