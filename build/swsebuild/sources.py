"""Spreadsheet sources: ``SWSE_Master_Reference`` and ``SagaForge 1.53``.

Both are Excel files whose *displayed* sheets are form UIs, not tables, so each
extractor states the exact header row + column map it relies on and degrades to
"no records" rather than guessing. Every emitted record keeps its sheet, row and
column provenance so an agent can cite it and a human can audit it.

Why mine them at all?
* Master Reference is the user's own curated tables: class/feat/prereq data with
  links, plus a crawl manifest (``Links``) that tells us what the wiki crawl was
  *supposed* to cover -- 99 of its URLs are not in the corpus.
* SagaForge carries **book + page citations** (``TotG 64``, ``KotOR 32``,
  ``JATM 14``) that the wiki crawl never had, plus two uniquely clean tables:
  ``ForcePowerCards`` (90 powers with DC/action/target) and ``NewStatBlockRef``
  (80 class special abilities with action economy). Those are the only
  page-cited data in the repo.
"""

from __future__ import annotations

import os
import re

from . import util, xlsx
from .wiki import _unquote as unquote_wiki

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

# SagaForge "Page" cells hold a book abbreviation + page number, e.g. "TotG 64".
_PAGE_REF = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]{1,7})\s+(\d{1,3})\s*$")

# Wiki titles vs. abbreviation codes used by SagaForge's Data sheet.
BOOK_ABBREVS = {
    "SECR": "Core Rulebook",
    "KotOR": "Knights of the Old Republic Campaign Guide",
    "CWCS": "Clone Wars Campaign Guide",
    "TFU": "Force Unleashed Campaign Guide",
    "TFULE": "Force Unleashed Campaign Guide",
    "LECG": "Legacy Era Campaign Guide",
    "RECG": "Rebellion Era Campaign Guide",
    "URCG": "Unknown Regions Campaign Guide",
    "UR": "Unknown Regions Campaign Guide",
    "JATM": "Jedi Academy Training Manual",
    "SaV": "Scum and Villainy",
    "TotG": "Threats of the Galaxy",
    "SotG": "Starships of the Galaxy",
    "GAW": "Galaxy at War",
    "GoI": "Galaxy of Intrigue",
    "SGtD": "Scavenger's Guide to Droids",
    "WEB": "Web Enhancements",
    "TAO": "Saga-Edition.com",
    "FAQ": "Saga Edition FAQ",
    "APG": "Apprentice Campaign Guide",
}


def cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).replace("\u00a0", " ")
    return util.squash(text)


def parse_page_ref(value: str) -> dict | None:
    m = _PAGE_REF.match(value or "")
    if not m:
        return None
    abbr, page = m.group(1), int(m.group(2))
    book = BOOK_ABBREVS.get(abbr) or BOOK_ABBREVS.get(abbr.upper())
    return {"abbr": abbr, "book": book, "page": page}


def _clean_link(value: str) -> str:
    v = cell_str(value)
    if not v.startswith("http"):
        return ""
    return v


def _link_slug(url: str) -> str:
    if "/wiki/" not in url:
        return ""
    return url.split("/wiki/")[-1].split("?")[0].replace("_", " ").strip()


def _entity(etype: str, name: str, source: str, **kw) -> dict:
    name = util.squash(re.sub(r"^[#*\s]+|[#*\s]+$", "", name))
    rec = {
        "type": etype,
        "name": name,
        "id": f"{etype}:{util.slugify(util.norm_name(name))}",
        "norm": util.norm_name(name),
        "key": f"{etype}|{util.norm_name(name)}",
        "fields": {},
        "categories": [],
        "books": [],
        "summary": "",
        "prerequisites": [],
        "flags": [],
        "provenance": {"source": source, **kw},
    }
    return rec


# --------------------------------------------------------------------------
# SWSE_Master_Reference_10-8-2026.xlsx
# --------------------------------------------------------------------------


