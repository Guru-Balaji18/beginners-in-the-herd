"""
Part F: simulation-calibrated herding test (docs/addendum2_2026-09-28.md).

Instead of comparing a t-statistic with the textbook -1.645, compare it
with the distribution the same statistic has in simulated NO-herding
markets calibrated to our real data (S5, kappa = 0). The calibrated
one-sided p-value is the share of null t-statistics at or below the
observed one.

Statistics (all computed by the project's own unchanged functions):
  base herding  CCK t on Rm^2, WH (ours) t on Rm^3
                -- robustness_wang_hudson.standard_cck_regression / wang_hudson_scsad_regression
  g5, g7        t on Post x High / Post x Low in the primary Step 5 design
                -- main_regression.design (dummy form, controls for CCK), NW(5)
The real entry-index High/Low dummies and the real control calendar are
put on the simulated days (the simulation uses the real trading calendar).

Seeds (new, never used in Part B): SeedSequence([20260928, part, scenario, rep])
  part 6 = null (2,000 S5 kappa=0 markets)
  part 7 = held-out validation (S5 kappa grid, S2 and S4 kappa=0; 1,000 each)
Usage:
  py calibrated_test.py run [workers]   # resumable -> results/calibrated_raw.csv
  py calibrated_test.py analyze         # -> results/calibrated_*.csv/png
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

import investor_index as ii
import main_regression as mr
import simulate_herding_tests as sim
from build_csad import compute_csad
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression

RES_DIR = Path("results")
RAW_PATH = RES_DIR / "calibrated_raw.csv"
PART_NULL, PART_HELDOUT = 6, 7
N_NULL, N_HELDOUT = 2000, 1000
ALPHA = 0.05
STATS = ["cck_t", "wh_t", "cck_g5_t", "wh_g5_t", "cck_g7_t", "wh_g7_t"]
LABELS = {"cck_t": "Base herding, standard CCK (Rm^2)", "wh_t": "Base herding, Wang-Hudson ours (Rm^3)",
          "cck_g5_t": "g5 Post x High, CCK", "wh_g5_t": "g5 Post x High, Wang-Hudson ours",
          "cck_g7_t": "g7 Post x Low, CCK", "wh_g7_t": "g7 Post x Low, Wang-Hudson ours"}


def rng_for(part, scenario, rep):
    return np.random.default_rng(np.random.SeedSequence([sim.BASE_SEED, part, sim.SCEN_INDEX[scenario], rep]))


# =====================================================================
# Fixed real-data context shared by every simulated market
# =====================================================================
def load_context(cal):
    days = pd.DatetimeIndex(pd.to_datetime(cal["dates"]))
    p = mr.PRIMARY
    ent = mr.entry_variant(p["hood"], p["mode"], p["form"], p["cutoff"], ii.load_components(), days)
    return {"days": days, "entry": ent[["high", "low"]],
            "vix": mr.load_vix().reindex(days).values,
            "fomc": pd.read_csv(mr.RAW / "fomc_dates.csv")["date"],
            "cpi": pd.read_csv(mr.RAW / "cpi_release_dates.csv")["date"]}


def market_frames(R, mkt, ctx):
    """Simulated returns -> (csad frame, primary-design frame, controls),
    built exactly the way main_regression.run builds them."""
    panel, market = sim.to_frames(R, mkt, ctx["days"])
    csad = compute_csad(panel, market).set_index("date")
    ctrl = mr.controls_frame(csad.index, csad["mkt_ret"].values, ctx["vix"], ctx["fomc"], ctx["cpi"])
    df = csad.join(ctx["entry"]).dropna(subset=["high", "low"])
    return csad, df, ctrl.reindex(df.index)


def primary_xy(df, ctrl, test):
    X = mr.design(df, "dummy", test, controls=ctrl if test == "cck" else None)
    return (df["csad"] if test == "cck" else df["scsad"]), X


def textbook_stats(csad, df, ctrl):
    cck, wh = standard_cck_regression(csad.reset_index()), wang_hudson_scsad_regression(csad.reset_index())
    out = {"cck_t": cck.tvalues["rm2"], "cck_post_t": cck.tvalues["rm2_post"],
           "wh_t": wh.tvalues["rm3"], "wh_post_t": wh.tvalues["rm3_post"]}
    for test in ["cck", "wh"]:
        y, X = primary_xy(df, ctrl, test)
        res = mr.fit(y, X)
        g5, g7 = mr.key_terms("dummy", test)
        out[f"{test}_g5_t"], out[f"{test}_g7_t"] = res.tvalues[g5], res.tvalues[g7]
    return {k: float(v) for k, v in out.items()}


def one_market(cal, ctx, part, scenario, kappa, rep):
    R, mkt = sim.simulate_returns(cal, scenario, kappa, rng_for(part, scenario, rep), winsorize=True)
    return {"part": part, "scenario": scenario, "kappa": kappa, "rep": rep,
            **textbook_stats(*market_frames(R, mkt, ctx))}


# =====================================================================
# Parallel, resumable run
# =====================================================================
_CAL = _CTX = None


def _init_worker():
    global _CAL, _CTX
    _CAL = sim.load_calibration()
    _CTX = load_context(_CAL)


def _work(task):
    return one_market(_CAL, _CTX, *task)


def tasks():
    t = [(PART_NULL, "S5", 0, r) for r in range(N_NULL)]
    t += [(PART_HELDOUT, "S5", k, r) for r in range(N_HELDOUT) for k in sim.KAPPAS]
    t += [(PART_HELDOUT, s, 0, r) for s in ["S2", "S4"] for r in range(N_HELDOUT)]
    return t


def run_all(workers=12):
    import multiprocessing as mp
    RES_DIR.mkdir(exist_ok=True)
    done = set()
    if RAW_PATH.exists():
        prev = pd.read_csv(RAW_PATH, usecols=["part", "scenario", "kappa", "rep"])
        done = set(zip(prev["part"], prev["scenario"], prev["kappa"], prev["rep"]))
    todo = [t for t in tasks() if t not in done]
    print(f"{len(done)} markets already done, {len(todo)} to go", flush=True)
    if not todo:
        return
    header, t0 = not RAW_PATH.exists(), time.time()
    with mp.Pool(workers, initializer=_init_worker) as pool, open(RAW_PATH, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(_work, todo, chunksize=4), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % 500 == 0:
                f.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)} done, {rate:.1f}/s, ~{(len(todo) - i) / rate / 60:.0f} min left", flush=True)


# =====================================================================
# The calibrated test itself
# =====================================================================
def calibrated_p(null_t, t):
    """One-sided (herding = more negative) calibrated p-value."""
    null_t = np.asarray(null_t)
    return float((null_t <= t).mean())


def real_stats():
    """Real-data values of every statistic, from the unchanged pipeline
    outputs: base t-stats from Part B's calibration, g5/g7 from Step 5."""
    cal = sim.load_calibration()
    step5 = pd.read_csv(mr.OUT_DIR / "step5_main_results.csv")
    prim = step5[step5["primary"] & ~step5["variant"].str.contains("lower-order")].set_index("test")
    out = {"cck_t": cal["real_base_herding"]["cck_rm2"]["t"], "wh_t": cal["real_base_herding"]["wh_rm3"]["t"]}
    for t in ["cck", "wh"]:
        out[f"{t}_g5_t"] = prim.loc[t, "g5"] / prim.loc[t, "g5_se"]
        out[f"{t}_g7_t"] = prim.loc[t, "g7_postlow"] / prim.loc[t, "g7_se"]
    return out


