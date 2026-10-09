# TASK-006 - Encode the droid option budget

**Status:** open | **Priority:** medium | **Gap:** GAP-010

## Problem

Droid characters buy from 121 `droid_option` records that carry cost and weight, but
the *allowance* a droid gets to spend is computed in SagaForge's VBA and stored in no
cell. So `swse.space` counts droid option combinations without any budget
constraint - it reports a space that is larger than the legal one.

`final_cost`-style columns were deliberately dropped as builder scratch during
extraction (they are computed UI values, not data), which is correct for extraction
but leaves the budget unmodelled.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
d=db.all('droid_option')
print('options', len(d))
print('with cost', sum(1 for x in d if x['attrs'].get('cost') not in (None,'')))
print('with weight', sum(1 for x in d if x['attrs'].get('weight') not in (None,'')))"
grep -n "droid" config/blocks.yaml | head
```

## Approach

1. Find the allowance: SECR's droid chapter (TASK-002) states how many options a droid
   of a given class/degree gets, and the builder's VBA encodes the same rule. Either
   is acceptable if it becomes a registered source rather than a code comment.
2. Model it as data, not as a hard-coded constant: a `droid_budget` entry in
   `config/analysis.yaml` with `verified:`, `note:` and `task:` fields, keyed by droid
   degree/size if the rule varies.
3. Enforce it in `enumerate.check_build` so a sampled droid build over budget is a
   *violation*, and in `space` so the droid dimension is a constrained count rather
   than a power set.

## Acceptance criteria

- [ ] The budget rule is declared in `config/analysis.yaml` with evidence.
- [ ] `check_build` rejects over-budget droid builds; the level-1/10/20 samples still
      report 0 violations (they should - they were generated under no budget, so this
      will legitimately reduce the legal count).
- [ ] `space` reports the droid dimension as constrained, with the before/after counts
      in `data/reports/decision-space.md`.
- [ ] A test builds a deliberately over-budget droid and asserts the violation.
- [ ] GAP-010 flips to `resolved`.

## Files likely to change

`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`,
`tests/test_enumerate_evaluate.py`.
