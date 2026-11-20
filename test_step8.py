"""
Validation for step8_analyses.py (D8, pre-registered in docs/addendum4_2026-11-19_step8.md).
Must pass before any real-data run.
"""
import numpy as np
import pandas as pd

import main_regression as mr
import step8_analyses as s8

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


# 1. Effect sizes in basis points from known synthetic coefficients (CCK uses (2 sigma)^2)
params = {"rm2": -1.0, "rm2_post": 2.0, "rm2_high": 0.5, "rm2_post_high": -4.0, "rm2_low": 0.25, "rm2_post_low": -3.0}
sigma = 0.01                                       # (2 sigma)^2 = 0.0004 -> x 10,000 bp = 4
es = s8.effect_sizes(params, sigma, test="cck")
check("g5 effect = g5 x (2 sigma)^2 x 10,000", np.isclose(es["g5_bp"], -16.0), f"{es['g5_bp']}")
check("cell post/high = (g2+g3+g4+g5) x 4", np.isclose(es["cells_bp"][("post", "high")], (-1 + 2 + 0.5 - 4) * 4))
check("cell pre/middle = g2 x 4", np.isclose(es["cells_bp"][("pre", "middle")], -4.0))
check("cell post/low = (g2+g3+g6+g7) x 4", np.isclose(es["cells_bp"][("post", "low")], (-1 + 2 + 0.25 - 3) * 4))
check("post-minus-pre, high = (g3+g5) x 4", np.isclose(es["post_minus_pre_bp"]["high"], (2 - 4) * 4))
check("post-minus-pre, low = (g3+g7) x 4", np.isclose(es["post_minus_pre_bp"]["low"], (2 - 3) * 4))
wh = {k.replace("rm2", "rm3"): v for k, v in params.items()}
es_wh = s8.effect_sizes(wh, sigma, test="wh")       # (2 sigma)^3 = 8e-6 -> x 10,000 = 0.08
check("WH uses (2 sigma)^3", np.isclose(es_wh["g5_bp"], -4.0 * 0.08), f"{es_wh['g5_bp']}")

# 2. Excluding tickers and recomputing the equal-weighted market
toy = pd.DataFrame({"date": pd.to_datetime(["2020-01-02"] * 3 + ["2020-01-03"] * 3),
                    "ticker": ["AAPL", "XOM", "KO"] * 2, "ret": [0.10, 0.01, 0.03, -0.20, 0.02, 0.04]})
kept = s8.exclude_tickers(toy, ["AAPL"])
mkt = s8.ew_market(kept)
check("excluded ticker absent", "AAPL" not in set(kept["ticker"]))
check("recomputed market = manual mean of the rest",
      np.allclose(mkt.set_index("date")["mkt_ret_eq"].values, [0.02, 0.03]))
check("the 8 big-tech tickers are the pre-registered ones",
      set(s8.BIG_TECH) == {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"})

# 3. Post dummy at the GPT-4 date
idx = pd.to_datetime(["2023-03-10", "2023-03-13", "2023-03-14", "2023-03-15"])
post = s8.post_dummy(idx, s8.GPT4_DATE)
check("GPT-4 Post switches on exactly at 2023-03-14", list(post) == [0, 0, 1, 1], f"{list(post)}")

# 4. Placebo percentile: share of placebo values at or below the observed g5
check("placebo percentile", s8.placebo_percentile(-2.0, pd.Series([-3.0, -2.0, -1.0, 0.0])) == 0.5)

# 5. Real data: the full-sample primary CCK fit reproduces Step 5's primary g5 and g7
panel, market = s8.load_panel_market()
df, ctrl = s8.frames_from(panel, market[["date", "mkt_ret_eq"]])
res = s8.fit_nw5(df, ctrl, "cck")
step5 = pd.read_csv(mr.OUT_DIR / "step5_main_results.csv")
prim = step5[step5["primary"] & ~step5["variant"].str.contains("lower-order")].set_index("test")
check("full sample reproduces Step 5 primary CCK g5", np.isclose(res.params["rm2_post_high"], prim.loc["cck", "g5"]),
      f"{res.params['rm2_post_high']:.6f} vs {prim.loc['cck', 'g5']:.6f}")
check("full sample reproduces Step 5 primary CCK g7", np.isclose(res.params["rm2_post_low"], prim.loc["cck", "g7_postlow"]))
res_wh = s8.fit_nw5(df, ctrl, "wh")
check("full sample reproduces Step 5 primary WH g5", np.isclose(res_wh.params["rm3_post_high"], prim.loc["wh", "g5"]))

print(f"\n{sum(results)}/{len(results)} checks passed")
