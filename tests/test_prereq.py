"""Prerequisite parsing: structure first, entity resolution second.

The corpus writes prerequisites as free text in spreadsheet cells. Parsing them
is what makes the prerequisite graph, the decision space and build legality
possible, so the parser's behaviour is pinned here.
"""

from __future__ import annotations

import pytest

from swse.ids import norm_key
from swse.prereq import (classify, normalize, parse, resolve, resolve_name,
                         split_fragments)


def types_of(parsed) -> list[str]:
    out = []
    for p in parsed["predicates"]:
        out.append(p["type"])
        for o in p.get("options") or []:
            out.append(o["type"])
    return out


def test_normalize_folds_lines_but_keeps_structure():
    assert normalize("Minimum Level:  7th\nTrained Skills:   Deception") == \
        "Minimum Level: 7th\nTrained Skills: Deception"


def test_normalize_fixes_known_corpus_typos():
    assert "Armor" in normalize("Armour Proficiency (Light)")
    assert "System" in normalize("Sytem: Heuristic")


def test_split_fragments_keeps_or_rules_intact():
    """Regression: comma-splitting shredded "Any one from the Fortune Talent Tree"."""
    frags = split_fragments("Talents: Any one from the Fortune Talent Tree, or the Misfortune Talent Tree")
    assert len(frags) == 1


def test_split_fragments_splits_newline_separated_requirements():
    assert split_fragments("Minimum Level: 7th\nTrained Skills: Use the Force") == \
        ["Minimum Level: 7th", "Trained Skills: Use the Force"]


def test_level_and_bab_gates():
    p = parse("Minimum Level: 7th")
    assert p["predicates"][0]["type"] == "level_min"
    assert p["predicates"][0]["min"] == 7
    assert p["coverage"] == 1.0

    p = parse("Base Attack Bonus: +7")
    assert p["predicates"][0]["type"] == "bab_min"
    assert p["predicates"][0]["min"] == 7

    p = parse("Minimum Base Attack Bonus: +7")
    assert p["predicates"][0]["type"] == "bab_min"


def test_ability_gate():
    p = parse("Strength 13")
    pred = p["predicates"][0]
    assert pred["type"] == "ability_min"
    assert pred["ability"] == "STR"
    assert pred["min"] == 13


def test_trained_skill_single_and_multiple():
    p = parse("Trained in Mechanics")
    pred = p["predicates"][0]
    assert pred["type"] == "trained_skill"
    assert pred["skills"] == ["Mechanics"]

    # "and" is a conjunction of two requirements, "or" an alternative
    p = parse("Trained in Mechanics and Use Computer")
    assert len(p["predicates"][0]["skills"]) == 2
    assert p["predicates"][0]["mode"] == "all"

    p = parse("Trained in Pilot or Ride")
    assert len(p["predicates"][0]["skills"]) == 2
    assert p["predicates"][0]["mode"] == "any"


def test_labelled_trained_skills_list():
    p = parse("Trained Skills: Deception, Stealth")
    pred = p["predicates"][0]
    assert pred["type"] == "trained_skill"
    assert {norm_key(s) for s in pred["skills"]} == {"deception", "stealth"}


def test_two_labels_on_one_line_still_split():
    """A comma before a *second* label separates two requirements."""
    frags = split_fragments("Trained Skills: Use the Force, Feats: Force Sensitivity")
    assert frags == ["Trained Skills: Use the Force", "Feats: Force Sensitivity"]
    kinds = types_of(parse("\n".join(frags)))
    assert "trained_skill" in kinds and "feat" in kinds


def test_knowledge_any_is_generic():
    """``Knowledge (Any)`` means "any Knowledge skill", not a skill called Any."""
    p = parse("Trained in Knowledge (Any)")
    pred = p["predicates"][0]
    assert pred["type"] == "trained_skill"
    assert norm_key(pred["skills"][0]) == norm_key("Knowledge")


def test_proficiency_grades_and_groups():
    p = parse("Armor Proficiency (Light)")
    assert p["predicates"][0]["type"] == "armor_proficiency"

    p = parse("Weapon Proficiency (Pistols)")
    pred = p["predicates"][0]
    assert pred["type"] == "weapon_proficiency"
    assert norm_key(pred.get("group", "")) == norm_key("Pistols")


