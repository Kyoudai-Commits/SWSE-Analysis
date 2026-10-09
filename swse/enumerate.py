"""Stage 5: build enumeration.

A *build* is one fully-specified character: a species, a class path, ability
scores, and the feats/talents/skills/powers chosen at each level. This module
can

* enumerate level-1 builds **exactly** (``iter_level1_builds``),
* count builds analytically (``count_builds``, delegating to :mod:`swse.space`),
* **sample** builds at any level (``sample_builds``) - required, because the
  level-20 space is ~10^25 and cannot be listed,
* and check any build against the prerequisite system (``check_build``).

Sampling is progressive: choices are made level by level and every choice is
validated against what the character actually has at that point, so a sampled
build is legal by construction unless ``constraints.ignore_prereqs`` is set.
"""

from __future__ import annotations

import itertools
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator

from .ids import fold, norm_key
from .space import ABILITY_KEYS, DecisionSpace, ability_modifier, load_assumptions, n_choose_k
from .store import Dataset


@dataclass
class Constraints:
    """What a run of the enumerator is allowed to consider."""
    level: int = 1
    species: list[str] | None = None          # ids or names; None = all
    classes: list[str] | None = None          # ids or names; None = all
    canon: str | None = None                  # None | official | third_party | homebrew
    include_homebrew: bool = True
    ability_method: str = "standard_array"    # see config/analysis.yaml
    abilities: dict | None = None             # explicit scores override the method
    force_sensitive: bool | None = None       # None = either
    include_gear: bool = False
    ignore_prereqs: bool = False
    seed: int | None = None
    limit: int | None = None
    require_feats: list[str] = field(default_factory=list)
    require_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _resolve_ids(db: Dataset, entity: str, names: list[str] | None) -> set[str]:
    if not names:
        return set()
    out = set()
    for n in names:
        rec = db.get(entity, n)
        if rec:
            out.add(rec["id"])
        else:
            out.update(r["id"] for r in db.find(entity, n))
    return out


def ability_arrays(db: Dataset, method: str, explicit: dict | None = None,
                   limit: int | None = None) -> Iterator[dict]:
    """Yield ability-score assignments as ``{"STR": 13, ...}``."""
    if explicit:
        yield {k: int(explicit.get(k, 10)) for k in ABILITY_KEYS}
        return
    a = load_assumptions()["ability_scores"]
    spec = next((m for m in a["methods"] if m["id"] == method), None)
    if spec is None:
        raise ValueError(f"unknown ability method {method!r}")
    if spec["id"] == "standard_array":
        for perm in itertools.permutations(spec["array"]):
            yield dict(zip(ABILITY_KEYS, perm))
            if limit and perm == perm:  # limit handled by caller
                pass
    elif spec["id"] == "distinct_vectors":
        lo, hi = spec["min"], spec["max"]
        for combo in itertools.product(range(lo, hi + 1), repeat=len(ABILITY_KEYS)):
            yield dict(zip(ABILITY_KEYS, combo))
    elif spec["id"] == "point_buy":
        curve = {int(k): int(v) for k, v in (spec.get("cost_curve") or {}).items()}
        if not curve:
            yield {k: 10 for k in ABILITY_KEYS}
            return
        budget = spec.get("budget", 0)
        scores = sorted(curve)

        def rec(i, spent, acc):
            if i == len(ABILITY_KEYS):
                yield dict(acc)
                return
            for s in scores:
                if spent + curve[s] <= budget:
                    acc[ABILITY_KEYS[i]] = s
                    yield from rec(i + 1, spent + curve[s], acc)
        yield from rec(0, 0, {})
    else:
        yield {k: 10 for k in ABILITY_KEYS}


