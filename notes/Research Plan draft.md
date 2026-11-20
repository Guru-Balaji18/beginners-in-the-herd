---
title: Research Plan draft
aliases: [research plan, revised research plan, combined plan]
type: document
tags: [plan, draft]
created: 2026-11-19
updated: 2026-11-19
status: draft
summary: Draft of the combined, standalone research plan (Nov 2026). One item (⚠) still needs a decision before submission.
---
# Research Plan (draft, November 2026)

> [!warning] Draft for Guru and Yuvraj to edit
> ⚠ Before submitting, ask Mrs. Kulkarni whether the fair wants a
> revised plan, or the original plan plus an addendum. Fair rules usually
> expect the plan to be written before the research, with later changes
> documented separately.
> Back to [[Home]] · sources: [[Handoff]], [[deviations_log]], [[wang_hudson_spec]], [[mechanisms]].

**Regional Science and Engineering Fair: Research Plan**

| | |
|---|---|
| Names | Yuvraj Sharma and Guru Balaji |
| School | Middleton High School, Tampa, Florida |
| Category | Mathematics, subcategory Statistics |
| Research teacher | Mrs. Kulkarni |

## Title and questions

**Title:** Beginners in the Herd: Did generative AI increase stock-market herding when new investors poured in, and can the standard herding tests tell?

**Question 1.** Did the public release of ChatGPT increase herding among stock market investors during periods when large numbers of new and inexperienced investors were entering the market, even though the average retail investor appears to have become less herd-prone?

**Question 2.** Can the two standard tests for herding be trusted on data like ours? In particular, how often does each one report herding in markets where there is none, and how often does it catch herding that is really there?

## Background: our original plan, what happened, and why this plan is revised

### The original plan (August 31, 2026)
Our first research plan asked only Question 1. We planned to:
- build daily returns for every stock in the Russell 1000 from 2016 to 2026, counting each stock only on days it was in the index;
- measure herding with the standard CSAD test (Chang, Cheng and Khorana, 2000);
- build a new-investor entry index from Google Trends searches and brokerage account counts;
- sort stocks by retail attention using FINRA off-exchange volume, each stock's Google Trends searches and institutional ownership;
- test H1 to H3 with one regression.

In that regression, the key coefficient g5 compared herding after ChatGPT on high-entry days against low-entry days. We also listed robustness checks: 200 random placebo break dates, a test for an unknown break date, later model release dates, dropping the largest technology stocks, international markets and a block bootstrap. The hypotheses H1, H2 and H3 below are copied from that plan without changes.

### What happened

#### While building the data (August and September 2026)
Several parts of the plan did not work with the real data. We changed them and wrote each change down.
- We dropped the rule that removed stocks priced under one dollar. Split-adjusted prices made companies such as NVIDIA look like penny stocks in 2016, and index membership already keeps real penny stocks out.
- Robinhood's account data only begin at its 2020 surge, which made every later quarter look like low entry. Our main entry index leaves Robinhood out, and a second version keeps it.
- Each entry source became a growth rate, because the raw counts were on very different scales.
- The high and low cutoffs use only past data. The original full-sample cutoffs would have used information from the future.
- We added terms for low-entry days and used the middle third as the baseline, so that H2 could be tested directly. This meant g5 compared high-entry days with middle days instead of low days. We later ran the original High-versus-Low version as well.
- We added Wang and Hudson's newer test next to the standard one, because they argue the standard test is biased against finding herding.
- Google limited our requests, so only 23 of 184 batches of per-stock search data finished. The attention split uses the other two measures.
- 542 index members (about 27%), mostly delisted companies, had no price data available. We record this as a limitation.

#### The main test (September 2026)
The main test came out weaker than we hoped, and parts of it pointed the wrong way.
- In our primary specification, g5 was −3.99 in the standard test (one-sided p = 0.053) and −430.5 in the Wang-Hudson test (p = 0.003).
- Herding also rose after ChatGPT on low-entry days, which contradicts H2.
- The effect was larger in low-attention stocks than in high-attention ones (difference +2.92, p < 0.001, standard test), the opposite of H3.
- Across our 25 regressions, 10 gave a significant g5: 6 negative and 4 positive.
- After November 2022 the entry groups fell into almost separate years, so g5 was comparing years more than investor types.
- The two tests did not agree on whether the market herds at all. On the same data, the standard test found no herding (p = 0.94) and the Wang-Hudson test found very strong herding (p < 0.0001).

