"""Hooks: the corpus-specific quirks that cannot be expressed declaratively.

Three kinds, all registered by name and referenced from ``config/entities.yaml``:

``ROW_HOOKS[name](ctx, raw_row) -> dict | None``
    Transform one extracted raw row *before* it becomes a record. Return
    ``None`` to drop the row (e.g. spreadsheet section labels).

``ENTITY_HOOKS[name](ctx, record) -> None``
    Enrich one merged canonical record in place (adds ``relations``, ``flags``,
    derived ``attrs``).

``POST_HOOKS[name](ctx) -> None``
    Run once after every entity is built; used for cross-entity work such as
    deriving talent trees from talent rows or attaching wiki URLs.

``ctx`` is a :class:`CanonContext` giving access to raw blocks, the records
built so far and the curation overlay.
"""

from __future__ import annotations

import re
from collections import Counter

from .ids import dedupe, fold, norm_key, slugify, split_list
from .sourcebooks import parse_source_tags

# ---------------------------------------------------------------------------
# Row hooks
# ---------------------------------------------------------------------------
ROW_HOOKS = {}
ENTITY_HOOKS = {}
POST_HOOKS = {}


def row_hook(name):
    def deco(fn):
        ROW_HOOKS[name] = fn
        return fn
    return deco


def entity_hook(name):
    def deco(fn):
        ENTITY_HOOKS[name] = fn
        return fn
    return deco


def post_hook(name):
    def deco(fn):
        POST_HOOKS[name] = fn
        return fn
    return deco


SECTION_LABEL = re.compile(r"^\s*-{1,3}\s*(?P<label>[^-]+?)\s*-{1,3}\s*$")


@row_hook("drop_section_labels")
def drop_section_labels(ctx, row):
    """Drop spreadsheet section dividers like ``-- Melee Weapons --``."""
    for key, value in row.items():
        if key.startswith("_"):
            continue
        if isinstance(value, str):
            m = SECTION_LABEL.match(value)
            if m:
                ctx.note_dropped(row["_block"], row["_row"], f"section label: {m.group('label').strip()}")
                return None
    return row


@row_hook("drop_placeholder_rows")
def drop_placeholder_rows(ctx, row):
    """Drop rows whose only meaningful content is a UI placeholder ('None', 'Custom armor')."""
    name = row.get("name") or row.get("key")
    if isinstance(name, str) and name.strip().lower() in {"none", "n/a", "-", "(none)", "custom armor", "custom"}:
        ctx.note_dropped(row["_block"], row["_row"], f"placeholder row: {name!r}")
        return None
    return row


@row_hook("mr_heroic_homebrew_section")
def mr_heroic_homebrew_section(ctx, row):
    """The Master Reference 'Heroic Classes' sheet mixes official and homebrew.

    Row 7 is a bare ``Homebrew`` label; everything after it is homebrew and must
    not be presented as official content.
    """
    values = [v for k, v in row.items() if not k.startswith("_") and v not in (None, "")]
    name = fold(row.get("class"))
    if name.lower() == "homebrew" and len(values) <= 1:
        ctx.state["mr_homebrew"] = True
        ctx.note_dropped(row["_block"], row["_row"], "homebrew section label")
        return None
    if ctx.state.get("mr_homebrew"):
        row["_canon"] = "homebrew"
        row.setdefault("_flags", []).append("homebrew")
    return row


@row_hook("talent_layout")
def talent_layout(ctx, row):
    """Recover talent name / tree / tier column from SagaForge's visual layout.

    ``Talents!B`` holds the name for most rows, but a few rows put it only in one
    of the tier columns E-I. C (owning class) and D (tree) are sparse and already
    forward-filled by the extractor.
    """
    tier_cols = [("layout_t1", 1), ("layout_t2", 2), ("layout_t3", 3), ("layout_t4", 4), ("layout_t5", 5)]
    name = row.get("name")
    column = None
    for field, idx in tier_cols:
        v = row.get(field)
        if v:
            column = idx
            if not name:
                name = v
            break
    if not name:
        ctx.note_dropped(row["_block"], row["_row"], "talent row with no name")
        return None
    row["name"] = fold(name)
    row["layout_column"] = column
    row["tree"] = fold(row.get("tree")) if row.get("tree") else None
    row["class_group"] = fold(row.get("class_group")) if row.get("class_group") else None
    for field, _ in tier_cols:
        row.pop(field, None)
    if row.get("page") is not None and not row.get("page_ref"):
        row["page_ref"] = row["page"]
    row.pop("page", None)
    for junk in ("available_flag", "taken_flag", "times_taken", "met_flag", "col_d"):
        row.pop(junk, None)
    return row


