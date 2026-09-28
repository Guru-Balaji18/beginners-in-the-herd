"""
Step 2: Compute CSAD (herding dispersion measure) and its signed variant SCSAD.

CSAD_t  = (1/N_t) * sum_i |R_i,t - R_m,t|        (Chang, Cheng & Khorana 2000)
SCSAD_t =  CSAD_t   if R_m,t >= 0
         = -CSAD_t  if R_m,t <  0                 (Wang & Hudson 2022, IJFE)

R_m,t is the equal-weighted market return (mkt_ret_eq from build_panel.py) --
the standard choice in the CCK/herding literature.

Also attaches Post_t (1 on/after 2022-11-30, the ChatGPT public release date)
since every regression this feeds (the standard CCK test and the Wang-Hudson
robustness check) needs it.
"""
import pandas as pd
from pathlib import Path

OUT_DIR = Path("data")
CHATGPT_RELEASE = pd.Timestamp("2022-11-30")


def compute_csad(panel, market):
    """panel: long [date, ticker, ret]. market: [date, mkt_ret_eq, ...].
    Returns [date, csad, scsad, mkt_ret, post] indexed by trading day."""
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])
    market = market.copy()
    market["date"] = pd.to_datetime(market["date"])

    merged = panel.merge(market[["date", "mkt_ret_eq"]], on="date", how="inner")
    merged["abs_dev"] = (merged["ret"] - merged["mkt_ret_eq"]).abs()

    csad = merged.groupby("date")["abs_dev"].mean().rename("csad").reset_index()
    csad = csad.merge(market[["date", "mkt_ret_eq"]], on="date", how="left")
    csad = csad.rename(columns={"mkt_ret_eq": "mkt_ret"})

    csad["scsad"] = csad["csad"].where(csad["mkt_ret"] >= 0, -csad["csad"])
    csad["post"] = (csad["date"] >= CHATGPT_RELEASE).astype(int)

    return csad.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    panel = pd.read_csv(OUT_DIR / "return_panel.csv")
    market = pd.read_csv(OUT_DIR / "market_returns.csv")

    csad = compute_csad(panel, market)
    csad.to_csv(OUT_DIR / "csad.csv", index=False)

    print(f"Saved {OUT_DIR/'csad.csv'} ({len(csad)} rows)")
    print(f"  date range: {csad['date'].min().date()} to {csad['date'].max().date()}")
    print(f"  post=1 days: {csad['post'].sum()} / {len(csad)}")
    print(f"  csad range: [{csad['csad'].min():.5f}, {csad['csad'].max():.5f}]")
    print(f"  scsad range: [{csad['scsad'].min():.5f}, {csad['scsad'].max():.5f}]")
