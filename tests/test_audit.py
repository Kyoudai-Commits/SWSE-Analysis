"""The canon-balance audit: statistics, classification, and the report's honesty.

Two things are worth testing hard here. The statistics, because a wrong p-value is
worse than no p-value. And the report's *refusals* - it must not quote a p-value from
a handful of records, and it must not present a data gap (the unscoreable homebrew
classes) as a balance finding.
"""
import math
import re

import pytest
import yaml

from swse import paths
from swse.audit import (MIN_COMPARABLE_N, canon_balance, describe, mann_whitney_u,
                        non_official_options, quantile, suspicious_numeric_attrs)
from swse.store import Dataset


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def test_quantile_interpolates():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([1, 2, 3, 4], 0.0) == 1
    assert quantile([1, 2, 3, 4], 1.0) == 4
    assert quantile([5], 0.5) == 5
    assert math.isnan(quantile([], 0.5))


def test_describe_reports_median_and_iqr_not_just_mean():
    d = describe([1, 2, 3, 4, 100])
    assert d["n"] == 5
    assert d["median"] == 3
    assert d["max"] == 100
    assert d["mean"] == 22          # the mean is why the median is reported
    assert d["p25"] < d["median"] < d["p75"]
    assert describe([])["n"] == 0


def test_mann_whitney_separates_disjoint_groups():
    mw = mann_whitney_u([1, 2, 3, 4, 5], [10, 11, 12, 13, 14])
    assert mw["U"] == 0             # complete separation
    assert mw["p"] < 0.05


def test_mann_whitney_gives_no_signal_for_identical_groups():
    a = [1, 2, 3, 4, 5, 6, 7, 8]
    mw = mann_whitney_u(a, list(a))
    assert mw["p"] > 0.5


def test_mann_whitney_survives_heavy_ties():
    """All-equal groups make the tie correction collapse sigma; that must not crash."""
    mw = mann_whitney_u([5] * 10, [5] * 10)
    assert mw["p"] is None or 0 <= mw["p"] <= 1
    mixed = mann_whitney_u([1, 1, 1, 2, 2], [1, 2, 2, 3, 3])
    assert 0 <= mixed["p"] <= 1


def test_mann_whitney_refuses_groups_too_small_to_mean_anything():
    assert mann_whitney_u([1], [2, 3, 4])["p"] is None
    assert mann_whitney_u([], [1, 2])["p"] is None


def test_mann_whitney_u_is_symmetric_in_p():
    a, b = [1, 3, 5, 7, 9], [2, 4, 6, 8, 10]
    assert mann_whitney_u(a, b)["p"] == mann_whitney_u(b, a)["p"]


# ---------------------------------------------------------------------------
# build classification
# ---------------------------------------------------------------------------
def test_non_official_options_separates_third_party_from_homebrew(db):
    """The distinction the whole audit turns on: homebrew classes are unscoreable."""
    official = {"species": "species_human",
                "class_path": [{"class": "class_soldier", "level": 1}],
                "feats": [], "talents": [], "force_powers": []}
    assert non_official_options(db, official) == []

    third_party = dict(official, species="species_devaronian")
    found = non_official_options(db, third_party)
    assert [rid for rid, _ in found] == ["species_devaronian"]
    assert found[0][1] == "third_party"

    homebrew = dict(official, class_path=[{"class": "class_force_prodigy", "level": 1}])
    found = non_official_options(db, homebrew)
    assert found and found[0][1] == "homebrew"


def test_homebrew_classes_really_are_unscoreable(db):
    """The claim the report makes about GAP-013, checked against the data."""
    for cid in ("class_technician", "class_force_prodigy"):
        rec = db.get("class", cid)
        assert rec is not None, f"{cid} missing from the corpus"
        assert rec["canon"] == "homebrew"
        for field in ("hit_die", "bab_progression", "reflex_progression"):
            assert rec["attrs"].get(field) in (None, ""), (
                f"{cid} gained a {field}; GAP-013 may have closed - update the audit text")


