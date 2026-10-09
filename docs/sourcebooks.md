# Sourcebooks and citations

Every record that came from a printed book should say which book and which page.
That citation is what makes `canon: official` mean something, so citation parsing is
a first-class part of the pipeline rather than a cosmetic field.

## The register

`config/sourcebooks.yaml` lists the printed books with an `id`, `title`,
`abbreviation` and `page_prefixes` - the tag strings that appear in the Master
Reference's citation cells. It also contains one pseudo-entry:

```yaml
- id: unknown
  title: "Uncited content"
  abbreviation: "Unknown"
  page_prefixes: []
```

`Unknown` is a deliberate sink, not a mistake: content with a page number but no
recognised tag lands here and is counted, so an unrecognised abbreviation shows up
as a number in the validation report instead of vanishing. Currently 4 source tags
are unresolved.

## How a citation is resolved

1. **Page references.** `page_to_sourcebooks` (row hook) and `resolve_sourcebooks`
   (post hook) read `attrs.page` / page-reference cells, run them through
   `sourcebooks.parse_page_refs()` (which coerces strings to ints and handles
   `12-15`, `12, 15` and multi-cell forms), and attach
   `sourcebooks: [{id, abbreviation, title, page}]`.
2. **Source tags.** The Master Reference prefixes page numbers with a book tag.
   Bare numbers mean the Core Rulebook; concatenated tags are split by longest
   prefix, so `TFULE` becomes `TFU` + `LE` rather than one unknown tag. The legend
   for these lives in `Lists!DY2:EC16` and the supplement map in `Data!IA3:IB12`.
3. **Canonicity.** A record with a resolved sourcebook citation is `official`
   regardless of which workbook carried it (`attrs.canon_basis:
   sourcebook_citation`). A record with no citation inherits its block's declared
   canon (`block_declaration`). Records derived by the pipeline (the 25
   `talent_tree` entries) are `derived_record`. Records whose only citation is a web
   page are `webpage_only_citation` and are **not** promoted to official.

Current split of the basis field across 4,830 records:

| basis | records |
|---|---:|
| `sourcebook_citation` | 2,604 |
| `block_declaration` | 2,182 |
| `derived_record` | 25 |
| `webpage_only_citation` | 19 |

## Tag frequency in the Master Reference

| tag | count | tag | count | tag | count |
|---|---:|---|---:|---|---:|
| GoI | 189 | RE | 76 | TotG | 21 |
| TFU | 164 | SGtD | 52 | FUCG | 20 |
| JATM | 157 | SotG | 27 | CWCG | 19 |
| KotOR | 140 | | | | |
| CW | 139 | | | | |
| SaV | 135 | | | | |
| LE | 123 | | | | |
| GAW | 101 | | | | |
| UR | 78 | | | | |

## Web links are not citations

812 `reference_link` records carry URLs to `swse.miraheze.org` and
`swse.fandom.com`, and the `attach_urls` hook puts them on the records they describe
as `attrs.url`. They are pointers for a human reader and a join key for a future
ingest. They are not evidence of canonicity: fan-wiki text is not a published book,
and none of it was fetched (the sandbox cannot reach those hosts - see GAP-009).

## Why this file matters to an agent

If you are about to claim a rule is official, check the record's `sourcebooks` first.
Three failure modes this catches:

- A record with `canon_basis: block_declaration` is official only because the block
  was declared official - that is a config assertion, not a citation.
- A record whose only citation is a URL is `webpage_only_citation`.
- A record citing `Unknown` has a page number nobody could attribute; treat the
  canonicity as unconfirmed.

Wiring `page_to_sourcebooks` to the three Force blocks moved 73 records from
`third_party` to `official`. Citation coverage is therefore not a detail - it changes
the canon split, and through it every `--canon official` figure in
`data/reports/decision-space-official.md`.
