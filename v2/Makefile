# CircuChain v2 pipeline. One target per stage; `make all` runs the full local sweep.
# Override SEED / BACKEND / MODELS on the command line, e.g. `make run BACKEND=mlx`.

SEED    ?= 20260709
BACKEND ?= ollama
MODELS  ?= configs/models.yaml
DS      := results/datasets/v2_seed$(SEED)

.PHONY: all generate verify run grade analyze regrade test smoke models clean

## Reproduce the Week-3 credibility result on the frozen v1 logs (CPU-only, no inference).
regrade:
	python scripts/regrade_v1_logs.py

## Unit tests (contract transforms + compliance grader).
test:
	python tests/test_contract_transforms.py
	python tests/test_compliance_grader.py

generate:
	circuchain generate --config configs/dataset.yaml --seed $(SEED)

verify: generate
	circuchain verify --dataset $(DS)

run: verify
	circuchain run --models $(MODELS) --backend $(BACKEND)

grade: run
	circuchain grade --responses results/responses

analyze: grade
	circuchain analyze --graded results/graded

all: analyze

## List which configured models are actually pulled locally (cross-checks Ollama).
models:
	circuchain models --installed --config configs/models.yaml

## Tiny end-to-end run for CI / a laptop.
smoke:
	circuchain generate --config configs/smoke.yaml --seed 1
	circuchain verify --dataset results/datasets/v2_seed1
	circuchain run --models configs/smoke.yaml
	circuchain grade --responses results/responses
	circuchain analyze --graded results/graded

clean:
	rm -rf results/cache results/responses results/graded
