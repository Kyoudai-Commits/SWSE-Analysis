# TASK-009 - Starship and vehicle decision space

**Status:** open | **Priority:** low

## Problem

The corpus contains a complete second decision space that `swse.space` counts but does
not model: `starship_base`, `starship_class`, `starship_weapon`, `starship_maneuver`,
`shield_template`, `vehicle_type`, `vehicle_weapon`, `mine`, `grenade_launcher` and
`explosive`. These are extracted, canonical and validated, but no report answers
"how many different ships can a character field?" - because ships are gated by
*character* options (feats, class features, skill ranks, licences) that the current
graph does not connect to them.

Also relevant: `mine` and `vehicle_weapon` records have empty `weapon_group`, so they
are deliberately excluded from `Evaluator.offense`. That exclusion is correct for
character combat but means vehicle-scale offense is unscored entirely.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
for e in ('starship_base','starship_class','starship_weapon','starship_maneuver',
          'shield_template','vehicle_type','vehicle_weapon','mine','explosive'):
    print(e, len(db.all(e)))"
grep -n "vehicle\|starship" swse/evaluate.py | head
```

## Approach

1. Decide the unit of analysis. A ship is not a character option; it is a *platform*
   with its own slots (weapons, defenses, maneuvers, modifications) and a crew
   requirement. Model it as a separate `DecisionSpace` subclass or a second dimension
   set behind a `--scope vehicle` flag, rather than forcing it into the character space.
2. Connect the gates: `starship_maneuver` and `shield_template` prerequisites already
   parse through `swse/prereq.py`; the missing link is which character options grant
   permission to *use* a platform (pilot skill ranks, Vehicle/Starship class features,
   licences).
3. Extend `evaluate` with vehicle-scale metrics only if a build-level question needs
   them; otherwise publish a separate ranking in `analysis/out/`.

## Acceptance criteria

- [ ] A `--scope vehicle` (or equivalent) space report lists every vehicle dimension
      with counts and gating, and states which gates are unsourced.
- [ ] Platform builds are enumerable and legality-checkable, with 0 violations on a
      sample.
- [ ] A report in `analysis/out/` ranks platforms, with its assumptions printed.
- [ ] `Evaluator.offense` still excludes vehicle weapons for character builds - a test
      asserts the exclusion is intentional, not accidental.
- [ ] Any new assumption is declared in `config/analysis.yaml`.

## Files likely to change

`swse/space.py`, `swse/enumerate.py`, `swse/evaluate.py`, `swse/report.py`,
`swse/cli.py`, `tests/test_space.py`.
