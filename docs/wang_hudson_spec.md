# Wang & Hudson specification check (Part E)

> **Update 2026-09-29: the paper is now available** (`wang_hudson_2022.pdf`, the CC-BY submitted
> manuscript from the Hull repository, 60 PDF pages). Sections E1 and E2 are at the end of this file.
> The sections below them are kept as written before we had the paper.

**Status (2026-09-28): nothing in this file has been verified against the paper.**

Paper: Junkai Wang & Robert Hudson, "Better ways to test for herding,"
*International Journal of Finance & Economics* 29(1), 790–818 (2024;
online 2022), DOI 10.1002/ijfe.2707.

- `docs/wang_hudson_2022.pdf` does not exist, and no copy is in the
  project folder or Downloads.
- Wiley's article page returned a bot-verification ("security
  verification") page to our automated check. We did not try to get
  around it.
- No open-access or working-paper version is listed on IDEAS/RePEc.

As pre-registered (addendum 2, Part E gate), Part E stops here. We do
**not** guess the paper's specification. No "paper-exact" or
"zero-intercept CCK" variant has been written, and steps E2–E6 have not
been run.

## Where our implementation came from

Our specification comes from this project's notes (PROJECT_CONTEXT.md,
"Wang & Hudson (2022) bias-corrected herding test"). Those notes were
written from secondary descriptions, not from the paper. The notes
themselves flag one open question: a citing paper mentioned
"suppression of intercept" in one of Wang & Hudson's modified
specifications, and we kept the intercept.

## What our code does, and the detail we cannot check

| # | Detail | What our code does | Can't verify: what the paper does | Could it cause the Part B over-rejection? |
|---|---|---|---|---|
| 1 | SCSAD definition | `build_csad.py:37`: SCSAD = +CSAD if R_m,t >= 0, else -CSAD | The exact definition, and the sign when R_m,t = 0 exactly | The R_m = 0 tie itself: no. The equal-weighted market return is never exactly 0 in our data. The **sign flip itself** creates a jump of about 2 x CSAD at R_m = 0 (addendum 1, B7). |
| 2 | Intercept | `robustness_wang_hudson.py:63` adds a constant (alpha) | Whether the intercept is kept, suppressed, or replaced (e.g. by a sign-of-R_m term) | **Possibly, yes.** Neither an intercept nor the odd powers R_m, R_m^3 can represent a jump at 0. How the paper handles the jump is the most likely difference. |
| 3 | Regressors | `robustness_wang_hudson.py:91`: R_m, R_m^2, R_m^3 (+ R_m^3 x Post) | Which powers of R_m appear, and whether an R_m^2 (even) term is included | Possibly, via the same jump. |
| 4 | Herding coefficient and sign | Coefficient on R_m^3, herding if negative | Which coefficient and sign indicate herding | Directly decides the test. |
| 5 | Standard errors | Newey-West HAC, 5 lags (`HAC_LAGS = 5`) | The paper's SE method and lag choice | Affects size, but can't explain a 100% false-alarm rate by itself. |
| 6 | Market return | Equal-weighted mean of the sample stocks | Equal- or value-weighted | Unlikely to matter for size. |
| 7 | Other proposed tests | Not implemented | Whether the paper proposes a CCK regression with the intercept constrained to zero, or other tests ("several simple alternative tests", per the abstract on IDEAS) | These would be new variants for E3. |
| 8 | Controls / Post interaction | WH version has no controls; Post (and in Step 5 High/Low) interact with R_m^3 | The paper has no ChatGPT/Post term. That part is our extension and is unaffected by the check. | No. |

## What we *can* say without the paper

- Part B found that **our** Wang-Hudson implementation says "herding"
  in 100% of simulated no-herding markets, in all five scenarios. That
  is a fact about our code.
- Whether it is also true of the published method is **unknown**. We
  must not write "the Wang-Hudson test over-rejects". The accurate
  statement is: "our implementation of the SCSAD cubic test, built from
  secondary descriptions, over-rejects."
