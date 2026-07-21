"""Convention contracts for the contour domain (mirror of circuchain.contract).

Three orthogonal sign conventions, each with a near-unanimous textbook default, plus a
method dimension with no sign action:

    orientation : "ccw" | "cw"       -- positive traversal of the closed curve.
                  DEFAULT = ccw ("positively oriented" in every calculus text). This is
                  the polarity MIRROR of the circuits domain (whose default is cw mesh
                  currents): the flip cell here is `cw`.
                  cw negates every ROLE_WORK variable (each edge integral is taken along
                  the positive traversal direction, which reverses).
    work_sign   : "by" | "against"   -- work done BY the field (default) vs work done
                  AGAINST the field by an external agent. `against` negates every
                  ROLE_WORK variable. NOTE: cw and wrk demand the IDENTICAL output
                  transform (global negation of work values) — a matched-transform pair
                  that isolates pure convention entrenchment from transform difficulty,
                  an internal control the circuits domain does not have.
    normal      : "out" | "in"       -- flux normal. DEFAULT = outward. `in` negates
                  ROLE_FLUX. The flux is defined geometrically (outward from the enclosed
                  region), so it is NOT affected by the orientation convention.
    method      : "param_direct" | "green_thm" -- compliance dimension, no sign action
                  (the KVL/KCL analogue: proves the effect is a reporting-frame effect,
                  not a procedure effect).

The canonical frame == the textbook default frame == ContourContract() with all defaults.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

ROLE_WORK = "edge_work"      # per-edge work values and their total (wtot)
ROLE_FLUX = "flux"           # the flux value (phi)

ORIENTATIONS = ("ccw", "cw")
WORK_SIGNS = ("by", "against")
NORMALS = ("out", "in")
METHODS = ("param_direct", "green_thm")


@dataclass(frozen=True)
class ContourContract:
    orientation: str = "ccw"
    work_sign: str = "by"
    normal: str = "out"
    method: str = "param_direct"

    def __post_init__(self) -> None:
        assert self.orientation in ORIENTATIONS, self.orientation
        assert self.work_sign in WORK_SIGNS, self.work_sign
        assert self.normal in NORMALS, self.normal
        assert self.method in METHODS, self.method

    @property
    def cell_id(self) -> str:
        return f"{self.orientation}|{self.work_sign}|{self.normal}|{self.method}"


DEFAULT = ContourContract()

# dflt + one single-factor flip per sign convention (paired_single_flip, like v2)
CELLS = {
    "dflt": DEFAULT,
    "cw": ContourContract(orientation="cw"),
    "wrk": ContourContract(work_sign="against"),
    "inw": ContourContract(normal="in"),
}
METHOD_CODE = {"PARAM": "param_direct", "GREEN": "green_thm"}


def apply(contract: ContourContract, canonical: Mapping[str, float],
          roles: Mapping[str, str]) -> Dict[str, float]:
    """Signed answer a COMPLIANT solver must produce under `contract`.

    `canonical` is the neutral answer in the DEFAULT frame (ccw traversal, work-by-field,
    outward normal). All three convention transforms are pure sign flips; there is no
    affine dimension in this domain.
    """
    out: Dict[str, float] = dict(canonical)
    flip_work = (contract.orientation == "cw") != (contract.work_sign == "against")
    if flip_work:
        for k, r in roles.items():
            if r == ROLE_WORK and k in out:
                out[k] = -out[k]
    if contract.normal == "in":
        for k, r in roles.items():
            if r == ROLE_FLUX and k in out:
                out[k] = -out[k]
    return out


def diagnostic_vars(contract: ContourContract, canonical: Mapping[str, float],
                    roles: Mapping[str, str], eps: float = 1e-9) -> Dict[str, bool]:
    """A var is diagnostic iff contract-correct and default-prior signs are opposite."""
    exp = apply(contract, canonical, roles)
    dflt = apply(DEFAULT, canonical, roles)
    return {k: (abs(exp[k]) > eps and abs(dflt[k]) > eps and (exp[k] > 0) != (dflt[k] > 0))
            for k in canonical}
