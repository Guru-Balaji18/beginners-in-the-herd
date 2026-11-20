---
title: Commit hash map
type: reference
tags: [reference, git]
created: 2026-11-19
updated: 2026-11-19
summary: Old → new commit hashes after the 2026-11-19 history rewrite (author fixed, Claude trailers removed).
---
# Commit hash map

On 2026-11-19, before the first push to GitHub, the history was rewritten:
- every commit was re-authored as Guru-Balaji18 instead of the old local identity;
- the `Co-Authored-By: Claude` trailers were removed;
- the original author and commit dates were kept to the second.

Each file in each commit was verified byte-identical to the original
apart from the commit hashes it cites, which were updated to the new
ones.

UPDATE summaries written **before** 2026-11-19, and the copy of the repo
in OneDrive, use the **old** hashes. Use this table to translate.

Back to [[Home]].

| Date | Old | New | Commit |
|---|---|---|---|
| 2026-10-21 | `1e4c78a` | `305c363` | Docs: record D7 outcome, run notes, and post-hoc observation |
| 2026-10-21 | `3d89421` | `d447f34` | D7 results: RLM (HuberT) Solution 2 also false-alarms 100% -- loophole closed |
| 2026-10-21 | `c75318c` | `f15b546` | Pre-register D7: robust-regression (RLM) check of WH Solution 2 |
| 2026-09-29 | `e18996f` | `c20989a` | Part E complete: paper-exact E5/E6 verdict (b), paper-simulation replication, F/H additions, docs |
| 2026-09-29 | `bd0a8bb` | `51adf33` | Part E: add Wang & Hudson paper (CC-BY manuscript) and paper-exact variant code (not yet run) |
| 2026-09-29 | `4927497` | `319731c` | Part E: E1 quotes + E2 line-by-line comparison from the paper; log D6 (paper-exact choices) before any code |
| 2026-09-29 | `42a3eb7` | `89a8cc7` | Part E (paper-independent) and Part G complete: E5 variant size/power, per-day SE test, docs |
| 2026-09-29 | `2dfc076` | `e8fe188` | Part E4 diagnosis results; Part G gap fixes (one-paragraph mechanisms.md, per-day SE test code) |
| 2026-09-29 | `704c455` | `edaa4ba` | Part E (paper-independent): E4 diagnosis + unverified/diagnostic variants; checks 8/8 pass; not yet run |
| 2026-09-29 | `315b623` | `6ab225c` | Log D5 before running: paper-independent Part E steps (E4 diagnosis, unverified variants) and Part G gap fixes |
| 2026-09-28 | `87c1e67` | `69d602a` | Part H results: SE validation (bootstrap best, none fully calibrated), real-data SEs, per-day winsorized Step 5, placebo rerun; context update |
| 2026-09-28 | `f025ce2` | `4b66c51` | mechanisms.md: mark the leftover 8.6% CCK over-rejection cause as untested |
| 2026-09-28 | `d7e2d9e` | `3ec6436` | Part G results: winsorization and CCK non-monotonic power mechanisms, per-day winsorization size, docs/mechanisms.md |
| 2026-09-28 | `fe5f30f` | `017be41` | Part F results: calibrated test (2,000-market S5 null, 12,000 markets total) |
| 2026-09-28 | `7cf5f89` | `b4ce21a` | Parts G/H code: mechanism diagnostics, robust SEs (NW long lags, 21-day block bootstrap), SE validation; checks 8/8 pass; not yet run |
| 2026-09-28 | `a344fb8` | `97c4ed0` | Part F: calibrated herding test code + machinery checks (11/11 pass), before running |
| 2026-09-28 | `723f218` | `6e4324d` | Part E: paper not available -- record what cannot be verified, stop as pre-registered |
| 2026-09-28 | `8065416` | `6bd1a17` | Pre-register addendum 2: Parts E-H (WH verification, calibrated test, mechanisms, SE fix) |
| 2026-09-28 | `3d5ebe1` | `4886af8` | Part C/D results: placebo break dates, year FE, plan-literal check; log D4 |
| 2026-09-28 | `36ad44f` | `88465b7` | Part B results: log D3 (Post-term size, post-hoc), add postsize command, fix size-table legend |
| 2026-09-28 | `5fcb639` | `581ec17` | Add Part C/D placebo break-date code (written, not yet run) |
| 2026-09-28 | `181fe39` | `84557b7` | Log deviations D1-D2 and add Part B simulation code before the full run |
| 2026-09-28 | `0b8b2ce` | `ed63759` | Add pre-registration addendum for Monte Carlo and placebo analyses |
| 2026-09-28 | `29306da` | `379efb2` | Baseline: analysis code, research plan, and project notes as of 2026-09-28 |