def test_talent_any_from_tree():
    p = parse("Talents: Any two from Camouflage Talent Tree")
    pred = p["predicates"][0]
    assert pred["type"] == "talent"
    assert pred["count"] == 2
    assert pred["mode"] == "any"
    assert any(norm_key(t) == norm_key("Camouflage") for t in pred.get("trees") or [])


def test_any_n_force_talents():
    p = parse("Talents: Any three Force Talents")
    pred = p["predicates"][0]
    assert pred["type"] == "talent"
    assert pred["count"] == 3
    assert pred.get("force_only") is True


def test_creature_type_and_droid_gates():
    assert parse("Droid")["predicates"][0]["type"] == "creature_type"
    p = parse("Non-Droid")
    assert p["predicates"][0]["type"] == "creature_type"


def test_unparseable_text_is_reported_not_dropped():
    p = parse("Gamemaster's Approval")
    assert p["unresolved"], "unparseable requirement must be surfaced"
    assert p["coverage"] < 1.0


def test_alternatives_become_any_of_predicates():
    """Regression: or-groups used to be marked by appending text to the fragment."""
    p = parse("Human or Bothan")
    preds = p["predicates"]
    assert len(preds) == 1
    assert preds[0]["type"] == "any_of"
    assert len(preds[0]["options"]) == 2
    for opt in preds[0]["options"]:
        assert "or-group" not in opt.get("text", "")


def test_classify_is_idempotent_on_plain_text():
    for text in ("Minimum Level: 7th", "Trained in Mechanics", "Weapon Proficiency (Rifles)"):
        assert classify(text) == classify(text)


def test_resolve_attaches_ids_using_the_entity_index(db):
    index = db.index()
    parsed = parse("Minimum Level: 7th\nTrained Skills: Use the Force\n"
                   "Feats: Force Sensitivity\nTalents: Any three Force Talents")
    resolved = resolve(parsed, index)
    kinds = {p["type"] for p in resolved["predicates"]}
    assert {"level_min", "trained_skill", "feat", "talent"} <= kinds
    feat_pred = next(p for p in resolved["predicates"] if p["type"] == "feat")
    assert feat_pred["refs"][0]["id"] == "feat_force_sensitivity"
    assert resolved["coverage"] == 1.0
    assert not resolved["unresolved"]


def test_resolve_name_handles_parameterised_options(db):
    index = db.index()
    hit = resolve_name(index, "Skill Focus (Stealth)")
    assert hit["id"] == "feat_skill_focus"
    assert norm_key(hit["param"]) == norm_key("Stealth")

    hit = resolve_name(index, "Force Sensitivity")
    assert hit["id"] == "feat_force_sensitivity"
    assert hit["param"] is None

    miss = resolve_name(index, "Definitely Not A Real Option")
    assert miss["id"] is None


def test_corpus_parse_coverage_is_high(db):
    """The whole point of the entity-aware resolver: coverage must stay above 98%."""
    total = unresolved = 0
    for entity in db.entities:
        for rec in db.all(entity):
            p = rec.get("prerequisites")
            if not p or p.get("empty"):
                continue
            for pred in p["predicates"]:
                stack = [pred]
                while stack:
                    cur = stack.pop()
                    stack.extend(cur.get("options") or [])
                    if cur["type"] == "any_of":
                        continue
                    total += 1
                    if cur["type"] == "other":
                        unresolved += 1
    assert total > 500, f"expected a large parsed corpus, got {total}"
    coverage = (total - unresolved) / total
    assert coverage >= 0.98, f"prerequisite coverage regressed to {coverage:.2%}"


@pytest.mark.parametrize("text,expected", [
    ("Minimum Level: 7th", "level_min"),
    ("Base Attack Bonus: +7", "bab_min"),
    ("Trained in Mechanics", "trained_skill"),
    ("Armor Proficiency (Medium)", "armor_proficiency"),
    ("Weapon Proficiency (Rifles)", "weapon_proficiency"),
    ("Droid", "creature_type"),
])
def test_classification_table(text, expected):
    assert parse(text)["predicates"][0]["type"] == expected
