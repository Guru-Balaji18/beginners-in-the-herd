"""
Part H: alternative standard errors for the herding regressions
(docs/addendum2_2026-09-28.md, H1). Existing code is not changed; these
functions take the same (y, X) the project's fit() takes.

  nw(y, X, lags)                 Newey-West / Bartlett HAC with `lags` maximum lags
  block_bootstrap(y, X, B, rng)  moving-block PAIRS bootstrap: rows (y_t, x_t)
                                 resampled jointly in 21-day blocks (no wrap-around,
                                 series length T); SE = SD of the bootstrap
                                 coefficients; t = coef / SE, normal p-values.

The bootstrap never refits OLS row by row. With C = running sums of
x_t x_t' and x_t y_t, each block contributes C[end] - C[start], so one
replication's X'X and X'y are sums of ~116 block terms. That gives exactly
the OLS estimate on the resampled series, just much faster.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

BLOCK = 21


class Result:
    """Minimal stand-in for a statsmodels result: params, bse, tvalues,
    pvalues (two-sided, normal), nobs."""

    def __init__(self, params, bse, nobs):
        self.params = pd.Series(params)
        self.bse = pd.Series(bse, index=self.params.index)
        self.tvalues = self.params / self.bse
        self.pvalues = pd.Series(2 * norm.sf(np.abs(self.tvalues)), index=self.params.index)
        self.nobs = nobs


def _clean(y, X):
    ok = y.notna() & X.notna().all(axis=1)
    return y[ok], add_constant(X[ok])


def nw(y, X, lags):
    y, Xc = _clean(y, X)
    return OLS(y, Xc).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def block_bootstrap(y, X, B, rng, block=BLOCK):
    names, beta_hat, draws = bootstrap_draws(y, X, B, rng, block)
    return Result(dict(zip(names, beta_hat)), draws.std(axis=0, ddof=1), len(y))


def bootstrap_draws(y, X, B, rng, block=BLOCK, chunk=50):
    y, Xc = _clean(y, X)
    Xv, yv = Xc.values.astype(float), y.values.astype(float)
    T, k = Xv.shape
    beta_hat = np.linalg.lstsq(Xv, yv, rcond=None)[0]
    Cxx = np.zeros((T + 1, k, k))
    Cxx[1:] = np.cumsum(Xv[:, :, None] * Xv[:, None, :], axis=0)
    Cxy = np.zeros((T + 1, k))
    Cxy[1:] = np.cumsum(Xv * yv[:, None], axis=0)
    nb = -(-T // block)
    lengths = np.full(nb, block)
    lengths[-1] = T - block * (nb - 1)
    draws = np.empty((B, k))
    for s in range(0, B, chunk):
        m = min(chunk, B - s)
        starts = rng.integers(0, T - block + 1, size=(m, nb))
        ends = starts + lengths[None, :]
        XtX = (Cxx[ends] - Cxx[starts]).sum(axis=1)
        Xty = (Cxy[ends] - Cxy[starts]).sum(axis=1)
        try:
            draws[s:s + m] = np.linalg.solve(XtX, Xty[..., None])[..., 0]
        except np.linalg.LinAlgError:          # a resample left a dummy column empty
            draws[s:s + m] = np.stack([np.linalg.lstsq(a, b, rcond=None)[0] for a, b in zip(XtX, Xty)])
    return list(Xc.columns), beta_hat, draws


def fit_with(method, y, X, rng=None, B=5000):
    """method: 'nw5', 'nw21', 'nw63', 'nw126' or 'boot'."""
    if method == "boot":
        return block_bootstrap(y, X, B, rng)
    return nw(y, X, int(method[2:]))
