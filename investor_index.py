"""
Step 3: New-investor entry index -> High_t / Low_t dummies.

Components (all free, all cached under data/raw/ after the first pull):
  1. Google Trends, weekly: beginner-investing search terms (pytrends).
  2. Interactive Brokers, monthly: client accounts from IBKR's monthly
     brokerage-metrics press-release PDFs (not filed with the SEC).
  3. Schwab, quarterly: new brokerage accounts from the earnings-release
     exhibit (8-K item 2.02) on SEC EDGAR.
  4. Robinhood, quarterly: Net Cumulative Funded Accounts / Funded Customers
     from 10-Q/10-K, the 2021 IPO prospectus, and earnings releases.

Each component is converted to an organic new-investor FLOW, z-scored
using only data up to that point (expanding window), mapped onto a
weekly grid, averaged across whichever components are available that
week, and forward-filled to trading days. Top third of the weekly index
= High_t, bottom third = Low_t.

Real-data adjustments (see UPDATE notes / PROJECT_CONTEXT.md for why):
  - Acquired accounts are removed from Schwab (optionsXpress 2011-Q3,
    USAA 2020-Q2, TD Ameritrade 2020-Q4) and IBKR (Folio, Jan 2021).
  - IBKR's 3 missing monthly releases are backed out from the next
    month's reported "% higher than prior month".
  - Google Trends is only weekly for windows <= 5 years, so overlapping
    windows are chain-rescaled onto one scale.
  - component_mode="growth" (default) divides each firm's flow by its
    existing account base. Raw counts trend up with firm size (IBKR's
    growth, Schwab absorbing TD Ameritrade), which would make "high
    entry" line up mechanically with the late, post-ChatGPT sample.
"""
import html
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT_DIR = Path("data")
RAW_DIR = OUT_DIR / "raw"

SEC_HEADERS = {"User-Agent": "StemFair herding research namadev.balaji18@gmail.com"}
WEB_HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")}

STUDY_START, STUDY_END = "2016-01-01", "2026-08-31"

# Beginner-investing terms. One pytrends payload (max 5 terms), so all
# five share one normalization. Brand names (e.g. "robinhood") are left
# out on purpose: they'd pick up app-specific news, not new-investor intent.
GT_TERMS = ["how to invest", "how to buy stocks", "stock market for beginners",
            "investing for beginners", "how to invest in stocks"]
# Weekly granularity is only returned for windows of ~5 years or less.
# Starts in 2011 so the expanding z-score has history before 2016.
GT_WINDOWS = [("2011-01-01", "2015-12-31"), ("2015-01-01", "2019-12-31"),
              ("2019-01-01", "2023-12-31"), ("2022-01-01", "2026-09-20")]

# Minimum observations (at each component's own frequency) before its
# expanding z-score is used.
MIN_PERIODS = {"gtrends": 52, "ibkr": 12, "schwab": 8, "hood": 4}

HOOD_CIK, SCHW_CIK = "1783879", "316709"


def _clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text.replace("\xa0", " "))


# =====================================================================
# Generic index machinery (pure functions -- tested in test_investor_index.py)
# =====================================================================
def expanding_zscore(series, min_periods):
    """z_t = (x_t - mean(x_1..x_t)) / std(x_1..x_t). Uses observations up
    to and including t, never anything after t. NaN until min_periods."""
    s = series.dropna()
    mean = s.expanding(min_periods=min_periods).mean()
    std = s.expanding(min_periods=min_periods).std()
    return ((s - mean) / std).reindex(series.index)


def stitch_windows(windows):
    """Chain overlapping Google Trends windows onto the first window's scale.
    windows: list of DataFrames (weekly index, one column per term), each
    independently normalized 0-100 by Google. Each later window is rescaled
    by sum(already-stitched)/sum(window) over their overlapping weeks,
    separately per term; only its new (non-overlapping) weeks are appended."""
    stitched = windows[0].astype(float).copy()
    for w in windows[1:]:
        w = w.astype(float)
        overlap = stitched.index.intersection(w.index)
        if len(overlap) == 0:
            raise ValueError("Google Trends windows must overlap to be stitched")
        factors = stitched.loc[overlap].sum() / w.loc[overlap].sum().replace(0, np.nan)
        new_part = w.loc[w.index > stitched.index.max()] * factors
        stitched = pd.concat([stitched, new_part])
    return stitched


