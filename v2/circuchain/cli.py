"""CircuChain v2 CLI.

Implemented (proven, runnable):
    circuchain regrade                 -- re-grade the v1 logs -> rule-vs-judge kappa (GNG-1)
    circuchain models --installed      -- cross-check configs/models.yaml against the backend
    circuchain generate                -- procedural generation + inline exact-MNA gate
    circuchain verify                  -- NGSPICE + exact-MNA dual-verification of a dataset
    circuchain run                     -- run the model panel (cached, resumable)
    circuchain grade                   -- deterministic extract + compliance grading

Stub (build step 13):
    circuchain analyze                 -- McNemar paired tests, tables + figures
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import typer

app = typer.Typer(add_completion=False, help="CircuChain v2 — Convention Blindness benchmark (M5-local).")

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(V2, ".."))


def _load_dotenv() -> None:
    """Load v2/.env (gitignored) into os.environ so API keys never touch config, CLI args,
    logs, or this chat. Real env vars win; only simple KEY=VALUE lines are parsed."""
    path = os.path.join(V2, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _v2path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(V2, p)


@app.command()
def regrade():
    """Re-grade the frozen v1 logs with the deterministic grader (CPU-only; the GNG-1 result)."""
    subprocess.run([sys.executable, os.path.join(V2, "scripts", "regrade_v1_logs.py")], check=True)


@app.command()
def models(
    installed: bool = typer.Option(False, "--installed", help="cross-check the panel config"),
    backend: str = typer.Option("lmstudio", help="lmstudio | ollama"),
    config: str = typer.Option("configs/models.yaml", help="panel config to cross-check"),
):
    """Enumerate downloaded models and report which causal contrasts the panel can support."""
    if backend == "lmstudio":
        from .providers.lmstudio import LMStudioProvider as P
        hint = "Start it with: lms server start   (and check `lms ls`)"
    else:
        from .providers.ollama import OllamaProvider as P
        hint = "Start it with: ollama serve"

    try:
        have = {m["name"]: m for m in P.list_installed()}
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Could not reach the {backend} server ({e}).\n{hint}")
        raise typer.Exit(1)

    typer.echo(f"Downloaded text models ({len(have)}) via {backend}:")
    for name, m in sorted(have.items()):
        bits = [str(m.get("arch") or ""), str(m.get("engine") or ""), str(m.get("quant") or "")]
        vision = " [vision]" if m.get("vision") else ""
        state = m.get("state") or ""
        typer.echo(f"  {name:<34} {' '.join(b for b in bits if b):<26} {state}{vision}")

    cfg_path = _v2path(config)
    if not (installed and os.path.exists(cfg_path)):
        return

    import yaml

    cfg = yaml.safe_load(open(cfg_path))
    entries = cfg.get("models", [])
    enabled = [m for m in entries if m.get("enabled", True)]
    missing_enabled = [m for m in enabled if m["model_id"] not in have]
    to_download = [m for m in entries if m.get("needs_download")]

    typer.echo(f"\nPanel: {len(enabled)} enabled, {len(missing_enabled)} of those missing locally.")
    for m in missing_enabled:
        typer.echo(f"  MISSING (enabled)  {m['key']:<20} id={m['model_id']}")

    typer.echo("\nCausal-contrast coverage (this is what makes the paper causal, not a leaderboard):")
    by_contrast: dict = {}
    for m in entries:
        for c in str(m.get("contrast", "")).split(","):
            if c:
                by_contrast.setdefault(c.strip(), []).append(m)
    for c, members in sorted(by_contrast.items()):
        present = [m for m in members if m["model_id"] in have]
        ok = "OK " if len(present) >= 2 else "GAP"
        names = ", ".join(m["key"] for m in present) or "none present"
        typer.echo(f"  [{ok}] {c:<12} {len(present)}/{len(members)} present  ({names})")

    if to_download:
        typer.echo("\nTo complete the design, download these in LM Studio (then fix the id + enable):")
        for m in to_download:
            typer.echo(f"  {m['key']:<14} search: {m['model_id']}")

    typer.echo(
        "\nBefore any sweep, PRE-LOAD each model with a constrained context "
        "(JIT defaults to full 262k ctx and will OOM):\n"
        "    lms load <model_id> --context-length 8192 --gpu max -y"
    )


@app.command()
def generate(
    config: str = typer.Option("configs/dataset.yaml", help="generator config"),
    seed: int = typer.Option(0, help="override the config seed (0 = use config)"),
    out: str = typer.Option("", help="output dir (default results/datasets/v2_seed<SEED>)"),
):
    """Procedurally generate contract-varied instances (inline mesh/nodal/MNA verification)."""
    import yaml
    from .generate import generate_dataset

    cfg = yaml.safe_load(open(_v2path(config)))
    the_seed = seed or int(cfg.get("seed", 20260709))
    out_dir = _v2path(out or f"results/datasets/v2_seed{the_seed}")
    manifest = generate_dataset(cfg, the_seed, out_dir, REPO)
    typer.echo(json.dumps({k: manifest[k] for k in
                           ("seed", "n_physics", "n_instances", "regime_counts", "rejects",
                            "canary_guid")}, indent=2))
    typer.echo(f"Wrote {out_dir}/instances.jsonl (+ manifest.json)")


@app.command()
def verify(
    dataset: str = typer.Option("results/datasets/v2_seed20260709", help="dataset dir"),
    tol: float = typer.Option(1e-4, help="relative tolerance for the SPICE gate"),
):
    """NGSPICE + exact-MNA dual-verification of every unique physics instance."""
    from .verify import verify_dataset, ngspice_available

    if not ngspice_available():
        typer.echo("ngspice not found — install it: brew install ngspice")
        raise typer.Exit(1)
    s = verify_dataset(_v2path(dataset), rel_tol=tol)
    typer.echo(f"verified physics: {s['n_pass']}/{s['n_physics']} PASS "
               f"(tol={s['rel_tol']}, ngspice={s['ngspice']})")
    for r in s["results"]:
        if r["status"] == "FAIL":
            typer.echo(f"  FAIL {r['physics_id']}: {r['errors']}")
    if s["n_fail"]:
        raise typer.Exit(1)


@app.command("validate-transforms")
def validate_transforms(
    dataset: str = typer.Option("results/datasets/v2_seed20260709", help="dataset dir"),
    out: str = typer.Option("results/tables/transform_validation.json", help="summary path"),
):
    """Independent validation of expected_under_contract + diagnostic_vars (methods-hole fix):
    physical re-grounded NGSPICE run for ref_node=top, raw-observable re-derivation for
    ccw/act, and diagnostic-mask recomputation from stored numbers."""
    from .validate_transforms import validate_dataset
    from .verify import ngspice_available

    if not ngspice_available():
        typer.echo("ngspice not found — install it: brew install ngspice")
        raise typer.Exit(1)
    s = validate_dataset(_v2path(dataset), _v2path(out))
    typer.echo(f"transform validation: {s['n_pass']}/{s['n_physics']} physics PASS "
               f"(checks: {', '.join(s['checks'])})")
    for r in s["results"]:
        if r["status"] == "FAIL":
            typer.echo(f"  FAIL {r['physics_id']}:")
            for e in r["errors"][:6]:
                typer.echo(f"    {e}")
    if s["n_fail"]:
        raise typer.Exit(1)


@app.command("gen-contour")
def gen_contour(
    config: str = typer.Option("configs/contour.yaml", help="contour generator config"),
    seed: int = typer.Option(0, help="override the config seed (0 = use config)"),
    out: str = typer.Option("", help="output dir (default results/contour/datasets/v3contour_seed<SEED>)"),
):
    """V3 second domain: generate contract-varied polygon line-integral instances
    (inline FOUR-WAY exact oracle: sympy-param == sympy-green == fraction == numeric)."""
    import yaml
    from .contour.generate import generate_contour

    cfg = yaml.safe_load(open(_v2path(config)))
    the_seed = seed or int(cfg.get("seed", 20260720))
    out_dir = _v2path(out or f"results/contour/datasets/v3contour_seed{the_seed}")
    manifest = generate_contour(cfg, the_seed, out_dir, REPO)
    typer.echo(json.dumps({k: manifest[k] for k in
                           ("seed", "n_physics", "n_instances", "regime_counts", "rejects",
                            "canary_guid")}, indent=2))
    typer.echo(f"Wrote {out_dir}/instances.jsonl (+ manifest.json)")


@app.command("validate-contour")
def validate_contour(
    dataset: str = typer.Option("results/contour/datasets/v3contour_seed20260720",
                                help="contour dataset dir"),
    out: str = typer.Option("results/contour/tables/transform_validation.json",
                            help="summary path"),
):
    """Independent validation of the contour convention transforms: reversed-traversal,
    negated-field, and left-normal re-integration + Green re-verify + mask recompute."""
    from .contour.validate import validate_dataset

    s = validate_dataset(_v2path(dataset), _v2path(out))
    typer.echo(f"contour transform validation: {s['n_pass']}/{s['n_physics']} physics PASS "
               f"(checks: {', '.join(s['checks'])})")
    for r in s["results"]:
        if r["status"] == "FAIL":
            typer.echo(f"  FAIL {r['physics_id']}:")
            for e in r["errors"][:6]:
                typer.echo(f"    {e}")
    if s["n_fail"]:
        raise typer.Exit(1)


@app.command()
def run(
    models: str = typer.Option("configs/models.yaml", help="panel config"),
    backend: str = typer.Option("lmstudio", help="default backend override"),
    dataset: str = typer.Option("results/datasets/v2_seed20260709", help="dataset dir"),
    out: str = typer.Option("results", help="output root (cache/ + responses/)"),
    only: str = typer.Option("", help="comma-separated model keys to run (default: all enabled)"),
):
    """Run the enabled model panel over the dataset (content-addressed cache, resumable)."""
    import yaml
    from .run import run_panel

    cfg = yaml.safe_load(open(_v2path(models)))
    cfg.setdefault("defaults", {})["backend"] = backend
    if only:
        keys = {k.strip() for k in only.split(",") if k.strip()}
        cfg["models"] = [m for m in cfg.get("models", []) if m.get("key") in keys]
        missing = keys - {m.get("key") for m in cfg["models"]}
        if missing:
            typer.echo(f"unknown model keys: {sorted(missing)}")
            raise typer.Exit(1)
    results = run_panel(cfg, _v2path(dataset), _v2path(out), progress=typer.echo)
    typer.echo(json.dumps(results, indent=2))


@app.command()
def grade(
    responses: str = typer.Option("results/responses", help="responses dir"),
    dataset: str = typer.Option("results/datasets/v2_seed20260709", help="dataset dir"),
    out: str = typer.Option("results/graded", help="graded output dir"),
):
    """Deterministic extract + numeric + compliance grading (no LLM on this path)."""
    from .grade.numeric import grade_responses, format_summary

    summary = grade_responses(_v2path(dataset), _v2path(responses), _v2path(out))
    typer.echo(format_summary(summary))
    typer.echo(f"\nWrote {_v2path(out)}/summary.json")


@app.command()
def analyze(
    graded: str = typer.Option("results/graded", help="graded rows dir"),
    out: str = typer.Option("results/tables", help="tables output dir"),
    dataset: str = typer.Option("results/datasets/v2_seed20260709",
                                help="dataset dir (for the diagnostic-vars-restricted table)"),
    factors: str = typer.Option("ccw,act,top",
                                help="flip cells to pair against dflt (contour: cw,wrk,inw)"),
):
    """Within-physics McNemar paired tests per factor, Wilson CIs, rate tables."""
    from .analyze.tables import analyze_graded, format_factor_table

    summary = analyze_graded(_v2path(graded), _v2path(out), _v2path(dataset),
                             factors=tuple(f.strip() for f in factors.split(",") if f.strip()))

    # V2-3 stats hygiene: bootstrap ORs, BH q-values, both var-level denominators.
    from .analyze.stats_extra import augment_analysis, write_outputs
    augment_analysis(summary)
    write_outputs(summary, _v2path(out))
    with open(os.path.join(_v2path(out), "analysis.json"), "w") as f:
        json.dump(summary, f, indent=2)

    typer.echo(f"analyzed {summary['n_rows']} graded rows across {len(summary['models'])} models\n")
    typer.echo(format_factor_table(summary))
    typer.echo(f"\nWrote {_v2path(out)}/cell_rates.csv, factor_pairs.csv, "
               "var_level*.csv, analysis.json")
    try:
        from .analyze.figures import make_figures
        figs = make_figures(os.path.join(_v2path(out), "analysis.json"),
                            _v2path("results/figures"))
        typer.echo(f"Wrote {len(figs)} figure files to {_v2path('results/figures')}")
    except Exception as e:  # noqa: BLE001  — figures are optional; never fail the analysis on them
        typer.echo(f"(figures skipped: {e})")


if __name__ == "__main__":
    app()
