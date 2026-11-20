"""
Step 8 of the research plan: the remaining pre-registered analyses (D8,
docs/addendum4_2026-11-19_step8.md, committed and pushed before this file).

  8a effect size in basis points from the primary CCK fit
  8b alternative break date: GPT-4 release (2023-03-14)
  8c exclude the seven largest technology companies (8 tickers)
  8d liquidity-weighted market (the panel's mkt_ret_vw, close x volume weights)

Primary specification and registered pooled-winsorized panel throughout.
Standard errors: Newey-West(5) (registered primary) and the 21-day
moving-block bootstrap, B = 5,000 (best-calibrated for CCK in Part H).
Wang-Hudson results are reported but, under the plan's H4 decision rule,
not used as evidence.

Usage:  py step8_analyses.py     -> results/step8_results.csv, results/step8_summary.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

import investor_index as ii
import main_regression as mr
import placebo_break_dates as pb
import robust_se as rse
from build_csad import compute_csad
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression

RES_DIR = Path("results")
GPT4_DATE = pd.Timestamp("2023-03-14")
BIG_TECH = ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"]
B_BOOT = 5000
SEED = [20260928, 11]
TERMS = {"cck": {"g2": "rm2", "g3": "rm2_post", "g4": "rm2_high", "g5": "rm2_post_high",
                 "g6": "rm2_low", "g7": "rm2_post_low"},
         "wh": {"g2": "rm3", "g3": "rm3_post", "g4": "rm3_high", "g5": "rm3_post_high",
                "g6": "rm3_low", "g7": "rm3_post_low"}}


# =====================================================================
# Pure helpers (tested in test_step8.py)
# =====================================================================
def effect_sizes(params, sigma, test="cck"):
    """Curvature contribution to CSAD (CCK) or SCSAD (WH), in basis points,
    for a 2-SD market move: coefficient sum x (2 sigma)^p x 10,000, with
    p = 2 for CCK and p = 3 for WH."""
    t = TERMS[test]
    g = {k: float(params[v]) for k, v in t.items()}
    scale = (2 * sigma) ** (2 if test == "cck" else 3) * 1e4
    cells = {}
    for period in ["pre", "post"]:
        p = 1 if period == "post" else 0
        for grp in ["low", "middle", "high"]:
            hi, lo = int(grp == "high"), int(grp == "low")
            cells[(period, grp)] = (g["g2"] + g["g3"] * p + g["g4"] * hi + g["g5"] * p * hi
                                    + g["g6"] * lo + g["g7"] * p * lo) * scale
    pmp = {grp: cells[("post", grp)] - cells[("pre", grp)] for grp in ["low", "middle", "high"]}
    return {"g5_bp": g["g5"] * scale, "cells_bp": cells, "post_minus_pre_bp": pmp, "scale": scale}


def exclude_tickers(panel, tickers):
    return panel[~panel["ticker"].isin(set(tickers))].copy()


def ew_market(panel):
    return panel.groupby("date", as_index=False)["ret"].mean().rename(columns={"ret": "mkt_ret_eq"})


def post_dummy(dates, break_date):
    return (pd.DatetimeIndex(dates) >= break_date).astype(int)


def placebo_percentile(g5, placebo_values):
    v = pd.Series(placebo_values).dropna()
    return float((v <= g5).mean())


# =====================================================================
# Data and fits
# =====================================================================
def load_panel_market():
    panel = pd.read_csv(mr.OUT_DIR / "return_panel_final.csv", usecols=["date", "ticker", "ret"], parse_dates=["date"])
    market = pd.read_csv(mr.OUT_DIR / "market_returns_final.csv", parse_dates=["date"])
    return panel, market


def frames_from(panel, market):
    """Like placebo_break_dates.load_primary, for any panel and any market
    series (market needs columns date, mkt_ret_eq)."""
    csad = compute_csad(panel, market).set_index("date")
    days = csad.index
    ctrl = mr.controls_frame(days, csad["mkt_ret"].values, mr.load_vix().reindex(days).values,
                             pd.read_csv(mr.RAW / "fomc_dates.csv")["date"],
                             pd.read_csv(mr.RAW / "cpi_release_dates.csv")["date"])
    p = mr.PRIMARY
    ent = mr.entry_variant(p["hood"], p["mode"], p["form"], p["cutoff"], ii.load_components(), days)
    df = csad.join(ent).dropna(subset=["high", "low"])
    return df, ctrl.reindex(df.index)


def xy(df, ctrl, test):
    X = mr.design(df, "dummy", test, controls=ctrl if test == "cck" else None)
    return (df["csad"] if test == "cck" else df["scsad"]), X


def fit_nw5(df, ctrl, test):
    return mr.fit(*xy(df, ctrl, test))


def fit_boot(df, ctrl, test, k):
    rng = np.random.default_rng(np.random.SeedSequence(SEED + [k]))
    return rse.fit_with("boot", *xy(df, ctrl, test), rng=rng, B=B_BOOT)


def key_rows(df, ctrl, analysis, k):
    """g5 and g7 for both tests under NW(5) and the block bootstrap."""
    rows, out = [], {}
    for test in ["cck", "wh"]:
        g5n, g7n = mr.key_terms("dummy", test)
        for method, res in [("nw5", fit_nw5(df, ctrl, test)), ("boot", fit_boot(df, ctrl, test, k))]:
            for name, term in [("g5", g5n), ("g7", g7n)]:
                coef, se = float(res.params[term]), float(res.bse[term])
                r = {"analysis": analysis, "test": test, "term": name, "method": method, "coef": coef, "se": se,
                     "t": coef / se, "p_one_sided": float(norm.cdf(coef / se)), "p_two_sided": float(2 * norm.sf(abs(coef / se))),
                     "n_days": int(len(df)), "n_post_high_days": int(((df["post"] == 1) & (df["high"] == 1)).sum())}
                rows.append(r)
                out[(test, name, method)] = r
    return rows, out


def depends_on(full, alt):
    """8c/8d rule: CCK g5 changes sign, or its bootstrap one-sided p crosses 0.05."""
    f, a = full[("cck", "g5", "boot")], alt[("cck", "g5", "boot")]
    sign_change = np.sign(f["coef"]) != np.sign(a["coef"])
    crossed = (f["p_one_sided"] < 0.05) != (a["p_one_sided"] < 0.05)
    return bool(sign_change or crossed)


# =====================================================================
# The four analyses
# =====================================================================
def main():
    RES_DIR.mkdir(exist_ok=True)
    panel, market = load_panel_market()
    df, ctrl = frames_from(panel, market[["date", "mkt_ret_eq"]])
    summary, rows = {}, []

    # full-sample reference (same as Step 5 primary)
    full_rows, full = key_rows(df, ctrl, "full sample (reference)", 1)
    rows += full_rows

    # 8a effect size
    sigma = float(df["mkt_ret"].std())
    y, X = xy(df, ctrl, "cck")
    names, beta, draws = rse.bootstrap_draws(y, X, B_BOOT, np.random.default_rng(np.random.SeedSequence(SEED + [1])))
    pos = {n: i for i, n in enumerate(names)}
    es = effect_sizes(dict(zip(names, beta)), sigma, "cck")
    sc = es["scale"]
    t = TERMS["cck"]

    def ci(comb):
        v = sum(draws[:, pos[t[g]]] for g in comb) * sc
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    big = df["mkt_ret"].abs() >= 2 * sigma
    mean_csad_big_bp = float(df.loc[big, "csad"].mean() * 1e4)
    wh_es = effect_sizes(fit_nw5(df, ctrl, "wh").params, sigma, "wh")
    summary["8a_effect_size"] = {
        "sigma_daily_market_return": sigma, "two_sd_move_pct": 200 * sigma,
        "mean_csad_bp_on_2sd_days": mean_csad_big_bp, "n_2sd_days": int(big.sum()),
        "g5_bp": es["g5_bp"], "g5_bp_ci95_boot": ci(["g5"]),
        "g5_pct_of_mean_csad_on_2sd_days": 100 * es["g5_bp"] / mean_csad_big_bp,
        "post_minus_pre_bp": es["post_minus_pre_bp"],
        "post_minus_pre_ci95_boot": {"high": ci(["g3", "g5"]), "middle": ci(["g3"]), "low": ci(["g3", "g7"])},
        "cells_bp": {f"{a}/{b}": v for (a, b), v in es["cells_bp"].items()},
        "economically_negligible_g5": bool(abs(es["g5_bp"]) < 1.0),
        "wh_for_completeness": {"g5_bp": wh_es["g5_bp"], "post_minus_pre_bp": wh_es["post_minus_pre_bp"]}}

    # 8b GPT-4 break date
    d4 = df.copy()
    d4["post"] = post_dummy(d4.index, GPT4_DATE)
    gpt_rows, gpt = key_rows(d4, ctrl, "8b GPT-4 date (2023-03-14)", 2)
    rows += gpt_rows
    plac = pd.read_csv(RES_DIR / "placebo_break_dates.csv")
    pct = {tt: placebo_percentile(gpt[(tt, "g5", "nw5")]["coef"], plac[f"{tt}_g5"]) for tt in ["cck", "wh"]}
    c = gpt[("cck", "g5", "boot")]
    summary["8b_gpt4"] = {"placebo_percentile_g5": pct, "n_placebo": int(plac["cck_g5"].notna().sum()),
                          "decision": ("herding tracks the GPT-4 release" if (c["coef"] < 0 and c["p_one_sided"] < 0.05
                                                                             and pct["cck"] <= 0.05)
                                       else "herding does not track the GPT-4 release")}

    # 8c exclude the largest tech companies
    p_ex = exclude_tickers(panel, BIG_TECH)
    df_ex, ctrl_ex = frames_from(p_ex, ew_market(p_ex))
    ex_rows, ex = key_rows(df_ex, ctrl_ex, "8c without the 7 largest tech companies", 3)
    rows += ex_rows
    csad_ex = compute_csad(p_ex, ew_market(p_ex))
    base_ex = {"cck_rm2_t": float(standard_cck_regression(csad_ex).tvalues["rm2"]),
               "wh_rm3_t": float(wang_hudson_scsad_regression(csad_ex).tvalues["rm3"])}
    summary["8c_exclude_big_tech"] = {"tickers_removed": BIG_TECH,
                                      "stock_days_removed": int(len(panel) - len(p_ex)),
                                      "base_herding_t": base_ex,
                                      "decision": ("result depends on these stocks" if depends_on(full, ex)
                                                   else "result does not depend on these stocks")}

    # 8d liquidity-weighted market
    vw = market[["date", "mkt_ret_vw"]].rename(columns={"mkt_ret_vw": "mkt_ret_eq"})
    df_vw, ctrl_vw = frames_from(panel, vw)
    vw_rows, vwr = key_rows(df_vw, ctrl_vw, "8d liquidity-weighted market", 4)
    rows += vw_rows
    summary["8d_liquidity_weighted"] = {"note": "weights are close x volume, a liquidity proxy, not market cap",
                                        "decision": ("result depends on the market weighting" if depends_on(full, vwr)
                                                     else "result does not depend on the market weighting")}

    # Holm across the three CCK bootstrap one-sided g5 p-values
    fam = {"8b_gpt4": gpt[("cck", "g5", "boot")]["p_one_sided"],
           "8c_exclude_big_tech": ex[("cck", "g5", "boot")]["p_one_sided"],
           "8d_liquidity_weighted": vwr[("cck", "g5", "boot")]["p_one_sided"]}
    summary["holm_cck_g5_boot"] = {k: {"raw_p": fam[k], "holm_p": v} for k, v in pb.holm(fam).items()}

    tab = pd.DataFrame(rows)
    tab.to_csv(RES_DIR / "step8_results.csv", index=False)
    (RES_DIR / "step8_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    pd.set_option("display.width", 220)
    print(tab.round(4).to_string(index=False))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
