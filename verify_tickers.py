"""
Rigorous, one-at-a-time verification of Yahoo Finance data availability
across the full Russell 1000 historical membership universe.

Unlike build_panel.py's batched download (threaded, group_by="ticker"),
this queries EVERY ticker individually with no threading, to rule out
batching/threading itself as a cause of failures and to give each ticker
a clean retry after a real delay before calling it a genuine gap. This is
slower (no parallelism) but is the most rigorous way to separate "Yahoo
truly has no data for this security" from "got rate-limited."

Phase 1: individual download attempt + 1 retry (after a real delay) per
ticker across the full membership.csv universe.
Phase 2: for tickers that still fail, look up the company's last-known
name (from build_membership.py's raw holdings) and query Yahoo's own
search/autocomplete endpoint for a possible renamed/successor ticker.
Any candidate is downloaded and verified before being reported -- this is
best-effort (misses multi-step corporate lineages, splits, and delistings
where the company is simply no longer independently traded) and is
reported separately from Phase 1's results, not silently merged in.
"""
import time
import difflib
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path
from build_panel import load_membership_universe, STUDY_START, STUDY_END

OUT_DIR = Path("data")
SEARCH_HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")}


def try_download_once(ticker, start=STUDY_START, end=STUDY_END):
    try:
        d = yf.download(ticker, start=start, end=end, auto_adjust=True,
                         progress=False, threads=False)
    except Exception:
        return None
    return d


def verify_ticker(ticker, retry_delay=5.0):
    """One attempt, then (if empty) a single retry after a real delay.
    Returns (ok: bool, n_rows: int)."""
    d = try_download_once(ticker)
    if d is not None and not d.empty:
        return True, len(d)
    time.sleep(retry_delay)
    d = try_download_once(ticker)
    if d is not None and not d.empty:
        return True, len(d)
    return False, 0


_SEARCH_QUERY_STRIP_WORDS = {
    "INC", "INC.", "INCORPORATED", "CORP", "CORP.", "CORPORATION", "CO",
    "CO.", "COMPANY", "LTD", "LTD.", "LIMITED", "PLC", "SA", "N.V.", "NV",
    "HOLDINGS", "HOLDING", "GROUP", "CLASS", "A", "B", "C",
}


def _search_query_variants(name):
    """Yahoo's search endpoint is picky about legal-entity suffixes (e.g.
    "WILLIS TOWERS WATSON PLC" returns nothing, but "Willis Towers Watson"
    finds WTW) -- try the full name first, then a suffix-stripped version.
    NOTE: this stripped version is ONLY used to build a better search
    query; the similarity check against Yahoo's returned name still uses
    the full original `name`, so this doesn't weaken validation."""
    variants = [name]
    words = [w for w in name.replace(".", " ").split() if w.upper() not in _SEARCH_QUERY_STRIP_WORDS]
    stripped = " ".join(words)
    if stripped and stripped.upper() != name.upper():
        variants.append(stripped)
    return variants


def search_candidates(name, exclude_ticker, max_candidates=5):
    """Query Yahoo's search endpoint for a company name, return candidate
    (symbol, matched_name, similarity) triples that look like plausible
    equity matches and aren't the ticker we already know failed. Tries
    the raw name, then a suffix-stripped query variant if that finds
    nothing (see _search_query_variants)."""
    for query in _search_query_variants(name):
        try:
            r = requests.get("https://query1.finance.yahoo.com/v1/finance/search",
                              params={"q": query, "quotesCount": max_candidates, "newsCount": 0},
                              headers=SEARCH_HEADERS, timeout=15)
            data = r.json()
        except Exception:
            continue
        out = []
        for q in data.get("quotes", []):
            sym = q.get("symbol")
            qtype = q.get("quoteType")
            matched_name = q.get("shortname") or q.get("longname") or ""
            if not sym or sym == exclude_ticker or qtype != "EQUITY":
                continue
            if "." in sym:  # skip foreign-exchange-suffixed listings (e.g. WTY.DE)
                continue
            similarity = difflib.SequenceMatcher(None, name.upper(), matched_name.upper()).ratio()
            out.append((sym, matched_name, similarity))
        if out:
            out.sort(key=lambda x: -x[2])
            return out
        time.sleep(0.5)
    return []


VERIFICATION_CSV = OUT_DIR / "ticker_verification.csv"


def load_checkpoint():
    """Resume support: this is a multi-hour job (individual queries, real
    retry delays for ~740 expected failures) and got killed partway
    through once already by a session restart, losing all progress since
    results were only written at the very end. Now every ticker's result
    is appended immediately, and a rerun skips whatever's already here."""
    if VERIFICATION_CSV.exists():
        done = pd.read_csv(VERIFICATION_CSV)
        return done
    return pd.DataFrame(columns=["ticker", "ok", "n_rows"])


def append_result(row):
    write_header = not VERIFICATION_CSV.exists()
    pd.DataFrame([row]).to_csv(VERIFICATION_CSV, mode="a", header=write_header, index=False)


