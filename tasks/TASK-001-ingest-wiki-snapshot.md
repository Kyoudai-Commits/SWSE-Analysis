# TASK-001 - Ingest a wiki snapshot as a provenance-tagged source

**Status:** open | **Priority:** medium | **Gap:** GAP-009

## Problem

The Master Reference embeds 812 wiki URLs (`swse.miraheze.org`, `swse.fandom.com`
for Force powers). Those pages hold rule text - benefit paragraphs, DC tables,
errata - that neither workbook contains. The analysis sandbox has outbound access to
github/pypi/npm only, so nothing was fetched and no record cites wiki content as
evidence.

## Evidence

```bash
python -m swse.cli stats --json | jq '.counts.reference_link'   # 812
```
`attrs.url` is already attached to the records the links describe (the `attach_urls`
hook), and `config/sources.yaml:planned_sources` names both wikis.

## Approach

1. Take a snapshot outside the sandbox (or accept a supplied dump) as JSONL:
   `{url, title, page_type, text, retrieved_utc}`.
2. Register it in `config/sources.yaml` with `kind: jsonl`, `canon: [third_party]`,
   and a recorded sha256. See `docs/adding-sources.md`.
3. One block per page type in `config/blocks.yaml`, joined to existing records on
   `attrs.url` first and on name second.
4. Pages that cite a printed book resolve to `official` via `sourcebook_citation`;
   fan-authored pages stay `third_party` (`webpage_only_citation` must never be
   promoted).

## Acceptance criteria

- [ ] `swse doctor` verifies the snapshot's hash.
- [ ] Records gained text without losing their existing `sources` entries - a wiki
      citation is *added*, never substituted.
- [ ] `validate` reports 0 errors and the join rate is published (how many of the
      812 links matched a record).
- [ ] A test asserts that no record's `canon` was promoted by a URL-only citation.
- [ ] GAP-009 flips to `resolved` with the snapshot id recorded as evidence.

## Files likely to change

`config/sources.yaml`, `config/blocks.yaml`, `config/entities.yaml`,
`swse/hooks.py` (a url-join hook), `tests/test_canonical_data.py`.

## Note

Licensing: wiki text is third-party fan content with its own terms. Keep it behind
the same `NOTICE.md` constraints, store the snapshot outside Git if it is large, and
record retrieval dates so citations remain checkable.
