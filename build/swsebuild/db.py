"""SQLite (FTS5) projection: one file, no services, safe for any agent to query.

The database is *derived* and disposable -- everything in it is rebuildable from
``data/*.jsonl``, which is why the schema keeps provenance columns instead of
inventing new truth. FTS5 uses the porter stemmer so "lightsaber", "Lightsabers"
and "lightsabering" all collide, and both tables expose the file + line range so
an agent can jump from a hit to the source text and quote it.
"""

from __future__ import annotations

import json
import os
import sqlite3

SCHEMA = """
PRAGMA journal_mode=MEMORY;

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE page (
  id            TEXT PRIMARY KEY,     -- wiki:<Slug>
  slug          TEXT UNIQUE,
  title       TEXT,
  type        TEXT,
  file        TEXT,                   -- path inside the repo, relative to root
  revision_id INTEGER,
  retrieved_at TEXT,
  chars       INTEGER,
  tokens      INTEGER,
  split       INTEGER DEFAULT 0,
  n_children  INTEGER DEFAULT 0,
  n_duplicates INTEGER DEFAULT 0,
  categories  TEXT                    -- JSON array
);
CREATE INDEX page_type ON page(type);

CREATE TABLE section (
  id        TEXT PRIMARY KEY,         -- wiki:<Slug> or wiki:<Slug>#NNN (a split section)
  page_id   TEXT REFERENCES page(id), -- canonical page this file belongs to
  file      TEXT,
  title     TEXT,
  heading   TEXT,
  type      TEXT,
  n_lines   INTEGER,
  chars     INTEGER,
  tokens    INTEGER,
  categories TEXT,                   -- JSON
  revision_id TEXT,
  content_sha256 TEXT,
  source_url TEXT,
  same_as   TEXT,                     -- identical-text sibling, when one exists
  n_chunks  INTEGER
);
CREATE INDEX section_page ON section (page_id);

CREATE TABLE chunk (
  id        TEXT PRIMARY KEY,         -- wiki:<Slug>#cNN
  page_id   TEXT REFERENCES page(id),
  title     TEXT,
  heading   TEXT,
  -- human forms of the chunk's [[slug]] links + their anchor text: the normalized
  -- files keep only [[Skill_Focus_(Survival)]] to save tokens, so prose searches
  -- for "Skill Focus (Survival)" are answered from this indexed column instead.
  aux       TEXT,
  file      TEXT,
  line_start INTEGER,
  line_end   INTEGER,
  tokens    INTEGER,
  text      TEXT
);
CREATE INDEX chunk_page ON chunk(page_id);

CREATE TABLE entity (
  id        TEXT PRIMARY KEY,         -- <family>:<norm>
  key       TEXT,
  type      TEXT,
  family    TEXT,
  name      TEXT,
  norm      TEXT,
  summary   TEXT,
  fields    TEXT,                     -- JSON
  prereq    TEXT,                     -- JSON (list)
  prereq_detail TEXT,                 -- JSON
  books     TEXT,                     -- JSON (list)
  categories TEXT,                    -- JSON (list)
  sources   TEXT,                     -- JSON (list of source names)
  n_sources INTEGER,
  flags     TEXT,                     -- JSON (list)
  page_id   TEXT,
  file      TEXT,
  url       TEXT,
  heading   TEXT,
  line_start INTEGER,
  line_end  INTEGER,
  sheet     TEXT,
  row       INTEGER,
  book_page TEXT                      -- JSON page numbers (sagaforge is the only source with them)
);
CREATE INDEX entity_family ON entity(family);
CREATE INDEX entity_norm ON entity(norm);
CREATE INDEX entity_name ON entity(name);

CREATE TABLE field (entity_id TEXT, key TEXT, value TEXT);
CREATE INDEX field_key ON field(key);
CREATE INDEX field_ent ON field(entity_id);

CREATE TABLE alias (
  alias TEXT, alias_norm TEXT, target_id TEXT, target_type TEXT, kind TEXT, note TEXT
);
CREATE INDEX alias_norm ON alias(alias_norm);
CREATE INDEX alias_target ON alias(target_id);

CREATE TABLE link (from_page TEXT, to_slug TEXT, n INTEGER);
CREATE INDEX link_from ON link(from_page);
CREATE INDEX link_to ON link(to_slug);

CREATE TABLE resolved_link (target_slug TEXT, to_id TEXT, to_title TEXT, resolved_by TEXT, confidence TEXT, refs INTEGER, n_pages INTEGER);
CREATE INDEX resolved_slug ON resolved_link(target_slug);

CREATE TABLE gap (target_slug TEXT, guess TEXT, norm TEXT, refs INTEGER, n_pages INTEGER, kind TEXT, sample_pages TEXT, approx_to TEXT, approx_by TEXT);
CREATE INDEX gap_refs ON gap(refs DESC);

CREATE TABLE book (name TEXT, abbr TEXT, pages INTEGER, feats INTEGER, talents INTEGER, force_powers INTEGER);
CREATE TABLE category (name TEXT, n_pages INTEGER);
CREATE TABLE discrepancy (entity_id TEXT, field TEXT, vals TEXT);

CREATE VIRTUAL TABLE chunk_fts USING fts5(
  title UNINDEXED, heading UNINDEXED, file UNINDEXED, text, aux,
  content='chunk', content_rowid='rowid', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE entity_fts USING fts5(
  name UNINDEXED, type UNINDEXED, summary, fields,
  content='entity', content_rowid='rowid', tokenize='porter unicode61'
);
"""


