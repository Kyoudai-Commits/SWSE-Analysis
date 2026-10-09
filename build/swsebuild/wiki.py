"""Wiki corpus loader: dedupe, de-noise, link-normalize, sectionize.

Design notes (what this module decides and why):

* ``raw/`` (``swse-miraheze-org/``) is treated as immutable. Every page is
  re-emitted under ``normalized/wiki/`` with:
  - crawl noise removed (``Loading comments...``, the duplicated ``> Source:``
    line that restates front matter, external CDN image transclusions),
  - MediaWiki markup noise removed (``action=edit&redlink=1`` hrefs),
  - internal links collapsed from ``[T](https://swse.miraheze.org/wiki/T "T")``
    to ``[[T]]`` / ``[[T|alias]]``. That single change removes ~40% of the
    corpus token count while *adding* structure an agent can resolve.
* 150 of 1,074 files are byte-identical redirect-crawl artifacts. They collapse
  to one canonical page each; every dropped file is preserved as a provenance
  record (its ``source_url`` is exactly the redirect an agent should follow).
* Oversized pages (58 ``Category:*`` pages that are really whole campaign books,
  plus a handful of long rules pages) are physically split at ``##`` headings so
  that no single file can blow a context window.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from . import util

WIKI_BASE = "https://swse.miraheze.org/wiki/"

# Size policy: a page bigger than this is split into section files so that no
# single Read() call can blow a context window.
SPLIT_THRESHOLD = 16000
MAX_CHILD_CHARS = 20000

# --- classification -------------------------------------------------------
_TYPE_BY_CATEGORY = [
    ("Talent Trees", "talent-tree"),
    ("Force Powers", "force-power"),
    ("Feats", "feat"),
    ("Species", "species"),
    ("Heroic Classes", "heroic-class"),
    ("Prestige Classes", "prestige-class"),
    ("Starships", "starship"),
    ("Vehicles", "vehicle"),
    ("Armor", "armor"),
    ("Weapons", "weapon"),
    ("Equipment Upgrades", "upgrade"),
    ("Implants", "implant"),
    ("Affiliations", "affiliation"),
    ("Reference Books", "reference-book"),
    ("Eras", "era"),
    ("Actions", "action"),
    ("Skills", "skill"),
]

_KNOWN_TYPES = {
    "talent-tree", "force-power", "feat", "species", "heroic-class", "prestige-class",
    "starship", "vehicle", "armor", "weapon", "upgrade", "implant", "affiliation",
    "reference-book", "era", "action", "skill", "creature", "droid", "planet",
    "organization", "rule", "keyword", "campaign", "npc", "compilation", "index", "other",
}


def classify(page: "Page") -> str:
    """Assign one primary type per page.

    Order matters: an entity-shaped category beats a shape heuristic, which beats
    a slug regex, which beats the ``Core Rulebook`` fallback. The goal is that an
    agent can trust ``type`` to mean "how do I query this", not "what folder was it
    in" -- so the chapter/keyword pages that dominate the uncategorised tail get
    named types (``rule``, ``skill``, ``action``, ``equipment``, ``npc``) instead of
    dumping into ``other``.
    """
    cats = [c.strip() for c in (page.meta.get("categories") or [])]
    catset = set(cats)
    title = util.squash(re.sub(r"^Category\s*:\s*", "", page.title, flags=re.I))
    if page.slug.startswith("Category:"):
        return "compilation" if len(page.body) > SPLIT_THRESHOLD else "index"
    for cat, typ in _TYPE_BY_CATEGORY:
        if cat in catset:
            return typ
    if _RE_SKILL_TITLE.match(title):
        return "skill"
    for cat, typ in _CAT_TYPE:
        if cat in catset:
            return typ
    if any(c.endswith("Actions") for c in cats):
        return "action"
    if title in _RULE_TITLES:
        return "rule"
    low = page.slug.lower()
    if "talent-tree" in low or "talent tree" in title.lower():
        return "talent-tree"
    if re.search(r"\\d+-degree", low) or ("droid" in low and ("degree" in low or "template" in low)):
        return "droid"
    if "template" in low:
        return "creature"
    if "beast" in low or "creature" in low:
        return "creature"
    if "planet" in catset or "worlds" in catset or re.search(r"\(Planet\)$", title) or re.search(r"\(Planet\)$", title):
        return "planet"
    if "organizations" in low or low.startswith("organization"):
        return "organization"
    if any(c in catset for c in ("Keywords", "Hazards", "Conditions")):
        return "keyword"
    if any(c.endswith("Bonus Feats") for c in cats):
        return "feat"
    if "Core Rulebook" in catset:
        return "rule"
    return "other"


_RE_SKILL_TITLE = re.compile(r"^(?P<name>.+)\s\((Str|Dex|Con|Int|Wis|Cha)\)$")

_CAT_TYPE = [
    ("Droid Systems", "droid-system"),
    ("Processor Systems", "droid-system"),
    ("Locomotion Systems", "droid-system"),
    ("Appendages", "droid-system"),
    ("Weapon Groups", "weapon-group"),
    ("General Equipment", "equipment"),
    ("Medical Gear", "equipment"),
    ("Survival Gear", "equipment"),
    ("Clothing", "equipment"),
    ("Alien Accessories", "equipment"),
    ("Bio-Implants", "implant"),
    ("Crew Positions", "crew-position"),
    ("Challenge Effects", "challenge"),
    ("Heroic Units", "npc"),
    ("Villain Units", "npc"),
    ("Minion Units", "npc"),
    ("Eras", "era"),
    ("Affiliations", "affiliation"),
    ("Organizations", "organization"),
    ("Planets", "planet"),
    ("Weapons", "weapon"),
    ("Armor", "armor"),
    ("Skills", "skill"),
]

_RULE_TITLES = {
    "Abilities", "Actions", "Attacks", "Attacks of Opportunity", "Backgrounds", "Character Creation",
    "Character Sheet", "Class Skills", "Combat", "Combat Sequence", "Conditions", "Defenses", "Destiny",
    "Force Powers", "Force Traditions", "Galactic Gazetteer", "Gamemastering", "Heroic Classes",
    "Heroic Traits", "Hit Points", "Introduction", "Ion Damage", "Languages", "Level Benefits",
    "Line of Sight", "Prestige Classes", "Skill Challenges", "Special Actions", "Speed", "Starships",
    "Vehicles", "Droids", "Equipment", "Followers", "The Force", "The Jedi", "The Sith", "The Dark Side",
    "Damage Threshold", "Other Effects", "Additional Rules", "Appendices", "Ranged Combat", "Melee Combat",
    "Common Situations", "Hazards", "Objects", "Cover", "Injury and Death", "Narrative",
}

# --------------------------------------------------------------------------
# patterns
# --------------------------------------------------------------------------

# crawl residue
_RE_SOURCE_LINE = re.compile(r"^> Source: \[?.*?Retrieved .*?\.\s*\n", re.M | re.S)
_RE_LOADING = re.compile(r"^\s*Loading comments\.\.\.\s*$", re.M)
_RE_IMAGE_LINK = re.compile(r"\[!\[[^\]]*\]\((?P<src>[^)]*)\)\]\((?P<href>[^)]*)\)")
_RE_IMAGE_BARE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# MediaWiki slugs contain parentheses ("Weapon_Proficiency_(Pistols)", and two
# levels for "Skill_Focus_(Knowledge_(Bureaucracy))"), so href matching must be
# paren-balanced -- a naive ``[^)]*`` silently truncates those targets, which is
# how 28 links originally survived normalization as raw URLs.
_HREF = r"(?:[^()\s]|\((?:[^()\s]|\([^()\s]*\))*\))*"
# the crawler's "Title" attributes carry escaped quotes ("SD-6 \"Hulk\" ..."),
# which break any simple quote-matching regex. They restate the link text, so
# they are dropped first and the link regex only has to handle the href.
_TITLE_ATTR = r'\s+"(?:\\.|[^"\\])*"'
_RE_TITLE_ATTR = re.compile(r"(\]\(" + _HREF + r")" + _TITLE_ATTR + r"(\))")
_RE_MD_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]\[]*)\]\((?P<href>" + _HREF + r")\)")

# **Field:** value  /  *Field:* value
# field labels appear bare ("**Effect:** …"), as bullets ("- **Ability Modifiers:** …")
# and as italic labels ("*Prerequisite:* …"), so the leading marker is optional
_RE_BOLD_FIELD = re.compile(r"^(?:[-*+] |[ \t]{2,})?\*\*(?P<k>[^*]{1,60}):\*\*[ \t]*", re.M)
_RE_ITAL_FIELD = re.compile(r"^(?:[-*+] |[ \t]{2,})?\*(?P<k>[^*]{1,60}):\*[ \t]+", re.M)

# crawler filename noise: ``slug-1a2b3c4d.md``
_RE_HASH_SUFFIX = re.compile(r"-[0-9a-f]{8}$")


@dataclass
class Section:
    level: int
    title: str
    text: str
    line_start: int
    line_end: int

    def as_dict(self, path: list[str] | None = None) -> dict:
        return {
            "heading": path,
            "level": self.level,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "chars": len(self.text),
            "tokens": util.tokens(self.text),
        }


@dataclass
class Page:
    file: str
    slug: str
    title: str
    meta: dict
    body: str
    sections: list[Section] = field(default_factory=list)
    children: list[str] = field(default_factory=list)  # split-off child files
    dup_of: str | None = None
    dup_sources: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    #: heading -> child file path, populated when the page is split
    child_paths: dict[str, str] = field(default_factory=dict)
    out_file: str = ""
    type: str = "other"
    line_count: int = 0
    n_duplicates: int = 0
    duplicates: list = field(default_factory=list)
    #: explicit identity, set when reading normalized files (a split section's id is
    #: ``wiki:<Parent>#NNN``, which cannot be derived from the file name)
    page_id: str = ""

    @property
    def id(self) -> str:
        return self.page_id or f"wiki:{self.slug}"


# --------------------------------------------------------------------------
# link + field rewriting
# --------------------------------------------------------------------------


def _slug_from_href(href: str) -> str | None:
    if not href.startswith(WIKI_BASE):
        return None
    target = href[len(WIKI_BASE) :]
    target = target.split("#", 1)[0]
    target = re.sub(r"\?action=edit.*$", "", target)
    target = _unquote(target)
    return target.rstrip("/") or None


def _unquote(text: str) -> str:
    for src, dst in (("%27", "'"), ("%22", '"'), ("%23", "#"), ("%25", "%"), ("%28", "("), ("%29", ")"), ("%2F", "/")):
        text = text.replace(src, dst)
    return text


def _display_matches(text: str, slug: str) -> bool:
    a = util.squash(util.decurly(text)).lower().replace("_", " ")
    b = util.squash(slug.replace("_", " ")).lower()
    return a == b


def rewrite_links(body: str) -> tuple[str, list[str], list[str], list[tuple[str, str]]]:
    """``[text](wiki/Target "T")`` -> ``[[Target]]``.

    Returns (text, link_targets, redlinks, alias_pairs) where ``alias_pairs`` are
    ``(target_slug, displayed_text)`` for every link whose anchor text differs from
    the target's own title -- i.e. the wiki's real synonym lexicon ("hit points" ->
    Hit_Point, "Reflex" -> Reflex_Defense), which we reuse to resolve agent queries.
    """
    redlinks: list[str] = []
    links: list[str] = []
    pairs: list[tuple[str, str]] = []

    def sub(m: re.Match) -> str:
        text, href = m.group("text"), m.group("href")
        slug = _slug_from_href(href)
        if slug is None:
            return m.group(0)  # external link: leave alone
        links.append(slug)
        if "action=edit&redlink=1" in href:
            redlinks.append(slug)
        if not text or text.strip() == "&quot;" or _display_matches(text, slug):
            return f"[[{slug}]]"
        clean = util.squash(util.decurly(re.sub(r"\s+", " ", text)))
        clean = re.sub(r"\[|\]|\(|\)|[*_`]", "", clean).strip()
        if clean and len(clean) < 60:
            pairs.append((slug, clean))
        return f"[[{slug}|{clean}]]"

    out = _RE_MD_LINK.sub(sub, body)
    return out, links, redlinks, pairs


def strip_markup(text: str) -> str:
    """Plain-text rendering of a heading/cell (no [[links]], no emphasis)."""
    t = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    t = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).replace("_", " "), t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_`]", "", t)
    return util.squash(t)


def extract_fields(body: str) -> dict[str, str]:
    """Collect ``**Key:** value`` stat lines (may continue across lines)."""
    lines = body.split("\n")
    fields: dict[str, str] = {}
    i = 0
    while i < len(lines):
        m = _RE_BOLD_FIELD.match(lines[i]) or _RE_ITAL_FIELD.match(lines[i])
        if not m:
            i += 1
            continue
        key = util.squash(strip_markup(m.group("k"))).rstrip(":").strip()
        if len(key) < 2 or (len(key) == 2 and key[-1] == ")") or key.isdigit():
            i += 1
            continue  # "**a)** …", "**1)** …": list markers inside a paragraph, not fields
        value = util.squash(strip_markup(lines[i][m.end() :]))
        if not value or value.endswith(":"):
            # the value is a block that follows: bullets (prestige-class
            # prerequisites) or a continuation paragraph
            follow, items = [], []
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1  # a label whose block follows after a blank line
            while j < len(lines) and lines[j].strip():
                ln = lines[j]
                if ln.startswith(("#", "|")):
                    break
                if re.match(r"^\s*[-*] ", ln):
                    items.append(re.sub(r"^\s*[-*] ", "", ln))
                elif items:
                    items[-1] = items[-1] + " " + util.squash(ln)
                else:
                    follow.append(ln)
                j += 1
            if items:
                value = util.squash(strip_markup("; ".join(items)))
            else:
                value = util.squash(value + " " + strip_markup(" ".join(follow))) if follow else value
        # continuation: none, keep tight. merge duplicates with ' ; '
        if key in fields and fields[key] != value:
            fields[key] = f"{fields[key]} ; {value}" if value else fields[key]
        else:
            fields.setdefault(key, value)
        i += 1
    return fields


# --------------------------------------------------------------------------
# cleaning pipeline
# --------------------------------------------------------------------------


def clean_body(raw_body: str) -> tuple[str, list[str], list[str], list[str], list[tuple[str, str]]]:
    body = raw_body.replace("\r\n", "\n").replace("\r", "\n")
    files: list[str] = []

    def drop_image(m: re.Match) -> str:
        src = m.group("href") if m.lastgroup == "href" else m.group(1)
        src = src or ""
        name = re.search(r"File:([^)\s]+)", src)
        if name:
            files.append("File:" + name.group(1))
        return ""

    body = _RE_IMAGE_LINK.sub(drop_image, body)
    body = _RE_IMAGE_BARE.sub(drop_image, body)
    body = _RE_TITLE_ATTR.sub(r"\1\2", body)
    body, links, redlinks, pairs = rewrite_links(body)
    body = _RE_SOURCE_LINE.sub("", body)
    body = _RE_LOADING.sub("", body)
    body = re.sub(r"\*\[[^\]]*\]\([^)]*\)\*", "", body)  # bare linked italic line
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = re.sub(r"[ \t]+\n", "\n", body)
    return body.strip() + "\n", links, redlinks, files, pairs


def sectionize(body: str) -> list[Section]:
    """Split on ATX headings into a flat, ordered list with line ranges."""
    lines = body.split("\n")
    heads = []
    for idx, line in enumerate(lines, start=1):
        m = _RE_HEADING.match(line)
        if m and not line.startswith("```"):
            heads.append((idx, len(m.group(1)), strip_markup(m.group(2))))
    sections: list[Section] = []
    if not heads:
        return [Section(0, "", body.strip(), 1, len(lines))]
    # text before the first heading
    pre = "\n".join(lines[: heads[0][0] - 1]).strip()
    if pre:
        sections.append(Section(0, "(top)", pre, 1, heads[0][0] - 1))
    for n, (line_no, level, title) in enumerate(heads):
        end = heads[n + 1][0] - 1 if n + 1 < len(heads) else len(lines)
        text = "\n".join(lines[line_no:end]).strip()
        sections.append(Section(level, title, text, line_no, end))
    return sections


def load_pages(wiki_dir: str) -> list[Page]:
    """Load + clean every ``*.md`` page, dedupe redirect-crawl twins."""
    pages: dict[str, Page] = {}
    groups: dict[str, list[Page]] = {}
    for name in sorted(os.listdir(wiki_dir)):
        if not name.endswith(".md"):
            continue
        raw = util.read_text(os.path.join(wiki_dir, name))
        meta, body = util.parse_front_matter(raw)
        slug = ""
        cu = meta.get("canonical_url") or ""
        if cu:
            slug = _unquote(re.sub(r"\?action=edit.*$", "", cu.split("/wiki/")[-1]))
        if not slug:
            slug = _RE_HASH_SUFFIX.sub("", name[:-3]).replace("-", "_")
            slug = "_".join(w.capitalize() for w in slug.split("_")) or name[:-3]
        clean, links, redlinks, images, pairs = clean_body(body)
        page = Page(file=name, slug=slug, title=meta.get("title") or slug.replace("_", " "), meta=meta, body=clean)
        page.flags = []
        if redlinks:
            page.meta["_redlinks"] = sorted(set(redlinks))
        page.meta["_links"] = links
        page.meta["_alias_pairs"] = sorted(set(pairs))
        page.meta["_images"] = images
        page.sections = sectionize(clean)
        pages[util.sha16(page.body) + ":" + slug] = page
        groups.setdefault(slug, []).append(page)

    out: list[Page] = []
    for slug, grp in sorted(groups.items()):
        # canonical pick: filename matches the slug, else newest revision, else first
        def rank(p: Page) -> tuple:
            base = _RE_HASH_SUFFIX.sub("", p.file[:-3])
            exact = 0 if base.replace("-", "_").lower() == slug.replace("-", "_").lower() else 1
            try:
                rev = -int(str(p.meta.get("revision_id") or 0))
            except ValueError:
                rev = 0
            return (exact, rev, p.file)

        grp.sort(key=rank)
        keeper = grp[0]
        seen = {util.sha16(keeper.body)}
        for other in grp[1:]:
            h = util.sha16(other.body)
            if h in seen:
                keeper.dup_sources.append(
                    {
                        "file": other.file,
                        "source_url": other.meta.get("source_url"),
                        "revision_id": other.meta.get("revision_id"),
                        "retrieved_at_utc": other.meta.get("retrieved_at_utc"),
                        "reason": "byte-identical body (redirect-crawl duplicate)",
                    }
                )
                other.dup_of = keeper.slug
            else:
                other.dup_of = keeper.slug
                other.flags.append("variant-body")
                keeper.dup_sources.append(
                    {
                        "file": other.file,
                        "source_url": other.meta.get("source_url"),
                        "revision_id": other.meta.get("revision_id"),
                        "retrieved_at_utc": other.meta.get("retrieved_at_utc"),
                        "reason": "same canonical page, different revision/anchor text",
                    }
                )
        keeper.flags.append("deduped" if keeper.dup_sources else "unique")
        out.append(keeper)
    out.sort(key=lambda p: p.slug)
    return out


# --------------------------------------------------------------------------
# emission
# --------------------------------------------------------------------------


def _pretty_name(page: "Page") -> str:
    """File-stem name: category pages lose their ``Category:`` prefix."""
    name = re.sub(r"^(Category|File)\s*:\s*", "", page.title, flags=re.I)
    return name or page.slug.split(":")[-1]


def emit_pages(
    pages: list["Page"],
    out_dir: str,
    root: str,
    split_over: int = SPLIT_THRESHOLD,
) -> list[dict]:
    """Write one normalized file per canonical page; oversized pages are split.

    Layout::

        normalized/wiki/by-title/<Slug>.md   normal pages (whole, in order)
        normalized/wiki/pages/<Slug>.md      oversized page: front matter + TOC
        normalized/wiki/pages/<Slug>/007-*.md  its section files

    Returns page records (with a private ``_page`` handle for the chunk pass).
    """
    records: list[dict] = []
    for page in pages:
        pretty = _pretty_name(page)
        is_cat = page.slug.startswith("Category:")
        display = page.title
        if is_cat:
            display = f"{pretty} ({'Compilation' if len(page.body) > split_over else 'Category'})"
        meta = {
            "title": display,
            "id": page.id,
            "slug": page.slug,
            "type": classify(page),
            "source_url": page.meta.get("source_url"),
            "canonical_url": page.meta.get("canonical_url"),
            "revision_id": page.meta.get("revision_id"),
            "retrieved_at_utc": page.meta.get("retrieved_at_utc"),
            "categories": page.meta.get("categories") or [],
        }
        if page.meta.get("_images"):
            meta["images"] = page.meta["_images"]
        if page.meta.get("_redlinks"):
            meta["redlinks"] = page.meta["_redlinks"]
        if page.dup_sources:
            meta["duplicates"] = [
                {"file": d["file"], "source_url": d["source_url"], "revision_id": d["revision_id"], "reason": d["reason"]}
                for d in page.dup_sources
            ]

        slug_file = util.slugify(_pretty_name(page)) + ".md"
        big = len(page.body) > split_over
        if big:
            child_dir = os.path.join(out_dir, "pages", util.slugify(_pretty_name(page)))
            path = os.path.join(out_dir, "pages", slug_file)
        else:
            child_dir = ""
            path = os.path.join(out_dir, "by-title", slug_file)
        util.ensure_dir(os.path.dirname(path))

        children: list[dict] = []
        body = page.body
        if big:
            body, children = emit_children(page, child_dir, meta, root)
            toc = "\n".join(
                f"| {c['heading']} | {c['chars']:,} | `{c['path']}` |" for c in children
            )
            body = (
                f"> **Split page:** the original was {len(page.body):,} chars, so each section "
                f"below is its own file under `{util.rel(root, child_dir)}/`\n\n"
                f"## Section files\n\n| heading | chars | file |\n| --- | --- | --- |\n{toc}\n"
            ) + ("\n\n" + body if body else "")
        page.out_file = util.rel(root, path)
        util.write_text(path, util.dump_front_matter(meta) + "\n" + body)

        records.append(
            {
                "id": page.id,
                "title": page.title,
                "slug": page.slug,
                "type": meta["type"],
                "file": util.rel(root, path),
                "categories": meta["categories"],
                "revision_id": page.meta.get("revision_id"),
                "retrieved_at_utc": page.meta.get("retrieved_at_utc"),
                "chars": len(page.body),
                "tokens": util.tokens(page.body),
                "n_sections": len([s for s in page.sections if s.level >= 2]),
                "n_links": len(page.meta.get("_links") or []),
            "link_targets": page.meta.get("_links") or [],
            "anchor_aliases": page.meta.get("_alias_pairs") or [],
            "n_alias_pairs": len(page.meta.get("_alias_pairs") or []),
                "n_redlinks": len(meta.get("redlinks") or []),
            "n_duplicates": len(page.dup_sources),
            "duplicates": [d["file"] for d in page.dup_sources],
            "duplicate_sources": page.dup_sources,
                "split": bool(children),
                "n_children": len(children),
                "flags": page.flags,
                "_page": page,
            }
        )
    return records


def emit_children(page: "Page", child_dir: str, meta: dict, root: str) -> tuple[str, list[dict]]:
    """Split an oversized page at ``##`` headings; returns (intro, child records)."""
    util.ensure_dir(child_dir)
    children: list[dict] = []
    intro_parts: list[str] = []
    top_idx = [i for i, s in enumerate(page.sections) if s.level == 2]
    if not top_idx:
        top_idx = [i for i, s in enumerate(page.sections) if s.level >= 3]
    first = top_idx[0] if top_idx else len(page.sections)
    intro_parts = [s.text for s in page.sections[:first] if s.text and s.level < 2]

    for n, start in enumerate(top_idx):
        end = top_idx[n + 1] if n + 1 < len(top_idx) else len(page.sections)
        block = page.sections[start:end]
        sec = block[0]
        text = "\n\n".join(b.text for b in block if b.text)
        # keep each child file inside a sane read budget
        if len(text) > MAX_CHILD_CHARS:
            text = _hard_wrap(text, MAX_CHILD_CHARS)
            parts = text.split("\n\n<!-- continued part -->\n\n")
        else:
            parts = [text]
        for pi, part in enumerate(parts):
            suffix = "" if len(parts) == 1 else f"-{pi + 1}"
            name = f"{n:03d}-{util.kebab(sec.title)[:56]}{suffix}.md"
            path = os.path.join(child_dir, name)
            child_meta = {
                "title": f"{meta.get('title') or page.title} — {sec.title}" + (f" (part {pi + 1}/{len(parts)})" if len(parts) > 1 else ""),
            "parent_title": page.title,
                "id": f"{page.id}#{n:03d}{('p' + str(pi + 1)) if len(parts) > 1 else ''}",
                "type": meta.get("type"),
                "parent": page.id,
                "parent_title": meta.get("title") or page.title,
                "heading": sec.title,
                "heading_path": [meta.get("title") or page.title, sec.title],
                "source_url": f"{meta.get('canonical_url')}#{util.slugify(sec.title)}",
                "revision_id": page.meta.get("revision_id"),
                "categories": meta.get("categories") or [],
            }
            util.write_text(
                path,
                util.dump_front_matter(child_meta) + "\n" + f"# {sec.title}\n\n" + part.strip() + "\n",
            )
            page.child_paths.setdefault(sec.title, util.rel(root, path))
            children.append(
                {
                    "path": util.rel(root, path),
                    "heading": sec.title + (f" (part {pi + 1})" if len(parts) > 1 else ""),
                    "chars": len(part),
                    "tokens": util.tokens(part),
                    "id": child_meta["id"],
                }
            )
    return "\n\n".join(p for p in intro_parts if p).strip(), children


