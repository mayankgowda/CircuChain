"""RHR problem families. Every cross-derived variable = exactly ONE cross product.

Four-way oracle per physics (mirrors circuits/contour):
    route A  numpy float                      (1e-9)
    route B  SymPy Rational Matrix.cross      (exact)
    route C  Fraction component formulas      (exact, vec.cross)
    route D  Levi-Civita summation            (exact, vec.cross_lc — independent formula)
plus THEOREM checks: torque/ang-mom transfer identities (tau_P == tau_O - P x F_net) and
Lorentz orthogonality ((v x B) . v == 0 == (v x B) . B), all exact.

Differentiated flip masks (the design core):
    torque_rigid : tau {cross+reactive}, fnet {reactive}, wd {}
    angmom_system: l {cross}, tau {cross+reactive}, tk {}
    lorentz_set  : f1/f2 {cross+reactive}, s {}
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Mapping, Tuple

import numpy as np
import sympy as sp

from ..topologies.base import InconsistentPhysics
from .contract import RhrContract
from .vec import Vec, add, cross, cross_lc, dot, scale, sub, vec, vsum

NUM_TOL = 1e-9


def _v(values: Mapping[str, float], prefix: str) -> Vec:
    return vec(round(values[f"{prefix}x"]), round(values[f"{prefix}y"]),
               round(values[f"{prefix}z"]))


def _put(out: Dict[str, float], prefix: str, v) -> None:
    out[f"{prefix}x"], out[f"{prefix}y"], out[f"{prefix}z"] = (float(v[0]), float(v[1]),
                                                              float(v[2]))


def _sp_cross(a: Vec, b: Vec) -> Vec:
    r = sp.Matrix([sp.Rational(x) for x in a]).cross(sp.Matrix([sp.Rational(x) for x in b]))
    return (Fraction(int(sp.numer(r[0])), int(sp.denom(r[0]))),
            Fraction(int(sp.numer(r[1])), int(sp.denom(r[1]))),
            Fraction(int(sp.numer(r[2])), int(sp.denom(r[2]))))


def _np_cross(a: Vec, b: Vec):
    return np.cross(np.array(a, dtype=float), np.array(b, dtype=float))


def _gate_cross(a: Vec, b: Vec) -> Vec:
    """One cross product through all four routes; returns the exact value or raises."""
    c_ = cross(a, b)
    if cross_lc(a, b, +1) != c_:
        raise InconsistentPhysics("route D (Levi-Civita) != route C")
    if _sp_cross(a, b) != c_:
        raise InconsistentPhysics("route B (sympy) != route C")
    n = _np_cross(a, b)
    if any(abs(float(c_[i]) - n[i]) > NUM_TOL * max(1.0, abs(n[i])) for i in range(3)):
        raise InconsistentPhysics("route A (numpy) != route C")
    return c_


def _sample_vec(rng, lo: int, hi: int, nonzero: bool = True) -> Tuple[int, int, int]:
    while True:
        t = tuple(int(rng.integers(lo, hi + 1)) for _ in range(3))
        if not nonzero or any(t):
            return t


class TorqueRigid:
    name = "torque_rigid"
    methods = ("DIRECT", "TRANSFER")
    requested = ("tau_x", "tau_y", "tau_z", "fnet_x", "fnet_y", "fnet_z", "wd")

    def roles(self) -> Dict[str, str]:
        r = {f"tau_{c}": "cross+reactive" for c in "xyz"}
        r.update({f"fnet_{c}": "reactive" for c in "xyz"})
        r["wd"] = ""
        return r

    def sample(self, rng, p: Mapping) -> Dict[str, float]:
        n = int(rng.integers(int(p.get("n_forces_min", 5)), int(p.get("n_forces_max", 6)) + 1))
        out: Dict[str, float] = {"n": float(n)}
        pv = _sample_vec(rng, -4, 4)
        out["pvx"], out["pvy"], out["pvz"] = map(float, pv)
        for i in range(1, n + 1):
            while True:
                pt = _sample_vec(rng, -7, 7)
                if pt != pv:
                    break
            fr = _sample_vec(rng, -9, 9)
            out[f"px{i}"], out[f"py{i}"], out[f"pz{i}"] = map(float, pt)
            out[f"fx{i}"], out[f"fy{i}"], out[f"fz{i}"] = map(float, fr)
        d = _sample_vec(rng, -5, 5)
        out["dx"], out["dy"], out["dz"] = map(float, d)
        return out

    def solve(self, values: Mapping[str, float], full_gate: bool = True,
              cross_fn=None) -> Dict[str, Fraction]:
        n = round(values["n"])
        P = _v(values, "pv")
        gate = cross_fn or (_gate_cross if full_gate else cross)
        taus: List[Vec] = []
        forces: List[Vec] = []
        for i in range(1, n + 1):
            pt = vec(round(values[f"px{i}"]), round(values[f"py{i}"]), round(values[f"pz{i}"]))
            fr = vec(round(values[f"fx{i}"]), round(values[f"fy{i}"]), round(values[f"fz{i}"]))
            taus.append(gate(sub(pt, P), fr))
            forces.append(fr)
        tau = vsum(taus)
        fnet = vsum(forces)
        if full_gate:
            # theorem: tau_P == tau_O - P x F_net (exact)
            tau_o = vsum(cross(vec(round(values[f"px{i}"]), round(values[f"py{i}"]),
                                   round(values[f"pz{i}"])),
                               vec(round(values[f"fx{i}"]), round(values[f"fy{i}"]),
                                   round(values[f"fz{i}"]))) for i in range(1, n + 1))
            if sub(tau_o, cross(P, fnet)) != tau:
                raise InconsistentPhysics("transfer theorem violated (torque)")
        out: Dict[str, Fraction] = {}
        out["tau_x"], out["tau_y"], out["tau_z"] = tau
        out["fnet_x"], out["fnet_y"], out["fnet_z"] = fnet
        out["wd"] = dot(fnet, _v(values, "d"))
        return out

    def components_block(self, v: Mapping[str, float]) -> str:
        n = round(v["n"])
        L = [f"Pivot point P = ({v['pvx']:.0f}, {v['pvy']:.0f}, {v['pvz']:.0f})."]
        for i in range(1, n + 1):
            L.append(f"Force F{i} = ({v[f'fx{i}']:.0f}, {v[f'fy{i}']:.0f}, {v[f'fz{i}']:.0f}) N "
                     f"applied at point p{i} = ({v[f'px{i}']:.0f}, {v[f'py{i}']:.0f}, {v[f'pz{i}']:.0f}) m.")
        L.append(f"Displacement d = ({v['dx']:.0f}, {v['dy']:.0f}, {v['dz']:.0f}) m.")
        return "\n".join(L)

    def task_block(self, contract: RhrContract) -> str:
        if contract.pair == "action":
            pair = ("Report the NET TORQUE about P of the applied forces on the body "
                    "(tau_x, tau_y, tau_z) and the NET FORCE on the body (fnet_x, fnet_y, fnet_z).")
        else:
            pair = ("REACTION convention: report the net REACTION torque about P and the net "
                    "REACTION force — the Newton's-third-law partners that the body exerts "
                    "back on the agents applying the forces (NOT the quantities on the body).")
        if contract.method == "direct":
            meth = ("Required method: compute the torque DIRECTLY about P, i.e. sum "
                    "(p_i - P) x F_i term by term.")
        else:
            meth = ("Required method: use the TRANSFER (shift) theorem — first compute the "
                    "torque about the ORIGIN, then shift: tau_P = tau_O - P x F_net.")
        return (pair + "\nwd is the work F_net . d done by the applied forces' resultant "
                "along d; report wd as this dot product regardless of the reaction "
                "convention.\n" + meth)


class AngmomSystem:
    name = "angmom_system"
    methods = ("DIRECT", "TRANSFER")
    requested = ("l_x", "l_y", "l_z", "tau_x", "tau_y", "tau_z", "tk")

    def roles(self) -> Dict[str, str]:
        r = {f"l_{c}": "cross" for c in "xyz"}
        r.update({f"tau_{c}": "cross+reactive" for c in "xyz"})
        r["tk"] = ""
        return r

    def sample(self, rng, p: Mapping) -> Dict[str, float]:
        n = int(rng.integers(int(p.get("n_particles_min", 4)), int(p.get("n_particles_max", 5)) + 1))
        out: Dict[str, float] = {"n": float(n)}
        pv = _sample_vec(rng, -4, 4)
        out["pvx"], out["pvy"], out["pvz"] = map(float, pv)
        for i in range(1, n + 1):
            r = _sample_vec(rng, -7, 7)
            vl = _sample_vec(rng, -6, 6)
            g = _sample_vec(rng, -9, 9)
            out[f"rx{i}"], out[f"ry{i}"], out[f"rz{i}"] = map(float, r)
            out[f"vx{i}"], out[f"vy{i}"], out[f"vz{i}"] = map(float, vl)
            out[f"gx{i}"], out[f"gy{i}"], out[f"gz{i}"] = map(float, g)
            out[f"m{i}"] = float(int(rng.integers(1, 6)))
        return out

    def solve(self, values: Mapping[str, float], full_gate: bool = True,
              cross_fn=None) -> Dict[str, Fraction]:
        n = round(values["n"])
        P = _v(values, "pv")
        gate = cross_fn or (_gate_cross if full_gate else cross)
        Ls: List[Vec] = []
        taus: List[Vec] = []
        ptot = (Fraction(0), Fraction(0), Fraction(0))
        gnet = (Fraction(0), Fraction(0), Fraction(0))
        tk = Fraction(0)
        for i in range(1, n + 1):
            r = vec(round(values[f"rx{i}"]), round(values[f"ry{i}"]), round(values[f"rz{i}"]))
            vl = vec(round(values[f"vx{i}"]), round(values[f"vy{i}"]), round(values[f"vz{i}"]))
            g = vec(round(values[f"gx{i}"]), round(values[f"gy{i}"]), round(values[f"gz{i}"]))
            m = Fraction(round(values[f"m{i}"]))
            Ls.append(scale(m, gate(sub(r, P), vl)))
            taus.append(gate(sub(r, P), g))
            ptot = add(ptot, scale(m, vl))
            gnet = add(gnet, g)
            tk += Fraction(1, 2) * m * dot(vl, vl)
        L = vsum(Ls)
        tau = vsum(taus)
        if full_gate:
            l_o = vsum(scale(Fraction(round(values[f"m{i}"])),
                             cross(vec(round(values[f"rx{i}"]), round(values[f"ry{i}"]),
                                       round(values[f"rz{i}"])),
                                   vec(round(values[f"vx{i}"]), round(values[f"vy{i}"]),
                                       round(values[f"vz{i}"])))) for i in range(1, n + 1))
            if sub(l_o, cross(P, ptot)) != L:
                raise InconsistentPhysics("transfer theorem violated (angular momentum)")
            t_o = vsum(cross(vec(round(values[f"rx{i}"]), round(values[f"ry{i}"]),
                                 round(values[f"rz{i}"])),
                             vec(round(values[f"gx{i}"]), round(values[f"gy{i}"]),
                                 round(values[f"gz{i}"]))) for i in range(1, n + 1))
            if sub(t_o, cross(P, gnet)) != tau:
                raise InconsistentPhysics("transfer theorem violated (torque)")
        out: Dict[str, Fraction] = {}
        out["l_x"], out["l_y"], out["l_z"] = L
        out["tau_x"], out["tau_y"], out["tau_z"] = tau
        out["tk"] = tk
        return out

    def components_block(self, v: Mapping[str, float]) -> str:
        n = round(v["n"])
        L = [f"Reference point P = ({v['pvx']:.0f}, {v['pvy']:.0f}, {v['pvz']:.0f})."]
        for i in range(1, n + 1):
            L.append(f"Particle {i}: mass m{i} = {v[f'm{i}']:.0f} kg, position "
                     f"r{i} = ({v[f'rx{i}']:.0f}, {v[f'ry{i}']:.0f}, {v[f'rz{i}']:.0f}) m, velocity "
                     f"v{i} = ({v[f'vx{i}']:.0f}, {v[f'vy{i}']:.0f}, {v[f'vz{i}']:.0f}) m/s, applied force "
                     f"G{i} = ({v[f'gx{i}']:.0f}, {v[f'gy{i}']:.0f}, {v[f'gz{i}']:.0f}) N.")
        return "\n".join(L)

    def task_block(self, contract: RhrContract) -> str:
        if contract.pair == "action":
            pair = ("Report the system's total ANGULAR MOMENTUM about P (l_x, l_y, l_z) and "
                    "the NET TORQUE about P of the applied forces on the particles "
                    "(tau_x, tau_y, tau_z).")
        else:
            pair = ("REACTION convention for torque: report the net REACTION torque about P "
                    "(the Newton's-third-law partner the particles exert back on the agents), "
                    "NOT the torque on the particles. Angular momentum has no reaction "
                    "partner: report l_x, l_y, l_z normally (of the particles about P).")
        if contract.method == "direct":
            meth = ("Required method: compute L and the torque DIRECTLY about P, i.e. sum "
                    "m_i (r_i - P) x v_i and (r_i - P) x G_i term by term.")
        else:
            meth = ("Required method: use the TRANSFER (shift) theorem — compute both about "
                    "the ORIGIN first, then shift: L_P = L_O - P x p_total and "
                    "tau_P = tau_O - P x G_net.")
        return (pair + "\ntk is the total kinetic energy (1/2) sum m_i |v_i|^2; it is "
                "convention-independent.\n" + meth)


class LorentzSet:
    name = "lorentz_set"
    methods = ("DIRECT", "DET")
    requested = ("f1_x", "f1_y", "f1_z", "f2_x", "f2_y", "f2_z", "s")

    def roles(self) -> Dict[str, str]:
        r = {f"f{k}_{c}": "cross+reactive" for k in (1, 2) for c in "xyz"}
        r["s"] = ""
        return r

    def sample(self, rng, p: Mapping) -> Dict[str, float]:
        out: Dict[str, float] = {"n": 3.0}
        for i in range(1, 4):
            q = 0
            while q == 0:
                q = int(rng.integers(-5, 6))
            out[f"q{i}"] = float(q)
            vl = _sample_vec(rng, -7, 7)
            b = _sample_vec(rng, -7, 7)
            out[f"vx{i}"], out[f"vy{i}"], out[f"vz{i}"] = map(float, vl)
            out[f"bx{i}"], out[f"by{i}"], out[f"bz{i}"] = map(float, b)
        return out

    def solve(self, values: Mapping[str, float], full_gate: bool = True,
              cross_fn=None) -> Dict[str, Fraction]:
        gate = cross_fn or (_gate_cross if full_gate else cross)
        out: Dict[str, Fraction] = {}
        s = Fraction(0)
        for i in range(1, 4):
            vl = vec(round(values[f"vx{i}"]), round(values[f"vy{i}"]), round(values[f"vz{i}"]))
            b = vec(round(values[f"bx{i}"]), round(values[f"by{i}"]), round(values[f"bz{i}"]))
            f = scale(Fraction(round(values[f"q{i}"])), gate(vl, b))
            if full_gate and (dot(f, vl) != 0 or dot(f, b) != 0):
                raise InconsistentPhysics("Lorentz orthogonality violated")
            if i <= 2:
                _putf = f
                out[f"f{i}_x"], out[f"f{i}_y"], out[f"f{i}_z"] = _putf
            s += dot(vl, b)
        out["s"] = s
        return out

    def components_block(self, v: Mapping[str, float]) -> str:
        L = []
        for i in range(1, 4):
            L.append(f"Particle {i}: charge q{i} = {v[f'q{i}']:.0f} C, velocity "
                     f"v{i} = ({v[f'vx{i}']:.0f}, {v[f'vy{i}']:.0f}, {v[f'vz{i}']:.0f}) m/s, in local field "
                     f"B{i} = ({v[f'bx{i}']:.0f}, {v[f'by{i}']:.0f}, {v[f'bz{i}']:.0f}) T.")
        return "\n".join(L)

    def task_block(self, contract: RhrContract) -> str:
        if contract.pair == "action":
            pair = ("Report the magnetic force ON particle 1 (f1_x, f1_y, f1_z) and ON "
                    "particle 2 (f2_x, f2_y, f2_z), F = q v x B.")
        else:
            pair = ("REACTION convention: for particles 1 and 2 report the Newton's-third-law "
                    "partner of the magnetic force — the force the particle exerts back on "
                    "the field-source magnet system — NOT the force on the particle.")
        if contract.method == "direct":
            meth = ("Required method: use the component formulas directly, e.g. "
                    "(a x b)_x = a_y b_z - a_z b_y.")
        else:
            meth = ("Required method: evaluate each cross product by expanding the 3x3 "
                    "DETERMINANT with unit-vector first row.")
        return (pair + "\ns is the scalar sum v1.B1 + v2.B2 + v3.B3 (dot products); it is "
                "convention-independent.\n" + meth)


FAMILIES = {f.name: f for f in (TorqueRigid(), AngmomSystem(), LorentzSet())}
