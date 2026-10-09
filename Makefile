# Every stage of the pipeline is one make target, and every target is one CLI
# command - no hidden shell logic lives here.
#
#   make doctor       is the workspace healthy?
#   make data         extract -> canonicalize -> db -> validate  (the dataset)
#   make analysis     graph -> space -> enumerate -> evaluate -> report
#   make all          both of the above, in order
#   make test         pytest
#   make clean        remove generated artefacts (never the sources or curation)

PY ?= python3
CLI := $(PY) -m swse.cli

.PHONY: help doctor extract canonicalize db validate data graph space enumerate evaluate report analysis all test clean hashes

help:
	@echo "targets: doctor extract canonicalize db validate data graph space"
	@echo "         enumerate evaluate report analysis all test clean hashes"

doctor:
	$(CLI) doctor

extract:
	$(CLI) extract

canonicalize:
	$(CLI) canonicalize

db:
	$(CLI) db

validate:
	$(CLI) validate

# The dataset: sources -> raw rows -> canonical records -> SQLite index -> checks.
data: extract canonicalize db validate

graph:
	$(CLI) graph

space:
	$(CLI) space --level 20
	$(CLI) space --level 20 --canon official --out data/reports/decision-space-official.md

# Sampling, not exhaustive enumeration: the level-20 space is ~10^165.
enumerate:
	$(CLI) enumerate --level 1 --exact --limit 4000 --check
	$(CLI) enumerate --level 5 --sample 200 --seed 20261008 --check
	$(CLI) enumerate --level 10 --sample 300 --seed 20261008 --check
	$(CLI) enumerate --level 20 --sample 300 --seed 20261008 --check

evaluate:
	$(CLI) evaluate --builds analysis/out/builds-level1.jsonl --top 10
	$(CLI) evaluate --builds analysis/out/builds-level10.jsonl --top 10
	$(CLI) evaluate --builds analysis/out/builds-level20.jsonl --top 10

report:
	$(CLI) report

analysis: graph space enumerate evaluate report

all: data analysis

test:
	$(PY) -m pytest

# Re-record the sha256 of the vendored workbooks after intentionally updating one.
hashes:
	$(PY) scripts/hashes.py

clean:
	rm -rf data/raw data/index analysis/out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
