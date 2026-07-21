"""Early-read report for the contour smoke test (dflt+cw subset).

Answers the one question the smoke exists to answer: when instructed CLOCKWISE-positive
in the math domain, do magnitude-correct models keep reporting in the COUNTERCLOCKWISE
textbook frame (reversion toward the domain prior — the polarity-mirror prediction), do
they comply, or do they fail incoherently?

Usage: .venv/bin/python v2/scripts/smoke_contour_report.py
"""
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
DS = os.path.join(V2, "results", "contour", "datasets", "smoke25")
GR = os.path.join(V2, "results", "contour", "graded")
RESP = os.path.join(V2, "results", "contour", "responses")

inst = {}
with open(os.path.join(DS, "instances.jsonl")) as f:
    for line in f:
        r = json.loads(line)
        inst[r["id"]] = r

for fname in sorted(os.listdir(GR)):
    if not fname.endswith(".jsonl") or fname.endswith(".failures.jsonl"):
        continue
    model = fname[:-6]
    rows = [json.loads(l) for l in open(os.path.join(GR, fname))]
    rows = [r for r in rows if r["instance_id"] in inst]
    if not rows:
        continue

    print(f"\n{'='*74}\n{model}  (n={len(rows)})")
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[r["cell"]].append(r)
    for cell in ("dflt", "cw"):
        c = Counter(r["dichotomy"] for r in by_cell[cell])
        mag = sum(r["magnitude_correct"] for r in by_cell[cell])
        n = len(by_cell[cell])
        print(f"  {cell:>4}: n={n:3d}  CORRECT={c['CORRECT']:3d}  COMPLIANCE={c['COMPLIANCE']:3d}  "
              f"COMPETENCE={c['COMPETENCE']:3d}  (mag-correct {mag}/{n})")

    # paired b/c on final_correct (the McNemar cells)
    idx = defaultdict(dict)
    for r in rows:
        idx[(r["physics_id"], r["method"])][r["cell"]] = r
    b = c_ = both_ok = both_bad = 0
    for cells in idx.values():
        if "dflt" not in cells or "cw" not in cells:
            continue
        d_ok = cells["dflt"]["dichotomy"] == "CORRECT"
        f_ok = cells["cw"]["dichotomy"] == "CORRECT"
        both_ok += d_ok and f_ok
        b += d_ok and not f_ok
        c_ += f_ok and not d_ok
        both_bad += (not d_ok) and (not f_ok)
    print(f"  paired (dflt vs cw): both_ok={both_ok} b={b} c={c_} both_bad={both_bad}"
          f"   [b>>c with empty c = reversion signature]")

    # variable-level: among magnitude-correct DIAGNOSTIC vars in the cw cell,
    # sign-correct (complied) vs matches-default (reverted to CCW prior) vs incoherent
    comply = revert = incoh = 0
    for r in by_cell["cw"]:
        ins = inst[r["instance_id"]]
        for var, lab in r["var_labels"].items():
            if not ins["diagnostic_vars"].get(var):
                continue
            if lab == "PASS":
                comply += 1
            elif lab == "ERR_SIGN_CONVENTION":
                revert += 1                      # matched the CCW default frame exactly
            elif lab == "ERR_SIGN_INCOHERENT":
                incoh += 1
    tot = comply + revert + incoh
    if tot:
        print(f"  cw diagnostic vars, magnitude-correct subset: n={tot}")
        print(f"    complied with instructed CW frame : {comply:4d}  ({comply/tot*100:5.1f}%)")
        print(f"    REVERTED to CCW textbook frame    : {revert:4d}  ({revert/tot*100:5.1f}%)"
              f"   <- the clockwise-prior mirror prediction")
        print(f"    incoherent (matched neither)      : {incoh:4d}  ({incoh/tot*100:5.1f}%)")

    # cost + truncation from the response files
    rp = os.path.join(RESP, f"{model}.jsonl")
    if os.path.exists(rp):
        rr = [json.loads(l) for l in open(rp) if json.loads(l)["instance_id"] in inst]
        cost = sum((r.get("usage") or {}).get("cost") or 0 for r in rr)
        trunc = sum(bool(r.get("truncated")) for r in rr)
        ctoks = sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in rr)
        print(f"  responses: truncated={trunc}/{len(rr)}  completion_toks~{ctoks//max(len(rr),1)}/row"
              f"  cost=${cost:.4f}" + ("  (Together: no cost field, tokens only)" if cost == 0 else ""))
