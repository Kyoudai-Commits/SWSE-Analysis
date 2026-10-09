# Adding a source

The pipeline is built so a new source is a **configuration change**, not a code
change. Adding the SWSE wiki, a printed-book transcription, or a new builder
spreadsheet follows the same five steps.

## 1. Register the source

Add an entry to `config/sources.yaml`:

```yaml
sources:
  - id: swse-wiki-2026-10          # stable, kebab-case; appears in every record's sources[]
    title: "SWSE Wiki (miraheze) snapshot"
    path: sources/swse-wiki.jsonl  # relative to the repo root
    sha256: "<64 hex chars>"       # required - `swse doctor` verifies it
    canon: [third_party]           # what this carrier's content defaults to
    kind: jsonl                    # xlsx | xlsm | jsonl
    notes: "Snapshot taken 2026-10-08; join on attrs.url"
```

`canon` here is the *default* for records this source carries. A record that cites a
published sourcebook is still tagged `official` - canonicity follows content, not
carrier (`attrs.canon_basis` records which rule applied).

Record the hash with `python scripts/hashes.py --write`. Never type one by hand and
never re-pin a hash silently: the digest is what makes a published figure traceable
to specific bytes.

`planned_sources` in the same file lists sources that are wanted but not yet
available (both wikis are there already, with the reason they are unreachable).

## 2. Declare the blocks to read

For a spreadsheet, add one block per table to `config/blocks.yaml`:

```yaml
- id: wiki_force_powers
  source: swse-wiki-2026-10
  sheet: powers
  range: "A2:H400"          # or explicit first_row/last_row/first_col/last_col
  header_row: 1             # 1-based within the range
  require_key: name         # skip rows where this column is empty
  skip_rows: [3, 4]         # section labels, sub-headers
  rename: {power_name: name, prereq: prerequisites_text}
  keep: [name, prerequisites_text, page, effect]
  drop: [internal_id, sort_key]
```

Lessons encoded in these fields, all paid for once already:

- **Pin `last_row` for small sub-tables.** An open range under a sub-table pulls in
  the next section's rows.
- **`require_key` is needed when a table shares rows with helper columns**, otherwise
  blank rows become blank records.
- **Hidden sheets are the real data.** SagaForge's visible sheets are formula-driven
  UI producing `#VALUE!`/`#REF!`; everything useful is in the hidden `Data`
  (417x261) and `Lists` (285x245) sheets.
- **Watch for overlapping ranges.** `Data!BO` and `Data!BV` both describe species
  traits; reading both inflates 131 species into 222. `Lists!AS:AZ` duplicates
  `EV:GH`.
- **Multi-section sheets need one block per section.** `Talents 2` is four pinned
  blocks plus a forms block, not one range.

For a JSONL source, `kind: jsonl` with one block whose `sheet` is the record type;
rows are read as-is and the same rename/keep/drop maps apply.

## 3. Map blocks to entities

In `config/entities.yaml`, add the block id to the entity it produces:

```yaml
feat:
  label: Feat
  role: option
  merge_on: name
  blocks:
    - mr_feats
    - sf_feats
    - wiki_force_powers      # new
  row_hooks: [page_to_sourcebooks]
  post_hooks: [split_class_grants, resolve_sourcebooks, prereq_pass]
```

- `merge_on` decides identity: `name`, `name_and_tree`, `name_and_group`, or a single
  field. Records merge **across sources only**; two same-name rows from one source
  stay separate and are flagged `name_collision`.
- `row_hooks` run per row (see `swse/hooks.py`); `post_hooks` run per entity after
  merging. The standard tail is
  `split_class_grants, audit_class_grants, attach_urls, derive_parameter_axes,
  resolve_sourcebooks, prereq_pass`.
- A record whose name is not a plain column needs a block-level `name_field` or
  `name_template`.

If the new source needs a new entity type, add it here with a `role`
(`core`/`option`/`gear`/`reference`/`analysis`) and a schema-compatible shape.

## 4. Handle sourcebooks and page citations

If the source cites printed books, make sure `config/sourcebooks.yaml` knows the
abbreviation, then add the `page_to_sourcebooks` row hook (or `resolve_sourcebooks`
as a post hook). Source tags in the Master Reference use prefixes (`GoI`, `TFU`,
`JATM`, `KotOR`, `CW`, `SaV`, `LE`, `GAW`, `UR`, `RE`, `SGtD`, `SotG`, `TotG`,
`FUCG`, `CWCG`); a bare number means the Core Rulebook; concatenated tags (`TFULE`)
are split by longest prefix. Unrecognised tags fall back to the `unknown` pseudo
sourcebook and are counted as `unresolved_source_tags` (currently 4).

This hook mattered: before it was wired to the Force blocks, 73 records (58 force
techniques, 15 force secrets) had `attrs.page` but no `sourcebooks`, and were
therefore mis-tagged as third-party. A config-coverage test now fails if a registered
hook is referenced by no block.

## 5. Rebuild and check

```bash
make data                                  # extract -> canonicalize -> db -> validate
python -m swse.cli stats --json            # did counts and the canon split move sensibly?
python -m swse.cli graph --json            # still 0 dangling, 0 cycles?
python -m swse.cli validate --show 20      # triage every new finding
make test
```

Then:

- Triage new warnings. A `name_collision` between the new source and an existing one
  is expected and usually means a real merge - declare it in
  `data/curation/merges.yaml` rather than loosening the merge rule.
- If the new source *contradicts* existing values, the conflict is recorded in
  `conflicts` with the chosen value and its origin. Decide deliberately, and if the
  automatic choice is wrong, override it in `data/curation/overrides.yaml`.
- Close any gap the new source fills: flip its `status` in `data/curation/gaps.yaml`,
  set the matching `verified: true` in `config/analysis.yaml`, and add a test that
  would fail if the gap reopened.
- Add tests: `tests/test_config.py` already asserts every block is referenced by an
  entity, every hook exists and is used, and every sourcebook abbreviation is sane.
  New blocks and hooks are covered automatically; new *entities* need a case in
  `tests/test_canonical_data.py`.

## Worked example: the wikis

`config/sources.yaml:planned_sources` records `swse.miraheze.org` and
`swse.fandom.com`. The join key already exists: 812 `reference_link` records, and
`attrs.url` is attached to the records they describe by the `attach_urls` hook. A
snapshot ingest would be `kind: jsonl`, one block per page type, `merge_on: name`,
canon defaulting to `third_party` (fan content) but resolving to `official` for any
page that cites a printed book. Nothing has been fetched from either host - the
sandbox cannot reach them - so this remains a plan, not a partial implementation.
