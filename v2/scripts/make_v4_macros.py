"""v4 macros from paper_stats_v4.json. Per-model tier table (no pooling), corrected scalars."""
import json, os
HERE=os.path.dirname(os.path.abspath(__file__)); V2=os.path.abspath(os.path.join(HERE,".."))
S=json.load(open(os.path.join(V2,"results","paper_v3","paper_stats_v4.json")))
OUT=os.path.join(V2,"paper","iclr","generated")
L=[]; M=lambda n,v: L.append(f"\\newcommand{{\\{n}}}{{{v}}}")
def pct(x,d=1): return f"{x*100:.{d}f}" if x is not None else "-"
F={"gpt5-api":"GptFive","gpt-oss-120b-api":"GptOss","gemma4-31b-api":"Gemma"}
T=S["tier_table"]
# scalars
M("totalDiagVarsV",f"{S['totals']['magcorrect_diag_vars']:,}")
M("revertedTotal",f"{S['totals']['reverted']:,}")
M("incoherentNV",S["totals"]["incoherent"])
M("bAgg",S["mcnemar_ccw_aggregate"]["b"]); M("cAgg",S["mcnemar_ccw_aggregate"]["c"])
M("tierSepMin",f"{S['tier_separation_min_pp']:.0f}")
M("spanRatio",f"{S['competence_span']['ratio']:.0f}")
M("spanLo",pct(S['competence_span']['min'])); M("spanHi",pct(S['competence_span']['max']))
for conv in ("ccw","cw","lh","rxn","act","top","wrk","inw"):
    for m,tag in F.items():
        pm=T[conv]["per_model"][m]
        M(f"{conv}{tag}",pct(pm["rate"]))
for m,tag in F.items():
    ce=S["contour_easy"][m]; ch=S["contour_hard"][m]
    M(f"vStrainE{tag}",pct(1-ce["mag"]["rate"],0)); M(f"vStrainH{tag}",pct(1-ch["mag"]["rate"],0))
    M(f"vCwE{tag}",pct(ce["cw"]["rate"])); M(f"vCwH{tag}",pct(ch["cw"]["rate"]))
    M(f"vWrkH{tag}",pct(ch["wrk"]["rate"]))
    iv=S["intervention"][m]
    M(f"vShotOne{tag}",pct(iv["shot1"]["rate"])); M(f"vShotThree{tag}",pct(iv["shot3"]["rate"]))
    M(f"vShotZero{tag}",pct(S["circuits"][m]["ccw"]["rate"]))
    M(f"vCircMag{tag}",pct(S["circuits"][m]["mag"]["rate"],1))
    M(f"vRhrMag{tag}",pct(S["rhr_xhard"][m]["mag"]["rate"],1))
RL=S["rhr_xhard"]
for tag,m in (("vLhThinkSmall","qwen3-1.7b-think"),("vLhThinkMid","qwen3-4b-think"),
              ("vLhThinkBig","qwen3-8b-think"),("vLhNothinkMid","qwen3-4b-nothink"),
              ("vRxnThinkBig","qwen3-8b-think"),("vRxnThinkSmall","qwen3-1.7b-think"),
              ("vRxnThinkMid","qwen3-4b-think")):
    cell="rxn" if "Rxn" in tag else "lh"
    M(tag,pct(RL[m][cell]["rate"]))
# per-model tier table (rows=conventions sorted tier desc then rate)
names={"ccw":"mesh direction (circuits)","act":"passive sign (circuits)","top":"reference node (circuits)",
       "cw":"orientation (contour)","wrk":"work sign (contour)","inw":"flux normal (contour)",
       "lh":"handedness (vectors)","rxn":"reaction pair (vectors)"}
rows=[]
order=sorted(T, key=lambda c:(-T[c]["tier"], -(max(T[c]["per_model"][m]["rate"] or 0 for m in F))))
for c in order:
    cells=[]
    for m in F:
        pm=T[c]["per_model"][m]
        ci=pm.get("ci")
        cells.append(f"{pct(pm['rate'])} [{pct(ci[0])},{pct(ci[1])}]" if ci else pct(pm["rate"]))
    rows.append(f"{names[c]} & {T[c]['tier']} & " + " & ".join(cells) + " \\\\")
head=("\\begin{tabular}{lcccc}\n\\toprule\n & & \\multicolumn{3}{c}{Reversion \\% [95\\% CI, clustered by problem]} \\\\\n"
      "Convention (domain) & Tier & GPT-5 & gpt-oss-120b & Gemma-4-31B \\\\\n\\midrule\n")
