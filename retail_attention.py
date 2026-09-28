"""
Step 4: Stock-level retail-attention index -> high / low attention groups.

Each stock is classified ONCE, using a formation window of the 52 weeks
before ChatGPT's release (2021-12-06 .. 2022-11-25):
  - FINRA's public OTC Transparency API only goes back to 2021-12-06, and
  - a pre-ChatGPT window can't be contaminated by the post-ChatGPT change
    in retail behavior this project is trying to measure.

Components (all cached under data/raw/ after the first pull):
  1. finra_share  -- off-exchange non-ATS dollar volume / total dollar
     volume. Non-ATS off-exchange trading is mostly wholesalers
     internalizing retail orders; ATS (dark-pool) volume is excluded since
     it's mostly institutional. Denominator = split-adjusted-but-NOT-
     dividend-adjusted close x volume (Yahoo's default prices are also
     dividend-adjusted, which would understate a high-yield stock's 2022
     dollar volume by ~10-15% and inflate its share).
  2. gt_attention -- Google Trends interest in "<TICKER> stock", relative
     to a common anchor term so it's comparable across stocks. Skipped
     for tickers that are ordinary words or 1-2 letters ("ALL stock",
     "F stock"), where search volume isn't really about the stock.
  3. inst_own     -- 13F institutional ownership as of 2022-09-30: shares
     held by 13F filers / shares outstanding (SEC XBRL). Enters the index
     NEGATIVELY: low institutional ownership = more retail.

Each component is winsorized (1/99%) and z-scored across stocks; the
index is the average of available z-scores (needs >= 2 of 3). Top third
= high retail attention, bottom third = low.
"""
import io
import re
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT_DIR = Path("data")
RAW = OUT_DIR / "raw"
SEC_HEADERS = {"User-Agent": "StemFair herding research namadev.balaji18@gmail.com"}
FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"

FORM_START, FORM_END = "2021-12-06", "2022-11-25"
IO_REPORT_DATE = "30-SEP-2022"
IO_13F_ZIP = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/2022q4_form13f.zip"
GT_ANCHOR = "KO stock"
# tickers whose "<TICKER> stock" search is dominated by an ordinary word
GT_SKIP_WORDS = {"ALL", "KEY", "NOW", "ON", "IT", "CAT", "LOW", "DOW", "EAT", "FAST", "BIG", "SNOW",
                 "WELL", "ARE", "GAP", "DAY", "HAS", "CAR", "FUN", "PEAK", "LIFE", "BALL", "SAVE",
                 "PLAY", "HOLD", "LOVE", "TRUE", "BEN", "AMP", "BR", "ROK", "EXPE", "DOCU", "NICE",
                 "MAN", "HOG", "CASH", "FIVE", "HOME", "SEE", "WEN", "BILL", "PATH", "RUN", "EDIT",
                 "WING", "GO", "TREE", "SAIL", "OPEN", "HUM", "ICE", "ONE", "PLUG", "SNAP", "FOX",
                 "DASH", "LYFT", "ZM", "U", "SAM", "PM", "MO", "TAP", "HAL", "ED", "EL", "RE", "AN"}
# ticker renames inside the formation window: FINRA reports the old symbol
# before the rename, while Yahoo files the whole history under the new one
FINRA_ALIASES = {"FB": "META", "ANTM": "ELV", "NLOK": "GEN", "NRZ": "RITM"}


def norm(sym):
    return re.sub(r"[.\-/ ]", "", str(sym)).upper()


# =====================================================================
# Pure functions (tested in test_retail_attention.py)
# =====================================================================
def dollar_volume_share(offex_notional, close_unadj, volume):
    """Off-exchange share of dollar volume. close_unadj/volume must be
    split-adjusted consistently (Yahoo auto_adjust=False 'Close' and
    'Volume' are): their product is then the true traded dollar amount,
    whatever splits happened later."""
    denom = (close_unadj * volume).sum()
    return offex_notional / denom if denom > 0 else np.nan


def winsorized_z(s, lower=0.01, upper=0.99):
    lo, hi = s.quantile([lower, upper])
    c = s.clip(lo, hi)
    return (c - c.mean()) / c.std()


