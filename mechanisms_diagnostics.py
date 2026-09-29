"""
Part G: why do the two strange Part B behaviours happen?
(docs/addendum2_2026-09-28.md, Part G). Uses Part B's seeds on purpose,
so every market here is one Part B also simulated.

G1  pooled winsorization -> false CCK herding (S1, kappa = 0)
    + size of per-day (cross-sectional) winsorization, S1 and S5, 1,000 markets
G2  CCK's non-monotonic power: one S1 market at kappa = 0, 100, 3000

Usage:
  py mechanisms_diagnostics.py g1          # one-market diagnostic + figure
  py mechanisms_diagnostics.py g1size [w]  # per-day winsorization size (resumable)
  py mechanisms_diagnostics.py g2          # figure + coefficient table
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import simulate_herding_tests as sim
from build_csad import compute_csad
from robustness_wang_hudson import standard_cck_regression

RES_DIR = Path("results")
SIZE_PATH = RES_DIR / "mech_daywins_size_raw.csv"
REP = 0


def pooled_clip(R):
    lo, hi = np.quantile(R, [0.001, 0.999])
    return np.clip(R, lo, hi), (R < lo) | (R > hi)


def per_day_clip(R):
    """Each day clipped at that day's own 0.1 / 99.9 percentiles."""
    lo, hi = np.quantile(R, [0.001, 0.999], axis=1)
    return np.clip(R, lo[:, None], hi[:, None])


def csad_of(R):
    return np.abs(R - R.mean(axis=1, keepdims=True)).mean(axis=1)


def cck_test(R, dates):
    """The unchanged test on a (T x N) return matrix."""
    panel, market = sim.to_frames(R, R.mean(axis=1), dates)
    res = standard_cck_regression(compute_csad(panel, market))
    return res


def quad_curve(x_abs, y):
    """Display curve a + b|Rm| + c Rm^2 (no Post term)."""
    A = np.column_stack([np.ones_like(x_abs), x_abs, x_abs ** 2])
    return np.linalg.lstsq(A, y, rcond=None)[0]