- The most likely source is detail 2/3, the jump at R_m = 0. This is a
  hypothesis, and it is exactly what step E4 is designed to test.

## To finish Part E

Get the PDF, for example through a school, university or public
library's Wiley access, or by requesting an author copy. Save it as
`docs/wang_hudson_2022.pdf`. Steps E1–E6 then run exactly as fixed in
`docs/addendum2_2026-09-28.md`.

## Update 2026-09-29: paper-independent Part E steps (deviation D5)

**Where the paper is.** OpenAlex lists a legal open-access copy (CC-BY,
submitted version) at https://hull-repository.worktribe.com/output/4076132.
That page and Wiley both show a bot-verification page to automated
access, so a person has to open the page in a normal browser and save
the PDF as `docs/wang_hudson_2022.pdf`.

**E4: diagnosis** (`results/wh_e4_diagnosis.png`,
`results/wh_e4_diagnosis.json`). Setup: one S1, kappa = 0 market with
no herding, no winsorization.
- SCSAD jumps by 2.81 points at R_m = 0, which is 2.00 x the average
  CSAD. This is the addendum-1 B7 prediction.
- Our cubic coefficient is -202.6 (t = -5.46, "herding"). The same
  regression fitted to the step alone, with no data, gives -203.3,
  i.e. 100% of it.
- Adding a sign(R_m) regressor gives a cubic of +0.8, t = +2.49 (no
  herding).
- Sanity check: for x ~ N(0,1), the cubic coefficient of sign(x) is
  -0.133. B7 predicted about -0.13.

**Conclusion:** our implementation's false herding is caused entirely by
the jump that the sign flip creates at R_m = 0.

**E5: size/power** (`results/wh_variants_size_power.csv`,
`results/wh_variants_size_*.png`, `results/wh_variants_power_*.png`).
- Setup: the same 80,000 Part B markets. `wh_old` and `cck` reproduce
  Part B to 3e-12.
- False-alarm rate at kappa = 0:

| Variant | Status | S1 | S2 | S3 | S4 | S5 (no winsorization) | S5 (winsorized) |
|---|---|---|---|---|---|---|---|
| wh_old | our implementation | 100% | 100% | 100% | 100% | 100% | 100% |
| wh_no_intercept | unverified candidate | 100% | 100% | 100% | 100% | 100% | 100% |
| cck_zero_intercept | unverified (as described in the request) | 100% | 100% | 100% | 100% | 100% | 100% |
| wh_sign_term | our diagnostic, not the paper | 11.2% | 0.0% | 8.9% | 12.4% | 0.0% | 13.0% |
| cck (reference) | standard | 8.6% | 0.0% | 8.4% | 8.3% | 0.0% | 0.1% |

- **Removing the intercept cannot fix the WH test.** The jump is an odd
  function (it flips sign with R_m), and a constant is even, so the
  constant was never what absorbed it.
- **CCK with the intercept forced to zero false-alarms 100%.** With no
  herding, CSAD sits near 1.4% even when R_m = 0, because of
  stock-specific noise. A curve forced through zero has to rise steeply
  and then bend down to reach that level, and the downward bend reads as
  herding. The paper may define this test differently, for example on a
  different dependent variable. We can't check without the text.
- **With the jump absorbed** (wh_sign_term), the Wang-Hudson form behaves
  like CCK.
  - Size is similar: slight over-rejection when betas are equal, and
    conservative with real betas.
  - Power in S5 without winsorization is somewhat higher than CCK:
    66.5% vs 56.4% at kappa = 30, and 99.6% vs 99.8% at kappa = 100.
  - Like CCK, it collapses at kappa = 3000 (2%).

**E6 can't be decided yet.** We can't say (a), (b) or (c) until we see
how the paper defines SCSAD and the regression. Two statements hold
either way:
- our implementation's 100% false-alarm rate is an artifact of the jump
  at zero, and
