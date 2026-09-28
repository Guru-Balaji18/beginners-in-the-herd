"""
Build a second version of the return panel that additionally includes
recovered price data (Stooq bulk archive, plus the 71 tickers already
recovered via Yahoo's own rename-search in verify_tickers.py Phase 2),
so it can be compared against the strict "native Yahoo data only" panel
already sitting in data/return_panel.csv.

Two extra ticker sources beyond native Yahoo, both keyed back to the
ORIGINAL historical ticker symbol (so they line up with membership.csv's
dates, not the successor company's current symbol):
  1. data/stooq_recovered_prices.csv -- from recover_from_stooq.py
  2. Yahoo rename-recoveries in data/ticker_alternate_recoveries.csv --
     these were found and verified in verify_tickers.py but never
     downloaded in full / merged into a panel. Re-downloaded here under
     the successor ticker, then relabeled to the original ticker.

Produces data/return_panel_recovered.csv / market_returns_recovered.csv
-- kept SEPARATE from data/return_panel.csv (the strict Yahoo-only
version) specifically so the two can be compared, not so one replaces
the other.
"""
import pandas as pd
import yfinance as yf
from pathlib import Path

from build_panel import (apply_membership_filter, clean_and_compute_returns,
                          compute_market_returns, download_prices_long,
                          STUDY_START, STUDY_END)

OUT_DIR = Path("data")


def download_rename_recoveries(recoveries_csv=OUT_DIR / "ticker_alternate_recoveries.csv"):
    """Download price data for the successor ticker of each Yahoo rename
    recovery, then relabel it back onto the ORIGINAL historical ticker."""
    recoveries = pd.read_csv(recoveries_csv)
    if recoveries.empty:
        return pd.DataFrame(columns=["date", "ticker", "close", "volume"])

    successor_tickers = sorted(recoveries["candidate_ticker"].unique())
    panel, failed = download_prices_long(successor_tickers, batch_size=20, pause_between_batches=1.5)
    if failed:
        print(f"  NOTE: {len(failed)} rename-successor tickers failed on redownload "
              f"(were verified working during verify_tickers.py, may be transient): {failed}")

    # relabel successor ticker -> original historical ticker
    successor_to_original = dict(zip(recoveries["candidate_ticker"], recoveries["ticker"]))
    panel = panel.copy()
    panel["ticker"] = panel["ticker"].map(successor_to_original)
    return panel


def build_recovered_panel():
    # data/return_panel.csv already has 'ret' computed -- it went through
    # clean_and_compute_returns() ONCE already. Reusing its close/volume
    # as fresh input to a SECOND clean_and_compute_returns() pass is a
    # real bug, not just redundant work: pct_change() always returns NaN
    # for the first row of each per-ticker group, and every ticker's
    # already-cleaned data starts exactly on its (correct) first trading
    # day -- so a second pass wrongly treats that genuine first day as
    # "no prior close" and drops it, silently shifting ~1,279 tickers'
    # start date forward by one day. (Caught this via the n_stocks sanity
    # check: 2016-01-05 dropped to just 20 tickers -- exactly the new
    # rename-recovered ones -- instead of ~940+.)
    #
    # Fix: keep the already-correctly-computed strict returns AS-IS, only
    # run the raw-data pipeline (membership filter + clean_and_compute_
    # returns) on the genuinely-new recovered rows, then concatenate the
    # two already-return-computed pieces. Note this does mean winsorization
    # bounds for the ~39-70 new tickers are computed on a smaller sample
    # (just those tickers) than the original 1,279-ticker bounds -- a
    # minor calibration difference, not expected to matter much given the
    # new tickers alone still contribute ~100k+ return observations.
    strict_returns = pd.read_csv(OUT_DIR / "return_panel.csv")
    strict_returns["date"] = pd.to_datetime(strict_returns["date"])

    rename_recovered = download_rename_recoveries()
    print(f"Rename-recovered: {rename_recovered['ticker'].nunique() if len(rename_recovered) else 0} tickers, "
          f"{len(rename_recovered)} rows")

    stooq_path = OUT_DIR / "stooq_recovered_prices.csv"
    if stooq_path.exists():
        stooq_recovered = pd.read_csv(stooq_path, parse_dates=["date"])
        print(f"Stooq-recovered: {stooq_recovered['ticker'].nunique() if len(stooq_recovered) else 0} tickers, "
              f"{len(stooq_recovered)} rows")
    else:
        stooq_recovered = pd.DataFrame(columns=["date", "ticker", "close", "volume"])
        print("No data/stooq_recovered_prices.csv found -- run recover_from_stooq.py first "
              "if Stooq recovery should be included. Proceeding with rename-recovery only.")

    new_raw = pd.concat([rename_recovered, stooq_recovered], ignore_index=True)
    new_raw = new_raw.drop_duplicates(subset=["date", "ticker"])
    # also exclude anything that (somehow) duplicates an already-strict ticker/date
    already_have = set(zip(strict_returns["ticker"], strict_returns["date"]))
    new_raw = new_raw[~new_raw.apply(lambda r: (r["ticker"], r["date"]) in already_have, axis=1)]

    membership_df = pd.read_csv(OUT_DIR / "membership.csv", parse_dates=["start_date", "end_date"])
    new_filtered = apply_membership_filter(new_raw, membership_df)
    new_returns = clean_and_compute_returns(new_filtered)

    panel = pd.concat([strict_returns, new_returns], ignore_index=True)
    market = compute_market_returns(panel)

    panel.to_csv(OUT_DIR / "return_panel_recovered.csv", index=False)
    market.to_csv(OUT_DIR / "market_returns_recovered.csv", index=False)
    print(f"\nSaved data/return_panel_recovered.csv ({len(panel)} rows, {panel['ticker'].nunique()} tickers)")
    print(f"Saved data/market_returns_recovered.csv ({len(market)} rows)")
    return panel, market


if __name__ == "__main__":
    build_recovered_panel()
