#!/usr/bin/env python3
"""Query API + CLI over the built index — the read side of the pipeline.

This is the *only* module an agent needs at runtime; it degrades gracefully when
the SQLite index is absent (falls back to the JSONL shards) so a partial checkout
still answers questions.

    python3 build/query.py stats
    python3 build/query.py lookup  "Weapon Focus (Lightsabers)"
    python3 build/query.py search  "reroll a d20 after an attack miss"
    python3 build/query.py class   Soldier
    python3 build/query.py book    "Galaxy at War" --family feat
    python3 build/query.py gap     Condition_Track
    python3 build/query.py chain   "Improved Critical"
    python3 build/query.py sql     "SELECT name FROM entity WHERE family='force-power' LIMIT 5"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SWSE_ROOT") or os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from swsebuild import util  # noqa: E402

DB = os.path.join("index", "swse.db")


def db_path(root: str | None = None) -> str:
    return os.path.join(root or ROOT, DB)


def connect(root: str | None = None) -> sqlite3.Connection | None:
    path = db_path(root)
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------
# core operations
# --------------------------------------------------------------------------


def resolve(conn, name: str) -> list[sqlite3.Row]:
    """Name/alias/slug -> entities. Mirrors how a human refers to a rule."""
    norm = util.norm_name(name)
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM entity WHERE norm = ? OR lower(replace(name,' ','_')) = lower(?) COLLATE NOCASE",
            (norm, name.strip()),
        ).fetchall()
    ]
    if rows:
        return rows
    ids = [
        r["target_id"]
        for r in conn.execute("SELECT DISTINCT target_id FROM alias WHERE alias_norm = ?", (norm,)).fetchall()
    ]
    if ids:
        qs = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT * FROM entity WHERE id IN ({qs})", ids).fetchall()
        if rows:
            return rows
    # no typed entity: fall back to the page itself, so "the text exists" is never
    # reported as "no record" (variant anchors, chapter pages, category indexes)
    page = conn.execute(
        "SELECT p.id, p.slug, p.title, p.type, p.file, a.kind FROM page p "
        "JOIN alias a ON a.target_id = p.id WHERE a.alias_norm = ? LIMIT 3",
        (norm,),
    ).fetchall()
    if page:
        return [
            sqlite3.Row  # placeholder replaced below
        ] if False else [
            {
                "id": r["id"],
                "key": r["id"],
                "type": r["type"],
                "family": r["type"],
                "name": r["title"],
                "norm": norm,
                "summary": "",
                "fields": {},
                "prereq": [],
                "prereq_detail": {},
                "books": [],
                "categories": [],
                "sources": ["wiki-page"],
                "file": r["file"],
                "line_start": None,
                "line_end": None,
                "flags": ["page-only", f"resolved-by:{r['kind']}"],
                "n_sources": 1,
            }
            for r in page
        ]
    return []


def lookup(conn, name: str, family: str | None = None, full: bool = False) -> list[dict]:
    rows = resolve(conn, name)
    out = []
    for r in rows:
        if family and r["family"] != family:
            continue
        d = dict(r)
        for key in ("fields", "prereq", "prereq_detail", "books", "categories", "sources", "flags"):
            if key in d:
                try:
                    d[key] = json.loads(d.get(key) or "null")
                except (json.JSONDecodeError, TypeError):
                    pass
                if d.get(key) is None:
                    d[key] = [] if key in ("prereq", "books", "categories", "sources", "flags") else {}
        out.append(d)
    return out


def search(conn, text: str, limit: int = 10) -> list[dict]:
    """FTS5 over chunks; returns file + line range + snippet for citation."""
    q = _fts_query(text)
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.page_id, c.title, c.heading, c.file, c.line_start, c.line_end,
                   c.tokens, rank, snippet(chunk_fts, 3, '>>', '<<', ' … ', 22) AS snip
            FROM chunk_fts f JOIN chunk c ON c.rowid = f.rowid
            WHERE chunk_fts MATCH ? ORDER BY rank LIMIT ?
            """,
            (q, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:  # e.g. sqlite build without FTS5
        return [{"error": str(exc)}]
    return [dict(r) for r in rows]


def search_entities(conn, text: str, limit: int = 15) -> list[dict]:
    q = _fts_query(text)
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.name, e.type, e.family, e.summary, e.file, e.line_start,
                   e.line_end, e.sources, rank
            FROM entity_fts f JOIN entity e ON e.rowid = f.rowid
            WHERE entity_fts MATCH ? ORDER BY rank LIMIT ?
            """,
            (q, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        return [{"error": str(exc)}]
    return [dict(r) for r in rows]


def _fts_query(text: str) -> str:
    """Quote each token so FTS5 operators in the user's phrasing can't break it."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-()]*", text or "")
    if not words:
        return '""'
    return " AND ".join(f'"{w}"' for w in words[:12])


def feats_for_class(conn, cls: str, family: str = "feat") -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, fields, books FROM entity WHERE family = ? AND categories LIKE ?",
        (family, f"%{cls} Bonus Feats%"),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["fields"] = json.loads(d.get("fields") or "{}")
        d["books"] = json.loads(d.get("books") or "[]")
        out.append(d)
    return sorted(out, key=lambda x: x["name"].lower())


