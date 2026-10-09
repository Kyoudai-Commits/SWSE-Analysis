# TASK-012 - Confirm the ability score generation methods

**Status:** open | **Priority:** high | **Gap:** GAP-003 | **Related:** TASK-007

## Problem

`config/analysis.yaml:ability_scores` declares three generation methods -
`standard_array`, `point_buy` and `dice` - and all three are `verified: false`. The
ability dimension contributes 16,777,216 allocations to the level-1 space, more than
any other single dimension except skill selections, so the headline level-1 figure
(580,200,130 core builds; 10^19.6 total) depends entirely on which method is assumed.

SagaForge has an ability grid and a "Point Buy" cell but no cost curve and no printed
array; the Master Reference has neither. There is no way to confirm any of this from
the two workbooks in the repository.

## Evidence

```bash
grep -n -A 40 "^ability_scores:" config/analysis.yaml
python -c "
from swse.space import ABILITY_KEYS, ability_modifier
print(ABILITY_KEYS, ability_modifier(14))"
python -m swse.cli space --level 1 --json | jq '.dimensions[] | select(.name==\"ability_allocations\")'
```

## Approach

TASK-007 handles the point-buy *arithmetic*. This task handles the method set:

1. Source which methods the game actually sanctions (SECR character creation chapter,
   via TASK-002) and record each as its own entry with `verified: true` and evidence.
2. Make the choice explicit at the CLI: `space --ability-method standard_array` already
   exists; ensure the report names the method used and prints all three counts side by
   side when no method is chosen, so a reader never mistakes one assumption for the
   total.
3. For `dice`, report a *distribution* rather than a count - the number of distinct
   outcomes, and the probability of meeting a given feat's `ability_min` gate. That is
   the question an agent actually asks ("can I roll into Jedi?"), and it is answerable
   exactly: 6 abilities x 4d6-drop-lowest is a small enumeration.
4. Ensure `enumerate.ability_arrays` emits arrays consistent with the sourced method,
   so sampled builds use legal scores.

## Acceptance criteria

- [ ] Each method in `config/analysis.yaml` has `verified:` set from evidence, with a
      `note:` explaining what was confirmed and an `evidence:` citation.
- [ ] `data/reports/decision-space.md` shows the ability dimension per method, and the
      headline total states which method it used.
- [ ] `dice` reports the probability of satisfying the strictest `ability_min` gates in
      the corpus (Jedi, Force-sensitive feats), not just a count.
- [ ] `enumerate` with each method produces builds that pass `--check` with 0 violations.
- [ ] `tests/test_space.py` asserts the three methods give three different, individually
      correct counts.
- [ ] GAP-003 flips to `resolved`.

## Files likely to change

`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`, `tests/test_space.py`,
`tests/test_enumerate_evaluate.py`.
