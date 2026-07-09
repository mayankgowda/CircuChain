"""T1 — Convention contracts and their deterministic sign/offset transforms.

This is the scientific centerpiece of v2 and the reason the compliance grader can be
deterministic (no LLM judge). A ConventionContract is a set of orthogonal convention
dimensions. Each dimension maps to a PURE, closed-form transform on the canonical
(contract-neutral) signed answer produced by the analytic solver:

    expected_answer_under(contract) = apply(contract, canonical_answer, roles)

Because we can compute BOTH the answer a compliant solver must produce under the stated
contract AND the answer the "textbook prior" (DEFAULT contract) would produce, sign
compliance becomes a table lookup:

    - prediction matches the contract-correct sign      -> COMPLIANT
    - prediction matches the *default-prior* sign but the
      contract demanded the opposite                    -> CONVENTION_BLIND (prior override)

The gap between `expected_under(contract)` and `expected_under(DEFAULT)` on a given
variable is the *operational definition of Convention Blindness*. Only variables where
those two disagree in sign are diagnostic for a given factor.

Each output variable carries a ROLE that determines which factors act on it:
    mesh_current   : reversed by mesh_dir = ccw
    branch_current : reversed by psc = active
    node_voltage   : affinely shifted by ref_node = top  (V'(n) = V(n) - V(ref_top))
    element_voltage: reversed by psc = active
The `required_method` dimension carries no sign action; it is graded structurally.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

# Roles a variable can have. `apply()` uses `roles[var]` to decide which transforms hit it.
ROLE_MESH_CURRENT = "mesh_current"
ROLE_BRANCH_CURRENT = "branch_current"
ROLE_NODE_VOLTAGE = "node_voltage"
ROLE_ELEMENT_VOLTAGE = "element_voltage"

MESH_DIRS = ("cw", "ccw")
PSCS = ("passive", "active")
REF_NODES = ("bottom", "top")
METHODS = ("mesh_kvl", "nodal_kcl")


@dataclass(frozen=True)
class ConventionContract:
    """One point in the convention-contract design space.

    mesh_dir : "cw" | "ccw"          -- ccw negates every mesh_current
    psc      : "passive" | "active"  -- active negates branch_current and element_voltage
    ref_node : "bottom" | "top"      -- top ref subtracts V(top_ref_key) from all node_voltage
    method   : "mesh_kvl" | "nodal_kcl"  -- compliance dimension, no sign action
    """

    mesh_dir: str = "cw"
    psc: str = "passive"
    ref_node: str = "bottom"
    method: str = "mesh_kvl"

    def __post_init__(self) -> None:
        assert self.mesh_dir in MESH_DIRS, self.mesh_dir
        assert self.psc in PSCS, self.psc
        assert self.ref_node in REF_NODES, self.ref_node
        assert self.method in METHODS, self.method

    @property
    def cell_id(self) -> str:
        return f"{self.mesh_dir}|{self.psc}|{self.ref_node}|{self.method}"


# v1's implicit textbook prior: clockwise mesh, passive sign convention, bottom ground, mesh/KVL.
# This is the contract every v1 instance was authored under, so `verifier_map` == expected_under(DEFAULT).
DEFAULT = ConventionContract("cw", "passive", "bottom", "mesh_kvl")


def apply(
    contract: ConventionContract,
    canonical: Mapping[str, float],
    roles: Mapping[str, str],
    top_ref_key: str | None = None,
) -> Dict[str, float]:
    """Return the signed answer a COMPLIANT solver must produce under `contract`.

    `canonical` is the neutral signed answer from the analytic solver, expressed in the
    DEFAULT frame. `roles` maps each variable to one of the ROLE_* constants. `top_ref_key`
    names the node whose potential is subtracted when ref_node == "top" (required only then).
    """
    out: Dict[str, float] = dict(canonical)

    if contract.mesh_dir == "ccw":
        for k, r in roles.items():
            if r == ROLE_MESH_CURRENT and k in out:
                out[k] = -out[k]

    if contract.psc == "active":
        for k, r in roles.items():
            if r in (ROLE_BRANCH_CURRENT, ROLE_ELEMENT_VOLTAGE) and k in out:
                out[k] = -out[k]

    if contract.ref_node == "top":
        if top_ref_key is None or top_ref_key not in canonical:
            raise ValueError("ref_node='top' requires a valid top_ref_key present in canonical")
        vref = canonical[top_ref_key]
        for k, r in roles.items():
            if r == ROLE_NODE_VOLTAGE and k in out:
                out[k] = out[k] - vref

    return out


def diagnostic_vars(
    contract: ConventionContract,
    canonical: Mapping[str, float],
    roles: Mapping[str, str],
    top_ref_key: str | None = None,
    eps: float = 1e-9,
) -> Dict[str, bool]:
    """Which variables are sign-diagnostic under `contract` vs DEFAULT.

    A variable is diagnostic iff the contract-correct answer and the default-prior answer
    have *opposite sign* (so a prior-following model is measurably non-compliant on it).
    """
    exp = apply(contract, canonical, roles, top_ref_key)
    dflt = apply(DEFAULT, canonical, roles, top_ref_key)
    out = {}
    for k in canonical:
        a, b = exp.get(k, 0.0), dflt.get(k, 0.0)
        out[k] = (abs(a) > eps and abs(b) > eps and (a > 0) != (b > 0))
    return out
