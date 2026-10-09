# Known gaps

A gap is data the model wants but neither source contains. Gaps are **declared**, in
`data/curation/gaps.yaml`, with the evidence that they are still true - so that
`swse validate` can distinguish "we know this is absent" from "we failed to extract
this", and so that no report can quietly imply more certainty than exists.

Each entry below names the impact, the workaround currently in force, and the task
that would close it.

| id | entity / field | summary | task | status |
|---|---|---|---|---|
| GAP-001 | `talent.tier` | tier within a tree absent from both sources | TASK-005 | open |
| GAP-002 | `class.progression_schedule` | per-level feat/talent grants are in neither workbook | TASK-011 | open |
| GAP-003 | `character.ability_score_generation` | no cost curve, no printed array | TASK-012 | open |
| GAP-004 | `force_power.powers_known` | how many powers a character knows is not encoded | TASK-013 | open |
| GAP-005 | `class.prestige_defense_encoding` | prestige defence values look like 2x the printed bonus | TASK-014 | open |
| GAP-006 | `weapon.damage` | Power lance damage cell holds `28` with no die size | TASK-004 | open |
| GAP-007 | multiple `.name` | 21 same-source name collisions, all genuinely distinct | TASK-003 | wont_fix |
| GAP-008 | `feat.prerequisites` | 8 fragments unresolved (droid systems, GM approval) | TASK-010 | open |
| GAP-009 | `reference_link.url_content` | 812 wiki URLs, none fetched, hosts unreachable | TASK-001 | open |
| GAP-010 | `droid_option.cost_budget` | costs exist, the budget to spend them does not | TASK-006 | open |
| GAP-011 | `character.starting_gear` | no rule ties starting credits to a gear allowance | TASK-008 | open |
| GAP-012 | `species.age_bounds` | which age categories are legal per species is absent | TASK-015 | open |
| GAP-013 | `class.homebrew_progression` | Technician / Force Prodigy have prose only | TASK-016 | open |
| GAP-014 | `weapon_mod.builder_combination_rows` | 101 of 156 weapon mods are the builder's pre-computed combinations | TASK-019 | open |

## The ones that change answers

**GAP-002 - progression schedule.** Every count above level 1 depends on how many
feats and talents a character gets per level. SagaForge's `Class` sheet is a blank
character-sheet UI grid (`Class!A6:V25` is entirely empty) and `Data!CT:CY`, the
per-level progression columns, are all zeros. The declared schedule (feat at 1st and
every odd level, talent every even level) is standard Saga Edition, but it is not
*sourced here*. Consequence: level-20 figures are orders of magnitude, not counts.

**GAP-003 - ability scores.** The largest single dimension (16,777,216 allocations
for a point-buy model) rests on a method the sources do not specify. SagaForge has an
ability grid and a Point Buy cell but no cost curve. Three methods are declared in
`config/analysis.yaml`, all `verified: false`, and every report labels the number it
produces.

**GAP-001 - talent tier.** `Talents!E-I` in the Master Reference is a *visual layout
grid*; a talent's column says where it was printed, not what rank it is. SagaForge's
tier-like columns are empty in v1.53. Consequence: the enumerator treats every
talent in a granted tree as available, which over-counts high-tier talents at low
levels. `layout_column` is preserved so a future source can fill this in without
re-extraction.

**GAP-005 - prestige defence.** Heroic defence values cross-verify exactly against
the printed column. Prestige values do not: they are roughly double. Dividing by 2
recovers the printed level-1 bonus for every class spot-checked, which is consistent
but not confirmed. Consequence: defence metrics for multiclass builds that reach a
prestige class are approximate, and the evaluator flags them.

## The ones that are contained

**GAP-006 - Power lance.** One weapon, one cell: the multiplier column holds `28`
with no die size, where the printed book says 2d8. The hook records
`{"flat": 28, "suspected_dice": "2d8"}`, sets the flag
`damage_suspected_concatenation`, notes the gap, and **does not rewrite the value**.
Silently "fixing" source data is how a dataset stops being evidence.