# ---------------------------------------------------------------------------
# data quality
# ---------------------------------------------------------------------------
def test_suspicious_numeric_attrs_finds_the_known_builder_columns(db):
    """Regression guard: droid_option carries attrs named '5', '6' and '9'."""
    found = dict(((e, k), n) for e, k, n in suspicious_numeric_attrs(db))
    assert ("droid_option", "6") in found
    assert ("droid_option", "5") in found
    assert all(isinstance(n, int) and n > 0 for n in found.values())


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------
def test_audit_tier_counts_match_the_dataset(db):
    text = canon_balance(db, top=1, include_builds=False)
    section = text.split("## Corpus by tier", 1)[1].split("##", 1)[0]
    for tier, expected in (("official", 3689), ("third_party", 1139), ("homebrew", 2)):
        m = re.search(rf"\| `{tier}` \| (\d+) \|", section)
        assert m, f"no row for {tier} in the corpus-by-tier table"
        assert int(m.group(1)) == expected, f"{tier} count moved from {expected}"
        # and it must agree with the dataset itself, not with a hard-coded number
        actual = sum(1 for e in db.entities for r in db.all(e) if r.get("canon") == tier)
        assert int(m.group(1)) == actual


def test_audit_never_quotes_a_p_value_from_a_tiny_group(db):
    """The refusal is the feature: p from n=4 is noise dressed as a finding."""
    text = canon_balance(db, top=1, include_builds=False)
    for line in text.splitlines():
        if "insufficient overlap to compare" in line:
            m = re.search(r"official n=(\d+), third_party n=(\d+)", line)
            assert m, f"unparsable refusal line: {line}"
            assert min(int(m.group(1)), int(m.group(2))) < MIN_COMPARABLE_N
            assert "p=" not in line, "a refused comparison must not also quote a p-value"
        if "-> " in line and "p=" in line:
            m = re.search(r"official \(n=(\d+)\) vs third_party \(n=(\d+)\)", line)
            assert m, f"p-value quoted without stating both sample sizes: {line}"
            assert min(int(m.group(1)), int(m.group(2))) >= MIN_COMPARABLE_N


def test_audit_names_the_confound(db):
    """The composition table is the finding that makes the rest interpretable."""
    text = canon_balance(db, top=1, include_builds=False)
    assert "confounded with entity type" in text
    assert "Single-tier entity types" in text
    # racial_ability is entirely third-party; the report must say so
    assert re.search(r"`racial_ability` \((official|third_party|homebrew)\)", text)


def test_audit_without_builds_says_the_build_half_is_missing(db):
    text = canon_balance(db, top=1, include_builds=False)
    assert "**Build-level: not run.**" in text


def test_audit_verdicts_reference_real_records_and_known_verdicts(db):
    path = paths.CURATION_DIR / "audit-verdicts.yaml"
    assert path.exists(), "audit-verdicts.yaml is gone; the report loses its verdict column"
    verdicts = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("verdicts", {})
    assert verdicts, "no verdicts recorded - the audit's outliers have not been inspected"
    for rid, v in verdicts.items():
        assert db.by_id.get(rid) is not None, f"verdict for unknown record {rid}"
        assert v.get("verdict") in {"real", "artefact", "missing"}, f"{rid}: bad verdict"
        assert v.get("note"), f"{rid}: verdict with no note explains nothing"
        assert v.get("checked_utc"), f"{rid}: verdict with no date cannot be re-checked"


def test_verdicts_cover_the_outliers_the_report_shows(db):
    """Every outlier the report shows at the default depth should have been looked at.

    Scoped to the Outliers section and to rows whose first cell is the numeric value,
    so entity-name cells from the composition and most-used tables are not mistaken
    for record ids.
    """
    text = canon_balance(db, top=3, include_builds=False)
    section = text.split("## Outliers", 1)[1].split("## Data-quality", 1)[0]
    shown = {m.group(1) for m in
             (re.match(r"^\|\s*[-\d.]+\s*\|\s*`([a-z0-9_]+)`\s*\|", line)
              for line in section.splitlines()) if m}
    assert len(shown) >= 20, f"only {len(shown)} outlier rows parsed - did the report shape change?"
    verdicts = (yaml.safe_load((paths.CURATION_DIR / "audit-verdicts.yaml")
                               .read_text(encoding="utf-8")) or {}).get("verdicts", {})
    missing = sorted(shown - set(verdicts))
    assert not missing, (
        f"outliers shown by `audit --top 3` with no hand-inspection verdict: {missing}. "
        f"Inspect them against their source cell and add an entry to "
        f"data/curation/audit-verdicts.yaml."
    )
