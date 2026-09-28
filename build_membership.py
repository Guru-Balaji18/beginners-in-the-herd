"""
Step 1b: Reconstruct historical Russell 1000 membership.

Approach: iShares' Russell 1000 ETF (IWB, portfolioId=239707) publishes its
full daily holdings list, and BlackRock's fund-document API will return that
list "as of" any historical date, going back years. Since IWB's holdings ARE
the Russell 1000 (that's the whole point of the fund), a monthly time series
of "what did IWB hold on this date" is a direct, free reconstruction of
historical Russell 1000 membership -- no survivorship bias, because you're
asking "who was in the index on date X" using data published as of date X,
not today's constituent list projected backward.

This is the same idea as https://github.com/talsan/ishares, but hits
BlackRock's underlying data endpoint directly (found via the browser's
network tab on the live product page) rather than the older iShares.com
AJAX route or a paid scraping proxy -- both of which returned the SPA's HTML
shell instead of data when tested in Sept 2026.

Endpoint (empirically confirmed working, no auth/cookies required):
    https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document
    ?appType=PRODUCT_PAGE&appSubType=ISHARES&targetSite=us-ishares&locale=en_US
    &portfolioId=239707&userType=individual&asOfDate=YYYYMMDD&component=holdings
Returns a CSV: a handful of fund-summary header lines, then one row per
holding (Ticker, Name, Sector, Asset Class, ..., Weight (%), ...), then a
few in-scope index-futures overlay rows at the bottom.

DATA AVAILABILITY (empirically probed, see probe_coverage() below):
  - No data at all before 2006 (fund inception was May 2000, but online
    holdings history doesn't reach that far back).
  - 2006-10 through ~2012-12: sparse and irregular. Isolated month-end
    snapshots exist, but most months in this window return empty, and
    there's no clean pattern to which ones work. NOT reliable for building
    a clean monthly series.
  - 2013-01 onward: every month-end trading day snapshot tested returned
    real data, as did arbitrary non-month-end business days. Reliable.
  - This comfortably covers the study's required 2016-2026 window with
    ~3 years of margin, so RELIABLE_START below is set to 2013-01-31
    rather than forced to 2016.
  - KNOWN GAP: 2017-01-01 through 2017-07-09 has NO snapshots at all
    (confirmed by probing weekly, not just the month-end fallback dates --
    this is a real hole in BlackRock's archive, not a fetch failure). Every
    month in this window is silently skipped rather than recorded as
    "no tickers present". The consequence: a ticker whose Russell 1000
    membership actually started or ended somewhere in this 6-month window
    will show a start/end date on the wrong side of the gap (rounded to
    the nearest surviving snapshot, Dec 2016 or Jul 2017), and a ticker
    that both joined AND left within the gap won't appear at all. This
    only matters for stocks near a membership boundary during H1 2017 --
    worth flagging in the paper as a limitation, not worth blocking on.
"""
import io
import time
from datetime import date

import pandas as pd
import requests
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessMonthEnd
from pathlib import Path

OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)

PORTFOLIO_ID = "239707"   # IWB - iShares Russell 1000 ETF
BASE_URL = ("https://www.blackrock.com/varnish-api/blk-one01-product-data/"
            "product-data/api/v1/get-fund-document")

# Empirically confirmed reliable window (see probe_coverage()). Data exists
# sporadically back to 2006-10, but is too gappy to trust before this.
RELIABLE_START = "2013-01-31"
END_DATE = pd.Timestamp.today().normalize()

# Sentinel for "still a member as of the most recent snapshot we pulled" --
# far in the future so apply_membership_filter() in build_panel.py never
# truncates a currently-active ticker just because this file wasn't rerun
# recently or build_panel.py's own end date moves.
STILL_ACTIVE_SENTINEL = pd.Timestamp("2099-12-31")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Referer": "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf",
    "Accept": "text/csv,application/json,*/*",
}


