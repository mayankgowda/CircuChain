"""LaTeX macros for the ICLR draft, generated from paper_stats.json. No hand-typed numbers."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
S = json.load(open(os.path.join(V2, "results", "paper_v3", "paper_stats.json")))
OUT = os.path.join(V2, "paper", "iclr", "generated")
os.makedirs(OUT, exist_ok=True)

L = []
def M(name, val):
    L.append(f"\\newcommand{{\\{name}}}{{{val}}}")

def pct(x, d=1):
    return f"{x*100:.{d}f}"

E = S["entrenchment"]
M("ccwRate", pct(E["ccw"]["rate"])); M("ccwN", E["ccw"]["n"])
M("cwRate", pct(E["cw"]["rate"])); M("cwN", E["cw"]["n"])
M("lhRate", pct(E["lh"]["rate"])); M("lhN", E["lh"]["n"])
M("wrkRate", pct(E["wrk"]["rate"])); M("actRate", pct(E["act"]["rate"]))
M("topRate", pct(E["top"]["rate"])); M("inwRate", pct(E["inw"]["rate"]))
M("rxnRate", pct(E["rxn"]["rate"]))
M("tierZ", f"{S['trend_tier']['z']:.1f}")
M("strainZ", f"{S['trend_strain']['z']:.1f}")

for m, tag in (("gpt5-api", "GptFive"), ("gpt-oss-120b-api", "GptOss"),
               ("gemma4-31b-api", "Gemma")):
    ce, ch = S["contour_easy"][m], S["contour_hard"][m]
    M(f"strainE{tag}", pct(1 - ce["mag"]["rate"], 0))
    M(f"strainH{tag}", pct(1 - ch["mag"]["rate"], 0))
    M(f"cwE{tag}", pct(ce["cw"]["rate"])); M(f"cwH{tag}", pct(ch["cw"]["rate"]))
    M(f"wrkH{tag}", pct(ch["wrk"]["rate"]))
    iv = S["intervention"][m]
    M(f"shotZero{tag}", pct(iv["shot0"]["rate"]))
    M(f"shotOne{tag}", pct(iv["shot1"]["rate"]))
    M(f"shotThree{tag}", pct(iv["shot3"]["rate"]))
    rx = S["rhr_xhard"][m]
    M(f"lh{tag}", pct(rx["lh"]["rate"])); M(f"lhN{tag}", rx["lh"]["n"])
    M(f"rxn{tag}", pct(rx["rxn"]["rate"]))
    M(f"circCcw{tag}", pct(S["circuits"][m]["ccw"]["rate"]))
    M(f"circMag{tag}", pct(S["circuits"][m]["mag"]["rate"], 0))

inc = S["incoherence"]
M("totalDiagVars", f"{inc['total_diag_vars']:,}")
M("incoherentN", inc["incoherent"])
M("coherencePct", pct(1 - inc["incoherent"] / inc["total_diag_vars"], 2))

# C1 table rows (contour, 5 rungs)
rows = []
for s in ("1.7b", "4b", "8b", "14b", "32b"):
    nt = S["contour_easy"][f"qwen3-{s}-nothink"]
    th = S["contour_easy"][f"qwen3-{s}-think"]
    rows.append(f"{s} & {pct(nt['mag']['rate'],0)} & {pct(nt['cw']['rate'])} & "
                f"{pct(th['mag']['rate'],0)} & {pct(th['cw']['rate'])} \\\\")
open(os.path.join(OUT, "table_c1.tex"), "w").write("\n".join(rows) + "\n")

# entrenchment table
T = S["entrenchment_tiers"]
names = {"ccw": "mesh direction (circuits)", "act": "passive sign (circuits)",
         "top": "reference node (circuits)", "cw": "orientation (contour)",
         "wrk": "work sign (contour)", "inw": "flux normal (contour)",
         "lh": "handedness (vectors)", "rxn": "reaction pair (vectors)"}
rows = []
for c in sorted(E, key=lambda c: (-T[c], -(E[c]["rate"] or 0))):
    e = E[c]
    lo, hi = e["wilson"]
    rows.append(f"{names[c]} & {T[c]} & {pct(e['rate'])} & "
                f"[{pct(lo)}, {pct(hi)}] & {e['n']:,} \\\\")
open(os.path.join(OUT, "table_entrench.tex"), "w").write("\n".join(rows) + "\n")

open(os.path.join(OUT, "macros.tex"), "w").write("\n".join(L) + "\n")
print(f"{len(L)} macros + 2 tables -> {OUT}")

# full tabular files (input-inside-tabular breaks latex; emit complete environments)
head_e = ("\\begin{tabular}{lcccc}\n\\toprule\nConvention (domain) & Tier & "
          "Reversion \\% & 95\\% CI & $n$ vars \\\\\n\\midrule\n")
body_e = open(os.path.join(OUT, "table_entrench.tex")).read()
open(os.path.join(OUT, "table_entrench_full.tex"), "w").write(
    head_e + body_e + "\\bottomrule\n\\end{tabular}\n")
head_c = ("\\begin{tabular}{lcccc}\n\\toprule\n& \\multicolumn{2}{c}{no-think} & "
          "\\multicolumn{2}{c}{think} \\\\\nScale & Comp.\\,\\% & Rev.\\,\\% & "
          "Comp.\\,\\% & Rev.\\,\\% \\\\\n\\midrule\n")
body_c = open(os.path.join(OUT, "table_c1.tex")).read()
open(os.path.join(OUT, "table_c1_full.tex"), "w").write(
    head_c + body_c + "\\bottomrule\n\\end{tabular}\n")
print("full tabular files emitted")
