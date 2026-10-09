"""Stage 3: loading canonical data, and the SQLite index built from it.

``Dataset`` is the object every analysis module works against::

    from swse.store import Dataset
    db = Dataset.load()
    db.count("feat")                       # 387
    db.get("feat", "feat_power_attack")    # one record
    db.where("feat", canon="official")     # filtered list
    db.index()                             # prereq.EntityIndex for lookups

The SQLite mirror exists so that agents (and humans) can answer questions with
plain SQL instead of loading 4,800 JSON records:

    sqlite3 data/index/swse.sqlite3 'select name from record where entity="feat"'
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from functools import cached_property
from pathlib import Path

from . import paths
from .ids import norm_key, slugify
from .prereq import EntityIndex

#: Entities that represent a choice a player makes when building a character.
OPTION_ENTITIES = (
    "species", "class", "feat", "talent", "talent_tree", "special_talent",
    "force_power", "force_technique", "force_secret", "force_regimen",
    "lightsaber_form", "skill", "destiny", "background", "language",
    "near_human_trait", "droid_option", "starship_maneuver", "unleashed_ability",
)

#: Entities that modify a character but are not chosen from a class/feat list.
MODIFIER_ENTITIES = ("racial_ability", "class_feature", "weapon_mod", "age_category",
                     "size_category", "exotic_weapon_group")

#: Entities that are purchasable gear.
GEAR_ENTITIES = ("weapon", "armor", "equipment", "ammunition", "cybernetic",
                 "weapon_template", "armor_template", "shield_template",
                 "weapon_accessory", "armor_accessory", "equipment_accessory")


class Dataset:
    """Read-only view over ``data/canonical``."""

    def __init__(self, records: dict[str, list[dict]], meta: dict | None = None):
        self.records = records
        self.meta = meta or {}

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, entities: tuple[str, ...] | list[str] | None = None) -> "Dataset":
        if not paths.CANONICAL_DIR.exists():
            raise FileNotFoundError(
                "no canonical data - run `python -m swse.cli canonicalize` (or `make data`)")
        out: dict[str, list[dict]] = {}
        meta: dict = {}
        for file in sorted(paths.CANONICAL_DIR.glob("*.json")):
            if file.name == "index.json":
                continue
            entity = file.stem
            if entities and entity not in entities:
                continue
            doc = json.loads(file.read_text(encoding="utf-8"))
            out[entity] = doc["records"]
            meta[entity] = {k: v for k, v in doc.items() if k != "records"}
        index_file = paths.CANONICAL_DIR / "index.json"
        if index_file.exists():
            meta["_index"] = json.loads(index_file.read_text(encoding="utf-8"))
        return cls(out, meta)

    # ------------------------------------------------------------- accessors
    @property
    def entities(self) -> list[str]:
        return sorted(self.records)

    def count(self, entity: str) -> int:
        return len(self.records.get(entity, []))

    def total(self) -> int:
        return sum(len(v) for v in self.records.values())

    def all(self, entity: str) -> list[dict]:
        return list(self.records.get(entity, []))

    def get(self, entity: str, record_id: str) -> dict | None:
        for rec in self.records.get(entity, []):
            if rec["id"] == record_id:
                return rec
        return None

    def find(self, entity: str, name: str) -> list[dict]:
        """Case/punctuation-insensitive name search."""
        k = norm_key(name)
        hits = [r for r in self.records.get(entity, []) if norm_key(r["name"]) == k]
        if hits:
            return hits
        return [r for r in self.records.get(entity, []) if k in norm_key(r["name"])]

    def search(self, text: str, entities: tuple[str, ...] | None = None) -> list[dict]:
        """Substring search across name + attrs values."""
        needle = norm_key(text)
        out = []
        for entity in (entities or self.entities):
            for rec in self.records.get(entity, []):
                hay = norm_key(rec["name"])
                if needle in hay or any(needle in norm_key(v) for v in rec["attrs"].values() if isinstance(v, str)):
                    out.append(rec)
        return out

    def where(self, entity: str, **kwargs) -> list[dict]:
        """Filter records: ``where("class", canon="official")`` or attrs via ``attr__field``."""
        out = []
        for rec in self.records.get(entity, []):
            ok = True
            for key, want in kwargs.items():
                if key.startswith("attr__"):
                    got = rec["attrs"].get(key[6:])
                elif key == "flag":
                    got = want in rec.get("flags", [])
                    if got:
                        continue
                    ok = False
                    break
                else:
                    got = rec.get(key)
                if isinstance(want, (list, tuple, set)):
                    if got not in want:
                        ok = False
                        break
                elif got != want:
                    ok = False
                    break
            if ok:
                out.append(rec)
        return out

    def by_flag(self, flag: str) -> Iterator[tuple[str, dict]]:
        for entity, recs in self.records.items():
            for rec in recs:
                if flag in rec.get("flags", []):
                    yield entity, rec

    @cached_property
    def by_id(self) -> dict[str, dict]:
        out = {}
        for recs in self.records.values():
            for rec in recs:
                out[rec["id"]] = rec
        return out

    def index(self) -> EntityIndex:
        idx = EntityIndex()
        for entity, recs in self.records.items():
            if entity == "reference_link":
                continue
            for rec in recs:
                idx.add(entity, rec["name"], rec["id"])
                for alias in rec["attrs"].get("aliases") or []:
                    idx.add(entity, alias, rec["id"])
        return idx

    # -------------------------------------------------------------- summaries
    def stats(self) -> dict:
        per_entity = {}
        for entity, recs in sorted(self.records.items()):
            canon = {"official": 0, "third_party": 0, "homebrew": 0}
            flagged: dict[str, int] = {}
            with_prereq = 0
            for rec in recs:
                canon[rec.get("canon", "third_party")] = canon.get(rec.get("canon", "third_party"), 0) + 1
                for f in rec.get("flags", []):
                    flagged[f] = flagged.get(f, 0) + 1
                if rec.get("prerequisites"):
                    with_prereq += 1
            per_entity[entity] = {
                "count": len(recs), "canon": canon, "flags": flagged,
                "with_prerequisites": with_prereq,
                "sourcebooks": len({sb["id"] for r in recs for sb in (r.get("sourcebooks") or [])}),
            }
        return {"entities": per_entity, "total": self.total()}


# ---------------------------------------------------------------------------
# SQLite mirror
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entity (
    name        TEXT PRIMARY KEY,
    label       TEXT,
    role        TEXT,
    record_count INTEGER
);
CREATE TABLE IF NOT EXISTS record (
    id          TEXT PRIMARY KEY,
    entity      TEXT NOT NULL,
    name        TEXT NOT NULL,
    canon       TEXT NOT NULL,
    norm_name   TEXT NOT NULL,
    slug        TEXT NOT NULL,
    flags       TEXT,
    sourcebooks TEXT,
    attrs_json  TEXT NOT NULL,
    prereq_json TEXT,
    sources_json TEXT NOT NULL,
    conflicts_json TEXT,
    FOREIGN KEY(entity) REFERENCES entity(name)
);
CREATE INDEX IF NOT EXISTS record_entity ON record(entity);
CREATE INDEX IF NOT EXISTS record_norm_name ON record(norm_name);
CREATE INDEX IF NOT EXISTS record_canon ON record(canon);
CREATE TABLE IF NOT EXISTS prerequisite_edge (
    src_entity  TEXT NOT NULL,
    src_id      TEXT NOT NULL,
    req_type    TEXT NOT NULL,
    req_entity  TEXT,
    req_id      TEXT,
    req_key     TEXT,
    param       TEXT,
    mode        TEXT,
    detail_json TEXT,
    resolved    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS edge_src ON prerequisite_edge(src_id);
CREATE INDEX IF NOT EXISTS edge_req ON prerequisite_edge(req_id);
CREATE TABLE IF NOT EXISTS attr (
    entity      TEXT NOT NULL,
    field       TEXT NOT NULL,
    filled      INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    sample      TEXT
);
CREATE TABLE IF NOT EXISTS provenance (
    record_id   TEXT NOT NULL,
    source      TEXT NOT NULL,
    block       TEXT NOT NULL,
    sheet       TEXT NOT NULL,
    row         INTEGER,
    ref         TEXT,
    canon       TEXT
);
CREATE INDEX IF NOT EXISTS prov_record ON provenance(record_id);
CREATE TABLE IF NOT EXISTS build_meta (
    key TEXT PRIMARY KEY, value TEXT
);
"""