# ---------------------------------------------------------------
# Fetch + parse one snapshot
# ---------------------------------------------------------------
def fetch_holdings_csv(as_of_date, session, max_retries=3):
    """Fetch the raw CSV text for one asOfDate (YYYYMMDD str). Returns the
    text, or None on repeated failure / non-200."""
    params = {
        "appType": "PRODUCT_PAGE", "appSubType": "ISHARES", "targetSite": "us-ishares",
        "locale": "en_US", "portfolioId": PORTFOLIO_ID, "userType": "individual",
        "asOfDate": as_of_date, "component": "holdings",
    }
    for attempt in range(max_retries):
        try:
            r = session.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))  # backoff
    return None


def parse_holdings_csv(text):
    """Parse one holdings CSV into a DataFrame[ticker, name, weight_pct].
    Returns None if this snapshot has no real holdings data (BlackRock
    returns a header-only CSV with 'Fund Holdings as of' = '-' for dates
    it has nothing for, instead of a 404)."""
    if text is None:
        return None
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Ticker,Name,Sector,Asset Class"):
            header_idx = i
            break
    if header_idx is None or header_idx + 1 >= len(lines):
        return None  # no holdings table at all -> empty/invalid snapshot

    body = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(body))
    if df.empty:
        return None

    # Keep real equity holdings only: drop cash placeholders (ticker "-")
    # and the index-futures overlay rows at the bottom of the file.
    df = df[(df["Asset Class"] == "Equity") & (df["Ticker"] != "-") & df["Ticker"].notna()]
    if df.empty:
        return None

    df["Weight (%)"] = pd.to_numeric(df["Weight (%)"], errors="coerce")
    df = df[["Ticker", "Name", "Weight (%)"]].rename(
        columns={"Ticker": "ticker", "Name": "name", "Weight (%)": "weight_pct"})

    # Older snapshots (2013 through part of 2014) append a footnote "*" to
    # some tickers (e.g. "AAPL*", "WFC*", "FB*") -- BlackRock's own
    # disclosure marker, not part of the ticker. Strip it so these don't
    # get treated as separate securities from their un-starred rows in
    # later snapshots. NOTE: other rare suffixes like "RXO WI" (when-issued),
    # "MRP-W" (warrants), "BF/B" (share class) are left as-is -- those are
    # genuinely distinct/temporary security types, not the same ticker.
    df["ticker"] = df["ticker"].str.strip().str.rstrip("*")
    return df


# ---------------------------------------------------------------
# Coverage probe (documents the DATA AVAILABILITY claims above)
# ---------------------------------------------------------------
def probe_coverage(session):
    """Quick empirical check that our reliable-window assumption still
    holds, and reports the widest range actually observed. Not exhaustive
    (that was done interactively while building this script) -- just a
    fast sanity check so a silent BlackRock data-retention change doesn't
    go unnoticed."""
    print("Probing data availability...")
    probe_dates = {
        "2005-12-30": "expect EMPTY (before any known coverage)",
        "2006-10-31": "expect real data (earliest isolated hit found)",
        "2012-01-31": "hit-or-miss pre-2013 (this one happens to hit)",
        "2013-01-31": "expect real data (RELIABLE_START)",
        "2016-01-04": "expect real data (study needs this)",
    }
    for d, note in probe_dates.items():
        txt = fetch_holdings_csv(d.replace("-", ""), session, max_retries=2)
        parsed = parse_holdings_csv(txt)
        n = 0 if parsed is None else len(parsed)
        print(f"  {d}: {n:4d} holdings  ({note})")
        time.sleep(0.3)
    print()


# ---------------------------------------------------------------
# Build monthly snapshot presence matrix
# ---------------------------------------------------------------
def monthly_snapshot_dates(start, end):
    cal = USFederalHolidayCalendar()
    cbme = CustomBusinessMonthEnd(calendar=cal)
    return pd.date_range(start, end, freq=cbme)