@row_hook("feat_cleanup")
def feat_cleanup(ctx, row):
    """Feats sheet: drop builder-UI columns, normalise the page reference."""
    for junk in ("met_flag", "taken_flag", "times_taken", "col_d"):
        row.pop(junk, None)
    if row.get("page") is not None:
        row["page_ref"] = row["page"]
        row.pop("page", None)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "feat row with no name")
        return None
    row["name"] = fold(row["name"])
    return row


@row_hook("force_power_marks")
def force_power_marks(ctx, row):
    """Turn SagaForge's 'x' supplement marks into sourcebook ids."""
    marks = {"supp_kotor": "kotor", "supp_tfu": "tfu", "supp_cwcs": "cw",
             "supp_lecg": "lecg", "supp_jatm": "jadm"}
    hits = [sb for field, sb in marks.items() if row.get(field) in {"x", "X", True, 1}]
    for field in list(marks) + ["uses", "taken_count", "slug"]:
        row.pop(field, None)
    if row.get("page") is not None:
        row["page_ref"] = row.pop("page")
    if hits:
        row["_sourcebook_ids"] = hits
    for junk in ("available_flag", "taken_flag", "times_taken"):
        row.pop(junk, None)
    return row


@row_hook("class_cleanup")
def class_cleanup(ctx, row):
    for junk in ("validation", "statblock_key", "col_bw", "no"):
        row.pop(junk, None)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "class row with no name")
        return None
    row["name"] = fold(row["name"])
    return row


@row_hook("mr_class_columns")
def mr_class_columns(ctx, row):
    """Master Reference class sheets use shouting header names."""
    renames = {
        "class": "name", "prestige_class": "name",
        "starting_hit_points": "starting_hit_points",
        "defense_bonus": "defense_bonus",
        "trained_skills": "trained_skills_formula",
        "class_skills": "class_skills_text",
        "starting_feats": "starting_feats_text",
        "talent_trees": "talent_trees_text",
        "links": "url",
        "prerequisites": "prerequisites_text",
    }
    for old, new in renames.items():
        if old in row and old != new:
            row[new] = row.pop(old)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "class row with no name")
        return None
    row["name"] = fold(row["name"])
    if row["_block"] == "mr_prestige_classes":
        row["class_kind"] = "prestige"
    else:
        row["class_kind"] = "heroic"
    return row


@row_hook("species_cleanup")
def species_cleanup(ctx, row):
    for junk in ("key",):
        row.pop(junk, None)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "species row with no name")
        return None
    row["name"] = fold(row["name"])
    tags = parse_source_tags(row.get("source_tag"))
    if tags:
        row["_sourcebook_ids"] = [t["sourcebook"] for t in tags if t.get("sourcebook")]
    return row


@row_hook("tag_to_sourcebooks")
def tag_to_sourcebooks(ctx, row):
    """Generic: convert a ``source_tag`` cell into sourcebook ids."""
    tags = parse_source_tags(row.pop("source_tag", None))
    ids = [t["sourcebook"] for t in tags if t.get("sourcebook")]
    unresolved = [t["raw"] for t in tags if not t.get("sourcebook")]
    if ids:
        row["_sourcebook_ids"] = ids
    if unresolved:
        row["_sourcebook_unresolved"] = unresolved
    return row


@row_hook("page_to_sourcebooks")
def page_to_sourcebooks(ctx, row):
    """Generic: keep ``page`` as ``page_ref`` for later sourcebook resolution."""
    if row.get("page") is not None and not row.get("page_ref"):
        row["page_ref"] = row.pop("page")
    return row


@row_hook("droid_option_group")
def droid_option_group(ctx, row):
    group = ctx.state.get("droid_group") or "unspecified"
    row["option_group"] = group
    for junk in ("statblock", "final_cost", "final_weight"):
        row.pop(junk, None)
    return row


@row_hook("mr_force_power_columns")
def mr_force_power_columns(ctx, row):
    renames = {"force_power": "name", "type": "descriptor", "time_requiement": "action_type",
               "time_requirement": "action_type", "description": "summary", "links": "url"}
    for old, new in renames.items():
        if old in row:
            row[new] = row.pop(old)
    if row.get("descriptor") in {"N/A", "NA", "-"}:
        row["descriptor"] = None
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "force power row with no name")
        return None
    row["name"] = fold(row["name"])
    return row


