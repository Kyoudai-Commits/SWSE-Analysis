# The decision space

`swse space` counts how many choices a character creator actually makes. It reports
the space **dimension by dimension** rather than as one opaque product, because the
interesting question is usually "which dimension dominates?" and "which of these
numbers is verified?".

Regenerate: `python -m swse.cli space --level 20` -> `data/reports/decision-space.md`.

## Headline numbers

| scope | level 1 core builds | total space | class paths |
|---|---:|---|---:|
| all canon | 580,200,130 | **10^19.6** | 7 heroic starts |
| all canon, level 20 | - | **10^164.95** | 2,533,086,352,502,117,155,404,251,136 |
| official only, level 20 | 18,268,714 | **10^138.07** | 1,913,000,000,000,000,000,000,000,000 (1.913e26) |

"Core builds" is the combinatorial count of *option* choices (species x class x
skills x feats x parameter axes) - the part the dataset can enumerate exactly.
"Total space" multiplies in the dimensions the sources do not pin down (ability
scores, destiny, background, age) and is therefore an assumption-dependent figure.
Every report prints the assumptions it used.

## The 17 dimensions

| dimension | count | verified? | notes |
|---|---:|---|---|
| `species` | 130 | yes | includes droid chassis, beasts, near-humans |
| `class` | 7 heroic / 41 total | yes | `class_paths` is the multiclass sequence, counted separately |
| `class_paths` | 7 (L1) -> 2.53e27 (L20) | no | needs the per-level progression schedule (GAP-002) |
| `species_class_pairs` | 910 | yes | species that can take each class |
| `skill_selections` | 4,743,620 | yes | class skill lists x trained-skill allowance |
| `feat_choices` | 163 available of 387 at L1 | yes | gated by prerequisites and class grants |
| `parameter_multiplier` | 3,488,400 | yes | the parameterised-feat axes |
| `talent_trees` / `talents` | 192 / 1,311 | partial | tier unknown (GAP-001) |
| `force_power` | 92 | partial | powers-known allowance absent (GAP-004) |
| `ability_allocations` | 16,777,216 | no | method is an assumption (GAP-003) |
| `age_category` | 6 | no | not gated per species (GAP-012) |
| `destiny` | 88 | yes | |
| `background` | 46 | yes | |
| `language` | 102 | yes | gated by Linguist / species |
| `gear` (weapons/armor/equipment) | opt-in | yes | excluded by default; `--gear` multiplies it in |
| `droid_options` | 121 | partial | no cost budget in the sources (GAP-010) |
| `vehicle/starship options` | counted, not gated | partial | a separate decision space (TASK-009) |

The level-1 detail behind 580,200,130: 910 species-class pairs, 4,743,620 skill
selections, 163 of 387 feats available, a 3,488,400 parameter multiplier,
16,777,216 ability allocations, 88 destinies, 46 backgrounds.

## Method

Two counting modes:

- **Level 1: exact.** The space is small enough to enumerate combinatorially.
  `iter_level1_builds` walks it for real; `enumerate --level 1 --limit 4000 --check`
  produced **1,691,028,090,892,800** legal level-1 builds with **0 violations** in
  0.4s. This is the ground truth the analytic model is checked against.
- **Levels 2-20: analytic.** Exact enumeration is impossible (10^165). The model
  counts per-level choices using the mean number of skill picks per class and the
  progression schedule declared in `config/analysis.yaml`, then raises it to the
  number of levels. `method` in the report says which mode was used.

Because the level-20 figure rests on an **unverified** progression schedule, it is
reported as an order of magnitude (`10^164.95`), not as a precise integer. That is
deliberate: the honest statement is "the space is astronomically larger than the
level-1 space", not a false-precision count.

## Assumptions

All assumptions live in `config/analysis.yaml` with three fields: `verified`,
`note` (what it is and why), and `task` (what would confirm it). Reports print the
unverified ones next to the numbers they affect. The load-bearing ones:

| assumption | value | verified | task |
|---|---|---|---|
| heroic feat/talent progression | feat at 1st and every odd level, talent every even | **no** | TASK-011 |
| prestige defence encoding | printed values are 2x the level-1 bonus | **no** | TASK-014 |
| ability score methods | standard array / point buy / 4d6 drop lowest | **no** | TASK-012 |
| force powers known | 1 + CHA mod | **no** | TASK-013 |
| level-1 hit points | 3 x hit die + CON mod | yes (both sources agree) | - |
| later-level hit points | hit die + CON mod | yes | - |
| damage threshold | 10 + CON mod | yes | - |
| starting credits | per class | yes | - |

The verified ones come from cross-source agreement; see
[`verification.md`](verification.md).

## Excluding content

`space` and `enumerate` both accept `--canon official|third_party|homebrew`,
`--no-homebrew` and `--gear`. The canon filter is **citation-based**: a record is
official if it cites a published sourcebook or comes from a block declared official,
not merely because SagaForge carried it. Filtering on the carrier file instead was a
bug that made `--canon official` return `10^0`.

## Sampling

`enumerate --level N --sample K --seed S` draws K builds uniformly at random and
runs `check_build` on each. Level 10 and level 20 samples of 300 both produced **0
violations** at seed 20261008. Sampling is the only tractable way to sanity-check
level-20 legality, so the seed is always recorded in the output.

One subtlety: class grants must be filtered through `feat_available` *after* skills
are chosen, or the sampler produces builds that take a feat the character is not
allowed. That bug is pinned by a test.
