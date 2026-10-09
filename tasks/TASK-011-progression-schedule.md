# TASK-011 - Source the per-level feat/talent schedule

**Status:** open | **Priority:** high | **Gap:** GAP-002

## Problem

Neither workbook says what a character gains at each level. SagaForge's `Class` sheet
is a blank character-sheet UI grid (`Class!A6:V25` is entirely empty) and `Data!CT:CY`
- the per-level progression columns - are all zeros. The schedule currently in force
(feat at 1st level and every odd level thereafter, talent at every even level,
ability increase every 4th) is declared in `config/analysis.yaml` with
`verified: false`.

Every number above level 1 rests on it: the level-20 total space (10^164.95), the
class-path count (2.53e27), and the level-10/20 sampled builds. That is why those
figures are reported as orders of magnitude rather than exact counts.

## Evidence

```bash
grep -n -B 3 -A 14 "^progression:" config/analysis.yaml
python -c "
from swse.sources import load_registry, workbook
wb=workbook(load_registry()['sagaforge-1.53'])
rows=list(wb['Class'].iter_rows(min_row=6,max_row=25,values_only=True))
print('non-empty cells in Class!A6:V25:', sum(1 for r in rows for c in r if c is not None))"
```

## Approach

This is a source-acquisition task, not a modelling one - see TASK-002 for the general
route. Concretely:

1. Transcribe the heroic class progression table (SECR p.~62 ff.) as a registered
   source: level -> feats, talents, ability increases, defence bonuses, BAB, hit die.
2. Encode it in `config/analysis.yaml:progression.heroic` as data with `verified: true`
   and an `evidence:` line, and have `swse.space` read the schedule from config rather
   than from a constant.
3. Keep the analytic level-2-20 counter, but drive it from the table so a per-class
   difference (Noble gets a talent tree choice, Jedi get Force training) is represented
   instead of averaged away.
4. Re-check the level-1 exactness assertion: at level 1 the analytic model must still
   equal `iter_level1_builds`.

## Acceptance criteria

- [ ] `progression.heroic.verified` is `true` with evidence naming source, sheet/range
      or book/page.
- [ ] `data/reports/decision-space.md` prints the schedule it used, per class, and the
      level-20 figures change accordingly.
- [ ] `tests/test_space.py` asserts the analytic level-2 count equals a hand-computed
      count from the sourced table for at least one class.
- [ ] Level-1 exactness still holds (analytic == enumerated).
- [ ] `enumerate --level 10 --sample 300 --check` still reports 0 violations under the
      sourced schedule.
- [ ] GAP-002 flips to `resolved`; README's level-20 figures are regenerated.

## Files likely to change

`config/analysis.yaml`, `swse/space.py`, `swse/enumerate.py`, `tests/test_space.py`,
`README.md` (regenerated numbers only).
