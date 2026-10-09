# SWSE-Analysis

A verified, provenance-tagged dataset of **every character-creation option in Star
Wars Saga Edition**, plus the tooling to enumerate and evaluate the combinations.

The goal is not a character builder. It is a workspace where a human or an AI agent
can answer questions like:

- How many different level-1 characters can be built? *(580,200,130 core builds; 10^19.6 including ability scores, destiny and background)*
- How many legal class paths reach level 20? *(2,533,086,352,502,117,155,404,251,136)*
- Which options are load-bearing - which unlock the most other options?
- What does a prestige class actually require, and which heroic classes can feed it?
- Where does the data run out, and what would have to be true to fill the hole?

Every number above is computed from the two source workbooks in this repository and
can be regenerated with one command.

## Quickstart

```bash
pip install -e ".[dev]"        # or: pip install openpyxl pyyaml jsonschema pytest

python -m swse.cli doctor      # are the sources, config and dependencies in place?
make data                      # extract -> canonicalize -> db -> validate
make analysis                  # graph -> space -> enumerate -> evaluate -> report
make test                      # the full suite, ~75s
```

`make all` runs everything. Individual stages:

| command | what it does | output |
|---|---|---|
| `swse doctor` | verifies workbooks by sha256, config, dependencies | stdout |
| `swse extract` | reads the workbooks at declared coordinates | `data/raw/*.jsonl` |
| `swse canonicalize` | merges raw rows into canonical records, applies curation | `data/canonical/*.json` |
| `swse validate` | runs every consistency check | `data/reports/validation.md` |
| `swse db` | builds the queryable index | `data/index/swse.sqlite3` |
| `swse stats` | corpus counts, canon split, per-entity breakdown | stdout |
| `swse graph` | prerequisite graph: edges, cycles, chains, dangling | `data/reports/prerequisite-graph.md` |
| `swse space` | the decision space, dimension by dimension | `data/reports/decision-space.md` |
| `swse enumerate` | exact level-1 builds, or sampled builds at any level | `analysis/out/builds-levelN.jsonl` |
| `swse evaluate` | scores builds and digests a sample | `analysis/out/builds-levelN.md` |
| `swse report` | every dataset and analysis document | `data/reports/`, `analysis/out/`, `docs/` |
| `swse audit` | are the official / third-party / homebrew tiers comparable? | `analysis/out/canon-balance.md` |

Every stage accepts `--json` for machine-readable output, so stages can be chained
without scraping prose.

## What is in the dataset

4,830 canonical records across 45 entity types, extracted from 60 declared blocks
in two workbooks:

| canon | records | meaning |
|---|---:|---|
| `official` | 3,689 | content that cites a published sourcebook (or comes from an official-content block) |
| `third_party` | 1,139 | content carried only by the third-party builder, with no printed citation |
| `homebrew` | 2 | the Master Reference's own homebrew section (Technician, Force Prodigy) |

Canonicity is about **content**, not carrier. SagaForge is a third-party spreadsheet,
but most of what it holds is official WotC rules text; a record that cites a
published book is treated as official whatever file carried it. Every record says
how that decision was made in `attrs.canon_basis`.

Selection of what exists to choose from:

| decision | options |
|---|---:|
| species (incl. droid chassis, beasts, near-humans) | 130 |
| heroic classes / prestige classes | 7 / 32 |
| feats | 387 |
| talents across 192 trees | 1,311 |
| Force powers / techniques / secrets / regimens | 92 / 58 / 15 / 12 |
| skills | 25 |
| weapons / armor / equipment / ammunition | 246 / 92 / 226 / 21 |
| weapon modifications / accessories | 156 / 46 |
| droid options | 121 |
| destinies / backgrounds / languages | 88 / 46 / 102 |

Full listing: [`data/reports/option-catalog.md`](data/reports/option-catalog.md).
Field-level reference: [`docs/data-dictionary.md`](docs/data-dictionary.md) (generated).

## How the data is layered

```
SWSE_Master_Reference_10-8-2026.xlsx          sources (pinned by sha256 in
3rd_Party_Builder/SagaForge 1.53.xlsm          config/sources.yaml)
        |
        |  swse extract        coordinates declared in config/blocks.yaml
        v
   data/raw/*.jsonl            gitignored, regenerable
        |
        |  swse canonicalize   config/entities.yaml + swse/hooks.py
        v                      + data/curation/*.yaml  <-- human decisions
   data/canonical/*.json       committed: the dataset
        |
        +-- swse db ---------> data/index/swse.sqlite3   gitignored, regenerable
        +-- swse graph/space/enumerate/evaluate/report
                              -> data/reports/*.md, analysis/out/*
```

Two rules keep this safe to regenerate:

1. **Nothing downstream of `data/raw` is hand-edited.** Fixes go into
   `config/blocks.yaml` (coordinates), `config/entities.yaml` (model),
   `swse/hooks.py` (corpus quirks) or `data/curation/*.yaml` (judgement calls).
2. **Curation survives regeneration.** Aliases, merges, drops and overrides live in
   `data/curation/` and are re-applied on every build, so re-extracting never
   destroys a human decision.

## Trustworthiness

- Every record carries `sources: [{source, block, sheet, row, ref, canon}]` - a cell
  reference into a hash-pinned workbook. There are no unsourced records.
- `swse validate` checks source hashes, index/file consistency, JSON-schema
  conformance, id uniqueness, provenance completeness, prerequisite cycles and
  dangling references, name collisions, curation integrity and config consistency.
  Current status: **0 errors, 1 warning** (21 deliberately unmerged name collisions).
- Prerequisite text is parsed into typed predicates: **98.5% coverage**, 680 edges,
  **0 dangling**, **0 cycles**.
- Where two sources overlap they cross-verify each other. Example: SagaForge's
  numeric defence bonuses reproduce the Master Reference's printed "Ref +1 / Will +2"
  text exactly for all five heroic classes - so the level-1 defence bonus is a
  *verified fact*, not an assumption. That test is
  `tests/test_canonical_data.py::test_defense_bonuses_match_the_printed_column`.
- Where the sources run out, the gap is declared rather than papered over:
  [`data/curation/gaps.yaml`](data/curation/gaps.yaml) and
  [`docs/known-gaps.md`](docs/known-gaps.md). Assumptions live in
  [`config/analysis.yaml`](config/analysis.yaml) with a `verified:` flag, and every
  report repeats the flag next to the numbers that depend on it.

## Reading order

1. [`AGENTS.md`](AGENTS.md) - how to work in this repository (start here if you are an agent)
2. [`docs/ontology.md`](docs/ontology.md) - the entity model and what each entity is
3. [`docs/data-dictionary.md`](docs/data-dictionary.md) - generated field reference
4. [`docs/prereq-grammar.md`](docs/prereq-grammar.md) - how prerequisite text becomes typed predicates
5. [`docs/decision-space.md`](docs/decision-space.md) - how the space is counted, and what is assumed
6. [`docs/verification.md`](docs/verification.md) - what is verified against what
7. [`docs/known-gaps.md`](docs/known-gaps.md) - what is missing and why it matters
8. [`docs/adding-sources.md`](docs/adding-sources.md) - how to ingest a new workbook or wiki dump
9. [`tasks/`](tasks/README.md) - the backlog

## Licensing and attribution

The code is MIT. The *data* is transcribed game content and is not ours to license -
see [`NOTICE.md`](NOTICE.md) for attribution and the constraints that follow from it.
