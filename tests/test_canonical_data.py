"""Invariants of the canonical dataset.

These tests are the contract every regeneration must satisfy. They are the
replacement for ad-hoc inspection scripts: if a change to a block, a hook or the
curation overlay breaks one of these, the build is not shippable.
"""

from __future__ import annotations

import json

import pytest

from swse import paths
from swse.ids import norm_key

RESERVED = {"id", "entity", "name", "canon", "attrs", "prerequisites", "relations",
            "sourcebooks", "sources", "conflicts", "flags"}


def test_index_matches_files_on_disk(db):
    index = json.loads((paths.CANONICAL_DIR / "index.json").read_text(encoding="utf-8"))
    assert index["total"] == db.total()
    assert set(index["entities"]) == set(db.entities)
    for entity, meta in index["entities"].items():
        assert meta["count"] == db.count(entity), entity


def test_every_record_has_the_required_shape(db):
    for entity in db.entities:
        for rec in db.all(entity):
            assert rec["entity"] == entity
            assert rec["id"].startswith(f"{entity}_"), rec["id"]
            assert rec["name"], rec["id"]
            assert rec["canon"] in {"official", "third_party", "homebrew"}, rec["id"]
            assert isinstance(rec["attrs"], dict)
            assert isinstance(rec["sources"], list) and rec["sources"], rec["id"]
            assert RESERVED.isdisjoint(rec["attrs"]), f"{rec['id']} has reserved keys in attrs"


def test_ids_are_unique(db):
    ids = [r["id"] for e in db.entities for r in db.all(e)]
    assert len(ids) == len(set(ids))
    dupes = [i for i in set(ids) if ids.count(i) > 1]
    assert not dupes


def test_every_record_has_provenance(db):
    """No record may exist without a workbook cell behind it."""
    for entity in db.entities:
        for rec in db.all(entity):
            for src in rec["sources"]:
                assert src.get("source"), rec["id"]
                assert src.get("block"), rec["id"]
                assert src.get("sheet"), rec["id"]
                assert src.get("row"), rec["id"]
                assert src.get("ref"), rec["id"]


def test_canon_basis_is_always_declared(db):
    """Provenance of the canonicity decision, not just the decision."""
    missing = [r["id"] for e in db.entities for r in db.all(e)
               if not r["attrs"].get("canon_basis")]
    assert not missing, f"{len(missing)} records lack attrs.canon_basis, e.g. {missing[:5]}"


def test_cited_records_are_official_content(db):
    """A record citing a published sourcebook is official content."""
    for entity in db.entities:
        for rec in db.all(entity):
            if rec["attrs"].get("canon_basis") == "sourcebook_citation":
                assert rec["canon"] == "official", rec["id"]
                assert rec["sourcebooks"], rec["id"]


def test_sourcebook_citations_are_known(db):
    import yaml
    known = {s["id"] for s in (yaml.safe_load(paths.SOURCEBOOKS_YAML.read_text(encoding="utf-8"))
                               or {}).get("sourcebooks", [])}
    used = {sb["id"] for e in db.entities for r in db.all(e) for sb in (r.get("sourcebooks") or [])}
    assert used <= known, f"records cite unknown sourcebooks: {sorted(used - known)}"


def test_key_entities_are_populated(db):
    """Sizes that would collapse to nothing if a block's coordinates broke."""
    expected_min = {
        "class": 30, "species": 100, "feat": 300, "talent": 1000, "talent_tree": 150,
        "skill": 20, "force_power": 80, "weapon": 200, "armor": 80, "language": 90,
        "destiny": 80, "background": 40, "droid_option": 100, "ammunition": 15,
        "near_human_trait": 20, "special_talent": 10, "lightsaber_form": 10,
    }
    for entity, minimum in expected_min.items():
        assert db.count(entity) >= minimum, f"{entity} has {db.count(entity)}, expected >= {minimum}"


def test_heroic_and_prestige_classes_are_separated(db):
    kinds = {}
    for c in db.all("class"):
        kinds.setdefault(c["attrs"].get("class_kind"), []).append(c["name"])
    assert "heroic" in kinds and "prestige" in kinds
    assert len(kinds["heroic"]) >= 5
    assert len(kinds["prestige"]) >= 25
    for name in ("Jedi", "Noble", "Scoundrel", "Scout", "Soldier"):
        assert name in kinds["heroic"], name


