"""v4 freeze: fixes every CONFIRMED statistical finding from the external red-team.
- No double counting (intervention shot0 == circuits baseline counted ONCE).
- Directedness replaced by a NON-tautological statistic: among ALL errors on
  diagnostic variables (including magnitude-wrong ones), the share that equals the
  default-frame value exactly. Falsifiable: magnitude-wrong is the alternative.
- Inference is problem-clustered: per-model per-convention rates with bootstrap CIs
  clustering on physics_id (2000 resamples). No variable-level z statistics.
- Adds the McNemar b/c artifacts (401/6) to the freeze.
- Computes the actual competence span from artifacts (no unsupported 790x).
"""
import json, math, os, random
import numpy as np

HERE=os.path.dirname(os.path.abspath(__file__)); V2=os.path.abspath(os.path.join(HERE,".."))
random.seed(20260809); np.random.seed(20260809)

def load_inst(ds):
    return {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(V2,ds,"instances.jsonl"))}

def rows_of(graded):
    p=os.path.join(V2,graded)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

def cell_stats(graded, inst, cell):
    """Per-variable tallies + per-physics clusters for bootstrap."""
    clus={}
    for row in rows_of(graded):
        if row["cell"]!=cell or row["instance_id"] not in inst: continue
        ins=inst[row["instance_id"]]
        c=clus.setdefault(row["physics_id"], [0,0,0,0])  # pass, revert, incoh, val
        for var,lab in row["var_labels"].items():
            if not ins["diagnostic_vars"].get(var): continue
            if lab=="PASS": c[0]+=1
            elif lab=="ERR_SIGN_CONVENTION": c[1]+=1
            elif lab=="ERR_SIGN_INCOHERENT": c[2]+=1
            elif lab in ("ERR_VAL","ERR_MISSING"): c[3]+=1
    P=sum(v[0] for v in clus.values()); R=sum(v[1] for v in clus.values())
    I=sum(v[2] for v in clus.values()); V=sum(v[3] for v in clus.values())
    n=P+R+I
    out={"pass":P,"revert":R,"incoherent":I,"magwrong_or_missing":V,
         "n_magcorrect":n,"rate":R/n if n else None,
         "err_default_share": R/(R+I+V) if (R+I+V) else None}
    if clus and n:
        keys=list(clus.keys()); rates=[]
        for _ in range(2000):
            s=[clus[k] for k in (random.choice(keys) for _ in keys)]
            p_=sum(x[0] for x in s); r_=sum(x[1] for x in s); i_=sum(x[2] for x in s)
            t=p_+r_+i_
            if t: rates.append(r_/t)
        rates.sort()
        out["boot_ci"]=[rates[int(0.025*len(rates))], rates[int(0.975*len(rates))]]
    return out

def mag_rate(graded, inst):
    k=n=0
    for row in rows_of(graded):
        if row["cell"]!="dflt" or row["instance_id"] not in inst: continue
        n+=1; k+=bool(row["magnitude_correct"])
    return {"k":k,"n":n,"rate":k/n if n else None}

S={}
CIRC=load_inst("results/datasets/v2_seed20260709")
CON_E=load_inst("results/contour/datasets/v3contour_seed20260720")
CON_H=load_inst("results/contour_hard/datasets/v3contourhard_seed20260721")
RHR_X=load_inst("results/rhr/datasets/v3rhrxhard_seed20260724")
I1=load_inst("results/intervention/datasets/v2ctx1shot")
I3=load_inst("results/intervention/datasets/v2ctx3shot")
FRONTIER=["gpt5-api","gpt-oss-120b-api","gemma4-31b-api"]
WEAK=["deepseek-v3-api","llama33-70b-api","qwen25-72b-api"]
LADDER=[f"qwen3-{s}-{m}" for s in ("1.7b","4b","8b","14b","32b") for m in ("nothink","think")]

BLOCKS=[("circuits", "results/graded/{m}.jsonl", CIRC, ("ccw","act","top"), FRONTIER+WEAK+["qwen3-32b-think","qwen3-32b-nothink"]),
        ("contour_easy","results/contour/graded/{m}.jsonl", CON_E, ("cw","wrk","inw"), FRONTIER+WEAK+LADDER),
        ("contour_hard","results/contour_hard/graded/{m}.jsonl", CON_H, ("cw","wrk"), FRONTIER),
        ("rhr_xhard","results/rhr_xhard/graded/{m}.jsonl", RHR_X, ("lh","rxn"), FRONTIER+[f"qwen3-{s}-{m}" for s in ("1.7b","4b","8b") for m in ("nothink","think")])]
