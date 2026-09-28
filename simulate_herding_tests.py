"""
Part B: Monte Carlo simulation -- which herding test can we trust?

On the same real data the standard CCK test finds no base herding
(quadratic term p = 0.95) while our Wang-Hudson SCSAD test finds strong
herding (cubic term p < 0.0001). This simulates markets where we KNOW
whether herding exists and measures how often each test says "herding".
Design and decision rules were fixed in docs/addendum_2026-09-28.md
before this file was written.

The tests are the project's own, called unchanged:
  compute_csad()                    -- build_csad.py
  standard_cck_regression()         -- robustness_wang_hudson.py
  wang_hudson_scsad_regression()    -- robustness_wang_hudson.py
Simulated days are stamped with the real trading calendar, so
compute_csad() sets Post_t on exactly the real days (on/after
2022-11-30) and both regressions run identically to the real ones.

Usage:
  py simulate_herding_tests.py calibrate   # -> data/sim_calibration.json
  py simulate_herding_tests.py run         # 40,000 markets, resumable
  py simulate_herding_tests.py summarize   # -> results/ tables + figures
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from build_csad import compute_csad
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression

OUT_DIR = Path("data")
RES_DIR = Path("results")
CAL_PATH = OUT_DIR / "sim_calibration.json"
RAW_PATH = RES_DIR / "sim_raw.csv"

BASE_SEED = 20260928
BLOCK = 21
KAPPAS = [0, 3, 10, 30, 100, 300, 1000, 3000]
REPS = 1000
T_DF = 4
ONE_SIDED_CRIT = -1.645
SCENARIOS = {
    #        betas     sigmas    shocks     vol clustering
    "S1": dict(beta="one", sigma="median", shock="normal", vol="flat"),
    "S2": dict(beta="real", sigma="median", shock="normal", vol="flat"),
    "S3": dict(beta="one", sigma="median", shock="t", vol="flat"),
    "S4": dict(beta="one", sigma="median", shock="normal", vol="clustered"),
    "S5": dict(beta="real", sigma="real", shock="t", vol="clustered"),
}
SCEN_INDEX = {s: i + 1 for i, s in enumerate(SCENARIOS)}


# =====================================================================
# Calibration (from the real, rename-corrected panel)
# =====================================================================
def calibrate(panel_path=OUT_DIR / "return_panel_final.csv",
              market_path=OUT_DIR / "market_returns_final.csv", min_obs=250):
    panel = pd.read_csv(panel_path, usecols=["date", "ticker", "ret"], parse_dates=["date"])
    market = pd.read_csv(market_path, parse_dates=["date"])
    df = panel.merge(market[["date", "mkt_ret_eq"]], on="date")

    # per-stock OLS of ret on the equal-weighted market (with intercept)
    g = df.groupby("ticker")
    n = g["ret"].size()
    mx, my = g["mkt_ret_eq"].transform("mean"), g["ret"].transform("mean")
    df["dx"], df["dy"] = df["mkt_ret_eq"] - mx, df["ret"] - my
    sxy = (df["dx"] * df["dy"]).groupby(df["ticker"]).sum()
    sxx = (df["dx"] ** 2).groupby(df["ticker"]).sum()
    beta = sxy / sxx
    df["resid"] = df["dy"] - df["ticker"].map(beta) * df["dx"]
    sigma = df.groupby("ticker")["resid"].std()
    keep = n[n >= min_obs].index
    beta, sigma = beta[keep], sigma[keep]

    # idiosyncratic volatility co-moving with |R_m|: s_t = a + b |R_m,t|
    d = df[df["ticker"].isin(keep)]
    s_t = d.groupby("date")["resid"].std()
    absm = market.set_index("date")["mkt_ret_eq"].abs().reindex(s_t.index)
    b, a = np.polyfit(absm.values, s_t.values, 1)
    z = d["resid"] / d["ticker"].map(sigma)
    excess_kurt = float(((z - z.mean()) ** 4).mean() / z.var() ** 2 - 3)

    # real-data base herding statistics, same functions as the simulation
    csad = compute_csad(panel, market)
    cck, wh = standard_cck_regression(csad), wang_hudson_scsad_regression(csad)
    real = {"cck_rm2": _stat(cck, "rm2"), "cck_rm2_post": _stat(cck, "rm2_post"),
            "wh_rm3": _stat(wh, "rm3"), "wh_rm3_post": _stat(wh, "rm3_post")}

    cal = {
        "source": {"panel": str(panel_path), "market": str(market_path)},
        "n_days": int(len(market)),
        "n_stocks_median": int(round(market["n_stocks"].median())),
        "dates": market["date"].dt.strftime("%Y-%m-%d").tolist(),
        "market_returns": market["mkt_ret_eq"].round(10).tolist(),
        "betas": beta.round(6).tolist(),
        "sigmas": sigma.round(8).tolist(),
        "n_calibration_stocks": int(len(keep)),
        "sigma_median": float(sigma.median()),
        "vol_comovement": {"a": float(a), "b": float(b),
                           "r2": float(np.corrcoef(absm, s_t)[0, 1] ** 2)},
        "residual_excess_kurtosis": excess_kurt,
        "real_base_herding": real,
    }
    OUT_DIR.mkdir(exist_ok=True)
    CAL_PATH.write_text(json.dumps(cal))
    return cal


def real_unwinsorized_check(panel_path=OUT_DIR / "return_panel_final.csv",
                            market_path=OUT_DIR / "market_returns_final.csv"):
    """Deviation D2 (post-hoc, exploratory). How much does the real
    pipeline's pooled winsorization clip on extreme days, and what are the
    real base-herding t-stats without it? Unclipped returns are rebuilt
    exactly: returns that were not clipped stay as they are, and clipped
    ones are recomputed from the adjacent cleaned closes."""
    p = pd.read_csv(panel_path, usecols=["date", "ticker", "close", "ret"], parse_dates=["date"])
    p = p.sort_values(["ticker", "date"])
    lo, hi = p["ret"].min(), p["ret"].max()
    clipped = (p["ret"] <= lo + 1e-12) | (p["ret"] >= hi - 1e-12)
    raw_ret = p.groupby("ticker")["close"].pct_change()
    p["ret_unw"] = p["ret"].where(~clipped, raw_ret)
    p["clipped"] = clipped
    market = pd.read_csv(market_path, parse_dates=["date"]).set_index("date")
    by_day = p.groupby("date").agg(clipped_share=("clipped", "mean"), n=("clipped", "size"))
    by_day["mkt_ret_eq"] = market["mkt_ret_eq"].reindex(by_day.index)
    worst = by_day.sort_values("clipped_share", ascending=False).head(10)
    p = p.dropna(subset=["ret_unw"])

    mkt_unw = p.groupby("date")["ret_unw"].mean().rename("mkt_ret_eq").reset_index()
    csad = compute_csad(p[["date", "ticker", "ret_unw"]].rename(columns={"ret_unw": "ret"}), mkt_unw)
    cck, wh = standard_cck_regression(csad), wang_hudson_scsad_regression(csad)
    out = {"clip_bounds": [float(lo), float(hi)], "clipped_stock_days": int(clipped.sum()),
           "clipped_share_all": float(clipped.mean()),
           "cck_coef": float(cck.params["rm2"]), "cck_t": float(cck.tvalues["rm2"]), "cck_p": float(cck.pvalues["rm2"]),
           "wh_coef": float(wh.params["rm3"]), "wh_t": float(wh.tvalues["rm3"]), "wh_p": float(wh.pvalues["rm3"]),
           "worst_days": [{"date": str(d.date()), "clipped_share": round(float(r.clipped_share), 4),
                           "n_stocks": int(r.n), "mkt_ret_eq": round(float(r.mkt_ret_eq), 4)}
                          for d, r in worst.iterrows()]}
    return out


def _stat(res, term):
    return {"coef": float(res.params[term]), "se": float(res.bse[term]),
            "t": float(res.tvalues[term]), "p_two_sided": float(res.pvalues[term])}


def load_calibration():
    return json.loads(CAL_PATH.read_text())


# =====================================================================
# Data-generating process
# =====================================================================
def block_bootstrap(series, length, rng, block=BLOCK):
    """Moving-block bootstrap: random 21-day blocks of the real series,
    concatenated and trimmed to `length`."""
    series = np.asarray(series)
    n_blocks = -(-length // block)
    starts = rng.integers(0, len(series) - block + 1, size=n_blocks)
    return np.concatenate([series[s:s + block] for s in starts])[:length]


def simulate_returns(cal, scenario, kappa, rng, n_stocks=None, n_days=None, winsorize=True):
    """Returns (T x N array of stock returns after winsorization,
    equal-weighted market return the tests will see)."""
    spec = SCENARIOS[scenario]
    T = n_days or cal["n_days"]
    N = n_stocks or cal["n_stocks_median"]
    rm = block_bootstrap(cal["market_returns"], T, rng)

    betas, sigmas = np.asarray(cal["betas"]), np.asarray(cal["sigmas"])
    pick = rng.integers(0, len(betas), size=N)     # (beta, sigma) drawn as real pairs
    beta = betas[pick] if spec["beta"] == "real" else np.ones(N)
    sigma = sigmas[pick] if spec["sigma"] == "real" else np.full(N, cal["sigma_median"])

    if spec["shock"] == "normal":
        z = rng.standard_normal((T, N))
    else:
        z = rng.standard_t(T_DF, size=(T, N)) * np.sqrt((T_DF - 2) / T_DF)   # unit variance
    if spec["vol"] == "clustered":
        a, b = cal["vol_comovement"]["a"], cal["vol_comovement"]["b"]
        m = (a + b * np.abs(rm)) / (a + b * np.abs(rm).mean())
    else:
        m = np.ones(T)

    eps = z * sigma[None, :] * m[:, None]
    h = 1.0 / (1.0 + kappa * rm ** 2)
    R = rm[:, None] + (beta[None, :] * rm[:, None] + eps - rm[:, None]) * h[:, None]

    if winsorize:                                   # same pooled winsorization as build_panel.py
        lo, hi = np.quantile(R, [0.001, 0.999])
        R = np.clip(R, lo, hi)
    return R, R.mean(axis=1)


def to_frames(R, mkt, dates):
    T, N = R.shape
    d = pd.to_datetime(pd.Index(dates))
    panel = pd.DataFrame({"date": np.repeat(d.values, N),
                          "ticker": np.tile(np.arange(N), T),
                          "ret": R.ravel()})
    market = pd.DataFrame({"date": d, "mkt_ret_eq": mkt})
    return panel, market


def run_tests(R, mkt, dates):
    panel, market = to_frames(R, mkt, dates)
    csad = compute_csad(panel, market)
    cck, wh = standard_cck_regression(csad), wang_hudson_scsad_regression(csad)
    out = {}
    for name, res, term in [("cck", cck, "rm2"), ("cck_post", cck, "rm2_post"),
                            ("wh", wh, "rm3"), ("wh_post", wh, "rm3_post")]:
        out[f"{name}_coef"] = float(res.params[term])
        out[f"{name}_t"] = float(res.tvalues[term])
        out[f"{name}_p"] = float(res.pvalues[term])
    return out


def rng_for(scenario, rep):
    """Same seed for every kappa within a scenario/rep (common random
    numbers), so power curves compare like with like."""
    return np.random.default_rng(np.random.SeedSequence([BASE_SEED, SCEN_INDEX[scenario], rep]))


def one_market(cal, scenario, kappa, rep, winsorize=True):
    R, mkt = simulate_returns(cal, scenario, kappa, rng_for(scenario, rep), winsorize=winsorize)
    return {"winsorized": winsorize, "scenario": scenario, "kappa": kappa, "rep": rep,
            **run_tests(R, mkt, cal["dates"])}


# =====================================================================
# Parallel, resumable run
# =====================================================================
_CAL = None


def _init_worker():
    global _CAL
    _CAL = load_calibration()


def _work(task):
    return one_market(_CAL, *task)


def run_all(workers=12, reps=REPS):
    import multiprocessing as mp
    RES_DIR.mkdir(exist_ok=True)
    done = set()
    if RAW_PATH.exists():
        prev = pd.read_csv(RAW_PATH, usecols=["scenario", "kappa", "rep", "winsorized"])
        done = set(zip(prev["scenario"], prev["kappa"], prev["rep"], prev["winsorized"]))
    # registered (winsorized) run first, then the D1 no-winsorization run
    tasks = [(s, k, r, w) for w in [True, False] for s in SCENARIOS for r in range(reps) for k in KAPPAS
             if (s, k, r, w) not in done]
    print(f"{len(done)} markets already done, {len(tasks)} to go", flush=True)
    if not tasks:
        return
    header = not RAW_PATH.exists()
    t0 = time.time()
    with mp.Pool(workers, initializer=_init_worker) as pool, open(RAW_PATH, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(_work, tasks, chunksize=4), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % 500 == 0:
                f.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(tasks)} done, {rate:.1f}/s, ~{(len(tasks) - i) / rate / 60:.0f} min left", flush=True)


# =====================================================================
# Summary, comparison with reality, figures
# =====================================================================
def size_power(raw):
    g = raw.groupby(["winsorized", "scenario", "kappa"])
    tab = pd.DataFrame({
        "reps": g.size(),
        "cck_detect": g["cck_t"].apply(lambda t: (t < ONE_SIDED_CRIT).mean()),
        "wh_detect": g["wh_t"].apply(lambda t: (t < ONE_SIDED_CRIT).mean()),
        "cck_mean_coef": g["cck_coef"].mean(), "wh_mean_coef": g["wh_coef"].mean(),
        "cck_median_t": g["cck_t"].median(), "wh_median_t": g["wh_t"].median(),
        "cck_positive_sig": g["cck_t"].apply(lambda t: (t > -ONE_SIDED_CRIT).mean()),
        "wh_positive_sig": g["wh_t"].apply(lambda t: (t > -ONE_SIDED_CRIT).mean()),
    }).reset_index()

    def verdict(rate):
        return "over-rejects" if rate > 0.064 else ("conservative" if rate < 0.036 else "well-sized")
    null = tab["kappa"] == 0
    tab.loc[null, "cck_size_verdict"] = tab.loc[null, "cck_detect"].map(verdict)
    tab.loc[null, "wh_size_verdict"] = tab.loc[null, "wh_detect"].map(verdict)
    return tab


def compare_with_reality(raw, tab, real_t, winsorized):
    """real_t = (t_CCK, t_WH) from real data processed the same way as this
    pipeline. Nearest cell = smallest Euclidean distance between the real
    pair and each cell's median simulated pair (addendum B6)."""
    rt = np.asarray(real_t)
    t = tab[tab.winsorized == winsorized]
    dist = np.hypot(t["cck_median_t"] - rt[0], t["wh_median_t"] - rt[1])
    best = t.loc[dist.idxmin(), ["scenario", "kappa", "cck_median_t", "wh_median_t"]].to_dict()
    pct = {}
    r = raw[raw.winsorized == winsorized]
    for sc in SCENARIOS:
        n = r[(r.scenario == sc) & (r.kappa == 0)]
        pct[sc] = {"cck_real_t_percentile_in_null": round(float((n["cck_t"] <= rt[0]).mean()), 4),
                   "wh_real_t_percentile_in_null": round(float((n["wh_t"] <= rt[1]).mean()), 4),
                   "wh_null_5th_pct_t": round(float(n["wh_t"].quantile(0.05)), 2),
                   "wh_null_median_t": round(float(n["wh_t"].median()), 2)}
    return best, pct


