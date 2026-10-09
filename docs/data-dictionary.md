# Data dictionary

_Generated 2026-10-09 by `swse.report`._

Generated from `data/canonical/` and `config/entities.yaml`. Do not edit by hand - run `python -m swse.cli report`.

## Record shape

Every record in every entity file has this shape:

```json
{
 "id": "feat_weapon_focus",
 "entity": "feat",
 "name": "Weapon Focus",
 "canon": "official",
 "attrs": {
  "...": "entity-specific fields, see below"
 },
 "prerequisites": {
  "raw": "...",
  "predicates": [
   "..."
  ],
  "coverage": 1.0
 },
 "relations": {},
 "sourcebooks": [
  {
   "id": "secr",
   "abbreviation": "SECR",
   "title": "...",
   "page": 123
  }
 ],
 "sources": [
  {
   "source": "sagaforge-1.53",
   "block": "sf_feats",
   "sheet": "Data",
   "row": 12,
   "ref": "Data!A12:Z12",
   "canon": "third_party"
  }
 ],
 "conflicts": {},
 "flags": [
  "parameterised"
 ]
}
```

- `canon` is *content* canonicity, and `attrs.canon_basis` says how it was decided (`sourcebook_citation`, `block_declaration`, `homebrew_section`, `webpage_only_citation`, `derived_record`).
- `sources` is never empty: every value traces to a workbook cell.
- `conflicts` appears only where two sources disagreed; it records the chosen value, where it came from, and the alternatives.

## Entities

| entity | label | role | records | merge_on | official/3rd/homebrew | source blocks |
|---|---|---|---|---|---|---|
| `age_category` | Age category | rule | 6 | name | 0/6/0 | `sf_ages` |
| `ammunition` | Ammunition / ordnance | gear | 21 | name | 0/21/0 | `sf_grenade_launchers` |
| `armor` | Armor | gear | 92 | name | 88/4/0 | `sf_armor` |
| `armor_accessory` | Armor accessory | gear | 48 | name | 44/4/0 | `sf_armor_accessories` |
| `armor_size` | Armor size | rule | 3 | name | 0/3/0 | `sf_armor_sizes` |
| `armor_template` | Armor template | gear | 27 | name | 27/0/0 | `sf_armor_templates` |
| `availability` | Equipment availability | rule | 6 | name | 0/6/0 | `sf_availability_types` |
| `background` | Background | option | 46 | name | 0/46/0 | `sf_backgrounds` |
| `class` | Class (heroic + prestige) | option | 41 | name | 39/0/2 | `sf_classes`, `mr_heroic_classes`, `mr_prestige_classes` |
| `class_feature` | Class feature | modifier | 41 | name | 0/41/0 | `sf_class_features` |
| `cybernetic` | Cybernetic / biotech upgrade | gear | 19 | name | 18/1/0 | `sf_head_devices`, `sf_implants` |
| `destiny` | Destiny | option | 88 | name | 0/88/0 | `sf_destinies` |
| `droid_degree` | Droid degree | rule | 5 | name | 0/5/0 | `sf_droid_degrees` |
| `droid_locomotion` | Droid locomotion | rule | 7 | name | 0/7/0 | `sf_droid_locomotion` |
| `droid_option` | Droid build option | option | 121 | name_and_group | 0/121/0 | `sf_droid_chassis`, `sf_droid_quirks`, `sf_droid_manufacturers`, `sf_droid_accessories`, `sf_droid_armor`, `sf_droid_appendages` |
| `droid_shield_rating` | Droid shield rating | rule | 4 | sr | 0/4/0 | `sf_droid_shield_ratings` |
| `droid_translator` | Droid translator | rule | 4 | dc | 0/4/0 | `sf_droid_translators` |
| `equipment` | Equipment | gear | 226 | name | 184/42/0 | `sf_equipment` |
| `equipment_accessory` | Equipment accessory | gear | 18 | name | 17/1/0 | `sf_equipment_accessories` |
| `exotic_weapon_group` | Exotic weapon proficiency group | modifier | 38 | weapon | 0/38/0 | `sf_exotic_weapon_listing` |
| `feat` | Feat | option | 387 | name | 385/2/0 | `sf_feats`, `mr_feats` |
| `force_power` | Force power | option | 92 | name | 92/0/0 | `sf_force_powers`, `mr_force_powers` |
| `force_regimen` | Force / lightsaber training regimen | option | 12 | name | 0/12/0 | `sf_force_regimens` |
| `force_secret` | Force secret | option | 15 | name | 15/0/0 | `sf_force_secrets` |
| `force_technique` | Force technique | option | 58 | name | 58/0/0 | `sf_force_techniques` |
| `language` | Language | option | 102 | name | 0/102/0 | `sf_languages` |
| `lightsaber_form` | Lightsaber combat form | option | 12 | name | 0/12/0 | `sf_lightsaber_forms` |
| `near_human_trait` | Near-Human trait | option | 24 | name | 0/24/0 | `sf_near_human_traits` |
| `racial_ability` | Racial / species ability | modifier | 215 | name | 0/215/0 | `sf_racial_abilities` |
| `range_increment` | Range increment table | rule | 7 | weapon_group | 0/7/0 | `sf_range_increments` |
| `reference_link` | Wiki reference link | reference | 812 | url | 812/0/0 | `mr_links` |
| `shield_template` | Shield template | gear | 4 | name | 4/0/0 | `sf_shield_templates` |
| `size_category` | Size category | rule | 9 | name | 0/9/0 | `sf_size_types` |
| `skill` | Skill | option | 25 | name | 0/25/0 | `sf_skills` |
| `sourcebook` | Sourcebook | reference | 10 | abbreviation | 0/10/0 | `sf_supplements` |
| `special_talent` | Repeatable special talent (per-class) | option | 16 | name | 0/16/0 | `sf_special_talents_soldier`, `sf_special_talents_ace_pilot`, `sf_special_talents_elite_trooper`, `sf_special_talents_gladiator` |
| `species` | Species | option | 130 | name | 121/9/0 | `sf_species` |
| `starship_maneuver` | Starship maneuver | option | 26 | name | 0/26/0 | `sf_starship_maneuvers` |
| `talent` | Talent | option | 1311 | name_and_tree | 1307/4/0 | `sf_talents` |
| `talent_tree` | Talent tree | option | 192 | name | 167/25/0 | `mr_talent_trees` |
| `unleashed_ability` | Force Unleashed alternate ability | option | 27 | name | 0/27/0 | `sf_unleashed_abilities` |
| `weapon` | Weapon | gear | 246 | name | 239/7/0 | `sf_weapons` |
| `weapon_accessory` | Weapon accessory | gear | 46 | name | 46/0/0 | `sf_weapon_accessories` |
| `weapon_mod` | Feat/talent weapon modifier | modifier | 156 | name | 0/156/0 | `sf_weapon_feat_mods`, `sf_weapon_mod_details` |
| `weapon_template` | Weapon template (custom/premium weapon upgrade) | gear | 35 | name | 26/9/0 | `sf_weapon_templates`, `sf_sith_weapon_traits` |

