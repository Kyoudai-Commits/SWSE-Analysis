# TASK-020 - Targeted tier comparisons with real statistical power

**Status:** resolved (2026-10-09) | **Priority:** medium | **Follow-up from:** TASK-018

## Outcome

`analysis/out/canon-balance.md` gained a **Targeted slot comparisons** section and a
**Sourcebook control** subsection, driven by `swse.audit.SLOT_COMPARISONS`. Four of the
seven declared slots had enough overlap to test, and none differs at p < 0.01:

| decision slot | measure | n official / 3rd | median official / 3rd | p |
|---|---|---|---|---|
| Talent tree | `talents_per_tree` | 151 / 25 | 5 / 5 | 0.473 |
| Species | `ability_bonus` | 109 / 9 | 2 / 2 | 0.945 |
| Species | `ability_penalty` | 105 / 9 | 2 / 2 | 0.958 |
| Equipment | `price` | 171 / 36 | 400 / 200 | 0.256 |
| Weapon | `avg_damage` | 215 / 5 | 9 / 13.5 | n too small |
| Weapon | `price` | 228 / 6 | 800 / 1600 | n too small |
| Armor | `armor_bonus` | 86 / 4 | 8 / 9 | n too small |

The three untestable slots are printed with their sample sizes rather than dropped, so a
reader can see that the corpus cannot speak about weapons or armour at all.

**The sourcebook control is the part that changed the interpretation.**

- Talent trees cite *no* sourcebook in either tier (they are derived from talent rows), so
  that slot has no control available and the report says so. The first implementation
  claimed a one-sided confound there - "the official side spans 1 sourcebooks" - because
  the `(uncited)` placeholder counted as a book. `test_sourcebook_control_does_not_invent_a_confound`
  caught it; `UNCITED` is now excluded from the book sets.
- Species: the entire third-party side is `WEB` (webpage-only citation) against 12
  sourcebooks on the official side. A difference there would be evidence about that one
  source's house style, not about third-party content in general.
- Gear carries a nuance the verdicts now record: weapons and equipment are extracted from
  the SagaForge builder sheets whatever their tier, so `official` means "the row cites a
  sourcebook" and `third_party` means "it cites none". A price difference between the
  tiers would be a difference between *cited and uncited* gear, not between publishers.

**Everything the new comparisons surfaced was hand-inspected against the raw cell**, not
just against the canonical record: 16 new outliers, all verdict `real`, taking
`data/curation/audit-verdicts.yaml` to 60 entries. Two are worth remembering:

- `talent_tree_superior_skills_talent_tree` holds **127** talents, six times any other
  tree, because it is roughly seven talent families (`Assured Skill`, `Skill Confidence`,
  `Skillful Recovery`, ...) crossed with the 18-skill list. Not an artefact - but it is
  why the slot table reports medians and IQR: one parameterised tree would otherwise drag
  the official mean up and manufacture a tier difference out of a naming convention.
- `weapon_verpine_shatter_gun` is the only outlier where price and damage move together
  (15,000 credits, 3d10), and that matches the printed weapon.

**Conclusion the report now states:** the four tested slots are the strongest support the
corpus offers for quoting mixed-canon rankings, and it is still absence of evidence rather
than proof of balance, because the slots that could not be tested are the ones a player
touches most often in combat. Combined with TASK-018's build-level result (level 1
p=0.495, level 10 p=0.562) there is no evidence of third-party inflation anywhere the
corpus can measure - and the standing caveat about the unscoreable homebrew classes
(GAP-013) is unchanged.

Also in this pass: p-values print to three decimals via `swse.audit._p`. `_fmt`'s `%g`
gave `p=0.47282`, which implies a precision a 25-record sample cannot support.

## Problem

The canon-balance audit answers "does third-party content inflate build rankings?"
with a build-level comparison, and the answer is *no evidence that it does*
(level 1: medians 45.2 official vs 46.0 third-party, p=0.50; level 10: 112.35 vs
112.95, p=0.56). But the comparison is weak by construction: random builds rarely
pick third-party options, so the third-party group is only 22-24 builds per level.

Record-level comparison is worse - canon tier and entity type nearly coincide, so
18 of 20 power proxies could not be compared at all (one tier had fewer than 8
records).

The comparisons that *would* have power are the ones nobody has run: within a single
decision slot, compare the tiers directly.

## Where the power is

| comparison | official n | third-party n | why it matters |
|---|---:|---:|---|
| talent trees (grants per tree) | 167 | 25 | the 25 SagaForge-only trees are the largest block of builder-only *character* content |
| talents inside those trees | 1,307 | 4 | lopsided - but the trees themselves can be compared by size and by bonus density |
| species | 121 | 9 | species is a level-1 decision every build makes |
| equipment | 184 | 42 | the only entity with real overlap in both tiers |
| weapons | 239 | 7 | small overlap, but damage is exactly comparable |
| armour | 88 | 4 | too small; report, do not test |

## Evidence

```bash
python -m swse.cli audit --top 4 --json          # the current audit and its sample sizes
sed -n '/## Composition/,/## Power proxies/p' analysis/out/canon-balance.md
```

## Approach

1. **Compare like with like inside a decision slot.** For talent trees: options granted
   per tree, talents per tree, and mean bonus density per talent. For species: total
   positive ability modifiers, penalties, and racial ability counts. For equipment and
   weapons: price against the numeric effect, since price is the game's own balance
   signal.
2. **Control for the confounder.** Third-party content is concentrated in specific
   supplements; if all 25 builder-only trees come from one book, the comparison is
   really "that book versus everything else". Report the sourcebook breakdown
   alongside the tier breakdown.
3. **Keep the rank-sum, name its limits.** `swse/audit.py:mann_whitney_u` already does
   tie- and continuity-corrected normal approximation; reuse it, and keep the
   `MIN_COMPARABLE_N` guard so a p-value is never quoted from a handful of records.
4. **Publish as an extension of the existing report**, not a new one - the audit's
   value is that record-level and build-level evidence sit next to each other.

## Acceptance criteria

- [ ] The audit gains a per-slot comparison for talent trees, species, equipment and
      weapons, each with n per tier, medians, IQR and a p-value only where
      `MIN_COMPARABLE_N` is met.
- [ ] Sourcebook breakdown is reported next to the tier breakdown for any comparison
      that differs.
- [ ] Every outlier in a differing comparison gets a verdict in
      `data/curation/audit-verdicts.yaml`, or is filed as a gap.
- [ ] The conclusion states plainly whether mixed-canon rankings are safe to quote, and
      the statement is supported by a comparison with at least 8 records per tier.
- [ ] A test asserts the new comparisons run on the real corpus and that no p-value is
      reported below `MIN_COMPARABLE_N`.

## Files likely to change

`swse/audit.py`, `tests/test_audit.py`, `analysis/out/canon-balance.md` (regenerated).
