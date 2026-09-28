"""
Tests for main_regression.py and retail_attention.py against synthetic
data with known answers (same philosophy as the other test_*.py files).
Offline only.
"""
import numpy as np
import pandas as pd
from main_regression import controls_frame, design, fit, key_terms
from retail_attention import dollar_volume_share, attention_index, aggregate_13f, norm

results = []


def check(name, ok):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")


rng = np.random.default_rng(7)
n = 2500
dates = pd.bdate_range("2016-01-04", periods=n)
rm = rng.uniform(-0.04, 0.04, n)
post = (dates >= "2022-11-30").astype(int)
high = (rng.random(n) < 0.33).astype(int)
low = ((rng.random(n) < 0.5) & (high == 0)).astype(int)
idx = rng.normal(0, 1, n)
noise = rng.normal(0, 1e-6, n)
df = pd.DataFrame({"mkt_ret": rm, "post": post, "high": high, "low": low, "idx": idx}, index=dates)

print("=" * 70)
print("TEST 1 - CCK dummy model recovers known g5 (H1) and g7 (H2)")
print("=" * 70)
true = dict(abs_rm=0.3, rm2=-2.0, rm2_post=1.0, rm2_high=0.5, rm2_post_high=-8.0, rm2_low=0.2, rm2_post_low=0.7)
X = design(df, "dummy", "cck")
y = 0.01 + sum(true[k] * X[k] for k in true) + noise
res = fit(pd.Series(y, index=dates), X)
check("g5 = -8.0 recovered", np.isclose(res.params["rm2_post_high"], -8.0, atol=0.05))
check("g7 = 0.7 recovered", np.isclose(res.params["rm2_post_low"], 0.7, atol=0.05))
check("key_terms names the right columns", key_terms("dummy", "cck") == ("rm2_post_high", "rm2_post_low"))

print()
print("=" * 70)
print("TEST 2 - continuous and Wang-Hudson forms recover known g5")
print("=" * 70)
Xc = design(df, "continuous", "cck")
yc = 0.01 + 0.3 * Xc["abs_rm"] - 2 * Xc["rm2"] + 1.5 * Xc["rm2_idx"] - 4.0 * Xc["rm2_post_idx"] + noise
check("continuous g5 = -4.0", np.isclose(fit(yc, Xc).params["rm2_post_idx"], -4.0, atol=0.05))
Xw = design(df, "dummy", "wh")
yw = 0.002 + 0.9 * Xw["mkt_ret"] + 0.3 * Xw["rm2"] - 60 * Xw["rm3"] - 150 * Xw["rm3_post_high"] + noise
rw = fit(yw, Xw)
check("Wang-Hudson g5 = -150", np.isclose(rw.params["rm3_post_high"], -150, atol=1.0))
check("W-H design has no controls or |Rm|", "abs_rm" not in Xw.columns)

print()
print("=" * 70)
print("TEST 3 - H3 difference regression = difference of the two regressions")
print("=" * 70)
y_hi = 0.012 + 0.35 * X["abs_rm"] - 10 * X["rm2_post_high"] + rng.normal(0, 1e-3, n)
y_lo = 0.008 + 0.25 * X["abs_rm"] - 2 * X["rm2_post_high"] + rng.normal(0, 1e-3, n)
r_hi, r_lo, r_d = fit(pd.Series(y_hi, index=dates), X), fit(pd.Series(y_lo, index=dates), X), \
    fit(pd.Series(y_hi - y_lo, index=dates), X)
check("diff coefficient equals g5_high - g5_low exactly",
      np.isclose(r_d.params["rm2_post_high"], r_hi.params["rm2_post_high"] - r_lo.params["rm2_post_high"]))

print()
print("=" * 70)
print("TEST 4 - controls: FOMC/CPI days, month dummies, top-decile days")
print("=" * 70)
c = controls_frame(dates[:40], rm[:40], np.r_[np.nan, np.full(39, 20.0)],
                   ["2016-01-27"], ["2016-01-20", "2016-02-19"])