def to_weekly(series, freq, week_starts, lag_periods=0):
    """Map a monthly ('M') or quarterly ('Q') series indexed by pd.Period onto
    weekly rows. Each week takes the value of the period containing its
    Wednesday (so a week is assigned to where most of its days fall).
    lag_periods > 0 shifts values later, i.e. a value can't be used until
    the period after it's reported (publication-date alignment)."""
    s = series.copy()
    s.index = s.index + lag_periods
    ref = (pd.DatetimeIndex(week_starts) + pd.Timedelta(days=3)).to_period(freq)
    return pd.Series(s.reindex(ref).values, index=week_starts)


def composite_index(zscores):
    """Average of whichever component z-scores are available each week."""
    return zscores.mean(axis=1, skipna=True), zscores.notna().sum(axis=1)


def tercile_dummies(index, method="full_sample", min_periods=52):
    """High = top third of index values, Low = bottom third.
    full_sample: one pair of cutoffs from all values in `index` (as the
      research plan specifies; note these cutoffs use the whole sample).
    expanding: cutoffs at each week come only from values up to that week."""
    if method == "full_sample":
        lo, hi = index.quantile([1 / 3, 2 / 3])
        high, low = index >= hi, index <= lo
    elif method == "expanding":
        lo = index.expanding(min_periods=min_periods).quantile(1 / 3)
        hi = index.expanding(min_periods=min_periods).quantile(2 / 3)
        high, low = index >= hi, index <= lo
    else:
        raise ValueError(method)
    valid = index.notna() if method == "full_sample" else (index.notna() & hi.notna())
    return (high & valid).astype(int).where(valid), (low & valid).astype(int).where(valid)


def weekly_to_daily(weekly, trading_days):
    """Each trading day gets the value of the week (Sunday start) it's in."""
    days = pd.DataFrame({"date": pd.DatetimeIndex(trading_days)}).sort_values("date")
    w = weekly.reset_index().rename(columns={weekly.index.name or "index": "week_start"})
    w = w.sort_values("week_start")
    out = pd.merge_asof(days, w, left_on="date", right_on="week_start", direction="backward")
    return out.drop(columns=["week_start"])


# =====================================================================
# 1. Google Trends
# =====================================================================
def fetch_gtrends_window(start, end, terms=GT_TERMS, max_retries=5):
    cache = RAW_DIR / "gtrends" / f"{start}_{end}.csv"
    if cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    from pytrends.request import TrendReq
    for attempt in range(max_retries):
        try:
            pt = TrendReq(hl="en-US", tz=300)
            pt.build_payload(terms, timeframe=f"{start} {end}", geo="US")
            df = pt.interest_over_time()
            break
        except Exception as e:  # pytrends raises on HTTP 429 rate limits
            wait = 60 * (attempt + 1)
            print(f"  Google Trends {start}..{end} attempt {attempt + 1} failed ({e!r}); waiting {wait}s")
            time.sleep(wait)
    else:
        raise RuntimeError(f"Google Trends pull failed for {start}..{end}")
    if "isPartial" in df.columns:
        df = df[~df["isPartial"].astype(bool)].drop(columns="isPartial")
    step = df.index.to_series().diff().dt.days.dropna()
    if not (step == 7).all():
        raise RuntimeError(f"{start}..{end} did not come back weekly -- window too long?")
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache)
    time.sleep(5)
    return df


def build_gtrends_weekly():
    windows = [fetch_gtrends_window(s, e) for s, e in GT_WINDOWS]
    stitched = stitch_windows(windows)
    return stitched.mean(axis=1).rename("gtrends"), stitched


# =====================================================================
# 2. Interactive Brokers (monthly press-release PDFs)
# =====================================================================
IBKR_URL = "https://www.interactivebrokers.com/mkt/getFileNew.php?file={ym}MetricsPressRelease.pdf"


def download_ibkr_pdfs(start="2016-01", end=None):
    """Cache monthly PDFs. Since 2024-06 IBKR's server wraps each PDF in a
    serialized Java SerialBlob (leaked server-side object); the PDF bytes
    are intact inside it, so the %PDF..%%EOF span is sliced out."""
    out = RAW_DIR / "ibkr"
    out.mkdir(parents=True, exist_ok=True)
    end = end or (pd.Timestamp.today() - pd.offsets.MonthBegin(1)).strftime("%Y-%m")
    for p in pd.period_range(start, end, freq="M"):
        ym = p.strftime("%Y%m")
        f = out / f"{ym}.pdf"
        if f.exists():
            continue
        c = requests.get(IBKR_URL.format(ym=ym), headers=WEB_HEADERS, timeout=30).content
        i, j = c.find(b"%PDF"), c.rfind(b"%%EOF")
        if i >= 0 and j > i:
            f.write_bytes(c[i:j + 5])
        time.sleep(0.4)


