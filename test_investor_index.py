"""
Test investor_index.py's logic against hand-built cases with known
answers, same philosophy as test_panel.py / test_csad.py. Offline only:
no network calls, only the pure parsing and index functions.
"""
import numpy as np
import pandas as pd
from investor_index import (expanding_zscore, stitch_windows, to_weekly, composite_index,
                            tercile_dummies, weekly_to_daily, parse_ibkr_text, fill_missing_months,
                            parse_schwab_row, parse_schwab_acquisitions, parse_hood_filing)

results = []


def check(name, ok):
    results.append(ok)
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")


print("=" * 70)
print("TEST 1 - expanding z-score uses only data up to t (no lookahead)")
print("=" * 70)
s = pd.Series([1.0, 2.0, 3.0, 4.0, 10.0, 6.0])
z = expanding_zscore(s, min_periods=3)
hand = (3.0 - np.mean([1, 2, 3])) / np.std([1, 2, 3], ddof=1)
check("z at t=2 matches hand calc from x_0..x_2", np.isclose(z.iloc[2], hand))
check("NaN before min_periods", z.iloc[:2].isna().all())
s2 = s.copy()
s2.iloc[4:] = [-500.0, 999.0]
z2 = expanding_zscore(s2, min_periods=3)
check("changing future values leaves z at t<=3 unchanged", np.allclose(z.iloc[2:4], z2.iloc[2:4]))

print()
print("=" * 70)
print("TEST 2 - Google Trends window stitching recovers the true shape")
print("=" * 70)
rng = np.random.default_rng(0)
weeks = pd.date_range("2011-01-02", periods=600, freq="W-SUN")
truth = pd.DataFrame({"a": 50 + 30 * np.sin(np.arange(600) / 40) + rng.normal(0, 2, 600),
                      "b": 20 + np.arange(600) / 10}, index=weeks).clip(lower=1)


def google_window(df, start, end):
    w = df.iloc[start:end]
    return (w / w.max().max() * 100).round()  # Google: 0-100 per window, integer, shared max


windows = [google_window(truth, 0, 260), google_window(truth, 200, 460), google_window(truth, 400, 600)]
stitched = stitch_windows(windows)
check("stitched covers every week exactly once", stitched.index.equals(weeks))
ratio = stitched / truth
check("stitched is proportional to truth (per-term ratio CV < 3%)",
      bool((ratio.std() / ratio.mean() < 0.03).all()))
check("correlation with truth > 0.99", bool((stitched.corrwith(truth) > 0.99).all()))
try:
    stitch_windows([google_window(truth, 0, 100), google_window(truth, 200, 300)])
    check("non-overlapping windows are rejected", False)
except ValueError:
    check("non-overlapping windows are rejected", True)

print()
print("=" * 70)
print("TEST 3 - IBKR press-release parsing across 10 years of formats")
print("=" * 70)
a = parse_ibkr_text("Ending client credit balances of $41.7 billion. 375 thousand client accounts, "
                    "15% higher than prior year and 1% higher than prior month. 374 annualized DARTs")
check("'375 thousand' era", a["accounts"] == 375_000 and a["acquired"] == 0 and a["pct_prior_month"] == 1)
b = parse_ibkr_text("1,189 thousand client accounts, including 57 thousand new accounts acquired from "
                    "Folio Investments Inc., 69% higher than prior year and 11% higher than prior month.")
check("Folio acquisition captured", b["accounts"] == 1_189_000 and b["acquired"] == 57_000
      and b["pct_prior_month"] == 11)
c = parse_ibkr_text("5.460 million client accounts, 35% higher than prior year and 3% higher than prior month.")
check("'5.460 million' era", np.isclose(c["accounts"], 5_460_000) and c["pct_prior_month"] == 3)
check("no match returns None", parse_ibkr_text("nothing relevant here") is None)

print()
print("=" * 70)
print("TEST 4 - IBKR missing month backed out from next month's growth")
print("=" * 70)
idx = pd.period_range("2020-01", "2020-05", freq="M")
levels = pd.Series([700_000, 720_000, np.nan, 806_000, 820_000.0], index=idx)
pct = pd.Series([np.nan, 3, np.nan, 11, 2.0], index=idx)
filled, how = fill_missing_months(levels, pct)
check("2020-03 = 806k / 1.11", np.isclose(filled[pd.Period("2020-03", "M")], 806_000 / 1.11))
check("fill method recorded", how[pd.Period("2020-03", "M")] == "backed_out"
      and (how.drop(pd.Period("2020-03", "M")) == "reported").all())
levels2 = pd.Series([100.0, np.nan, 400.0], index=pd.period_range("2019-01", "2019-03", freq="M"))
f2, h2 = fill_missing_months(levels2, pd.Series(np.nan, index=levels2.index))
check("falls back to log-linear interpolation", np.isclose(f2.iloc[1], 200.0) and h2.iloc[1] == "interpolated")

