# Canonicalisation report

Generated: 2026-10-09T04:43:35+00:00  
Sources: sagaforge-1.53, swse-master-reference-2026-10-08

## Entities

| entity | records | official | 3rd-party | homebrew | file |
|---|---:|---:|---:|---:|---|
| `age_category` | 6 | 0 | 6 | 0 | `data/canonical/age_category.json` |
| `ammunition` | 21 | 0 | 21 | 0 | `data/canonical/ammunition.json` |
| `armor` | 92 | 88 | 4 | 0 | `data/canonical/armor.json` |
| `armor_accessory` | 48 | 44 | 4 | 0 | `data/canonical/armor_accessory.json` |
| `armor_size` | 3 | 0 | 3 | 0 | `data/canonical/armor_size.json` |
| `armor_template` | 27 | 27 | 0 | 0 | `data/canonical/armor_template.json` |
| `availability` | 6 | 0 | 6 | 0 | `data/canonical/availability.json` |
| `background` | 46 | 0 | 46 | 0 | `data/canonical/background.json` |
| `class` | 41 | 39 | 0 | 2 | `data/canonical/class.json` |
| `class_feature` | 41 | 0 | 41 | 0 | `data/canonical/class_feature.json` |
| `cybernetic` | 19 | 18 | 1 | 0 | `data/canonical/cybernetic.json` |
| `destiny` | 88 | 0 | 88 | 0 | `data/canonical/destiny.json` |
| `droid_degree` | 5 | 0 | 5 | 0 | `data/canonical/droid_degree.json` |
| `droid_locomotion` | 7 | 0 | 7 | 0 | `data/canonical/droid_locomotion.json` |
| `droid_option` | 121 | 0 | 121 | 0 | `data/canonical/droid_option.json` |
| `droid_shield_rating` | 4 | 0 | 4 | 0 | `data/canonical/droid_shield_rating.json` |
| `droid_translator` | 4 | 0 | 4 | 0 | `data/canonical/droid_translator.json` |
| `equipment` | 226 | 184 | 42 | 0 | `data/canonical/equipment.json` |
| `equipment_accessory` | 18 | 17 | 1 | 0 | `data/canonical/equipment_accessory.json` |
| `exotic_weapon_group` | 38 | 0 | 38 | 0 | `data/canonical/exotic_weapon_group.json` |
| `feat` | 387 | 385 | 2 | 0 | `data/canonical/feat.json` |
| `force_power` | 92 | 92 | 0 | 0 | `data/canonical/force_power.json` |
| `force_regimen` | 12 | 0 | 12 | 0 | `data/canonical/force_regimen.json` |
| `force_secret` | 15 | 15 | 0 | 0 | `data/canonical/force_secret.json` |
| `force_technique` | 58 | 58 | 0 | 0 | `data/canonical/force_technique.json` |
| `language` | 102 | 0 | 102 | 0 | `data/canonical/language.json` |
| `lightsaber_form` | 12 | 0 | 12 | 0 | `data/canonical/lightsaber_form.json` |
| `near_human_trait` | 24 | 0 | 24 | 0 | `data/canonical/near_human_trait.json` |
| `racial_ability` | 215 | 0 | 215 | 0 | `data/canonical/racial_ability.json` |
| `range_increment` | 7 | 0 | 7 | 0 | `data/canonical/range_increment.json` |
| `reference_link` | 812 | 812 | 0 | 0 | `data/canonical/reference_link.json` |
| `shield_template` | 4 | 4 | 0 | 0 | `data/canonical/shield_template.json` |
| `size_category` | 9 | 0 | 9 | 0 | `data/canonical/size_category.json` |
| `skill` | 25 | 0 | 25 | 0 | `data/canonical/skill.json` |
| `sourcebook` | 10 | 0 | 10 | 0 | `data/canonical/sourcebook.json` |
| `special_talent` | 16 | 0 | 16 | 0 | `data/canonical/special_talent.json` |
| `species` | 130 | 121 | 9 | 0 | `data/canonical/species.json` |
| `starship_maneuver` | 26 | 0 | 26 | 0 | `data/canonical/starship_maneuver.json` |
| `talent` | 1311 | 1307 | 4 | 0 | `data/canonical/talent.json` |
| `talent_tree` | 192 | 167 | 25 | 0 | `data/canonical/talent_tree.json` |
| `unleashed_ability` | 27 | 0 | 27 | 0 | `data/canonical/unleashed_ability.json` |
| `weapon` | 246 | 239 | 7 | 0 | `data/canonical/weapon.json` |
| `weapon_accessory` | 46 | 46 | 0 | 0 | `data/canonical/weapon_accessory.json` |
| `weapon_mod` | 156 | 0 | 156 | 0 | `data/canonical/weapon_mod.json` |
| `weapon_template` | 35 | 26 | 9 | 0 | `data/canonical/weapon_template.json` |

**Total records:** 4830

## Pipeline statistics

- `aliases_applied`: 5
- `class_skills_resolved`: 73
- `damage_suspected_concatenation`: 1
- `duplicate_rows_collapsed`: 109
- `name_collisions`: 21
- `parameterised_feats`: 5
- `prereq_fragments_unresolved`: 8
- `rows_dropped`: 55
- `rows_read`: 5340
- `split_starting_feats`: 24
- `split_talent_trees`: 66
- `starting_feats_resolved`: 24
- `talent_trees_resolved`: 66
- `unresolved_source_tags`: 4
- `urls_attached`: 316
- `wildcard_grants`: 1

