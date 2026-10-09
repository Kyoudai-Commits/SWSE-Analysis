"""The decision-space model.

Counting rules are the most dangerous code in the repository: a plausible-looking
formula that is silently wrong produces a confident, wrong answer. These tests
pin the arithmetic that *is* derivable from the data and pin the fact that the
rest is flagged as an assumption.
"""

from __future__ import annotations

import pytest

from swse.space import (ABILITY_KEYS, DecisionSpace, ability_modifier,
                        n_choose_k, parse_skill_formula)


def test_ability_modifier_table():
    assert ability_modifier(10) == 0
    assert ability_modifier(11) == 0
    assert ability_modifier(12) == 1
    assert ability_modifier(13) == 1
    assert ability_modifier(18) == 4
    assert ability_modifier(9) == -1
    assert ability_modifier(8) == -1
    assert ability_modifier(7) == -2
    assert ability_modifier(3) == -4


def test_n_choose_k_edges():
    assert n_choose_k(5, 2) == 10
    assert n_choose_k(5, 0) == 1
    assert n_choose_k(3, 5) == 0
    assert n_choose_k(-1, 2) == 0


def test_parse_skill_formula():
    assert parse_skill_formula("2+Int") == (2, "INT")
    assert parse_skill_formula("6 + Int") == (6, "INT")
    assert parse_skill_formula("4") == (4, "")
    assert parse_skill_formula(None) == (0, "")
    assert parse_skill_formula("nonsense") == (0, "")


def test_populations(space):
    assert len(space.heroic_classes) >= 5
    assert len(space.prestige_classes) >= 25
    assert len(space.species) >= 100
    assert len(space.skills) >= 20
    assert len(space.feats) >= 300


def test_class_skill_choices(space):
    soldier = next(c for c in space.heroic_classes if c["name"] == "Soldier")
    at_zero = space.class_skill_choices(soldier, 0)
    at_plus_two = space.class_skill_choices(soldier, 2)
    assert at_zero["pool"] >= 8
    assert at_plus_two["picks"] == at_zero["picks"] + 2
    assert at_plus_two["combinations"] > at_zero["combinations"]
    assert at_zero["combinations"] == n_choose_k(at_zero["pool"], at_zero["picks"])
    assert at_zero["verified"], "official heroic classes must carry their own skill data"


def test_knowledge_all_expands_to_every_knowledge_skill(space, db):
    """``Knowledge (all; taken individually)`` is one entry standing for many."""
    jedi = next(c for c in space.heroic_classes if c["name"] == "Jedi")
    sc = space.class_skill_choices(jedi, 0)
    knowledge = [s["name"] for s in db.all("skill") if s["name"].lower().startswith("knowledge")]
    assert knowledge, "the corpus must contain Knowledge skills"
    assert "Knowledge (all; taken individually)" in jedi["attrs"]["class_skills"]
    assert sc["pool"] == len(jedi["attrs"]["class_skills"]) - 1 + len(knowledge)


def test_feat_pool_partitions_the_corpus(space, db):
    pool = space.feat_pool_at_level1()
    assert pool["eligible"], "some feats must be takeable at level 1"
    total = len(pool["eligible"]) + len(pool["gated_on_other_options"]) + len(pool["blocked_by_numbers"])
    assert total == len(space.feats)
    assert set(pool["eligible"]).isdisjoint(pool["blocked_by_numbers"])


def test_class_path_dp(space):
    counts = space.class_path_counts(20)
    assert counts["counts"][0] == 1
    assert counts["counts"][1] == len(space.heroic_classes)
    for lvl in range(2, 21):
        assert counts["counts"][lvl] > counts["counts"][lvl - 1]
        assert counts["counts"][lvl] % counts["counts"][lvl - 1] == 0
    assert counts["counts"][20] > 10 ** 20


def test_prestige_classes_are_gated_by_level(space):
    """No prestige class may be reachable at level 1."""
    counts = space.class_path_counts(20)
    heroic = len(space.heroic_classes)
    assert counts["detail"][0]["classes_available"] == heroic
    assert any(d["classes_available"] > heroic for d in counts["detail"])


