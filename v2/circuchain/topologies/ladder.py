"""3-loop resistive ladder (v1 Prob4).

Layout: node1(V+) --R1--> node2(v1) --R3--> node3(v2) --R5--> node4(v3);
verticals R2 (v1->0), R4 (v2->0), R6 (v3->0).
Canonical: i1,i2,i3 clockwise; v1,v2,v3 vs bottom rail; i_r4 positive DOWNWARD through R4;
v_r3 = V(v1) - V(v2).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_resistor, sample_voltage


class Ladder(Topology):
    name = "ladder"
    title = "3-Loop Resistive Ladder"
    mesh_vars = ("i1", "i2", "i3")
    node_vars = ("v1", "v2", "v3")
    branch_vars = ("i_r4",)
    element_vars = ("v_r3",)
    source_keys = ("V",)

    def sample(self, rng, p):
        vals = {"V": sample_voltage(rng, p)}
        for i in range(1, 7):
            vals[f"R{i}"] = sample_resistor(rng, p)
        return vals

    def solve_mesh(self, v) -> List[float]:
        A = np.array([
            [v["R1"] + v["R2"], -v["R2"], 0.0],
            [-v["R2"], v["R2"] + v["R3"] + v["R4"], -v["R4"]],
            [0.0, -v["R4"], v["R4"] + v["R5"] + v["R6"]],
        ])
        b = np.array([v["V"], 0.0, 0.0])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        G = np.array([
            [1 / v["R1"] + 1 / v["R2"] + 1 / v["R3"], -1 / v["R3"], 0.0],
            [-1 / v["R3"], 1 / v["R3"] + 1 / v["R4"] + 1 / v["R5"], -1 / v["R5"]],
            [0.0, -1 / v["R5"], 1 / v["R5"] + 1 / v["R6"]],
        ])
        rhs = np.array([v["V"] / v["R1"], 0.0, 0.0])
        n = solve_checked(G, rhs)
        return {"v1": n[0], "v2": n[1], "v3": n[2]}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, i2, i3 = mesh
        return {
            "v1": (i1 - i2) * v["R2"],
            "v2": (i2 - i3) * v["R4"],
            "v3": i3 * v["R6"],
        }

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_r4": nodes["v2"] / v["R4"],            # downward through R4
            "v_r3": nodes["v1"] - nodes["v2"],        # + at the v1 side
            TOP_REF_KEY: v["V"],
        }

    def netlist(self, v) -> str:
        return f"""* ladder (v2 procedural)
V1 1 0 DC {v['V']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
R2 2 0 {v['R2']}
R3 2 2s {v['R3']}
Vsense_i2 2s 3 DC 0
R4 3 r4s {v['R4']}
Vsense_ir4 r4s 0 DC 0
R5 3 3s {v['R5']}
Vsense_i3 3s 4 DC 0
R6 4 0 {v['R6']}
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i3": "i(vsense_i3)",
            "i_r4": "i(vsense_ir4)",
            "v1": "v(2)", "v2": "v(3)", "v3": "v(4)",
            "v_r3": ("diff", "v(2)", "v(3)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Source V={v['V']}V (positive terminal up), Series Resistor "
            f"R1={v['R1']}Ω (top), Shared Vertical R2={v['R2']}Ω.\n"
            f"- Mesh 2 (Center): Shared R2, Series Resistor R3={v['R3']}Ω (top), Shared "
            f"Vertical R4={v['R4']}Ω.\n"
            f"- Mesh 3 (Right): Shared R4, Series Resistor R5={v['R5']}Ω (top), Termination "
            f"Vertical R6={v['R6']}Ω.\n"
            f"- v1: node at the top of R2. v2: node at the top of R4. v3: node at the top of R6."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_r4: current through R4, positive flowing DOWNWARD "
                "(from the v2 node to the bottom rail).",
                "v_r3: voltage across R3, defined v_r3 = V(v1) - V(v2) "
                "(positive terminal at the v1 side).",
            ]
        return [
            "i_r4: current through R4, positive flowing UPWARD "
            "(from the bottom rail to the v2 node).",
            "v_r3: voltage across R3, defined v_r3 = V(v2) - V(v1) "
            "(positive terminal at the v2 side).",
        ]


register(Ladder())
