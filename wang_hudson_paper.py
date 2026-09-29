"""
Part E completed with the paper (docs/wang_hudson_spec.md E1/E2; choices
fixed in docs/deviations_log.md D6 before this file was written).

Paper-exact ingredients (Wang & Hudson, CC-BY submitted manuscript):
  log returns ln(1+R); equal-weighted market of log returns; CSAD Eq.1;
  SCSAD = +CSAD if Rm > 0, -CSAD if Rm < 0 (Rm = 0 undefined -> dropped);
  OLS with White HC1 standard errors ("robust regression", p.23).
Variants:
  wh_paper    Solution 2, Eq.3: SCSAD = a + g1 Rm + g2 Rm^2 + g3 Rm^3, herding g3 < 0
  cck_paper   Eq.2: CSAD = a + g1 Rm + g2 |Rm| + g3 Rm^2, herding g3 < 0
  sol1_paper  Solution 1: Eq.2 with a = 0
  sol3_abs1   Solution 3: Eq.2 on days with |Rm| >= 1%
  sol3_top10  Solution 3: Eq.2 on the largest 10% of days by |Rm|

Usage:
  py wang_hudson_paper.py e5run [w]     # 80,000 Part B markets (resumable)
  py wang_hudson_paper.py e5summary     # size/power + E6 verdict
  py wang_hudson_paper.py replicate     # the paper's own no-herding simulation
  py wang_hudson_paper.py frun [w]      # Part F addition (same seeds as Part F)
  py wang_hudson_paper.py fsummary
  py wang_hudson_paper.py hrun [w]      # Part H addition (same seeds as Part H)
  py wang_hudson_paper.py hsummary
  py wang_hudson_paper.py real          # real-data paper-exact results
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

import calibrated_test as ct
import main_regression as mr
import robust_se as rse
import simulate_herding_tests as sim
from build_csad import CHATGPT_RELEASE

RES_DIR = Path("results")
E5_RAW = RES_DIR / "wh_paper_e5_raw.csv"
F_RAW = RES_DIR / "calibrated_paper_raw.csv"
H_RAW = RES_DIR / "se_validation_paper_raw.csv"
PAPER_CRIT = -1.96                       # paper's rule: two-sided 5%
VARIANTS = ["wh_paper", "cck_paper", "sol1_paper", "sol3_abs1", "sol3_top10"]
LABEL = {"wh_paper": "WH Solution 2 (paper-exact)", "cck_paper": "CCK Eq.2 (paper-exact)",
         "sol1_paper": "Solution 1: no constant (paper-exact)", "sol3_abs1": "Solution 3: |Rm| >= 1%",
         "sol3_top10": "Solution 3: largest 10% |Rm|"}
H_METHODS = ["hc1", "nw5", "nw21", "nw63", "nw126", "boot"]


# =====================================================================
# Paper-exact building blocks
# =====================================================================
def log_csad(R, dates):
    """Simple returns (T x N) -> paper-exact CSAD/SCSAD frame on log returns."""
    r = np.log1p(R)
    m = r.mean(axis=1)
    c = np.abs(r - m[:, None]).mean(axis=1)
    d = pd.to_datetime(pd.Index(dates))
    out = pd.DataFrame({"csad": c, "scsad": np.where(m > 0, c, np.where(m < 0, -c, np.nan)), "mkt_ret": m,
                        "post": (d >= CHATGPT_RELEASE).astype(int)}, index=d)
    out.index.name = "date"
    return out


def hc1(y, X, const=True):
    ok = y.notna() & X.notna().all(axis=1)
    Xo = add_constant(X[ok], has_constant="add") if const else X[ok]
    return OLS(y[ok], Xo).fit(cov_type="HC1")


def eq2_x(c):
    rm = c["mkt_ret"]
    return pd.DataFrame({"rm": rm, "abs_rm": rm.abs(), "rm2": rm ** 2}, index=c.index)


def eq3_x(c):
    rm = c["mkt_ret"]
    return pd.DataFrame({"rm": rm, "rm2": rm ** 2, "rm3": rm ** 3}, index=c.index)


def paper_variants(c):
    """t (and coef) of each variant's herding coefficient."""
    fits = {"wh_paper": (hc1(c["scsad"], eq3_x(c)), "rm3"),
            "cck_paper": (hc1(c["csad"], eq2_x(c)), "rm2"),
            "sol1_paper": (hc1(c["csad"], eq2_x(c), const=False), "rm2")}
    a = c["mkt_ret"].abs()
    for name, keep in [("sol3_abs1", a >= 0.01), ("sol3_top10", a >= a.quantile(0.90))]:
        s = c[keep]
        fits[name] = (hc1(s["csad"], eq2_x(s)), "rm2")
    out = {}
    for name, (res, term) in fits.items():
        out[f"{name}_coef"] = float(res.params[term])
        out[f"{name}_t"] = float(res.tvalues[term])
    return out