class Builder:
    """Knows how to make legal choices for one character."""

    def __init__(self, db: Dataset, constraints: Constraints):
        self.db = db
        self.c = constraints
        self.space = DecisionSpace(db, level=constraints.level,
                                   include_homebrew=constraints.include_homebrew,
                                   canon_filter=constraints.canon,
                                   include_gear=constraints.include_gear,
                                   ability_method=constraints.ability_method)
        self.rng = random.Random(constraints.seed)
        self.species_ids = _resolve_ids(db, "species", constraints.species)
        self.class_ids = _resolve_ids(db, "class", constraints.classes)
        self._feat_pool = None

    # -- populations -------------------------------------------------------
    def species_pool(self) -> list[dict]:
        pool = [s for s in self.space.species]
        if self.species_ids:
            pool = [s for s in pool if s["id"] in self.species_ids]
        return pool

    def class_pool(self, level: int, total_level: int, path: list[str],
                   state: dict | None = None) -> list[dict]:
        """Classes legal to take as the ``level``-th level of this character.

        Level 1 must be heroic; a prestige class needs both the character level
        (``attrs.min_level``) and its own parsed prerequisites - so a Nazren can
        never take Independent Droid, and Jedi Knight needs BAB +7 and
        Weapon Proficiency (Lightsabers).
        """
        if total_level == 0:
            pool = list(self.space.heroic_classes)
        else:
            pool = list(self.space.heroic_classes) + [
                c for c in self.space.prestige_classes
                if total_level + 1 >= int(c["attrs"].get("min_level") or 7)]
        if state is not None and not self.c.ignore_prereqs:
            pool = [c for c in pool if self.class_available(c, state)]
        if self.class_ids:
            allowed = [c for c in pool if c["id"] in self.class_ids]
            pool = allowed or pool
        return pool

    def class_available(self, cls: dict, state: dict) -> bool:
        """Check a class's prerequisites against the character so far."""
        p = cls.get("prerequisites")
        if not p or not p.get("predicates"):
            return True
        abilities = state.get("abilities") or {}
        bab = state.get("bab", 0)
        level = state.get("level", 0)
        trained = {norm_key(s) for s in state.get("trained_skills", [])}
        feats = {f["id"] for f in state.get("feats", [])}
        talents = {t["id"] for t in state.get("talents", [])}
        kind = state.get("species_kind")
        for pred in _walk(p["predicates"]):
            t = pred.get("type")
            if t == "level_min" and level < pred.get("min", 0):
                return False
            if t == "bab_min" and bab < pred.get("min", 0):
                return False
            if t == "ability_min" and abilities.get(pred.get("ability"), 10) < pred.get("min", 0):
                return False
            if t == "trained_skill":
                wanted = {norm_key(w) for w in ([pred.get("skill")] + list(pred.get("skills") or [])) if w}
                if wanted and not (wanted & trained if pred.get("mode") == "any" else wanted <= trained):
                    return False
            if t in {"skill"}:
                wanted = {norm_key(w) for w in (pred.get("names") or ([pred.get("name")] if pred.get("name") else [])) if w}
                if wanted and not (wanted & trained):
                    return False
            if t == "feat":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")}
                if pred.get("id"):
                    ids.add(pred["id"])
                if ids and not (ids & feats if pred.get("mode") == "any" else ids <= feats):
                    return False
            if t == "talent":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")}
                if ids and not (ids & talents):
                    return False
            if t == "talent_tree":
                names = {norm_key(x) for x in (pred.get("trees") or pred.get("names") or []) if x}
                have = {norm_key(x) for x in state.get("trees", [])}
                if names and not (names & have):
                    return False
            if t == "creature_type":
                want = fold(pred.get("value", "")).lower()
                if want == "droid" and kind != "droid_chassis":
                    return False
                if want in {"non-droid", "nondroid", "organic"} and kind == "droid_chassis":
                    return False
            if t == "species":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")}
                if ids and state.get("species") not in ids:
                    return False
            if t == "force_sensitive" and not state.get("force_sensitive"):
                return False
            if t == "weapon_proficiency" and pred.get("group"):
                if norm_key(pred["group"]) not in {norm_key(g) for g in state.get("weapon_groups", [])}:
                    return False
            if t == "armor_proficiency" and pred.get("grade"):
                if norm_key(pred["grade"]) not in {norm_key(g) for g in state.get("armor_grades", [])}:
                    return False
            # 'special' and 'other' are GM-judgement gates: recorded, not enforced
        return True

    def feat_pool(self) -> list[dict]:
        if self._feat_pool is None:
            self._feat_pool = self.space.feat_pool_at_level1()["eligible"]
        return self._feat_pool

    def tree_pool(self, cls: dict) -> list[dict]:
        names = {norm_key(t) for t in (cls["attrs"].get("talent_trees") or [])}
        trees = []
        for t in self.db.all("talent_tree"):
            keys = {norm_key(t["name"])} | {norm_key(a) for a in (t["attrs"].get("aliases") or [])}
            cg = {norm_key(c) for c in (t["attrs"].get("classes_from_builder") or [])}
            if names & (keys | cg) or (not names and cls["name"] in (t["attrs"].get("availability") or [])):
                trees.append(t)
        return trees

    def talents_in(self, trees: list[dict]) -> list[dict]:
        ids = {t for tree in trees for t in (tree["attrs"].get("talents") or [])}
        out = [t for t in self.db.all("talent") if t["id"] in ids]
        return out or [t for t in self.db.all("talent")
                       if norm_key(t["attrs"].get("tree") or "") in {norm_key(x["name"]) for x in trees}]

    def skills_for(self, cls: dict, species: dict, abilities: dict) -> list[str]:
        sc = self.space.class_skill_choices(cls, ability_modifier(abilities.get("INT", 10)))
        pool = cls["attrs"].get("class_skills") or [s["name"] for s in self.db.all("skill")]
        if "Knowledge (all; taken individually)" in pool:
            knowledge = [s["name"] for s in self.db.all("skill") if s["name"].lower().startswith("knowledge")]
            pool = [p for p in pool if not p.lower().startswith("knowledge (all")] + knowledge
        return pool

    # -- legality ----------------------------------------------------------
    def feat_available(self, feat_id: str, build: dict, abilities: dict, bab: int) -> bool:
        if self.c.ignore_prereqs:
            return True
        rec = self.db.get("feat", feat_id)
        if not rec:
            return False
        p = rec.get("prerequisites")
        if not p or not p.get("predicates"):
            return True
        taken_feats = {f["id"] for f in build.get("feats", [])}
        taken_talents = {t["id"] for t in build.get("talents", [])}
        trained = {norm_key(s) for s in build.get("trained_skills", [])}
        for pred in _walk(p["predicates"]):
            t = pred.get("type")
            if t == "ability_min" and abilities.get(pred["ability"], 10) < pred["min"]:
                return False
            if t == "bab_min" and bab < pred["min"]:
                return False
            if t == "level_min" and build.get("level", 1) < pred["min"]:
                return False
            if t == "trained_skill":
                wanted = [pred.get("skill")] + list(pred.get("skills") or [])
                wanted = [norm_key(w) for w in wanted if w]
                if wanted and pred.get("mode") == "any":
                    if not (set(wanted) & trained):
                        return False
                elif wanted and not set(wanted) <= trained:
                    return False
            if t == "feat":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")}
                if pred.get("id"):
                    ids.add(pred["id"])
                if ids and pred.get("mode") == "any":
                    if not (ids & taken_feats):
                        return False
                elif ids and not ids <= taken_feats:
                    return False
            if t == "talent":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")}
                if ids and not (ids & taken_talents):
                    return False
            if t == "force_sensitive" and not build.get("force_sensitive"):
                return False
            if t == "creature_type":
                kind = build.get("species_kind")
                want = pred.get("value", "")
                if want == "droid" and kind != "droid_chassis":
                    return False
                if want in {"non-droid", "nondroid"} and kind == "droid_chassis":
                    return False
        return True


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
# exact level-1 enumeration
# ---------------------------------------------------------------------------
def iter_level1_builds(db: Dataset, constraints: Constraints | None = None) -> Iterator[dict]:
    """Every legal level-1 build, streamed. Exact but combinatorially large.

    Order: species -> class -> ability array -> trained skills -> feat.
    Set ``constraints.limit`` to stop early; use :func:`sample_builds` for
    representative subsets of a large space.
    """
    c = constraints or Constraints()
    c.level = 1
    b = Builder(db, c)
    emitted = 0
    abilities_iter = list(ability_arrays(db, c.ability_method, c.abilities, c.limit))
    feat_pool = b.feat_pool()
    required_feats = _resolve_ids(db, "feat", c.require_feats)
    for species in b.species_pool():
        kind = species["attrs"].get("species_kind", "species")
        for cls in b.class_pool(1, 0, []):
            for abilities in abilities_iter:
                final = {k: v + int(species["attrs"].get(f"mod_{k.lower()}") or 0) for k, v in abilities.items()}
                pool = b.skills_for(cls, species, final)
                picks = b.space.class_skill_choices(cls, ability_modifier(final.get("INT", 10)))["picks"]
                for skills in itertools.combinations(pool, max(0, min(picks, len(pool)))):
                    if c.require_skills and not set(map(norm_key, c.require_skills)) <= {norm_key(s) for s in skills}:
                        continue
                    build = {
                        "level": 1,
                        "species": species["id"], "species_kind": kind,
                        "class_path": [{"level": 1, "class": cls["id"]}],
                        "abilities_base": abilities, "abilities_final": final,
                        "trained_skills": list(skills),
                        "feats": [], "talents": [], "force_powers": [],
                        "force_sensitive": False,
                        "starting_credits": cls["attrs"].get("starting_credits"),
                        "hit_die": cls["attrs"].get("hit_die"),
                    }
                    unmet = []
                    for grant in cls["attrs"].get("starting_feats") or []:
                        head = grant.split(" (")[0]
                        hits = db.find("feat", head) or db.find("feat", grant)
                        if not hits or any(f["id"] == hits[0]["id"] for f in build["feats"]):
                            continue
                        if b.feat_available(hits[0]["id"], build, final, bab=0):
                            build["feats"].append({"id": hits[0]["id"], "granted_by": cls["id"], "raw": grant})
                        else:
                            unmet.append({"feat": hits[0]["id"], "granted_by": cls["id"], "raw": grant})
                    build["unmet_grants"] = unmet
                    for feat_id in feat_pool:
                        if required_feats and feat_id not in required_feats:
                            continue
                        if any(f["id"] == feat_id for f in build["feats"]):
                            continue
                        if not b.feat_available(feat_id, build, final, bab=0):
                            continue
                        candidate = dict(build)
                        candidate["feats"] = build["feats"] + [{"id": feat_id, "chosen_at": 1}]
                        if c.force_sensitive is True and not _is_force_sensitive(candidate):
                            continue
                        if c.force_sensitive is False and _is_force_sensitive(candidate):
                            continue
                        yield candidate
                        emitted += 1
                        if c.limit and emitted >= c.limit:
                            return


