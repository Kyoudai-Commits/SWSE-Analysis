"""Stage 1: workbook -> ``data/raw/<block>.jsonl``.

Every emitted row keeps enough provenance to be traced back to the exact cells
it came from, so any downstream claim can be re-verified against the source
workbook:

.. code-block:: json

   {"_block": "sf_feats", "_row": 9, "_ref": "Feats!C9:N9",
    "name": "A Few Maneuvers", "prerequisites": "Dodge, Vehicular Combat", ...}

Raw dumps are *not* committed (see .gitignore); regenerate with
``make raw`` or ``python -m swse.cli extract``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import paths
from .blocks import Block, cell_value, load_blocks
from .ids import is_blank
from .sources import workbook


def detect_last_row(ws, block: Block) -> int:
    """Last row of the block, found by scanning for a run of empty rows."""
    if block.last_row:
        return block.last_row
    cols = block.columns or [block.key_column]
    max_row = ws.max_row
    blanks = 0
    last = block.first_row - 1
    for r in range(block.first_row, max_row + 1):
        present = any(not is_blank(ws[f"{c}{r}"].value) for c in cols if c)
        if present:
            last = r
            blanks = 0
        else:
            blanks += 1
            if blanks >= block.blank_run:
                break
    return last


def extract_block(block: Block) -> tuple[list[dict], int]:
    """Return ``(rows, skipped_rows)``."""
    ws = workbook(block.source)[block.sheet]
    last = detect_last_row(ws, block)
    cols = block.columns or ([block.key_column] if block.key_column else [])
    if not cols:
        raise ValueError(f"block {block.id}: no columns and no key_column")

    headers = {c: ws[f"{c}{block.header_row}"].value for c in cols}
    fields = {c: block.field_for(c, headers[c]) for c in cols}

    # duplicate field names would silently drop data -> make them unique
    seen: Counter = Counter()
    for c in cols:
        f = fields[c]
        seen[f] += 1
        if seen[f] > 1:
            fields[c] = f"{f}_{seen[f]}"

    fill_state: dict[str, object] = {}
    rows: list[dict] = []
    skipped = 0
    for r in range(block.first_row, last + 1):
        if block.require_key and block.key_column:
            if is_blank(ws[f"{block.key_column}{r}"].value):
                skipped += 1
                continue
        rec: dict = {"_block": block.id, "_row": r, "_ref": block.ref(r)}
        empty = True
        for c in cols:
            v = cell_value(ws, r, c)
            if c in block.forward_fill:
                if v is None:
                    v = fill_state.get(c)
                else:
                    fill_state[c] = v
            if v is not None:
                empty = False
            rec[fields[c]] = v
        if empty:
            skipped += 1
            continue
        rows.append(rec)
    return rows, skipped


def extract_all(blocks: list[Block] | None = None, verbose: bool = True) -> dict[str, dict]:
    """Extract every block to ``data/raw`` and write ``data/raw/_extract_stats.json``."""
    from datetime import datetime, timezone

    from .sources import load_registry

    paths.ensure_dirs()
    blocks = blocks or load_blocks()
    stats: dict[str, dict] = {}
    for b in blocks:
        rows, skipped = extract_block(b)
        out = paths.RAW_DIR / f"{b.id}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for rec in rows:
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=False) + "\n")
        stats[b.id] = {
            "entity": b.entity, "source": b.source, "sheet": b.sheet,
            "rows": len(rows), "skipped": skipped,
            "range": f"{b.columns[0]}{b.first_row}:{b.columns[-1]}{detect_last_row(workbook(b.source)[b.sheet], b)}" if b.columns else "",
            "file": paths.rel(out),
        }
        if verbose:
            extra = f"  (skipped {skipped})" if skipped else ""
            print(f"  {b.id:<32} {len(rows):>5} rows{extra}  -> {paths.rel(out)}")
    # Remove dumps for blocks that no longer exist. A renamed or split block would
    # otherwise leave a stale file in data/raw that looks like current data.
    current = {f"{b.id}.jsonl" for b in blocks} | {"_extract_stats.json"}
    pruned = []
    for p in sorted(paths.RAW_DIR.glob("*.jsonl")):
        if p.name not in current:
            p.unlink()
            pruned.append(p.name)
            if verbose:
                print(f"  pruned stale dump: {paths.rel(p)}")
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": [{"id": s.id, "path": s.path, "sha256": s.sha256} for s in load_registry()],
        "blocks": stats,
        "totals": {"blocks": len(stats), "rows": sum(v["rows"] for v in stats.values()),
                   "skipped": sum(v["skipped"] for v in stats.values())},
        "pruned_stale_dumps": pruned,
    }
    (paths.RAW_DIR / "_extract_stats.json").write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return stats


def read_raw(block_id: str) -> list[dict]:
    p: Path = paths.RAW_DIR / f"{block_id}.jsonl"
    if not p.exists():
        raise FileNotFoundError(
            f"raw dump {p} missing - run `python -m swse.cli extract` first"
        )
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