def attention_index(df, min_components=2):
    """df columns: finra_share, gt_attention, inst_own (NaN allowed).
    Returns df with z_ columns, index, n_components, group."""
    out = df.copy()
    out["z_finra"] = winsorized_z(out["finra_share"])
    out["z_gt"] = winsorized_z(np.log1p(out["gt_attention"]))
    out["z_inst"] = -winsorized_z(out["inst_own"])          # less institutional = more retail
    zs = out[["z_finra", "z_gt", "z_inst"]]
    out["n_components"] = zs.notna().sum(axis=1)
    out["attention_index"] = zs.mean(axis=1).where(out["n_components"] >= min_components)
    lo, hi = out["attention_index"].quantile([1 / 3, 2 / 3])
    out["group"] = np.select([out["attention_index"] >= hi, out["attention_index"] <= lo],
                             ["high", "low"], default="mid")
    out.loc[out["attention_index"].isna(), "group"] = "unclassified"
    lo2 = out["attention_index"].median()
    out["group_half"] = np.where(out["attention_index"] >= lo2, "high", "low")
    out.loc[out["attention_index"].isna(), "group_half"] = "unclassified"
    return out


def aggregate_13f(infotable, submission, coverpage, report_date=IO_REPORT_DATE, field="SSHPRNAMT"):
    """Total 13F common-share holdings per CUSIP for one report date.
    Uses original 13F-HR filings plus 'NEW HOLDINGS' amendments (which
    add positions); 'RESTATEMENT' amendments are skipped to avoid double
    counting the filer's original report. Options (PUT/CALL) and
    principal-amount (bond) rows are excluded."""
    sub = submission[submission["PERIODOFREPORT"].str.upper() == report_date]
    cov = coverpage.set_index("ACCESSION_NUMBER")
    keep = []
    for acc, stype in zip(sub["ACCESSION_NUMBER"], sub["SUBMISSIONTYPE"]):
        if stype == "13F-HR":
            keep.append(acc)
        elif stype == "13F-HR/A" and acc in cov.index and \
                str(cov.at[acc, "AMENDMENTTYPE"]).upper().startswith("NEW HOLDINGS"):
            keep.append(acc)
    it = infotable[infotable["ACCESSION_NUMBER"].isin(set(keep))]
    it = it[(it["SSHPRNAMTTYPE"].str.upper() == "SH") & it["PUTCALL"].isna()]
    return it.groupby(it["CUSIP"].str.upper())[field].sum()