SCEN_LABEL = {"S1": "textbook", "S2": "real betas", "S3": "fat tails", "S4": "vol. clustering", "S5": "realistic"}


def figures(tab, winsorized):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    RES_DIR.mkdir(exist_ok=True)
    tag = "winsorized" if winsorized else "unwinsorized"
    note = ("returns winsorized as in our real pipeline (pre-registered)" if winsorized
            else "no winsorization (deviation D1)")
    t = tab[tab.winsorized == winsorized]

    null = t[t.kappa == 0].set_index("scenario").reindex(list(SCENARIOS))
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = np.arange(len(null))
    ax.axhspan(3.6, 6.4, color="0.88", zorder=0, label="correct range (3.6-6.4%)")
    ax.bar(x - 0.2, null["cck_detect"] * 100, 0.4, label="Standard CCK", color="#1f77b4", zorder=2)
    ax.bar(x + 0.2, null["wh_detect"] * 100, 0.4, label="Wang-Hudson (ours)", color="#d62728", zorder=2)
    for i, (c, w) in enumerate(zip(null["cck_detect"], null["wh_detect"])):
        ax.text(i - 0.2, c * 100 + 1.5, f"{c:.0%}", ha="center", fontsize=8)
        ax.text(i + 0.2, w * 100 + 1.5, f"{w:.0%}", ha="center", fontsize=8)
    ax.set_xticks(x, [f"{sc}" + chr(10) + SCEN_LABEL[sc] for sc in null.index])
    ax.set_ylabel('% of markets where the test says "herding"')
    ax.set_ylim(0, 112)
    ax.set_title("False alarms when there is NO herding (1,000 markets each)" + chr(10) + note, fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(RES_DIR / f"sim_size_table_{tag}.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 5, figsize=(17, 3.9), sharey=True)
    for ax, sc in zip(axes, SCENARIOS):
        d = t[t.scenario == sc].sort_values("kappa")
        xs = d["kappa"].replace(0, 1)          # kappa = 0 plotted at the left edge of the log axis
        ax.plot(xs, d["cck_detect"] * 100, "o-", label="Standard CCK", color="#1f77b4")
        ax.plot(xs, d["wh_detect"] * 100, "s-", label="Wang-Hudson (ours)", color="#d62728")
        ax.axhline(5, color="0.5", lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_xticks([1, 10, 100, 1000], ["0", "10", "100", "1000"])
        ax.set_title(f"{sc}: {SCEN_LABEL[sc]}")
        ax.set_xlabel("true herding strength (kappa)")
    axes[0].set_ylabel('% of markets where test says "herding"')
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Detection rate vs. true herding strength -- {note}")
    fig.tight_layout()
    fig.savefig(RES_DIR / f"sim_power_curves_{tag}.png", dpi=200)
    plt.close(fig)


def summarize():
    cal = load_calibration()
    raw = pd.read_csv(RAW_PATH)
    tab = size_power(raw)
    tab.to_csv(RES_DIR / "sim_size_power.csv", index=False)
    pd.set_option("display.width", 220)
    real = cal["real_base_herding"]
    out = {}
    for w in [True, False]:
        if not (tab.winsorized == w).any():
            continue
        figures(tab, w)
        key = "winsorized" if w else "unwinsorized"
        rt = ((real["cck_rm2"]["t"], real["wh_rm3"]["t"]) if w else
              (cal.get("real_unwinsorized", {}).get("cck_t", np.nan), cal.get("real_unwinsorized", {}).get("wh_t", np.nan)))
        cols = ["scenario", "kappa", "reps", "cck_detect", "wh_detect", "cck_median_t", "wh_median_t",
                "cck_size_verdict", "wh_size_verdict"]
        print(chr(10) + f"=== {key} ===")
        print(tab[tab.winsorized == w][cols].round(3).to_string(index=False))
        if not np.isnan(rt[0]):
            best, pct = compare_with_reality(raw, tab, rt, w)
            print(f"real t-stats ({key}): CCK {rt[0]:.2f}, Wang-Hudson {rt[1]:.2f}")
            print("nearest simulated cell:", best)
            print(json.dumps(pct, indent=1))
            out[key] = {"real_t": rt, "best": best, "percentiles": pct}
    return tab, out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summarize"
    if cmd == "calibrate":
        c = calibrate()
        print(json.dumps({k: v for k, v in c.items() if k not in ("dates", "market_returns", "betas", "sigmas")}, indent=1))
    elif cmd == "realcheck":
        cal = load_calibration()
        cal["real_unwinsorized"] = real_unwinsorized_check()
        CAL_PATH.write_text(json.dumps(cal))
        print(json.dumps(cal["real_unwinsorized"], indent=1))
    elif cmd == "run":
        run_all(workers=int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    else:
        summarize()