def test_heroic_classes_carry_the_printed_numbers(db):
    """The five official heroic classes must have their full stat block."""
    for name in ("Jedi", "Noble", "Scoundrel", "Scout", "Soldier"):
        rec = db.find("class", name)[0]
        a = rec["attrs"]
        for field in ("hit_die", "base_attack", "trained_skills_per_level", "class_skills",
                      "starting_feats", "talent_trees", "reflex_progression",
                      "fortitude_progression", "will_progression"):
            assert a.get(field) not in (None, "", []), f"{name}.{field} missing"


def test_defense_bonuses_match_the_printed_column(db):
    """Cross-source verification: SagaForge's numbers == Master Reference's text.

    ``Data!CA:CC`` hold 0/1/2 defence values; the Master Reference's DEFENSE
    BONUS column holds the same information as prose ("Ref +1 / Will +2"). Where
    both exist they must agree - that is what makes the level-1 defence bonus a
    verified fact instead of an assumption.
    """
    import re
    checked = 0
    for rec in db.all("class"):
        a = rec["attrs"]
        text = a.get("defense_bonus")
        if not text or a.get("class_kind") != "heroic":
            continue
        printed = {}
        for m in re.finditer(r"(Ref|Fort|Will)\s*\+\s*(\d+)", str(text), re.I):
            key = {"ref": "reflex_progression", "fort": "fortitude_progression",
                   "will": "will_progression"}[m.group(1).lower()]
            printed[key] = int(m.group(2))
        # Classes that exist only in the Master Reference (the homebrew section)
        # have the printed text but no SagaForge numbers to compare against.
        if any(a.get(k) is None for k in printed):
            continue
        for key, value in printed.items():
            assert int(a.get(key) or 0) == value, f"{rec['name']}: {key} {a.get(key)} != printed {value}"
        checked += 1
    assert checked >= 5, f"only cross-checked {checked} classes"


def test_starting_hit_points_are_three_hit_dice(db):
    """Verified formula: 1st-level HP = 3 x hit die + CON modifier."""
    import re
    checked = 0
    for rec in db.all("class"):
        a = rec["attrs"]
        shp, hd = a.get("starting_hit_points"), a.get("hit_die")
        if not shp or not hd:
            continue
        m = re.match(r"^(\d+)\s*\+\s*Con$", str(shp).strip(), re.I)
        assert m, f"{rec['name']}: unrecognised starting HP {shp!r}"
        assert int(m.group(1)) == 3 * int(hd), f"{rec['name']}: {shp} != 3 x d{hd}"
        checked += 1
    assert checked >= 5


def test_class_grants_are_split_into_options(db):
    """Regression: grants arrived as one space-joined string per class.

    A fragment of a parenthetical ("taken individually)") or a blob holding two
    option names means the split failed. ``test_class_grants_resolve_against_the_
    vocabularies`` is the strict half of this check.
    """
    for rec in db.all("class"):
        a = rec["attrs"]
        for field in ("starting_feats", "talent_trees", "class_skills"):
            for item in a.get(field) or []:
                assert "\n" not in item, f"{rec['id']}.{field} still holds a multi-line blob"
                assert item.count("(") == item.count(")"), \
                    f"{rec['id']}.{field} holds an unbalanced fragment: {item!r}"
                assert not item.startswith(")"), f"{rec['id']}.{field} fragment: {item!r}"


def test_class_grants_resolve_against_the_vocabularies(db):
    """Every parsed grant must name a real option (or be an explicit wildcard)."""
    feat_keys = {norm_key(r["name"]) for r in db.all("feat")}
    feat_heads = {norm_key(r["name"].split(" (")[0]) for r in db.all("feat")}
    tree_keys = {norm_key(r["name"]) for r in db.all("talent_tree")}
    tree_keys |= {norm_key(r["name"].replace(" Talent Tree", "")) for r in db.all("talent_tree")}
    skill_keys = {norm_key(r["name"]) for r in db.all("skill")} | {norm_key("Knowledge (all; taken individually)")}
    problems = []
    for rec in db.all("class"):
        a = rec["attrs"]
        for grant in a.get("starting_feats") or []:
            # a grant may be parameterised ("Weapon Proficiency (Pistols)"): the
            # corpus stores the generic feat plus a parameter, so match either
            if norm_key(grant) in feat_keys or norm_key(grant.split(" (")[0]) in feat_keys | feat_heads:
                continue
            problems.append(f"{rec['id']} feat {grant!r}")
        for tree in a.get("talent_trees") or []:
            if norm_key(tree) not in tree_keys and not a.get("grants_all_trees"):
                problems.append(f"{rec['id']} tree {tree!r}")
        for skill in a.get("class_skills") or []:
            if norm_key(skill) not in skill_keys and not skill.lower().startswith("knowledge"):
                problems.append(f"{rec['id']} skill {skill!r}")
    assert not problems, "unresolved class grants: " + "; ".join(problems[:10])