def _aux(chunk: dict) -> str:
    """Searchable text the normalized file deliberately dropped: linked page names + anchor text.

    Normalized pages keep ``[[Skill_Focus_(Survival)]]`` instead of the verbose raw
    link, which halves the corpus but loses the prose form. Indexing this column
    restores recall for full-text search without inflating the files.
    """
    names = [
        t.replace("_", " ").replace(" (", "(").replace(") ", ")")
        for t in (chunk.get("links") or [])
    ]
    parts = [chunk["title"], chunk.get("heading") or ""] + names + list(chunk.get("anchor") or [])
    return " / ".join(dict.fromkeys(p.strip() for p in parts if p and len(p) < 200))


def build(
    db_path: str,
    pages: list[dict],
    sections: list[dict],
    chunks: list[dict],
    entities: list[dict],
    aliases: list[dict],
    links: list[dict],
    resolved: list[dict],
    gaps: list[dict],
    books: dict,
    categories: dict,
    diffs: list[dict],
    meta: dict,
) -> dict:
    for suffix in ("", "-wal", "-shm", "-journal"):  # a stale WAL would replay an old schema
        try:
            os.remove(db_path + suffix)
        except OSError:
            pass
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    cur = conn.cursor()

    cur.executemany(
        "INSERT INTO page VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                p["id"], p["slug"], p["title"], p["type"], p["file"],
                int(p["revision_id"]) if str(p.get("revision_id") or "").isdigit() else None,
                p.get("retrieved_at_utc"), p["chars"], p["tokens"],
                1 if p.get("split") else 0, p.get("n_children", 0), p.get("n_duplicates", 0),
                json.dumps(p.get("categories") or []),
            )
            for p in pages
        ],
    )
    cur.executemany(
        "INSERT INTO section VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                s["id"], s["page_id"], s["file"], s["title"], s.get("heading") or "", s["type"],
                s["n_lines"], s["chars"], s["tokens"], json.dumps(s.get("categories") or []),
                s.get("revision_id") or "", s.get("content_sha256") or "", s.get("source_url") or "",
                "; ".join(s["same_as"]) if isinstance(s.get("same_as"), list) else (s.get("same_as") or ""),
                s.get("n_chunks", 0),
            )
            for s in sections
        ],
    )
    cur.executemany(
        "INSERT INTO chunk (id,page_id,title,heading,file,line_start,line_end,tokens,text,aux) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            (
                c["id"], c["page_id"], c["title"], c["heading"], c.get("file", ""),
                c.get("line_start"), c.get("line_end"), c["tokens"], c["text"], _aux(c),
            )
            for c in chunks
        ],
    )
    # external-content FTS: index is derived from the content tables, so build it
    # once *after* all rows for that table exist (see the second rebuild below).
    cur.execute("INSERT INTO chunk_fts(chunk_fts) VALUES ('rebuild')")

    ent_rows, field_rows = [], []
    for e in entities:
        prov = e.get("provenance") or {}
        ent_rows.append(
            (
                e["id"], e["key"], e["type"], e["family"], e["name"], e["norm"], e.get("summary", ""),
                json.dumps(e.get("fields") or {}, ensure_ascii=False),
                json.dumps(e.get("prerequisites") or [], ensure_ascii=False),
                json.dumps(e.get("prerequisite_detail") or {}, ensure_ascii=False),
                json.dumps(e.get("books") or [], ensure_ascii=False),
                json.dumps(e.get("categories") or [], ensure_ascii=False),
                json.dumps(e.get("sources") or [], ensure_ascii=False),
                e.get("n_sources", 1),
                json.dumps(e.get("flags") or [], ensure_ascii=False),
                e.get("page_id") or prov.get("page_id") or "",
                prov.get("file", ""),
                prov.get("url", ""),
                prov.get("heading", ""),
                prov.get("line_start"),
                prov.get("line_end"),
                prov.get("sheet", ""),
                prov.get("row"),
                json.dumps((e.get("page_citation") or {}).get("book_page") or [], ensure_ascii=False),
            )
        )
        for k, v in (e.get("fields") or {}).items():
            field_rows.append((e["id"], k, str(v)[:4000]))
    cur.executemany(
        "INSERT INTO entity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ent_rows
    )
    cur.executemany("INSERT INTO field VALUES (?,?,?)", field_rows)
    cur.execute("INSERT INTO entity_fts(entity_fts) VALUES ('rebuild')")

    cur.executemany(
        "INSERT INTO alias VALUES (?,?,?,?,?,?)",
        [(a["alias"], a["alias_norm"], a["target_id"], a["target_type"], a["kind"], a.get("note", "")) for a in aliases],
    )
    cur.executemany("INSERT INTO link VALUES (?,?,?)", [(l["from"], l["to_slug"], l["n"]) for l in links])
    cur.executemany(
        "INSERT INTO resolved_link VALUES (?,?,?,?,?,?,?)",
        [
            (r["target_slug"], r["to"], r["to_title"], r["resolved_by"], r.get("confidence", "high"), r["refs"], r["n_pages"])
            for r in resolved
        ],
    )
    cur.executemany(
        "INSERT INTO gap VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                g["target_slug"], g["guess"], g["norm"], g["refs"], g["n_pages"], g["kind"],
                json.dumps(g["sample_pages"]), g.get("approx_to", ""), g.get("approx_by", ""),
            )
            for g in gaps
        ],
    )
    cur.executemany(
        "INSERT INTO book VALUES (?,?,?,?,?,?)",
        [(b["name"], b.get("abbr", ""), b.get("pages", 0), b.get("feats", 0), b.get("talents", 0), b.get("force_powers", 0)) for b in books.values()],
    )
    cur.executemany(
        "INSERT INTO category VALUES (?,?)",
        sorted(categories.items(), key=lambda kv: -kv[1]),
    )
    cur.executemany("INSERT INTO discrepancy VALUES (?,?,?)", [tuple(d[:3]) for d in diffs])
    for k, v in meta.items():
        cur.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, json.dumps(v, ensure_ascii=False)))

    conn.commit()
    conn.execute("VACUUM")  # the db file is a committed artifact: ship it compact
    counts = {}
    for tbl in ("page", "section", "chunk", "entity", "field", "alias", "link", "resolved_link", "gap", "book", "category", "discrepancy"):
        counts[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    counts["chunk_fts"] = cur.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0]
    counts["entity_fts"] = cur.execute("SELECT COUNT(*) FROM entity_fts").fetchone()[0]
    conn.close()
    counts["db_bytes"] = os.path.getsize(db_path)
    return counts
