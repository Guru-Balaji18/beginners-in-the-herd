# Project: "Beginners in the herd"
Regional Science and Engineering Fair — Mathematics/Statistics category
Researchers: Yuvraj Sharma and Guru Balaji, Middleton High School, Tampa FL

## Research question
Did ChatGPT's Nov 30, 2022 public release increase herding among stock
market investors specifically during periods of heavy new/inexperienced
investor entry, even though the average retail investor became LESS
herd-prone overall (per Even-Tov et al. 2025)?

## Hypothesis (H1)
The nonlinear CSAD coefficient becomes significantly more negative after
Nov 30, 2022, but only in high new-investor-entry periods. H2: in the
post-ChatGPT period during LOW entry, herding is unchanged/weaker vs.
pre-period (compatible with Even-Tov et al., not contradicting them). H3:
effect concentrated in high-retail-attention stocks, weak/absent in
institutional-heavy stocks.

## Herding measure: CSAD (NOT the earlier LSV approach — deprecated)
Cross-Sectional Absolute Deviation (Chang, Cheng & Khorana 2000), built
from daily stock RETURN DISPERSION vs. market return — not buy/sell
imbalance. Formula:

    CSAD_t = (1/N_t) * sum_i |R_i,t - R_m,t|

Secondary measures: Christie-Huang (1995) cross-sectional std dev, and
rolling 21-day average pairwise return correlation.

**IMPORTANT: Nasdaq RTAT data source and the LSV formula explored earlier
in this project are NOT part of the official plan. Do not use RTAT or
buy a subscription — CSAD only needs stock prices.**

## Data sources (all free, no subscriptions needed)
- Daily adjusted closes: Yahoo Finance (via `yfinance` Python library),
  Russell 1000 / S&P 500 constituents, Jan 2016 - Aug 2026
- Reconstructed historical index membership (from archived SPY/IWB
  holdings) — REQUIRED to avoid survivorship bias, not yet built
- Kenneth R. French Data Library — market factor, risk-free rate
- FRED — VIX, fed funds rate, NBER recession indicators
- Google Trends (via `pytrends`) — weekly beginner-investing search terms
- Interactive Brokers monthly net-new-account releases
- Robinhood / Schwab quarterly funded account counts (SEC EDGAR)
- FINRA daily short-sale volume files (retail attention split)

## New-investor entry index
Weekly Google Trends (beginner terms) + monthly IBKR net new accounts +
quarterly Robinhood/Schwab funded accounts -> standardize each to
z-scores (past data only, no lookahead) -> average into one index ->
forward-fill to daily. Top third = high entry, bottom third = low entry.

## Main regression model
    CSAD_t = g0 + g1|R_m,t| + g2(R_m,t)^2
             + g3(R_m,t)^2 * Post_t
             + g4(R_m,t)^2 * High_t
             + g5(R_m,t)^2 * Post_t * High_t
             + controls + e_t

Post_t = 1 on/after Nov 30, 2022. High_t = 1 on high-entry days.
Key coefficient: g5 (three-way interaction) — hypothesis predicts
significantly NEGATIVE. Controls: VIX, top-decile volatility day
dummy, month FEs, linear time trend, FOMC/CPI day dummies.
Estimation: OLS with Newey-West HAC standard errors, 5 lags.

Also split stocks into high vs. low retail-attention groups (FINRA
off-exchange volume share + Google Trends + inverse 13F institutional
ownership) and rerun CSAD within each group to test H3.

## Robustness / placebo plan
- 200 random placebo break dates
- Unknown-break-date supremum Wald test
- Pre-ChatGPT high-entry check (2020 pandemic surge, 2021 meme-stock
  surge) — if these already show the same herding, effect is about new
  investors generally, not AI specifically
- Alternative break dates (e.g. GPT-4, March 2023)
- Exclude top-7 tech stocks (index concentration check)
- International market comparison (lower ChatGPT penetration control)
- 5,000-iteration block bootstrap, 21-day blocks
- **Wang & Hudson (2022) bias-corrected herding test** — added as a
  robustness check alongside the main CCK/CSAD model, not a replacement.
  Their finding: the standard CSAD/CCK test is biased AGAINST detecting
  herding, because its null (no herding) implicitly assumes returns
  follow the CAPM exactly. Real idiosyncratic (stock-specific) error
  makes the TRUE no-herding relationship between CSAD and |R_m,t| convex
  rather than linear, so a non-finding from the standard test alone is
  weak evidence against herding. Their fix uses a SIGNED dispersion
  measure, SCSAD_t (= CSAD_t when R_m,t >= 0, = -CSAD_t when R_m,t < 0),
  regressed on signed (odd) powers of R_m,t instead of only |R_m,t| and
  R_m,t^2:
      SCSAD_t = alpha + gamma1*R_m,t + gamma2*R_m,t^2 + gamma3*R_m,t^3 + mu_t
  A significantly negative gamma3 indicates herding under this corrected
  test. We run this alongside the standard test with the same Post_t
  interaction applied (gamma3 * Post_t term) so the two can be directly
  compared; the paper should report both and flag any disagreement, since
  disagreement is exactly the failure mode Wang & Hudson describe.
  NOTE: could not verify one detail against the original paper directly
  (paywalled at Wiley/IJFE) — a citing paper's description mentioned
  "suppression of intercept" as part of one of their modified
  specifications. We kept the intercept (alpha) as specified in this
  project's version, matching the formula above. Worth the students
  double-checking against the original paper (Wang & Hudson 2022/2024,
  IJFE 29(1), 790-818, doi:10.1002/ijfe.2707) if they get institutional
  access, before finalizing the write-up.
  Full three-way version (adding High_t and High_t*Post_t interactions,
  matching the main model's g4/g5 structure) is blocked on Step 3 (new-
  investor entry index) — not yet built. Current implementation runs the
  two-way Post_t interaction only.

