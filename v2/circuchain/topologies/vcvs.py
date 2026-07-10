"""2-mesh circuit with a VCVS dependent source (v1 Prob5, AAC archetype).

Layout: node1(V1+) --R1--> node2(vx); R_share vx->0; VCVS from vx to node3 with
V(node3) - V(vx) = k*vx (+ terminal at node3); R2 node3->0.
Canonical: i1,i2 clockwise; vx vs bottom rail; i_sh positive DOWNWARD through R_share;
v_dep = V(node3) - V(vx) = k*vx (+ at the node3 side).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .base import Topology, register, solve_checked, TOP_REF_KEY
from .sampling import sample_gain, sample_resistor, sample_voltage


class VCVS(Topology):
    name = "vcvs"
    title = "Two-Mesh Circuit with a Voltage-Controlled Voltage Source"
    mesh_vars = ("i1", "i2")
    node_vars = ("vx",)
    branch_vars = ("i_sh",)
    element_vars = ("v_dep",)
    source_keys = ("V1",)

    def sample(self, rng, p):
        return {
            "V1": sample_voltage(rng, p), "k": sample_gain(rng, p),
            "R1": sample_resistor(rng, p), "R2": sample_resistor(rng, p),
            "R_share": sample_resistor(rng, p),
        }

    def solve_mesh(self, v) -> List[float]:
        R1, R2, Rsh, k = v["R1"], v["R2"], v["R_share"], v["k"]
        A = np.array([
            [R1 + Rsh, -Rsh],
            [-Rsh * (1 + k), R2 + Rsh * (1 + k)],
        ])
        b = np.array([v["V1"], 0.0])
        return solve_checked(A, b)

    def solve_nodal(self, v) -> Dict[str, float]:
        R1, R2, Rsh, k = v["R1"], v["R2"], v["R_share"], v["k"]
        g_total = 1 / R1 + 1 / Rsh + (1 + k) / R2
        return {"vx": (v["V1"] / R1) / g_total}

    def nodes_from_mesh(self, v, mesh) -> Dict[str, float]:
        i1, i2 = mesh
        return {"vx": (i1 - i2) * v["R_share"]}

    def derived(self, v, mesh, nodes) -> Dict[str, float]:
        return {
            "i_sh": nodes["vx"] / v["R_share"],       # downward through R_share
            "v_dep": v["k"] * nodes["vx"],            # + at the node3 side
            TOP_REF_KEY: v["V1"],
        }

    def netlist(self, v) -> str:
        return f"""* vcvs (v2 procedural)
V1 1 0 DC {v['V1']}
R1 1 1s {v['R1']}
Vsense_i1 1s 2 DC 0
Rsh 2 shs {v['R_share']}
Vsense_ish shs 0 DC 0
Edep 3 2 2 0 {v['k']}
R2 3 r2s {v['R2']}
Vsense_i2 r2s 0 DC 0
.op
.end
"""

    def spice_targets(self):
        return {
            "i1": "i(vsense_i1)", "i2": "i(vsense_i2)", "i_sh": "i(vsense_ish)",
            "vx": "v(2)", "v_dep": ("diff", "v(3)", "v(2)"), TOP_REF_KEY: "v(1)",
        }

    def components_block(self, v) -> str:
        return (
            f"- Mesh 1 (Left): Independent Voltage Source V1={v['V1']}V (positive terminal up), "
            f"Top Resistor R1={v['R1']}Ω. Shares Vertical Resistor R_share={v['R_share']}Ω "
            f"with Mesh 2.\n"
            f"- Mesh 2 (Right): Shares R_share with Mesh 1. Top branch contains a Dependent "
            f"Voltage Source (negative terminal on the left/vx side, positive terminal on the "
            f"right). Right vertical branch contains Resistor R2={v['R2']}Ω.\n"
            f"- Dependent Source value: {v['k']} * vx.\n"
            f"- Control variable: vx is the voltage at the top-center node "
            f"(across R_share, positive at top)."
        )

    def reference_lines(self, psc: str) -> List[str]:
        if psc == "passive":
            return [
                "i_sh: current through R_share, positive flowing DOWNWARD "
                "(from the vx node to the bottom rail).",
                "v_dep: voltage across the dependent source, defined "
                "v_dep = V(right terminal) - V(vx) (positive terminal on the right).",
            ]
        return [
            "i_sh: current through R_share, positive flowing UPWARD "
            "(from the bottom rail to the vx node).",
            "v_dep: voltage across the dependent source, defined "
            "v_dep = V(vx) - V(right terminal) (positive terminal at the vx side).",
        ]


register(VCVS())
