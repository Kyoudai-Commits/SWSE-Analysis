# Prestige class entry paths

_Generated 2026-10-09 by `swse.report`._

Each prestige class is reachable only through a chain of earlier choices. This report decomposes those chains from the parsed prerequisites, so an agent can see which heroic classes and which feats/talents/skills feed each prestige option.

| prestige class | canon | min level | requirement kinds | resolved edges | required entity types | heroic classes that grant a requirement |
|---|---|---|---|---|---|---|
| Independent Droid | official | 3 | level_min:1, trained_skill:1, other:1, special:1, creature_type:1 | 2 | skill:2 | - |
| Ace Pilot | official | 7 | level_min:1, trained_skill:1, feat:1 | 3 | skill:2, feat:1 | - |
| Assassin | official | 7 | level_min:1, trained_skill:1, feat:1, talent:1 | 5 | skill:2, talent:2, feat:1 | - |
| Bounty Hunter | official | 7 | level_min:1, trained_skill:1, talent:1 | 3 | skill:2, talent_tree:1 | - |
| Charlatan | official | 7 | level_min:1, trained_skill:1, talent:1 | 5 | talent_tree:3, skill:2 | - |
| Corporate Agent | official | 7 | level_min:1, trained_skill:1, feat:1, special:1 | 3 | skill:2, feat:1 | - |
| Crime Lord | official | 7 | level_min:1, trained_skill:1, talent:1 | 5 | talent_tree:3, skill:2 | - |
| Droid Commander | official | 7 | level_min:1, trained_skill:1, talent:1, special:1, creature_type:1 | 4 | skill:2, talent_tree:2 | - |
| Elite Trooper | official | 7 | bab_min:1, feat:1, armor_proficiency:1, talent:1 | 8 | feat:4, talent_tree:4 | Scoundrel, Soldier |
| Enforcer | official | 7 | level_min:1, trained_skill:1, talent:1, special:1 | 3 | skill:2, talent_tree:1 | - |
| Force Adept | official | 7 | level_min:1, trained_skill:1, feat:1, talent:1 | 3 | skill:2, feat:1 | Force Prodigy, Jedi |
| Gladiator | official | 7 | level_min:1, bab_min:1, feat:1, weapon_proficiency:1 | 2 | feat:2 | - |
| Gunslinger | official | 7 | level_min:1, feat:1, weapon_proficiency:1 | 4 | feat:4 | Scoundrel |
| Imperial Knight | official | 7 | bab_min:1, trained_skill:1, feat:1, armor_proficiency:1, weapon_proficiency:1 | 5 | feat:3, skill:2 | Force Prodigy, Jedi, Soldier |
| Improviser | official | 7 | level_min:1, trained_skill:1, feat:1 | 3 | skill:2, feat:1 | - |
| Infiltrator | official | 7 | level_min:1, trained_skill:1, feat:1, talent:1 | 5 | skill:2, talent_tree:2, feat:1 | - |
| Jedi Knight | official | 7 | bab_min:1, trained_skill:1, feat:1, weapon_proficiency:1, special:1, affiliation:1 | 4 | skill:2, feat:2 | Force Prodigy, Jedi |
| Martial Arts Master | official | 7 | bab_min:1, feat:1, any_of_category:1, talent:1 | 4 | feat:2, talent_tree:2 | - |
| Master Privateer | official | 7 | level_min:1, trained_skill:1, feat:1, talent:1 | 6 | talent_tree:3, skill:2, feat:1 | - |
| Medic | official | 7 | level_min:1, trained_skill:1, feat:1 | 3 | skill:2, feat:1 | - |
| Melee Duelist | official | 7 | level_min:1, bab_min:1, feat:1, weapon_focus:1 | 2 | feat:2 | - |
| Military Engineer | official | 7 | bab_min:1, trained_skill:1 | 2 | skill:2 | - |
| Officer | official | 7 | level_min:1, trained_skill:1, talent:1, special:1 | 5 | talent_tree:3, skill:2 | - |
| Outlaw | official | 7 | level_min:1, trained_skill:1, talent:1, special:1 | 4 | skill:2, talent_tree:2 | - |
| Pathfinder | official | 7 | level_min:1, trained_skill:1, talent:1 | 5 | talent_tree:3, skill:2 | - |
| Saboteur | official | 7 | level_min:1, trained_skill:1 | 3 | skill:3 | - |
| Shaper | official | 7 | level_min:1, trained_skill:1, feat:1, species:1 | 4 | skill:2, feat:1, species:1 | - |
| Sith Apprentice | official | 7 | level_min:1, trained_skill:1, feat:1, dark_side_equals_ability:1 | 3 | skill:2, feat:1 | Force Prodigy, Jedi |
| Vanguard | official | 7 | level_min:1, trained_skill:1, talent:1 | 4 | skill:2, talent_tree:2 | - |
| Force Disciple | official | 12 | level_min:1, trained_skill:1, feat:1, talent:1, force_power:1, force_technique:1 | 7 | talent_tree:3, skill:2, feat:1, force_power:1 | Force Prodigy, Jedi |
| Jedi Master | official | 12 | level_min:1, trained_skill:1, feat:1, weapon_proficiency:1, force_technique:1, special:1, affiliation:1 | 4 | skill:2, feat:2 | Force Prodigy, Jedi |
| Sith Lord | official | 12 | level_min:1, trained_skill:1, feat:1, weapon_proficiency:1, force_technique:1, dark_side_equals_ability:1 | 4 | skill:2, feat:2 | Force Prodigy, Jedi |

