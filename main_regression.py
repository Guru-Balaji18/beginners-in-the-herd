"""
Step 5: main herding regression (all variants) + Step 4's H3 split.

Standard (CCK) model, dummy form -- middle third of entry is the baseline:
  CSAD_t = g0 + g1|Rm| + g2 Rm^2 + g3 Rm^2*Post + g4 Rm^2*High + g5 Rm^2*Post*High
              + g6 Rm^2*Low + g7 Rm^2*Post*Low + controls + e
  H1: g5 < 0 (herding rises after ChatGPT in HIGH-entry periods)
  H2: g7 >= 0 / insignificant (no such rise in LOW-entry periods)
Continuous form: High/Low replaced by the entry index value itself (Idx).
Wang-Hudson form: SCSAD on Rm, Rm^2, Rm^3 with the same Post/High/Low
  interactions on the cubic term (no controls, as in their paper).

Controls: VIX, top-decile |Rm| day dummy, calendar-month dummies, linear
time trend, FOMC-announcement and CPI-release day dummies.
Estimation: OLS, Newey-West HAC standard errors, 5 lags.

H3: CSAD is rebuilt separately for high- and low-retail-attention stocks
(retail_attention.py), each measured against the SAME overall market
return, so both groups share identical right-hand-side variables. The
difference regression (CSAD_high - CSAD_low on those regressors) then
gives exactly g5_high - g5_low, with a HAC standard error that accounts
for the two groups being observed on the same days.
"""
import numpy as np
import pandas as pd
from pathlib import Path

import investor_index as ii
from build_csad import compute_csad
from robustness_wang_hudson import _fit_hac

OUT_DIR = Path("data")
RAW = OUT_DIR / "raw"
CHATGPT = pd.Timestamp("2022-11-30")
PRIMARY = dict(hood=False, mode="growth", form="dummy", cutoff="expanding")


# =====================================================================
# Design construction (pure -- tested in test_main_regression.py)
# =====================================================================
def controls_frame(dates, mkt_ret, vix, fomc_dates, cpi_dates):
    d = pd.DatetimeIndex(dates)
    out = pd.DataFrame(index=d)
    out["vix"] = pd.Series(vix, index=d).ffill().values
    absr = pd.Series(np.abs(mkt_ret), index=d)
    out["top_decile_vol"] = (absr >= absr.quantile(0.9)).astype(int)
    for m in range(2, 13):
        out[f"month_{m}"] = (d.month == m).astype(int)
    out["trend"] = (d - d[0]).days / 365.25
    out["fomc"] = d.isin(pd.DatetimeIndex(fomc_dates)).astype(int)
    out["cpi"] = d.isin(pd.DatetimeIndex(cpi_dates)).astype(int)
    return out


def design(df, form, test, controls=None, lower_order=False):
    """df needs mkt_ret, post, and (form='dummy') high/low or (form='continuous') idx."""
    rm = df["mkt_ret"]
    X = pd.DataFrame(index=df.index)
    if test == "cck":
        X["abs_rm"], X["rm2"] = rm.abs(), rm ** 2
        base, tag = rm ** 2, "rm2"
    else:  # Wang-Hudson
        X["mkt_ret"], X["rm2"], X["rm3"] = rm, rm ** 2, rm ** 3
        base, tag = rm ** 3, "rm3"
    X[f"{tag}_post"] = base * df["post"]
    groups = ["high", "low"] if form == "dummy" else ["idx"]
    for g in groups:
        X[f"{tag}_{g}"] = base * df[g]
        X[f"{tag}_post_{g}"] = base * df["post"] * df[g]
    if lower_order and test == "cck":
        X["post"] = df["post"]
        for g in groups:
            X[g] = df[g]
            X[f"post_{g}"] = df["post"] * df[g]
    if controls is not None and test == "cck":
        X = X.join(controls)
    return X


def key_terms(form, test):
    tag = "rm2" if test == "cck" else "rm3"
    g = "high" if form == "dummy" else "idx"
    return f"{tag}_post_{g}", (f"{tag}_post_low" if form == "dummy" else None)


def fit(y, X):
    ok = y.notna() & X.notna().all(axis=1)
    return _fit_hac(y[ok], X[ok])


def summarize_term(res, term):
    if term is None or term not in res.params:
        return (np.nan, np.nan, np.nan)
    return (res.params[term], res.bse[term], res.pvalues[term])


# =====================================================================
# Data assembly
# =====================================================================
def load_vix(start="2016-01-01", end="2026-08-31"):
    f = RAW / "vix.csv"
    if not f.exists():
        import yfinance as yf
        v = yf.download("^VIX", start=start, end=end, auto_adjust=True, progress=False)["Close"]
        v = v.iloc[:, 0] if isinstance(v, pd.DataFrame) else v
        v.rename("vix").to_csv(f)
    return pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]


def entry_variant(hood, mode, form, cutoff, comps, trading_days):
    exclude = () if hood else ("hood",)
    w, _ = ii.build_index(mode, "reference", cutoff if form == "dummy" else "full_sample",
                          components=comps, exclude=exclude)
    cols = ["index", "high", "low"]
    d = ii.weekly_to_daily(w[cols], trading_days).set_index("date")
    return d.rename(columns={"index": "idx"})


def group_csad(panel, market, tickers, min_stocks=30):
    sub = panel[panel["ticker"].isin(set(tickers))]
    c = compute_csad(sub, market).set_index("date")
    n = sub.groupby("date")["ticker"].nunique()
    n.index = pd.to_datetime(n.index)
    c.loc[n.reindex(c.index).fillna(0) < min_stocks, ["csad", "scsad"]] = np.nan
    return c


