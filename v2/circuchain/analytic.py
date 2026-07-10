"""Analytic verification layer.

Two independent pieces:

1. ``EquationVerifier`` — v1 notebook port (cell 0). Checks whether a free-form equation
   string holds under the ground-truth values (used by the optional trace/audit stages).

2. ``mna_solve_netlist`` — an exact-arithmetic Modified-Nodal-Analysis solver that parses a
   SPICE netlist (the very same text handed to ngspice) and solves it symbolically with
   SymPy Rationals. This is a THIRD independent derivation of every instance:
       (a) hand-derived mesh matrix        (numpy, topologies/*.solve_mesh)
       (b) hand-derived nodal matrix       (numpy, topologies/*.solve_nodal)
       (c) generic MNA from the netlist    (sympy exact, here)
       (d) ngspice on the same netlist     (verify.py, external binary)
   A shared bug would have to appear identically in all four to survive the pipeline.

Supported devices: R, V, I, E (VCVS), G (VCCS), F (CCCS) — linear DC only, which is the
benchmark's deliberate scope (closed-form truth, no convergence questions).
"""
from __future__ import annotations

import re
from typing import Dict, List, Mapping, Tuple, Union

import sympy as sp

SpiceKey = Union[str, Tuple[str, str, str]]        # "v(2)" | ("diff", "v(2)", "v(3)")


# ==============================================================================
# 1. v1 EquationVerifier (ported verbatim-in-behavior from notebook cell 0)
# ==============================================================================
class EquationVerifier:
    """Standardize a free-form equation string and test it against truth values."""

    def clean_equation_string(self, eq_str: str) -> str:
        if not eq_str or not isinstance(eq_str, str) or eq_str.strip() == "":
            return "0"
        eq_str = eq_str.lower()
        eq_str = eq_str.replace("$", "").replace("\\", "").replace("{", "").replace("}", "")
        eq_str = eq_str.replace("[", "(").replace("]", ")")
        eq_str = re.sub(r"(\d)\s*k", r"\1*1000", eq_str)
        eq_str = re.sub(r"(?i)(ma|mv|v|a|ω|ohm)", "", eq_str)
        eq_str = re.sub(r"(\d)([a-z\(])", r"\1*\2", eq_str)
        if "=" in eq_str:
            lhs, _, rhs = eq_str.partition("=")
            rhs = rhs.strip() or "0"
            eq_str = f"({lhs.strip()}) - ({rhs})"
        return eq_str

    def verify(self, student_eq: str, truth_values: Mapping[str, float],
               tolerance: float = 0.1) -> dict:
        clean_eq = self.clean_equation_string(student_eq)
        try:
            expr = sp.sympify(clean_eq)
            sub_map = {sp.Symbol(k.lower()): v for k, v in truth_values.items()}
            residual = float(abs(expr.subs(sub_map)))
            return {"passed": residual < tolerance, "residual": residual, "cleaned_eq": clean_eq}
        except Exception as e:  # noqa: BLE001
            return {"passed": False, "residual": -1, "error": str(e)}


# ==============================================================================
# 2. Exact MNA netlist solver (independent derivation path (c))
# ==============================================================================
def _rat(tok: str) -> sp.Rational:
    return sp.Rational(str(tok))