def pull_all_snapshots(start=RELIABLE_START, end=END_DATE):
    session = requests.Session()
    dates = monthly_snapshot_dates(start, end)
    print(f"Pulling {len(dates)} monthly snapshots from {dates[0].date()} to {dates[-1].date()}...")

    frames = []
    n_failed = 0
    for d in dates:
        yyyymmdd = d.strftime("%Y%m%d")
        txt = fetch_holdings_csv(yyyymmdd, session)
        parsed = parse_holdings_csv(txt)
        if parsed is None:
            # Retry falling back a few business days earlier in case this
            # exact date's snapshot is missing (seen occasionally pre-2013;
            # kept here as a safety net even inside the "reliable" window).
            fallback_found = False
            for back in range(1, 6):
                alt = (d - pd.tseries.offsets.BDay(back)).strftime("%Y%m%d")
                txt = fetch_holdings_csv(alt, session, max_retries=2)
                parsed = parse_holdings_csv(txt)
                if parsed is not None:
                    print(f"  {d.date()}: no snapshot, using {alt} instead")
                    fallback_found = True
                    break
                time.sleep(0.3)
            if not fallback_found:
                print(f"  WARNING: no snapshot found near {d.date()} even after fallback, skipping month")
                n_failed += 1
                continue
        parsed = parsed.copy()
        parsed["snapshot_date"] = d
        frames.append(parsed)
        time.sleep(0.4)  # polite throttle

    if n_failed:
        print(f"  {n_failed} month(s) skipped entirely (no snapshot found)")
    all_holdings = pd.concat(frames, ignore_index=True)
    return all_holdings


def resolve_alternate_ticker_codes(all_holdings, early_cutoff="2014-04-30"):
    """Snapshots through ~2014-04 sometimes report a non-standard identifier
    in the Ticker column instead of the real exchange ticker -- e.g. "8686"
    for AFLAC, "2BH" for HCA Healthcare, "USX1" for US Steel (SEDOL/CUSIP-
    style codes), but also plain company-name fragments like "VISA" for
    Visa Inc (real ticker "V") -- so this ISN'T just a digit-vs-letter
    pattern; a digit-only heuristic (an earlier version of this function)
    missed "VISA". Left alone, each one becomes its own phantom "ticker"
    in the membership table, splitting the real company's history the same
    way the "AAPL*" footnote issue did (see parse_holdings_csv).

    Fix: for snapshots on/before `early_cutoff` (the window where this
    behavior has been observed), compare each row's ticker against the
    DOMINANT ticker used for that EXACT company name string across
    post-cutoff ("clean era") snapshots. If they differ, remap to the
    dominant one.

    Deliberately uses an exact `name` match, NOT a normalized/fuzzy one.
    A normalized-name version of this (stripping "INC", "CLASS A", etc.)
    was tried and reverted: it correctly caught a few more cases like
    VISA, but also silently collided genuinely different securities that
    happen to share a stripped-down name -- e.g. "ALPHABET INC CLASS A"
    and "ALPHABET INC CLASS C" both normalize to "ALPHABET", but GOOGL and
    GOOG are separately-traded share classes, not the same ticker; same
    problem for FOXA/FOX, DISCA/DISCK, BF.A/BF.B. Worse, "GANNETT CO INC"
    (ticker TGNA) and "GANNETT INC" (ticker GCI) normalize to the same
    "GANNETT" despite being two DIFFERENT companies from Gannett's 2015
    corporate split -- that would have silently merged two unrelated
    companies' membership histories. Given that risk, a residual few
    exact-match misses (like VISA, whose early name "VISA INC" doesn't
    exact-match its later "VISA INC CLASS A") are left unresolved rather
    than fixed, and reported below.
    """
    early_cutoff = pd.Timestamp(early_cutoff)
    is_early = all_holdings["snapshot_date"] <= early_cutoff

    # Dominant ticker per name computed ONLY from post-cutoff ("clean era")
    # rows -- never from the early window itself. A name with a roughly
    # even split of early/late occurrences (e.g. it left the index shortly
    # after the cutoff) could otherwise tie and pick the buggy code as
    # "dominant" via value_counts().idxmax()'s arbitrary tie-break.
    clean_era = all_holdings[~is_early]
    dominant_ticker = clean_era.groupby("name")["ticker"].agg(lambda s: s.value_counts().idxmax())
    resolved_ticker = all_holdings["name"].map(dominant_ticker)

    needs_fix = is_early & (all_holdings["ticker"] != resolved_ticker) & resolved_ticker.notna()
    # Unresolved: an early-window row whose name never appears in any
    # post-cutoff ("clean era") snapshot at all -- e.g. acquired/renamed
    # before the clean-ticker era started, so there's nothing to match
    # against. Only worth reporting when the ticker actually looks like
    # one of these leaked alt-codes (contains a digit) rather than every
    # ordinary early-and-delisted-by-cutoff company.
    truly_unresolved = all_holdings.loc[
        is_early & resolved_ticker.isna()
        & all_holdings["ticker"].str.contains(r"[0-9]", regex=True),
        ["ticker", "name"]
    ].drop_duplicates()

    n_resolved_rows = needs_fix.sum()
    if n_resolved_rows:
        n_tickers = all_holdings.loc[needs_fix, "ticker"].nunique()
        print(f"  Resolved {n_resolved_rows} rows ({n_tickers} alternate-code tickers) "
              f"to their real ticker via name match")
    if len(truly_unresolved):
        print(f"  {len(truly_unresolved)} alternate-code ticker(s) could not be resolved "
              f"(no clean-ticker snapshot found for that name): "
              f"{truly_unresolved.to_dict('records')}")

    all_holdings = all_holdings.copy()
    all_holdings.loc[needs_fix, "ticker"] = resolved_ticker[needs_fix]
    return all_holdings