def variant_grid():
    grid = []
    for hood in [False, True]:
        for mode in ["growth", "raw"]:
            for form in ["dummy", "continuous"]:
                for cutoff in (["expanding", "full_sample"] if form == "dummy" else ["n/a"]):
                    grid.append(dict(hood=hood, mode=mode, form=form, cutoff=cutoff))
    return grid


def label(v):
    return (f"{'with' if v['hood'] else 'no'} Robinhood / {v['mode']} / {v['form']}"
            + (f" / {v['cutoff']} cutoffs" if v["form"] == "dummy" else ""))


def run(panel_path, market_path, attention_path=OUT_DIR / "retail_attention.csv"):
    panel = pd.read_csv(panel_path, parse_dates=["date"])
    market = pd.read_csv(market_path, parse_dates=["date"])
    csad = compute_csad(panel, market).set_index("date")
    days = csad.index

    ctrl = controls_frame(days, csad["mkt_ret"].values, load_vix().reindex(days).values,
                          pd.read_csv(RAW / "fomc_dates.csv")["date"], pd.read_csv(RAW / "cpi_release_dates.csv")["date"])

    groups = {}
    if Path(attention_path).exists():
        att = pd.read_csv(attention_path, index_col=0)
        for split in ["group", "group_half"]:
            for g in ["high", "low"]:
                groups[(split, g)] = group_csad(panel, market, att.index[att[split] == g])

    comps = ii.load_components()
    main_rows, h3_rows = [], []
    for v in variant_grid():
        ent = entry_variant(v["hood"], v["mode"], v["form"], v["cutoff"], comps, days)
        df = csad.join(ent)
        need = ["idx"] if v["form"] == "continuous" else ["high", "low"]
        df = df.dropna(subset=need)
        n_post_high = int(((df["post"] == 1) & (df["high"] == 1)).sum()) if v["form"] == "dummy" else np.nan
        is_primary = all(v[k] == PRIMARY[k] for k in PRIMARY)
        for test in ["cck", "wh"]:
            X = design(df, v["form"], test, controls=ctrl.reindex(df.index))
            y = df["csad"] if test == "cck" else df["scsad"]
            res = fit(y, X)
            g5, g7 = key_terms(v["form"], test)
            main_rows.append({**v, "variant": label(v), "primary": is_primary, "test": test,
                              "n_days": int(res.nobs), "n_post_high_days": n_post_high,
                              **dict(zip(["g5", "g5_se", "g5_p"], summarize_term(res, g5))),
                              **dict(zip(["g7_postlow", "g7_se", "g7_p"], summarize_term(res, g7)))})
            if is_primary and test == "cck":
                Xl = design(df, v["form"], test, controls=ctrl.reindex(df.index), lower_order=True)
                rl = fit(y, Xl)
                main_rows.append({**v, "variant": label(v) + " + lower-order terms", "primary": False,
                                  "test": test, "n_days": int(rl.nobs), "n_post_high_days": n_post_high,
                                  **dict(zip(["g5", "g5_se", "g5_p"], summarize_term(rl, g5))),
                                  **dict(zip(["g7_postlow", "g7_se", "g7_p"], summarize_term(rl, g7)))})

            # H3 split
            for split in ((["group", "group_half"] if is_primary else ["group"]) if groups else []):
                hi, lo = groups[(split, "high")].reindex(df.index), groups[(split, "low")].reindex(df.index)
                col = "csad" if test == "cck" else "scsad"
                r_hi, r_lo = fit(hi[col], X), fit(lo[col], X)
                r_diff = fit(hi[col] - lo[col], X)
                h3_rows.append({**v, "variant": label(v), "primary": is_primary, "test": test,
                                "split": "terciles" if split == "group" else "halves",
                                "n_days": int(r_diff.nobs),
                                **dict(zip(["g5_high", "g5_high_se", "g5_high_p"], summarize_term(r_hi, g5))),
                                **dict(zip(["g5_low", "g5_low_se", "g5_low_p"], summarize_term(r_lo, g5))),
                                **dict(zip(["diff", "diff_se", "diff_p"], summarize_term(r_diff, g5)))})
    return pd.DataFrame(main_rows), pd.DataFrame(h3_rows)


if __name__ == "__main__":
    import sys
    panel_path = sys.argv[1] if len(sys.argv) > 1 else OUT_DIR / "return_panel_final.csv"
    market_path = sys.argv[2] if len(sys.argv) > 2 else OUT_DIR / "market_returns_final.csv"
    main, h3 = run(panel_path, market_path)
    main.to_csv(OUT_DIR / "step5_main_results.csv", index=False)
    h3.to_csv(OUT_DIR / "step4_h3_results.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
    fmt = lambda s: s.map(lambda x: f"{x:.4g}" if pd.notna(x) else "")
    for test in ["cck", "wh"]:
        t = main[main.test == test][["variant", "primary", "n_days", "n_post_high_days", "g5", "g5_se", "g5_p",
                                    "g7_postlow", "g7_p"]]
        print(f"\n=== Step 5 ({'standard CCK' if test == 'cck' else 'Wang-Hudson'}) ===")
        print(t.assign(**{c: fmt(t[c]) for c in ["g5", "g5_se", "g5_p", "g7_postlow", "g7_p"]}).to_string(index=False))
    if h3.empty:
        print("\n(H3 skipped: data/retail_attention.csv not built yet)")
        sys.exit(0)
    print("\n=== H3 (high vs low retail attention) ===")
    t = h3[["variant", "test", "split", "g5_high", "g5_high_p", "g5_low", "g5_low_p", "diff", "diff_se", "diff_p"]]
    print(t.assign(**{c: fmt(t[c]) for c in t.columns[3:]}).to_string(index=False))
