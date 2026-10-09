"""Report determinism.

Set iteration order in CPython depends on PYTHONHASHSEED, which is randomised per
process. Any report that slices or joins a set before sorting therefore produces
different text on different runs of identical data. That is not cosmetic: an agent
diffing two runs cannot tell a real change from noise, and a reviewer cannot tell
whether a regenerated report reflects a code change.

This was found in `unlock_ranking`, which took `list(g.unlocks(id))[:8]` before
sorting - the unlock *counts* were stable but the "sample of what it unlocks" column
reshuffled every run.

These tests run the report producers in subprocesses under two different hash seeds
and require byte-identical output (timestamp lines excluded).
"""
import os
import re
import subprocess
import sys

import pytest

from swse import paths

pytestmark = pytest.mark.slow

SCRIPT = r"""
import hashlib, re
from swse.store import Dataset
from swse import report
from swse.graph import PrereqGraph

db = Dataset.load()
g = PrereqGraph(db)
parts = [
    report.option_catalog(db),
    report.species_class_matrix(db),
    report.prestige_paths(db),
    report.unlock_ranking(db),
    report.data_dictionary(db),
]
text = "\n".join(parts)
# the header carries a generation timestamp; that is expected to differ
text = re.sub(r"(?m)^Generated:.*$", "", text)
graph_json = g.to_json()
for key in ("generated_utc", "generated"):
    graph_json.pop(key, None)
digest = hashlib.sha256(
    (text + repr(sorted(graph_json.items(), key=lambda kv: kv[0]))).encode()
).hexdigest()
print(digest)
"""

TIMESTAMP = re.compile(r"(?m)^Generated:.*$")


def _digest(seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    out = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True,
                         cwd=str(paths.ROOT), env=env, timeout=600)
    assert out.returncode == 0, f"report producers failed under PYTHONHASHSEED={seed}:\n{out.stderr[-2000:]}"
    return out.stdout.strip().splitlines()[-1]


def test_reports_are_byte_identical_across_hash_seeds():
    a = _digest("0")
    b = _digest("1")
    assert a == b, (
        "report output depends on PYTHONHASHSEED: something is iterating a set and "
        "slicing or joining it before sorting. Sort the full collection first."
    )


def test_unlock_ranking_sample_is_the_alphabetical_prefix():
    """The sample column must be the first names in sorted order, not an arbitrary 8."""
    from swse.report import unlock_ranking
    from swse.store import Dataset
    from swse.graph import PrereqGraph

    db = Dataset.load()
    g = PrereqGraph(db)
    text = unlock_ranking(db, limit=5)
    rows = [line for line in text.splitlines() if line.startswith("| ") and "`" in line]
    assert rows, "unlock_ranking produced no rows"
    for line in rows:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        name, sample = cells[1], cells[5]
        rec = next((r for r in db.records[cells[2].strip("`")] if r["name"] == name), None)
        assert rec is not None, f"row for {name!r} does not match a record"
        expected = sorted({db.by_id[u]["name"] for u in g.unlocks(rec["id"]) if u in db.by_id})[:6]
        assert sample == ", ".join(expected), (
            f"{name}: sample column {sample!r} is not the alphabetical prefix {expected!r}"
        )
