# Deviations from the 2026-09-28 addendum

Each entry is committed **before** the analysis it describes is run. The
addendum itself (`docs/addendum_2026-09-28.md`, commit ed63759) is never
edited after registration.

---

## D1 — 2026-09-28: add a no-winsorization run to Part B (in addition to, not instead of, the registered run)

**What happened.** The pre-registered validation (B8,
`test_simulate_herding_tests.py`) was run before the full simulation.
S1 is the textbook scenario, with no herding (kappa = 0) and 200
simulated markets:

| Pipeline | Standard CCK: "herding" found | Wang-Hudson: "herding" found |
|---|---|---|
| winsorized, as registered | 100% (mean t = -5.90) | 100% (mean t = -9.61) |
| no winsorization | 6.5% (mean t = -0.03) | 100% (mean t = -7.44) |

Two separate problems show up:

1. **Pooled winsorization manufactures false herding.** The registered
   pipeline copies `build_panel.py`: it clips all returns at the pooled
   0.1/99.9 percentiles. On an extreme market day most stocks fall past
   that shared cutoff and get clipped to the same value, which flattens
   that day's dispersion. On the worst simulated day, 45% of stocks were
   clipped. CCK then reads the flattening as herding.
2. **Our Wang-Hudson implementation over-rejects regardless**, exactly as
   predicted in addendum B7 (the SCSAD sign flip makes a jump at
   R_m = 0).

**Deviation.** The registered winsorized run goes ahead unchanged and
stays the primary Part B result. We **add** an identical run with
winsorization switched off:
- same scenarios, kappa grid, 1,000 markets per cell, seeds and
  decision rules;
- results tagged `winsorized = False`.

Reason: with winsorization on, the simulation can't tell "which test is
right" apart from "our cleaning step distorts both tests".

**Also found in validation (reported, not changed).** The registered
sign check (B6) fails for CCK: at kappa = 3000 in S1, CCK's quadratic
coefficient is strongly **positive** (mean t = +29 unwinsorized). A
follow-up on 6 simulated markets per kappa shows why. The quadratic
term detects herding at moderate strength (mean t = -4.6 at kappa = 10,
-13.3 at kappa = 100), then flips sign at extreme strength (+5.7 at
kappa = 1000, +37.7 at kappa = 3000). By then the decline has moved into
the |R_m| term (t = -44, -124). The CCK sign convention is therefore
right, but its power is **non-monotonic** in kappa under this
data-generating process. That is reported as a result.

## D2 — 2026-09-28: post-hoc real-data check of winsorization (not in the addendum; exploratory)

D1 implies the **real** pipeline's pooled winsorization could bias the
real CCK and Wang-Hudson base-herding statistics. Before looking at any
new numbers, we define the check:

- Count, per real trading day, the share of stocks clipped at the
  pooled bounds. Report the 10 worst days.
- Recompute returns without clipping: per-ticker `pct_change` of the
  cleaned close prices in `return_panel_final.csv`, i.e. the pipeline
  minus the clip.
- Rerun `compute_csad`, `standard_cck_regression` and
  `wang_hudson_scsad_regression` unchanged, and report the base t-stats
  next to the winsorized ones.

This is labeled post-hoc and exploratory. It does not change any
registered decision rule.

## D3 — 2026-09-28: post-hoc check of the Post-interaction terms in the Part B simulation (exploratory; found after the full run)

**Why.** In every simulated market the herding strength kappa is
constant over time, so each Post interaction (R_m^2 x Post for CCK,
R_m^3 x Post for Wang-Hudson) is a **true null**. B1 put the Post dummy in
so the regression call matched the real one, but B6 wrote no decision
rule for it. This check was added after seeing the results and is
labeled exploratory. The code is `py simulate_herding_tests.py postsize`
and the output is `results/sim_post_term_size.csv`.

**Result (kappa = 0, 1,000 markets each).**

| Pipeline | Scenario | CCK Post: false alarms | CCK Post: SD of t | WH Post: false alarms | WH Post: SD of t |
|---|---|---|---|---|---|
| winsorized (registered) | S1 | 13.0% | 1.92 | 26.6% | 2.82 |
| winsorized (registered) | S5 | 14.8% | 2.02 | 34.2% | 3.23 |
| no winsorization | S1 | 7.2% | 1.17 | 35.0% | 3.23 |
| no winsorization | S5 | 11.7% | 1.67 | 37.8% | 3.32 |

At the nominal 5% level, a well-behaved t-statistic has a standard
deviation of about 1. Here it is 1.2 to 3.3. The HAC(5) standard errors
on the Post interactions are therefore too small, by a factor of about 2
for CCK and about 3 for Wang-Hudson. With 21-day blocks, a whole crisis
episode such as March 2020 can land entirely before or entirely after
the break date. That changes the Post slope far more than the HAC
standard error allows for.

**What this implies for H1 (with caveats).** The real Step 5 g5 is a
Post x **High** interaction, which the simulation doesn't contain. It
rests on fewer days, so if anything it is noisier. As a rough benchmark,
we compared the real g5 t-statistics to the simulated null
distribution of the Post t-statistics (S5, winsorized):
- CCK g5: t = -1.62. It is at the **15th** percentile of the null.
  The 5th-percentile critical value is -3.22.