_IBKR_ACCOUNTS = re.compile(r"([\d,]+(?:\.\d+)?)\s*(thousand|million)\s+client accounts(.{0,220})", re.I)


def parse_ibkr_text(text):
    """-> dict(accounts, acquired, pct_prior_month) from one release's text.
    Formats seen: '375 thousand client accounts', '2.86 million client
    accounts', '1,189 thousand client accounts, including 57 thousand new
    accounts acquired from Folio Investments Inc., ...'."""
    text = re.sub(r"\s+", " ", text)
    m = _IBKR_ACCOUNTS.search(text)
    if not m:
        return None
    mult = 1e3 if m.group(2).lower() == "thousand" else 1e6
    accounts = float(m.group(1).replace(",", "")) * mult
    tail = m.group(3)
    acquired = 0.0
    a = re.search(r"including ([\d,.]+)\s*(thousand|million)\s+(?:new )?accounts acquired", tail, re.I)
    if a:
        acquired = float(a.group(1).replace(",", "")) * (1e3 if a.group(2).lower() == "thousand" else 1e6)
    pct = re.search(r"(\d+(?:\.\d+)?)%\s*(higher|lower) than prior month", tail, re.I)
    pct_prior = None
    if pct:
        pct_prior = float(pct.group(1)) * (1 if pct.group(2).lower() == "higher" else -1)
    return {"accounts": accounts, "acquired": acquired, "pct_prior_month": pct_prior}


def fill_missing_months(levels, pct_prior_month):
    """levels: monthly Series (PeriodIndex, freq M) with NaN for months whose
    release is missing. Back out a missing month from the NEXT month's
    reported '% higher than prior month': L[m] = L[m+1] / (1 + pct/100).
    Falls back to log-linear interpolation if that isn't available.
    Returns (filled_levels, Series of fill method per month)."""
    filled = levels.copy()
    how = pd.Series("reported", index=levels.index)
    for m in levels.index[levels.isna()]:
        nxt = m + 1
        if nxt in levels.index and pd.notna(levels.get(nxt)) and pd.notna(pct_prior_month.get(nxt)):
            filled[m] = levels[nxt] / (1 + pct_prior_month[nxt] / 100)
            how[m] = "backed_out"
    still = filled.isna()
    if still.any():
        filled = np.exp(np.log(filled).interpolate(limit_area="inside"))
        how[still & filled.notna()] = "interpolated"
    return filled, how


def build_ibkr_monthly():
    download_ibkr_pdfs()
    from pypdf import PdfReader
    rows = {}
    for f in sorted((RAW_DIR / "ibkr").glob("*.pdf")):
        text = " ".join(p.extract_text() or "" for p in PdfReader(f).pages[:2])
        parsed = parse_ibkr_text(text)
        if parsed:
            rows[pd.Period(f.stem, freq="M")] = parsed
    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    full = pd.period_range(df.index.min(), df.index.max(), freq="M")
    df = df.reindex(full)
    df["accounts"], df["fill"] = fill_missing_months(df["accounts"], df["pct_prior_month"])
    df["acquired"] = df["acquired"].fillna(0)
    df["organic_net_new"] = df["accounts"].diff() - df["acquired"]
    df["growth"] = df["organic_net_new"] / df["accounts"].shift(1)
    return df


# =====================================================================
# 3. Schwab (quarterly earnings-release exhibit)
# =====================================================================
def _filing_index(cik):
    base = requests.get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json",
                        headers=SEC_HEADERS, timeout=30).json()
    frames = [pd.DataFrame(base["filings"]["recent"])]
    for extra in base["filings"].get("files", []):
        frames.append(pd.DataFrame(requests.get("https://data.sec.gov/submissions/" + extra["name"],
                                                headers=SEC_HEADERS, timeout=30).json()))
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    df["filingDate"] = pd.to_datetime(df["filingDate"])
    return df


def _sec_doc(cik, accession, name):
    acc = accession.replace("-", "")
    return requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{name}",
                        headers=SEC_HEADERS, timeout=120).text