## Attributes by entity

`filled` is how many records carry a non-empty value; `sample` is one real value.

### `age_category` - Age category

6 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 6/6 | str | block_declaration |
| `mod_cha` | 6/6 | int | 0 |
| `mod_con` | 6/6 | int | 0 |
| `mod_dex` | 6/6 | int | 0 |
| `mod_int` | 6/6 | int | 0 |
| `mod_str` | 6/6 | int | 0 |
| `mod_wis` | 6/6 | int | 0 |

### `ammunition` - Ammunition / ordnance

21 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 21/21 | str | block_declaration |
| `price` | 21/21 | int | 20 |
| `statblock` | 21/21 | str | ammunition clip |
| `statblock_plural` | 21/21 | str | ammunition clips |
| `weight` | 21/21 | float, int | 0.1 |
| `launcher` | 1/21 | str | Grenade, frag |

### `armor` - Armor

92 records, 26 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `availability` | 92/92 | str | Military |
| `canon_basis` | 92/92 | str | sourcebook_citation |
| `stat_block` | 92/92 | str | ARC trooper armor |
| `stat_block_plural` | 92/92 | str | suits of ARC trooper armor |
| `canon_cited_sourcebooks` | 91/92 | list | ["SECR"] |
| `slots` | 91/92 | int | 1 |
| `type` | 90/92 | str | L |
| `ref_bonus` | 88/92 | int | 6 |
| `weight` | 88/92 | float, int | 8.9 |
| `max_dex` | 87/92 | int | 3 |
| `price` | 77/92 | int | 8000 |
| `fort_bonus` | 72/92 | int | 2 |
| `helmet` | 54/92 | str | Helmet with helmet package |
| `accessory_1` | 48/92 | str | Internal Comlink, short-range |
| `rarity` | 30/92 | str | Rare |
| `accessory_2` | 27/92 | str | Helmet Package |
| `extra` | 24/92 | str | Gain DR 2 against energy and fire |
| `accessory_3` | 13/92 | str | Helmet Package |
| `jet_pack` | 11/92 | int | 4 |
| `accessory_4` | 6/92 | str | Jet Pack |
| `str` | 5/92 | int | 2 |
| `template` | 5/92 | str | Mandalorian Iron |
| `bonus_1` | 2/92 | int | 2 |
| `equip_1` | 2/92 | str | Liquid cable dispenser (15 meters) |
| `skill_1` | 2/92 | str | Swim |
| `equip_2` | 1/92 | str | Ubese voice modulator |