## Prerequisite fragments that could not be resolved

8 fragments. Extend `swse/prereq.py` rules or add aliases in `data/curation/aliases.yaml`.

-   2x `Basic Processor`
-   2x `Cyborg Hybrid with Subcutaneous Comlink`
-   2x `Droid Systems: Heuristic Processor`
-   2x `Shield Generator System`
-   2x `larger Droid with 2+ Appendages`
-   2x `larger Droid with 2+ Tool Mounts`
-   2x `or Tracked Locomotion`
-   1x `"Gamemaster's Approval"`

## Other gaps detected during canonicalisation

- **collision**: species: 'Replica droid' appears 3x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: racial_ability: 'Pack Hunter' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: racial_ability: 'Physically Intimidating' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: racial_ability: 'Scent' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: feat: 'Staggering Attack' appears 3x across 2 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: force_power: 'Force Storm' appears 3x across 2 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: weapon: 'Shockboxing gloves' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **damage**: Power lance: damage column holds '28' with no die size; suspected 2d8 - confirm against the printed book
- **collision**: weapon_mod: 'Inquisition' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option
- **collision**: weapon_mod: 'Double Attack' appears 2x across 1 source(s) - kept separate, declare a merge in data/curation/merges.yaml if they are the same option

## Dropped rows

55 rows were skipped (section labels, placeholders, unnamed rows).

| block | row | reason |
|---|---:|---|
| `sf_species` | 14 | species row with no name |
| `sf_racial_abilities` | 218 | no merge key (missing name) |
| `sf_racial_abilities` | 219 | no merge key (missing name) |
| `sf_racial_abilities` | 220 | no merge key (missing name) |
| `sf_racial_abilities` | 221 | no merge key (missing name) |
| `sf_racial_abilities` | 222 | no merge key (missing name) |
| `mr_heroic_classes` | 7 | homebrew section label |
| `sf_talents` | 1318 | talent row with no name |
| `sf_force_regimens` | 12 | no merge key (missing name) |
| `sf_force_regimens` | 20 | no merge key (missing name) |
| `sf_force_regimens` | 21 | no merge key (missing name) |
| `sf_force_regimens` | 22 | no merge key (missing name) |
| `sf_force_regimens` | 23 | no merge key (missing name) |
| `sf_force_regimens` | 24 | no merge key (missing name) |
| `sf_force_regimens` | 25 | no merge key (missing name) |
| `sf_force_regimens` | 26 | no merge key (missing name) |
| `sf_force_regimens` | 27 | no merge key (missing name) |
| `sf_force_regimens` | 28 | no merge key (missing name) |
| `sf_force_regimens` | 29 | no merge key (missing name) |
| `sf_force_regimens` | 30 | no merge key (missing name) |
| `sf_force_regimens` | 31 | no merge key (missing name) |
| `sf_force_regimens` | 32 | no merge key (missing name) |
| `sf_force_regimens` | 33 | no merge key (missing name) |
| `sf_destinies` | 11 | section label: Legacy Destinies |
| `sf_weapons` | 3 | section label: Melee Weapons |
| `sf_weapons` | 4 | section label: Advanced Melee Weapons |
| `sf_weapons` | 26 | section label: Lightsabers |
| `sf_weapons` | 46 | section label: Simple Melee Weapons |
| `sf_weapons` | 71 | section label: Unarmed and Natural Attacks |
| `sf_weapons` | 81 | section label: Improvised Weapons |
| `sf_weapons` | 87 | section label: Exotic Melee Weapons |
| `sf_weapons` | 108 | section label: Ranged Weapons |
| `sf_weapons` | 109 | section label: Heavy |
| `sf_weapons` | 126 | section label: Pistols |
| `sf_weapons` | 160 | section label: Rifles |
| `sf_weapons` | 208 | section label: Simple Ranged Weapons |
| `sf_weapons` | 230 | section label: Exotic Ranged Weapons |
| `sf_weapons` | 249 | section label: Other Weapons |
| `sf_weapons` | 257 | section label: Explosives |
| `sf_weapons` | 266 | section label: Custom Weapons |
| `sf_armor` | 3 | placeholder row: 'Custom armor' |
| `sf_armor` | 6 | section label: Light armor |
| `sf_armor` | 57 | section label: Medium armor |
| `sf_armor` | 82 | section label: Heavy armor |
| `sf_equipment` | 202 | section label: Ammunition |
| `sf_sith_weapon_traits` | 2 | section label: Sith Weapon Traits |
| `sf_sith_weapon_traits` | 6 | section label: Sith Armor Traits |
| `sf_sith_weapon_traits` | 11 | section label: Sith Abomination Traits |
| `sf_armor_templates` | 3 | placeholder row: '(None)' |
| `mr_links` | 41 | non-URL link row: '[[Core Classes]]' |
| `mr_links` | 50 | non-URL link row: '[[Prestige Classes]]' |
| `mr_links` | 82 | non-URL link row: '[[Feats]]' |
| `mr_links` | 437 | non-URL link row: '[[Talent Trees]]' |
| `mr_links` | 606 | non-URL link row: '[[Force Powers]]' |
| `mr_links` | 697 | non-URL link row: '[[Species]]' |
