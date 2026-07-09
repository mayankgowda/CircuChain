"""Deterministic RULE-BASED compliance grader (T4) — the headline credibility engine.

No LLM is involved in deciding compliance. Given a prediction, the contract-correct answer,
and (optionally) the default-prior answer, sign-convention compliance is a table lookup.

Two operating modes:
  1. v1 RE-GRADE mode  (default == expected):  reduces to a signed-frame magnitude match.
     This is how we re-grade the 500 v1 log rows to produce the rule-vs-judge Cohen's kappa.
  2. v2 CONTRACT mode  (default != expected on diagnostic vars):  the CONVENTION_BLIND branch
     fires when the model produced the *prior* answer where the *contract* demanded the opposite.

Every subtask also emits the 2x2 JOINT flags (magnitude_correct x sign_compliant). This is the
mandatory answer to the #1 reviewer blocker ("compliance is conditioned on a competence gate"):
it lets analysis show the compliance gradient exists *within the magnitude-correct subset*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

REL_TOL = 0.05        # 5% relative tolerance, matches v1 grade_problem()
ABS_TOL = 1e-5        # absolute floor for near-zero true values
NEAR_ZERO = 1e-6      # deadzone below which a true value is treated as a genuine null


def _sign(x: float, dz: float = NEAR_ZERO) -> int:
    if x is None:
        return 0
    if abs(x) <= dz:
        return 0
    return 1 if x > 0 else -1


def _final_correct(pred: float, truth: float, rel: float = REL_TOL) -> bool:
    """Final value correct: right magnitude AND right sign."""
    if pred is None:
        return False
    diff = abs(pred - truth)
    if abs(truth) < NEAR_ZERO:
        return diff < ABS_TOL
    return (diff / abs(truth)) <= rel


def _magnitude_correct(pred: float, truth: float, rel: float = REL_TOL) -> bool:
    """|pred| matches |truth| within tolerance, ignoring sign (competence, sign-agnostic)."""
    if pred is None:
        return False
    if abs(truth) < NEAR_ZERO:
        return abs(abs(pred) - abs(truth)) < ABS_TOL
    return (abs(abs(pred) - abs(truth)) / abs(truth)) <= rel


# Per-variable labels
V_PASS = "PASS"                              # correct magnitude and sign
V_SIGN_CONVENTION = "ERR_SIGN_CONVENTION"    # right magnitude, sign follows the competing prior
V_SIGN_INCOHERENT = "ERR_SIGN_INCOHERENT"    # right magnitude, sign matches neither reference
V_VAL = "ERR_VAL"                            # wrong magnitude (competence)
V_MISSING = "ERR_MISSING"

# Subtask-level dichotomy
CORRECT = "CORRECT"
COMPLIANCE = "COMPLIANCE"     # a pure convention/sign failure (competence intact)
COMPETENCE = "COMPETENCE"     # a physics/arithmetic failure (defer subcategory to the judge)


@dataclass
class SubtaskGrade:
    label: str                                   # CORRECT | COMPLIANCE | COMPETENCE
    var_labels: Dict[str, str] = field(default_factory=dict)
    magnitude_correct: bool = False              # 2x2 axis: all required vars magnitude-correct
    sign_compliant: bool = False                 # 2x2 axis: all required vars sign-correct
    n_sign_convention: int = 0                   # pure convention (prior-override) var count
    n_val: int = 0                               # magnitude-wrong var count

    @property
    def joint_cell(self) -> str:
        """The 2x2 joint cell used for the grader-hardening analysis."""
        m = "mag+" if self.magnitude_correct else "mag-"
        s = "sign+" if self.sign_compliant else "sign-"
        return f"{m}/{s}"


def grade_variable(
    pred: Optional[float],
    expected: float,
    default: Optional[float] = None,
    rel: float = REL_TOL,
) -> str:
    """Deterministic per-variable label.

    `expected` = contract-correct signed value. `default` = default-prior signed value
    (pass None or == expected for v1 re-grade mode). The CONVENTION_BLIND branch fires only
    when the model matched the competing prior on a variable where the contract demanded a
    different sign.
    """
    if pred is None:
        return V_MISSING
    if _final_correct(pred, expected, rel):
        return V_PASS
    # Wrong final value. Is the magnitude right (i.e. a pure sign problem)?
    if _magnitude_correct(pred, expected, rel):
        if default is not None and _sign(default) != _sign(expected) and _final_correct(pred, default, rel):
            return V_SIGN_CONVENTION           # obeyed the training prior over the stated contract
        if _sign(pred) != _sign(expected):
            # In v1 re-grade mode (default is None/==expected) any sign flip vs the declared
            # frame IS a convention violation, since the declared frame is the only contract.
            if default is None or _sign(default) == _sign(expected):
                return V_SIGN_CONVENTION
            return V_SIGN_INCOHERENT
        return V_SIGN_INCOHERENT
    return V_VAL


def grade_subtask(
    pred_map: Mapping[str, Optional[float]],
    expected_map: Mapping[str, float],
    default_map: Optional[Mapping[str, float]] = None,
    rel: float = REL_TOL,
) -> SubtaskGrade:
    """Grade one (model, instance, method) subtask against the contract-correct answer.

    Subtask reduction rule (deterministic):
      - CORRECT     : every required variable is final-correct.
      - COMPLIANCE  : at least one pure sign/convention failure AND no magnitude-wrong variable
                      (competence intact; the only thing broken is convention adherence).
      - COMPETENCE  : any magnitude-wrong or missing variable (real physics/arithmetic failure);
                      the judge may later refine this into PHYSICS/CALC/HALLUC.
    """
    var_labels: Dict[str, str] = {}
    n_pass = n_sign = n_val = n_missing = 0
    all_mag_ok = True
    all_sign_ok = True

    for var, exp in expected_map.items():
        p = pred_map.get(var) if pred_map else None
        dfl = default_map.get(var) if default_map else None
        lab = grade_variable(p, exp, dfl, rel)
        var_labels[var] = lab

        if lab == V_PASS:
            n_pass += 1
        elif lab in (V_SIGN_CONVENTION, V_SIGN_INCOHERENT):
            n_sign += 1
        elif lab == V_MISSING:
            n_missing += 1
        else:
            n_val += 1

        # 2x2 joint axes (sign-agnostic magnitude, and sign correctness)
        if not (p is not None and _magnitude_correct(p, exp, rel)):
            all_mag_ok = False
        if not (p is not None and _sign(p) == _sign(exp)):
            all_sign_ok = False

    total = len(expected_map)
    if n_pass == total:
        label = CORRECT
    elif n_val == 0 and n_missing == 0 and n_sign > 0:
        label = COMPLIANCE
    else:
        label = COMPETENCE

    return SubtaskGrade(
        label=label,
        var_labels=var_labels,
        magnitude_correct=all_mag_ok,
        sign_compliant=all_sign_ok,
        n_sign_convention=n_sign,
        n_val=n_val,
    )


# ---- small stats helper reused by the re-grade + analysis stages ----
def cohen_kappa(pairs) -> float:
    """Cohen's kappa for a list of (a, b) categorical label pairs."""
    from collections import Counter

    n = len(pairs)
    if n == 0:
        return float("nan")
    cats = {c for p in pairs for c in p}
    obs = sum(1 for a, b in pairs if a == b) / n
    ma, mb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ma[c] / n) * (mb[c] / n) for c in cats)
    return 1.0 if pe == 1 else (obs - pe) / (1 - pe)
