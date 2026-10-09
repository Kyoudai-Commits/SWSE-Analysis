# TASK-014 - Confirm the prestige defence encoding

**Status:** open | **Priority:** medium | **Gap:** GAP-005

## Problem

Heroic class defence bonuses are a **verified fact**: SagaForge's numeric columns
(`Data!CA:CC`) reproduce the Master Reference's printed prose exactly for all five
heroic classes (Jedi 1/1/1, Noble 1/0/2, Soldier 1/2/0, Scout 2/1/0, Scoundrel
2/0/1). `tests/test_canonical_data.py::test_defense_bonuses_match_the_printed_column`
asserts it.

Prestige classes store values on a different scale - Ace Pilot 4/2/0, Charlatan
2/0/4, Elite Trooper 2/4/0, Force Disciple 3/3/6, Droid Commander 2/2/2. Dividing by
2 recovers the printed level-1 bonus for every class spot-checked, which suggests the
column encodes a *progression rate* (bonus gained every two levels) rather than a
level-1 value. That is consistent, not confirmed: neither source contains a prestige
progression table.

`config/analysis.yaml:defense_progression.prestige` therefore carries
`divisor: 2`, `verified: false`, `task: TASK-014`, and the evaluator flags every
defence metric derived from it.

Consequence: defence scores for multiclass builds that reach a prestige class - which
is most high-level builds, including the top-ranked level-20 build - are approximate.

## Evidence

```bash
grep -n -B 4 -A 14 "defense_progression:" config/analysis.yaml
python -c "
from swse.store import Dataset; db=Dataset.load()
for c in db.all('class'):
    a=c['attrs']
    if a.get('class_kind')=='prestige':
        print(c['name'], a.get('reflex_progression'), a.get('fortitude_progression'), a.get('will_progression'))" | head -12
```

## Approach

1. Get one prestige class page (SECR/JATM/any supplement, via TASK-002 or TASK-001)
   that prints the defence bonus by level. One class is enough to test the divisor
   hypothesis: if Ace Pilot's printed bonuses are +2 Ref/+1 Fort at level 1 and grow
   every two levels, `divisor: 2` is confirmed as a *rate*, and the model should store
   the rate rather than a level-1 value.
2. Either way, replace the divisor hack with an explicit progression model:
   `defense_progression.prestige.rate_per_levels: 2` (or whatever the source says), so
   `swse.evaluate.defense` computes the bonus at the character's actual level in that
   class instead of assuming level 1.
3. Re-verify the heroic classes under the same model - if one formula explains both,
   the heroic case stops being a special case.

## Acceptance criteria

- [ ] `defense_progression.prestige.verified` is `true` with evidence naming the class
      and the printed values that confirmed it.
- [ ] The divisor is replaced by an explicit rate, and `evaluate.defense` computes
      defence at the build's level in each class rather than at level 1.
- [ ] The heroic cross-check test still passes, ideally extended to assert both kinds
      of class under one model.
- [ ] `analysis/out/builds-level20.md` is regenerated and its defence columns change;
      the digest notes which ranks moved.
- [ ] GAP-005 flips to `resolved`, and the "unverified defence" caveat disappears from
      `docs/verification.md`.

## Files likely to change

`config/analysis.yaml`, `swse/evaluate.py`, `swse/space.py`,
`tests/test_canonical_data.py`, `tests/test_enumerate_evaluate.py`.
