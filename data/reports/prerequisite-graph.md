# Prerequisite graph report

## Summary

- edges: **680** (635 resolved to a record, 0 dangling)
- nodes touched: 402
- deepest requirement chain: 3
- cycles detected: 0

## Edge types

| requirement type | edges |
|---|---:|
| `trained_skill` | 203 |
| `feat` | 147 |
| `bab_min` | 63 |
| `ability_min` | 63 |
| `species` | 52 |
| `talent_tree` | 34 |
| `level_min` | 28 |
| `weapon_proficiency` | 17 |
| `creature_type` | 16 |
| `racial_ability` | 9 |
| `special` | 8 |
| `other` | 8 |
| `requires_item` | 6 |
| `talent` | 5 |
| `armor_proficiency` | 5 |
| `force_sensitive` | 5 |
| `size_min` | 3 |
| `dark_side_equals_ability` | 2 |
| `droid_locomotion` | 2 |
| `force_power` | 1 |
| `any_of_category` | 1 |
| `dark_side_score` | 1 |
| `affiliation` | 1 |

## Edges by requiring entity

| entity | edges |
|---|---:|
| `feat` | 507 |
| `class` | 173 |

## Cycles

None. The requirement relation is acyclic.

## Dangling requirements

0 edges point at a name that no canonical record matches.

| requiring record | requirement type | unresolved name |
|---|---|---|

## Deepest prerequisite chains

- Assassin (`class_assassin`) ← requires ← Sniper (`feat_sniper`) ← requires ← Precise Shot (`feat_precise_shot`) ← requires ← Point-Blank Shot (`feat_point_blank_shot`)
- Deadly Sniper (`feat_deadly_sniper`) ← requires ← Sniper (`feat_sniper`) ← requires ← Precise Shot (`feat_precise_shot`) ← requires ← Point-Blank Shot (`feat_point_blank_shot`)
- Pinpoint Accuracy (`feat_pinpoint_accuracy`) ← requires ← Aiming Accuracy (`feat_aiming_accuracy`) ← requires ← Precise Shot (`feat_precise_shot`) ← requires ← Point-Blank Shot (`feat_point_blank_shot`)
- Tactical Genius (`feat_tactical_genius`) ← requires ← Starship Tactics (`feat_starship_tactics`) ← requires ← Vehicular Combat (`feat_vehicular_combat`) ← requires ← Pilot (`skill_pilot`)
- Ace Pilot (`class_ace_pilot`) ← requires ← Vehicular Combat (`feat_vehicular_combat`) ← requires ← Pilot (`skill_pilot`)
- Elite Trooper (`class_elite_trooper`) ← requires ← Armor Proficiency (Medium) (`feat_armor_proficiency_medium`) ← requires ← Armor Proficiency (Light) (`feat_armor_proficiency_light`)
- Gunslinger (`class_gunslinger`) ← requires ← Precise Shot (`feat_precise_shot`) ← requires ← Point-Blank Shot (`feat_point_blank_shot`)
- Martial Arts Master (`class_martial_arts_master`) ← requires ← Martial Arts II (`feat_martial_arts_ii`) ← requires ← Martial Arts I (`feat_martial_arts_i`)
- Master Privateer (`class_master_privateer`) ← requires ← Vehicular Combat (`feat_vehicular_combat`) ← requires ← Pilot (`skill_pilot`)
- Medic (`class_medic`) ← requires ← Surgical Expertise (`feat_surgical_expertise`) ← requires ← Treat Injury (`skill_treat_injury`)
- Shaper (`class_shaper`) ← requires ← Biotech Specialist (`feat_biotech_specialist`) ← requires ← Mechanics (`skill_mechanics`)
- A Few Maneuvers (`feat_a_few_maneuvers`) ← requires ← Vehicular Combat (`feat_vehicular_combat`) ← requires ← Pilot (`skill_pilot`)
- Acrobatic Dodge (`feat_acrobatic_dodge`) ← requires ← Mobility (`feat_mobility`) ← requires ← Dodge (`feat_dodge`)
- Aiming Accuracy (`feat_aiming_accuracy`) ← requires ← Precise Shot (`feat_precise_shot`) ← requires ← Point-Blank Shot (`feat_point_blank_shot`)
- Armor Proficiency (Heavy) (`feat_armor_proficiency_heavy`) ← requires ← Armor Proficiency (Medium) (`feat_armor_proficiency_medium`) ← requires ← Armor Proficiency (Light) (`feat_armor_proficiency_light`)