#### Checking the result (September 28 to October 21, 2026)
Before running anything more, we wrote down a plan for checking these results and committed it, and every later check followed the same rule. The checks found:
- In simulated markets built to have no herding, our Wang-Hudson test reported herding in 100% of them. The standard test almost never did (0.1%), but it also missed weak herding.
- When we moved the "ChatGPT date" to 84 fake dates, the effect was just as large (empirical p = 0.43 standard, 0.70 Wang-Hudson). It also disappeared once each year got its own slope. So it is not tied to ChatGPT's release.
- The plain High-versus-Low comparison from our original plan gives a positive g5 (+2.43 and +268), the opposite of H1.
- With standard errors that passed our simulation check, g5's one-sided p-value is 0.20 in the standard test. Judged against simulated no-herding markets, it is 0.12 (standard) and 0.39 (Wang-Hudson).
- We obtained Wang and Hudson's paper and confirmed that our test is exactly their Equation 3. Their own method, under both possible readings of their estimator, also reports herding in 100% of markets that have none. The cause is a jump in their signed measure at a market return of zero. Their own simulation hid the problem because its market moves went up to ±50% in a day.

#### Final checks (November 19, 2026)
We wrote down the last planned checks and pushed them to GitHub before running them (deviations log entry D8). None of them changed the answer:
- Using the GPT-4 release date (March 14, 2023) instead of November 30, 2022 gave the same result (standard test, one-sided p = 0.21 with the standard errors that passed our simulation check).
- Leaving out the seven largest technology companies gave the same result (p = 0.21).
- Measuring dispersion around a liquidity-weighted market made g5 smaller (p = 0.33).
- On a day when the market moves 2 standard deviations (2.5%), g5 corresponds to about −25 basis points of dispersion, roughly 11% of normal dispersion on such days. Its 95% interval runs from −55 to +60 basis points, so the data cannot rule out zero.

### Why we revised the plan
- The data forced design changes, and the plan should describe the study we actually ran.
- Question 1 now has an answer: the evidence does not support H1, H2 or H3. We keep the hypotheses exactly as written and report them as tested.
- The checking turned up a result we did not plan for and now think matters more: one of the two published herding tests gives false alarms on daily stock data, for a reason we can show and explain. That became Question 2.
- Every change is dated and recorded in our deviations log (entries D1 to D8), so a reader can see what was planned and when.

### Our new goal and hypothesis
Our goal now is to find out whether the standard herding tests can be trusted on daily stock data, to explain any failure in plain terms, and to answer Question 1 only with methods that pass that check.

The new hypothesis is H4: a valid test, run at the 5% level, reports herding in about 5% of simulated markets that have no herding. Together with it, we predicted on September 28, 2026, before running any simulations, that the Wang-Hudson test would fail this check because of the jump at zero. Both are stated in full under Hypotheses below. H1 to H3 stay unchanged. The last analyses (Step 8) checked whether the answer to Question 1 changes with the effect size, the GPT-4 release date, the largest technology stocks or the way the market return is weighted.

## Rationale

Herding in finance means investors copying what other investors are doing instead of trading on their own information. It leaves a signature in price data. When people herd, individual stock returns cluster tighter around the market return than any rational asset pricing model predicts, and they cluster tightest on the days when the market moves the most. Christie and Huang (1995) wrote the first test for this. Chang, Cheng and Khorana (2000) improved it using a measure called cross sectional absolute deviation, or CSAD, which is now the standard tool for detecting herding from daily returns alone.

ChatGPT went public on November 30, 2022. Since then a large number of ordinary investors have started asking a chatbot what to buy. Two recent papers look at what that did, and they point in different directions. Even-Tov, Lourie, Munevar and Nekrasov (2025) used account level trading data along with Italy’s temporary ban on ChatGPT as a natural experiment. During the ban, investors concentrated their trades in fewer assets and shifted toward already popular ones. Read in reverse, having access to ChatGPT made the average retail investor trade more independently, not less. Cheng, Lin and Zhao (2025) used unexpected ChatGPT outages and found that trading volume and informed trading both dropped when the tool went down, which confirms that a real share of investors are using it to make decisions.

