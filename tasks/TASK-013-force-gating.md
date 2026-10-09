# TASK-013 - Source the Force powers-known allowance

**Status:** open | **Priority:** medium | **Gap:** GAP-004

## Problem

The corpus holds 92 `force_power`, 58 `force_technique`, 15 `force_secret` and 12
`force_regimen` records, all fully cited (the `page_to_sourcebooks` hook was wired to
the three Force blocks specifically so these would carry their printed page numbers).
What is *not* encoded is how many a character may know.

`config/analysis.yaml:force` declares a placeholder allowance (1 + CHA mod) with
`verified: false`. `swse.evaluate` scores Force builds by counting known powers, so a
Force-heavy build's `force_power` metric is currently a function of an unsourced
formula.

Force users are also the corpus's deepest prerequisite chains - `Force Sensitivity`
and `Force Training` gate most of them - so this dimension interacts with the graph
more than any other.

## Evidence

```bash
grep -n -A 10 "^force:" config/analysis.yaml
python -c "
from swse.store import Dataset; db=Dataset.load()
for e in ('force_power','force_technique','force_secret','force_regimen'):
    print(e, len(db.all(e)))"
python -c "
from swse.store import Dataset; from swse.graph import PrereqGraph
g=PrereqGraph(Dataset.load())
print([c for c in g.deepest_chains(5)])"
```

## Approach

1. Source the allowance: SECR's Force chapter plus *Jedi Academy Training Manual*
   (JATM is the most-cited supplement in the Master Reference after GoI and TFU, at
   157 tags). Register as a source per TASK-002.
2. Model it as data in `config/analysis.yaml:force` with `verified: true`, keyed by
   what actually grants powers (Force Sensitivity, Force Training, class features,
   Force Prodigy's `grants_all_trees`-style blanket grants).
3. Enforce it in `enumerate.check_build`: a build knowing more powers than its
   allowance is a violation.
4. Score it in `evaluate` against the allowance rather than raw count - "powers known
   / powers allowed" is the comparable quantity across builds.

## Acceptance criteria

- [ ] `force.powers_known.verified` is `true` with evidence.
- [ ] `enumerate` rejects over-allowance Force builds; a test asserts it, and the
      level-10/20 samples are re-run and reported.
- [ ] `evaluate`'s `force_power` metric is documented in `METRICS` as a ratio, and
      `config/analysis.yaml:scoring.weights` still matches `METRICS` exactly
      (`tests/test_config.py` guards this).
- [ ] `analysis/out/builds-level20.md` top builds change only if the allowance binds,
      and the digest says whether it bound.
- [ ] GAP-004 flips to `resolved`.

## Files likely to change

`config/analysis.yaml`, `swse/enumerate.py`, `swse/evaluate.py`,
`tests/test_enumerate_evaluate.py`.
