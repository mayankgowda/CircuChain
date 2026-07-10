"""2-mesh opposing-sources T-network (v1 Prob2, Kuphaldt archetype).

Layout: node1(V1+) --R1--> node2(vm) --R2--> node3(V2+); R_share from vm down to ground.
Canonical: i1,i2 clockwise; vm vs bottom rail; i_sh positive DOWNWARD through R_share;
v_r1 = V(node1) - V(vm). (v1 called the node voltage "v1"; renamed vm to avoid colliding
with the source name V1 in prompts/extraction.)
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_resistor, sample_voltage


class OpposingT(Topology):
    name = "opposing_t"
    title = "2-Loop T-Network with Opposing Sources"
    mesh_vars = ("i1", "i2")
    node_vars = ("vm",)
    branch_vars = ("i_sh",)
    element_vars = ("v_r1",)
    source_keys = ("V1", "V2")

    def sample(self, rng, p):
        return {
            "V1": sample_voltage(rng, p), "V2": sample_voltage(rng, p),
            "R1": sample_resistor(rng, p), "R2": sample_resistor(rng, p),
            "R_share": sample_resistor(rng, p),
        }

    def solve_mesh(self, v) -> List[float]:
        A = np.array([
            [v["R1"] + v["R_share"], -v["R_share"]],
            [-v["R_share"], v["R2"] + v["R_share"]],
        ])
        b = np.array([v["V1"], -v["V2"]])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        g = 1 / v["R1"] + 1 / v["R2"] + 1 / v["R_share"]
        return {"vm": (v["V1"] / v["R1"] + v["V2"] / v["R2"]) / g}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, i2 = mesh
        return {"vm": (i1 - i2) * v["R_share"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_sh": nodes["vm"] / v["R_share"],       # downward through R_share
            "v_r1": v["V1"] - nodes["vm"],            # + at the V1 side
            TOP_REF_KEY: v["V1"],
        }

    def netlist(self, v) -> str:
        return f"""* opposing_t (v2 procedural)
V1 1 0 DC {v['V1']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
Rsh 2 shs {v['R_share']}
Vsense_ish shs 0 DC 0
R2 2 2s {v['R2']}
Vsense_i2 2s 3 DC 0
V2 3 0 DC {v['V2']}
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i_sh": "i(vsense_ish)",
            "vm": "v(2)", "v_r1": ("diff", "v(1)", "v(2)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Independent Voltage Source V1={v['V1']}V (positive terminal up), "
            f"Top Resistor R1={v['R1']}Ω.\n"
            f"- Shared Branch: Vertical Resistor R_share={v['R_share']}Ω from the center node "
            f"down to the bottom rail.\n"
            f"- Mesh 2 (Right): Top Resistor R2={v['R2']}Ω, Independent Voltage Source "
            f"V2={v['V2']}V (positive terminal up).\n"
            f"- vm: node voltage at the top-center junction (top of R_share)."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_sh: current through R_share, positive flowing DOWNWARD "
                "(from the vm node to the bottom rail).",
                "v_r1: voltage across R1, defined v_r1 = V(V1-side node) - V(vm) "
                "(positive terminal at the V1 side).",
            ]
        return [
            "i_sh: current through R_share, positive flowing UPWARD "
            "(from the bottom rail to the vm node).",
            "v_r1: voltage across R1, defined v_r1 = V(vm) - V(V1-side node) "
            "(positive terminal at the vm side).",
        ]


register(OpposingT())
