"""Stage 7: canon-balance audit.

The corpus mixes official rules text with third-party builder content and a little
homebrew. Everything is tagged, but tagging only helps if someone checks whether the
tiers are *comparable*. If builder-only options systematically grant bigger numbers
than published ones, then every mixed-canon ranking is quietly dominated by content
the printed game never published - and the honest response is to publish official-only
rankings instead.

This module answers that question with distributions rather than anecdotes:

* a **power proxy** per record, computed from the canonical data (weapon damage,
  armour bonuses, species ability modifiers, weapon-mod bonuses, and bonus signatures
  parsed out of rules text);
* per-tier **distribution statistics** (n, median, IQR, max) for each proxy;
* a **Mann-Whitney U** rank-sum comparison between the official and third-party tiers
  (normal approximation with tie correction - no scipy dependency);
* the **outliers** in each tier's top decile, with the source cell that produced them,
  so each can be inspected against the workbook;
* **data-quality findings** - numeric attributes whose names are not field names,
  which indicate extraction artefacts rather than game data.

Nothing here edits data. A suspicious record becomes either a fix in ``swse/hooks.py``
plus a regression test, or an entry in ``data/curation/gaps.yaml``; verdicts from
hand-inspection are recorded in ``data/curation/audit-verdicts.yaml`` so the report
can carry them.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from . import paths
from .evaluate import Evaluator
from .ids import fold
from .store import Dataset

# entity -> (measure name, accessor) for numeric proxies that live in attrs
NUMERIC_PROXIES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "armor": [("armor_bonus", ("ref_bonus", "fort_bonus"))],
    "weapon_mod": [("mod_bonus", ("attack_mod", "damage_mod", "damage_dice_mod"))],
    "species": [("ability_bonus", ("mod_str", "mod_dex", "mod_con", "mod_int", "mod_wis", "mod_cha"))],
}

#: Decision slots worth comparing directly (TASK-020), as
#: ``(slot label, entity, measure, why it matters)``.
#:
#: The generic proxies above answer "which measures can be compared at all?" - the
#: answer is 2 of 20, because canon tier and entity type nearly coincide. These are the
#: slots where a reader's actual question can be asked: *within one decision a player
#: makes, do the tiers differ?* Slots are listed even when one tier is too small to test,
#: so the report shows the reader where power is missing instead of hiding it.
SLOT_COMPARISONS: tuple[tuple[str, str, str, str], ...] = (
    ("Talent tree", "talent_tree", "talents_per_tree",
     "the 25 builder-only trees are the largest block of third-party character content"),
    ("Species", "species", "ability_bonus",
     "every level-1 build picks a species, so this is the most-used decision in the corpus"),
    ("Species", "species", "ability_penalty",
     "a tier that only grants and never charges would show up here and nowhere else"),
    ("Equipment", "equipment", "price",
     "the only slot with real overlap in both tiers; price is the game's own balance signal"),
    ("Weapon", "weapon", "avg_damage",
     "damage is exactly comparable and is what `offense` actually reads"),
    ("Weapon", "weapon", "price",
     "damage per credit: a tier that is cheaper for the same damage is inflated"),
    ("Armor", "armor", "armor_bonus",
     "reported, never tested - 4 third-party records cannot support a p-value"),
)

# entities whose power has to be read out of their rules text
TEXT_ENTITIES = ("feat", "talent", "racial_ability", "force_power", "force_technique",
                 "force_secret", "class_feature", "droid_option", "special_talent",
                 "unleashed_ability", "near_human_trait", "cybernetic")

# fields that hold rules text, in the order they should be concatenated
TEXT_FIELDS = ("benefit", "effect", "description", "text", "rules_text", "special",
               "improvements", "notes", "ability_text", "power_text")

TIERS = ("official", "third_party", "homebrew")

#: Placeholder used in the sourcebook control when a record cites no sourcebook at
#: all - talent trees, which are derived from talent rows, are the common case. It is
#: deliberately not a valid abbreviation so it can never be mistaken for a real book.
UNCITED = "(uncited)"

#: Both tiers need at least this many records before a rank-sum p-value means
#: anything. Below it the test reports "insufficient overlap" instead of a number:
#: p=0.03 computed from 5 records in one tier is noise dressed as a finding.
MIN_COMPARABLE_N = 8

#: Build-level audit settings. Seeded so the report is reproducible.
BUILD_LEVELS = (1, 10)
BUILD_SAMPLE = 300
BUILD_SEED = 20261008


# ---------------------------------------------------------------------------
# statistics (no scipy: everything here is standard and testable)
# ---------------------------------------------------------------------------
def quantile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear-interpolated quantile of an already-sorted sequence."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo))


def describe(values: Iterable[float]) -> dict:
    """n / median / IQR / max / mean - medians, because these distributions skew."""
    v = sorted(float(x) for x in values)
    if not v:
        return {"n": 0, "median": None, "p25": None, "p75": None, "max": None, "mean": None}
    return {
        "n": len(v),
        "median": round(quantile(v, 0.5), 3),
        "p25": round(quantile(v, 0.25), 3),
        "p75": round(quantile(v, 0.75), 3),
        "max": round(v[-1], 3),
        "mean": round(sum(v) / len(v), 3),
    }


def mann_whitney_u(a: Sequence[float], b: Sequence[float]) -> dict:
    """Two-sided Mann-Whitney U with normal approximation and tie correction.

    Returns ``U`` (the smaller of U1/U2), ``z``, and ``p``. ``p`` is an
    approximation - it is used to say "these tiers differ" or "no evidence they
    differ", never as a precise significance claim, and the report says so.
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return {"U": None, "z": None, "p": None, "n1": n1, "n2": n2}
    combined = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks: list[float] = []
    tie_groups: list[int] = []
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2 + 1          # average rank of this tie group (1-based)
        ranks.extend([avg] * (j - i + 1))
        tie_groups.append(j - i + 1)
        i = j + 1
    r1 = sum(r for r, (_, grp) in zip(ranks, combined) if grp == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    n = n1 + n2
    tie_term = sum(t ** 3 - t for t in tie_groups if t > 1) / (n * (n - 1)) if n > 1 else 0.0
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term))
    if sigma == 0:
        return {"U": u, "z": None, "p": None, "n1": n1, "n2": n2}
    z = (abs(u - n1 * n2 / 2) - 0.5) / sigma      # continuity correction
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"U": round(u, 1), "z": round(z, 3), "p": round(p, 5), "n1": n1, "n2": n2}


