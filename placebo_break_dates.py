"""
Part C (placebo break dates, year fixed effects) and Part D (plan-literal
High-vs-Low check), exactly as pre-specified in
docs/addendum_2026-09-28.md, sections 4 and 5.

Reuses main_regression.py's functions unchanged. The primary spec (no
Robinhood, growth, High/Low dummies with middle-third baseline,
expanding cutoffs) is rerun with Post_t = 1{date >= fake date} for every
month-end 2017-06..2025-06 more than 182 days from 2022-11-30. Running the
same code with the real date must reproduce the Step 5 primary estimates;
that's checked below.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import investor_index as ii
import main_regression as mr
from build_csad import compute_csad

OUT_DIR, RES_DIR = Path("data"), Path("results")
REAL_DATE = pd.Timestamp("2022-11-30")
EXCLUDE_DAYS = 182
ONE_SIDED_CRIT = -1.645


def fit_drop_empty(y, X):
    """Some fake dates leave an interaction cell empty (e.g. no Post x Low
    days); a column of zeros can't be estimated, so it's dropped and that
    coefficient reported as missing."""
    X = X.loc[:, (X != 0).any(axis=0)]
    return mr.fit(y, X)


def one_sided_p(coef, p_two):
    """p-value for H1's direction (coefficient < 0)."""
    if np.isnan(coef):
        return np.nan
    return p_two / 2 if coef < 0 else 1 - p_two / 2


def load_primary():
    panel = pd.read_csv(OUT_DIR / "return_panel_final.csv", parse_dates=["date"])
    market = pd.read_csv(OUT_DIR / "market_returns_final.csv", parse_dates=["date"])
    csad = compute_csad(panel, market).set_index("date")
    days = csad.index
    ctrl = mr.controls_frame(days, csad["mkt_ret"].values, mr.load_vix().reindex(days).values,
                             pd.read_csv(OUT_DIR / "raw" / "fomc_dates.csv")["date"],
                             pd.read_csv(OUT_DIR / "raw" / "cpi_release_dates.csv")["date"])
    p = mr.PRIMARY
    ent = mr.entry_variant(p["hood"], p["mode"], p["form"], p["cutoff"], ii.load_components(), days)
    df = csad.join(ent).dropna(subset=["high", "low"])
    return df, ctrl.reindex(df.index)


def estimate(df, ctrl, break_date, extra_ctrl=None, slope_by_year=False):
    """g5 (Post x High) and g7 (Post x Low) for both tests at one break date."""
    d = df.copy()
    d["post"] = (d.index >= break_date).astype(int)
    out = {}
    for test in ["cck", "wh"]:
        X = mr.design(d, "dummy", test, controls=ctrl if test == "cck" else None)
        if extra_ctrl is not None:
            X = X.join(extra_ctrl)
        if slope_by_year:
            base = d["mkt_ret"] ** (2 if test == "cck" else 3)
            yrs = pd.get_dummies(d.index.year, prefix="yr", drop_first=True).set_index(d.index).astype(float)
            X = X.join(yrs.mul(base, axis=0).add_prefix("slope_"))
        res = fit_drop_empty(d["csad"] if test == "cck" else d["scsad"], X)
        g5, g7 = mr.key_terms("dummy", test)
        for name, term in [("g5", g5), ("g7", g7)]:
            coef, se, p = mr.summarize_term(res, term)
            out.update({f"{test}_{name}": coef, f"{test}_{name}_se": se, f"{test}_{name}_p": p,
                        f"{test}_{name}_t": coef / se if se else np.nan})
    return out


def placebo_dates():
    ends = pd.date_range("2017-06-30", "2025-06-30", freq="ME")
    return [f for f in ends if abs((f - REAL_DATE).days) > EXCLUDE_DAYS]


def within_year_share(df):
    """1 - R^2 of each entry dummy on year dummies: how much High/Low
    variation is left once calendar year is known."""
    out = {}
    for label, sub in [("all_days", df), ("post_days", df[df.index >= REAL_DATE])]:
        yrs = pd.get_dummies(sub.index.year).astype(float).values
        for col in ["high", "low"]:
            y = sub[col].values.astype(float)
            fitted = yrs @ np.linalg.lstsq(yrs, y, rcond=None)[0]
            ss_tot = ((y - y.mean()) ** 2).sum()
            out[f"{col}_{label}_within_year_share"] = float(1 - ((fitted - y.mean()) ** 2).sum() / ss_tot) if ss_tot else np.nan
    return out