def mna_solve_netlist(netlist: str) -> Dict[str, float]:
    """Parse a linear-DC SPICE netlist and solve it exactly. Returns {'v(node)': val,
    'i(devname)': val} with i() defined as ngspice does for V-type devices: positive current
    flows INTO the + (first) node terminal, through the device, out of the - node."""
    devices = []
    for raw in netlist.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("."):
            continue
        toks = line.split()
        devices.append(toks)

    nodes: List[str] = []

    def node_idx(n: str) -> int:
        if n == "0":
            return -1
        if n not in nodes:
            nodes.append(n)
        return nodes.index(n)

    # first pass: collect nodes and V-type branch unknowns (V sources, E sources)
    vbranches: List[str] = []           # device names, order = extra unknown index
    for t in devices:
        kind = t[0][0].upper()
        if kind in ("R", "V", "I"):
            node_idx(t[1]); node_idx(t[2])
        elif kind in ("E", "G"):
            node_idx(t[1]); node_idx(t[2]); node_idx(t[3]); node_idx(t[4])
        elif kind == "F":
            node_idx(t[1]); node_idx(t[2])
        else:
            raise ValueError(f"unsupported device in netlist: {t[0]}")
        if kind in ("V", "E"):
            vbranches.append(t[0].lower())

    n_n, n_b = len(nodes), len(vbranches)
    N = n_n + n_b
    A = sp.zeros(N, N)
    z = sp.zeros(N, 1)

    def stamp(i: int, j: int, val) -> None:
        if i >= 0 and j >= 0:
            A[i, j] += val

    def rhs(i: int, val) -> None:
        if i >= 0:
            z[i, 0] += val

    def bidx(name: str) -> int:
        return n_n + vbranches.index(name.lower())

    def strip_dc(toks: List[str]) -> str:
        return toks[1] if toks[0].upper() == "DC" else toks[0]

    for t in devices:
        kind = t[0][0].upper()
        if kind == "R":
            a, b = node_idx(t[1]), node_idx(t[2])
            g = 1 / _rat(t[3])
            stamp(a, a, g); stamp(b, b, g); stamp(a, b, -g); stamp(b, a, -g)
        elif kind == "V":
            a, b = node_idx(t[1]), node_idx(t[2])
            val = _rat(strip_dc(t[3:]))
            k = bidx(t[0])
            # branch current j flows a -> b through the source (ngspice i(V) convention)
            stamp(a, k, 1); stamp(b, k, -1)
            stamp(k, a, 1); stamp(k, b, -1)
            z[k, 0] += val
        elif kind == "I":
            a, b = node_idx(t[1]), node_idx(t[2])
            val = _rat(strip_dc(t[3:]))
            rhs(a, -val); rhs(b, val)          # current val flows a -> b through the source
        elif kind == "E":                       # E a b c d gain : V(a)-V(b) = gain*(V(c)-V(d))
            a, b = node_idx(t[1]), node_idx(t[2])
            c, d = node_idx(t[3]), node_idx(t[4])
            gain = _rat(t[5])
            k = bidx(t[0])
            stamp(a, k, 1); stamp(b, k, -1)
            stamp(k, a, 1); stamp(k, b, -1)
            stamp(k, c, -gain); stamp(k, d, gain)
        elif kind == "G":                       # G a b c d g : current g*(V(c)-V(d)) from a->b
            a, b = node_idx(t[1]), node_idx(t[2])
            c, d = node_idx(t[3]), node_idx(t[4])
            g = _rat(t[5])
            stamp(a, c, g); stamp(a, d, -g); stamp(b, c, -g); stamp(b, d, g)
        elif kind == "F":                       # F a b Vname gain : current gain*i(Vname) a->b
            a, b = node_idx(t[1]), node_idx(t[2])
            k = bidx(t[3])
            gain = _rat(t[4])
            stamp(a, k, gain); stamp(b, k, -gain)

    sol = A.solve(z)

    out: Dict[str, float] = {"v(0)": 0.0}
    for i, n in enumerate(nodes):
        out[f"v({n.lower()})"] = float(sol[i, 0])
    for j, name in enumerate(vbranches):
        out[f"i({name})"] = float(sol[n_n + j, 0])
    return out


def resolve_target(spice_out: Mapping[str, float], key: SpiceKey) -> float:
    """Resolve a topology spice_targets() entry against a parsed output map."""
    if isinstance(key, tuple):
        assert key[0] == "diff"
        return spice_out[key[1].lower()] - spice_out[key[2].lower()]
    return spice_out[key.lower()]


def dual_check(reference: Mapping[str, float], other: Mapping[str, float],
               rel_tol: float = 1e-4, abs_floor: float = 1e-9) -> List[str]:
    """Compare two var->value maps; return a list of mismatch descriptions (empty == agree)."""
    errs = []
    for k, ref in reference.items():
        if k not in other:
            errs.append(f"{k}: missing from comparison map")
            continue
        got = other[k]
        if abs(got - ref) > max(abs_floor, rel_tol * max(abs(ref), abs(got))):
            errs.append(f"{k}: ref {ref:.9g} != {got:.9g}")
    return errs
