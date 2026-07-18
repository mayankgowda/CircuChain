"""Positive-control dataset (V2-2): unusual-but-NON-convention instructions.

The reviewer objection this answers: "maybe the models don't specifically revert to
trained sign conventions — maybe they just ignore ANY unusual instruction." The control:
take the DEFAULT-cell instances (no convention flip anywhere) and add an unusual
*formatting* instruction matched for surprise, whose obedience is mechanically checkable
from the raw ANSWER line and whose numeric expectations are UNCHANGED:

  ctlrev : report the ANSWER-line variables in exactly REVERSED order
  ctlsci : write every numeric value in scientific notation

If models comply with these at a high rate while complying with the ccw convention at
~25%, the blindness is convention-specific — not generic weird-instruction decay.

Builds results/datasets/v2_control124 from the 31-physics pilot subset (dflt cells only,
both methods): 62 instances x 2 variants = 124. IDs: <physics>-ctlrev-<method> etc., so
the standard grader's cell parsing yields 'ctlrev'/'ctlsci' and numeric grading works
against this dataset dir unchanged.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(V2, "results", "datasets", "v2_pilot248", "instances.jsonl")
OUT_DIR = os.path.join(V2, "results", "datasets", "v2_control124")

ANSWER_MARKER = "**Output format (mandatory):**"


def reversed_order_prompt(prompt: str, req_vars: list) -> str:
    rev = list(reversed(req_vars))
    extra = ("**Unusual output requirement — follow EXACTLY:** in the ANSWER line, report the "
             f"variables in exactly this order: {', '.join(rev)} (the REVERSE of the order "
             "listed above).\n\n")
    out = prompt.replace(ANSWER_MARKER, extra + ANSWER_MARKER)
    # also rewrite the ANSWER template itself to the reversed order
    old_tpl = "ANSWER: " + ", ".join(f"{k}=<number>" for k in req_vars)
    new_tpl = "ANSWER: " + ", ".join(f"{k}=<number>" for k in rev)
    assert old_tpl in out, "ANSWER template not found"
    return out.replace(old_tpl, new_tpl)


def sci_notation_prompt(prompt: str) -> str:
    extra = ("**Unusual output requirement — follow EXACTLY:** in the ANSWER line, write EVERY "
             "numeric value in scientific notation with exactly three significant digits "
             "(e.g. -1.34e-3, 2.90e+1), even when the value is a round number.\n\n")
    assert ANSWER_MARKER in prompt
    return prompt.replace(ANSWER_MARKER, extra + ANSWER_MARKER)


def main() -> None:
    rows = [json.loads(l) for l in open(SRC)]
    dflt = [r for r in rows if r["id"].rsplit("-", 2)[-2] == "dflt"]
    assert len(dflt) == 62, f"expected 62 dflt instances, got {len(dflt)}"

    out = []
    for r in dflt:
        req = list(r["expected_under_contract"].keys())
        for variant, xform in (("ctlrev", lambda p: reversed_order_prompt(p, req)),
                               ("ctlsci", sci_notation_prompt)):
            n = dict(r)
            n["id"] = r["id"].replace("-dflt-", f"-{variant}-")
            n["prompt"] = xform(r["prompt"])
            out.append(n)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "instances.jsonl"), "w") as f:
        for n in out:
            f.write(json.dumps(n) + "\n")
    print(f"wrote {len(out)} control instances -> {OUT_DIR}")
    # show one modified block for eyeballing
    sample = next(n for n in out if "-ctlrev-" in n["id"])
    tail = sample["prompt"][sample["prompt"].index("**Unusual"):][:260]
    print("sample (ctlrev):", tail.replace("\n", " ")[:240])


if __name__ == "__main__":
    sys.exit(main())
