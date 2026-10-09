# Data validation report

- errors: **0**
- warnings: **1**
- info: 16

| severity | code | where | message |
|---|---|---|---|
| warning | `name_collision` | `-` | 21 records share a name with another record from the same source and were kept separate; review and declare merges in data/curation/merges.yaml |
| info | `attribute_coverage` | `armor` | armor.type: 90/92 (98%) |
| info | `attribute_coverage` | `class` | class.class_kind: 41/41 (100%) |
| info | `attribute_coverage` | `species` | species.size: 130/130 (100%) |
| info | `attribute_coverage` | `species` | species.speed: 130/130 (100%) |
| info | `attribute_coverage` | `talent` | talent.tree: 1311/1311 (100%) |
| info | `attribute_coverage` | `weapon` | weapon.weapon_group: 233/246 (95%) |
| info | `id_uniqueness` | `-` | 4830 unique ids across 45 entities |
| info | `index_consistency` | `-` | 45 entities indexed, 4830 records |
| info | `prereq_acyclic` | `-` | no circular prerequisites |
| info | `prereq_edges` | `-` | 680 edges, 635 resolved, 0 dangling |
| info | `prereq_parse_coverage` | `-` | 555/563 prerequisite predicates parsed (98.58%); 8 unresolved |
| info | `provenance_complete` | `-` | every record traces to a source workbook row |
| info | `schema_violation` | `-` | all 4830 records match schemas/record.schema.json |
| info | `source_file` | `-` | SagaForge character builder v1.53 verified (sha256 63c903f2fa07...) |
| info | `source_file` | `-` | SWSE Master Reference (2026-10-08) verified (sha256 80cb44f362ac...) |
| info | `sourcebooks_loaded` | `-` | 17 sourcebooks registered |
