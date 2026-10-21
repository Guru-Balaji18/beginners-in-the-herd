"""
D7 validation (docs/deviations_log.md, pre-registered in f15b546): the
RLM estimator used for the robust reading of Wang & Hudson Solution 2
must recover known coefficients on clean data and with injected outliers,
before any simulation is run.

Model: SCSAD-like y = a + b1 R + b2 R^2 + b3 R^3 + e, fitted with
statsmodels RLM, HuberT(t = 1.345), default MAD scale, default covariance.
statsmodels.api is blocked on this machine (Windows Application Control),
so RLM and HuberT are imported from their modules directly.
"""
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.robust.norms import HuberT
from statsmodels.robust.robust_linear_model import RLM
from statsmodels.tools import add_constant

TRUE = np.array([0.002, 0.9, 3.0, -60.0])       # const, R, R^2, R^3
T, NOISE_SD = 2678, 0.0005
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


def design(R):
    return add_constant(pd.DataFrame({"rm": R, "rm2": R ** 2, "rm3": R ** 3}))


def rlm_fit(y, X):
    return RLM(y, X, M=HuberT(t=1.345)).fit()


rng = np.random.default_rng(np.random.SeedSequence([20260928, 7, 1]))
R = rng.standard_normal(T) * 0.012
X = design(R)

# 0. settings are the pre-registered ones
res0 = rlm_fit(X @ TRUE + rng.standard_normal(T) * NOISE_SD, X)
check("norm is HuberT with t = 1.345", isinstance(res0.model.M, HuberT) and res0.model.M.t == 1.345)
check("scale estimator is the default (MAD)", str(res0.fit_options["scale_est"]).lower() == "mad")
check("covariance is the default (H1)", res0.fit_options["cov"] == "H1")

# (a) exact data: recovery to numerical precision
exact = rlm_fit(X @ TRUE, X)
check("(a0) noise-free data: coefficients recovered exactly", np.allclose(exact.params.values, TRUE, rtol=1e-6, atol=1e-9),
      np.array2string(exact.params.values, precision=6))

# (a) clean data: every coefficient within 4 SE of the truth, over 50 fresh datasets
worst, cover = 0.0, []
for i in range(50):
    r = np.random.default_rng(np.random.SeedSequence([20260928, 7, 2, i]))
    Ri = r.standard_normal(T) * 0.012
    Xi = design(Ri)
    fit = rlm_fit(Xi @ TRUE + r.standard_normal(T) * NOISE_SD, Xi)
    z = (fit.params.values - TRUE) / fit.bse.values
    worst = max(worst, float(np.abs(z).max()))
    cover.append(np.abs(z) < 1.96)
cover = np.mean(cover, axis=0)
check("(a) clean data: all coefficients within 4 SE in 50/50 datasets", worst < 4, f"max |z| = {worst:.2f}")
check("(a) clean data: 95% intervals cover the truth 85-100% of the time", (cover >= 0.85).all(),
      "coverage " + ", ".join(f"{c:.0%}" for c in cover))

# (b) inject a few large outliers: 1% of days shifted by +/- 40 noise SDs
r = np.random.default_rng(np.random.SeedSequence([20260928, 7, 3]))
y = X @ TRUE + r.standard_normal(T) * NOISE_SD
idx = r.choice(T, size=27, replace=False)
y_out = y.copy()
y_out[idx] += r.choice([-1, 1], size=27) * 40 * NOISE_SD
clean_fit, out_fit = rlm_fit(y, X), rlm_fit(y_out, X)
ols_out = OLS(y_out, X).fit()
z_rlm = (out_fit.params.values - TRUE) / clean_fit.bse.values
z_ols = (ols_out.params.values - TRUE) / clean_fit.bse.values
check("(b) with 27 outliers: RLM coefficients within 4 clean-data SE of the truth", np.abs(z_rlm).max() < 4,
      f"max |z| RLM = {np.abs(z_rlm).max():.2f}")
check("(b) RLM moves far less than OLS when outliers are injected",
      np.abs(out_fit.params.values - clean_fit.params.values).sum() < 0.25 * np.abs(ols_out.params.values - OLS(y, X).fit().params.values).sum(),
      f"max |z| OLS = {np.abs(z_ols).max():.2f}")
check("(b) outliers are down-weighted (weight < 0.2 on all 27)", (out_fit.weights[idx] < 0.2).all(),
      f"max outlier weight {out_fit.weights[idx].max():.3f}")

print(f"\n{sum(results)}/{len(results)} checks passed")
