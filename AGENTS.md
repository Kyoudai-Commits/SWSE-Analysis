# Playbook for agents working on this corpus

This repo is a Star Wars Saga Edition rules corpus with three raw sources and one derived,
agent-ready layer. Answer rules questions from the derived layers only.

## 0. Orient in one read

`index/INDEX.md` — corpus totals, coverage warnings, where to look per question type.
It is generated; it is never stale.

## 1. Lookup ladder (stop at the first hit)

1. **Exact name or phrasing** → `python3 build/query.py lookup "<name>" [--type feat]`
   Returns the merged record: typed fields, per-field source, `file:line`, flags.
2. **Words from a rule** → `search "<query>"` (BM25 over 2,472 chunks; `esearch` for SQLite FTS5
   syntax: `NEAR("flat footed" combatant 5)`, `"Skill Focus" Survival`).
3. **Class / book / entity-type questions** → read `index/by-class/<class>.md`,
   `index/by-book/<Abbr>.md`, `index/by-type/<type>.md` — pre-joined, one read, table of records.
4. **Set algebra** (prerequisites, tags, multi-condition lists) →
   `python3 build/query.py sql "SELECT name, prerequisites FROM entity WHERE type='feat' …"`
   Schema: `python3 build/query.py sql "SELECT name, sql FROM sqlite_master WHERE type='table'"`.
5. **Only then** open `normalized/wiki/...` — the cited `file:line`, or the whole page if it is small.

`gap <term>` answers the question "is this missing from the crawl, or missing from the game?" —
use it before ever writing "the rules don't cover that".

## 2. Answer rules

* **Quote or paraphrase the line you opened.** Never answer from a search snippet alone; snippets
  truncate table rows (`|` is escaped in wiki tables on purpose).
* **Cite the normalized path + line span**: `` `normalized/wiki/by-title/Toughness.md:9-9` ``.
  Add the wiki URL if the user wants the human-visible source.
* **Prefer typed fields over prose**: `feat.benefit`, `talent.benefit`, `force-power.action`,
  `heroic-class.hit_points`. If a field is flagged `disputed`, report both values and their sources.
* **Numbers matter.** If a value came from `sagaforge`, say so — it is the only source with page
  numbers: report `books` + `pages: p.<n>` (lookup prints them) when present.
* **State the ceiling.** If the entity has flag `no-wiki-page`, or `gap` says the page was never
  crawled, say *"the crawl didn't include X; here is what the reference tables say"* — do not fill
  the hole from general Star Wars knowledge.

## 3. Things that will bite you

* `Weapon Focus (Lightsabers)`, `Dexterity 13`, `Crew Use (Pilot)` in prerequisite text are
  *patterns*, not links — `lookup` splits them into `type/name/qualifier/minimum`. `chain` walks
  prerequisite graphs but hits `…` where a prerequisite is unparsed prose.
* A resolution with `resolved-by:variant-name` is an **approximation**: e.g. `Force_Sensitivity`
  resolves to the *page* `Force_Sensitive_Baseline`, which is a different rules term. Say so, or
  treat it as a gap.
* `[[Wiki_Slug]]` in normalized text is a link *marker*, not the word a book would print. Prose
  search still finds human names (the index carries an `aux` column with link titles and anchor text),
  but plain `grep` for "Skill Focus (Survival)" in `normalized/` needs `grep -r Skill_Focus`.
* `Category:*` content was split; `wiki:Category:Web_Enhancements#000`-style ids are sections, with
  `parent` set. Reading the parent gives you the section index, not the text.
* Never edit `swse-miraheze-org/`, the spreadsheets, `normalized/`, `data/`, or `index/` — the last
  three are overwritten by the build. Fix `build/` and re-run.

## 4. Rebuild & verify

```bash
python3 build/build.py                    # full build + verification (all stages must print ok)
python3 build/build.py --stage registry,index,render,verify   # iterate on the index/projection layer
python3 build/build.py --report           # stats JSON only
```

Verification failures exit non-zero with `FAIL <check>`. If you change extraction rules, update the
golden tables in `build/swsebuild/verify.py` **and** `docs/MAPPING.md`, and keep
`index/INDEX.md`'s "read this first" list honest. See `docs/RETRIEVAL.md` for the evaluation harness
(`verify.run` doubles as the recall/precision test).
