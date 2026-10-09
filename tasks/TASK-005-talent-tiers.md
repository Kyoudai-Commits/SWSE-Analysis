# TASK-005 - Model talent tier within a tree

**Status:** open | **Priority:** high | **Gap:** GAP-001

## Problem

A talent's *tier* - which rank inside its tree it sits at - is absent from both
sources. The Master Reference's `Talents!E-I` columns are a visual layout grid (where
a talent was printed), not tier columns; SagaForge's tier-like columns are empty in
v1.53. So `talent.attrs.layout_column` is preserved but unused.

Consequence: `swse.space` and `swse.enumerate` treat every talent in a granted tree
as selectable at any level. That over-counts high-tier talents for low-level
characters, which inflates both the level-1 feat/talent dimension and every
above-level-1 count, and it makes `evaluate` unable to reward deep tree investment.

Talent is the largest entity in the corpus (1,311 records across 192 trees), so this
is the single biggest fidelity gap after the progression schedule (TASK-011).

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
ts=db.all('talent')
print('talents', len(ts))
print('trees', len({t['attrs'].get('tree') for t in ts}))
print('with layout_column', sum(1 for t in ts if t['attrs'].get('layout_column')))"
python -c "
from swse.sources import load_registry, workbook
print(workbook(load_registry()['master-reference']).sheetnames)"
```

## Approach

Tiers need a source that lists them. Options, in order of preference:

1. The Core Rulebook and supplement talent trees (TASK-002) - authoritative.
2. A wiki snapshot (TASK-001) - the miraheze tree pages render tiers as rows.
3. **Inference as a stopgap, clearly labelled.** Column position in `Talents!E-I`
   correlates with tier for trees printed in a grid. If used, it must be stored as
   `attrs.tier_inferred: true` with `attrs.tier_basis: layout_column`, flagged, and
   excluded from any `verified` claim. Inference must never overwrite a sourced tier.

## Acceptance criteria

- [ ] `talent.attrs.tier` is populated for every talent in a tree that has a sourced
      tier, and coverage is reported by `validate`.
- [ ] Inferred tiers, if any, are distinguishable from sourced ones by a flag and a
      basis field, and `swse.space` reports them separately.
- [ ] `enumerate` gates talent selection by tier and level; `--check` still reports 0
      violations on the level-1 and level-10 samples.
- [ ] The level-1 talent dimension in `data/reports/decision-space.md` drops, and the
      report explains why.
- [ ] A test asserts a known tree's tier ordering (pick one tree with a printed
      layout) and fails if tiers regress to "all available".
- [ ] GAP-001 flips to `resolved`.

## Files likely to change

`config/entities.yaml` (keep `tier`), `swse/hooks.py` (a tier hook),
`swse/space.py`, `swse/enumerate.py`, `tests/test_canonical_data.py`,
`tests/test_space.py`.
