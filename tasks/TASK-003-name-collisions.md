# TASK-003 - Triage the 21 same-source name collisions

**Status:** wont_fix (declared) | **Priority:** low | **Gap:** GAP-007

## Problem

21 records share a name with another record from the *same* source. They are kept
separate with disambiguated ids and the `name_collision` flag, which is the only
warning `swse validate` currently reports.

Every one was inspected and is a genuinely distinct option:

| name | n | why they differ |
|---|---:|---|
| feat `Staggering Attack` | 3 | three different feats in three different books |
| force_power `Force Storm` | 3 | power, technique-scale variant, and a suite entry |
| species `Replica droid` | 3 | three chassis sizes |
| racial_ability `Pack Hunter`, `Physically Intimidating`, `Scent` | 2 each | granted by different species groups |
| weapon `Shockboxing gloves` | 2 | standard and modified versions |
| weapon_mod `Inquisition`, `Double Attack` | 2 each | different weapon groups |

## Why this is filed anyway

The status is `wont_fix` because merging them would destroy real options - an early
attempt to merge same-source duplicates by name did exactly that. But the
disambiguation is currently *positional* (id suffix from the source row), which means
a re-extraction after an upstream row insert could renumber ids. That is the actual
risk this task tracks.

## Evidence

```bash
python -m swse.cli validate --show 5     # the name_collision warning
grep -c "collision" data/reports/canonicalisation.md
```

## Acceptance criteria (if picked up)

- [ ] Each colliding group gets a **stable** disambiguator derived from content
      (weapon group, tree, chassis size, sourcebook page) rather than row position.
- [ ] Ids survive a re-extraction with rows inserted above them - assert with a test
      that shuffles raw row order and checks ids are unchanged.
- [ ] `data/curation/aliases.yaml` records any pair a human confirms *is* the same
      option, so the merge is explicit and auditable.
- [ ] The warning text names the disambiguator used, so a reader can tell two
      "Staggering Attack" feats apart without opening the JSON.

## Files likely to change

`swse/canon.py` (`_disambiguator`), `data/curation/aliases.yaml`,
`tests/test_canonical_data.py`.
