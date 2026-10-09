# TASK-002 - Transcribe the Core Rulebook progression tables

**Status:** open | **Priority:** high | **Gaps:** GAP-002, GAP-003, GAP-005

## Problem

Four of the highest-impact assumptions in `config/analysis.yaml` are unverified for
one reason: the Saga Edition Core Rulebook is not a source in this repository. Both
workbooks encode *options* faithfully but neither encodes the *progression tables*
that say what a character gets at each level.

Closing this single task unblocks TASK-005, TASK-007, TASK-011, TASK-012, TASK-013
and TASK-014.

## Evidence

The absence is directly observable in both workbooks:

```bash
# SagaForge's Class sheet is a blank character-sheet UI grid
python -c "
from swse.sources import load_registry, workbook
wb=workbook(load_registry()['sagaforge-1.53'])
rows=list(wb['Class'].iter_rows(min_row=6,max_row=25,values_only=True))
print('non-empty cells in Class!A6:V25:', sum(1 for r in rows for c in r if c is not None))"

# the per-level progression columns are all zeros
python -c "
from swse.sources import load_registry, workbook
wb=workbook(load_registry()['sagaforge-1.53'])
cols=list(wb['Data'].iter_rows(min_row=3,max_row=43,min_col=98,max_col=103,values_only=True))
print('distinct values in Data!CT:CY:', sorted({c for r in cols for c in r if c is not None}))"

# and the schedule in force is a declared assumption, not a fact
grep -n -B 3 -A 14 "^progression:" config/analysis.yaml
```

## What is needed

| table | where it is used | current state |
|---|---|---|
| class level progression (feats, talents, ability increases) | `space`, `enumerate` at levels 2-20 | declared, `verified: false` |
| heroic and prestige defence bonus by level | `evaluate.defense` | heroic verified, prestige assumed 2x |
| ability score generation (array, point-buy curve, dice) | `space.ability_allocations` | three methods declared, none verified |
| Force powers known / Force Training allowance | `enumerate`, `evaluate` | placeholder formula |
| talent tier by tree | `enumerate` talent gating | absent (GAP-001) |
| age category bounds per species | `space` age dimension | ungated (GAP-012) |

## Approach

Transcribe as a **new source**, not as edits to existing ones: a JSONL or CSV per
table registered in `config/sources.yaml` with `canon: [official]` and a recorded
sha256, then mapped to entities in `config/entities.yaml` (`class`, `talent`,
`species`, `age_table`). Follow `docs/adding-sources.md`.

Where a transcribed value contradicts a workbook value, the conflict lands in
`conflicts` automatically. Do not resolve it by editing the transcription - decide in
`data/curation/overrides.yaml` and record why.

## Acceptance criteria

- [ ] At least the heroic class progression table is a registered, hash-pinned source.
- [ ] `config/analysis.yaml:progression.heroic.verified` becomes `true` with an
      `evidence:` line naming the source and the cell/row range.
- [ ] Level-2-20 counts change, and `data/reports/decision-space.md` no longer
      carries the "unverified schedule" caveat for heroic classes.
- [ ] `test_defense_bonuses_match_the_printed_column` is extended from level 1 to the
      full progression, and still passes.
- [ ] A new test fails if the progression source's hash changes without a rebuild.

## Files likely to change

`config/sources.yaml`, `config/blocks.yaml`, `config/entities.yaml`,
`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`,
`tests/test_canonical_data.py`, `tests/test_space.py`.
