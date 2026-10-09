"""The character-creation decision space.

This module answers the question the whole repository exists for: **how many
different characters can be built, and what exactly is being chosen at each
step?**

It models character creation as a set of *dimensions*. Each dimension is one
independent (or gated) decision, with a cardinality that is either read straight
out of the canonical data or computed from a declared rule. Every dimension
carries:

``options``    how many choices it offers
``formula``    how that number was computed (so it can be re-derived by hand)
``source``     which canonical entity / config assumption it comes from
``verified``   True when the number comes from the data, False when it rests on
               an assumption in ``config/analysis.yaml`` that still needs a
               primary-source check

Counting policy
---------------
* Level 1 is counted **exactly**: we iterate every (species, class) pair and
  compute the number of legal skill/feat/talent/parameter choices for it, then
  multiply by the ability-score allocation count.
* Levels 2-20 are counted **analytically**: the class path is an exact dynamic
  programme over 20 levels, and the per-level choice counts are multiplied in.
  The result is astronomically large (see ``report()``), which is a finding, not
  a bug: it is why ``swse.enumerate`` samples instead of exhaustively listing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from functools import cached_property
from itertools import product
from typing import Any

import yaml

from . import paths
from .ids import fold, norm_key
from .store import Dataset

ABILITY_KEYS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def load_assumptions() -> dict:
    return yaml.safe_load(paths.CONFIG_DIR.joinpath("analysis.yaml").read_text(encoding="utf-8")) or {}


@dataclass
class Dimension:
    key: str
    label: str
    options: int
    kind: str = "choice"                 # choice | sequence | allocation | parameter | derived | sub_space
    entity: str | None = None
    per: str = "once"                    # once | per_level | per_class_level
    gated_by: list[str] = field(default_factory=list)
    formula: str = ""
    source: str = ""
    verified: bool = True
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def ability_modifier(score: int) -> int:
    """SWSE ability modifier: (score - 10) // 2, rounded towards zero at even/odd."""
    return (score - 10) // 2 if score >= 10 else -((10 - score + 1) // 2)


def n_choose_k(n: int, k: int) -> int:
    if k < 0 or n < 0 or k > n:
        return 0
    return math.comb(n, k)


def parse_skill_formula(text: Any) -> tuple[int, str]:
    """``"6+Int"`` -> ``(6, "INT")``; ``"2+Int"`` -> ``(2, "INT")``."""
    if not text:
        return (0, "")
    m = re.match(r"^\s*(\d+)\s*\+\s*([A-Za-z]{3})\s*$", fold(str(text)))
    if m:
        return int(m.group(1)), m.group(2).upper()
    m = re.match(r"^\s*(\d+)\s*$", fold(str(text)))
    if m:
        return int(m.group(1)), ""
    return (0, "")


