---
title: UPDATE log
aliases: [updates, update log]
type: log
tags: [log, status]
created: 2026-11-19
updated: 2026-11-19
summary: Session-by-session UPDATE summaries, newest first. Every session (Guru, Yuvraj or Claude Code) adds one at the top.
---
# UPDATE log

Newest first. Add your UPDATE **at the top**, under this line, then
commit and sync ([[How to sync]]). Start each entry with the date and
who wrote it. Back to [[Home]] · read-first: [[Handoff]].

Format:
```
## YYYY-MM-DD — who
UPDATE: [one-line title]
- What I did
- What the result was (with the numbers)
- Any decision made or problem hit
- What's next
```

---

## 2026-11-20 — Guru (with Claude Code)
UPDATE: Research plan reformatted in the official 2026-27 format, board figures pushed, abstract drafted
- **What I did:**
  - Researched the ISEF, SSEF and Hillsborough plan rules, judging criteria and winning examples (`reports/ISEF research plan format.md`).
  - Rebuilt the plan as `Research_Plan_and_Addendum_Balaji_Sharma.docx` / `.pdf`:
    - Part 1: the original 08/31/26 plan in Form 1A order (A to E);
    - Part 2: a dated addendum with 17 changes and their reasons, methods only;
    - Section D: an AI disclosure.
  - Deleted the old results-containing plan draft and its PDF.
  - Pushed the board figures and drafted the abstract (249 words).
- **What the result was:**
  - SSEF does not allow data or conclusions in the plan, and changes go in an addendum.
  - The 2026-27 ISEF rules also restrict generative AI from writing the plan, abstract or poster. Our research teacher told us to use AI, so keep that guidance in writing and disclose AI use on Form 2A and in Section D.
- **What's next:** edit the plan and addendum; upload the plan, forms and abstract to Hillsborough by Jan 11, 2027.

## 2026-11-19 — Guru (with Claude Code)
UPDATE: Step 8 analyses run (D8); research plan finalized except one question
- **What I did:**
  - Pre-registered D8 and pushed it before any code (`0b7cd6b`).
  - Wrote `step8_analyses.py` with 15/15 validation checks, then pushed the code before running it (`71c3f35`).
  - Ran the four analyses (`39f805d`).
  - Research plan: appendix deleted, research teacher set to Mrs. Kulkarni. CSSD, pairwise correlation, per-stock Google Trends, sup-Wald, international and GARCH are dropped, with reasons.
- **What the result was:**
  - Nothing changes the answer. The GPT-4 date, leaving out the 7 largest tech companies and a liquidity-weighted market give CCK bootstrap one-sided p = 0.21 / 0.21 / 0.33.
  - g5 ≈ −25 bp of dispersion on a 2-SD (2.5%) market day, about 11% of normal, with a 95% interval from −55 to +60 bp.
- **Any decision made or problem hit:** I chose to drop CSSD and pairwise correlation; Question 2 already compares two tests.
- **What's next:** ask Mrs. Kulkarni whether to submit a revised plan or an addendum; then the board visuals.

## 2026-11-19 — Guru (with Claude Code)
UPDATE: Research plan drafted
- **What I did:** drafted the combined research plan (since replaced by `Research_Plan_and_Addendum_Balaji_Sharma.docx`), following the original plan's section order.
  - It keeps the original question, rationale and H1–H3 word for word.
  - It adds a background section: the original plan, what happened, why it was revised, and the new goal and hypothesis.
  - It adds Question 2 and H4 (can the herding tests be trusted), plus the procedures as actually carried out, the remaining analyses, a who-did-the-work disclosure (we did the research; Claude Code completed it under our direction) and a progress appendix.
- **What the result was:** every number in the draft was checked against `results/` and `data/`. I also corrected the stale sample sizes in [[Handoff]]: 2,260,838 stock-days, 1,280 stocks, 2,019 members.
- **Any decision made or problem hit:** the draft is long (about 5,700 words). The appendix is the easiest cut if the fair limits length.
- **What's next:** resolve the ⚠ items in the draft (revised plan or addendum, teacher name, CSSD, Google Trends, which Step 8 analyses, appendix).