for name, tpl, inst, cells, models in BLOCKS:
    S[name]={}
    for m in models:
        d={"mag":mag_rate(tpl.format(m=m), inst)}
        for c in cells: d[c]=cell_stats(tpl.format(m=m), inst, c)
        S[name][m]=d

# intervention: shots 1 and 3 ONLY (shot0 == circuits baseline; never double count)
S["intervention"]={}
for m in ("gemma4-31b-api","gpt-oss-120b-api","gpt5-api"):
    S["intervention"][m]={"shot1":cell_stats(f"results/intervention/graded/{m}.jsonl", I1, "ccw"),
                          "shot3":cell_stats(f"results/intervention_3shot/graded/{m}.jsonl", I3, "ccw")}

# ---- study-wide tallies, no double counting ----
tot=inco=rev=val=0
for name,_,_,cells,_ in BLOCKS:
    for m,d in S[name].items():
        for c in cells:
            v=d[c]
            if not v["n_magcorrect"] and not v["magwrong_or_missing"]: continue
            tot+=v["n_magcorrect"]; inco+=v["incoherent"]; rev+=v["revert"]; val+=v["magwrong_or_missing"]
for m,d in S["intervention"].items():
    for k,v in d.items():
        tot+=v["n_magcorrect"]; inco+=v["incoherent"]; rev+=v["revert"]; val+=v["magwrong_or_missing"]
S["totals"]={"magcorrect_diag_vars":tot,"reverted":rev,"incoherent":inco,
             "magwrong_or_missing_diag":val,
             "err_default_share_study": rev/(rev+inco+val) if (rev+inco+val) else None,
             "note":"err_default_share is NON-tautological: magnitude-wrong errors are the alternative outcome"}

# ---- per-model tier summary (no pooled z; descriptive with clustered CIs) ----
CONV={"ccw":("circuits",2),"act":("circuits",1),"top":("circuits",1),
      "cw":("contour_easy",0),"wrk":("contour_easy",0),"inw":("contour_easy",0),
      "lh":("rhr_xhard",1),"rxn":("rhr_xhard",0)}
S["tier_table"]={}
for conv,(blk,tier) in CONV.items():
    S["tier_table"][conv]={"tier":tier,
        "per_model":{m:{"rate":S[blk][m][conv]["rate"],"ci":S[blk][m][conv].get("boot_ci"),
                        "n":S[blk][m][conv]["n_magcorrect"]} for m in FRONTIER}}
# separation stat: min over models of (ccw - max tier0 conv), clustered CIs already attached
seps=[]
for m in FRONTIER:
    t0=max(S["tier_table"][c]["per_model"][m]["rate"] or 0 for c,(b,t) in CONV.items() if t==0)
    seps.append((S["tier_table"]["ccw"]["per_model"][m]["rate"] or 0)-t0)
S["tier_separation_min_pp"]=min(seps)*100

# ---- mcnemar b/c for circuits ccw from analysis.json (the frozen v2 artifact) ----
A=json.load(open(os.path.join(V2,"results","tables","analysis.json")))
b=c=0
for k,v in A["factor_pairs"].items():
    if k.endswith("|ccw|final_correct"): b+=v["b"]; c+=v["c"]
S["mcnemar_ccw_aggregate"]={"b":b,"c":c}

# ---- actual competence span from artifacts ----
mags=[d["mag"]["rate"] for blk in ("circuits","contour_easy") for d in S[blk].values()
      if d["mag"] and d["mag"]["rate"]]
S["competence_span"]={"min":min(mags),"max":max(mags),
                      "ratio":max(mags)/min(mags) if min(mags)>0 else None}

out=os.path.join(V2,"results","paper_v3")
json.dump(S, open(os.path.join(out,"paper_stats_v4.json"),"w"), indent=2, default=float)
print(f"v4 freeze: {tot:,} magnitude-correct diag vars (no double count)")
print(f"errors on diag vars: revert {rev:,} / incoherent {inco} / magwrong {val:,}")
print(f"NON-tautological default-share among all diag errors: {S['totals']['err_default_share_study']*100:.1f}%")
print(f"tier separation (min over frontier models, ccw - best tier0): {S['tier_separation_min_pp']:.1f}pp")
print(f"mcnemar ccw aggregate: b={b} c={c}")
print(f"competence span: {S['competence_span']['ratio']:.0f}x ({min(mags)*100:.1f}% to {max(mags)*100:.1f}%)")
