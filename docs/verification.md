# Verification - what is checked against what

The dataset's credibility rests on one property: **where two independent sources
overlap, they agree, and the agreement is asserted by a test.** Where they do not
overlap, the value is flagged as an assumption instead of being presented as fact.

## Cross-source agreement (verified facts)

Both workbooks describe the five heroic classes. They encode defence bonuses in
completely different ways - SagaForge as numbers in hidden columns, the Master
Reference as printed prose - so agreement is meaningful evidence.

| class | SagaForge `Data!CA:CC` | Master Reference printed text | match |
|---|---|---|---|
| Jedi | 1 / 1 / 1 | +1 Ref, +1 Fort, +1 Will | yes |
| Noble | 1 / 0 / 2 | +1 Ref, +0 Fort, +2 Will | yes |
| Soldier | 1 / 2 / 0 | +1 Ref, +2 Fort, +0 Will | yes |
| Scout | 2 / 1 / 0 | +2 Ref, +1 Fort, +0 Will | yes |
| Scoundrel | 2 / 0 / 1 | +2 Ref, +0 Fort, +1 Will | yes |

Asserted by `tests/test_canonical_data.py::test_defense_bonuses_match_the_printed_column`.

Prestige classes show a consistent pattern (Ace Pilot 4/2/0, Charlatan 2/0/4,
Elite Trooper 2/4/0, Force Disciple 3/3/6, Droid Commander 2/2/2) - all even or
half-integer when divided by 2, matching the printed level-1 bonuses for the classes
checked. That is *consistent*, not *confirmed*, so it is an assumption with a
divisor of 2 and a task (TASK-014, GAP-005).

Other verified rules:

| rule | value | evidence |
|---|---|---|
| level-1 hit points | 3 x hit die + CON mod | both sources |
| later-level hit points | hit die + CON mod | both sources |
| damage threshold | 10 + CON mod | both sources |
| starting credits | per class | both sources |
| class skill lists | 73 resolved | SagaForge numeric + MR prose |
| class-to-talent-tree | MR AVAILABILITY column | the only authoritative mapping |

## Attribute coverage

How much of the model is actually populated, from `swse validate`:

| attribute | coverage |
|---|---|
| `species.size`, `species.speed` | 100% |
| `class.class_kind` | 100% |
| `talent.tree` | 100% |
| `weapon.weapon_group` | 95% (233/246) |
| `armor.type` | 98% (90/92) |
| prerequisite parse coverage | 98.55% (545/553) |

Low coverage is reported as an info-level finding, not hidden. `mines` and `vehicle
weapons` legitimately have no `weapon_group` and are excluded from offense scoring
rather than counted as missing.

## Structural checks (`swse validate`)

Errors block the pipeline; warnings and infos are reported and must be triaged.

**Errors** - any of these fails the build:

- source file missing or sha256 mismatch (`config/sources.yaml`)
- canonical `index.json` disagreeing with the files on disk (count or sha256)
- a record failing `schemas/record.schema.json`
- duplicate ids, or an id that does not match `<entity>_<slug>`
- a record with no `sources` entry (nothing unsourced may exist)
- a prerequisite edge pointing at a non-existent id (dangling)
- a cycle in the prerequisite graph
- a curation entry naming a record that does not exist
- a config reference to a block, entity, hook or metric that does not exist

**Warnings**: `name_collision` (21 - deliberate, GAP-007).

**Infos** (16): attribute coverage below 100%, unresolved prerequisite fragments,
unresolved source tags (4), duplicate rows collapsed (109), rows dropped (55).

Current status: **0 errors, 1 warning, 16 infos**.

## Graph invariants

`swse graph` asserts the prerequisite graph is usable:

- 680 edges, 628 resolved, **0 dangling**, **0 cycles**
- 402 nodes, maximum depth 3
- deepest chain: `Assassin <- Sniper <- Precise Shot <- Point-Blank Shot`

A cycle would mean an option requires itself; a dangling edge would mean the
enumerator could not decide legality. Both are errors.

## Enumeration as a check on the model

The strongest verification available is that the enumerator's own legality checker
agrees with the space model:

| check | result |
|---|---|
| level 1, exact, `--limit 4000 --check` | 1,691,028,090,892,800 builds, **0 violations**, 0.4s |
| level 10, sample 300, seed 20261008 | **0 violations**, 12.2s |
| level 20, sample 300 | **0 violations** |