def test_name_collisions_are_flagged_not_merged(db):
    """Same name inside one source is never silently merged.

    Two genuinely different options that happen to share a name (three different
    feats called "Staggering Attack", three "Force Storm" powers) must stay
    separate records, each flagged, each with a distinct id.
    """
    collisions = [r for e in db.entities for r in db.all(e) if "name_collision" in (r.get("flags") or [])]
    assert collisions, "expected some flagged collisions in this corpus"
    for rec in collisions:
        twins = [r for r in db.all(rec["entity"])
                 if norm_key(r["name"]) == norm_key(rec["name"]) and r["id"] != rec["id"]]
        assert twins, f"{rec['id']} is flagged name_collision but has no same-named sibling"
        # they must be distinguishable: different id, and not identical payloads
        for twin in twins:
            assert twin["id"] != rec["id"]
            assert twin["attrs"] != rec["attrs"] or twin["sources"] != rec["sources"], \
                f"{rec['id']} and {twin['id']} are indistinguishable duplicates"


def test_parameterised_feats_expose_their_option_axis(db):
    """Weapon Proficiency and friends are one record with a hidden choice."""
    by_id = db.by_id
    wp = by_id.get("feat_weapon_proficiency")
    assert wp is not None
    assert wp["attrs"]["parameter_axis"] == "weapon_group"
    assert set(wp["attrs"]["parameter_options"]) >= {"simple", "pistols", "rifles", "heavy", "lightsabers"}
    sf = by_id.get("feat_skill_focus")
    assert sf is not None
    assert sf["attrs"]["parameter_axis"] == "skill"
    assert len(sf["attrs"]["parameter_options"]) >= 20
    assert "parameterised" in wp["flags"]


def test_weapons_carry_structured_damage(db):
    """Damage is parsed into multiplier/die/bonus so it can be compared numerically.

    Three shapes are legitimate: dice (``2d6+1``), flat points (unarmed deals 1),
    and ``special`` (targeting laser). What is *not* legitimate is an entry that
    says nothing at all.
    """
    structured = 0
    for w in db.all("weapon"):
        dmg = w["attrs"].get("damage")
        if isinstance(dmg, list) and dmg and isinstance(dmg[0], dict):
            for entry in dmg:
                assert entry.get("die_size") or entry.get("flat") is not None or entry.get("special"), \
                    f"{w['id']} has an empty damage entry: {entry}"
            structured += 1
    assert structured >= 150, f"only {structured} weapons have structured damage"


def test_flat_damage_weapons_are_modelled_as_flat(db):
    unarmed = db.get("weapon", "weapon_unarmed")
    assert unarmed is not None
    assert unarmed["attrs"]["damage"][0]["flat"] == 1
    assert unarmed["attrs"]["damage"][0].get("die_size") is None


def test_suspected_concatenated_damage_is_flagged_not_rewritten(db):
    """The Power lance's damage cell holds "28"; the printed book says 2d8.

    The pipeline must not invent the die. It flags the record and files a gap so
    the decision is made deliberately in the curation overlay.
    """
    lance = db.get("weapon", "weapon_power_lance")
    assert lance is not None
    entry = lance["attrs"]["damage"][0]
    assert entry.get("suspected_dice") == "2d8"
    assert entry.get("die_size") is None, "the parser must not silently rewrite the source"
    assert "damage_suspected_concatenation" in lance["flags"]


def test_no_record_keeps_internal_scratch_keys(db):
    for entity in db.entities:
        for rec in db.all(entity):
            for key in rec["attrs"]:
                assert not key.startswith("_"), f"{rec['id']} leaks internal key {key}"
            assert "_prereq_text" not in rec
            assert "_sourcebook_ids" not in rec


@pytest.mark.parametrize("entity", ["species", "class", "feat", "talent", "force_power"])
def test_entity_files_are_valid_json(db, entity):
    path = paths.CANONICAL_DIR / f"{entity}.json"
    assert path.exists()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["entity"] == entity
    assert doc["count"] == len(doc["records"]) == db.count(entity)
    assert doc["records"][0]["entity"] == entity