# =====================================================================
# E5: 80,000 Part B markets (same seeds)
# =====================================================================
_CAL = _CTX = None


def _init(ctx=False):
    global _CAL, _CTX
    _CAL = sim.load_calibration()
    if ctx:
        _CTX = ct.load_context(_CAL)


def _init_ctx():
    _init(ctx=True)


def _e5_one(task):
    w, s, k, rep = task
    R, _ = sim.simulate_returns(_CAL, s, k, sim.rng_for(s, rep), winsorize=w)
    return {"winsorized": w, "scenario": s, "kappa": k, "rep": rep, **paper_variants(log_csad(R, _CAL["dates"]))}


def _pool_run(path, keys, todo_all, work, init, workers, every=2000):
    import multiprocessing as mp
    RES_DIR.mkdir(exist_ok=True)
    done = set()
    if path.exists():
        prev = pd.read_csv(path, usecols=keys)
        done = set(map(tuple, prev[keys].itertuples(index=False, name=None)))
    todo = [t for t in todo_all if t not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    header, t0 = not path.exists(), time.time()
    with mp.Pool(workers, initializer=init) as pool, open(path, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(work, todo, chunksize=4), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % every == 0:
                f.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)} done, {rate:.1f}/s, ~{(len(todo) - i) / rate / 60:.0f} min left", flush=True)


def e5_run(workers=12):
    todo = [(w, s, k, r) for w in [True, False] for s in sim.SCENARIOS for r in range(sim.REPS) for k in sim.KAPPAS]
    _pool_run(E5_RAW, ["winsorized", "scenario", "kappa", "rep"], todo, _e5_one, _init, workers)


def e5_summary():
    raw = pd.read_csv(E5_RAW)
    old = pd.read_csv(RES_DIR / "wh_variants_raw.csv")[["winsorized", "scenario", "kappa", "rep", "wh_old_t", "cck_t"]]
    both = raw.merge(old, on=["winsorized", "scenario", "kappa", "rep"])
    rows = []
    for (w, s, k), g in both.groupby(["winsorized", "scenario", "kappa"]):
        for name, col in [(v, f"{v}_t") for v in VARIANTS] + [("wh_old", "wh_old_t"), ("cck", "cck_t")]:
            t = g[col]
            rows.append({"winsorized": w, "scenario": s, "kappa": k, "variant": name, "n": len(g),
                         "flag_one_sided": float((t < sim.ONE_SIDED_CRIT).mean()),
                         "flag_paper_two_sided": float((t < PAPER_CRIT).mean()),
                         "median_t": float(t.median())})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES_DIR / "wh_paper_e5_size_power.csv", index=False)

    def rate(v, s="S5", w=True, col="flag_one_sided"):
        return float(tab[(tab.variant == v) & (tab.scenario == s) & (tab.winsorized == w) & (tab.kappa == 0)][col].iloc[0])
    p, o = rate("wh_paper"), rate("wh_old")
    verdict = "a" if (0.036 <= p <= 0.064 and o > 0.064) else ("b" if p > 0.064 else "c")
    corr = float(both[["wh_paper_t", "wh_old_t"]].corr().iloc[0, 1])
    out = {"S5_winsorized_kappa0_false_alarm": {"wh_paper": p, "wh_old": o},
           "S5_winsorized_kappa0_false_alarm_paper_rule": {"wh_paper": rate("wh_paper", col="flag_paper_two_sided"),
                                                           "wh_old": rate("wh_old", col="flag_paper_two_sided")},
           "verdict": verdict, "corr_t_wh_paper_vs_wh_old": corr, "n_markets": int(len(both))}
    (RES_DIR / "wh_paper_e6_verdict.json").write_text(json.dumps(out, indent=1))
    e5_figure(tab)
    pd.set_option("display.width", 230)
    k0 = tab[tab.kappa == 0]
    print(k0.pivot_table(index=["winsorized", "scenario"], columns="variant", values="flag_one_sided").round(3).to_string())
    print(k0.pivot_table(index=["winsorized", "scenario"], columns="variant", values="flag_paper_two_sided").round(3).to_string())
    print(tab[tab.scenario == "S5"].pivot_table(index=["winsorized", "kappa"], columns="variant",
                                                values="flag_one_sided").round(3).to_string())
    print(json.dumps(out, indent=1))


