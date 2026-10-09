# TASK-016 - Give the homebrew classes a progression

**Status:** open | **Priority:** low | **Gap:** GAP-013

## Problem

Two records in the corpus are `canon: homebrew`: the **Technician** and **Force
Prodigy** classes, contributed by the Master Reference's own homebrew section. They
exist as prose only - no hit die, no BAB rate, no defence numbers, no per-level
progression.

Consequence: builds using them score 0 for BAB, defence and durability contributions,
and the evaluator warns when a class has no hit die. Force Prodigy appears in the
top-ranked level-10 build (Gen'Dai, Soldier/Force Prodigy/Jedi/...), so this is not a
corner case - the ranking is partly an artefact of a class whose numbers do not exist.

`--no-homebrew` excludes them, and `tests/test_canonical_data.py` skips classes with
no numeric `*_progression` in its defence cross-check for exactly this reason.

## Evidence

```bash
python -c "
from swse.store import Dataset; db=Dataset.load()
for c in db.all('class'):
    if c['canon']=='homebrew':
        print(c['id'], '|', c['name'], '| hit_die:', c['attrs'].get('hit_die'),
              '| bab:', c['attrs'].get('bab_progression'), '| flags:', c['flags'])"
python -m swse.cli space --level 10 --no-homebrew --json | jq '.total_space'
python -m swse.cli space --level 10 --json | jq '.total_space'
```

## Approach

Homebrew content has no printed authority, so there are three honest options. Pick one
and record the decision in the task file:

1. **Exclude by default.** Keep them in the dataset (they are real content someone
   wrote) but make `--no-homebrew` the default for evaluation, and publish homebrew
   rankings separately. Cheapest, and the most defensible: an unnumbered class cannot
   be ranked against numbered ones.
2. **Model by analogy.** Assign the Technician the Soldier/Scout progression and Force
   Prodigy the Jedi progression, stored in `data/curation/overrides.yaml` with
   `attrs.progression_basis: analogy_to:<class>` and a flag. Usable for analysis, but
   the numbers are invented and must never be presented as sourced.
3. **Source the author's intent.** If the homebrew section names an author or a thread,
   the progression may exist there. This is a research task, not a modelling one, and
   it would make the records `third_party` rather than `homebrew`.

## Acceptance criteria

- [ ] A decision is recorded here, with the reasoning.
- [ ] Either the classes are excluded from evaluation by default and the reports say so,
      or every derived number carries `progression_basis` and a flag naming it as
      invented.
- [ ] `evaluate` stops warning about a missing hit die, or the warning text explains
      the decision.
- [ ] `analysis/out/builds-level10.md` and `builds-level20.md` are regenerated, and if
      the top build changes, the digest says why.
- [ ] A test asserts that a homebrew class is either excluded or flagged - never
      silently scored as if it had numbers.
- [ ] GAP-013 flips to `resolved`.

## Files likely to change

`config/analysis.yaml`, `data/curation/overrides.yaml`, `swse/evaluate.py`,
`swse/space.py`, `tests/test_enumerate_evaluate.py`.
