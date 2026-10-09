"""Registry: cross-source merge, alias lexicon, link graph, coverage + gaps.

Three sources describe the same game and disagree in ordinary ways (a feat page
exists but has no spreadsheet row; a spreadsheet row has no crawled page; the
prerequisite text differs by an errata wording). This layer does *not* silently
pick a winner: it unions everything, records which source said what, and
surfaces the disagreements as ``field_diffs`` so an agent can answer with the
discrepancy visible instead of inventing a resolution.

It also produces the two things that make the corpus navigable:

``aliases``
    every name variant that should find an entity -- page titles, MediaWiki
    slugs, the 150 redirect slugs we collapsed, and 1,100+ anchor-text
    synonyms harvested from the wiki's own ``[[Target|display text]]`` links.

``gaps``
    link targets the crawl never fetched, ranked by how many times the corpus
    leans on them -- i.e. a concrete, prioritised crawl backlog.
"""

from __future__ import annotations

import collections
import re

from . import util

FAMILY = {
    "feat": "feat",
    "talent": "talent",
    "talent-tree": "talent-tree",
    "force-power": "force-power",
    "species": "species",
    "heroic-class": "heroic-class",
    "prestige-class": "prestige-class",
    "weapon": "weapon",
    "armor": "armor",
    "equipment": "equipment",
    "upgrade": "upgrade",
    "implant": "implant",
    "creature": "creature",
    "droid": "droid",
    "beast": "creature",
    "starship": "starship",
    "vehicle": "vehicle",
    "planet": "planet",
    "organization": "organization",
    "affiliation": "affiliation",
    "ability": "class-ability",
    "action": "action",
    "skill": "skill",
    "keyword": "keyword",
    "rule": "rule",
    "equipment": "equipment",
    "weapon-group": "weapon-group",
    "droid-system": "droid-system",
    "crew-position": "crew-position",
    "challenge": "challenge",
    "npc": "npc",
    "era": "era",
    "upgrade": "upgrade",
    "index": "index",
    "compilation": "compilation",
    "section": "section",
}

SOURCE_PRIORITY = ["wiki", "master_reference", "sagaforge"]


def family_of(etype: str) -> str:
    return FAMILY.get(etype, "other")


def _vkey(value: str) -> str:
    """Comparable form of a field value: case/punct/markup-insensitive."""
    t = util.decurly(str(value or "")).lower()
    t = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"[\s]+", " ", t)
    t = re.sub(r"[^0-9a-z ,.:+/\-()]", "", t)
    return t.strip(" .")


