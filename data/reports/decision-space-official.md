# Character-creation decision space

Settings: level 20, canon filter `official`, homebrew included, gear excluded, ability method `distinct_vectors`.

## Headline numbers

| measure | value |
|---|---:|
| species usable at level 1 | 121 |
| heroic classes | 5 |
| prestige classes | 32 |
| (species x class) pairs | 605 |
| trained-skill selections across all pairs | 112,078 |
| feats selectable at level 1 | 163 |
| ability-score allocations (distinct_vectors) | 16,777,216 |
| **level-1 core builds** (species x class x skills x feat) | 18,268,714 |
| level-1 builds incl. ability scores | 306,498,160,820,224 |
| level-1 builds incl. destiny + background | 1,240,704,555,000,266,752 |
| legal class paths to level 20 | 191,317,682,744,290,690,087,795,200 |
| feat/talent choices per path to level 20 | 198,565,119,250,954,921,038,572,458,568,919,109,822,549,996,230,366,249 |
| **total space at level 20** | 10^138.07 (analytic (mean skill choices per class, per level)) |
| analytic cross-check | 10^138.07 |

## Dimensions

| key | label | options | kind | gated by | verified |
|---|---|---:|---|---|---|
| `species` | Species | 121 | choice | - | yes |
| `age_category` | Age category | 6 | choice | - | yes |
| `ability_scores` | Ability scores | 16,777,216 | allocation | - | **no** |
| `heroic_class` | Heroic class (1st level) | 5 | choice | - | yes |
| `trained_skills_level1` | Trained skills at 1st level | 949 | derived | heroic_class, ability_scores | yes |
| `feat_level1` | Feat at 1st level | 163 | choice | ability_scores, heroic_class | yes |
| `parameterised_feats` | Parameter choices inside feats | 3,488,400 | parameter | feat_level1 | yes |
| `talent_tree` | Talent trees | 192 | choice | heroic_class | yes |
| `force_powers` | Force powers | 92 | choice | feat:force_sensitivity, feat:force_training | yes |
| `destiny` | Destiny | 88 | choice | - | yes |
| `background` | Background | 46 | choice | - | yes |
| `languages` | Languages | 102 | choice | - | yes |
| `class_path` | Class path to level 20 | 191,317,682,744,290,690,087,795,200 | sequence | heroic_class, level | **no** |
| `feat_grants` | Feat grants over the progression | 10 | derived | - | **no** |
| `talent_grants` | Talent grants over the progression | 10 | derived | - | **no** |
| `droid_sub_space` | Droid build sub-space | 35 | sub_space | species:droid_chassis | yes |
| `near_human_sub_space` | Near-Human customisation sub-space | 24 | sub_space | species:near_human | yes |

## How each dimension is counted

### `species` - Species

- options: **121**
- formula: 121 species records (12 droid_chassis, 109 species)
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

- options: **5**
- formula: 5 classes with class_kind=heroic and min_level<=1 (Jedi, Noble, Scoundrel, Scout, Soldier)
- source: `class entity (Data!BX3:CS42 + Master Reference)`
- verified from data: yes

### `trained_skills_level1` - Trained skills at 1st level

- options: **949**
- formula: sum over heroic classes of C(class skill pool, trained skill count)
- source: `class.attrs.class_skills / trained_skills_per_level`
- verified from data: yes
- notes: Per class: Jedi C(8, 2+Int)=28; Noble C(9, 6+Int)=84; Scoundrel C(10, 4+Int)=210; Scout C(11, 5+Int)=462; Soldier C(11, 3+Int)=165

### `feat_level1` - Feat at 1st level

- options: **163**
- formula: 163 feats with no unsatisfiable prerequisite at level 1 (119 more gated on other options, 103 blocked by numeric gates)
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

- options: **191,317,682,744,290,690,087,795,200**
- formula: paths(L) = paths(L-1) x (#classes available at L); level 1 restricted to heroic
- source: `class.attrs.min_level + config/analysis.yaml:first_level_must_be_heroic`
- verified from data: NO - rests on an assumption in config/analysis.yaml
- notes: 5 heroic + 32 prestige classes.

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

- options: **35**
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
| Jedi | 8 | 2 | 28 | `C(8, 2+Int)` | yes |
| Noble | 9 | 6 | 84 | `C(9, 6+Int)` | yes |
| Scoundrel | 10 | 4 | 210 | `C(10, 4+Int)` | yes |
| Scout | 11 | 5 | 462 | `C(11, 5+Int)` | yes |
| Soldier | 11 | 3 | 165 | `C(11, 3+Int)` | yes |

## Class-path dynamic programme

| level | classes available | cumulative paths |
|---:|---:|---:|
| 1 | 5 | 5 |
| 2 | 5 | 25 |
| 3 | 6 | 150 |
| 4 | 6 | 900 |
| 5 | 6 | 5,400 |
| 6 | 6 | 32,400 |
| 7 | 34 | 1,101,600 |
| 8 | 34 | 37,454,400 |
| 9 | 34 | 1,273,449,600 |
| 10 | 34 | 43,297,286,400 |
| 11 | 34 | 1,472,107,737,600 |
| 12 | 37 | 54,467,986,291,200 |
| 13 | 37 | 2,015,315,492,774,400 |
| 14 | 37 | 74,566,673,232,652,800 |
| 15 | 37 | 2,758,966,909,608,153,600 |
| 16 | 37 | 102,081,775,655,501,683,200 |
| 17 | 37 | 3,777,025,699,253,562,278,400 |
| 18 | 37 | 139,749,950,872,381,804,300,800 |
| 19 | 37 | 5,170,748,182,278,126,759,129,600 |
| 20 | 37 | 191,317,682,744,290,690,087,795,200 |