- Wang-Hudson g5: t = -2.80, one-sided p = 0.003. It is at the **20th**
  percentile of the null. The 5th-percentile critical value is -7.85.

Neither real g5 is unusual compared with what these tests produce when
nothing changes at the break date. This does not change any registered
decision. Part C, the placebo break-date test, is the registered check
of the same question on real data.

## D4 — 2026-09-28: identification rule in Part C (a code fix, found on the first run)

**What happened.** On the first run of `placebo_break_dates.py`, 20
regressions returned statsmodels "rank-deficient" warnings: 10
early fake dates x 2 tests. The cause is the expanding tercile cutoffs.
Before 2018-04 there are no Low days in the pre-period, and at 2017-06-30
every pre-period day is High. That makes some regressors exact linear
combinations of others:
- Rm^2 x Post x Low duplicates Rm^2 x Low (2017-06..2018-03), so
  Post x Low (g7) is not identified at these dates;
- at 2017-06-30, Rm^2 - Rm^2 x Post - Rm^2 x High + Rm^2 x Post x High
  = 0, so g5 is not identified at that date either.

statsmodels quietly returned pseudo-inverse values for these
coefficients, which are arbitrary numbers.

**Fix.** A Post x group coefficient is reported as missing whenever one
of its four cells is empty: pre/post x in-group/not-in-group. Duplicate
columns are dropped before fitting. The empirical p and the shares are
computed over the identified dates: g5 at 84 of 85 dates, g7 at 74 of 85.

**Effect.** Negligible. The CCK empirical p moved 0.424 -> 0.429 and the
Wang-Hudson one 0.694 -> 0.702. Decisions are unchanged. The real-date
estimate (the reproduction assert) and the year-FE and plan-literal fits
were never affected.

**Figures.** The axes are zoomed to the dates from 2018-04 on. The one
2017-07-31 point, which rests on only 10 non-High pre-period days,
is drawn at the edge and noted on the chart. It is still counted in all
statistics.

## Parts E–H (addendum 2) — no deviations

- Part E stopped at its pre-registered gate, because
  `docs/wang_hudson_2022.pdf` is not available (see
  `docs/wang_hudson_spec.md`). This is the registered plan, not a
  deviation.
- Parts F, G and H ran as registered: same seeds, market counts, methods
  and decision rules. The bootstrap used B = 999 in simulation and
  B = 5,000 on real data, as registered.
- H2 needed no reduction in the number of markets.
- Extra output, not used for any decision: the H3 (retail-attention)
  results on the per-day-winsorized panel,
  `results/step5_daywins_h3_results.csv`, produced as a side effect of
  rerunning `main_regression.run`.

## D5 — 2026-09-29: finish the paper-independent parts of Part E, and close two gaps in Part G

**Part E.** Addendum 2 made all of Part E wait for the paper. The paper
still can't be read here:
- OpenAlex lists a legal open-access copy (CC-BY, submitted version) at
  https://hull-repository.worktribe.com/output/4076132;
- both that page and Wiley return a bot-verification page to automated
  access, and we don't try to get around it.

We were asked to complete Part E, so we now run every step that does
**not** need the paper:
- **E4 diagnosis, as registered:** one S1 kappa = 0 market (Part B
  seed, rep 0); SCSAD vs R_m with the fitted old curve; the jump at
  R_m = 0; the old cubic fitted to a pure step. Added diagnostic: the
  old regression plus one extra regressor, sign(R_m). If the jump at
  zero causes the false herding, this term should absorb it and the
  cubic t should move to about 0.
- **E3/E5 on variants that don't need the paper**, all on the same
  Part B markets (both pipelines, all scenarios, full kappa grid,
  1,000 per cell):
  - `wh_old`: unchanged. It must reproduce Part B exactly; this is a
    check.
  - `cck_zero_intercept`: CSAD = g1|R_m| + g2 R_m^2 + g3 R_m^2 x Post,
    no constant; herding if g2 < 0. The request describes this as
    Wang & Hudson's other fix. It is **unverified against the paper**.
  - `wh_no_intercept`: the old SCSAD cubic with the constant removed.
    This is the "suppression of intercept" mentioned by a citing paper
    (PROJECT_CONTEXT.md). It is **an unverified candidate, not
    paper-exact**.
  - `wh_sign_term`: the old SCSAD cubic plus a sign(R_m) regressor.
    **Our diagnostic, not from the paper.** It tests whether removing
    the jump fixes the size.
- Speed: this pass computes CSAD/SCSAD with numpy instead of
  `compute_csad`. Addendum 1 (B1) allows this if it matches to within
  1e-12; that is checked on simulated panels before the run.
- **E6 cannot be decided** until `wh_paper` exists. We will report which
  **candidates** are well-sized, and say explicitly that this is not
  outcome (a), (b) or (c).

**Part G.**
- `docs/mechanisms.md` is rewritten to **one paragraph per mechanism**,
  as requested. The numbers move into a table below each paragraph.
- The leftover 8.6% CCK false-alarm rate with per-day winsorization (S1)
  was left untested. We now test it: the same 1,000 S1 kappa = 0
  per-day-winsorized markets (Part B seeds), base CCK R_m^2 term, NW(5)
  vs the 21-day block bootstrap (B = 999). If the bootstrap brings the
  rate into 3.6–6.4%, the leftover is a standard-error problem.
