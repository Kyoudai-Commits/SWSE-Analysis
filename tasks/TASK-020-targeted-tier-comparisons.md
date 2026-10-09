# TASK-020 - Targeted tier comparisons with real statistical power

**Status:** open | **Priority:** medium | **Follow-up from:** TASK-018

## Problem

The canon-balance audit answers "does third-party content inflate build rankings?"
with a build-level comparison, and the answer is *no evidence that it does*
(level 1: medians 45.2 official vs 46.0 third-party, p=0.50; level 10: 112.35 vs
112.95, p=0.56). But the comparison is weak by construction: random builds rarely
pick third-party options, so the third-party group is only 22-24 builds per level.

Record-level comparison is worse - canon tier and entity type nearly coincide, so
18 of 20 power proxies could not be compared at all (one tier had fewer than 8
records).

The comparisons that *would* have power are the ones nobody has run: within a single
decision slot, compare the tiers directly.

## Where the power is

| comparison | official n | third-party n | why it matters |
|---|---:|---:|---|
| talent trees (grants per tree) | 167 | 25 | the 25 SagaForge-only trees are the largest block of builder-only *character* content |
| talents inside those trees | 1,307 | 4 | lopsided - but the trees themselves can be compared by size and by bonus density |
| species | 121 | 9 | species is a level-1 decision every build makes |
| equipment | 184 | 42 | the only entity with real overlap in both tiers |
| weapons | 239 | 7 | small overlap, but damage is exactly comparable |
| armour | 88 | 4 | too small; report, do not test |

## Evidence

```bash
python -m swse.cli audit --top 4 --json          # the current audit and its sample sizes
sed -n '/## Composition/,/## Power proxies/p' analysis/out/canon-balance.md
```

## Approach

1. **Compare like with like inside a decision slot.** For talent trees: options granted
   per tree, talents per tree, and mean bonus density per talent. For species: total
   positive ability modifiers, penalties, and racial ability counts. For equipment and
   weapons: price against the numeric effect, since price is the game's own balance
   signal.
2. **Control for the confounder.** Third-party content is concentrated in specific
   supplements; if all 25 builder-only trees come from one book, the comparison is
   really "that book versus everything else". Report the sourcebook breakdown
   alongside the tier breakdown.
3. **Keep the rank-sum, name its limits.** `swse/audit.py:mann_whitney_u` already does
   tie- and continuity-corrected normal approximation; reuse it, and keep the
   `MIN_COMPARABLE_N` guard so a p-value is never quoted from a handful of records.
4. **Publish as an extension of the existing report**, not a new one - the audit's
   value is that record-level and build-level evidence sit next to each other.

## Acceptance criteria

- [ ] The audit gains a per-slot comparison for talent trees, species, equipment and
      weapons, each with n per tier, medians, IQR and a p-value only where
      `MIN_COMPARABLE_N` is met.
- [ ] Sourcebook breakdown is reported next to the tier breakdown for any comparison
      that differs.
- [ ] Every outlier in a differing comparison gets a verdict in
      `data/curation/audit-verdicts.yaml`, or is filed as a gap.
- [ ] The conclusion states plainly whether mixed-canon rankings are safe to quote, and
      the statement is supported by a comparison with at least 8 records per tier.
- [ ] A test asserts the new comparisons run on the real corpus and that no p-value is
      reported below `MIN_COMPARABLE_N`.

## Files likely to change

`swse/audit.py`, `tests/test_audit.py`, `analysis/out/canon-balance.md` (regenerated).