def download_schwab_exhibits(since="2011-10-01"):
    out = RAW_DIR / "schwab"
    out.mkdir(parents=True, exist_ok=True)
    idx = _filing_index(SCHW_CIK)
    e = idx[(idx.form == "8-K") & idx["items"].astype(str).str.contains("2.02") & (idx.filingDate >= since)]
    for _, row in e.iterrows():
        f = out / f"{row.filingDate.date()}.txt"
        if f.exists():
            continue
        acc = row.accessionNumber.replace("-", "")
        listing = requests.get(f"https://www.sec.gov/Archives/edgar/data/{SCHW_CIK}/{acc}/index.json",
                               headers=SEC_HEADERS, timeout=30).json()["directory"]["item"]
        names = [x["name"] for x in listing
                 if "99" in x["name"] and x["name"].lower().endswith((".htm", ".html"))
                 and not x["name"].startswith(("R", "0000"))]
        f.write_text(" ||| ".join(_clean(_sec_doc(SCHW_CIK, row.accessionNumber, n)) for n in names),
                     encoding="utf-8")
        time.sleep(0.2)


_PCT = re.compile(r"\(\s*-?[\d.]+\s*%\s*\)|\(?\s*-?[\d.]+\s*\)?\s*%")


def parse_schwab_row(text, label=r"New brokerage accounts \(in thousands, for the quarter ended\)",
                     stop=r"Client|Active"):
    """Return the 5 quarterly values (most recent first) from a Schwab
    'Key Metrics' table row. The row looks like
        <label> [footnote] <pct change> <pct change> v1 v2 v3 v4 v5
    where pct changes come in many forms: '11%', '(9%)', '(29) %', '(10 %)',
    'N/M', or an em dash for 'unchanged'. All percent-like tokens and
    parenthesized footnote markers are removed; the last 5 numbers remain."""
    text = html.unescape(text)
    # the label also appears in prose ("...active brokerage accounts...");
    # take the first occurrence that actually parses as a 5-value table row
    for m in re.finditer(label + r"(.{0,200}?)(?:" + stop + ")", text, re.I):
        seg = _PCT.sub(" ", m.group(1))
        seg = re.sub(r"N\s*/\s*M|[—–\u0097]", " ", seg)
        nums = [t for t in re.findall(r"\(?\d[\d,]*\)?", seg) if not t.startswith("(")]
        if len(nums) >= 5:
            return [float(t.replace(",", "")) for t in nums[-5:]]
    return None


_QWORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                        "august", "september", "october", "november", "december"], 1)}


def parse_schwab_acquisitions(text):
    """Footnotes like 'Fourth quarter of 2020 includes 14.5 million new
    brokerage accounts related to the acquisition of TD Ameritrade' or
    'September 2011 includes 315,000 new brokerage accounts related to the
    acquisition of optionsXpress'. The same event appears in both quarterly
    and monthly footnotes, so results are keyed by quarter -> thousands."""
    text = html.unescape(text)
    found = {}
    pat = re.compile(r"(?:(first|second|third|fourth) quarter of (\d{4})|(" + "|".join(_MONTHS) +
                     r") (\d{4})) includes ([\d,.]+)\s*(million|thousand)?\s*new brokerage accounts "
                     r"related to the acquisition", re.I)
    for m in pat.finditer(text):
        if m.group(1):
            q = pd.Period(year=int(m.group(2)), quarter=_QWORD[m.group(1).lower()], freq="Q")
        else:
            q = pd.Period(year=int(m.group(4)), month=_MONTHS[m.group(3).lower()], freq="M").asfreq("Q")
        n = float(m.group(5).replace(",", ""))
        unit = (m.group(6) or "").lower()
        thousands = n * 1000 if unit == "million" else (n if unit == "thousand" else n / 1000)
        found[q] = round(thousands, 1)
    return found


def build_schwab_quarterly():
    download_schwab_exhibits()
    new, active, acquired = {}, {}, {}
    for f in sorted((RAW_DIR / "schwab").glob("*.txt")):
        text = f.read_text(encoding="utf-8")
        q = pd.Period(f.stem, freq="Q") - 1   # release reports the quarter before it's filed
        vals = parse_schwab_row(text)
        acts = parse_schwab_row(text, label=r"Active Brokerage Accounts", stop=r"Banking")
        # later releases overwrite earlier ones, so restated figures win
        if vals:
            for k, v in enumerate(vals):
                new[q - k] = v
        if acts:
            for k, v in enumerate(acts):
                active[q - k] = v
        acquired.update(parse_schwab_acquisitions(text))
    df = pd.DataFrame({"new_accounts": pd.Series(new), "active_accounts": pd.Series(active)}).sort_index()
    df = df.reindex(pd.period_range(df.index.min(), df.index.max(), freq="Q"))
    df["acquired"] = pd.Series(acquired).reindex(df.index).fillna(0)
    df["organic_new"] = df["new_accounts"] - df["acquired"]
    df["growth"] = df["organic_new"] / df["active_accounts"].shift(1)
    return df


