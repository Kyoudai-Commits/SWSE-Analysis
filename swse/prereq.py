"""Prerequisite parsing: free text -> structured, machine-checkable predicates.

Prerequisites are the constraint system of the whole character-creation space.
They arrive as prose::

    "BAB +6"
    "Strength 13, Power Attack"
    "Minimum Level: 7th\nTrained Skills: Pilot\nFeats: Vehicular Combat"
    "Talents: Any one from the Fortune Talent Tree, Lineage Talent Tree, or
              Misfortune Talent Tree"

and must become something :mod:`swse.graph` and :mod:`swse.enumerate` can
evaluate.

Two phases
----------
``parse(text)``
    Structural parsing. Recognises numbered gates (ability scores, BAB, level),
    labelled sections, proficiency requirements and "any N from ..." talent
    rules. Anything it cannot classify becomes ``{"type": "other"}`` - it is
    *never* dropped.

``resolve(parsed, index)``
    Entity-aware typing. A bare name fragment ("Power Attack", "Rage", "Droid")
    is ambiguous by construction; :func:`resolve` looks it up in the canonical
    entity index and re-types it as a feat / talent / force power / species /
    class requirement. What still cannot be resolved stays ``other`` and is
    reported by ``python -m swse.cli prereq-coverage``.

Rules of the road
-----------------
1. The raw string is always preserved (``prerequisites.raw``).
2. Parsing never raises and never loses text.
3. Every predicate carries ``rule`` - the id of the rule that produced it - so a
   wrong parse can be traced to a line in this file.
4. Extend by adding to :data:`RULES` (first match wins) plus a case in
   ``tests/test_prereq.py``. Never special-case in a caller.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .ids import fold, fold_multiline, norm_key, slugify

ABILITIES = {
    "str": "STR", "strength": "STR",
    "dex": "DEX", "dexterity": "DEX",
    "con": "CON", "constitution": "CON",
    "int": "INT", "intelligence": "INT",
    "wis": "WIS", "wisdom": "WIS",
    "cha": "CHA", "charisma": "CHA",
}

_WORD_NUMS = {"a": 1, "an": 1, "any": 1, "one": 1, "two": 2, "three": 3,
              "four": 4, "five": 5, "six": 6, "seven": 7}

WEAPON_GROUPS = ("simple", "pistols", "rifles", "heavy weapons", "heavy",
                 "lightsabers", "advanced melee", "explosives", "vehicle weapons")


def word_num(text: str | None, default: int = 1) -> int:
    if text is None:
        return default
    t = text.strip().lower()
    if t.isdigit():
        return int(t)
    return _WORD_NUMS.get(t, default)


def normalize(text: object) -> str:
    """Fold unicode/whitespace but KEEP newlines - they delimit sections."""
    s = fold_multiline(text)
    return s.replace("Armour", "Armor").replace("armour", "armor").replace("Sytem", "System")


def _any_count(text: str) -> tuple[int, str] | None:
    """If ``text`` is an "any N ..." rule, return (N, remainder)."""
    m = re.match(r"^any\s+(?P<n>one|two|three|four|five|six|seven|\d+)\b\s*(?P<rest>.*)$", fold(text), re.I)
    if not m:
        return None
    return word_num(m.group("n")), m.group("rest").strip()


def skill_name(text: str) -> str:
    t = fold(text)
    t = re.sub(r"\s+skill$", "", t, flags=re.I)
    t = re.sub(r"^(?:be\s+)?trained in\s+", "", t, flags=re.I)
    m = re.match(r"^knowledge\s*\(([^)]*)\)$", t, re.I)
    if m:
        inner = m.group(1).strip().lower()
        if inner in {"", "any", "all", "all skills", "all; taken individually",
                     "all skills, taken individually", "any one", "any skill"}:
            return "Knowledge"          # "pick any Knowledge skill"
        return f"Knowledge ({m.group(1).strip().title()})"
    if t.lower().startswith("knowledge"):
        inner = t[t.find("(") + 1:t.rfind(")")].strip().lower() if "(" in t else ""
        if inner in {"", "any", "all", "all; taken individually", "all skills", "all skills, taken individually"}:
            return "Knowledge"
        return t
    return t if not t.islower() else t.title()


def split_names(text: str) -> tuple[list[str], str]:
    """Split a name list on ',', ';', 'and', 'or'. Returns ``(names, mode)``.

    Parenthesis-aware: ``"Armor Proficiency (Light, Medium)"`` is one option with
    a two-part parameter, not an option called "Armor Proficiency (Light" plus
    one called "Medium)".
    """
    mode = "any" if re.search(r"\bor\b", text, re.I) else "all"
    parts: list[str] = []
    buf = ""
    depth = 0
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and ch in ",;":
            parts.append(buf)
            buf = ""
            i += 1
            continue
        if depth == 0 and ch == " " and (text[i:i + 5].lower() == " and " or text[i:i + 4].lower() == " or "):
            word = " and " if text[i:i + 5].lower() == " and " else " or "
            parts.append(buf)
            buf = ""
            i += len(word)
            continue
        buf += ch
        i += 1
    parts.append(buf)
    return [p.strip(" .") for p in parts if p.strip(" .")], mode


# ---------------------------------------------------------------------------
# Rules. (id, compiled regex, builder) - matched against the folded fragment.
# ---------------------------------------------------------------------------
def _ability(m):
    return {"type": "ability_min", "ability": ABILITIES[m.group("ab").lower()], "min": int(m.group("n"))}


def _bab(m):
    return {"type": "bab_min", "min": int(m.group("n"))}


def _level(m):
    return {"type": "level_min", "min": int(m.group("n"))}


def _trained(m):
    """``Trained in X`` - X may be a list ("Pilot or Ride", "Mechanics and Use Computer")."""
    raw = m.group("skill")
    names, mode = split_names(raw)
    names = [skill_name(n) for n in names]
    if len(names) == 1:
        return {"type": "trained_skill", "skill": names[0], "skills": names, "mode": "all"}
    return {"type": "trained_skill", "skill": None, "skills": names, "mode": mode}


def _trained_label(m):
    names, mode = split_names(m.group("rest"))
    names = [skill_name(n) for n in names]
    return {"type": "trained_skill", "skills": names,
            "skill": names[0] if len(names) == 1 else None, "mode": mode}


def _armor_prof(m):
    return {"type": "armor_proficiency", "grade": fold(m.group("g")).title()}


def _weapon_prof(m):
    g = fold(m.group("g")).lower()
    return {"type": "weapon_proficiency", "group": g, "any": g in {"", "any", "used", "weapon used", "weapon"}}


def _proficient_with(m):
    g = fold(m.group("g")).lower().strip()
    if g in {"weapon", "weapon used", "the weapon", "the weapon used", "all weapons", ""}:
        return {"type": "weapon_proficiency", "group": None, "any": True}
    if g.startswith("all "):
        g = g[4:]
    known = next((w for w in WEAPON_GROUPS if g.startswith(w)), None)
    return {"type": "weapon_proficiency", "group": known or g, "any": known is None}


def _labelled_names(kind):
    def build(m):
        rest = m.group("rest")
        any_n = _any_count(rest)
        if any_n:
            count, remainder = any_n
            pred = {"type": kind, "count": count, "mode": "any"}
            if remainder:
                pred.update(_classify_remainder(kind, remainder))
            return pred
        # "Any Martial Arts Feat" - a category rule with no number attached
        m_any = re.match(r"^any\b\s*(?P<rest>.*)$", fold(rest), re.I)
        if m_any:
            remainder = m_any.group("rest").strip()
            pred = {"type": kind, "count": 1, "mode": "any", "category": remainder}
            pred.update(_classify_remainder(kind, remainder))
            return pred
        # The label may wrap a structured rule instead of a list of names, e.g.
        # "Feats: Weapon Focus with any melee weapon". Only *relational* rules
        # qualify: "Feats: Force Sensitivity" is a feat name that happens to
        # match the force_sensitive state rule, and must stay a feat reference.
        inner = classify_no_labels(rest)
        if inner.get("rule") in LABEL_INNER_RULES:
            inner["label"] = kind
            return inner
        names, mode = split_names(rest)
        # Mixed lists are common: "Feats: Martial Arts II, Melee Defense, any
        # Martial Arts Feat". Classify each item; structured items are lifted out
        # by `parse` into requirements of their own.
        plain, items = [], []
        for item in names:
            sub = classify_no_labels(item)
            if sub.get("rule") in LABEL_INNER_RULES:
                sub["label"] = kind
                items.append(sub)
                continue
            m_item = re.match(r"^any\b\s*(?P<rest>.*)$", fold(item), re.I)
            if m_item:
                remainder = m_item.group("rest").strip()
                cat = {"type": kind, "count": 1, "mode": "any", "category": remainder,
                       "text": fold(item), "rule": "any_category_item"}
                cat.update(_classify_remainder(kind, remainder))
                items.append(cat)
                continue
            plain.append(item)
        pred = {"type": kind, "names": plain, "mode": mode}
        if items:
            pred["items"] = items
        return pred
    return build


#: Rules that may be recognised *inside* a labelled list. These describe a
#: relation ("Weapon Focus with any melee weapon", "Armor Proficiency (Light)")
#: rather than a character state, so lifting them out of a "Feats:" list is
#: correct. State rules such as ``force_sensitive`` or ``creature_type`` are
#: deliberately excluded: "Feats: Force Sensitivity" names a feat.
LABEL_INNER_RULES = {
    "armor_proficiency", "armor_proficiency_multi", "armor_proficiency_any",
    "weapon_proficiency", "weapon_proficiency_bare", "weapon_focus_with",
    "proficient_with", "requires_item", "droid_with", "any_category",
}


def classify_no_labels(fragment: str) -> dict:
    """:func:`classify` with the ``Label: ...`` rules disabled.

    Used from inside a label rule so that "Feats: Weapon Focus with any melee
    weapon" is recognised as a Weapon Focus rule rather than being treated as a
    feat named "Weapon Focus with any melee weapon".
    """
    f = fold(fragment).strip(" .")
    low = f.lower()
    for rule_id, pattern, builder in RULES:
        if rule_id.endswith("_label"):
            continue
        m = pattern.match(low)
        if m:
            pred = builder(m)
            pred.setdefault("text", f)
            pred["rule"] = rule_id
            return pred
    return {"type": "other", "text": f, "rule": None}


def _classify_remainder(kind: str, remainder: str) -> dict:
    """Interpret the tail of an 'any N <tail>' rule."""
    r = fold(remainder)
    low = r.lower()
    m = re.match(r"^(?:talents?\s+)?(?:from\s+)?(?:the\s+)?(?P<trees>.+)$", r, re.I)
    if kind in {"talent"} and m:
        tail = m.group("trees")
        names, _ = split_names(tail)
        trees = []
        for n in names:
            n = re.sub(r"\btalent trees?\b", "", n, flags=re.I).strip(" .,")
            if n:
                trees.append(fold(n).title())
        if trees and not low.startswith("force talent"):
            return {"trees": trees}
        if "force talent" in low:
            return {"force_only": True}
    if kind == "force_technique" or "technique" in low:
        return {"of": "force_technique"}
    if "force power" in low:
        return {"of": "force_power"}
    if "force secret" in low or "secret" in low:
        return {"of": "force_secret"}
    if m and m.group("trees"):
        return {"names": [x.strip() for x in split_names(m.group("trees"))[0]]}
    return {}


def _talent_any_from(m):
    tail = m.group("trees")
    names, _ = split_names(tail)
    trees = []
    for n in names:
        n = re.sub(r"\btalent trees?\b", "", n, flags=re.I).strip(" .,")
        if n:
            trees.append(fold(n).title())
    return {"type": "talent", "trees": trees, "count": word_num(m.group("n")), "mode": "any"}


def _any_n(kind, **extra):
    def build(m):
        d = {"type": kind, "count": word_num(m.group("n")), "mode": "any"}
        d.update(extra)
        return d
    return build


RULES: list[tuple[str, re.Pattern, Any]] = [
    ("ability_min", re.compile(r"^(?P<ab>str|dex|con|int|wis|cha|strength|dexterity|constitution|intelligence|wisdom|charisma)\s*(?:score)?\s*(?:of\s*)?(?P<n>\d{1,2})\s*\+?(?:\s+or\s+higher)?$"), _ability),
    ("bab", re.compile(r"^(?:minimum\s+)?(?:bab|base attack bonus)\s*[:=+]?\s*\+?(?P<n>\d{1,2})$"), _bab),
    ("level_min", re.compile(r"^(?:minimum\s+)?(?:character\s+)?level\s*[:=]?\s*(?P<n>\d{1,2})\s*(?:st|nd|rd|th)?(?:\s+level)?$"), _level),
    ("level_min_ordinal", re.compile(r"^(?P<n>\d{1,2})\s*(?:st|nd|rd|th)\s+level$"), _level),
    ("talent_any_from", re.compile(r"^(?:talents?\s*[:=]\s*)?any\s+(?P<n>one|two|three|four|five|six|seven|\d+)\b.*?\bfrom\s+(?:the\s+)?(?P<trees>.+)$"), _talent_any_from),
    ("talent_any_n", re.compile(r"^(?:talents?\s*[:=]\s*)?any\s+(?P<n>one|two|three|four|five|six|seven|\d+)\s+talents?$"), _any_n("talent")),
    ("force_talent_any_n", re.compile(r"^(?:talents?\s*[:=]\s*)?any\s+(?P<n>one|two|three|four|five|six|seven|\d+)\s+force\s+talents?$"), _any_n("talent", force_only=True)),
    ("trained_skill", re.compile(r"^(?:must be\s+)?trained in\s+(?P<skill>.+)$"), _trained),
    ("trained_skill_label", re.compile(r"^trained skills?\s*[:=]\s*(?P<rest>.+)$"), _trained_label),
    ("armor_proficiency", re.compile(r"^armor proficiency\s*\((?P<g>light|medium|heavy)\)$"), _armor_prof),
    ("armor_proficiency_multi", re.compile(r"^armor\s+proficiency\s*\((?P<g>light|medium|heavy)(?:\s*,\s*(?:light|medium|heavy))+\)$"), lambda m: {"type": "armor_proficiency", "grades": [x.strip().title() for x in m.group("g").split(",")], "text": m.group(0)}),
    ("armor_proficiency_any", re.compile(r"^armor proficiency$"), lambda m: {"type": "armor_proficiency", "grade": None, "any": True}),
    ("weapon_focus_with", re.compile(r"^weapon focus with (?P<g>any\s+)?(?P<group>.+?)(?:\s+weapons?)?$"), lambda m: {"type": "weapon_focus", "group": None if m.group("g") else fold(m.group("group")).lower(), "any": bool(m.group("g"))}),
    ("special_label", re.compile(r"^special\s*[:=]\s*(?P<rest>.+)$"), lambda m: {"type": "special", "detail": fold(m.group("rest")), **(_shallow(classify(m.group("rest"))) or {})}),
    ("system_label", re.compile(r"^(?:system|sytem)s?\s*[:=]\s*(?P<rest>.+)$"), lambda m: {"type": "requires_item", "name": fold(m.group("rest")), "context": "droid"}),
    ("size_word", re.compile(r"^(?P<size>fine|diminutive|tiny|small|medium|large|huge|gargantuan|colossal)$"), lambda m: {"type": "size_min", "size": fold(m.group("size")).title(), "direction": "exact"}),
    ("weapon_proficiency", re.compile(r"^weapon proficiency\s*\((?P<g>[a-z ,]+)\)$"), _weapon_prof),
    ("weapon_proficiency_bare", re.compile(r"^weapon proficiency$"), _weapon_prof),
    ("proficient_with", re.compile(r"^(?:must be\s+)?proficient with\s+(?P<g>.+)$"), _proficient_with),
    ("proficiency", re.compile(r"^(?:must have\s+)?proficiency(?:\s+with\s+(?P<g>.+))?$"), _proficient_with),
    ("force_sensitive", re.compile(r"^force\s+sensitiv(?:e|ity)$"), lambda m: {"type": "force_sensitive"}),
    ("feats_label", re.compile(r"^feats?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("feat")),
    ("talents_label", re.compile(r"^talents?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("talent")),
    ("force_powers_label", re.compile(r"^force powers?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("force_power")),
    ("force_techniques_label", re.compile(r"^force techniques?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("force_technique")),
    ("force_secrets_label", re.compile(r"^force secrets?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("force_secret")),
    ("species_label", re.compile(r"^species\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("species")),
    ("class_label", re.compile(r"^(?:heroic\s+)?(?:prestige\s+)?classes?\s*[:=]\s*(?P<rest>.+)$"), _labelled_names("class")),
    ("dark_side_score", re.compile(r"^dark side (?:score|points?)\s*(?:[:=]?\s*(?P<n>\d+)\s*\+?)?$"), lambda m: {"type": "dark_side_score", "min": int(m.group("n") or 1)}),
    ("creature_type", re.compile(r"^(?:must be a\s+)?(?P<value>droid|non-droid|nondroid|beast|cyborg hybrid|cyborg)(?:\s+only)?$"), lambda m: {"type": "creature_type", "value": fold(m.group("value")).lower()}),
    ("size_min", re.compile(r"^(?P<size>fine|diminutive|tiny|small|medium|large|huge|gargantuan|colossal)\s+or\s+(?:larger|smaller)\s+sized?$"), lambda m: {"type": "size_min", "size": fold(m.group("size")).title(), "direction": "larger" if "larger" in m.group(0) else "smaller"}),
    ("affiliation", re.compile(r"^(?:must be a\s+)?member of\s+(?P<org>.+)$"), lambda m: {"type": "affiliation", "name": fold(m.group("org"))}),
    ("requires_item", re.compile(r"^(?:possess|must possess|have|must have)\s+(?:an?|the)\s+(?P<item>.+)$"), lambda m: {"type": "requires_item", "name": fold(m.group("item"))}),
    ("dark_side_equals", re.compile(r"^dark side score must equal (?P<ab>wisdom|charisma|intelligence|strength|dexterity|constitution) score$"), lambda m: {"type": "dark_side_equals_ability", "ability": ABILITIES[m.group("ab").lower()]}),
    ("any_category", re.compile(r"^any\s+(?P<cat>[a-z\- ]+?)\s+(?P<kind>feat|talent|power|skill)s?$"), lambda m: {"type": "any_of_category", "category": fold(m.group("cat")), "kind": fold(m.group("kind")), "count": 1, "mode": "any"}),
    ("droid_with", re.compile(r"^droid with (?P<part>.+)$"), lambda m: {"type": "requires_item", "name": fold(m.group("part")), "context": "droid"}),
    ("droid_only", re.compile(r"^(?:must be a\s+)?droid$"), lambda m: {"type": "creature_type", "value": "droid"}),
    ("nonheroic_ban", re.compile(r"^cannot be a nonheroic character$"), lambda m: {"type": "not_nonheroic"}),
]


def _shallow(pred: dict | None) -> dict | None:
    """Flatten a nested classification into extra keys (no recursion loops)."""
    if not pred or pred.get("type") == "other":
        return None
    return {"nested": pred}


#: A line that begins "Label:" carries its own list of names; the label rule
#: splits them, so :func:`split_fragments` must not.
_LABELLED_LINE = re.compile(
    r"^\s*(?:minimum\s+)?(?:trained\s+skills?|skills?|feats?|talents?|force\s+powers?|"
    r"force\s+techniques?|force\s+secrets?|force\s+regimens?|force\s+traditions?|species|"
    r"talent\s+trees?|droid\s+systems?|equipment|items?|weapons?|armor)\s*[:=]", re.I)


def split_fragments(text: str) -> list[str]:
    """Split prerequisite text into independently classifiable fragments.

    Splitting happens on newlines and semicolons always, and on commas only where
    the comma genuinely separates two requirements. Two exceptions matter:

    * ``"any N ... from the X, Y, or Z"`` - the commas belong to the rule and must
      survive to :func:`_talent_any_from`;
    * ``"Trained Skills: Deception, Stealth"`` - a labelled list; the commas are
      the label's own separators, so the whole line goes to the label rule. A
      comma *is* still a separator when what follows it is another label
      (``"Trained Skills: Use the Force, Feats: Force Sensitivity"``).
    """
    out: list[str] = []
    for line in re.split(r"[\n;]+", text):
        line = line.strip()
        if not line:
            continue
        if re.search(r"\bany\b.*\bfrom\b", line, re.I):
            out.append(line)
            continue
        # Inside a labelled list the commas belong to the label's own rule; in an
        # unlabelled list ("Base Attack Bonus +4, Point-Blank Shot") they separate
        # requirements and must split.
        labelled = bool(_LABELLED_LINE.match(line))
        depth, buf = 0, ""
        for i, ch in enumerate(line):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                rest = line[i + 1:].lstrip()
                if not labelled or _LABELLED_LINE.match(rest):
                    if buf.strip():
                        out.append(buf.strip())
                    buf = ""
                else:
                    buf += ch
                continue
            buf += ch
        if buf.strip():
            out.append(buf.strip())
    return out


def classify(fragment: str) -> dict:
    """Classify one fragment. Always returns a dict (type ``other`` if unknown)."""
    f = fold(fragment).strip(" .")
    if not f:
        return {"type": "other", "text": f, "rule": None}
    low = f.lower()

    # 1. try the whole fragment (keeps parentheticals: "Armor Proficiency (Light)")
    for rule_id, pattern, builder in RULES:
        m = pattern.match(low)
        if m:
            pred = builder(m)
            pred.setdefault("text", f)
            pred["rule"] = rule_id
            return pred

    # 2. a "Name (clarification)" form: classify head and remember the note
    m = re.match(r"^(?P<head>[^()]+?)\s*\((?P<note>[^()]+)\)\s*$", f)
    if m:
        head_low = m.group("head").strip().lower()
        for rule_id, pattern, builder in RULES:
            mm = pattern.match(head_low)
            if mm:
                pred = builder(mm)
                pred["text"] = f
                pred["note"] = m.group("note")
                pred["rule"] = rule_id
                nested = classify(m.group("note"))
                if nested["type"] != "other":
                    pred["nested"] = nested
                return pred

    return {"type": "other", "text": f, "rule": None}


EMPTY_TOKENS = {"", "none", "n/a", "na", "-", "--", "no", "no special"}


def _expand_alternatives(pred: dict) -> dict:
    """``{"type": "other", "text": "Sneak Attack or Rapid Shot"}`` -> an any_of group.

    Splitting on ``or`` happens *after* structural rules, so phrases like
    "Medium or larger sized" (which a rule already matched) are never broken up.
    """
    if pred.get("type") != "other":
        return pred
    text = pred.get("text", "")
    if not re.search(r"\bor\b", text, re.I) or re.search(r"\bfrom\b", text, re.I):
        return pred
    parts = [x.strip(" ,") for x in re.split(r"\bor\b", text, flags=re.I) if x.strip(" ,")]
    if len(parts) < 2:
        return pred
    options = [classify(x) for x in parts]
    return {
        "type": "any_of", "mode": "any", "count": 1, "options": options,
        "text": text, "rule": "alternatives",
    }


def walk(pred: dict):
    """Yield a predicate and every nested sub-predicate."""
    yield pred
    for key in ("options", "nested", "of"):
        sub = pred.get(key)
        if isinstance(sub, dict):
            yield from walk(sub)
        elif isinstance(sub, list):
            for item in sub:
                if isinstance(item, dict):
                    yield from walk(item)


def parse(text: object) -> dict:
    """Phase 1: structural parse of a prerequisite string."""
    raw = normalize(text)
    if raw.lower() in EMPTY_TOKENS:
        return {"raw": raw, "predicates": [], "unresolved": [], "mode": "all",
                "coverage": 1.0, "empty": True, "resolved": False}

    frags = split_fragments(raw)
    preds = [classify(f) for f in frags if f.strip()]
    # A labelled list can mix plain names with structured rules
    # ("Feats: Martial Arts II, any Martial Arts Feat"). Lift the structured
    # items out into requirements of their own so every walker sees a flat list.
    lifted: list[dict] = []
    for p in preds:
        items = p.pop("items", None)
        if p.get("names") or not items:
            lifted.append(p)
        if items:
            lifted.extend(items)
    preds = [_expand_alternatives(p) for p in lifted]
    parsed = {
        "raw": raw,
        "predicates": preds,
        "unresolved": [],
        "mode": "all",
        "coverage": 1.0,
        "empty": False,
        "resolved": False,
    }
    parsed["unresolved"] = [p["text"] for p in _all_predicates(parsed) if p["type"] == "other"]
    parsed["coverage"] = _coverage(parsed)
    return parsed


def _all_predicates(parsed: dict) -> list[dict]:
    out: list[dict] = []
    for pred in parsed.get("predicates", []):
        out.extend(walk(pred))
    return out


def _coverage(parsed: dict) -> float:
    preds = [p for p in _all_predicates(parsed) if p.get("type") not in {"any_of"}]
    if not preds:
        return 1.0
    bad = sum(1 for p in preds if p["type"] == "other")
    return round((len(preds) - bad) / len(preds), 4)


# ---------------------------------------------------------------------------
# Phase 2: entity-aware resolution
# ---------------------------------------------------------------------------
class EntityIndex:
    """Lookup of norm_key -> entity id, per entity type."""

    TYPES = ("feat", "talent", "talent_tree", "skill", "class", "species",
             "force_power", "force_technique", "force_secret", "racial_ability",
             "special_talent", "lightsaber_form", "force_regimen", "starship_maneuver",
             "droid_option", "droid_locomotion", "cybernetic", "equipment",
             "weapon", "armor", "background", "destiny", "language",
             "near_human_trait", "unleashed_ability")

    def __init__(self, mapping: dict[str, dict[str, str]] | None = None):
        self.map: dict[str, dict[str, str]] = {t: {} for t in self.TYPES}
        for t, d in (mapping or {}).items():
            self.map.setdefault(t, {}).update(d)

    def add(self, entity_type: str, name: str, entity_id: str) -> None:
        k = norm_key(name)
        if k:
            self.map.setdefault(entity_type, {}).setdefault(k, entity_id)

    def find(self, name: str, types: Iterable[str] = ()) -> tuple[str, str] | None:
        k = norm_key(name)
        for t in types or self.TYPES:
            hit = self.map.get(t, {}).get(k)
            if hit:
                return t, hit
        return None

    @property
    def empty(self) -> bool:
        return not any(self.map.values())


#: entity types a bare name fragment may resolve to, most specific first.
_BARE_ORDER = ("feat", "talent", "special_talent", "force_power", "force_technique",
               "force_secret", "talent_tree", "skill", "class", "species",
               "racial_ability", "force_regimen", "lightsaber_form",
               "starship_maneuver", "unleashed_ability", "droid_option",
               "droid_locomotion", "cybernetic", "near_human_trait", "background",
               "destiny", "language", "armor", "weapon", "equipment")


def resolve_name(index: EntityIndex, name: str) -> dict:
    """Resolve one option name to ``(entity_type, id, clean_name, param)``.

    Handles parameterised options: the corpus stores ``Skill Focus`` once, and
    ``Skill Focus (Stealth)`` is that feat plus a parameter choice.
    """
    text = fold(name)
    direct = index.find(text, _BARE_ORDER)
    if direct:
        return {"entity_type": direct[0], "id": direct[1], "name": text, "param": None}
    m = re.match(r"^(?P<head>[^()]+?)\s*\((?P<param>.+)\)\s*$", text)
    if m:
        head = fold(m.group("head"))
        hit = index.find(head, _BARE_ORDER)
        if hit:
            return {"entity_type": hit[0], "id": hit[1], "name": head, "param": fold(m.group("param"))}
    return {"entity_type": None, "id": None, "name": text, "param": None}


def resolve_name_multi(index: EntityIndex, name: str) -> list[dict]:
    """Resolve a name that may grant *several* parameterised options at once.

    ``Armor Proficiency (light, medium)`` means both ``Armor Proficiency (Light)``
    and ``Armor Proficiency (Medium)``, which are two separate records. Without
    this the requirement resolves to the generic head feat and the two real
    records are never linked.
    """
    one = resolve_name(index, name)
    param = one.get("param")
    if param and re.search(r",|\band\b|\bor\b", param, re.I):
        head = one.get("name") or fold(name).split("(")[0].strip()
        parts, _mode = split_names(param)
        if len(parts) > 1:
            out = []
            for part in parts:
                cand = resolve_name(index, f"{head} ({fold(part)})")
                cand["param"] = fold(part)
                cand["expanded_from"] = fold(name)
                out.append(cand)
            if any(c["id"] for c in out):
                return out
    return [one]


def resolve(parsed: dict, index: EntityIndex) -> dict:
    """Phase 2: re-type ``other`` fragments (and ``names`` lists) using the index.

    Mutates and returns ``parsed``. Idempotent.
    """
    if parsed.get("resolved"):
        return parsed
    for pred in _all_predicates(parsed):
        # labelled lists ("Feats: X, Y") - attach ids where known
        if pred.get("names"):
            refs = [r for n in pred["names"] for r in resolve_name_multi(index, n)]
            pred["refs"] = refs
            if all(r["id"] for r in refs):
                pred["resolved_refs"] = True
        if pred["type"] != "other":
            continue
        text = pred.get("text", "")
        # "Any two X" leftovers
        m = re.match(r"^any\s+(one|two|three|four|five|six|seven|\d+)\b\s*(.*)$", text, re.I)
        if m:
            pred["type"] = "any_of"
            pred["count"] = word_num(m.group(1))
            pred["mode"] = "any"
            rest = m.group(2).strip()
            if rest:
                pred["of"] = classify(rest)
            continue
        resolved = resolve_name(index, text)
        if resolved["id"]:
            pred["type"] = resolved["entity_type"]
            pred["id"] = resolved["id"]
            pred["name"] = resolved["name"]
            if resolved["param"]:
                pred["param"] = resolved["param"]
            pred["rule"] = "index_lookup_parameterised" if resolved["param"] else "index_lookup"
        else:
            # an unresolved bare name is *probably* a feat/talent; keep the text
            pred["rule"] = None
            pred["candidate_type"] = "feat_or_talent" if re.match(r"^[A-Z]", text) else None
    parsed["unresolved"] = [p["text"] for p in _all_predicates(parsed) if p["type"] == "other"]
    parsed["coverage"] = _coverage(parsed)
    total = len(parsed.get("predicates")) or 1
    parsed["coverage"] = round((total - len(parsed["unresolved"])) / total, 4)
    parsed["resolved"] = True
    return parsed


def parse_and_resolve(text: object, index: EntityIndex) -> dict:
    return resolve(parse(text), index)


# ---------------------------------------------------------------------------
# Predicate -> graph edges / build-time gates
# ---------------------------------------------------------------------------
NUMERIC_GATES = {"ability_min", "bab_min", "level_min", "dark_side_score"}


def requirement_refs(pred: dict) -> list[tuple[str, str]]:
    """``(entity_type, id)`` pairs a predicate demands (edges in the prereq graph)."""
    out: list[tuple[str, str]] = []
    for sub in walk(pred):
        out.extend(_refs_one(sub))
    seen, uniq = set(), []
    for pair in out:
        if pair not in seen:
            seen.add(pair)
            uniq.append(pair)
    return uniq


def _refs_one(pred: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    t = pred.get("type")
    if pred.get("id") and t in _BARE_ORDER:
        out.append((t, pred["id"]))
    for r in pred.get("refs") or []:
        if r.get("id") and r.get("entity_type"):
            out.append((r["entity_type"], r["id"]))
    if t == "trained_skill":
        for s in ([pred["skill"]] if pred.get("skill") else []) + list(pred.get("skills") or []):
            if s:
                out.append(("skill", norm_key(s)))
    if t == "weapon_proficiency" and pred.get("group") and not pred.get("any"):
        out.append(("feat", norm_key(f"weaponproficiency{pred['group']}")))
    if t == "armor_proficiency" and pred.get("grade"):
        out.append(("feat", norm_key(f"armorproficiency{pred['grade'].lower()}")))
    if t == "talent":
        for tree in pred.get("trees") or []:
            out.append(("talent_tree", norm_key(re.sub(r"talent tree$", "", tree.lower()).strip())))
    return out


def is_numeric_gate(pred: dict) -> bool:
    return pred.get("type") in NUMERIC_GATES


def slug_of(pred: dict) -> str:
    """Compact machine key for a predicate (report/caching use)."""
    parts = [pred.get("type", "other")]
    for k in ("ability", "min", "skill", "group", "grade", "count", "mode", "id"):
        if pred.get(k) is not None:
            parts.append(f"{k}={pred[k]}")
    for k in ("skills", "trees", "names"):
        if pred.get(k):
            parts.append(k + "=" + "|".join(slugify(x) for x in pred[k]))
    if pred.get("type") == "other":
        parts.append(slugify(pred.get("text", ""))[:40])
    return ":".join(str(p) for p in parts)
