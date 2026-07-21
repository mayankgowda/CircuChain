"""Procedural generator for the contour domain (mirror of circuchain.generate).

N = n_physics x 4 cells x 2 methods. Every accepted physics passes the FOUR-WAY exact
oracle (sympy-param == sympy-green == pure-fraction == mpmath numeric) at generation
time, so `inconsistent = 0` holds by construction. Determinism: rng streams keyed
(master_seed, family_key, slot, attempt); same config + seed => byte-identical output.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from fractions import Fraction
from typing import Dict, List, Sequence

import numpy as np

from ..schema import Instance
from ..topologies.base import InconsistentPhysics
from .contract import (CELLS, DEFAULT, METHOD_CODE, ROLE_FLUX, ROLE_WORK,
                       ContourContract, apply, diagnostic_vars)
from .curves import flatten_values, poly_str, sample_verts
from .fieldpoly import Point, Poly2, polygon_edge_works, polygon_flux
from .solvers import solve_polygon

MAX_ATTEMPTS_PER_SLOT = 800

SYSTEM_PROMPT_CONTOUR = (
    "You are a careful multivariable-calculus assistant. Solve vector-field line-integral "
    "problems exactly as specified: follow the stated orientation, sign, and normal "
    "conventions and the required method, and end with the mandatory ANSWER line in the "
    "requested format."
)

_DEG1 = [(0, 0), (1, 0), (0, 1)]
_DEG2 = _DEG1 + [(2, 0), (1, 1), (0, 2)]
_DEG3 = _DEG2 + [(3, 0), (2, 1), (1, 2), (0, 3)]
_DEG4 = _DEG3 + [(4, 0), (3, 1), (2, 2), (1, 3), (0, 4)]
_MONOS = {1: _DEG1, 2: _DEG2, 3: _DEG3, 4: _DEG4}


def _sample_poly(rng, field_cfg: dict) -> Poly2:
    dd = field_cfg.get("degree_dist")            # e.g. {3: 0.5, 4: 0.5} — the hard tier
    if dd:
        r, acc, deg = rng.random(), 0.0, max(int(k) for k in dd)
        for k in sorted(dd, key=int):
            acc += float(dd[k])
            if r < acc:
                deg = int(k)
                break
        monos = _MONOS[deg]
    else:                                        # original path: byte-identical rng use
        monos = _DEG2 if rng.random() < float(field_cfg.get("degree2_prob", 0.7)) else _DEG1
    lo, hi = field_cfg.get("n_terms", [2, 4])
    n = int(rng.integers(int(lo), int(hi) + 1))
    picks = rng.choice(len(monos), size=min(n, len(monos)), replace=False)
    clo, chi = field_cfg.get("coeff_range", [-9, 9])
    out: Poly2 = {}
    for k in picks:
        c = 0
        while c == 0:
            c = int(rng.integers(int(clo), int(chi) + 1))
        out[monos[int(k)]] = Fraction(c)
    return out


def physics_hash(family: str, values: Dict[str, float]) -> str:
    payload = family + "|" + json.dumps({k: round(float(v), 12) for k, v in sorted(values.items())})
    return hashlib.sha256(payload.encode()).hexdigest()


def _git_sha(cwd: str) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def regime_tags(canonical: Dict[str, Fraction], n_edges: int) -> List[str]:
    """Code predicates for 'tricky sign structure' (the trap regime), like v2."""
    tags: List[str] = []
    edges = [canonical[f"e{i+1}"] for i in range(n_edges)]
    if canonical["wtot"] < 0:
        tags.append("negative_total")
    if (canonical["phi"] > 0) != (canonical["wtot"] > 0):
        tags.append("flux_circ_opposite")
    if abs(canonical["wtot"]) < Fraction(1, 5) * max(abs(e) for e in edges):
        tags.append("near_cancellation")
    return tags


def build_prompt(verts: Sequence[Point], p: Poly2, q: Poly2,
                 contract: ContourContract) -> str:
    k = len(verts)
    vlist = ", ".join(f"V{i+1}({int(x)}, {int(y)})" for i, (x, y) in enumerate(verts))
    elist = ", ".join(f"E{i+1} = V{i+1}V{i+2 if i+1 < k else 1}" for i in range(k))
    evars = ", ".join(f"e{i+1}" for i in range(k))

    orient = ("COUNTERCLOCKWISE (the standard positive orientation)"
              if contract.orientation == "ccw"
              else "CLOCKWISE — i.e., the REVERSE of the usual counterclockwise positive "
                   "orientation")
    if contract.work_sign == "by":
        work = ("Each edge value e_i is the line integral of F along edge E_i taken in the "
                "direction of positive traversal of C: the work done BY the field F. wtot "
                "is their sum (the circulation under the stated orientation).")
    else:
        work = ("Each edge value e_i is the work done AGAINST the field F along edge E_i in "
                "the direction of positive traversal of C (the work an external agent must "
                "supply — the NEGATIVE of the field's own work). wtot is their sum under "
                "the same against-the-field sign convention.")
    normal = ("phi is the outward flux of F across C (outward-pointing unit normal, the "
              "standard choice)."
              if contract.normal == "out"
              else "phi is the flux of F across C computed with the INWARD-pointing unit "
                   "normal — the REVERSE of the usual outward choice.")
    if contract.method == "param_direct":
        method = ("Compute each edge integral by DIRECT PARAMETRIZATION of that segment and "
                  "sum them for wtot; compute phi edge by edge from its boundary-integral "
                  "definition. Do not use Green's theorem except as an optional check.")
    else:
        method = ("Compute wtot and phi via GREEN'S THEOREM double integrals over the "
                  "enclosed region (curl form for circulation, divergence form for flux), "
                  "taking care to express the results under the stated conventions; obtain "
                  "the individual edge values by direct evaluation.")

    return f"""Analyze the vector field F on the closed polygonal curve C.