# =====================================================================
# Data pulls (cached)
# =====================================================================
def fetch_finra_week(week_start):
    f = RAW / "finra" / f"{week_start}.csv"
    if f.exists():
        return pd.read_csv(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for tier in ["T1", "T2"]:
        off = 0
        while True:
            body = {"limit": 5000, "offset": off, "compareFilters": [
                {"compareType": "equal", "fieldName": "weekStartDate", "fieldValue": week_start},
                {"compareType": "equal", "fieldName": "summaryTypeCode", "fieldValue": "OTC_W_SMBL"},
                {"compareType": "equal", "fieldName": "tierIdentifier", "fieldValue": tier}]}
            r = requests.post(FINRA_URL, json=body, headers={"Accept": "application/json"}, timeout=60)
            d = r.json() if r.status_code == 200 else []
            rows += d
            if len(d) < 5000:
                break
            off += 5000
        time.sleep(0.3)
    df = pd.DataFrame(rows)[["issueSymbolIdentifier", "totalWeeklyShareQuantity", "totalNotionalSum"]]
    df.to_csv(f, index=False)
    return df


def build_finra(tickers):
    weeks = pd.date_range(FORM_START, FORM_END, freq="W-MON").strftime("%Y-%m-%d")
    frames = [fetch_finra_week(w) for w in weeks]
    allw = pd.concat(frames).dropna(subset=["issueSymbolIdentifier"])
    allw["sym"] = allw["issueSymbolIdentifier"].map(norm)
    aliases = dict(FINRA_ALIASES)
    if (OUT_DIR / "renames.csv").exists():   # every verified rename, not just the four above
        rn = pd.read_csv(OUT_DIR / "renames.csv")
        aliases.update(dict(zip(rn["old"], rn["new"])))
    allw["sym"] = allw["sym"].replace({norm(k): norm(v) for k, v in aliases.items()})
    notional = allw.groupby("sym")["totalNotionalSum"].sum()
    return pd.Series({t: notional.get(norm(t), np.nan) for t in tickers}), len(weeks)


def fetch_unadjusted(tickers):
    f = RAW / "formation_unadjusted_prices.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["date"])
    import yfinance as yf
    frames = []
    for i in range(0, len(tickers), 50):
        batch = tickers[i:i + 50]
        d = yf.download(batch, start=FORM_START, end=(pd.Timestamp(FORM_END) + pd.Timedelta(days=1)),
                        auto_adjust=False, progress=False, group_by="ticker", threads=True)
        for t in batch:
            try:
                sub = d[t][["Close", "Volume"]].dropna()
            except KeyError:
                continue
            sub = sub.reset_index().rename(columns={"Date": "date", "Close": "close", "Volume": "volume"})
            sub["ticker"] = t
            frames.append(sub)
        time.sleep(1.5)
    px = pd.concat(frames, ignore_index=True)
    px.to_csv(f, index=False)
    return px


def build_inst_own(tickers):
    zpath = RAW / "13f" / "2022q4_form13f.zip"
    zpath.parent.mkdir(parents=True, exist_ok=True)
    if not zpath.exists():
        zpath.write_bytes(requests.get(IO_13F_ZIP, headers=SEC_HEADERS, timeout=600).content)
    with zipfile.ZipFile(zpath) as z:
        name = lambda stem: next(n for n in z.namelist() if n.upper().endswith(stem))
        read = lambda stem, cols=None: pd.read_csv(z.open(name(stem)), sep="\t", dtype=str, usecols=cols)
        sub = read("SUBMISSION.TSV")
        cov = read("COVERPAGE.TSV", ["ACCESSION_NUMBER", "AMENDMENTTYPE"])
        it = read("INFOTABLE.TSV", ["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "SSHPRNAMT",
                                     "SSHPRNAMTTYPE", "PUTCALL"])
    for c in ["SSHPRNAMT", "VALUE"]:
        it[c] = pd.to_numeric(it[c], errors="coerce")
    held = aggregate_13f(it, sub, cov)
    # Only map CUSIPs with > $300M held by 13F filers (13F VALUE was in
    # $thousands until 2023). Every Russell 1000 stock clears this easily;
    # a share-count cutoff would wrongly drop high-priced names with few
    # shares (e.g. NVR, ~3M shares outstanding).
    value = aggregate_13f(it, sub, cov, field="VALUE")
    cusip_ticker = map_cusips_openfigi(value[value > 300_000].index.tolist())
    by_ticker = held.rename(index=cusip_ticker).groupby(level=0).sum()
    by_ticker = by_ticker[by_ticker.index.isin(set(cusip_ticker.values()))]

    held_by_ticker = pd.Series({t: by_ticker.get(norm(t), np.nan) for t in tickers})
    held_by_ticker = fill_by_issuer_name(held_by_ticker, it, held, value)

    shares_out = shares_outstanding(tickers)
    io_ = held_by_ticker / shares_out.reindex(tickers)
    return io_.clip(upper=1.5)   # 13F double-counting can push this past 100%


_NAME_NOISE = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "SA", "NV", "AG", "SE",
               "HOLDINGS", "HOLDING", "GROUP", "THE", "CLASS", "A", "B", "C", "COM", "ORD", "SHS", "NEW", "REIT"}


def normalize_issuer(name):
    words = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper()).split()
    return " ".join(w for w in words if w not in _NAME_NOISE)


def fill_by_issuer_name(held_by_ticker, infotable, held, value):
    """Last resort for the few tickers whose 2022 CUSIP OpenFIGI no longer
    maps (retired after a later split or reorganization, e.g. Lam
    Research, BlackRock): match the 13F issuer name to the company name
    iShares used in the formation window, and take the highest-value
    CUSIP with that exact normalized name. Only applied to still-missing
    tickers, so a name clash can't overwrite a CUSIP-based match."""
    missing = held_by_ticker.index[held_by_ticker.isna()]
    if not len(missing):
        return held_by_ticker
    snaps = sorted((RAW / "iwb_holdings_full").glob("*.csv"))
    snaps = [f for f in snaps if FORM_START[:7] <= f.stem[:7] <= FORM_END[:7]]
    names = pd.concat(pd.read_csv(f, usecols=["Ticker", "Name"]) for f in snaps).drop_duplicates("Ticker")
    name_of = dict(zip(names["Ticker"].map(norm), names["Name"].map(normalize_issuer)))
    issuer = infotable.drop_duplicates("CUSIP").set_index(infotable.drop_duplicates("CUSIP")["CUSIP"].str.upper())
    by_name = pd.DataFrame({"name": issuer["NAMEOFISSUER"].map(normalize_issuer),
                            "value": value.reindex(issuer.index)}).dropna()
    out = held_by_ticker.copy()
    for t in missing:
        n = name_of.get(norm(t))
        cands = by_name[by_name["name"] == n] if n else by_name.iloc[0:0]
        if len(cands):
            out[t] = held.get(cands["value"].idxmax(), np.nan)
    return out


