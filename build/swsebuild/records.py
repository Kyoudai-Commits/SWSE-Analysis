"""Record layer: pages -> retrieval chunks -> typed entities (wiki side).

Entity typing rules (deterministic, documented, and conservative):

* A page of type ``talent-tree`` yields one entity per ``### Talent`` heading,
  with the parent tree as its scope and ``*Prerequisite:*`` parsed into
  ``prerequisites``.
* A ``feat``/``force-power``/``species``/... page yields one entity from its
  page-level ``**Field:**`` block (fields before the first ``##`` only, so that
  nested section fields don't leak upward).
* Section files split out of compilation pages (whole campaign books) are
  *classified by shape*: a section carrying ``Prerequisite`` + ``Effect`` looks
  like a feat, one carrying ``Damage``/``Cost`` like a weapon, and so on. This
  recovers rules text that only exists inside the mega-pages (e.g. the ``Web
  Enhancements`` feats), which is otherwise unreachable at file granularity.
"""

from __future__ import annotations

import re

from . import util
from .wiki import Page, extract_fields

MAX_CHUNK_TOKENS = 1000
MAX_CHUNK_SLACK = 1.3  # tables and stat blocks may exceed the target; this is the hard ceiling

_PREREQ_SPLIT = re.compile(r",(?![^()]*\))")
_BOOK_WORDS = re.compile(r"(Campaign Guide|Rulebook|Manual|Guide|Sourcebook)")


# --------------------------------------------------------------------------
# chunks
# --------------------------------------------------------------------------


def chunks_for_page(page: Page) -> list[dict]:
    """Heading-delimited chunks with line ranges back into the source file.

    Small pages become one chunk; long pages chunk per ``##``, and any chunk
    still over budget is sub-chunked per ``###`` and finally hard-wrapped, so
    that every chunk fits a modest context budget.
    """
    out: list[dict] = []
    level2 = [s for s in page.sections if s.level == 2]
    # blocks=None means "chunk the whole body"; either way every piece goes
    # through _fit(), so a page with no level-2 headings can't emit one huge chunk
    blocks: list = level2 if (len(page.body) > 4000 and level2) else [None]
    for bi, sec in enumerate(blocks):
        if sec is None:
            pieces = _fit(page.body.strip(), MAX_CHUNK_TOKENS)
            heading = ""
            line_start, line_end = 1, len(page.body.split("\n"))
            if len(pieces) == 1:
                blocks = []
        else:
            start_idx = page.sections.index(sec)
            tail = [sec]
            for nxt in page.sections[start_idx + 1 :]:
                if nxt.level <= 2:
                    break
                tail.append(nxt)
            heading = " > ".join([page.title, sec.title])
            line_start, line_end = sec.line_start, tail[-1].line_end
            text = "\n\n".join(t.text for t in tail if t.text)
            pieces = _fit(text, MAX_CHUNK_TOKENS)
        for pi, piece in enumerate(pieces):
            if not piece.strip():
                continue
            out.append(
                {
                    "id": f"{page.id}#c{bi:02d}{'.' + str(pi) if pi else ''}",
                    "heading_only": (sec.title if sec else ""),
                    "page_id": page.id,
                    "title": page.title,
                    "heading": heading or page.title,
                    "level": 2 if sec else 1,
                    "line_start": line_start,
                    "line_end": line_end,
                    "file": page.file,
                    "tokens": util.tokens(piece),
                    "chars": len(piece),
                    "categories": page.meta.get("categories") or [],
                    "text": piece.strip(),
                }
            )
    return out


def _fit(text: str, max_tokens: int) -> list[str]:
    """Split at ``###`` boundaries, then paragraphs, until under budget."""
    if util.tokens(text) <= max_tokens:
        return [text]
    subs = re.split(r"\n(?=### )", text)
    if len(subs) > 1:
        out: list[str] = []
        for s in subs:
            out.extend(_fit(s, max_tokens))
        return out
    pieces, cur = [], ""
    for para in text.split("\n\n"):
        if cur and util.tokens(cur + "\n\n" + para) > max_tokens:
            pieces.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        pieces.append(cur)
    # a single oversized table can't be split by paragraphs: chunk its rows and
    # repeat the header so each piece stays self-describing
    final: list[str] = []
    for piece in pieces:
        if util.tokens(piece) <= max_tokens:
            final.append(piece)
            continue
        for sub in _split_table(piece, max_tokens):
            if util.tokens(sub) <= max_tokens * MAX_CHUNK_SLACK:
                final.append(sub)
            else:  # last resort: break long prose lines at sentence ends
                final.extend(_split_sentences(sub, max_tokens))
    return final