## Tech stack
Python 3.12, pandas, numpy, statsmodels (regression + HAC SEs +
structural break tests), arch (GARCH volatility control), scipy
(hypothesis testing, bootstrap), matplotlib, yfinance, pytrends,
Git/GitHub for version control.

## Progress so far
### Step 1 (return panel) — DONE, real Russell 1000 universe
Built and validated `build_panel.py`, now wired to the real reconstructed
membership (no longer the 10-ticker placeholder):
- Loads `data/membership.csv`, downloads daily prices via yfinance for
  all ~2,019 tickers in batches of 75 (Yahoo rate-limits/blocks very
  large single requests) with retry+backoff per batch
- Reshapes to long panel [date, ticker, close, volume]
- `apply_membership_filter()` now called with the real membership_df —
  survivorship-bias-safe
- Cleans: drops missing prices, zero-volume days (no price floor — see
  code comment on why a $ floor on split-adjusted prices is wrong)
- Winsorizes returns at 0.1/99.9 percentiles
- Computes equal-weighted and value-weighted market return series
- Study window: 2016-01-01 to 2026-08-31 (not 2013, even though
  membership.csv goes back further — no planned robustness check needs
  pre-2016 prices, and it roughly halves an already-huge pull)
- Validated with `test_panel.py` (5 tests, including a new
  `apply_membership_filter` test) — all passed

**Real-data run results (2026-09-10):**
- Final panel: 2,216,818 rows, 1,279 unique tickers, 2016-01-05 to
  2026-08-28. `n_stocks` per day ranges 664-1,011 (median 823) — hovers
  near expected Russell-1000-ish scale, doesn't drift to the full
  2,019-ticker universe, confirming membership turnover is being applied
  rather than everyone showing up every day.