if __name__ == "__main__":
    membership_df, tickers = load_membership_universe()
    done = load_checkpoint()
    already_checked = set(done["ticker"])
    remaining = [t for t in tickers if t not in already_checked]

    print(f"Phase 1: {len(already_checked)} tickers already checked (resuming), "
          f"{len(remaining)} remaining out of {len(tickers)} total...")

    for i, t in enumerate(remaining, 1):
        ok, n = verify_ticker(t)
        append_result({"ticker": t, "ok": ok, "n_rows": n})
        time.sleep(0.6)  # pacing between EVERY ticker, success or fail
        if i % 25 == 0:
            print(f"  {i}/{len(remaining)} checked this run, "
                  f"{len(already_checked) + i}/{len(tickers)} total", flush=True)

    ver = pd.read_csv(VERIFICATION_CSV)
    n_ok = ver["ok"].sum()
    print(f"\nPhase 1 done: {n_ok}/{len(ver)} tickers have real data "
          f"({n_ok/len(ver):.1%}), {len(ver) - n_ok} confirmed failed "
          f"after individual query + retry.", flush=True)

    # ----------------------------------------------------------------
    # Phase 2: alternate-ticker lookup for confirmed failures
    # (same incremental-append/resume pattern as Phase 1 -- see
    # load_checkpoint()'s docstring for why that matters here)
    # ----------------------------------------------------------------
    RECOVERIES_CSV = OUT_DIR / "ticker_alternate_recoveries.csv"
    UNRESOLVED_CSV = OUT_DIR / "ticker_still_unresolved.csv"

    failed = ver.loc[~ver["ok"], "ticker"].tolist()
    already_done_p2 = set()
    if RECOVERIES_CSV.exists():
        already_done_p2 |= set(pd.read_csv(RECOVERIES_CSV)["ticker"])
    if UNRESOLVED_CSV.exists():
        already_done_p2 |= set(pd.read_csv(UNRESOLVED_CSV)["ticker"])
    remaining_p2 = [t for t in failed if t not in already_done_p2]

    print(f"\nPhase 2: {len(already_done_p2)} already searched (resuming), "
          f"{len(remaining_p2)} remaining out of {len(failed)} confirmed failures...", flush=True)

    raw_holdings = pd.read_csv(OUT_DIR / "iwb_monthly_holdings_raw.csv")
    last_name = (raw_holdings.sort_values("snapshot_date")
                 .drop_duplicates("ticker", keep="last")
                 .set_index("ticker")["name"])

    def append_row(path, row):
        write_header = not path.exists()
        pd.DataFrame([row]).to_csv(path, mode="a", header=write_header, index=False)

    n_recovered_this_run = 0
    for i, t in enumerate(remaining_p2, 1):
        name = last_name.get(t)
        if not name:
            append_row(UNRESOLVED_CSV, {"ticker": t, "name": None, "reason": "no name on file",
                                         "best_candidate_seen": None})
            continue
        candidates = search_candidates(name, exclude_ticker=t)
        recovered = False
        for sym, matched_name, sim in candidates[:3]:
            if sim < 0.5:  # too dissimilar a name match to trust
                continue
            ok, n = verify_ticker(sym, retry_delay=3.0)
            if ok:
                append_row(RECOVERIES_CSV, {"ticker": t, "name": name, "candidate_ticker": sym,
                                             "candidate_name": matched_name, "name_similarity": round(sim, 3),
                                             "n_rows": n})
                recovered = True
                n_recovered_this_run += 1
                break
            time.sleep(0.5)
        if not recovered:
            best = candidates[0] if candidates else None
            append_row(UNRESOLVED_CSV, {
                "ticker": t, "name": name,
                "reason": "no plausible/verifiable candidate found",
                "best_candidate_seen": f"{best[0]} ({best[1]}, sim={best[2]:.2f})" if best else None,
            })
        time.sleep(0.6)
        if i % 25 == 0:
            print(f"  {i}/{len(remaining_p2)} searched this run, "
                  f"{n_recovered_this_run} recovered this run", flush=True)

    recoveries_df = pd.read_csv(RECOVERIES_CSV) if RECOVERIES_CSV.exists() else pd.DataFrame(columns=["ticker"])
    unresolved_df = pd.read_csv(UNRESOLVED_CSV) if UNRESOLVED_CSV.exists() else pd.DataFrame(columns=["ticker"])
    print(f"\nPhase 2 done: {len(recoveries_df)} recovered via an alternate ticker, "
          f"{len(unresolved_df)} remain genuinely unresolved.", flush=True)

    # ----------------------------------------------------------------
    # Final report
    # ----------------------------------------------------------------
    relevant = membership_df.drop_duplicates("ticker").set_index("ticker")
    relevant = relevant.loc[relevant.index.isin(tickers)]
    still_active = set(relevant[relevant["end_date"] >= pd.Timestamp("2099-01-01")].index)
    exited = set(relevant.index) - still_active

    recovered_tickers = set(recoveries_df["ticker"])
    truly_failed = set(unresolved_df["ticker"])

    print("\n" + "="*70)
    print("FINAL REPORT")
    print("="*70)
    for label, group in [("STILL ACTIVE", still_active), ("EXITED (delisted/acquired/renamed)", exited)]:
        n_total = len(group)
        n_recovered = len(group & recovered_tickers)
        n_failed = len(group & truly_failed)
        n_ok_direct = n_total - n_recovered - n_failed
        print(f"{label}: {n_total} tickers")
        print(f"  direct Yahoo data: {n_ok_direct} ({n_ok_direct/n_total:.1%})")
        print(f"  recovered via alternate ticker: {n_recovered} ({n_recovered/n_total:.1%})")
        print(f"  genuinely unresolved: {n_failed} ({n_failed/n_total:.1%})")