@row_hook("mr_talent_tree_columns")
def mr_talent_tree_columns(ctx, row):
    renames = {"talent_tree": "name", "availability": "availability_text",
               "description": "summary", "links": "url"}
    for old, new in renames.items():
        if old in row:
            row[new] = row.pop(old)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "talent tree row with no name")
        return None
    row["name"] = fold(row["name"])
    row["availability"] = split_list(row.get("availability_text"))
    return row


@row_hook("mr_feat_columns")
def mr_feat_columns(ctx, row):
    renames = {"feat": "name", "prerequisites": "prerequisites_text", "benefits": "summary", "links": "url"}
    for old, new in renames.items():
        if old in row:
            row[new] = row.pop(old)
    if not row.get("name"):
        ctx.note_dropped(row["_block"], row["_row"], "feat row with no name")
        return None
    row["name"] = fold(row["name"])
    return row


@row_hook("link_row")
def link_row(ctx, row):
    url = row.get("url")
    if not isinstance(url, str) or not url.strip().lower().startswith("http"):
        ctx.note_dropped(row["_block"], row["_row"], f"non-URL link row: {str(url)[:40]!r}")
        return None
    row["url"] = url.strip()
    row["name"] = re.sub(r"\s+", " ", url.rsplit("/", 1)[-1].replace("_", " ")).strip()
    return row


@row_hook("special_talent_context")
def special_talent_context(ctx, row):
    """Attach the owning class + choice axis to a repeatable special talent."""
    if not row.get("name") or fold(row["name"]).lower() == "talent":
        ctx.note_dropped(row["_block"], row["_row"], "repeated column header")
        return None
    row["special_talent_class"] = ctx.state.get("special_talent_class")
    row["choice_axis"] = ctx.state.get("choice_axis")
    row.pop("uses", None)
    return row


@row_hook("lightsaber_form_row")
def lightsaber_form_row(ctx, row):
    """Forms live in G, alternates in H; take whichever is populated."""
    name = row.get("name") or row.get("alternate")
    if not name:
        ctx.note_dropped(row["_block"], row["_row"], "empty lightsaber form row")
        return None
    row["form_slot"] = "primary" if row.get("name") else "alternate"
    row["name"] = fold(name)
    row.pop("alternate", None)
    return row


# ---------------------------------------------------------------------------
# Entity hooks (post-merge enrichment)
# ---------------------------------------------------------------------------
HEROIC_CLASSES = {"Jedi", "Noble", "Scoundrel", "Scout", "Soldier"}


@entity_hook("class_kind")
def class_kind(ctx, rec):
    """Classify a class as heroic / prestige / non-heroic / beast / droid."""
    a = rec["attrs"]
    name = rec["name"]
    kind = a.get("class_kind")
    if not kind:
        min_level = a.get("min_level")
        if isinstance(min_level, int) and min_level > 1:
            kind = "prestige"
        elif name in HEROIC_CLASSES or name in {"Technician", "Force Prodigy"}:
            kind = "heroic"
        elif name.lower() in {"nonheroic", "non-heroic"}:
            kind = "nonheroic"
        elif name.lower() in {"beast", "droid", "independent droid"}:
            kind = name.lower()
        else:
            kind = "unknown"
    a["class_kind"] = kind
    rec["flags"] = sorted(set(rec.get("flags", [])) | {f"class:{kind}"})
    if kind == "heroic" and name not in HEROIC_CLASSES:
        rec["flags"] = sorted(set(rec["flags"]) | {"homebrew"})
        rec["canon"] = "homebrew" if rec["canon"] == "official" else rec["canon"]
    # Prerequisites: the Master Reference gives one prose block; SagaForge gives
    # up to six separate columns. Keep the richest single rendering as the parse
    # target and preserve the other as `prerequisites_text_alt` so no source text
    # is lost (they occasionally disagree, e.g. "Force Sensitivity" vs
    # "Force Sensitive" - see data/curation/aliases.yaml).
    from .prereq import normalize
    mr_text = normalize(a.get("prerequisites_text") or "")
    sf_text = normalize("\n".join(
        normalize(a.get(f"prereq_{i}") or "") for i in range(1, 7))).strip()
    candidates = [t for t in (mr_text, sf_text) if t.strip()]
    if candidates:
        best = max(candidates, key=len)
        rec["_prereq_text"] = best
        others = [t for t in candidates if t != best]
        if others and norm_key(others[0]) != norm_key(best):
            a["prerequisites_text_alt"] = others[0]
    for i in range(1, 7):
        a.pop(f"prereq_{i}", None)
    a.pop("prerequisites_text", None)