def e5_figure(tab):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = ["wh_old", "wh_paper", "cck", "cck_paper", "sol1_paper", "sol3_abs1", "sol3_top10"]
    names = {"wh_old": "WH, ours (old)", "cck": "Standard CCK, ours", **LABEL}
    cols = ["#d62728", "#ff9896", "#1f77b4", "#aec7e8", "#9467bd", "#2ca02c", "#98df8a"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), sharey=True)
    for ax, w in zip(axes, [True, False]):
        sub = tab[(tab.winsorized == w) & (tab.kappa == 0)]
        x = np.arange(len(sim.SCENARIOS))
        for j, v in enumerate(show):
            vals = [100 * sub[(sub.scenario == s) & (sub.variant == v)]["flag_one_sided"].iloc[0] for s in sim.SCENARIOS]
            ax.bar(x + (j - 3) * 0.12, vals, 0.12, color=cols[j], label=names[v])
        ax.axhspan(3.6, 6.4, color="0.5", alpha=0.25, label="correct (3.6-6.4%)")
        ax.set_xticks(x)
        ax.set_xticklabels(list(sim.SCENARIOS))
        ax.set_ylim(0, 128)
        ax.set_title("winsorized as in our pipeline" if w else "no winsorization", fontsize=10)
    axes[0].set_ylabel("% of NO-herding markets flagged 'herding'")
    axes[0].legend(fontsize=7, ncol=4, loc="upper center")
    fig.suptitle("Paper-exact Wang & Hudson tests vs ours: false alarms with no herding (1,000 markets per bar)")
    fig.tight_layout()
    fig.savefig(RES_DIR / "wh_paper_e5_size.png", dpi=200)
    plt.close(fig)


# =====================================================================
# The paper's own no-herding simulation (p.12-15), error-SD grid
# =====================================================================
def replicate(n_sims=500, sds=(1.0, 0.3, 0.1, 0.03, 0.01)):
    rm = np.round(np.arange(-500, 501) / 1000, 3)
    betas = np.repeat([0.5, 0.8, 1.2, 1.5], 5)
    rows = []
    for sd in sds:
        ts, gaps = [], []
        for i in range(n_sims):
            rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, 10, int(sd * 1000), i]))
            R = betas[None, :] * rm[:, None] + sd * rng.standard_normal((len(rm), len(betas)))
            c = np.abs(R - rm[:, None]).mean(axis=1)
            keep = rm != 0
            f = pd.DataFrame({"scsad": np.where(rm > 0, c, -c)[keep], "rm": rm[keep]})
            res = hc1(f["scsad"], pd.DataFrame({"rm": f.rm, "rm2": f.rm ** 2, "rm3": f.rm ** 3}))
            ts.append(res.tvalues["rm3"])
            gaps.append(2 * c[np.abs(rm) <= 0.005].mean())
        ts = np.array(ts)
        rows.append({"error_sd": sd, "n_sims": n_sims, "jump_at_0": float(np.mean(gaps)),
                     "jump_over_scsad_range": float(np.mean(gaps) / (0.5 * np.abs(betas - 1).mean() * 2)),
                     "herding_two_sided_5pct": float((ts < PAPER_CRIT).mean()),
                     "anti_herding_two_sided_5pct": float((ts > -PAPER_CRIT).mean()),
                     "herding_one_sided_5pct": float((ts < sim.ONE_SIDED_CRIT).mean()), "median_t": float(np.median(ts))})
    t = pd.DataFrame(rows)
    t.to_csv(RES_DIR / "wh_paper_replication.csv", index=False)
    print(t.round(4).to_string(index=False))
    print("paper's Table 1 (p.15): SCSAD herding 14.4%, nothing 85.6%, anti-herding 0%")
    return t


