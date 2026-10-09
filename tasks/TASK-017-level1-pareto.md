# TASK-017 - Rank every legal level-1 build and publish the frontier

**Status:** open | **Priority:** medium

## Problem

Level 1 is the only level the pipeline can enumerate **exactly**: 1,691,028,090,892,800
legal builds, verified with 0 violations in 0.4s for a 4,000-build slice. But
`evaluate` currently scores a *sample* (the digest covers the top 10 of 300 sampled
builds), so the published level-1 ranking is "best of a sample", not "best".

The interesting questions are unanswerable from a sample:

- What is the actual best level-1 build under the declared weights?
- Which builds are Pareto-optimal - best on some metric without being dominated?
- How flat is the top? The current level-1 top ties at 49.40 (Aleena/Jedi), which
  suggests a large plateau that a 300-build sample cannot characterise.
- Which species/class pairs are never competitive, and is that a balance finding or a
  data gap?

## Evidence

```bash
python -m swse.cli enumerate --level 1 --limit 4000 --check --quiet --json
python -m swse.cli evaluate --level 1 --sample 300 --seed 20261008 --json
head -40 analysis/out/builds-level1.md
```

## Approach

1. **Score exhaustively, but cheaply.** 1.69e15 builds cannot each be scored. The
   tractable route is to score the *quotient*: group builds by the choices that affect
   metrics (species, class, feats, ability allocation) and note that skill selections
   only affect `skill_breadth`/`versatility`. Score representatives, then multiply out.
   Record the grouping argument in the report so the shortcut is auditable.
2. **Publish the Pareto frontier** over `METRICS`, not a single weighted ranking. A
   weighted total is one opinion; the frontier is a fact. Keep both.
3. **Report weight sensitivity.** The weights in `config/analysis.yaml:scoring.weights`
   are a declared opinion. Show how the top-10 changes under 2-3 alternative weight
   sets (offense-heavy, defense-heavy, versatility-heavy). This is the honest way to
   present a ranking.
4. **Cross-check against the sample.** The exhaustive top set must contain the sampled
   top build; if it does not, one of the two is wrong.

## Acceptance criteria

- [ ] `analysis/out/builds-level1-pareto.md` lists the frontier with each build's
      metric vector and why nothing dominates it.
- [ ] The exhaustive best matches or beats the sampled best, and the report states the
      relationship explicitly.
- [ ] A weight-sensitivity table shows the top-10 under at least three weight sets.
- [ ] The grouping/quotient argument is written down and a test asserts that two builds
      in the same group really do score identically.
- [ ] Runtime is recorded; if the full pass exceeds a few minutes, the CLI grows a
      `--exhaustive` flag and the default stays sampled.

## Files likely to change

`swse/evaluate.py`, `swse/report.py`, `swse/cli.py`, `Makefile`,
`tests/test_enumerate_evaluate.py`.