# =====================================================================
# 4. Robinhood (quarterly, from 2020-Q1)
# =====================================================================
# From the 424B4 IPO prospectus (July 2021) KPI table, in millions, read
# column by column: year-ends 2017-2020 plus the Mar-2020 / Mar-2021
# quarter columns. Hand-verified against the table header, since the
# prospectus mixes annual and quarterly columns in one row.
HOOD_PROSPECTUS = {"2017-12": 1.9, "2018-12": 3.3, "2019-12": 5.1, "2020-12": 12.5,
                   "2020-03": 7.2, "2021-03": 18.0}
_HOOD_ROW = re.compile(r"(Net Cumulative Funded Accounts|Funded Customers)\s*(?:\(in millions\))?"
                       r"\s*(?:\(\d\))?((?:\s+\d+\.\d)+)")
_HOOD_PROSE = re.compile(r"(?:Net Cumulative Funded Accounts|Funded Customers)[^.]{0,200}?\bto (\d+\.\d) million")


def parse_hood_filing(text, report_date, form):
    """10-Q/10-K KPI rows list ending balances oldest -> newest, so the
    last number of the last row is the current period. Earlier numbers in
    that row are the same date 1 (and in 10-Ks, 2) years before."""
    rows = [m.group(2).split() for m in _HOOD_ROW.finditer(text)]
    rows = [r for r in rows if len(r) >= 2]
    if not rows:
        return {}
    last = [float(x) for x in rows[-1]]
    q = pd.Period(report_date, freq="Q")
    return {q - 4 * (len(last) - 1 - i): v for i, v in enumerate(last)}


def build_hood_quarterly():
    out = RAW_DIR / "hood"
    out.mkdir(parents=True, exist_ok=True)
    idx = _filing_index(HOOD_CIK)
    levels = {pd.Period(k, freq="M").asfreq("Q"): v for k, v in HOOD_PROSPECTUS.items()}

    # earnings-release prose first (lowest priority): quarter before filing
    for _, row in idx[(idx.form == "8-K") & idx["items"].astype(str).str.contains("2.02")].iterrows():
        f = out / f"8K_{row.filingDate.date()}.txt"
        if not f.exists():
            f.write_text(_clean(_sec_doc(HOOD_CIK, row.accessionNumber, row.primaryDocument)) + " ||| " +
                         _hood_exhibits(row), encoding="utf-8")
            time.sleep(0.2)
        m = _HOOD_PROSE.search(f.read_text(encoding="utf-8"))
        if m:
            levels[pd.Period(row.filingDate, freq="Q") - 1] = float(m.group(1))

    # 10-Q / 10-K tables override prose where both exist
    for _, row in idx[idx.form.isin(["10-Q", "10-K"])].iterrows():
        f = out / f"{row.form}_{row.reportDate}.txt"
        if not f.exists():
            f.write_text(_clean(_sec_doc(HOOD_CIK, row.accessionNumber, row.primaryDocument)), encoding="utf-8")
            time.sleep(0.3)
        levels.update(parse_hood_filing(f.read_text(encoding="utf-8"), row.reportDate, row.form))

    s = pd.Series(levels).sort_index()
    quarterly = s[s.index >= pd.Period("2019Q4", freq="Q")]
    quarterly = quarterly.reindex(pd.period_range(quarterly.index.min(), quarterly.index.max(), freq="Q"))
    df = pd.DataFrame({"funded_millions": quarterly})
    df["net_adds"] = df["funded_millions"].diff()
    df["growth"] = df["net_adds"] / df["funded_millions"].shift(1)
    return df


def _hood_exhibits(row):
    acc = row.accessionNumber.replace("-", "")
    listing = requests.get(f"https://www.sec.gov/Archives/edgar/data/{HOOD_CIK}/{acc}/index.json",
                           headers=SEC_HEADERS, timeout=30).json()["directory"]["item"]
    names = [x["name"] for x in listing if "99" in x["name"] and x["name"].lower().endswith((".htm", ".html"))
             and not x["name"].startswith(("R", "0000"))]
    return " ||| ".join(_clean(_sec_doc(HOOD_CIK, row.accessionNumber, n)) for n in names)


