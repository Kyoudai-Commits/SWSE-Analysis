# TASK-007 - Encode the ability point-buy cost curve

**Status:** open | **Priority:** medium | **Gap:** GAP-003 | **Related:** TASK-012

## Problem

`swse.space` counts 16,777,216 ability allocations - the largest single dimension of
the decision space - from a point-buy model whose cost curve is **declared, not
sourced**. SagaForge has an ability grid and a "Point Buy" cell but stores no cost
table; the curve lives in the builder's VBA.

TASK-012 covers which generation *methods* exist. This task covers the arithmetic of
one method: the cost of each score, the budget, and therefore which allocations are
legal.

## Evidence

```bash
grep -n -A 12 "ability_scores:" config/analysis.yaml
python -c "
from swse.space import load_assumptions; a=load_assumptions()
print(a['ability_scores'])"
```

## Approach

1. Source the curve (SECR via TASK-002, or the builder's VBA transcribed as a
   registered source).
2. Replace the current flat count with a real constrained count: enumerate allocations
   whose total cost is within budget. At six abilities and a bounded score range this
   is small enough to count exactly rather than estimate.
3. Keep the three declared methods independent - `standard_array` is a fixed set of
   permutations, `point_buy` a budget constraint, `dice` a distribution. Each needs
   its own count and its own `verified` flag.

## Acceptance criteria

- [ ] `config/analysis.yaml` holds the curve as data (score -> cost) with `verified:`
      and an `evidence:` line.
- [ ] `space.ability_allocations` is computed from the curve, and the report shows the
      budget and the count for each method separately.
- [ ] `enumerate` rejects an over-budget allocation under `--check`; a test asserts it.
- [ ] The level-1 total space changes, and `data/reports/decision-space.md` records the
      old and new figures with the reason.
- [ ] `test_space.py`'s level-1 exactness assertion still holds against
      `iter_level1_builds`.

## Files likely to change

`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`, `tests/test_space.py`,
`tests/test_enumerate_evaluate.py`.