print()
print("=" * 70)
print("TEST 5 - Schwab table rows in every percent/footnote format seen")
print("=" * 70)
L = "New brokerage accounts (in thousands, for the quarter ended) "
cases = {
    "plain pct":        (L + "11% (9%) 254 280 274 243 229 Clients (in thousands)", [254, 280, 274, 243, 229]),
    "N/M + footnote":   (L + "(7) N&#47;M N&#47;M 15,774 592 1,652 609 433 Client accounts", [15774, 592, 1652, 609, 433]),
    "'(29) %' style":   (L + "(29) % 4 % 931 897 1,014 1,202 1,318 Client accounts", [931, 897, 1014, 1202, 1318]),
    "em dash":          (L + "— (7) % 894 960 1,042 931 897 Client accounts", [894, 960, 1042, 931, 897]),
    "'(10 %)' style":   (L + "(4) (10 %) (60 %) 203 506 205 224 225 Clients (in thousands)", [203, 506, 205, 224, 225]),
}
for name, (text, want) in cases.items():
    check(name, parse_schwab_row(text) == want)
check("active accounts row", parse_schwab_row(
    "Active brokerage accounts 140 % 106 % 29,629 14,393 14,107 12,736 12,333 Banking accounts",
    label=r"Active Brokerage Accounts", stop=r"Banking") == [29629, 14393, 14107, 12736, 12333])

print()
print("=" * 70)
print("TEST 6 - Schwab acquisition footnotes, deduped by quarter")
print("=" * 70)
foot = ("(7) Fourth quarter of 2020 includes 14.5 million new brokerage accounts related to the "
        "acquisition of TD Ameritrade. Second quarter of 2020 includes 1.1 million new brokerage accounts "
        "related to the acquisition of the assets of USAA. (5) October 2020 includes 14.5 million new "
        "brokerage accounts related to the acquisition of TD Ameritrade. May 2020 includes 1.1 million new "
        "brokerage accounts related to the acquisition of the assets of USAA. (2) September 2011 includes "
        "315,000 new brokerage accounts related to the acquisition of optionsXpress Holdings, Inc.")
acq = parse_schwab_acquisitions(foot)
want = {pd.Period("2020Q4", "Q"): 14500.0, pd.Period("2020Q2", "Q"): 1100.0, pd.Period("2011Q3", "Q"): 315.0}
check("3 events, quarterly+monthly footnotes collapse, units in thousands", acq == want)

print()
print("=" * 70)
print("TEST 7 - Robinhood 10-Q/10-K KPI rows map to the right quarters")
print("=" * 70)
tenk = "Funded Customers 22.7 23.0 23.4 ... Net Funded Customers 12.2 1.3 1.1 ... Funded Customers 22.7 23.0 23.4"
got = parse_hood_filing(tenk, "2023-12-31", "10-K")
check("10-K: last row -> Q4 of 2021/2022/2023",
      got == {pd.Period("2021Q4", "Q"): 22.7, pd.Period("2022Q4", "Q"): 23.0, pd.Period("2023Q4", "Q"): 23.4})
tenq = "Net Cumulative Funded Accounts 12.5 22.7 blah Net Cumulative Funded Accounts 18.0 22.8"
got = parse_hood_filing(tenq, "2022-03-31", "10-Q")
check("10-Q: ending row (not beginning row) used",
      got == {pd.Period("2021Q1", "Q"): 18.0, pd.Period("2022Q1", "Q"): 22.8})

print()
print("=" * 70)
print("TEST 8 - weekly mapping, compositing, terciles, daily fill")
print("=" * 70)
wk = pd.date_range("2021-01-03", "2021-04-25", freq="W-SUN")
monthly = pd.Series([1.0, 2.0, 3.0, 4.0], index=pd.period_range("2021-01", "2021-04", freq="M"))
w = to_weekly(monthly, "M", wk)
check("week of Sun 2021-01-31 (Wed = Feb 3) gets February's value", w[pd.Timestamp("2021-01-31")] == 2.0)
w_lag = to_weekly(monthly, "M", wk, lag_periods=1)
check("publication lag: February weeks get January's value", w_lag[pd.Timestamp("2021-02-07")] == 1.0)
zs = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [3.0, 2.0, np.nan]})
idx_vals, n = composite_index(zs)
check("composite averages only available components", list(idx_vals) == [2.0, 2.0, 3.0] and list(n) == [2, 1, 1])
vals = pd.Series(np.arange(1, 10, dtype=float), index=pd.date_range("2020-01-05", periods=9, freq="W-SUN"))
high, low = tercile_dummies(vals)
check("top third High, bottom third Low, never both",
      list(high) == [0, 0, 0, 0, 0, 0, 1, 1, 1] and list(low) == [1, 1, 1, 0, 0, 0, 0, 0, 0]
      and not ((high == 1) & (low == 1)).any())
growing = pd.Series(np.arange(1, 61, dtype=float), index=pd.date_range("2020-01-05", periods=60, freq="W-SUN"))
eh, el = tercile_dummies(growing, method="expanding", min_periods=10)
check("expanding terciles: NaN during burn-in, then a new high is High", eh.iloc[:9].isna().all() and eh.iloc[-1] == 1)
weekly = pd.DataFrame({"index": [1.0, 2.0]}, index=pd.DatetimeIndex(["2021-01-03", "2021-01-10"], name="week_start"))
d = weekly_to_daily(weekly, pd.to_datetime(["2021-01-08", "2021-01-09", "2021-01-11"]))
check("Friday/Saturday keep their week's value, next Monday gets the new week's",
      list(d["index"]) == [1.0, 1.0, 2.0])

print()
print(f"{sum(results)}/{len(results)} checks passed")
