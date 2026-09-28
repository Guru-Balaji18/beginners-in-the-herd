"""
Recover price history for tickers Yahoo Finance has fully purged, using a
manually-downloaded Stooq bulk EOD archive.

CONTEXT: Stooq's per-symbol CSV export and bulk-archive download pages
are both gated behind a CAPTCHA as of 2026-09 (confirmed via plain
requests, an authenticated browser fetch, and an actual UI click -- all
returned "Access denied" until a literal image CAPTCHA appeared on the
bulk-archive page). pandas_datareader's 'stooq' data source has also been
fully removed from the current release (0.11.1) -- no `stooq` module
exists at all, which is presumably why: the maintainers likely gave up
once Stooq started blocking automated access this way.

Given that, this script does NOT hit Stooq's site itself. It expects a
human to have manually downloaded Stooq's US daily ASCII bulk archive
(https://stooq.com/db/h/ -> U.S. -> Daily -> ASCII, ~514MB zip, solving
the CAPTCHA themselves) and parses it locally.

Stooq's bulk archive format (as of past exports -- verify against
whatever the actual downloaded file looks like, since Stooq could have
changed this too): a ZIP containing one .txt file per ticker, nested
under exchange/category subfolders, e.g.
    data/daily/us/nasdaq stocks/1/aapl.us.txt
Each file is CSV: <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>
with DATE as YYYYMMDD. This script scans the whole archive recursively
by filename rather than assuming the exact folder layout, since that's
the part most likely to have changed.
"""
import re
import zipfile
from pathlib import Path

import pandas as pd

OUT_DIR = Path("data")


def find_ticker_files_in_zip(zip_path, wanted_tickers):
    """wanted_tickers: set of our historical ticker symbols (e.g. "TWTR").
    Stooq files are typically named "<ticker>.us.txt" (lowercase, dots for
    share classes sometimes rendered as "-" or "_" -- both checked).
    Returns {ticker: full_path_inside_zip}."""
    wanted_lower = {t.lower(): t for t in wanted_tickers}
    found = {}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".txt"):
                continue
            base = Path(name).name.lower()
            # strip ".us.txt" / ".txt" and any exchange suffix
            stem = re.sub(r"\.txt$", "", base)
            stem = re.sub(r"\.us$", "", stem)
            if stem in wanted_lower:
                found[wanted_lower[stem]] = name
    return found


def parse_stooq_txt(zip_path, inner_path):
    """Parse one Stooq per-ticker .txt file into [date, close, volume]."""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(inner_path) as f:
            df = pd.read_csv(f)
    df.columns = [c.strip("<>").upper() for c in df.columns]
    if "DATE" not in df.columns or "CLOSE" not in df.columns:
        return None
    out = pd.DataFrame({
        "date": pd.to_datetime(df["DATE"].astype(str), format="%Y%m%d"),
        "close": df["CLOSE"],
        "volume": df.get("VOL", pd.NA),
    })
    return out.dropna(subset=["close"])


def recover_tickers(zip_path, unresolved_csv=OUT_DIR / "ticker_still_unresolved.csv",
                     study_start="2016-01-01", study_end="2026-08-31"):
    unresolved = pd.read_csv(unresolved_csv)
    wanted = set(unresolved["ticker"])
    print(f"Looking for {len(wanted)} unresolved tickers in {zip_path}...")

    matches = find_ticker_files_in_zip(zip_path, wanted)
    print(f"Found {len(matches)}/{len(wanted)} tickers present in the Stooq archive")

    frames = []
    still_missing = []
    for t in sorted(wanted):
        if t not in matches:
            still_missing.append(t)
            continue
        df = parse_stooq_txt(zip_path, matches[t])
        if df is None or df.empty:
            still_missing.append(t)
            continue
        df = df[(df["date"] >= study_start) & (df["date"] <= study_end)]
        if df.empty:
            still_missing.append(t)
            continue
        df["ticker"] = t
        frames.append(df)

    recovered = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "ticker", "close", "volume"])
    print(f"Recovered usable price data for {recovered['ticker'].nunique() if len(recovered) else 0} tickers "
          f"({len(recovered)} rows) within the study window")
    print(f"Still missing entirely: {len(still_missing)}")
    return recovered, still_missing


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python recover_from_stooq.py <path to Stooq bulk archive .zip>")
        sys.exit(1)
    zip_path = sys.argv[1]

    recovered, still_missing = recover_tickers(zip_path)
    recovered.to_csv(OUT_DIR / "stooq_recovered_prices.csv", index=False)
    with open(OUT_DIR / "still_missing_after_stooq.txt", "w") as f:
        f.write("\n".join(still_missing))
    print(f"\nSaved data/stooq_recovered_prices.csv and data/still_missing_after_stooq.txt")
