"""Shared parameter-sampling helpers. Values are rounded to sig figs BEFORE solving so the
prompt, the analytic solution, and the SPICE netlist all see byte-identical numbers."""
from __future__ import annotations

import math

import numpy as np


def round_sig(x: float, sig: int = 3) -> float:
    if x == 0:
        return 0.0
    return float(round(x, -int(math.floor(math.log10(abs(x)))) + (sig - 1)))


def sample_resistor(rng: np.random.Generator, p) -> float:
    c = p["resistor"]
    lo, hi = math.log(c["low"]), math.log(c["high"])
    return round_sig(math.exp(rng.uniform(lo, hi)), p.get("round_sig_figs", 3))


def sample_voltage(rng: np.random.Generator, p, min_abs: float = 5.0) -> float:
    c = p["voltage_source"]
    while True:
        x = rng.uniform(c["low"], c["high"])
        if abs(x) >= min_abs:
            return round_sig(x, p.get("round_sig_figs", 3))


def sample_current(rng: np.random.Generator, p, min_abs_ma: float = 0.2) -> float:
    """Config range is in mA (see dataset.yaml); returns AMPS."""
    c = p["current_source"]
    while True:
        x = rng.uniform(c["low"], c["high"])
        if abs(x) >= min_abs_ma:
            return round_sig(x * 1e-3, p.get("round_sig_figs", 3))


def sample_gain(rng: np.random.Generator, p, min_abs: float = 0.25) -> float:
    c = p["dependent_gain"]
    while True:
        x = rng.uniform(c["low"], c["high"])
        if abs(x) >= min_abs:
            return round_sig(x, p.get("round_sig_figs", 3))
