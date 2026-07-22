"""Procedural generator for the RHR domain (mirror of contour/generate).

N = n_physics x {dflt, lh, rxn} x 2 methods. Every accepted physics passes the four-way
cross-product oracle + exact transfer/orthogonality theorem checks at generation time.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from fractions import Fraction
from typing import Dict, List

import numpy as np

from ..schema import Instance
from ..topologies.base import InconsistentPhysics
from .contract import CELLS, DEFAULT, METHOD_CODE, RhrContract, apply, diagnostic_vars
from .families import FAMILIES

MAX_ATTEMPTS_PER_SLOT = 800

SYSTEM_PROMPT_RHR = (
    "You are a careful classical-mechanics and electromagnetism assistant. Solve vector "
    "problems exactly as specified: follow the stated cross-product handedness, sign, and "
    "reporting conventions and the required method, and end with the mandatory ANSWER line "
    "in the requested format."
)


def physics_hash(family: str, values: Dict[str, float]) -> str:
    payload = family + "|" + json.dumps({k: round(float(v), 12) for k, v in sorted(values.items())})
    return hashlib.sha256(payload.encode()).hexdigest()


def _git_sha(cwd: str) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def regime_tags(canonical: Dict[str, Fraction], fam) -> List[str]:
    tags: List[str] = []
    diag = [v for k, v in canonical.items() if fam.roles()[k]]
    if diag and sum(1 for v in diag if v < 0) >= len(diag) / 2:
        tags.append("mostly_negative")
    mags = [abs(v) for v in diag if v != 0]
    if mags and min(mags) < Fraction(1, 20) * max(mags):
        tags.append("near_cancellation")
    return tags


def build_prompt(fam, values: Dict[str, float], contract: RhrContract) -> str:
    hand = ("the RIGHT-HAND rule (x-hat x y-hat = +z-hat, the standard convention)"
            if contract.handedness == "rh"
            else "the LEFT-HAND rule — x-hat x y-hat = MINUS z-hat, the REVERSE of the "
                 "usual right-hand convention. Apply it to EVERY cross product you evaluate")
    req = ", ".join(fam.requested)
    return f"""Analyze the following three-dimensional vector mechanics problem.

**Given (all components in a fixed Cartesian basis):**
{fam.components_block(values)}

**Sign and orientation conventions — follow EXACTLY:**
- Every cross product in this problem follows {hand}.
- {fam.task_block(contract)}

**Report these variables:** {req}

**Output format (mandatory):** the FINAL line of your response must be exactly one line of the form
ANSWER: {", ".join(f"{k}=<number>" for k in fam.requested)}
Every value must be a plain or scientific-notation number given to at least 4 significant figures. No fractions, symbols, or units inside the ANSWER line."""


def generate_rhr(cfg: dict, seed: int, out_dir: str, repo_root: str) -> dict:
    n_physics = int(cfg["n_physics"])
    cells = {k: v for k, v in CELLS.items() if k in cfg.get("cells", list(CELLS))}
    trap_target = float(cfg.get("target_trap_fraction", 0.5))
    fam_names = [f["name"] for f in cfg["families"] for _ in range(int(f.get("weight", 1)))]
    params = cfg.get("parameters", {})
    rej = cfg.get("reject", {})
    min_diag = Fraction(str(rej.get("min_diag_mag", 1)))
    max_mag = Fraction(str(rej.get("max_mag", 3000)))

    seen: set = set()
    canary = str(uuid.uuid5(uuid.NAMESPACE_URL, f"circuchain-v3rhr-canary-{seed}"))
    slots = [fam_names[i % len(fam_names)] for i in range(n_physics)]

    instances: List[Instance] = []
    counts = {"trap": 0, "control": 0}
    rejects = {"inconsistent": 0, "dupe": 0, "quota": 0, "magnitude": 0}

    for slot, fname in enumerate(slots):
        fam = FAMILIES[fname]
        placed = False
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            fam_key = int(hashlib.sha256(fname.encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng([seed, fam_key, slot, attempt])
            values = fam.sample(rng, params)
            h = physics_hash(fname, values)
            if h in seen:
                rejects["dupe"] += 1
                continue
            try:
                fast = fam.solve(values, full_gate=False)
            except InconsistentPhysics:
                rejects["inconsistent"] += 1
                continue
            roles = fam.roles()
            diag_vals = [v for k, v in fast.items() if roles[k]]
            if (any(abs(v) < min_diag for v in diag_vals)
                    or any(abs(v) > max_mag for v in fast.values())):
                rejects["magnitude"] += 1
                continue
            tags = regime_tags(fast, fam)
            regime = "trap" if tags else "control"
            want_trap = counts["trap"] < trap_target * (counts["trap"] + counts["control"] + 1)
            if (regime == "trap") != want_trap and attempt < MAX_ATTEMPTS_PER_SLOT // 2:
                rejects["quota"] += 1
                continue
            try:
                gated = fam.solve(values, full_gate=True)
            except InconsistentPhysics:
                rejects["inconsistent"] += 1
                continue
            assert gated == fast

            seen.add(h)
            counts[regime] += 1
            physics_id = f"{fname}-{slot:04d}"
            canonical = {k: float(v) for k, v in gated.items()}

            for cell_code, cell in cells.items():
                exp = apply(cell, canonical, roles)
                dflt = apply(DEFAULT, canonical, roles)
                diag = diagnostic_vars(cell, canonical, roles)
                for m in fam.methods:
                    c = RhrContract(cell.handedness, cell.pair,
                                    METHOD_CODE.get(m, m.lower()))
                    instances.append(Instance(
                        id=f"{physics_id}-{cell_code}-{m.lower()}",
                        physics_id=physics_id,
                        topology=fname,
                        regime=regime,
                        regime_tags=tags,
                        values=dict(values),
                        contract={"handedness": c.handedness, "pair": c.pair,
                                  "method": c.method},
                        roles=dict(roles),
                        top_ref_key=None,
                        canonical=dict(canonical),
                        expected_under_contract={k: exp[k] for k in fam.requested},
                        expected_under_default={k: dflt[k] for k in fam.requested},
                        diagnostic_vars={k: diag[k] for k in fam.requested},
                        prompt=build_prompt(fam, values, c),
                        seed=seed,
                        instance_hash=hashlib.sha256((h + cell_code + m).encode()).hexdigest(),
                    ))
            placed = True
            break
        if not placed:
            raise RuntimeError(f"could not fill slot {slot} ({fname})")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "instances.jsonl"), "w") as f:
        for inst in instances:
            row = asdict(inst)
            row["canary"] = canary
            f.write(json.dumps(row) + "\n")

    manifest = {
        "domain": "rhr",
        "seed": seed,
        "canary_guid": canary,
        "git_sha": _git_sha(repo_root),
        "n_physics": n_physics,
        "n_instances": len(instances),
        "cells": list(cells.keys()),
        "methods": sorted({m for f in FAMILIES.values() for m in f.methods}),
        "regime_counts": counts,
        "rejects": rejects,
        "topologies": sorted(set(slots)),
        "system_prompt": SYSTEM_PROMPT_RHR,
        "config": cfg,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest
