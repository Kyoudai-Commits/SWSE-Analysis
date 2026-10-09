# TASK-008 - Turn starting credits into a gear allowance

**Status:** open | **Priority:** medium | **Gap:** GAP-011

## Problem

`class.attrs.starting_credits` is sourced and verified, but nothing ties it to what a
level-1 character may actually buy. Gear is therefore excluded from the decision space
by default and multiplied in only with `--gear`, which counts every combination of
246 weapons x 92 armor x 226 equipment regardless of price.

That makes the `--gear` figure an upper bound with no legality content, and it leaves
`evaluate` unable to score a build's equipment loadout - offense uses the best weapon
the character is *proficient with*, not one they could afford.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
cs=db.all('class')
print([(c['name'], c['attrs'].get('starting_credits')) for c in cs if c['attrs'].get('class_kind')=='heroic'])"
python -c "
from swse.store import Dataset; db=Dataset.load()
ws=db.all('weapon')
print('weapons with cost', sum(1 for w in ws if w['attrs'].get('cost') not in (None,'')), 'of', len(ws))"
python -m swse.cli space --level 1 --gear --json | jq '.dimensions[] | select(.name|test(\"gear\"))'
```

## Approach

1. Establish the rule: is the allowance exactly `starting_credits`, a multiple, or a
   class-specific equipment package? Both workbooks list prices, so the arithmetic is
   checkable even if the rule needs sourcing (TASK-002).
2. Model it as a knapsack constraint in `enumerate`: a gear selection is legal when its
   total cost is within the allowance and every item is available to the character
   (`attrs.availability`, size, and proficiency where relevant).
3. Score it in `evaluate`: add a `gear_efficiency` metric (or fold cost into `offense`
   and `durability`) so loadout quality is comparable across builds. Any new metric
   must be added to `METRICS` **and** to `config/analysis.yaml:scoring.weights` -
   `tests/test_config.py` fails otherwise, which is exactly the drift guard that caught
   the last time these two disagreed.

## Acceptance criteria

- [ ] The allowance rule is declared in `config/analysis.yaml` with `verified:` and
      evidence.
- [ ] `enumerate --gear` produces only affordable loadouts; `--check` reports 0
      violations on the level-1 sample.
- [ ] `space --gear` reports a constrained gear dimension, with the unconstrained
      figure retained for comparison.
- [ ] `evaluate` scores loadouts, and the new metric appears in `METRICS`, in
      `scoring.weights`, and in `analysis/out/builds-level1.md`.
- [ ] A test asserts an unaffordable loadout is rejected and an affordable one is not.
- [ ] GAP-011 flips to `resolved`.

## Files likely to change

`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`, `swse/evaluate.py`,
`tests/test_enumerate_evaluate.py`, `tests/test_config.py`.
