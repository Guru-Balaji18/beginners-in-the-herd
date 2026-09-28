"""
Step 1: Build the return panel.
Downloads daily adjusted closes for Russell 1000 constituents, reconstructs
historical membership to avoid survivorship bias, computes daily returns,
cleans/winsorizes, and builds equal- and value-weighted market return series.

Run this on your own laptop (yfinance needs real internet access).
"""
import time
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path

OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------
# STEP 1.1 — Ticker universe
# ---------------------------------------------------------------
# Real Russell 1000 historical membership from build_membership.py
# (data/membership.csv), replacing the old 10-ticker placeholder list.
MEMBERSHIP_PATH = OUT_DIR / "membership.csv"

# Study window: 2016-01-01 through 2026-08-31, per the research plan.
# membership.csv itself is reliable back to 2013-01 (see build_membership.py),
# but there's no reason for the RETURN panel to reach back that far -- none
# of the planned robustness checks (placebo dates, pre-ChatGPT high-entry
# periods, alternative breaks) need pre-2016 prices, and starting in 2016
# roughly halves the size of an already-huge ~2,000-ticker x 10-year pull.
# membership.csv's 2013-01 start still does its job correctly for this
# window: any ticker that entered/exited the index before 2016 simply won't
# match any 2016+ panel rows in apply_membership_filter().
STUDY_START = "2016-01-01"
STUDY_END = "2026-08-31"


def load_membership_universe(path=MEMBERSHIP_PATH):
    """Load membership.csv and return (membership_df, unique_ticker_list).
    Tickers get a light sanitization: BlackRock's holdings CSV uses "/" for
    some dual-class tickers (e.g. "BF/B"), but Yahoo Finance uses "-"
    (e.g. "BF-B") -- translate so these aren't silently lost. Other odd
    entries (e.g. "RXO WI", "OXY WS WI" -- when-issued/warrant temp tickers
    from build_membership.py's monthly snapshots) are left as-is; they're
    genuinely not going to resolve on Yahoo and are expected+reported
    download failures, not a bug to work around."""
    membership_df = pd.read_csv(path, parse_dates=["start_date", "end_date"])
    membership_df["ticker"] = membership_df["ticker"].str.replace("/", "-", regex=False)
    if RENAMES_PATH.exists():
        membership_df = relabel_renamed_tickers(membership_df, pd.read_csv(RENAMES_PATH))
    tickers = sorted(membership_df["ticker"].unique())
    return membership_df, tickers


def download_prices_long(tickers, start=STUDY_START, end=STUDY_END,
                          batch_size=75, pause_between_batches=1.5, max_retries=3):
    """Download daily close/volume for a large ticker universe in batches
    and reshape straight to long format [date, ticker, close, volume].

    Batching (rather than one yf.download call for 2,000+ tickers) matters
    at this scale: Yahoo Finance rate-limits/blocks very large single
    requests, and a single giant multi-index DataFrame for ~2,000 tickers
    x 10 years is unwieldy to work with. Each batch gets its own retry
    loop with backoff for transient failures (network errors, or Yahoo
    returning an empty/rate-limited response without raising).

    Returns (panel_long_df, failed_tickers) where failed_tickers is a list
    of tickers that produced no usable data after retries, for reporting.
    """
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    print(f"Downloading {len(tickers)} tickers from {start} to {end} "
          f"in {len(batches)} batches of up to {batch_size}...")

    frames = []
    failed = []
    for bi, batch in enumerate(batches, 1):
        data = None
        for attempt in range(1, max_retries + 1):
            try:
                attempt_data = yf.download(batch, start=start, end=end, auto_adjust=True,
                                            progress=False, group_by="ticker", threads=True)
            except Exception as e:
                attempt_data = None
                print(f"  batch {bi}/{len(batches)} attempt {attempt}/{max_retries}: "
                      f"exception {e!r}")
            if attempt_data is not None and not attempt_data.empty:
                data = attempt_data
                break
            time.sleep(pause_between_batches * attempt)  # backoff
        if data is None:
            print(f"  batch {bi}/{len(batches)}: FAILED after {max_retries} attempts "
                  f"(empty/errored response), skipping {len(batch)} tickers")
            failed.extend(batch)
            continue

        n_ok = 0
        for t in batch:
            try:
                sub = data[t][["Close", "Volume"]].copy()
            except KeyError:
                failed.append(t)
                continue
            sub = sub.dropna(how="all")
            if sub.empty:
                failed.append(t)
                continue
            sub.columns = ["close", "volume"]
            sub["ticker"] = t
            sub = sub.reset_index().rename(columns={"Date": "date"})
            frames.append(sub)
            n_ok += 1
        print(f"  batch {bi}/{len(batches)}: {n_ok}/{len(batch)} tickers OK")
        time.sleep(pause_between_batches)

    panel = (pd.concat(frames, ignore_index=True) if frames
             else pd.DataFrame(columns=["date", "ticker", "close", "volume"]))
    if failed:
        print(f"\n{len(failed)} tickers failed to download: {failed}")
    return panel, failed