- neither simple "intercept" reading of the paper fixes it.

If the paper's specification contains nothing that handles the jump, the
published method would share the flaw (outcome b). If it does, the flaw
was ours (outcome a).


---

## E1 — The paper's exact specification (quoted)

Source: `wang_hudson_2022.pdf`, the author-submitted manuscript
(CC-BY, Hull repository). Page numbers are **PDF pages of that file**,
not the journal's pages 790–818.

| # | Item | Quote | PDF page |
|---|---|---|---|
| 1 | CSAD | "CSAD_t = (1/N) Σ_{i=1..N} \|R_it − R_mt\|  (Equation 1)" | 3 |
| 2 | Standard CCK test | "CSAD_t = α + γ1 R_m,t + γ2 \|R_m,t\| + γ3 R²_m,t + ε_t  (Equation 2)" | 3 |
| 3 | CCK herding rule | "If γ3 is not significant that is taken as evidence of no herding, if γ3 is negative and significant that is evidence of herding and if γ3 is positive and significant that is evidence of anti-herding." | 3 |
| 4 | Solution 1 (no constant) | "a reasonable way to test for herding is to adopt the standard approach in the literature but constrain the constant in the regression to be zero so that the fitted line goes through the origin of the graph" | 9–10 |
| 5 | Solution 1 equation | "CSAD_t = γ1 R_m,t + γ2 \|R_m,t\| + γ3 R²_m,t + ε_t" (heading of Table 10) | 26 |
| 6 | **SCSAD definition** | "SCSAD = CSAD if R_mt > 0 / SCSAD = − CSAD if R_mt < 0" (**R_mt = 0 is not defined**) | 10 |
| 7 | Why SCSAD, near zero | "when R_mt is close to 0, in 50% of cases SCSAD will be greater than 0 and in 50% of cases it will be less than 0, so there will not be any systematic random bias related to small values of R_mt, and fitted lines will go through the origin." | 10 |
| 8 | **Solution 2 equation** | "SCSAD_t = α + γ1 R_m,t + γ2 R²_m,t + γ3 R³_m,t + μ_t  (Equation 3)" (**has an intercept**; estimated as `_cons` in Table 11) | 10, 27 |
| 9 | **Herding rule, Solution 2** | "A negative coefficient on the cubic term will indicate herding." / "we need to have a significantly negative coefficient of the cubic market return to confirm herding behaviour" | 10, 15 |
| 10 | Solution 3 | Use the standard test only on large market moves, e.g. \|R_m\| ≥ 0.5%, 5%, 10% in the simulation; ≥ 0.5%, 1%, 2%, 3% and the largest 50%, 10%, 5% of \|R_m\| in the data | 11, 16–17, 28–33 |
| 11 | **Their own no-herding simulation** | Table 1: Solution 2 (SCSAD) "Herding" 14.40%; Solution 1 (no constant) "Herding" 26.20%. Their comment: "they perhaps have a slight bias towards finding herding when it does not exist." | 15–16 |
| 12 | Simulation design | 20 stocks (betas 0.5, 0.8, 1.2, 1.5; five each), R_m from −0.5 to 0.5 in steps of 0.001 (1,001 observations), error "generated to follow the standard normal distribution", 500 simulations | 12–13 |
| 13 | **Estimator / standard errors** | "Logarithmic returns and robust regression methods are used throughout." Tables are headed "Robust Regression", report "t statistics in parentheses" and adjusted R², with stars at 10/5/1%. **The estimator is not defined further.** | 23, 25–27 |
| 14 | Significance level | "At the conventional 5% significance level" | 51 |
| 15 | Typo in the paper | "whereas a positive coefficient would indicate herding" (should read *anti-herding*) | 15 |
| 16 | **The jump at R_m = 0** | **Never discussed.** Nothing in the text mentions a jump, discontinuity or sign dummy. The paper's own Figure 5 (zero-herding SCSAD scatter) shows a visible small gap at R_m = 0. | 15 |

