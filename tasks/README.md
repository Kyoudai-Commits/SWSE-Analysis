# Task backlog

One file per task, named `TASK-nnn-slug.md`. A task is worth filing when it has a
stated problem, evidence that the problem is real, and acceptance criteria someone
else can check. Tasks that are blocked on data this repository does not have say so
and link the gap that must close first.

Task ids are stable and referenced from `config/analysis.yaml`,
`data/curation/gaps.yaml` and the docs. Never renumber a task; close it instead.

## Status

| id | title | priority | blocked by | status |
|---|---|---|---|---|
| [TASK-001](TASK-001-ingest-wiki-snapshot.md) | Ingest a wiki snapshot as a provenance-tagged source | medium | sandbox network access | open |
| [TASK-002](TASK-002-core-rulebook-tables.md) | Transcribe the Core Rulebook progression tables | high | access to SECR | open |
| [TASK-003](TASK-003-name-collisions.md) | Triage the 21 same-source name collisions | low | - | wont_fix (declared) |
| [TASK-004](TASK-004-power-lance-damage.md) | Confirm the Power lance damage cell | low | access to RECG | open |
| [TASK-005](TASK-005-talent-tiers.md) | Model talent tier within a tree | high | a printed talent list | open |
| [TASK-006](TASK-006-droid-budget.md) | Encode the droid option budget | medium | builder logic or SECR | open |
| [TASK-007](TASK-007-point-buy-curve.md) | Encode the ability point-buy cost curve | medium | access to SECR | open |
| [TASK-008](TASK-008-starting-gear.md) | Turn starting credits into a gear allowance | medium | - | open |
| [TASK-009](TASK-009-starship-space.md) | Starship and vehicle decision space | low | - | open |
| [TASK-010](TASK-010-unresolved-prereqs.md) | Resolve the 8 remaining prerequisite fragments | medium | a droid_system entity | open |
| [TASK-011](TASK-011-progression-schedule.md) | Source the per-level feat/talent schedule | high | access to SECR | open |
| [TASK-012](TASK-012-ability-methods.md) | Confirm the ability score generation methods | high | access to SECR | open |
| [TASK-013](TASK-013-force-gating.md) | Source the Force powers-known allowance | medium | access to SECR/Jedi Academy | open |
| [TASK-014](TASK-014-prestige-defense.md) | Confirm the prestige defence encoding | medium | access to a prestige class page | open |
| [TASK-015](TASK-015-species-age-bounds.md) | Gate age categories per species | low | - | open |
| [TASK-016](TASK-016-homebrew-progression.md) | Give the homebrew classes a progression | low | homebrew author intent | open |
| [TASK-017](TASK-017-level1-pareto.md) | Rank every legal level-1 build and publish the frontier | medium | - | open |
| [TASK-018](TASK-018-canon-balance-audit.md) | Audit metric distributions across canon tiers | medium | - | **resolved** |
| [TASK-019](TASK-019-builder-combination-rows.md) | Flag the builder's combination rows | medium | - | **resolved** |
| [TASK-020](TASK-020-targeted-tier-comparisons.md) | Targeted tier comparisons with real statistical power | medium | - | **resolved** |

## Priority

- **high** - the answer to a headline question is wrong or unknowable until this closes.
  TASK-002, TASK-005, TASK-011, TASK-012 all gate level-2-20 numbers.
- **medium** - a dimension or entity is modelled but not sourced; results are usable
  with the caveat printed.
- **low** - contained, cosmetic, or affects a small slice of the corpus.

## How to pick one up

1. Read the task file, then the gap it links (`data/curation/gaps.yaml`) and the
   assumption it links (`config/analysis.yaml`).
2. Reproduce the problem before changing anything - each task names the command.
3. Follow [`AGENTS.md`](../AGENTS.md): fix the producer, never the generated file,
   and rebuild with `make data`.
4. Meet the acceptance criteria, add the regression test the task asks for, and run
   `make test`.
5. Update the task's status line, the gap's `status`, and the assumption's `verified`
   flag in the same commit. Regenerate reports if a quoted number moved.

## Completed

- **TASK-018** - canon-balance audit (`swse/audit.py`, `analysis/out/canon-balance.md`).
  Found no evidence that third-party content inflates rankings, found that the
  published top decile is dominated by builds using unscoreable homebrew classes, and
  turned up a real scoring bug (a bonus regex that read "roll a natural 20 on an attack
  roll" as a +20 attack bonus) plus a corpus artefact (GAP-014). It also spawned
  TASK-019 and TASK-020. Its report is the model for how a finding should be written
  up: distributions, sample sizes, what could not be compared, and verdicts for every
  outlier that was inspected by hand.

- **TASK-019** - flag the builder's combination rows (GAP-014). The
  `flag_builder_combinations` post hook marks 72 `weapon_mod` rows as combinations of two
  real options (with `relations.combines`) and 101 as parameter variants of one option,
  leaving 43 distinct choices out of 156 - flagged, never deleted, so each row keeps its
  cell citation. Its real finding is the scoping: an entity-agnostic version also flagged
  "Battle armor, heavy" and "Datapad, basic", which are item-plus-qualifier names that only
  look like combinations because the corpus holds reference records called "heavy" and
  "basic". The hook now applies to `weapon_mod` alone and says why in its docstring.

- **TASK-020** - targeted tier comparisons (`swse.audit.SLOT_COMPARISONS`, published as a
  section of `analysis/out/canon-balance.md`). Four decision slots had enough overlap to
  test - talent trees 151/25, species bonuses 109/9, species penalties 105/9, equipment
  price 171/36 - and none differs at p < 0.01; weapons (5-6 third-party records) and armour
  (4) are printed as untestable rather than dropped. Its real contribution is the sourcebook
  control sitting next to each comparison: talent trees cite no sourcebook in either tier so
  there is nothing to control for, and the whole third-party species side is one web citation
  against 12 official books, so a difference there would be about that source and not about
  canonicity. It also caught a false finding in its own first draft, which claimed a
  one-book confound for talent trees because an "(uncited)" placeholder counted as a book.

Every other task here is a real limitation found while building the dataset, the
decision space or the evaluator - not a wishlist.
