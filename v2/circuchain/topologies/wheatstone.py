"""Unbalanced Wheatstone bridge (v1 Prob3, Kuphaldt archetype).

Layout: node1 = top rail (source +), node2 = A (left midpoint), node3 = B (right midpoint).
R_LT 1->2, R_LB 2->0, R_RT 1->3, R_RB 3->0, R_Br 2->3 (the bridge).
Canonical: i1 (source loop), i2 (top triangle), i3 (bottom triangle), all clockwise;
va, vb vs bottom rail; i_br positive A->B through the bridge; v_rbr = V(A) - V(B).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_resistor, sample_voltage


class Wheatstone(Topology):
    name = "wheatstone"
    title = "Unbalanced Wheatstone Bridge"
    mesh_vars = ("i1", "i2", "i3")
    node_vars = ("va", "vb")
    branch_vars = ("i_br",)
    element_vars = ("v_rbr",)
    source_keys = ("V",)

    def sample(self, rng, p):
        return {
            "V": sample_voltage(rng, p),
            "R_LT": sample_resistor(rng, p), "R_LB": sample_resistor(rng, p),
            "R_RT": sample_resistor(rng, p), "R_RB": sample_resistor(rng, p),
            "R_Br": sample_resistor(rng, p),
        }

    def solve_mesh(self, v) -> List[float]:
        R1, R3 = v["R_LT"], v["R_LB"]
        R2, R4 = v["R_RT"], v["R_RB"]
        R5 = v["R_Br"]
        A = np.array([
            [R1 + R3, -R1, -R3],
            [-R1, R1 + R2 + R5, -R5],
            [-R3, -R5, R3 + R4 + R5],
        ])
        b = np.array([v["V"], 0.0, 0.0])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        R1, R3 = v["R_LT"], v["R_LB"]
        R2, R4 = v["R_RT"], v["R_RB"]
        R5 = v["R_Br"]
        G = np.array([
            [1 / R1 + 1 / R3 + 1 / R5, -1 / R5],
            [-1 / R5, 1 / R2 + 1 / R4 + 1 / R5],
        ])
        rhs = np.array([v["V"] / R1, v["V"] / R2])
        va, vb = solve_checked(G, rhs)
        return {"va": va, "vb": vb}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, _, i3 = mesh
        # down-current through R_LB is (i1 - i3); through R_RB it is i3 (only mesh 3 touches it)
        return {"va": (i1 - i3) * v["R_LB"], "vb": i3 * v["R_RB"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_br": (nodes["va"] - nodes["vb"]) / v["R_Br"],   # A -> B through the bridge
            "v_rbr": nodes["va"] - nodes["vb"],                # + at the A side
            TOP_REF_KEY: v["V"],
        }

    def netlist(self, v) -> str:
        return f"""* wheatstone (v2 procedural)
Vsrc 1src 0 DC {v['V']}
Vsense_i1 1src 1 DC 0
Rlt 1 2 {v['R_LT']}
Rlb 2 0 {v['R_LB']}
Rrt 1 3 {v['R_RT']}
Rrb 3 0 {v['R_RB']}
Rbr 2 brs {v['R_Br']}
Vsense_ibr brs 3 DC 0
.op
.end
"""

    def spice_targets(self):
        # i2/i3 are loop currents, not single-branch currents -> validated indirectly through
        # va/vb/i1/i_br (every branch current is a linear combination of validated quantities).
        return {
            "i1": "i(vsense_i1)", "i_br": "i(vsense_ibr)",
            "va": "v(2)", "vb": "v(3)",
            "v_rbr": ("diff", "v(2)", "v(3)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Source: Independent Voltage Source V={v['V']}V between the top rail (positive "
            f"terminal) and the bottom rail.\n"
            f"- Left Leg: Top Resistor R_LT={v['R_LT']}Ω (top rail to Node A), Bottom Resistor "
            f"R_LB={v['R_LB']}Ω (Node A to bottom rail).\n"
            f"- Right Leg: Top Resistor R_RT={v['R_RT']}Ω (top rail to Node B), Bottom Resistor "
            f"R_RB={v['R_RB']}Ω (Node B to bottom rail).\n"
            f"- Bridge: Resistor R_Br={v['R_Br']}Ω connecting Node A to Node B.\n"
            f"- i1: mesh current of the Source Loop (V -> R_LT -> R_LB).\n"
            f"- i2: mesh current of the Top Triangle (R_LT -> R_RT -> R_Br).\n"
            f"- i3: mesh current of the Bottom Triangle (R_LB -> R_Br -> R_RB).\n"
            f"- va, vb: node voltages at Node A and Node B."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_br: current through the bridge resistor R_Br, positive flowing from "
                "Node A to Node B.",
                "v_rbr: voltage across R_Br, defined v_rbr = V(A) - V(B) "
                "(positive terminal at Node A).",
            ]
        return [
            "i_br: current through the bridge resistor R_Br, positive flowing from "
            "Node B to Node A.",
            "v_rbr: voltage across R_Br, defined v_rbr = V(B) - V(A) "
            "(positive terminal at Node B).",
        ]


register(Wheatstone())
