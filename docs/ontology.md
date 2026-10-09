# Ontology - the entity model

Everything in the dataset is one of 45 entity types. Each entity has a `role`
(declared in `config/entities.yaml`) that says what it is *for* in analysis, which
drives how `swse.space`, `swse.enumerate` and `swse.evaluate` treat it.

Roles:

- **`core`** - a top-level character-creation choice: `species`, `class`, `age_category`,
  `destiny`, `background`.
- **`option`** - something a character can take: `feat`, `talent`, `force_power`,
  `force_technique`, `force_secret`, `force_regimen`, `language`, `skill`,
  `racial_ability`, `droid_option`, `starship_maneuver`, `shield_template`.
- **`gear`** - purchasable equipment: `weapon`, `armor`, `equipment`, `ammunition`,
  `weapon_mod`, `armor_accessory`, `armor_template`, `vehicle_weapon`, `starship_weapon`,
  `starship_base`, `mine`, `grenade_launcher`, `explosive`.
- **`reference`** - not choices, but the scaffolding the choices are described with:
  `talent_tree`, `class_feature`, `skill_use`, `force_power_suite`, `force_regimen_group`,
  `reference_link`, `sourcebook`, `availability`, `armor_size`, `weapon_group`,
  `droid_type`, `starship_class`, `vehicle_type`, `size`, `age_table`, `skill_formula`,
  `parameter_axis`.
- **`analysis`** - records the pipeline derived rather than read: `derived_option`,
  `assumption`, `gap`.

## Record shape

```json
{
  "id": "feat_weapon_focus",
  "entity": "feat",
  "name": "Weapon Focus",
  "canon": "official",
  "attrs": { "prerequisites_text": "...", "benefit": "...", "page": 82 },
  "prerequisites": {
    "raw": "BAB +1, Weapon Proficiency (chosen group)",
    "predicates": [
      {"type": "bab_min", "value": 1, "resolved": true},
      {"type": "feat", "ref": "feat_weapon_proficiency", "resolved": true}
    ],
    "coverage": 1.0
  },
  "relations": { "parameter_of": ["weapon_group_pistol", "..."], "granted_by": ["class_soldier"] },
  "sourcebooks": [{"id": "secr", "abbreviation": "SECR", "title": "Saga Edition Core Rulebook", "page": 82}],
  "sources": [{"source": "sagaforge-1.53", "block": "sf_feats", "sheet": "Data", "row": 104, "ref": "Data!A104:Z104", "canon": "third_party"}],
  "conflicts": { "benefit": {"chosen": "...", "from": "master-reference", "alternatives": ["..."]} },
  "flags": ["parameterised"]
}
```

Field semantics:

| field | meaning |
|---|---|
| `id` | `<entity>_<slug>`, with a disambiguating suffix where a name repeats inside one source. Stable across rebuilds; never re-slug it by hand. |
| `canon` | `official` \| `third_party` \| `homebrew` - the *content*'s canonicity, not the carrier's. |
| `attrs.canon_basis` | how `canon` was decided: `sourcebook_citation`, `block_declaration`, `derived_record`, `webpage_only_citation`. |
| `attrs` | entity-specific fields. Populated from the source row, then modified by hooks. Reserved names (`id`, `entity`, `name`, `canon`, `prerequisites`, `relations`, `sourcebooks`, `sources`, `conflicts`, `flags`) are never duplicated into `attrs`. |
| `prerequisites` | parsed gate, or `null` if the record has none. `coverage` is the fraction of fragments resolved to real records. |
| `relations` | edges this record declares towards others (`parameter_of`, `granted_by`, `part_of`, `tree`, `group`). |
| `sourcebooks` | printed citations with page numbers, resolved from page refs and source tags. |
| `sources` | **always non-empty.** Every value in the record traces to at least one workbook cell. |
| `conflicts` | present only where two sources disagreed; records the chosen value, its origin and the alternatives. |
| `flags` | machine-readable annotations: `parameterised`, `name_collision`, `homebrew`, `unverified_progression`, `damage_suspected_concatenation`, `derived`, ... |

## Merge semantics

`merge_on` decides when two rows from *different* sources are the same option:

| rule | used by | meaning |
|---|---|---|
| `name` | most entities | same display name |
| `name_and_tree` | `talent` | same name in the same talent tree (two trees can both have "Rage") |
| `name_and_group` | `weapon`, `weapon_mod` | same name in the same weapon group |
| a single field | e.g. `class_feature` | merge on that field alone |

Same-name records from the *same* source are **not** merged: they are flagged
`name_collision` and get a disambiguated id. Three different feats really are all
called "Staggering Attack".

When two sources disagree about a value, the winner is chosen by canon rank
(official beats third_party beats homebrew) and then by longest text - the assumption
being that the more complete description is the more useful one. The loser is kept in
`conflicts` so the choice is auditable and can be overridden in
`data/curation/overrides.yaml`.

## Entity notes worth knowing

- **`class`** carries `class_kind` (`heroic` \| `prestige` \| `beast` \| `nonheroic`),
  numeric progression columns (`bab_progression`, `reflex_progression`, ...) and
  structured grants (`grants_feats`, `grants_trees`, `grants_skills`,
  `grants_all_trees`). Prestige classes carry their entry requirements as free text
  in `attrs.prerequisites_text` plus parsed predicates.
- **`talent`** is the largest entity (1,311). Tier within a tree is *absent* from
  both sources (GAP-001); `layout_column` records the spreadsheet column the name
  appeared in, which is layout, not rank.
- **`talent_tree`** is `derived_record` - built from the talents themselves plus the
  Master Reference's AVAILABILITY column, which is the only authoritative
  class-to-tree mapping.
- **`species`** includes droid chassis, beasts and near-humans. Trait text is keyed
  into a glossary block; 19 species also grant skill re-rerolls.
- **`feat`** includes 5 parameterised feats whose axes are materialised as
  `parameter_axis` records (Weapon Proficiency x 6 groups, Exotic Weapon Proficiency
  x 33, Skill Focus x 25, Linguist x 102 languages, Weapon Focus x 6).
- **`force_power`** / **`force_technique`** / **`force_secret`** are distinct
  entities; how many a character knows is *not* in the sources (GAP-004).
- **`reference_link`** (812) holds the wiki URLs from the Master Reference. Nothing
  was fetched from them; they exist so a future ingest can join on the URL.
- **`sourcebook`** (10) is the printed-book register used to resolve page citations.

Field-level coverage for every entity: [`data-dictionary.md`](data-dictionary.md)
(generated by `python -m swse.cli report`).
