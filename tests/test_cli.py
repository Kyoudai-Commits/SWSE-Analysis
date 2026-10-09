"""CLI smoke tests.

Every stage must be runnable as a command and must report its result in a shape
an agent can parse with ``--json``.
"""

from __future__ import annotations

import json

import pytest

from swse import paths
from swse.cli import main


def run(argv, capsys) -> dict:
    rc = main(argv)
    out = capsys.readouterr().out
    return {"rc": rc, "out": out}


def test_doctor_passes(capsys):
    res = run(["doctor", "--json"], capsys)
    assert res["rc"] == 0
    doc = json.loads(res["out"])
    assert doc["ok"] is True
    assert doc["problems"] == []


def test_stats_json_is_parseable(capsys, db):
    res = run(["stats", "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["total"] == db.total()
    assert set(doc["by_canon"]) <= {"official", "third_party", "homebrew"}
    assert sum(doc["by_canon"].values()) == doc["total"]
    assert doc["counts"]["talent"] > 1000


def test_stats_entity_drilldown(capsys, db):
    res = run(["stats", "--entity", "species", "--limit", "2", "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["entity"] == "species"
    assert doc["records"] == db.count("species")
    assert len(doc["sample"]) == 2
    assert "attrs" in doc["sample"][0]


def test_validate_reports_no_errors(capsys, db):
    res = run(["validate", "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["rc"] if "rc" in doc else True
    assert doc["errors"] == 0
    assert doc["ok"] is True


def test_space_writes_a_report(capsys, db, tmp_path):
    out = tmp_path / "space.md"
    res = run(["space", "--level", "1", "--out", str(out), "--json"], capsys)
    doc = json.loads(res["out"])
    assert out.exists()
    assert doc["level"] == 1
    text = out.read_text(encoding="utf-8")
    assert "decision space" in text.lower()
    assert doc["dimensions"] >= 12


def test_graph_writes_a_report(capsys, db):
    res = run(["graph", "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["dangling_edges"] == 0
    assert doc["cycles"] == 0
    assert (paths.REPORTS_DIR / "prerequisite-graph.md").exists()


def test_enumerate_and_evaluate_roundtrip(capsys, db, tmp_path):
    builds = tmp_path / "builds.jsonl"
    res = run(["enumerate", "--level", "1", "--exact", "--limit", "20", "--check",
               "--out", str(builds), "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["builds"] == 20
    assert doc["violations"] == 0
    assert builds.exists()

    digest = tmp_path / "digest.md"
    res = run(["evaluate", "--builds", str(builds), "--top", "5", "--out", str(digest), "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["builds"] == 20
    assert digest.exists()
    assert "Sampled build digest" in digest.read_text(encoding="utf-8")


def test_enumerate_sampling_with_seed(capsys, db, tmp_path):
    out = tmp_path / "sampled.jsonl"
    res = run(["enumerate", "--level", "5", "--sample", "10", "--seed", "99",
               "--out", str(out), "--json"], capsys)
    doc = json.loads(res["out"])
    assert doc["builds"] == 10
    assert doc["mode"] == "sampled level-5"


def test_evaluate_without_builds_fails_cleanly(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ANALYSIS_DIR", tmp_path)
    rc = main(["evaluate", "--json"])
    assert rc == 2


def test_report_writes_every_analysis_document(capsys, db):
    res = run(["report", "--json"], capsys)
    doc = json.loads(res["out"])
    names = {p.split("/")[-1] for p in doc["reports"]}
    assert {"option-catalog.md", "species-class-matrix.md", "prestige-paths.md",
            "unlock-ranking.md", "prerequisite-graph.md", "validation.md"} <= names
    for rel in doc["reports"]:
        assert (paths.ROOT / rel).exists(), rel


def test_unknown_command_is_rejected():
    with pytest.raises(SystemExit):
        main(["not-a-stage"])


def test_help_lists_every_stage(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for stage in ("doctor", "extract", "canonicalize", "validate", "db", "stats",
                  "graph", "space", "enumerate", "evaluate", "report", "all"):
        assert stage in out