# ---------------------------------------------------------------------------
# power proxies
# ---------------------------------------------------------------------------
def _num(rec: dict, field: str) -> float:
    v = (rec.get("attrs") or {}).get(field)
    if isinstance(v, bool) or v in (None, ""):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def numeric_proxy(rec: dict, fields: Sequence[str]) -> float:
    """Sum of numeric attribute fields. Missing fields count as 0, not as absent."""
    return round(sum(_num(rec, f) for f in fields), 3)


def positive_ability_bonus(rec: dict, fields: Sequence[str]) -> float:
    """Sum of *positive* ability modifiers.

    A species with +2 DEX / -2 CON is not weaker than one with +0/+0; netting the
    two would say so. Only gains are counted here, and the report also lists the
    penalties separately so a reader can see both.
    """
    return round(sum(max(0.0, _num(rec, f)) for f in fields), 3)


def text_proxy(ev: Evaluator, rec: dict) -> dict:
    """Bonus signatures parsed out of a record's rules text.

    ``bonus_sum`` is the total of positive bonus amounts, ``bonus_max`` the single
    largest, ``bonus_count`` how many distinct (type, target) signatures appear.
    This is a proxy for power, not power itself: a +2 competence bonus to attack is
    worth more than a +2 bonus to a niche skill check, and the parser cannot tell.
    """
    attrs = rec.get("attrs") or {}
    text = "\n".join(str(attrs[f]) for f in TEXT_FIELDS if attrs.get(f))
    sigs = ev.bonuses_in(text)
    positives = [amt for _t, _tgt, amt in sigs if amt > 0]
    return {
        "bonus_sum": float(sum(positives)),
        "bonus_max": float(max(positives)) if positives else 0.0,
        "bonus_count": float(len({(t, tgt) for t, tgt, _a in sigs})),
    }


#: Builder rows that combine or parameterise options which each exist on their own
#: (GAP-014 / TASK-019). They are real records with real cell citations, but a
#: distribution over them measures the builder's UI rather than the options, so the
#: per-tier comparisons exclude them.
BUILDER_ARTEFACT_FLAGS = frozenset({"builder_combination", "builder_parameter_variant"})


def distinct_options(db: Dataset, entity: str) -> list[dict]:
    """Records of ``entity`` that are separate choices, not builder combinations."""
    return [r for r in db.all(entity)
            if not (BUILDER_ARTEFACT_FLAGS & set(r.get("flags") or ()))]


def measure_records(db: Dataset, ev: Evaluator) -> dict[str, dict[str, list[tuple[dict, float]]]]:
    """entity -> measure -> [(record, value)] for every proxy this audit computes."""
    out: dict[str, dict[str, list[tuple[dict, float]]]] = defaultdict(dict)

    # weapons: average damage, the only numeric power a weapon carries
    vals = []
    for w in db.all("weapon"):
        dmg = (w.get("attrs") or {}).get("damage")
        if dmg in (None, "", [], {}):
            continue
        vals.append((w, round(ev.damage_value(dmg), 3)))
    out["weapon"]["avg_damage"] = vals

    # armour / mods / species: numeric attrs
    for entity, proxies in NUMERIC_PROXIES.items():
        for measure, fields in proxies:
            fn = positive_ability_bonus if entity == "species" else numeric_proxy
            out[entity][measure] = [(r, fn(r, fields)) for r in distinct_options(db, entity)]
    if "species" in out:
        out["species"]["ability_penalty"] = [
            (r, round(-sum(min(0.0, _num(r, f)) for f in NUMERIC_PROXIES["species"][0][1]), 3))
            for r in db.all("species")
        ]

    # slot comparisons (TASK-020): measures that exist for both tiers in one decision
    out["talent_tree"]["talents_per_tree"] = [
        (t, float(len(t["attrs"].get("talents") or [])))
        for t in db.all("talent_tree")
    ]
    for entity in ("equipment", "weapon"):
        out[entity]["price"] = [(r, _num(r, "price")) for r in db.all(entity)]

    # text-bearing entities: bonus signatures
    for entity in TEXT_ENTITIES:
        recs = distinct_options(db, entity)
        if not recs:
            continue
        by_measure: dict[str, list[tuple[dict, float]]] = {"bonus_sum": [], "bonus_max": [], "bonus_count": []}
        for r in recs:
            p = text_proxy(ev, r)
            for k, v in p.items():
                by_measure[k].append((r, v))
        # keep only measures that actually fire for this entity
        for k, v in by_measure.items():
            if any(val > 0 for _r, val in v):
                out[entity][k] = v
    return out


