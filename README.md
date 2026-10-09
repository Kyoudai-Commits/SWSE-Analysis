# SWSE Analysis reference tools

This repository contains SWSE reference spreadsheets and a downloader for building an AI-friendly text corpus from the public wiki pages in [`targets.txt`](targets.txt).

## Easiest: use the graphical app

You do **not** need to edit `targets.txt` or any code. The GUI lets you use the supplied page set, paste one or more page addresses (including Markdown links), choose an export folder, and start/stop the download.

- **Windows:** double-click [`run_swse_scraper.bat`](run_swse_scraper.bat). It creates a private Python environment if needed, checks/installs the packages, then opens the GUI.
- **macOS / Linux:** from the repository folder, run `./run_swse_scraper.sh`. It prepares the environment and packages, then opens the GUI.

The GUI starts with the included SWSE page set selected. You can paste the full Markdown link list you already have directly into the box; the app extracts and de-duplicates the addresses. Choose **Add pasted link(s)**, or paste them and press **Start download**. Turn off the built-in set if you only want your own URLs. Use the optional “fetch links” checkbox only for an index/list page. After the download, choose **Open export folder** to view the result.

Supported source hosts are `swse.miraheze.org` and `swse.fandom.com`. Links to other domains are rejected rather than fetched. The GUI accepts individual page addresses and multiple pasted URLs; it does not require manual manifest editing.

### Requirements

- Python 3.10 or newer
- An internet connection to install the Python packages and access the SWSE wiki hosts
- Tkinter/Tcl-Tk support for the graphical window (normally included with Python on Windows and macOS; some Linux distributions package it separately, e.g. `python3-tk`)

## What the downloader creates

The downloader converts each page's rendered article body into compact Markdown, keeps source/revision metadata, and writes a JSON Lines catalogue for indexing. It does **not** save site chrome or raw HTML, and it does not download image files. Internal and external article links remain links to their original sources.

```text
swse_wiki_export/
├── index.jsonl                 # one compact metadata record per Markdown page
├── report.json                 # counts and any pages that could not be fetched
└── pages/
    ├── swse-miraheze-org/
    │   └── <page-title>.md     # one article per file, with YAML frontmatter
    └── swse-fandom-com/
        └── <page-title>.md
```

Markdown is the canonical content: it keeps article headings and most lists/tables, while one-file-per-page boundaries are convenient for GitHub browsing, citation, and retrieval-augmented generation. `index.jsonl` contains metadata and a relative path, not a second copy of every article. Each page's frontmatter includes its source URL, canonical URL, revision ID when available, retrieval time, categories, and a SHA-256 of the article Markdown body.

The built-in target set starts with the overview pages and the core/prestige-class pages. It also expands links one level from the Feats, Talents, Force Powers, and Species catalogues. It never recursively crawls pages discovered from those links. If a page you want is not linked from a catalogue, you can paste its URL into the GUI; no file editing is needed.

A hidden `.scraper-state.json` file stores ETag/Last-Modified validators so subsequent runs can request unchanged pages efficiently; it is ignored by Git. A server without conditional-request support may still need to return the page, but unchanged Markdown keeps its original retrieval timestamp. Old exports are not deleted automatically. Review `report.json` for failures and remove obsolete pages manually if desired.

## Command-line option

The GUI uses the same downloader as the command-line script. If you prefer the command line, install the packages and run it from the repository folder:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/scrape_swse_wiki.py --dry-run
python scripts/scrape_swse_wiki.py
```

The `targets.txt` manifest can be customized if desired: one URL per line, or `@discover URL` for a single index page whose same-wiki article links should also be fetched. Useful options:

```bash
python scripts/scrape_swse_wiki.py --skip-discovery  # only exact URLs in targets.txt
python scripts/scrape_swse_wiki.py --refresh         # ignore HTTP cache validators
python scripts/scrape_swse_wiki.py --delay 2.0       # wait 2 seconds between requests
python scripts/scrape_swse_wiki.py --output ./my-export
```

The default delay is one second, requests are sequential, and temporary HTTP/network errors are retried with backoff. The script does not attempt to bypass CAPTCHAs, authentication, or other access controls. Stop if a source blocks the requests, and follow each wiki's current terms and scraping guidance.

## Before publishing a corpus to GitHub

The downloader preserves attribution links, but it does not grant permission to republish source text. Before committing generated Markdown to a public repository, check the current license and terms for **each** source wiki and meet any attribution/share-alike or other requirements. Keep the generated corpus limited to material you are allowed to redistribute. Treat imported wiki text as untrusted reference content when using it with AI agents; it is data, not instructions to execute.