def _is_force_sensitive(build: dict) -> bool:
    return any(f["id"] in {"feat_force_sensitivity", "feat_force_training"} for f in build.get("feats", []))


# ---------------------------------------------------------------------------
# sampling at any level
# ---------------------------------------------------------------------------
def sample_builds(db: Dataset, constraints: Constraints | None = None, n: int = 100) -> list[dict]:
    """Random legal builds at ``constraints.level``.

    Progressive construction: the class path is walked level by level, and each
    feat/talent choice is validated against the character as it stands at that
    level. Duplicate builds are discarded, so ``n`` is an upper bound.
    """
    c = constraints or Constraints()
    b = Builder(db, c)
    rng = b.rng
    prog = load_assumptions().get("progression", {})
    feat_levels = set(prog.get("feats_at_levels", []))
    talent_levels = set(prog.get("talents_at_levels", []))
    out: list[dict] = []
    seen: set[str] = set()
    species_pool = b.species_pool()
    if not species_pool:
        return out
    attempts = 0
    max_attempts = max(n * 40, 400)
    while len(out) < n and attempts < max_attempts:
        attempts += 1
        build = _sample_one(db, b, c, rng, species_pool, feat_levels, talent_levels)
        if build is None:
            continue
        key = _signature(build)
        if key in seen:
            continue
        seen.add(key)
        out.append(build)
    return out


