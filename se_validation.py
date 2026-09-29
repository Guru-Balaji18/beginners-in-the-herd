"""
Part H: which standard errors give honest p-values for the Post terms?
(docs/addendum2_2026-09-28.md, H2-H4)

H2  simulation: S5, kappa = 0 markets (herding constant over time, so every
    Post / g5 / g7 term is a true null), winsorized and unwinsorized,
    1,000 markets each, seed part 8. Methods: NW(5) [current], NW(21),
    NW(63), NW(126), 21-day moving-block pairs bootstrap (B = 999 per
    simulated market -- the feasible subset; 5,000 on real data).
H3  real data: primary spec with the best-calibrated method; Step 5 rerun
    on a per-day-winsorized panel.
H4  placebo / year-FE / plan-literal / Holm rerun with the best method.

Usage:
  py se_validation.py run [workers]   # H2 simulation, resumable
  py se_validation.py summarize       # H2 table + figure + best method
  py se_validation.py real            # H3 (i): primary spec, all methods
  py se_validation.py daywins         # H3 (ii): per-day winsorized Step 5
  py se_validation.py placebo         # H4
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import calibrated_test as ct
import main_regression as mr
import robust_se as rse
import simulate_herding_tests as sim

RES_DIR = Path("results")
RAW_PATH = RES_DIR / "se_validation_raw.csv"
PART_H = 8
N_MARKETS = 1000
B_SIM, B_REAL = 999, 5000
METHODS = ["nw5", "nw21", "nw63", "nw126", "boot"]
METHOD_LABEL = {"nw5": "Newey-West 5 lags (current)", "nw21": "Newey-West 21 lags", "nw63": "Newey-West 63 lags",
                "nw126": "Newey-West 126 lags", "boot": "block bootstrap (21-day)"}
# (regression, term) pairs checked; all are true nulls in these markets
TERMS = {"post_cck": ("d3_cck", "rm2_post"), "post_wh": ("d3_wh", "rm3_post"),
         "g5_cck": ("prim_cck", "rm2_post_high"), "g5_wh": ("prim_wh", "rm3_post_high"),
         "g7_cck": ("prim_cck", "rm2_post_low"), "g7_wh": ("prim_wh", "rm3_post_low")}
BAND = (0.036, 0.064)


def regressions(csad, df, ctrl):
    """The four regressions, as (y, X): the D3 two-way Post regressions
    (same columns as robustness_wang_hudson) and the primary Step 5 design."""
    c = csad
    rm = c["mkt_ret"]
    d3_cck = pd.DataFrame({"abs_rm": rm.abs(), "rm2": rm ** 2, "rm2_post": rm ** 2 * c["post"]})
    d3_wh = pd.DataFrame({"mkt_ret": rm, "rm2": rm ** 2, "rm3": rm ** 3, "rm3_post": rm ** 3 * c["post"]})
    out = {"d3_cck": (c["csad"], d3_cck), "d3_wh": (c["scsad"], d3_wh)}
    for test in ["cck", "wh"]:
        out[f"prim_{test}"] = ct.primary_xy(df, ctrl, test)
    return out


def t_stats(regs, rng, B):
    row = {}
    for method in METHODS:
        fits = {name: rse.fit_with(method, y, X, rng=rng, B=B) for name, (y, X) in regs.items()}
        for key, (reg, term) in TERMS.items():
            row[f"{key}_{method}"] = float(fits[reg].tvalues[term])
        if method == "nw5":
            for key, (reg, term) in TERMS.items():
                row[f"{key}_coef"] = float(fits[reg].params[term])
    return row


# =====================================================================
# H2 simulation
# =====================================================================
_CAL = _CTX = None


def _init():
    global _CAL, _CTX
    _CAL = sim.load_calibration()
    _CTX = ct.load_context(_CAL)


def _work(task):
    winsorize, rep = task
    rng = ct.rng_for(PART_H, "S5", rep)
    R, mkt = sim.simulate_returns(_CAL, "S5", 0, rng, winsorize=winsorize)
    regs = regressions(*ct.market_frames(R, mkt, _CTX))
    boot_rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, PART_H, 99, rep, int(winsorize)]))
    return {"winsorized": winsorize, "rep": rep, **t_stats(regs, boot_rng, B_SIM)}


def run_all(workers=12):
    import multiprocessing as mp
    RES_DIR.mkdir(exist_ok=True)
    done = set()
    if RAW_PATH.exists():
        prev = pd.read_csv(RAW_PATH, usecols=["winsorized", "rep"])
        done = set(zip(prev["winsorized"], prev["rep"]))
    todo = [(w, r) for w in [True, False] for r in range(N_MARKETS) if (w, r) not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    header, t0 = not RAW_PATH.exists(), time.time()
    with mp.Pool(workers, initializer=_init) as pool, open(RAW_PATH, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(_work, todo, chunksize=2), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % 100 == 0:
                f.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)} done, {rate:.2f}/s, ~{(len(todo) - i) / rate / 60:.0f} min left", flush=True)


def summarize():
    raw = pd.read_csv(RAW_PATH)
    rows = []
    for w, g in raw.groupby("winsorized"):
        for key in TERMS:
            for m in METHODS:
                t = g[f"{key}_{m}"]
                rows.append({"winsorized": w, "term": key, "method": m, "n_markets": len(g),
                             "false_alarm": float((t < sim.ONE_SIDED_CRIT).mean()),
                             "two_sided_rejection": float((t.abs() > 1.96).mean()),
                             "sd_t": float(t.std())})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES_DIR / "se_validation_summary.csv", index=False)

    # pre-registered choice: winsorized cells Post-CCK, Post-WH, g5-CCK, g5-WH
    crit_terms = ["post_cck", "post_wh", "g5_cck", "g5_wh"]
    score = {}
    for m in METHODS:
        s_w = tab[(tab.winsorized) & (tab.method == m) & tab.term.isin(crit_terms)]["false_alarm"]
        s_u = tab[(~tab.winsorized) & (tab.method == m) & tab.term.isin(crit_terms)]["false_alarm"]
        score[m] = {"mad_winsorized": float((s_w - 0.05).abs().mean()), "mad_unwinsorized": float((s_u - 0.05).abs().mean()),
                    "all_four_winsorized_in_band": bool(s_w.between(*BAND).all())}
    best = min(METHODS, key=lambda m: (score[m]["mad_winsorized"], score[m]["mad_unwinsorized"]))
    choice = {"scores": score, "best_method": best, "best_label": METHOD_LABEL[best],
              "calibrated": score[best]["all_four_winsorized_in_band"], "n_markets_per_setting": int(raw.groupby("winsorized").size().min()),
              "bootstrap_reps_in_simulation": B_SIM}
    (RES_DIR / "se_validation_choice.json").write_text(json.dumps(choice, indent=1))
    figure(tab)
    pd.set_option("display.width", 200)
    print(tab.pivot_table(index=["winsorized", "term"], columns="method", values="false_alarm")[METHODS].round(3).to_string())
    print(tab.pivot_table(index=["winsorized", "term"], columns="method", values="sd_t")[METHODS].round(2).to_string())
    print(json.dumps(choice, indent=1))
    return choice


def figure(tab):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    terms = ["post_cck", "post_wh", "g5_cck", "g5_wh", "g7_cck", "g7_wh"]
    names = {"post_cck": "Post, CCK", "post_wh": "Post, WH", "g5_cck": "g5 Post x High, CCK",
             "g5_wh": "g5 Post x High, WH", "g7_cck": "g7 Post x Low, CCK", "g7_wh": "g7 Post x Low, WH"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    cols = ["#7f7f7f", "#aec7e8", "#6baed6", "#2171b5", "#d62728"]
    for ax, w in zip(axes, [True, False]):
        sub = tab[tab.winsorized == w]
        x = np.arange(len(terms))
        for j, m in enumerate(METHODS):
            v = [100 * sub[(sub.term == t) & (sub.method == m)]["false_alarm"].iloc[0] for t in terms]
            ax.bar(x + (j - 2) * 0.16, v, 0.16, color=cols[j], label=METHOD_LABEL[m])
        ax.axhspan(100 * BAND[0], 100 * BAND[1], color="#2ca02c", alpha=0.18, label="correct (3.6-6.4%)")
        ax.set_xticks(x)
        ax.set_xticklabels([names[t] for t in terms], rotation=25, ha="right", fontsize=8)
        ax.set_title("winsorized as in our pipeline" if w else "no winsorization", fontsize=10)
    axes[0].set_ylabel("% of no-effect markets flagged 'significant'")
    axes[0].legend(fontsize=7, loc="upper left")
    fig.suptitle("False alarms on ChatGPT-date terms that are truly zero (S5, 1,000 simulated markets each)")
    fig.tight_layout()
    fig.savefig(RES_DIR / "se_validation.png", dpi=200)
    plt.close(fig)


# =====================================================================
# H3 / H4 on real data
# =====================================================================
def best_method():
    return json.loads((RES_DIR / "se_validation_choice.json").read_text())["best_method"]


def real_frames(panel_path=mr.OUT_DIR / "return_panel_final.csv", market_path=mr.OUT_DIR / "market_returns_final.csv"):
    cal = sim.load_calibration()
    ctx = ct.load_context(cal)
    from build_csad import compute_csad
    panel = pd.read_csv(panel_path, parse_dates=["date"])
    market = pd.read_csv(market_path, parse_dates=["date"])
    csad = compute_csad(panel, market).set_index("date")
    ctrl = mr.controls_frame(csad.index, csad["mkt_ret"].values, mr.load_vix().reindex(csad.index).values,
                             ctx["fomc"], ctx["cpi"])
    df = csad.join(ctx["entry"]).dropna(subset=["high", "low"])
    return csad, df, ctrl.reindex(df.index)


def real(panel_path=mr.OUT_DIR / "return_panel_final.csv", market_path=mr.OUT_DIR / "market_returns_final.csv",
         tag="pooled winsorization (registered)"):
    csad, df, ctrl = real_frames(panel_path, market_path)
    rows = []
    for test in ["cck", "wh"]:
        y, X = ct.primary_xy(df, ctrl, test)
        g5, g7 = mr.key_terms("dummy", test)
        for m in METHODS:
            rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, PART_H, 7777]))
            res = rse.fit_with(m, y, X, rng=rng, B=B_REAL)
            for name, term in [("g5", g5), ("g7_postlow", g7)]:
                coef, se = res.params[term], res.bse[term]
                rows.append({"panel": tag, "test": test, "term": name, "method": m, "coef": coef, "se": se,
                             "t": coef / se, "p_one_sided": float(rse.norm.cdf(coef / se)),
                             "p_two_sided": float(2 * rse.norm.sf(abs(coef / se)))})
    return pd.DataFrame(rows)


def unclipped_panel(panel_path=mr.OUT_DIR / "return_panel_final.csv"):
    """Returns before the pooled clip, rebuilt exactly as in D2."""
    p = pd.read_csv(panel_path, usecols=["date", "ticker", "close", "ret"], parse_dates=["date"])
    p = p.sort_values(["ticker", "date"])
    lo, hi = p["ret"].min(), p["ret"].max()
    clipped = (p["ret"] <= lo + 1e-12) | (p["ret"] >= hi - 1e-12)
    p["ret"] = p["ret"].where(~clipped, p.groupby("ticker")["close"].pct_change())
    return p.dropna(subset=["ret"])[["date", "ticker", "ret"]]


def build_daywins_panel():
    p = unclipped_panel()
    q = p.groupby("date")["ret"].quantile([0.001, 0.999]).unstack()
    q.columns = ["lo", "hi"]
    p = p.join(q, on="date")
    n_clipped = int(((p["ret"] < p["lo"]) | (p["ret"] > p["hi"])).sum())
    p["ret"] = p["ret"].clip(p["lo"], p["hi"])
    p = p.drop(columns=["lo", "hi"])
    mkt = p.groupby("date").agg(mkt_ret_eq=("ret", "mean"), n_stocks=("ret", "size")).reset_index()
    pp, mp_ = mr.OUT_DIR / "return_panel_daywins.csv", mr.OUT_DIR / "market_returns_daywins.csv"
    p.to_csv(pp, index=False)
    mkt.to_csv(mp_, index=False)
    return pp, mp_, n_clipped, len(p)


def daywins():
    pp, mp_, n_clipped, n = build_daywins_panel()
    print(f"per-day winsorized panel: {n:,} stock-days, {n_clipped:,} clipped ({n_clipped / n:.2%})")
    main, h3 = mr.run(pp, mp_)
    main.to_csv(RES_DIR / "step5_daywins_results.csv", index=False)
    h3.to_csv(RES_DIR / "step5_daywins_h3_results.csv", index=False)
    orig = pd.read_csv(mr.OUT_DIR / "step5_main_results.csv")
    cmp = orig[["variant", "test", "g5", "g5_p", "g7_postlow", "g7_p"]].merge(
        main[["variant", "test", "g5", "g5_p", "g7_postlow", "g7_p"]], on=["variant", "test"], suffixes=("_pooled", "_perday"))
    cmp.to_csv(RES_DIR / "step5_pooled_vs_daywins.csv", index=False)
    rows = real(pp, mp_, tag="per-day winsorization")
    rows.to_csv(RES_DIR / "real_se_daywins.csv", index=False)
    pd.set_option("display.width", 220)
    print(cmp.round(4).to_string(index=False))
    b = best_method()
    print(rows[rows.method.isin(["nw5", b])].round(4).to_string(index=False))


def placebo():
    """H4: rerun the SE-dependent parts of Part C with the best method by
    routing main_regression.fit through it (the module's code is unchanged)."""
    import placebo_break_dates as pb
    m = best_method()
    rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, PART_H, 8888]))
    mr.fit = lambda y, X: rse.fit_with(m, y, X, rng=rng, B=B_REAL)
    df, ctrl = pb.load_primary()
    real_ = pb.estimate(df, ctrl, pb.REAL_DATE)
    plac = pd.DataFrame([{"break_date": f, **pb.estimate(df, ctrl, f)} for f in pb.placebo_dates()])
    plac.to_csv(RES_DIR / "placebo_break_dates_H.csv", index=False)
    s = {"se_method": METHOD_LABEL[m], "real": real_}
    for t in ["cck", "wh"]:
        s[f"{t}_empirical_p"] = float((plac[f"{t}_g5"].dropna() <= real_[f"{t}_g5"]).mean())
        s[f"{t}_share_placebo_neg_sig"] = float((plac[f"{t}_g5_t"].dropna() < sim.ONE_SIDED_CRIT).mean())
        s[f"{t}_share_placebo_g7_neg_sig"] = float((plac[f"{t}_g7_t"].dropna() < sim.ONE_SIDED_CRIT).mean())
    yrs = pd.get_dummies(df.index.year, prefix="year", drop_first=True).set_index(df.index).astype(float)
    fe_a = pb.estimate(df, ctrl, pb.REAL_DATE, extra_ctrl=yrs)
    fe_b = pb.estimate(df, ctrl, pb.REAL_DATE, extra_ctrl=yrs, slope_by_year=True)
    s["year_fe_levels"], s["year_fe_levels_and_slopes"] = fe_a, fe_b
    s["plan_literal"] = pb.plan_literal(df, ctrl)
    fam = {}
    for t in ["cck", "wh"]:
        fam[f"{t}_placebo"] = s[f"{t}_empirical_p"]
        fam[f"{t}_year_fe_levels"] = pb.one_sided_p(fe_a[f"{t}_g5"], fe_a[f"{t}_g5_p"])
        fam[f"{t}_year_fe_slopes"] = pb.one_sided_p(fe_b[f"{t}_g5"], fe_b[f"{t}_g5_p"])
        fam[f"{t}_plan_literal"] = s["plan_literal"][f"{t}_g5_p_one"]
        pbb = pb.one_sided_p(fe_b[f"{t}_g5"], fe_b[f"{t}_g5_p"])
        s[f"{t}_year_fe_decision"] = ("g5 survives within-year identification" if (fe_b[f"{t}_g5"] < 0 and pbb < 0.05)
                                     else "primary g5 driven by between-year differences (calendar confound)")
        s[f"{t}_decision"] = ("effect NOT specific to ChatGPT's release" if s[f"{t}_empirical_p"] > 0.05
                              else "real date more extreme than 95% of placebo dates")
    s["holm"] = {k: {"raw_p": fam[k], "holm_p": v} for k, v in pb.holm(fam).items()}
    (RES_DIR / "partC_summary_H.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps(s, indent=1, default=str))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summarize"
    if cmd == "run":
        run_all(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    elif cmd == "summarize":
        summarize()
    elif cmd == "real":
        out = real()
        out.to_csv(RES_DIR / "real_se_comparison.csv", index=False)
        pd.set_option("display.width", 200)
        print(out.round(4).to_string(index=False))
    elif cmd == "daywins":
        daywins()
    elif cmd == "placebo":
        placebo()