# ---------------------------------------------------------------
# STEP 1.2 — Membership filter (placeholder — see build_membership.py)
# ---------------------------------------------------------------
def apply_membership_filter(panel, membership_df=None):
    """
    membership_df should have columns [ticker, start_date, end_date]
    marking when each stock was actually in the Russell 1000.
    If not provided, this step is skipped (ALL history is used) —
    that is NOT survivorship-bias-safe and is a placeholder only.
    """
    if membership_df is None:
        print("  NOTE: no membership file provided — skipping survivorship "
              "bias correction. Replace with real reconstructed membership "
              "before drawing conclusions.")
        return panel
    merged = panel.merge(membership_df, on="ticker", how="inner")
    mask = (merged["date"] >= merged["start_date"]) & (merged["date"] <= merged["end_date"])
    # a ticker can have several membership rows; never let them duplicate a day
    return (merged[mask].drop(columns=["start_date", "end_date"])
            .drop_duplicates(subset=["date", "ticker"]))


RENAMES_PATH = OUT_DIR / "renames.csv"


def relabel_renamed_tickers(membership_df, renames):
    """When a company changes its ticker (FB -> META), Yahoo re-files the
    whole price history under the NEW ticker and drops the old one, so the
    old ticker's membership years would otherwise find no prices at all
    (Facebook was missing for 2016 to mid-2022). Point those membership
    rows at the new ticker so the company stays one continuous stock.
    renames: DataFrame[old, new] -- see data/renames.csv (36 renames,
    each verified by an exact price match between iShares' holdings and
    Yahoo's history on the day of the switch)."""
    m = membership_df.copy()
    m["ticker"] = m["ticker"].replace(dict(zip(renames["old"], renames["new"])))
    return m

# ---------------------------------------------------------------
# STEP 1.3 — Clean and compute returns
# ---------------------------------------------------------------
def clean_and_compute_returns(panel, winsor_lower=0.001, winsor_upper=0.999):
    # NOTE: no absolute price floor here. Yahoo Finance always retroactively
    # split-adjusts historical closes, so a stock with many splits since
    # (e.g. NVDA: 4:1 in 2021 + 10:1 in 2024 = 40x) shows a sub-$1 adjusted
    # price in its early history even though it never traded that low. A
    # fixed $ floor on adjusted prices would incorrectly drop those rows.
    # Real penny stocks are excluded structurally once the Russell 1000
    # historical membership filter (apply_membership_filter) is populated,
    # since index eligibility rules already enforce a minimum price/market
    # cap at each point in time.
    panel = panel.sort_values(["ticker", "date"]).copy()

    # Drop missing prices, zero-volume days
    n0 = len(panel)
    panel = panel.dropna(subset=["close"])
    panel = panel[panel["volume"] > 0]
    print(f"  Dropped {n0 - len(panel)} rows (missing price / zero volume)")

    # Daily simple return per ticker
    panel["ret"] = panel.groupby("ticker")["close"].pct_change()
    panel = panel.dropna(subset=["ret"])

    # Winsorize at given percentiles (cross-sectionally, per day is the
    # LSV-style approach; here we do it globally for simplicity — can be
    # switched to per-day if the plan calls for that)
    lo, hi = panel["ret"].quantile([winsor_lower, winsor_upper])
    n_before = len(panel)
    panel["ret"] = panel["ret"].clip(lower=lo, upper=hi)
    print(f"  Winsorized returns at [{winsor_lower}, {winsor_upper}] "
          f"percentiles -> bounds [{lo:.4f}, {hi:.4f}]")

    return panel