check("FOMC day flagged only on 2016-01-27", c["fomc"].sum() == 1 and c.loc["2016-01-27", "fomc"] == 1)
check("CPI days flagged", c["cpi"].sum() == 2)
check("Feb dummy on for Feb days only", c.loc["2016-02-01", "month_2"] == 1 and c.loc["2016-01-29", "month_2"] == 0)
check("top-decile days ~10%", c["top_decile_vol"].sum() == 4)
check("VIX forward-filled, not invented backward", np.isnan(c["vix"].iloc[0]) and c["vix"].iloc[1] == 20)

print()
print("=" * 70)
print("TEST 5 - retail attention: split-proof dollar share, signs, terciles")
print("=" * 70)
close, vol = pd.Series([100.0, 110.0]), pd.Series([1000.0, 2000.0])
s1 = dollar_volume_share(90_000, close, vol)
s2 = dollar_volume_share(90_000, close / 10, vol * 10)     # a later 10:1 split, split-adjusted both ways
check("off-exchange share unchanged by a later split", np.isclose(s1, s2) and np.isclose(s1, 90_000 / 320_000))
tick = [f"S{i}" for i in range(9)]
comp = pd.DataFrame({"finra_share": np.linspace(0.1, 0.5, 9), "gt_attention": np.linspace(0, 8, 9),
                     "inst_own": np.linspace(0.95, 0.3, 9)}, index=tick)
a = attention_index(comp)
check("higher off-exchange + search + LOWER inst. ownership = more retail",
      a["attention_index"].is_monotonic_increasing)
check("top/bottom third groups", list(a["group"]) == ["low"] * 3 + ["mid"] * 3 + ["high"] * 3)
comp2 = comp.copy(); comp2.loc["S0", ["gt_attention", "inst_own"]] = np.nan
check("fewer than 2 components -> unclassified", attention_index(comp2).loc["S0", "group"] == "unclassified")
check("ticker normalization matches FINRA's style", norm("BRK.B") == norm("BRK-B") == "BRKB")

print()
print("=" * 70)
print("TEST 6 - 13F aggregation: originals + 'new holdings', no restatements/options")
print("=" * 70)
sub = pd.DataFrame({"ACCESSION_NUMBER": ["a1", "a2", "a3", "a4"],
                    "SUBMISSIONTYPE": ["13F-HR", "13F-HR/A", "13F-HR/A", "13F-HR"],
                    "PERIODOFREPORT": ["30-SEP-2022", "30-SEP-2022", "30-SEP-2022", "30-JUN-2022"]})
cov = pd.DataFrame({"ACCESSION_NUMBER": ["a2", "a3"], "AMENDMENTTYPE": ["NEW HOLDINGS", "RESTATEMENT"]})
it = pd.DataFrame({"ACCESSION_NUMBER": ["a1", "a1", "a1", "a2", "a3", "a4"],
                   "CUSIP": ["037833100"] * 6,
                   "SSHPRNAMT": [100.0, 50.0, 30.0, 20.0, 999.0, 777.0],
                   "SSHPRNAMTTYPE": ["SH", "SH", "PRN", "SH", "SH", "SH"],
                   "PUTCALL": [np.nan, "PUT", np.nan, np.nan, np.nan, np.nan]})
check("100 (original) + 20 (new holdings) = 120", aggregate_13f(it, sub, cov).get("037833100") == 120)
from retail_attention import pick_us_ticker
xom = [{"ticker": "EXMOC", "exchCode": "CP"}, {"ticker": "EXMOC", "exchCode": "RC"}, {"ticker": "XOM_KZ", "exchCode": "KZ"},
       {"ticker": "XOM", "exchCode": "UZ"}, {"ticker": "XOM", "exchCode": "OU"}, {"ticker": "1XOMM", "exchCode": "PO"}]
check("OpenFIGI: US listing picked over more numerous foreign ones", pick_us_ticker(xom) == "XOM")
check("OpenFIGI: no US listing -> None", pick_us_ticker([{"ticker": "EXMOC", "exchCode": "CP"}]) is None)

print()
print(f"{sum(results)}/{len(results)} checks passed")
