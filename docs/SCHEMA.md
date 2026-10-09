# Schemas

Two equivalent views of the same data: **JSONL** (append-only, git-diffable, stream-friendly)
and **SQLite** (relations, FTS5, ad-hoc analytics). JSONL is the source of truth for content;
SQLite is rebuilt from the same in-memory rows, so counts must agree (`verify` asserts it).

## ID conventions

| pattern | means |
| --- | --- |
| `wiki:<Slug>` | a canonical page, e.g. `wiki:Defenses` |
| `wiki:<Slug>#012` | section 12 of a split page (`parent` points at the page) |
| `wiki:<Slug>#cNN` / `#cNN.M` | chunk NN (`.M` = part M of an oversized block) |
| `<type>:<norm>` | entity id, e.g. `feat:a_few_maneuvers`; `key` is the same in readable form (`feat\|a few maneuver`) |

`norm_name` = lowercase, non-alphanumerics stripped. Aliases are resolved on that key only, which
is why punctuation differences never matter.

## `data/pages.jsonl` — one record per canonical page

```jsonc
{
  "id": "wiki:Toughness", "slug": "Toughness", "title": "Toughness", "type": "feat",
  "file": "normalized/wiki/by-title/Toughness.md",
  "n_lines": 14, "chars": 330, "tokens": 84,
  "source_url": "https://swse.miraheze.org/wiki/Toughness",
  "canonical_url": "https://swse.miraheze.org/wiki/Toughness",
  "revision_id": "18567", "retrieved_at_utc": "2026-10-09T07:51:35Z",
  "content_sha256": "…",                       // of the raw file body
  "categories": ["Feats", "Soldier Bonus Feats", "Core Rulebook"],
  "books": ["Core Rulebook"],
  "sections": [ {"title": "…", "line": 9, "level": 2} ],
  "chunk_ids": ["wiki:Toughness#c00"],
  "n_children": 0, "split": false, "child_paths": [],
  "link_targets": ["Hit_Point"], "n_links": 1,
  "duplicate_files": ["theforce-e058a51e.md"],  // raw files collapsed into this page
  "duplicate_sources": [ {"file": "…", "source_url": "…", "content_sha256": "…"} ],
  "n_duplicates": 10,
  "front_matter": {…}                           // verbatim, so nothing is lost
}
```

## `data/sections.jsonl` — one record per normalized file (1,780)

Parents *and* split sections, so any citation resolves:

```jsonc
{ "id": "wiki:Category:Web_Enhancements#141", "page_id": "wiki:Category:Web_Enhancements",
  "file": "normalized/wiki/pages/Web_Enhancements/141-order-the-retreat-and-keep-moving.md",
  "title": "Web Enhancements (Compilation) — Order the Retreat and Keep Moving!",
  "heading": "Order the Retreat and Keep Moving!", "type": "compilation",
  "n_lines": 24, "chars": 1610, "tokens": 402,
  "categories": ["Web Enhancements"], "revision_id": "26287",
  "content_sha256": "…", "source_url": "https://swse.miraheze.org/wiki/Category:Web_Enhancements#…",
  "same_as": "", "n_chunks": 1 }
```

## `data/chunks.jsonl` — retrieval units (heading-aligned, ~≤1.1k tokens)

```jsonc
{
  "id": "wiki:Toughness#c00", "page_id": "wiki:Toughness",
  "file": "normalized/wiki/by-title/Toughness.md", "line_start": 12, "line_end": 14,
  "title": "Toughness", "heading": "Toughness", "heading_only": "", "level": 1,
  "text": "# Toughness\n\n*Reference Book: [[Core_Rulebook]]…",  // verbatim slice of `file`
  "tokens": 84, "chars": 330,
  "links": ["Hit_Point"], "anchor": ["Hit Point"],
  "categories": ["Feats"], "type": "feat", "is_split": false
}
```

Chunk text is *byte-exact* to the cited lines (verified), so a citation can be re-read by any tool.
`anchor` + `links` are what make the FTS `aux` column possible (see below).

## `data/entities/<family>.jsonl` — typed rules records

```jsonc
{
  "id": "feat:assault",                  // <type>:<norm with underscores>
  "key": "feat|assault", "slug": "wiki:Assault", "page_id": "wiki:Assault",
  "name": "Assault", "norm": "assault", "type": "feat", "family": "feat",
  "summary": "…",
  "fields": { "benefit": "…", "prerequisites": "Base Attack Bonus +1", "special": "…" },
  "fields_by_source": { "wiki": { "benefit": "…" }, "sagaforge": { "benefit": "…" } },
  "provenance": { "source": "wiki", "file": "normalized/wiki/by-title/Assault.md",
                  "url": "https://swse.miraheze.org/wiki/Assault", "revision_id": "15649",
                  "retrieved_at_utc": "…" },
  "field_diffs": [ { "field": "benefit", "values": { "wiki": "…", "sagaforge": "…" },
                     "severity": "wording" } ],
  "prerequisites": ["Dodge", "Vehicular Combat"],
  "prerequisite_detail": { "free_text": ["Dodge", "Vehicular Combat"] },   // parsed: type/name/qualifier/minimum
  "page_citation": { "book_page": [57] },      // sagaforge is the only source with page numbers
  "aliases": [], "books": ["SECR"], "categories": ["Feats"],
  "sources": ["wiki", "master_reference", "sagaforge"], "n_sources": 3,
  "n_duplicates": 0, "n_value_diffs": 1,
  "flags": ["from-master-reference", "from-sagaforge", "has-field-diffs"]
  // flags: no-wiki-page | has-field-diffs (real conflict) | has-wording-diffs | sources-agree
  //        from-<source> | resolved-by:slug|redirect|anchor|title|variant-name
}
```