**Field and curve:**
F(x, y) = (P(x, y), Q(x, y)) with
P(x, y) = {poly_str(p)}
Q(x, y) = {poly_str(q)}
C is the closed polygon with vertices {vlist}, listed in order around the polygon, with edges {elist}.

**Sign and orientation conventions — follow EXACTLY:**
- Positive traversal of C is {orient}.
- {work}
- {normal}

**Required method:** {method}

**Report these variables:** {evars}, wtot, phi

**Output format (mandatory):** the FINAL line of your response must be exactly one line of the form
ANSWER: {", ".join(f"{v}=<number>" for v in [f"e{i+1}" for i in range(k)] + ["wtot", "phi"])}
Every value must be a plain or scientific-notation number given to at least 4 significant figures. No fractions, symbols, or units inside the ANSWER line."""


def generate_contour(cfg: dict, seed: int, out_dir: str, repo_root: str) -> dict:
    n_physics = int(cfg["n_physics"])
    methods = [str(m) for m in cfg.get("methods", ["PARAM", "GREEN"])]
    cells = {k: v for k, v in CELLS.items() if k in cfg.get("cells", list(CELLS))}
    trap_target = float(cfg.get("target_trap_fraction", 0.5))
    fam_names = [f["name"] for f in cfg["families"] for _ in range(int(f.get("weight", 1)))]
    field_cfg = cfg.get("field", {})
    rej = cfg.get("reject", {})
    min_edge = Fraction(str(rej.get("min_edge_mag", 0.25)))
    min_total = Fraction(str(rej.get("min_total_mag", 0.5)))
    max_mag = Fraction(str(rej.get("max_mag", 5000)))

    seen: set = set()
    canary = str(uuid.uuid5(uuid.NAMESPACE_URL, f"circuchain-v3contour-canary-{seed}"))
    slots: List[str] = [fam_names[i % len(fam_names)] for i in range(n_physics)]

    instances: List[Instance] = []
    counts = {"trap": 0, "control": 0}
    rejects = {"inconsistent": 0, "dupe": 0, "quota": 0, "magnitude": 0}

    for slot, family in enumerate(slots):
        placed = False
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            fam_key = int(hashlib.sha256(family.encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng([seed, fam_key, slot, attempt])
            verts = sample_verts(family, rng)
            p, q = _sample_poly(rng, field_cfg), _sample_poly(rng, field_cfg)
            values = flatten_values(verts, p, q)
            h = physics_hash(family, values)
            if h in seen:
                rejects["dupe"] += 1
                continue

            # cheap exact pre-checks via the Fraction engine (route 3) only
            works = polygon_edge_works(p, q, verts)
            wtot = sum(works, Fraction(0))
            phi = polygon_flux(p, q, verts)
            vals = works + [wtot, phi]
            if (any(abs(w) < min_edge for w in works) or abs(wtot) < min_total
                    or abs(phi) < min_total or any(abs(v) > max_mag for v in vals)):
                rejects["magnitude"] += 1
                continue

            canonical_frac = {f"e{i+1}": w for i, w in enumerate(works)}
            canonical_frac["wtot"] = wtot
            canonical_frac["phi"] = phi
            tags = regime_tags(canonical_frac, len(verts))
            regime = "trap" if tags else "control"
            want_trap = counts["trap"] < trap_target * (counts["trap"] + counts["control"] + 1)
            if (regime == "trap") != want_trap and attempt < MAX_ATTEMPTS_PER_SLOT // 2:
                rejects["quota"] += 1
                continue

            # full four-way oracle gate (sympy param + Green + numeric) on the accepted sample
            try:
                gated = solve_polygon(verts, p, q, full_gate=True)
            except InconsistentPhysics:
                rejects["inconsistent"] += 1
                continue
            assert gated == canonical_frac    # fast path must equal the gated result

            seen.add(h)
            counts[regime] += 1
            physics_id = f"{family}-{slot:04d}"
            canonical = {k: float(v) for k, v in canonical_frac.items()}
            roles = {k: (ROLE_FLUX if k == "phi" else ROLE_WORK) for k in canonical}
            requested = list(canonical.keys())

            for cell_code, cell in cells.items():
                exp = apply(cell, canonical, roles)
                dflt = apply(DEFAULT, canonical, roles)
                diag = diagnostic_vars(cell, canonical, roles)
                for m in methods:
                    c = ContourContract(cell.orientation, cell.work_sign, cell.normal,
                                        METHOD_CODE[m])
                    instances.append(Instance(
                        id=f"{physics_id}-{cell_code}-{m.lower()}",
                        physics_id=physics_id,
                        topology=family,
                        regime=regime,
                        regime_tags=tags,
                        values=dict(values),
                        contract={"orientation": c.orientation, "work_sign": c.work_sign,
                                  "normal": c.normal, "method": c.method},
                        roles=dict(roles),
                        top_ref_key=None,
                        canonical=dict(canonical),
                        expected_under_contract={k: exp[k] for k in requested},
                        expected_under_default={k: dflt[k] for k in requested},
                        diagnostic_vars={k: diag[k] for k in requested},
                        prompt=build_prompt(verts, p, q, c),
                        seed=seed,
                        instance_hash=hashlib.sha256((h + cell_code + m).encode()).hexdigest(),
                    ))
            placed = True
            break
        if not placed:
            raise RuntimeError(f"could not fill slot {slot} ({family}) after "
                               f"{MAX_ATTEMPTS_PER_SLOT} attempts — loosen the config")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "instances.jsonl"), "w") as f:
        for inst in instances:
            row = asdict(inst)
            row["canary"] = canary
            f.write(json.dumps(row) + "\n")

    manifest = {
        "domain": "contour",
        "seed": seed,
        "canary_guid": canary,
        "git_sha": _git_sha(repo_root),
        "n_physics": n_physics,
        "n_instances": len(instances),
        "cells": list(cells.keys()),
        "methods": methods,
        "regime_counts": counts,
        "rejects": rejects,
        "topologies": sorted(set(slots)),
        "system_prompt": SYSTEM_PROMPT_CONTOUR,
        "config": cfg,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest
