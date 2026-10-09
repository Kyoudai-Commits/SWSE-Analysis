# Mapping: how the raw sources become the agent layer

This is the design contract for `build/`. It records *why* each transformation exists, so a
future edit can preserve the intent instead of guessing at it. See `docs/AUDIT.md` for the
measured before/after, `docs/SCHEMA.md` for the record shapes, `docs/RETRIEVAL.md` for how the
result is consumed.

## Pipeline

```
                    ┌── stage wiki ──→ normalized/wiki/**        text layer (dedup, clean, split, link-normalize)
 raw sources ───────┤
 (read-only)        ├── stage records → data/pages.jsonl         page records + provenance
                    │                   data/chunks.jsonl         retrieval chunks (heading-aligned, ≤ ~1.1k tok)
                    │                   entities (wiki side)      typed records extracted from page structure
                    ├── stage sources → entities (spreadsheet side)
                    ├── stage registry→ data/entities/*.jsonl     merge + alias + link registry + discrepancies
                    │                   data/aliases.jsonl, discrepancies.jsonl
                    ├── stage index   → index/swse.db             SQLite: relational tables + FTS5
                    ├── stage render  → index/*.md, *.tsv         projections for file-tree consumers
                    └── stage verify  → docs/AUDIT.md + gate      golden tests; non-zero exit on regression
```

Stage order matters and is enforced by `build/build.py`: `records` **re-reads the emitted
normalized files** rather than the in-memory pages, which is what guarantees that every
`file:line` citation resolves.

## Source-of-truth rules

| layer | authority | rule |
| --- | --- | --- |
| page identity | `canonical_url` slug | never the filename: 151 files carry a `-[0-9a-f]{8}` suffix, and 8 URLs can share one slug |
| text | `wiki:` source | wiki prose is the rulebook text; spreadsheets are tables *about* it |
| structured fields | merge by field | `wiki` > `master_reference` > `sagaforge` (see `SOURCE_PRIORITY`), but **only when the values actually differ**; a missing field in one source is not a conflict |
| citations (book + page) | `sagaforge` | only source with per-entry page numbers; propagated into `entity.page_citation.book_page` / `entity.books` |
| naming | entity `key` = `<family>:<norm_name>` | `norm_name` lowercases and strips every non-alphanumeric char, so `Skill Focus (Survival)` and `skill focus survival` collide — which is the point |

## The wiki layer (`swse-miraheze-org/` → `normalized/wiki/`)

1. **Group by canonical slug**, keep the largest body per group (front matter is parsed with a
   small YAML subset reader — `revision_id` is a *quoted string*, so no `yaml` dependency).
2. **Dedup by body hash** (`content_sha256` of the raw file, recomputed): the first file is kept
   as `<slug>.md`, every other one becomes a `same_as: <path>  # reason: duplicate-body` pointer.
   151 raw files collapsed this way; 27 same-content groups remain in the output (empty
   `Category:` stubs) and are marked rather than deleted, because a grep-friendly pointer is
   more useful than a missing file.
3. **Clean**: strip the injected `> Source:` line, `Loading comments...`, the Fandom image
   alias block (`[[alias|...]]`), external `<figure>/<img>` transclusions, `?action=edit`
   redlinks, `File:` links and the `Category :` prefix line. Escape `|` inside table cells as
   `\|` so a chunk never looks like a broken table row.
4. **Normalize links**: `[Text](https://swse.miraheze.org/wiki/Target "Title")` → `[[Target]]`
   (title-cased, underscores). This is the single biggest token win. A second pass converts
   residual `[[Target|Text]]` and `[[Target]]`-style raw forms the export left behind.
5. **Split oversized pages** (> 24,000 chars) on `##` boundaries into `pages/<Slug>/NNN-<heading>.md`
   (and `###` when a single section is still > 40,000 chars). The parent keeps front matter, the
   intro, and an index of its children. 44 pages → 857 section files. Category pages get their
   `Category :` title replaced by `… (Compilation)` / `… (Category)` in *display* titles only;
   `slug`/`id` keep the canonical `Category:Name`.

## Link registry (the hard part)

Every normalized link target is classified:

```
target slug ──► exact page slug?           → resolved (confidence high,  kind: slug)
          ──► redirect alias → page?       → resolved (high,             kind: redirect)
          ──► title/anchor alias → page?   → resolved (medium/high,      kind: anchor|title)
          ──► category prefix + anchor?    → resolved (medium,           kind: variant)
          ──► otherwise                    → gap row (kept, with refs + sample pages)
```