def suspicious_numeric_attrs(db: Dataset) -> list[tuple[str, str, int]]:
    """Numeric attributes whose *name* is not a field name.

    ``droid_option`` records carry keys like ``"5"``, ``"6"`` and ``"9"`` - these are
    unnamed spreadsheet columns picked up during extraction. They are not game data,
    and any proxy computed from them would be meaningless. Reporting them is the
    point: an audit that silently averaged them would be worse than no audit.
    """
    found: dict[tuple[str, str], int] = defaultdict(int)
    for entity in db.entities:
        for rec in db.all(entity):
            for k, v in (rec.get("attrs") or {}).items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and fold(k).strip().isdigit():
                    found[(entity, k)] += 1
    return sorted(((e, k, n) for (e, k), n in found.items()), key=lambda t: (-t[2], t[0], t[1]))


# ---------------------------------------------------------------------------
# build-level audit
# ---------------------------------------------------------------------------
def _build_options(db: Dataset, build: dict) -> list[str]:
    """Every option id a build commits to, in a stable order."""
    ids = []
    if build.get("species"):
        ids.append(build["species"])
    ids += [e["class"] for e in build.get("class_path", []) if e.get("class")]
    ids += [f["id"] for f in build.get("feats", []) if f.get("id")]
    ids += [t["id"] for t in build.get("talents", []) if t.get("id")]
    ids += list(build.get("force_powers", []) or [])
    return ids


def non_official_options(db: Dataset, build: dict) -> list[tuple[str, str]]:
    """``(id, canon)`` for every option in a build that is not official content."""
    out = []
    for rid in _build_options(db, build):
        rec = db.by_id.get(rid)
        if rec and rec.get("canon") != "official":
            out.append((rid, rec["canon"]))
    return out


def build_level_audit(db: Dataset, ev: Evaluator, level: int, n: int = BUILD_SAMPLE,
                      seed: int = BUILD_SEED, include_homebrew: bool = True) -> dict:
    """Do builds that use third-party content outscore official-only builds?

    The record-level comparison above is confounded: canon tier and entity type
    nearly coincide, so most entity types have almost nothing to compare. Builds are
    different - there are plenty of them, and every one is scored on the same scale,
    so the question "does opening the corpus to third-party content inflate the top
    of the ranking?" becomes answerable with real statistical power.

    Builds are split **three** ways, not two. The homebrew classes (Technician, Force
    Prodigy) have no hit die, BAB rate or defence numbers in either source, so any
    build using them is scored as if those levels contributed nothing. Putting them in
    the same bucket as third-party content measures a data gap (GAP-013) and reports it
    as a balance finding - which is exactly the mistake this audit exists to avoid. At
    level 10 almost every sampled path touches one of them, so the confound is total.
    """
    from collections import Counter

    from .enumerate import Constraints, sample_builds

    builds = sample_builds(db, Constraints(level=level, seed=seed,
                                           include_homebrew=include_homebrew), n)
    scores = ev.score_many(builds)
    groups = {"official_only": [], "third_party_only": [], "homebrew_tainted": []}
    offenders: Counter = Counter()
    mixed_examples = []
    classification: list[str] = []
    for s in scores:
        bad = non_official_options(db, s.build)
        total = s.metrics.get("total", 0.0)
        if any(canon == "homebrew" for _rid, canon in bad):
            key = "homebrew_tainted"
        elif bad:
            key = "third_party_only"
        else:
            key = "official_only"
        groups[key].append(total)
        classification.append(key)
        for rid, _canon in bad:
            offenders[rid] += 1
        if bad and len(mixed_examples) < 5:
            mixed_examples.append({
                "total": total, "group": key,
                "species": (db.by_id.get(s.build.get("species")) or {}).get("name"),
                "classes": "/".join((db.by_id.get(e["class"]) or {}).get("name", "?")
                                    for e in s.build.get("class_path", [])),
                "non_official": sorted({f"{(db.by_id.get(rid) or {}).get('name', rid)} ({canon})"
                                        for rid, canon in bad}),
            })

    ordered = sorted((s.metrics.get("total", 0.0) for s in scores), reverse=True)
    cut = max(1, math.ceil(len(ordered) * 0.1))
    top_threshold = ordered[cut - 1] if ordered else 0.0
    in_top = [c for s, c in zip(scores, classification) if s.metrics.get("total", 0.0) >= top_threshold]
    return {
        "level": level, "sampled": len(scores), "seed": seed,
        "stats_official": describe(groups["official_only"]),
        "stats_third_party": describe(groups["third_party_only"]),
        "stats_homebrew": describe(groups["homebrew_tainted"]),
        "n_official": len(groups["official_only"]),
        "n_third_party": len(groups["third_party_only"]),
        "n_homebrew": len(groups["homebrew_tainted"]),
        # the balance comparison: official-only vs third-party-only, homebrew excluded
        "mw": mann_whitney_u(groups["official_only"], groups["third_party_only"]),
        "top_decile_size": cut,
        "top_decile_third_party": in_top.count("third_party_only"),
        "top_decile_homebrew": in_top.count("homebrew_tainted"),
        "top_decile_threshold": round(top_threshold, 3),
        "most_used_non_official": [(rid, c, (db.by_id.get(rid) or {}).get("name", rid))
                                   for rid, c in offenders.most_common(8)],
        "mixed_examples": sorted(mixed_examples, key=lambda ex: -ex["total"])[:5],
    }


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------
def _verdicts() -> dict[str, dict]:
    """Hand-inspection verdicts, curated so they survive regeneration."""
    import yaml

    path = paths.CURATION_DIR / "audit-verdicts.yaml"
    if not path.exists():
        return {}
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("verdicts", {}) or {}