# =====================================================================
# G1
# =====================================================================
def g1():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cal = sim.load_calibration()
    R, _ = sim.simulate_returns(cal, "S1", 0, sim.rng_for("S1", REP), winsorize=False)
    Rp, clipped = pooled_clip(R)
    Rd = per_day_clip(R)
    rm = R.mean(axis=1)
    absrm = np.abs(rm)
    share = clipped.mean(axis=1)
    c_raw, c_pool, c_day = csad_of(R), csad_of(Rp), csad_of(Rd)

    dec = pd.qcut(absrm, 10, labels=False)
    tab = pd.DataFrame({"abs_rm_decile": dec + 1, "abs_rm": absrm, "clipped_share": share,
                        "csad_raw": c_raw, "csad_pooled": c_pool, "csad_perday": c_day})
    by = tab.groupby("abs_rm_decile").agg(mean_abs_rm=("abs_rm", "mean"), max_abs_rm=("abs_rm", "max"),
                                         clipped_share=("clipped_share", "mean"),
                                         csad_raw=("csad_raw", "mean"), csad_pooled=("csad_pooled", "mean"),
                                         csad_perday=("csad_perday", "mean"))
    by["csad_cut_pooled_pct"] = 100 * (1 - by["csad_pooled"] / by["csad_raw"])
    by["csad_cut_perday_pct"] = 100 * (1 - by["csad_perday"] / by["csad_raw"])
    top = np.argsort(-absrm)[:10]
    worst = pd.DataFrame({"mkt_ret": rm[top], "clipped_share": share[top],
                          "csad_raw": c_raw[top], "csad_pooled": c_pool[top]})
    worst["csad_cut_pct"] = 100 * (1 - worst["csad_pooled"] / worst["csad_raw"])

    tests = {}
    for name, M in [("unwinsorized", R), ("pooled", Rp), ("per_day", Rd)]:
        r = cck_test(M, cal["dates"])
        tests[name] = {"rm2_coef": float(r.params["rm2"]), "rm2_t": float(r.tvalues["rm2"])}
    lo, hi = np.quantile(R, [0.001, 0.999])
    out = {"market": f"S1 kappa=0 Part B rep {REP}", "pooled_bounds": [float(lo), float(hi)],
           "share_clipped_all": float(clipped.mean()),
           "share_clipped_top_decile_days": float(by["clipped_share"].iloc[-1]),
           "share_clipped_bottom_5_deciles": float(by["clipped_share"].iloc[:5].mean()),
           "cck_rm2": tests, "by_decile": by.round(6).reset_index().to_dict("records"),
           "ten_biggest_days": worst.round(5).to_dict("records")}
    (RES_DIR / "mech_winsorization.json").write_text(json.dumps(out, indent=1))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axes[0]
    ax.scatter(100 * absrm, 100 * share, s=5, color="0.55", alpha=0.6)
    ax.plot(100 * by["mean_abs_rm"], 100 * by["clipped_share"], "o-", color="#d62728", label="average per |R_m| decile")
    ax.set_xlabel("|market return| that day (%)")
    ax.set_ylabel("% of stocks clipped that day")
    ax.set_title("Pooled winsorization clips almost only on big-move days", fontsize=10)
    ax.legend(fontsize=8)
    ax = axes[1]
    xs = np.linspace(0, absrm.max(), 200)
    for y, col, lab in [(c_raw, "0.45", "before winsorization"), (c_pool, "#d62728", "after pooled winsorization")]:
        ax.scatter(100 * absrm, 100 * y, s=5, color=col, alpha=0.45)
        a, b, c = quad_curve(absrm, y)
        key = "unwinsorized" if col == "0.45" else "pooled"
        ax.plot(100 * xs, 100 * (a + b * xs + c * xs ** 2), color=col, lw=2.2,
                label=f"{lab}: CCK Rm^2 t = {tests[key]['rm2_t']:+.2f}")
    ax.set_xlabel("|market return| that day (%)")
    ax.set_ylabel("CSAD (%)")
    ax.set_title("Clipping flattens dispersion exactly on big days -> looks like herding", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("One simulated market with NO herding and identical betas (S1, kappa = 0)")
    fig.tight_layout()
    fig.savefig(RES_DIR / "mech_winsorization.png", dpi=200)
    plt.close(fig)
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_decile", "ten_biggest_days")}, indent=1))
    print(by.round(4).to_string())
    print(worst.round(4).to_string())


# ---- per-day winsorization size (S1, S5, kappa = 0, Part B seeds) ----
_CAL = None


def _init():
    global _CAL
    _CAL = sim.load_calibration()


def _size_one(task):
    scenario, rep = task
    R, _ = sim.simulate_returns(_CAL, scenario, 0, sim.rng_for(scenario, rep), winsorize=False)
    Rd = per_day_clip(R)
    return {"scenario": scenario, "rep": rep, **sim.run_tests(Rd, Rd.mean(axis=1), _CAL["dates"])}


def g1_size(workers=12, reps=1000):
    import multiprocessing as mp
    done = set()
    if SIZE_PATH.exists():
        prev = pd.read_csv(SIZE_PATH, usecols=["scenario", "rep"])
        done = set(zip(prev["scenario"], prev["rep"]))
    todo = [(s, r) for s in ["S1", "S5"] for r in range(reps) if (s, r) not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    header = not SIZE_PATH.exists()
    with mp.Pool(workers, initializer=_init) as pool, open(SIZE_PATH, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(_size_one, todo, chunksize=4), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % 250 == 0:
                f.flush()
                print(f"  {i}/{len(todo)}", flush=True)
    summarize_size()


def summarize_size():
    d = pd.read_csv(SIZE_PATH)
    b = pd.read_csv(sim.RAW_PATH)
    b = b[(b.kappa == 0) & b.scenario.isin(["S1", "S5"])]
    rows = []
    for s in ["S1", "S5"]:
        for label, g in [("pooled (Part B, registered)", b[(b.scenario == s) & b.winsorized]),
                         ("none (Part B, D1)", b[(b.scenario == s) & ~b.winsorized]),
                         ("per-day (Part G)", d[d.scenario == s])]:
            rows.append({"scenario": s, "winsorization": label, "n_markets": len(g),
                         "cck_false_alarm": float((g["cck_t"] < sim.ONE_SIDED_CRIT).mean()),
                         "cck_median_t": float(g["cck_t"].median()),
                         "wh_false_alarm": float((g["wh_t"] < sim.ONE_SIDED_CRIT).mean()),
                         "cck_post_false_alarm": float((g["cck_post_t"] < sim.ONE_SIDED_CRIT).mean())})
    t = pd.DataFrame(rows)
    t.to_csv(RES_DIR / "mech_daywins_size.csv", index=False)
    print(t.round(3).to_string(index=False))


# =====================================================================
# G2
# =====================================================================
def g2():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cal = sim.load_calibration()
    sigma = cal["sigma_median"]
    kappas = [0, 100, 3000]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    rows = []
    for ax, k in zip(axes, kappas):
        R, _ = sim.simulate_returns(cal, "S1", k, sim.rng_for("S1", REP), winsorize=False)
        rm = R.mean(axis=1)
        c = csad_of(R)
        res = cck_test(R, cal["dates"])
        rows.append({"kappa": k, "abs_rm_coef": res.params["abs_rm"], "abs_rm_t": res.tvalues["abs_rm"],
                     "rm2_coef": res.params["rm2"], "rm2_t": res.tvalues["rm2"],
                     "inflection_abs_rm_pct": (100 / np.sqrt(3 * k)) if k else np.nan,
                     "share_days_beyond_inflection": float((np.abs(rm) > 1 / np.sqrt(3 * k)).mean()) if k else np.nan})
        a, b, q = quad_curve(np.abs(rm), c)
        xs = np.linspace(rm.min(), rm.max(), 400)
        ax.scatter(100 * rm, 100 * c, s=4, color="0.55", alpha=0.5, label="simulated days")
        ax.plot(100 * xs, 100 * (a + b * np.abs(xs) + q * xs ** 2), color="#d62728", lw=2.2,
                label=f"fitted CCK curve (Rm^2 t = {res.tvalues['rm2']:+.1f})")
        ax.plot(100 * xs, 100 * sigma * np.sqrt(2 / np.pi) / (1 + k * xs ** 2), color="#1f77b4", lw=1.4, ls="--",
                label="true average dispersion")
        if k:
            for sgn in (-1, 1):
                ax.axvline(sgn * 100 / np.sqrt(3 * k), color="0.3", ls=":", lw=1)
        verdict = "herding detected" if res.tvalues["rm2"] < sim.ONE_SIDED_CRIT else "herding NOT detected"
        ax.set_title(f"kappa = {k}: {verdict}", fontsize=10)
        ax.set_xlabel("market return that day (%)")
        ax.legend(fontsize=7, loc="lower center")
    axes[0].set_ylabel("CSAD (%)")
    fig.suptitle("Same simulated market, herding strength turned up (S1, no winsorization). "
                 "Dotted lines: where the true curve switches from bending down to bending up")
    fig.tight_layout()
    fig.savefig(RES_DIR / "mech_cck_nonmonotonic.png", dpi=200)
    plt.close(fig)
    t = pd.DataFrame(rows)
    t.to_csv(RES_DIR / "mech_cck_nonmonotonic.csv", index=False)
    print(t.round(4).to_string(index=False))


if __name__ == "__main__":
    RES_DIR.mkdir(exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "g1"
    if cmd == "g1":
        g1()
    elif cmd == "g1size":
        g1_size(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    elif cmd == "g2":
        g2()