def plan_literal(df, ctrl):
    """Part D: the Aug-31 plan's definition -- High_t = 1 on high-entry days,
    0 on low-entry days, middle days dropped. Built with design()'s
    continuous form with idx = High, which gives exactly the
    Rm^2 x High and Rm^2 x Post x High terms."""
    d = df[(df["high"] == 1) | (df["low"] == 1)].copy()
    d["idx"] = d["high"]
    out = {"n_days": int(len(d)), "n_post_high": int(((d["post"] == 1) & (d["high"] == 1)).sum())}
    for test in ["cck", "wh"]:
        X = mr.design(d, "continuous", test, controls=ctrl.reindex(d.index) if test == "cck" else None)
        res = mr.fit(d["csad"] if test == "cck" else d["scsad"], X)
        coef, se, p = mr.summarize_term(res, mr.key_terms("continuous", test)[0])
        out.update({f"{test}_g5": coef, f"{test}_g5_se": se, f"{test}_g5_p_two": p,
                    f"{test}_g5_p_one": one_sided_p(coef, p)})
    return out


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (dict name -> p)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, running, adj = len(items), 0.0, {}
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def figures(plac, real):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    RES_DIR.mkdir(exist_ok=True)
    names = {"cck": "Standard CCK", "wh": "Wang-Hudson (ours)"}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, t in zip(axes, ["cck", "wh"]):
        ax.hist(plac[f"{t}_g5"].dropna(), bins=25, color="0.7", edgecolor="white")
        ax.axvline(real[f"{t}_g5"], color="#d62728", lw=2, label="real date (2022-11-30)")
        ax.axvline(0, color="0.3", lw=0.8, ls=":")
        pct = (plac[f"{t}_g5"] <= real[f"{t}_g5"]).mean()
        ax.set_title(f"{names[t]}: real g5 more negative than {1 - pct:.0%} of fake dates", fontsize=10)
        ax.set_xlabel("g5 (Post x High) at fake break dates")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("number of fake dates")
    fig.tight_layout()
    fig.savefig(RES_DIR / "placebo_hist.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    for ax, t in zip(axes, ["cck", "wh"]):
        p = plac.sort_values("break_date")
        ax.fill_between(p["break_date"], p[f"{t}_g5"] - 1.96 * p[f"{t}_g5_se"],
                        p[f"{t}_g5"] + 1.96 * p[f"{t}_g5_se"], color="0.85", label="95% CI")
        ax.plot(p["break_date"], p[f"{t}_g5"], "o-", ms=3, color="0.3", label="fake break dates")
        ax.errorbar([REAL_DATE], [real[f"{t}_g5"]], yerr=[1.96 * real[f"{t}_g5_se"]], fmt="o",
                    color="#d62728", ms=7, label="real date (2022-11-30)")
        ax.axvspan(REAL_DATE - pd.Timedelta(days=EXCLUDE_DAYS), REAL_DATE + pd.Timedelta(days=EXCLUDE_DAYS),
                   color="#d62728", alpha=0.07)
        ax.axhline(0, color="0.3", lw=0.8, ls=":")
        ax.set_ylabel(f"g5, {names[t]}")
        ax.legend(fontsize=8, loc="best")
    axes[1].set_xlabel("break date used as the 'ChatGPT date'")
    fig.suptitle("g5 when the ChatGPT date is moved to fake month-ends")
    fig.tight_layout()
    fig.savefig(RES_DIR / "placebo_g5_line.png", dpi=200)
    plt.close(fig)


def main():
    RES_DIR.mkdir(exist_ok=True)
    df, ctrl = load_primary()

    real = estimate(df, ctrl, REAL_DATE)
    step5 = pd.read_csv(OUT_DIR / "step5_main_results.csv")
    prim = step5[step5["primary"] & ~step5["variant"].str.contains("lower-order")].set_index("test")
    assert np.isclose(real["cck_g5"], prim.loc["cck", "g5"]) and np.isclose(real["wh_g5"], prim.loc["wh", "g5"]), \
        "real-date estimate does not reproduce the Step 5 primary result"

    rows = [{"break_date": f, **estimate(df, ctrl, f)} for f in placebo_dates()]
    plac = pd.DataFrame(rows)
    plac.to_csv(RES_DIR / "placebo_break_dates.csv", index=False)

    summary = {"n_placebo_dates": len(plac), "real": real}
    for t in ["cck", "wh"]:
        g = plac[f"{t}_g5"]
        summary[f"{t}_empirical_p"] = float((g <= real[f"{t}_g5"]).mean())
        summary[f"{t}_share_placebo_neg_sig"] = float((plac[f"{t}_g5_t"] < ONE_SIDED_CRIT).mean())
        summary[f"{t}_share_placebo_g7_neg_sig"] = float((plac[f"{t}_g7_t"] < ONE_SIDED_CRIT).mean())
        summary[f"{t}_decision"] = ("effect NOT specific to ChatGPT's release" if summary[f"{t}_empirical_p"] > 0.05
                                    else "real date more extreme than 95% of placebo dates")

    yrs = pd.get_dummies(df.index.year, prefix="year", drop_first=True).set_index(df.index).astype(float)
    fe_a = estimate(df, ctrl, REAL_DATE, extra_ctrl=yrs)
    fe_b = estimate(df, ctrl, REAL_DATE, extra_ctrl=yrs, slope_by_year=True)
    summary["year_fe_levels"], summary["year_fe_levels_and_slopes"] = fe_a, fe_b
    summary["within_year_variation"] = within_year_share(df)
    summary["plan_literal"] = plan_literal(df, ctrl)

    family = {}
    for t in ["cck", "wh"]:
        family[f"{t}_placebo"] = summary[f"{t}_empirical_p"]
        family[f"{t}_year_fe_levels"] = one_sided_p(fe_a[f"{t}_g5"], fe_a[f"{t}_g5_p"])
        family[f"{t}_year_fe_slopes"] = one_sided_p(fe_b[f"{t}_g5"], fe_b[f"{t}_g5_p"])
        family[f"{t}_plan_literal"] = summary["plan_literal"][f"{t}_g5_p_one"]
    summary["holm"] = {k: {"raw_p": family[k], "holm_p": v} for k, v in holm(family).items()}
    for t in ["cck", "wh"]:
        g5b, pb = fe_b[f"{t}_g5"], one_sided_p(fe_b[f"{t}_g5"], fe_b[f"{t}_g5_p"])
        summary[f"{t}_year_fe_decision"] = ("g5 survives within-year identification" if (g5b < 0 and pb < 0.05)
                                            else "primary g5 driven by between-year differences (calendar confound)")

    (RES_DIR / "partC_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    figures(plac, real)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