def analyze():
    raw = pd.read_csv(RAW_PATH)
    null = raw[raw["part"] == PART_NULL]
    held = raw[raw["part"] == PART_HELDOUT]
    assert len(null) == N_NULL, f"null has {len(null)} markets, expected {N_NULL}"
    crit = {s: float(np.quantile(null[s], ALPHA)) for s in STATS}

    # size / power / mismatch, textbook vs calibrated, on held-out markets
    rows = []
    for (sc, k), g in held.groupby(["scenario", "kappa"]):
        for s in STATS:
            null_true = s.split("_")[1] in ("g5", "g7") or k == 0     # g5/g7 are nulls at every kappa
            rows.append({"scenario": sc, "kappa": k, "statistic": s, "n_markets": len(g),
                         "true_effect": "none (null)" if null_true else "herding",
                         "textbook_flag_rate": float((g[s] < sim.ONE_SIDED_CRIT).mean()),
                         "calibrated_flag_rate": float((g[s] <= crit[s]).mean())})
    sp = pd.DataFrame(rows)
    sp.to_csv(RES_DIR / "calibrated_size_power.csv", index=False)

    real = real_stats()
    res = pd.DataFrame([{"statistic": s, "label": LABELS[s], "real_t": real[s],
                         "textbook_p_one_sided": float(norm.cdf(real[s])),
                         "calibrated_p_one_sided": calibrated_p(null[s], real[s]),
                         "null_5th_pct_t": crit[s], "null_median_t": float(null[s].median()),
                         "null_sd_t": float(null[s].std()), "n_null": len(null)} for s in STATS])
    res.to_csv(RES_DIR / "calibrated_test_results.csv", index=False)
    figure(null, real, crit)

    pd.set_option("display.width", 220)
    print(res.drop(columns=["label"]).round(4).to_string(index=False))
    for s in STATS:
        print(f"\n{s}")
        print(sp[sp.statistic == s].drop(columns=["statistic"]).round(3).to_string(index=False))
    return res, sp


def figure(null, real, crit):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(11, 10))
    for ax, s in zip(axes.ravel(), STATS):
        ax.hist(null[s], bins=50, color="0.72", edgecolor="white")
        ax.axvline(crit[s], color="0.2", ls="--", lw=1.2, label=f"calibrated 5% cutoff ({crit[s]:.2f})")
        ax.axvline(sim.ONE_SIDED_CRIT, color="#1f77b4", ls=":", lw=1.5, label="textbook 5% cutoff (-1.645)")
        ax.axvline(real[s], color="#d62728", lw=2.2, label=f"real data ({real[s]:.2f})")
        p = calibrated_p(null[s], real[s])
        ax.set_title(f"{LABELS[s]}\ncalibrated p = {p:.3f}", fontsize=9.5)
        ax.set_xlabel("t-statistic", fontsize=8)
        ax.legend(fontsize=7)
    for ax in axes[:, 0]:
        ax.set_ylabel("simulated no-herding markets")
    fig.suptitle(f"Where the real t-statistic falls among {len(null):,} simulated NO-herding markets (S5, realistic)")
    fig.tight_layout()
    fig.savefig(RES_DIR / "calibrated_null_distributions.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "run":
        run_all(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    else:
        analyze()