@entity_hook("class_grants")
def class_grants(ctx, rec):
    """Parse the Master Reference free-text grant columns into structured lists."""
    a = rec["attrs"]
    if a.get("class_skills_text"):
        a["class_skills"] = _parse_class_skills(a["class_skills_text"])
    if a.get("starting_feats_text"):
        a["starting_feats"] = _clean_grant_list(a["starting_feats_text"])
    if a.get("talent_trees_text"):
        a["talent_trees"] = [fold(t) for t in split_list(a["talent_trees_text"], separators="\n") if fold(t)]
    if a.get("trained_skills_formula"):
        a["trained_skills_per_level"] = fold(a["trained_skills_formula"])


def _parse_class_skills(text: str) -> list[str]:
    """Split a class-skill cell into individual skill names.

    The source cells use newlines and/or commas, and contain parentheticals that
    must survive (``Knowledge (all; taken individually)``), so splitting is
    paren-aware and newline-preserving.
    """
    out: list[str] = []
    for part in split_list(text, separators=",\n;"):
        p = fold(part)
        if not p:
            continue
        if p.lower().startswith("knowledge (all"):
            out.append("Knowledge (all; taken individually)")
            continue
        if p.lower().startswith("use the force"):
            out.append("Use the Force")
            continue
        p = re.sub(r"\s*\(force sensitive\)\s*$", "", p, flags=re.I)
        out.append(p)
    seen, uniq = set(), []
    for o in out:
        k = norm_key(o)
        if k and k not in seen:
            seen.add(k)
            uniq.append(o)
    return uniq


def _clean_grant_list(text: str) -> list[str]:
    """Starting feats arrive as 'Linguist (must have ... Intelligence of 13), X, Y'."""
    items, buf, depth = [], "", 0
    for ch in fold(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            items.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf.strip())
    return [i for i in items if i]


@entity_hook("species_kind")
def species_kind(ctx, rec):
    a = rec["attrs"]
    name = rec["name"]
    low = name.lower()
    if "droid" in low or low.endswith("chassis"):
        kind = "droid_chassis"
    elif low in {"beast", "0"}:
        kind = "beast_template"
    elif "near-human" in low or "near human" in low:
        kind = "near_human"
    else:
        kind = "species"
    a["species_kind"] = kind
    rec["flags"] = sorted(set(rec.get("flags", [])) | {f"species:{kind}"})
    specials = [a.get(f"special_{i}") for i in range(1, 6)]
    a["specials"] = [fold(s) for s in specials if s]
    for i in range(1, 6):
        a.pop(f"special_{i}", None)
    nats = []
    for i, (nm, dmg, ty) in enumerate([( "natural_weapon_1","damage_1","type"),
                                       ("natural_weapon_2","damage_2","type_2"),
                                       ("natural_weapon_3","damage_3","type_3")], 1):
        if a.get(nm):
            nats.append({"name": fold(a.pop(nm)), "damage": a.pop(dmg, None), "type": a.pop(ty, None)})
        else:
            a.pop(nm, None); a.pop(dmg, None); a.pop(ty, None)
    if nats:
        a["natural_weapons"] = nats
    langs = [a.pop(k, None) for k in ("languages", "language_2", "language_3")]
    a["languages"] = [fold(x) for x in langs if x]


@entity_hook("talent_position")
def talent_position(ctx, rec):
    a = rec["attrs"]
    if a.get("tree"):
        rec.setdefault("relations", {})["talent_tree"] = None  # resolved by post hook
    a.pop("available_flag", None)
    a.pop("taken_flag", None)


@entity_hook("destiny_split")
def destiny_split(ctx, rec):
    """Destiny rows carry a type plus bonus/penalty text."""
    a = rec["attrs"]
    if a.get("type") and not a.get("destiny_type"):
        a["destiny_type"] = fold(a.pop("type"))
    for k in ("bonus", "penalty", "completed_effect"):
        if a.get(k):
            a[k] = fold(a[k])


