"""Machinery checks for wang_hudson_paper.py (D6). Must pass before running."""
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

import simulate_herding_tests as sim
import wang_hudson_paper as whp
import wang_hudson_variants as whv

cal = sim.load_calibration()
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


R, _ = sim.simulate_returns(cal, "S5", 0, sim.rng_for("S5", 0))

# 1. Eq.3 is our WH regression without the Post term: same point estimates on the same data
c_simple = whv.fast_csad(R, cal["dates"]).set_index("date")
X_old = pd.DataFrame({"mkt_ret": c_simple["mkt_ret"], "rm2": c_simple["mkt_ret"] ** 2, "rm3": c_simple["mkt_ret"] ** 3})
old = OLS(c_simple["scsad"], add_constant(X_old)).fit()
new = whp.hc1(c_simple["scsad"], whp.eq3_x(c_simple))
check("Eq.3 point estimates == our WH form (no Post) on the same data",
      np.allclose(new.params.values, old.params.values, rtol=1e-10))

# 2. log-return CSAD by hand
c = whp.log_csad(R, cal["dates"])
r = np.log1p(R)
m = r.mean(1)
check("log_csad == manual log-return CSAD", np.allclose(c["csad"].values, np.abs(r - m[:, None]).mean(1)))
check("SCSAD sign: + if Rm > 0, - if Rm < 0", ((c["scsad"] > 0) == (c["mkt_ret"] > 0)).all())

# 3. variant structure
v = whp.paper_variants(c)
check("all 5 variants give finite t", all(np.isfinite(v[f"{k}_t"]) for k in whp.VARIANTS))
s1 = whp.hc1(c["csad"], whp.eq2_x(c), const=False)
check("Solution 1: no constant, includes signed Rm", "const" not in s1.params.index and "rm" in s1.params.index)
check("HC1 covariance", s1.cov_type == "HC1")

# 4. real frame
g = whp.real_frame()
mk = pd.read_csv("data/market_returns_final.csv", parse_dates=["date"]).set_index("date")["mkt_ret_eq"]
cr = g["mkt_ret"].corr(mk.reindex(g.index))
check("real log-return market tracks the simple EW market (corr > 0.999)", cr > 0.999, f"corr {cr:.5f}")
check("no real day with Rm exactly 0", int((g["mkt_ret"] == 0).sum()) == 0)
print(f"\n{sum(results)}/{len(results)} checks passed")
