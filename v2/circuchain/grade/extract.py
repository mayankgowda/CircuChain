"""Deterministic answer extractor (build step 11) — retires v1's GPT-4o extraction.

Primary path: the prompt REQUIRES a final line `ANSWER: i1=..., vx=..., ...` in SI base
units. We take the LAST such line and parse name=value pairs.

Fallback path (extraction_mode='fallback'): per-variable regex over the response tail for
models that ignore the format. Deterministic unit multipliers (mA, uA, mV, kV) are applied
when a unit is attached to the number; bare values are taken as SI base units, as instructed.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_UNIT_MULT = {
    "a": 1.0, "v": 1.0, "amps": 1.0, "amperes": 1.0, "volts": 1.0,
    "ma": 1e-3, "mv": 1e-3, "ua": 1e-6, "µa": 1e-6, "uv": 1e-6, "µv": 1e-6,
    "ka": 1e3, "kv": 1e3,
}

_ANSWER_LINE = re.compile(r"^\s*\**\s*ANSWER\s*\**\s*[:=]\s*(.+?)\s*$",
                          re.IGNORECASE | re.MULTILINE)
_PAIR = re.compile(rf"([A-Za-z][A-Za-z0-9_]*)\s*[=:≈]\s*({_NUM})\s*([a-zA-Zµ]*)")


def _apply_unit(val: float, unit: str) -> Optional[float]:
    u = unit.strip().lower()
    if not u:
        return val
    if u in _UNIT_MULT:
        return val * _UNIT_MULT[u]
    return None                      # unrecognized trailing token -> reject this pair


def parse_answer_line(text: str) -> Dict[str, float]:
    """Parse the LAST ANSWER: line into {lowercase_name: value}."""
    matches = _ANSWER_LINE.findall(text)
    if not matches:
        return {}
    out: Dict[str, float] = {}
    for name, num, unit in _PAIR.findall(matches[-1]):
        val = _apply_unit(float(num), unit)
        if val is not None:
            out[name.lower()] = val
    return out


def parse_fallback(text: str, wanted: Tuple[str, ...], tail_chars: int = 1500) -> Dict[str, float]:
    """Scan the response tail for `var = value [unit]` statements, last occurrence wins."""
    tail = text[-tail_chars:]
    out: Dict[str, float] = {}
    for name in wanted:
        pat = re.compile(rf"\b{re.escape(name)}\s*[=:≈]\s*({_NUM})\s*([a-zA-Zµ]*)",
                         re.IGNORECASE)
        for num, unit in pat.findall(tail):
            val = _apply_unit(float(num), unit)
            if val is not None:
                out[name.lower()] = val         # keep overwriting: last statement wins
    return out


def extract(text: str, wanted: Tuple[str, ...]) -> Tuple[Dict[str, Optional[float]], str]:
    """Return ({var: value or None for every wanted var}, extraction_mode)."""
    parsed = parse_answer_line(text)
    mode = "answer_line"
    hits = sum(1 for w in wanted if w.lower() in parsed)
    if hits < len(wanted):
        fb = parse_fallback(text, wanted)
        for k, v in fb.items():
            parsed.setdefault(k, v)
        if hits == 0:
            mode = "fallback" if fb else "none"
        elif len(fb) > 0:
            mode = "answer_line+fallback"
    return {w: parsed.get(w.lower()) for w in wanted}, mode
