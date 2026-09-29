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
