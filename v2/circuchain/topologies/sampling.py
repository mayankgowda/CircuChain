"""Shared parameter-sampling helpers. Values are rounded to sig figs BEFORE solving so the
prompt, the analytic solution, and the SPICE netlist all see byte-identical numbers."""
from __future__ import annotations

import math

import numpy as np


def round_sig(x: float, sig: int = 3) -> float:
    if x == 0:
        return 0.0
    return float(round(x, -int(math.floor(math.log10(abs(x)))) + (sig - 1)))


def _bounds(p, key) -> tuple:
    # float() coercion: pyyaml parses unsigned-exponent literals like 1.0e2 as STRINGS
    c = p[key]
    return float(c["low"]), float(c["high"])


def sample_resistor(rng: np.random.Generator, p) -> float:
    lo, hi = _bounds(p, "resistor")
    return round_sig(math.exp(rng.uniform(math.log(lo), math.log(hi))),
                     p.get("round_sig_figs", 3))


def sample_voltage(rng: np.random.Generator, p, min_abs: float = 5.0) -> float:
    lo, hi = _bounds(p, "voltage_source")
    while True:
        x = rng.uniform(lo, hi)
        if abs(x) >= min_abs:
            return round_sig(x, p.get("round_sig_figs", 3))


def sample_current(rng: np.random.Generator, p, min_abs_ma: float = 0.2) -> float:
    """Config range is in mA (see dataset.yaml); returns AMPS."""
    lo, hi = _bounds(p, "current_source")
    while True:
        x = rng.uniform(lo, hi)
        if abs(x) >= min_abs_ma:
            return round_sig(x * 1e-3, p.get("round_sig_figs", 3))


def sample_gain(rng: np.random.Generator, p, min_abs: float = 0.25) -> float:
    lo, hi = _bounds(p, "dependent_gain")
    while True:
        x = rng.uniform(lo, hi)
        if abs(x) >= min_abs:
            return round_sig(x, p.get("round_sig_figs", 3))
