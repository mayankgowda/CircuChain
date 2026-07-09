"""Shared data contracts for the v2 pipeline. Additive/backward-compatible with v1 instances.

A v1 instance is:
    {id, values, prompt, ground_truth:{mesh_currents, node_voltages, verifier_map}}
A v2 instance is a superset that adds a physics_id (unit of pairing), variable roles, the
convention contract it is posed under, and both the contract-correct and default-prior answers.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class Instance:
    id: str                                  # unique per (physics x contract x method)
    physics_id: str                          # SAME across contracts/methods -> the matched-pair key
    topology: str                            # supermesh | opposing_t | wheatstone | ladder | vcvs
    regime: str                              # "control" | "trap" (assigned by CODE, not by hand)
    regime_tags: List[str] = field(default_factory=list)
    values: Dict[str, float] = field(default_factory=dict)

    # convention contract this instance is posed under (T1)
    contract: Dict[str, str] = field(default_factory=dict)      # mesh_dir/psc/ref_node/method
    roles: Dict[str, str] = field(default_factory=dict)         # var -> ROLE_* (see contract.py)
    top_ref_key: Optional[str] = None

    # answers, all signed
    canonical: Dict[str, float] = field(default_factory=dict)         # neutral analytic answer
    expected_under_contract: Dict[str, float] = field(default_factory=dict)
    expected_under_default: Dict[str, float] = field(default_factory=dict)
    diagnostic_vars: Dict[str, bool] = field(default_factory=dict)    # which vars are sign-diagnostic

    prompt: str = ""
    seed: int = 0
    instance_hash: str = ""                  # contamination-guard dedupe key

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Completion:
    text: str                                # final answer body (think stripped)
    think: str = ""                          # reasoning trace, if any (feeds grade/trace.py)
    raw: str = ""
    usage: Dict = field(default_factory=dict)
    provenance: Dict = field(default_factory=dict)  # model_id, weight_sha, quant, backend, versions
    truncated: bool = False                  # hit max_tokens (a data point: constraint-drop under length)


@dataclass
class GradeRow:
    model: str
    instance_id: str
    physics_id: str
    method: str                              # KVL | KCL
    regime: str                              # control | trap
    contract_cell: str                       # ConventionContract.cell_id
    # deterministic outputs
    dichotomy: str                           # CORRECT | COMPLIANCE | COMPETENCE
    magnitude_correct: bool = False
    sign_compliant: bool = False
    var_labels: Dict[str, str] = field(default_factory=dict)
    # optional competence subcategory from the judge (COMPETENCE rows only)
    judge_category: Optional[str] = None
    # T6 trace locus
    trace_locus: Optional[str] = None

    def to_json(self) -> dict:
        return asdict(self)