def extract_master_reference(path: str) -> tuple[list[dict], dict]:
    """Return (entities, extras) from the user's curated reference workbook."""
    wb = xlsx.read(path)
    entities: list[dict] = []
    extras: dict = {"workbook": os.path.basename(path), "sheets": [s.name for s in wb.sheets]}

    def table(sheet: str, header_row: int, colmap: dict[str, int]):
        ws = wb.by_name[sheet]
        grid = ws.grid()
        rows = []
        for ri in range(header_row, len(grid)):
            row = grid[ri]
            rec = {}
            for field, col in colmap.items():
                rec[field] = cell_str(row[col]) if col < len(row) else ""
            if rec and any(v for v in rec.values()):
                rec["__row__"] = ri + 1
                rows.append(rec)
        return rows

    # -- Heroic Classes ---------------------------------------------------
    heroic = table(
        "Heroic Classes",
        1,
        {
            "name": 0,
            "hit_points": 1,
            "defense_bonus": 2,
            "trained_skills": 3,
            "class_skills": 4,
            "starting_feats": 5,
            "talent_trees": 6,
            "link": 7,
        },
    )
    for r in heroic:
        e = _entity("heroic-class", r["name"], "master_reference", sheet="Heroic Classes", row=r["__row__"])
        e["fields"] = {
            k: v.replace("\n", "; ")
            for k, v in r.items()
            if k not in ("name", "__row__", "link") and v
        }
        e["links"] = [_link_slug(_clean_link(r["link"]))] if r["link"] else []
        e["summary"] = (
            f"Starting HP {r['hit_points']}; trained skills {r['trained_skills']}; "
            f"talent trees: {util.squash(r['talent_trees'].replace(chr(10), ', '))}"
        )
        e["flags"].append("from-master-reference")
        entities.append(e)

    # -- Prestige Classes -------------------------------------------------
    for r in table("Prestige Classes", 1, {"name": 0, "prerequisites": 1, "link": 2}):
        e = _entity("prestige-class", r["name"], "master_reference", sheet="Prestige Classes", row=r["__row__"])
        e["fields"] = {"prerequisites": r["prerequisites"].replace("\n", "; ")}
        e["prerequisites"] = split_prereq_list(r["prerequisites"])
        e["prerequisite_detail"] = util.parse_prerequisites(r["prerequisites"])
        e["links"] = [_link_slug(_clean_link(r["link"]))] if r["link"] else []
        e["flags"].append("from-master-reference")
        entities.append(e)

    # -- Feats ------------------------------------------------------------
    for r in table("Feats", 1, {"name": 0, "prerequisites": 1, "benefit": 2, "link": 3}):
        e = _entity("feat", r["name"], "master_reference", sheet="Feats", row=r["__row__"])
        e["fields"] = {"prerequisites": r["prerequisites"], "benefit": r["benefit"]}
        e["prerequisites"] = split_prereq_list(r["prerequisites"])
        e["prerequisite_detail"] = util.parse_prerequisites(r["prerequisites"])
        e["summary"] = r["benefit"][:320]
        e["books"] = infer_books_from_name(r["link"])
        e["links"] = [_link_slug(_clean_link(r["link"]))] if r["link"] else []
        e["flags"].append("from-master-reference")
        entities.append(e)

    # -- Force Powers -----------------------------------------------------
    for r in table("Force Powers", 1, {"name": 0, "spare": 1, "type": 2, "action_time": 3, "benefit": 4, "link": 5}):
        e = _entity("force-power", r["name"], "master_reference", sheet="Force Powers", row=r["__row__"])
        fields = {"power_type": r["type"], "action_time": r["action_time"], "benefit": r["benefit"]}
        if r["spare"]:
            fields["form"] = r["spare"]
        e["fields"] = {k: v for k, v in fields.items() if v}
        e["summary"] = r["benefit"][:320]
        e["links"] = [_link_slug(_clean_link(r["link"]))] if r["link"] else []
        e["provenance"]["link"] = r["link"]
        e["flags"].append("from-master-reference")
        entities.append(e)

    # -- Talents (one row per talent *tree*) ------------------------------
    for r in table("Talents", 1, {"name": 0, "availability": 1, "description": 2, "link": 3}):
        e = _entity("talent-tree", r["name"], "master_reference", sheet="Talents", row=r["__row__"])
        e["fields"] = {"availability": r["availability"], "benefit": r["description"]}
        e["summary"] = r["description"][:320]
        e["links"] = [_link_slug(_clean_link(r["link"]))] if r["link"] else []
        e["flags"].append("from-master-reference")
        entities.append(e)

    # -- Links: the crawl manifest ---------------------------------------
    ws = wb.by_name["Links"]
    manifest = []
    for ri, row in enumerate(ws.grid()):
        url = cell_str(row[0]) if row else ""
        if not url.startswith("http"):
            continue
        slug = url.split("/wiki/")[-1].split("?")[0]
        manifest.append({"row": ri + 1, "url": url, "slug": unquote_wiki(slug)})
    extras["link_manifest"] = manifest
    extras["counts"] = {
        "heroic_classes": len(heroic),
        "prestige_classes": sum(1 for e in entities if e["type"] == "prestige-class"),
        "feats": sum(1 for e in entities if e["type"] == "feat"),
        "force_powers": sum(1 for e in entities if e["type"] == "force-power"),
        "talent_trees": sum(1 for e in entities if e["type"] == "talent-tree"),
        "links": len(manifest),
    }
    return entities, extras


def infer_books_from_name(url: str) -> list[str]:
    """Master Reference only links; recover the book from the wiki category later."""
    return []