Both findings can be correct and still leave something out. Even-Tov et al. report an average across every retail account in their sample, and averages hide subgroups. Someone who already knows how to read an income statement can use a chatbot as a research assistant, check its output against a filing, and end up with a portfolio that looks less like everyone else’s. Someone who opened their first brokerage account three weeks ago has no way to evaluate the answer. For that person the model is not a research tool, it is an authority. And because the model gives near identical answers to near identical prompts, ten thousand beginners asking which AI stocks to buy get roughly the same list. That is a herding mechanism, not a de-herding one.

So the sign of the effect should depend on who is trading. In stretches where the market fills up with brand new accounts, we expect ChatGPT to push herding up. In stretches where it does not, we expect the Even-Tov result to win out.

This is worth knowing because herding is not only a problem for the person doing it. When enough investors move in the same direction at once, the random noise in their individual decisions stops cancelling out and turns into systematic risk that cannot be diversified away. Bikhchandani and Sharma (2001) described how information cascades produce exactly this. The Financial Stability Board (2024) has warned that broad AI adoption could raise correlation across market participants because so many of them depend on the same small set of models. Nobody has tested whether that has already shown up in the price data, and nobody has tested it conditionally on how many inexperienced people are in the market at the time. That is the gap we are trying to fill.

The answer to Question 1 depends on which herding test we use, which is why we added Question 2. The standard test (Chang, Cheng and Khorana, 2000; "CCK") and a newer alternative by Wang and Hudson (2024), which uses a signed version of CSAD, are both in use, and Wang and Hudson argue that the standard test is biased against finding herding. On our data the two tests disagree about whether there is any herding at all, so at least one of them is wrong for data like ours. Whether a test works can be checked: build simulated markets where we decide whether herding exists, run the test on thousands of them, and count how often it gives the right answer. At the 5% level, a test that works should report herding in about 5% of the markets that have none.

## Hypotheses and expected outcomes

**Question 1.** Our hypothesis is that herding increased after ChatGPT's release, but only when many new and inexperienced investors were entering the market, because new investors lack the financial literacy to use AI output critically. As testable statements:

- H1. The nonlinear CSAD coefficient becomes significantly more negative after November 30, 2022, but only in high entry periods. In the model below, the coefficient on the three way interaction is negative and statistically significant.
- H2. In the post-ChatGPT period during low entry, herding is unchanged or weaker than in the matched pre-period. This is the condition under which our result is compatible with Even-Tov et al. rather than contradicting them.
- H3. The effect is concentrated in stocks with high retail attention and is much smaller or absent in stocks held mostly by institutions.
- Null hypothesis. The three way interaction coefficient is zero. ChatGPT's release did not change the relationship between new investor entry and herding.

What would falsify the hypothesis: a three way interaction coefficient that is zero, positive, or negative but not statistically distinguishable from zero once we control for volatility and market stress. A negative coefficient that also appears at placebo break dates would mean we are picking up a trend rather than an event, and we treat that as a failed result too. We report the result either way.

**Question 2.**

- H4. A valid test, run at the 5% level on simulated markets with no herding, reports herding in about 5% of them. With 1,000 simulated markets the acceptable range is 3.6% to 6.4%.
- Prediction, written down on September 28, 2026, before the simulations were run. The Wang-Hudson signed measure equals +CSAD on up days and −CSAD on down days. Since CSAD is always positive, the measure jumps from about −CSAD to +CSAD at a market return of exactly zero. A smooth cubic curve fitted across that jump bends in a way that looks like herding, so the Wang-Hudson test may report herding even when there is none. If so, we report it as a finding and do not change the test to hide it.
- Decision rule. Conclusions about Question 1 rely only on tests that pass H4 in our most realistic simulated market. A test that fails is reported, with an explanation of why it fails, but is not used as evidence for or against herding.

## Materials

This project uses no chemicals, no living organisms, no human participants, no vertebrate animals and no hazardous devices. Every input is publicly available secondary data or free software.

Hardware: one personal laptop used for all analysis.

