"""
Test build_panel.py's logic against synthetic data with KNOWN properties,
same validation philosophy as the LSV testing: inject known values, check
the code recovers them correctly.
"""
import numpy as np
import pandas as pd
from build_panel import clean_and_compute_returns, compute_market_returns, apply_membership_filter

rng = np.random.default_rng(0)

print("="*70)
print("TEST 1 — basic correctness: hand-built 3-stock, 5-day panel")
print("="*70)
# Stock A: steady 1% daily gains. Stock B: steady -1% losses. Stock C: flat.
dates = pd.bdate_range("2024-01-02", periods=6)
rows = []
prices = {"A": 100.0, "B": 100.0, "C": 100.0}
for d in dates:
    for t, growth in [("A", 1.01), ("B", 0.99), ("C", 1.00)]:
        rows.append({"date": d, "ticker": t, "close": prices[t], "volume": 1000})
        prices[t] *= growth
panel = pd.DataFrame(rows)
clean = clean_and_compute_returns(panel)
print(clean[["date","ticker","close","ret"]].to_string(index=False))
expected = {"A": 0.01, "B": -0.01, "C": 0.00}
ok = all(np.isclose(clean[clean.ticker==t]["ret"], v, atol=1e-9).all() for t,v in expected.items())
print(f"\nReturns match expected constants exactly: {'PASS' if ok else 'FAIL'}")

print()
print("="*70)
print("TEST 2 — dirty data gets cleaned correctly")
print("="*70)
dirty = pd.DataFrame([
    {"date": dates[0], "ticker": "X", "close": 100, "volume": 500},
    {"date": dates[1], "ticker": "X", "close": np.nan, "volume": 500},   # missing price
    {"date": dates[2], "ticker": "X", "close": 105, "volume": 0},        # zero volume
    {"date": dates[3], "ticker": "X", "close": 0.50, "volume": 500},     # low but real price (no floor - see build_panel.py note on split adjustment)
    {"date": dates[4], "ticker": "X", "close": 110, "volume": 500},
])
clean2 = clean_and_compute_returns(dirty)
print(clean2[["date","ticker","close","volume","ret"]].to_string(index=False))
print(f"\nRows surviving: {len(clean2)} (expect 2 — day1 and day3 are dropped for missing price / "
      f"zero volume; day4 (the $0.50 close) and day5 both keep a valid prior clean price to diff against)")

print()
print("="*70)
print("TEST 3 — winsorization clips extreme outliers")
print("="*70)
n = 2000
normal_rets = rng.normal(0, 0.01, n)
normal_rets[0] = 5.0    # a fake 500% return (bad data / stock split glitch)
normal_rets[1] = -0.99  # a fake -99% return
fake_panel = pd.DataFrame({
    "date": pd.bdate_range("2020-01-01", periods=n),
    "ticker": "Y",
    "close": 100 * np.cumprod(1 + normal_rets),
    "volume": 1000,
})
clean3 = clean_and_compute_returns(fake_panel)
print(f"  max return after winsorizing: {clean3['ret'].max():.4f} (should be << 5.0)")
print(f"  min return after winsorizing: {clean3['ret'].min():.4f} (should be >> -0.99)")
ok3 = clean3['ret'].max() < 1.0 and clean3['ret'].min() > -0.5
print(f"  Outliers successfully clipped: {'PASS' if ok3 else 'FAIL'}")

print()
print("="*70)
print("TEST 4 — market return aggregation (equal weighted)")
print("="*70)
# 3 stocks, one day: returns 0.10, 0.20, 0.30 -> equal weighted avg should be 0.20
d = dates[0]
mkt_panel = pd.DataFrame([
    {"date": d, "ticker": "P", "ret": 0.10, "close": 100, "volume": 100, "weight_proxy": 10000},
    {"date": d, "ticker": "Q", "ret": 0.20, "close": 100, "volume": 100, "weight_proxy": 10000},
    {"date": d, "ticker": "R", "ret": 0.30, "close": 100, "volume": 100, "weight_proxy": 10000},
])
mkt = compute_market_returns(mkt_panel)
print(mkt.to_string(index=False))
ok4 = np.isclose(mkt["mkt_ret_eq"].iloc[0], 0.20)
print(f"\nEqual-weighted market return = 0.20 as expected: {'PASS' if ok4 else 'FAIL'}")

print()
print("="*70)
print("TEST 5 — apply_membership_filter enforces survivorship-bias-safe dates")
print("="*70)
days = pd.bdate_range("2016-01-04", periods=6)  # 6 trading days
# Ticker A: a member for the whole window.
# Ticker B: only a member for days[2]-days[3] (added then dropped, like a
#           real mid-window index reconstitution).
# Ticker C: has price data in the panel but is NOT in membership.csv at all
#           (e.g. a temp/when-issued symbol build_membership.py picked up
#           that never resolves to a real, tracked constituent) -- every
#           row should be dropped.
panel5 = pd.DataFrame([
    {"date": d, "ticker": t, "close": 100.0, "volume": 500}
    for d in days for t in ["A", "B", "C"]
])
membership5 = pd.DataFrame([
    {"ticker": "A", "start_date": pd.Timestamp("2010-01-01"), "end_date": pd.Timestamp("2099-12-31")},
    {"ticker": "B", "start_date": days[2], "end_date": days[3]},
    # note: no row for ticker "D" or "C" -- D tests the "in membership but
    # never in panel" direction (should just be silently absent, no error);
    # C tests the "in panel but not in membership" direction (should be dropped)
    {"ticker": "D", "start_date": pd.Timestamp("2010-01-01"), "end_date": pd.Timestamp("2099-12-31")},
])
filtered = apply_membership_filter(panel5, membership5)
a_days = set(filtered[filtered.ticker == "A"]["date"])
b_days = set(filtered[filtered.ticker == "B"]["date"])
c_days = set(filtered[filtered.ticker == "C"]["date"])
print(f"  A present on {len(a_days)}/6 days (expect 6, full window)")
print(f"  B present on {len(b_days)}/6 days (expect 2, only days[2]-days[3])")
print(f"  C present on {len(c_days)}/6 days (expect 0, never in membership.csv)")
print(f"  'D' (in membership, never in panel) appears in output: "
      f"{'D' in set(filtered.ticker)} (expect False)")
ok5 = (len(a_days) == 6 and b_days == {days[2], days[3]} and len(c_days) == 0
       and "D" not in set(filtered.ticker))
print(f"\nMembership filter correctly bounds each ticker's dates: {'PASS' if ok5 else 'FAIL'}")
