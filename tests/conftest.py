"""Shared fixtures.

The dataset fixtures skip (not fail) when ``data/canonical`` has not been built
yet, so a fresh clone can run the pure-logic tests immediately and the
data-dependent tests after ``make data``.
"""

from __future__ import annotations

import pytest

from swse import paths


@pytest.fixture(scope="session")
def canonical_ready() -> bool:
    paths.ensure_dirs()
    return bool(list(paths.CANONICAL_DIR.glob("*.json")))


@pytest.fixture(scope="session")
def db(canonical_ready):
    if not canonical_ready:
        pytest.skip("canonical data not built - run `make data`")
    from swse.store import Dataset

    return Dataset.load()


@pytest.fixture(scope="session")
def graph(db):
    from swse.graph import PrereqGraph

    return PrereqGraph(db)


@pytest.fixture(scope="session")
def space(db):
    from swse.space import DecisionSpace

    return DecisionSpace(db, level=1)


@pytest.fixture(scope="session")
def raw_ready() -> bool:
    return bool(list(paths.RAW_DIR.glob("*.jsonl")))
