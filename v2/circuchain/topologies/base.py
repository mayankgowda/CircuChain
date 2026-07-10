"""Topology ABC + registry (T3). Ported/generalized from the v1 notebook's CircuitProblem.

Every topology supplies TWO independent hand-derived solvers (mesh/KVL matrix and nodal/KCL
matrix). `solve()` runs both, reconstructs every node voltage from the mesh solution, and
REJECTS the sample unless the two formulations agree — that internal cross-check, plus the
external NGSPICE gate in verify.py, is the dual-verification story: an error would have to
appear identically in three independent derivations to slip through.

Canonical frame (== v1's implicit textbook prior, == contract.DEFAULT):
    * mesh currents clockwise
    * node voltages referenced to the bottom rail (ground)
    * branch/element references in the per-topology stated arrow direction (passive convention)
The canonical map also carries the auxiliary key ``v_top`` — the potential of the designated
top-reference node (the + terminal of the left independent source) — which contract.apply()
uses for the ref_node=top affine shift. ``v_top`` is never a requested output.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Mapping, Tuple

import numpy as np

from ..contract import (
    ConventionContract,
    ROLE_BRANCH_CURRENT,
    ROLE_ELEMENT_VOLTAGE,
    ROLE_MESH_CURRENT,
    ROLE_NODE_VOLTAGE,
)

TOP_REF_KEY = "v_top"          # aux canonical entry: potential of the top-reference node
CONSISTENCY_TOL = 1e-6         # rel tol for mesh-vs-nodal cross-check (reject sample if exceeded)
COND_LIMIT = 1e8               # reject ill-conditioned samples (keeps the 1e-4 SPICE gate honest)


class InconsistentPhysics(RuntimeError):
    """Mesh and nodal formulations disagree — the sampled instance is rejected."""


def _rel_close(a: float, b: float, rel: float = CONSISTENCY_TOL, abs_tol: float = 1e-9) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b)))


def solve_checked(A: np.ndarray, b: np.ndarray) -> List[float]:
    """np.linalg.solve with a condition-number guard."""
    cond = np.linalg.cond(A)
    if not np.isfinite(cond) or cond > COND_LIMIT:
        raise InconsistentPhysics(f"ill-conditioned system (cond={cond:.3g})")
    return np.linalg.solve(A, b).tolist()


class Topology(ABC):
    """One circuit family. Subclasses implement the physics; the base assembles everything else."""

    name: str = ""
    title: str = ""                         # human title used in the prompt
    mesh_vars: Tuple[str, ...] = ()
    node_vars: Tuple[str, ...] = ()
    branch_vars: Tuple[str, ...] = ()       # extra branch currents (distinct from mesh currents)
    element_vars: Tuple[str, ...] = ()      # element voltages
    source_keys: Tuple[str, ...] = ()       # independent V-source value keys (regime tagging)
    top_ref_desc: str = "the TOP-LEFT node (the positive terminal of the left source)"

    # ---------------- physics (subclass) ----------------
    @abstractmethod
    def sample(self, rng: np.random.Generator, p: Mapping) -> Dict[str, float]:
        """Draw one parameter set (already rounded to sig figs) from the config distributions."""

    @abstractmethod
    def solve_mesh(self, v: Mapping[str, float]) -> List[float]:
        """Clockwise mesh currents [i1..iN] — independent formulation #1."""

    @abstractmethod
    def solve_nodal(self, v: Mapping[str, float]) -> Dict[str, float]:
        """Node voltages (bottom-rail reference) — independent formulation #2."""

    @abstractmethod
    def nodes_from_mesh(self, v: Mapping[str, float], mesh: List[float]) -> Dict[str, float]:
        """Reconstruct every node voltage from the mesh solution (cross-check path)."""

    @abstractmethod
    def derived(self, v: Mapping[str, float], mesh: List[float],
                nodes: Mapping[str, float]) -> Dict[str, float]:
        """Branch currents + element voltages + v_top, in the canonical frame."""

    # ---------------- SPICE (subclass) ----------------
    @abstractmethod
    def netlist(self, v: Mapping[str, float]) -> str:
        """NGSPICE .op netlist with 0V V_sense sensors for every measured current."""

    @abstractmethod
    def spice_targets(self) -> Dict[str, str]:
        """canonical var -> ngspice output key (e.g. i1 -> 'i(v_sense_i1)', vx -> 'v(2)')."""

    # ---------------- prompt (subclass supplies the pieces) ----------------
    @abstractmethod
    def components_block(self, v: Mapping[str, float]) -> str:
        """The **Components** description (values interpolated)."""

    @abstractmethod
    def reference_lines(self, psc: str) -> List[str]:
        """One line per branch/element var stating its reference direction/polarity under `psc`."""

    # ---------------- assembled behavior (base) ----------------
    def requested_vars(self) -> Tuple[str, ...]:
        return self.mesh_vars + self.node_vars + self.branch_vars + self.element_vars

    def roles(self) -> Dict[str, str]:
        r: Dict[str, str] = {TOP_REF_KEY: ROLE_NODE_VOLTAGE}
        r.update({k: ROLE_MESH_CURRENT for k in self.mesh_vars})
        r.update({k: ROLE_NODE_VOLTAGE for k in self.node_vars})
        r.update({k: ROLE_BRANCH_CURRENT for k in self.branch_vars})
        r.update({k: ROLE_ELEMENT_VOLTAGE for k in self.element_vars})
        return r

    def solve(self, v: Mapping[str, float]) -> Dict[str, float]:
        """Canonical signed answer. Raises InconsistentPhysics unless mesh == nodal everywhere."""
        mesh = self.solve_mesh(v)
        nodes = self.solve_nodal(v)
        recon = self.nodes_from_mesh(v, mesh)
        for k, nv in nodes.items():
            if not _rel_close(recon[k], nv):
                raise InconsistentPhysics(
                    f"{self.name}: node {k} mesh-derived {recon[k]:.9g} != nodal {nv:.9g}")
        out: Dict[str, float] = {}
        out.update({k: mesh[i] for i, k in enumerate(self.mesh_vars)})
        out.update({k: nodes[k] for k in self.node_vars})
        out.update(self.derived(v, mesh, nodes))
        missing = [k for k in self.requested_vars() + (TOP_REF_KEY,) if k not in out]
        if missing:
            raise RuntimeError(f"{self.name}: solve() missing {missing}")
        return out

    # regime tagging — code predicates, not hand labels (dataset.yaml regime_tags)
    def regime_tags(self, v: Mapping[str, float], canonical: Mapping[str, float]) -> List[str]:
        tags: List[str] = []
        rs = [val for key, val in v.items() if key.startswith("R")]
        if rs and max(rs) / min(rs) > 100:
            tags.append("max_r_ratio_gt_100")
        if canonical[self.mesh_vars[0]] < 0:
            tags.append("dominant_current_negative")
        currents = [abs(canonical[k]) for k in self.mesh_vars + self.branch_vars]
        if max(currents) > 0 and min(currents) < 0.02 * max(currents):
            tags.append("near_cancellation")
        k = v.get("k", v.get("g_mS"))
        if k is not None and abs(k) > 2:
            tags.append("dependent_dominates")
        return tags

    # ---------------- the contract-aware prompt ----------------
    def prompt(self, v: Mapping[str, float], contract: ConventionContract) -> str:
        mesh_dir = ("CLOCKWISE" if contract.mesh_dir == "cw"
                    else "COUNTER-CLOCKWISE (i.e., the reverse of the usual clockwise choice)")
        ref = ("the bottom rail (the circuit's bottom wire) as the 0 V reference"
               if contract.ref_node == "bottom"
               else f"{self.top_ref_desc} as the 0 V reference — NOT the bottom rail")
        psc_name = ("passive (load) sign convention" if contract.psc == "passive"
                    else "ACTIVE (generator) sign convention")
        conv_lines = "\n".join(f"- {line}" for line in self.reference_lines(contract.psc))
        if contract.method == "mesh_kvl":
            method = ("Solve using MESH ANALYSIS (KVL loop equations) ONLY. Derive every "
                      "requested quantity from your mesh currents.")
        else:
            method = ("Solve using NODAL ANALYSIS (KCL node equations) ONLY. Derive every "
                      "requested quantity from your node voltages.")
        req = ", ".join(self.requested_vars())
        return f"""Analyze the {self.title} circuit.

**Components:**
{self.components_block(v)}

**Sign and reference conventions — follow EXACTLY:**
- Mesh currents ({', '.join(self.mesh_vars)}) are defined {mesh_dir}.
- Node voltages ({', '.join(self.node_vars)}) use {ref}.
{conv_lines}
- Branch-current and element-voltage references above follow the {psc_name}.

**Required method:** {method}

**Report these variables:** {req}

**Output format (mandatory):** the FINAL line of your response must be exactly one line of the form
ANSWER: {', '.join(f'{k}=<number>' for k in self.requested_vars())}
Every value must be a plain or scientific-notation number in SI base units (amperes for all currents, volts for all voltages). No unit symbols inside the ANSWER line."""


# ---------------- registry ----------------
TOPOLOGY_REGISTRY: Dict[str, Topology] = {}


def register(topo: Topology) -> Topology:
    assert topo.name and topo.name not in TOPOLOGY_REGISTRY, topo.name
    TOPOLOGY_REGISTRY[topo.name] = topo
    return topo


def get_topology(name: str) -> Topology:
    try:
        return TOPOLOGY_REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown topology {name!r}; known: {sorted(TOPOLOGY_REGISTRY)}") from None
