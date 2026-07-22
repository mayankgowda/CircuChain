"""Convention contracts for the RHR domain.

    handedness : "rh" | "lh"        -- cross-product rule. DEFAULT rh (universal).
                 lh negates every ROLE with the CROSS flag (single-cross variables).
    pair       : "action" | "reaction" -- Newton's-third-law reporting convention.
                 DEFAULT action (forces/torques ON the body). reaction negates every
                 ROLE with the REACTIVE flag. Heavily trained -> the matched control.
    method     : "direct" | "transfer" -- required procedure, no sign action.

Per-variable roles are FLAG SETS, because the two conventions hit different, overlapping
variable subsets (the differentiated-mask design):
    torque vars   : {cross, reactive}   (flip under lh AND rxn)
    net-force vars: {reactive}          (flip under rxn only — no cross in their formula)
    ang-mom vars  : {cross}             (flip under lh only — no reaction partner)
    scalars       : {}                  (invariant anchors)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

FLAG_CROSS = "cross"
FLAG_REACTIVE = "reactive"

HANDEDNESS = ("rh", "lh")
PAIRS = ("action", "reaction")
METHODS = ("direct", "transfer", "det")   # det: determinant expansion (lorentz_set's 2nd procedure)


@dataclass(frozen=True)
class RhrContract:
    handedness: str = "rh"
    pair: str = "action"
    method: str = "direct"

    def __post_init__(self) -> None:
        assert self.handedness in HANDEDNESS, self.handedness
        assert self.pair in PAIRS, self.pair
        assert self.method in METHODS, self.method

    @property
    def cell_id(self) -> str:
        return f"{self.handedness}|{self.pair}|{self.method}"


DEFAULT = RhrContract()

CELLS = {
    "dflt": DEFAULT,
    "lh": RhrContract(handedness="lh"),
    "rxn": RhrContract(pair="reaction"),
}
METHOD_CODE = {"DIRECT": "direct", "TRANSFER": "transfer", "DET": "det"}


def apply(contract: RhrContract, canonical: Mapping[str, float],
          roles: Mapping[str, str]) -> Dict[str, float]:
    """roles[var] is a '+'-joined flag string, e.g. 'cross+reactive', 'cross', ''."""
    out: Dict[str, float] = dict(canonical)
    for k, flags in roles.items():
        if k not in out:
            continue
        f = set(flags.split("+")) if flags else set()
        neg = False
        if contract.handedness == "lh" and FLAG_CROSS in f:
            neg = not neg
        if contract.pair == "reaction" and FLAG_REACTIVE in f:
            neg = not neg
        if neg:
            out[k] = -out[k]
    return out


def diagnostic_vars(contract: RhrContract, canonical: Mapping[str, float],
                    roles: Mapping[str, str], eps: float = 1e-9) -> Dict[str, bool]:
    exp = apply(contract, canonical, roles)
    dflt = apply(DEFAULT, canonical, roles)
    return {k: (abs(exp[k]) > eps and abs(dflt[k]) > eps and (exp[k] > 0) != (dflt[k] > 0))
            for k in canonical}
