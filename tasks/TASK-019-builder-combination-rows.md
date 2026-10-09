# TASK-019 - Flag the builder's combination rows

**Status:** open | **Priority:** medium | **Gap:** GAP-014

## Problem

101 of the 156 `weapon_mod` records are not game options. They are the builder's
pre-computed *combinations* of two real modifications, materialised as rows so its UI
can offer them from a dropdown: `Dreadful Rage`, then `Dreadful Rage and Power Attack
(-1)` through `(-10)`, plus further permutations.

The entity is 100% third-party, so these rows inflate the third-party tier's gear
counts and, wherever gear is counted, the decision space - one real choice appears as
dozens.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
mods=db.all('weapon_mod')
print('weapon_mod records:', len(mods))
print('dreadful_rage family:', sum(1 for m in mods if 'dreadful_rage' in m['id']))
print('power_attack family:', sum(1 for m in mods if 'power_attack' in m['id']))
print([m['name'] for m in mods if 'power_attack' in m['id']][:6])"
```

The canon-balance audit reports the family as an `artefact`, with verdicts recorded in
`data/curation/audit-verdicts.yaml`.

## Approach

1. **Flag, do not delete.** A row hook in `swse/hooks.py` marks records whose name
   matches `<mod> and <mod> (-N)` with `builder_combination`, and records the two
   component mods in `relations.combines`. Deleting them would lose the fact that the
   builder offers the combination; flagging lets every consumer decide.
2. **Exclude flagged records from counts that mean "distinct options"** - the option
   catalog, the gear dimension of the decision space, and the per-tier comparison in
   `swse/audit.py`. Report both numbers (raw and de-duplicated) so the change is
   visible.
3. **Do not change `merge_on`.** These are not duplicates of one another; each row is
   a distinct combination. Merging them would destroy the components.
4. Check whether the same pattern exists in other builder-derived entities
   (`armor_template`, `weapon_template`, `equipment_accessory`) before assuming
   `weapon_mod` is the only case.

## Acceptance criteria

- [ ] Combination rows carry `builder_combination` and name their components in
      `relations`.
- [ ] `data/reports/option-catalog.md` and the gear dimension of
      `data/reports/decision-space.md` report raw and de-duplicated counts.
- [ ] `swse/audit.py` excludes flagged records from per-tier proxies, and the report
      says so.
- [ ] A test asserts the flag is applied to the known family and *not* to a plain
      single-mod record.
- [ ] `validate` stays at 0 errors; GAP-014 flips to `resolved`.

## Files likely to change

`swse/hooks.py`, `config/entities.yaml` (row hook wiring), `swse/report.py`,
`swse/space.py`, `swse/audit.py`, `tests/test_canonical_data.py`.
