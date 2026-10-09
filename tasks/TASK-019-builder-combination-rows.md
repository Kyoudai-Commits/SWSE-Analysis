# TASK-019 - Flag the builder's combination rows

**Status:** resolved (2026-10-09) | **Priority:** medium | **Gap:** GAP-014

## Outcome

The `flag_builder_combinations` post hook (`swse/hooks.py`, registered in
`config/entities.yaml`) now marks the artefacts instead of leaving counts to guess:

- **72** rows carry `builder_combination`, with `relations.combines` naming the real
  options and `attrs.combination_of` their source-book names. A component may resolve
  outside the entity: `Dreadful Rage and Power Attack (-1)` combines
  `weapon_mod_dreadful_rage` with `feat_power_attack`, because there is no bare
  `Power Attack` modification row.
- **101** carry `builder_parameter_variant`, with `attrs.parameter_base` and
  `attrs.parameter_value`; 7 bases have more than one variant, covering 105 rows.
- **43** of the 156 remain distinct options. Nothing was deleted or merged and every row
  keeps its cell citation.

The counts changed shape as a result. The audit's `weapon_mod` proxies are now computed
over distinct options only (`swse.audit.distinct_options`), and the top `attack_mod`
outlier moved from a builder combination to `weapon_mod_powerful_charge` (+4 attack on a
charge, `single: Yes`) - verdict recorded in `data/curation/audit-verdicts.yaml`.
`report.option_catalog` prints `records` and `distinct options` side by side with a
footnote, so the corpus size and the choice size are no longer the same number.

**The scoping is the finding.** An entity-agnostic first run flagged 19 more rows across
`armor`, `weapon`, `equipment` and `armor_accessory`, and all 19 were false positives:
"Battle armor, heavy", "Blaster pistol, snap shot" and "Datapad, basic" are
item-plus-qualifier *names*, and they only look like combinations because the corpus holds
reference records called "heavy", "basic" and "miniaturized" (`armor_size`, `availability`).
`racial_ability`'s "Fly Speed (6)" / "(8)" are different species grants, not one ability on
a dial. So the hook applies to `BUILDER_ARTEFACT_ENTITIES = ("weapon_mod",)` and the
docstring records what was inspected and why the others are excluded; extending the tuple
means redoing that inspection. Pinned by
`test_item_plus_qualifier_names_are_not_builder_artefacts` and
`test_no_entity_outside_the_inspected_list_is_flagged`.

The headline decision-space figures never moved: the gear dimension is opt-in and counts
only weapons x armor x equipment.

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
