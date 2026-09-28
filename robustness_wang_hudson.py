"""
Robustness check: Wang & Hudson (2022), "Better ways to test for herding,"
International Journal of Finance & Economics 29(1), 790-818.

WHY THIS EXISTS
Wang & Hudson show the standard Chang-Cheng-Khorana (2000) CSAD/CCK test is
biased AGAINST finding herding. The CCK test's null (no herding) implicitly
assumes stock returns follow the CAPM exactly; but real stocks carry
idiosyncratic (stock-specific) error even with zero herding, and that
idiosyncratic error makes the TRUE no-herding relationship between CSAD and
|R_m,t| convex rather than linear. The standard test can mistake that
baseline convexity for "no herding" (a false negative) or, more precisely,
needs a stronger effect than truly exists to register significance -- so a
non-finding from the standard test alone is weak evidence of no herding.

THEIR FIX
Build a SIGNED dispersion measure (SCSAD) so the regression can use odd
(sign-preserving) powers of R_m,t instead of only |R_m,t| and R_m,t^2:

    SCSAD_t =  CSAD_t   if R_m,t >= 0
             = -CSAD_t  if R_m,t <  0

    SCSAD_t = alpha + gamma1*R_m,t + gamma2*R_m,t^2 + gamma3*R_m,t^3 + mu_t

A significantly negative gamma3 indicates herding under this corrected
test -- R_m,t^3 preserves the sign of R_m,t while still capturing convexity,
which is what lets this specification separate genuine herding-driven
curvature from the baseline convexity the standard test can't distinguish.

SCOPE OF THIS SCRIPT (read before interpreting output)
This project's full main model (PROJECT_CONTEXT.md's g0..g5 three-way
interaction: Rm^2 * Post * High) needs the new-investor entry index (Step 3)
and hasn't been built yet -- Step 3, Step 4, and Step 5 are all still
outstanding. What CAN be run today, and what this script does, is the
two-way Post_t interaction (no High_t yet) on BOTH:
  (a) the standard CCK/CSAD test    -- the existing methodology
  (b) the Wang-Hudson SCSAD test    -- this robustness check
run side by side on the same data, so the two can be directly compared.
Once Step 3 lands, extend both specs below with High_t and High_t*Post_t
interactions to get the full three-way robustness comparison.

Also note: this runs on data/csad.csv, which is still built from
build_panel.py's PLACEHOLDER 10-ticker universe, not the real
membership-filtered Russell 1000 panel. Treat all numbers below as a
pipeline check, not a research finding.
"""
import numpy as np
import pandas as pd
# NOTE: import OLS/add_constant directly rather than `import statsmodels.api
# as sm` -- the top-level api module eagerly imports statsmodels' Kalman-
# filter/state-space code (for ARIMA etc.), which this machine's endpoint
# security ("Application Control policy") blocks at the DLL level. We only
# need plain OLS with HAC errors, which doesn't touch any of that.
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from pathlib import Path

OUT_DIR = Path("data")
HAC_LAGS = 5  # matches PROJECT_CONTEXT.md's stated estimation method


def _fit_hac(y, X):
    X = add_constant(X)
    model = OLS(y, X, missing="drop")
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def standard_cck_regression(csad):
    """The existing/standard test: CSAD_t = d0 + d1|Rm| + d2*Rm^2
    + d3*Rm^2*Post + e_t. Herding signal: d2 < 0 (significant).
    d3 < 0 (significant) means herding got MORE severe post-ChatGPT --
    the two-way analog of the main model's g3 term (no High_t yet)."""
    df = csad.copy()
    df["abs_rm"] = df["mkt_ret"].abs()
    df["rm2"] = df["mkt_ret"] ** 2
    df["rm2_post"] = df["rm2"] * df["post"]
    X = df[["abs_rm", "rm2", "rm2_post"]]
    res = _fit_hac(df["csad"], X)
    return res


def wang_hudson_scsad_regression(csad):
    """The robustness check: SCSAD_t = a + g1*Rm + g2*Rm^2 + g3*Rm^3
    + g4*Rm^3*Post + mu_t. Herding signal: g3 < 0 (significant).
    g4 < 0 (significant) is the corrected-test analog of the standard
    test's d3: did herding get more severe post-ChatGPT."""
    df = csad.copy()
    df["rm2"] = df["mkt_ret"] ** 2
    df["rm3"] = df["mkt_ret"] ** 3
    df["rm3_post"] = df["rm3"] * df["post"]
    X = df[["mkt_ret", "rm2", "rm3", "rm3_post"]]
    res = _fit_hac(df["scsad"], X)
    return res


def summarize(res, key_terms, label):
    print(f"\n--- {label} ---")
    for term in key_terms:
        coef = res.params[term]
        se = res.bse[term]
        p = res.pvalues[term]
        stars = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
        print(f"  {term:12s} = {coef:+.6f}  (HAC SE {se:.6f}, p={p:.4f}) {stars}")
    print(f"  n = {int(res.nobs)}, R^2 = {res.rsquared:.4f}")


if __name__ == "__main__":
    csad = pd.read_csv(OUT_DIR / "csad.csv", parse_dates=["date"])

    print("="*70)
    print("STANDARD CCK/CSAD TEST (existing methodology)")
    print("="*70)
    cck = standard_cck_regression(csad)
    summarize(cck, ["abs_rm", "rm2", "rm2_post"], "Standard CCK")
    cck_herding = cck.pvalues["rm2"] < 0.05 and cck.params["rm2"] < 0
    cck_post_shift = cck.pvalues["rm2_post"] < 0.05 and cck.params["rm2_post"] < 0
    print(f"\n  Base herding detected (d2<0, p<0.05)?      {cck_herding}")
    print(f"  Herding increased post-ChatGPT (d3<0, p<0.05)? {cck_post_shift}")

    print()
    print("="*70)
    print("WANG-HUDSON SCSAD TEST (robustness check)")
    print("="*70)
    wh = wang_hudson_scsad_regression(csad)
    summarize(wh, ["mkt_ret", "rm2", "rm3", "rm3_post"], "Wang-Hudson SCSAD")
    wh_herding = wh.pvalues["rm3"] < 0.05 and wh.params["rm3"] < 0
    wh_post_shift = wh.pvalues["rm3_post"] < 0.05 and wh.params["rm3_post"] < 0
    print(f"\n  Base herding detected (g3<0, p<0.05)?      {wh_herding}")
    print(f"  Herding increased post-ChatGPT (g4<0, p<0.05)? {wh_post_shift}")

    print()
    print("="*70)
    print("COMPARISON")
    print("="*70)
    print(f"  Standard test  -> base herding: {cck_herding}, post-ChatGPT increase: {cck_post_shift}")
    print(f"  Wang-Hudson    -> base herding: {wh_herding}, post-ChatGPT increase: {wh_post_shift}")
    if cck_herding == wh_herding and cck_post_shift == wh_post_shift:
        print("  Conclusions AGREE between standard and bias-corrected tests.")
    else:
        print("  Conclusions DIFFER -- exactly the scenario Wang & Hudson warn about:")
        print("  the standard test may be underpowered relative to the corrected one.")