def merge_entities(wiki_ents: list[dict], mr_ents: list[dict], sf_ents: list[dict]) -> list[dict]:
    """Union entities across sources, keyed by (family, normalized name)."""
    buckets: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for ent in list(wiki_ents) + list(mr_ents) + list(sf_ents):
        fam = family_of(ent["type"])
        key = ent.get("key") or f"{fam}|{ent['norm']}"
        norm_key = ent.get("norm") or util.norm_name(ent["name"])
        buckets[(fam, norm_key)].append(ent)

    merged: list[dict] = []
    for (fam, norm), group in sorted(buckets.items()):
        by_src: dict[str, dict] = {}
        for ent in group:
            src = ent["provenance"].get("source") or "wiki"
            prev = by_src.get(src)
            # within one source keep the richest record (most fields / longest summary)
            if prev is None or _richness(ent) > _richness(prev):
                by_src[src] = ent
        primary = None
        for src in SOURCE_PRIORITY:
            if src in by_src:
                primary = by_src[src]
                break
        assert primary is not None
        name = primary["name"]
        eid = f"{fam}:{norm.replace(' ', '_')}"

        fields: dict[str, str] = {}
        fields_by_source: dict[str, dict] = {}
        diffs: list[dict] = []
        all_keys: set[str] = set()
        for src, ent in by_src.items():
            fl = {k: v for k, v in (ent.get("fields") or {}).items() if v}
            fields_by_source[src] = fl
            all_keys |= set(fl)
        for k in sorted(all_keys):
            vals = {s: f[k] for s, f in fields_by_source.items() if k in f}
            if len({util.squash(v).lower() for v in vals.values()}) > 1:
                distinct = {_vkey(v) for v in vals.values()}
                if len(distinct) > 1:
                    severity = util.diff_severity(list(vals.values()))
                    if severity != "equivalent":
                        diffs.append({"field": k, "values": vals, "severity": severity})
            # wiki prose wins for narrative fields; spreadsheets win for stats
            for src in SOURCE_PRIORITY:
                if k in fields_by_source.get(src, {}):
                    fields[k] = fields_by_source[src][k]
                    break

        aliases = sorted({e["name"] for e in group if e["name"] and e["name"] != name})
        books = sorted({b for e in group for b in (e.get("books") or [])})
        categories = sorted({c for e in group for c in (e.get("categories") or [])})
        prereq_sources = {s: sorted(set((f.get("prerequisites") or "").split(", "))) for s, f in fields_by_source.items()}
        page_refs = [
            e["provenance"]["page"]
            for e in group
            if isinstance(e["provenance"].get("page"), int)
        ]

        rec = {
            "id": eid,
            "key": f"{fam}|{norm}",
            "type": primary["type"],
            "family": fam,
            "name": name,
            "norm": norm,
            "aliases": aliases,
            "summary": primary.get("summary") or next((e.get("summary") for e in group if e.get("summary")), ""),
            "fields": fields,
            "fields_by_source": fields_by_source,
            "field_diffs": diffs,
            "prerequisites": primary.get("prerequisites") or [],
            "prerequisite_detail": primary.get("prerequisite_detail") or {},
            "books": books,
            "categories": categories,
            "sources": sorted(by_src, key=lambda s: SOURCE_PRIORITY.index(s) if s in SOURCE_PRIORITY else 9),
            "provenance": primary["provenance"],
            "provenance_all": {
                s: {k: v for k, v in (e["provenance"] or {}).items() if k != "columns"}
                for s, e in by_src.items()
            },
            "flags": sorted(set(primary.get("flags") or []) | {f for e in group for f in (e.get("flags") or [])}),
            "n_sources": len(by_src),
            "page_citation": {"book_page": page_refs} if page_refs else {},
        }
        if "wiki" not in by_src:
            rec["flags"].append("no-wiki-page")
        if len(by_src) > 1 and not diffs:
            rec["flags"].append("sources-agree")
        if any(d["severity"] == "value" for d in diffs):
            rec["flags"].append("has-field-diffs")  # real conflict: numbers/words differ
        elif diffs:
            rec["flags"].append("has-wording-diffs")  # paraphrase / abbreviation only
        rec["n_value_diffs"] = sum(1 for d in diffs if d["severity"] == "value")
        for opt in ("tree", "tree_page", "scope", "parent", "slug", "page_id", "n_children"):
            if primary.get(opt) is not None:
                rec[opt] = primary[opt]
        merged.append(rec)
    return merged


def _richness(ent: dict) -> int:
    return (
        len(ent.get("fields") or {}) * 10
        + len(ent.get("summary") or "")
        + len(ent.get("prerequisites") or [])
        + (50 if ent.get("provenance", {}).get("source") == "wiki" else 0)
    )


# --------------------------------------------------------------------------
# alias lexicon
# --------------------------------------------------------------------------


def build_aliases(pages: list[dict], entities: list[dict], alias_pairs: list[tuple[str, str, str]], redirects: list[dict]) -> list[dict]:
    """Every name variant -> the record it should resolve to.

    ``kind`` explains the evidence, which is what makes this auditable:
    ``title`` / ``slug`` (page identity), ``anchor`` (wiki's own synonym text),
    ``redirect`` (a crawled URL that landed on this page), ``source-name``
    (spreadsheet spelling), ``singular``/``plural`` (mechanical variants).
    """
    rows: dict[tuple[str, str], dict] = {}

    def add(alias: str, target_id: str, target_type: str, kind: str, note: str = "") -> None:
        alias = util.squash(re.sub(r"[*_`]", "", str(alias or "")))
        if not alias or len(alias) < 2:
            return
        norm = util.norm_name(alias)
        if not norm:
            return
        rec = {
            "alias": alias,
            "alias_norm": norm,
            "target_id": target_id,
            "target_type": target_type,
            "kind": kind,
            "target_slug": target_id.split(":", 1)[-1] if target_id.startswith("wiki:") else "",
        }
        if note:
            rec["note"] = note
        prev = rows.get((norm, target_id))
        if prev is None or _KIND_RANK[kind] > _KIND_RANK[prev["kind"]]:
            rows[(norm, target_id)] = rec

    by_slug = {p["slug"]: p for p in pages}
    for p in pages:
        add(p["title"], p["id"], p["type"], "title")
        add(p["slug"].replace("_", " "), p["id"], p["type"], "slug")
        if p["slug"].startswith("Category:"):
            add(p["slug"].split(":", 1)[1].replace("_", " "), p["id"], p["type"], "slug", "category page")
        if util.norm_name(p["title"]) != util.norm_name(p["slug"].replace("_", " ")):
            add(p["slug"].replace("_", " "), p["id"], p["type"], "slug")

    for target, text, _src in alias_pairs:
        page = by_slug.get(target)
        if page:
            add(text, page["id"], page["type"], "anchor", f"anchor text on {page['title']}")

    for ent in entities:
        for alias in ent.get("aliases") or []:
            add(alias, ent["id"], ent["family"], "source-name")
        add(ent["name"], ent["id"], ent["family"], "title")

    for r in redirects:
        page = by_slug.get(r.get("to"))
        if page:
            add(r.get("from", ""), page["id"], page["type"], "redirect")

    return sorted(rows.values(), key=lambda x: (x["alias_norm"], x["target_id"]))


