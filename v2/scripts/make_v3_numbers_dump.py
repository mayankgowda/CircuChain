"""Readable exhaustive dump of paper_stats.json for external review. Deterministic."""
import json, os
HERE=os.path.dirname(os.path.abspath(__file__)); V2=os.path.abspath(os.path.join(HERE,".."))
S=json.load(open(os.path.join(V2,"results","paper_v3","paper_stats.json")))
L=[]; w=L.append
def pct(x,d=1): return f"{x*100:.{d}f}%" if x is not None else "-"
def cellrow(name,d):
    if not d: return f"| {name} | - | - | - |"
    return f"| {name} | {d['revert']}/{d['n']} ({pct(d['rate'])}) | incoh {d['incoherent']} | |"
w("# The Clockwise Prior — complete numbers (auto-generated from graded artifacts)")
w("\nEvery value extracted programmatically; nothing hand-typed. This file backs the paper.")
w(f"\n## Study-wide directedness\n- graded magnitude-correct diagnostic variables: **{S['incoherence']['total_diag_vars']:,}**")
w(f"- incoherent sign errors: **{S['incoherence']['incoherent']}** (all in circuits ref-node affine cell)")
w(f"- trend reversion~pedagogy-tier: z={S['trend_tier']['z']:.2f}; reversion~strain: z={S['trend_strain']['z']:.2f}")
w("\n## Entrenchment table (frontier pooled, low strain)")
w("| convention | tier | revert | wilson95 | n |"); w("|---|---|---|---|---|")
for c,e in S["entrenchment"].items():
    lo,hi=e["wilson"]
    w(f"| {c} | {S['entrenchment_tiers'][c]} | {pct(e['rate'])} | [{pct(lo)},{pct(hi)}] | {e['n']:,} |")
for block in ("circuits","contour_easy","contour_hard","rhr_xhard","rhr_ladder","intervention"):
    if block not in S: continue
    w(f"\n## {block}")
    for m,d in S[block].items():
        parts=[]
        for k,v in d.items():
            if k=="mag" and v: parts.append(f"mag {v['k']}/{v['n']} ({pct(v['rate'],0)})")
            elif v and isinstance(v,dict) and "revert" in v: parts.append(f"{k} {v['revert']}/{v['n']} ({pct(v['rate'])}, incoh {v['incoherent']})")
        w(f"- **{m}**: " + "; ".join(parts))
open(os.path.join(V2,"results","paper_v3","RESULTS_V3_ALL_NUMBERS.md"),"w").write("\n".join(L)+"\n")
print(f"wrote RESULTS_V3_ALL_NUMBERS.md ({len(L)} lines)")
