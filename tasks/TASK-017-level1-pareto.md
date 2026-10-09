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

## Measured shape of the search space (2026-10-09)

These are measured, not estimated - re-derive them with the snippet at the end of this
section before trusting the plan, because they move with the corpus.

| axis | size | note |
|---|---:|---|
| species | 130 | `Builder.species_pool()` |
| heroic classes | 7 | `Builder.class_pool(1, 0, [])` |
| ability allocations | 720 | every permutation of the standard array |
| discretionary feats | 163 | `Builder.feat_pool()`, returns **ids (str)**, not records |
| **product** | **106,797,600** | before skills |

- `Builder.feat_available()` costs **~8 us per call**, so feasibility-checking the full
  product is **~857 s (14 min) before scoring anything**. That call, not the scoring, is
  the bottleneck.
- Feasibility prunes almost nothing: **157 of 163** feats are available to a level-1 Jedi
  at BAB 0. Do not plan around "filter the feat pool first".
- The skill pool **does not vary by species** (Jedi: 15 skills for every species tried),
  so it is memoisable per class.
- The number of trained skills **does vary with abilities**: Jedi picks are 2 at INT mod
  0, 3 at +1, 5 at +3, 7 at +5. The skill axis is therefore ability-coupled and cannot be
  quotiented away independently of the allocation.

### The route that fits

1. **Precompute each feat's requirement pattern once** (163 feats, ~a dozen
   `ability_min` / proficiency / BAB predicates) and evaluate it inline with a few integer
   comparisons instead of calling `feat_available`. At ~0.3 us that turns the 107M inner
   loop from 857 s into roughly 30 s, which is the difference between an opt-in flag and
   an unusable one.
2. **Solve skills by memoised DP, not by enumeration.** For a given `(class, picks)` the
   only metric-relevant facts about a skill set are how many distinct key abilities it
   covers (`versatility`) and whether it completes a prerequisite edge with the chosen feat
   (`synergy`); `skill_breadth` and `option_count` depend on the count alone. DP over the
   2^6 key-ability mask with `picks` items is exact and memoises across all 130 species.
3. **Keep `Evaluator.score()` as the only definition of a score.** The fast path proposes;
   the evaluator disposes. Materialise the top-N candidates as real build dicts and assert
   the fast path's number equals `Evaluator.score()`'s. Two implementations of the same
   formula drifting apart is the failure mode this repo is built to avoid, and a fast path
   that is never checked against the slow one *is* that failure mode.
4. Everything in the original approach below still holds: publish the frontier over
   `METRICS` as well as the weighted ranking, show weight sensitivity, and cross-check
   against the sampled best.

```bash
python -c "
import time
from swse.store import Dataset
from swse.enumerate import Builder, Constraints, ability_arrays
from swse.space import ability_modifier
db = Dataset.load(); c = Constraints(); c.level = 1
b = Builder(db, c)
sp, cl = b.species_pool(), b.class_pool(1, 0, [])
perms = list(ability_arrays(db, c.ability_method, None, None))
fp = b.feat_pool()
print(len(sp), len(cl), len(perms), len(fp), len(sp)*len(cl)*len(perms)*len(fp))
cls, s, ab = cl[0], sp[0], perms[0]
final = {k: v + int(s['attrs'].get(f'mod_{k.lower()}') or 0) for k, v in ab.items()}
build = {'level': 1, 'species': s['id'], 'class_path': [{'level': 1, 'class': cls['id']}],
         'abilities_final': final, 'trained_skills': [], 'feats': [], 'talents': [],
         'force_powers': []}
t = time.time(); ok = [f for f in fp if b.feat_available(f, build, final, bab=0)]; dt = time.time()-t
print(f'feasible {len(ok)}/{len(fp)} at {dt*1e6/len(fp):.1f} us per check')
print([b.space.class_skill_choices(cls, m)['picks'] for m in (0, 1, 3, 5)])
print(len(b.skills_for(cls, s, final)), b.skills_for(cls, s, final) == b.skills_for(cls, sp[5], final))
"
```

## Approach

1. **Score exhaustively, but cheaply.** 1.69e15 builds cannot each be scored. The
   tractable route is to score the *quotient*: group builds by the choices that affect
   metrics (species, class, feats, ability allocation) and collapse the skill axis to what
   the metrics can see. Score representatives, then multiply out. Record the grouping
   argument in the report so the shortcut is auditable.

   **Correction (2026-10-09):** this step originally claimed skill selections affect only
   `skill_breadth` and `versatility`, which is wrong in two ways and would have produced a
   quietly incorrect frontier. *How many* skills a character trains depends on INT modifier
   (Jedi: 2 picks at INT mod 0, 7 at +5), so the skill axis is coupled to the ability
   allocation rather than free-floating; and `synergy` counts prerequisite edges whose
   endpoints are both inside the build, so a feat that requires a trained skill makes the
   skill set metric-relevant. `skill_breadth` and `option_count` are the only metrics that
   depend on the count alone.
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
