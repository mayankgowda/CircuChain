"""v5 addenda: (a) unconditional four-outcome shares; (b) common-support paired
intervention analysis (same variable magnitude-correct in BOTH arms); (c) tolerance
sweep re-grading headline cells at 1/2/5/10% from raw responses; (d) dose-curve
artifact including GPT-5. Appends to paper_stats_v4.json (as *_v5 keys)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from circuchain.grade.extract import extract
from circuchain.grade.compliance import grade_variable

HERE=os.path.dirname(os.path.abspath(__file__)); V2=os.path.abspath(os.path.join(HERE,".."))
S=json.load(open(os.path.join(V2,"results","paper_v3","paper_stats_v4.json")))
def load_inst(ds): return {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(V2,ds,"instances.jsonl"))}
def rows(p):
    p=os.path.join(V2,p); return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
CIRC=load_inst("results/datasets/v2_seed20260709")
CON_H=load_inst("results/contour_hard/datasets/v3contourhard_seed20260721")
I1=load_inst("results/intervention/datasets/v2ctx1shot")
I3=load_inst("results/intervention/datasets/v2ctx3shot")
TRIO=["gpt5-api","gpt-oss-120b-api","gemma4-31b-api"]

# (a) unconditional outcome shares are already in v4 per cell (pass/revert/incoh/magwrong) — emit table macros later.

# (b) common-support: per (instance_id.physicsroot, var) magnitude-correct in both arms
def varmap(graded, inst, cell):
    out={}
    for r in rows(graded):
        if r["cell"]!=cell or r["instance_id"] not in inst: continue
        ins=inst[r["instance_id"]]
        for var,lab in r["var_labels"].items():
            if not ins["diagnostic_vars"].get(var): continue
            out[(r["instance_id"],var)]=lab
    return out
CS={}
for m in TRIO:
    base=varmap(f"results/graded/{m}.jsonl", CIRC, "ccw")
    for arm,ds,gd in (("shot1",I1,f"results/intervention/graded/{m}.jsonl"),
                      ("shot3",I3,f"results/intervention_3shot/graded/{m}.jsonl")):
        other=varmap(gd, ds, "ccw")
        keys=[k for k in base if k in other
              and base[k] in ("PASS","ERR_SIGN_CONVENTION","ERR_SIGN_INCOHERENT")
              and other[k] in ("PASS","ERR_SIGN_CONVENTION","ERR_SIGN_INCOHERENT")]
        rb=sum(base[k]=="ERR_SIGN_CONVENTION" for k in keys)
        ra=sum(other[k]=="ERR_SIGN_CONVENTION" for k in keys)
        b=sum(base[k]=="ERR_SIGN_CONVENTION" and other[k]=="PASS" for k in keys)   # fixed by demo
        c=sum(base[k]=="PASS" and other[k]=="ERR_SIGN_CONVENTION" for k in keys)   # broken by demo
        CS.setdefault(m,{})[arm]={"n_common":len(keys),
            "rate_base":rb/len(keys) if keys else None,"rate_arm":ra/len(keys) if keys else None,
            "fixed_by_demo":b,"broken_by_demo":c}
S["common_support_v5"]=CS

# (c) tolerance sweep on headline cells
def sweep(resp, inst, cell, tols=(0.01,0.02,0.05,0.10)):
    out={f"{t:.2f}":[0,0] for t in tols}   # revert, n_magcorrect
    seen=set()   # dedupe retry rows first-wins, matching grade_responses exactly
    for r in rows(resp):
        if r["instance_id"] in seen: continue
        seen.add(r["instance_id"])
        i=inst.get(r["instance_id"])
        if not i: continue
        if i["id"].rsplit("-",2)[-2]!=cell: continue
        wanted=tuple(i["expected_under_contract"].keys())
        pred,_=extract(r["text"], wanted)
        for var in wanted:
            if not i["diagnostic_vars"].get(var): continue
            for t in tols:
                lab=grade_variable(pred.get(var), i["expected_under_contract"][var],
                                   i["expected_under_default"][var], rel=t)
                if lab in ("PASS","ERR_SIGN_CONVENTION","ERR_SIGN_INCOHERENT"):
                    out[f"{t:.2f}"][1]+=1
                    if lab=="ERR_SIGN_CONVENTION": out[f"{t:.2f}"][0]+=1
    return {k:{"revert":v[0],"n":v[1],"rate":v[0]/v[1] if v[1] else None} for k,v in out.items()}
TS={}
for m in TRIO:
    TS[m]={"circuits_ccw":sweep(f"results/responses/{m}.jsonl", CIRC, "ccw"),
           "contour_hard_cw":sweep(f"results/contour_hard/responses/{m}.jsonl", CON_H, "cw")}
S["tolerance_sweep_v5"]=TS

# (d) dose curve artifact incl. GPT-5 (from v4 freeze numbers)
DC={m:{"shot0":S["circuits"][m]["ccw"]["rate"],
       "shot1":S["intervention"][m]["shot1"]["rate"],
       "shot3":S["intervention"][m]["shot3"]["rate"]} for m in TRIO}
S["dose_curve_v5"]=DC

json.dump(S, open(os.path.join(V2,"results","paper_v3","paper_stats_v4.json"),"w"), indent=2, default=float)
print("common-support:")
for m,d in CS.items():
    for arm,v in d.items():
        print(f"  {m} {arm}: n={v['n_common']} base {v['rate_base']*100:.1f}% -> arm {v['rate_arm']*100:.1f}%  fixed {v['fixed_by_demo']} broken {v['broken_by_demo']}")
print("tolerance sweep (rate% at 1/2/5/10):")
for m,d in TS.items():
    for cellname,sw in d.items():
        r=[f"{sw[k]['rate']*100:.1f}" if sw[k]['rate'] is not None else "-" for k in ("0.01","0.02","0.05","0.10")]
        print(f"  {m} {cellname}: {'/'.join(r)}")
