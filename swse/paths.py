"""Repository layout helpers.

Every module resolves paths through here so that the tooling can be run from any
working directory and so that an agent reading the code can see the whole layout
in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Repository root (the directory that holds this package's parent).
ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CANONICAL_DIR = DATA_DIR / "canonical"
CURATION_DIR = DATA_DIR / "curation"
INDEX_DIR = DATA_DIR / "index"
REPORTS_DIR = DATA_DIR / "reports"
SCHEMA_DIR = ROOT / "schemas"
DOCS_DIR = ROOT / "docs"
TASKS_DIR = ROOT / "tasks"
ANALYSIS_DIR = ROOT / "analysis"
TESTS_DIR = ROOT / "tests"

SOURCES_YAML = CONFIG_DIR / "sources.yaml"
BLOCKS_YAML = CONFIG_DIR / "blocks.yaml"
ENTITIES_YAML = CONFIG_DIR / "entities.yaml"
SOURCEBOOKS_YAML = CONFIG_DIR / "sourcebooks.yaml"

SQLITE_PATH = INDEX_DIR / "swse.sqlite3"

#: Directories that must exist before any pipeline stage runs.
MANAGED_DIRS = (
    RAW_DIR,
    CANONICAL_DIR,
    CURATION_DIR,
    INDEX_DIR,
    REPORTS_DIR,
    ANALYSIS_DIR / "out",
)


def ensure_dirs() -> None:
    """Create every managed directory (idempotent)."""
    for d in MANAGED_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def rel(path: os.PathLike | str) -> str:
    """Path relative to the repo root, with forward slashes (stable in reports)."""
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()
