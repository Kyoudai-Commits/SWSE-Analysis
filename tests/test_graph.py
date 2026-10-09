"""Prerequisite graph invariants."""

from __future__ import annotations

def test_graph_has_edges(graph):
    assert len(graph.edges()) > 500


def test_no_circular_prerequisites(graph):
    """A cycle would make build legality undecidable."""
    assert graph.cycles() == []


def test_no_dangling_requirements(graph):
    """Every named option resolves to a canonical record."""
    dangling = graph.dangling()
    assert not dangling, [ (d["src_id"], d["req_type"], d.get("req_key")) for d in dangling[:5] ]


def test_edges_carry_their_predicate(graph):
    for e in graph.edges()[:200]:
        assert e["src_id"] and e["req_type"]
        assert isinstance(e.get("predicate"), dict)
        assert e["mode"] in {"all", "any"}


def test_requires_and_required_by_are_symmetric(graph):
    edges = graph.edges()
    sample = [e for e in edges if e.get("req_id")][:50]
    assert sample
    for e in sample:
        assert any(x.get("req_id") == e["req_id"] for x in graph.requires(e["src_id"]))
        assert any(x["src_id"] == e["src_id"] for x in graph.required_by(e["req_id"]))


def test_closure_is_transitive(graph, db):
    knight = db.get("class", "class_jedi_knight")
    assert knight is not None
    closure = graph.closure(knight["id"])
    assert closure, "Jedi Knight must require something"
    direct = {e["req_id"] for e in graph.requires(knight["id"]) if e.get("req_id")}
    assert direct <= closure, "closure must contain the direct requirements"


def test_unlocks_finds_dependents(graph):
    """Some options are load-bearing: taking them opens several other options."""
    req_ids = {e["req_id"] for e in graph.edges() if e.get("req_id")}
    assert req_ids
    counts = {rid: len(graph.unlocks(rid)) for rid in req_ids}
    assert max(counts.values()) >= 3, "no option unlocks anything substantial"


def test_depth_is_finite_and_small(graph):
    depths = graph.depth()
    assert depths
    assert max(depths.values()) <= 8, f"prerequisite chains deeper than expected: {max(depths.values())}"


def test_deepest_chains(graph):
    chains = graph.deepest_chains(limit=5)
    assert chains
    assert all(len(c) >= 2 for c in chains)


def test_stats_shape(graph):
    st = graph.stats()
    for key in ("edges", "resolved_edges", "dangling_edges", "nodes", "max_chain_depth", "cycles"):
        assert key in st
    assert st["dangling_edges"] == 0
    assert st["cycles"] == 0
    assert st["resolved_edges"] / st["edges"] > 0.9


def test_parameterised_requirements_are_recorded(graph):
    """Weapon Proficiency (Pistols) is the generic feat plus a parameter."""
    params = [e for e in graph.edges() if e.get("param")]
    assert params, "expected parameterised prerequisite edges"
    assert any(e["req_id"] == "feat_weapon_proficiency" for e in params)