## 2026-11-19 — Guru (with Claude Code)
UPDATE: Repo on GitHub + shared Obsidian vault set up
- **What I did:**
  - Rewrote the git history before the first push: all 24 commits are re-authored as Guru-Balaji18, AI co-author trailers are removed, and dates are unchanged. A byte-for-byte check found no content changes except the cited hashes. See [[Commit hash map]].
  - Moved the working copy to `Desktop\Stem Fair`. The OneDrive copy stays as a backup.
  - Pushed to a public GitHub repo.
  - Made the repo an Obsidian vault with these notes, Obsidian Git settings, a `CLAUDE.md` for Claude Code sessions, and a README.
- **What the result was:** both of us can now pull, edit notes and code, and push. Claude Code sessions read [[Handoff]] first and add their UPDATE here.
- **Any decision made or problem hit:**
  - The repo is public, by choice. It includes Guru's SEC contact email in two scripts.
  - Obsidian Git auto-**pulls** (at startup and every 10 min), but commit-and-sync is **manual**, so half-finished code or simulation output never gets committed by accident.
  - `data/` (759 MB) is not in git.
- **Problem hit and fixed:** numpy stopped importing ("An Application Control policy has blocked this file").
  - **Cause:** Windows 11 **Smart App Control**, a consumer feature (this is not a school laptop). numpy 2.2.6 never had an official Python 3.14 wheel, so in August pip *compiled it locally*. That file is unsigned and has no reputation, so Smart App Control started blocking it.
  - **Fix:** installed the official wheel, numpy **2.3.5** (`pip install --only-binary=:all: "numpy>=2.3,<2.4"`). Smart App Control was left on.
  - **Check:** all reproduction tests pass with identical numbers, and Windows logged no blocks after the install.
  - **Side note:** opencv-python 4.12 says it wants numpy < 2.3. This project doesn't use OpenCV.
- **What's next:** Yuvraj accepts the invite and sets up; then work through [[To-dos]].

## 2026-10-21 — Guru (with Claude Code)
UPDATE: D7 – the robust-regression reading of Wang-Hudson also fails
- **What the result was:** the RLM (Huber) fit of Solution 2 false-alarms in 100% of no-herding markets (Wilson CI 99.6–100) in S1/S5, winsorized and not, under both the one-sided and two-sided rules. The pre-registered rule says "loophole closed". The median t is more extreme than with OLS (−29 to −32 vs −7 to −13).
- **Commits:** `f15b546` (pre-registration), `d447f34` (code + results), `305c363` (docs).

## 2026-09-29 — Guru (with Claude Code)
UPDATE: Part E complete – verdict (b), the published Wang-Hudson method over-rejects
- **What the result was:**
  - Our regression is the paper's Equation 3. The paper never addresses the jump at R_m = 0.
  - The paper-exact Solutions 1 and 2 give 100% false alarms everywhere.
  - Rerunning the paper's own simulation with its stated errors also gives 100%. Its reported 14.4% needs an error SD of 0.01.
  - Solution 3 is well-sized only without pooled winsorization; on per-day-winsorized real data it finds no herding.
- **Details:** `docs/wang_hudson_spec.md`.

## 2026-09-28/29 — Guru (with Claude Code)
UPDATE: Parts B–D and F–H done
- **B:** WH (ours) false-alarms 100%. CCK is conservative and has non-monotonic power. Pooled winsorization creates false CCK herding.
- **C/D:** placebo empirical p = .43 (CCK) / .70 (WH), so the effect is not ChatGPT-specific. Year slopes remove g5. The plan-literal g5 is positive.
- **F:** calibrated p for g5 = .12 (CCK) / .39 (WH), not significant.
- **G:** mechanisms explained in `docs/mechanisms.md`.
- **H:** longer Newey-West lags are worse. The bootstrap fixes CCK (g5 p = .20) but not WH.
