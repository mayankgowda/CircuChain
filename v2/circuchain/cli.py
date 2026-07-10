"""CircuChain v2 CLI.

Implemented now (proven, runnable):
    circuchain regrade                 -- re-grade the v1 logs -> rule-vs-judge kappa (GNG-1)
    circuchain models --installed      -- cross-check configs/models.yaml against local Ollama

Stubs (see ENGINEERING_PLAN.md build order — implement in this order):
    generate  verify  run  grade  analyze  judge
Each stub explains what to build and where. This keeps the installed package honest: it never
pretends a stage works before it does.
"""
from __future__ import annotations

import os
import subprocess
import sys

import typer

app = typer.Typer(add_completion=False, help="CircuChain v2 — Convention Blindness benchmark (M5-local).")

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, ".."))


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

    cfg_path = config if os.path.isabs(config) else os.path.join(V2, config)
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

    # Which causal contrasts are currently satisfiable?
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


def _todo(stage: str, builds: str):
    typer.echo(f"[not-yet-implemented] `circuchain {stage}` — see v2/ENGINEERING_PLAN.md build order.")
    typer.echo(f"  Implement: {builds}")
    raise typer.Exit(2)


@app.command()
def generate(config: str = "configs/dataset.yaml", seed: int = 20260709):
    """(stub) Procedurally generate + dual-verify N>=500 contract-varied instances."""
    _todo("generate", "circuchain/topologies/*, analytic.py, generate.py, verify.py (build steps 3-8)")


@app.command()
def verify(dataset: str = ""):
    """(stub) NGSPICE(.op) + SymPy dual-verification of a generated dataset."""
    _todo("verify", "circuchain/verify.py + tests/test_analytic_vs_spice.py (build step 6)")


@app.command()
def run(models: str = "configs/models.yaml", backend: str = "ollama"):
    """(stub) Run the model panel over the dataset (resumable, cached)."""
    _todo("run", "circuchain/run.py + cache.py (providers/ollama.py already built) (build steps 9-10)")


@app.command()
def grade(responses: str = "results/responses"):
    """(stub) Deterministic extract + numeric + compliance grading (grade/compliance.py is built)."""
    _todo("grade", "circuchain/grade/extract.py + numeric.py + trace.py (build steps 11-12)")


@app.command()
def analyze(graded: str = "results/graded"):
    """(stub) McNemar paired tests, mixed-effects ORs, tables + figures."""
    _todo("analyze", "circuchain/analyze/stats.py + tables.py + figures.py (build step 13)")


if __name__ == "__main__":
    app()