## E2 — Line-by-line comparison with our code

| # | Element | Paper | Ours | Same? |
|---|---|---|---|---|
| 1 | CSAD formula | Eq. 1, equal-weighted market | `build_csad.py:31-33`, equal-weighted market | **Same** |
| 2 | SCSAD sign rule | +CSAD if R_m > 0, −CSAD if R_m < 0 | `build_csad.py:37`: +CSAD if R_m ≥ 0 | Same except R_m = 0, which the paper leaves undefined; never happens in our data or simulations |
| 3 | WH regressors | α, R_m, R_m², R_m³ | `robustness_wang_hudson.py:63,91`: constant, mkt_ret, rm2, rm3 | **Same** |
| 4 | WH herding sign | γ3 < 0, "significant" | rm3 < 0 | **Same** |
| 5 | Significance rule | two-sided, "conventional 5%" | registered one-sided 5% (t < −1.645) | Differs; we report both |
| 6 | Returns | logarithmic | simple (`pct_change`) | **Differs** |
| 7 | Estimator / SE | "robust regression", undefined | OLS + Newey-West HAC, 5 lags | **Differs** (see D6) |
| 8 | Post (ChatGPT) interaction | none | `rm3_post` added | Our extension; not part of the paper's test |
| 9 | Standard CCK regressors | α, **R_m**, \|R_m\|, R_m² | constant, \|R_m\|, R_m² (`robustness_wang_hudson.py:73-78`) | **Differs**: we omit the signed R_m term |
| 10 | Solution 1 | Eq. 2 without α (incl. R_m) | our D5 `cck_zero_intercept` omitted R_m | **Differs** |
| 11 | Solution 3 | large-move subsamples | not implemented | Missing |
| 12 | Jump at R_m = 0 | not handled | not handled | **Same**: neither addresses it |

**Bottom line of E2:** our Wang-Hudson regression, Equation 3 with an
intercept and a negative cubic meaning herding, **is the paper's
Solution 2**. The only differences are the return type (log vs simple),
the standard-error method, and the one-sided vs two-sided rule. None of
these changes the point estimate's reaction to the jump at zero.
**The paper does not address the sign jump at R_m = 0**, and neither
did we.

## E5/E6 with the paper-exact variants (D6)

**Machinery.** `test_wang_hudson_paper.py` passes 8/8. In particular,
Equation 3 gives exactly the same point estimates as our WH regression
on the same data.

**E5: false alarms with no herding, 1,000 markets per cell, Part B
seeds.** One-sided 5% rule; the paper's two-sided rule gives the same
picture.

| Variant | S1 | S2 | S3 | S4 | S5 | S5 winsorized |
|---|---|---|---|---|---|---|
| **wh_paper (Solution 2, Eq. 3)** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |
| wh_old (ours) | 100% | 100% | 100% | 100% | 100% | 100% |
| **sol1_paper (Solution 1, no constant)** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |
| sol3_abs1 (Solution 3, \|R_m\| ≥ 1%) | 5.2% | 0.0% | 6.2% | 6.3% | 0.0% | 82.7% |
| sol3_top10 (Solution 3, top 10%) | 5.1% | 0.0% | 6.3% | 6.0% | 0.2% | 94.7% |
| cck_paper (Eq. 2 incl. signed R_m, HC1) | 4.9% | 0.0% | 5.7% | 3.9% | 0.0% | 0.0% |
| cck (ours, NW5) | 8.6% | 0.0% | 8.4% | 8.3% | 0.0% | 0.1% |

Unless marked winsorized, columns are without winsorization.

- Power in S5 without winsorization, at kappa = 3 / 10 / 30 / 100 / 1000 / 3000:
  - sol3_top10: 1.5% / 20.8% / 96.3% / 100% / 0.2% / 0%;
  - cck_paper: 0% / 0% / 59.9% / 99.7% / 100% / 1.7%.
