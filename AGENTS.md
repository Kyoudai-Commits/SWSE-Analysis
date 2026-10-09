# AGENTS.md - working in this repository

This file is the operating manual for AI agents (and humans) working on
SWSE-Analysis. Read it before changing anything. Everything in it exists because
someone got it wrong once.

## The one rule that matters most

**Do not hand-edit generated files.** If a value in the dataset is wrong, fix the
thing that produces it:

| the problem is in | fix it here |
|---|---|
| which cells are read | `config/blocks.yaml` (coordinates, `require_key`, `skip_rows`) |
| how a row becomes a record | `config/entities.yaml` (rename, keep, drop, `row_hooks`, `merge_on`) |
| a quirk that repeats across the corpus | `swse/hooks.py` (a new row hook) |
| a one-off judgement call | `data/curation/{aliases,merges,overrides,drops}.yaml` |
| an assumption about the game | `config/analysis.yaml` (with `verified:` and `note:`) |
| missing data | `data/curation/gaps.yaml` + a task in `tasks/` |

Generated, never edited: `data/raw/`, `data/canonical/`, `data/index/`,
`data/reports/`, `analysis/out/`, `docs/data-dictionary.md`.

After changing anything above, the dataset is stale until you rebuild:

```bash
make data          # extract + canonicalize + db + validate
```

Editing `config/*.yaml`, a hook, `swse/ids.py` or `swse/prereq.py` has **no effect
whatsoever** until `canonicalize` and `db` have been re-run. This is the single most
common way to conclude wrongly that a fix "didn't work".

## Verify with the repository's own tools

Use the CLI, the Makefile and the tests - not throwaway shell scripts:

```bash
make test                                     # 142 tests, ~1 minute
python -m swse.cli validate --show 5          # errors first
python -m swse.cli stats --json               # did the corpus shape change?
python -m swse.cli graph --json               # dangling edges, cycles
python -m swse.cli enumerate --level 1 --limit 100 --check --quiet --json   # legal?
```

Ad-hoc `python3 - <<'PY'` heredocs have already silently no-op'd twice in this
repository's history. If you need to inspect data, prefer
`python -m swse.cli stats`/`graph`/`enumerate` or a one-line
`python -c "from swse.store import Dataset; ..."`, and if you must patch a file,
use an editor tool so the change is reviewable in the diff.

## Definition of done for a data change

A change is done when all of these hold:

1. `make data` runs clean and `validate` reports **0 errors**.
2. `make test` passes. If you fixed a data bug, add a test that fails without the
   fix - the suite already contains several regression tests named after the bug
   they pin down.
3. New warnings/infos are either resolved or declared in `data/curation/gaps.yaml`.
4. Anything you assumed is recorded in `config/analysis.yaml` with
   `verified: false` and a `note:` saying what would confirm it.
5. If the change alters a number quoted in `README.md` or a report, regenerate the
   report (`python -m swse.cli report`) rather than editing prose.

## Definition of done for an analysis question

1. The answer is reproducible from a CLI invocation recorded in the document.
2. The document says which assumptions it rests on, and whether they are verified.
3. Where the data ran out, the document says so explicitly and links the gap/task.

Never let a report imply more confidence than the data supports. "This number is
exact given assumption X, which is unverified" is the house style.

## Where things live