- Spot-checked 5 known corporate events via membership.csv (Twitter/Musk,
  Activision-Microsoft, VMware-Broadcom, SVB collapse, Aaron's/IQVentures)
  — all correct in principle, but see the Yahoo data-availability finding
  below: several of these specific tickers have ZERO Yahoo price data at
  all, not because of a pipeline bug.
- 40 tickers had a >10-calendar-day gap in trading days; 37/40 are fully
  explained by legitimate index exit-then-re-entry (e.g. VIAV/SPXC/ATI
  left the Russell 1000 in 2016 and didn't rejoin until 2026 — the panel
  correctly shows a small 2016 cluster, a ~10-year gap, then a small 2026
  cluster). 3 unexplained smaller gaps (CBI 13 days, PARA 31 days, VVC 14
  days) — not investigated further, plausibly real short trading halts or
  minor Yahoo data hiccups, low priority given their small size.
- `data/failed_tickers.txt`: 740 of 2,019 tickers (36.7%) have zero
  usable price data. Root-caused, not a bug -- see below.

**MAJOR FINDING — Yahoo Finance systematically lacks data for delisted
securities.** Initial batched-download estimate (58.3% failure among
exited tickers) was superseded by a rigorous follow-up verification
(`verify_tickers.py`, 2026-09-10): every one of the 2,018 universe
tickers queried INDIVIDUALLY (no threading/batching) with a real delay +
retry on failure, to fully separate genuine data gaps from rate-limiting,
followed by a second pass searching Yahoo's own search API for a
renamed/successor ticker for anything still failing (validated by
actually downloading and checking name similarity before accepting a
match — see `build_membership.py`'s ALPHABET/GANNETT collision lesson
for why that validation matters).

Final, rigorous numbers:
| group | direct Yahoo data | recovered via alternate ticker | genuinely unresolved |
|---|---|---|---|
| STILL ACTIVE (944 tickers) | 940 (99.6%) | 4 (0.4%) | **0 (0.0%)** |
| EXITED (1,075 tickers) | 466 (43.3%) | 67 (6.2%) | **542 (50.4%)** |

Rate-limiting fully ruled out as a cause: still-active tickers now show
ZERO unresolved failures (down from 7.8% in the batched run), confirming
those earlier failures were transient rate-limiting, not real gaps. The
~50% gap is concentrated entirely and specifically among exited/delisted
securities — including huge, unambiguous cases confirmed via direct
individual query: Twitter (Musk deal, 2022), Activision Blizzard
(Microsoft, 2023), VMware (Broadcom, 2023), Silicon Valley Bank
(collapsed 2023). This is a real, structural limitation of free Yahoo
Finance data: once a security has been delisted for a while, Yahoo
appears to eventually purge its historical quote data entirely, not just
stop updating it.

The alternate-ticker search recovered 71 renames worth noting for future
use (full list in `data/ticker_alternate_recoveries.csv`), e.g.
HCN->WELL (Welltower), PEAK->DOC (Healthpeak), AAXN->AXON, GDI->IR
(Ingersoll Rand), WTR->WTRG (Essential Utilities), VISA->V (Visa's own
2013-14 alternate-code bug, an independent confirmation of the
build_membership.py fix from earlier). These aren't wired into
`return_panel.csv` yet — recovering them there requires relabeling the
successor ticker's price data back onto the original historical ticker
symbol (so it lines up with membership.csv's dates), which is a small
but real design decision, not done in this session.

Outputs: `data/ticker_verification.csv` (per-ticker pass/fail),
`data/ticker_alternate_recoveries.csv` (71 recovered renames),
`data/ticker_still_unresolved.csv` (542 genuinely unrecoverable, with
the best candidate name-match considered for each, for manual review).

**Stooq recovery attempt (2026-09-22) — DEAD END.** Investigated Stooq
as a supplementary free source for the 542 genuinely-unresolved tickers.
`pandas_datareader`'s `stooq` data source has been fully removed from
the current release (0.11.1, also the latest -- no `stooq` module exists
at all). Stooq's own site now gates BOTH its per-symbol CSV export
(`/q/d/l/`) and its bulk EOD archive download (`/db/h/`) behind an actual
image CAPTCHA -- confirmed via plain requests, an authenticated browser
fetch, and a real UI click, all returned "Access denied" until the
CAPTCHA appeared. Per policy, CAPTCHAs are never bypassed.
The user manually solved the CAPTCHA and downloaded Stooq's ~514MB "US
daily ASCII" bulk archive. Parsing it (13,287 entries: NASDAQ/NYSE/NYSE
American common stocks + ETFs) found **0 of the 542 unresolved tickers
present** -- this bulk archive only contains CURRENTLY listed securities,
not delisted ones, despite Stooq's general reputation for retaining
delisted-security history. Individually spot-checked 3 tickers directly
on Stooq's website to confirm this wasn't an archive-format artifact:
TWTR.US and VMW.US both return "Symbol does not exist in the database";
LC.US (LendingClub) redirects to "HAPN.US," which turned out to be a
**completely unrelated company** ("Happen Inc") that later recycled the
same ticker symbol -- a trap that would have silently corrupted the
panel with the wrong company's prices if merged without checking.
**Conclusion: Stooq does not provide a usable path to recovering these
542 tickers.** `recover_from_stooq.py` exists and works correctly (ready
to reuse if a real delisted-inclusive archive is ever found), it's just
that this particular data source doesn't have the data.

**Recovery robustness check (2026-09-22).** Since Stooq added nothing,
compared the strict native-Yahoo-only panel against a panel that adds
back the 71 tickers already recoverable via Yahoo's own rename-search
(`ticker_alternate_recoveries.csv`, e.g. WLTW->WTW, HCN->WELL) -- the
only genuinely recovered data actually available. `rebuild_panel_with_
recovery.py` builds this second panel (`return_panel_recovered.csv` /
`market_returns_recovered.csv`, kept separate from the main panel).
**Caught and fixed a real bug while building it**: naively re-running
`clean_and_compute_returns()` on `return_panel.csv`'s already-cleaned
close/volume columns double-differences the data -- `pct_change()`'s
per-ticker first-row NaN, which correctly drops each ticker's first
*truly unknown* day on a first pass, incorrectly drops every ticker's
already-valid first day on a second pass. Caught via the n_stocks sanity
check (2016-01-05 dropped to 20 tickers instead of ~940). Fixed by
computing returns fresh ONLY for the newly-added rows and concatenating
already-computed results, not re-cleaning everything from scratch.
Panel-quality re-check on the corrected recovered panel: n_stocks now
681-1,015 (vs strict panel's 664-1,011) across 1,318 tickers (vs 1,279);
same 40 legitimate membership-turnover gaps as before, plus 3 new ones
from the added tickers, no new anomalies.
`compare_recovery_robustness.py` reran both the standard CCK test and
the Wang-Hudson SCSAD test on both panels. **The Post_t interaction
coefficient (the two-way proxy for the eventual g5 three-way term)
agrees in sign and significance between the strict and recovered
panels** -- standard test: +0.59 (p=0.32) vs +0.58 (p=0.33), 1.6% change;
Wang-Hudson: -15.85 (p=0.18) vs -16.77 (p=0.16), 5.8% change. **The
Yahoo delisted-data gap does not appear to change this conclusion.**
(Recovering only 39-70 tickers out of 542 missing wasn't going to be a
strong test of this either way -- worth re-running once/if a real
delisted-security data source is found, but the base-case answer right
now is "the gap doesn't seem to matter.")
**Separately, and more importantly for the actual research question**:
on the REAL panel (unlike the earlier placeholder-universe run), the
standard CCK test and the Wang-Hudson test now DISAGREE on the BASE
herding effect (not the Post interaction) -- standard test's rm2 is
insignificant (p=0.95, essentially zero), while Wang-Hudson's rm3 is
strongly significant and negative (-75.07, p<0.0001) in BOTH panel
versions. This is exactly the failure mode Wang & Hudson's paper
describes: the standard test misses herding that the corrected test
detects. Worth highlighting in the write-up regardless of what happens
with Post_t/High_t once the full model is built.

Also fixed along the way: `robustness_wang_hudson.py` was importing
`statsmodels.api`, which eagerly loads state-space/Kalman-filter code
this machine's endpoint security now blocks at the DLL level
("Application Control policy") -- switched to importing `OLS`/
`add_constant` directly from their own submodules, which avoids that
code path entirely (we only ever needed plain OLS + HAC errors). If this
DLL block resurfaces elsewhere, this is the fix.

**This is a real constraint on the free-data-only approach stated in the
plan, and needs a decision**: (a) accept the gap and note it as a
limitation -- the recovery robustness check above is a data point in
favor of this being safe, though not a full resolution, since Stooq
specifically didn't pan out and we only tested with a small recovered
subset, (b) look for a different supplementary free source (Tiingo's
free tier, archived data, something else -- Stooq is now a dead end),
(c) revisit the free-data-only constraint. Not resolved in this
session — flagging for the research team to decide.

### Historical Russell 1000 membership — DONE
Built and validated `build_membership.py`: reconstructs membership from
iShares IWB ETF holdings (IWB's holdings ARE the Russell 1000) via
BlackRock's fund-document API. Reliable daily/monthly snapshots confirmed
from 2013-01 onward (data exists sporadically back to 2006-10 but is too
gappy to trust before 2013) — comfortably covers the study's 2016-2026
window. Output: `data/membership.csv` ([ticker, start_date, end_date],
2,155 rows / 2,019 tickers). Validated against 5 known real-world events
(Twitter/Musk, Activision-Microsoft, VMware-Broadcom, Splunk-Cisco, SVB
collapse) — every end_date landed one snapshot after the real event.
Known limitations:
- A ~6-month gap in BlackRock's archive (2017-01-01 to 2017-07-09, zero
  snapshots) means membership changes within that window specifically
  may be misdated.
- `resolve_alternate_ticker_codes()` fixes cases where BlackRock's own
  2013-2014-era exports used a leaked SEDOL/CUSIP-style code or a plain
  company-name fragment instead of the real ticker (e.g. "8686"/"VISA"
  for AFLAC/Visa) by matching on exact company name against later "clean
  era" snapshots. Deliberately does NOT use fuzzy/normalized name
  matching — that was tried and reverted after it was found to silently
  merge genuinely different securities that share a normalized name
  (GOOGL/GOOG, FOXA/FOX, and worse, two actually-unrelated companies:
  Gannett Co [TGNA] and the 2015 Gannett spinoff [GCI]). A small residual
  of exact-match misses (e.g. Visa's early name "VISA INC" vs later
  "VISA INC CLASS A") are left unresolved by design rather than guessed
  at — see the function's docstring for the full reasoning. 3 tickers
  remain permanently unresolved (name never appears in a clean-era
  snapshot at all): Time Warner Cable, Towers Watson, Actavis.
- Validated with `test_membership.py` (2 tests: alternate-code
  resolution + the "don't auto-merge on name changes" guard).

### Step 2 (CSAD) — code DONE, `data/csad.csv` STALE
Built and validated `build_csad.py`: computes CSAD_t (mean absolute
deviation of stock returns from equal-weighted market return) and its
signed variant SCSAD_t, plus the Post_t (Nov 30 2022) dummy. Validated
with `test_csad.py` (exact hand-computed recovery, sign-following SCSAD,
post-dummy boundary, non-negativity) — all tests passed.
**`data/csad.csv` on disk was built from the OLD 10-ticker placeholder
panel, before Step 1 was rerun on the real universe (2026-09-10) — rerun
`python build_csad.py` before using it for anything.**

### Wang & Hudson (2022) robustness check — code DONE, needs rerun
(see Robustness plan above for the methodology). Built
`robustness_wang_hudson.py`, which runs the standard CCK test and the
SCSAD-cubic test side by side and reports whether their conclusions
agree. Validated with `test_robustness_wang_hudson.py` (exact
coefficient recovery from synthetic data with known true coefficients,
for both a herding and a no-herding case, on both regressions). Last run
on the OLD placeholder-universe `csad.csv` (see above) — both tests
agreed then, but that result is stale now that Step 1 uses the real
universe; rerun after regenerating `csad.csv`.

### Step 3 (new-investor entry index) — BUILT, design decisions open
`investor_index.py` builds the index; `test_investor_index.py` (29
checks, all pass) validates it offline. Outputs:
`data/investor_index_weekly.csv` (per-component z-scores, composite,
High/Low), `data/investor_index_daily.csv` (trading days 2016-01-05 to
2026-08-28), `data/entry_component_*.csv` (each cleaned component).
Raw pulls are cached in `data/raw/` so reruns don't hit the sources.

Components and coverage:
- Google Trends (weekly): 5 beginner-investing terms ("how to invest",
  "how to buy stocks", "stock market for beginners", "investing for
  beginners", "how to invest in stocks"), 2011-2026. Google only returns
  weekly data for windows of 5 years or less, so 4 overlapping windows
  are chain-rescaled. Terms were chosen to match the spirit of Reyes
  (2018), NOT checked against that paper's exact term list. Brand names
  (e.g. "robinhood") were left out on purpose.
- IBKR (monthly): client accounts from IBKR's monthly press-release
  PDFs, 2016-10 to 2026-08 (not on EDGAR). Since 2024-06, IBKR's server
  wraps each PDF in a leaked Java `SerialBlob` object; the PDF inside is
  intact and gets extracted. 3 releases are missing (2017-12, 2020-03,
  2021-10); each is backed out from the next month's reported "% higher
  than prior month". Without that, March 2020 (the COVID crash) got
  folded into April. The Folio acquisition (57k accounts, Jan 2021) is
  subtracted.
- Schwab (quarterly): "new brokerage accounts" from earnings-release
  exhibits on EDGAR, 2010-Q3 to 2026-Q2 (the pre-2016 part is burn-in
  history for the z-scores). Acquired accounts are removed using
  Schwab's own footnotes: optionsXpress 315k (2011-Q3), USAA 1.1M
  (2020-Q2), TD Ameritrade 14.5M (2020-Q4).
- Robinhood (quarterly): funded accounts, 2020-Q1 to 2026-Q2, from the
  IPO prospectus, 10-Q/10-K tables, and earnings releases. Pre-2020
  only year-end totals exist (Robinhood was private). The Q4-2023 rename
  ("Net Cumulative Funded Accounts" -> "Funded Customers", accounts ->
  unique people) was checked: restated history matches the old figures
  at the 0.1M precision reported. Levels are only reported to 0.1M,
  which is coarse next to 2022-23 quarterly net adds of about 0.1M.
- SEC EDGAR requires a declared contact in the User-Agent header;
  `namadev.balaji18@gmail.com` is used (sent only to sec.gov).

Method: each component becomes an organic new-investor flow, gets an
expanding (past-only) z-score at its own frequency, is mapped to weeks,
and is averaged with whatever components are available that week (2 of
4 before IBKR's z-score starts in 2017-10, all 4 from 2020-Q4). The
result is forward-filled to trading days. High_t = top third of weekly
index values in 2016-2026, Low_t = bottom third.

Validity checks: all components correlate positively (0.35-0.58). Top
weeks are exactly the known surges: March 2020 (COVID crash), late
January 2021 (GameStop), and the week of Dec 31, 2017 (crypto peak).

**Design decisions / problems to resolve before Step 5:**
1. **Post x High cell is thin and late.** Only 110 of 939
   post-ChatGPT trading days are High, and all 110 are in 2025-2026;
   none fall in Dec 2022-2024 (2022-23 are 90-98% Low). The key g5
   coefficient would be identified entirely from ~110 days in 2025-26,
   and any market event specific to that window is a confound.
   Pre-ChatGPT High days are dominated by 2017, 2020, and part of 2021,
   so the comparison group is mostly COVID-era and meme-era stress.
   Options: accept it and say so; use the continuous index instead of
   tercile dummies (Rm^2 x Post x Index uses every day); or both.
2. **Robinhood's baseline is distorted by past-only z-scoring.** Its
   history starts during the 2020 surge (16-44% quarterly growth), so
   every later quarter scores low, including 2020-21 itself (average z
   -1.06 in 2020). It pushes 2022-26 toward Low. Dropping it moves
   post-ChatGPT High days from 110 to 156, still concentrated in
   2025-26. Options: keep it, drop it from the main index and use it
   only as a robustness check, or delay it with a longer burn-in.
3. **Growth rates vs raw counts.** Growth rates (flow / existing
   accounts) are the default. The worry that raw counts trend with firm
   size (IBKR's growth, Schwab absorbing TD Ameritrade) was right in
   direction: raw counts put more High days post-ChatGPT (21.8% vs
   11.7%). But it's smaller than the COVID-era effect, and
   corr(High, Post) is negative under every variant: -0.335 (growth,
   full-sample terciles), -0.226 (growth, expanding), -0.18 (raw,
   full-sample), -0.065 (raw, expanding).
4. **Tercile cutoffs.** The plan's full-sample terciles use the whole
   2016-2026 distribution, a mild form of lookahead that the past-only
   z-scores otherwise avoid. An expanding-cutoff version is available
   (`tercile_method="expanding"`).
5. **Google Trends.** Google notes data-collection changes on
   2016-01-01 and 2022-01-01. No visible level step at 2022-01-01
   (Q4-21 to Q1-22 ratios 0.73-1.10), but the year-earlier comparison
   is distorted by GameStop, so a subtle break can't be ruled out.
   Google Trends is also sampled: re-pulling gives slightly different
   numbers, and the cached pull in `data/raw/gtrends/` is the one used.
6. **Alignment.** Each monthly/quarterly value covers the period it
   describes ("reference" alignment), the standard choice for a
   contemporaneous classification variable (like NBER recession dates).
   `alignment="publication"` lags values until they were actually
   released, if the team prefers that.

### Step 1 fix (2026-09-23): ticker renames dropped years of data
When a company changes ticker (FB -> META), Yahoo re-files its whole
history under the new ticker and drops the old one. membership.csv still
listed the old ticker for the pre-rename years, so those years had no
prices at all: Facebook was missing from 2016 to mid-2022, and so were
Anthem, Welltower, Priceline/Booking, Coach/Tapestry and others.
Detection: an old ticker leaves the index at the snapshot right before
a new ticker enters, and Yahoo's price for the NEW ticker on that day
exactly equals the price iShares recorded for the OLD ticker (after
allowing for a later split confirmed in Yahoo's split history). Pairs
must also be one-to-one on the full candidate pool. Weight and
share-count continuity alone gave many false matches around the June
index reconstitutions (e.g. NorthStar -> Conduent).
Result: 36 verified renames in `data/renames.csv`.
`build_panel.relabel_renamed_tickers()` now handles them in any full
rebuild, and `python build_panel.py --patch-renames` patched the
existing panel: +44,020 stock-days, no duplicate-company warnings.
**Main results now use `return_panel_final.csv` / `market_returns_final.csv`.**

### Step 4 (retail attention) — BUILT (2 of 3 components; Google Trends pending)
`retail_attention.py` -> `data/retail_attention.csv`. Each stock is
classified ONCE over a formation window, the 52 weeks before ChatGPT
(2021-12-06..2022-11-25). FINRA's public API only goes back to
2021-12-06, and a pre-ChatGPT window can't be contaminated by the
post-ChatGPT change being tested. 861 stocks qualify (>=75% of window
days in the panel).
- FINRA non-ATS off-exchange share of dollar volume (retail
  internalization; ATS dark pools excluded): 861/861 stocks. The
  denominator uses unadjusted (split-only) prices; Yahoo's default
  prices are also dividend-adjusted, which would understate a
  high-yield stock's 2022 dollar volume by ~10-15%. Highest: AMD, NVDA,
  DKNG, ROKU, TSLA; lowest: quiet mid-caps.
- 13F institutional ownership as of 2022-09-30 (SEC bulk 13F data):
  850/861. Several real-data fixes were needed:
  - OpenFIGI's exchCode="US" filter fails even for Exxon, so US
    listings are picked manually.
  - Foreign-domiciled CUSIPs must be sent as ID_CINS.
  - SEC's current ticker->CIK map points to post-2022 holding companies
    (ExxonMobil, BlackRock), so Yahoo's historical share count is the
    fallback.
  - Multi-class companies use weighted-average basic shares.
  - Retired CUSIPs (Lam Research, BlackRock) are matched by issuer name.
- Google Trends "<TICKER> stock": STOPPED at 23 of 184 batches. Google
  throttled the free pytrends requests to ~3 min each, then stopped
  answering altogether (no new batch for 35+ min). Continuing would
  mostly produce skipped batches (patchy, alphabetically-biased
  coverage) and risk a longer IP block. The 23 finished batches are
  cached in `data/raw/gt_stocks/`, and `build_gt()` resumes where it
  stopped. The current index uses FINRA + 13F only (meets the ">= 2 of
  3 components" rule). DECISION NEEDED: drop this component, or resume
  it in slow overnight runs over several days.
- Validity: the two components correlate 0.36 in the expected
  direction. Most retail: GME, UPST, PLTR, TSLA, QS, F, NVAX, CHPT,
  DKNG. Least: CRI, FRPT, FIVE, LEA, BURL.
- Split: terciles (284/283/283, 11 unclassified); halves as robustness.
- Subsample CSAD is measured against the OVERALL market return, so both
  groups share identical regressors. The regression of CSAD_high -
  CSAD_low then gives exactly g5_high - g5_low with a correct HAC SE
  (the H3 test).
- Caveats: (1) stocks not alive in 2022 can't be classified, so the H3
  subsamples in early years are survivor-weighted; (2) high-attention
  stocks are higher-beta, so their CSAD relative to the market
  partly reflects beta.

### Step 5 (main regression) — RUN, all variants
`main_regression.py` -> `data/step5_main_results.csv`,
`data/step4_h3_results.csv`. The model follows the plan, plus a Low_t
interaction (middle third = baseline), so g7 = Rm^2*Post*Low tests H2.
Controls: VIX (Yahoo ^VIX), top-decile |Rm| day, calendar-month
dummies, linear trend, FOMC days (`data/raw/fomc_dates.csv`, 100 dates
incl. the March 2020 emergency meetings), CPI release days
(`data/raw/cpi_release_dates.csv`, from BLS; BLS blocks scripts, so it
was read through a real browser; note Oct-2025 CPI was never
published: shutdown). Newey-West HAC, 5 lags. Wang-Hudson version uses
the same interactions on the cubic term, no controls.
`test_main_regression.py`: 20/20 checks pass.

Primary spec (no Robinhood, growth, High/Low dummies, expanding cutoffs):
- Standard CCK: g5 = -3.99 (SE 2.47, p=0.106); g7 (post x LOW) =
  -6.15 (p=0.031). With lower-order terms: g5 -4.42 (p=0.073).
- Wang-Hudson: g5 = -430.5 (SE 153.6, p=0.005); g7 = -767.7 (p<0.001).
- H3 (terciles): CCK g5_high -1.76 (p=0.52) vs g5_low -4.68 (p=0.037);
  diff +2.92 (SE 0.87, p=0.0008), i.e. the OPPOSITE of H3. Halves:
  diff +2.07 (p=0.002). Wang-Hudson diff +50.4 (p=0.14).
Across all 25 main regressions, 10 have p<.05 for g5 (6 negative, 4
positive). The continuous-index versions flip sign: g5 is positive,
and significant in all 4 Wang-Hudson continuous runs.

**Key interpretation problem, calendar confound:** after ChatGPT, entry
terciles are almost pure year blocks. Low = all of 2023 (250/250 days)
+ Dec 2022; High = only 2025-26; Middle = mostly 2024-25. So g5 and g7
largely compare 2025-26 vs 2024 and 2023 vs 2024, and the design
can't separate new-investor entry from anything else that differed
across those years.

**Reading of the evidence:**
- H1: weak and fragile. Wang-Hudson supports it, the standard test
  doesn't, the continuous index contradicts it, and the sign flips
  across specifications.
- H2: contradicted. Herding-like curvature rose post-ChatGPT in
  low-entry periods as much or more than in high-entry periods.
- H3: not supported. The primary standard test is significant in the
  opposite direction.
- What survives: dispersion curvature does look different after Nov
  2022 relative to the middle-entry baseline, especially under
  Wang-Hudson, but it isn't tied to new-investor entry or retail
  attention.

**"Pre-registered" label:** the primary spec was fixed before any g5
estimate was seen, but after the Step 3 index diagnostics, and it isn't
registered with a third party. The only document that predates the
data is the Aug-31 research plan. Suggest wording: "primary
specification, fixed before examining any regression results". Also
list the deviations from the Aug-31 plan: Robinhood excluded,
expanding cutoffs, growth rates, Low_t term added, Wang-Hudson version
added, entry measured in the 52 weeks before ChatGPT for Step 4.

### Parts A-D of the 2026-09-28 addendum — DONE (see docs/addendum_2026-09-28.md, docs/deviations_log.md D1-D4)
- **Part B, Monte Carlo** (`simulate_herding_tests.py`, 80,000 simulated markets,
  outputs in `results/sim_*`):
  - **Wang-Hudson (our implementation):** says "herding" in 100% of
    no-herding markets in every scenario. The real WH t = -8.27 is at the
    50th percentile of the S5 null, so it is not evidence of herding.
  - **CCK:**
    - S5 is conservative (0.1% false alarms) and low-powered at the
      best-matching cell (S5, kappa=3, about 4%).
    - The registered pooled winsorization makes CCK false-alarm 97-100%
      when betas are equal.
    - Power is non-monotonic, and the sign check fails at kappa=3000.
  - **D3, the Post interactions:** null t-stats have SD 2-3 instead of 1.
    One-sided false alarms are 15% (CCK) and 34% (WH). The real g5 t
    (-1.62 CCK, -2.80 WH) is at the 15th/20th percentile of that null.
- **Part C, placebo break dates** (`placebo_break_dates.py`, 85 fake
  month-ends, `results/placebo_*`, `results/partC_summary.json`):
  - The real g5 is at empirical p = 0.43 (CCK) and 0.70 (WH).
  - 43% (CCK) and 89% (WH) of fake dates give a "significant" negative g5.
  - Decision rule: the effect is **not specific to ChatGPT's release**,
    in both tests.
  - g5 is nearly identical for any break from 2022-04 to 2024-10, because
    the High days sit in 2025-26.
- **Year fixed effects:**
  - Levels leave g5 unchanged.
  - Year-specific Rm^2 / Rm^3 slopes: CCK g5 -2.94 (p .27), WH -132 (p .39).
  - Decision: g5 is driven by between-year differences (calendar
    confound).
  - Within-year share of High variation: 49% overall, 69% of post days.
    For Low: 44% / 36%.
- **Part D, plan-literal High vs Low:**
  - CCK g5 +2.43 (one-sided p .93); WH +268 (one-sided p .996). Both
    are opposite to H1.
- **Holm across the 8 tests:** only WH year-FE-levels survives (0.021).
  That test is itself undermined by Part B, where WH's Post terms
  over-reject.

### Parts E–H of addendum 2 (2026-09-28) — see docs/addendum2_2026-09-28.md
- **Part E (verify Wang-Hudson against the paper): BLOCKED.** No PDF is
  available, and Wiley showed a bot-verification page.
  - `docs/wang_hudson_spec.md` lists the 8 details we can't verify.
  - Until the paper is checked, write "our implementation over-rejects",
    never "Wang-Hudson over-rejects".
  - To resume, put the paper at `docs/wang_hudson_2022.pdf`.
- **Part F (calibrated test, `calibrated_test.py`):**
  - Held-out size is 4.3–5.7% for every statistic.
  - Real calibrated one-sided p: CCK base 0.136, WH base 0.50,
    CCK g5 0.119, WH g5 0.39, CCK g7 0.075, WH g7 0.24. **Nothing is
    significant.**
  - Calibrated WH (ours) has no power.
  - The base-herding calibration depends heavily on the scenario
    (S5-calibrated CCK false-alarms on 100% of S4 markets).
  - The g5/g7 calibration is fairly robust across scenarios.
- **Part G (`mechanisms_diagnostics.py`, `docs/mechanisms.md`):**
  - Pooled winsorization clips 74% of stocks on a +9% day and cuts that
    day's CSAD by 72%, which creates false herding.
  - Per-day winsorization has the same size as no winsorization.
  - CCK's power collapses because a parabola can't fit the
    spike-and-flat-tails shape of extreme herding.
- **Part H (`robust_se.py`, `se_validation.py`):**
  - Newey-West with **longer** lags makes the false alarms **worse**, so
    the forward-filled-index explanation is wrong.
  - The 21-day block bootstrap fixes CCK (g5 4.9%, g7 6.6%, Post 8.5%)
    but not WH (15–18%). No method is fully calibrated; the bootstrap is
    best.
  - Real data with the bootstrap: g5 CCK p = 0.20, WH p = 0.071
    (one-sided); g7 CCK 0.031, WH 0.006, but WH's bootstrap over-rejects.
  - Per-day winsorization Step 5: primary CCK g5 -4.63 (NW5 one-sided p
    0.028; bootstrap 0.155), WH g5 -420 (bootstrap 0.074). No sign
    changes in the primary spec.
  - Placebo/year-FE decisions are unchanged. WH year-FE-levels no longer
    survives Holm (0.021 -> 0.65).

### Not yet started
- Deciding on the per-stock Google Trends component (see Step 4)
- `data/csad.csv` / `robustness_wang_hudson.py` standalone outputs are
  still stale (placeholder era). The Step 5 code rebuilds CSAD itself
  from the final panel, so these files are superseded rather than needed.
- Deciding how to handle the Yahoo delisted-data gap (see Step 1 finding
  above) before treating any regression result as meaningful
- Step 6: remaining robustness tests (international comparison, etc.);
  break-date placebo and simulation done (see above)
- Step 7: documentation/versioning

## Files in this handoff
- `build_panel.py` — Step 1 pipeline, run on the real ~2,019-ticker
  Russell 1000 universe (done, see results above)
- `test_panel.py` — validation suite for build_panel.py
- `build_membership.py` — Russell 1000 membership reconstruction (done)
- `test_membership.py` — validation suite for build_membership.py
- `verify_tickers.py` — rigorous individual (unbatched) Yahoo data-
  availability check + alternate-ticker recovery search (done, see
  Yahoo delisted-data finding above)
- `build_csad.py` — CSAD/SCSAD/Post computation (code done, output stale)
- `test_csad.py` — validation suite for build_csad.py
- `robustness_wang_hudson.py` — Wang & Hudson (2022) robustness check
- `test_robustness_wang_hudson.py` — validation suite for the above
- `recover_from_stooq.py` — parses a manually-downloaded Stooq bulk
  archive for delisted-ticker recovery (works correctly; Stooq itself
  turned out not to have the data — see finding above)
- `rebuild_panel_with_recovery.py` — builds a second panel version
  (`return_panel_recovered.csv`) including any recovered tickers, for
  comparison against the strict Yahoo-only panel
- `compare_recovery_robustness.py` — runs both regressions on both panel
  versions and reports whether the data gap changes the conclusion
- `retail_attention.py` — Step 4 stock-level retail-attention index
  (FINRA off-exchange share, 13F ownership, Google Trends) -> groups
- `main_regression.py` — Step 5 main regression, all variants, plus the
  Step 4 H3 split
- `test_main_regression.py` — validation suite for the two above
- `data/renames.csv` — 36 verified ticker renames used by build_panel.py
- `investor_index.py` — Step 3 new-investor entry index (Google Trends,
  IBKR, Schwab, Robinhood) -> High_t / Low_t
- `test_investor_index.py` — validation suite for investor_index.py
