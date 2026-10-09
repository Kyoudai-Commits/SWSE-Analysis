#!/usr/bin/env python3
"""Re-record the sha256 of the vendored source workbooks.

``config/sources.yaml`` pins every source file by hash so that `swse validate`
can prove the canonical data was built from the bytes you think it was. When you
deliberately replace a workbook (a new SagaForge release, a refreshed Master
Reference), run this to update the pin:

    python3 scripts/hashes.py            # show what would change
    python3 scripts/hashes.py --write    # update config/sources.yaml

It only ever touches the ``sha256`` field, and it prints a diff-style summary so
an unintended source swap is obvious.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swse import paths                                     # noqa: E402
from swse.sources import load_registry                     # noqa: E402


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="update config/sources.yaml")
    args = ap.parse_args(argv)

    text = paths.SOURCES_YAML.read_text(encoding="utf-8")
    changed = 0
    for s in load_registry():
        p = s.abs_path
        if not p.exists():
            print(f"  MISSING  {s.id:<34} {paths.rel(p)}")
            continue
        actual = sha256_of(p)
        if actual == s.sha256:
            print(f"  ok       {s.id:<34} {actual[:16]}...")
            continue
        changed += 1
        print(f"  CHANGED  {s.id:<34} recorded {s.sha256[:16]}... -> found {actual[:16]}...")
        if args.write:
            if s.sha256 not in text:
                print(f"    !! recorded hash not found verbatim in {paths.rel(paths.SOURCES_YAML)}", file=sys.stderr)
                continue
            text = text.replace(s.sha256, actual)

    if args.write and changed:
        paths.SOURCES_YAML.write_text(text, encoding="utf-8")
        print(f"\nupdated {changed} hash(es) in {paths.rel(paths.SOURCES_YAML)}")
        print("now re-run: make data   (the canonical data must be rebuilt from the new bytes)")
    elif changed:
        print(f"\n{changed} source(s) differ from the pinned hash; re-run with --write to accept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