# =====================================================================
# Assembly
# =====================================================================
def load_components():
    """Read the cleaned components saved by a previous full run (offline)."""
    comps = {"gtrends": pd.read_csv(OUT_DIR / "entry_component_gtrends.csv", index_col=0,
                                    parse_dates=True).iloc[:, 0]}
    for name, freq in [("ibkr", "M"), ("schwab", "Q"), ("hood", "Q")]:
        df = pd.read_csv(OUT_DIR / f"entry_component_{name}.csv", index_col=0)
        df.index = pd.PeriodIndex(df.index, freq=freq)
        comps[name] = df
    return comps


def build_index(component_mode="growth", alignment="reference", tercile_method="full_sample",
                components=None, exclude=()):
    """component_mode: 'growth' (flow / existing base) or 'raw' (flow counts).
    alignment: 'reference' = each value covers the period it describes;
               'publication' = usable only from the next period on.
    exclude: component names to leave out of the composite (e.g. ("hood",)).
    Returns (weekly DataFrame, component dict)."""
    if components is None:
        gt, _ = build_gtrends_weekly()
        components = {"gtrends": gt, "ibkr": build_ibkr_monthly(),
                      "schwab": build_schwab_quarterly(), "hood": build_hood_quarterly()}
    gt = components["gtrends"]
    weeks = gt.index
    col = {"growth": {"ibkr": "growth", "schwab": "growth", "hood": "growth"},
           "raw": {"ibkr": "organic_net_new", "schwab": "organic_new", "hood": "net_adds"}}[component_mode]
    lag = 0 if alignment == "reference" else 1

    z = pd.DataFrame(index=weeks)
    z["gtrends"] = expanding_zscore(gt, MIN_PERIODS["gtrends"])
    for name, freq in [("ibkr", "M"), ("schwab", "Q"), ("hood", "Q")]:
        native = components[name][col[name]].dropna()
        z[name] = to_weekly(expanding_zscore(native, MIN_PERIODS[name]), freq, weeks, lag)

    weekly = z.add_prefix("z_")
    weekly["index"], weekly["n_components"] = composite_index(z.drop(columns=list(exclude)))
    study = weekly.loc[STUDY_START:STUDY_END].copy()
    study["high"], study["low"] = tercile_dummies(study["index"], method=tercile_method)
    study.index.name = "week_start"
    return study, components


def post_overlap(daily):
    """Share of High days that are post-ChatGPT, and corr(High, Post)."""
    post = (daily["date"] >= "2022-11-30").astype(int)
    h = daily["high"]
    return {"corr_high_post": round(float(np.corrcoef(h, post)[0, 1]), 3),
            "high_share_pre": round(float(h[post == 0].mean()), 3),
            "high_share_post": round(float(h[post == 1].mean()), 3)}


if __name__ == "__main__":
    trading_days = pd.read_csv(OUT_DIR / "market_returns.csv", parse_dates=["date"])["date"]

    weekly, comps = build_index("growth", "reference", "full_sample")
    daily = weekly_to_daily(weekly[["index", "n_components", "high", "low"]], trading_days)

    comps["ibkr"].to_csv(OUT_DIR / "entry_component_ibkr.csv")
    comps["schwab"].to_csv(OUT_DIR / "entry_component_schwab.csv")
    comps["hood"].to_csv(OUT_DIR / "entry_component_hood.csv")
    comps["gtrends"].to_csv(OUT_DIR / "entry_component_gtrends.csv")
    weekly.to_csv(OUT_DIR / "investor_index_weekly.csv")
    daily.to_csv(OUT_DIR / "investor_index_daily.csv", index=False)

    print(f"Weekly index: {weekly.index.min().date()} -> {weekly.index.max().date()} ({len(weekly)} weeks)")
    print("Components available per week:", weekly["n_components"].value_counts().sort_index().to_dict())
    print(f"Daily: {len(daily)} trading days, High={int(daily.high.sum())}, Low={int(daily.low.sum())}")
    print("Component z-score correlations:\n", weekly.filter(like="z_").corr().round(2))

    print("\nHigh_t vs Post_t overlap under each design choice:")
    for mode in ["growth", "raw"]:
        for tm in ["full_sample", "expanding"]:
            w, _ = build_index(mode, "reference", tm, components=comps)
            d = weekly_to_daily(w[["index", "high", "low"]], trading_days)
            print(f"  {mode:6s} / {tm:11s}: {post_overlap(d.dropna())}")