Families (27): `talent` `feat` `talent-tree` `species` `force-power` `class-ability` `rule`
`affiliation` `prestige-class` `index` `skill` `compilation` `action` `weapon` `droid-system`
`heroic-class` `equipment` `weapon-group` `other` `droid` `creature` `challenge` `crew-position`
`planet` `npc` `organization` `armor`. Files are sharded per family so a consumer can stream one
family without loading 2,328 records.

## `data/aliases.jsonl` and `data/discrepancies.jsonl`

```jsonc
// alias: one name variant → one entity or page
{"alias": "Reflex Defense", "alias_norm": "reflexdefense", "entity_id": "rule:defense",
 "page_id": "wiki:Defenses", "kind": "anchor", "source": "wiki"}
// kind: title | slug | source-name | redirect | anchor | variant  (rank: anchor > title > slug > redirect > source-name)

// discrepancy: one field of one entity, values per source, severity from util.diff_severity
{"entity_id": "feat:ace_pilot", "name": "Ace Pilot", "field": "prerequisites",
 "values": {"wiki": "…", "master_reference": "…"}, "severity": "equivalent|wording|value"}
```

## `index/swse.db` — SQLite

14 tables (12 relational + 2 FTS5 virtual, which own 8 `*_fts_*` shadow tables). Read the DDL
live — it is the source of truth, this table is a guide:

```bash
python3 build/query.py sql "SELECT name, sql FROM sqlite_master WHERE type='table'"
```

| table | key columns | notes |
| --- | --- | --- |
| `page` | `id, slug UNIQUE, title, type, file, revision_id, retrieved_at, chars, tokens, split, n_children, n_duplicates, categories` | one row per **canonical** crawled page (923) |
| `section` | `id, page_id → page.id, file, title, heading, type, n_lines, chars, tokens, categories, revision_id, content_sha256, source_url, same_as, n_chunks` | one row per **normalized file** (1,780) — the unit an agent opens; this is what `chunk.page_id` points at, so any fragment of text joins back to its revision |
| `chunk` | `id, page_id → section.id, title, heading, aux, file, line_start, line_end, tokens, text` | `aux` = linked page titles + anchor text, **search-only**: restores prose recall without inflating the `.md` files |
| `chunk_fts` | FTS5 `(title, heading, file UNINDEXED; text, aux)` | external content over `chunk`; `snippet(chunk_fts, 3, …)` = the `text` column |
| `entity` | `id, key, type, family, name, norm, summary, fields, prereq, prereq_detail, books, categories, sources, n_sources, flags, page_id, file, url, heading, line_start, line_end, sheet, row, book_page` | `fields`/`prereq_detail` are JSON; `sheet`+`row` point at the originating spreadsheet cell; `book_page` is the sagaforge page list |
| `entity_fts` | FTS5 `(name, type UNINDEXED; summary, fields)` | |
| `field` | `entity_id, key, value` | one row per entity field — this is where `LIKE`/`GROUP BY` over rules data happens |
| `alias` | `alias, alias_norm, target_id, target_type, kind, note` | `kind` ∈ title \| slug \| source-name \| redirect \| anchor \| variant |
| `link` | `from_page, to_slug, n` | normalized link graph, aggregated per (page, target) |
| `resolved_link` | `target_slug, to_id, to_title, resolved_by, confidence, refs, n_pages` | 1,201 rows; `confidence` ∈ high \| medium |
| `gap` | `target_slug, guess, norm, refs, n_pages, kind, sample_pages, approx_to, approx_by` | 4,198 rows; `approx_to` non-empty ⇒ resolvable only approximately |
| `book` | `name, abbr, pages, feats, talents, force_powers` | per-sourcebook counts, from page categories |
| `category` | `name, n_pages` | 513 wiki categories |
| `discrepancy` | `entity_id, field, vals` | `vals` is the per-source JSON plus a trailing `[severity]` marker |
| `meta` | `key, value` | build manifest (version, commit, source sizes) |

Per-field *source* attribution lives in `data/entities/*.jsonl` (`provenance`, `fields_by_source`),
not in a SQL column — the JSONL layer is the richer record, the DB is the queryable projection.

## Invariants `verify` enforces

* `normalized/` contains no raw wiki URLs and no crawl-noise strings.
* every `file` in pages/sections/chunks/entities exists; `line_start ≤ line_end ≤ n_lines`;
  every chunk `text` is byte-identical to the cited slice of that file.
* **citation integrity in SQL**: `chunk.page_id → section.id → page.page_id` has no orphans
  (`checks["citation_orphans"] == 0`), and DB row counts equal the JSONL counts for
  `page`, `section`, `chunk`, `entity`.
* duplicate-body groups: each member carries a `same_as` pointer to a surviving file.
* golden lookups / field values / alias resolutions / *negative* gaps — see
  `build/swsebuild/verify.py`; a regression fails the build.