@entity_hook("weapon_stats")
def weapon_stats(ctx, rec):
    """Normalise SagaForge's split damage columns into one structure.

    Three shapes occur in the source, and each is modelled explicitly rather
    than being forced into a single dice template:

    ``mult=2, die=6, add=1``  -> ``{"multiplier": 2, "die_size": 6, "bonus": 1}``  (2d6+1)
    ``mult=1, die=None``      -> ``{"flat": 1}``                                   (unarmed: 1 point)
    ``mult="special"``        -> ``{"special": "special"}``                        (targeting laser)

    A two-digit multiplier with no die ("28" on the Power lance, which the
    Rebellion Era Campaign Guide prints as 2d8) is almost certainly two numbers
    typed into one cell. It is *flagged and recorded as a gap*, never silently
    rewritten - deciding what it means belongs in the curation overlay.
    """
    a = rec["attrs"]
    dice = []
    for i in (1, 2):
        mult, die, add = a.pop(f"mult{i}", None), a.pop(f"die{i}", None), a.pop(f"add{i}", None)
        if die:
            dice.append({"multiplier": int(mult) if str(mult or "").isdigit() else 1,
                         "die_size": int(die), "bonus": add})
        elif mult is not None:
            text = fold(mult)
            if not text.isdigit():
                dice.append({"special": text, "bonus": add})
                continue
            entry: dict = {"flat": int(text), "bonus": add}
            if add is None and len(text) == 2 and text[0] in "1234" and text[1:] in {"4", "6", "8"}:
                entry["suspected_dice"] = f"{text[0]}d{text[1:]}"
                rec["flags"] = sorted(set(rec.get("flags") or []) | {"damage_suspected_concatenation"})
                ctx.note_gap("damage", f"{rec.get('name')}: damage column holds {text!r} with no die size; "
                                       f"suspected {entry['suspected_dice']} - confirm against the printed book")
                ctx.stat("damage_suspected_concatenation")
            dice.append(entry)
    if dice:
        a["damage"] = dice
    if a.get("group"):
        a["weapon_group"] = fold(a["group"]).lower()
        a.pop("group", None)
    if a.get("proficiency_feat"):
        a["proficiency"] = fold(a["proficiency_feat"])
        a.pop("proficiency_feat", None)
    for junk in ("statblock", "statblock_plural", "col_fq", "accurate", "retractablestock"):
        a.pop(junk, None)


# ---------------------------------------------------------------------------
# Post hooks (cross-entity)
# ---------------------------------------------------------------------------
def tree_key(name: str) -> str:
    """Match key for a talent tree: 'Awareness Talent Tree' == 'Awareness'."""
    return norm_key(re.sub(r"\s*talent trees?\s*$", "", fold(name).lower()).strip())


@post_hook("derive_talent_trees")
def derive_talent_trees(ctx):
    """Build/merge talent_tree records from SagaForge talent rows.

    The Master Reference gives tree -> availability; SagaForge gives
    tree -> owning class and the ordered talent list. Both land in one entity.
    """
    trees: dict[str, dict] = {}
    order: list[str] = []
    for rec in ctx.records.get("talent", []):
        a = rec["attrs"]
        tree = a.get("tree")
        if not tree:
            continue
        key = tree_key(tree)
        if key not in trees:
            trees[key] = {"name": fold(tree), "talents": [], "classes": [], "order": []}
            order.append(key)
        t = trees[key]
        t["talents"].append(rec["id"])
        t["order"].append({"id": rec["id"], "layout_column": a.get("layout_column"), "row": rec["sources"][0]["row"]})
        cg = a.get("class_group")
        if cg and cg not in t["classes"]:
            t["classes"].append(cg)
    existing = {tree_key(r["name"]): r for r in ctx.records.get("talent_tree", [])}
    for key in order:
        t = trees[key]
        if key in existing:
            rec = existing[key]
            rec["attrs"]["talents"] = t["talents"]
            rec["attrs"]["talent_order"] = t["order"]
            rec["attrs"]["classes_from_builder"] = t["classes"]
            rec["attrs"]["derived_from"] = sorted(set((rec["attrs"].get("derived_from") or []) + ["sf_talents"]))
            rec["attrs"]["aliases"] = sorted(set((rec["attrs"].get("aliases") or []) + [t["name"]]))
            rec["flags"] = sorted(set(rec["flags"]) | {"derived:from_talent_rows"})
        else:
            ctx.add_record("talent_tree", name=t["name"], attrs={
                "talents": t["talents"],
                "talent_order": t["order"],
                "classes_from_builder": t["classes"],
                "availability": t["classes"],
                "derived_from": ["sf_talents"],
            }, canon="third_party",
                sources=[{"source": "sagaforge-1.53", "block": "sf_talents", "sheet": "Talents",
                          "row": t["order"][0]["row"], "ref": f"Talents!D{t['order'][0]['row']}",
                          "canon": "third_party"}],
                flags=["derived:from_talent_rows"])