# ---------------------------------------------------------------
# Turn monthly presence into [ticker, start_date, end_date] intervals
# ---------------------------------------------------------------
def build_membership_table(all_holdings):
    snapshot_dates = sorted(all_holdings["snapshot_date"].unique())
    presence = (all_holdings.assign(present=True)
                .pivot_table(index="snapshot_date", columns="ticker",
                             values="present", aggfunc="any", fill_value=False))
    presence = presence.reindex(snapshot_dates, fill_value=False)

    last_snapshot = snapshot_dates[-1]
    rows = []
    for ticker in presence.columns:
        series = presence[ticker]
        in_run = False
        run_start = None
        prev_date = None
        for d, is_member in series.items():
            if is_member and not in_run:
                run_start = d
                in_run = True
            elif not is_member and in_run:
                rows.append({"ticker": ticker, "start_date": run_start, "end_date": prev_date})
                in_run = False
            prev_date = d
        if in_run:
            # still a member at the last snapshot we have -> treat as
            # currently active, don't truncate at run_start's last-seen date
            end = STILL_ACTIVE_SENTINEL if run_start is not None and prev_date == last_snapshot else prev_date
            rows.append({"ticker": ticker, "start_date": run_start, "end_date": end})

    membership = pd.DataFrame(rows).sort_values(["ticker", "start_date"]).reset_index(drop=True)
    return membership


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == "__main__":
    session = requests.Session()
    probe_coverage(session)

    all_holdings = pull_all_snapshots()
    all_holdings = resolve_alternate_ticker_codes(all_holdings)
    membership = build_membership_table(all_holdings)

    all_holdings.to_csv(OUT_DIR / "iwb_monthly_holdings_raw.csv", index=False)
    membership.to_csv(OUT_DIR / "membership.csv", index=False)

    print(f"\nSaved:")
    print(f"  {OUT_DIR/'iwb_monthly_holdings_raw.csv'}  ({len(all_holdings)} rows, "
          f"{all_holdings['snapshot_date'].nunique()} snapshots)")
    print(f"  {OUT_DIR/'membership.csv'}  ({len(membership)} rows, "
          f"{membership['ticker'].nunique()} unique tickers)")