def pick_us_ticker(data):
    """Most common ticker among a CUSIP's US listings (Bloomberg exchange
    codes starting with 'U': US composite, UN = NYSE, UW = Nasdaq, ...).
    Foreign listings (e.g. 'EXMOC' on a Chilean exchange) are ignored."""
    us = [d.get("ticker") for d in data if str(d.get("exchCode", "")).startswith("U") and d.get("ticker")]
    return pd.Series(us).mode().iloc[0] if us else None


def map_cusips_openfigi(cusips):
    """CUSIP -> normalized US ticker via OpenFIGI (free tier: 10 CUSIPs per
    request, 25 requests/minute without an API key)."""
    cache = RAW / "13f" / "openfigi_map.csv"
    known = pd.read_csv(cache, dtype=str) if cache.exists() else pd.DataFrame(columns=["cusip", "ticker"])
    known = known[known["ticker"].fillna("") != ""]      # retry earlier blanks
    done = set(known["cusip"])
    todo = [c for c in cusips if c not in done]
    rows = known.to_dict("records")
    for i in range(0, len(todo), 10):
        chunk = todo[i:i + 10]
        # no exchCode filter: exchCode="US" returns "No identifier found" even
        # for plain US stocks like Exxon (30231G102); pick the US listing below
        # foreign-domiciled issuers (Accenture G1151C101, Chubb H1467J104...)
        # have CINS codes -- same 9-character format, but OpenFIGI only
        # recognizes them as idType ID_CINS
        jobs = [{"idType": "ID_CINS" if c[0].isalpha() else "ID_CUSIP", "idValue": c} for c in chunk]
        r = None
        for attempt in range(6):
            try:
                r = requests.post("https://api.openfigi.com/v3/mapping", json=jobs, timeout=30)
            except requests.RequestException:     # dropped connections happen on long runs
                time.sleep(15 * (attempt + 1))
                continue
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            break
        if r is None or r.status_code != 200:
            continue
        for c, res in zip(chunk, r.json()):
            pick = pick_us_ticker(res.get("data") or [])
            rows.append({"cusip": c, "ticker": norm(pick) if pick else ""})
        pd.DataFrame(rows).to_csv(cache, index=False)   # checkpoint every request
        if (i // 10) % 50 == 0:
            print(f"  OpenFIGI: {i + len(chunk)}/{len(todo)} CUSIPs mapped", flush=True)
        time.sleep(2.5)
    m = pd.DataFrame(rows)
    m.to_csv(cache, index=False)
    m = m[m["ticker"].astype(str) != ""]
    return dict(zip(m["cusip"], m["ticker"]))


def shares_outstanding(tickers):
    """dei:EntityCommonStockSharesOutstanding reported with a date in
    2022-Q3 (SEC XBRL frames), matched ticker -> CIK via company_tickers.json.
    Multi-class companies usually report this per class (with a dimension),
    which the frames API leaves out -- those come back missing."""
    # A frame only holds values dated inside that quarter, so companies with
    # other fiscal calendars (e.g. Accenture, Applied Materials) are missing
    # from CY2022Q3I; fall back to the neighbouring quarters, nearest first.
    by_cik = {}
    for frame in ["CY2022Q4I", "CY2022Q2I", "CY2022Q3I"]:   # later ones overwrite -> Q3 wins
        data = requests.get("https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/"
                            f"shares/{frame}.json", headers=SEC_HEADERS, timeout=60).json()["data"]
        by_cik.update({d["cik"]: d["val"] for d in data})
        time.sleep(0.2)
    # Multi-class companies (Alphabet, Meta, Visa, Ford, UPS...) report the
    # cover-page count per share class, which frames omit. Fall back to
    # weighted-average basic shares (the EPS denominator) -- one total
    # across classes. For dual-class firms this makes ownership of the
    # listed class look lower than its float-based figure; noted in the docs.
    for frame in ["CY2022Q3", "CY2022Q4", "CY2022Q2"]:   # first found wins
        data = requests.get("https://data.sec.gov/api/xbrl/frames/us-gaap/WeightedAverageNumberOfSharesOutstandingBasic/"
                            f"shares/{frame}.json", headers=SEC_HEADERS, timeout=60).json().get("data", [])
        for d in data:
            by_cik.setdefault(d["cik"], d["val"])
        time.sleep(0.2)
    ct = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS, timeout=60).json()
    tick_cik = {norm(v["ticker"]): v["cik_str"] for v in ct.values()}
    for old, new in FINRA_ALIASES.items():
        tick_cik.setdefault(norm(old), tick_cik.get(norm(new)))
    out = pd.Series({t: by_cik.get(tick_cik.get(norm(t)), np.nan) for t in tickers})
    # SEC's ticker file maps CURRENT tickers to CURRENT registrants; a few
    # companies re-registered under a new holding company after 2022 (e.g.
    # ExxonMobil, BlackRock), so their 2022 filings sit under an old CIK.
    # Fall back to Yahoo's historical share count, median over Jul-Dec 2022.
    import yfinance as yf
    for t in out.index[out.isna()]:
        try:
            s = yf.Ticker(t).get_shares_full(start="2022-07-01", end="2022-12-31")
            if s is not None and len(s):
                out[t] = float(s.median())
        except Exception:
            pass
        time.sleep(0.3)
    return out


