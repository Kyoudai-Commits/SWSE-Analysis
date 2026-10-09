# NOTICE - data provenance and licensing

## Code

The Python package `swse/`, the tests, the Makefile and the configuration files in
this repository are original work, released under the MIT License (see `LICENSE`).

## Data

The content in `data/canonical/`, `data/raw/`, `data/reports/` and `analysis/out/`
is **transcribed game content that this project does not own**. It was extracted
from two spreadsheets supplied with this repository:

| file | what it is | canon of its contents |
|---|---|---|
| `SWSE_Master_Reference_10-8-2026.xlsx` | a community-maintained reference workbook | mostly official rules text, plus a homebrew section and 812 wiki links |
| `3rd_Party_Builder/SagaForge 1.53.xlsm` | a third-party character builder | mostly official rules text encoded for the builder, plus builder-only content |

The underlying game - *Star Wars Roleplaying Game Saga Edition* - was published by
Wizards of the Coast in 2007 and is out of print. Star Wars itself is a property of
Lucasfilm Ltd. / The Walt Disney Company. Neither Wizards of the Coast, Lucasfilm
nor Disney is associated with, or has endorsed, this repository.

### What follows from that

1. **No commercial use.** Do not sell, license or monetise the dataset or anything
   derived from it.
2. **Attribution.** If you publish an analysis built on this data, credit the source
   workbooks and Wizards of the Coast for the game content.
3. **Citations, not substitutions.** Records keep sourcebook and page references
   (`sourcebooks`, `attrs.page`) so a reader can consult the printed book. This
   repository is an analysis aid, not a replacement for the rulebooks.
4. **Homebrew is labelled.** The two records this repository's sources contributed
   themselves (the Technician and Force Prodigy classes) are marked
   `canon: homebrew` and are excluded from official-only queries. Third-party
   builder content that cites no printed book is marked `canon: third_party`.
5. **Removal on request.** If a rights holder asks, the offending records or the
   whole dataset can be dropped: `data/curation/drops.yaml` exists precisely so that
   removal is a declared, auditable operation rather than a destructive edit.

## Web links

The Master Reference embeds links to `swse.miraheze.org` and `swse.fandom.com`.
Those links are preserved as `reference_link` records and attached to the records
they describe (`attrs.url`). **No content was fetched from them**: the analysis
sandbox has no access to those hosts, and nothing in this repository is copied from
either wiki. Those sites are third-party fan resources with their own terms.

## Regenerating the data

Because the dataset is derived, not authored, it can always be rebuilt from the two
workbooks:

```bash
python -m swse.cli doctor    # confirms both files match their recorded sha256
make data                    # extract -> canonicalize -> db -> validate
```

The sha256 digests in `config/sources.yaml` pin exactly which bytes produced the
committed data, so any published figure can be traced to a specific version of a
specific workbook. If a source file changes, re-record the hash deliberately with
`python scripts/hashes.py --write` - never silently.
