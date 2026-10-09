"""Build enumeration and evaluation.

The enumerator must produce *legal* characters: every sampled build is checked
against the prerequisite system, and class-granted feats that the character does
not qualify for are recorded rather than silently granted.
"""

from __future__ import annotations

import json

import pytest

from swse.enumerate import (Constraints, ability_arrays, check_build, count_builds,
                            iter_level1_builds, read_builds, sample_builds, write_builds)
from swse.evaluate import Evaluator, METRICS, rank
from swse.ids import norm_key


# ---------------------------------------------------------------------------
# ability score generation
# ---------------------------------------------------------------------------
def test_standard_array_yields_every_permutation(db):
    arrays = list(ability_arrays(db, "standard_array"))
    assert len(arrays) == 720
    assert len({tuple(sorted(a.values())) for a in arrays}) == 1   # same multiset every time


def test_explicit_abilities_override_the_method(db):
    arrays = list(ability_arrays(db, "standard_array", explicit={"STR": 18}))
    assert len(arrays) == 1
    assert arrays[0]["STR"] == 18
    assert set(arrays[0]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}


# ---------------------------------------------------------------------------
# exact level-1 enumeration
# ---------------------------------------------------------------------------
def test_level1_builds_are_complete_and_legal(db):
    builds = list(iter_level1_builds(db, Constraints(limit=25)))
    assert len(builds) == 25
    for b in builds:
        assert b["level"] == 1
        assert b["species"] in db.by_id
        assert len(b["class_path"]) == 1
        assert b["class_path"][0]["class"] in db.by_id
        assert set(b["abilities_final"]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
        assert b["trained_skills"]
        assert b["feats"]
        assert check_build(db, b) == [], check_build(db, b)


def test_level1_first_class_is_heroic(db):
    for b in list(iter_level1_builds(db, Constraints(limit=10))):
        cls = db.get("class", b["class_path"][0]["class"])
        assert cls["attrs"]["class_kind"] == "heroic"


def test_species_and_class_filters_are_honoured(db):
    builds = list(iter_level1_builds(db, Constraints(species=["Human"], classes=["Soldier"], limit=10)))
    assert builds
    for b in builds:
        assert norm_key(db.by_id[b["species"]]["name"]) == norm_key("Human")
        assert b["class_path"][0]["class"] == "class_soldier"


def test_skills_come_from_the_class_list(db):
    for b in list(iter_level1_builds(db, Constraints(classes=["Jedi"], limit=10))):
        jedi = db.get("class", "class_jedi")
        pool = {norm_key(s) for s in jedi["attrs"]["class_skills"]}
        knowledge = {norm_key(s["name"]) for s in db.all("skill") if s["name"].lower().startswith("knowledge")}
        for s in b["trained_skills"]:
            assert norm_key(s) in pool | knowledge, f"{s} is not a Jedi class skill"


# ---------------------------------------------------------------------------
# sampling at depth
# ---------------------------------------------------------------------------
def test_sampled_multiclass_builds_are_legal(db):
    builds = sample_builds(db, Constraints(level=8, seed=1), n=25)
    assert len(builds) == 25
    for b in builds:
        assert len(b["class_path"]) == 8
        assert check_build(db, b) == [], (b["species"], check_build(db, b))


def test_sampling_is_deterministic_for_a_seed(db):
    a = sample_builds(db, Constraints(level=5, seed=42), n=10)
    b = sample_builds(db, Constraints(level=5, seed=42), n=10)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_seeds_give_different_builds(db):
    a = sample_builds(db, Constraints(level=5, seed=1), n=10)
    b = sample_builds(db, Constraints(level=5, seed=2), n=10)
    assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


def test_prestige_classes_only_appear_after_their_minimum_level(db):
    builds = sample_builds(db, Constraints(level=12, seed=5), n=40)
    prestige = {c["id"]: int(c["attrs"].get("min_level") or 7)
                for c in db.all("class") if c["attrs"].get("class_kind") == "prestige"}
    reached = 0
    for b in builds:
        for entry in b["class_path"]:
            if entry["class"] in prestige:
                reached += 1
                assert entry["level"] >= prestige[entry["class"]], \
                    f"{entry['class']} taken at level {entry['level']}"
    assert reached, "a 12-level sample should reach some prestige class"


def test_non_droids_never_take_droid_only_classes(db):
    """Regression: Independent Droid was being sampled for organic species."""
    builds = sample_builds(db, Constraints(level=10, seed=11), n=60)
    droid_class = db.get("class", "class_independent_droid")
    assert droid_class is not None
    for b in builds:
        if any(e["class"] == "class_independent_droid" for e in b["class_path"]):
            assert b["species_kind"] == "droid_chassis", \
                f"{b['species']} ({b['species_kind']}) took Independent Droid"


def test_homebrew_can_be_excluded(db):
    builds = sample_builds(db, Constraints(level=5, seed=3, include_homebrew=False), n=20)
    for b in builds:
        assert "homebrew" not in (db.by_id[b["species"]].get("flags") or [])
        for e in b["class_path"]:
            assert "homebrew" not in (db.by_id[e["class"]].get("flags") or [])


def test_unmet_class_grants_are_recorded_not_granted(db):
    """A Scout with CON 8 does not get Shake It Off - and the build says so."""
    builds = sample_builds(db, Constraints(level=1, seed=9), n=40)
    for b in builds:
        granted = {f["id"] for f in b["feats"] if f.get("granted_by")}
        unmet = {u["feat"] for u in b.get("unmet_grants", [])}
        assert granted.isdisjoint(unmet)
        assert check_build(db, b) == []


def test_builds_roundtrip_through_jsonl(db, tmp_path):
    builds = sample_builds(db, Constraints(level=3, seed=8), n=5)
    c = Constraints(level=3, seed=8)
    out = write_builds(builds, tmp_path / "b.jsonl", c)
    back = read_builds(out)
    assert len(back) == len(builds)
    assert back[0]["species"] == builds[0]["species"]
    assert "_constraints" not in back[0]


def test_count_builds_matches_the_space_model(db):
    c = Constraints(level=1)
    assert count_builds(db, c)["total_space"] > 0


# ---------------------------------------------------------------------------
# legality checking
# ---------------------------------------------------------------------------
def test_check_build_catches_an_illegal_build(db):
    bad = {
        "level": 1,
        "species": "species_human",
        "class_path": [{"level": 1, "class": "class_jedi_knight"}],   # prestige at level 1
        "abilities_final": {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8},
        "trained_skills": [], "feats": [{"id": "feat_shake_it_off"}],  # needs CON 13
        "talents": [], "force_powers": [],
    }
    codes = {v["code"] for v in check_build(db, bad)}
    assert "first_level_not_heroic" in codes or "prestige_entry_level" in codes
    assert "ability_gate" in codes or "class_grant_ability_gate" in codes


def test_check_build_flags_unknown_options(db):
    bad = {"level": 1, "species": "species_human",
           "class_path": [{"level": 1, "class": "class_does_not_exist"}],
           "abilities_final": {}, "trained_skills": [],
           "feats": [{"id": "feat_nope"}], "talents": [], "force_powers": []}
    codes = {v["code"] for v in check_build(db, bad)}
    assert "unknown_class" in codes and "unknown_feat" in codes


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
def test_damage_value_handles_structured_and_text():
    assert Evaluator.damage_value([{"multiplier": 3, "die_size": 6, "bonus": None}]) == 10.5
    assert Evaluator.damage_value([{"multiplier": 2, "die_size": 6, "bonus": 2}]) == 9.0
    assert Evaluator.damage_value("2d6+1") == 8.0
    assert Evaluator.damage_value(None) == 0
    assert Evaluator.damage_value([]) == 0


def test_damage_value_handles_flat_and_special():
    assert Evaluator.damage_value([{"flat": 1, "bonus": None}]) == 1.0
    assert Evaluator.damage_value([{"flat": 1, "bonus": 3}]) == 4.0
    assert Evaluator.damage_value([{"special": "special"}]) == 0
    # a flagged, unrewritten "28" is still read as the source wrote it
    assert Evaluator.damage_value([{"flat": 28, "suspected_dice": "2d8"}]) == 28.0


def test_bonus_signatures_are_extracted():
    ev = Evaluator.__new__(Evaluator)
    ev._bonus_cache = {}
    found = ev.bonuses_in("Grants a +2 competence bonus to attack rolls")
    assert found and found[0][0] == "competence" and found[0][2] == 2
    assert ev.bonuses_in("") == []


def _ev():
    ev = Evaluator.__new__(Evaluator)
    ev._bonus_cache = {}
    return ev


@pytest.mark.parametrize("text", [
    # Found by the canon-balance audit (TASK-018): a bare number before "to"/"on"
    # is not a bonus. These three are real rules text from the corpus.
    "Once per encounter, take 20 on a trained Knowledge check or 10 on an untrained check",
    "You regain all starship maneuvers at the end of any round you roll a natural 20 on an attack roll",
    "Reroll any Climb or Jump check. Take 10 on Climb and Jump checks.",
])
def test_take_n_and_natural_n_are_not_bonuses(text):
    """The 'natural 20 on an attack roll' case used to add +20 to `offense`."""
    assert _ev().bonuses_in(text) == []


@pytest.mark.parametrize("text,expected", [
    ("+2 competence bonus to attack rolls", ("competence", "attack rolls", 2)),
    ("2 bonus to Reflex Defense", ("untyped", "Reflex Defense", 2)),
    ("-2 penalty to Stealth checks", ("penalty", "Stealth checks", -2)),
    ("+1 dodge bonus to Reflex Defense", ("dodge", "Reflex Defense", 1)),
    ("gain a +10 bonus on your attack roll to disarm", ("untyped", "your attack roll to disarm", 10)),
])
def test_real_bonus_wordings_still_parse(text, expected):
    btype, target, amount = expected
    found = _ev().bonuses_in(text)
    assert (btype, target, amount) in found, f"{text!r} -> {found}"


def test_a_signed_penalty_is_not_also_read_as_an_unsigned_bonus():
    """"-2 penalty to X" must yield one signature, not (-2, penalty) and (+2, untyped)."""
    found = _ev().bonuses_in("-2 penalty to Stealth checks")
    assert len(found) == 1, found
    assert found[0][2] == -2


def test_metrics_are_documented():
    assert len(METRICS) >= 10
    for name, label, formula, verified in METRICS:
        assert name and label and formula
        assert isinstance(verified, bool)
    # defence scaling is not in the sources, so it must be flagged unverified
    assert {m[0] for m in METRICS if not m[3]} >= {"defense_reflex", "defense_fortitude", "defense_will"}


def test_scoring_a_known_build(db):
    human = db.find("species", "Human")[0]
    soldier = db.get("class", "class_soldier")
    build = {
        "level": 1, "species": human["id"],
        "species_kind": human["attrs"].get("species_kind", "species"),
        "class_path": [{"level": 1, "class": soldier["id"]}],
        "abilities_base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        "abilities_final": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        "trained_skills": ["Climb", "Endurance"], "feats": [], "talents": [],
        "force_powers": [], "force_sensitive": False,
    }
    ev = Evaluator(db)
    s = ev.score(build)
    assert s.metrics["bab"] == 1                              # Soldier is a full-BAB class
    assert s.parts["durability"]["hp"] == 30 + 2              # 3 x d10 + CON mod (verified formula)
    assert s.metrics["defense_fortitude"] == 10 + 2 + 2       # 10 + CON mod + Soldier's +2
    assert s.metrics["skill_breadth"] == 2
    assert "total" in s.metrics
    assert any("unverified" in w for w in s.warnings)


def test_scoring_is_deterministic(db):
    builds = sample_builds(db, Constraints(level=4, seed=13), n=6)
    ev = Evaluator(db)
    first = [ev.score(b).metrics for b in builds]
    second = [ev.score(b).metrics for b in builds]
    assert first == second


def test_rank_orders_by_metric(db):
    builds = sample_builds(db, Constraints(level=3, seed=14), n=12)
    ev = Evaluator(db)
    scores = ev.score_many(builds)
    ordered = rank(scores, "total")
    totals = [s.metrics["total"] for s in ordered]
    assert totals == sorted(totals, reverse=True)


def test_weights_change_the_ranking(db):
    builds = sample_builds(db, Constraints(level=6, seed=15), n=20)
    default = Evaluator(db).score_many(builds)
    heavy = Evaluator(db, weights={"offense": 1.0}).score_many(builds)
    assert [s.metrics["total"] for s in default] != [s.metrics["total"] for s in heavy]


def test_breadth_metrics_move_with_the_build(db):
    ev = Evaluator(db)
    small = {"level": 1, "species": "species_human", "class_path": [{"level": 1, "class": "class_soldier"}],
             "abilities_final": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
             "trained_skills": ["Climb"], "feats": [], "talents": [], "force_powers": [],
             "force_sensitive": False}
    many = dict(small)
    many["trained_skills"] = ["Climb", "Jump", "Swim", "Pilot", "Mechanics"]
    assert ev.score(many).metrics["skill_breadth"] > ev.score(small).metrics["skill_breadth"]