@post_hook("attach_urls")
def attach_urls(ctx):
    """Attach wiki URLs from the Master Reference Links sheet by name match."""
    links = ctx.records.get("reference_link", [])
    if not links:
        return
    by_name: dict[str, str] = {}
    for rec in links:
        url = rec["attrs"].get("url") or ""
        tail = url.rsplit("/", 1)[-1]
        for variant in (tail, tail.replace("_", " "), rec["name"]):
            k = norm_key(variant)
            if k:
                by_name.setdefault(k, url)
    hits = 0
    for entity, recs in ctx.records.items():
        if entity == "reference_link":
            continue
        for rec in recs:
            if rec["attrs"].get("url"):
                continue
            url = by_name.get(norm_key(rec["name"]))
            if url:
                rec["attrs"]["url"] = url
                rec["flags"] = sorted(set(rec.get("flags", [])) | {"url:matched_by_name"})
                hits += 1
    ctx.stat("urls_attached", hits)


@post_hook("skill_class_matrix")
def skill_class_matrix(ctx):
    """Add ``class_skills`` / ``starting_class`` info to skill records."""
    classes = [r for r in ctx.records.get("class", []) if r["attrs"].get("class_kind") == "heroic"]
    skills = {norm_key(r["name"]): r for r in ctx.records.get("skill", [])}
    for cls in classes:
        for s in cls["attrs"].get("class_skills", []):
            if s.lower().startswith("knowledge (all"):
                for k, rec in skills.items():
                    if k.startswith("knowledge"):
                        rec["attrs"].setdefault("class_skills_of", []).append(cls["name"])
                continue
            rec = skills.get(norm_key(s))
            if rec:
                rec["attrs"].setdefault("class_skills_of", []).append(cls["name"])
            else:
                ctx.note_gap("skill", f"class skill {s!r} (from {cls['name']}) is not in the skill list")


@post_hook("audit_class_grants")
def audit_class_grants(ctx):
    """Check every parsed class grant against the authoritative vocabulary.

    Class skills, starting feats and talent trees are free text in the Master
    Reference. Splitting them is lossy by nature, so each parsed item is checked
    against the canonical skill / feat / talent-tree records. Anything that does
    not resolve is kept in a ``*_unmatched`` attribute and counted, which turns a
    silent parse error into a visible, actionable gap.
    """
    skill_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("skill", [])}
    feat_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("feat", [])}
    tree_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("talent_tree", [])}
    for r in ctx.records.get("talent_tree", []):
        base = re.sub(r"\btalent tree\b", "", fold(r["name"]), flags=re.I).strip()
        if base:
            tree_vocab.setdefault(norm_key(base), base)

    def head_key(name: str) -> str:
        """Canonical head of a parameterised name, nesting-aware.

        ``"Skill Focus (Knowledge (Any), Mechanics)"`` -> ``"Skill Focus"``.
        A regex on ``[^)]*`` cannot span nested parentheses, so find the first
        "(" whose remainder is balanced and cut there.
        """
        t = fold(name)
        i = t.find("(")
        if i > 0 and t.count("(", i) == t.count(")", i):
            return norm_key(t[:i])
        return norm_key(t)

    for rec in ctx.records.get("class", []):
        a = rec["attrs"]
        for field, vocab, allow_wildcard in (("class_skills", skill_vocab, False),
                                             ("starting_feats", feat_vocab, True),
                                             ("talent_trees", tree_vocab, True)):
            items = a.get(field)
            if not items:
                continue
            clean, unmatched = [], []
            for item in items:
                text = fold(item)
                low = text.lower()
                if low.startswith("knowledge (all"):
                    clean.append("Knowledge (all; taken individually)")
                    continue
                if low.startswith("use the force"):
                    clean.append("Use the Force")
                    continue
                key = norm_key(text)
                exact = vocab.get(key)
                if exact:
                    clean.append(exact)
                    continue
                hit = vocab.get(head_key(text))
                if hit:
                    if "(" in text:
                        # the head is canonical ("Weapon Proficiency"); keep the
                        # parameter that was written next to it
                        clean.append(f"{hit} {text[text.index('('):]}")
                    else:
                        clean.append(hit)
                elif allow_wildcard and re.search(r"\ball\b", low):
                    clean.append(text)
                else:
                    unmatched.append(text)
            a[field] = dedupe(clean)
            if unmatched:
                a[f"{field}_unmatched"] = unmatched
                ctx.stat(f"{field}_unmatched", len(unmatched))
            ctx.stat(f"{field}_resolved", len(a[field]))


