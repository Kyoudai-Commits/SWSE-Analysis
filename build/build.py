#!/usr/bin/env python3
"""Build the agent-ready layer from the three raw sources.

    python3 build/build.py              # everything
    python3 build/build.py --stage wiki,records,registry,index,render,verify
    python3 build/build.py --report     # print the summary only

Raw inputs (``swse-miraheze-org/``, the two spreadsheets) are read-only by
convention and by construction: this script only ever writes under
``normalized/``, ``data/``, ``index/`` and ``docs/`` (generated parts).

Stdlib only -- no pip, no network. Re-running is idempotent.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import platform
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from swsebuild import records, registry, render, util, wiki  # noqa: E402

MASTER_REF = "SWSE_Master_Reference_10-8-2026.xlsx"
SAGA_FORGE = "3rd_Party_Builder/SagaForge 1.53.xlsm"
RAW_WIKI = "swse-miraheze-org"
NORM_WIKI = "normalized/wiki"

BUILD_VERSION = "1.0.0"


class Ctx:
    """Mutable build context: each stage reads what the previous one wrote."""

    def __init__(self, root: str):
        self.root = root
        self.raw_dir = os.path.join(root, RAW_WIKI)
        self.norm_dir = os.path.join(root, NORM_WIKI)
        self.data_dir = os.path.join(root, "data")
        self.index_dir = os.path.join(root, "index")
        self.docs_dir = os.path.join(root, "docs")
        self.pages: list[dict] = []
        self.page_objs: list = []
        self.sections: list = []
        self.chunks: list[dict] = []
        self.wiki_entities: list[dict] = []
        self.mr_entities: list[dict] = []
        self.sf_entities: list[dict] = []
        self.entities: list[dict] = []
        self.aliases: list[dict] = []
        self.edges: list[dict] = []
        self.gaps: list[dict] = []
        self.pairs: list[dict] = []
        self.coverage: dict = {}
        self.diffs: list[tuple] = []
        self.mr_extras: dict = {}
        self.sf_extras: dict = {}
        self.meta: dict = {}
        self.xcheck: list[tuple] = []
        self.stats: dict = {}
        self.n_type_files = self.n_book_files = self.n_class_files = 0
        self.manifest_norms: set = set()
        self.xcheck: list = []


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------


def stage_wiki(ctx: Ctx) -> None:
    t0 = time.time()
    raw_files = [f for f in os.listdir(ctx.raw_dir) if f.endswith(".md")]
    raw_bytes = sum(os.path.getsize(os.path.join(ctx.raw_dir, f)) for f in raw_files)
    pages = wiki.load_pages(ctx.raw_dir)
    recs = wiki.emit_pages(pages, ctx.norm_dir, ctx.root)
    for rec in recs:
        rec.pop("_page", None)
    ctx.pages = recs
    util.write_jsonl(os.path.join(ctx.data_dir, "pages.jsonl"), recs)
    n_children = sum(r["n_children"] for r in recs)
    n_same = wiki.mark_cross_duplicates(ctx.norm_dir, ctx.root)
    ctx.stats["wiki"] = {
        "cross_page_duplicate_refs": n_same,
        "raw_files": len(raw_files),
        "raw_bytes": raw_bytes,
        "canonical_pages": len(recs),
        "duplicates_collapsed": sum(r["n_duplicates"] for r in recs),
        "split_pages": sum(1 for r in recs if r["split"]),
        "section_files": n_children,
        "emitted_files": len(recs) + n_children,
        "normalized_bytes": sum(r["chars"] for r in recs),
        "seconds": round(time.time() - t0, 2),
    }


def stage_records(ctx: Ctx) -> None:
    """Re-read the emitted files so every chunk/entity cites real file:line."""
    t0 = time.time()
    objs = wiki.load_normalized(ctx.norm_dir, ctx.root)
    # keep the dedupe / provenance info gathered from the raw pass on its page record
    by_slug = {p["id"]: p for p in ctx.pages}
    for page in objs:
        parent = by_slug.get(page.id)
        if parent:
            page.n_duplicates = parent["n_duplicates"]
            page.duplicates = parent["duplicates"]
    ctx.page_objs = objs
    chunks: list[dict] = []
    ents: list[dict] = []
    for page in objs:
        chunks.extend(records.chunks_for_page(page))
        ents.extend(records.entities_from_page(page))
    ctx.chunks = chunks
    ctx.wiki_entities = ents
    util.write_jsonl(os.path.join(ctx.data_dir, "chunks.jsonl"), chunks)
    ctx.sections = section_rows(objs, by_slug, chunks)
    util.write_jsonl(os.path.join(ctx.data_dir, "sections.jsonl"), ctx.sections)
    ctx.stats["records"] = {
        "files_reloaded": len(objs),
        "sections": len(ctx.sections),
        "chunks": len(chunks),
        "chunk_tokens_max": max(c["tokens"] for c in chunks),
        "chunk_tokens_mean": sum(c["tokens"] for c in chunks) // max(1, len(chunks)),
        "wiki_entities": len(ents),
        "seconds": round(time.time() - t0, 2),
    }


def section_rows(objs, pages_by_id: dict, chunks: list) -> list[dict]:
    """One row per normalized file — a canonical page or one section of a split page.

    This is the unit an agent actually opens, so chunk and entity citations join
    through it: ``chunk.page_id -> section.id -> page.id`` carries provenance
    (revision, sha, source url) down to every fragment of text.
    """
    n_chunks = collections.Counter(c["page_id"] for c in chunks)
    rows = []
    for page in objs:
        meta = page.meta
        pid = meta.get("parent") or page.id
        anc = pages_by_id.get(pid) or {}
        rows.append(
            {
                "id": page.id,
                "page_id": pid,
                "file": page.file,
                "title": meta.get("title") or page.title,
                "heading": meta.get("heading") or "",
                "type": page.type,
                "n_lines": page.line_count,
                "chars": len(page.body),
                "tokens": util.tokens(page.body),
                "categories": meta.get("categories") or anc.get("categories") or [],
                "revision_id": str(meta.get("revision_id") or anc.get("revision_id") or ""),
                "content_sha256": meta.get("content_sha256") or anc.get("content_sha256") or "",
                "source_url": meta.get("source_url") or anc.get("source_url") or "",
                "same_as": meta.get("same_as") or "",
                "n_chunks": n_chunks.get(page.id, 0),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return rows


def stage_sources(ctx: Ctx) -> None:
    """Spreadsheet sources. Optional: each is skipped with a warning if absent."""
    t0 = time.time()
    from swsebuild import sources

    mr_path = os.path.join(ctx.root, MASTER_REF)
    if os.path.exists(mr_path):
        ctx.mr_entities, ctx.mr_extras = sources.extract_master_reference(mr_path)
    sf_path = os.path.join(ctx.root, SAGA_FORGE)
    if os.path.exists(sf_path):
        ctx.sf_entities, ctx.sf_extras = sources.extract_sagaforge(sf_path)
    ctx.stats["sources"] = {
        "master_reference_entities": len(ctx.mr_entities),
        "master_reference_counts": ctx.mr_extras.get("counts", {}),
        "sagaforge_entities": len(ctx.sf_entities),
        "sagaforge_counts": ctx.sf_extras.get("counts", {}),
        "seconds": round(time.time() - t0, 2),
    }


def stage_registry(ctx: Ctx) -> None:
    t0 = time.time()
    merged = registry.merge_entities(ctx.wiki_entities, ctx.mr_entities, ctx.sf_entities)
    # wiki-only metadata that the merge does not carry
    pages_by_slug = {p["slug"]: p for p in ctx.pages}
    for e in merged:
        pid = e.get("page_id") or ""
        pg = pages_by_slug.get(pid.replace("wiki:", "")) if pid.startswith("wiki:") else None
        e["n_duplicates"] = pg["n_duplicates"] if pg else 0
        if e["family"] == "heroic-class" and e.get("fields", {}).get("starting_feats"):
            e["books"] = sorted({c for c in (e.get("categories") or []) if render._looks_like_book(c)} or ["Core Rulebook"])
    ctx.entities = merged

    # alias lexicon: anchor-text synonyms harvested from every raw page
    alias_pairs = []
    for page in ctx.raw_pages_objs:
        for tgt, text in page.meta.get("_alias_pairs") or []:
            alias_pairs.append((tgt, text, page.slug))
    redirects = []
    for rec in ctx.pages:
        for dup in rec.get("duplicate_sources") or []:
            src = (dup.get("source_url") or "").split("/wiki/")[-1]
            if src:
                redirects.append({"from": src.replace("_", " "), "to": rec["slug"]})
    ctx.aliases = registry.build_aliases(ctx.pages, merged, alias_pairs, redirects)
    ctx.edges, ctx.gaps, extra_aliases = registry.build_links(ctx.pages, ctx.aliases)
    if extra_aliases:
        ctx.aliases = ctx.aliases + extra_aliases
    ctx.pairs = registry.pair_rows(ctx.pages)
    ctx.coverage = registry.coverage_report(ctx.pages, merged, ctx.gaps)
    ctx.diffs = [
        (e["id"], e["name"], d["field"], d["values"], d.get("severity", "value"))
        for e in merged
        for d in (e.get("field_diffs") or [])
    ]
    ctx.diffs.sort(key=lambda r: (r[4] != "value", r[1].lower()))
    util.write_jsonl(os.path.join(ctx.data_dir, "aliases.jsonl"), ctx.aliases)
    util.write_jsonl(
        os.path.join(ctx.data_dir, "discrepancies.jsonl"),
        [{"entity_id": a, "name": b, "field": c, "values": d, "severity": e} for a, b, c, d, e in ctx.diffs],
    )
    shards: dict[str, list[dict]] = collections.defaultdict(list)
    for e in merged:
        shards[e["family"]].append(e)
    ent_dir = util.ensure_dir(os.path.join(ctx.data_dir, "entities"))
    for fam, rows in sorted(shards.items()):
        rows.sort(key=lambda e: e["name"].lower())
        util.write_jsonl(os.path.join(ent_dir, f"{util.kebab(fam)}.jsonl"), rows)
    ctx.stats["registry"] = {
        "entities": len(merged),
        "families": {k: len(v) for k, v in sorted(shards.items())},
        "aliases": len(ctx.aliases),
        "resolved_links": len(ctx.edges),
        "gaps": len(ctx.gaps),
        "discrepancies": len(ctx.diffs),
        "seconds": round(time.time() - t0, 2),
    }


def stage_index(ctx: Ctx) -> None:
    t0 = time.time()
    from swsebuild import db

    books: dict[str, dict] = {}
    for name, st in ctx.coverage["by_book"].items():
        books[name] = {"name": name, "abbr": _abbr_of(name), **{k: v for k, v in st.items()}}
    cats: collections.Counter = collections.Counter()
    for p in ctx.pages:
        for c in p.get("categories") or []:
            cats[c] += 1
    counts = db.build(
        os.path.join(ctx.index_dir, "swse.db"),
        ctx.pages,
        ctx.sections,
        ctx.chunks,
        ctx.entities,
        ctx.aliases,
        ctx.pairs,
        ctx.edges,
        ctx.gaps,
        books,
        cats,
        [(a, c, json.dumps({k: v for k, v in d.items()}, ensure_ascii=False) + f" [{e}]") for a, b, c, d, e in ctx.diffs],
        {
            "built_at": ctx.meta["built_at"],
            "build_version": BUILD_VERSION,
            "commit": ctx.meta.get("commit", ""),
            "sources": json.dumps(ctx.meta.get("sources", {})),
        },
    )
    ctx.stats["index"] = {**counts, "seconds": round(time.time() - t0, 2)}


def stage_render(ctx: Ctx) -> None:
    t0 = time.time()
    fill_meta_counts(ctx)
    manifest_slugs = {util.norm_name(m["slug"].replace("_", " ")) for m in (ctx.mr_extras.get("link_manifest") or []) if m.get("slug")}
    ctx.manifest_norms = manifest_slugs
    idx = ctx.index_dir
    ctx.xcheck = cross_check(ctx)
    classes = [e for e in ctx.entities if e["family"] == "heroic-class"]
    # projections first, so INDEX.md can report how many files each produced
    by_type = render.by_type_files(util.ensure_dir(os.path.join(idx, "by-type")), ctx.entities, ctx.root)
    by_book = render.by_book_files(util.ensure_dir(os.path.join(idx, "by-book")), ctx.pages, ctx.entities, ctx.root)
    by_class = render.by_class_files(util.ensure_dir(os.path.join(idx, "by-class")), ctx.pages, ctx.entities, classes, ctx.root)
    util.write_text(os.path.join(idx, "coverage.md"), render.coverage_md(ctx))
    util.write_text(os.path.join(idx, "discrepancies.md"), render.discrepancies_md(ctx))
    util.write_text(os.path.join(idx, "crawl-backlog.md"), render.backlog_md(ctx))
    ctx.n_type_files, ctx.n_book_files, ctx.n_class_files = len(by_type), len(by_book), len(by_class)
    util.write_text(os.path.join(idx, "INDEX.md"), render.index_md(ctx))
    ctx.stats["render"] = {
        "aliases_rows": render.aliases_tsv(os.path.join(idx, "aliases.tsv"), ctx.aliases),
        "backlog_rows": render.gaps_tsv(os.path.join(idx, "crawl-backlog.tsv"), ctx.gaps, manifest_slugs),
        "by_type_files": len(by_type),
        "by_book_files": len(by_book),
        "by_class_files": len(by_class),
        "seconds": round(time.time() - t0, 2),
    }


def stage_verify(ctx: Ctx) -> None:
    from swsebuild import verify

    report = verify.run(ctx)
    ctx.stats["verify"] = report
    util.write_text(os.path.join(ctx.docs_dir, "AUDIT.md"), verify.audit_md(ctx))
    mf = os.path.join(ctx.data_dir, "manifest.json")
    with open(mf, "w", encoding="utf-8") as fh:
        json.dump({"meta": ctx.meta, "stats": ctx.stats, "verify": report}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    if not report["ok"]:
        print("\n".join("  FAIL " + f for f in report["failures"]), file=sys.stderr)
        raise SystemExit(2)


def _abbr_of(book: str) -> str:
    from swsebuild.sources import BOOK_ABBREVS

    return {v: k for k, v in BOOK_ABBREVS.items()}.get(book, "")


# --------------------------------------------------------------------------


def prepare(ctx: Ctx) -> None:
    commit = ""
    try:
        commit = (
            subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ctx.root, capture_output=True, text=True)
            .stdout.strip()
        )
    except OSError:
        pass
    raw = os.path.join(ctx.raw_dir)
    raw_files = [f for f in os.listdir(raw) if f.endswith(".md")]
    raw_text = "".join(util.read_text(os.path.join(raw, f)) for f in raw_files)
    raw_bytes = sum(os.path.getsize(os.path.join(raw, f)) for f in raw_files)
    # measured defects, so the audit never quotes a stale number
    spans = [m.span() for m in re.finditer(r"\[[^\]\n]{0,200}\]\(https?://[^)\s]*/wiki/[^)\n]*\)", raw_text)]
    ctx.raw_audit = {
        "link_markup_bytes": sum(e - s for s, e in spans),
        "link_markup_n": len(spans),
        "noise_loading": raw_text.count("Loading comments..."),
        "noise_redlinks": raw_text.count("?action=edit&redlink=1"),
        "noise_cdn": raw_text.count("static.wikitide.net"),
    }
    ctx.meta = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": commit,
        "build_version": BUILD_VERSION,
        "python": platform.python_version(),
        "n_raw": len(raw_files),
        "raw_tokens": util.tokens(raw_text),
        "n_pages": 0,
        "n_split": 0,
        "n_children": 0,
        "n_dupes": 0,
        "n_chunks": 0,
        "n_entities": 0,
        "n_multi_source": 0,
        "n_aliases": 0,
        "n_links": 0,
        "n_resolved": 0,
        "n_gaps": 0,
        "token_savings_pct": 0,
        "sources": {
            "wiki": {"dir": RAW_WIKI, "files": len(raw_files), "bytes": raw_bytes},
            "master_reference": MASTER_REF,
            "sagaforge": SAGA_FORGE,
        },
    }
    ctx.meta["raw_audit"] = ctx.raw_audit or {}
    ctx.raw_pages_objs = wiki.load_pages(ctx.raw_dir)  # keeps anchor-text alias evidence


def fill_meta_counts(ctx: Ctx) -> None:
    m = ctx.meta
    m["n_pages"] = len(ctx.pages)
    m["n_split"] = sum(1 for p in ctx.pages if p["split"])
    m["n_children"] = sum(p["n_children"] for p in ctx.pages)
    m["n_dupes"] = sum(p["n_duplicates"] for p in ctx.pages)
    m["n_chunks"] = len(ctx.chunks)
    m["n_entities"] = len(ctx.entities)
    m["n_multi_source"] = sum(1 for e in ctx.entities if e.get("n_sources", 1) > 1)
    m["n_aliases"] = len(ctx.aliases)
    m["n_links"] = sum(len(p.get("link_targets") or []) for p in ctx.pages)
    m["n_resolved"] = len(ctx.edges)
    m["n_gaps"] = len(ctx.gaps)
    m["total_tokens"] = sum(p["tokens"] for p in ctx.pages)
    m["chunk_tokens"] = sum(c["tokens"] for c in ctx.chunks)
    m["token_savings_pct"] = round(100 * (1 - m["total_tokens"] / max(1, m["raw_tokens"])), 1)


def cross_check(ctx: Ctx) -> list[tuple]:
    """Reconcile the three inputs so 'not found' is never mistaken for 'absent'."""
    pages_by_norm = {util.norm_name(p["title"]): p for p in ctx.pages}
    mr_feats = [e for e in ctx.mr_entities if e["type"] == "feat"]
    sf_feats = [e for e in ctx.sf_entities if e["type"] == "feat"]
    mr_only = [e for e in mr_feats if util.norm_name(e["name"]) not in pages_by_norm]
    sf_only = [e for e in sf_feats if util.norm_name(e["name"]) not in pages_by_norm]
    wiki_only_feats = [p for n, p in pages_by_norm.items() if p["type"] == "feat" and n not in {util.norm_name(e["name"]) for e in mr_feats}]
    manifest = ctx.mr_extras.get("link_manifest") or []
    not_crawled = [m for m in manifest if util.norm_name(m["slug"].replace("_", " ")) not in {util.norm_name(p["slug"].replace("_", " ")) for p in ctx.pages}]
    rows = [
        ("master_reference feats", len(mr_feats), "rows in the curated workbook"),
        ("… master_reference feats with no wiki page", len(mr_only), "needs a crawl or is spreadsheet-only"),
        ("sagaforge feats", len(sf_feats), "3rd-party list; superset of the workbook"),
        ("… sagaforge feats with no wiki page", len(sf_only), "mostly non-Core books"),
        ("wiki feat pages", sum(1 for p in ctx.pages if p["type"] == "feat"), "crawled feat articles"),
        ("… absent from the workbook", len(wiki_only_feats), "workbook is incomplete, not the wiki"),
        ("Links manifest rows", len(manifest), "URLs the crawl was meant to fetch"),
        ("… never crawled", len(not_crawled), "intended but missing → backlog"),
        ("force powers (workbook)", sum(1 for e in ctx.mr_entities if e["type"] == "force-power"), "cites swse.fandom.com, not miraheze"),
        ("force powers (sagaforge cards)", sum(1 for e in ctx.sf_entities if e["type"] == "force-power"), "has DC/action/target columns"),
        ("talent rows (sagaforge)", sum(1 for e in ctx.sf_entities if e["type"] == "talent"), "individual talents inside trees"),
    ]
    ctx.mr_only_feats = mr_only
    ctx.sf_only_feats = sf_only
    ctx.not_crawled_manifest = not_crawled
    return rows


def summarize(ctx: Ctx) -> None:
    print(json.dumps(ctx.stats, indent=2, default=str))


STAGES = {
    "wiki": stage_wiki,
    "records": stage_records,
    "sources": stage_sources,
    "registry": stage_registry,
    "index": stage_index,
    "render": stage_render,
    "verify": stage_verify,
}
ORDER = list(STAGES)

#: what each stage needs to have run before it, so `--stage verify` cannot write a
#: manifest full of zeros and call it a build
STAGE_DEPS = {
    "wiki": (),
    "records": ("wiki",),
    "sources": ("records",),
    "registry": ("sources",),
    "index": ("registry",),
    "render": ("index",),
    "verify": ("render",),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--stage", default="all", help="comma list of: " + ",".join(ORDER) + " | all")
    ap.add_argument("--report", action="store_true", help="print stats and exit")
    args = ap.parse_args(argv)

    ctx = Ctx(os.path.abspath(args.root))
    prepare(ctx)
    wanted = ORDER if args.stage in ("all", "") else [s.strip() for s in args.stage.split(",")]
    if args.report:
        summarize(ctx)
        return 0
    # every stage's artifacts are committed, so a partial run must still produce a
    # complete manifest/index/AUDIT: pull in the dependency closure, not just the stage asked for
    run = set(wanted)
    changed = True
    while changed:  # transitive closure
        changed = False
        for name, needs in STAGE_DEPS.items():
            if name in run and not set(needs) <= run:
                run |= set(needs)
                changed = True
    run = [name for name in ORDER if name in run]
    for name in run:
        t0 = time.time()
        STAGES[name](ctx)
        print(f"[{name:<9}] ok, {time.time() - t0:.1f}s")
    print()
    summarize(ctx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