## Requirement detail

### Independent Droid

- id: `class_independent_droid`  |  canon: official  |  earliest entry level: **3**
- source text: `Minimum Level: 3rd Trained Skills: Use Computer Droid Systems: Heuristic Processor Special: Must be a Droid`
- parsed requirements:
    - `level_min` - Minimum Level: 3rd
    - `trained_skill` - Trained Skills: Use Computer
    - `other` - Droid Systems: Heuristic Processor
    - `special` - Special: Must be a Droid
- transitive closure (1 options): Use Computer
- **unresolved fragments**: ['Droid Systems: Heuristic Processor']

### Ace Pilot

- id: `class_ace_pilot`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Pilot Feats: Vehicular Combat`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Pilot
    - `feat` - Feats: Vehicular Combat
- transitive closure (2 options): Pilot, Vehicular Combat

### Assassin

- id: `class_assassin`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Stealth Feats: Sniper Talents: Dastardly Strike`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Stealth
    - `feat` - Feats: Sniper
    - `talent` - Talents: Dastardly Strike
- transitive closure (5 options): Dastardly Strike, Point-Blank Shot, Precise Shot, Sniper, Stealth

### Bounty Hunter

- id: `class_bounty_hunter`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Survival Talents: Any two from the Awareness Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Survival
    - `talent` - Talents: Any two from the Awareness Talent Tree
- transitive closure (2 options): Awareness Talent Tree, Survival

### Charlatan

- id: `class_charlatan`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Deception and Persuasion Talents: Any one from the Disgrace Talent Tree, Influence Talent Tree, or Lineage Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Deception and Persuasion
    - `talent` - Talents: Any one from the Disgrace Talent Tree, Influence Talent Tree, or Lineage Talent Tree
- transitive closure (5 options): Deception, Disgrace Talent Tree, Influence Talent Tree, Lineage Talent Tree, Persuasion

### Corporate Agent

- id: `class_corporate_agent`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Gather Information and Knowledge (Bureaucracy) Feats: Skill Focus (Knowledge (Bureaucracy)) Special: Must be employed by a major interstellar corporation`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Gather Information and Knowledge (Bureaucracy)
    - `feat` - Feats: Skill Focus (Knowledge (Bureaucracy))
    - `special` - Special: Must be employed by a major interstellar corporation
- transitive closure (3 options): Gather Information, Knowledge (Bureaucracy), Skill Focus

### Crime Lord

- id: `class_crime_lord`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Deception and Persuasion Talents: Any one from the Fortune Talent Tree, Lineage Talent Tree, or Misfortune Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Deception and Persuasion
    - `talent` - Talents: Any one from the Fortune Talent Tree, Lineage Talent Tree, or Misfortune Talent Tree
- transitive closure (5 options): Deception, Fortune Talent Tree, Lineage Talent Tree, Misfortune Talent Tree, Persuasion

### Droid Commander

- id: `class_droid_commander`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Knowledge (Tactics) and Use Computer Talents: Any one from the Leadership Talent Tree or Commando Talent Tree Special: Must be a Droid`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Knowledge (Tactics) and Use Computer
    - `talent` - Talents: Any one from the Leadership Talent Tree or Commando Talent Tree
    - `special` - Special: Must be a Droid