open(os.path.join(OUT,"table_entrench_v4.tex"),"w").write(head+"\n".join(rows)+"\n\\bottomrule\n\\end{tabular}\n")
open(os.path.join(OUT,"macros_v4.tex"),"w").write("\n".join(L)+"\n")
print(f"{len(L)} v4 macros + per-model tier table")

# ---- v5 additions: precise separation, appendix tables ----
L2=[]
M2=lambda n,v: L2.append(f"\\newcommand{{\\{n}}}{{{v}}}")
M2("tierSepMinPrec", f"{S['tier_separation_min_pp']:.1f}")
CS=S.get("common_support_v5",{})
if CS:
    ARMN={"shot1":"ShotOne","shot3":"ShotThree"}
    for m,tag in F.items():
        for arm in ("shot1","shot3"):
            v=CS[m][arm]
            M2(f"cs{ARMN[arm]}N{tag}", v["n_common"])
            M2(f"cs{ARMN[arm]}Base{tag}", pct(v["rate_base"]))
            M2(f"cs{ARMN[arm]}Arm{tag}", pct(v["rate_arm"]))
    rows=[]
    nm={"gpt5-api":"GPT-5","gpt-oss-120b-api":"gpt-oss-120b","gemma4-31b-api":"Gemma-4-31B"}
    for m in F:
        for arm,lbl in (("shot1","1 example"),("shot3","3 examples")):
            v=CS[m][arm]
            rows.append(f"{nm[m]} & {lbl} & {v['n_common']} & {pct(v['rate_base'])} & "
                        f"{pct(v['rate_arm'])} & {v['fixed_by_demo']} & {v['broken_by_demo']} \\\\")
    head=("\\begin{tabular}{llccccc}\n\\toprule\nModel & Arm & $n$ common & Base \\% & "
          "Arm \\% & Fixed & Broken \\\\\n\\midrule\n")
    open(os.path.join(OUT,"table_commonsupport.tex"),"w").write(head+"\n".join(rows)+"\n\\bottomrule\n\\end{tabular}\n")
TS=S.get("tolerance_sweep_v5",{})
if TS:
    rows=[]
    nm={"gpt5-api":"GPT-5","gpt-oss-120b-api":"gpt-oss-120b","gemma4-31b-api":"Gemma-4-31B"}
    for m in F:
        for cell,lbl in (("circuits_ccw","circuits ccw"),("contour_hard_cw","contour hard cw")):
            sw=TS[m][cell]
            vals=" & ".join(pct(sw[k]["rate"]) for k in ("0.01","0.02","0.05","0.10"))
            rows.append(f"{nm[m]} & {lbl} & {vals} \\\\")
    head=("\\begin{tabular}{llcccc}\n\\toprule\nModel & Cell & 1\\% & 2\\% & 5\\% & 10\\% \\\\\n\\midrule\n")
    open(os.path.join(OUT,"table_tolerance.tex"),"w").write(head+"\n".join(rows)+"\n\\bottomrule\n\\end{tabular}\n")
# unconditional outcome shares over ALL diagnostic variables (trio, 8 conventions)
CONV2={"ccw":"circuits","act":"circuits","top":"circuits","cw":"contour_easy",
       "wrk":"contour_easy","inw":"contour_easy","lh":"rhr_xhard","rxn":"rhr_xhard"}
rows=[]
nm={"gpt5-api":"GPT-5","gpt-oss-120b-api":"gpt-oss","gemma4-31b-api":"Gemma"}
for conv,blk in CONV2.items():
    for m in F:
        v=S[blk][m][conv]
        tot=v["n_magcorrect"]+v["magwrong_or_missing"]
        if not tot: continue
        rows.append(f"{conv} & {nm[m]} & {pct(v['pass']/tot)} & {pct(v['revert']/tot)} & "
                    f"{pct(v['incoherent']/tot)} & {pct(v['magwrong_or_missing']/tot)} & {tot:,} \\\\")
head=("\\begin{tabular}{llccccc}\n\\toprule\nConvention & Model & Compliant & Reverted & "
      "Incoherent & Mag.-wrong & $n$ all diag \\\\\n\\midrule\n")
open(os.path.join(OUT,"table_outcomes.tex"),"w").write(head+"\n".join(rows)+"\n\\bottomrule\n\\end{tabular}\n")
with open(os.path.join(OUT,"macros_v4.tex"),"a") as f:
    f.write("\n"+"\n".join(L2)+"\n")
print(f"v5: +{len(L2)} macros, 3 appendix tables")
