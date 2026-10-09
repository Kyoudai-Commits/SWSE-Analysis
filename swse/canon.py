"""Stage 2: raw blocks -> ``data/canonical/<entity>.json``.

Responsibilities
----------------
* apply row/entity/post hooks from :mod:`swse.hooks`
* merge the same option as recorded by different sources into one record,
  resolving field conflicts by canon priority (official > third_party > homebrew)
* apply the committed curation overlay in ``data/curation/`` so human/agent
  corrections survive regeneration
* assign stable ids, attach provenance, and emit a canonicalisation report

Output record shape::

    {
      "id": "feat_power_attack",
      "entity": "feat",
      "name": "Power Attack",
      "canon": "official",
      "attrs": {...},                    # every data field
      "prerequisites": {...} | null,     # structured, see swse.prereq
      "relations": {...},                # ids of related entities
      "sourcebooks": [...],
      "sources": [{source, block, sheet, row, ref, canon}, ...],
      "conflicts": {field: {chosen, alternatives}},
      "flags": [...]
    }
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

import yaml

from . import paths
from .blocks import load_blocks
from .extract import read_raw
from .hooks import ENTITY_HOOKS, POST_HOOKS, ROW_HOOKS
from .ids import fold, norm_key, slugify
from .prereq import EntityIndex, parse_and_resolve
from .sources import load_registry

CANON_RANK = {"official": 0, "third_party": 1, "homebrew": 2}
RESERVED = {"id", "entity", "name", "canon", "attrs", "prerequisites", "relations",
            "sourcebooks", "sources", "conflicts", "flags"}


class CanonError(RuntimeError):
    pass


class CanonContext:
    """Shared state passed to every hook."""

    def __init__(self, config: dict, blocks: dict, curation: dict):
        self.config = config
        self.blocks = blocks
        self.curation = curation
        self.records: dict[str, list[dict]] = defaultdict(list)
        self.state: dict = {}
        self.stats: dict[str, int] = defaultdict(int)
        self.dropped: list[dict] = []
        self.gaps: list[dict] = []
        self._index: EntityIndex | None = None

    # ---- hook services ---------------------------------------------------
    def note_dropped(self, block: str, row: int, reason: str) -> None:
        self.dropped.append({"block": block, "row": row, "reason": reason})
        self.stats["rows_dropped"] += 1

    def note_gap(self, kind: str, detail: str) -> None:
        """Record a gap. Identical gaps are noted once.

        A name collision is reported by every record involved in it, so without
        de-duplication one three-way collision fills the report with three
        identical lines.
        """
        entry = {"kind": kind, "detail": detail}
        if entry not in self.gaps:
            self.gaps.append(entry)

    def stat(self, key: str, amount: int = 1) -> None:
        self.stats[key] += amount

    def add_record(self, entity: str, name: str, attrs: dict, canon: str = "third_party",
                   sources: list[dict] | None = None, flags: list[str] | None = None) -> dict:
        rec = {
            "id": "", "entity": entity, "name": fold(name), "canon": canon,
            "attrs": attrs, "prerequisites": None, "relations": {},
            "sourcebooks": [], "sources": sources or [], "conflicts": {},
            "flags": list(flags or []),
        }
        # Records synthesised by a hook (e.g. talent trees derived from talent
        # rows) say so explicitly, so `canon_basis` is never missing.
        rec["attrs"].setdefault("canon_basis", "derived_record")
        self.records[entity].append(rec)
        return rec

    def build_index(self) -> EntityIndex:
        idx = EntityIndex()
        for entity, recs in self.records.items():
            if entity in {"reference_link"}:
                continue
            for rec in recs:
                idx.add(entity, rec["name"], rec["id"])
                for alias in rec["attrs"].get("aliases") or []:
                    idx.add(entity, alias, rec["id"])
        self._index = idx
        return idx

    def parse_prereq(self, text: object) -> dict:
        if self._index is None:
            self.build_index()
        return parse_and_resolve(text, self._index)


# ---------------------------------------------------------------------------
# config / curation loading
# ---------------------------------------------------------------------------
def load_config() -> dict:
    if not paths.ENTITIES_YAML.exists():
        raise CanonError(f"missing {paths.rel(paths.ENTITIES_YAML)}")
    return yaml.safe_load(paths.ENTITIES_YAML.read_text(encoding="utf-8")) or {}


def load_curation() -> dict:
    out = {"aliases": {}, "merges": {}, "drops": {}, "overrides": {}, "gaps": {}}
    for key in out:
        p = paths.CURATION_DIR / f"{key}.yaml"
        if p.exists():
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            out[key] = doc.get(key, doc) or out[key]
    return out


# ---------------------------------------------------------------------------
# merge keys & ids
# ---------------------------------------------------------------------------
def merge_key(entity: str, mode: str, fields: dict) -> str | None:
    if mode in ("name", None, ""):
        base = fields.get("name")
        return norm_key(base) if base else None
    if mode == "name_and_tree":
        n, t = norm_key(fields.get("name")), norm_key(fields.get("tree"))
        return f"{n}|{t}" if n else None
    if mode == "name_and_group":
        n, g = norm_key(fields.get("name")), norm_key(fields.get("option_group"))
        return f"{n}|{g}" if n else None
    v = fields.get(mode)
    return norm_key(v) if v is not None else None


def _clean_name(name: object) -> str:
    """Normalise a display name.

    Source cells sometimes leave an empty parenthetical behind ("Double Attack
    ()") when a parameter column is blank; that trailing "()" is noise, not part
    of the option's name.
    """
    s = fold(name)
    s = re.sub(r"\s*\(\s*\)(\s*\(\s*\))*\s*$", "", s).strip()
    return s or fold(name)


def _disambiguator(rec: dict) -> str:
    """Best available suffix to tell two same-named records apart.

    Order: a discriminating attribute, then the sourcebook the record comes
    from, then the block+row (always available, always traceable).
    """
    a = rec.get("attrs", {})
    for field in ("tree", "option_group", "destiny_type", "species_kind",
                  "class_kind", "size", "type", "grade", "special_talent_class"):
        if a.get(field):
            return slugify(a[field])
    from .sourcebooks import by_id
    for sb_id in rec.get("_sourcebook_ids") or []:
        sb = by_id(sb_id)
        if sb:
            return slugify(sb.abbreviation)
    sbs = rec.get("sourcebooks") or []
    if sbs:
        return slugify(sbs[0].get("abbreviation") or sbs[0].get("id") or "")
    if rec.get("sources"):
        src = rec["sources"][0]
        return slugify(f"{src.get('block')} {src.get('row')}")
    return "x"


def assign_ids(entity: str, records: list[dict], used: set[str] | None = None) -> set[str]:
    """Assign ``<entity>_<slug>[__<disambiguator>]`` ids. Returns the used-id set."""
    counts: dict[str, int] = defaultdict(int)
    for rec in records:
        counts[f"{entity}_{slugify(rec['name'])}"] += 1
    used = set(used or ()) | {r["id"] for r in records if r.get("id")}
    for rec in records:
        if rec.get("id"):
            continue
        base = f"{entity}_{slugify(rec['name'])}"
        candidate = f"{base}__{_disambiguator(rec)}" if counts[base] > 1 else base
        n = 2
        while candidate in used:
            candidate = f"{base}_{n}"
            n += 1
        used.add(candidate)
        rec["id"] = candidate
    return used


# ---------------------------------------------------------------------------
# building
# ---------------------------------------------------------------------------
def map_fields(spec: dict | str, row: dict) -> dict:
    if spec == "*":
        return {k: v for k, v in row.items() if not k.startswith("_")}
    out = {}
    for canonical, extracted in (spec or {}).items():
        if extracted in row:
            out[canonical] = row[extracted]
    return out


def build_entity(ctx: CanonContext, entity: str, spec: dict) -> None:
    """Build one entity: per-source records first, then cross-source merge.

    Merge policy (deliberate, and the reason the corpus stays trustworthy):

    * Rows from **different sources** that share a merge key are the same option
      and are merged, with differing field values recorded in ``conflicts``.
    * Rows from the **same source** that share a merge key are *not* merged - in
      this corpus a repeated name usually means two genuinely different options
      (two feats called "Staggering Attack", two powers called "Force Storm",
      a beast trait and a species trait both called "Scent"). They become
      separate records flagged ``name_collision`` and are listed in the report
      so a human or agent can decide, then declare the merge in
      ``data/curation/merges.yaml``.
    """
    mode = spec.get("merge_on", "name")
    # (merge_key, source_id) -> list of variants, in sheet order
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    order: list[tuple[str, str]] = []

    for bspec in spec.get("blocks", []):
        block_id = bspec["id"]
        block = ctx.blocks.get(block_id)
        if block is None:
            raise CanonError(f"entity {entity}: unknown block {block_id!r} (config/blocks.yaml)")
        rows = read_raw(block_id)
        ctx.state = dict(bspec.get("state") or {})
        ctx.stat("rows_read", len(rows))

        for row in rows:
            row = dict(row)
            dropped = False
            for hook_name in bspec.get("row_hooks", []) or []:
                hook = ROW_HOOKS.get(hook_name)
                if hook is None:
                    raise CanonError(f"unknown row hook {hook_name!r}")
                row = hook(ctx, row)
                if row is None:
                    dropped = True
                    break
            if dropped:
                continue
            canon = row.get("_canon") or bspec.get("canon") or block.canon
            fields = map_fields(bspec.get("fields", "*"), row)
            if not fields:
                continue
            if not fields.get("name") and block.name_field:
                value = next((fields.get(c) for c in block.name_field if fields.get(c) not in (None, "")), None)
                if value is not None:
                    fields["name"] = block.name_template.format(value=value) if block.name_template else str(value)
            key = merge_key(entity, mode, fields)
            if not key:
                ctx.note_dropped(block_id, row.get("_row", -1), "no merge key (missing name)")
                continue

            variant = {
                "fields": fields,
                "canon": canon,
                "flags": list(row.get("_flags") or []),
                "sourcebook_ids": list(row.get("_sourcebook_ids") or []),
                "sourcebook_unresolved": list(row.get("_sourcebook_unresolved") or []),
                "provenance": {
                    "source": block.source, "block": block_id, "sheet": block.sheet,
                    "row": row.get("_row"), "ref": row.get("_ref"), "canon": canon,
                },
            }
            gk = (key, block.source)
            if gk not in groups:
                order.append(gk)
            groups[gk].append(variant)

    for gk in list(groups):
        groups[gk] = collapse_duplicates(groups[gk], ctx, entity, gk[0])

    # ---- collapse each (key, source) group into one provisional record ----
    by_key: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    for key, source in order:
        by_key[key].append((source, groups[(key, source)]))

    records: list[dict] = []
    for key, per_source in by_key.items():
        # a source with several same-named rows: each row becomes its own record
        ambiguous = any(len(variants) > 1 for _, variants in per_source)
        units: list[tuple[str, list[dict]]] = []
        for source, variants in per_source:
            if len(variants) == 1:
                units.append((source, variants))
            else:
                units.extend((source, [v]) for v in variants)
        if len(per_source) == 1 and not ambiguous:
            merged_units = [units]                      # single source, single row
        elif ambiguous:
            merged_units = [[u] for u in units]         # never merge: collisions
        else:
            merged_units = [units]                      # one row per source -> merge
        for unit in merged_units:
            rec = _merge_unit(entity, unit, ctx)
            if ambiguous:
                rec["flags"] = sorted(set(rec["flags"]) | {"name_collision"})
                ctx.stat("name_collisions")
                ctx.note_gap("collision", f"{entity}: {rec['name']!r} appears "
                             f"{sum(len(v) for _, v in per_source)}x across "
                             f"{len(per_source)} source(s) - kept separate, "
                             f"declare a merge in data/curation/merges.yaml if they are the same option")
            records.append(rec)

    ctx.records[entity] = records
    assign_ids(entity, records)
    for hook_name in spec.get("entity_hooks", []) or []:
        hook = ENTITY_HOOKS.get(hook_name)
        if hook is None:
            raise CanonError(f"unknown entity hook {hook_name!r}")
        for rec in records:
            hook(ctx, rec)


def _fields_signature(fields: dict) -> dict:
    """Comparable form of a variant's fields: drop nulls, fold strings."""
    return {k: (norm_key(v) if isinstance(v, str) else v) for k, v in fields.items() if v not in (None, "")}


def collapse_duplicates(variants: list[dict], ctx: CanonContext, entity: str, key: str) -> list[dict]:
    """Collapse rows that are the same record written twice.

    Two variants collapse when one's populated fields are a subset of the
    other's and every shared field agrees (case/punctuation insensitive). The
    richer variant wins and absorbs the other's provenance. This removes
    SagaForge's repeated UI rows (``Double Attack`` appears 7x identically) and
    its near-duplicate equipment rows ("Energy cell" / "Energy Cell") without
    ever merging rows that actually disagree.
    """
    out: list[dict] = []
    for v in variants:
        sig = _fields_signature(v["fields"])
        placed = False
        for existing in out:
            esig = _fields_signature(existing["fields"])
            small, big = (sig, esig) if len(sig) <= len(esig) else (esig, sig)
            if all(big.get(k) == val for k, val in small.items()):
                keep = existing if len(esig) >= len(sig) else v
                drop = v if keep is existing else existing
                for f, val in drop["fields"].items():
                    keep["fields"].setdefault(f, val)
                keep["provenance"] = existing["provenance"]
                keep["sources_absorbed"] = (existing.get("sources_absorbed") or []) + [drop["provenance"]]
                keep["flags"] = sorted(set(keep["flags"]) | {"duplicate_rows_collapsed"})
                out[out.index(existing)] = keep
                placed = True
                ctx.stat("duplicate_rows_collapsed")
                break
        if not placed:
            out.append(v)
    return out


def _merge_unit(entity: str, units: list[tuple[str, list[dict]]], ctx: CanonContext) -> dict:
    """Merge one or more (source, variants) units into a canonical record."""
    values: dict[str, list[dict]] = defaultdict(list)
    sources: list[dict] = []
    flags: set[str] = set()
    sb_ids: list[str] = []
    sb_unres: list[str] = []
    canons: list[str] = []
    names: list[str] = []
    for _source, variants in units:
        for v in variants:
            sources.append(v["provenance"])
            sources.extend(v.get("sources_absorbed") or [])
            flags |= set(v["flags"])
            sb_ids += v["sourcebook_ids"]
            sb_unres += v["sourcebook_unresolved"]
            canons.append(v["canon"])
            for f, val in v["fields"].items():
                if val is None or val == "":
                    continue
                values[f].append({"value": val, **v["provenance"]})
            if v["fields"].get("name") or v["fields"].get("url"):
                names.append(str(v["fields"].get("name") or v["fields"].get("url")))

    best_canon = min(canons, key=lambda c: CANON_RANK.get(c, 9)) if canons else "third_party"
    # the display name comes from the best-canon source
    name = None
    for _source, variants in units:
        for v in variants:
            if v["canon"] == best_canon and (v["fields"].get("name") or v["fields"].get("url")):
                name = str(v["fields"].get("name") or v["fields"].get("url"))
                break
        if name:
            break
    name = name or (names[0] if names else "")

    rec = {
        "id": "", "entity": entity, "name": _clean_name(name), "canon": best_canon,
        "attrs": {}, "prerequisites": None, "relations": {},
        "sourcebooks": [], "sources": sources, "conflicts": {},
        "flags": sorted(flags), "_prereq_text": None,
    }
    if sb_ids:
        rec["_sourcebook_ids"] = sorted(set(sb_ids))
    if sb_unres:
        rec["_sourcebook_unresolved"] = sorted(set(sb_unres))
    # Default canonicity basis. `resolve_sourcebooks` upgrades records that cite a
    # published sourcebook to official, whatever workbook carried them.
    rec["attrs"]["canon_basis"] = "block_declaration"
    for f, entries in values.items():
        if f in RESERVED:
            # `name` arrives as a mapped column but belongs on the record, not in
            # attrs; duplicating it there wastes space and breaks the schema's
            # reserved-key guard.
            continue
        chosen = _pick(entries)
        rec["attrs"][f] = chosen["value"]
        alts = [e for e in entries if e is not chosen and _differ(e["value"], chosen["value"])]
        if alts:
            rec["conflicts"][f] = {
                "chosen": chosen["value"],
                "chosen_from": {"source": chosen["source"], "block": chosen["block"], "row": chosen["row"]},
                "alternatives": [
                    {"value": e["value"], "source": e["source"], "block": e["block"], "row": e["row"],
                     "canon": e["canon"]}
                    for e in alts
                ],
            }
            ctx.stat("field_conflicts")
    texts = [rec["attrs"].get("prerequisites_text")] + [
        rec["attrs"].get(k) for k in rec["attrs"] if k.endswith("_prereq_text")]
    texts = [t for t in texts if t]
    if texts:
        rec["_prereq_text"] = max(texts, key=len)
    return rec


def _differ(a, b) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return norm_key(a) != norm_key(b)
    return a != b


def _pick(entries: list[dict]) -> dict:
    """Choose the authoritative value: best canon, then longest text, then first."""
    def sort_key(e):
        v = e["value"]
        length = len(fold(v)) if isinstance(v, str) else (0 if v is None else 1)
        return (CANON_RANK.get(e.get("canon", "third_party"), 9), -length)
    return sorted(entries, key=sort_key)[0]


# ---------------------------------------------------------------------------
# curation overlay
# ---------------------------------------------------------------------------
def apply_curation(ctx: CanonContext) -> None:
    cur = ctx.curation
    by_entity: dict[str, dict[str, dict]] = {e: {r["id"]: r for r in recs} for e, recs in ctx.records.items()}

    # drops
    for entity, ids in (cur.get("drops") or {}).items():
        keep = []
        drop_set = set(ids or [])
        for rec in ctx.records.get(entity, []):
            if rec["id"] in drop_set or rec["name"] in drop_set:
                ctx.stat("curated_drops")
                continue
            keep.append(rec)
        if entity in ctx.records:
            ctx.records[entity] = keep
            by_entity[entity] = {r["id"]: r for r in keep}

    # aliases (extra merge keys)
    for entity, mapping in (cur.get("aliases") or {}).items():
        for rec in ctx.records.get(entity, []):
            extra = mapping.get(rec["id"]) or mapping.get(rec["name"])
            if extra:
                rec["attrs"]["aliases"] = sorted(set((rec["attrs"].get("aliases") or []) + list(extra)))
                ctx.stat("aliases_applied")

    # merges: [keep_id, dropped_id, ...]
    for entity, groups in (cur.get("merges") or {}).items():
        recs = ctx.records.get(entity, [])
        index = {r["id"]: r for r in recs}
        for group in groups or []:
            if not group:
                continue
            keep_id, *dupes = group
            keep = index.get(keep_id)
            if keep is None:
                ctx.note_gap("curation", f"merge target {keep_id} not found in {entity}")
                continue
            for d in dupes:
                other = index.pop(d, None)
                if other is None:
                    ctx.note_gap("curation", f"merge source {d} not found in {entity}")
                    continue
                keep["sources"].extend(other["sources"])
                for f, v in other["attrs"].items():
                    keep["attrs"].setdefault(f, v)
                for f, c in other["conflicts"].items():
                    keep["conflicts"].setdefault(f, c)
                keep["flags"] = sorted(set(keep["flags"]) | {"curated:merged"} | set(other["flags"]))
                keep["attrs"]["aliases"] = sorted(set((keep["attrs"].get("aliases") or []) + [other["name"]]))
                ctx.stat("curated_merges")
        ctx.records[entity] = list(index.values())
        by_entity[entity] = index

    # overrides
    for entity, mapping in (cur.get("overrides") or {}).items():
        for rec_id, patch in (mapping or {}).items():
            rec = by_entity.get(entity, {}).get(rec_id)
            if rec is None:
                ctx.note_gap("curation", f"override target {entity}:{rec_id} not found")
                continue
            for f, v in (patch.get("attrs") or {}).items():
                rec["attrs"][f] = v
            if patch.get("name"):
                rec["name"] = fold(patch["name"])
            if patch.get("canon"):
                rec["canon"] = patch["canon"]
            if patch.get("flags"):
                rec["flags"] = sorted(set(rec["flags"]) | set(patch["flags"]))
            if patch.get("relations"):
                rec["relations"].update(patch["relations"])
            if patch.get("prerequisites"):
                rec["attrs"]["prerequisites_text"] = patch["prerequisites"]
                rec["prerequisites"] = None
            rec["flags"] = sorted(set(rec["flags"]) | {"curated:overridden"})
            if patch.get("note"):
                rec["attrs"]["curation_note"] = fold(patch["note"])
            ctx.stat("overrides_applied")


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


def write_canonical(ctx: CanonContext, config: dict) -> dict:
    paths.ensure_dirs()
    entities = config.get("entities", {})
    index = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "sources": [s.id for s in load_registry()], "entities": {}}
    for entity, recs in sorted(ctx.records.items()):
        assign_ids(entity, recs)          # post hooks may have added id-less records
        recs = sorted(recs, key=lambda r: (r["canon"] != "official", r["name"].lower(), r["id"]))
        for rec in recs:
            rec.pop("_prereq_text", None)
            rec["attrs"] = {k: v for k, v in sorted(rec["attrs"].items()) if v is not None}
            rec["flags"] = sorted(set(rec.get("flags") or []))
            if not rec.get("sourcebooks"):
                rec.pop("sourcebooks", None)
            if not rec.get("conflicts"):
                rec.pop("conflicts", None)
            if not rec.get("relations"):
                rec.pop("relations", None)
        payload = {
            "entity": entity,
            "label": entities.get(entity, {}).get("label", entity),
            "role": entities.get(entity, {}).get("role", "option"),
            "count": len(recs),
            "generated_utc": index["generated_utc"],
            "records": recs,
        }
        out = paths.CANONICAL_DIR / f"{entity}.json"
        text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False, default=_json_default) + "\n"
        out.write_text(text, encoding="utf-8")
        index["entities"][entity] = {
            "count": len(recs),
            "file": paths.rel(out),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            "canon": {c: sum(1 for r in recs if r["canon"] == c) for c in ("official", "third_party", "homebrew")},
        }
    # Corpus totals, so a reader can size the dataset without opening 45 files.
    index["total"] = sum(meta["count"] for meta in index["entities"].values())
    index["canon"] = {
        c: sum(meta["canon"][c] for meta in index["entities"].values())
        for c in ("official", "third_party", "homebrew")
    }
    (paths.CANONICAL_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return index


def build(verbose: bool = True) -> tuple[CanonContext, dict]:
    config = load_config()
    blocks = {b.id: b for b in load_blocks()}
    curation = load_curation()
    ctx = CanonContext(config, blocks, curation)

    for entity, spec in config.get("entities", {}).items():
        build_entity(ctx, entity, spec)
        if verbose:
            print(f"  {entity:<22} {len(ctx.records[entity]):>5} records")

    apply_curation(ctx)
    for hook_name in config.get("post_hooks", []) or []:
        hook = POST_HOOKS.get(hook_name)
        if hook is None:
            raise CanonError(f"unknown post hook {hook_name!r}")
        hook(ctx)
        if verbose and hook_name == "derive_talent_trees":
            print(f"  {'talent_tree (derived)':<22} {len(ctx.records['talent_tree']):>5} records")

    index = write_canonical(ctx, config)
    if verbose:
        total = sum(v["count"] for v in index["entities"].values())
        print(f"  total canonical records: {total}")
        print(f"  field conflicts: {ctx.stats.get('field_conflicts', 0)}, "
              f"rows dropped: {ctx.stats.get('rows_dropped', 0)}")
    return ctx, index


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def write_report(ctx: CanonContext, index: dict) -> paths.Path:
    lines = ["# Canonicalisation report", "",
             f"Generated: {index['generated_utc']}  ",
             f"Sources: {', '.join(index['sources'])}", "",
             "## Entities", "",
             "| entity | records | official | 3rd-party | homebrew | file |",
             "|---|---:|---:|---:|---:|---|"]
    for entity, meta in sorted(index["entities"].items()):
        c = meta["canon"]
        lines.append(f"| `{entity}` | {meta['count']} | {c['official']} | {c['third_party']} | {c['homebrew']} | `{meta['file']}` |")
    total = sum(m["count"] for m in index["entities"].values())
    lines += ["", f"**Total records:** {total}", "", "## Pipeline statistics", ""]
    for k, v in sorted(ctx.stats.items()):
        lines.append(f"- `{k}`: {v}")

    unresolved = [g for g in ctx.gaps if g["kind"] == "prereq"]
    lines += ["", "## Prerequisite fragments that could not be resolved", "",
              f"{len(unresolved)} fragments. Extend `swse/prereq.py` rules or add aliases in "
              "`data/curation/aliases.yaml`.", ""]
    counts: dict[str, int] = defaultdict(int)
    for g in unresolved:
        for frag in re.findall(r"\['(.+?)'\]", g["detail"]) or []:
            counts[frag] += 1
        m = re.search(r"unresolved \[(.+)\]$", g["detail"])
        if m:
            for part in m.group(1).split("', '"):
                counts[part.strip("'")] += 1
    for frag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:60]:
        lines.append(f"- {n:>3}x `{frag}`")

    other_gaps = [g for g in ctx.gaps if g["kind"] != "prereq"]
    if other_gaps:
        lines += ["", "## Other gaps detected during canonicalisation", ""]
        for g in other_gaps[:80]:
            lines.append(f"- **{g['kind']}**: {g['detail']}")

    if ctx.dropped:
        lines += ["", "## Dropped rows", "",
                  f"{len(ctx.dropped)} rows were skipped (section labels, placeholders, unnamed rows).", "",
                  "| block | row | reason |", "|---|---:|---|"]
        for d in ctx.dropped[:120]:
            lines.append(f"| `{d['block']}` | {d['row']} | {d['reason']} |")

    out = paths.REPORTS_DIR / "canonicalisation.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
