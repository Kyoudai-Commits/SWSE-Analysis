"""Sourcebook resolution: abbreviation / page-ref -> normalised sourcebook.

The corpus stores provenance in three dialects (see config/sourcebooks.yaml).
This module is the only place that interprets them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from . import paths
from .ids import fold


@dataclass(frozen=True)
class Sourcebook:
    id: str
    abbreviation: str
    title: str
    canon: str
    aliases: tuple[str, ...] = ()
    short_title: str = ""
    publisher: str = ""
    year: int | None = None
    notes: str = ""


@lru_cache(maxsize=1)
def load_sourcebooks() -> dict[str, Sourcebook]:
    """abbreviation/alias (case-insensitive) -> Sourcebook."""
    doc = yaml.safe_load(paths.SOURCEBOOKS_YAML.read_text(encoding="utf-8")) or {}
    out: dict[str, Sourcebook] = {}
    for e in doc.get("sourcebooks", []):
        sb = Sourcebook(
            id=e["id"],
            abbreviation=e["abbreviation"],
            title=e["title"],
            canon=e.get("canon", "official"),
            aliases=tuple(e.get("aliases") or ()),
            short_title=e.get("short_title", ""),
            publisher=e.get("publisher", ""),
            year=e.get("year"),
            notes=e.get("notes", ""),
        )
        for key in (sb.abbreviation, *sb.aliases):
            out[key.strip().lower()] = sb
    return out


def by_id(sourcebook_id: str) -> Sourcebook | None:
    for sb in load_sourcebooks().values():
        if sb.id == sourcebook_id:
            return sb
    return None


_PAGE_RE = re.compile(r"^\s*(?P<abbr>[A-Za-z][A-Za-z0-9'\-\.]*)\s*(?P<page>\d+)\s*$")
_NUM_RE = re.compile(r"^\s*(?P<page>\d+)\s*$")


def parse_page_ref(ref: object) -> dict | None:
    """``"JATM 14"`` -> ``{"sourcebook": "jadm", "abbreviation": "JATM", "page": 14}``.

    A bare number is a Core Rulebook page. Returns ``None`` when the ref cannot
    be interpreted; the raw string is always preserved by the caller.
    """
    s = fold(ref)
    if not s:
        return None
    m = _PAGE_RE.match(s)
    if m:
        abbr = m.group("abbr")
        sb = load_sourcebooks().get(abbr.lower())
        return {
            "sourcebook": sb.id if sb else None,
            "abbreviation": abbr if not sb else sb.abbreviation,
            "page": int(m.group("page")),
            "raw": s,
            "resolved": bool(sb),
        }
    m = _NUM_RE.match(s)
    if m:
        return {"sourcebook": "secr", "abbreviation": "SECR", "page": int(m.group("page")), "raw": s, "resolved": True}
    sb = load_sourcebooks().get(s.lower())
    if sb:
        return {"sourcebook": sb.id, "abbreviation": sb.abbreviation, "page": None, "raw": s, "resolved": True}
    return {"sourcebook": None, "abbreviation": None, "page": None, "raw": s, "resolved": False}


def parse_page_refs(ref: object) -> list[dict]:
    """Parse refs that cite several books, e.g. ``"FUCG 86/LECG 54"``."""
    s = fold(ref)
    if not s:
        return []
    if "/" in s:
        parts = [p for p in s.split("/") if p.strip()]
        out = [parse_page_ref(p) for p in parts]
        return [o for o in out if o]
    one = parse_page_ref(s)
    return [one] if one else []


def parse_source_tags(tag: object) -> list[dict]:
    """``",KotOR,TFU,"`` -> one entry per recognised abbreviation.

    SagaForge wraps tags in commas and sometimes concatenates two abbreviations
    without a separator ('TotGKotOR'); both are handled by longest-prefix
    matching against the registry.
    """
    s = fold(tag)
    if not s or s.lower() in {"none", "unknown", "-"}:
        return []
    s = s.strip(",").replace(";", ",")
    known = load_sourcebooks()
    keys = sorted({k for k in known}, key=len, reverse=True)

    out: list[dict] = []
    for chunk in re.split(r"[,\s/]+", s):
        chunk = chunk.strip()
        if not chunk:
            continue
        rest = chunk
        matched = False
        while rest:
            hit = next((k for k in keys if rest.lower().startswith(k)), None)
            if not hit:
                break
            sb = known[hit]
            out.append({"sourcebook": sb.id, "abbreviation": sb.abbreviation, "raw": chunk, "resolved": True})
            rest = rest[len(hit):]
            matched = True
        if not matched:
            out.append({"sourcebook": None, "abbreviation": None, "raw": chunk, "resolved": False})
    # de-duplicate preserving order
    seen, uniq = set(), []
    for o in out:
        k = (o["sourcebook"], o["abbreviation"], o["raw"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(o)
    return uniq


def url_source(url: object) -> str | None:
    """Which wiki a Master Reference link points at (for provenance notes)."""
    s = fold(url).lower()
    if "swse.miraheze.org" in s:
        return "swse-miraheze"
    if "swse.fandom.com" in s:
        return "swse-fandom"
    if s.startswith("http"):
        return "external"
    return None