### `armor_accessory` - Armor accessory

48 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 48/48 | str | sourcebook_citation |
| `description` | 48/48 | str | Swim 3 |
| `price` | 48/48 | int | 500 |
| `slots` | 48/48 | int | 1 |
| `canon_cited_sourcebooks` | 44/48 | list | ["SaV"] |
| `effect` | 40/48 | str | Swim half your speed, reroll swim check and take better result, take 10 on Swim checks |
| `weight` | 18/48 | float, int | 1 |

### `armor_size` - Armor size

3 records, 3 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `abbr` | 3/3 | str | H |
| `canon_basis` | 3/3 | str | block_declaration |
| `sort` | 3/3 | int | 4 |

### `armor_template` - Armor template

27 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 27/27 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 27/27 | list | ["KotOR"] |
| `price_minimum` | 27/27 | int | 1000 |
| `price_percent` | 27/27 | float, int | 0.1 |
| `effect` | 19/27 | str | 4 Fortitude bonus against cold hazards, none against heat hazards |
| `url` | 3/27 | str | https://swse.miraheze.org/wiki/Arkanian |

### `availability` - Equipment availability

6 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `abbr` | 6/6 | str | C |
| `black_market_mod` | 6/6 | int | 1 |
| `canon_basis` | 6/6 | str | block_declaration |
| `price_multiplier` | 6/6 | int | 1 |
| `dc` | 5/6 | int | 5 |
| `license_dc_mod` | 5/6 | float, int | 0 |

### `background` - Background

46 records, 5 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 46/46 | str | block_declaration |
| `skills` | 46/46 | int | 1 |
| `language` | 24/46 | str | High Galactic |
| `notes` | 22/46 | str | You gain a +2 competence bonus oto untrained skill checks with the skills in your occup... |
| `url` | 1/46 | str | https://swse.miraheze.org/wiki/Mon_Calamari |

### `class` - Class (heroic + prestige)

