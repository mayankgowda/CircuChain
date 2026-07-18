"""Generate LaTeX macros + table bodies for the v2 paper from the frozen artifacts.

Reads: results/tables/analysis.json, positive_control.json, test_retest.json,
       transform_validation.json, graded rows (for the method split)
Writes: paper/generated/macros.tex, table_main.tex, table_c1.tex, table_invariance.tex

Every number in main.tex comes from here — rebuild with:
    .venv/bin/python v2/scripts/make_paper_macros.py
so the paper can never disagree with the frozen artifact.
"""
import glob
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
T = os.path.join(V2, "results", "tables")
OUT = os.path.join(V2, "paper", "generated")
os.makedirs(OUT, exist_ok=True)

a = json.load(open(os.path.join(T, "analysis.json")))
pc = json.load(open(os.path.join(T, "positive_control.json")))
tr = json.load(open(os.path.join(T, "test_retest.json")))
tv = json.load(open(os.path.join(T, "transform_validation.json")))

PRETTY = {
    "gemma4-31b-api": "Gemma-4-31B", "gpt-oss-120b-api": "GPT-OSS-120B",
    "deepseek-v3-api": "DeepSeek-V3", "gpt5-api": "GPT-5 (low)",
    "llama33-70b-api": "Llama-3.3-70B", "qwen25-72b-api": "Qwen2.5-72B",
    "qwen25-32b": "Qwen2.5-32B", "qwen25-7b-instruct": "Qwen2.5-7B",
    "qwen3-1.7b-think": "Qwen3-1.7B (think)", "qwen3-1.7b-nothink": "Qwen3-1.7B",
    "qwen3-4b-think": "Qwen3-4B (think)", "qwen3-4b-nothink": "Qwen3-4B",
    "qwen3-8b-think": "Qwen3-8B (think)", "qwen3-8b-nothink": "Qwen3-8B",
    "qwen3-14b-think": "Qwen3-14B (think)", "qwen3-14b-nothink": "Qwen3-14B",
    "qwen3-32b-think": "Qwen3-32B (think)", "qwen3-32b-nothink": "Qwen3-32B",
}
COMPETENT = ["gemma4-31b-api", "gpt-oss-120b-api", "deepseek-v3-api", "gpt5-api"]


def mag_of(m):
    n = corr = magw = 0
    for cell in ("dflt", "ccw", "act", "top"):
        s = a["cell_rates"].get(f"{m}|{cell}|all")
        if s:
            n += s["n"]; corr += s["dichotomy"]["CORRECT"]
            magw += s["magnitude_correct"]["rate"] * s["n"]
    return (magw / n if n else 0), corr, n


macros = []


def mac(name, val):
    macros.append(f"\\newcommand{{\\{name}}}{{{val}}}")


# ---- aggregate empty-c-cell ----
B = C = 0
for k, s in a["factor_pairs"].items():
    if k.endswith("|ccw|final_correct"):
        B += s["b"]; C += s["c"]
mac("AggB", B)
mac("AggC", C)
mac("AggRatio", f"{B/max(C,1):.0f}")

# ---- invariance band (var-level ccw, n>=20, no ctl columns) ----
band = []
for key, s in sorted(a["var_level_diagnostic"].items()):
    m, c = key.split("|")
    cb = s["convention_blind_given_mag"]
    if c == "ccw" and cb["n"] >= 20 and not m.endswith("-ctl"):
        band.append((m, cb["rate"], cb["wilson_lo"], cb["wilson_hi"], cb["n"]))
rates = [r for _, r, _, _, _ in band]
mac("BandMin", f"{min(rates)*100:.0f}")
mac("BandMax", f"{max(rates)*100:.0f}")
mac("BandMean", f"{sum(rates)/len(rates)*100:.1f}")
mac("BandN", len(band))
mags = [mag_of(m)[0] for m, *_ in band]
mac("CompetenceSpanX", f"{max(mags)/max(min(mags),1e-9):.0f}")

