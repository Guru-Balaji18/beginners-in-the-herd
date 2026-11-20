---
title: Handoff
aliases: [handoff, project handoff]
type: reference
tags: [reference, status]
created: 2026-11-19
updated: 2026-11-19
summary: Read-first project handoff for every new session (human or Claude Code). Status is current to 2026-11-19.
---
# Handoff: "Beginners in the Herd" (STEM Fair)

Read this first in any new session. Then read the latest entries in
[[UPDATE log]]. Navigation: [[Home]].

> **Out of date, don't use:** the August 2026 docs "Everything" and
> "Sources" describe an LSV herding measure and a Nasdaq RTAT data plan
> that were dropped. Do not recommend an RTAT subscription. The current
> method is CSAD-based (see below). The papers listed in "Sources" are
> still valid background reading.

> **Commit hashes changed on 2026-11-19.** The history was rewritten
> before the first push to GitHub. UPDATE summaries from before that
> date cite old hashes; translate them with [[Commit hash map]].

---

## 1. The project
- **Title:** Beginners in the Herd
- **Team:** Guru Balaji and Yuvraj Sharma, Middleton High School, Tampa FL. Adult sponsor: Mrs. Kulkarni.
- **Category:** Mathematics (Probability & Statistics)
- **Key dates:** Hillsborough Regional STEM Fair Feb 17, 2027 → SSEF Florida Mar 30–Apr 1, 2027 → ISEF May 8–14, 2027
- **Research question:** Did ChatGPT's release on Nov 30, 2022 increase stock-market herding during periods of heavy new or inexperienced investor entry, even though Even-Tov et al. (2025) found that the average retail investor became *less* herd-prone?
- **Study window:** 2016–2026

## 2. Methodology
- **Main regression:** CSAD_t on |R_m,t| and (R_m,t)², with interactions on Post_t (after ChatGPT), High_t and Low_t (entry terciles). Controls are VIX, a top-decile volatility day dummy, month fixed effects, a time trend and FOMC/CPI day dummies. Code: `main_regression.py`.
- **Key coefficient:** g5 = (R_m,t)² × Post_t × High_t. H1 predicts it is significantly negative (one-sided test). g7 = Post × Low.
- **Estimation:** OLS with Newey-West HAC standard errors (5 lags). Part H showed these are too small for the Post terms; see §4.
- **Two herding tests run side by side:** the standard CCK test (Chang/Cheng/Khorana 2000) and the Wang & Hudson (2022/2024) SCSAD test, which is their "Solution 2".
- **Literature:** CCK 2000, Wang & Hudson 2022 (the CC-BY manuscript is in the repo as `wang_hudson_2022.pdf`), Even-Tov et al. 2025, Reyes 2018

## 3. Pipeline status
| Step | File(s) | Status |
|---|---|---|
| Membership | `build_membership.py` → `data/membership.csv` | Done. Russell 1000 from iShares IWB holdings (current BlackRock endpoint). 2,048 tickers, reliable from 2013-01. Known gap: Jan–Jul 2017 is missing from BlackRock's archive. |
| 1. Return panel | `build_panel.py`, `test_panel.py` | Done: 2,216,818 rows, 1,279 tickers, 664–1,011 active per day. 36 renames fixed (FB→META etc.). |
| 2. CSAD | `build_csad.py`, `robustness_wang_hudson.py` | Done. CCK and Wang-Hudson disagree on base herding; Parts B and E explain why. |
| 3. Entry index | `investor_index.py` | Done (29 checks). |
| 4. Retail attention | `retail_attention.py` | Done for FINRA and inverse 13F. Per-stock Google Trends is incomplete (23/184 batches). |
| 5. Main regression | `main_regression.py` | Done. Results mostly do not support H1–H3. |
| Part A | `docs/addendum_2026-09-28.md` | Pre-registration addendum, done |
| Part B | `simulate_herding_tests.py` | Monte Carlo of size and power, done |
| Parts C/D | `placebo_break_dates.py` | Placebo break dates, year FE, plan-literal High vs Low, done |
| Parts E–H | `docs/addendum2_2026-09-28.md`; `wang_hudson_variants.py`, `wang_hudson_paper.py`, `calibrated_test.py`, `mechanisms_diagnostics.py`, `robust_se.py`, `se_validation.py` | Done |
| D7 | `docs/addendum3_2026-10-21_rlm.md`, `test_rlm.py` | Robust-regression (RLM) check of Wang-Hudson, done |

