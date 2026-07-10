"""NEW in v2: two-mesh circuit with a FLOATING voltage source between the two non-reference
nodes — the classic supernode configuration. Mesh analysis sees an ordinary source in the top
branch; nodal analysis must merge nodes A and B into a supernode. That asymmetry makes the
required_method dimension bite hardest here.

Layout: node1(Vs+) --R1--> node2(A); R2 A->0; floating source Vf from A to B with
V(B) - V(A) = Vf (+ terminal at B); R3 B->0.
Canonical: i1,i2 clockwise; va,vb vs bottom rail; i_r2 positive DOWNWARD through R2;
v_r1 = V(node1) - V(A).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_resistor, sample_voltage


class Supernode(Topology):
    name = "supernode"
    title = "Two-Mesh Circuit with a Floating Voltage Source (Supernode)"
    mesh_vars = ("i1", "i2")
    node_vars = ("va", "vb")
    branch_vars = ("i_r2",)
    element_vars = ("v_r1",)
    source_keys = ("Vs", "Vf")

    def sample(self, rng, p):
        return {
            "Vs": sample_voltage(rng, p), "Vf": sample_voltage(rng, p),
            "R1": sample_resistor(rng, p), "R2": sample_resistor(rng, p),
            "R3": sample_resistor(rng, p),
        }

    def solve_mesh(self, v) -> List[float]:
        # M1: (R1+R2)i1 - R2*i2 = Vs ;  M2: -R2*i1 + (R2+R3)i2 = Vf
        A = np.array([
            [v["R1"] + v["R2"], -v["R2"]],
            [-v["R2"], v["R2"] + v["R3"]],
        ])
        b = np.array([v["Vs"], v["Vf"]])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        # supernode {A,B}: (va-Vs)/R1 + va/R2 + vb/R3 = 0 ; constraint vb - va = Vf
        A = np.array([
            [1 / v["R1"] + 1 / v["R2"], 1 / v["R3"]],
            [-1.0, 1.0],
        ])
        b = np.array([v["Vs"] / v["R1"], v["Vf"]])
        va, vb = solve_checked(A, b)
        return {"va": va, "vb": vb}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, i2 = mesh
        return {"va": (i1 - i2) * v["R2"], "vb": i2 * v["R3"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_r2": nodes["va"] / v["R2"],            # downward through R2
            "v_r1": v["Vs"] - nodes["va"],            # + at the Vs side
            TOP_REF_KEY: v["Vs"],
        }

    def netlist(self, v) -> str:
        return f"""* supernode (v2 procedural)
Vs 1 0 DC {v['Vs']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
R2 2 r2s {v['R2']}
Vsense_ir2 r2s 0 DC 0
Vf 3 2 DC {v['Vf']}
R3 3 3s {v['R3']}
Vsense_i2 3s 0 DC 0
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i_r2": "i(vsense_ir2)",
            "va": "v(2)", "vb": "v(3)",
            "v_r1": ("diff", "v(1)", "v(2)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Independent Voltage Source Vs={v['Vs']}V (positive terminal up), "
            f"Top Resistor R1={v['R1']}Ω, Shared Vertical Resistor R2={v['R2']}Ω.\n"
            f"- Top Branch (Mesh 2): a FLOATING Independent Voltage Source Vf={v['Vf']}V "
            f"connected between Node A and Node B, with its NEGATIVE terminal at Node A and "
            f"its POSITIVE terminal at Node B (so V(B) - V(A) = Vf).\n"
            f"- Mesh 2 (Right): Vertical Resistor R3={v['R3']}Ω from Node B down to the "
            f"bottom rail.\n"
            f"- Node A: junction of R1, R2, and the floating source. Node B: junction of the "
            f"floating source and R3."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_r2: current through R2, positive flowing DOWNWARD "
                "(from Node A to the bottom rail).",
                "v_r1: voltage across R1, defined v_r1 = V(Vs-side node) - V(A) "
                "(positive terminal at the Vs side).",
            ]
        return [
            "i_r2: current through R2, positive flowing UPWARD "
            "(from the bottom rail to Node A).",
            "v_r1: voltage across R1, defined v_r1 = V(A) - V(Vs-side node) "
            "(positive terminal at the Node A side).",
        ]


register(Supernode())