```
config/
  sources.yaml      the two workbooks: path, sha256, canon, kind, planned_sources
  blocks.yaml       60 extraction blocks: sheet, range, header row, rename/drop maps
  entities.yaml     45 entities: role, merge_on, keep/rename, row_hooks, post hooks
  sourcebooks.yaml  10 sourcebooks + the 'unknown' pseudo-entry, with page_prefixes
  analysis.yaml     scoring weights, ability methods, progression, assumptions
swse/
  paths.py          all filesystem locations (never hard-code a path elsewhere)
  ids.py            slug(), make_id(), clean_cell(), fold(), fold_multiline(), tree_key()
  sources.py        Source, load_registry(), workbook(), sheet_names(), defined_names()
  blocks.py         block declarations and range parsing
  extract.py        workbook -> data/raw/*.jsonl
  sourcebooks.py    page references and source-tag parsing (GoI, TFU, JATM, ...)
  prereq.py         prerequisite text -> typed predicates; the EntityIndex resolver
  hooks.py          row hooks and post hooks that fix corpus-level quirks
  canon.py          merge-on rules, curation application, canonical files, gaps
  store.py          Dataset (the in-memory/JSON API) and build_sqlite()
  graph.py          PrereqGraph: edges, closure, unlocks, cycles, depth
  validate.py       every consistency check
  space.py          DecisionSpace: dimension-by-dimension counting
  enumerate.py      Constraints, Builder, iter_level1_builds, sample_builds, check_build
  evaluate.py       METRICS, Evaluator, rank(), summary_table()
  report.py         the markdown/jsonl reports
  cli.py            argparse entry point
tests/              9 modules; conftest.py holds session-scoped fixtures
tasks/              the backlog: TASK-nnn.md, one file per task
docs/               hand-written docs (+ generated data-dictionary.md)
```

## Corpus facts worth knowing before you dig

- **Two sources, overlapping.** The Master Reference (MR) is a human-curated
  spreadsheet that mixes official content with its own homebrew section. SagaForge
  (SF) 1.53 is a third-party character builder whose real data lives in the *hidden*
  `Data` (417x261) and `Lists` (285x245) sheets; its visible sheets are
  formula-driven UI and produce `#VALUE!`/`#REF!` garbage. Extract only via the
  coordinates in `blocks.yaml`.
- **Merge across sources only.** Two records with the same name from the *same*
  source are kept separate and flagged `name_collision` (21 of them, all inspected,
  all genuinely distinct - see GAP-007). Merging within a source destroyed real
  options the first time it was tried.
- **Value conflicts are resolved by canon rank then by longest text**, and the loser
  is preserved in `conflicts` so the decision is auditable.
- **Newlines are data.** `clean_cell()` collapsing `\n` was the single largest
  prerequisite bug: names and ids use `fold()`, values use `fold_multiline()`.
- **The `Talents!E-I` columns are a visual layout grid, not tiers.** Talent tier is
  genuinely absent (GAP-001).
- **Species data overlaps itself.** `Data!BO` and `Data!BV` both describe species
  traits; reading both inflates 131 species to 222. `blocks.yaml` handles this.
- **Parameterised feats.** "Weapon Proficiency" is one feat plus a `param` axis (6
  weapon groups); the derived axis is materialised by `derive_parameter_axes`, and
  such records carry the `parameterised` flag.
- **Class grants are structured.** `split_class_grants` produces `grants_feats`,
  `grants_trees`, `grants_skills` etc. with 0 unmatched items; `mr_talent_trees`
  AVAILABILITY is the only authoritative class-to-tree mapping.

## Dependencies

Non-persistent in the sandbox: `pip install --break-system-packages openpyxl pandas
pytest jsonschema pyyaml` (or `pip install -e ".[dev]"`). `swse doctor` tells you
what is missing.

## Style

- Python 3.11+, dataclasses, type hints, no runtime deps beyond openpyxl/pyyaml/
  jsonschema. `pyproject.toml` configures the package; `scripts/hashes.py --write`
  is the only sanctioned way to re-pin a source hash.
- Reports are Markdown with a header block naming the command that produced it, so a
  reader can always re-derive them.
- Comments explain *why*, especially where a rule was learned the hard way. Tests
  that pin down a past bug say so in their docstring.
- Keep the SQLite schema in `swse/store.py::SCHEMA_SQL` and the column count in
  `build_sqlite()` in step - they must match exactly.

## If you are picking up work

Start at [`tasks/README.md`](tasks/README.md). Each task file states the problem,
the evidence, the acceptance criteria and the files that will change. Tasks that are
blocked on data we do not have say so, and link the gap that must close first.
