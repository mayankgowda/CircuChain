"""Procedural instance generator (T3/T8).

N = n_physics x |contract cells| x |methods| — scaling to 1-2k instances is a config knob,
not a redesign. Every accepted physics sample must pass (a) mesh==nodal cross-check inside
Topology.solve(), and (b) the exact-MNA netlist check inline here; the external ngspice pass
runs in `circuchain verify` before anything is used.

Contract design (paired_single_flip): the DEFAULT cell plus one single-factor flip per sign
factor — ccw, active, top — each posed under both methods. Every physics instance therefore
yields a clean within-physics matched pair for every factor (what McNemar needs), and the
DEFAULT cell doubles as the uninstructed-prior control.

Determinism: rng streams are keyed (master_seed, topology_index, slot, attempt); same config
+ same seed => byte-identical instances.jsonl.

Contamination guard: sha256 instance hashes, dedupe across the run, exclusion of any physics
whose (topology, values) hash collides with the 50 frozen v1 instances, and a per-release
canary GUID in the manifest + every record.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from typing import Dict, List, Mapping

import numpy as np

from .contract import DEFAULT, ConventionContract, apply, diagnostic_vars
from .schema import Instance
from .topologies import TOP_REF_KEY, InconsistentPhysics, get_topology
from .analytic import mna_solve_netlist, resolve_target, dual_check

MAX_ATTEMPTS_PER_SLOT = 800

CELLS = {
    "dflt": DEFAULT,
    "ccw": ConventionContract(mesh_dir="ccw"),
    "act": ConventionContract(psc="active"),
    "top": ConventionContract(ref_node="top"),
}
METHOD_CODE = {"KVL": "mesh_kvl", "KCL": "nodal_kcl"}


def physics_hash(topology: str, values: Mapping[str, float]) -> str:
    payload = topology + "|" + json.dumps({k: round(float(v), 12) for k, v in sorted(values.items())})
    return hashlib.sha256(payload.encode()).hexdigest()


def v1_exclusion_hashes(repo_root: str) -> set:
    """Hashes of the 50 frozen v1 instances (never regenerate a v1-colliding physics)."""
    topo_map = {"Prob1": "supermesh", "Prob2": "opposing_t", "Prob3": "wheatstone",
                "Prob4": "ladder", "Prob5": "vcvs"}
    path = os.path.join(repo_root, "data", "circuchain_full_dataset - final.json")
    out = set()
    if os.path.exists(path):
        for row in json.load(open(path)):
            topo = topo_map[row["id"].split("_")[0]]
            values = dict(row["values"])
            if topo == "supermesh":
                values.setdefault("k", 2.0)
            out.add(physics_hash(topo, values))
    return out


def _git_sha(cwd: str) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _mna_gate(topo, values, canonical) -> None:
    mna = mna_solve_netlist(topo.netlist(values))
    got = {var: resolve_target(mna, key) for var, key in topo.spice_targets().items()}
    errs = dual_check({v: canonical[v] for v in got}, got, rel_tol=1e-8, abs_floor=1e-12)
    if errs:
        raise InconsistentPhysics("MNA gate: " + "; ".join(errs))


def generate_dataset(cfg: dict, seed: int, out_dir: str, repo_root: str) -> dict:
    """Generate + inline-verify the dataset. Returns the manifest dict."""
    n_physics = int(cfg["n_physics"])
    methods = [str(m) for m in cfg.get("methods", ["KVL", "KCL"])]
    params = cfg["parameters"]
    trap_target = float(cfg.get("target_trap_fraction", 0.5))
    topo_names = [t["name"] for t in cfg["topologies"] for _ in range(int(t.get("weight", 1)))]

    exclude = v1_exclusion_hashes(repo_root)
    seen: set = set()
    canary = str(uuid.uuid5(uuid.NAMESPACE_URL, f"circuchain-v2-canary-{seed}"))

    # even split of physics slots across the (weight-expanded) topology list
    slots: List[str] = [topo_names[i % len(topo_names)] for i in range(n_physics)]

    instances: List[Instance] = []
    counts = {"trap": 0, "control": 0}
    rejects = {"inconsistent": 0, "dupe_or_v1": 0, "quota": 0}

    for slot, topo_name in enumerate(slots):
        topo = get_topology(topo_name)
        placed = False
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            topo_key = int(hashlib.sha256(topo_name.encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng([seed, topo_key, slot, attempt])
            values = topo.sample(rng, params)
            h = physics_hash(topo_name, values)
            if h in seen or h in exclude:
                rejects["dupe_or_v1"] += 1
                continue
            try:
                canonical = topo.solve(values)
                _mna_gate(topo, values, canonical)
            except (InconsistentPhysics, Exception):  # noqa: BLE001
                rejects["inconsistent"] += 1
                continue
            tags = topo.regime_tags(values, canonical)
            regime = "trap" if tags else "control"
            # rejection-sample toward the target trap fraction
            want_trap = counts["trap"] < trap_target * (counts["trap"] + counts["control"] + 1)
            if (regime == "trap") != want_trap and attempt < MAX_ATTEMPTS_PER_SLOT // 2:
                rejects["quota"] += 1
                continue
            seen.add(h)
            counts[regime] += 1
            physics_id = f"{topo_name}-{slot:04d}"
            roles = topo.roles()
            requested = topo.requested_vars()
            for cell_code, contract in CELLS.items():
                exp_full = apply(contract, canonical, roles, TOP_REF_KEY)
                dflt_full = apply(DEFAULT, canonical, roles, TOP_REF_KEY)
                diag = diagnostic_vars(contract, canonical, roles, TOP_REF_KEY)
                for m in methods:
                    c = ConventionContract(contract.mesh_dir, contract.psc,
                                           contract.ref_node, METHOD_CODE[m])
                    instances.append(Instance(
                        id=f"{physics_id}-{cell_code}-{m.lower()}",
                        physics_id=physics_id,
                        topology=topo_name,
                        regime=regime,
                        regime_tags=tags,
                        values=dict(values),
                        contract={"mesh_dir": c.mesh_dir, "psc": c.psc,
                                  "ref_node": c.ref_node, "method": c.method},
                        roles={k: roles[k] for k in requested},
                        top_ref_key=TOP_REF_KEY,
                        canonical=dict(canonical),
                        expected_under_contract={k: exp_full[k] for k in requested},
                        expected_under_default={k: dflt_full[k] for k in requested},
                        diagnostic_vars={k: diag[k] for k in requested},
                        prompt=topo.prompt(values, c),
                        seed=seed,
                        instance_hash=hashlib.sha256((h + cell_code + m).encode()).hexdigest(),
                    ))
            placed = True
            break
        if not placed:
            raise RuntimeError(f"could not fill slot {slot} ({topo_name}) after "
                               f"{MAX_ATTEMPTS_PER_SLOT} attempts — loosen the config")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "instances.jsonl"), "w") as f:
        for inst in instances:
            row = asdict(inst)
            row["canary"] = canary
            f.write(json.dumps(row) + "\n")

    manifest = {
        "seed": seed,
        "canary_guid": canary,
        "git_sha": _git_sha(repo_root),
        "n_physics": n_physics,
        "n_instances": len(instances),
        "cells": list(CELLS.keys()),
        "methods": methods,
        "regime_counts": counts,
        "rejects": rejects,
        "topologies": sorted(set(slots)),
        "config": cfg,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest
