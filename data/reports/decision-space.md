# Character-creation decision space

Settings: level 20, canon filter `all`, homebrew included, gear excluded, ability method `distinct_vectors`.

## Headline numbers

| measure | value |
|---|---:|
| species usable at level 1 | 130 |
| heroic classes | 7 |
| prestige classes | 32 |
| (species x class) pairs | 910 |
| trained-skill selections across all pairs | 3,559,510 |
| feats selectable at level 1 | 163 |
| ability-score allocations (distinct_vectors) | 16,777,216 |
| **level-1 core builds** (species x class x skills x feat) | 580,200,130 |
| level-1 builds incl. ability scores | 9,734,142,904,238,080 |
| level-1 builds incl. destiny + background | 39,403,810,476,355,747,840 |
| legal class paths to level 20 | 2,533,086,352,502,117,155,404,251,136 |
| feat/talent choices per path to level 20 | 198,565,119,250,954,921,038,572,458,568,919,109,822,549,996,230,366,249 |
| **total space at level 20** | 10^164.95 (analytic (mean skill choices per class, per level)) |
| analytic cross-check | 10^164.95 |

## Dimensions

| key | label | options | kind | gated by | verified |
|---|---|---:|---|---|---|
| `species` | Species | 130 | choice | - | yes |
| `age_category` | Age category | 6 | choice | - | yes |
| `ability_scores` | Ability scores | 16,777,216 | allocation | - | **no** |
| `heroic_class` | Heroic class (1st level) | 7 | choice | - | yes |
| `trained_skills_level1` | Trained skills at 1st level | 25,718 | derived | heroic_class, ability_scores | yes |
| `feat_level1` | Feat at 1st level | 163 | choice | ability_scores, heroic_class | yes |
| `parameterised_feats` | Parameter choices inside feats | 3,488,400 | parameter | feat_level1 | yes |
| `talent_tree` | Talent trees | 192 | choice | heroic_class | yes |
| `force_powers` | Force powers | 92 | choice | feat:force_sensitivity, feat:force_training | yes |
| `destiny` | Destiny | 88 | choice | - | yes |
| `background` | Background | 46 | choice | - | yes |
| `languages` | Languages | 102 | choice | - | yes |
| `class_path` | Class path to level 20 | 2,533,086,352,502,117,155,404,251,136 | sequence | heroic_class, level | **no** |
| `feat_grants` | Feat grants over the progression | 10 | derived | - | **no** |
| `talent_grants` | Talent grants over the progression | 10 | derived | - | **no** |
| `droid_sub_space` | Droid build sub-space | 493,136,000 | sub_space | species:droid_chassis | yes |
| `near_human_sub_space` | Near-Human customisation sub-space | 24 | sub_space | species:near_human | yes |

## How each dimension is counted

### `species` - Species

- options: **130**
- formula: 130 species records (12 droid_chassis, 118 species)
- source: `species entity (Data!J3:BN133)`
- verified from data: yes
- notes: Beast templates excluded. Droid chassis open the droid sub-space; near-human species open the near-human sub-space.

### `age_category` - Age category

- options: **6**
- formula: 6 age brackets
- source: `age_category entity (Data!A3:G8)`
- verified from data: yes
- notes: Age brackets shift ability scores; species age tables bound which are legal.

### `ability_scores` - Ability scores

- options: **16,777,216**
- formula: (18 - 3 + 1)^6 = 16,777,216
- source: `config/analysis.yaml:distinct_vectors`
- verified from data: NO - rests on an assumption in config/analysis.yaml
- notes: The 3-18 range is the classic dice span, not a rule quoted from either source. Neither workbook states how ability scores are generated; this method exists so the space can be counted at all.

### `heroic_class` - Heroic class (1st level)

- options: **7**
- formula: 7 classes with class_kind=heroic and min_level<=1 (Jedi, Noble, Scoundrel, Scout, Soldier, Force Prodigy, Technician)
- source: `class entity (Data!BX3:CS42 + Master Reference)`
- verified from data: yes

### `trained_skills_level1` - Trained skills at 1st level

- options: **25,718**
- formula: sum over heroic classes of C(class skill pool, trained skill count)
- source: `class.attrs.class_skills / trained_skills_per_level`
- verified from data: yes
- notes: Per class: Jedi C(15, 2+Int)=105; Noble C(16, 6+Int)=8,008; Scoundrel C(17, 4+Int)=2,380; Scout C(18, 5+Int)=8,568; Soldier C(11, 3+Int)=165; Force Prodigy C(18, 4+Int)=3,060; Technician C(14, 7+Int)=3,432

### `feat_level1` - Feat at 1st level

- options: **163**
- formula: 163 feats with no unsatisfiable prerequisite at level 1 (119 more gated on other options, 105 blocked by numeric gates)
- source: `feat entity + swse.prereq predicates`
- verified from data: yes
- notes: Starting feats granted by the class are free and are not counted here.

### `parameterised_feats` - Parameter choices inside feats

- options: **3,488,400**
- formula: product over parameterised feats of their option counts (see attrs.parameter_options)
- source: `derive_parameter_axes hook (weapon groups, skills, languages, exotic weapons)`
- verified from data: yes
- notes: Choosing Weapon Proficiency is not one decision but 1 + 6; Skill Focus is 1 + 25.

### `talent_tree` - Talent trees

- options: **192**
- formula: 192 trees (1311 individual talents)
- source: `talent_tree entity (Master Reference + derived from SagaForge talent rows)`
- verified from data: yes
- notes: Trees are granted by classes; individual talents are the choices.

### `force_powers` - Force powers

- options: **92**
- formula: 92 powers, 58 techniques, 15 secrets
- source: `force_power / force_technique / force_secret entities`
- verified from data: yes
- notes: 1 + Cha modifier at first Force Training, +1 per later Force Training

### `destiny` - Destiny

- options: **88**
- formula: 88 destinies
- source: `destiny entity (Lists!AD2:AG90)`
- verified from data: yes
- notes: Legacy-era destinies grant a bonus, a penalty and a completed effect.

### `background` - Background

- options: **46**
- formula: 46 backgrounds
- source: `background entity (Lists!GL2:GO48)`
- verified from data: yes
- notes: Backgrounds grant bonus trained skills and a language.

### `languages` - Languages

- options: **102**
- formula: 102 languages
- source: `language entity (Lists!AH)`
- verified from data: yes
- notes: Species grants some free; Intelligence and Linguist add more.

### `class_path` - Class path to level 20

- options: **2,533,086,352,502,117,155,404,251,136**
- formula: paths(L) = paths(L-1) x (#classes available at L); level 1 restricted to heroic
- source: `class.attrs.min_level + config/analysis.yaml:first_level_must_be_heroic`
- verified from data: NO - rests on an assumption in config/analysis.yaml
- notes: 7 heroic + 32 prestige classes.

### `feat_grants` - Feat grants over the progression

- options: **10**
- formula: 10 grants at levels [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
- source: `config/analysis.yaml:progression`
- verified from data: NO - rests on an assumption in config/analysis.yaml
- notes: SWSE heroic progression grants a feat at 1st level and every odd level, and a talent at every even level. Class-specific bonus feats (Soldier, Jedi) and prestige-class schedules are handled separately via `class.attrs`.

### `talent_grants` - Talent grants over the progression

- options: **10**
- formula: 10 grants at levels [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
- source: `config/analysis.yaml:progression`
- verified from data: NO - rests on an assumption in config/analysis.yaml

### `droid_sub_space` - Droid build sub-space

- options: **493,136,000**
- formula: chassis x degree x locomotion x quirks x manufacturer x accessories x armor
- source: `droid_option entity + droid_degree/locomotion/shield/translator tables`
- verified from data: yes
- notes: Only reachable by taking a droid chassis as species.

### `near_human_sub_space` - Near-Human customisation sub-space

- options: **24**
- formula: 24 selectable traits (combinations depend on how many are allowed)
- source: `near_human_trait entity (Near-Humans!P4:Q27)`
- verified from data: yes
- notes: Near-Humans remove one base trait and add near-human traits; the trait budget is not in the sources.

## Per-class trained-skill arithmetic

| class | pool | picks | combinations | formula | verified |
|---|---:|---:|---:|---|---|
| Jedi | 15 | 2 | 105 | `C(15, 2+Int)` | yes |
| Noble | 16 | 6 | 8,008 | `C(16, 6+Int)` | yes |
| Scoundrel | 17 | 4 | 2,380 | `C(17, 4+Int)` | yes |
| Scout | 18 | 5 | 8,568 | `C(18, 5+Int)` | yes |
| Soldier | 11 | 3 | 165 | `C(11, 3+Int)` | yes |
| Force Prodigy | 18 | 4 | 3,060 | `C(18, 4+Int)` | yes |
| Technician | 14 | 7 | 3,432 | `C(14, 7+Int)` | yes |

## Class-path dynamic programme

| level | classes available | cumulative paths |
|---:|---:|---:|
| 1 | 7 | 7 |
| 2 | 7 | 49 |
| 3 | 8 | 392 |
| 4 | 8 | 3,136 |
| 5 | 8 | 25,088 |
| 6 | 8 | 200,704 |
| 7 | 36 | 7,225,344 |
| 8 | 36 | 260,112,384 |
| 9 | 36 | 9,364,045,824 |
| 10 | 36 | 337,105,649,664 |
| 11 | 36 | 12,135,803,387,904 |
| 12 | 39 | 473,296,332,128,256 |
| 13 | 39 | 18,458,556,953,001,984 |
| 14 | 39 | 719,883,721,167,077,376 |
| 15 | 39 | 28,075,465,125,516,017,664 |
| 16 | 39 | 1,094,943,139,895,124,688,896 |
| 17 | 39 | 42,702,782,455,909,862,866,944 |
| 18 | 39 | 1,665,408,515,780,484,651,810,816 |
| 19 | 39 | 64,950,932,115,438,901,420,621,824 |
| 20 | 39 | 2,533,086,352,502,117,155,404,251,136 |