def _source_ref(rec: dict) -> str:
    srcs = rec.get("sources") or []
    if not srcs:
        return "-"
    s = srcs[0]
    return f"{s.get('sheet', '?')}!r{s.get('row', '?')}"


def _fmt(x: Any) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:g}"
    return str(x)


def _p(p: float | None) -> str:
    """A p-value to three decimals.

    Not ``_fmt``: `%g` prints six significant digits, and `p=0.47282` implies a
    precision that a 25-record sample cannot support. Three decimals is the least
    that still separates 0.010 from 0.001 at the ``alpha`` this audit uses.
    """
    return "-" if p is None else f"{p:.3f}"


def canon_balance(db: Dataset, top: int = 8, alpha: float = 0.01,
                  include_builds: bool = True) -> str:
    """Markdown audit of metric distributions across canon tiers.

    ``include_builds=False`` skips the build-level sampling (two 300-build samples per
    level, ~25s each) and reports only the record-level half. Tests use it; the CLI
    does not.
    """
    from .graph import PrereqGraph
    from .report import _header, _table

    ev = Evaluator(db)
    ev._graph = PrereqGraph(db)
    measured = measure_records(db, ev)
    verdicts = _verdicts()

    lines = _header(
        "Canon balance audit",
        "Do the canon tiers grant comparable numbers? Distributions per power proxy, "
        "a rank-sum comparison between the official and third-party tiers, and every "
        "top-decile outlier with the cell it came from. Generated by "
        "`python -m swse.cli report`; hand-inspection verdicts live in "
        "`data/curation/audit-verdicts.yaml`.",
    )

    # ---- tier sizes, cross-checked against the dataset itself --------------
    tier_counts = {t: sum(1 for e in db.entities for r in db.all(e) if r.get("canon") == t) for t in TIERS}
    lines += ["## Corpus by tier", ""]
    lines += _table(["canon tier", "records"], [[f"`{t}`", tier_counts[t]] for t in TIERS])
    lines += ["", "## Composition: tier is confounded with entity type", "",
              "This is the single most important fact in the audit, and it constrains "
              "every comparison below. Canon tier and entity type nearly coincide: "
              "racial abilities, weapon mods, skills, destinies, backgrounds, languages "
              "and droid options are *entirely* third-party, while Force powers, "
              "techniques and secrets are *entirely* official. Only a handful of entity "
              "types carry both tiers at all.", "",
              "So \"do the tiers grant comparable numbers?\" cannot be answered by pooling "
              "records - a pooled comparison would measure corpus composition, not balance. "
              "It can only be asked *within* an entity type, and only where both tiers have "
              f"at least {MIN_COMPARABLE_N} records.", ""]
    composition = []
    for e in sorted(db.entities):
        c = {t: 0 for t in TIERS}
        for r in db.all(e):
            c[r.get("canon", "third_party")] = c.get(r.get("canon", "third_party"), 0) + 1
        composition.append((e, c))
    both = [(e, c) for e, c in composition if c["official"] and c["third_party"]]
    single = [(e, c) for e, c in composition if not (c["official"] and c["third_party"])]
    lines += [f"{len(both)} of {len(composition)} entity types carry both official and "
              "third-party records:", ""]
    lines += _table(["entity", "official", "third_party", "homebrew", "comparable?"],
                    [[f"`{e}`", c["official"], c["third_party"], c["homebrew"],
                      "yes" if min(c["official"], c["third_party"]) >= MIN_COMPARABLE_N else "no"]
                     for e, c in sorted(both, key=lambda t: -min(t[1]["official"], t[1]["third_party"]))])
    lines += ["", "Single-tier entity types (no within-entity comparison is possible):", "",
              ", ".join(f"`{e}` ({'official' if c['official'] else 'third_party' if c['third_party'] else 'homebrew'})"
                        for e, c in single) or "-", ""]

    # ---- distributions -----------------------------------------------------
    lines += ["## Power proxies by tier", "",
              "Each proxy is computed from canonical data only. `n` is how many records "
              "in that tier carry a non-zero value; medians and IQR are reported because "
              "these distributions are skewed.", ""]
    comparisons = []
    skipped = 0
    for entity in sorted(measured):
        for measure in sorted(measured[entity]):
            pairs = measured[entity][measure]
            by_tier = {t: [v for r, v in pairs if r.get("canon") == t and v > 0] for t in TIERS}
            if not any(by_tier.values()):
                continue
            lines += [f"### `{entity}` - {measure}", ""]
            lines += _table(["tier", "n", "median", "p25", "p75", "max", "mean"],
                            [[f"`{t}`", d["n"], _fmt(d["median"]), _fmt(d["p25"]), _fmt(d["p75"]),
                              _fmt(d["max"]), _fmt(d["mean"])]
                             for t in TIERS for d in [describe(by_tier[t])] if d["n"]])
            n_off, n_tp = len(by_tier["official"]), len(by_tier["third_party"])
            if min(n_off, n_tp) < MIN_COMPARABLE_N:
                skipped += 1
                lines += ["", f"insufficient overlap to compare (official n={n_off}, "
                              f"third_party n={n_tp}, needs {MIN_COMPARABLE_N} in each tier)", ""]
                continue
            mw = mann_whitney_u(by_tier["official"], by_tier["third_party"])
            if mw["p"] is not None:
                verdict = ("**tiers differ**" if mw["p"] < alpha else "no evidence of a difference")
                higher = None
                if mw["p"] < alpha:
                    med_o, med_t = describe(by_tier["official"])["median"], describe(by_tier["third_party"])["median"]
                    higher = "third_party" if (med_t or 0) > (med_o or 0) else "official"
                lines += ["", f"official (n={mw['n1']}) vs third_party (n={mw['n2']}): "
                              f"U={_fmt(mw['U'])}, z={_fmt(mw['z'])}, p={_p(mw['p'])} -> {verdict}"
                          + (f" ({higher} higher)" if higher else ""),
                          ""]
                comparisons.append({"entity": entity, "measure": measure, **mw,
                                    "differs": mw["p"] < alpha, "higher": higher,
                                    "median_official": describe(by_tier["official"])["median"],
                                    "median_third_party": describe(by_tier["third_party"])["median"]})
            else:
                lines += ["", "too few records in one tier to compare", ""]

    # ---- targeted slot comparisons (TASK-020) ------------------------------
    lines += ["## Targeted slot comparisons", "",
              "The proxies above answer *which measures can be compared at all* - almost none, "
              "because canon tier and entity type nearly coincide. These answer the question a "
              "reader actually has: **within one decision a player makes, do the tiers differ?** "
              f"A rank-sum is quoted only where each tier has at least {MIN_COMPARABLE_N} "
              "records. Slots that miss that bar are shown with their sample sizes rather than "
              "dropped, so where the evidence is missing stays visible.", ""]
    slot_rows: list[list] = []
    slot_tests: list[dict] = []
    for label, entity, measure, why in SLOT_COMPARISONS:
        pairs = measured.get(entity, {}).get(measure) or []
        by_tier = {t: [v for r, v in pairs if r.get("canon") == t and v > 0] for t in TIERS}
        n_off, n_tp = len(by_tier["official"]), len(by_tier["third_party"])
        d_off, d_tp = describe(by_tier["official"]), describe(by_tier["third_party"])
        if min(n_off, n_tp) < MIN_COMPARABLE_N:
            slot_rows.append([label, f"`{measure}`", n_off, n_tp, _fmt(d_off["median"]),
                              _fmt(d_tp["median"]), f"n too small (needs {MIN_COMPARABLE_N})", why])
            continue
        mw = mann_whitney_u(by_tier["official"], by_tier["third_party"])
        differs = mw["p"] is not None and mw["p"] < alpha
        slot_rows.append([label, f"`{measure}`", n_off, n_tp, _fmt(d_off["median"]),
                          _fmt(d_tp["median"]),
                          f"U={_fmt(mw['U'])}, p={_p(mw['p'])}" + (" **differs**" if differs else ""),
                          why])
        slot_tests.append({"slot": label, "entity": entity, "measure": measure,
                           "differs": differs, "pairs": pairs, "p": mw["p"],
                           "n_official": n_off, "n_third_party": n_tp})
    lines += _table(["decision slot", "measure", "n official", "n 3rd", "median official",
                     "median 3rd", "rank-sum", "why it matters"], slot_rows)
    lines += [""]

    # A tier difference is only evidence about *canon* if the tiers are not also
    # separated by which book the records came from. Third-party content here is
    # builder-derived, so this control decides whether a difference means anything.
    shown = [s for s in slot_tests if s["differs"]] or slot_tests
    lines += ["### Sourcebook control", "",
              "Which sourcebooks the compared records actually cite. If one tier is a single "
              "source, the comparison is really \"that source versus everything else\" and says "
              "nothing about canonicity as such."
              + ("" if shown else " No slot had enough overlap to test."), ""]
    for s in shown:
        counts: Counter = Counter()
        for r, v in s["pairs"]:
            if v <= 0:
                continue
            books = {b["abbreviation"] for b in (r.get("sourcebooks") or [])} or {UNCITED}
            for b in books:
                counts[(r.get("canon"), b)] += 1
        books = sorted({b for _c, b in counts},
                       key=lambda b: (-counts[("official", b)] - counts[("third_party", b)], b))
        rows = [[f"`{b}`", counts[("official", b)], counts[("third_party", b)]] for b in books[:12]]
        if len(books) > 12:
            rest = books[12:]
            rows.append([f"*{len(rest)} more*", sum(counts[("official", b)] for b in rest),
                         sum(counts[("third_party", b)] for b in rest)])
        lines += [f"**{s['slot']} / `{s['measure']}`** - official n={s['n_official']}, "
                  f"third-party n={s['n_third_party']}, p={_p(s['p'])}"
                  + (" (**tiers differ**)" if s["differs"] else ""), ""]
        lines += _table(["sourcebook", "official", "third_party"], rows)
        # `UNCITED` is a placeholder, not a sourcebook: counting it as one makes an
        # all-derived slot look like a one-book confound ("spans 1 sourcebooks").
        tp_books = sorted({b for (c, b) in counts if c == "third_party" and b != UNCITED})
        off_books = sorted({b for (c, b) in counts if c == "official" and b != UNCITED})
        if not tp_books and not off_books:
            lines += ["", "Neither tier cites a sourcebook here, so this slot has no sourcebook "
                          "control at all: the comparison is tier-only and cannot be "
                          "cross-checked against print provenance.", ""]
        elif not off_books or not tp_books:
            lines += ["", "One tier has no cited records, so the control cannot be read.", ""]
        elif len(tp_books) == 1:
            lines += ["", f"The entire third-party side of this comparison cites `{tp_books[0]}` "
                          f"while the official side spans {len(off_books)} sourcebooks. The tier "
                          "difference and that one source's house style cannot be separated: a "
                          "difference here would be evidence about "
                          f"`{tp_books[0]}`, not about third-party content in general.", ""]
        else:
            lines += ["", f"Third-party records here cite {len(tp_books)} sourcebooks "
                          f"({', '.join(f'`{b}`' for b in tp_books[:6])}"
                          f"{'...' if len(tp_books) > 6 else ''}) against {len(off_books)} on the "
                          "official side, so a difference would not reduce to one book.", ""]
        lines += [""]

    # ---- outliers ----------------------------------------------------------
    lines += ["## Outliers (top decile per tier)", "",
              "Each row names the cell the value came from, so it can be checked against "
              "the workbook. `verdict` is a hand inspection recorded in "
              "`data/curation/audit-verdicts.yaml`: `real` (the content genuinely is that "
              "strong), `artefact` (a parsing or extraction bug), or `missing` (the value "
              "is inflated because data is absent).", ""]
    for entity in sorted(measured):
        for measure in sorted(measured[entity]):
            pairs = measured[entity][measure]
            if not pairs:
                continue
            for tier in TIERS:
                rows = sorted(((v, r) for r, v in pairs if r.get("canon") == tier and v > 0),
                              key=lambda t: (-t[0], t[1]["id"]))
                if not rows:
                    continue
                cut = max(1, math.ceil(len(rows) * 0.1))
                shown = rows[:max(1, min(cut, top))]
                lines += [f"### `{entity}` / {measure} - `{tier}` (top {len(shown)} of {len(rows)})", ""]
                lines += _table(["value", "record", "name", "source cell", "verdict"],
                                [[_fmt(v), f"`{r['id']}`", r["name"], _source_ref(r),
                                  (verdicts.get(r["id"], {}) or {}).get("verdict", "-")]
                                 for v, r in shown])
                lines += [""]
                note = (verdicts.get(rows[0][1]["id"], {}) or {}).get("note")
                if note:
                    lines += [f"> {note}", ""]

    # ---- data quality ------------------------------------------------------
    sus = suspicious_numeric_attrs(db)
    lines += ["## Data-quality findings", ""]
    if sus:
        lines += ["Numeric attributes whose name is a bare number are unnamed spreadsheet "
                  "columns, not game data. They are excluded from every proxy above.", ""]
        lines += _table(["entity", "attribute", "records"],
                        [[f"`{e}`", f"`{k}`", n] for e, k, n in sus[:25]])
        lines += [""]
    else:
        lines += ["No unnamed numeric columns found.", ""]

    artefacts = {e: (len(db.all(e)) - len(distinct_options(db, e))) for e in db.entities
                 if len(db.all(e)) != len(distinct_options(db, e))}
    if artefacts:
        lines += ["Rows flagged as builder combinations or parameter variants (GAP-014) are "
                  "excluded from every distribution above. They are rows the builder "
                  "materialised so its UI could offer a pre-computed choice, not options a "
                  "player picks independently, so counting them measures the builder.", ""]
        lines += _table(["entity", "records", "distinct options", "builder rows"],
                        [[f"`{e}`", len(db.all(e)), len(distinct_options(db, e)), n]
                         for e, n in sorted(artefacts.items())])
        lines += [""]

    # ---- build-level audit -------------------------------------------------
    lines += ["## Build-level audit", "",
              "Record-level comparisons are weak here because the tiers barely overlap "
              "within an entity type. Builds are not weak: every build is scored on the "
              "same scale, so splitting a seeded sample into builds that use only official "
              "content and builds that use any third-party or homebrew option answers the "
              "question that actually matters - *does opening the corpus inflate the top "
              "of the ranking?*", ""]
    build_audits = []      # homebrew excluded: the balance comparison
    taint_audits = []      # homebrew allowed: how much of the ranking is unscoreable
    for lvl in (BUILD_LEVELS if include_builds else ()):
        # Two samples per level. The clean one excludes homebrew classes so that every
        # build in it can actually be scored - that is the comparison with power. The
        # full one keeps them, to measure how much of the published ranking rests on
        # levels that contribute nothing.
        clean = build_level_audit(db, ev, lvl, n=BUILD_SAMPLE, seed=BUILD_SEED,
                                  include_homebrew=False)
        full = build_level_audit(db, ev, lvl, n=BUILD_SAMPLE, seed=BUILD_SEED,
                                 include_homebrew=True)
        build_audits.append(clean)
        taint_audits.append(full)
        so, st, mw = clean["stats_official"], clean["stats_third_party"], clean["mw"]
        lines += [f"### Level {lvl} - balance sample ({clean['sampled']} builds, "
                  f"seed {clean['seed']}, homebrew excluded)", ""]
        lines += _table(["group", "n", "median total", "p25", "p75", "max"],
                        [["official content only", so["n"], _fmt(so["median"]), _fmt(so["p25"]),
                          _fmt(so["p75"]), _fmt(so["max"])],
                         ["third-party content", st["n"], _fmt(st["median"]), _fmt(st["p25"]),
                          _fmt(st["p75"]), _fmt(st["max"])]])
        if min(so["n"], st["n"]) < MIN_COMPARABLE_N:
            lines += ["", f"too few builds to compare (official n={so['n']}, third-party "
                          f"n={st['n']}, needs {MIN_COMPARABLE_N} in each): no p-value is "
                          "reported, because a rank-sum on a handful of builds is noise. "
                          "Third-party options are rare in random builds - most of the "
                          "corpus's third-party content is in entity types the level-1 "
                          "sampler barely touches.", ""]
        elif mw["p"] is not None:
            verdict = ("**third-party builds score higher**"
                       if mw["p"] < alpha and (st["median"] or 0) > (so["median"] or 0) else
                       "**official-only builds score higher**" if mw["p"] < alpha else
                       "no evidence of a difference")
            lines += ["", f"official-only (n={mw['n1']}) vs third-party (n={mw['n2']}): "
                          f"U={_fmt(mw['U'])}, z={_fmt(mw['z'])}, p={_p(mw['p'])} -> {verdict}", ""]
        lines += [f"### Level {lvl} - taint sample ({full['sampled']} builds, homebrew allowed)",
                  "",
                  "Technician and Force Prodigy have no hit die, BAB rate or defence numbers "
                  "in either source (GAP-013, TASK-016), so every level taken in them "
                  "contributes nothing to `bab`, `offense`, `defense_*` or `durability`. "
                  "Builds using them are not weak - they are partly unscoreable.", ""]
        sh = full["stats_homebrew"]
        lines += _table(["group", "n", "median total", "p75", "max"],
                        [["official content only", full["stats_official"]["n"],
                          _fmt(full["stats_official"]["median"]), _fmt(full["stats_official"]["p75"]),
                          _fmt(full["stats_official"]["max"])],
                         ["third-party content", full["n_third_party"],
                          _fmt(full["stats_third_party"]["median"]),
                          _fmt(full["stats_third_party"]["p75"]),
                          _fmt(full["stats_third_party"]["max"])],
                         ["uses a homebrew class", sh["n"], _fmt(sh["median"]), _fmt(sh["p75"]),
                          _fmt(sh["max"])]])
        lines += ["",
                  f"Top decile (total >= {_fmt(full['top_decile_threshold'])}, "
                  f"{full['top_decile_size']} builds): **{full['top_decile_homebrew']} use a "
                  f"homebrew class**, {full['top_decile_third_party']} use third-party content, "
                  f"{full['top_decile_size'] - full['top_decile_homebrew'] - full['top_decile_third_party']} "
                  "are official-only.", ""]
        if full["most_used_non_official"]:
            lines += ["Most-used non-official options in the taint sample:"]
            lines += _table(["option", "entity", "canon", "builds"],
                            [[f"`{rid}`", f"`{(db.by_id.get(rid) or {}).get('entity', '?')}`",
                              (db.by_id.get(rid) or {}).get("canon", "?"), cnt]
                             for rid, cnt, _name in full["most_used_non_official"]])
            lines += [""]
        if full["mixed_examples"]:
            lines += ["Highest-scoring builds that use non-official content:"]
            lines += _table(["total", "group", "species", "class path", "non-official options"],
                            [[_fmt(round(ex["total"], 2)), ex["group"].replace("_", " "),
                              ex["species"], ex["classes"], "; ".join(ex["non_official"])]
                             for ex in full["mixed_examples"]])
            lines += [""]

    # ---- conclusion --------------------------------------------------------
    differing = [c for c in comparisons if c["differs"]]
    lines += ["## Conclusion", "",
              f"**Record-level:** {len(comparisons)} of {len(comparisons) + skipped} power "
              f"proxies could be compared at all; {skipped} were skipped because one tier "
              f"had fewer than {MIN_COMPARABLE_N} records. "
              + (f"{len(differing)} show a difference at p < {alpha}." if differing
                 else "None shows a difference at p < " + f"{alpha}.")
              + " Either way this is weak evidence: the tiers barely overlap within an "
              "entity type, so absence of a difference here is not evidence of balance.", ""]
    differing_slots = [s for s in slot_tests if s["differs"]]
    if slot_tests:
        sizes = ", ".join(f"{s['slot'].lower()} {s['measure']} {s['n_official']}/{s['n_third_party']}"
                          for s in slot_tests)
        lines += [f"**Slot-level:** {len(slot_tests)} of {len(SLOT_COMPARISONS)} decision-slot "
                  f"comparisons had at least {MIN_COMPARABLE_N} records per tier ({sizes}). "
                  + (f"{len(differing_slots)} differ at p < {alpha}: "
                     + ", ".join(f"{s['slot']} `{s['measure']}` (p={_p(s['p'])})"
                                 for s in differing_slots)
                     + ". Mixed-canon rankings are **not** safe to quote until those slots are "
                       "inspected record by record and given verdicts."
                     if differing_slots else
                     f"None differs at p < {alpha}. This is the strongest support the corpus "
                     "offers for quoting mixed-canon rankings, and it is still absence of "
                     "evidence rather than proof of balance: the slots that could not be tested "
                     "are exactly the ones a player touches most often in combat."), ""]
    else:
        lines += ["**Slot-level: nothing testable.** No decision slot had "
                  f"{MIN_COMPARABLE_N} records in both tiers, so the corpus cannot say whether "
                  "the tiers differ where a player actually chooses. Mixed-canon rankings are "
                  "unsupported by record-level evidence either way.", ""]
    inflated = [ba for ba in build_audits
                if ba["mw"]["p"] is not None and ba["mw"]["p"] < alpha
                and min(ba["n_official"], ba["n_third_party"]) >= MIN_COMPARABLE_N
                and (ba["stats_third_party"]["median"] or 0) > (ba["stats_official"]["median"] or 0)]
    comparable = [ba for ba in build_audits
                  if min(ba["n_official"], ba["n_third_party"]) >= MIN_COMPARABLE_N]
    if build_audits:
        lines += _table(["level", "balance sample: n official / n 3rd-party",
                         "median official", "median 3rd-party", "p",
                         "taint sample: homebrew builds", "top decile using homebrew"],
                        [[ba["level"], f"{ba['n_official']} / {ba['n_third_party']}",
                          _fmt(ba["stats_official"]["median"]), _fmt(ba["stats_third_party"]["median"]),
                          _p(ba["mw"]["p"]) if min(ba["n_official"], ba["n_third_party"]) >= MIN_COMPARABLE_N
                          else "n too small",
                          f"{ta['n_homebrew']} of {ta['sampled']}",
                          f"{ta['top_decile_homebrew']} of {ta['top_decile_size']}"]
                         for ba, ta in zip(build_audits, taint_audits)])
        lines += [""]
    if not build_audits:
        lines += ["**Build-level: not run.** This copy of the audit was generated with "
                  "`include_builds=False`, so only the record-level half is present. That "
                  "half cannot answer whether mixed-canon rankings are safe to quote - run "
                  "`python -m swse.cli audit` for the full audit.", ""]
    elif inflated:
        lines += ["**Build-level: third-party content does inflate the ranking.** Publish "
                  "rankings from `--canon official` when the number will be quoted, and label "
                  "any mixed-canon ranking provisional. Before calling a specific option "
                  "over-powered, inspect it against its source cell and record a verdict in "
                  "`data/curation/audit-verdicts.yaml` - a statistical difference is a prompt "
                  "to look, not a conclusion.", ""]
    elif comparable:
        lines += ["**Build-level: no evidence that third-party content inflates the ranking.** "
                  "Where the two groups are large enough to compare, official-only builds score "
                  "the same or higher, so mixed-canon rankings are not being quietly dominated "
                  "by builder-only content.", ""]
    else:
        lines += ["**Build-level: undetermined.** Third-party options are too rare in random "
                  "builds to compare - in these samples the third-party group never reached "
                  f"{MIN_COMPARABLE_N} builds. That is itself a finding: third-party content "
                  "mostly lives in entity types (racial abilities, weapon mods, skills, "
                  "destinies, droid options) that the character-level sampler treats as fixed "
                  "or ignores, so it cannot inflate a build ranking by very much. A targeted "
                  "comparison - third-party talent trees against official ones, third-party "
                  "species against official ones - is the way to get power here, and it is "
                  "filed as follow-up work below.", ""]
    if taint_audits and any(ta["top_decile_homebrew"] for ta in taint_audits):
        lines += ["**But the published top of the ranking is still not trustworthy**, for a reason "
                  "this audit can name and not fix: the top decile is largely made of builds whose "
                  "class levels are partly *unscoreable*. Technician and Force Prodigy have no "
                  "progression numbers in either source (GAP-013), so those levels contribute "
                  "nothing to `bab`, `offense`, `defense_*` or `durability` - and such builds still "
                  "reach the top, because Force Prodigy grants every talent tree and Technician "
                  "grants a large option set. Their true totals are unknown, not low. Quote "
                  "`--no-homebrew` rankings until TASK-016 closes, and treat the mixed ranking as "
                  "unresolved rather than as settled in either direction.", ""]
    if build_audits:
        lines += ["Two further limits: the underlying progression and ability-score assumptions are "
                  "unverified (see `docs/verification.md`), and the sample is "
                  f"{BUILD_SAMPLE} builds per level at seed {BUILD_SEED}, so a small effect would "
                  "not show up.", ""]
    if differing:
        lines += [f"Record-level differences at p < {alpha}:", ""]
        lines += _table(["entity", "measure", "median official", "median third_party", "p", "higher"],
                        [[f"`{c['entity']}`", c["measure"], _fmt(c["median_official"]),
                          _fmt(c["median_third_party"]), _fmt(c["p"]), c["higher"]]
                         for c in sorted(differing, key=lambda c: c["p"])])
        lines += [""]
    lines += ["## Method and limits", "",
              "- Rank-sum p-values use a normal approximation with tie correction and a "
              "continuity correction; they are indicative, not exact.",
              "- Text proxies parse bonus signatures with the same regex the evaluator uses, "
              "so they inherit its blind spots (a bonus expressed without a number is worth 0).",
              "- Proxies are per-record and ignore stacking rules: two +2 bonuses to the same "
              "target do not stack in play, and this audit does not model that.",
              "- Homebrew has 2 records; no comparison involving it is meaningful.", ""]
    return "\n".join(lines) + "\n"


def write_canon_balance(db: Dataset | None = None, out=None, top: int = 8) -> "paths.Path":
    db = db or Dataset.load()
    from .report import _write

    return _write(canon_balance(db, top=top), out or (paths.ANALYSIS_DIR / "out" / "canon-balance.md"))
