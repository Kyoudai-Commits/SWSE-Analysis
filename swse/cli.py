"""Command-line interface: every pipeline stage is one command.

    python -m swse.cli doctor          # is the workspace healthy?
    python -m swse.cli extract         # workbooks -> data/raw/*.jsonl
    python -m swse.cli canonicalize    # data/raw -> data/canonical/*.json (+ curation)
    python -m swse.cli validate        # data/reports/validation.md, exit 1 on errors
    python -m swse.cli db              # data/index/swse.sqlite3
    python -m swse.cli graph           # data/reports/prerequisite-graph.md
    python -m swse.cli space           # data/reports/decision-space.md
    python -m swse.cli enumerate       # analysis/out/builds-levelN.jsonl
    python -m swse.cli evaluate        # analysis/out/builds-levelN.md
    python -m swse.cli report          # every analysis report
    python -m swse.cli all             # extract .. report, in order

Run ``python -m swse.cli <stage> --help`` for the flags of one stage. Every stage
prints a one-line summary and, with ``--json``, a machine-readable result so an
agent can chain stages without scraping prose.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import paths


def _emit(result: dict, args) -> None:
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, default=str, sort_keys=True))
    else:
        for key, value in result.items():
            if isinstance(value, (dict, list)) and len(str(value)) > 160:
                print(f"{key}: {type(value).__name__}({len(value)})")
            else:
                print(f"{key}: {value}")


# ---------------------------------------------------------------------------
def cmd_doctor(args) -> int:
    """Check the workspace is complete and consistent before running anything."""
    from .sources import load_registry

    problems, info = [], {}
    paths.ensure_dirs()
    try:
        registry = load_registry()
        info["sources"] = len(registry)
        for s in registry:
            p = s.abs_path
            if not p.exists():
                problems.append(f"missing source workbook: {paths.rel(p)}")
                continue
            ok, detail = s.verify()
            info[f"source:{s.id}"] = (f"{p.stat().st_size:,} bytes, canon={'/'.join(s.canon)}, "
                                      f"sha256 {'ok' if ok else 'MISMATCH'}")
            if not ok:
                problems.append(f"source hash mismatch for {s.id}: {detail}")
    except Exception as exc:                                  # pragma: no cover
        problems.append(f"config/sources.yaml unreadable: {exc}")

    for name in ("blocks.yaml", "entities.yaml", "sourcebooks.yaml", "analysis.yaml"):
        p = paths.CONFIG_DIR / name
        if not p.exists():
            problems.append(f"missing config/{name}")
    for name in ("aliases.yaml", "merges.yaml", "drops.yaml", "overrides.yaml", "gaps.yaml"):
        if not (paths.CURATION_DIR / name).exists():
            problems.append(f"missing data/curation/{name}")
    if not (paths.SCHEMA_DIR / "record.schema.json").exists():
        problems.append("missing schemas/record.schema.json")

    canonical = sorted(paths.CANONICAL_DIR.glob("*.json"))
    info["canonical_files"] = len(canonical)
    if not canonical:
        problems.append("no canonical data yet - run `extract` then `canonicalize`")
    raw = sorted(paths.RAW_DIR.glob("*.jsonl"))
    info["raw_blocks"] = len(raw)
    if not raw:
        problems.append("no extracted rows yet - run `extract`")
    info["sqlite"] = "present" if paths.SQLITE_PATH.exists() else "absent (run `db`)"

    for mod in ("openpyxl", "yaml", "jsonschema"):
        try:
            __import__(mod)
            info[f"dep:{mod}"] = "ok"
        except ImportError:
            problems.append(f"missing dependency: {mod}")

    result = {"ok": not problems, "problems": problems, **info}
    _emit(result, args)
    return 1 if problems else 0


def cmd_extract(args) -> int:
    from .extract import extract_all

    t0 = time.time()
    stats = extract_all(verbose=not args.quiet)
    rows = sum(s["rows"] for s in stats.values())
    result = {"blocks": len(stats), "rows": rows,
              "skipped": sum(s.get("skipped", 0) for s in stats.values()),
              "seconds": round(time.time() - t0, 1),
              "output": paths.rel(paths.RAW_DIR)}
    _emit(result, args)
    return 0


def cmd_canonicalize(args) -> int:
    from . import canon

    t0 = time.time()
    ctx, index = canon.build(verbose=not args.quiet)
    canon.write_canonical(ctx, index)
    report = canon.write_report(ctx, index)
    result = {"records": sum(len(v) for v in ctx.records.values()),
              "entities": len(ctx.records),
              "conflicts": sum(len(r.get("conflicts") or {}) for recs in ctx.records.values() for r in recs),
              "duplicates_collapsed": ctx.stats.get("duplicate_rows_collapsed", 0),
              "name_collisions": sum(1 for recs in ctx.records.values() for r in recs
                                     if "name_collision" in (r.get("flags") or [])),
              "seconds": round(time.time() - t0, 1),
              "report": paths.rel(report), "output": paths.rel(paths.CANONICAL_DIR)}
    _emit(result, args)
    return 0


def cmd_validate(args) -> int:
    from . import validate
    from .store import Dataset

    db = Dataset.load()
    rep = validate.validate(db, strict=args.strict)
    out = validate.write_report(rep)
    result = {"errors": len(rep.errors), "warnings": len(rep.warnings), "infos": len(rep.infos),
              "ok": rep.ok, "report": paths.rel(out)}
    if not args.json:
        for f in (rep.errors + rep.warnings)[: args.show]:
            print(" ", f.as_row())
    _emit(result, args)
    return 0 if rep.ok or not args.strict else 1


def cmd_db(args) -> int:
    from .store import Dataset, build_sqlite

    db = Dataset.load()
    path = build_sqlite(db, verbose=not args.quiet)
    _emit({"sqlite": paths.rel(path), "records": db.total(), "entities": len(db.entities),
           "size_bytes": path.stat().st_size}, args)
    return 0


def cmd_stats(args) -> int:
    """Corpus statistics. ``--entity X`` drills into one entity type."""
    from collections import Counter

    from .store import Dataset

    db = Dataset.load()
    stats = db.stats()
    if args.entity:
        recs = db.all(args.entity)
        info = stats["entities"].get(args.entity, {})
        _emit({"entity": args.entity, "records": len(recs), "canon": info.get("canon", {}),
               "flags": info.get("flags", {}),
               "with_prerequisites": info.get("with_prerequisites", 0),
               "sample": [{"id": r["id"], "name": r["name"], "canon": r.get("canon"),
                           "attrs": r["attrs"]} for r in recs[: args.limit]]}, args)
        return 0
    canon = Counter(r.get("canon") for e in db.entities for r in db.all(e))
    basis = Counter(r["attrs"].get("canon_basis") for e in db.entities for r in db.all(e))
    per_entity = {e: stats["entities"][e]["count"] for e in sorted(stats["entities"],
                                                                   key=lambda x: -stats["entities"][x]["count"])}
    if not args.json:
        print(f"records: {db.total()}  entities: {len(db.entities)}")
        print(f"canon:   {dict(canon.most_common())}")
        print(f"basis:   {dict(basis.most_common())}")
        for e, n in per_entity.items():
            print(f"  {e:<26} {n:>5}")
        return 0
    _emit({"total": db.total(), "entities": len(db.entities),
           "by_canon": dict(canon.most_common()), "by_canon_basis": dict(basis.most_common()),
           "counts": per_entity}, args)
    return 0


def cmd_graph(args) -> int:
    from . import graph as graph_mod
    from .store import Dataset

    db = Dataset.load()
    g = graph_mod.PrereqGraph(db)
    if args.dot:
        out = paths.REPORTS_DIR / "prerequisite-graph.dot"
        out.write_text(g.to_dot(limit=args.limit), encoding="utf-8")
        _emit({"dot": paths.rel(out)}, args)
        return 0
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(g.to_json(), indent=1, default=str), encoding="utf-8")
        _emit({"json": paths.rel(out)}, args)
        return 0
    report = graph_mod.write_report(g)
    _emit({"report": paths.rel(report), **g.stats()}, args)
    return 0


def cmd_space(args) -> int:
    from . import space as space_mod
    from .store import Dataset

    db = Dataset.load()
    sp = space_mod.DecisionSpace(db, level=args.level, include_homebrew=not args.no_homebrew,
                                 canon_filter=args.canon, include_gear=args.gear,
                                 ability_method=args.ability_method)
    out = space_mod.write_report(sp, Path(args.out) if args.out else None)
    counts = sp.count()
    _emit({"report": paths.rel(out), "level": args.level,
           "total_space": f"10^{counts['log10_total_space']}",
           "method": counts["method"],
           "class_paths": counts["paths_at_level"],
           "level1_core_builds": counts["level1"]["core_builds"],
           "dimensions": len(sp.dimensions())}, args)
    return 0


def cmd_enumerate(args) -> int:
    from . import enumerate as enum
    from .store import Dataset

    db = Dataset.load()
    c = enum.Constraints(level=args.level, canon=args.canon,
                         include_homebrew=not args.no_homebrew,
                         ability_method=args.ability_method,
                         force_sensitive=args.force_sensitive,
                         include_gear=args.gear, ignore_prereqs=args.ignore_prereqs,
                         seed=args.seed, limit=args.limit,
                         species=args.species.split(",") if args.species else None,
                         classes=args.classes.split(",") if args.classes else None)
    t0 = time.time()
    if args.exact:
        builds = list(enum.iter_level1_builds(db, c))
        mode = "exact level-1"
    else:
        builds = enum.sample_builds(db, c, n=args.sample)
        mode = f"sampled level-{args.level}"
    out = Path(args.out) if args.out else paths.ANALYSIS_DIR / "out" / f"builds-level{args.level}.jsonl"
    enum.write_builds(builds, out, c)
    violations = sum(len(enum.check_build(db, b)) for b in builds) if args.check else None
    _emit({"mode": mode, "builds": len(builds), "seconds": round(time.time() - t0, 1),
           "output": paths.rel(out), "violations": violations,
           "count": enum.count_builds(db, c)["total_space"] if args.count else None}, args)
    return 0


def cmd_evaluate(args) -> int:
    from . import enumerate as enum
    from .evaluate import Evaluator, rank
    from .report import write_build_digest
    from .store import Dataset

    db = Dataset.load()
    if args.builds:
        src = Path(args.builds)
    else:
        candidates = sorted((paths.ANALYSIS_DIR / "out").glob("builds-level*.jsonl"))
        if not candidates:
            print("no builds found - run `swse enumerate` first", file=sys.stderr)
            return 2
        src = candidates[-1]
    builds = enum.read_builds(src)
    if not builds:
        print(f"no builds in {paths.rel(src)}", file=sys.stderr)
        return 2
    ev = Evaluator(db, weights=json.loads(args.weights) if args.weights else None)
    scores = ev.score_many(builds)
    out = write_build_digest(builds, scores, db=db,
                             out=Path(args.out) if args.out else None)
    top = rank(scores, args.metric)[: args.top]
    if not args.json:
        for i, s in enumerate(top, 1):
            b = s.build
            print(f"{i:3}. {s.metrics[args.metric]:8.2f}  "
                  f"{db.by_id.get(b['species'], {}).get('name', '?'):20} "
                  f"{'/'.join(db.by_id.get(e['class'], {}).get('name', e['class']) for e in b['class_path'])}")
    _emit({"builds": len(builds), "metric": args.metric, "report": paths.rel(out),
           "top": [{"total": s.metrics[args.metric], "species": s.build.get("species"),
                    "classes": [e["class"] for e in s.build.get("class_path", [])]} for s in top]}, args)
    return 0


def cmd_report(args) -> int:
    from .report import write_all
    from .store import Dataset

    db = Dataset.load()
    outs = write_all(db)
    _emit({"reports": [paths.rel(o) for o in outs]}, args)
    return 0


def cmd_audit(args) -> int:
    """Canon-balance audit. Writes analysis/out/canon-balance.md and summarises."""
    from .audit import canon_balance
    from .report import _write
    from .store import Dataset

    db = Dataset.load()
    text = canon_balance(db, top=args.top)
    out = _write(text, Path(args.out) if args.out
                 else paths.ANALYSIS_DIR / "out" / "canon-balance.md")
    differing = text.count("**tiers differ**")
    comparisons = text.count(" vs third_party (n=")
    if args.json:
        _emit({"report": paths.rel(out), "records": db.total(), "comparisons": comparisons,
               "differing_proxies": differing, "uninspected_outliers": text.count("| - |")}, args)
    else:
        print(f"wrote {paths.rel(out)}")
        print(f"  comparisons: {comparisons}, differing at p < 0.01: {differing}")
        if differing:
            print("  mixed-canon rankings should be treated as provisional - see the report")
    return 0


def cmd_all(args) -> int:
    stages = [cmd_extract, cmd_canonicalize, cmd_db, cmd_validate, cmd_graph, cmd_space, cmd_report]
    for stage in stages:
        print(f"\n=== {stage.__name__.replace('cmd_', '')} ===")
        rc = stage(args)
        if rc and not args.keep_going:
            return rc
    return 0


# ---------------------------------------------------------------------------
def _common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", help="suppress progress chatter")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="swse", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # --json/--quiet are accepted both before and after the subcommand, so an
    # agent can write either `swse --json stats` or `swse stats --json`.
    _common_flags(p)
    common = argparse.ArgumentParser(add_help=False)
    _common_flags(common)
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, fn, help_text):
        s = sub.add_parser(name, help=help_text, description=help_text, parents=[common])
        s.set_defaults(func=fn)
        return s

    add("doctor", cmd_doctor, "check workbooks, config, dependencies and generated data")
    add("extract", cmd_extract, "read the source workbooks into data/raw/*.jsonl")
    add("canonicalize", cmd_canonicalize, "merge raw rows into data/canonical/*.json")
    s = add("validate", cmd_validate, "run every consistency check, write data/reports/validation.md")
    s.add_argument("--strict", action="store_true", help="treat warnings as failures")
    s.add_argument("--show", type=int, default=10, help="how many findings to print")

    add("db", cmd_db, "rebuild data/index/swse.sqlite3")
    s = add("stats", cmd_stats, "corpus statistics")
    s.add_argument("--entity", help="report on one entity type")
    s.add_argument("--limit", type=int, default=5)

    s = add("graph", cmd_graph, "prerequisite graph report")
    s.add_argument("--dot", action="store_true", help="write GraphViz DOT instead of Markdown")
    s.add_argument("--json-out", help="write the graph as JSON to this path")
    s.add_argument("--limit", type=int, default=4000)

    s = add("space", cmd_space, "decision-space report")
    s.add_argument("--level", type=int, default=20)
    s.add_argument("--canon", choices=["official", "third_party", "homebrew"])
    s.add_argument("--no-homebrew", action="store_true")
    s.add_argument("--gear", action="store_true", help="include starting-gear combinations")
    s.add_argument("--ability-method", default=None,
                   help="distinct_vectors | standard_array | point_buy")
    s.add_argument("--out", help="write the report elsewhere")

    s = add("enumerate", cmd_enumerate, "produce builds (exact at level 1, sampled above)")
    s.add_argument("--level", type=int, default=1)
    s.add_argument("--sample", type=int, default=100)
    s.add_argument("--exact", action="store_true", help="exact level-1 enumeration (respects --limit)")
    s.add_argument("--limit", type=int, default=None)
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--species", help="comma-separated species names or ids")
    s.add_argument("--classes", help="comma-separated class names or ids")
    s.add_argument("--canon", choices=["official", "third_party", "homebrew"])
    s.add_argument("--no-homebrew", action="store_true")
    s.add_argument("--ability-method", default="standard_array")
    s.add_argument("--force-sensitive", dest="force_sensitive", action="store_true", default=None)
    s.add_argument("--no-force", dest="force_sensitive", action="store_false")
    s.add_argument("--gear", action="store_true")
    s.add_argument("--ignore-prereqs", action="store_true")
    s.add_argument("--check", action="store_true", help="re-validate every produced build")
    s.add_argument("--count", action="store_true", help="also report the analytic space size")
    s.add_argument("--out", help="output JSONL path")

    s = add("evaluate", cmd_evaluate, "score builds and write the digest report")
    s.add_argument("--builds", help="JSONL from `enumerate` (default: newest)")
    s.add_argument("--metric", default="total")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--weights", help="JSON object overriding config/analysis.yaml weights")
    s.add_argument("--out", help="write the digest elsewhere")

    add("report", cmd_report, "write every dataset + analysis report")
    s = add("audit", cmd_audit, "canon-balance audit: are the canon tiers comparable?")
    s.add_argument("--top", type=int, default=8, help="outliers to list per tier (default 8)")
    s.add_argument("--out", help="write the report elsewhere")
    s = add("all", cmd_all, "extract -> canonicalize -> db -> validate -> graph -> space -> report")
    s.add_argument("--keep-going", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths.ensure_dirs()
    try:
        return args.func(args)
    except KeyboardInterrupt:                                  # pragma: no cover
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
