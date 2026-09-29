# Wang & Hudson specification check (Part E) — BLOCKED: paper not available

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