def prereq_chain(conn, name: str, depth: int = 3) -> list[dict]:
    """Walk a prerequisite graph — the query that plain grep always gets wrong."""
    seen: dict[str, dict] = {}

    def visit(nm: str, level: int) -> None:
        ents = resolve(conn, nm)
        ent = next((e for e in ents if e["family"] in ("feat", "talent", "talent-tree", "prestige-class")), ents[0] if ents else None)
        key = ent["id"] if ent else util.norm_name(nm)
        if key in seen or level > depth:
            return
        node = {
            "name": nm,
            "resolved": bool(ent),
            "id": ent["id"] if ent else None,
            "file": (ent["file"] if ent else None),
            "line_start": (ent["line_start"] if ent else None),
            "level": level,
            "prerequisites": json.loads((ent["prereq"] if ent else None) or "[]"),
            "children": [],
        }
        seen[key] = node
        if ent:
            for pre in node["prerequisites"]:
                clean = re.sub(r"\s*\(.*?\)\s*$", "", pre).strip()
                if clean and len(seen) < 40:
                    visit(clean, level + 1)
                    node["children"].append(seen.get(util.norm_name(clean)) or {"name": clean, "resolved": False})

    visit(name, 1)
    return list(seen.values())


def gaps_for(conn, name: str) -> list[dict]:
    norm = util.norm_name(name.replace("_", " "))
    rows = conn.execute("SELECT * FROM gap WHERE norm = ? OR target_slug = ?", (norm, name)).fetchall()
    return [dict(r) for r in rows]


def _as_list(val):
    val = _as_obj(val)
    return val if isinstance(val, list) else []


def _as_obj(val):
    if isinstance(val, str):
        try:
            return json.loads(val or "null")
        except json.JSONDecodeError:
            return {} if not val.strip().startswith("[") else []
    return val if val is not None else {}


def manifest_lookup(root: str | None = None) -> dict:
    path = os.path.join(root or ROOT, "data", "manifest.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="query the SWSE index")
    ap.add_argument("cmd", choices=["lookup", "search", "esearch", "class", "chain", "gap", "sql", "stats", "book"])
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--family", "--type", dest="family", default=None)
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--quiet", action="store_true", dest="quiet", help="suppress header lines")
    ap.add_argument("--json", action="store_true", help="raw JSON instead of a table")
    args = ap.parse_args(argv)

    if args.cmd == "stats":
        print(json.dumps(manifest_lookup(), indent=2, default=str))
        return 0

    conn = connect()
    if conn is None:
        print(f"error: {DB} not found — run `python3 build/build.py` first", file=sys.stderr)
        return 3

    if args.cmd == "lookup":
        rows = lookup(conn, args.arg, args.family, full=True)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
            return 0
        if not rows:
            print(f"no record for {args.arg!r} — check `gap` and `search`")
            return 1
        for r in rows:
            print(f"{r['id']}  [{r['type']}]  sources={','.join(_as_list(r['sources']))}")
            if r["summary"]:
                print(f"  summary : {r['summary'][:300]}")
            fields = _as_obj(r["fields"])
            for k, v in list(fields.items())[:8]:
                print(f"  {k:<10}: {str(v)[:240]}")
            if _as_list(r["prereq"]):
                print(f"  prereq  : {'; '.join(_as_list(r['prereq']))[:240]}")
            if _as_list(r["books"]):
                print(f"  books   : {', '.join(_as_list(r['books']))}")
                bp = _as_list(r.get('book_page'))
                if bp:
                    print(f"  pages   : {', '.join('p.' + str(n) for n in bp)}  (cited from 3rd-party builder data)")
            if r["file"]:
                span = f":{r['line_start']}-{r['line_end']}" if r["line_start"] else ""
                print(f"  cite    : {r['file']}{span}")
            flags = _as_list(r["flags"])
            if flags:
                print(f"  flags   : {', '.join(flags)}")
            print()
        return 0

    if args.cmd == "search":
        rows = search(conn, args.arg, args.limit)
    elif args.cmd == "esearch":
        rows = search_entities(conn, args.arg, args.limit)
    elif args.cmd == "class":
        rows = feats_for_class(conn, args.arg, args.family or "feat")
    elif args.cmd == "chain":
        rows = prereq_chain(conn, args.arg)
    elif args.cmd == "gap":
        rows = gaps_for(conn, args.arg)
    elif args.cmd == "book":
        # accept a full book name or its abbreviation ("KotOR" == "Knights of the Old
        # Republic Campaign Guide"); entity.books stores full names, index/by-book uses abbrs
        arg = (args.arg or "").strip()
        hit = conn.execute(
            "SELECT name, abbr FROM book WHERE name = ?1 OR abbr = ?1 OR name LIKE ?2 OR abbr LIKE ?2"
            " COLLATE NOCASE LIMIT 1",
            (arg, f"%{arg}%"),
        ).fetchone()
        pats = [arg] + ([hit["name"], hit["abbr"]] if hit else [])
        params: list = [f"%{p}%" for p in dict.fromkeys(pats) if p]
        sql = "SELECT id, name, family FROM entity WHERE (" + " OR ".join(["books LIKE ?"] * len(params)) + ")"
        if args.family:
            sql += " AND family = ?"
            params.append(args.family)
        sql += " ORDER BY name LIMIT ?"
        params.append(args.limit * 40)
        if hit and not args.quiet and not args.json:
            print(f"# book: {hit['name']} ({hit['abbr']})")
        rows = [dict(r) for r in conn.execute(sql, params)]
    elif args.cmd == "sql":
        cur = conn.execute(args.arg)
        rows = [dict(zip([d[0] for d in cur.description], r)) if cur.description else {} for r in cur.fetchall()]
    else:  # pragma: no cover
        return 2

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
    else:
        for r in rows:
            if "snip" in r:
                print(f"- {r['title']}  {r['file']}:{r['line_start']}-{r['line_end']}  (rank {r.get('rank')})")
                print(f"  {re.sub(chr(10), ' ', r['snip'])[:300]}")
            else:
                keys = [k for k in r if r[k] not in (None, "", [], {}, 0)][:6]
                print("- " + "  ".join(f"{k}={str(r[k])[:80]}" for k in keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
