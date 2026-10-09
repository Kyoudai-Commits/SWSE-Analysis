"""Text normalisation and identifier helpers.

These are pure functions with no data dependency, so they run on a fresh clone.
Several of them encode bugs that were found the hard way - each of those has a
regression test naming the bug.
"""

from __future__ import annotations

from swse.ids import (clean_cell, dedupe, fold, fold_multiline, is_blank,
                      norm_key, slugify, split_by_vocabulary, split_list)


def test_fold_collapses_whitespace_and_unicode_noise():
    assert fold("  Ace\u00a0 Pilot \t ") == "Ace Pilot"
    assert fold("Jedi\u2019s Saber") == "Jedi's Saber"
    assert fold(None) == ""


def test_fold_multiline_keeps_newlines():
    """Regression: collapsing newlines destroyed multi-part prerequisite cells.

    The Master Reference stores prerequisites as newline-separated lines. Folding
    them into one line glued unrelated requirements together ("Minimum Level: 7th
    Trained Skills: Deception") and dropped prerequisite coverage to ~48%.
    """
    text = "Minimum Level: 7th\n  Trained Skills:   Deception"
    assert fold_multiline(text) == "Minimum Level: 7th\nTrained Skills: Deception"
    assert "\n" not in fold(text)


def test_clean_cell_preserves_line_structure():
    assert clean_cell("A\n B") == "A\nB"
    assert clean_cell("   ") is None      # blank cells normalise to None
    assert clean_cell("#VALUE!") is None  # spreadsheet error placeholders
    assert clean_cell(None) is None
    assert clean_cell(7) == 7


def test_slugify_and_norm_key():
    assert slugify("Force Storm (JATM)") == "force_storm_jatm"
    assert slugify("Point-Blank Shot") == "point_blank_shot"
    assert norm_key("Ace Pilot ") == norm_key("ace pilot") == "acepilot"


def test_is_blank_catches_spreadsheet_noise():
    for v in (None, "", "   ", "-", "--", "N/A", "None", "#VALUE!", "#REF!", "#N/A"):
        assert is_blank(v), v
    assert not is_blank("0")
    assert not is_blank(0)


def test_split_list_is_paren_aware():
    """Regression: ``"Knowledge (all; taken individually)"`` was split on the ``;``."""
    text = "Deception,\nKnowledge (all; taken individually),\nPerception"
    assert split_list(text) == ["Deception", "Knowledge (all; taken individually)", "Perception"]


def test_split_list_handles_newline_only_lists():
    assert split_list("Acrobatics\nEndurance\nJump") == ["Acrobatics", "Endurance", "Jump"]


def test_dedupe_preserves_order():
    assert dedupe(["b", "a", "b", "c"]) == ["b", "a", "c"]


VOCAB = {norm_key(n): n for n in [
    "Force Sensitivity", "Force Training", "Weapon Proficiency", "Armor Proficiency",
    "Skill Focus", "Point-Blank Shot", "Shake It Off", "Linguist", "Tech Specialist",
]}


def test_split_by_vocabulary_segments_space_joined_grants():
    """The Master Reference stores class grants as one space-joined string."""
    parts = split_by_vocabulary(
        "Force Sensitivity Weapon Proficiency (Lightsabers) Weapon Proficiency (Simple Weapons)", VOCAB)
    assert [p["name"] for p in parts] == [
        "Force Sensitivity", "Weapon Proficiency (Lightsabers)", "Weapon Proficiency (Simple Weapons)"]
    assert parts[1]["param"] == "Lightsabers"
    assert all(p["matched"] for p in parts)


def test_split_by_vocabulary_handles_nested_parens():
    parts = split_by_vocabulary(
        "Skill Focus (Knowledge (Any), Mechanics, Treat Injury, or Use Computer) Tech Specialist* "
        "Weapon Proficiency (Simple Weapons)", VOCAB)
    assert parts[0]["param"] == "Knowledge (Any), Mechanics, Treat Injury, or Use Computer"
    assert parts[1]["name"] == "Tech Specialist"          # footnote asterisk dropped
    assert parts[2]["param"] == "Simple Weapons"


def test_split_by_vocabulary_separates_notes_from_parameters():
    """``Linguist (must have the prerequisite Intelligence of 13)`` is a note."""
    parts = split_by_vocabulary("Linguist (must have the prerequisite Intelligence of 13) "
                                "Weapon Proficiency (Pistols)", VOCAB)
    assert parts[0]["name"] == "Linguist"
    assert parts[0]["param"] is None
    assert parts[0]["note"].startswith("must have the prerequisite")
    assert parts[1]["param"] == "Pistols"


def test_split_by_vocabulary_reports_unmatched_text():
    parts = split_by_vocabulary("Force Sensitivity Something Unknown Here", VOCAB)
    assert parts[0]["matched"] is True
    assert parts[1]["matched"] is False
    assert "Something Unknown" in parts[1]["name"]