"0 violations" means no generated build broke a prerequisite, a class skill limit, a
BAB gate or an ability score gate. It does **not** mean the space is complete -
missing data (talent tiers, progression schedule) can only make the model
permissive, never illegal.

## Regression tests

`make test` runs the full suite across 10 modules (`pytest --collect-only -q` prints
the current count). Several tests exist specifically to pin down a bug that was
already fixed once:

| test | what it protects |
|---|---|
| `test_defense_bonuses_match_the_printed_column` | cross-source defence agreement |
| `test_flat_damage_weapons_are_modelled_as_flat` | unarmed-style weapons store flat damage in the multiplier column |
| `test_suspected_concatenated_damage_is_flagged_not_rewritten` | `28` stays `28` + a flag; never silently becomes `2d8` |
| `test_config.py` metric/hook coverage | `scoring.weights` keys must match `evaluate.METRICS`; every registered hook must be referenced |
| `test_prereq.py` labelled/unlabelled cases | the label and bracket splitting rules |
| `test_space.py` level-1 exactness | the analytic model matches exact enumeration at level 1 |
| `test_docs_and_tasks.py` reference checks | every `TASK-nnn` in config/curation has a file, every `GAP-nnn` is documented, every relative link in the prose resolves, and every count quoted in the README's dataset tables is a real corpus count |
| `test_determinism.py` hash-seed stability | reports are byte-identical under two `PYTHONHASHSEED` values - no set is sliced before being sorted |
| `test_take_n_and_natural_n_are_not_bonuses` | "take 20 on a check" and "roll a natural 20 on an attack roll" are rules text, not +20 bonuses; the second one used to be added to `offense` |
| `test_audit_never_quotes_a_p_value_from_a_tiny_group` | a comparison with fewer than `MIN_COMPARABLE_N` records per tier reports "insufficient overlap", never a p-value |
| `test_homebrew_classes_really_are_unscoreable` | the audit's claim about GAP-013 stays true; if those classes gain progression numbers the test fails and the audit text must be updated |
| `test_verdicts_cover_the_outliers_the_report_shows` | every outlier the audit prints has been hand-inspected and has a verdict in `data/curation/audit-verdicts.yaml` |
| `test_no_slot_quotes_a_p_value_below_min_comparable_n` | a decision-slot comparison with too few records prints "n too small" and no p-value; one with enough records may not be refused |
| `test_slot_sample_sizes_agree_with_the_dataset` | the n per tier in the slot table is recomputed from the dataset, so a measure that silently went empty cannot pass as a null result |
| `test_sourcebook_control_does_not_invent_a_confound` | a slot whose records cite no sourcebook in either tier reports "no control available"; only a genuinely one-sided slot may claim a confound |
| `test_slot_conclusion_is_supported_by_a_tested_comparison` | the conclusion may call mixed-canon rankings safe only when a slot with >= `MIN_COMPARABLE_N` per tier actually ran, and a null result must stay worded as absence of evidence |
| `test_builder_combination_rows_are_flagged_not_deleted` / `test_item_plus_qualifier_names_are_not_builder_artefacts` | 113 builder rows are flagged and 43 stay distinct, while "Battle armor, heavy" and "Datapad, basic" are *not* flagged (GAP-014) |

The two config-coverage tests were added after real drift: `scoring.weights`
contained metric names the evaluator never produced (so those metrics silently
scored 0), and `page_to_sourcebooks` was registered but referenced by no block (so
73 records lost their page citations). Neither was visible in any report.

## What is *not* verified

Stated plainly, because an agent must not over-trust the numbers:

1. The per-level feat/talent progression schedule (GAP-002) - drives every
   above-level-1 count.
2. Ability score generation (GAP-003) - drives the largest single dimension.
3. Talent tier within a tree (GAP-001) - makes talent counts permissive.
4. Force powers known (GAP-004).
5. Prestige defence encoding (GAP-005).
6. Droid option budgets (GAP-010).
7. Age category legality per species (GAP-012).
8. Homebrew class progression (GAP-013) - Technician and Force Prodigy have prose
   only.
9. The 812 wiki links (GAP-009) - unreachable from the sandbox, never fetched.

Each is declared in `data/curation/gaps.yaml` with the evidence that it is still
true, and each has a task in `tasks/`.
