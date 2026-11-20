# Beginners in the Herd: instructions for Claude Code sessions

This repo is a STEM fair research project (Guru Balaji & Yuvraj Sharma). It
is also a shared Obsidian vault synced through GitHub. Two people work on it,
each in their own Claude Code sessions.

## Start of every session
1. Run `git pull` (the other person may have pushed).
2. Read `notes/Handoff.md`, then the top few entries of `notes/UPDATE log.md`.
3. For background on any step, read `PROJECT_CONTEXT.md` and `docs/`.

## End of every session
1. Write an UPDATE in the format below and add it to the **top** of
   `notes/UPDATE log.md` (newest first), with the date and who you worked
   with:
   ```
   ## YYYY-MM-DD — <name> (with Claude Code)
   UPDATE: [one-line title]
   - What I did
   - What the result was (with the numbers)
   - Any decision made or problem hit
   - What's next
   ```
2. If the status changed, update `notes/Handoff.md` §3–4 and tick
   `notes/To-dos.md`.
3. Commit and push only when the user asks.

## Research rules (do not break)
- **Pre-register first.** Any new analysis or change from the plan gets
  an entry in `docs/deviations_log.md` (and an addendum if it's large).
  Commit that entry **alone**, before writing the code. Then commit the
  code, then the results, each in its own commit.
- Never edit an existing pre-registration or addendum. Add a dated note
  instead.
- **Validation-first:** each analysis has a `test_*.py` that recovers
  known synthetic values. Make it pass before running on real data.
- Report results honestly, including unfavorable ones. Every result must
  be explainable to a fair judge in plain English.
- `data/` is gitignored (759 MB) and is never committed. Don't commit
  while a simulation is still writing to `results/`.

## Technical notes
- Windows Application Control blocks `statsmodels.api`. Import from
  submodules instead, e.g.
  `from statsmodels.regression.linear_model import OLS` or
  `from statsmodels.robust.robust_linear_model import RLM`.
- Multiprocessing simulations are resumable: they append each finished
  market to `results/*_raw.csv`. 12 workers can run out of memory; use 6.
- Commit hashes changed on 2026-11-19 (history rewrite before the first
  push). Older UPDATE summaries cite old hashes; translate them with
  `notes/Commit hash map.md`.

## Git
- Each person commits under their own GitHub identity (the global git
  config).
- No AI co-author or "Generated with" lines in commit messages.
- Notes link with Obsidian wikilinks (`[[Note title]]`). Don't move or
  rename notes from the shell, because that breaks links; ask the user to
  rename them inside Obsidian.
