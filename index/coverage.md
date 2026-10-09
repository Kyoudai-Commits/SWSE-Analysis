# Coverage & reconciliation

How complete this knowledge base is, per entity family and per source, and what the
three inputs disagree about. **Read this before trusting a negative answer.**

## By entity family

| family | entities | with wiki page | spreadsheet-only | pages | chars |
| --- | --- | --- | --- | --- | --- |
| `talent` | 1,213 | 1,105 | 108 | 0 | 0 |
| `feat` | 395 | 319 | 76 | 318 | 266,545 |
| `talent-tree` | 177 | 164 | 13 | 164 | 485,229 |
| `species` | 125 | 125 | 0 | 124 | 550,124 |
| `force-power` | 91 | 78 | 13 | 77 | 127,349 |
| `class-ability` | 80 | 0 | 80 | 0 | 0 |
| `rule` | 40 | 40 | 0 | 40 | 723,812 |
| `affiliation` | 33 | 33 | 0 | 33 | 328,608 |
| `prestige-class` | 32 | 28 | 4 | 28 | 119,074 |
| `index` | 32 | 32 | 0 | 32 | 98,290 |
| `skill` | 18 | 18 | 0 | 18 | 128,451 |
| `compilation` | 16 | 16 | 0 | 16 | 1,770,431 |
| `action` | 15 | 15 | 0 | 15 | 28,391 |
| `weapon` | 9 | 9 | 0 | 9 | 9,263 |
| `droid-system` | 8 | 8 | 0 | 8 | 6,764 |
| `heroic-class` | 8 | 5 | 3 | 5 | 32,136 |
| `other` | 7 | 7 | 0 | 7 | 191,018 |
| `equipment` | 6 | 6 | 0 | 6 | 6,807 |
| `weapon-group` | 6 | 6 | 0 | 6 | 26,866 |
| `droid` | 5 | 5 | 0 | 5 | 21,104 |
| `creature` | 3 | 3 | 0 | 3 | 40,624 |
| `challenge` | 2 | 2 | 0 | 2 | 1,812 |
| `crew-position` | 2 | 2 | 0 | 2 | 21,392 |
| `planet` | 2 | 2 | 0 | 2 | 3,200 |
| `npc` | 1 | 1 | 0 | 1 | 17,277 |
| `organization` | 1 | 1 | 0 | 1 | 103,861 |
| `armor` | 1 | 1 | 0 | 1 | 1,179 |

## By source book

| book | pages | feats | talents | force powers |
| --- | --- | --- | --- | --- |
| Core Rulebook | 254 | 57 | 418 | 16 |
| Knights of the Old Republic Campaign Guide | 129 | 35 | 292 | 11 |
| Rebellion Era Campaign Guide | 116 | 62 | 133 | 0 |
| Force Unleashed Campaign Guide | 112 | 27 | 300 | 4 |
| Clone Wars Campaign Guide | 109 | 20 | 285 | 8 |
| Legacy Era Campaign Guide | 103 | 22 | 229 | 12 |
| Galaxy at War | 100 | 74 | 172 | 0 |
| Jedi Academy Training Manual | 100 | 5 | 228 | 43 |
| Scum and Villainy | 92 | 36 | 237 | 0 |
| Unknown Regions Campaign Guide | 78 | 26 | 183 | 0 |
| Galaxy of Intrigue | 62 | 31 | 109 | 0 |
| Web Enhancements | 62 | 10 | 44 | 4 |
| Threats of the Galaxy | 31 | 4 | 56 | 0 |
| Starships of the Galaxy | 29 | 12 | 48 | 1 |
| Scavenger's Guide to Droids | 28 | 17 | 58 | 0 |

## Source cross-check

| check | count | meaning |
| --- | --- | --- |
| master_reference feats | 353 | rows in the curated workbook |
| … master_reference feats with no wiki page | 39 | needs a crawl or is spreadsheet-only |
| sagaforge feats | 425 | 3rd-party list; superset of the workbook |
| … sagaforge feats with no wiki page | 89 | mostly non-Core books |
| wiki feat pages | 318 | crawled feat articles |
| … absent from the workbook | 5 | workbook is incomplete, not the wiki |
| Links manifest rows | 818 | URLs the crawl was meant to fetch |
| … never crawled | 88 | intended but missing → backlog |
| force powers (workbook) | 90 | cites swse.fandom.com, not miraheze |
| force powers (sagaforge cards) | 90 | has DC/action/target columns |
| talent rows (sagaforge) | 1,092 | individual talents inside trees |

## Known limits

- **Equipment stats are thin.** The crawl captured rulebook *chapter intros* (`Category:Weapons`,
  `Category:Armor`) and only a handful of item pages; full weapon/armor/starship/vehicle stat
  blocks live on uncrawled pages (see `crawl-backlog.md`) or in `3rd_Party_Builder/` only.
- **No page numbers from the wiki.** Only SagaForge carries book+page citations (its `Page` column),
  so book-level citation for wiki-only records stops at the source book, not the page.
- **Droids / starships / vehicles / planets are index-shaped**, not stat-shaped: the pages exist as
  lists that point at uncrawled targets.
- **Raw spreadsheets are form UIs**, so `3rd_Party_Builder/` coverage is limited to the four
  rectangular sheets this build parses (`Feats`, `Talents`, `ForcePowerCards`, `NewStatBlockRef`) plus
  the `Data` sheet's book-abbreviation legend. The other 26 sheets are character-calculation forms.