# ---- headline per-model rows (competent set) ----
rows_main = []
for m in COMPETENT:
    s = a["factor_pairs"][f"{m}|ccw|final_correct"]
    mag, corr, n = mag_of(m)
    orv = s["mcnemar"]["odds_ratio"]
    ors = "$\\infty$" if orv == float("inf") else f"{orv:.1f}"
    lo, hi = s["or_boot_ci"]
    rows_main.append(
        f"{PRETTY[m]} & {mag*100:.0f}\\% & {s['rate_default']['rate']:.2f} & "
        f"{s['rate_flipped']['rate']:.2f} & {s['b']} & {s['c']} & {ors} & "
        f"{s['or_haldane']:.0f} [{lo:.0f},\\,{hi:.0f}] & "
        f"{s['mcnemar']['p']:.1e} & {s['q_bh']:.1e} \\\\")
mac("GemmaOrH", f"{a['factor_pairs']['gemma4-31b-api|ccw|final_correct']['or_haldane']:.0f}")
mac("GemmaP", f"{a['factor_pairs']['gemma4-31b-api|ccw|final_correct']['mcnemar']['p']:.0e}")

# ---- C1 table ----
rows_c1 = []
for size in ("1.7b", "4b", "8b", "14b", "32b"):
    cells = []
    for mode in ("nothink", "think"):
        m = f"qwen3-{size}-{mode}"
        mag, _, _ = mag_of(m)
        cb = a["var_level_diagnostic"].get(f"{m}|ccw", {}).get("convention_blind_given_mag", {})
        cells.append((mag, cb))
    (magn, cbn), (magt, cbt) = cells
    rows_c1.append(
        f"{size} & {magn*100:.1f}\\% & {cbn.get('rate',0)*100:.0f}\\% ({cbn.get('n',0)}) & "
        f"{magt*100:.1f}\\% & {cbt.get('rate',0)*100:.0f}\\% ({cbt.get('n',0)}) \\\\")

# ---- invariance table (all 18 columns) ----
rows_inv = []
for m, r, lo, hi, n in sorted(band, key=lambda x: -x[1]):
    mag, _, _ = mag_of(m)
    rows_inv.append(f"{PRETTY.get(m,m)} & {mag*100:.1f}\\% & "
                    f"{r*100:.1f}\\% [{lo*100:.0f},\\,{hi*100:.0f}] & {n} \\\\")

# ---- positive controls ----
for key, name in (("gemma4-31b-ctl|ctlrev", "CtlGemmaRev"), ("gemma4-31b-ctl|ctlsci", "CtlGemmaSci"),
                  ("deepseek-v3-ctl|ctlrev", "CtlDsRev"), ("deepseek-v3-ctl|ctlsci", "CtlDsSci")):
    s = pc[key]
    mac(name, f"{s['rate']*100:.0f}")

# ---- test-retest ----
mac("RetestMean", f"{tr['conv_blind_ccw_mean']*100:.1f}")
mac("RetestSD", f"{tr['conv_blind_ccw_sd']*100:.1f}")
mac("RetestUnanimity", f"{tr['item_unanimity_rate']*100:.0f}")
mac("RetestK", tr["k"])

# ---- transform validation / dataset ----
mac("TvPass", f"{tv['n_pass']}/{tv['n_physics']}")
mac("NInstances", 1000)
mac("NPhysics", 125)
mac("NFamilies", 7)
mac("NColumns", len(band))

with open(os.path.join(OUT, "macros.tex"), "w") as f:
    f.write("% AUTO-GENERATED by scripts/make_paper_macros.py — do not edit\n")
    f.write("\n".join(macros) + "\n")
for fname, rows in (("table_main.tex", rows_main), ("table_c1.tex", rows_c1),
                    ("table_invariance.tex", rows_inv)):
    with open(os.path.join(OUT, fname), "w") as f:
        f.write("% AUTO-GENERATED — do not edit\n" + "\n".join(rows) + "\n")
print(f"wrote {len(macros)} macros + 3 table bodies -> {OUT}")
