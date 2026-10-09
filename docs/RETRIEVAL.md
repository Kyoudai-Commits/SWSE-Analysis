# Retrieval: how to consume this corpus

One canonical layer (`data/`), three projections. Pick the projection by *question shape*, not by habit.

| mode | good for | bad for | cost |
| --- | --- | --- | --- |
| **A. file tree** (`normalized/`, `index/*.md`) | reading the rulebook text, one-hop navigation, grep | aggregation across 2,328 entities | 1 Read ≈ 1–3 k tokens |
| **B. SQLite** (`index/swse.db`) | exact lookups, set algebra, prerequisites, joins to provenance | long prose passages (chunk text is truncated per row) | one query, ~50–300 tokens |
| **C. chunk manifest** (`data/chunks.jsonl`) | embedding/RAG over the whole corpus at a fixed budget | anything requiring the *whole* page | offline, 1,235,424 tokens total |

All three are produced by `python3 build/build.py`; none is edited by hand.

## A. File tree (agentic grep/Read)

```bash
grep -rl "Condition Track" normalized/wiki/ | head        # which files mention a term
grep -rn "Skill_Focus" normalized/wiki/by-title/Skills.md # links are [[Wiki_Slug]], not prose
head -60 normalized/wiki/by-title/Toughness.md             # a small page: front matter + text
sed -n '104,132p' normalized/wiki/pages/Galaxy_at_War/012-droids.md   # one section of a split mega-page
```

* Start at `index/INDEX.md`; `index/by-type/`, `index/by-book/`, `index/by-class/` are pre-joined
  tables that usually answer a whole class of question in a single read.
* Every normalized file's front matter carries `id`, `type`, `source_url`, `revision_id` — cite the
  path plus the line span you actually read.
* `same_as: <path>` means "identical text lives here too" — read one, not both.

## B. SQLite / CLI

```bash
python3 build/query.py lookup "Weapon Focus" --type feat    # merged record + citation + flags
python3 build/query.py search "flat-footed"                 # BM25 over chunks (snippets + file:line)
python3 build/query.py esearch 'NEAR("Skill Focus" Survival 6)'   # FTS5 syntax
python3 build/query.py class Soldier                        # class build sheet
python3 build/query.py chain "Ace Pilot"                    # prerequisite graph
python3 build/query.py gap "Base_Attack_Bonus"              # why is this not here?
python3 build/query.py book KotOR --type feat
python3 build/query.py sql "SELECT e.name, f.value FROM entity e JOIN field f ON f.entity_id=e.id
                            WHERE e.type='force-power' AND f.key='action' GROUP BY 2 ORDER BY COUNT(*) DESC LIMIT 6"
```

Useful shapes (all verified against the current build):

```sql
-- feats that need a 13 in a mental ability, by book
SELECT name, prereq FROM entity WHERE type='feat' AND prereq LIKE '%Charisma 13%';
-- every chunk of one page, in reading order (for a long-context dump)
SELECT c.id, c.file, c.text FROM chunk c WHERE c.page_id = 'wiki:Defenses' ORDER BY c.line_start;
-- provenance of any chunk: which revision of which page, and its sha
SELECT s.file, s.revision_id, substr(s.content_sha256,1,12) FROM section s WHERE s.id = :page_id;
-- entity coverage of the uncrawled vocabulary
SELECT target_slug, refs, kind, approx_to FROM gap ORDER BY refs DESC LIMIT 20;
```

## C. Chunk manifest (RAG)

`data/chunks.jsonl` — 2,472 chunks, p50 461 / p95 974 / max 1,131 tokens, heading-aligned, each a
verbatim slice of a file with `file`/`line_start`/`line_end`. That is the contract:

* **Retrieve chunks, not pages.** Chunking already happened at `##`/`###` boundaries; oversized
  blocks were split further (`#cNN.M`) so nothing exceeds ~1.2 k tokens.
* **Embed `text`; store `id`, `file`, `line_start`, `line_end`, `title`, `heading_path`, `categories`,
  `book`, `links`.** The last three let you filter by family/source and expand a hit to its neighbours
  without re-chunking.
* **Cite `file:line`, never the embedding score.** A chunk id is re-derivable, a vector is not.
* To rebuild context around a hit: `SELECT … WHERE page_id = <chunk.page_id>` (mode B) or read the
  parent file's index (mode A) for split pages.
* `anchor` + `links` are the graph edges inside the chunk: they turn "one retrieved paragraph" into
  "the two pages that define its terms", which is how you avoid answering a Reflex-defense question
  from a table that merely mentions it.

## Absence protocol

The corpus is a *partial* crawl, so "not found" must be qualified:

1. `lookup` → `gap` → `index/crawl-backlog.md` (ranked by referencing-page count;
   `in_master_reference_manifest=1` means the crawl meant to fetch it).
2. A `resolved-by:variant-name` / `confidence=medium` hit is a **near miss**: e.g. `The_Dark_Side`
   resolves to *Dark Side Talent Tree*, which is not a definition of the term. Report it as such.
3. `flags: ["no-wiki-page"]` (297 entities) means the rules tables define it and the wiki crawl has no
   article. `flags: ["page-only"]` from `query.resolve()` means the reverse: a page exists, no typed
   record was extracted.
4. Say which of the four it is. Never let an agent infer "no rule exists" from "no file matched".

## Evaluation harness

`build/swsebuild/verify.py` doubles as a retrieval test suite: `GOLDEN_LOOKUP` (name → record),
`GOLDEN_FIELD` (record → value), `GOLDEN_ALIAS` / `GOLDEN_RESOLVE` (phrasing → page, with expected
`confidence`), `GOLDEN_SEARCH` (phrase → must retrieve the page), `GOLDEN_ABSENT` / `GOLDEN_APPROX`
(must *stay* unresolved / approximate). Extend it whenever you add an extraction rule: a change that
breaks a golden check is either a regression or a deliberate improvement that needs its expectations
updated in the same commit. For a recall benchmark over your own question set, drive `query.lookup` /
`query.search` from a list and diff against these tables — the same code path both an agent and the CI
gate use.
