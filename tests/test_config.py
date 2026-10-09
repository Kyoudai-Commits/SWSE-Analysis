"""Config consistency.

The config files are the specification an agent edits to add a source, so they
are checked against each other: every block names a real entity, every entity
names real blocks, every hook referenced is registered, and every analysis
assumption states whether it is verified.
"""

from __future__ import annotations

import yaml

from swse import paths
from swse.blocks import load_blocks
from swse.hooks import ENTITY_HOOKS, POST_HOOKS, ROW_HOOKS


def _load(name: str) -> dict:
    return yaml.safe_load((paths.CONFIG_DIR / name).read_text(encoding="utf-8")) or {}


def test_blocks_reference_known_entities():
    entities = set(_load("entities.yaml")["entities"])
    unknown = sorted({b.entity for b in load_blocks()} - entities)
    assert not unknown, f"blocks declare entities that entities.yaml does not: {unknown}"


def test_entities_reference_known_blocks():
    block_ids = {b.id for b in load_blocks()}
    doc = _load("entities.yaml")
    missing = []
    for name, spec in doc["entities"].items():
        for b in spec.get("blocks") or []:
            bid = b if isinstance(b, str) else b.get("id")
            if bid and bid not in block_ids:
                missing.append(f"{name}:{bid}")
    assert not missing, f"entities reference blocks that blocks.yaml does not define: {missing}"


def test_every_block_has_the_minimum_coordinates():
    for b in load_blocks():
        assert b.id and b.entity and b.source and b.sheet, b.id
        assert b.header_row >= 1 and b.first_row >= 1, b.id
        assert b.columns, f"{b.id} declares no columns"
        assert b.key_column in b.columns or not b.key_column, \
            f"{b.id} key_column {b.key_column} is not one of its columns"


def test_block_ids_are_unique():
    ids = [b.id for b in load_blocks()]
    assert len(ids) == len(set(ids))


def test_hooks_referenced_by_config_are_registered():
    doc = _load("entities.yaml")
    for name in doc.get("post_hooks") or []:
        assert name in POST_HOOKS, f"post_hooks names unregistered hook {name}"
    for entity, spec in doc["entities"].items():
        for name in spec.get("entity_hooks") or []:
            assert name in ENTITY_HOOKS, f"{entity} names unregistered entity hook {name}"
        for b in spec.get("blocks") or []:
            for hook in (b.get("row_hooks") or []) if isinstance(b, dict) else []:
                assert hook in ROW_HOOKS, f"{entity} names unregistered row hook {hook}"


def test_registered_hooks_are_all_used():
    """A hook nobody calls is dead weight - or a wiring mistake."""
    doc = _load("entities.yaml")
    used_post = set(doc.get("post_hooks") or [])
    used_entity = {n for spec in doc["entities"].values() for n in (spec.get("entity_hooks") or [])}
    used_row = {h for spec in doc["entities"].values()
                for b in (spec.get("blocks") or []) if isinstance(b, dict)
                for h in (b.get("row_hooks") or [])}
    # block-level row hooks may also be declared in blocks.yaml
    block_doc = _load("blocks.yaml")
    for entry in block_doc.get("blocks") or []:
        for h in entry.get("row_hooks") or []:
            used_row.add(h)
    assert set(POST_HOOKS) - used_post == set(), f"unreferenced post hooks: {set(POST_HOOKS) - used_post}"
    assert set(ENTITY_HOOKS) - used_entity == set(), f"unreferenced entity hooks: {set(ENTITY_HOOKS) - used_entity}"
    assert set(ROW_HOOKS) - used_row == set(), f"unreferenced row hooks: {set(ROW_HOOKS) - used_row}"


def test_sourcebooks_have_required_fields():
    doc = _load("sourcebooks.yaml")
    seen = set()
    for sb in doc["sourcebooks"]:
        assert {"id", "abbreviation", "title"} <= set(sb), sb
        assert sb["id"] not in seen, f"duplicate sourcebook id {sb['id']}"
        seen.add(sb["id"])
        assert len(sb["abbreviation"]) <= 8, sb


def test_sources_are_pinned_by_hash():
    doc = _load("sources.yaml")
    for s in doc["sources"]:
        assert {"id", "title", "path", "sha256", "canon"} <= set(s), s["id"]
        assert len(s["sha256"]) == 64, f"{s['id']} sha256 is not a full digest"
        assert set(s["canon"]) <= {"official", "third_party", "homebrew"}, s["id"]


def test_analysis_assumptions_declare_verification():
    """Every assumption must say whether it is verified, and point at its evidence."""
    doc = _load("analysis.yaml")

    def walk(node, path=""):
        if isinstance(node, dict):
            if "verified" in node:
                assert isinstance(node["verified"], bool), f"{path}.verified is not a boolean"
                if node["verified"] is False:
                    assert node.get("task") or node.get("note"), \
                        f"unverified assumption {path} has neither a task nor a note"
                else:
                    assert node.get("evidence") or node.get("source") or node.get("note"), \
                        f"verified assumption {path} cites no evidence"
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc)


def test_level_range_matches_user_scope():
    doc = _load("analysis.yaml")
    assert doc["level_range"]["min"] == 1
    assert doc["level_range"]["max"] == 20
