# CircuChain v2 pipeline. One target per stage; `make all` runs the full local sweep.
# Override SEED / BACKEND / MODELS on the command line, e.g. `make run BACKEND=mlx`.

SEED    ?= 20260709
BACKEND ?= lmstudio
MODELS  ?= configs/models.yaml
DS      := results/datasets/v2_seed$(SEED)

.PHONY: all generate verify run grade analyze regrade test smoke models clean

## Reproduce the Week-3 credibility result on the frozen v1 logs (CPU-only, no inference).
regrade:
	python scripts/regrade_v1_logs.py

## Unit tests (contract transforms + compliance grader + topology goldens + SPICE gate).
test:
	python tests/test_contract_transforms.py
	python tests/test_compliance_grader.py
	python tests/test_topologies_golden.py
	python tests/test_analytic_vs_spice.py
	python tests/test_extract.py
	python tests/test_analyze.py
	python tests/test_validate_transforms.py

generate:
	circuchain generate --config configs/dataset.yaml --seed $(SEED)

verify: generate
	circuchain verify --dataset $(DS)

run: verify
	circuchain run --models $(MODELS) --backend $(BACKEND) --dataset $(DS)

grade: run
	circuchain grade --responses results/responses --dataset $(DS)

analyze: grade
	circuchain analyze --graded results/graded

all: analyze

## List downloaded models + which causal contrasts the panel can currently support.
models:
	circuchain models --installed --backend $(BACKEND) --config configs/models.yaml

## Pre-load one model with a constrained context (JIT defaults to full 262k ctx and OOMs).
## Usage: make load MODEL=qwen/qwen3.5-9b [CTX=8192]
CTX ?= 8192
load:
	lms load $(MODEL) --context-length $(CTX) --gpu max -y

## Tiny end-to-end run for CI / a laptop (pre-load the smoke model first, see configs/smoke.yaml).
smoke:
	circuchain generate --config configs/smoke.yaml --seed 1
	circuchain verify --dataset results/datasets/v2_seed1
	circuchain run --models configs/smoke.yaml --dataset results/datasets/v2_seed1 --out results/smoke
	circuchain grade --responses results/smoke/responses --dataset results/datasets/v2_seed1 --out results/smoke/graded

clean:
	rm -rf results/cache results/responses results/graded results/smoke