def _hard_wrap(text: str, limit: int) -> str:
    """Guarantee a size ceiling by cutting at paragraph boundaries."""
    if len(text) <= limit:
        return text
    out = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut < limit // 3:
            cut = text.rfind("\n", 0, limit)
        if cut < limit // 3:
            cut = limit
        out.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        out.append(text)
    return "\n\n<!-- continued part -->\n\n".join(out)


# --------------------------------------------------------------------------
# second pass: read back what we emitted (so chunks/entities cite real files)
# --------------------------------------------------------------------------


def load_normalized(root_dir: str, repo_root: str) -> list["Page"]:
    """Re-load the emitted normalized tree.

    Chunk line ranges and entity provenance must refer to files an agent can
    actually open, so the record layer works off these files rather than off the
    in-memory raw pages: for a split page, ``file`` is the *section* file and
    ``line_start``/``line_end`` are its real lines.
    """
    out: list[Page] = []
    for dirpath, _dirs, files in os.walk(root_dir):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            raw = util.read_text(path)
            meta, body = util.parse_front_matter(raw)
            ident = meta.get("id") or ""
            slug = meta.get("slug") or ident.replace("wiki:", "").split("#")[0] or name[:-3]
            page = Page(
                file=util.rel(repo_root, path),
                slug=slug,
                page_id=ident,
                title=meta.get("title") or name[:-3],
                meta={**meta, "_links": re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", body), "_alias_pairs": []},
                body=body,
            )
            page.type = meta.get("type") or "other"
            page.sections = sectionize(body)
            page.line_count = len(body.split("\n"))
            out.append(page)
    out.sort(key=lambda p: (p.slug.startswith("pages/"), p.slug))
    return out


def mark_cross_duplicates(root_dir: str, repo_root: str) -> int:
    """Back-reference sections whose *text* is identical across different pages.

    The wiki itself repeats content: campaign-book compilation pages restate whole
    chapters that also exist as standalone articles (``Category:Clone Wars Campaign
    Guide`` contains *The Council of First Knowledge*, which is also a section of
    ``The Jedi``). Those are not crawl artifacts, so they are kept -- but each copy
    gets ``same_as`` in its front matter, and an agent that reads one knows the other
    is word-for-word identical instead of re-reading it.
    """
    groups: dict[str, list[str]] = {}
    metas: dict[str, tuple[dict, str]] = {}
    for dirpath, _d, names in os.walk(root_dir):
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            raw = util.read_text(path)
            meta, body = util.parse_front_matter(raw)
            metas[path] = (meta, body)
            groups.setdefault(util.sha16(body), []).append(path)
    n_marked = 0
    for _hash, paths in groups.items():
        if len(paths) < 2:
            continue
        rels = sorted(util.rel(repo_root, pth) for pth in paths)
        for path in paths:
            meta, body = metas[path]
            others = [r for r in rels if r != util.rel(repo_root, path)]
            if meta.get("same_as") == others:
                continue
            meta["same_as"] = others
            util.write_text(path, util.dump_front_matter(meta) + "\n" + body)
            n_marked += 1
    return n_marked