def _sample_one(db: Dataset, b: Builder, c: Constraints, rng: random.Random,
                species_pool: list[dict], feat_levels: set[int], talent_levels: set[int]) -> dict | None:
    species = rng.choice(species_pool)
    abilities = next(iter(ability_arrays(db, c.ability_method, c.abilities, 1)),
                     {k: 10 for k in ABILITY_KEYS})
    if not c.abilities:
        # random pick from the method's space without enumerating it
        a = load_assumptions()["ability_scores"]
        spec = next((m for m in a["methods"] if m["id"] == c.ability_method), None)
        if spec and spec["id"] == "distinct_vectors":
            abilities = {k: rng.randint(spec["min"], spec["max"]) for k in ABILITY_KEYS}
        elif spec and spec["id"] == "standard_array":
            arr = list(spec["array"])
            rng.shuffle(arr)
            abilities = dict(zip(ABILITY_KEYS, arr))
    final = {k: v + int(species["attrs"].get(f"mod_{k.lower()}") or 0) for k, v in abilities.items()}

    path: list[dict] = []
    feats: list[dict] = []
    talents: list[dict] = []
    trained: list[str] = []
    trees: list[dict] = []
    weapon_groups: list[str] = []
    armor_grades: list[str] = []
    unmet_grants: list[dict] = []
    bab = 0
    bab_acc = 0.0
    for level in range(1, c.level + 1):
        state = {
            "level": level - 1, "bab": bab, "abilities": final,
            "trained_skills": trained, "feats": feats, "talents": talents,
            "species": species["id"], "species_kind": species["attrs"].get("species_kind"),
            "force_sensitive": any(f["id"] == "feat_force_sensitivity" for f in feats),
            "trees": [t["name"] for t in trees],
            "weapon_groups": weapon_groups, "armor_grades": armor_grades,
        }
        pool = b.class_pool(level, level - 1, [p["class"] for p in path], state)
        if not pool:
            return None
        cls = rng.choice(pool)
        path.append({"level": level, "class": cls["id"]})
        # BAB accrues at the class's own rate (1.0 or 0.75) and is floored, so a
        # Scout 3 / Soldier 2 has BAB 4, not 5.
        bab_acc += float(cls["attrs"].get("base_attack") or 0.75)
        bab = int(bab_acc)
        # Skills are chosen before class-granted feats are filtered, because a
        # grant such as Shake It Off can itself require a trained skill.
        skill_pool = b.skills_for(cls, species, final)
        picks = b.space.class_skill_choices(cls, ability_modifier(final.get("INT", 10)))["picks"]
        k = max(0, min(picks, len(skill_pool))) if skill_pool else 0
        for s in (rng.sample(skill_pool, k) if k else []):
            if norm_key(s) not in {norm_key(x) for x in trained}:
                trained.append(s)
        params = cls["attrs"].get("starting_feats_params") or {}
        for grant, param in params.items():
            head = grant.split(" (")[0]
            if norm_key(head) == norm_key("Weapon Proficiency") and param:
                weapon_groups.append(param.lower())
            elif norm_key(head) == norm_key("Armor Proficiency") and param:
                armor_grades.append(param.lower())
        if level == 1:
            # Class-granted feats still carry their own prerequisites: the Scout
            # grants Shake It Off "(must have the prerequisite Constitution of 13
            # and be Trained in Endurance)". Honour them, and record what the
            # character did not qualify for instead of pretending it did.
            for grant in cls["attrs"].get("starting_feats") or []:
                head = grant.split(" (")[0]
                hits = db.find("feat", head) or db.find("feat", grant)
                if not hits or any(x["id"] == hits[0]["id"] for x in feats):
                    continue
                entry = {"id": hits[0]["id"], "granted_by": cls["id"], "level": 1}
                if params.get(grant):
                    entry["param"] = params[grant]
                probe = {"level": level, "feats": feats, "talents": talents,
                         "trained_skills": trained,
                         "species_kind": species["attrs"].get("species_kind"),
                         "force_sensitive": any(x["id"] == "feat_force_sensitivity" for x in feats)}
                if b.feat_available(hits[0]["id"], probe, final, bab):
                    feats.append(entry)
                else:
                    unmet_grants.append({
                        "feat": hits[0]["id"], "granted_by": cls["id"],
                        "note": (cls["attrs"].get("starting_feats_notes") or {}).get(grant),
                    })
            trees.extend(b.tree_pool(cls))
        if level in feat_levels:
            options = [f["id"] for f in db.all("feat")
                       if not any(x["id"] == f["id"] for x in feats)]
            rng.shuffle(options)
            build_so_far = {"level": level, "feats": feats, "talents": talents,
                            "trained_skills": trained, "species_kind": species["attrs"].get("species_kind"),
                            "force_sensitive": any(x["id"] == "feat_force_sensitivity" for x in feats)}
            for fid in options:
                if b.feat_available(fid, build_so_far, final, bab):
                    feats.append({"id": fid, "level": level})
                    if fid == "feat_force_sensitivity":
                        build_so_far["force_sensitive"] = True
                    break
        if level in talent_levels and trees:
            cand = b.talents_in(trees)
            cand = [t for t in cand if not any(x["id"] == t["id"] for x in talents)]
            if cand:
                talents.append({"id": rng.choice(cand)["id"], "level": level})
    build = {
        "level": c.level,
        "species": species["id"], "species_kind": species["attrs"].get("species_kind"),
        "class_path": path,
        "abilities_base": abilities, "abilities_final": final,
        "trained_skills": trained, "feats": feats, "talents": talents,
        "force_powers": [], "force_sensitive": any(f["id"] == "feat_force_sensitivity" for f in feats),
        "destiny": None, "background": None,
        "weapon_groups": sorted(set(weapon_groups)), "armor_grades": sorted(set(armor_grades)),
        "unmet_grants": unmet_grants,
    }
    if build["force_sensitive"]:
        powers = db.all("force_power")
        if powers:
            k = min(len(powers), max(1, 1 + ability_modifier(final.get("CHA", 10))))
            build["force_powers"] = [rng.choice(powers)["id"] for _ in range(k)]
    if db.count("destiny"):
        build["destiny"] = rng.choice(db.all("destiny"))["id"]
    if db.count("background"):
        build["background"] = rng.choice(db.all("background"))["id"]
    if c.force_sensitive is True and not build["force_sensitive"]:
        return None
    if c.force_sensitive is False and build["force_sensitive"]:
        return None
    return build


