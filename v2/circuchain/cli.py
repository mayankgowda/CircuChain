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
    installed: bool = typer.Option(False, "--installed", help="list locally-pulled Ollama models"),
    config: str = typer.Option("configs/models.yaml", help="panel config to cross-check"),
):
    """Enumerate installed models and flag any configured model that isn't pulled yet."""
    from .providers.ollama import OllamaProvider

    try:
        have = {m["name"]: m for m in OllamaProvider.list_installed()}
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Could not reach Ollama at localhost:11434 ({e}). Is `ollama serve` running?")
        raise typer.Exit(1)

    typer.echo(f"Installed locally ({len(have)}):")
    for name, m in sorted(have.items()):
        gb = (m.get("size") or 0) / 1e9
        typer.echo(f"  {name:<34} {gb:5.1f} GB  {m.get('quant') or ''}")

    cfg_path = config if os.path.isabs(config) else os.path.join(V2, config)
    if installed and os.path.exists(cfg_path):
        import yaml

        cfg = yaml.safe_load(open(cfg_path))
        want = [m for m in cfg.get("models", []) if m.get("enabled", True)]
        missing = [m for m in want if m["model_id"] not in have]
        typer.echo(f"\nConfigured & enabled: {len(want)}   missing locally: {len(missing)}")
        for m in missing:
            typer.echo(f"  MISSING  {m['key']:<20} -> ollama pull {m['model_id']}")


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
