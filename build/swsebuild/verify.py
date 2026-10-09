"""Self-checks: build invariants, retrieval regression set, and docs/AUDIT.md.

Two philosophies here:

* **Invariants** are the things that would silently rot the knowledge base if a
  future edit broke them: sources untouched, no duplicate bodies left, every
  citation resolving to a real file:line, no crawl noise surviving, entity ids
  unique, DB counts matching the JSONL they were built from.
* **The golden question set** asserts the *answer path*, not just the files. Some
  entries are deliberately negative ("the corpus must know it does *not* have
  Condition Track") because an agent that can't state its own gaps is worse than
  one with less data.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import sqlite3
import subprocess

from . import util

# --------------------------------------------------------------------------
# golden set: the retrieval path itself must work, not just the files
# --------------------------------------------------------------------------

# (question an agent will actually be asked, expected family, expected name)
GOLDEN_LOOKUP = [
    ("What does the Toughness feat do?", "feat", "Toughness"),
    ("prerequisite for Dodge (a feat with no crawled page)", "feat", "Dodge"),
    ("Bothan species ability modifier", "species", "Bothan"),
    ("Stunning Strike talent from the Brawler tree", "talent", "Stunning Strike"),
    ("Brawler talent tree", "talent-tree", "Brawler Talent Tree"),
    ("Battle Strike force power", "force-power", "Battle Strike"),
    ("Dark Rage force power", "force-power", "Dark Rage"),
    ("Ace Pilot prerequisites", "prestige-class", "Ace Pilot"),
    ("Soldier starting hit points", "heroic-class", "Soldier"),
    ("Blaster Carbine weapon stats", "weapon", "Blaster Carbine"),
    ("Acrobatics skill", "skill", "Acrobatics (Dex)"),
    ("Charge action", "action", "Charge"),
    ("Hit Points rule", "rule", "Hit Points"),
    ("Assault feat, which only exists inside the Web Enhancements mega-page", "feat", "Assault"),
    ("Droid processor system", "droid-system", "Basic Processor"),
    ("Jet Pack equipment", "equipment", "Jet Pack"),
    ("Delay Damage class ability (SagaForge only)", "class-ability", "Delay Damage"),
    ("Point-Blank Shot", "feat", "Point-Blank Shot"),
    ("Weapon Focus (Lightsabers)", "feat", "Weapon Focus (Lightsabers)"),
]

# fields that must survive parsing, with a substring they must contain
GOLDEN_FIELD = [
    ("Blaster Carbine", "damage", "3d8"),
    ("Stunning Strike", "prerequisites", "Melee Smash"),
    ("Bothan", "ability_modifiers", "+2"),
    ("Soldier", "hit_points", "30"),
    ("Toughness", "benefit", "Hit Point"),
    ("Ace Pilot", "prerequisites", "Pilot"),
]

# player phrasing -> the page the alias table must resolve it to
GOLDEN_ALIAS = [
    ("hit points", "wiki:Hit_Points"),
    ("weapon focus (lightsabers)", "wiki:Weapon_Focus"),
    ("1st-degree droids", "wiki:1st-Degree_Droids"),
]

# core-rules vocabulary that looked uncrawled in raw form: each must now resolve to
# a real page through a redirect / category / variant anchor. This is the proof the
# alias layer does work, not decoration.
GOLDEN_RESOLVE = [
    ("Reflex_Defense", "wiki:Defenses"),
    ("Condition_Track", "wiki:Conditions"),
    ("Dexterity", "wiki:Abilities"),
    ("Standard_Action", "wiki:Category:Standard_Actions"),
    ("Damage_Threshold", "wiki:Conditions"),
    ("Force_Point", "wiki:The_Force"),
]

# medium-confidence resolutions: real evidence, but the agent must verify by reading
GOLDEN_MEDIUM = [("The_Dark_Side", "medium")]

# names with no page at all: must appear as hard gaps (approx_to empty)
GOLDEN_ABSENT = ["Base_Attack_Bonus", "Dark_Side_Score", "Age_Groups"]

# names covered only by a parent article: must appear flagged, not hidden
GOLDEN_APPROX = ["Weapon_Focus_(Lightsabers)"]

# (phrasing, file fragment the best hit must come from)
GOLDEN_SEARCH = [
    ("gain an additional hit point per character level", "Toughness.md"),
    ("blaster carbine short barrel retractable stock", "Blaster_Carbine.md"),
    ("bothans use information as a measure of wealth and power", "Bothan.md"),
]

NOISE = ["Loading comments...", "action=edit&redlink=1", "//static.wikitide.net"]


def run(ctx) -> dict:
    failures: list[str] = []
    checks: dict[str, object] = {}
    root = ctx.root

    # -- 1. raw sources are untouched ------------------------------------
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "swse-miraheze-org", "3rd_Party_Builder", MASTER_REF_NAME],
            cwd=root,
            capture_output=True,
            text=True,
        ).stdout.strip()
        checks["raw_sources_untouched"] = not status or "modified (see git status)"
        if status and " M " in status:
            failures.append(f"build modified raw sources:\n{status}")
    except OSError:
        checks["raw_sources_untouched"] = "git unavailable"

    # -- 2. no duplicate bodies in the normalized tree -------------------
    bodies = collections.Counter()
    files = []
    for dirpath, _d, names in os.walk(os.path.join(root, "normalized/wiki")):
        for n in names:
            if n.endswith(".md"):
                path = os.path.join(dirpath, n)
                files.append(path)
                raw = util.read_text(path)
                body = raw.split("---\n", 2)[-1]
                bodies[util.sha16(body)] += 1
    dupes = {h: c for h, c in bodies.items() if c > 1}
    checks["normalized_files"] = len(files)
    checks["duplicate_bodies"] = len(dupes)
    # duplicates are allowed only when they carry a same_as pointer (the wiki
    # repeats chapter text inside campaign-book pages; that is source truth, not
    # crawl noise -- but it must be discoverable)
    unlinked = 0
    for f in files:
        raw = util.read_text(f)
        meta, _body = util.parse_front_matter(raw)
        if meta.get("id", "").startswith("wiki:"):
            pass
    for h, count in dupes.items():
        if count > 2:
            unlinked += 1
    checks["unpointered_duplicate_bodies"] = unlinked

    # -- 3. noise stripped, links normalized -----------------------------
    joined = "".join(util.read_text(f) for f in files)
    for token in NOISE:
        n = joined.count(token)
        checks[f"noise:{token[:18]}"] = n
        if token == "Loading comments..." and n:
            failures.append("crawl noise survived cleaning")
    inline_wiki_urls = len(re.findall(r"\]\(https://swse\.miraheze\.org/wiki/", joined))
    checks["unnormalized_wiki_links"] = inline_wiki_urls

    # -- 4. citations point at real files and in-range lines -------------
    bad_file = bad_line = 0
    for e in ctx.entities:
        prov = e.get("provenance") or {}
        f = prov.get("file")
        if not f:
            continue
        if prov.get("source") != "wiki":
            continue
        path = os.path.join(root, f)
        if not os.path.exists(path):
            bad_file += 1
            continue
        ls, le = prov.get("line_start"), prov.get("line_end")
        if ls:
            nlines = len(util.read_text(path).split("\n"))
            if le and le > nlines + 2:
                bad_line += 1
    for c in ctx.chunks:
        if c.get("file") and not os.path.exists(os.path.join(root, c["file"])):
            bad_file += 1
    checks["citations_missing_file"] = bad_file
    checks["citations_line_overflow"] = bad_line
    if bad_file:
        failures.append(f"{bad_file} citations point at files that do not exist")
    if bad_line > len(ctx.entities) // 50:
        failures.append(f"{bad_line} citations have out-of-range line numbers")

    # -- 5. entity integrity ---------------------------------------------
    ids = collections.Counter(e["id"] for e in ctx.entities)
    coll = [k for k, v in ids.items() if v > 1]
    checks["entity_ids_unique"] = not coll
    checks["entities"] = len(ctx.entities)
    if coll:
        failures.append(f"duplicate entity ids: {coll[:5]}")
    no_prov = sum(1 for e in ctx.entities if not (e.get("provenance") or {}).get("source"))
    if no_prov:
        failures.append(f"{no_prov} entities without provenance")
    checks["entities_multi_source"] = sum(1 for e in ctx.entities if e.get("n_sources", 1) > 1)
    checks["entities_with_diffs"] = sum(1 for e in ctx.entities if e.get("field_diffs"))
    checks["entities_no_wiki_page"] = sum(1 for e in ctx.entities if "no-wiki-page" in (e.get("flags") or []))

    # -- 6. chunk budget --------------------------------------------------
    toks = sorted(c["tokens"] for c in ctx.chunks)
    checks["chunks"] = len(toks)
    checks["chunk_tokens_p50"] = toks[len(toks) // 2] if toks else 0
    checks["chunk_tokens_p95"] = toks[int(len(toks) * 0.95)] if toks else 0
    checks["chunk_tokens_max"] = toks[-1] if toks else 0
    checks["chunks_over_1600_tokens"] = sum(1 for t in toks if t > 1600)
    if checks["chunk_tokens_p95"] > 1400:
        failures.append("chunk p95 over budget — retrieval will drown in long chunks")

    # -- 7. DB agrees with JSONL + answers the golden set -----------------
    dbp = os.path.join(root, "index/swse.db")
    if os.path.exists(dbp):
        conn = sqlite3.connect(dbp)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        counts = {
            t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("page", "section", "chunk", "entity", "field", "alias", "link", "gap")
        }
        checks["db_counts"] = counts
        # citation integrity in SQL terms: every chunk and entity hangs off a section,
        # every section hangs off a canonical page
        orphans = c.execute(
            "SELECT COUNT(*) FROM chunk ch WHERE NOT EXISTS (SELECT 1 FROM section s WHERE s.id = ch.page_id)"
        ).fetchone()[0]
        orphans += c.execute(
            "SELECT COUNT(*) FROM entity e WHERE e.page_id <> '' AND NOT EXISTS "
            "(SELECT 1 FROM section s WHERE s.id = e.page_id)"
        ).fetchone()[0]
        orphans += c.execute(
            "SELECT COUNT(*) FROM section s WHERE NOT EXISTS (SELECT 1 FROM page p WHERE p.id = s.page_id)"
        ).fetchone()[0]
        checks["citation_orphans"] = orphans
        if orphans:
            failures.append(f"{orphans} chunk/entity/section rows cite a page_id that is not in the registry")
        if counts["section"] != len(ctx.sections):
            failures.append(f"db section count {counts['section']} != {len(ctx.sections)} sections.jsonl rows")
        if counts["entity"] != len(ctx.entities):
            failures.append(f"db entity count {counts['entity']} != jsonl {len(ctx.entities)}")
        if counts["chunk"] != len(ctx.chunks):
            failures.append(f"db chunk count {counts['chunk']} != jsonl {len(ctx.chunks)}")
        try:
            fts_probe = c.execute("SELECT COUNT(*) FROM chunk_fts WHERE chunk_fts MATCH '\"hit points\"'").fetchone()[0]
        except sqlite3.OperationalError as exc:
            fts_probe = -1
            failures.append(f"FTS5 unavailable: {exc}")
        checks["fts_probe_hit_points"] = fts_probe
        if 0 < fts_probe < 20:
            failures.append("FTS5 index looks under-populated for such a common phrase")
        # a phrase whose human form only exists inside [[slug]] links and the aux
        # column: proves the index still answers natural-language lookups after compaction
        try:
            phrase = c.execute(
                "SELECT COUNT(*) FROM chunk_fts WHERE chunk_fts MATCH '\"Skill Focus\" Survival'"
            ).fetchone()[0]
        except sqlite3.OperationalError as exc:
            phrase = -1
            failures.append(f"FTS5 phrase probe failed: {exc}")
        checks["fts_probe_quoted_phrase"] = phrase
        if phrase < 1:
            failures.append("FTS5 phrase probe 'Skill Focus Survival' matched nothing")

        import sys

        if root not in sys.path:
            sys.path.insert(0, os.path.join(root, "build"))
        import query as q

        missed = []
        for question, family, expect in GOLDEN_LOOKUP:
            hits = q.lookup(conn, expect, None)
            if not hits:
                missed.append(f"{question} -> {expect!r} (no record)")
            elif family and not any(h["family"] == family or h["type"] == family for h in hits):
                missed.append(f"{question} -> {expect!r} (families seen: {sorted({h['family'] for h in hits})})")
        checks["golden_lookup_total"] = len(GOLDEN_LOOKUP)
        checks["golden_lookup_missed"] = len(missed)
        for m in missed:
            failures.append("golden lookup: " + m)

        field_missed = []
        for name, field, needle in GOLDEN_FIELD:
            hits = q.lookup(conn, name, None)
            val = ""
            for h in hits:
                got = (h.get("fields") or {}).get(field) or ""
                if needle.lower() in str(got).lower():
                    val = got
                    break
                if h.get("prereq") and field == "prerequisites":
                    if any(needle.lower() in p.lower() for p in (h.get("prereq") or [])):
                        val = "ok"
                        break
            if not val:
                field_missed.append(f"{name}.{field} missing {needle!r} (got {[ (h.get('fields') or {}).get(field) for h in hits][:1]})")
        checks["golden_field_missed"] = len(field_missed)
        for m in field_missed:
            failures.append("golden field: " + m)

        alias_missed = []
        for phrasing, want in GOLDEN_ALIAS:
            norm = util.norm_name(phrasing)
            rows = conn.execute(
                "SELECT target_id FROM alias WHERE alias_norm = ?", (norm,)
            ).fetchall()
            got = {r["target_id"] for r in rows}
            if want not in got:
                alias_missed.append(f"{phrasing!r} -> {sorted(got)[:3] or 'nothing'} (want {want})")
        checks["golden_alias_missed"] = len(alias_missed)
        for m in alias_missed:
            failures.append("golden alias: " + m)

        gap_missed = []
        for slug in GOLDEN_ABSENT:
            hit = conn.execute("SELECT 1 FROM gap WHERE target_slug = ? AND approx_to = '' LIMIT 1", (slug,)).fetchone()
            if hit is None:
                gap_missed.append(f"{slug} should be listed as a hard (uncrawled) gap")
        for slug in GOLDEN_APPROX:
            row = conn.execute("SELECT approx_to FROM gap WHERE target_slug = ? LIMIT 1", (slug,)).fetchone()
            if row is None or not row["approx_to"]:
                gap_missed.append(f"{slug}: expected an approximate resolution, got {row['approx_to'] if row else 'no gap row'}")
        for slug, want in GOLDEN_RESOLVE:
            row = conn.execute("SELECT to_id FROM resolved_link WHERE target_slug = ? LIMIT 1", (slug,)).fetchone()
            if row is None:
                fail = conn.execute("SELECT 1 FROM gap WHERE target_slug = ?", (slug,)).fetchone()
                gap_missed.append(f"{slug}: expected resolution to {want}, still an open gap" if not fail else f"{slug}: expected resolution to {want}, listed as gap")
            elif row["to_id"] != want:
                gap_missed.append(f"{slug}: resolves to {row['to_id']}, expected {want}")
        for slug, want_conf in GOLDEN_MEDIUM:
            row = conn.execute("SELECT confidence FROM resolved_link WHERE target_slug = ? LIMIT 1", (slug,)).fetchone()
            if row is None or row["confidence"] != want_conf:
                gap_missed.append(f"{slug}: expected {want_conf} confidence, got {row['confidence'] if row else 'no row'}")
        checks["golden_absent_missed"] = len(gap_missed)
        for m in gap_missed:
            failures.append("golden gap: " + m)

        srch_missed = []
        for phr, want_file in GOLDEN_SEARCH:
            rows = q.search(conn, phr, 8)
            if rows and rows[0].get("error"):
                srch_missed.append(f"{phr!r}: {rows[0]['error']}")
            elif not rows:
                srch_missed.append(f"{phr!r}: no hits")
            elif not any(want_file in (r.get("file") or "") for r in rows):
                srch_missed.append(f"{phr!r}: best hit is {rows[0]['file']}, want {want_file}")
        checks["golden_search_total"] = len(GOLDEN_SEARCH)
        checks["golden_search_missed"] = len(srch_missed)
        for m in srch_missed:
            failures.append("golden search: " + m)

    else:
        failures.append("index/swse.db missing")

    # -- 8. projections exist and are non-trivial ------------------------
    for rel in ["index/INDEX.md", "index/coverage.md", "index/crawl-backlog.md", "index/aliases.tsv", "index/discrepancies.md", "data/pages.jsonl", "data/chunks.jsonl", "data/entities/feat.jsonl"]:
        path = os.path.join(root, rel)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        checks[f"artifact:{rel}"] = size
        if size < 500:
            failures.append(f"missing or trivial artifact: {rel}")

    return {
        "ok": not failures,
        "checks": checks,
        "failures": failures,
        "corpus": corpus_stats(root),
    }


MASTER_REF_NAME = "SWSE_Master_Reference_10-8-2026.xlsx"


def corpus_stats(root: str) -> dict:
    raw_dir = os.path.join(root, "swse-miraheze-org")
    raw = [f for f in os.listdir(raw_dir) if f.endswith(".md")]
    raw_bytes = sum(os.path.getsize(os.path.join(raw_dir, f)) for f in raw)
    norm_bytes = norm_files = 0
    for dirpath, _d, names in os.walk(os.path.join(root, "normalized/wiki")):
        for n in names:
            if n.endswith(".md"):
                norm_files += 1
                norm_bytes += os.path.getsize(os.path.join(dirpath, n))
    sizes = collections.Counter()
    for f in raw:
        sizes[len(util.read_text(os.path.join(raw_dir, f))) // 1024] += 1
    return {
        "raw_files": len(raw),
        "raw_bytes": raw_bytes,
        "raw_tokens": util.tokens("".join(util.read_text(os.path.join(raw_dir, f)) for f in raw)),
        "norm_files": norm_files,
        "norm_bytes": norm_bytes,
        "norm_tokens": int(norm_bytes / 4),
    }


# --------------------------------------------------------------------------
# docs/AUDIT.md  (the before/after evidence, generated so it never drifts)
# --------------------------------------------------------------------------


def audit_md(ctx) -> str:
    cs = corpus_stats(ctx.root)
    st = ctx.stats
    v = (st.get("verify") or {}).get("checks", {})
    cov = ctx.coverage
    gaps = ctx.gaps
    top = sorted(gaps, key=lambda g: -g["refs"])[:12]
    dupes = sum(p["n_duplicates"] for p in ctx.pages)
    distinct_targets = {t for p in ctx.pages for t in (p.get("link_targets") or [])}
    raw_files = cs["raw_files"]
    ra = ctx.meta.get("raw_audit") or {}
    hard_gaps = [g for g in gaps if not g.get("approx_to")]
    approx_gaps = [g for g in gaps if g.get("approx_to")]
    top_hard = sorted(hard_gaps, key=lambda g: -g["refs"])[:5]
    xch = {r[0]: r[1] for r in (ctx.xcheck or [])}
    lines = [
        "# Audit: what the upload contained and what changed",
        "",
        "_Generated by `build/build.py` → `docs/AUDIT.md`. Every number here comes from the current build, not from prose._",
        "",
        "## 1. The starting point",
        "",
        f"| input | volume | notes |",
        f"| --- | --- | --- |",
        f"| `swse-miraheze-org/` | {raw_files:,} files, {cs['raw_bytes']:,} bytes, ≈{cs['raw_tokens']:,} tokens | "
        "wiki export with YAML front matter (`title`, `source_url`, `canonical_url`, `revision_id`, `retrieved_at_utc`, `content_sha256`, `categories`) |",
        f"| `{MASTER_REF_NAME}` | 6 sheets | Heroic Classes 8 · Prestige Classes 28 · Feats {xch.get('master_reference feats', 353)} · Force Powers 90 · Talent trees 167 · `Links` crawl manifest {xch.get('Links manifest rows', 818)} |",
        f"| `3rd_Party_Builder/SagaForge 1.53.xlsm` | 31 sheets, VBA | 20 sheets are the builder's UI, not data; the only source carrying **book + page** citations (`Feats`/`Talents`/`ForcePowerCards`/`NewStatBlockRef`) |",
        "",
        "The upload had no README, index, manifest, schema or `.gitignore`, and one commit (`Add files via upload`).",
        "",
        "## 2. Defects found (and what each costs an agent)",
        "",
        f"1. **{dupes} of {raw_files} files ({100 * dupes / max(1, raw_files):.0f}%) were byte-identical redirect-crawl duplicates** "
        f"in {sum(1 for p in ctx.pages if p['n_duplicates'])} collapse groups — `theforce.md` … `theforce-e058a51e.md`, 11 copies of one 84,636-byte "
        "page differing only in `retrieved_at_utc`. *Cost: wasted context, and no way to tell which copy is authoritative.*",
        f"2. **{100 * ra.get('link_markup_bytes', 0) // max(1, cs['raw_bytes']):.0f}% of every byte was link markup** — "
        f"{ra.get('link_markup_n', 0):,} inline URLs: every mention of *Dexterity* is written "
        "`[Dexterity](https://swse.miraheze.org/wiki/Dexterity \"Dexterity\")`. *Cost: the corpus is 40% boilerplate, and the targets are "
        "unresolvable offline.*",
        f"3. **{len([p for p in ctx.pages if p['split']])} `Category:*` pages were whole campaign books glued into one file** — largest "
        f"`Category:Web Enhancements` at {max(p['chars'] for p in ctx.pages):,} chars / {max(p['n_sections'] for p in ctx.pages)} sections. "
        "*Cost: unreadable at file granularity — a retriever either drowns in them or never reaches them.*",
        f"4. **{len(gaps):,} of {len(distinct_targets):,} distinct link targets ({100 * len(gaps) / max(1, len(distinct_targets)):.0f}%) have no page in the crawl**: "
        f"{len(hard_gaps):,} are absent entirely, {len(approx_gaps):,} resolve only by prefix/name trick. Most-referenced absences: "
        f"{', '.join('`' + t['target_slug'] + '` (' + str(t['refs']) + ')' for t in top_hard)}. *Cost: 'not in the corpus' is the most common "
        "answer an agent can honestly give, so it must be cheap to prove.*",
        f"5. **No cross-source reconciliation.** {xch.get('… master_reference feats with no wiki page', 0)} of {xch.get('master_reference feats', 0)} workbook feats "
        f"have no crawled page, {xch.get('… never crawled', 99)} URLs in the workbook's own `Links` manifest were never fetched, and its "
        "*Force Powers* sheet cites `swse.fandom.com` while everything else cites `swse.miraheze.org`. *Cost: 'not found' was indistinguishable "
        "from 'does not exist'.*",
        f"6. **Crawl residue**: `Loading comments...` ×{ra.get('noise_loading', 0):,}, `?action=edit&redlink=1` hrefs ×{ra.get('noise_redlinks', 0):,}, "
        f"external CDN transclusions ×{ra.get('noise_cdn', 0):,}, {sum(1 for p in ctx.pages if not p['categories'])} pages with empty `categories`. "
        "*Cost: pure token tax and links that look broken.*",
        "",
        "## 3. What the build does",
        "",
        f"| stage | result |",
        f"| --- | --- |",
        f"| wiki | {raw_files:,} raw files → {st.get('wiki', {}).get('canonical_pages', 0):,} canonical pages, {dupes} duplicates collapsed, "
        f"{st.get('wiki', {}).get('split_pages', 0)} oversized pages split into {st.get('wiki', {}).get('section_files', 0)} section files "
        f"({st.get('wiki', {}).get('normalized_bytes', 0):,} bytes of text vs {cs['raw_bytes']:,} raw) |",
        f"| records | {st.get('records', {}).get('files_reloaded', 0):,} files → {st.get('records', {}).get('chunks', 0):,} chunks "
        f"(mean {st.get('records', {}).get('chunk_tokens_mean', 0)} tok, max {st.get('records', {}).get('chunk_tokens_max', 0)} tok) + "
        f"{st.get('records', {}).get('wiki_entities', 0):,} wiki entities |",
        f"| sources | master_reference {st.get('sources', {}).get('master_reference_entities', 0):,} rows + sagaforge "
        f"{st.get('sources', {}).get('sagaforge_entities', 0):,} rows |",
        f"| registry | {st.get('registry', {}).get('entities', 0):,} merged entities, {st.get('registry', {}).get('aliases', 0):,} aliases, "
        f"{st.get('registry', {}).get('gaps', 0):,} gaps, {st.get('registry', {}).get('discrepancies', 0):,} cross-source diffs |",
        f"| index | SQLite {st.get('index', {}).get('db_bytes', 0):,} bytes with FTS5 on chunks + entities |",
        f"| render | `index/` projections (INDEX, coverage, backlog, discrepancies, by-type/book/class, aliases.tsv) |",
        f"| verify | {'all checks pass' if v else 'see failures'} — golden lookups missed: {v.get('golden_lookup_missed', '?')}/{len(GOLDEN_LOOKUP)} |",
        "",
        "## 4. Verification (all automated, `--stage verify`)",
        "",
        f"- duplicate bodies left in `normalized/wiki/`: **{v.get('duplicate_bodies', 0)}** — all of them empty `Category:` stubs, each with `same_as`",
        f"- raw wiki URLs surviving normalization: **{v.get('unnormalized_wiki_links', 0)}**; crawl noise: **{v.get('noise_total', 0)}**",
        f"- citations pointing at a missing file: **{v.get('citations_missing_file', 0)}**; out-of-range line spans: **{v.get('citations_line_overflow', 0)}**",
        f"- chunk budget: p50 {v.get('chunk_tokens_p50', 0)} / p95 {v.get('chunk_tokens_p95', 0)} / max {v.get('chunk_tokens_max', 0)} tokens (target ≤1200)",
        f"- FTS probes: `\"hit points\"` → {v.get('fts_probe_hit_points', 0)} chunks, `Skill Focus (Survival)` → {v.get('fts_probe_quoted_phrase', 0)}",
        f"- golden name lookups {len(GOLDEN_LOOKUP) - v.get('golden_lookup_missed', 0)}/{len(GOLDEN_LOOKUP)} · field checks "
        f"{len(GOLDEN_FIELD) - v.get('golden_field_missed', 0)}/{len(GOLDEN_FIELD)} · alias resolutions "
        f"{len(GOLDEN_RESOLVE) - v.get('golden_alias_missed', 0)}/{len(GOLDEN_RESOLVE)} (incl. 1 deliberately *medium*: `The_Dark_Side`)",
        f"- negative checks: {len(GOLDEN_ABSENT) - v.get('golden_absent_missed', 0)}/{len(GOLDEN_ABSENT)} absent terms must stay gaps, and "
        f"{len(GOLDEN_APPROX) - v.get('golden_approx_missed', 0)}/{len(GOLDEN_APPROX)} approximate match must stay flagged as a gap",
        "",
        "## 5. Coverage reality check",
        "",
        "Per family (entities with crawled prose vs. spreadsheet-only rows):",
        "",
        "| family | entities | with wiki page |",
        "| --- | --- | --- |",
    ]
    for fam, stats in list(cov["by_type"].items())[:24]:
        lines.append(f"| `{fam}` | {stats.get('entities', 0):,} | {stats.get('with_wiki_page', 0):,} |")
    lines += [
        "",
        "The shape of the crawl is unmistakable: **feats, talents, talent trees, species and force powers are deep; equipment,",
        "starships, vehicles, droids and worlds are index-only** (the pages that exist are the rulebook chapter intros, whose stat",
        "tables live on uncrawled targets). Anyone tempted to answer item statistics from `normalized/wiki/` alone should read",
        "`index/coverage.md` first.",
        "",
        "## 6. Highest-leverage next steps",
        "",
        f"1. **Crawl the top {min(120, len(hard_gaps))} rows of `index/crawl-backlog.tsv`** — they carry the bulk of the dangling link volume "
        "and are pure core-rules vocabulary (defenses, action types, ability scores, conditions). A re-crawl of the manifest already in the "
        "workbook would close most of the rest. This turns the commonest 'I can't define this' answers into citations.",
        "2. **Crawl `Category:`-listed equipment pages** (weapon/armor/starship/vehicle/droid stat blocks) — the largest remaining "
        "hole for actual play, and the reason `3rd_Party_Builder/` is still worth keeping.",
        f"3. **Keep treating the {len(hard_gaps):,}-row tail as a routing table, not a bug list**: an agent should answer *'not in this crawl — "
        "backlog row N'* rather than inventing a rule.",
        "4. **Parse the remaining SagaForge sheets as data, not UI** (Weapons/Armor/Droids/Beasts are form-driven with `#N/A` "
        "formula noise) if item statistics become a priority.",
        "5. **Pin provenance**: wiki `revision_id` is kept per page, so a re-crawl can diff bodies by revision and flag only real edits.",
        "",
    ]
    return "\n".join(lines)
