"""3-loop supermesh (v1 Prob1), generalized: dependent CCCS gain k is sampled (v1 fixed k=2).

Layout (bottom rail = ground = node 0):
    node1(V1+) --R1--> node2(vx) --R2--> node3(vy) --R3--> node4(V2+)
    Is  : independent current source from ground UP into vx      (mesh1|mesh2 shared branch)
    CCCS: k*i1 from vy DOWN to ground, i1 = current through R1   (mesh2|mesh3 shared branch)

Canonical frame: i1,i2,i3 clockwise; vx,vy vs bottom rail; i_ds positive DOWNWARD through the
dependent branch; v_r2 = V(vx) - V(vy).
"""
from __future__ import annotations

from typing import Dict, List, Mapping

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_current, sample_gain, sample_resistor, sample_voltage


class Supermesh(Topology):
    name = "supermesh"
    title = "3-Loop Supermesh"
    mesh_vars = ("i1", "i2", "i3")
    node_vars = ("vx", "vy")
    branch_vars = ("i_ds",)
    element_vars = ("v_r2",)
    source_keys = ("V1", "V2")

    def sample(self, rng, p):
        return {
            "V1": sample_voltage(rng, p), "V2": sample_voltage(rng, p),
            "Is": sample_current(rng, p), "k": sample_gain(rng, p),
            "R1": sample_resistor(rng, p), "R2": sample_resistor(rng, p),
            "R3": sample_resistor(rng, p),
        }

    def solve_mesh(self, v) -> List[float]:
        # i2 - i1 = Is ; i2 - i3 = k*i1 ; R1*i1 + R2*i2 + R3*i3 = V1 - V2   (v1 rows, k general)
        k = v["k"]
        A = np.array([
            [-1.0, 1.0, 0.0],
            [-k, 1.0, -1.0],
            [v["R1"], v["R2"], v["R3"]],
        ])
        b = np.array([v["Is"], 0.0, v["V1"] - v["V2"]])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        # KCL at vx and vy with i1 = (V1 - vx)/R1 substituted into the CCCS term (v1, k general)
        R1, R2, R3, k = v["R1"], v["R2"], v["R3"], v["k"]
        G = np.array([
            [1 / R1 + 1 / R2, -1 / R2],
            [-1 / R2 - k / R1, 1 / R2 + 1 / R3],
        ])
        rhs = np.array([v["V1"] / R1 + v["Is"], v["V2"] / R3 - k * v["V1"] / R1])
        vx, vy = solve_checked(G, rhs)
        return {"vx": vx, "vy": vy}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, _, i3 = mesh
        return {"vx": v["V1"] - i1 * v["R1"], "vy": v["V2"] + i3 * v["R3"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        i1, i2, i3 = mesh
        return {
            "i_ds": i2 - i3,                        # downward through the dependent branch
            "v_r2": nodes["vx"] - nodes["vy"],      # + at the vx side
            TOP_REF_KEY: v["V1"],
        }

    def netlist(self, v) -> str:
        return f"""* supermesh (v2 procedural)
V1 1 0 DC {v['V1']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
Isrc 0 2 DC {v['Is']}
R2 2 2s {v['R2']}
Vsense_i2 2s 3 DC 0
Fdep 3 3d Vsense_i1 {v['k']}
Vsense_ids 3d 0 DC 0
R3 3 3s {v['R3']}
Vsense_i3 3s 4 DC 0
V2 4 0 DC {v['V2']}
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i3": "i(vsense_i3)",
            "i_ds": "i(vsense_ids)",
            "vx": "v(2)", "vy": "v(3)",
            "v_r2": ("diff", "v(2)", "v(3)"),
            TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Voltage Source V1={v['V1']}V (positive terminal up), "
            f"Top Resistor R1={v['R1']}Ω.\n"
            f"- Shared Branch (Mesh 1-2): Independent Current Source Is={v['Is']}A "
            f"(arrow pointing UP, from the bottom rail into the vx node).\n"
            f"- Mesh 2 (Center): Top Resistor R2={v['R2']}Ω.\n"
            f"- Shared Branch (Mesh 2-3): Dependent Current Source of value {v['k']}*i1 "
            f"(arrow pointing DOWN, from the vy node to the bottom rail), where i1 is the "
            f"current through R1 flowing from the V1 side toward vx.\n"
            f"- Mesh 3 (Right): Top Resistor R3={v['R3']}Ω, Voltage Source V2={v['V2']}V "
            f"(positive terminal up).\n"
            f"- vx: node between R1 and R2. vy: node between R2 and R3."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_ds: current through the dependent-source branch, positive flowing DOWNWARD "
                "(from the vy node to the bottom rail).",
                "v_r2: voltage across R2, defined v_r2 = V(vx) - V(vy) "
                "(positive terminal at the vx side).",
            ]
        return [
            "i_ds: current through the dependent-source branch, positive flowing UPWARD "
            "(from the bottom rail to the vy node).",
            "v_r2: voltage across R2, defined v_r2 = V(vy) - V(vx) "
            "(positive terminal at the vy side).",
        ]


register(Supermesh())