# =====================================================================
# Part F addition (same seeds as Part F)
# =====================================================================
F_STATS = ["wh_paper_t", "sol1_paper_t", "wh_paper_g5_t", "wh_paper_g7_t"]


def primary_wh_paper(c, ctx, method="hc1", rng=None, B=999):
    """Primary Step 5 WH design (main_regression.design) on the log-return SCSAD."""
    df = c.join(ctx["entry"]).dropna(subset=["high", "low", "scsad"])
    X = mr.design(df, "dummy", "wh")
    if method == "hc1":
        return hc1(df["scsad"], X)
    return rse.fit_with(method, df["scsad"], X, rng=rng, B=B)


def f_stats(c, ctx):
    v = paper_variants(c)
    res = primary_wh_paper(c, ctx)
    return {"wh_paper_t": v["wh_paper_t"], "sol1_paper_t": v["sol1_paper_t"],
            "wh_paper_g5_t": float(res.tvalues["rm3_post_high"]), "wh_paper_g7_t": float(res.tvalues["rm3_post_low"])}


def _f_one(task):
    part, s, k, rep = task
    R, _ = sim.simulate_returns(_CAL, s, k, ct.rng_for(part, s, rep), winsorize=True)
    return {"part": part, "scenario": s, "kappa": k, "rep": rep, **f_stats(log_csad(R, _CAL["dates"]), _CTX)}


def f_run(workers=12):
    _pool_run(F_RAW, ["part", "scenario", "kappa", "rep"], ct.tasks(), _f_one, _init_ctx, workers, every=1000)


def real_frame(panel_path=mr.OUT_DIR / "return_panel_final.csv"):
    """Real panel -> paper-exact log-return CSAD frame (the market is the
    equal-weighted mean of the stocks' log returns, as in the paper)."""
    p = pd.read_csv(panel_path, usecols=["date", "ticker", "ret"], parse_dates=["date"])
    p["lr"] = np.log1p(p["ret"])
    m = p.groupby("date")["lr"].transform("mean")
    p["dev"] = (p["lr"] - m).abs()
    g = p.assign(m=m).groupby("date").agg(csad=("dev", "mean"), mkt_ret=("m", "first"))
    g["scsad"] = np.where(g["mkt_ret"] > 0, g["csad"], np.where(g["mkt_ret"] < 0, -g["csad"], np.nan))
    g["post"] = (g.index >= CHATGPT_RELEASE).astype(int)
    return g


def f_summary():
    raw = pd.read_csv(F_RAW)
    null, held = raw[raw.part == ct.PART_NULL], raw[raw.part == ct.PART_HELDOUT]
    crit = {s: float(np.quantile(null[s], 0.05)) for s in F_STATS}
    rows = []
    for (sc, k), g in held.groupby(["scenario", "kappa"]):
        for s in F_STATS:
            is_null = ("g5" in s or "g7" in s) or k == 0
            rows.append({"scenario": sc, "kappa": k, "statistic": s, "n_markets": len(g),
                         "true_effect": "none (null)" if is_null else "herding",
                         "textbook_flag_rate": float((g[s] < sim.ONE_SIDED_CRIT).mean()),
                         "calibrated_flag_rate": float((g[s] <= crit[s]).mean())})
    sp = pd.DataFrame(rows)
    sp.to_csv(RES_DIR / "calibrated_paper_size_power.csv", index=False)
    _init(ctx=True)
    c = real_frame()
    real = f_stats(c, _CTX)
    res = pd.DataFrame([{"statistic": s, "real_t": real[s], "textbook_p_one_sided": float(norm.cdf(real[s])),
                         "calibrated_p_one_sided": ct.calibrated_p(null[s], real[s]),
                         "null_5th_pct_t": crit[s], "null_median_t": float(null[s].median()),
                         "null_sd_t": float(null[s].std()), "n_null": len(null)} for s in F_STATS])
    res.to_csv(RES_DIR / "calibrated_paper_results.csv", index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 4, figsize=(17, 3.9))
    for ax, s in zip(axes, F_STATS):
        ax.hist(null[s], bins=50, color="0.72", edgecolor="white")
        ax.axvline(crit[s], color="0.2", ls="--", lw=1.2, label=f"calibrated 5% cutoff ({crit[s]:.2f})")
        ax.axvline(sim.ONE_SIDED_CRIT, color="#1f77b4", ls=":", lw=1.5, label="textbook cutoff (-1.645)")
        ax.axvline(real[s], color="#d62728", lw=2.2, label=f"real data ({real[s]:.2f})")
        ax.set_title(f"{s}\ncalibrated p = {ct.calibrated_p(null[s], real[s]):.3f}", fontsize=9)
        ax.legend(fontsize=6.5)
    fig.suptitle("Paper-exact tests: real t-statistic vs 2,000 simulated NO-herding markets (S5)")
    fig.tight_layout()
    fig.savefig(RES_DIR / "calibrated_paper_null_distributions.png", dpi=200)
    plt.close(fig)
    pd.set_option("display.width", 220)
    print(res.round(4).to_string(index=False))
    for s in F_STATS:
        print("\n" + s)
        print(sp[sp.statistic == s].drop(columns="statistic").round(3).to_string(index=False))