Related and correctly modelled rather than treated as errors: unarmed-style weapons
(unarmed strike, combat gloves, vibroknucklers, stunning gauntlet) genuinely store
*flat* damage in the multiplier column, and the targeting laser genuinely has
`special` damage. `swse/hooks.py::weapon_stats` emits three explicit shapes -
`{multiplier, die_size, bonus}`, `{flat, bonus}`, `{special}` - and
`Evaluator.damage_value` understands all three.

**GAP-007 - name collisions.** 21 records share a name with another record from the
same source. All were inspected: three feats called "Staggering Attack" are different
feats, three "Force Storm" powers are different powers, three "Replica droid" entries
are different chassis sizes, two "Scent" traits belong to different species groups.
They are kept separate with a disambiguated id and the `name_collision` flag. The
early attempt to merge same-source duplicates by name destroyed real options; that is
why the rule is "merge across sources only".

**GAP-008 - unresolved prerequisites.** 8 fragments, 1.45% of parsed prerequisite
text: `Heuristic Processor`, `Basic Processor`, `Shield Generator System`,
`Cyborg Hybrid with Subcutaneous Comlink`, `larger Droid with 2+ Appendages`,
`larger Droid with 2+ Tool Mounts`, `or Tracked Locomotion`, `"Gamemaster's
Approval"`. The first five need a `droid_system` entity that no block currently
extracts; the last is a rule, not an option, and should become a `gm_approval`
predicate type. Until then those gates are ignored in legality checks, which can only
make the model permissive.

**GAP-009 - wiki content.** The Master Reference embeds 812 URLs to
`swse.miraheze.org` and `swse.fandom.com`. The analysis sandbox has outbound access
to github/pypi/npm only, so none were fetched and nothing in this repository is
copied from either site. The URLs are attached to the records they describe
(`attrs.url`) so a future ingest can join on them; `config/sources.yaml` lists both
wikis under `planned_sources`.

**GAP-014 - builder combination rows.** 101 of the 156 `weapon_mod` records are not
distinct game options: they are the builder's pre-computed *combinations* of two real
modifications ("Dreadful Rage", then "Dreadful Rage and Power Attack (-1)" through
"(-10)"), materialised as rows so the builder's UI can offer them from a list. The
entity is entirely third-party, so the rows inflate that tier's gear counts and, wherever
gear is counted, the decision space. Found by the canon-balance audit, which reports the
family as an `artefact` with verdicts in `data/curation/audit-verdicts.yaml`. Gear is
excluded from the headline space figures by default, so nothing quoted in `README.md` is
affected. TASK-019 flags them `builder_combination` rather than deleting them - the fact
that the builder offers the combination is itself information.

**GAP-010 - droid budgets.** Droid options carry cost and weight, but the allowance
a droid character gets to spend is computed in the builder's VBA, not stored in a
cell. Consequence: the droid sub-space is counted, not budgeted.

**GAP-011 - starting gear.** Starting credits are present per class, but nothing ties
them to a purchasable allowance. Gear is therefore excluded from the decision space
by default and multiplied in only with `--gear`.

**GAP-012 - age bounds.** The age table gives ability modifiers for six categories,
but no species row says which categories that species may take. The age dimension is
counted as 6 options for every species and flagged as ungated.

**GAP-013 - homebrew progression.** Technician and Force Prodigy exist only in the
Master Reference's homebrew section, as prose: no hit die, no BAB rate, no defence
numbers. Builds using them score 0 for those contributions and the evaluator warns.
`--no-homebrew` excludes them.

## Closing a gap

1. Get the data - a new block in `config/blocks.yaml`, a new source in
   `config/sources.yaml` (see [`adding-sources.md`](adding-sources.md)), or a
   judgement call recorded in `data/curation/overrides.yaml`.
2. `make data`, then confirm `validate` is still 0 errors and the coverage/parse
   numbers moved.
3. Flip the gap's `status` to `resolved`, and if an assumption in
   `config/analysis.yaml` depended on it, set `verified: true` and record the
   evidence.
4. Add a test that would fail if the gap reopened.
5. Regenerate the reports; the numbers quoted in `README.md` and
   `docs/decision-space.md` may change.
