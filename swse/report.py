"""Stage 7: analysis reports.

Everything here is *derived*: each function reads the canonical dataset (and the
prerequisite graph / decision space built from it) and writes a Markdown report a
human or an agent can read. No report contains a number that was not computed
from ``data/canonical/`` or declared in ``config/analysis.yaml``.

Reports land in two places:

``data/reports/``     dataset-level documents that describe the corpus itself
                      (option catalog, canonicalisation, validation, prereq graph)
``analysis/out/``     analysis-level documents that answer a question about
                      character creation (species x class matrix, prestige entry
                      paths, unlock ranking, sampled-build digests)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from . import paths
from .evaluate import Evaluator, Scores, rank
from .graph import PrereqGraph
from .ids import fold, norm_key
from .space import DecisionSpace
from .store import Dataset


def _header(title: str, subtitle: str = "") -> list[str]:
    lines = [f"# {title}", "", f"_Generated {date.today().isoformat()} by `swse.report`._", ""]
    if subtitle:
        lines += [subtitle, ""]
    return lines


def _table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return out


# ---------------------------------------------------------------------------
# 1. option catalog
# ---------------------------------------------------------------------------
def option_catalog(db: Dataset) -> str:
    """Every option in the corpus, grouped by what it is for."""
    lines = _header(
        "Option catalog",
        "What exists to be chosen when building a character, counted from the canonical "
        f"dataset ({db.total():,} records over {len(db.entities)} entity types).",
    )
    stats = db.stats()
    lines += ["## Counts by entity", ""]
    rows = []
    for entity in sorted(db.entities):
        recs = db.all(entity)
        canon = Counter(r.get("canon", "?") for r in recs)
        sources = Counter(s["source"] for r in recs for s in r.get("sources", []))
        with_prereq = sum(1 for r in recs if (r.get("prerequisites") or {}).get("predicates"))
        flagged = Counter(f for r in recs for f in (r.get("flags") or []))
        rows.append([
            f"`{entity}`", len(recs),
            canon.get("official", 0), canon.get("third_party", 0), canon.get("homebrew", 0),
            with_prereq,
            ", ".join(f"{k.replace('swse-', '').replace('-2026-10-08', '')}:{v}" for k, v in sources.most_common()),
            ", ".join(f"`{k}`={v}" for k, v in flagged.most_common(3)) or "-",
        ])
    lines += _table(["entity", "records", "official", "3rd-party", "homebrew",
                     "with prerequisites", "sources", "top flags"], rows)

    lines += ["", "## Character-creation options", "",
              "The entities a player actually picks from, in the order a character sheet fills in:", ""]
    order = [
        ("species", "1. Species"), ("age_category", "1b. Age category (species-dependent modifiers)"),
        ("heroic", "2. Heroic class"), ("background", "3. Background"),
        ("destiny", "4. Destiny"), ("skill", "5. Skills (trained)"),
        ("feat", "6. Feats"), ("talent_tree", "7a. Talent trees (granted by class)"),
        ("talent", "7b. Talents"), ("force_power", "8a. Force powers"),
        ("force_technique", "8b. Force techniques"), ("force_secret", "8c. Force secrets"),
        ("force_regimen", "8d. Force regimens"), ("special_talent", "9. Class-specific special talents"),
        ("lightsaber_form", "9b. Lightsaber forms"),
        ("weapon", "10a. Weapons"), ("armor", "10b. Armor"), ("equipment", "10c. Equipment"),
        ("ammunition", "10d. Ammunition"), ("weapon_mod", "10e. Weapon modifications"),
        ("weapon_accessory", "10f. Weapon accessories"), ("armor_accessory", "10g. Armor accessories"),
        ("cybernetic", "11. Cybernetics"), ("droid_option", "12. Droid options"),
        ("near_human_trait", "13. Near-Human traits"), ("language", "14. Languages"),
        ("class", "Classes (heroic + prestige)"), ("prestige", "Prestige classes"),
    ]
    rows = []
    for entity, label in order:
        if entity in {"heroic", "prestige"}:
            recs = [r for r in db.all("class")
                    if r["attrs"].get("class_kind") == ("heroic" if entity == "heroic" else "prestige")]
        else:
            recs = db.all(entity)
        if not recs:
            continue
        rows.append([label, f"`{entity}`", len(recs),
                     Counter(r.get("canon") for r in recs).most_common(1)[0][0]])
    lines += _table(["decision", "entity", "options", "dominant canon"], rows)

    lines += ["", "## Provenance summary", ""]
    lines += _table(["canon", "records", "share"],
                    [[k, v, f"{v / max(db.total(), 1):.1%}"]
                     for k, v in Counter(r.get("canon") for e in db.entities for r in db.all(e)).most_common()])
    lines += ["", "## Flag histogram", ""]
    flags = Counter(f for e in db.entities for r in db.all(e) for f in (r.get("flags") or []))
    lines += _table(["flag", "records"], [[f"`{k}`", v] for k, v in flags.most_common()])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 2. species x class matrix
# ---------------------------------------------------------------------------
def species_class_matrix(db: Dataset, space: DecisionSpace | None = None) -> str:
    """How many trained-skill selections each (species, heroic class) pair allows.

    This is the first real cross-product of the decision space: the species
    Intelligence modifier changes the class skill budget, so the same class is a
    different number of choices for every species.
    """
    space = space or DecisionSpace(db, level=1)
    lines = _header(
        "Species x heroic class matrix",
        "Cells are the number of distinct trained-skill selections available to that "
        "pair at 1st level (`C(class skill pool, base + INT modifier)`). The INT column is "
        "the species modifier from `species.attrs.mod_int`.",
    )
    classes = space.heroic_classes
    rows = []
    for sp in sorted(space.species, key=lambda r: r["name"].lower()):
        a = sp["attrs"]
        cells = []
        for cls in classes:
            sc = space.class_skill_choices(cls, int(a.get("mod_int") or 0))
            cells.append(f"{sc['combinations']:,}")
        rows.append([sp["name"], a.get("species_kind", "species"), a.get("mod_int") or 0,
                     a.get("size") or "-", *cells])
    lines += _table(["species", "kind", "INT mod", "size", *[c["name"] for c in classes]], rows)

    totals = {c["name"]: 0 for c in classes}
    for sp in space.species:
        for cls in classes:
            totals[cls["name"]] += space.class_skill_choices(cls, int(sp["attrs"].get("mod_int") or 0))["combinations"]
    lines += ["", "## Totals", "",
              f"{len(space.species)} species x {len(classes)} heroic classes = "
              f"{len(space.species) * len(classes):,} pairs, "
              f"{sum(totals.values()):,} trained-skill selections in total.", "",
              "*Note:* droid chassis and beast templates are included in the species count; "
              "droids additionally open the droid-option sub-space, which this matrix does not show."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 3. prestige entry paths
# ---------------------------------------------------------------------------
def prestige_paths(db: Dataset) -> str:
    """For each prestige class: what it takes to get in, and who can get in."""
    g = PrereqGraph(db)
    space = DecisionSpace(db, level=20)
    lines = _header(
        "Prestige class entry paths",
        "Each prestige class is reachable only through a chain of earlier choices. This "
        "report decomposes those chains from the parsed prerequisites, so an agent can see "
        "which heroic classes and which feats/talents/skills feed each prestige option.",
    )
    rows = []
    detail: list[str] = []
    for cls in sorted(space.prestige_classes, key=lambda c: (int(c["attrs"].get("min_level") or 7), c["name"])):
        p = cls.get("prerequisites") or {}
        preds = p.get("predicates") or []
        min_level = int(cls["attrs"].get("min_level") or 7)
        kinds = Counter(x["type"] for x in _walk(preds))
        edges = g.requires(cls["id"])
        resolved = [e for e in edges if e.get("req_id")]
        by_entity = Counter(e["req_entity"] for e in resolved)
        # which heroic classes grant something this prestige class requires?
        feeders = set()
        for e in resolved:
            rid = e["req_id"]
            for c in space.heroic_classes:
                grants = {norm_key(x) for x in (c["attrs"].get("starting_feats") or [])}
                trees = {norm_key(x) for x in (c["attrs"].get("talent_trees") or [])}
                rec = db.by_id.get(rid)
                if not rec:
                    continue
                if norm_key(rec["name"]) in grants or norm_key(rec["name"]) in trees:
                    feeders.add(c["name"])
        rows.append([cls["name"], cls.get("canon"), min_level,
                     ", ".join(f"{k}:{v}" for k, v in kinds.most_common()) or "-",
                     len(resolved), ", ".join(f"{k}:{v}" for k, v in by_entity.most_common()) or "-",
                     ", ".join(sorted(feeders)) or "-"])
        detail.append(f"### {cls['name']}")
        detail.append("")
        detail.append(f"- id: `{cls['id']}`  |  canon: {cls.get('canon')}  |  earliest entry level: **{min_level}**")
        if p.get("raw"):
            detail.append(f"- source text: `{fold(p['raw'])[:400]}`")
        if preds:
            detail.append("- parsed requirements:")
            for pred in preds:
                detail.append(f"    - `{pred['type']}` - {fold(pred.get('text', ''))[:160]}")
        closure = g.closure(cls["id"])
        if closure:
            names = sorted({db.by_id[i]["name"] for i in closure if i in db.by_id})
            detail.append(f"- transitive closure ({len(closure)} options): " + ", ".join(names[:40])
                          + ("..." if len(names) > 40 else ""))
        if p.get("unresolved"):
            detail.append(f"- **unresolved fragments**: {p['unresolved']}")
        detail.append("")
    lines += _table(["prestige class", "canon", "min level", "requirement kinds",
                     "resolved edges", "required entity types", "heroic classes that grant a requirement"], rows)
    lines += ["", "## Requirement detail", ""] + detail
    return "\n".join(lines) + "\n"


def _walk(predicates):
    for pred in predicates:
        yield pred
        for key in ("options", "nested", "of"):
            v = pred.get(key)
            if isinstance(v, dict):
                yield from _walk([v])
            elif isinstance(v, list):
                yield from _walk([i for i in v if isinstance(i, dict)])


# ---------------------------------------------------------------------------
# 4. unlock ranking
# ---------------------------------------------------------------------------
def unlock_ranking(db: Dataset, limit: int = 40) -> str:
    """Which options open the most other options.

    Uses the prerequisite graph in reverse: an option's *unlock set* is everything
    that lists it (transitively) as a requirement. High-unlock options are the
    load-bearing choices in a build; low-unlock options are terminal.
    """
    g = PrereqGraph(db)
    lines = _header(
        "Option unlock ranking",
        "Number of other options that become reachable when a character takes this one "
        "(transitive reverse closure of the prerequisite graph).",
    )
    rows = []
    for rec_id in sorted({e["req_id"] for e in g.edges() if e.get("req_id")}):
        rec = db.by_id.get(rec_id)
        if not rec:
            continue
        rows.append((len(g.unlocks(rec_id)), rec))
    # Deterministic ordering, ties included: set iteration order depends on
    # PYTHONHASHSEED, so slicing a set before sorting made this table change
    # between runs of identical data.
    rows.sort(key=lambda t: (-t[0], t[1]["name"].lower(), t[1]["id"]))
    table_rows = []
    for i, (n, r) in enumerate(rows[:limit], 1):
        names = sorted({db.by_id[u]["name"] for u in g.unlocks(r["id"]) if u in db.by_id})
        table_rows.append([i, r["name"], f"`{r['entity']}`", r.get("canon"), n,
                           ", ".join(names[:6]) or "-"])
    lines += _table(["rank", "option", "entity", "canon", "unlocks", "sample of what it unlocks"],
                    table_rows)
    lines += ["", f"{len(rows)} options are named as a prerequisite by something else; "
                  f"{db.total() - len(rows):,} records are never a prerequisite (terminal options)."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 5. sampled build digest
# ---------------------------------------------------------------------------
def build_digest(builds: list[dict], scores: list[Scores], constraints=None,
                 db: Dataset | None = None) -> str:
    """What a sample of legal builds looks like: distributions and top builds."""
    db = db or Dataset.load()
    lines = _header(
        f"Sampled build digest (level {builds[0]['level'] if builds else '?'})",
        f"{len(builds)} legal builds sampled with constraints "
        f"`{json.dumps(constraints.to_dict(), sort_keys=True) if constraints else 'defaults'}`.",
    )
    if not scores:
        return "\n".join(lines + ["No builds to report.", ""]) + "\n"

    def col(key):
        return sorted(s.metrics.get(key, 0) for s in scores)

    lines += ["## Metric distributions", ""]
    rows = []
    for key in ("total", "bab", "offense", "defense_reflex", "defense_fortitude", "defense_will",
                "durability", "skill_breadth", "versatility", "force_power", "synergy", "redundancy"):
        vals = col(key)
        if not vals:
            continue
        rows.append([f"`{key}`", f"{vals[0]:.1f}", f"{vals[len(vals) // 2]:.1f}",
                     f"{sum(vals) / len(vals):.1f}", f"{vals[-1]:.1f}"])
    lines += _table(["metric", "min", "median", "mean", "max"], rows)

    lines += ["", "## Top builds by weighted total", ""]
    rows = []
    for i, s in enumerate(rank(scores, "total")[:20], 1):
        b = s.build
        rows.append([i, f"{s.metrics['total']:.1f}", db.by_id.get(b["species"], {}).get("name", b["species"]),
                     " > ".join(db.by_id.get(e["class"], {}).get("name", e["class"]) for e in b["class_path"]),
                     len(b.get("feats", [])), len(b.get("talents", [])), len(b.get("trained_skills", [])),
                     f"{s.metrics['offense']:.0f}", f"{s.metrics['defense_reflex']:.0f}",
                     s.parts["durability"]["hp"], f"{s.metrics['synergy']:.0f}"])
    lines += _table(["#", "total", "species", "class path", "feats", "talents", "skills",
                     "offense", "Ref", "HP", "synergy"], rows)

    lines += ["", "## What the sample chose", ""]
    species_c = Counter(db.by_id.get(b["species"], {}).get("name", b["species"]) for b in builds)
    class_c = Counter(db.by_id.get(e["class"], {}).get("name", e["class"]) for b in builds for e in b["class_path"])
    feat_c = Counter(db.by_id.get(f["id"], {}).get("name", f["id"]) for b in builds for f in b.get("feats", []))
    talent_c = Counter(db.by_id.get(t["id"], {}).get("name", t["id"]) for b in builds for t in b.get("talents", []))
    lines += ["### Species", ""] + _table(["species", "count"], species_c.most_common(15))
    lines += ["", "### Class levels taken", ""] + _table(["class", "levels taken"], class_c.most_common(20))
    lines += ["", "### Feats", ""] + _table(["feat", "count"], feat_c.most_common(20))
    lines += ["", "### Talents", ""] + _table(["talent", "count"], talent_c.most_common(20))

    unmet = Counter(u["feat"] for b in builds for u in b.get("unmet_grants", []))
    if unmet:
        lines += ["", "## Class grants the sample could not legally take", "",
                  "A class may grant a feat whose prerequisite the character does not meet "
                  "(e.g. the Scout's Shake It Off needs Constitution 13 and trained Endurance). "
                  "These are recorded per build rather than silently ignored.", ""]
        lines += _table(["granted feat", "times unmet"],
                        [[db.by_id.get(k, {}).get("name", k), v] for k, v in unmet.most_common()])
    warns = Counter(w for s in scores for w in s.warnings)
    if warns:
        lines += ["", "## Evaluation caveats", ""]
        lines += [f"- {w} ({n} builds)" for w, n in warns.most_common()]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 6. data dictionary (generated - never hand-maintained)
# ---------------------------------------------------------------------------
def data_dictionary(db: Dataset) -> str:
    """Every entity, its merge rule, its source blocks and its attribute coverage.

    Generated from the canonical data plus ``config/entities.yaml``, so it cannot
    drift from what is actually stored. An agent reading this file knows which
    fields exist, how often they are populated, and what a value looks like.
    """
    import yaml

    entities_cfg = (yaml.safe_load(paths.ENTITIES_YAML.read_text(encoding="utf-8")) or {}).get("entities", {})
    lines = _header(
        "Data dictionary",
        "Generated from `data/canonical/` and `config/entities.yaml`. Do not edit by hand - "
        "run `python -m swse.cli report`.",
    )
    lines += ["## Record shape", "",
              "Every record in every entity file has this shape:", "",
              "```json",
              json.dumps({
                  "id": "feat_weapon_focus",
                  "entity": "feat",
                  "name": "Weapon Focus",
                  "canon": "official",
                  "attrs": {"...": "entity-specific fields, see below"},
                  "prerequisites": {"raw": "...", "predicates": ["..."], "coverage": 1.0},
                  "relations": {},
                  "sourcebooks": [{"id": "secr", "abbreviation": "SECR", "title": "...", "page": 123}],
                  "sources": [{"source": "sagaforge-1.53", "block": "sf_feats", "sheet": "Data",
                               "row": 12, "ref": "Data!A12:Z12", "canon": "third_party"}],
                  "conflicts": {},
                  "flags": ["parameterised"],
              }, indent=1),
              "```", "",
              "- `canon` is *content* canonicity, and `attrs.canon_basis` says how it was decided "
              "(`sourcebook_citation`, `block_declaration`, `homebrew_section`, `webpage_only_citation`, "
              "`derived_record`).",
              "- `sources` is never empty: every value traces to a workbook cell.",
              "- `conflicts` appears only where two sources disagreed; it records the chosen value, "
              "where it came from, and the alternatives.", "",
              "## Entities", ""]
    rows = []
    for entity in sorted(db.entities):
        cfg = entities_cfg.get(entity, {})
        recs = db.all(entity)
        canon = Counter(r.get("canon") for r in recs)
        rows.append([f"`{entity}`", cfg.get("label", entity), cfg.get("role", "-"), len(recs),
                     cfg.get("merge_on", "name"),
                     "/".join(str(canon.get(k, 0)) for k in ("official", "third_party", "homebrew")),
                     ", ".join(f"`{b}`" if isinstance(b, str) else f"`{b.get('id')}`"
                               for b in (cfg.get("blocks") or []))])
    lines += _table(["entity", "label", "role", "records", "merge_on",
                     "official/3rd/homebrew", "source blocks"], rows)

    lines += ["", "## Attributes by entity", "",
              "`filled` is how many records carry a non-empty value; `sample` is one real value.", ""]
    for entity in sorted(db.entities):
        recs = db.all(entity)
        if not recs:
            continue
        fields: dict[str, list] = {}
        for r in recs:
            for k, v in r["attrs"].items():
                slot = fields.setdefault(k, [0, None, set()])
                if v not in (None, "", [], {}):
                    slot[0] += 1
                    slot[2].add(type(v).__name__)
                    if slot[1] is None:
                        slot[1] = v
        lines += [f"### `{entity}` - {entities_cfg.get(entity, {}).get('label', entity)}", "",
                  f"{len(recs)} records, {len(fields)} distinct attributes.", "",
                  "| attribute | filled | types | sample |", "|---|---:|---|---|"]
        for k in sorted(fields, key=lambda x: (-fields[x][0], x)):
            filled, sample, kinds = fields[k]
            text = json.dumps(sample, ensure_ascii=False, default=str) if not isinstance(sample, str) else sample
            text = text.replace("|", "\\|").replace("\n", " ")
            if len(text) > 90:
                text = text[:87] + "..."
            lines.append(f"| `{k}` | {filled}/{len(recs)} | {', '.join(sorted(kinds))} | {text} |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
def _write(text: str, out: Path | str) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def write_option_catalog(db: Dataset | None = None, out=None) -> Path:
    db = db or Dataset.load()
    return _write(option_catalog(db), out or paths.REPORTS_DIR / "option-catalog.md")


def write_species_class_matrix(db: Dataset | None = None, out=None) -> Path:
    db = db or Dataset.load()
    return _write(species_class_matrix(db), out or paths.ANALYSIS_DIR / "out" / "species-class-matrix.md")


def write_prestige_paths(db: Dataset | None = None, out=None) -> Path:
    db = db or Dataset.load()
    return _write(prestige_paths(db), out or paths.ANALYSIS_DIR / "out" / "prestige-paths.md")


def write_unlock_ranking(db: Dataset | None = None, out=None, limit: int = 40) -> Path:
    db = db or Dataset.load()
    return _write(unlock_ranking(db, limit), out or paths.ANALYSIS_DIR / "out" / "unlock-ranking.md")


def write_build_digest(builds, scores, constraints=None, db: Dataset | None = None, out=None) -> Path:
    db = db or Dataset.load()
    default = paths.ANALYSIS_DIR / "out" / f"builds-level{builds[0]['level'] if builds else 1}.md"
    return _write(build_digest(builds, scores, constraints, db), out or default)


def write_data_dictionary(db: Dataset | None = None, out=None) -> Path:
    db = db or Dataset.load()
    return _write(data_dictionary(db), out or paths.DOCS_DIR / "data-dictionary.md")


def write_all(db: Dataset | None = None) -> list[Path]:
    """Every dataset-level report. Analysis reports are written by the CLI stages."""
    db = db or Dataset.load()
    from . import graph as graph_mod, validate
    out = [
        write_option_catalog(db),
        write_data_dictionary(db),
        write_species_class_matrix(db),
        write_prestige_paths(db),
        write_unlock_ranking(db),
        graph_mod.write_report(PrereqGraph(db)),
        validate.write_report(validate.validate(db)),
    ]
    return out