@post_hook("split_class_grants")
def split_class_grants(ctx):
    """Turn space-joined class grants into real lists of options.

    ``class.attrs.starting_feats`` and ``class.attrs.talent_trees`` arrive from
    the Master Reference as a single concatenated string. Re-segment them
    against the feat and talent-tree vocabularies so downstream code (the
    prerequisite graph, the decision space, the enumerator) can treat a starting
    feat as an actual feat. Wildcards such as "All Force Disciplines and Force
    Traditions" are preserved as a flag rather than being split.
    """
    from .ids import split_by_vocabulary

    feat_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("feat", [])}
    tree_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("talent_tree", [])}
    for r in ctx.records.get("talent_tree", []):
        base = re.sub(r"\btalent tree\b", "", fold(r["name"]), flags=re.I).strip()
        if base:
            tree_vocab.setdefault(norm_key(base), base)
    talent_vocab = {norm_key(r["name"]): r["name"] for r in ctx.records.get("talent", [])}

    stats = Counter()
    for rec in ctx.records.get("class", []):
        a = rec["attrs"]
        for field, vocab, out_field in (("starting_feats", feat_vocab, "starting_feats"),
                                        ("talent_trees", tree_vocab, "talent_trees")):
            raw = a.get(field)
            if not raw:
                continue
            joined = " ".join(x if isinstance(x, str) else str(x) for x in (raw if isinstance(raw, list) else [raw]))
            a[f"{field}_raw"] = joined
            parts = split_by_vocabulary(joined, vocab)
            matched = [p for p in parts if p["matched"]]
            unmatched = [p["name"] for p in parts if not p["matched"]]
            a[out_field] = [p["name"] for p in matched]
            params = {p["name"]: p["param"] for p in matched if p.get("param")}
            notes = {p["name"]: p["note"] for p in matched if p.get("note")}
            if params:
                a[f"{out_field}_params"] = params
            if notes:
                a[f"{out_field}_notes"] = notes
            if unmatched:
                text = " ".join(unmatched).lower()
                if re.search(r"\ball\b.*\b(force|talent|tree|discipline|tradition)", text):
                    a["grants_all_trees"] = True
                    stats["wildcard_grants"] += 1
                else:
                    a[f"{out_field}_unmatched"] = unmatched
                    stats[f"unmatched_{field}"] += len(unmatched)
            stats[f"split_{field}"] += len(matched)
    for k, v in sorted(stats.items()):
        ctx.stat(k, v)


@post_hook("derive_parameter_axes")
def derive_parameter_axes(ctx):
    """Record which feats are *parameterised*, and what their options are.

    The corpus stores ``Weapon Proficiency`` once, but taking it means choosing a
    weapon group - a real decision with real consequences. Same for Skill Focus
    (choose a skill), Weapon Focus (choose a group), Exotic Weapon Proficiency
    (choose an exotic weapon) and Linguist (choose languages). Making the axes
    explicit turns them into first-class dimensions of the decision space
    instead of hidden choices.
    """
    feats = {r["name"].lower(): r for r in ctx.records.get("feat", [])}

    groups = sorted({fold(r["attrs"].get("weapon_group")).lower()
                     for r in ctx.records.get("weapon", [])
                     if r["attrs"].get("weapon_group")
                     and fold(r["attrs"].get("weapon_group")).lower()
                     in {"simple", "pistols", "rifles", "heavy", "lightsabers", "advanced melee"}})
    exotic = sorted({fold(r["name"]).lower() for r in ctx.records.get("weapon", [])
                     if fold(r["attrs"].get("proficiency")).upper() == "EWP"})
    skills = sorted(fold(r["name"]) for r in ctx.records.get("skill", []))
    languages = sorted(fold(r["name"]) for r in ctx.records.get("language", []))
    armor_grades = ["light", "medium", "heavy"]

    axes = {
        "weapon proficiency": {"axis": "weapon_group", "options": groups,
                               "derived_from": "weapon.attrs.weapon_group where proficiency = WP"},
        "exotic weapon proficiency": {"axis": "exotic_weapon", "options": exotic,
                                      "derived_from": "weapon records whose proficiency code is EWP"},
        "weapon focus": {"axis": "weapon_group", "options": groups,
                         "derived_from": "weapon.attrs.weapon_group"},
        "skill focus": {"axis": "skill", "options": skills, "derived_from": "skill entity"},
        "linguist": {"axis": "language", "options": languages, "derived_from": "language entity"},
        "armor proficiency": {"axis": "armor_grade", "options": armor_grades,
                              "derived_from": "armor.attrs.type (L/M/H) - note: stored as separate feats"},
    }
    added = 0
    for name, spec in axes.items():
        rec = feats.get(name)
        if not rec or not spec["options"]:
            continue
        rec["attrs"]["parameter_axis"] = spec["axis"]
        rec["attrs"]["parameter_options"] = spec["options"]
        rec["attrs"]["parameter_options_count"] = len(spec["options"])
        rec["attrs"]["parameter_options_source"] = spec["derived_from"]
        rec["flags"] = sorted(set(rec["flags"]) | {"parameterised"})
        added += 1
    ctx.stat("parameterised_feats", added)


