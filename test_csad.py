"""
Test build_csad.py's CSAD/SCSAD/post-dummy logic against hand-computed
known values, same philosophy as test_panel.py.
"""
import numpy as np
import pandas as pd
from build_csad import compute_csad

print("="*70)
print("TEST 1 - CSAD matches hand-computed values, SCSAD sign follows mkt_ret")
print("="*70)
dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])

# Day 1: mkt_ret = +0.02 (positive) -> SCSAD should equal +CSAD
# Day 2: mkt_ret = -0.03 (negative) -> SCSAD should equal -CSAD
# Day 3: mkt_ret =  0.00 (exactly zero) -> convention: SCSAD = +CSAD
panel = pd.DataFrame([
    {"date": dates[0], "ticker": "A", "ret": 0.05},
    {"date": dates[0], "ticker": "B", "ret": 0.03},
    {"date": dates[0], "ticker": "C", "ret": -0.02},
    {"date": dates[1], "ticker": "A", "ret": -0.01},
    {"date": dates[1], "ticker": "B", "ret": -0.05},
    {"date": dates[1], "ticker": "C", "ret": 0.02},
    {"date": dates[2], "ticker": "A", "ret": 0.01},
    {"date": dates[2], "ticker": "B", "ret": -0.01},
    {"date": dates[2], "ticker": "C", "ret": 0.02},
])
market = pd.DataFrame([
    {"date": dates[0], "mkt_ret_eq": 0.02},
    {"date": dates[1], "mkt_ret_eq": -0.03},
    {"date": dates[2], "mkt_ret_eq": 0.00},
])

csad = compute_csad(panel, market)
print(csad[["date", "mkt_ret", "csad", "scsad"]].to_string(index=False))

expected_csad = {0: (0.03+0.01+0.04)/3, 1: (0.02+0.02+0.05)/3, 2: (0.01+0.01+0.02)/3}
expected_scsad = {0: expected_csad[0], 1: -expected_csad[1], 2: expected_csad[2]}

ok_csad = all(np.isclose(csad["csad"].iloc[i], expected_csad[i]) for i in range(3))
ok_scsad = all(np.isclose(csad["scsad"].iloc[i], expected_scsad[i]) for i in range(3))
print(f"\nCSAD matches hand-computed values: {'PASS' if ok_csad else 'FAIL'}")
print(f"SCSAD sign follows mkt_ret (incl. mkt_ret==0 case): {'PASS' if ok_scsad else 'FAIL'}")

print()
print("="*70)
print("TEST 2 - post dummy switches exactly on 2022-11-30")
print("="*70)
dates2 = pd.to_datetime(["2022-11-28", "2022-11-29", "2022-11-30", "2022-12-01"])
panel2 = pd.DataFrame({"date": np.repeat(dates2, 2), "ticker": ["A", "B"] * 4,
                        "ret": [0.01, -0.01] * 4})
market2 = pd.DataFrame({"date": dates2, "mkt_ret_eq": [0.005, 0.005, 0.005, 0.005]})
csad2 = compute_csad(panel2, market2)
print(csad2[["date", "post"]].to_string(index=False))
ok_post = list(csad2["post"]) == [0, 0, 1, 1]
print(f"\npost=0 through 2022-11-29, post=1 from 2022-11-30 onward: {'PASS' if ok_post else 'FAIL'}")

print()
print("="*70)
print("TEST 3 - CSAD is always non-negative, SCSAD magnitude always equals CSAD")
print("="*70)
rng = np.random.default_rng(1)
n_days, n_stocks = 200, 8
dates3 = pd.bdate_range("2020-01-02", periods=n_days)
rows = []
for d in dates3:
    for s in range(n_stocks):
        rows.append({"date": d, "ticker": f"S{s}", "ret": rng.normal(0, 0.02)})
panel3 = pd.DataFrame(rows)
mkt3 = panel3.groupby("date")["ret"].mean().rename("mkt_ret_eq").reset_index()
csad3 = compute_csad(panel3, mkt3)
ok_nonneg = (csad3["csad"] >= 0).all()
ok_magnitude = np.allclose(csad3["scsad"].abs(), csad3["csad"])
print(f"CSAD always >= 0 across {len(csad3)} random days: {'PASS' if ok_nonneg else 'FAIL'}")
print(f"|SCSAD| == CSAD for every day: {'PASS' if ok_magnitude else 'FAIL'}")