# ---------------------------------------------------------------
# STEP 1.4 — Market return series
# ---------------------------------------------------------------
def compute_market_returns(panel):
    """Equal-weighted and value-weighted (by prior-day market cap proxy
    = close*volume, a crude liquidity-weighted stand-in until real
    shares-outstanding data is added) market return per day."""
    eq = panel.groupby("date")["ret"].mean().rename("mkt_ret_eq")

    panel = panel.copy()
    panel["weight_proxy"] = panel["close"] * panel["volume"]
    panel["weighted_ret"] = panel["ret"] * panel["weight_proxy"]
    vw = (panel.groupby("date")["weighted_ret"].sum() /
          panel.groupby("date")["weight_proxy"].sum()).rename("mkt_ret_vw")

    n_stocks = panel.groupby("date")["ticker"].nunique().rename("n_stocks")

    market = pd.concat([eq, vw, n_stocks], axis=1).reset_index()
    return market

# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def patch_renames(panel_path=OUT_DIR / "return_panel.csv"):
    """Fix an already-built panel for data/renames.csv without re-downloading
    all ~2,000 tickers: rebuild each renamed company from its full Yahoo
    history under the new ticker, filtered by its combined (old + new)
    membership, clipped to the existing panel's winsorization bounds so all
    returns share one cutoff. Writes return_panel_final.csv /
    market_returns_final.csv."""
    renames = pd.read_csv(RENAMES_PATH)
    base = pd.read_csv(panel_path, parse_dates=["date"])
    lo, hi = base["ret"].min(), base["ret"].max()          # existing winsorization bounds
    membership_df, _ = load_membership_universe()           # already relabeled old -> new
    new_tickers = sorted(renames["new"].unique())

    raw, failed = download_prices_long(new_tickers, batch_size=20, pause_between_batches=1.5)
    raw["date"] = pd.to_datetime(raw["date"])
    kept = apply_membership_filter(raw, membership_df).sort_values(["ticker", "date"])
    kept = kept.dropna(subset=["close"])
    kept = kept[kept["volume"] > 0].copy()
    kept["ret"] = kept.groupby("ticker")["close"].pct_change()
    kept = kept.dropna(subset=["ret"])
    kept["ret"] = kept["ret"].clip(lo, hi)

    rebuilt = set(kept["ticker"])
    panel = pd.concat([base[~base["ticker"].isin(rebuilt)], kept[base.columns]], ignore_index=True)
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)

    dup = panel.duplicated(subset=["date", "close", "volume"], keep=False) & panel["volume"].gt(0)
    if dup.any():
        print(f"  WARNING: {int(dup.sum())} rows share an identical (date, close, volume) with another "
              f"ticker -- possible double-counted company: {sorted(panel.loc[dup, 'ticker'].unique())[:20]}")

    market = compute_market_returns(panel)
    panel.to_csv(OUT_DIR / "return_panel_final.csv", index=False)
    market.to_csv(OUT_DIR / "market_returns_final.csv", index=False)
    added = len(panel) - len(base)
    print(f"Rebuilt {len(rebuilt)} renamed tickers (failed: {failed}); net +{added} stock-days; "
          f"{panel['ticker'].nunique()} tickers, {len(panel)} rows")
    return panel, market


if __name__ == "__main__":
    import sys
    if "--patch-renames" in sys.argv:
        patch_renames()
        sys.exit(0)

    membership_df, tickers = load_membership_universe()
    print(f"Loaded {len(tickers)} unique tickers from {MEMBERSHIP_PATH}")

    panel, failed = download_prices_long(tickers)
    panel.to_csv(OUT_DIR / "return_panel_raw.csv", index=False)  # pre-filter, for debugging
    with open(OUT_DIR / "failed_tickers.txt", "w") as f:
        f.write("\n".join(failed))

    panel = apply_membership_filter(panel, membership_df)
    panel = clean_and_compute_returns(panel)
    market = compute_market_returns(panel)

    panel.to_csv(OUT_DIR / "return_panel.csv", index=False)
    market.to_csv(OUT_DIR / "market_returns.csv", index=False)

    print("\nSaved:")
    print(f"  {OUT_DIR/'return_panel.csv'}  ({len(panel)} rows)")
    print(f"  {OUT_DIR/'market_returns.csv'}  ({len(market)} rows)")
    print(f"  {OUT_DIR/'failed_tickers.txt'}  ({len(failed)} tickers)")
    print("\nPreview of market returns:")
    print(market.head())
    print("\nActive-ticker count (n_stocks) distribution:")
    print(market["n_stocks"].describe())