@post_hook("resolve_sourcebooks")
def resolve_sourcebooks(ctx):
    """Fill ``sourcebooks`` from page refs / source tags collected during ingest."""
    from .sourcebooks import by_id, parse_page_refs

    for entity, recs in ctx.records.items():
        for rec in recs:
            ids: list[str] = list(rec.pop("_sourcebook_ids", []) or [])
            unresolved: list[str] = list(rec.pop("_sourcebook_unresolved", []) or [])
            pages: dict[str, int] = {}
            page_ref = rec["attrs"].get("page_ref")
            for pr in parse_page_refs(page_ref) if page_ref else []:
                if pr.get("sourcebook"):
                    if pr["sourcebook"] not in ids:
                        ids.append(pr["sourcebook"])
                    if pr.get("page") is not None:
                        pages[pr["sourcebook"]] = pr["page"]
                elif pr.get("raw"):
                    unresolved.append(pr["raw"])
            out = []
            for sid in ids:
                sb = by_id(sid)
                if sb:
                    out.append({"id": sb.id, "abbreviation": sb.abbreviation, "title": sb.title,
                                "page": pages.get(sid)})
            if out:
                rec["sourcebooks"] = out
                rec["canon"], basis = _best_canon(rec, out)
                rec["attrs"]["canon_basis"] = basis
                rec["attrs"]["canon_cited_sourcebooks"] = sorted({s["abbreviation"] for s in out})
            if len(pages) == 1:
                rec["attrs"]["page"] = next(iter(pages.values()))
            elif pages:
                rec["attrs"]["pages"] = {k: v for k, v in sorted(pages.items())}
            rec["attrs"].pop("page_ref", None) if not page_ref else None
            if unresolved:
                rec["attrs"]["unresolved_source_tags"] = sorted(set(unresolved))
                ctx.stat("unresolved_source_tags", len(set(unresolved)))


def _best_canon(rec, sourcebooks) -> tuple[str, str]:
    """Decide *content* canonicity, and say why.

    SagaForge is a third-party builder, but almost everything in it is official
    WotC rules text transcribed into a spreadsheet. Tagging those records
    ``third_party`` would mislabel the corpus, so the rule is:

    * a record flagged ``homebrew`` by its block (the Master Reference's
      Homebrew section: Technician, Force Prodigy) stays ``homebrew``;
    * a record citing at least one published sourcebook is ``official`` - the
      citation, not the carrier file, decides;
    * a record citing only a webpage/unknown tag is ``third_party``;
    * anything else keeps the canon its extraction block declared.

    The second return value is the basis, stored as ``attrs.canon_basis`` so the
    decision is auditable per record.
    """
    if "homebrew" in rec.get("flags", []):
        return "homebrew", "homebrew_section"
    cited = {s["id"] for s in sourcebooks}
    published = cited - {"tao", "unknown", "web"}
    if published:
        return "official", "sourcebook_citation"
    if cited:
        return "third_party", "webpage_only_citation"
    return rec.get("canon", "third_party"), "block_declaration"


@post_hook("prereq_pass")
def prereq_pass(ctx):
    """Parse every collected prerequisite string once the entity index exists."""
    ctx.build_index()
    for entity, recs in ctx.records.items():
        for rec in recs:
            text = rec.pop("_prereq_text", None) or rec["attrs"].get("prerequisites_text")
            if not text:
                continue
            parsed = ctx.parse_prereq(text)
            rec["prerequisites"] = parsed
            rec["attrs"].pop("prerequisites_text", None)
            if parsed["unresolved"]:
                ctx.stat("prereq_fragments_unresolved", len(parsed["unresolved"]))
                ctx.note_gap("prereq", f"{entity}:{rec['id']} unresolved {parsed['unresolved']}")
