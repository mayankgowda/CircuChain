"""Positive-control compliance analysis (V2-2).

Measures, from the RAW final ANSWER lines of the control runs:
  ctlrev : did the model list the variables in the instructed REVERSED order?
  ctlsci : did the model write every value in scientific notation?
plus numeric magnitude-correctness via the standard extractor (values are unchanged
by both controls, so the default-frame expectations still apply).

Output: per-model compliance rates with Wilson CIs — the specificity comparison against
the ~20-30% ccw sign-compliance measured in the main panel.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, V2)

from circuchain.grade.extract import extract  # noqa: E402

DATASET = os.path.join(V2, "results", "datasets", "v2_control124", "instances.jsonl")
RESPONSES = os.path.join(V2, "results", "responses")
MODELS = ("gemma4-31b-ctl", "deepseek-v3-ctl")

_SCI = re.compile(r"^[-+]?\d(?:\.\d+)?e[-+]?\d+$", re.I)


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def answer_line(text: str) -> str:
    for line in reversed([l.strip() for l in text.splitlines() if l.strip()]):
        if line.upper().startswith("ANSWER"):
            return line
    return ""


def var_order(line: str, wanted) -> list:
    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
    wl = [w.lower() for w in wanted]
    return [p.lower() for p in pairs if p.lower() in wl]


def value_tokens(line: str) -> list:
    return [m.group(1).strip() for m in
            re.finditer(r"=\s*([^,\n]+?)(?=,|$)", line)]


def main() -> None:
    inst = {}
    with open(DATASET) as f:
        for l in f:
            r = json.loads(l)
            inst[r["id"]] = r

    print(f"{'model':<20}{'variant':<9}{'n':>4}{'instr-compliant':>17}{'mag-correct':>13}")
    print("-" * 65)
    summary = {}
    for model in MODELS:
        path = os.path.join(RESPONSES, f"{model}.jsonl")
        if not os.path.exists(path):
            print(f"{model:<20} (no responses yet)")
            continue
        rows = [json.loads(l) for l in open(path)]
        for variant in ("ctlrev", "ctlsci"):
            comp = mag = n = 0
            for r in rows:
                i = inst.get(r["instance_id"])
                if i is None or f"-{variant}-" not in r["instance_id"]:
                    continue
                n += 1
                wanted = list(i["expected_under_contract"].keys())
                line = answer_line(r["text"])
                if variant == "ctlrev":
                    ok = var_order(line, wanted) == [w.lower() for w in reversed(wanted)]
                else:
                    toks = value_tokens(line)
                    ok = bool(toks) and all(_SCI.match(t) for t in toks)
                comp += bool(ok)
                pred, _mode = extract(r["text"], tuple(wanted))
                exp = i["expected_under_default"]
                mags = [pred.get(k) is not None and
                        abs(abs(pred[k]) - abs(exp[k])) <= max(1e-9, 0.02 * abs(exp[k]))
                        for k in wanted]
                mag += all(mags)
            lo, hi = wilson(comp, n)
            print(f"{model:<20}{variant:<9}{n:>4}{comp:>7}/{n} ({comp/max(n,1)*100:5.1f}%)"
                  f"   {mag:>4}/{n}")
            summary[f"{model}|{variant}"] = {
                "n": n, "instruction_compliant": comp,
                "rate": comp / n if n else None,
                "wilson_lo": lo, "wilson_hi": hi,
                "magnitude_all_correct": mag,
            }
    out = os.path.join(V2, "results", "tables", "positive_control.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out}")
    print("\nSpecificity comparison: main-panel ccw sign-compliance for these models is ~20-30%")
    print("(gemma 12% final-correct under ccw flip vs 82% default). High control compliance")
    print("=> the failure is convention-SPECIFIC, not generic unusual-instruction decay.")


if __name__ == "__main__":
    main()