* **Redirect aliases come from the raw crawl**: each collapsed duplicate file's `source_url`
  slug is a name the wiki *redirects* into the canonical page, so it becomes an alias of that page.
* **Anchor aliases are harvested from every page**: `(Text](…/wiki/Target)` pairs where `Target`
  is *not* the obvious reading of `Text` (e.g. anchor "Reflex Defense" → page `Defenses`) become
  `anchor` aliases. That is what makes 1,201 of 5,399 distinct targets resolvable at all.
* **Variant aliases** come from `Category:X` children: `Skill_Focus_(Knowledge_(Bureaucracy))`
  is a *variant* of page `Skill_Focus`, so `kind: variant` and the resolution is marked `variant-name`.
* Approximate resolutions are **also gap rows** (`approx_to`, `approx_by`). Hiding them would
  inflate coverage and delete the crawl backlog's most actionable entries.
* Confidence is recorded per edge (`resolved_link.confidence` = high|medium) and shown on
  lookups as `resolved-by:<kind>`.

## Gaps are first-class data

`data/*.jsonl` has no gap file, but `index/crawl-backlog.{md,tsv}` and the `gap` table do, ranked by
referencing-page count: `rank, target_slug, guess, kind, refs, n_pages, in_master_reference_manifest,
approx_to, approx_by, sample_pages`. `kind` ∈ `category-index | image | rules-term |
frequently-referenced | entity-page`, and `in_master_reference_manifest = 1` means the crawl
*intended* to fetch it — those are the cheap wins (88 of them). The 297 entities with no wiki page
carry flag `no-wiki-page`: they exist in the reference tables, they are just not in this crawl.

## Field extraction (why `fields` is a dict, not a fixed schema)

The wiki writes stat lines as `**Prerequisite:**`, `**Effect:**`, `**Normal:**`, `**Special:**` and
per-class `*Hit Points:*` — 60+ distinct labels across families. Rather than hand-maintaining a
schema per family, `extract_fields` keys them verbatim (snake-cased) and keeps the value as text;
a label whose value ends in `:` takes the following bullet block or paragraph (which is how
prestige-class `**Prerequisites:**` gets its `Minimum Level / Trained Skills / Feats` list). Single
letter keys (`**Q:**`, `**A:**`) are dropped as paragraph markers, but FAQ *answers* on a feat page
are genuine rules clarifications and do land in `fields` — treat `fields` as "the page's own labels",
and prefer the merged canonical trio (`summary`, `benefit`, `prerequisites`) for cross-entity work.

## Entity merge

`build/swsebuild/records.py` produces wiki-side entities (one per page, plus per-entity rows for
feat/talent/power tables), `sources.py` produces spreadsheet-side rows; `registry.merge_entities`
joins them on `key` and:

* keeps the highest-priority non-empty value per field, recording `provenance[field] = source`;
* records `field_diffs` with a **severity** from `util.diff_severity`: `equivalent` (same meaning,
  different abbreviation/punctuation → dropped), `wording` (same facts, paraphrased → kept, quiet),
  `value` (numbers or content words differ → kept, raises `has-field-diffs`);
* attaches `page_citation.book_page` (sagaforge only — the only real page citations in the upload),
  `aliases`, `books`, `categories`, `prerequisites` + `prerequisite_detail` (parsed by
  `util.parse_prerequisites` into `{type, name, qualifier, minimum}`), and `provenance`
  (`source`, `file`, `url`, `revision_id`, `retrieved_at_utc`) so every record states where its text
  came from.

Family is not guessed from the title: it comes from the wiki page's own front matter `type`, else
the `Links` manifest's `guess`, else `other`.

## What we deliberately do **not** do

* No LLM-generated summaries — a model can hallucinate a rule; a citation cannot.
* No prose reconstruction of uncrawled pages, even though the gap list makes it tempting.
* No modification of raw inputs. The xlsx files are read through a stdlib-only
  `zipfile` + shared-strings reader (`build/swsebuild/xlsx.py`) because `openpyxl` is not
  installable in the build environment; the workbook's zero-padded sheets are trimmed by
  `filled_rows()`.
* No embeddings in the repo. `data/chunks.jsonl` is the embedding input; see `docs/RETRIEVAL.md`.