- transitive closure (4 options): Commando Talent Tree, Knowledge (Tactics), Leadership Talent Tree, Use Computer

### Elite Trooper

- id: `class_elite_trooper`  |  canon: official  |  earliest entry level: **7**
- source text: `Base Attack Bonus: +7 Feats: Armor Proficiency (Medium), Martial Arts I, Point-Blank Shot or Flurry Talents: Any one from the Armor Specialist Talent Tree, Commando Talent Tree, Mercenary Talent Tree, or Weapon Specialist Talent Tree`
- parsed requirements:
    - `bab_min` - Base Attack Bonus: +7
    - `feat` - Feats: Armor Proficiency (Medium), Martial Arts I, Point-Blank Shot or Flurry
    - `armor_proficiency` - armor proficiency (medium)
    - `talent` - Talents: Any one from the Armor Specialist Talent Tree, Commando Talent Tree, Mercenary Talent Tree, or Weapon Specialist Talent Tree
- transitive closure (9 options): Armor Proficiency (Light), Armor Proficiency (Medium), Armor Specialist Talent Tree, Commando Talent Tree, Flurry, Martial Arts I, Mercenary Talent Tree, Point-Blank Shot, Weapon Specialist Talent Tree

### Enforcer

- id: `class_enforcer`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Gather Information and Perception Talents: Any one from the Survivor Talent Tree Special: Must belong to a law enforcement or similar security organization`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Gather Information and Perception
    - `talent` - Talents: Any one from the Survivor Talent Tree
    - `special` - Special: Must belong to a law enforcement or similar security organization
- transitive closure (3 options): Gather Information, Perception, Survivor Talent Tree

### Force Adept

- id: `class_force_adept`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Use the Force Feats: Force Sensitivity Talents: Any three Force Talents`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitivity
    - `talent` - Talents: Any three Force Talents
- transitive closure (2 options): Force Sensitivity, Use the Force

### Gladiator

- id: `class_gladiator`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Minimum Base Attack Bonus: +7 Feats: Improved Damage Threshold, Weapon Proficiency (advanced melee weapons)`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `bab_min` - Minimum Base Attack Bonus: +7
    - `feat` - Feats: Improved Damage Threshold, Weapon Proficiency (advanced melee weapons)
    - `weapon_proficiency` - weapon proficiency (advanced melee weapons)
- transitive closure (2 options): Improved Damage Threshold, Weapon Proficiency

### Gunslinger

- id: `class_gunslinger`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Feats: Point-Blank Shot, Precise Shot, Quick Draw, Weapon Proficiency (Pistols)`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `feat` - Feats: Point-Blank Shot, Precise Shot, Quick Draw, Weapon Proficiency (Pistols)
    - `weapon_proficiency` - weapon proficiency (pistols)
- transitive closure (4 options): Point-Blank Shot, Precise Shot, Quick Draw, Weapon Proficiency

### Imperial Knight

- id: `class_imperial_knight`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Base Attack Bonus: +7 Trained Skills: Use the Force Feats: Force Sensitive, Armor Proficiency (light, medium), Weapon Proficiency (lightsabers)`
- parsed requirements:
    - `bab_min` - Minimum Base Attack Bonus: +7
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitive, Armor Proficiency (light, medium), Weapon Proficiency (lightsabers)
    - `armor_proficiency` - armor proficiency (light, medium)
    - `weapon_proficiency` - weapon proficiency (lightsabers)
- transitive closure (4 options): Armor Proficiency (Light), Force Sensitivity, Use the Force, Weapon Proficiency

### Improviser

- id: `class_improviser`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Mechanics and Use Computer Feat: Skill Focus (Mechanics)`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Mechanics and Use Computer
    - `feat` - Feat: Skill Focus (Mechanics)
- transitive closure (3 options): Mechanics, Skill Focus, Use Computer

### Infiltrator

- id: `class_infiltrator`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Perception and Stealth Feats: Skill Focus (Stealth) Talents: Any two from the Camouflage Talent Tree or Spy Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Perception and Stealth
    - `feat` - Feats: Skill Focus (Stealth)
    - `talent` - Talents: Any two from the Camouflage Talent Tree or Spy Talent Tree
- transitive closure (5 options): Camouflage Talent Tree, Perception, Skill Focus, Spy Talent Tree, Stealth

### Jedi Knight

