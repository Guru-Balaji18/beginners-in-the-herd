"""
Part E, paper-independent steps (docs/addendum2_2026-09-28.md Part E;
docs/deviations_log.md D5). The paper itself is still unavailable, so
there is NO paper-exact variant here yet.

Variants (the old code in robustness_wang_hudson.py is never edited):
  wh_old              wang_hudson_scsad_regression, unchanged (must reproduce Part B)
  cck_zero_intercept  CSAD = g1|Rm| + g2 Rm^2 + g3 Rm^2*Post, no constant; herding g2 < 0
                      -- described in the request as W&H's other fix; UNVERIFIED
  wh_no_intercept     the old SCSAD cubic without the constant; herding g3 < 0
                      -- "suppression of intercept" per a citing paper; UNVERIFIED candidate
  wh_sign_term        the old SCSAD cubic + a sign(Rm) regressor; herding g3 < 0
                      -- OUR diagnostic, not from the paper: does absorbing the jump fix size?

Usage:
  py wang_hudson_variants.py e4          # one-market diagnosis + figure
  py wang_hudson_variants.py run [w]     # E5 simulation on Part B seeds (resumable)
  py wang_hudson_variants.py summarize   # size/power tables + figures
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

import simulate_herding_tests as sim
from build_csad import CHATGPT_RELEASE
from robustness_wang_hudson import HAC_LAGS, standard_cck_regression, wang_hudson_scsad_regression

RES_DIR = Path("results")
RAW_PATH = RES_DIR / "wh_variants_raw.csv"
VARIANTS = {  # name: (key term, post term, label)
    "cck": ("rm2", "rm2_post", "Standard CCK (reference)"),
    "wh_old": ("rm3", "rm3_post", "Wang-Hudson, ours (old)"),
    "cck_zero_intercept": ("rm2", "rm2_post", "CCK, intercept = 0 (unverified)"),
    "wh_no_intercept": ("rm3", "rm3_post", "WH, no intercept (unverified candidate)"),
    "wh_sign_term": ("rm3", "rm3_post", "WH + sign(Rm) term (our diagnostic)"),
}


def _hac(y, X, const=True):
    return OLS(y, add_constant(X) if const else X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def cck_zero_intercept(csad):
    rm = csad["mkt_ret"]
    X = pd.DataFrame({"abs_rm": rm.abs(), "rm2": rm ** 2, "rm2_post": rm ** 2 * csad["post"]})
    return _hac(csad["csad"], X, const=False)


def _wh_x(csad):
    rm = csad["mkt_ret"]
    return pd.DataFrame({"mkt_ret": rm, "rm2": rm ** 2, "rm3": rm ** 3, "rm3_post": rm ** 3 * csad["post"]})


def wh_no_intercept(csad):
    return _hac(csad["scsad"], _wh_x(csad), const=False)


def wh_sign_term(csad):
    X = _wh_x(csad)
    X.insert(0, "sign_rm", np.where(csad["mkt_ret"] >= 0, 1.0, -1.0))
    return _hac(csad["scsad"], X)


FITS = {"cck": standard_cck_regression, "wh_old": wang_hudson_scsad_regression,
        "cck_zero_intercept": cck_zero_intercept, "wh_no_intercept": wh_no_intercept, "wh_sign_term": wh_sign_term}


def fast_csad(R, dates):
    """numpy version of build_csad.compute_csad for a (T x N) matrix whose
    market return is the row mean (checked against compute_csad in
    test_wang_hudson_variants.py)."""
    mkt = R.mean(axis=1)
    c = np.abs(R - mkt[:, None]).mean(axis=1)
    d = pd.to_datetime(pd.Index(dates))
    return pd.DataFrame({"date": d, "csad": c, "scsad": np.where(mkt >= 0, c, -c), "mkt_ret": mkt,
                         "post": (d >= CHATGPT_RELEASE).astype(int)})


def all_variants(csad):
    out = {}
    for name, fit in FITS.items():
        res = fit(csad)
        key, post, _ = VARIANTS[name]
        out[f"{name}_coef"] = float(res.params[key])
        out[f"{name}_t"] = float(res.tvalues[key])
        out[f"{name}_post_t"] = float(res.tvalues[post])
    return out


# =====================================================================
# E4: one-market diagnosis
# =====================================================================
def e4():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cal = sim.load_calibration()
    out = {}
    for w in [False, True]:
        R, _ = sim.simulate_returns(cal, "S1", 0, sim.rng_for("S1", 0), winsorize=w)
        c = fast_csad(R, cal["dates"])
        rm, sc = c["mkt_ret"].values, c["scsad"].values
        old = wang_hudson_scsad_regression(c)
        sgn = wh_sign_term(c)
        near = 0.0025
        jump = sc[(rm > 0) & (rm <= near)].mean() - sc[(rm < 0) & (rm >= -near)].mean()
        # the same regression fitted to a pure step: sign(Rm) x mean CSAD, nothing else
        step = c.assign(scsad=np.where(rm >= 0, 1.0, -1.0) * c["csad"].mean())
        st = wang_hudson_scsad_regression(step)
        out["winsorized" if w else "unwinsorized"] = {
            "mean_csad": float(c["csad"].mean()),
            "jump_at_zero": float(jump), "jump_over_mean_csad": float(jump / c["csad"].mean()),
            "old_rm3_coef": float(old.params["rm3"]), "old_rm3_t": float(old.tvalues["rm3"]),
            "pure_step_rm3_coef": float(st.params["rm3"]),
            "share_of_old_cubic_from_step": float(st.params["rm3"] / old.params["rm3"]),
            "with_sign_term_rm3_coef": float(sgn.params["rm3"]), "with_sign_term_rm3_t": float(sgn.tvalues["rm3"]),
            "sign_term_coef": float(sgn.params["sign_rm"]), "sign_term_t": float(sgn.tvalues["sign_rm"])}
        if not w:
            fig_data = (rm, sc, old, sgn, c["csad"].mean())
    # B7 sanity check: cubic coefficient of sign(x) on x, x^2, x^3 for x ~ N(0,1)
    x = np.random.default_rng(0).standard_normal(2_000_000)
    A = np.column_stack([np.ones_like(x), x, x ** 2, x ** 3])
    out["B7_check_cubic_coef_for_sign_x_N01"] = float(np.linalg.lstsq(A, np.sign(x), rcond=None)[0][3])
    (RES_DIR / "wh_e4_diagnosis.json").write_text(json.dumps(out, indent=1))

    rm, sc, old, sgn, mc = fig_data
    xs = np.linspace(rm.min(), rm.max(), 600)
    p = old.params
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, lim in zip(axes, [None, 0.012]):
        ax.scatter(100 * rm, 100 * sc, s=4, color="0.55", alpha=0.5, label="simulated days (no herding)")
        ax.plot(100 * xs, 100 * (p["const"] + p["mkt_ret"] * xs + p["rm2"] * xs ** 2 + p["rm3"] * xs ** 3),
                color="#d62728", lw=2.2, label=f"our WH fitted curve (Rm^3 t = {old.tvalues['rm3']:+.2f})")
        q = sgn.params
        ax.plot(100 * xs, 100 * (q["const"] + q["sign_rm"] * np.sign(xs) + q["mkt_ret"] * xs + q["rm2"] * xs ** 2
                                 + q["rm3"] * xs ** 3), color="#1f77b4", lw=1.6, ls="--",
                label=f"same + a jump term (Rm^3 t = {sgn.tvalues['rm3']:+.2f})")
        ax.axvline(0, color="0.3", lw=0.8, ls=":")
        ax.set_xlabel("market return that day (%)")
        if lim:
            ax.set_xlim(-100 * lim, 100 * lim)
            ax.set_title(f"Zoom near 0: SCSAD jumps by {100 * out['unwinsorized']['jump_at_zero']:.2f} points"
                         f" (= {out['unwinsorized']['jump_over_mean_csad']:.2f} x average CSAD)", fontsize=10)
        else:
            ax.set_title("Signed CSAD (SCSAD) vs market return, one market with NO herding", fontsize=10)
            ax.set_ylabel("SCSAD (%)")
        ax.legend(fontsize=7.5, loc="upper left")
    fig.suptitle("Why our Wang-Hudson test says 'herding' when there is none: the sign flip makes a jump at 0 "
                 "that a smooth cubic can only bend around", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(RES_DIR / "wh_e4_diagnosis.png", dpi=200)
    plt.close(fig)
    print(json.dumps(out, indent=1))


# =====================================================================
# E5: simulation on the Part B seeds
# =====================================================================
_CAL = None


def _init():
    global _CAL
    _CAL = sim.load_calibration()


def _work(task):
    w, scenario, kappa, rep = task
    R, _ = sim.simulate_returns(_CAL, scenario, kappa, sim.rng_for(scenario, rep), winsorize=w)
    return {"winsorized": w, "scenario": scenario, "kappa": kappa, "rep": rep,
            **all_variants(fast_csad(R, _CAL["dates"]))}


def run_all(workers=12):
    import multiprocessing as mp
    RES_DIR.mkdir(exist_ok=True)
    done = set()
    if RAW_PATH.exists():
        prev = pd.read_csv(RAW_PATH, usecols=["winsorized", "scenario", "kappa", "rep"])
        done = set(zip(prev["winsorized"], prev["scenario"], prev["kappa"], prev["rep"]))
    todo = [(w, s, k, r) for w in [True, False] for s in sim.SCENARIOS for r in range(sim.REPS) for k in sim.KAPPAS
            if (w, s, k, r) not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    header, t0 = not RAW_PATH.exists(), time.time()
    with mp.Pool(workers, initializer=_init) as pool, open(RAW_PATH, "a", newline="") as f:
        for i, row in enumerate(pool.imap_unordered(_work, todo, chunksize=8), 1):
            pd.DataFrame([row]).to_csv(f, header=header, index=False)
            header = False
            if i % 2000 == 0:
                f.flush()
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)} done, {rate:.1f}/s, ~{(len(todo) - i) / rate / 60:.0f} min left", flush=True)


def summarize():
    raw = pd.read_csv(RAW_PATH)
    # wh_old and cck must reproduce Part B exactly (same seeds, same functions)
    b = pd.read_csv(sim.RAW_PATH)
    m = raw.merge(b, on=["winsorized", "scenario", "kappa", "rep"])
    repro = {"markets_compared": len(m),
             "max_abs_diff_wh_t": float((m["wh_old_t"] - m["wh_t"]).abs().max()),
             "max_abs_diff_cck_t": float((m["cck_t_x"] - m["cck_t_y"]).abs().max())}
    rows = []
    for (w, s, k), g in raw.groupby(["winsorized", "scenario", "kappa"]):
        for v in VARIANTS:
            t = g[f"{v}_t"]
            rate = float((t < sim.ONE_SIDED_CRIT).mean())
            rows.append({"winsorized": w, "scenario": s, "kappa": k, "variant": v, "n": len(g),
                         "detect_rate": rate, "median_t": float(t.median()),
                         "post_false_alarm": float((g[f"{v}_post_t"] < sim.ONE_SIDED_CRIT).mean()),
                         "size_verdict": (("over-rejects" if rate > 0.064 else "conservative" if rate < 0.036
                                           else "well-sized") if k == 0 else "")})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES_DIR / "wh_variants_size_power.csv", index=False)
    (RES_DIR / "wh_variants_reproduction_check.json").write_text(json.dumps(repro, indent=1))
    figures(tab)
    pd.set_option("display.width", 220)
    print(json.dumps(repro, indent=1))
    print(tab[tab.kappa == 0].pivot_table(index=["winsorized", "scenario"], columns="variant",
                                          values="detect_rate")[list(VARIANTS)].round(3).to_string())
    print(tab[(tab.scenario == "S5")].pivot_table(index=["winsorized", "kappa"], columns="variant",
                                                  values="detect_rate")[list(VARIANTS)].round(3).to_string())
    return tab


def figures(tab):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"cck": "#1f77b4", "wh_old": "#d62728", "cck_zero_intercept": "#9467bd",
            "wh_no_intercept": "#ff7f0e", "wh_sign_term": "#2ca02c"}
    for w in [True, False]:
        tag = "winsorized" if w else "unwinsorized"
        sub = tab[(tab.winsorized == w) & (tab.kappa == 0)]
        fig, ax = plt.subplots(figsize=(11, 4.6))
        x = np.arange(len(sim.SCENARIOS))
        for j, v in enumerate(VARIANTS):
            vals = [100 * sub[(sub.scenario == s) & (sub.variant == v)]["detect_rate"].iloc[0] for s in sim.SCENARIOS]
            ax.bar(x + (j - 2) * 0.16, vals, 0.16, color=cols[v], label=VARIANTS[v][2])
        ax.axhspan(3.6, 6.4, color="0.5", alpha=0.25, label="correct (3.6-6.4%)")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{s}\n{sim.SCENARIOS[s]['beta']} betas, {sim.SCENARIOS[s]['shock']}, "
                            f"{sim.SCENARIOS[s]['vol']} vol" for s in sim.SCENARIOS], fontsize=8)
        ax.set_ylabel("% of no-herding markets flagged")
        ax.set_ylim(0, 125)
        ax.legend(fontsize=7.5, ncol=3, loc="upper center")
        ax.set_title(f"False alarms with NO herding, 1,000 markets each ({tag})", fontsize=10)
        fig.tight_layout()
        fig.savefig(RES_DIR / f"wh_variants_size_{tag}.png", dpi=200)
        plt.close(fig)

        fig, axes = plt.subplots(1, 5, figsize=(18, 3.8), sharey=True)
        for ax, s in zip(axes, sim.SCENARIOS):
            for v in VARIANTS:
                d = tab[(tab.winsorized == w) & (tab.scenario == s) & (tab.variant == v)].sort_values("kappa")
                ax.plot(np.arange(len(d)), 100 * d["detect_rate"], "o-", ms=3, color=cols[v], label=VARIANTS[v][2])
            ax.axhline(5, color="0.4", ls="--", lw=0.8)
            ax.set_xticks(np.arange(len(sim.KAPPAS)))
            ax.set_xticklabels(sim.KAPPAS, fontsize=7)
            ax.set_title(s, fontsize=10)
            ax.set_xlabel("true herding strength (kappa)", fontsize=8)
        axes[0].set_ylabel("% flagged 'herding'")
        axes[0].legend(fontsize=6.5)
        fig.suptitle(f"Detection rate vs herding strength, all variants ({tag})", fontsize=10)
        fig.tight_layout()
        fig.savefig(RES_DIR / f"wh_variants_power_{tag}.png", dpi=200)
        plt.close(fig)


if __name__ == "__main__":
    RES_DIR.mkdir(exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summarize"
    if cmd == "e4":
        e4()
    elif cmd == "run":
        run_all(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    else:
        summarize()