# --------------------------------------------------------------------------- #
# builder artefacts (GAP-014 / TASK-019)
# --------------------------------------------------------------------------- #
BUILDER_FLAGS = {"builder_combination", "builder_parameter_variant"}


def _flagged(db, entity, flag):
    return [r for r in db.all(entity) if flag in (r.get("flags") or [])]


def test_builder_combination_rows_are_flagged_not_deleted(db):
    """The 101 Dreadful Rage / Power Attack rows stay in the corpus, marked as what they are."""
    mods = db.all("weapon_mod")
    combos = _flagged(db, "weapon_mod", "builder_combination")
    variants = _flagged(db, "weapon_mod", "builder_parameter_variant")
    assert len(mods) == 156                      # nothing was dropped or merged
    assert len(combos) == 72
    assert len(variants) == 101
    assert len(mods) - len({r["id"] for r in combos + variants}) == 43

    by_id = {r["id"]: r for r in mods}
    combo = by_id["weapon_mod_careful_shot_and_deadeye"]
    assert combo["attrs"]["combination_of"] == ["Careful Shot", "Deadeye"]
    # the components must be real records, or the flag is an assertion about nothing
    for cid in combo["relations"]["combines"]:
        assert cid in by_id, cid
    # a component may resolve outside the entity: there is no bare `Power Attack`
    # weapon_mod (only its parameter variants), so the feat is the real option
    dreadful = by_id["weapon_mod_dreadful_rage_and_power_attack_1"]
    assert dreadful["attrs"]["combination_of"] == ["Dreadful Rage", "Power Attack"]
    assert "weapon_mod_dreadful_rage" in dreadful["relations"]["combines"]
    assert db.by_id["feat_power_attack"]["id"] in dreadful["relations"]["combines"]
    assert set(dreadful["flags"]) >= {"builder_combination", "builder_parameter_variant"}
    # flagged rows keep their provenance: they are still facts about the source
    assert all(r["sources"] for r in combos + variants)


def test_parameter_variants_name_their_base_and_value(db):
    """`Power Attack (-1)` .. `(-16)` are one option on a dial, recorded as such."""
    variants = _flagged(db, "weapon_mod", "builder_parameter_variant")
    bases = {}
    for r in variants:
        base = r["attrs"]["parameter_base"]
        bases.setdefault(base, set()).add(r["attrs"]["parameter_value"])
        assert isinstance(r["attrs"]["parameter_value"], int)
    assert bases["Power Attack"] >= {-1, -10, -16}
    assert bases["Dreadful Rage and Power Attack"] >= {-1, -20}
    # every base with variants really has more than one row, so the GAP-007
    # same-name collisions ("Double Attack", "Inquisition") cannot be swept up
    for base, values in bases.items():
        assert len(values) >= 2, base


@pytest.mark.parametrize("entity,name", [
    ("armor", "Battle armor, heavy"),
    ("weapon", "Blaster pistol, heavy"),
    ("weapon", "Blaster rifle, assault"),
    ("equipment", "Datapad, basic"),
    ("equipment", "Jet pack, miniaturized"),
    ("racial_ability", "Fly Speed (6)"),
])
def test_item_plus_qualifier_names_are_not_builder_artefacts(db, entity, name):
    """A comma is a naming convention in this corpus, not a combination.

    "Battle armor, heavy" looks like `Battle armor` + `heavy` and both halves exist as
    records - `heavy` because the corpus holds armor_size and availability rows. It is
    one item, and flagging it would delete real options from every count.
    """
    rec = next((r for r in db.all(entity) if r["name"] == name), None)
    assert rec is not None, f"{entity}:{name} missing - rename the test, not the data"
    assert not (BUILDER_FLAGS & set(rec.get("flags") or [])), rec["flags"]


def test_no_entity_outside_the_inspected_list_is_flagged(db):
    """The artefact was verified by hand for `weapon_mod` only; nothing else is touched."""
    from swse.hooks import BUILDER_ARTEFACT_ENTITIES

    for entity in db.entities:
        if entity in BUILDER_ARTEFACT_ENTITIES:
            continue
        leaked = [r["id"] for r in db.all(entity) if BUILDER_FLAGS & set(r.get("flags") or [])]
        assert not leaked, f"{entity}: {leaked[:5]}"