- id: `class_jedi_knight`  |  canon: official  |  earliest entry level: **7**
- source text: `Base Attack Bonus: +7 Trained Skills: Use the Force Feats: Force Sensitivity, Weapon Proficiency (Lightsabers) Special: Must be a member of The Jedi and have completed Lightsaber Construction`
- parsed requirements:
    - `bab_min` - Base Attack Bonus: +7
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitivity, Weapon Proficiency (Lightsabers)
    - `weapon_proficiency` - weapon proficiency (lightsabers)
    - `special` - Special: Must be a member of The Jedi and have completed Lightsaber Construction
- transitive closure (3 options): Force Sensitivity, Use the Force, Weapon Proficiency

### Martial Arts Master

- id: `class_martial_arts_master`  |  canon: official  |  earliest entry level: **7**
- source text: `Base Attack Bonus: +7 Feats: Martial Arts II, Melee Defense, any Martial Arts Feat Talents: Any one from the Brawler Talent Tree or Survivor Talent Tree`
- parsed requirements:
    - `bab_min` - Base Attack Bonus: +7
    - `feat` - Feats: Martial Arts II, Melee Defense, any Martial Arts Feat
    - `any_of_category` - any martial arts feat
    - `talent` - Talents: Any one from the Brawler Talent Tree or Survivor Talent Tree
- transitive closure (5 options): Brawler Talent Tree, Martial Arts I, Martial Arts II, Melee Defense, Survivor Talent Tree

### Master Privateer

- id: `class_master_privateer`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Deception and Pilot Feats: Vehicular Combat Talents: Any two from the Misfortune Talent Tree, Smuggling Talent Tree, or Spacer Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Deception and Pilot
    - `feat` - Feats: Vehicular Combat
    - `talent` - Talents: Any two from the Misfortune Talent Tree, Smuggling Talent Tree, or Spacer Talent Tree
- transitive closure (6 options): Deception, Misfortune Talent Tree, Pilot, Smuggling Talent Tree, Spacer Talent Tree, Vehicular Combat

### Medic

- id: `class_medic`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Knowledge (Life Sciences) and Treat Injury Feats: Surgical Expertise`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Knowledge (Life Sciences) and Treat Injury
    - `feat` - Feats: Surgical Expertise
- transitive closure (3 options): Knowledge (Life Sciences), Surgical Expertise, Treat Injury

### Melee Duelist

- id: `class_melee_duelist`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Minimum Base Attack Bonus: +7 Feats: Melee Defense, Rapid Strike, Weapon Focus with any melee weapon`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `bab_min` - Minimum Base Attack Bonus: +7
    - `feat` - Feats: Melee Defense, Rapid Strike, Weapon Focus with any melee weapon
    - `weapon_focus` - weapon focus with any melee weapon
- transitive closure (2 options): Melee Defense, Rapid Strike

### Military Engineer

- id: `class_military_engineer`  |  canon: official  |  earliest entry level: **7**
- source text: `Base Attack Bonus: +7 Trained Skills: Mechanics and Use Computer`
- parsed requirements:
    - `bab_min` - Base Attack Bonus: +7
    - `trained_skill` - Trained Skills: Mechanics and Use Computer
- transitive closure (2 options): Mechanics, Use Computer

### Officer

- id: `class_officer`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Knowledge (Tactics) Talents: Any one from the Leadership Talent Tree, Commando Talent Tree, or Veteran Talent Tree Special: Must belong to any organization with a military or paramilitary division`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Knowledge (Tactics)
    - `talent` - Talents: Any one from the Leadership Talent Tree, Commando Talent Tree, or Veteran Talent Tree
    - `special` - Special: Must belong to any organization with a military or paramilitary division
- transitive closure (4 options): Commando Talent Tree, Knowledge (Tactics), Leadership Talent Tree, Veteran Talent Tree

### Outlaw

- id: `class_outlaw`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Stealth and Survival Talents: Any one from the Disgrace Talent Tree or Misfortune Talent Tree Special: You must be wanted by the authorities in at least one star system`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Stealth and Survival
    - `talent` - Talents: Any one from the Disgrace Talent Tree or Misfortune Talent Tree
    - `special` - Special: You must be wanted by the authorities in at least one star system
- transitive closure (4 options): Disgrace Talent Tree, Misfortune Talent Tree, Stealth, Survival

### Pathfinder