def build_sqlite(db: Dataset | None = None, path: Path | None = None, verbose: bool = True) -> Path:
    """Create/refresh ``data/index/swse.sqlite3`` from the canonical data."""
    from .graph import PrereqGraph

    db = db or Dataset.load()
    path = path or paths.SQLITE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_SQL)

    for entity, recs in db.records.items():
        meta = db.meta.get(entity, {})
        con.execute("INSERT OR REPLACE INTO entity VALUES (?,?,?,?)",
                    (entity, meta.get("label", entity), meta.get("role", "option"), len(recs)))
        fields: dict[str, list] = {}
        for rec in recs:
            con.execute(
                "INSERT INTO record VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rec["id"], entity, rec["name"], rec.get("canon", "third_party"),
                 norm_key(rec["name"]), slugify(rec["name"]),
                 ",".join(rec.get("flags") or []),
                 ",".join(sb["id"] for sb in (rec.get("sourcebooks") or [])),
                 json.dumps(rec["attrs"], ensure_ascii=False),
                 json.dumps(rec.get("prerequisites"), ensure_ascii=False) if rec.get("prerequisites") else None,
                 json.dumps(rec["sources"], ensure_ascii=False),
                 json.dumps(rec.get("conflicts"), ensure_ascii=False) if rec.get("conflicts") else None))
            for src in rec["sources"]:
                con.execute("INSERT INTO provenance VALUES (?,?,?,?,?,?,?)",
                            (rec["id"], src.get("source"), src.get("block"), src.get("sheet"),
                             src.get("row"), src.get("ref"), src.get("canon")))
            for f, v in rec["attrs"].items():
                bucket = fields.setdefault(f, [0, None])
                if v not in (None, "", []):
                    bucket[0] += 1
                    if bucket[1] is None:
                        bucket[1] = str(v)[:120]
        for f, (filled, sample) in sorted(fields.items()):
            con.execute("INSERT INTO attr VALUES (?,?,?,?,?)", (entity, f, filled, len(recs), sample))

    graph = PrereqGraph(db)
    for edge in graph.edges():
        con.execute("INSERT INTO prerequisite_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (edge["src_entity"], edge["src_id"], edge["req_type"], edge.get("req_entity"),
                     edge.get("req_id"), edge.get("req_key"), edge.get("param"), edge.get("mode"),
                     json.dumps(edge.get("predicate"), ensure_ascii=False),
                     1 if edge.get("req_id") else 0))

    con.execute("INSERT INTO build_meta VALUES (?,?)", ("generated_from", "data/canonical"))
    con.execute("INSERT INTO build_meta VALUES (?,?)", ("record_count", str(db.total())))
    con.commit()
    con.close()
    if verbose:
        print(f"  wrote {paths.rel(path)} ({path.stat().st_size/1024:.0f} KiB)")
    return path


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or paths.SQLITE_PATH
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run `python -m swse.cli db`")
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con