def split_prereq_list(text: str) -> list[str]:
    if not text or text.strip().lower() in ("none", "n/a", "-"):
        return []
    parts = re.split(r";|\n", text)
    out = []
    for part in parts:
        for sub in re.split(r",(?![^()]*\))", part):
            sub = util.squash(re.sub(r"^(must have|min(?:imum)?\s*level[:\s]*)", "", sub, flags=re.I))
            if sub and sub.lower() not in ("none", "n/a"):
                out.append(sub)
    return out


# --------------------------------------------------------------------------
# SagaForge 1.53.xlsm
# --------------------------------------------------------------------------

# (sheet, header_row(1-based), data_start_row, column map)
_SAGA_FORGE_TABLES = {
    "feat": ("Feats", 8, 9, {"name": 2, "prerequisites": 4, "benefit": 5, "page": 13, "tag": 17}),
    "talent": ("Talents", 6, 7, {"name": 1, "class": 2, "tree": 3, "tree2": 4, "benefit": 9, "page": 13}),
    "force-power": ("ForcePowerCards", 1, 2, {"name": 0, "descriptors": 1, "action": 2, "target": 3, "squares": 4, "los": 5, "benefit": 6, "alignment": 7, "source": 11}),
    "ability": ("NewStatBlockRef", 1, 2, {"name": 0, "action": 1, "tags": 2, "proper_tag": 3, "benefit": 4, "source": 5}),
}


def extract_sagaforge(path: str) -> tuple[list[dict], dict]:
    wb = xlsx.read(path)
    entities: list[dict] = []
    extras: dict = {"workbook": os.path.basename(path), "sheets": [s.name for s in wb.sheets]}

    for etype, (sheet, header_row, start_row, colmap) in _SAGA_FORGE_TABLES.items():
        if sheet not in wb.by_name:
            continue
        ws = wb.by_name[sheet]
        grid = ws.grid()
        headers = {}
        hrow = grid[header_row - 1] if header_row - 1 < len(grid) else []
        for field, col in colmap.items():
            if col < len(hrow) and hrow[col]:
                headers[field] = cell_str(hrow[col])
        for ri in range(start_row - 1, len(grid)):
            row = grid[ri]
            vals = {}
            for field, col in colmap.items():
                vals[field] = cell_str(row[col]) if isinstance(col, int) and col < len(row) else ""
            name = vals.get("name", "")
            if not name or name in ("Feat", "Name", "Special Name", "FORCE POWER"):
                continue
            if re.fullmatch(r"[\d.,\s]+", name):
                continue
            e = _entity(etype, name, "sagaforge", sheet=sheet, row=ri + 1, columns=headers)
            prov_page = vals.get("page") or vals.get("source")
            ref = parse_page_ref(prov_page)
            fields = {k: v for k, v in vals.items() if v and k not in ("name", "page")}
            e["fields"] = fields
            e["prerequisites"] = split_prereq_list(vals.get("prerequisites", ""))
            if vals.get("prerequisites"):
                e["prerequisite_detail"] = util.parse_prerequisites(vals["prerequisites"])
            e["summary"] = (vals.get("benefit") or "")[:320]
            if ref:
                e["provenance"]["book"] = ref["book"] or ref["abbr"]
                e["provenance"]["book_abbr"] = ref["abbr"]
                e["provenance"]["page"] = ref["page"]
                if ref["book"]:
                    e["books"] = [ref["book"]]
            elif prov_page:
                e["provenance"]["page_raw"] = prov_page
            e["flags"].append("from-sagaforge")
            entities.append(e)

    extras["book_abbreviations"] = _sagaforge_book_legend(wb)
    extras["counts"] = {
        t: sum(1 for e in entities if e["type"] == t) for t in _SAGA_FORGE_TABLES
    }
    return entities, extras


def _sagaforge_book_legend(wb) -> dict[str, str]:
    """Harvest the ``Supplements`` / ``Supplement Abbreviation`` pair-columns."""
    legend = dict(BOOK_ABBREVS)
    if "Data" not in wb.by_name:
        return legend
    grid = wb.by_name["Data"].grid()
    # locate the header cell, then read down both columns
    anchor = None
    for ri, row in enumerate(grid[:6]):
        for ci, val in enumerate(row):
            if val and "Supplement Abbreviation" in str(val):
                anchor = (ri, ci)
                break
        if anchor:
            break
    if not anchor:
        return legend
    ri, ci = anchor
    for row in grid[ri + 1 : ri + 40]:
        abbr = cell_str(row[ci]) if ci < len(row) else ""
        name = cell_str(row[ci - 1]) if ci - 1 < len(row) else ""
        if abbr and name and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,8}", abbr):
            legend.setdefault(abbr, name)
    return legend
