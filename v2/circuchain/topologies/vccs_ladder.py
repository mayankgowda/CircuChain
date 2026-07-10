"""NEW in v2: 3-mesh ladder with a VCCS (voltage-controlled current source) output branch.
Completes the dependent-source matrix: v1 had a CCCS (supermesh) and a VCVS (vcvs); this adds
transconductance. Nodal analysis is direct (the VCCS adds one conductance-like term); mesh
analysis must handle a dependent current source in an outer branch (it pins mesh 3).

Layout: node1(V1+) --R1--> node2(A) --R3--> node3(B); R2 A->0; R4 B->0;
VCCS from B down to 0 (parallel with R4), value g*va with g in siemens (prompted in mS).
Canonical: i1,i2,i3 clockwise; va,vb vs bottom rail; i_r4 positive DOWNWARD through R4;
v_r3 = V(A) - V(B).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_gain, sample_resistor, sample_voltage


class VCCSLadder(Topology):
    name = "vccs_ladder"
    title = "3-Mesh Ladder with a Voltage-Controlled Current Source"
    mesh_vars = ("i1", "i2", "i3")
    node_vars = ("va", "vb")
    branch_vars = ("i_r4",)
    element_vars = ("v_r3",)
    source_keys = ("V1",)

    def sample(self, rng, p):
        return {
            "V1": sample_voltage(rng, p), "g_mS": sample_gain(rng, p),
            "R1": sample_resistor(rng, p), "R2": sample_resistor(rng, p),
            "R3": sample_resistor(rng, p), "R4": sample_resistor(rng, p),
        }

    @staticmethod
    def _g(v) -> float:
        return v["g_mS"] * 1e-3

    def solve_mesh(self, v) -> List[float]:
        # M1: (R1+R2)i1 - R2*i2 = V1
        # M2: -R2*i1 + (R2+R3+R4)i2 - R4*i3 = 0
        # M3 pinned by the VCCS: i3 = g*va = g*R2*(i1-i2)  ->  -g*R2*i1 + g*R2*i2 + i3 = 0
        g = self._g(v)
        A = np.array([
            [v["R1"] + v["R2"], -v["R2"], 0.0],
            [-v["R2"], v["R2"] + v["R3"] + v["R4"], -v["R4"]],
            [-g * v["R2"], g * v["R2"], 1.0],
        ])
        b = np.array([v["V1"], 0.0, 0.0])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        # A: (va-V1)/R1 + va/R2 + (va-vb)/R3 = 0
        # B: (vb-va)/R3 + vb/R4 + g*va = 0
        g = self._g(v)
        G = np.array([
            [1 / v["R1"] + 1 / v["R2"] + 1 / v["R3"], -1 / v["R3"]],
            [-1 / v["R3"] + g, 1 / v["R3"] + 1 / v["R4"]],
        ])
        rhs = np.array([v["V1"] / v["R1"], 0.0])
        va, vb = solve_checked(G, rhs)
        return {"va": va, "vb": vb}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, i2, i3 = mesh
        return {"va": (i1 - i2) * v["R2"], "vb": (i2 - i3) * v["R4"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_r4": nodes["vb"] / v["R4"],            # downward through R4
            "v_r3": nodes["va"] - nodes["vb"],        # + at the Node A side
            TOP_REF_KEY: v["V1"],
        }

    def netlist(self, v) -> str:
        return f"""* vccs_ladder (v2 procedural)
V1 1 0 DC {v['V1']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
R2 2 0 {v['R2']}
R3 2 2s {v['R3']}
Vsense_i2 2s 3 DC 0
R4 3 r4s {v['R4']}
Vsense_ir4 r4s 0 DC 0
Gdep 3 3g 2 0 {self._g(v)}
Vsense_i3 3g 0 DC 0
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i3": "i(vsense_i3)",
            "i_r4": "i(vsense_ir4)",
            "va": "v(2)", "vb": "v(3)",
            "v_r3": ("diff", "v(2)", "v(3)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Independent Voltage Source V1={v['V1']}V (positive terminal up), "
            f"Top Resistor R1={v['R1']}Ω, Shared Vertical Resistor R2={v['R2']}Ω.\n"
            f"- Mesh 2 (Center): Shared R2, Top Resistor R3={v['R3']}Ω, Shared Vertical "
            f"Resistor R4={v['R4']}Ω.\n"
            f"- Mesh 3 (Right): Shared R4 on the left; the right branch is a Dependent Current "
            f"Source (VCCS) from Node B down to the bottom rail, value g*va with "
            f"g={v['g_mS']} mS (i.e., {self._g(v)} A/V), arrow pointing DOWN.\n"
            f"- Control variable: va is the node voltage at Node A.\n"
            f"- Node A: junction of R1, R2, R3 (top of R2). Node B: junction of R3, R4, and "
            f"the VCCS (top of R4)."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_r4: current through R4, positive flowing DOWNWARD "
                "(from Node B to the bottom rail).",
                "v_r3: voltage across R3, defined v_r3 = V(A) - V(B) "
                "(positive terminal at Node A).",
            ]
        return [
            "i_r4: current through R4, positive flowing UPWARD "
            "(from the bottom rail to Node B).",
            "v_r3: voltage across R3, defined v_r3 = V(B) - V(A) "
            "(positive terminal at Node B).",
        ]


register(VCCSLadder())
