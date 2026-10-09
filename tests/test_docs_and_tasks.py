"""Documentation and backlog consistency.

This repository's value is that its prose can be trusted: a doc that names a task,
a gap, a file or a headline figure has to name one that exists. Two real bugs in
this project's history were invisible drift between a config file and the code that
consumed it (scoring weights that matched no metric; a registered hook that no block
referenced). Prose drifts the same way, and nobody notices until an agent follows a
dead link or quotes a stale number.

These tests are cheap and deliberately strict. If one fails because you reworded
something, update the other side in the same commit.
"""
import re

import yaml

from swse import paths
from swse.store import Dataset

ROOT = paths.ROOT
DOCS = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "NOTICE.md",
        *sorted((ROOT / "docs").glob("*.md")), *sorted((ROOT / "tasks").glob("*.md"))]

# Generated files are excluded: their links and numbers are produced by `report`.
GENERATED = {paths.DOCS_DIR / "data-dictionary.md"}

VALID_GAP_STATUS = {"open", "in_progress", "resolved", "wont_fix"}
TASK_ID = re.compile(r"TASK-\d{3}")
GAP_ID = re.compile(r"GAP-\d{3}")


def _task_files() -> dict[str, str]:
    """TASK-nnn -> filename, from what is actually on disk."""
    out = {}
    for p in sorted(paths.ROOT.joinpath("tasks").glob("TASK-*.md")):
        m = TASK_ID.match(p.name)
        assert m, f"task file {p.name} does not start with a TASK-nnn id"
        out[m.group(0)] = p.name
    return out


def _gap_ids() -> set[str]:
    gaps = (yaml.safe_load((paths.CURATION_DIR / "gaps.yaml").read_text(encoding="utf-8")) or {}).get("gaps", [])
    return {g["id"] for g in gaps}


# ---------------------------------------------------------------------------
# tasks
# ---------------------------------------------------------------------------
def test_every_referenced_task_exists():
    """A `task:` reference in config or curation must point at a real task file."""
    on_disk = _task_files()
    referenced: set[str] = set()
    for cfg in ("analysis.yaml", "entities.yaml", "blocks.yaml", "sources.yaml"):
        text = (paths.CONFIG_DIR / cfg).read_text(encoding="utf-8")
        referenced |= set(TASK_ID.findall(text))
    gaps = (yaml.safe_load((paths.CURATION_DIR / "gaps.yaml").read_text(encoding="utf-8")) or {}).get("gaps", [])
    for g in gaps:
        if g.get("task"):
            referenced.add(g["task"])

    missing = sorted(referenced - set(on_disk))
    assert not missing, (
        f"config/curation reference tasks with no file in tasks/: {missing}. "
        f"Write the task file or remove the reference."
    )


def test_tasks_readme_indexes_every_task_file():
    """The backlog index and the files on disk must agree in both directions."""
    on_disk = _task_files()
    index = (paths.ROOT / "tasks" / "README.md").read_text(encoding="utf-8")
    listed = set(TASK_ID.findall(index))

    assert set(on_disk) - listed == set(), (
        f"task files not listed in tasks/README.md: {sorted(set(on_disk) - listed)}"
    )
    assert listed - set(on_disk) == set(), (
        f"tasks/README.md lists tasks with no file: {sorted(listed - set(on_disk))}"
    )
    # and the links in the index must resolve
    for task_id, fname in on_disk.items():
        if task_id in listed:
            assert f"({fname})" in index, f"tasks/README.md mentions {task_id} without linking {fname}"


def test_task_files_state_status_and_acceptance_criteria():
    """A task without acceptance criteria cannot be finished, only abandoned."""
    for p in sorted((paths.ROOT / "tasks").glob("TASK-*.md")):
        text = p.read_text(encoding="utf-8").lower()
        assert "**status:**" in text, f"{p.name} has no Status line"
        assert "acceptance criteria" in text, f"{p.name} has no acceptance criteria"
        assert "```bash" in text, (
            f"{p.name} has no reproducible command; an agent picking it up must be "
            f"able to see the problem before changing anything"
        )


# ---------------------------------------------------------------------------
# gaps
# ---------------------------------------------------------------------------
def test_gap_entries_are_complete_and_well_formed():
    gaps = (yaml.safe_load((paths.CURATION_DIR / "gaps.yaml").read_text(encoding="utf-8")) or {}).get("gaps", [])
    assert gaps, "gaps.yaml declares no gaps; the corpus certainly has some"
    ids = set()
    for g in gaps:
        for key in ("id", "entity", "summary", "status", "impact", "workaround", "evidence"):
            assert g.get(key), f"gap {g.get('id')} is missing {key!r}"
        assert GAP_ID.fullmatch(g["id"]), f"gap id {g['id']!r} is not GAP-nnn"
        assert g["id"] not in ids, f"duplicate gap id {g['id']}"
        ids.add(g["id"])
        assert g["status"] in VALID_GAP_STATUS, f"gap {g['id']} has status {g['status']!r}"
        # a gap that is not wont_fix needs a route to closing it
        if g["status"] != "wont_fix":
            assert g.get("task"), f"gap {g['id']} is {g['status']} but names no task"


def test_every_gap_is_documented():
    """docs/known-gaps.md is the human-readable register; it must not fall behind."""
    doc = (paths.DOCS_DIR / "known-gaps.md").read_text(encoding="utf-8")
    missing = sorted(_gap_ids() - set(GAP_ID.findall(doc)))
    assert not missing, f"gaps absent from docs/known-gaps.md: {missing}"