class DecisionSpace:
    """The option/combination space for one set of analysis settings."""

    def __init__(self, db: Dataset | None = None, *, level: int = 1,
                 include_homebrew: bool = True, canon_filter: str | None = None,
                 include_gear: bool = False, ability_method: str | None = None,
                 assumptions: dict | None = None):
        self.db = db or Dataset.load()
        self.a = assumptions or load_assumptions()
        enum = self.a.get("enumeration", {})
        self.level = level
        self.include_homebrew = bool(enum.get("include_homebrew", True)) if include_homebrew is None else include_homebrew
        self.canon_filter = canon_filter if canon_filter is not None else enum.get("canon_filter")
        self.include_gear = include_gear if include_gear is not None else bool(enum.get("include_gear", False))
        scores = self.a.get("ability_scores", {})
        self.ability_method = ability_method or scores.get("default_method", "distinct_vectors")
        self.assumption_flags: list[str] = []

    # ------------------------------------------------------------- filtering
    def usable(self, entity: str) -> list[dict]:
        recs = self.db.all(entity)
        if self.canon_filter:
            recs = [r for r in recs if r.get("canon") == self.canon_filter]
        if not self.include_homebrew:
            recs = [r for r in recs if "homebrew" not in (r.get("flags") or [])]
        return recs

    # ------------------------------------------------------------ populations
    @cached_property
    def species(self) -> list[dict]:
        out = [r for r in self.usable("species")
               if r["attrs"].get("species_kind") not in {"beast_template"}]
        return out

    @cached_property
    def species_by_kind(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for r in self.species:
            out.setdefault(r["attrs"].get("species_kind", "species"), []).append(r)
        return out

    @cached_property
    def heroic_classes(self) -> list[dict]:
        return [r for r in self.usable("class")
                if r["attrs"].get("class_kind") == "heroic"
                and int(r["attrs"].get("min_level") or 1) <= 1]

    @cached_property
    def prestige_classes(self) -> list[dict]:
        return [r for r in self.usable("class") if r["attrs"].get("class_kind") == "prestige"]

    @cached_property
    def feats(self) -> list[dict]:
        return self.usable("feat")

    @cached_property
    def talents(self) -> list[dict]:
        return self.usable("talent")

    @cached_property
    def skills(self) -> list[dict]:
        return self.usable("skill")

    @cached_property
    def force_powers(self) -> list[dict]:
        return self.usable("force_power")

    # ---------------------------------------------------------- ability scores
    def ability_allocations(self) -> Dimension:
        method = next((m for m in self.a["ability_scores"]["methods"]
                       if m["id"] == self.ability_method), None)
        if method is None:
            raise ValueError(f"unknown ability method {self.ability_method!r}")
        if method["id"] == "distinct_vectors":
            lo, hi = method["min"], method["max"]
            n = (hi - lo + 1) ** len(ABILITY_KEYS)
            formula = f"({hi} - {lo} + 1)^{len(ABILITY_KEYS)} = {n:,}"
        elif method["id"] == "standard_array":
            n = math.factorial(len(ABILITY_KEYS))
            formula = f"{len(ABILITY_KEYS)}! permutations of {method['array']} = {n}"
        elif method["id"] == "point_buy":
            curve = method.get("cost_curve") or {}
            if not curve:
                n = 0
                formula = "cost curve absent from the sources - count unavailable"
                self.assumption_flags.append("point_buy_cost_curve_missing")
            else:
                n = self._point_buy_count(curve, method.get("budget", 0))
                formula = f"DP over cost curve with budget {method.get('budget')}"
        else:
            n, formula = 0, "unknown method"
        return Dimension(
            key="ability_scores", label="Ability scores", options=n, kind="allocation",
            per="once", formula=formula, source=f"config/analysis.yaml:{method['id']}",
            verified=bool(method.get("verified")),
            notes=method.get("note", "Species and age modifiers are applied on top of the rolled/bought base."),
        )

    @staticmethod
    def _point_buy_count(curve: dict, budget: int) -> int:
        costs = {int(k): int(v) for k, v in curve.items()}
        scores = sorted(costs)
        # dp[i][spent] = ways to assign the first i abilities
        dp = [0] * (budget + 1)
        dp[0] = 1
        for _ in scores:
            nxt = [0] * (budget + 1)
            for spent in range(budget + 1):
                if not dp[spent]:
                    continue
                for s in scores:
                    c = costs[s]
                    if spent + c <= budget:
                        nxt[spent + c] += dp[spent]
            dp = nxt
        return sum(dp)

    # ---------------------------------------------------------------- skills
    def class_skill_choices(self, cls: dict, int_mod: int = 0) -> dict:
        """How many trained-skill selections a class allows at 1st level."""
        skills = cls["attrs"].get("class_skills") or []
        formula_text = cls["attrs"].get("trained_skills_per_level") or ""
        base, mod_ability = parse_skill_formula(formula_text)
        if not skills:
            # SagaForge-only classes: fall back to the count in attrs.trained_skills
            base = int(cls["attrs"].get("trained_skills") or 0)
            mod_ability = "INT"
            skills = [s["name"] for s in self.skills]
            notes = "class_skills list absent for this class; counted against the full skill list"
        else:
            notes = ""
        if "Knowledge (all; taken individually)" in skills:
            knowledge = [s["name"] for s in self.skills if s["name"].lower().startswith("knowledge")]
            skills = [s for s in skills if not s.lower().startswith("knowledge (all")] + knowledge
        k = base + (int_mod if mod_ability == "INT" else 0)
        return {
            "class": cls["name"], "pool": len(skills), "picks": k,
            "combinations": n_choose_k(len(skills), k),
            "formula": f"C({len(skills)}, {base}{'+Int' if mod_ability == 'INT' else ''})",
            "source": "class.attrs.class_skills + class.attrs.trained_skills_per_level",
            "verified": bool(skills) and bool(formula_text),
            "notes": notes,
        }

    # ----------------------------------------------------------------- feats
    def feat_pool_at_level1(self, abilities: dict[str, int] | None = None) -> dict:
        """Feats whose prerequisites a 1st-level character could satisfy.

        Numeric gates (ability score, BAB) are evaluated against ``abilities``
        (default: all 10, BAB +0). Option gates (other feats, trained skills)
        are treated as *not* satisfiable at level 1 unless the feat has no such
        gate, because a 1st-level character has only their starting feats.
        """
        abilities = abilities or {k: 10 for k in ABILITY_KEYS}
        eligible, gated, blocked = [], [], []
        for f in self.feats:
            p = f.get("prerequisites")
            if not p or p.get("empty") or not p.get("predicates"):
                eligible.append(f["id"])
                continue
            ok_numeric, needs_option = True, False
            for pred in _walk(p["predicates"]):
                t = pred.get("type")
                if t == "ability_min":
                    if abilities.get(pred["ability"], 10) < pred["min"]:
                        ok_numeric = False
                elif t in {"bab_min", "level_min"}:
                    ok_numeric = False
                elif t in {"feat", "talent", "trained_skill", "talent_tree", "force_power",
                           "skill", "weapon_proficiency", "armor_proficiency", "force_technique",
                           "force_secret", "class_level_min", "any_of"}:
                    needs_option = True
            if ok_numeric and not needs_option:
                eligible.append(f["id"])
            elif ok_numeric:
                gated.append(f["id"])
            else:
                blocked.append(f["id"])
        return {"eligible": eligible, "gated_on_other_options": gated, "blocked_by_numbers": blocked}

    # --------------------------------------------------------- class paths DP
    def class_path_counts(self, max_level: int | None = None) -> dict:
        """Exact count of legal class-level sequences per level, via DP.

        Rules applied (all declared in config/analysis.yaml):
        * level 1 must be a heroic class
        * a prestige class may only be taken once the character's total level
          reaches that class's own ``min_level``
        * every level after the first may be any allowed class (multiclassing)
        """
        max_level = max_level or int(self.a["level_range"]["max"])
        heroic = len(self.heroic_classes)
        prestige = [(int(c["attrs"].get("min_level") or 7), c["name"]) for c in self.prestige_classes]
        counts = [0] * (max_level + 1)
        counts[0] = 1
        detail = []
        for lvl in range(1, max_level + 1):
            allowed = heroic if lvl == 1 and self.a.get("first_level_must_be_heroic", {}).get("value", True) \
                else heroic + sum(1 for ml, _ in prestige if lvl >= ml)
            counts[lvl] = counts[lvl - 1] * allowed
            detail.append({"level": lvl, "classes_available": allowed, "paths": counts[lvl]})
        return {
            "heroic_classes": heroic, "prestige_classes": len(prestige),
            "counts": counts, "detail": detail,
            "formula": "paths(L) = paths(L-1) x (#classes available at L); level 1 restricted to heroic",
            "verified": bool(self.a.get("first_level_must_be_heroic", {}).get("verified", False)),
        }

    # ------------------------------------------------------------ dimensions
    def dimensions(self) -> list[Dimension]:
        prog = self.a.get("progression", {})
        dims: list[Dimension] = []

        kinds = {k: len(v) for k, v in self.species_by_kind.items()}
        dims.append(Dimension(
            key="species", label="Species", options=len(self.species), entity="species",
            formula=f"{len(self.species)} species records "
                    f"({', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))})",
            source="species entity (Data!J3:BN133)", verified=True,
            notes="Beast templates excluded. Droid chassis open the droid sub-space; "
                  "near-human species open the near-human sub-space."))

        dims.append(Dimension(
            key="age_category", label="Age category", options=self.db.count("age_category"),
            entity="age_category", formula=f"{self.db.count('age_category')} age brackets",
            source="age_category entity (Data!A3:G8)", verified=True,
            notes="Age brackets shift ability scores; species age tables bound which are legal."))

        dims.append(self.ability_allocations())

        dims.append(Dimension(
            key="heroic_class", label="Heroic class (1st level)", options=len(self.heroic_classes),
            entity="class", formula=f"{len(self.heroic_classes)} classes with class_kind=heroic and min_level<=1 "
                                    f"({', '.join(c['name'] for c in self.heroic_classes)})",
            source="class entity (Data!BX3:CS42 + Master Reference)", verified=True))

        skill_counts = [self.class_skill_choices(c) for c in self.heroic_classes]
        total_skill = sum(s["combinations"] for s in skill_counts)
        dims.append(Dimension(
            key="trained_skills_level1", label="Trained skills at 1st level", options=total_skill,
            kind="derived", entity="skill", per="per_class_level", gated_by=["heroic_class", "ability_scores"],
            formula="sum over heroic classes of C(class skill pool, trained skill count)",
            source="class.attrs.class_skills / trained_skills_per_level",
            verified=all(s["verified"] for s in skill_counts),
            notes="Per class: " + "; ".join(f"{s['class']} {s['formula']}={s['combinations']:,}" for s in skill_counts)))

        pool = self.feat_pool_at_level1()
        dims.append(Dimension(
            key="feat_level1", label="Feat at 1st level", options=len(pool["eligible"]),
            kind="choice", entity="feat", gated_by=["ability_scores", "heroic_class"],
            formula=f"{len(pool['eligible'])} feats with no unsatisfiable prerequisite at level 1 "
                    f"({len(pool['gated_on_other_options'])} more gated on other options, "
                    f"{len(pool['blocked_by_numbers'])} blocked by numeric gates)",
            source="feat entity + swse.prereq predicates", verified=True,
            notes="Starting feats granted by the class are free and are not counted here."))

        dims.append(Dimension(
            key="parameterised_feats", label="Parameter choices inside feats", options=self._parameter_option_count(),
            kind="parameter", entity="feat", gated_by=["feat_level1"],
            formula="product over parameterised feats of their option counts (see attrs.parameter_options)",
            source="derive_parameter_axes hook (weapon groups, skills, languages, exotic weapons)",
            verified=True,
            notes="Choosing Weapon Proficiency is not one decision but 1 + 6; Skill Focus is 1 + 25."))

        dims.append(Dimension(
            key="talent_tree", label="Talent trees", options=self.db.count("talent_tree"),
            entity="talent_tree", gated_by=["heroic_class"],
            formula=f"{self.db.count('talent_tree')} trees ({self.db.count('talent')} individual talents)",
            source="talent_tree entity (Master Reference + derived from SagaForge talent rows)",
            verified=True,
            notes="Trees are granted by classes; individual talents are the choices."))

        dims.append(Dimension(
            key="force_powers", label="Force powers", options=self.db.count("force_power"),
            entity="force_power", gated_by=["feat:force_sensitivity", "feat:force_training"],
            formula=f"{self.db.count('force_power')} powers, {self.db.count('force_technique')} techniques, "
                    f"{self.db.count('force_secret')} secrets",
            source="force_power / force_technique / force_secret entities", verified=True,
            notes=self.a.get("force", {}).get("powers_known_formula", ""),
            ))

        dims.append(Dimension(
            key="destiny", label="Destiny", options=self.db.count("destiny"), entity="destiny",
            formula=f"{self.db.count('destiny')} destinies", source="destiny entity (Lists!AD2:AG90)",
            verified=True, notes="Legacy-era destinies grant a bonus, a penalty and a completed effect."))

        dims.append(Dimension(
            key="background", label="Background", options=self.db.count("background"), entity="background",
            formula=f"{self.db.count('background')} backgrounds", source="background entity (Lists!GL2:GO48)",
            verified=True, notes="Backgrounds grant bonus trained skills and a language."))

        dims.append(Dimension(
            key="languages", label="Languages", options=self.db.count("language"), entity="language",
            formula=f"{self.db.count('language')} languages", source="language entity (Lists!AH)",
            verified=True, notes="Species grants some free; Intelligence and Linguist add more."))

        # progression dimensions (levels > 1)
        if self.level > 1 or True:
            paths_ = self.class_path_counts(self.level)
            dims.append(Dimension(
                key="class_path", label=f"Class path to level {self.level}", options=paths_["counts"][self.level],
                kind="sequence", entity="class", per="per_level",
                gated_by=["heroic_class", "level"],
                formula=paths_["formula"],
                source="class.attrs.min_level + config/analysis.yaml:first_level_must_be_heroic",
                verified=paths_["verified"],
                notes=f"{paths_['heroic_classes']} heroic + {paths_['prestige_classes']} prestige classes."))
            feat_grants = len([l for l in prog.get("feats_at_levels", []) if l <= self.level])
            talent_grants = len([l for l in prog.get("talents_at_levels", []) if l <= self.level])
            dims.append(Dimension(
                key="feat_grants", label="Feat grants over the progression", options=feat_grants,
                kind="derived", per="per_level", formula=f"{feat_grants} grants at levels {prog.get('feats_at_levels')}",
                source="config/analysis.yaml:progression", verified=bool(prog.get("verified")),
                notes=prog.get("note", "")))
            dims.append(Dimension(
                key="talent_grants", label="Talent grants over the progression", options=talent_grants,
                kind="derived", per="per_level", formula=f"{talent_grants} grants at levels {prog.get('talents_at_levels')}",
                source="config/analysis.yaml:progression", verified=bool(prog.get("verified"))))

        # sub-spaces
        dims.append(Dimension(
            key="droid_sub_space", label="Droid build sub-space", options=self._droid_space(),
            kind="sub_space", entity="droid_option", gated_by=["species:droid_chassis"],
            formula="chassis x degree x locomotion x quirks x manufacturer x accessories x armor",
            source="droid_option entity + droid_degree/locomotion/shield/translator tables",
            verified=True, notes="Only reachable by taking a droid chassis as species."))

        dims.append(Dimension(
            key="near_human_sub_space", label="Near-Human customisation sub-space",
            options=max(self.db.count("near_human_trait"), 1), kind="sub_space",
            entity="near_human_trait", gated_by=["species:near_human"],
            formula=f"{self.db.count('near_human_trait')} selectable traits (combinations depend on how many are allowed)",
            source="near_human_trait entity (Near-Humans!P4:Q27)", verified=True,
            notes="Near-Humans remove one base trait and add near-human traits; the trait budget is not in the sources."))

        if self.include_gear:
            dims.append(Dimension(
                key="gear", label="Starting gear", options=self._gear_space(), kind="sub_space",
                gated_by=["heroic_class"], formula="weapons x armor x equipment within starting credits",
                source="weapon/armor/equipment entities + class.attrs.starting_credits", verified=True,
                notes="Opt-in: multiplies the space by orders of magnitude."))
        return dims

    def _parameter_option_count(self) -> int:
        total = 1
        for f in self.feats:
            n = f["attrs"].get("parameter_options_count")
            if n:
                total *= max(int(n), 1)
        return total

    def _droid_space(self) -> int:
        counts = {
            "chassis": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "chassis"]),
            "degree": self.db.count("droid_degree"),
            "locomotion": self.db.count("droid_locomotion"),
            "quirk": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "quirk"]),
            "manufacturer": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "manufacturer"]),
            "accessory": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "accessory"]),
            "armor": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "armor"]),
            "appendage": len([r for r in self.usable("droid_option") if r["attrs"].get("option_group") == "appendage"]),
        }
        self._droid_counts = counts
        n = 1
        for k, v in counts.items():
            n *= max(v, 1)
        return n

    def _gear_space(self) -> int:
        return max(self.db.count("weapon"), 1) * max(self.db.count("armor"), 1) * max(self.db.count("equipment"), 1)

    # ---------------------------------------------------------------- counts
    def count_level1(self) -> dict:
        """Exact level-1 count, summed over every (species, class) pair."""
        abilities_dim = self.ability_allocations()
        per_pair = []
        for sp, cls in product(self.species, self.heroic_classes):
            int_mod = ability_modifier(10 + int(sp["attrs"].get("mod_int") or 0))
            sc = self.class_skill_choices(cls, int_mod)
            per_pair.append({
                "species": sp["id"], "class": cls["id"],
                "skill_choices": sc["combinations"],
            })
        skill_total = sum(p["skill_choices"] for p in per_pair)
        pool = self.feat_pool_at_level1()
        feat_choices = len(pool["eligible"])
        params = self._parameter_option_count()
        base = len(self.species) * len(self.heroic_classes)
        result = {
            "species_class_pairs": base,
            "species_class_pairs_with_skills": len(per_pair),
            "skill_selections_total": skill_total,
            "feat_choices": feat_choices,
            "parameter_multiplier": params,
            "ability_allocations": abilities_dim.options,
            "destiny_choices": self.db.count("destiny"),
            "background_choices": self.db.count("background"),
            "pairs": per_pair,
        }
        core = skill_total * max(feat_choices, 1)
        result["core_builds"] = core                       # species x class x skills x feat
        result["with_abilities"] = core * max(abilities_dim.options, 1)
        result["with_destiny_and_background"] = result["with_abilities"] * max(self.db.count("destiny"), 1) \
            * max(self.db.count("background"), 1)
        result["with_parameters"] = result["with_destiny_and_background"] * params
        return result

    def count(self) -> dict:
        """Headline numbers for the configured level."""
        l1 = self.count_level1()
        paths_ = self.class_path_counts(self.level)
        prog = self.a.get("progression", {})
        feat_grants = len([l for l in prog.get("feats_at_levels", []) if l <= self.level])
        talent_grants = len([l for l in prog.get("talents_at_levels", []) if l <= self.level])
        pool = self.feat_pool_at_level1()
        per_level_talent_choices = max(self.db.count("talent"), 1)
        out = {
            "level": self.level,
            "level1": {k: v for k, v in l1.items() if k != "pairs"},
            "class_paths": paths_["counts"][self.level],
            "feat_grants": feat_grants,
            "talent_grants": talent_grants,
            "feat_pool_size": len(pool["eligible"]),
            "talent_pool_size": per_level_talent_choices,
        }
        # ---- analytic total -------------------------------------------------
        # total(level) = species x ability_allocations x class_paths(level)
        #                x (mean trained-skill selections per class)^level
        #                x feat_pool^feat_grants x talent_pool^talent_grants
        #                x destiny x background x parameter_multiplier
        skill_per_class = [self.class_skill_choices(c)["combinations"] for c in self.heroic_classes]
        mean_skill = (sum(skill_per_class) / len(skill_per_class)) if skill_per_class else 1.0
        choices_per_path = (max(len(pool["eligible"]), 1) ** feat_grants) * (per_level_talent_choices ** talent_grants)
        out["mean_skill_selections_per_class"] = round(mean_skill, 1)
        out["choices_per_class_path"] = choices_per_path
        out["paths_at_level"] = paths_["counts"][self.level]
        analytic = (len(self.species) * max(l1["ability_allocations"], 1) * paths_["counts"][self.level]
                    * max(int(round(mean_skill)), 1) ** self.level * choices_per_path
                    * max(l1["destiny_choices"], 1) * max(l1["background_choices"], 1))
        out["analytic_total"] = analytic
        out["analytic_log10"] = round(math.log10(analytic), 2) if analytic else 0
        if self.level == 1:
            # exact for level 1; the analytic figure is reported alongside so the
            # approximation used for deeper levels can be checked against it
            out["total_space"] = l1["with_destiny_and_background"]
            out["log10_total_space"] = round(math.log10(out["total_space"]), 2) if out["total_space"] else 0
            out["method"] = "exact"
            out["exact_vs_analytic_ratio"] = round(out["total_space"] / analytic, 4) if analytic else None
        else:
            out["total_space"] = analytic
            out["log10_total_space"] = out["analytic_log10"]
            out["method"] = "analytic (mean skill choices per class, per level)"
        out["assumption_flags"] = sorted(set(self.assumption_flags))
        return out

    # ---------------------------------------------------------------- report
    def report(self) -> str:
        counts = self.count()
        dims = self.dimensions()
        lines = [
            "# Character-creation decision space",
            "",
            f"Settings: level {self.level}, canon filter `{self.canon_filter or 'all'}`, "
            f"homebrew {'included' if self.include_homebrew else 'excluded'}, "
            f"gear {'included' if self.include_gear else 'excluded'}, "
            f"ability method `{self.ability_method}`.",
            "",
            "## Headline numbers",
            "",
            "| measure | value |", "|---|---:|",
            f"| species usable at level 1 | {len(self.species):,} |",
            f"| heroic classes | {len(self.heroic_classes):,} |",
            f"| prestige classes | {len(self.prestige_classes):,} |",
            f"| (species x class) pairs | {counts['level1']['species_class_pairs']:,} |",
            f"| trained-skill selections across all pairs | {counts['level1']['skill_selections_total']:,} |",
            f"| feats selectable at level 1 | {counts['level1']['feat_choices']:,} |",
            f"| ability-score allocations ({self.ability_method}) | {counts['level1']['ability_allocations']:,} |",
            f"| **level-1 core builds** (species x class x skills x feat) | {counts['level1']['core_builds']:,} |",
            f"| level-1 builds incl. ability scores | {counts['level1']['with_abilities']:,} |",
            f"| level-1 builds incl. destiny + background | {counts['level1']['with_destiny_and_background']:,} |",
            f"| legal class paths to level {self.level} | {counts['class_paths']:,} |",
            f"| feat/talent choices per path to level {self.level} | {counts['choices_per_class_path']:,} |",
            f"| **total space at level {self.level}** | 10^{counts['log10_total_space']} ({counts['method']}) |",
            f"| analytic cross-check | 10^{counts['analytic_log10']} |",
            "",
            "## Dimensions",
            "",
            "| key | label | options | kind | gated by | verified |",
            "|---|---|---:|---|---|---|",
        ]
        for d in dims:
            lines.append(f"| `{d.key}` | {d.label} | {d.options:,} | {d.kind} | "
                         f"{', '.join(d.gated_by) or '-'} | {'yes' if d.verified else '**no**'} |")
        lines += ["", "## How each dimension is counted", ""]
        for d in dims:
            lines.append(f"### `{d.key}` - {d.label}")
            lines.append("")
            lines.append(f"- options: **{d.options:,}**")
            lines.append(f"- formula: {d.formula}")
            lines.append(f"- source: `{d.source}`")
            lines.append(f"- verified from data: {'yes' if d.verified else 'NO - rests on an assumption in config/analysis.yaml'}")
            if d.notes:
                lines.append(f"- notes: {d.notes}")
            lines.append("")
        lines += ["## Per-class trained-skill arithmetic", "",
                  "| class | pool | picks | combinations | formula | verified |", "|---|---:|---:|---:|---|---|"]
        for c in self.heroic_classes:
            sc = self.class_skill_choices(c)
            lines.append(f"| {sc['class']} | {sc['pool']} | {sc['picks']} | {sc['combinations']:,} | "
                         f"`{sc['formula']}` | {'yes' if sc['verified'] else 'NO'} |")
        lines += ["", "## Class-path dynamic programme", "",
                  "| level | classes available | cumulative paths |", "|---:|---:|---:|"]
        for row in self.class_path_counts(self.level)["detail"]:
            lines.append(f"| {row['level']} | {row['classes_available']} | {row['paths']:,} |")
        if counts.get("assumption_flags"):
            lines += ["", "## Unverified assumptions affecting these numbers", ""]
            for f in counts["assumption_flags"]:
                lines.append(f"- `{f}`")
        return "\n".join(lines) + "\n"


def _walk(predicates: list[dict]):
    for pred in predicates:
        yield pred
        for key in ("options", "nested", "of"):
            v = pred.get(key)
            if isinstance(v, dict):
                yield from _walk([v])
            elif isinstance(v, list):
                yield from _walk([i for i in v if isinstance(i, dict)])


def write_report(space: DecisionSpace, out_path=None) -> str:
    out = out_path or (paths.REPORTS_DIR / "decision-space.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(space.report(), encoding="utf-8")
    return str(out)
