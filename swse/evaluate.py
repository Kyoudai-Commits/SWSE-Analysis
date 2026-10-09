"""Stage 6: build evaluation.

Turns a build into numbers that can be compared, ranked and sliced. Every metric
is computed from the canonical data - nothing is hardcoded from memory of the
rulebook - and every formula is documented in :data:`METRICS` so a reviewer can
check it.

Metrics fall into three families:

**Power** - how strong the character is: offense, defense, durability, force.
**Breadth** - how much the character can do: skills, versatility, action types.
**Design quality** - how well the pieces fit: synergy (options in the build that
reference each other), redundancy (two options granting the same bonus),
prerequisite depth (how much of the build exists to unlock other things).

Where SWSE's printed progression tables are not present in the sources
(defense-bonus scaling, talent tiers, feat-per-level schedule), the formulas use
the assumption recorded in ``config/analysis.yaml`` and the metric is flagged
``verified: False``. That flag is part of the result, not a footnote: rankings
built on unverified rules must be reported as provisional.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .ids import fold, norm_key
from .space import ABILITY_KEYS, DecisionSpace, ability_modifier, load_assumptions
from .store import Dataset

# (metric, what it measures, formula, verified from data?)
METRICS: list[tuple[str, str, str, bool]] = [
    ("bab", "base attack bonus", "round(class.base_attack x level), summed over the class path", True),
    ("offense", "attack/damage output", "bab + best weapon damage die + attack-bonus feats + weapon mods for the chosen group", True),
    ("defense_reflex", "Reflex Defense", "10 + DEX mod + class defense bonus (+ scaling if the config says so)", False),
    ("defense_fortitude", "Fortitude Defense", "10 + CON mod + class defense bonus", False),
    ("defense_will", "Will Defense", "10 + WIS mod + class defense bonus", False),
    ("durability", "hit points + damage threshold",
     "level 1 = 3 x hit_die + CON mod (verified), each further level = hit_die + CON mod; DT = 10 + CON mod", True),
    ("skill_breadth", "trained skills", "count of trained skills", True),
    ("versatility", "distinct action types available", "distinct force-power action types + distinct skill abilities + combat stances", True),
    ("force_power", "Force capability", "count of known powers/techniques/secrets weighted by dark-side cost", True),
    ("synergy", "internal cohesion", "prereq-graph edges whose endpoints are both inside the build", True),
    ("redundancy", "wasted choices", "options granting the same (bonus type, target) signature", True),
    ("unlock_depth", "how much of the build exists to unlock more", "max prerequisite chain depth reached inside the build", True),
    ("option_count", "how many choices the build commits to", "feats + talents + powers + skills + classes", True),
]

_BONUS_TYPES = r"competence|morale|dodge|circumstance|insight|luck|penalty|equipment|armor"
_TARGET = r"[a-z ,()/-]{2,60}"

# A bonus must be *either* explicitly signed ("+2 to Reflex", "-2 penalty to ...")
# *or* explicitly labelled ("2 bonus to attack rolls"). Matching any bare number
# before "to"/"on" read "take 20 on a trained Knowledge check" and "roll a natural
# 20 on an attack roll" as +20 bonuses - the second one landed in `offense`, because
# its target contains "attack". Found by the canon-balance audit (TASK-018).
_BONUS_SIGNED_RE = re.compile(
    rf"(?P<sign>[+-]\d+)\s*(?P<type>{_BONUS_TYPES})?\s*(?:bonus|penalty)?\s*(?:to|on)\s*(?P<target>{_TARGET})",
    re.I)
_BONUS_LABELLED_RE = re.compile(
    rf"(?<![+-])\b(?P<sign>\d+)\s*(?P<type>{_BONUS_TYPES})?\s*(?:bonus|penalty)\s+(?:to|on)\s*(?P<target>{_TARGET})",
    re.I)
_DIE_RE = re.compile(r"\b(?P<n>\d+)d(?P<sides>\d+)(?P<plus>\+\d+)?\b")


@dataclass
class Scores:
    build: dict
    metrics: dict[str, float] = field(default_factory=dict)
    parts: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.metrics.get("total", 0.0)

    def to_dict(self) -> dict:
        return {"metrics": self.metrics, "parts": self.parts, "warnings": self.warnings}


class Evaluator:
    def __init__(self, db: Dataset | None = None, weights: dict | None = None):
        self.db = db or Dataset.load()
        self.a = load_assumptions()
        w = (weights or self.a.get("scoring", {}).get("weights") or {})
        self.weights = {k: float(v) for k, v in w.items()}
        self.space = DecisionSpace(self.db, level=1)
        self._bonus_cache: dict[str, list[tuple[str, str, int]]] = {}
        self._graph = None

    # ------------------------------------------------------------------ text
    def bonuses_in(self, text: Any) -> list[tuple[str, str, int]]:
        """Extract ``(type, target, amount)`` bonus signatures from rules text."""
        s = fold(text)
        if not s:
            return []
        key = s[:120]
        if key in self._bonus_cache:
            return self._bonus_cache[key]
        out = []
        seen = set()
        for regex in (_BONUS_SIGNED_RE, _BONUS_LABELLED_RE):
            for m in regex.finditer(s):
                amt = int(m.group("sign").replace("+", "") or 0)
                btype = (m.group("type") or "untyped").lower()
                target = fold(m.group("target")).strip(" .,")[:40]
                if target and (btype, target, amt) not in seen:
                    seen.add((btype, target, amt))
                    out.append((btype, target, amt))
        self._bonus_cache[key] = out
        return out

    @staticmethod
    def damage_value(damage: Any) -> float:
        """Average damage of a weapon.

        ``damage`` is structured in the canonical data and takes three shapes
        (see the ``weapon_stats`` hook): dice ``{"multiplier": 3, "die_size": 6,
        "bonus": null}``, flat ``{"flat": 1}`` for unarmed-style weapons, and
        ``{"special": "special"}`` for weapons with no numeric damage. Free text
        such as ``"3d6+2"`` is also accepted so the evaluator works on both.
        """
        best = 0.0
        if isinstance(damage, list):
            for entry in damage:
                if not isinstance(entry, dict):
                    continue
                bonus = float(entry.get("bonus") or 0)
                if entry.get("special"):
                    continue                      # "special" has no numeric damage
                if entry.get("flat") is not None:
                    # unarmed-style weapons deal a flat number of points
                    best = max(best, float(entry["flat"]) + bonus)
                    continue
                n = int(entry.get("multiplier") or 0)
                sides = int(entry.get("die_size") or 0)
                if n and sides:
                    best = max(best, n * (sides + 1) / 2 + bonus)
        elif isinstance(damage, dict):
            best = Evaluator.damage_value([damage])
        else:
            for m in _DIE_RE.finditer(fold(damage)):
                n, sides = int(m.group("n")), int(m.group("sides"))
                best = max(best, n * (sides + 1) / 2 + int((m.group("plus") or "+0").replace("+", "") or 0))
        return best

    def best_damage_die(self, text: Any) -> float:
        return self.damage_value(text)

    # ------------------------------------------------------------- build bits
    def records_for(self, build: dict) -> dict:
        db = self.db
        out = {
            "species": db.get("species", build.get("species")) if build.get("species") else None,
            "classes": [db.get("class", e["class"]) for e in build.get("class_path", [])],
            "feats": [db.get("feat", f["id"]) for f in build.get("feats", []) if db.get("feat", f["id"])],
            "talents": [db.get("talent", t["id"]) for t in build.get("talents", []) if db.get("talent", t["id"])],
            "force_powers": [db.get("force_power", p) for p in build.get("force_powers", []) if db.get("force_power", p)],
            "destiny": db.get("destiny", build.get("destiny")) if build.get("destiny") else None,
            "background": db.get("background", build.get("background")) if build.get("background") else None,
        }
        out["classes"] = [c for c in out["classes"] if c]
        return out

    def bab(self, build: dict, recs: dict) -> float:
        total = 0.0
        for entry, rec in zip(build.get("class_path", []), recs["classes"]):
            rate = rec["attrs"].get("base_attack")
            rate = float(rate) if rate not in (None, "") else 0.75
            total += rate
        return round(total)

    def defense(self, build: dict, recs: dict, key: str, ability: str) -> float:
        level = build.get("level", 1)
        abilities = build.get("abilities_final") or build.get("abilities_base") or {}
        base = 10 + ability_modifier(abilities.get(ability, 10))
        field_map = {"defense_reflex": "reflex_progression",
                     "defense_fortitude": "fortitude_progression",
                     "defense_will": "will_progression"}
        attr = field_map[key]
        conf = self.a.get("defense_progression", {})
        heroic, prestige = conf.get("heroic", {}), conf.get("prestige", {})
        bonus = 0.0
        scaled = False
        for rec in recs["classes"]:
            v = rec["attrs"].get(attr)
            if v in (None, ""):
                continue
            v = float(v)
            if rec["attrs"].get("class_kind") == "prestige":
                divisor = float(prestige.get("prestige_divisor", 2) or 1)
                v = v / divisor
                scaled = True
            bonus += v
        if scaled:
            self._defense_scaled = True
        spec = prestige if scaled else heroic
        if spec.get("scale_with_level"):
            bonus += float(spec.get("per_level", 0)) * (level - 1)
        return base + bonus

    def durability(self, build: dict, recs: dict) -> dict:
        abilities = build.get("abilities_final") or build.get("abilities_base") or {}
        con = ability_modifier(abilities.get("CON", 10))
        hp = 0
        for i, rec in enumerate(recs["classes"]):
            die = rec["attrs"].get("hit_die")
            die = int(die) if isinstance(die, str) and die.isdigit() else die
            if not die:
                die = 6
                warnings_missing_hit_die = True
            else:
                warnings_missing_hit_die = False
            # 1st level grants three hit dice (verified against the printed
            # "starting hit points" column of all five heroic classes)
            hp += (3 * int(die) if i == 0 else int(die)) + con
        dt = 10 + con
        return {"hp": hp, "damage_threshold": dt, "con_mod": con,
                "levels_missing_hit_die": bool(locals().get("warnings_missing_hit_die"))}

    def offense(self, build: dict, recs: dict, bab: float) -> dict:
        # best weapon the build is proficient with, by average damage
        abilities = build.get("abilities_final") or build.get("abilities_base") or {}
        proficient_groups = self._proficient_groups(recs)
        candidates = []
        for w in self.db.all("weapon"):
            group = fold(w["attrs"].get("weapon_group")).lower()
            code = fold(w["attrs"].get("proficiency")).upper()
            # WP = needs Weapon Proficiency (group); EWP = needs the exotic feat
            # for that specific weapon; U/I = unarmed/improvised, no feat needed.
            # Anything else (mines, vehicle weapons, starship guns) is not a
            # personal weapon a character can be assumed to swing.
            wieldable = (code == "WP" and group in proficient_groups) or code in {"U", "I"}
            if not wieldable:
                continue
            dmg = self.best_damage_die(w["attrs"].get("damage"))
            if dmg:
                candidates.append((dmg, w["name"], group))
        candidates.sort(reverse=True)
        best = candidates[0] if candidates else (0, None, None)
        attack_bonus = bab + ability_modifier(abilities.get("DEX", 10))
        feat_bonuses = 0
        for f in recs["feats"]:
            for _t, target, amt in self.bonuses_in(f["attrs"].get("summary")):
                if "attack" in target.lower():
                    feat_bonuses += amt
        return {
            "bab": bab, "best_weapon": best[1], "best_weapon_damage": best[0],
            "best_weapon_group": best[2], "attack_bonus": attack_bonus,
            "feat_attack_bonus": feat_bonuses, "weapon_candidates": len(candidates),
        }

    def _proficient_groups(self, recs: dict) -> set[str]:
        groups: set[str] = set()
        for c in recs["classes"]:
            for f in c["attrs"].get("starting_feats") or []:
                m = re.search(r"weapon proficiency\s*\(([^)]+)\)", fold(f), re.I)
                if m:
                    groups.add(m.group(1).lower())
                elif fold(f).lower().startswith("weapon proficiency"):
                    groups.update({"simple", "pistols", "rifles", "heavy", "lightsabers", "advanced melee"})
        for f in recs["feats"]:
            for src in (f["attrs"].get("summary"), f["name"]):
                m = re.search(r"weapon proficiency\s*\(([^)]+)\)", fold(src), re.I)
                if m:
                    groups.add(m.group(1).lower())
        return groups or {"simple", "pistols", "rifles", "heavy", "lightsabers", "advanced melee"}

    def force(self, build: dict, recs: dict) -> dict:
        powers = recs["force_powers"]
        dark = sum(1 for p in powers if "dark side" in fold(p["attrs"].get("alignment")).lower())
        uses = sum(int(p["attrs"].get("uses") or 0) for p in powers)
        return {"powers": len(powers), "dark_side_powers": dark, "total_uses": uses,
                "force_sensitive": bool(build.get("force_sensitive"))}

    def versatility(self, build: dict, recs: dict) -> dict:
        action_types = {fold(p["attrs"].get("action_type")) for p in recs["force_powers"] if p["attrs"].get("action_type")}
        skills = build.get("trained_skills", [])
        abilities_covered = set()
        for s in skills:
            rec = self.db.find("skill", s)
            if rec:
                abilities_covered.add(fold(rec[0]["attrs"].get("ability")))
        stances = sum(1 for t in recs["talents"] if "stance" in fold(t["attrs"].get("summary")).lower())
        return {"action_types": len(action_types), "skill_abilities_covered": len(abilities_covered),
                "stances": stances, "distinct_skills": len(set(map(norm_key, skills)))}

    def synergy(self, build: dict, recs: dict) -> dict:
        """How many prerequisite edges point *inside* the build.

        A build where every feat exists to unlock another feat is cohesive; a
        build of unrelated options is broad but shallow. Both are interesting.
        """
        from .graph import PrereqGraph
        if self._graph is None:
            # building the graph costs ~1s; scoring hundreds of builds must not
            # pay that per build
            self._graph = PrereqGraph(self.db)
        g = self._graph
        inside = {build.get("species")} | {f["id"] for f in build.get("feats", [])} \
            | {t["id"] for t in build.get("talents", [])} | {p for p in build.get("force_powers", [])} \
            | {e["class"] for e in build.get("class_path", [])} | {build.get("destiny"), build.get("background")}
        inside.discard(None)
        internal = 0
        total = 0
        depths = g.depth()
        for src in inside:
            for e in g.requires(src):
                if not e.get("req_id"):
                    continue
                total += 1
                if e["req_id"] in inside:
                    internal += 1
        depth = max((depths.get(s, 0) for s in inside), default=0)
        trees = {norm_key(t["attrs"].get("tree") or "") for t in recs["talents"]}
        classes_trees = set()
        for c in recs["classes"]:
            classes_trees |= {norm_key(t) for t in (c["attrs"].get("talent_trees") or [])}
        tree_alignment = len(trees & classes_trees)
        return {"internal_edges": internal, "outgoing_edges": total, "max_depth": depth,
                "tree_alignment": tree_alignment, "cohesion": round(internal / total, 3) if total else 0.0}

    def redundancy(self, build: dict, recs: dict) -> dict:
        """Options that grant the same (bonus type, target) signature."""
        sigs = Counter()
        per_option = {}
        for kind, items in (("feat", recs["feats"]), ("talent", recs["talents"])):
            for r in items:
                found = self.bonuses_in(r["attrs"].get("summary"))
                for sig in found:
                    sigs[sig] += 1
                    per_option.setdefault(sig, []).append(r["name"])
        dupes = {f"{t} bonus to {target}": names for (t, target, _amt), names in per_option.items() if sigs[(t, target, _amt)] > 1}
        return {"duplicate_signatures": len(dupes), "details": dupes}

    # ------------------------------------------------------------------ score
    def score(self, build: dict) -> Scores:
        recs = self.records_for(build)
        warnings: list[str] = []
        if not recs["classes"]:
            warnings.append("build has no class records")
        bab = self.bab(build, recs)
        off = self.offense(build, recs, bab)
        dur = self.durability(build, recs)
        forc = self.force(build, recs)
        vers = self.versatility(build, recs)
        syn = self.synergy(build, recs)
        red = self.redundancy(build, recs)
        abilities = build.get("abilities_final") or build.get("abilities_base") or {}
        metrics = {
            "bab": bab,
            "offense": off["attack_bonus"] + off["best_weapon_damage"] + off["feat_attack_bonus"],
            "defense_reflex": self.defense(build, recs, "defense_reflex", "DEX"),
            "defense_fortitude": self.defense(build, recs, "defense_fortitude", "CON"),
            "defense_will": self.defense(build, recs, "defense_will", "WIS"),
            "durability": dur["hp"] + dur["damage_threshold"],
            "skill_breadth": len(set(map(norm_key, build.get("trained_skills", [])))),
            "versatility": vers["action_types"] + vers["skill_abilities_covered"] + vers["stances"],
            "force_power": forc["powers"] * 2 + forc["total_uses"] - forc["dark_side_powers"],
            "synergy": syn["internal_edges"] + syn["tree_alignment"],
            "redundancy": -red["duplicate_signatures"],
            "unlock_depth": syn["max_depth"],
            "option_count": (len(recs["feats"]) + len(recs["talents"]) + len(recs["force_powers"])
                             + len(set(build.get("trained_skills", []))) + len(recs["classes"])),
            "power_total": sum(ability_modifier(abilities.get(k, 10)) for k in ABILITY_KEYS),
        }
        # unverified metrics must be flagged in the output
        for name, _label, _formula, verified in METRICS:
            if not verified and name in metrics:
                warnings.append(f"metric '{name}' rests on an unverified rule assumption")
        if getattr(self, "_defense_scaled", False):
            warnings.append("prestige-class defence bonus divided by "
                            f"{self.a.get('defense_progression', {}).get('prestige', {}).get('prestige_divisor', 2)}"
                            " (unverified encoding, see config/analysis.yaml)")
        metrics["total"] = round(sum(metrics[k] * self.weights.get(k, 0.0) for k in metrics), 3)
        parts = {"offense": off, "durability": dur, "force": forc, "versatility": vers,
                 "synergy": syn, "redundancy": red, "abilities": abilities}
        return Scores(build=build, metrics=metrics, parts=parts, warnings=warnings)

    def score_many(self, builds: list[dict]) -> list[Scores]:
        return [self.score(b) for b in builds]


def rank(scores: list[Scores], key: str = "total", descending: bool = True) -> list[Scores]:
    return sorted(scores, key=lambda s: s.metrics.get(key, 0), reverse=descending)


def summary_table(scores: list[Scores], top: int = 20, key: str = "total") -> list[list[str]]:
    rows = [["rank", key] + ["species", "class_path", "level", "feats"]]
    for i, s in enumerate(rank(scores, key)[:top], 1):
        b = s.build
        rows.append([str(i), f"{s.metrics.get(key, 0):.2f}",
                     str(b.get("species")), " > ".join(e["class"] for e in b.get("class_path", [])),
                     str(b.get("level")), str(len(b.get("feats", [])))])
    return rows