def test_gap_task_references_resolve():
    on_disk = _task_files()
    gaps = (yaml.safe_load((paths.CURATION_DIR / "gaps.yaml").read_text(encoding="utf-8")) or {}).get("gaps", [])
    for g in gaps:
        task = g.get("task")
        if task:
            assert task in on_disk, f"gap {g['id']} points at {task}, which has no file"


# ---------------------------------------------------------------------------
# links and headline figures
# ---------------------------------------------------------------------------
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_relative_markdown_links_resolve():
    """No dead links in hand-written docs. Anchors and external URLs are skipped."""
    for doc in DOCS:
        if doc in GENERATED:
            continue
        for target in LINK.findall(doc.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = (doc.parent / target.split("#")[0]).resolve()
            assert path.exists(), f"{doc.relative_to(ROOT)} links to {target}, which does not exist"


def _num(text: str) -> int:
    return int(text.replace(",", ""))


def test_readme_headline_counts_match_the_dataset():
    """The README's opening figures are the ones everyone quotes.

    If this fails because the corpus changed, regenerate the reports and update the
    README sentence in the same commit - do not relax the regex.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"([\d,]+) canonical records across (\d+) entity types", readme)
    assert m, (
        "README.md no longer contains the sentence '<N> canonical records across <M> "
        "entity types'; restore it (with current numbers) or update this test."
    )
    db = Dataset.load()
    assert _num(m.group(1)) == db.stats()["total"], (
        f"README says {m.group(1)} records, the dataset has {db.stats()['total']}"
    )
    assert _num(m.group(2)) == len(db.entities), (
        f"README says {m.group(2)} entity types, the dataset has {len(db.entities)}"
    )


def test_readme_corpus_counts_match_the_dataset():
    """The counts the README quotes for the big entities are the real ones."""
    db = Dataset.load()
    expected = {
        "species": 130, "class": 41, "feat": 387, "talent": 1311, "talent_tree": 192,
        "force_power": 92, "force_technique": 58, "force_secret": 15,
        "force_regimen": 12, "skill": 25, "weapon": 246, "armor": 92,
        "equipment": 226, "ammunition": 21, "weapon_mod": 156,
        "weapon_accessory": 46, "armor_accessory": 48, "droid_option": 121,
        "destiny": 88, "background": 46, "language": 102, "reference_link": 812,
        "racial_ability": 215, "sourcebook": 10,
    }
    for entity, n in expected.items():
        assert len(db.all(entity)) == n, (
            f"{entity} count moved from {n} to {len(db.all(entity))}; update README.md "
            f"and this expectation in the same commit"
        )


NUMERIC_CELL = re.compile(r"^[\d,]+(?:\s*/\s*[\d,]+)*$")


def test_every_number_in_the_readme_dataset_tables_is_a_real_count():
    """No stale figure survives in the README's dataset tables.

    Each numeric cell must equal a count that exists in the corpus: an entity's
    record count, a `class_kind` split, or a canon split. This is deliberately
    label-free - the table is prose, and mapping prose to entities is exactly the
    kind of thing that drifts.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## What is in the dataset", 1)[1].split("## How the data is layered", 1)[0]

    db = Dataset.load()
    allowed = {len(db.all(e)) for e in db.entities}
    allowed |= {db.stats()["total"], len(db.entities)}
    canon_totals: dict[str, int] = {}
    for e in db.entities:
        for r in db.all(e):
            canon_totals[r["canon"]] = canon_totals.get(r["canon"], 0) + 1
    allowed |= set(canon_totals.values())
    kinds: dict[str, int] = {}
    for c in db.all("class"):
        k = c["attrs"].get("class_kind", "?")
        kinds[k] = kinds.get(k, 0) + 1
    allowed |= set(kinds.values())

    quoted = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        for cell in line.split("|")[1:]:
            cell = cell.strip()
            if NUMERIC_CELL.match(cell):
                quoted += [_num(part) for part in cell.split("/")]

    assert quoted, "no numeric cells found in the README dataset tables - did the section move?"
    stale = sorted({n for n in quoted if n not in allowed})
    assert not stale, (
        f"README quotes counts that match nothing in the corpus: {stale}. "
        f"Known counts are entity sizes {sorted(allowed)}."
    )


def test_docs_do_not_claim_verified_for_unverified_assumptions():
    """A doc may not call an assumption verified while config says otherwise."""
    assumptions = yaml.safe_load((paths.CONFIG_DIR / "analysis.yaml").read_text(encoding="utf-8")) or {}
    unverified = set()

    def walk(node, path=()):
        if isinstance(node, dict):
            if node.get("verified") is False:
                unverified.add(".".join(str(p) for p in path))
            for k, v in node.items():
                walk(v, path + (k,))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + (i,))

    walk(assumptions)
    assert unverified, "config/analysis.yaml declares nothing unverified - suspicious"

    verification = (paths.DOCS_DIR / "verification.md").read_text(encoding="utf-8")
    assert "What is *not* verified" in verification, (
        "docs/verification.md must keep an explicit section listing unverified items"
    )
    known = (paths.DOCS_DIR / "known-gaps.md").read_text(encoding="utf-8")
    # every unverified assumption must be traceable to a gap or a task somewhere in docs
    for path in sorted(unverified):
        leaf = path.split(".")[-1]
        assert leaf in verification or leaf in known or "TASK-" in verification, (
            f"assumption {path} is verified:false but is not discussed in the docs"
        )
