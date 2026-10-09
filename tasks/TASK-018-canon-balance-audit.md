# TASK-018 - Audit metric distributions across canon tiers

**Status:** open | **Priority:** medium

## Problem

The corpus is 3,689 official, 1,139 third-party and 2 homebrew records. Third-party
content is included by design and tagged by provenance, but nobody has checked whether
it is *balanced* against the official baseline. If SagaForge-only options score
systematically higher than official ones, every mixed-canon ranking is quietly
dominated by content the printed game never published - and the 25 SagaForge-only
talent trees (Idealogue, Gambling Leader, Recklessness, Smuggler, Unpredictable,
Ambusher, First-Fifth-Degree Droid, Wingman, Republican Commando, Pathfinder) are the
obvious suspects.

The reverse is also worth knowing: if third-party content scores *lower*, it is
evidence the extraction preserved it faithfully rather than inflating it.

This is a verification task about the dataset, not a game-balance task.

## Evidence

```bash
python -m swse.cli stats --json | jq '.by_canon'
python -c "
from swse.store import Dataset; from swse.evaluate import Evaluator, METRICS
db=Dataset.load(); ev=Evaluator(db)
print(METRICS)"
python -m swse.cli evaluate --level 20 --sample 300 --seed 20261008 --json
```

## Approach

1. **Compare like with like.** For each option entity, compute the metric contribution
   per record (e.g. a feat's marginal `offense`/`durability` delta) and compare the
   distributions across canon tiers. Report medians and interquartile ranges, not
   means - the distributions are skewed.
2. **Control for the confounders.** Third-party content is concentrated in talent trees
   and feats; official content covers gear and species. Compare within entity type, and
   within a level band, or the comparison measures corpus composition rather than
   balance.
3. **Publish the audit** as `analysis/out/canon-balance.md` with the sample sizes, the
   test used, and an explicit statement of what a difference would and would not prove.
   A statistical difference is not evidence of bad extraction; it is a prompt to inspect
   specific records.
4. **Inspect the outliers.** For any tier that scores significantly higher, list the top
   contributing records and check them by hand against their source cells. If a record
   is inflated by a parsing artefact (a concatenated damage value, a doubled bonus),
   that is a bug to fix in `swse/hooks.py` and a gap to declare - not a balance finding.

## Acceptance criteria

- [ ] `analysis/out/canon-balance.md` reports per-entity-type metric distributions by
      canon tier, with sample sizes and the comparison method named.
- [ ] Every outlier in the top decile of any tier is individually inspected, and the
      report records the verdict (real content / parsing artefact / missing data).
- [ ] Any parsing artefact found becomes a fix in `swse/hooks.py` plus a regression
      test, and a `data/curation/gaps.yaml` entry if the data is genuinely absent.
- [ ] The report states whether mixed-canon rankings are safe to publish, and if not,
      what `--canon official` should be used for instead.
- [ ] A test asserts the audit's inputs (per-tier record counts) match `swse stats`.

## Files likely to change

`swse/report.py`, `swse/cli.py`, possibly `swse/hooks.py`, `tests/`.