Software:
- Python 3.14;
- pandas and numpy for data handling;
- statsmodels for regression, Newey-West standard errors and robust regression;
- scipy for statistics;
- matplotlib for figures;
- yfinance and pytrends for data collection;
- Git and GitHub for version control;
- Obsidian for shared project notes.

Data sources (all public and free):
- Yahoo Finance: daily adjusted closing prices for every Russell 1000 member, January 2016 through August 2026, and the daily VIX.
- iShares IWB (Russell 1000 ETF) holdings archive from BlackRock, used to rebuild index membership day by day.
- SEC EDGAR: Robinhood and Charles Schwab quarterly filings (funded accounts), 13F institutional holdings data sets, and XBRL shares-outstanding data.
- Interactive Brokers monthly brokerage metrics (net new accounts).
- Google Trends weekly search volume for beginner investing queries such as "how to buy stocks" and "best brokerage account for beginners".
- FINRA OTC (off-exchange) transparency data.
- OpenFIGI, to match securities identifiers to tickers.
- Federal Reserve FOMC meeting calendar and Bureau of Labor Statistics CPI release schedule.
- Wang and Hudson's own manuscript (open access, CC-BY), used to check our implementation of their test.

## Procedures

**Who did the work.** Guru Balaji and Yuvraj Sharma did all of the research. We chose the question, designed the study, decided every method and every change to the plan, and interpreted the results. We used an AI assistant, Claude Code (by Anthropic), to complete the research under our direction. It wrote and ran the code that collected the data, ran the analyses and simulations, and drafted text, including parts of this plan. Every script, its validation tests and its outputs are kept in the project repository. The raw price, account and holdings data are produced by third parties (Yahoo Finance, BlackRock, FINRA, the SEC, Google and the brokerages), and we use them as published.

### Step 1. Build the return panel
1. Rebuild Russell 1000 membership for every trading day from archived iShares IWB holdings files, so that each stock enters the sample only on days it was actually in the index. This avoids survivorship bias. Holdings files that list securities by SEDOL or CUSIP codes are matched to tickers by company name.
2. Download daily adjusted closing prices for all 2,019 tickers that were ever members. Repair renamed tickers (for example FB → META) by matching price histories, so a company's history is not cut off when its symbol changes. Members with no price data available, mostly delisted companies (542 tickers, about 27%), are recorded as a documented limitation; a recovery check on the 71 we could find elsewhere showed only a small effect.
3. Compute daily simple returns. No minimum price filter is applied, because split-adjusted prices make large companies (for example NVIDIA in 2016) look like penny stocks, and index membership already excludes true penny stocks.
4. Winsorize returns at the 0.1 and 99.9 percentiles, pooled across all days (the primary pipeline). As a robustness check, also winsorize each day separately at that day's own percentiles. Step 7 shows that pooled clipping changes the dispersion measure on big-move days.
5. Compute the equal-weighted market return each day as the cross-sectional mean. The final panel has 2,260,838 stock-days across 1,280 stocks and 2,678 trading days (January 5, 2016 to August 28, 2026), with 685 to 1,011 stocks per day.

### Step 2. Compute the herding measures
For each trading day, calculate the cross sectional absolute deviation (Chang, Cheng and Khorana, 2000):

CSAD_t = (1/N_t) × Σ_i |R_i,t − R_m,t|

Under standard asset pricing with no herding, CSAD rises roughly in line with the size of the market move; herding makes it flatten or fall on big-move days. We also compute the Wang and Hudson (2024) signed version, SCSAD_t = +CSAD_t on days when R_m,t > 0 and −CSAD_t when R_m,t < 0, used in their regression SCSAD_t = α + γ1·R_m,t + γ2·R_m,t² + γ3·R_m,t³, where a negative γ3 indicates herding.

We do not compute the Christie and Huang (1995) standard deviation measure or the rolling pairwise correlation. Question 2 already compares two herding tests in depth, the Christie-Huang measure is the earlier and less powerful form of the same idea, and the pairwise correlation has no no-herding benchmark in our framework.

