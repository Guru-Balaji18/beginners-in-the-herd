D8 — Step 8 analyses of the research plan (pre-registered 2026-11-19, before code).

Decisions on measures. These analyses will not be run, with the reasons:
- The Christie-Huang CSSD and the rolling pairwise-correlation measures. Question 2 already compares two herding tests in depth. CSSD is the earlier, less powerful form of the CCK idea, and pairwise correlation has no no-herding benchmark in our framework.
- The per-stock Google Trends attention measure (team decision). Google rate limits left only 23 of 184 batches.
- The unknown-break-date (sup-Wald) test. The Part C placebo grid already asks whether the break is special.
- International markets and a GARCH volatility control. Both need large new data work for little gain at this stage.

Common setup for 8a to 8d:
- Specification: the registered primary specification (no Robinhood, growth rates, High/Low tercile dummies with the middle third as baseline, expanding cutoffs).
- Data: the registered pooled-winsorized panel.
- Tests: both tests are run. CCK uses the controls; Wang-Hudson (WH) does not.
- Standard errors: two methods are reported. Newey-West with 5 lags is the registered primary. The 21-day moving-block bootstrap (B = 5,000) is the best-calibrated method for CCK in Part H.
- Bootstrap seeds: SeedSequence([20260928, 11, k]), with k = 1, 2, 3, 4 for 8a to 8d.
- Wang-Hudson: under the plan's H4 decision rule, WH results are reported but not used as evidence, because WH fails H4.

8a Effect size, from the primary CCK fit on the full sample.
- Inputs: σ = the standard deviation of the daily equal-weighted market return over the regression sample. A "2-SD move" means |R_m| = 2σ.
- Six regime cells (pre/post x low/middle/high entry). For each, the curvature contribution to CSAD in basis points is (g2 + g3·post + g4·high + g5·post·high + g6·low + g7·post·low) x (2σ)² x 10,000.
- Reported:
  - (i) the g5 effect alone, g5 x (2σ)² x 10,000 bp, with a 95% interval from the block bootstrap;
  - (ii) the post-minus-pre change in each entry group (g3, g3 + g5, g3 + g7, scaled the same way);
  - (iii) each figure as a percentage of mean CSAD on days with |R_m| ≥ 2σ.
- WH: the same quantities with (2σ)³ on the signed measure, for completeness.
- Rule, following the plan's effect-size statement: if |g5 effect| is below 1 basis point, it is called economically negligible.

8b Alternative break date: the GPT-4 release.
- Post_t = 1 on and after 2023-03-14. Rerun the primary specification for both tests and record g5 and g7 under both standard-error methods.
- Report the empirical percentile of the GPT-4 g5 among the 84 identified Part C placebo g5 values (results/placebo_break_dates.csv), for each test.
- Rule: herding "tracks the GPT-4 release" only if both hold:
  - CCK g5 < 0 with a bootstrap one-sided p < 0.05;
  - the CCK g5 is more negative than 95% of the placebo values.
  Otherwise it does not.

8c Exclude the seven largest technology companies.
- Remove AAPL, MSFT, GOOGL, GOOG, AMZN, NVDA, META and TSLA (seven companies; Alphabet has two share classes) from the registered panel.
- Recompute the equal-weighted market return and CSAD/SCSAD.
- Rerun the primary specification for both tests, plus the base-herding regressions (standard_cck_regression, wang_hudson_scsad_regression).
- Rule: the result "depends on these stocks" if, relative to the full sample, either holds:
  - the CCK g5 changes sign;
  - its bootstrap one-sided p crosses 0.05.
  Otherwise it does not.

8d Liquidity-weighted market.
- Measure CSAD/SCSAD against the panel's existing mkt_ret_vw instead of the equal-weighted market. Its weights are close x volume, a liquidity proxy, not true market capitalization; it is labeled that way.
- Rerun the primary specification for both tests.
- Rule: the same as 8c.

Multiple testing: apply Holm-Bonferroni across the three CCK bootstrap one-sided g5 p-values from 8b, 8c and 8d.

Outputs: results/step8_results.csv and results/step8_summary.json.

Validation first: test_step8.py must pass before any real-data run. It must:
- reproduce the Step 5 primary g5 exactly on the full sample;
- recover known effect sizes in basis points from synthetic coefficients;
- confirm the excluded tickers are absent and the recomputed market equals the manual mean;
- confirm the GPT-4 Post dummy switches on exactly at 2023-03-14.
