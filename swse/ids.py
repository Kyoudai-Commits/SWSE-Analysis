"""Stable identifier and text-normalisation helpers.

Canonical entities are keyed by a slug derived from their display name, e.g.
``Weapon Proficiency (Pistols)`` -> ``weapon_proficiency_pistols``. Slugs are the
join keys used across JSON, SQLite and the prerequisite graph, so they must be:

* deterministic (same input text -> same slug, forever),
* readable (an agent can guess the slug from a name),
* unique within an entity type (collisions get a disambiguating suffix).
"""

from __future__ import annotations

import re
import unicodedata

_SLUG_KEEP = re.compile(r"[a-z0-9]+")

#: Characters/patterns that are pure formatting noise in this corpus.
_NOISE = (
    ("\u2019", "'"),
    ("\u2018", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2013", "-"),
    ("\u2014", "-"),
    ("\u2026", "..."),
    ("\u00a0", " "),
)


def fold(text: object) -> str:
    """Normalise unicode, collapse whitespace, strip. Never returns ``None``."""
    if text is None:
        return ""
    s = str(text)
    for a, b in _NOISE:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def slugify(name: object) -> str:
    """``"Force Storm (JATM)"`` -> ``"force_storm_jatm"``."""
    s = fold(name).lower()
    s = s.replace("&", " and ")
    parts = _SLUG_KEEP.findall(s)
    return "_".join(parts)


def norm_key(name: object) -> str:
    """Aggressive match key used when merging records across sources.

    Two records with the same ``norm_key`` are candidates for the same entity.
    This is deliberately lossier than :func:`slugify` (punctuation and case are
    dropped entirely) so that ``"Ace Pilot"`` and ``"Ace Pilot "`` and
    ``"ace pilot"`` all merge.
    """
    s = fold(name).lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def is_blank(value: object) -> bool:
    """True for None, empty string, whitespace-only, or Excel error placeholders."""
    if value is None:
        return True
    if isinstance(value, str):
        t = value.strip()
        return t == "" or t.startswith("#") or t in {"-", "--", "N/A", "n/a", "None", "none"}
    return False


def fold_multiline(text: object) -> str:
    """Like :func:`fold` but preserves newlines.

    Newlines are *structural* in this corpus: the Master Reference stores
    multi-part prerequisites and class-skill lists as newline-separated cells,
    so collapsing them would destroy the section boundaries.
    """
    if text is None:
        return ""
    s = str(text)
    for a, b in _NOISE:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t\v\f]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()


def clean_cell(value: object) -> object:
    """Return a JSON-friendly value for a spreadsheet cell.

    * blank-ish cells -> ``None``
    * whole-number floats -> ``int`` (Excel stores every number as float)
    * strings -> whitespace-normalised **with newlines preserved**
    * everything else -> ``str(value)``
    """
    if is_blank(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else round(value, 6)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return fold_multiline(value)
    return fold_multiline(str(value))


def split_list(text: object, separators: str = ",\n;") -> list[str]:
    """Split a spreadsheet cell that holds a delimited list of names.

    Parenthesis-aware: ``"Knowledge (all; taken individually)"`` must survive as
    one entry, so separators are only honoured at bracket depth zero. Newlines
    are preserved as separators (see :func:`fold_multiline`) because the Master
    Reference uses them as the primary list delimiter.
    """
    s = fold_multiline(text)
    if not s:
        return []
    out: list[str] = []
    buf = ""
    depth = 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if depth == 0 and ch in separators:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
            continue
        buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def dedupe(seq):
    """Order-preserving de-duplication."""
    seen = set()
    out = []
    for item in seq:
        key = item if isinstance(item, str) else repr(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def split_by_vocabulary(text: object, vocabulary: dict[str, str]) -> list[dict]:
    """Split a space-joined list of option names using a known vocabulary.

    The Master Reference stores class grants as a single string, e.g.

        "Force Sensitivity Weapon Proficiency (Lightsabers) Weapon Proficiency
         (Simple Weapons)"

    which is unusable without re-segmenting it. ``vocabulary`` maps
    ``norm_key(name) -> canonical name``. Matching is greedy-longest at every
    position, and a matched head may be followed by a parenthesised *parameter*
    (``Weapon Proficiency (Lightsabers)``), which is captured separately.

    Returns a list of ``{"name", "norm", "param", "matched"}`` dicts; text that
    matches nothing is returned as an unmatched entry rather than silently
    dropped, so a vocabulary gap is visible instead of invisible.
    """
    s = fold(text)
    if not s:
        return []
    # index by first word so the inner loop stays small
    index: dict[str, list[tuple[str, str]]] = {}
    for key, name in vocabulary.items():
        first = fold(name).split(" ")[0].lower()
        index.setdefault(first, []).append((fold(name).lower(), name))
    for bucket in index.values():
        bucket.sort(key=lambda t: -len(t[0]))

    out: list[dict] = []
    i, n = 0, len(s)
    buf = ""
    note_re = re.compile(r"^(must|requires?|prerequisite|see|if|only|cannot|not)\b", re.I)
    while i < n:
        ch = s[i]
        if ch.isspace():
            # whitespace is a separator between options, but inside unmatched text
            # it is part of the words we are still trying to recognise
            if buf:
                buf += " "
            i += 1
            continue
        word = s[i:].split(" ", 1)[0].strip(",:;*").lower()
        best: tuple[int, str, str] | None = None
        for disp, name in index.get(word, []):
            if s[i:i + len(disp)].lower() == disp and (
                    i + len(disp) >= n or not s[i + len(disp)].isalnum()):
                best = (len(disp), disp, name)
                break
        if best:
            if buf.strip():
                out.append({"name": fold(buf), "norm": norm_key(buf), "param": None, "matched": False})
                buf = ""
            length, _disp, name = best
            j = i + length
            while j < n and s[j] == "*":     # footnote markers ("Force Training*")
                j += 1
            param = None
            note = None
            while j < n and s[j].isspace():
                j += 1
            if j < n and s[j] == "(":
                depth = 0
                k = j
                while k < n:
                    if s[k] == "(":
                        depth += 1
                    elif s[k] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k < n:
                    inner = fold(s[j + 1:k])
                    j = k + 1
                    # "(must have the prerequisite Intelligence of 13)" is a note,
                    # not a parameter choice
                    if note_re.match(inner):
                        note = inner
                    else:
                        param = inner
            entry = {"name": fold(name), "norm": norm_key(name), "param": param,
                     "note": note, "matched": True}
            if param:
                entry["name"] = f"{fold(name)} ({param})"
            out.append(entry)
            i = j
        else:
            buf += ch
            i += 1
    if buf.strip():
        out.append({"name": fold(buf), "norm": norm_key(buf), "param": None, "matched": False})
    return out