### Step 3. Build the new investor entry index
1. Collect four entry proxies: weekly Google Trends volume for beginner investing queries, Interactive Brokers monthly net new accounts, and Robinhood and Schwab quarterly funded accounts.
2. Convert each source to a growth rate, so that sources measured in different units are on a common scale.
3. Standardize each series to a z-score using only data available up to that date, so the index never uses future information.
4. Average the z-scores into one weekly index and carry it forward to daily frequency. Because the brokerage series are monthly or quarterly, the index is a slow-moving regime variable, not a daily signal.
5. Define High_t as days in the top third of the index and Low_t as days in the bottom third, using cutoffs computed only from past data (expanding window). The middle third is the baseline. A continuous version of the index is also kept.
6. Robinhood's data begin at its 2020 account surge, which makes every later quarter look low, so the primary index excludes Robinhood and a version with Robinhood is run as a robustness check.

This index measures new account creation and beginner search interest, not anyone's actual financial literacy. We treat it as a proxy and say so.

### Step 4. Split stocks by retail attention
1. Score each stock on its off-exchange share of trading volume (FINRA) and the inverse of its institutional ownership (13F filings). The planned third measure, each stock's own Google Trends volume, could not be collected because Google limits the number of requests (only 23 of 184 batches completed), so we dropped it.
2. Sort stocks into high, middle and low attention thirds (and, as a check, halves).
3. Compute CSAD separately within each group, measured against the same overall market return, and regress the difference between the high and low groups on the main model's terms. This gives the high-minus-low difference in the key coefficient directly, with a standard error that accounts for both groups being observed on the same days.

### Step 5. Estimate the main model
Define Post_t = 1 on and after November 30, 2022. The main regression is:

CSAD_t = g0 + g1·|R_m,t| + g2·R_m,t² + g3·R_m,t²·Post_t + g4·R_m,t²·High_t + g5·R_m,t²·Post_t·High_t + g6·R_m,t²·Low_t + g7·R_m,t²·Post_t·Low_t + controls + e_t

- g5 is the coefficient H1 is about; H1 predicts g5 < 0.
- g7 is the matching term for low-entry periods; H2 predicts it is not negative.
- Controls. VIX, a top-decile market-move day indicator, calendar-month dummies, a linear time trend, and indicators for FOMC announcement days and CPI release days.
- The Wang-Hudson version replaces CSAD with SCSAD and R_m,t² with R_m,t³ in the interaction terms. It runs without the controls, as in their paper.
- Primary specification. Fixed before examining regression results: Robinhood excluded, growth rates, High/Low tercile dummies with the middle third as baseline, expanding-window cutoffs.
- Robustness variants. With and without Robinhood, growth rates vs raw counts, dummy vs continuous index, and expanding vs full-sample cutoffs. That gives 12 specifications per test, plus one version of the standard primary model with lower-order terms added: 25 regressions in total.

### Step 6. Is any effect specific to ChatGPT?
1. Placebo break dates. Rerun the primary model with the "ChatGPT date" moved to every month-end from June 2017 to June 2025, skipping six months on either side of the real date (85 fake dates). If the real g5 is not more extreme than 95% of the fake-date values, the effect is not specific to ChatGPT's release.
2. Calendar check. After November 2022, the entry groups fall almost entirely into separate years. So rerun the model with year fixed effects, first for the level and then also for year-specific R_m,t² slopes, and measure how much High/Low variation is left within years.
3. Plain High vs Low comparison. Compare high-entry days directly against low-entry days, with middle days dropped. This is the most direct version of H1.
4. Multiple testing. Correct the family of tests in this step with the Holm-Bonferroni method.

### Step 7. Can the herding tests be trusted? (Question 2)
1. Monte Carlo simulation. Build simulated markets that look like ours:
   - real market returns resampled in 21-day blocks;
   - stock betas and volatilities taken from real stocks;
   - five scenarios, from textbook (S1: equal betas, normal shocks) to realistic (S5: real betas, fat-tailed shocks, volatility that rises with the market move).
   - Herding is added with strength κ through R_i,t = R_m,t + (β_i·R_m,t + ε_i,t − R_m,t)·h_t, where h_t = 1/(1 + κ·R_m,t²). This pulls stocks toward the market more on big-move days; κ = 0 means no herding.
   - Run both tests on 1,000 markets for each scenario and each κ in {0, 3, 10, 30, 100, 300, 1000, 3000}, with and without winsorization. That is 80,000 simulated markets.
   - Count how often each test reports herding.