def _split_sentences(text: str, max_tokens: int) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z*\-|])", text)
    out, cur = [], ""
    for part in parts:
        if cur and util.tokens(cur + " " + part) > max_tokens:
            out.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}" if cur else part
    if cur:
        out.append(cur)
    return out or [text]


def _split_table(text: str, max_tokens: int) -> list[str]:
    lines = text.split("\n")
    head = [ln for ln in lines[:3] if ln.strip().startswith("|")]
    body = [ln for ln in lines if ln.strip().startswith("|")]
    if len(head) < 2 or len(body) <= len(head):
        # no table: hard-wrap on line boundaries
        chunks, cur = [], ""
        for ln in lines:
            if cur and util.tokens(cur + "\n" + ln) > max_tokens:
                chunks.append(cur)
                cur = ln
            else:
                cur = f"{cur}\n{ln}" if cur else ln
        if cur:
            chunks.append(cur)
        return chunks
    header = "\n".join(head)
    rows = body[len(head) :]
    per = max(1, len(rows) // max(1, (util.tokens(text) // max_tokens) + 1) + 1)
    out = []
    # keep non-table preamble attached to the first piece
    pre = "\n".join(ln for ln in lines[: lines.index(body[0])] if not ln.strip().startswith("|")).strip()
    for i in range(0, len(rows), per):
        block = header + "\n" + "\n".join(rows[i : i + per])
        if i == 0 and pre:
            block = pre + "\n\n" + block
        out.append(block)
    return out


# --------------------------------------------------------------------------
# entities
# --------------------------------------------------------------------------


def _entity_id(kind: str, name: str) -> str:
    return f"{kind}:{util.slugify(util.norm_name(name)) or util.sha16(name)[:8]}"


def split_prereq(text: str) -> list[str]:
    if not text or text.strip().lower() in ("none", "n/a", "-"):
        return []
    parts = [util.squash(strip_parens_noise(p)) for p in _PREREQ_SPLIT.split(text)]
    out = []
    for p in parts:
        p = re.sub(r"\s+\d+(st|nd|rd|th)\s+level$", lambda m: m.group(0), p)
        if p:
            out.append(p)
    return out


def strip_parens_noise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .;")


def parse_books(categories: list[str], field: str = "") -> list[str]:
    """Reference books come from the wiki's own category tags."""
    cats = {c.strip() for c in categories or []}
    books = sorted(c for c in cats if _BOOK_WORDS.search(c) or c in _EXTRA_BOOKS)
    return books


_EXTRA_BOOKS = {
    "Core Rulebook",
    "Saga Edition FAQ",
    "Scum and Villainy",
    "Threats of the Galaxy",
    "Starships of the Galaxy",
    "Knights of the Old Republic Campaign Guide",
    "Galaxy at War",
    "Rebellion Era Campaign Guide",
    "Legacy Era Campaign Guide",
    "Force Unleashed Campaign Guide",
    "Clone Wars Campaign Guide",
    "Unknown Regions Campaign Guide",
    "Jedi Academy Training Manual",
    "Galaxy of Intrigue",
    "Dark Side Campaign Notes",
    "Web Enhancements",
    "Saga Edition Complete",
}

_FIELD_ALIASES = {
    "Prerequisites": "prerequisites",
    "Prerequisite": "prerequisites",
    "Effect": "benefit",
    "Benefit": "benefit",
    "Benefits": "benefit",
    "Normal": "normal",
    "Special": "special",
    "Roleplaying": "roleplaying",
    "Time": "action_time",
    "Use Time": "action_time",
    "Range": "range",
    "Duration": "duration",
    "Target": "target",
    "Damage": "damage",
    "Cost": "cost_credits",
    "Weight": "weight_kg",
    "Type": "damage_type",
    "Size": "size",
    "Weapon Type": "weapon_group",
    "Rate of Fire": "rate_of_fire",
    "Stun Setting": "stun_setting",
    "Availability": "availability",
    "Inaccurate": "quality_inaccurate",
    "Defense": "defense_bonus",
    "Armor Check Penalty": "armor_check_penalty",
    "Speed": "speed",
    "Ability Modifiers": "ability_modifiers",
    "Skill Bonuses": "skill_bonuses",
    "Hit Points": "hit_points",
    "Damage Threshold": "damage_threshold",
    "Base Attack Bonus": "base_attack_bonus",
    "Fortitude": "fortitude",
    "Reflex": "reflex",
    "Will": "will",
}


def normalize_fields(raw: dict[str, str]) -> dict[str, str]:
    """Map wiki field labels to stable snake_case keys (keeping unmapped ones)."""
    out: dict[str, str] = {}
    for key, val in raw.items():
        k = util.squash(key).rstrip(":").strip()
        mapped = _FIELD_ALIASES.get(k, re.sub(r"[^a-z0-9]+", "_", k.lower()).strip("_"))
        if mapped in out and out[mapped] != val:
            out[mapped] = f"{out[mapped]}; {val}"
        else:
            out[mapped] = val
    return out


_LEAD_LABEL = re.compile(r"^(?:\*\*|\*)(?P<k>[^*]{1,60}):(?:\*\*|\*)\s*")
_SKIP_PARA = re.compile(r"^(#|\||>|\*Reference Book|Loading comments)")


def summary_of(text: str, limit: int = 320) -> str:
    """A one-line gloss: the first paragraph that is not just a stat label."""
    fallback = ""
    for para in (text or "").split("\n\n"):
        p = para.strip()
        if not p or _SKIP_PARA.match(p):
            continue
        m = _LEAD_LABEL.match(p)
        if m:
            rest = util.squash(_plain(p[m.end() :]))
            label = util.squash(m.group("k")).lower()
            if label in ("prerequisite", "prerequisites", "source", "reference book", "link to edition"):
                continue
            if len(rest) >= 45:
                return rest[:limit]
            if not fallback:
                fallback = rest
            continue
        clean = util.squash(_plain(p))
        if len(clean) >= 25:
            return clean[:limit]
        if clean and not fallback:
            fallback = clean
    return fallback[:limit]


def _plain(text: str) -> str:
    t = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    t = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).replace("_", " "), t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[*_`]", "", t)
    return t


def entities_from_page(page: Page) -> list[dict]:
    ptype = getattr(page, "type", None) or classify_page(page)
    if page.meta.get("parent"):
        return entities_from_section_file(page)
    lines = page.body.split("\n")
    first_h2 = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    intro = "\n".join(lines[:first_h2])
    fields = normalize_fields(extract_fields(intro))
    if ptype not in ("talent-tree", "compilation", "index"):
        # some page types (species, classes) keep their stat block in sections:
        # fill any key the intro did not carry, intro wins on conflict
        whole = normalize_fields(extract_fields(page.body))
        for k, v in whole.items():
            fields.setdefault(k, v)
    cats = page.meta.get("categories") or []
    books = parse_books(cats)
    entities: list[dict] = []

    base = {
        "type": ptype,
        "name": page.title,
        "slug": page.slug,
        "page_id": page.id,
        "categories": cats,
        "books": books,
        "fields": fields,
        "summary": summary_of(intro),
        "prerequisites": split_prereq(fields.get("prerequisites", "")),
        "prerequisite_detail": util.parse_prerequisites(fields.get("prerequisites", "")),
        "provenance": {
            "source": "wiki",
            "file": page.file,
            "url": page.meta.get("canonical_url"),
            "revision_id": page.meta.get("revision_id"),
            "retrieved_at_utc": page.meta.get("retrieved_at_utc"),
        },
        "flags": [],
    }

    if ptype == "talent-tree":
        tree_name = re.sub(r"\s*Talent Tree$", "", page.title, flags=re.I)
        children = _children_of_level(page, 3)
        if children:
            for sec, parent in children:
                cfields = normalize_fields(extract_fields(sec.text))
                scope = parent.title if parent else "Core Talents"
                entities.append(
                    {
                        **base,
                        "type": "talent",
                        "name": sec.title,
                        "tree": tree_name,
                        "tree_page": page.id,
                        "scope": scope,
                        "fields": cfields,
                        "summary": summary_of(sec.text),
                        "prerequisites": split_prereq(cfields.get("prerequisites", "")),
                        "prerequisite_detail": util.parse_prerequisites(cfields.get("prerequisites", "")),
                        "provenance": {**base["provenance"], "heading": sec.title, "line_start": sec.line_start, "line_end": sec.line_end},
                        "flags": ["from-talent-tree"],
                    }
                )
            base = {**base, "flags": [*base["flags"], "has-children"]}
            base["n_children"] = len(children)
        entities.insert(0, base)
        return [_finish(e) for e in entities]

    if ptype == "compilation":
        for sec, _ in _children_of_level(page, 2):
            if not sec.text or len(sec.text) < 120:
                continue
            stype = classify_section(sec.text)
            if stype == "section":
                continue
            sfields = normalize_fields(extract_fields(sec.text))
            child = page.child_paths.get(sec.title)
            entities.append(
                _finish(
                    {
                        **base,
                        "type": stype,
                        "name": sec.title,
                        "fields": sfields,
                        "summary": summary_of(sec.text),
                        "prerequisites": split_prereq(sfields.get("prerequisites", "")),
                        "prerequisite_detail": util.parse_prerequisites(sfields.get("prerequisites", "")),
                        "parent": page.id,
                        "categories": cats,
                        "provenance": {
                            "source": "wiki",
                            "file": child or page.file,
                            "parent_file": page.file,
                            "url": page.meta.get("canonical_url"),
                            "heading": sec.title,
                            "line_start": sec.line_start,
                            "line_end": sec.line_end,
                            "split": bool(child),
                        },
                        "flags": ["from-compilation"],
                    }
                )
            )
        entities.insert(0, _finish({**base, "flags": [*base["flags"], "compilation-index"]}))
        return entities

    entities.append(base)
    return [_finish(e) for e in entities]


def _finish(entity: dict) -> dict:
    entity["id"] = _entity_id(entity["type"], entity["name"])
    entity["norm"] = util.norm_name(entity["name"])
    entity["key"] = f"{entity['type']}|{entity['norm']}"
    return entity


def _children_of_level(page: Page, level: int) -> list[tuple]:
    """Every ``###`` (or ``##``) section paired with its nearest enclosing parent."""
    out = []
    parent = None
    for sec in page.sections:
        if sec.level == level - 1 and sec.level >= 2:
            parent = sec
        elif sec.level == level:
            out.append((sec, parent))
    return out


def classify_section(text: str) -> str:
    """Shape-based typing for sections that live inside mega-pages."""
    f = normalize_fields(extract_fields(text))
    keys = set(f)
    if {"damage", "cost_credits"} & keys and ("weapon_group" in keys or "rate_of_fire" in keys or "stun_setting" in keys):
        return "weapon"
    if "defense_bonus" in keys and "armor_check_penalty" in keys:
        return "armor"
    if "cost_credits" in keys and "weight_kg" in keys:
        return "equipment"
    if "prerequisites" in keys and ("benefit" in keys or len(text) < 2500):
        return "feat"
    if "action_time" in keys and ("duration" in keys or "target" in keys):
        return "force-power"
    if "ability_modifiers" in keys or "skill_bonuses" in keys:
        return "species"
    if re.search(r"\*\*(Initiative|Perception|Offense|Defense)\*\*", text):
        return "creature"
    if re.search(r"\*\*(Scale|Speed|Maneuverability|Hyperdrive)\*\*", text):
        return "starship"
    if re.search(r"\*\*Prerequisite:\*\*", text):
        return "talent"
    return "section"


def entities_from_section_file(page: Page) -> list[dict]:
    """A split-off section file (one heading of a mega-page).

    These files are where the campaign-book and Web-Enhancement content lives, so
    they get shape-classified: a section with ``Prerequisites`` + ``Effect`` is a
    feat whether or not it has its own wiki page. Talent-tree children additionally
    yield one entity per talent heading.
    """
    parent = page.meta.get("parent", "")
    heading = page.meta.get("heading") or page.title
    cats = page.meta.get("categories") or []
    books = parse_books(cats)
    body = page.body
    lines = body.split("\n")
    first_h2 = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    intro = "\n".join(lines[:first_h2])
    fields = normalize_fields(extract_fields(body))
    prov = {
        "source": "wiki",
        "file": page.file,
        "url": page.meta.get("source_url"),
        "revision_id": page.meta.get("revision_id"),
        "heading": heading,
        "line_start": 1,
        "line_end": page.line_count,
        "split": True,
    }
    base = {
        "type": classify_section(body) or "section",
        "name": heading,
        "slug": page.slug,
        "page_id": page.id,
        "categories": cats,
        "books": books,
        "fields": fields,
        "summary": summary_of(intro) or summary_of(body),
        "prerequisites": split_prereq(fields.get("prerequisites", "")),
        "prerequisite_detail": util.parse_prerequisites(fields.get("prerequisites", "")),
        "provenance": prov,
        "flags": ["from-compilation-section"],
        "parent": parent,
    }
    out = [_finish(base)]
    if base["type"] == "section":
        out = []
    if (page.meta.get("type") or "") == "talent-tree":
        tree_name = re.sub(r"\s*\(part.*?\)\s*$", "", re.sub(r"^.*—\s*", "", page.title, flags=re.S), flags=re.I)
        for sec, parent_sec in _children_of_level(page, 3):
            sfields = normalize_fields(extract_fields(sec.text))
            out.append(
                _finish(
                    {
                        **base,
                        "type": "talent",
                        "name": sec.title,
                        "tree": tree_name,
                        "scope": parent_sec.title if parent_sec else "Talents",
                        "fields": sfields,
                        "summary": summary_of(sec.text),
                        "prerequisites": split_prereq(sfields.get("prerequisites", "")),
                        "prerequisite_detail": util.parse_prerequisites(sfields.get("prerequisites", "")),
                        "provenance": {**prov, "line_start": sec.line_start, "line_end": sec.line_end},
                        "flags": ["from-talent-tree", "from-compilation-section"],
                    }
                )
            )
    return out


def classify_page(page: Page) -> str:
    from .wiki import classify  # local import to avoid module-cycle noise

    return classify(page)