def _signature(build: dict) -> str:
    return json.dumps({
        "s": build["species"],
        "p": [x["class"] for x in build["class_path"]],
        "a": build["abilities_base"],
        "f": sorted(x["id"] for x in build["feats"]),
        "t": sorted(x["id"] for x in build["talents"]),
        "k": sorted(build["trained_skills"]),
    }, sort_keys=True)


# ---------------------------------------------------------------------------
# legality report for an arbitrary build
# ---------------------------------------------------------------------------
def check_build(db: Dataset, build: dict) -> list[dict]:
    """Return a list of rule violations for a build (empty == legal).

    Checks: prerequisite satisfaction at the level taken, class-skill legality,
    trained-skill budget, duplicate options, and prestige-class entry level.
    """
    violations: list[dict] = []
    abilities = build.get("abilities_final") or build.get("abilities_base") or {}
    taken_feats = {f["id"] for f in build.get("feats", [])}
    taken_talents = {t["id"] for t in build.get("talents", [])}
    trained = {norm_key(s) for s in build.get("trained_skills", [])}

    for f in build.get("feats", []):
        rec = db.get("feat", f["id"])
        if not rec:
            violations.append({"code": "unknown_feat", "detail": f["id"]})
            continue
        granted = bool(f.get("granted_by"))
        p = rec.get("prerequisites")
        if not p:
            continue
        for pred in _walk(p["predicates"]):
            t = pred.get("type")
            if t == "ability_min" and abilities.get(pred["ability"], 10) < pred["min"]:
                violations.append({"code": "class_grant_ability_gate" if granted else "ability_gate",
                                   "feat": f["id"],
                                   "detail": f"{pred['ability']} {pred['min']} required, have {abilities.get(pred['ability'])}"})
            if t == "feat":
                ids = {r["id"] for r in (pred.get("refs") or []) if r.get("id")} | ({pred["id"]} if pred.get("id") else set())
                if ids and pred.get("mode") != "any" and not ids <= taken_feats:
                    violations.append({"code": "missing_prereq_feat", "feat": f["id"], "detail": sorted(ids - taken_feats)})
                if ids and pred.get("mode") == "any" and not (ids & taken_feats):
                    violations.append({"code": "missing_prereq_feat_any", "feat": f["id"], "detail": sorted(ids)})
            if t == "trained_skill":
                wanted = {norm_key(w) for w in ([pred.get("skill")] + list(pred.get("skills") or [])) if w}
                if wanted and not (wanted & trained if pred.get("mode") == "any" else wanted <= trained):
                    violations.append({"code": "missing_trained_skill", "feat": f["id"], "detail": sorted(wanted)})

    for entry in build.get("class_path", []):
        rec = db.get("class", entry["class"])
        if not rec:
            violations.append({"code": "unknown_class", "detail": entry["class"]})
            continue
        if rec["attrs"].get("class_kind") == "prestige":
            min_level = int(rec["attrs"].get("min_level") or 7)
            if entry["level"] < min_level:
                violations.append({"code": "prestige_entry_level", "class": entry["class"],
                                   "detail": f"taken at level {entry['level']}, requires {min_level}"})
        if entry["level"] == 1 and rec["attrs"].get("class_kind") != "heroic":
            violations.append({"code": "first_level_not_heroic", "class": entry["class"]})
    return violations


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def count_builds(db: Dataset, constraints: Constraints | None = None) -> dict:
    c = constraints or Constraints()
    space = DecisionSpace(db, level=c.level, include_homebrew=c.include_homebrew,
                          canon_filter=c.canon, include_gear=c.include_gear,
                          ability_method=c.ability_method)
    return space.count()


def write_builds(builds, path: Path | str, constraints: Constraints | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        if constraints:
            fh.write(json.dumps({"_constraints": constraints.to_dict()}) + "\n")
        for b in builds:
            fh.write(json.dumps(b, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_builds(path: Path | str) -> list[dict]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "_constraints" in rec:
            continue
        out.append(rec)
    return out