2. Check against the source. Compare our Wang-Hudson code line by line with the published paper and quote its exact specification. Build "paper-exact" versions of each test the paper proposes. Rerun the simulation with them, and rerun the paper's own simulation design. The paper's estimator is described only as "robust regression", so test both readings: OLS with heteroskedasticity-robust standard errors, and a Huber M-estimator.
3. Explain the mechanisms. On single simulated markets, plot dispersion against the market return with each test's fitted curve, to show in plain terms why a test fails when it does.
4. Simulation-calibrated test. Instead of the textbook cutoff, judge the real t-statistic against its distribution in 2,000 fresh simulated no-herding markets calibrated to our data. Validate on held-out markets, and check how much the answer depends on which scenario the simulation assumes.
5. Standard errors.
   - Compare Newey-West standard errors (5, 21, 63 and 126 lags) and a 21-day moving-block bootstrap.
   - Check each on simulated markets in which the ChatGPT-date terms are truly zero, counting how often each method calls them "significant".
   - Use the best-calibrated method for the real data.

### Step 8. Final analyses
These were pre-registered as deviations-log entry D8 and pushed to GitHub before any code was written. Each uses the primary specification, both tests, Newey-West standard errors and the 21-day block bootstrap, and has its own decision rule:
1. Effect size. Convert g5 into basis points of dispersion for a market move of 2 standard deviations, with a bootstrap 95% interval. Following the original plan, an effect smaller than 1 basis point is called economically negligible.
2. Alternative break date. Set the "ChatGPT date" to the GPT-4 release (March 14, 2023), and compare that g5 with the placebo dates from Step 6.
3. Leave out the seven largest technology companies (Apple, Microsoft, Alphabet's two share classes, Amazon, NVIDIA, Meta and Tesla), since index concentration in the AI rally can compress dispersion by itself.
4. Measure dispersion around a liquidity-weighted market return (weights are price times volume, a proxy, since true market caps are not in our data).
5. Correct the three robustness tests (items 2 to 4) together with the Holm-Bonferroni method.

Dropped, with reasons recorded in D8: an unknown-break-date (sup-Wald) test, because the placebo grid already asks whether the break is special; international markets and a GARCH volatility control, which need large new data work for little gain.

### Step 9. Documentation
- Version control. Every script, test and result is kept in a version-controlled repository with dated commits, now public at github.com/Guru-Balaji18/beginners-in-the-herd.
- Pre-registration routine. Each new analysis is written down first, in a dated addendum or a numbered deviations-log entry, and committed alone. The code is committed next, and the results last. GitHub records push times from November 19, 2026. Earlier ordering rests on the local commit history, so we describe it that way and do not present it as independently verified.
- Deviations log. Every specification run, including failed ones, and every change from the original design is recorded with its date (entries D1 to D8).
- Validation first. Each analysis has a test that injects known synthetic values and checks that the code recovers them before it touches real data.
- AI disclosure. We used an AI assistant, Claude Code, to write and run the code and to draft text, as described at the start of Procedures.

## Risk and safety

The only risk is extended screen and keyboard time, so we take breaks during long sessions. There is no chemical, biological, radiological, mechanical or electrical hazard, and nothing needs disposal.

This study involves no human participants. We do not recruit, survey, interview or observe anyone. Every data series is aggregated market data or publicly filed corporate disclosure, and Google Trends returns only anonymized aggregate indices. No personally identifiable information is collected. If we later decided to survey investors, that would be human participant research and would need Scientific Review Committee or Institutional Review Board approval before any data collection.

Code, documentation and results are stored in a public GitHub repository; raw downloaded data are kept locally and not redistributed. Automated requests to SEC EDGAR identify the project with a contact email, as the SEC requires.

Forms we expect to submit: Checklist for Adult Sponsor (1), Student Checklist (1A), this Research Plan, Approval Form (1B), and the Abstract form after experimentation.

## Data analysis

**Question 1**
- Estimation. Ordinary least squares on daily data with Newey-West standard errors at five lags.
- Primary test. A one-sided t-test on g5 against zero at α = 0.05, reporting the estimate, standard error, t-statistic and p-value together.
- Robustness. The same test with block-bootstrap standard errors, and with the simulation-calibrated p-value from Step 7.
- Placebo decision rule. The empirical p-value is the share of fake dates whose g5 is at least as negative as the real one. If it is above 0.05, the effect is not specific to ChatGPT's release.
- Calendar decision rule. If g5 is not negative and significant once year-specific slopes are included, the result is attributed to differences between years rather than between investor types.
- H3. The high-minus-low attention difference in g5, with its standard error, from the difference regression.
- Multiple comparisons. Holm-Bonferroni across the family of decision tests; we report both raw and adjusted p-values. All 25 regressions are reported, not just the significant ones.
- Effect size. See Step 8.

**Question 2**
- Size. The share of no-herding markets (κ = 0) in which a test reports herding, using a one-sided 5% rule (t below −1.645). With 1,000 markets the Monte Carlo standard error is about 0.7 percentage points, so a test is:
  - well-sized between 3.6% and 6.4%;
  - over-rejecting above 6.4%;
  - conservative below 3.6%.
  We report each rate with a 95% Wilson interval.
- Power. The detection rate at each κ > 0, plotted as a power curve.
- Matching reality. We find the simulated scenario and herding strength whose typical t-statistics are closest to the real ones, and we report where the real t-statistic falls in each scenario's no-herding distribution.
- Calibrated test. The calibrated p-value is the share of simulated no-herding t-statistics at or below the real one. We check its size on held-out markets, including markets from scenarios other than the one the null was built from.

Visualizations planned for the board:
- the entry index over time, with High/Low periods, the ChatGPT date and the surges marked;
- dispersion against market return, before vs after ChatGPT;
- a forest plot of g5 across specifications;
- the H3 high/low comparison;
- the false-alarm rates of each test;
- the Wang-Hudson jump diagram;
- the placebo histogram;
- a pipeline diagram.

## Bibliography

- Barber, B. M., and Odean, T. (2008). All that glitters: The effect of attention and news on the buying behavior of individual and institutional investors. *The Review of Financial Studies*, 21(2), 785–818.
- Bikhchandani, S., and Sharma, S. (2001). Herd behavior in financial markets. *IMF Staff Papers*, 47(3), 279–310.
- Chang, E. C., Cheng, J. W., and Khorana, A. (2000). An examination of herd behavior in equity markets: An international perspective. *Journal of Banking and Finance*, 24(10), 1651–1679.
- Cheng, Q., Lin, P., and Zhao, Y. (2025). Does generative AI facilitate investor trading? Early evidence from ChatGPT outages. *Journal of Accounting and Economics*, 80(2). doi:10.1016/j.jacceco.2025.101821
- Christie, W. G., and Huang, R. D. (1995). Following the pied piper: Do individual returns herd around the market? *Financial Analysts Journal*, 51(4), 31–37.
- Da, Z., Engelberg, J., and Gao, P. (2011). In search of attention. *The Journal of Finance*, 66(5), 1461–1499.
- Even-Tov, O., Lourie, B., Munevar, K., and Nekrasov, A. (2025). The effect of AI on retail investor behavior: Evidence from account-level trading data. SSRN Working Paper 5778246.
- Financial Stability Board (2024). *The financial stability implications of artificial intelligence*. Basel: Financial Stability Board.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65–70.
- Huber, P. J. (1964). Robust estimation of a location parameter. *The Annals of Mathematical Statistics*, 35(1), 73–101.
- Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *The Annals of Statistics*, 17(3), 1217–1241.
- Lopez-Lira, A., and Tang, Y. (2025). Can ChatGPT forecast stock price movements? Return predictability and large language models. *Journal of Financial Economics*. SSRN Working Paper 4412788, arXiv:2304.07619.
- Newey, W. K., and West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.
- Shiller, R. J. (2015). *Irrational Exuberance* (3rd ed.). Princeton, NJ: Princeton University Press.
- Wang, J., and Hudson, R. (2024). Better ways to test for herding. *International Journal of Finance & Economics*, 29(1), 790–818. doi:10.1002/ijfe.2707
- White, H. (1980). A heteroskedasticity-consistent covariance matrix estimator and a direct test for heteroskedasticity. *Econometrica*, 48(4), 817–838.
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209–212.