- id: `class_pathfinder`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Perception, Survival Talents: Any two from the Awareness Talent Tree, Camouflage Talent Tree, or Survivor Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Perception, Survival
    - `talent` - Talents: Any two from the Awareness Talent Tree, Camouflage Talent Tree, or Survivor Talent Tree
- transitive closure (5 options): Awareness Talent Tree, Camouflage Talent Tree, Perception, Survival, Survivor Talent Tree

### Saboteur

- id: `class_saboteur`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Deception, Mechanics, and Use Computer`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Deception, Mechanics, and Use Computer
- transitive closure (3 options): Deception, Mechanics, Use Computer

### Shaper

- id: `class_shaper`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Knowledge (life sciences), Treat Injury Feat: Biotech Specialist Species: Yuuzhan Vong`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Knowledge (life sciences), Treat Injury
    - `feat` - Feat: Biotech Specialist
    - `species` - Species: Yuuzhan Vong
- transitive closure (5 options): Biotech Specialist, Knowledge (Life Sciences), Mechanics, Treat Injury, Yuuzhan Vong

### Sith Apprentice

- id: `class_sith_apprentice`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Use the Force Feats: Force Sensitive Dark Side Score must equal Wisdom score`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitive
    - `dark_side_equals_ability` - Dark Side Score must equal Wisdom score
- transitive closure (2 options): Force Sensitivity, Use the Force

### Vanguard

- id: `class_vanguard`  |  canon: official  |  earliest entry level: **7**
- source text: `Minimum Level: 7th Trained Skills: Perception and Stealth Talents: Any two from the Camouflage Talent Tree or Commando Talent Tree`
- parsed requirements:
    - `level_min` - Minimum Level: 7th
    - `trained_skill` - Trained Skills: Perception and Stealth
    - `talent` - Talents: Any two from the Camouflage Talent Tree or Commando Talent Tree
- transitive closure (4 options): Camouflage Talent Tree, Commando Talent Tree, Perception, Stealth

### Force Disciple

- id: `class_force_disciple`  |  canon: official  |  earliest entry level: **12**
- source text: `Minimum Level: 12th Trained Skills: Use the Force Feats: Force Sensitivity Talents: Any two from the Dark Side Devotee Talent Tree, Force Adept Talent Tree, or Force Item Talent Tree Force Powers: Farseeing Force Techniques: Any one`
- parsed requirements:
    - `level_min` - Minimum Level: 12th
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitivity
    - `talent` - Talents: Any two from the Dark Side Devotee Talent Tree, Force Adept Talent Tree, or Force Item Talent Tree
    - `force_power` - Force Powers: Farseeing
    - `force_technique` - Force Techniques: Any one
- transitive closure (6 options): Dark Side Devotee Talent Tree, Farseeing, Force Adept Talent Tree, Force Item Talent Tree, Force Sensitivity, Use the Force

### Jedi Master

- id: `class_jedi_master`  |  canon: official  |  earliest entry level: **12**
- source text: `Minimum Level: 12th Trained Skills: Use the Force Feats: Force Sensitivity, Weapon Proficiency (Lightsabers) Force Techniques: Any one Special: Must be a member of The Jedi`
- parsed requirements:
    - `level_min` - Minimum Level: 12th
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitivity, Weapon Proficiency (Lightsabers)
    - `weapon_proficiency` - weapon proficiency (lightsabers)
    - `force_technique` - Force Techniques: Any one
    - `special` - Special: Must be a member of The Jedi
- transitive closure (3 options): Force Sensitivity, Use the Force, Weapon Proficiency

### Sith Lord

- id: `class_sith_lord`  |  canon: official  |  earliest entry level: **12**
- source text: `Minimum Level: 12th Trained Skills: Use the Force Feats: Force Sensitive, Weapon Proficiency (lightsabers) Force Techniques: Any one Dark Side Score must equal Wisdom score`
- parsed requirements:
    - `level_min` - Minimum Level: 12th
    - `trained_skill` - Trained Skills: Use the Force
    - `feat` - Feats: Force Sensitive, Weapon Proficiency (lightsabers)
    - `weapon_proficiency` - weapon proficiency (lightsabers)
    - `force_technique` - Force Techniques: Any one
    - `dark_side_equals_ability` - Dark Side Score must equal Wisdom score
- transitive closure (3 options): Force Sensitivity, Use the Force, Weapon Proficiency

