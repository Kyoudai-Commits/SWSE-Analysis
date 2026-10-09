"""Shared helpers: front matter, slugs, text statistics, file IO.

Stdlib only, on purpose (see xlsx.py for the rationale).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata

# --------------------------------------------------------------------------
# text normalization
# --------------------------------------------------------------------------

_WS = re.compile(r"[ \t]+")
_CURLY = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": "...",
    " ": " ",
}


def squash(text: str) -> str:
    return _WS.sub(" ", text).strip()


def decurly(text: str) -> str:
    for src, dst in _CURLY.items():
        text = text.replace(src, dst)
    return text


_PUNCT = re.compile(r"[^0-9a-z ]+")
_AN = re.compile(r"^(the|a|an)\s+")


def norm_name(text: str) -> str:
    """Canonical join key for entity names -- the single most load-bearing function here.

    Rules: case-fold, underscores to spaces, parentheses to spaces (their content
    is *kept*: ``Weapon Focus (Lightsabers)`` and ``Weapon Focus (Rifles)`` are
    different feats and must never collide), punctuation dropped, leading articles
    dropped, and the final word depluralized only when that is safe (not ``-us``,
    ``-ss``, ``-is``).

    Deliberately lossy but collision-averse: it has to reconcile wiki titles,
    MediaWiki slugs, spreadsheet spellings and player phrasing onto one key.
    """
    t = decurly(str(text or ""))
    t = re.sub(r"%27", "'", t)
    t = re.sub(r"%[0-9A-Fa-f]{2}", " ", t)
    t = t.replace("_", " ")
    t = re.sub(r"[()]", " ", t)
    t = unicodedata.normalize("NFKD", t)
    t = t.lower()
    t = re.sub(r"[^0-9a-z ']+", " ", t)
    t = squash(t)
    t = _AN.sub("", t)
    parts = t.split()
    if parts:
        last = parts[-1]
        if last.endswith("s") and not last.endswith(("ss", "us", "is", "as", "os")) and len(last) > 4:
            parts[-1] = last[:-1]
    t = " ".join(parts)
    return squash(t)


def slugify(text: str) -> str:
    t = decurly(str(text or "")).strip()
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"[^0-9A-Za-z_\-.()'!]", "", t)
    return t.strip("_")


def kebab(text: str) -> str:
    t = decurly(str(text or "")).lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "untitled"


def tokens(text: str) -> int:
    """Rough token estimate for GPT-family tokenizers (~1.33 tokens/word)."""
    if not text:
        return 0
    return int(len(text) / 4 + 0.5)


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


# --------------------------------------------------------------------------
# front matter (YAML subset used by the crawler)
# --------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def parse_front_matter(raw: str) -> tuple[dict, str]:
    """Split ``---\\nkey: value\\n---\\nbody``. Tolerant of the subset we emitted.

    Returns (meta, body). Unparseable lines are kept as raw strings.
    """
    m = _FM_RE.match(raw)
    if not m:
        return {}, raw
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        key, sep, val = line.partition(":")
        if not sep:
            continue
        key, val = key.strip(), val.strip()
        meta[key] = _coerce_scalar(val)
    return meta, raw[m.end() :]


def _coerce_scalar(val: str):
    if val == "":
        return None
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        out = []
        for part in re.findall(r'"((?:[^"\\]|\\.)*)"|([^,\s][^,]*?)(?=\s*,|\s*$)', inner):
            item = part[0] if part[0] else part[1]
            item = item.strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            if item:
                out.append(item)
        return out
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    return val


def dump_front_matter(meta: dict) -> str:
    out = ["---"]
    for key, val in meta.items():
        if val is None:
            continue
        if isinstance(val, list):
            out.append(f"{key}: [{', '.join(json.dumps(str(v), ensure_ascii=False) for v in val)}]")
        elif isinstance(val, int) and not isinstance(val, bool):
            out.append(f"{key}: {val}")
        else:
            out.append(f'{key}: {json.dumps(str(val), ensure_ascii=False)}')
    out.append("---")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_text(path: str, text: str) -> str:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


class JsonlWriter:
    """Streaming .jsonl writer with a count, so manifests can report it."""

    def __init__(self, path: str):
        self.path = path
        self.n = 0
        ensure_dir(os.path.dirname(path))
        self._fh = open(path, "w", encoding="utf-8", newline="\n")

    def write(self, obj: dict) -> None:
        self._fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        self._fh.write("\n")
        self.n += 1

    def close(self) -> int:
        self._fh.close()
        return self.n

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def write_jsonl(path: str, rows, key: str | None = None) -> int:
    if isinstance(rows, list):
        rows = iter(rows)
    n = 0
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            if key is not None and not row:
                continue
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            n += 1
    return n


def read_jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


# --------------------------------------------------------------------------
# prerequisites
# --------------------------------------------------------------------------

_PREREQ_KEYS_RAW = {
    "minimum level": "min_level",
    "min level": "min_level",
    "level": "min_level",
    "base attack bonus": "base_attack_bonus",
    "bab": "base_attack_bonus",
    "trained skills": "trained_skills",
    "skills": "skills",
    "feats": "feats",
    "feat": "feats",
    "force points": "force_points",
    "hit points": "hit_points",
    "alignment": "alignment",
    "ability scores": "ability_scores",
    "ability score": "ability_scores",
    "force sensitivity": "force_sensitivity",
    "special": "special",
    "other": "other",
    "languages": "languages",
    "size": "size",
    "species": "species",
    "talent": "talents",
    "talents": "talents",
    "destiny": "destiny",
}

# keys are canonicalized with norm_name() so "Base Attack Bonus", "BAB" and any
# plural/singular drift all land on the same field
_PREREQ_KEYS = {norm_name(k): v for k, v in _PREREQ_KEYS_RAW.items()}

_SPLIT_COMMA = re.compile(r",(?![^()]*\))")


def split_list(text: str) -> list[str]:
    """Split a rule list on commas that are not inside parentheses."""
    out = []
    for part in _SPLIT_COMMA.split(str(text or "")):
        part = squash(part).strip(" .;")
        if part:
            out.append(part)
    return out


def parse_prerequisites(text: str) -> dict:
    """Parse a SWSE prerequisite block into structured parts.

    Handles the labelled form used by prestige classes::

        Minimum Level: 7th
        Trained Skills: Pilot
        Feats: Melee Defense, Rapid Strike, Weapon Focus (Melee Weapon)

    and the bare form used by feats/talents ("Trained in Acrobatics",
    "Str 13, BAB +1"). Bare items land under ``free_text``.
    """
    text = str(text or "").replace("\\n", "\n")
    out: dict = {}
    free: list[str] = []
    for part in re.split(r"[;\n]", text):
        part = squash(part)
        if not part:
            continue
        key, sep, val = part.partition(":")
        mapped = _PREREQ_KEYS.get(norm_name(key)) if sep else None
        if mapped:
            items = out.setdefault(mapped, [])
            for item in split_list(val):
                if item not in items:
                    items.append(item)
        else:
            for item in split_list(part):
                if item.lower() in ("none", "n/a", "-"):
                    continue
                if item not in free:
                    free.append(item)
    if free:
        out["free_text"] = free
    return out


# --------------------------------------------------------------------------
# value comparison (cross-source disagreement severity)
# --------------------------------------------------------------------------

# spellings that mean the same thing across our three sources
ABBREV = {
    "bab": "base attack bonus",
    "str": "strength", "dex": "dexterity", "con": "constitution",
    "int": "intelligence", "wis": "wisdom", "cha": "charisma",
    "ac": "armor class", "hp": "hit points", "fp": "force points",
    "cr": "challenge rating", "cl": "character level",
    "rtg": "rating", "swa": "star wars saga edition",
}

_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "with", "you", "your", "youre",
    "is", "are", "in", "on", "as", "for", "that", "this", "can", "may", "can",
    "when", "if", "it", "its", "they", "them", "make", "makes", "making",
    "use", "used", "using", "gain", "gains", "get", "gets", "receive", "receives",
    "as", "an", "instead", "also", "then", "than", "than", "once", "effect",
}


def value_tokens(text: str) -> list[str]:
    """Comparable token bag: abbreviations expanded, function words dropped."""
    t = norm_name(str(text or ""))
    t = re.sub(r"\b(\d+)d(\d+)\b", r"\1d\2", t)
    words = []
    for w in t.split():
        w = ABBREV.get(w, w)
        if w in _STOPWORDS:
            continue
        words.extend(w.split())
    return words


def diff_severity(values: list[str]) -> str:
    """How much do these per-source spellings of one field actually differ?

    ``equivalent``  same words, different order/punctuation  -> not a disagreement
    ``wording``     same numbers and same dice, different prose (paraphrase/errata)
    ``value``       the numbers, dice, or content words differ -> a real conflict
    """
    bags = [set(value_tokens(v)) for v in values if v not in (None, "")]
    if len(bags) < 2:
        return "equivalent"
    if all(b == bags[0] for b in bags):
        return "equivalent"

    def nums(bag):
        return sorted(x for x in bag if re.search(r"\d", x))

    if all(nums(b) == nums(bags[0]) for b in bags):
        return "wording"
    return "value"