`data/` is not in git (759 MB). It has to be rebuilt with the scripts or copied from Guru's machine.

## 4. Results (current)
- **Step 5:**
  - g5 = −3.99 standard (one-sided p = .053) and −430.5 Wang-Hudson (p = .003).
  - H2 is contradicted: Post×Low is negative too.
  - H3 goes the wrong way: the effect is larger in low-attention stocks.
  - 10 of 25 variant regressions are significant (6 negative, 4 positive).
- **Part B (Monte Carlo):**
  - Our Wang-Hudson test says "herding" in **100%** of no-herding markets.
  - CCK is conservative and low-powered, and its power is non-monotonic.
  - Pooled winsorization manufactures false CCK herding.
- **Parts C/D:**
  - **Placebo test:** the real g5 is ordinary among 84 fake break dates (empirical p = .43 CCK, .70 WH). The effect is **not specific to ChatGPT's release**.
  - **Year-specific slopes:** they remove g5 (calendar confound).
  - **The plan's own High-vs-Low test:** g5 comes out positive (+2.43 / +268), the opposite of H1.
- **Part E (Wang & Hudson checked against the paper), verdict (b):** the published method itself over-rejects.
  - Our regression *is* the paper's Equation 3.
  - The paper never addresses the jump the sign flip creates at R_m = 0.
  - The paper-exact version also flags herding in 100% of no-herding markets.
  - The paper's own simulation only looked fine because its market moves spanned ±50%.
- **D7:** reading "robust regression" as a Huber M-estimator doesn't help either. False alarms are 100% in all runs, so that loophole is closed.
- **Part F (calibrated test):** the real data are judged against simulated no-herding markets. Nothing is significant: g5 calibrated p = .12 CCK, .39 WH.
- **Part G:** plain-English mechanisms are in `docs/mechanisms.md`. Per-day winsorization fixes the cleaning artifact.
- **Part H:** longer Newey-West lags make things worse. The 21-day block bootstrap fixes CCK but not WH. With the bootstrap, g5 has one-sided p = .20 (CCK).
- **Takeaway:** every route to H1 now points the same way. The lead contribution is the **CCK vs Wang-Hudson** story: why a published herding test gives false alarms, shown by simulation, mechanism and replication of the paper.

## 5. Plan (decided 2026-09-28): honest reframing
- H1–H3 stay unchanged and are reported as tested.
- New work goes into a dated addendum and the deviations log (`docs/deviations_log.md`, D1–D7) **before** its code runs.
- The lead contribution is the CCK vs Wang-Hudson disagreement.
- The team is resubmitting one standalone, combined research plan.

## 6. Decisions and lessons (read before touching the data code)
- **Stooq is a dead end** (current securities only; LC.US redirects to an unrelated company).
- **Delisted gap:** 542 tickers (~27%) have no Yahoo data. This is a documented limitation; Tiingo could be tried later.
- **No price floor** (split-adjusted prices make NVDA look like a penny stock).
- **Never re-clean already-clean data** (it drops the first day twice).
- **Old snapshots:** pre-2015 BlackRock CSVs add "*" to some tickers, and the 2013–14 snapshots use SEDOL/CUSIP codes, which were resolved by name matching.
- **Windows DLL policy blocks `statsmodels.api`.** Import `OLS` / `RLM` from their modules directly.
- **Robinhood:** keep it in the main index and run a dropped-Robinhood robustness check. Use growth rates, not raw counts. Use the expanding-window cutoffs (no lookahead).
- **Pre-registration wording:** "primary specification, fixed before examining regression results".
- **H3 caveats:** survivor tilt from using 2022 data; high-attention stocks have higher betas.
- **Pooled winsorization biases CCK** on big-move days. Per-day winsorization doesn't.

## 7. Open to-dos
See [[To-dos]].

## 8. Ways of working
- **Validation-first:** inject known synthetic values and confirm exact recovery before using real data. Every analysis has a `test_*.py`.
- **Plain English:** every result must be explainable to a STEM fair judge.
- **Pre-register, then run:** commit the plan or deviation entry alone, then the code, then the results, each in its own commit.
- **End every session with an UPDATE** (format in [[UPDATE log]]). Add it to the top of that note and sync. See [[How to sync]].
- **Stack:** Python 3.14, pandas, numpy, statsmodels, scipy, matplotlib, yfinance, pytrends, Git, Obsidian + Obsidian Git.
- **Commit identity:** each person commits under their own GitHub account. No AI co-author trailers.