def test_count_level1_is_exact_and_positive(space):
    c = space.count_level1()
    assert c["species_class_pairs"] == len(space.species) * len(space.heroic_classes)
    assert c["skill_selections_total"] > 1_000_000
    assert c["feat_choices"] > 100
    assert c["ability_allocations"] > 0
    assert c["core_builds"] == c["skill_selections_total"] * c["feat_choices"]


def test_total_space_and_cross_check(space):
    counts = space.count()
    assert counts["method"] == "exact"
    assert counts["total_space"] > 0
    # the analytic approximation used for levels 2-20 must be in the same
    # ballpark as the exact level-1 number, or it is not usable
    ratio = counts["exact_vs_analytic_ratio"]
    assert ratio is not None
    assert 0.5 < ratio < 2.0, f"analytic model is off by {ratio}x at level 1"


def test_deeper_levels_grow(space, db):
    small = DecisionSpace(db, level=5).count()
    big = DecisionSpace(db, level=20).count()
    assert big["total_space"] > small["total_space"]
    assert big["paths_at_level"] > small["paths_at_level"]
    assert big["log10_total_space"] > 100


def test_every_dimension_is_documented(space):
    dims = space.dimensions()
    assert len(dims) >= 12
    for d in dims:
        assert d.key and d.label, d
        assert d.formula, f"{d.key} has no formula"
        assert d.source, f"{d.key} has no source"
        assert isinstance(d.verified, bool), f"{d.key} does not say whether it is verified"
        assert d.options >= 0
    assert any(d.verified is False for d in dims), \
        "progression is not in the sources, so something must be flagged unverified"


def test_unverified_dimensions_are_the_declared_assumptions(space):
    unverified = {d.key for d in space.dimensions() if not d.verified}
    # the feat/talent schedule is the one big assumption; anything else appearing
    # here means a new gap opened up and should be looked at deliberately
    assert unverified <= {"feat_grants", "talent_grants", "class_path", "ability_scores"}, unverified


def test_parameterised_feats_multiply_the_space(space):
    dims = {d.key: d for d in space.dimensions()}
    assert dims["parameterised_feats"].options > 1000
    assert dims["parameterised_feats"].kind == "parameter"


def test_canon_filter_shrinks_the_space(db):
    everything = DecisionSpace(db, level=1).count()
    official = DecisionSpace(db, level=1, canon_filter="official").count()
    assert official["level1"]["species_class_pairs"] <= everything["level1"]["species_class_pairs"]
    assert official["total_space"] <= everything["total_space"]
    assert official["total_space"] > 0, "official-only analysis must still be meaningful"


def test_excluding_homebrew_removes_the_two_homebrew_classes(db):
    with_hb = DecisionSpace(db, level=1, include_homebrew=True)
    without = DecisionSpace(db, level=1, include_homebrew=False)
    assert len(without.heroic_classes) <= len(with_hb.heroic_classes)


def test_ability_methods(db):
    from swse.space import load_assumptions
    methods = {m["id"]: m for m in load_assumptions()["ability_scores"]["methods"]}

    std = DecisionSpace(db, level=1, ability_method="standard_array").ability_allocations()
    assert std.options == 720          # 6! permutations of the array
    assert std.verified is False       # the array itself is not in the sources

    vec = DecisionSpace(db, level=1, ability_method="distinct_vectors").ability_allocations()
    span = methods["distinct_vectors"]["max"] - methods["distinct_vectors"]["min"] + 1
    assert vec.options == span ** len(ABILITY_KEYS)
    assert vec.verified is False

    with pytest.raises(ValueError):
        DecisionSpace(db, level=1, ability_method="not_a_method").ability_allocations()


def test_report_renders(space):
    text = space.report()
    assert text.startswith("# Character-creation decision space")
    assert "| measure | value |" in text
    assert "## Dimensions" in text
    assert "Class-path dynamic programme" in text
    assert len(text) > 3000


def test_ability_keys_are_the_swse_six():
    assert ABILITY_KEYS == ("STR", "DEX", "CON", "INT", "WIS", "CHA")
