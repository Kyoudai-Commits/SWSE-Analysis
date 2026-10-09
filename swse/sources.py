"""Source-workbook registry and cached workbook handles.

Loading a 2 MB Excel workbook with openpyxl takes ~5 s, and the pipeline touches
it many times, so workbooks are parsed once per process and memoised.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import openpyxl
import yaml

from . import paths


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    path: str
    sha256: str
    canon: tuple[str, ...]
    kind: str = "workbook"
    notes: str = ""
    maintainer: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def abs_path(self) -> Path:
        return paths.ROOT / self.path

    def verify(self) -> tuple[bool, str]:
        """Check the vendored file still matches the recorded hash."""
        p = self.abs_path
        if not p.exists():
            return False, f"missing file: {self.path}"
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != self.sha256:
            return False, f"sha256 mismatch for {self.path}: recorded {self.sha256[:12]}..., found {actual[:12]}..."
        return True, "ok"


@lru_cache(maxsize=1)
def load_registry() -> tuple[Source, ...]:
    doc = yaml.safe_load(paths.SOURCES_YAML.read_text(encoding="utf-8")) or {}
    out = []
    for entry in doc.get("sources", []):
        out.append(
            Source(
                id=entry["id"],
                title=entry["title"],
                path=entry["path"],
                sha256=entry.get("sha256", ""),
                canon=tuple(entry.get("canon") or ("official",)),
                kind=entry.get("kind", "workbook"),
                notes=entry.get("notes", ""),
                maintainer=entry.get("maintainer", ""),
                extra={k: v for k, v in entry.items()
                       if k not in {"id", "title", "path", "sha256", "canon", "kind", "notes", "maintainer"}},
            )
        )
    return tuple(out)


def get_source(source_id: str) -> Source:
    for s in load_registry():
        if s.id == source_id:
            return s
    raise KeyError(f"unknown source id {source_id!r}; see {paths.rel(paths.SOURCES_YAML)}")


_WORKBOOKS: dict[str, openpyxl.Workbook] = {}


def workbook(source_id: str) -> openpyxl.Workbook:
    """Memoised workbook handle (``data_only=True`` -> cached formula values)."""
    if source_id not in _WORKBOOKS:
        src = get_source(source_id)
        _WORKBOOKS[source_id] = openpyxl.load_workbook(src.abs_path, data_only=True)
    return _WORKBOOKS[source_id]


def sheet_names(source_id: str, include_hidden: bool = True) -> list[str]:
    wb = workbook(source_id)
    return [ws.title for ws in wb.worksheets if include_hidden or ws.sheet_state == "visible"]


def defined_names(source_id: str) -> dict[str, str]:
    """Name -> A1 reference, for every defined name in the workbook.

    SagaForge uses ~880 defined names as its data dictionary; they are the most
    reliable map of where each lookup table lives.
    """
    wb = workbook(source_id)
    out = {}
    for name, defn in wb.defined_names.items():
        out[name] = defn.value if hasattr(defn, "value") else str(defn)
    return out
