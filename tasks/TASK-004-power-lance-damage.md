# TASK-004 - Confirm the Power lance damage cell

**Status:** open | **Priority:** low | **Gap:** GAP-006

## Problem

One weapon record holds damage as `28` with no die size:

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
r=db.get('weapon','weapon_power_lance'); print(r['attrs']['damage'], r['flags'])"
```

The printed *Rebellion Era Campaign Guide* lists the power lance as 2d8. The most
likely explanation is that `2d8` was typed into SagaForge's multiplier column and the
die column was left blank, so the extractor read `mult1: 28, die1: null`.

The pipeline **does not rewrite it**. `swse/hooks.py::weapon_stats` records
`{"flat": 28, "suspected_dice": "2d8"}`, sets the flag
`damage_suspected_concatenation`, notes the gap, and bumps
`ctx.stats["damage_suspected_concatenation"]`. `Evaluator.damage_value` therefore
scores it as 28 flat damage - wrong, but visibly wrong rather than silently
corrected.

## Why it matters beyond one weapon

Unarmed-style weapons (unarmed strike, combat gloves, vibroknucklers, stunning
gauntlet) legitimately store *flat* damage in the same multiplier column, and the
targeting laser legitimately stores `special`. So the column is overloaded three
ways, and the only safe handling is to model all three shapes explicitly and flag the
ambiguous case. `test_flat_damage_weapons_are_modelled_as_flat` and
`test_suspected_concatenated_damage_is_flagged_not_rewritten` pin that behaviour.

## Acceptance criteria

- [ ] The printed value is confirmed against RECG (or a wiki snapshot from TASK-001).
- [ ] The correction goes in `data/curation/overrides.yaml` as
      `weapon:weapon_power_lance -> attrs.damage: [{multiplier: 2, die_size: 8}]`,
      with the source of the correction named in the override's `note`.
- [ ] After `make data`, the flag and the `suspected_dice` key are gone from that
      record and `damage_suspected_concatenation` in
      `data/reports/canonicalisation.md` drops to 0.
- [ ] The two damage tests still pass - they assert the *mechanism*, not this record.
- [ ] GAP-006 flips to `resolved`.

## Files likely to change

`data/curation/overrides.yaml`, `data/curation/gaps.yaml`. No code change expected;
if one is needed, the mechanism belongs in `swse/hooks.py`, not in a special case.