- Solution 3 keeps only big-move days, which are exactly where pooled
  winsorization distorts CSAD (Part G). That is why it false-alarms
  83–95% on the winsorized pipeline.

**E6 verdict: (b). The published method also over-rejects.**
- `wh_paper`'s false-alarm rate in S5 (winsorized, kappa = 0) is 100%,
  the same as `wh_old`.
- The paper's method **does not address the sign jump at R_m = 0**. It
  leaves R_m = 0 undefined, never mentions the jump, and fits a smooth
  cubic across it (E1 items 6–9, 16).
- The Part B failure was **not** an implementation error on our side.
  The remaining differences (log returns, HC1 vs Newey-West) do not
  change the result.
- Paper-exact and old t-statistics correlate 0.69 across the 80,000
  markets; both are below -1.645 in every no-herding market.

**Why the paper's own simulation looked fine** (`results/wh_paper_replication.csv`).
We reran the paper's no-herding design: 20 stocks, R_m from -0.5 to 0.5,
500 simulations, HC1, two-sided 5%.

| Error SD | Jump at 0 ÷ range of the SCSAD line | "Herding" found |
|---|---|---|
| 1.0 (the stated "standard normal") | 4.55 | 100% |
| 0.3 | 1.37 | 100% |
| 0.1 | 0.46 | 100% |
| 0.03 | 0.14 | 100% |
| **0.01** | **0.05** | **16.6%** (paper: 14.4%) |

- The paper's 14.4% is reproduced only when the jump is about 5% of the
  vertical range of SCSAD. This matches the small gap visible in its
  Figure 5, where market moves span ±50%.
- In real daily data, market moves are about ±1–10% while CSAD is about
  1.4%. The jump is then as large as the whole SCSAD line, so the bias
  is total.

**Real data, paper-exact** (`results/real_wh_paper.json`,
`results/calibrated_paper_results.csv`). Calibrated p uses the S5 null:

| Test | Real t | Textbook one-sided p | Calibrated p |
|---|---|---|---|
| Solution 2 (base) | -7.58 | <0.0001 | 0.708 |
| Solution 1 (base) | -8.32 | <0.0001 | 0.648 |
| Solution 2 g5 (Post x High), HC1 | -2.91 | 0.002 | 0.374 |
| Solution 2 g7 (Post x Low), HC1 | -4.06 | <0.0001 | 0.226 |
| Solution 2 g5, 21-day bootstrap | -1.40 | 0.081 | — |

- Solution 3 on the registered pooled-winsorized panel: t = -2.36
  (|R_m| ≥ 1%) and -3.15 (top 10%). E5 shows a 83–95% false-alarm rate
  on that pipeline.
- Solution 3 on the per-day-winsorized panel (post-hoc, D6 note):
  t = -0.02 and -1.19, i.e. **no herding**.

## Two readings of "robust regression": both fail

The paper says only that "robust regression methods are used
throughout" (PDF p.23) and never names the estimator. It can be read two
ways, and we tested both on the same no-herding markets (Part E seeds):

| Reading | Where | Solution 2 false alarms |
|---|---|---|
| OLS with White (HC1) standard errors | D6, commit c20989a | **100%** in every scenario and pipeline |
| Huber M-estimator (statsmodels RLM, HuberT t = 1.345, MAD scale) | D7, commit d447f34 | **100%** [Wilson 95% CI 99.6–100] in S1 and S5, winsorized and unwinsorized |

Both readings give 100% under the one-sided 5% rule and under the
paper's two-sided rule. The over-rejection therefore does not depend on
which estimator the paper meant. It comes from the jump in SCSAD at
R_m = 0, which shifts every observation near zero rather than a few
outliers. The robust fit gives a more extreme median t than OLS (−29 to
−32 vs −7 to −13); see D7's post-hoc note.