_KIND_RANK = {"title": 4, "slug": 3, "anchor": 5, "redirect": 2, "source-name": 1, "singular": 0, "plural": 0}


# --------------------------------------------------------------------------
# link graph + coverage
# --------------------------------------------------------------------------


def _prefix_page(tgt: str, by_norm: dict[str, dict]) -> tuple[dict | None, int]:
    """Longest-prefix page match for MediaWiki's per-variant anchors.

    ``Weapon_Focus_(Lightsabers)`` has no page of its own: the wiki anchors every
    chosen-weapon variant at the single ``Weapon Focus`` article. Dropping trailing
    tokens (max 3) and matching the longest page name recovers that without
    guessing across unrelated records.
    """
    words = util.norm_name(tgt.replace("_", " ")).split()
    for k in range(1, min(4, len(words))):
        cand = " ".join(words[: len(words) - k])
        page = by_norm.get(cand)
        if page is not None:
            return page, k
    return None, 0


def build_links(pages: list[dict], alias_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    # (resolved edges, unresolved gaps)
    """Resolve every internal link; return (edges, gap rows)."""
    by_slug = {p["slug"]: p for p in pages}
    by_norm_slug = {util.norm_name(p["slug"].replace("_", " ")): p for p in pages}
    by_norm_title = {util.norm_name(p["title"]): p for p in pages}
    for p in pages:  # category pages answer for their bare name too
        if p["slug"].startswith("Category:"):
            by_norm_title.setdefault(util.norm_name(p["slug"].split(":", 1)[1]), p)
    alias_target: dict[str, list[dict]] = collections.defaultdict(list)
    for a in alias_rows:
        alias_target[a["alias_norm"]].append(a)

    pair_counts: collections.Counter = collections.Counter()
    counter: collections.Counter = collections.Counter()
    seen_pages: dict[str, set] = collections.defaultdict(set)
    for p in pages:
        for tgt in p.get("link_targets", []):
            counter[tgt] += 1
            pair_counts[(p["id"], tgt)] += 1
            seen_pages[tgt].add(p["id"])

    edges: list[dict] = []
    extra_aliases: list[dict] = []
    gaps: list[dict] = []
    for tgt, n in counter.most_common():
        page = by_slug.get(tgt)
        how = "exact-slug"
        if page is None:
            page = by_norm_title.get(util.norm_name(tgt.replace("_", " "))) or by_norm_slug.get(util.norm_name(tgt.replace("_", " ")))
            how = "normalized-name"
        if page is None:
            hits = alias_target.get(util.norm_name(tgt.replace("_", " ")))
            if hits and hits[0]["target_id"].startswith("wiki:"):
                page = by_slug.get(hits[0]["target_slug"]) or next((q for q in pages if q["id"] == hits[0]["target_id"]), None)
                how = f"alias:{hits[0]['kind']}"
        if page is None:
            page, dropped = _prefix_page(tgt, by_norm_title)
            if page is not None:
                how = f"variant-name(-{dropped})"
                extra_aliases.append(
                    {
                        "alias": util.squash(tgt.replace("_", " ")),
                        "alias_norm": util.norm_name(tgt.replace("_", " ")),
                        "target_id": page["id"],
                        "target_type": page["type"],
                        "kind": "variant",
                        "target_slug": page["slug"],
                        "note": f"MediaWiki variant anchor: {tgt}",
                    }
                )
        approx = how.startswith("variant-name")
        if page is not None and not approx:
            edges.append(
                {
                    "target_slug": tgt,
                    "to": page["id"],
                    "to_title": page["title"],
                    "resolved_by": how,
                    # 'medium' = inferred from anchor text or a slug variant: the
                    # link exists, but the target may be a related page rather than
                    # the definition (e.g. "The Dark Side" -> Dark Side Talent Tree).
                    # Agents are told in AGENTS.md to verify medium hits by reading.
                    "confidence": "high"
                    if how in ("exact-slug", "normalized-name") or how.startswith("alias:redirect")
                    else "medium",
                    "refs": n,
                    "n_pages": len(seen_pages[tgt]),
                }
            )
            continue
        gaps.append(
            {
                "target_slug": tgt,
                "approx_to": page["id"] if (page is not None and approx) else "",
                "approx_by": how if approx else "",
                "guess": util.squash(tgt.replace("_", " ")),
                "norm": util.norm_name(tgt.replace("_", " ")),
                "refs": n,
                "n_pages": len(seen_pages[tgt]),
                "sample_pages": sorted(seen_pages[tgt])[:4],
                "kind": _gap_kind(tgt, seen_pages[tgt]),
            }
        )
    return edges, gaps, extra_aliases


def pair_rows(pages: list[dict]) -> list[dict]:
    """Raw (source page -> target slug) edges, for a "what links here" query."""
    out: list[dict] = []
    for p in pages:
        counts: collections.Counter = collections.Counter(p.get("link_targets") or [])
        for tgt, n in counts.most_common():
            out.append({"from": p["id"], "to_slug": tgt, "n": n})
    return out


_RULEISH = re.compile(
    r"_(defense|action|skills?|score|track|bonus|damage|setting|points?|proficiency)$|"
    r"^(The_|Droid|Vehicle|Starship|Skill|Feat|Talent|Condition|Range|Size|Hit_Points)",
)


def _gap_kind(target: str, sources: set) -> str:
    if target.startswith("Category:"):
        return "category-index"
    if target.startswith("File:"):
        return "image"
    if _RULEISH.search(target):
        return "rules-term"
    if len(sources) >= 12:
        return "frequently-referenced"
    return "entity-page"


def coverage_report(pages: list[dict], entities: list[dict], gaps: list[dict]) -> dict:
    by_type: dict[str, dict] = collections.defaultdict(lambda: {"pages": 0, "entities": 0, "chars": 0})
    for p in pages:
        t = family_of(p["type"])
        by_type[t]["pages"] += 1
        by_type[t]["chars"] += p["chars"]
    for e in entities:
        by_type[e["family"]]["entities"] += 1
        by_type[e["family"]].setdefault("with_wiki_page", 0)
        if "wiki" in e["sources"]:
            by_type[e["family"]]["with_wiki_page"] += 1
    by_book: dict[str, dict] = collections.defaultdict(lambda: {"pages": 0, "feats": 0, "talents": 0, "force_powers": 0})
    for p in pages:
        for b in _books_of(p):
            by_book[b]["pages"] += 1
    for e in entities:
        for b in e.get("books") or []:
            if e["family"] == "feat":
                by_book[b]["feats"] += 1
            elif e["family"] == "talent":
                by_book[b]["talents"] += 1
            elif e["family"] == "force-power":
                by_book[b]["force_powers"] += 1
    hard = [g for g in gaps if not g.get("approx_to")]
    soft = [g for g in gaps if g.get("approx_to")]
    return {
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1]["entities"])),
        "by_book": dict(sorted(by_book.items(), key=lambda kv: -kv[1]["pages"])),
        "dangling_targets": len(hard),
        "dangling_refs": sum(g["refs"] for g in hard),
        "approx_targets": len(soft),
        "approx_refs": sum(g["refs"] for g in soft),
    }


def _books_of(page: dict) -> list[str]:
    return [c for c in page.get("categories") or [] if _is_book(c)]


def _is_book(cat: str) -> bool:
    return bool(
        re.search(r"(Campaign Guide|Rulebook|Training Manual|Sourcebook)$", cat)
        or cat
        in {
            "Scum and Villainy",
            "Threats of the Galaxy",
            "Starships of the Galaxy",
            "Galaxy at War",
            "Galaxy of Intrigue",
            "Core Rulebook",
            "Web Enhancements",
            "Saga Edition FAQ",
            "Scavenger's Guide to Droids",
        }
    )
