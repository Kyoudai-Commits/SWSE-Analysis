# Prerequisite grammar

Prerequisites arrive as free text written for humans: `"BAB +1, Weapon Proficiency
(chosen group)"`, `"Force Sensitivity and Use Computer"`, `"Trained in Mechanics"`,
`"Human or Cyborg"`, `"Jedi Knight 5"`. The parser in `swse/prereq.py` turns that
text into typed predicates that the graph, the enumerator and the evaluator can use.

Current state: **545 of 553 records with prerequisite text are fully parsed
(98.55%)**; 8 fragments remain unresolved and are listed in
`data/reports/prerequisite-graph.md`.

## Predicate types

| type | example text | shape |
|---|---|---|
| `feat` | `Weapon Proficiency` | `{"type":"feat","ref":"feat_weapon_proficiency","resolved":true}` |
| `talent` | `Rage` | `{"type":"talent","ref":"...","tree":"..."}` |
| `talent_tree` | `Jedi Guardian Talent Tree` | `{"type":"talent_tree","ref":"talent_tree_jedi_guardian"}` |
| `class_level` | `Soldier 3` | `{"type":"class_level","ref":"class_soldier","level":3}` |
| `class` | `Jedi` | `{"type":"class","ref":"class_jedi"}` |
| `trained_skill` | `Trained in Mechanics` | `{"type":"trained_skill","ref":"skill_mechanics"}` |
| `skill_rank` | `Mechanics 5 ranks` | `{"type":"skill_rank","ref":"...","value":5}` |
| `bab_min` | `BAB +1` | `{"type":"bab_min","value":1}` |
| `ability_min` | `Strength 13` | `{"type":"ability_min","ability":"str","value":13}` |
| `level_min` | `Character level 6` | `{"type":"level_min","value":6}` |
| `force_sensitive` | `Force Sensitivity` | state predicate, no ref |
| `species` / `creature_type` | `Human`, `Droid` | `{"type":"species","ref":"species_human"}` |
| `armor_proficiency` / `weapon_proficiency` | `Armor Proficiency (light)` | parameterised ref |
| `force_power` / `force_technique` / `force_secret` | `Force Storm` | ref into the Force entities |
| `droid_with` | `larger Droid with 2+ Appendages` | structural requirement |
| `any_category` | `Any one feat` | choice requirement |
| `gm_approval` | `"Gamemaster's Approval"` | rule, not an option |
| `other` | anything unrecognised | kept with `resolved:false` |

Conjunction is a list of predicates (all must hold). Disjunction is expressed by
`or` inside the fragment and is preserved in `raw`; the parser records the group so
the enumerator can treat it as a choice.

## How a line is parsed

1. **`normalize`** - fold whitespace with `fold_multiline()` (newlines are
   meaningful in values; `fold()` is used only for names and ids), strip leading
   "Prerequisite(s):", unify bullet characters.
2. **`split_fragments`** - split on `,` / `;` / `and`, but **bracket-depth aware**
   and **label aware**. `Weapon Proficiency (pistol, blaster)` is one fragment.
   A line that carries a label (`Feats: Force Sensitivity`) is *not* split on the
   colon.
3. **`classify`** per fragment - try the whole fragment first, then head+note
   (`Rage (Jedi Guardian)` -> head `Rage`, note `Jedi Guardian`). Regexes handle the
   numeric predicates; everything else goes to name resolution.
4. **`resolve_name` / `resolve_name_multi`** - look the name up in the
   `EntityIndex`, which is built from the canonical dataset (names, aliases, tree
   keys, head words). Exact match first, then head match, then alias.
5. **`_classify_remainder`** - whatever is left is kept as `other` with
   `resolved:false` and counted in `prereq_fragments_unresolved`.

## The three rules that were learned the hard way

**1. Newlines are data.** `ids.clean_cell()` originally collapsed `\n` into a space.
That destroyed multi-line prerequisite cells and was the single largest cause of
unparsed prerequisites. Names and ids use `fold()`; values use `fold_multiline()`.

**2. Splitting must be both bracket-aware and label-aware.** Comma-splitting
`Weapon Proficiency (pistol, blaster)` yields two non-existent feats. Colon-splitting
`Feats: Force Sensitivity` yields a fragment whose head is a category word. The rule
that survived testing is: *split unless the line is labelled*.

**3. Labels must not swallow structured sub-rules.** `_labelled_names` lifts an
inner structured rule out of a labelled line only when the inner rule is on the
`LABEL_INNER_RULES` whitelist (`armor_proficiency*`, `weapon_proficiency*`,
`weapon_focus_with`, `proficient_with`, `requires_item`, `droid_with`,
`any_category`). Without the whitelist, `"Feats: Force Sensitivity"` was being
reclassified as a `force_sensitive` state predicate instead of a feat reference, and
every feat gated on Force Sensitivity lost its edge.

## Labelled vs unlabelled input

Two corpus shapes reach the parser:

- **Unlabelled** (SagaForge): `"BAB +1, Weapon Proficiency"` - parsed by
  `classify_no_labels`, which never consults category words.
- **Labelled** (Master Reference): `"Feats: Force Sensitivity; Skills: Trained in
  Mechanics"` - parsed by `_labelled_names`, which uses the label to bias the
  entity type but still classifies each item individually.

## Extending the grammar

To resolve a new fragment shape:

1. Reproduce it: `python -m swse.cli validate --show 20` and
   `data/reports/prerequisite-graph.md` list every unresolved fragment with counts.
2. If it is a *name* problem, add an alias in `data/curation/aliases.yaml` - do not
   patch the parser for one record.
3. If it is a *shape* problem (a new predicate type), add the regex/predicate in
   `swse/prereq.py`, add a test in `tests/test_prereq.py`, then `make data`.
4. If it is genuinely not in the data (a droid component that no block extracts),
   declare it in `data/curation/gaps.yaml` and open a task.

The 8 currently unresolved fragments are all shape or missing-entity problems, not
parser bugs: droid system components, `Cyborg Hybrid with Subcutaneous Comlink`,
`larger Droid with 2+ Appendages/Tool Mounts`, `or Tracked Locomotion`, and
`"Gamemaster's Approval"`. See TASK-010.

## Consumers

- `swse/graph.py` builds a `PrereqGraph` from resolved predicates only: 680 edges,
  628 resolved, **0 dangling, 0 cycles**, max depth 3. Edge type counts:
  `trained_skill` 202, `feat` 148, `bab_min` 63, `ability_min` 63.
- `swse/enumerate.py::check_build` uses the predicates as the legality test. A build
  that fails a gate is a violation, and the enumerator reports violations rather
  than silently dropping the build.
- `swse/evaluate.py` uses `unlock_depth` (graph depth) and `synergy` as metrics.
