"""Grading pipeline glue (build steps 11-12): responses JSONL -> graded JSONL + summary.

Per response: deterministic extraction (extract.py) -> compliance grading against the
contract-correct AND default-prior answers (compliance.py) -> GradeRow-shaped record.
No LLM anywhere on this path.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Dict, List

from .compliance import grade_subtask, CORRECT, COMPLIANCE, COMPETENCE
from .extract import extract


def grade_responses(dataset_dir: str, responses_dir: str, out_dir: str) -> dict:
    """Grade every responses/*.jsonl against the dataset. Returns the summary dict."""
    instances: Dict[str, dict] = {}
    with open(os.path.join(dataset_dir, "instances.jsonl")) as f:
        for line in f:
            row = json.loads(line)
            instances[row["id"]] = row

    os.makedirs(out_dir, exist_ok=True)
    summary_rows: List[dict] = []

    for fname in sorted(os.listdir(responses_dir)):
        if not fname.endswith(".jsonl") or fname.endswith(".failures.jsonl"):
            continue
        model = fname[:-6]
        graded_path = os.path.join(out_dir, fname)
        with open(os.path.join(responses_dir, fname)) as f_in, open(graded_path, "w") as f_out:
            for line in f_in:
                resp = json.loads(line)
                inst = instances.get(resp["instance_id"])
                if inst is None:
                    continue
                wanted = tuple(inst["expected_under_contract"].keys())
                pred, mode = extract(resp["text"], wanted)
                g = grade_subtask(pred, inst["expected_under_contract"],
                                  inst["expected_under_default"])
                row = {
                    "model": model,
                    "instance_id": inst["id"], "physics_id": inst["physics_id"],
                    "topology": inst["topology"], "regime": inst["regime"],
                    "contract": inst["contract"],
                    "cell": inst["id"].rsplit("-", 2)[-2],
                    "method": inst["contract"]["method"],
                    "dichotomy": g.label,
                    "magnitude_correct": g.magnitude_correct,
                    "sign_compliant": g.sign_compliant,
                    "joint_cell": g.joint_cell,
                    "var_labels": g.var_labels,
                    "n_sign_convention": g.n_sign_convention,
                    "extraction_mode": mode,
                    "truncated": resp.get("truncated", False),
                    "think_len": resp.get("think_len", 0),
                }
                summary_rows.append(row)
                f_out.write(json.dumps(row) + "\n")

    summary = _summarize(summary_rows)
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def _summarize(rows: List[dict]) -> dict:
    by_model_cell: dict = defaultdict(Counter)
    by_model: dict = defaultdict(Counter)
    for r in rows:
        by_model_cell[(r["model"], r["cell"])][r["dichotomy"]] += 1
        by_model[r["model"]][r["dichotomy"]] += 1
        by_model[r["model"]]["_n"] += 1
        if r["extraction_mode"] in ("fallback", "none"):
            by_model[r["model"]]["_extract_fallback_or_none"] += 1
        if r["truncated"]:
            by_model[r["model"]]["_truncated"] += 1
    return {
        "n_rows": len(rows),
        "per_model": {m: dict(c) for m, c in by_model.items()},
        "per_model_cell": {f"{m}|{c}": dict(v) for (m, c), v in by_model_cell.items()},
    }


def format_summary(summary: dict) -> str:
    lines = []
    lines.append(f"graded rows: {summary['n_rows']}")
    hdr = f"{'model':<14}{'cell':<6}{'N':>4}{'CORRECT':>9}{'COMPLIANCE':>11}{'COMPETENCE':>11}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for key in sorted(summary["per_model_cell"]):
        m, cell = key.split("|")
        c = summary["per_model_cell"][key]
        n = sum(v for k, v in c.items() if not k.startswith("_"))
        lines.append(f"{m:<14}{cell:<6}{n:>4}{c.get(CORRECT, 0):>9}"
                     f"{c.get(COMPLIANCE, 0):>11}{c.get(COMPETENCE, 0):>11}")
    for m, c in summary["per_model"].items():
        n = c.get("_n", 0)
        lines.append(f"\n{m}: n={n} correct={c.get(CORRECT, 0)} "
                     f"compliance={c.get(COMPLIANCE, 0)} competence={c.get(COMPETENCE, 0)} "
                     f"extract_issues={c.get('_extract_fallback_or_none', 0)} "
                     f"truncated={c.get('_truncated', 0)}")
    return "\n".join(lines)
