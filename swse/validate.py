"""Stage 4: validation. Everything that must be true for the data to be usable.

Run directly (``python -m swse.cli validate``) or from pytest
(``tests/test_data_integrity.py`` asserts there are no ``error`` findings).

Severity
--------
``error``    the data is wrong or the pipeline is broken - `make check` fails
``warning``  the data is usable but something needs a human/agent decision
``info``     a measurement worth tracking over time
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

import yaml

from . import paths
from .ids import norm_key
from .sources import load_registry
from .store import Dataset

SEVERITIES = ("error", "warning", "info")


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    entity: str = ""
    record_id: str = ""
    detail: dict = field(default_factory=dict)

    def as_row(self) -> str:
        where = f"{self.entity}:{self.record_id}" if self.record_id else self.entity
        return f"[{self.severity.upper():<7}] {self.code:<34} {where:<44} {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity, code, message, entity="", record_id="", **detail) -> None:
        self.findings.append(Finding(severity, code, message, entity, record_id, detail))

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def infos(self):
        return [f for f in self.findings if f.severity == "info"]

    @property
    def ok(self) -> bool:
        """True when no error-level finding was raised."""
        return not self.errors

    def to_dicts(self) -> list[dict]:
        return [asdict(f) for f in self.findings]


# ---------------------------------------------------------------------------
def validate(db: Dataset | None = None, strict: bool = False) -> Report:
    rep = Report()
    db = db or Dataset.load()

    _check_sources(rep)
    _check_index_consistency(rep, db)
    _check_record_shape(rep, db)
    _check_ids(rep, db)
    _check_provenance(rep, db)
    _check_prerequisites(rep, db)
    _check_curation(rep, db)
    _check_config(rep)
    _check_coverage(rep, db, strict=strict)
    return rep


def _check_sources(rep: Report) -> None:
    for src in load_registry():
        ok, msg = src.verify()
        if not ok:
            rep.add("error", "source_file", msg, detail={"source": src.id})
        else:
            rep.add("info", "source_file", f"{src.title} verified (sha256 {src.sha256[:12]}...)",
                    detail={"source": src.id})


def _check_index_consistency(rep: Report, db: Dataset) -> None:
    idx = db.meta.get("_index")
    if not idx:
        rep.add("error", "index_missing", "data/canonical/index.json is missing")
        return
    for entity, meta in idx.get("entities", {}).items():
        actual = db.count(entity)
        if actual != meta.get("count"):
            rep.add("error", "index_count_mismatch",
                    f"index says {meta.get('count')} but {entity}.json holds {actual}", entity=entity)
    for entity in db.entities:
        if entity not in idx.get("entities", {}):
            rep.add("error", "index_entity_missing", f"{entity}.json is not listed in index.json", entity=entity)
    rep.add("info", "index_consistency", f"{len(idx.get('entities', {}))} entities indexed, {db.total()} records")


def _check_record_shape(rep: Report, db: Dataset) -> None:
    """Every record must match ``schemas/record.schema.json``."""
    schema_file = paths.SCHEMA_DIR / "record.schema.json"
    if not schema_file.exists():
        rep.add("error", "schema_missing", "schemas/record.schema.json is missing")
        return
    try:
        import jsonschema
    except ImportError:
        rep.add("warning", "jsonschema_unavailable",
                "jsonschema is not installed; record shape validation skipped (pip install jsonschema)")
        return
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    bad = 0
    for entity, recs in db.records.items():
        for rec in recs:
            errs = sorted(validator.iter_errors(rec), key=lambda e: e.path)
            if errs:
                bad += 1
                if bad <= 25:
                    first = errs[0]
                    rep.add("error", "schema_violation",
                            f"{'/'.join(str(p) for p in first.path) or '<root>'}: {first.message[:160]}",
                            entity=entity, record_id=rec.get("id", "?"))
    if bad > 25:
        rep.add("error", "schema_violation", f"{bad - 25} further schema violations not shown")
    if bad == 0:
        rep.add("info", "schema_violation", f"all {db.total()} records match schemas/record.schema.json")


def _check_ids(rep: Report, db: Dataset) -> None:
    seen: dict[str, str] = {}
    for entity, recs in db.records.items():
        local: set[str] = set()
        for rec in recs:
            rid = rec["id"]
            if not rid:
                rep.add("error", "missing_id", "record has no id", entity=entity)
                continue
            if not rid.startswith(f"{entity}_"):
                rep.add("error", "id_prefix", f"id {rid!r} does not start with {entity}_", entity=entity, record_id=rid)
            if rid in local:
                rep.add("error", "duplicate_id", f"duplicate id inside {entity}", entity=entity, record_id=rid)
            local.add(rid)
            if rid in seen and seen[rid] != entity:
                rep.add("error", "cross_entity_id_collision",
                        f"id also used by entity {seen[rid]}", entity=entity, record_id=rid)
            seen[rid] = entity
            if not rec.get("name"):
                rep.add("error", "missing_name", "record has no name", entity=entity, record_id=rid)
    rep.add("info", "id_uniqueness", f"{len(seen)} unique ids across {len(db.entities)} entities")


def _check_provenance(rep: Report, db: Dataset) -> None:
    known_sources = {s.id for s in load_registry()}
    missing = 0
    unknown = 0
    for entity, recs in db.records.items():
        for rec in recs:
            srcs = rec.get("sources") or []
            if not srcs:
                missing += 1
                if missing <= 10:
                    rep.add("error", "no_provenance", "record has no source row", entity=entity, record_id=rec["id"])
                continue
            for s in srcs:
                if s.get("source") not in known_sources:
                    unknown += 1
                    if unknown <= 10:
                        rep.add("error", "unknown_source_id",
                                f"source {s.get('source')!r} is not in config/sources.yaml",
                                entity=entity, record_id=rec["id"])
                if s.get("row") is None:
                    rep.add("warning", "provenance_row_missing",
                            "source entry has no row number", entity=entity, record_id=rec["id"])
    if missing > 10:
        rep.add("error", "no_provenance", f"{missing - 10} further records without provenance")
    if missing == 0 and unknown == 0:
        rep.add("info", "provenance_complete", "every record traces to a source workbook row")


def _check_prerequisites(rep: Report, db: Dataset) -> None:
    from .graph import PrereqGraph

    graph = PrereqGraph(db)
    stats = graph.stats()
    rep.add("info", "prereq_edges",
            f"{stats['edges']} edges, {stats['resolved_edges']} resolved, {stats['dangling_edges']} dangling")

    cycles = graph.cycles()
    if cycles:
        for comp in cycles[:10]:
            rep.add("error", "prereq_cycle", "circular prerequisite: " + " -> ".join(comp),
                    detail={"component": comp})
    else:
        rep.add("info", "prereq_acyclic", "no circular prerequisites")

    dangling = graph.dangling()
    if dangling:
        buckets: dict[str, int] = {}
        for e in dangling:
            buckets[e["req_type"]] = buckets.get(e["req_type"], 0) + 1
        rep.add("warning", "prereq_dangling",
                f"{len(dangling)} requirement(s) name an option that is not in the canonical data: "
                + ", ".join(f"{k}={v}" for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])),
                detail={"examples": [{"src": e["src_id"], "type": e["req_type"], "key": e.get("req_key")}
                                     for e in dangling[:10]]})

    # unparseable prerequisite text
    total_preds = unresolved = 0
    worst: list[tuple[str, str]] = []
    for entity, recs in db.records.items():
        for rec in recs:
            p = rec.get("prerequisites")
            if not p:
                continue
            stack = list(p.get("predicates") or [])
            while stack:
                q = stack.pop()
                for k in ("options", "nested", "of"):
                    v = q.get(k)
                    if isinstance(v, dict):
                        stack.append(v)
                    elif isinstance(v, list):
                        stack.extend(i for i in v if isinstance(i, dict))
                total_preds += 1
                if q.get("type") == "other":
                    unresolved += 1
                    if len(worst) < 10:
                        worst.append((rec["id"], q.get("text", "")[:80]))
    if total_preds:
        share = round(unresolved / total_preds, 4)
        sev = "warning" if share > 0.05 else "info"
        rep.add(sev, "prereq_parse_coverage",
                f"{total_preds - unresolved}/{total_preds} prerequisite predicates parsed "
                f"({100 * (1 - share):.2f}%); {unresolved} unresolved",
                detail={"examples": worst})

    collisions = sum(1 for _e, r in db.by_flag("name_collision"))
    if collisions:
        rep.add("warning", "name_collision",
                f"{collisions} records share a name with another record from the same source and were "
                f"kept separate; review and declare merges in data/curation/merges.yaml")


def _check_curation(rep: Report, db: Dataset) -> None:
    if not paths.CURATION_DIR.exists():
        return
    overrides = yaml.safe_load((paths.CURATION_DIR / "overrides.yaml").read_text(encoding="utf-8")) or {}
    for entity, mapping in (overrides.get("overrides") or {}).items():
        for rec_id, patch in (mapping or {}).items():
            if db.get(entity, rec_id) is None:
                rep.add("error", "curation_target_missing",
                        f"override targets {entity}:{rec_id}, which does not exist", entity=entity, record_id=rec_id)
            if not (patch or {}).get("note"):
                rep.add("error", "curation_override_unjustified",
                        "override has no `note` explaining the correction", entity=entity, record_id=rec_id)
    merges = yaml.safe_load((paths.CURATION_DIR / "merges.yaml").read_text(encoding="utf-8")) or {}
    for entity, groups in (merges.get("merges") or {}).items():
        for group in groups or []:
            for rec_id in group:
                if db.get(entity, rec_id) is None and not any(r["name"] == rec_id for r in db.all(entity)):
                    rep.add("warning", "curation_merge_target_missing",
                            f"merge references {entity}:{rec_id}, which does not exist",
                            entity=entity, record_id=rec_id)
    gaps_file = paths.CURATION_DIR / "gaps.yaml"
    if gaps_file.exists():
        gaps = yaml.safe_load(gaps_file.read_text(encoding="utf-8")) or {}
        for gap in gaps.get("gaps") or []:
            for required in ("id", "entity", "summary", "status"):
                if not gap.get(required):
                    rep.add("error", "curation_gap_incomplete",
                            f"gap entry {gap.get('id', '?')} is missing `{required}`")


def _check_config(rep: Report) -> None:
    from .blocks import load_blocks

    blocks = load_blocks()
    entities_cfg = yaml.safe_load(paths.ENTITIES_YAML.read_text(encoding="utf-8")) or {}
    declared = {e for e in (entities_cfg.get("entities") or {})}
    used_blocks = {b["id"] for e in (entities_cfg.get("entities") or {}).values() for b in e.get("blocks", [])}
    for b in blocks:
        if b.id not in used_blocks:
            rep.add("warning", "block_unused",
                    f"block {b.id} is extracted but not consumed by any entity", detail={"block": b.id})
    for e in declared:
        if not entities_cfg["entities"][e].get("blocks"):
            rep.add("warning", "entity_without_blocks", f"entity {e} declares no source blocks", entity=e)
    sb_doc = yaml.safe_load(paths.SOURCEBOOKS_YAML.read_text(encoding="utf-8")) or {}
    ids = {s["id"] for s in sb_doc.get("sourcebooks", [])}
    if not ids:
        rep.add("error", "sourcebooks_empty", "config/sourcebooks.yaml declares no sourcebooks")
    else:
        rep.add("info", "sourcebooks_loaded", f"{len(ids)} sourcebooks registered")


def _check_coverage(rep: Report, db: Dataset, strict: bool = False) -> None:
    """Entity-level sanity: empty entities, missing key attributes."""
    for entity, recs in db.records.items():
        if not recs:
            rep.add("error" if strict else "warning", "entity_empty",
                    f"{entity}.json contains no records", entity=entity)
    expectations = {
        "species": ("size", "speed"),
        "class": ("class_kind",),
        "feat": (),
        "weapon": ("weapon_group",),
        "armor": ("type",),
        "talent": ("tree",),
    }
    for entity, fields in expectations.items():
        recs = db.all(entity)
        if not recs:
            continue
        for f in fields:
            filled = sum(1 for r in recs if r["attrs"].get(f) not in (None, "", []))
            share = filled / len(recs)
            if share < 0.5:
                rep.add("warning", "attribute_sparse",
                        f"{entity}.{f} is populated on only {filled}/{len(recs)} records ({share:.0%})",
                        entity=entity, detail={"field": f, "filled": filled, "total": len(recs)})
            else:
                rep.add("info", "attribute_coverage",
                        f"{entity}.{f}: {filled}/{len(recs)} ({share:.0%})", entity=entity)


def write_report(rep: Report, out_path=None) -> str:
    lines = ["# Data validation report", ""]
    lines += [f"- errors: **{len(rep.errors)}**", f"- warnings: **{len(rep.warnings)}**",
              f"- info: {len(rep.infos)}", "",
              "| severity | code | where | message |", "|---|---|---|---|"]
    for f in sorted(rep.findings, key=lambda x: (SEVERITIES.index(x.severity), x.code, x.entity)):
        where = f"{f.entity}:{f.record_id}" if f.record_id else (f.entity or "-")
        lines.append(f"| {f.severity} | `{f.code}` | `{where}` | {f.message} |")
    text = "\n".join(lines) + "\n"
    out = out_path or (paths.REPORTS_DIR / "validation.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return str(out)