41 records, 30 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 41/41 | str | sourcebook_citation |
| `class_kind` | 41/41 | str | prestige |
| `base_attack` | 39/41 | float, int | 0.75 |
| `canon_cited_sourcebooks` | 39/41 | list | ["SECR"] |
| `force_points` | 39/41 | int | 6 |
| `fortitude_progression` | 39/41 | int | 2 |
| `hit_die` | 39/41 | int | 8 |
| `min_level` | 39/41 | int | 7 |
| `reflex_progression` | 39/41 | int | 4 |
| `will_progression` | 39/41 | int | 0 |
| `url` | 37/41 | str | https://swse.miraheze.org/wiki/Ace_Pilot |
| `prerequisites_text_alt` | 25/41 | str | Minimum Level: 7th Trained Skills: Stealth Feat: Sniper Talents: Dastardly Strike |
| `special` | 9/41 | str | Must be employed by a major interstellar corporation |
| `class_skills` | 7/41 | list | ["Acrobatics", "Endurance", "Initiative", "Jump", "Knowledge (all; taken individually)"... |
| `class_skills_text` | 7/41 | str | Acrobatics Endurance Initiative Jump Knowledge (all skills, taken individually) Mechani... |
| `defense_bonus` | 7/41 | str | Fort +1 Ref +1 Will +1 |
| `starting_credits` | 7/41 | int | 0 |
| `starting_feats` | 7/41 | list | ["Force Sensitivity", "Weapon Proficiency (Lightsabers)", "Weapon Proficiency (Simple W... |
| `starting_feats_params` | 7/41 | dict | {"Weapon Proficiency (Lightsabers)": "Lightsabers", "Weapon Proficiency (Simple Weapons... |
| `starting_feats_raw` | 7/41 | str | Force Sensitivity Weapon Proficiency (Lightsabers) Weapon Proficiency (Simple Weapons) |
| `starting_feats_text` | 7/41 | str | Force Sensitivity Weapon Proficiency (Lightsabers) Weapon Proficiency (Simple Weapons) |
| `starting_hit_points` | 7/41 | str | 30+Con |
| `talent_trees_raw` | 7/41 | str | Jedi Consular Jedi Guardian Jedi Sentinel Lightsaber Combat |
| `talent_trees_text` | 7/41 | str | Jedi Consular Jedi Guardian Jedi Sentinel Lightsaber Combat |
| `trained_skills` | 7/41 | int | 1 |
| `trained_skills_formula` | 7/41 | str | 2+Int |
| `trained_skills_per_level` | 7/41 | str | 2+Int |
| `talent_trees` | 6/41 | list | ["Jedi Consular", "Jedi Guardian", "Jedi Sentinel", "Lightsaber Combat"] |
| `starting_feats_notes` | 2/41 | dict | {"Linguist": "must have the prerequisite Intelligence of 13"} |
| `grants_all_trees` | 1/41 | bool | true |

### `class_feature` - Class feature

41 records, 1 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 41/41 | str | block_declaration |

### `cybernetic` - Cybernetic / biotech upgrade

19 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 19/19 | str | sourcebook_citation |
| `price` | 19/19 | int | 2000 |
| `canon_cited_sourcebooks` | 18/19 | list | ["KotOR"] |
| `stat_block` | 17/19 | str | aural amplifier |
| `weight` | 12/19 | float, int | 0.5 |
| `stat_block_plural` | 10/19 | str | aural amplifiers |
| `url` | 1/19 | str | https://swse.miraheze.org/wiki/Combat |

### `destiny` - Destiny

88 records, 5 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `bonus` | 88/88 | str | +2 to single attack or skill roll |
| `canon_basis` | 88/88 | str | block_declaration |
| `penalty` | 88/88 | str | -2 to first attack in every encounter |
| `completed_effect` | 7/88 | str | +1 to two ability scores |
| `url` | 1/88 | str | https://swse.miraheze.org/wiki/Corruption |

### `droid_degree` - Droid degree

5 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 5/5 | str | block_declaration |
| `mod_cha` | 4/5 | int | -2 |
| `mod_int` | 4/5 | int | 2 |
| `mod_str` | 3/5 | int | -2 |
| `mod_wis` | 2/5 | int | 2 |
| `mod_dex` | 1/5 | int | 2 |

### `droid_locomotion` - Droid locomotion

7 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 7/7 | str | block_declaration |
| `cost` | 7/7 | int | 200 |
| `speed_large` | 7/7 | int | 8 |
| `speed_medium` | 7/7 | int | 6 |
| `speed_small` | 7/7 | int | 4 |
| `weight` | 2/7 | int | 50 |

### `droid_option` - Droid build option

121 records, 19 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 121/121 | str | block_declaration |
| `option_group` | 121/121 | str | armor |
| `cost` | 56/121 | int, str | 100 |
| `weight` | 55/121 | float, int, str | .5 kg |
| `description` | 47/121 | str | The droid does not back down from a fight unless it has direct orders from its master o... |
| `6` | 37/121 | int | 1 |
| `9` | 37/121 | int | 1 |
| `final_weight_2` | 37/121 | float, int | 0.5 |
| `5` | 35/121 | int, str | 100 |
| `software` | 29/121 | str | S |
| `4` | 15/121 | str | Restricted |
| `availability` | 14/121 | str | m |
| `max_dex` | 14/121 | int | 2 |
| `ref_bonus` | 14/121 | int | 10 |
| `trait` | 14/121 | str | Once per day, an Arakyd droid can make a Persuasion check or a Use Computer check again... |
| `type` | 14/121 | str | Heavy |
| `hardware` | 13/121 | str | H |
| `rarity` | 3/121 | str | r |
| `url` | 1/121 | str | https://swse.miraheze.org/wiki/Slow |

### `droid_shield_rating` - Droid shield rating

4 records, 5 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 4/4 | str | block_declaration |
| `cost` | 4/4 | int | 5000 |
| `size_restriction` | 4/4 | int | 4 |
| `sr` | 4/4 | int | 10 |
| `weight` | 4/4 | int | 20 |

### `droid_translator` - Droid translator

4 records, 4 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 4/4 | str | block_declaration |
| `cost` | 4/4 | int | 1000 |
| `dc` | 4/4 | int | 10 |
| `weight` | 4/4 | int | 4 |

### `equipment` - Equipment

226 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 226/226 | str | sourcebook_citation |
| `size` | 226/226 | str | d |
| `stat_block` | 226/226 | str | 8-2A medical bundle |
| `stat_block_plural` | 226/226 | str | 8-2A medical bundles |
| `weight` | 212/226 | float, int | 1 |
| `price` | 210/226 | int | 200 |
| `canon_cited_sourcebooks` | 185/226 | list | ["JATM"] |

### `equipment_accessory` - Equipment accessory

18 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 18/18 | str | sourcebook_citation |
| `price` | 18/18 | float, int | 500 |
| `slots` | 18/18 | int | 1 |
| `canon_cited_sourcebooks` | 17/18 | list | ["SaV"] |
| `description` | 11/18 | str | -5 to Use Computer checks to detect |
| `col_ar` | 5/18 | str | -5 to Use Computer checks to detect |
| `url` | 1/18 | str | https://swse.miraheze.org/wiki/Ion_Shielding |

### `exotic_weapon_group` - Exotic weapon proficiency group

38 records, 5 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 38/38 | str | block_declaration |
| `index` | 38/38 | int | 1 |
| `source_row_ref` | 38/38 | int | 11 |
| `weapon` | 38/38 | str | Amphistaff |
| `weapon_list` | 38/38 | str | Amphistaff;Amphistaff (quarterstaff form);Amphistaff (spear form);Amphistaff (whip form... |

### `feat` - Feat

387 records, 12 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 387/387 | str | sourcebook_citation |
| `url` | 354/387 | str | https://swse.miraheze.org/wiki/A_Few_Maneuvers |
| `summary` | 353/387 | str | You can weave, juke, and roll to avoid enemy fire in the thick of combat. |
| `canon_cited_sourcebooks` | 309/387 | list | ["TotG"] |
| `description` | 309/387 | str | Gain +2 to defense of Colossal or smaller vehicles, and projectile attacks which miss y... |
| `page_ref` | 309/387 | int, str | TotG 64 |
| `page` | 307/387 | int | 64 |
| `parameter_axis` | 5/387 | str | exotic_weapon |
| `parameter_options` | 5/387 | list | ["amphistaff", "amphistaff (quarterstaff form)", "amphistaff (spear form)", "amphistaff... |
| `parameter_options_count` | 5/387 | int | 38 |
| `parameter_options_source` | 5/387 | str | weapon records whose proficiency code is EWP |
| `aliases` | 4/387 | list | ["Force Sensitive"] |

### `force_power` - Force power

92 records, 14 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 92/92 | str | block_declaration |
| `summary` | 90/92 | str | You trade power for accuracy. |
| `time_requirment` | 90/92 | str | Standard Action |
| `url` | 88/92 | str | https://swse.miraheze.org/wiki/Assured_Strike |
| `canon_cited_sourcebooks` | 64/92 | list | ["LECG"] |
| `page_ref` | 64/92 | int, str | LECG 53 |
| `page` | 63/92 | int | 53 |
| `descriptor` | 45/92 | str | Telekinetic |
| `col_b` | 25/92 | str | Juyo |
| `descriptor_telekinetic` | 16/92 | str | Telekinetic |
| `descriptor_dark_side` | 12/92 | str | Dark Side |
| `descriptor_mind_affecting` | 6/92 | str | Mind-Affecting |
| `descriptor_light_side` | 3/92 | str | Light Side |
| `pages` | 1/92 | dict | {"lecg": 54, "tfu": 86} |

### `force_regimen` - Force / lightsaber training regimen

12 records, 2 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 12/12 | str | block_declaration |
| `group` | 7/12 | str | Lightsaber Training Regimens |

### `force_secret` - Force secret

15 records, 4 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 15/15 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 15/15 | list | ["TFU"] |
| `page` | 15/15 | int | 89 |
| `page_ref` | 15/15 | int, str | FUCG 89 |

### `force_technique` - Force technique

58 records, 4 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 58/58 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 58/58 | list | ["CW"] |
| `page` | 58/58 | int | 54 |
| `page_ref` | 58/58 | int, str | CWCG 54 |

### `language` - Language

102 records, 2 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 102/102 | str | block_declaration |
| `url` | 41/102 | str | https://swse.miraheze.org/wiki/Aleena |

### `lightsaber_form` - Lightsaber combat form

12 records, 2 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 12/12 | str | block_declaration |
| `form_slot` | 12/12 | str | primary |

### `near_human_trait` - Near-Human trait

24 records, 2 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 24/24 | str | block_declaration |
| `description` | 24/24 | str | Increase one ability score by 2 and reduce another by 2 to account for emphasis in cert... |

### `racial_ability` - Racial / species ability

215 records, 3 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 215/215 | str | block_declaration |
| `description` | 213/215 | str | Increase one ability score by 2 and reduce another by 2 to account for emphasis in cert... |
| `url` | 8/215 | str | https://swse.miraheze.org/wiki/Force_Blast |

### `range_increment` - Range increment table

7 records, 7 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 7/7 | str | block_declaration |
| `long` | 7/7 | int | 500 |
| `medium` | 7/7 | int | 250 |
| `point_blank` | 7/7 | int | 50 |
| `short` | 7/7 | int | 100 |
| `sort` | 7/7 | int | 2 |
| `weapon_group` | 7/7 | str | heavy |

### `reference_link` - Wiki reference link

812 records, 2 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 812/812 | str | block_declaration |
| `url` | 812/812 | str | https://swse.miraheze.org/wiki/1st-Degree_Droid_Talent_Tree |

### `shield_template` - Shield template

4 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 4/4 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 4/4 | list | ["KotOR"] |
| `effect` | 4/4 | str | DR 5 (sonic damage only, from shields) |
| `price_minimum` | 4/4 | int | 1000 |
| `price_percent` | 4/4 | float | 0.1 |
| `url` | 1/4 | str | https://swse.miraheze.org/wiki/Verpine |

### `size_category` - Size category

9 records, 9 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `abbr` | 9/9 | str | c |
| `canon_basis` | 9/9 | str | block_declaration |
| `carrying_capacity_mult` | 9/9 | float, int | 20 |
| `damage_threshold_mod` | 9/9 | int | 50 |
| `die_size` | 9/9 | int | 12 |
| `hp_mod` | 9/9 | int | 100 |
| `ref_mod` | 9/9 | int | -10 |
| `sort` | 9/9 | int | 9 |
| `stealth_mod` | 9/9 | int | -20 |

### `skill` - Skill

25 records, 6 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `ability` | 25/25 | str | Dexterity |
| `armor_check_penalty` | 25/25 | int | 0 |
| `canon_basis` | 25/25 | str | block_declaration |
| `class_skill_flag` | 25/25 | str | No |
| `class_skills_of` | 25/25 | list | ["Jedi", "Scoundrel", "Force Prodigy"] |
| `aliases` | 1/25 | list | ["Knowledge (bureacracy)"] |

### `sourcebook` - Sourcebook

10 records, 3 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `abbreviation` | 10/10 | str | CWCS |
| `canon_basis` | 10/10 | str | block_declaration |
| `title` | 9/10 | str | Clone Wars Campaign Guide |

### `special_talent` - Repeatable special talent (per-class)

16 records, 1 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 16/16 | str | block_declaration |

### `species` - Species

130 records, 45 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 130/130 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 130/130 | list | ["TFU"] |
| `languages` | 130/130 | list | ["Basic", "Aleena"] |
| `size` | 130/130 | str | s |
| `source_tag` | 130/130 | str | TFU |
| `species_kind` | 130/130 | str | species |
| `speed` | 130/130 | int, str | 4 |
| `specials` | 126/130 | list | ["Nimble", "Quick Energy"] |
| `age_adult` | 123/130 | int | 19 |
| `age_middle` | 123/130 | int | 46 |
| `age_old` | 123/130 | int | 61 |
| `age_venerable` | 123/130 | int | 80 |
| `age_young_adult` | 123/130 | int | 13 |
| `url` | 112/130 | str | https://swse.miraheze.org/wiki/Aleena |
| `mod_cha` | 65/130 | int | -2 |
| `mod_dex` | 56/130 | int, str | 2 |
| `mod_wis` | 56/130 | int | -2 |
| `mod_str` | 47/130 | int, str | 0 |
| `mod_int` | 46/130 | int | 2 |
| `mod_con` | 40/130 | int | 2 |
| `skill_focus_1` | 29/130 | str | Mechanics |
| `reroll_skill_1` | 18/130 | str | Acrobatics |
| `reroll_skill_1_mode` | 18/130 | str | worse |
| `ref_bonus` | 14/130 | int | 2 |
| `feat1` | 13/130 | str | Toughness |
| `fort_bonus` | 13/130 | int | 0 |
| `natural_weapons` | 11/130 | list | [{"name": "claws", "damage": "1d6", "type": "slashing"}, {"name": "bite", "damage": "1d... |
| `skill_trained_1` | 11/130 | str | Mechanics |
| `will_bonus` | 8/130 | int | 2 |
| `natural_armor` | 7/130 | int | 0 |
| `if_weapongroup` | 6/130 | str | simple |
| `then_exotic` | 6/130 | str | Cesta |
| `damage_reduction` | 3/130 | int | 2 |
| `skill_trained_2` | 3/130 | str | Stealth |
| `take10_skill_1` | 3/130 | str | Climb |
| `if_weapongroup2` | 2/130 | str | simple |
| `reroll_skill_2` | 2/130 | str | Jump |
| `reroll_skill_2_mode` | 2/130 | str | worse |
| `skill_focus_2` | 2/130 | str | Use Computer |
| `then_exotic2` | 2/130 | str | Atlatl |
| `feat2` | 1/130 | str | Weapon Focus () |
| `feat3` | 1/130 | str | Weapon Focus () |
| `if_first` | 1/130 | str | Martial Arts I |
| `take10_skill_2` | 1/130 | str | Jump |
| `then_feat` | 1/130 | str | Mighty Swing |

### `starship_maneuver` - Starship maneuver

26 records, 3 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 26/26 | str | block_declaration |
| `descriptor` | 16/26 | str | attack patern |
| `url` | 1/26 | str | https://swse.miraheze.org/wiki/Intercept |

### `talent` - Talent

1311 records, 10 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 1311/1311 | str | sourcebook_citation |
| `class_group` | 1311/1311 | str | Jedi |
| `layout_column` | 1311/1311 | int | 1 |
| `page_ref` | 1311/1311 | int, str | 40 |
| `tree` | 1311/1311 | str | Jedi Guardian |
| `description` | 1310/1311 | str | Make a DC 20 Acrobatics check to negate falling prone |
| `canon_cited_sourcebooks` | 1307/1311 | list | ["SECR"] |
| `page` | 1307/1311 | int | 40 |
| `url` | 5/1311 | str | https://swse.miraheze.org/wiki/Combustion |
| `unresolved_source_tags` | 4/1311 | list | ["JATM17"] |

### `talent_tree` - Talent tree

192 records, 10 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `availability` | 192/192 | list | ["Droid Talent Tree"] |
| `canon_basis` | 192/192 | str | block_declaration |
| `classes_from_builder` | 176/192 | list | ["Scout"] |
| `derived_from` | 176/192 | list | ["sf_talents"] |
| `talent_order` | 176/192 | list | [{"id": "talent_mobile_combatant__advance_patrol_talent_tree", "layout_column": 1, "row... |
| `talents` | 176/192 | list | ["talent_mobile_combatant__advance_patrol_talent_tree", "talent_trailblazer", "talent_w... |
| `url` | 169/192 | str | https://swse.miraheze.org/wiki/1st-Degree_Droid_Talent_Tree |
| `availability_text` | 167/192 | str | Droid Talent Tree |
| `summary` | 167/192 | str | 1st-Degree Droids are usually Medical, Analytical, or Scientific Droids. |
| `aliases` | 151/192 | list | ["Advance Patrol Talent Tree"] |

### `unleashed_ability` - Force Unleashed alternate ability

27 records, 4 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 27/27 | str | block_declaration |
| `qualify` | 26/27 | str | No |
| `unleashed_name` | 26/27 | str | Unleashed Bantha Rush |
| `url` | 15/27 | str | https://swse.miraheze.org/wiki/Bantha_Rush |

### `weapon` - Weapon

246 records, 21 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 246/246 | str | sourcebook_citation |
| `price` | 246/246 | int | 0 |
| `weight` | 246/246 | float, int, str | 2 |
| `availability` | 245/246 | str | C |
| `canon_cited_sourcebooks` | 243/246 | list | ["SECR"] |
| `proficiency` | 234/246 | str | EWP |
| `range_increment` | 234/246 | str | M |
| `weapon_group` | 233/246 | str | amphistaff |
| `size` | 232/246 | str | l |
| `damage` | 228/246 | list | [{"multiplier": 1, "die_size": 6, "bonus": null}, {"multiplier": 1, "die_size": 6, "bon... |
| `damage_type` | 227/246 | str | Bludgeoning |
| `ammo` | 155/246 | int, str | 50 |
| `special` | 137/246 | str | Poison, Can be thrown |
| `rates` | 110/246 | str | S |
| `lifetime` | 102/246 | int | 50 |
| `number` | 57/246 | int | 1 |
| `stun` | 56/246 | str | 3d8 |
| `rarity` | 52/246 | str | Rare |
| `ratea` | 26/246 | str | A |
| `handedness` | 24/246 | str | L |
| `double` | 12/246 | str | Yes |

### `weapon_accessory` - Weapon accessory

46 records, 5 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 46/46 | str | sourcebook_citation |
| `canon_cited_sourcebooks` | 46/46 | list | ["SaV"] |
| `slots` | 46/46 | int | 0 |
| `effect` | 33/46 | str | Once per encounter, damage bonus from Power Blast is doubled |
| `price` | 31/46 | int | 1200 |

### `weapon_mod` - Feat/talent weapon modifier

156 records, 40 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 156/156 | str | block_declaration |
| `prerequisite_type` | 146/156 | str | ranged |
| `attack_mod` | 136/156 | int | 2 |
| `damage_mod` | 115/156 | int | 0 |
| `damage_mod_2` | 101/156 | int | 7 |
| `is_attack` | 80/156 | int, str | Other |
| `kind` | 80/156 | int, str | Improved Battle Strike |
| `sort_tags` | 80/156 | int, str | Technique |
| `source_tag` | 80/156 | str | CR |
| `standalone` | 80/156 | str | No |
| `tags` | 80/156 | int, str | Force, Technique |
| `desc2` | 78/156 | int, str | // Improved Battle Strike• Force, Technique |
| `ref` | 75/156 | int, str | FUCG 89 |
| `action_2` | 56/156 | int, str | move |
| `prerequisite_proficiency` | 56/156 | int, str | heavy |
| `single` | 56/156 | str | Yes |
| `desc1` | 54/156 | int, str | Maintain cloak power as move action instead of a standard action |
| `combat_description` | 46/156 | bool, int | true |
| `damage_dice_mod` | 40/156 | int | 2 |
| `condition` | 36/156 | str | against opponent tumbled past |
| `action` | 33/156 | str | free |
| `condition_2` | 33/156 | int, str | 7 |
| `action_3` | 32/156 | int, str | 6 |
| `url` | 25/156 | str | https://swse.miraheze.org/wiki/Acrobatic_Strike |
| `name_2` | 13/156 | str | No |
| `atk_mode` | 5/156 | int, str | 22 |
| `weapon_type` | 5/156 | int, str | 21 |
| `dice` | 3/156 | int | 11 |
| `att` | 2/156 | int | 8 |
| `autofire` | 2/156 | str | A |
| `dam1` | 2/156 | int | 9 |
| `ignore_bonuses` | 2/156 | bool | true |
| `dam2` | 1/156 | int | 10 |
| `w1` | 1/156 | int | 12 |
| `w2` | 1/156 | int | 13 |
| `w3` | 1/156 | int | 14 |
| `w4` | 1/156 | int | 15 |
| `w5` | 1/156 | int | 16 |
| `w6` | 1/156 | int | 17 |
| `weaponcalc` | 1/156 | int | 18 |

### `weapon_template` - Weapon template (custom/premium weapon upgrade)

35 records, 13 distinct attributes.

| attribute | filled | types | sample |
|---|---:|---|---|
| `canon_basis` | 35/35 | str | sourcebook_citation |
| `effect` | 35/35 | str | Deal fire and energy damage |
| `canon_cited_sourcebooks` | 26/35 | list | ["KotOR"] |
| `price_minimum` | 26/35 | int | 1000 |
| `price_percent` | 26/35 | float, int | 0.1 |
| `limitdamagetype1` | 7/35 | str | Energy |
| `limittype` | 7/35 | str | Ranged |
| `url` | 7/35 | str | https://swse.miraheze.org/wiki/Arkanian |
| `group_1` | 3/35 | str | advanced melee |
| `group_2` | 3/35 | str | simple |
| `limitstun` | 3/35 | str | Stun |
| `limitdamagetype2` | 2/35 | str | Piercing |
| `limittypefeat` | 1/35 | str | Simple |