def fetch_gt_batch(terms, max_retries=6):
    """One pytrends request: up to 4 stock terms + the anchor, weekly over the
    formation window. Returns mean interest per term relative to the anchor."""
    key = "_".join(re.sub(r"\W", "", t) for t in terms)
    f = RAW / "gt_stocks" / f"{key}.csv"
    if f.exists():
        return pd.read_csv(f, index_col=0).iloc[:, 0]
    from pytrends.request import TrendReq
    for attempt in range(max_retries):
        try:
            pt = TrendReq(hl="en-US", tz=300)
            pt.build_payload(terms + [GT_ANCHOR], timeframe=f"{FORM_START} {FORM_END}", geo="US")
            df = pt.interest_over_time()
            break
        except Exception:
            time.sleep(60 * (attempt + 1))
    else:
        return None
    means = df.drop(columns="isPartial", errors="ignore").mean() if len(df) else pd.Series(0.0, index=terms + [GT_ANCHOR])
    anchor = means.get(GT_ANCHOR, 0.0)
    rel = pd.Series({t: (means.get(t, 0.0) / anchor) if anchor >= 0.5 else np.nan for t in terms})
    f.parent.mkdir(parents=True, exist_ok=True)
    rel.to_frame("rel").to_csv(f)
    time.sleep(12)
    return rel


def build_gt(tickers):
    usable = [t for t in tickers if len(norm(t)) > 2 and norm(t) not in GT_SKIP_WORDS]
    rel = {}
    for i in range(0, len(usable), 4):
        batch = usable[i:i + 4]
        r = fetch_gt_batch([f"{t} stock" for t in batch])
        if r is None:
            continue
        for t in batch:
            v = r.get(f"{t} stock")
            if pd.isna(v):   # anchor rounded to 0 next to a very popular ticker -> retry pairwise
                pair = fetch_gt_batch([f"{t} stock"])
                v = pair.get(f"{t} stock") if pair is not None else np.nan
            rel[t] = v
    return pd.Series(rel).reindex(tickers)


# =====================================================================
# Assembly
# =====================================================================
def formation_universe(panel_path=OUT_DIR / "return_panel_final.csv", min_coverage=0.75):
    p = pd.read_csv(panel_path, usecols=["date", "ticker"], parse_dates=["date"])
    w = p[(p["date"] >= FORM_START) & (p["date"] <= FORM_END)]
    n_days = w["date"].nunique()
    cov = w.groupby("ticker")["date"].nunique() / n_days
    return sorted(cov[cov >= min_coverage].index)


def build(panel_path=OUT_DIR / "return_panel_final.csv", skip_gt=False):
    tickers = formation_universe(panel_path)
    print(f"Formation window {FORM_START}..{FORM_END}: {len(tickers)} stocks")

    offex, n_weeks = build_finra(tickers)
    px = fetch_unadjusted(tickers)
    finra_share = pd.Series({t: dollar_volume_share(offex.get(t, np.nan), g["close"], g["volume"])
                             for t, g in px.groupby("ticker")}).reindex(tickers)
    finra_share[offex.reindex(tickers).isna()] = np.nan
    inst = build_inst_own(tickers)
    gt = pd.Series(np.nan, index=tickers) if skip_gt else build_gt(tickers)

    df = pd.DataFrame({"finra_share": finra_share, "gt_attention": gt, "inst_own": inst})
    df.index.name = "ticker"
    return attention_index(df)


if __name__ == "__main__":
    import sys
    res = build(sys.argv[1] if len(sys.argv) > 1 else OUT_DIR / "return_panel_final.csv")
    res.to_csv(OUT_DIR / "retail_attention.csv")
    print("coverage:", res[["finra_share", "gt_attention", "inst_own"]].notna().sum().to_dict())
    print("groups:", res["group"].value_counts().to_dict())
    print("component correlations:\n", res[["z_finra", "z_gt", "z_inst"]].corr().round(2))
    print("most retail:", res.nlargest(12, "attention_index").index.tolist())
    print("least retail:", res.nsmallest(12, "attention_index").index.tolist())
