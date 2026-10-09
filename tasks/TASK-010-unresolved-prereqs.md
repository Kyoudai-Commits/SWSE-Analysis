# TASK-010 - Resolve the 8 remaining prerequisite fragments

**Status:** open | **Priority:** medium | **Gap:** GAP-008

## Problem

Prerequisite parse coverage is 98.55% (545 of 553 records). Eight fragments still do
not resolve to a record, so those gates are ignored in legality checks:

| fragment | n | what it needs |
|---|---:|---|
| `Basic Processor` | 2 | a `droid_system` entity |
| `Droid Systems: Heuristic Processor` | 2 | a `droid_system` entity |
| `Shield Generator System` | 2 | a `droid_system` entity (or `requires_item`) |
| `Cyborg Hybrid with Subcutaneous Comlink` | 2 | a cyborg/template entity |
| `larger Droid with 2+ Appendages` | 2 | a structural predicate over droid options |
| `larger Droid with 2+ Tool Mounts` | 2 | a structural predicate over droid options |
| `or Tracked Locomotion` | 2 | a `droid_option` ref (locomotion) |
| `"Gamemaster's Approval"` | 1 | a `gm_approval` predicate type - a rule, not an option |

Because unresolved gates are skipped, their effect is permissive: a build that should
be illegal can be counted as legal. It can never produce a false violation.

## Evidence

```bash
python -m swse.cli validate --show 20
sed -n '/could not be resolved/,/^## /p' data/reports/prerequisite-graph.md
python -c "
from swse.store import Dataset; db=Dataset.load()
n=0
for e in db.entities:
    for r in db.all(e):
        p=r.get('prerequisites') or {}
        for pred in p.get('predicates',[]):
            if not pred.get('resolved'): n+=1; print(r['id'], '|', pred)
print('unresolved predicates', n)"
```

## Approach

Split into three kinds of fix, in this order:

1. **Missing entity** (droid systems, cyborg templates). Add blocks to
   `config/blocks.yaml` for whatever table lists droid systems, register the entity in
   `config/entities.yaml`, and let `prereq_pass` resolve against it. This is the only
   real data work in the task.
2. **New predicate type** (`gm_approval`, and the structural `droid_with` comparisons
   like "2+ Appendages"). Add the type in `swse/prereq.py` with a test in
   `tests/test_prereq.py`. `droid_with` already exists on `LABEL_INNER_RULES`; it
   needs a *count* form.
3. **Alias only** (`or Tracked Locomotion` is a locomotion option already in the
   corpus under another name). Add to `data/curation/aliases.yaml` - never patch the
   parser for one record.

Note the leading `or` in `or Tracked Locomotion`: it is a disjunction whose first
branch resolved, so the fragment text kept the conjunction. The fix is in the
disjunction handling, not in a name lookup.

## Acceptance criteria

- [ ] `prereq_parse_coverage` reaches 100%, or every remaining fragment is declared in
      `data/curation/gaps.yaml` with a reason it cannot resolve.
- [ ] `swse graph` still reports 0 dangling and 0 cycles, with a higher resolved-edge
      count than 628.
- [ ] New predicate types have unit tests in `tests/test_prereq.py`.
- [ ] `enumerate --check` on the level-1 sample still reports 0 violations - and if a
      newly resolved gate makes a previously legal build illegal, the report says how
      many builds that removed.
- [ ] GAP-008 flips to `resolved`.

## Files likely to change

`config/blocks.yaml`, `config/entities.yaml`, `swse/prereq.py`,
`data/curation/aliases.yaml`, `tests/test_prereq.py`.
