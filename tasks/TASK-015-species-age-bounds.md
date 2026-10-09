# TASK-015 - Gate age categories per species

**Status:** open | **Priority:** low | **Gap:** GAP-012

## Problem

The corpus has an `age_table` entity with six `age_category` records carrying ability
modifiers, and 130 species. What no source states is which categories a given species
may take. `swse.space` therefore counts the age dimension as 6 options for every
species and flags it as ungated.

That is wrong in both directions for some species: a droid has no age category at
all, and long-lived species (Gen'Dai, for instance - the top-ranked level-10 build)
cannot plausibly be "old" in the human sense at level 1. The dimension is small
compared with skills or ability scores, so the impact on headline numbers is modest,
but it produces illegal builds in samples.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
print('age categories:', [a['name'] for a in db.all('age_category')])
print('species with age attrs:', sum(1 for s in db.all('species')
      if any('age' in k for k in s['attrs'])), 'of', len(db.all('species')))"
python -m swse.cli space --level 1 --json | jq '.dimensions[] | select(.name|test("age"))'
```

## Approach

1. Source the rule (SECR species chapter, via TASK-002). Some species entries in the
   Master Reference carry lifespan prose; if so, that is a partial source already -
   check `species.attrs` for lifespan text before assuming it is absent.
2. Model it as a per-species allowlist: `species.attrs.age_categories: [...]`, defaulting
   to all six where a species has no stated bounds, with `attrs.age_gating: sourced |
   assumed` so the two cases stay distinguishable.
3. Enforce it in `enumerate.check_build` and reflect it in `space`'s age dimension,
   which becomes a per-species count rather than a flat 6.
4. Exclude droids and other ageless types explicitly - that is a real rule, not a guess.

## Acceptance criteria

- [ ] Species carry an age allowlist with a basis field, and coverage is reported by
      `validate`.
- [ ] `space`'s age dimension is computed per species; `data/reports/decision-space.md`
      shows the constrained count and how many species are ungated-by-assumption.
- [ ] `enumerate --check` rejects a droid build with an age category; a test asserts it.
- [ ] The level-1 sample re-runs with 0 violations.
- [ ] GAP-012 flips to `resolved`, or is narrowed to exactly the species still ungated.

## Files likely to change

`config/entities.yaml`, `swse/hooks.py`, `swse/space.py`, `swse/enumerate.py`,
`tests/test_canonical_data.py`, `tests/test_enumerate_evaluate.py`.