# =====================================================================
# Part H addition (same seeds as Part H)
# =====================================================================
H_TERMS = {"post_whp": ("d3", "rm3_post"), "g5_whp": ("prim", "rm3_post_high"), "g7_whp": ("prim", "rm3_post_low")}


def h_regs(c, ctx):
    X = eq3_x(c)
    X["rm3_post"] = X["rm3"] * c["post"]
    df = c.join(ctx["entry"]).dropna(subset=["high", "low", "scsad"])
    return {"d3": (c["scsad"], X), "prim": (df["scsad"], mr.design(df, "dummy", "wh"))}


def fit_method(m, y, X, rng, B):
    return hc1(y, X) if m == "hc1" else rse.fit_with(m, y, X, rng=rng, B=B)


def _h_one(task):
    w, rep = task
    R, _ = sim.simulate_returns(_CAL, "S5", 0, ct.rng_for(8, "S5", rep), winsorize=w)
    regs = h_regs(log_csad(R, _CAL["dates"]), _CTX)
    rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, 8, 99, rep, int(w)]))
    row = {"winsorized": w, "rep": rep}
    for m in H_METHODS:
        fits = {k: fit_method(m, y, X, rng, 999) for k, (y, X) in regs.items()}
        for key, (reg, term) in H_TERMS.items():
            row[f"{key}_{m}"] = float(fits[reg].tvalues[term])
    return row


def h_run(workers=12):
    todo = [(w, r) for w in [True, False] for r in range(1000)]
    _pool_run(H_RAW, ["winsorized", "rep"], todo, _h_one, _init_ctx, workers, every=200)


def h_summary():
    raw = pd.read_csv(H_RAW)
    rows = []
    for w, g in raw.groupby("winsorized"):
        for key in H_TERMS:
            for m in H_METHODS:
                t = g[f"{key}_{m}"]
                rows.append({"winsorized": w, "term": key, "method": m, "n_markets": len(g),
                             "false_alarm": float((t < sim.ONE_SIDED_CRIT).mean()), "sd_t": float(t.std())})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES_DIR / "se_validation_paper_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(tab.pivot_table(index=["winsorized", "term"], columns="method", values="false_alarm")[H_METHODS].round(3).to_string())
    print(tab.pivot_table(index=["winsorized", "term"], columns="method", values="sd_t")[H_METHODS].round(2).to_string())


def real():
    _init(ctx=True)
    c = real_frame()
    out = {"base": paper_variants(c)}
    rows = []
    for m in ["hc1", "boot"]:
        rng = np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, 8, 7777]))
        res = primary_wh_paper(c, _CTX, method=m, rng=rng, B=5000)
        for name, term in [("g5", "rm3_post_high"), ("g7_postlow", "rm3_post_low")]:
            coef, se = float(res.params[term]), float(res.bse[term])
            rows.append({"method": m, "term": name, "coef": coef, "se": se, "t": coef / se,
                         "p_one_sided": float(norm.cdf(coef / se)), "p_two_sided": float(2 * norm.sf(abs(coef / se)))})
    out["primary_wh_paper"] = rows
    (RES_DIR / "real_wh_paper.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    RES_DIR.mkdir(exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "e5summary"
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    {"e5run": lambda: e5_run(w), "e5summary": e5_summary, "replicate": replicate, "frun": lambda: f_run(w),
     "fsummary": f_summary, "hrun": lambda: h_run(w), "hsummary": h_summary, "real": real}[cmd]()
