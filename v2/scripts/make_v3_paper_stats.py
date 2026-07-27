"""Master analysis freeze for the ICLR paper. Reads ONLY graded artifacts; emits
results/paper_v3/paper_stats.json — every number the paper cites. Nothing hand-typed.

Adds the two synthesis analyses:
  * entrenchment mapping: 8 conventions x measured frontier low-strain reversion,
    coded on the ordinal reversal-pedagogy tier (0=taught as operation, 1=taught as
    error-contrast, 2=absent) from the documented textbook audit.
  * weighted logistic trends: (a) reversion vs design strain within trained-reversal
    frontier cells; (b) reversion vs entrenchment tier at low strain.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))


def load_inst(ds):
    return {json.loads(l)["id"]: json.loads(l)
            for l in open(os.path.join(V2, ds, "instances.jsonl"))}


def var_level(graded, inst, cell):
    """(revert, total, incoherent) on magnitude-correct diagnostic vars for one cell."""
    p = os.path.join(V2, graded)
    if not os.path.exists(p):
        return None
    c = r = i_ = 0
    for line in open(p):
        row = json.loads(line)
        if row["cell"] != cell or row["instance_id"] not in inst:
            continue
        ins = inst[row["instance_id"]]
        for var, lab in row["var_labels"].items():
            if not ins["diagnostic_vars"].get(var):
                continue
            if lab == "PASS":
                c += 1
            elif lab == "ERR_SIGN_CONVENTION":
                r += 1
            elif lab == "ERR_SIGN_INCOHERENT":
                i_ += 1
    t = c + r + i_
    return {"revert": r, "n": t, "incoherent": i_, "rate": r / t if t else None}


def mag_rate(graded, inst):
    p = os.path.join(V2, graded)
    if not os.path.exists(p):
        return None
    k = n = 0
    for line in open(p):
        row = json.loads(line)
        if row["cell"] != "dflt" or row["instance_id"] not in inst:
            continue
        n += 1
        k += bool(row["magnitude_correct"])
    return {"k": k, "n": n, "rate": k / n if n else None}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z / den * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0, c - h), min(1, c + h))


def wlogit(xs, ks, ns):
    """Weighted logistic regression k/n ~ x via IRLS; returns slope, z, p."""
    X = np.column_stack([np.ones(len(xs)), np.array(xs, float)])
    y = np.array(ks, float) / np.array(ns, float)
    w = np.array(ns, float)
    b = np.zeros(2)
    for _ in range(50):
        eta = X @ b
        mu = 1 / (1 + np.exp(-eta))
        W = w * mu * (1 - mu) + 1e-9
        z_ = eta + (y - mu) / (mu * (1 - mu) + 1e-9)
        b = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * z_))
    cov = np.linalg.inv(X.T @ ((w * mu * (1 - mu) + 1e-9)[:, None] * X))
    se = math.sqrt(cov[1, 1])
    zst = b[1] / se
    from scipy.stats import norm
    return {"slope": b[1], "z": zst, "p": float(2 * norm.sf(abs(zst)))}


S = {}

# ---------------- datasets ----------------
CIRC = load_inst("results/datasets/v2_seed20260709")
CON_E = load_inst("results/contour/datasets/v3contour_seed20260720")
CON_H = load_inst("results/contour_hard/datasets/v3contourhard_seed20260721")
RHR_X = load_inst("results/rhr/datasets/v3rhrxhard_seed20260722".replace("20260722", "20260724")) \
    if os.path.exists(os.path.join(V2, "results/rhr/datasets/v3rhrxhard_seed20260724/instances.jsonl")) \
    else load_inst("results/rhr/datasets/v3rhrxhard_seed20260724")
I1 = load_inst("results/intervention/datasets/v2ctx1shot")
I3 = load_inst("results/intervention/datasets/v2ctx3shot")

FRONTIER = ["gpt5-api", "gpt-oss-120b-api", "gemma4-31b-api"]
WEAK = ["deepseek-v3-api", "llama33-70b-api", "qwen25-72b-api"]
LADDER = [f"qwen3-{s}-{m}" for s in ("1.7b", "4b", "8b", "14b", "32b")
          for m in ("nothink", "think")]

# ---------------- circuits ----------------
S["circuits"] = {}
for m in FRONTIER + WEAK + ["qwen3-32b-think", "qwen3-32b-nothink"]:
    g = f"results/graded/{m}.jsonl"
    S["circuits"][m] = {"mag": mag_rate(g, CIRC),
                        "ccw": var_level(g, CIRC, "ccw"),
                        "act": var_level(g, CIRC, "act"),
                        "top": var_level(g, CIRC, "top")}

# ---------------- contour (both tiers) ----------------
S["contour_easy"] = {}
S["contour_hard"] = {}
for m in FRONTIER + WEAK + LADDER:
    ge = f"results/contour/graded/{m}.jsonl"
    S["contour_easy"][m] = {"mag": mag_rate(ge, CON_E),
                            "cw": var_level(ge, CON_E, "cw"),
                            "wrk": var_level(ge, CON_E, "wrk"),
                            "inw": var_level(ge, CON_E, "inw")}
for m in FRONTIER:
    gh = f"results/contour_hard/graded/{m}.jsonl"
    S["contour_hard"][m] = {"mag": mag_rate(gh, CON_H),
                            "cw": var_level(gh, CON_H, "cw"),
                            "wrk": var_level(gh, CON_H, "wrk")}

# ---------------- rhr (xhard, at scale) ----------------
S["rhr_xhard"] = {}
for m in FRONTIER:
    g = f"results/rhr_xhard/graded/{m}.jsonl"
    S["rhr_xhard"][m] = {"mag": mag_rate(g, RHR_X),
                         "lh": var_level(g, RHR_X, "lh"),
                         "rxn": var_level(g, RHR_X, "rxn")}

# ---------------- intervention dose curves ----------------
S["intervention"] = {}
for m in ("gemma4-31b-api", "gpt-oss-120b-api", "gpt5-api"):
    S["intervention"][m] = {
        "shot0": var_level(f"results/graded/{m}.jsonl", CIRC, "ccw"),
        "shot1": var_level(f"results/intervention/graded/{m}.jsonl", I1, "ccw"),
        "shot3": var_level(f"results/intervention_3shot/graded/{m}.jsonl", I3, "ccw"),
    }

# ---------------- entrenchment mapping (ordinal pedagogy tier) ----------------
# tier 2 = reversal ABSENT from pedagogy; 1 = taught as error-contrast; 0 = taught as
# standard operation. Coded from the documented textbook audit (paper Table + citations).
TIERS = {"ccw": 2, "act": 1, "top": 1, "cw": 0, "wrk": 0, "inw": 0, "lh": 1, "rxn": 0}
# frontier LOW-STRAIN reversion per convention (pooled over frontier models)
def pooled(entries):
    k = sum(e["revert"] for e in entries if e)
    n = sum(e["n"] for e in entries if e)
    return {"revert": k, "n": n, "rate": k / n if n else None,
            "wilson": wilson(k, n)}

S["entrenchment"] = {
    "ccw": pooled([S["circuits"][m]["ccw"] for m in FRONTIER]),
    "act": pooled([S["circuits"][m]["act"] for m in FRONTIER]),
    "top": pooled([S["circuits"][m]["top"] for m in FRONTIER]),
    "cw":  pooled([S["contour_easy"][m]["cw"] for m in FRONTIER]),
    "wrk": pooled([S["contour_easy"][m]["wrk"] for m in FRONTIER]),
    "inw": pooled([S["contour_easy"][m]["inw"] for m in FRONTIER]),
    "lh":  pooled([S["rhr_xhard"][m]["lh"] for m in FRONTIER]),
    "rxn": pooled([S["rhr_xhard"][m]["rxn"] for m in FRONTIER]),
}
S["entrenchment_tiers"] = TIERS

# trend: reversion ~ tier (weighted logistic over the 8 conventions)
xs = [TIERS[c] for c in S["entrenchment"]]
ks = [S["entrenchment"][c]["revert"] for c in S["entrenchment"]]
ns = [S["entrenchment"][c]["n"] for c in S["entrenchment"]]
S["trend_tier"] = wlogit(xs, ks, ns)

# trend: reversion ~ design strain within trained-reversal frontier cells (contour cw)
rows = []
for m in FRONTIER:
    e = S["contour_easy"][m]["cw"]; h = S["contour_hard"][m]["cw"]
    if e: rows.append((0, e["revert"], e["n"]))
    if h: rows.append((1, h["revert"], h["n"]))
S["trend_strain"] = wlogit([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows])

# ---------------- incoherence audit ----------------
inco = tot = 0
for block in ("circuits", "contour_easy", "contour_hard", "rhr_xhard"):
    for m, d in S[block].items():
        for k, v in d.items():
            if k != "mag" and v:
                inco += v["incoherent"]; tot += v["n"]
for m, d in S["intervention"].items():
    for k, v in d.items():
        if v:
            inco += v["incoherent"]; tot += v["n"]
S["incoherence"] = {"incoherent": inco, "total_diag_vars": tot}

out = os.path.join(V2, "results", "paper_v3")
os.makedirs(out, exist_ok=True)
json.dump(S, open(os.path.join(out, "paper_stats.json"), "w"), indent=2, default=float)
print(f"paper_stats.json frozen: {tot} diagnostic vars audited, {inco} incoherent")
print(f"trend tier: z={S['trend_tier']['z']:.2f} p={S['trend_tier']['p']:.2g}")
print(f"trend strain: z={S['trend_strain']['z']:.2f} p={S['trend_strain']['p']:.2g}")
