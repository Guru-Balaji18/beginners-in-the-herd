"""Machinery checks for robust_se.py / se_validation.py (Part H)."""
import numpy as np
import pandas as pd
from statsmodels.tools import add_constant

import calibrated_test as ct
import main_regression as mr
import robust_se as rse
import se_validation as sv
import simulate_herding_tests as sim

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


csad, df, ctrl = sv.real_frames()
y, X = ct.primary_xy(df, ctrl, "cck")
ref = mr.fit(y, X)
got = rse.nw(y, X, 5)
check("nw(5) == project fit() on the real primary CCK", np.allclose(got.tvalues, ref.tvalues))
check("real g5 t reproduced", np.isclose(got.tvalues["rm2_post_high"], ct.real_stats()["cck_g5_t"]))

# fast bootstrap == explicit resampling of rows, replication by replication
yc, Xc = y[y.notna()], add_constant(X[y.notna()])
T = len(yc)
names, bh, draws = rse.bootstrap_draws(y, X, 3, np.random.default_rng(1))
rng = np.random.default_rng(1)
nb = -(-T // 21)
lengths = np.full(nb, 21); lengths[-1] = T - 21 * (nb - 1)
starts = rng.integers(0, T - 21 + 1, size=(3, nb))
ok = True
for b in range(3):
    idx = np.concatenate([np.arange(s, s + L) for s, L in zip(starts[b], lengths)])
    beta = np.linalg.lstsq(Xc.values[idx], yc.values[idx], rcond=None)[0]
    ok &= np.allclose(beta, draws[b], rtol=1e-6, atol=1e-8 * np.abs(beta).max())
check("fast block bootstrap == explicit row resampling (3 replications)", ok)
check("bootstrap sample length == T", lengths.sum() == T)
check("point estimate == OLS", np.allclose(bh, ref.params.values))

# i.i.d. data: bootstrap SE ~ classical SE
r = np.random.default_rng(0)
Xs = pd.DataFrame({"x": r.standard_normal(3000)})
ys = pd.Series(0.5 * Xs["x"] + r.standard_normal(3000))
b = rse.block_bootstrap(ys, Xs, 2000, np.random.default_rng(2))
check("iid data: bootstrap SE within 10% of OLS SE", abs(b.bse["x"] / (1 / np.sqrt(3000)) - 1) < 0.10,
      f"{b.bse['x']:.5f} vs {1 / np.sqrt(3000):.5f}")

# D3 regressions == the unchanged functions
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression
regs = sv.regressions(csad, df, ctrl)
check("D3 CCK regression == standard_cck_regression",
      np.isclose(rse.nw(*regs["d3_cck"], 5).tvalues["rm2_post"], standard_cck_regression(csad.reset_index()).tvalues["rm2_post"]))
check("D3 WH regression == wang_hudson_scsad_regression",
      np.isclose(rse.nw(*regs["d3_wh"], 5).tvalues["rm3_post"], wang_hudson_scsad_regression(csad.reset_index()).tvalues["rm3_post"]))
print(f"\n{sum(results)}/{len(results)} checks passed")
