"""Six print-ready STEM-fair poster figures (PNG) plus a JSON of every plotted number.

Usage:  py board_figures.py          (all six)
        py board_figures.py b e      (only those)
Outputs: results/board/{a_entry_index,...,f_pipeline}.png and board_figures_data.json
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "board"
OUT.mkdir(parents=True, exist_ok=True)
JSON_PATH = OUT / "board_figures_data.json"

# ---------------------------------------------------------------- style
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID = "#e6e5e1"
CCK, WH, HIGH, LOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
FIGSIZE, DPI = (13, 7.5), 300

plt.rcParams.update({
    "font.family": "DejaVu Sans", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.labelsize": 15,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 13, "ytick.labelsize": 13,
    "axes.spines.top": False, "axes.spines.right": False, "text.color": INK,
    "axes.grid": False, "legend.frameon": False, "legend.fontsize": 13,
    "lines.linewidth": 2.5, "savefig.facecolor": SURFACE,
})


def style_ax(ax, grid=True):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK2, labelsize=13)
    if grid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def titles(fig, title, subtitle, y=0.99, wrap=None):
    fig.text(0.01, y, title, fontsize=21, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.01, y - 0.065, subtitle, fontsize=14, color=INK2, ha="left", va="top", linespacing=1.3)


def save(fig, name, pad=0.15):
    fig.savefig(OUT / name, dpi=DPI, facecolor=SURFACE, bbox_inches="tight", pad_inches=pad)
    plt.close(fig)
    print("wrote", OUT / name)


def load_json():
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def store(key, val):
    d = load_json()
    d[key] = val
    JSON_PATH.write_text(json.dumps(d, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                         encoding="utf-8")


def p_text(p, dec=3):
    return "p < 0.001" if p < 0.001 else f"p = {p:.{dec}f}"


# ================================================================ (a)
def fig_a():
    import investor_index as ii
    w, _ = ii.build_index("growth", "reference", "expanding", components=ii.load_components(), exclude=("hood",))
    w = w.copy()
    w.index = pd.to_datetime(w.index)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    style_ax(ax)
    ax.plot(w.index, w["index"], color=INK2, lw=2.5, zorder=3)

    def runs(col):
        v = (w[col] == 1).values
        out, start = [], None
        for i, flag in enumerate(v):
            if flag and start is None:
                start = i
            if (not flag or i == len(v) - 1) and start is not None:
                end = i if flag else i - 1
                out.append((w.index[start], w.index[end] + pd.Timedelta(days=7)))
                start = None
        return out

    for col, colr in (("high", HIGH), ("low", LOW)):
        for a, b in runs(col):
            ax.axvspan(a, b, color=colr, alpha=0.28, lw=0, zorder=1)

    cg = pd.Timestamp("2022-11-30")
    ax.axvline(cg, color=INK, ls="--", lw=2, zorder=4)
    ymin, ymax = w["index"].min(), w["index"].max()
    span = ymax - ymin
    ax.set_ylim(ymin - 0.05 * span, ymax + 0.22 * span)
    ax.text(cg + pd.Timedelta(days=25), ax.get_ylim()[1] - 0.03 * span, "ChatGPT released (Nov 30, 2022)",
            fontsize=13, color=INK, ha="left", va="top")

    peaks = {}
    spec = [("COVID account boom", "2020-01-01", "2020-06-30", (-95, 38), "right"),
            ("Meme-stock surge", "2020-12-15", "2021-03-15", (0, 22), "center"),
            ("AI rally", "2024-01-01", "2024-12-31", (0, 38), "center")]
    for label, a, b, off, ha in spec:
        seg = w.loc[a:b, "index"]
        t, v = seg.idxmax(), float(seg.max())
        peaks[label] = {"week_start": str(t.date()), "index": v}
        ax.annotate(label, xy=(t, v), xytext=off, textcoords="offset points", fontsize=13, color=INK2,
                    ha=ha, va="bottom", arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, shrinkA=2, shrinkB=3))
    ax.set_ylabel("New-investor entry index (z-score)")
    ax.set_xlim(w.index.min(), w.index.max() + pd.Timedelta(days=7))
    ax.legend(handles=[Patch(color=HIGH, alpha=0.28, label="High-entry weeks (top third)"),
                       Patch(color=LOW, alpha=0.28, label="Low-entry weeks (bottom third)"),
                       Line2D([], [], color=INK2, lw=2.5, label="Entry index")],
              loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0), columnspacing=1.6, handlelength=1.6)
    titles(fig, "New investors poured in at different times, before and after ChatGPT",
           "Average of Google Trends, Interactive Brokers and Schwab growth z-scores, using only past data.")
    fig.subplots_adjust(top=0.83, left=0.07, right=0.985, bottom=0.1)
    post = w[w.index >= cg]
    hi = post.loc[post["high"] == 1].groupby(post.loc[post["high"] == 1].index.year).size()
    lo = post.loc[post["low"] == 1].groupby(post.loc[post["low"] == 1].index.year).size()
    store("a_entry_index", {
        "source": "investor_index.build_index('growth','reference','expanding', exclude=('hood',))",
        "n_weeks": int(len(w)), "first_week": str(w.index.min().date()), "last_week": str(w.index.max().date()),
        "n_high_weeks_total": int((w["high"] == 1).sum()), "n_low_weeks_total": int((w["low"] == 1).sum()),
        "high_weeks_by_year_on_or_after_2022-11-30": {int(k): int(v) for k, v in hi.items()},
        "low_weeks_by_year_on_or_after_2022-11-30": {int(k): int(v) for k, v in lo.items()},
        "high_weeks_after_chatgpt_total": int(hi.sum()), "low_weeks_after_chatgpt_total": int(lo.sum()),
        "annotated_peaks": peaks, "chatgpt_date": "2022-11-30",
    })
    save(fig, "a_entry_index.png")


# ================================================================ (b)
def fig_b():
    import step8_analyses as s8
    panel, market = s8.load_panel_market()
    df, ctrl = s8.frames_from(panel, market[["date", "mkt_ret_eq"]])
    res = s8.fit_nw5(df, ctrl, "cck")
    P = res.params
    g5 = float(P["rm2_post_high"])
    s5 = pd.read_csv(ROOT / "data" / "step5_main_results.csv")
    r = s5[(s5.primary == True) & (s5.test == "cck") & (~s5.variant.str.contains("lower-order"))].iloc[0]
    p_nw = float(r.g5_p) / 2 if g5 < 0 else 1 - float(r.g5_p) / 2
    rs = pd.read_csv(ROOT / "results" / "real_se_comparison.csv")
    p_boot = float(rs[(rs.test == "cck") & (rs.term == "g5") & (rs.method == "boot")].p_one_sided.iloc[0])
    edges = [0, .005, .01, .015, .02, .03, .05]
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True)
    data = {}
    for ax, post, name in zip(axes, (0, 1), ("Before ChatGPT", "After ChatGPT")):
        style_ax(ax)
        for flag, colr, lab in (("high", HIGH, "High entry"), ("low", LOW, "Low entry")):
            hi, lo = (1, 0) if flag == "high" else (0, 1)
            cell = df[(df["post"] == post) & (df[flag] == 1)]
            days = cell.index
            ab = cell["mkt_ret"].abs()
            xmax = min(0.05, float(np.quantile(ab, 0.99)))
            x = np.linspace(0, xmax, 100)
            base = float(P["const"]) + sum(float(P[c]) * float(ctrl.loc[days, c].mean()) for c in ctrl.columns)
            q = float(P["rm2"]) + float(P["rm2_post"]) * post + float(P["rm2_high"]) * hi \
                + float(P["rm2_post_high"]) * post * hi + float(P["rm2_low"]) * lo + float(P["rm2_post_low"]) * post * lo
            y = base + float(P["abs_rm"]) * x + q * x ** 2
            ax.plot(x * 100, y * 100, color=colr, lw=2.5, zorder=3)
            bins = pd.cut(ab, edges, include_lowest=True)
            g = cell.assign(ab=ab, b=bins).groupby("b", observed=True).agg(n=("csad", "size"), x=("ab", "mean"), y=("csad", "mean"))
            g = g[g.n >= 10]
            ax.plot(g.x * 100, g.y * 100, "o", color=colr, ms=9, mec=INK, mew=0.6, zorder=4)
            ax.annotate(lab, xy=(x[-1] * 100, y[-1] * 100), xytext=(6, 0), textcoords="offset points",
                        fontsize=13, color=INK, ha="left", va="center")
            data[f"{name}|{lab}"] = {"n_days": int(len(cell)), "curve_x_pct": (x * 100).tolist(), "curve_y_pct": (y * 100).tolist(),
                                    "dots_x_pct": (g.x * 100).tolist(), "dots_y_pct": (g.y * 100).tolist(), "dots_n": g.n.tolist(),
                                    "quad_coef": q, "base_intercept_with_mean_controls": base}
        ax.set_title(name, fontsize=16, fontweight="bold", color=INK, loc="left")
        ax.set_xlabel("Size of the day's market move, |R_m| (%)")
        ax.set_xlim(0, 6.6)
    axes[0].set_ylabel("Dispersion across stocks, CSAD (%)")
    note = f"Key coefficient g5 = {g5:.2f};\none-sided p = {p_nw:.3f} (Newey-West), {p_boot:.2f} (bootstrap)"
    axes[1].text(0.02, 0.97, note, transform=axes[1].transAxes, fontsize=13, color=INK2, ha="left", va="top", wrap=True)
    titles(fig, "Herding would make the High-entry curve bend down after ChatGPT. It does not.",
           "Lines: fitted standard (CCK) model. Dots: average dispersion on days with similar market moves.")
    fig.subplots_adjust(top=0.82, left=0.07, right=0.985, bottom=0.12, wspace=0.06)
    store("b_dispersion_curves", {
        "sources": "step8_analyses.fit_nw5(cck); data/step5_main_results.csv; results/real_se_comparison.csv",
        "g5": g5, "p_one_sided_newey_west": p_nw, "p_one_sided_bootstrap": p_boot,
        "g5_p_two_sided_step5": float(r.g5_p), "params": {k: float(v) for k, v in P.items()},
        "bin_edges": edges, "cells": data})
    save(fig, "b_dispersion_curves.png")


# ================================================================ (c)
def fig_c():
    s5 = pd.read_csv(ROOT / "data" / "step5_main_results.csv")
    s8 = pd.read_csv(ROOT / "results" / "step8_results.csv")

    def label(r):
        parts = ["with Robinhood" if r.hood else "no Robinhood",
                 "growth rates" if r["mode"] == "growth" else "raw counts",
                 "High/Low dummies" if r.form == "dummy" else "continuous index"]
        if isinstance(r.cutoff, str):
            parts.append("past-data cutoffs" if r.cutoff == "expanding" else "full-sample cutoffs")
        if "lower-order" in r.variant:
            return "Main specification + lower-order terms"
        return ", ".join(parts)

    s5 = s5.copy()
    s5["label"] = s5.apply(label, axis=1)
    cck = s5[s5.test == "cck"]
    n_neg = int(((s5.g5_p < 0.05) & (s5.g5 < 0)).sum())
    n_pos = int(((s5.g5_p < 0.05) & (s5.g5 > 0)).sum())
    n_rows = len(s5)

    # row order: union of labels, main first
    main_lab = s5[s5.primary == True].label.iloc[0]
    labs = [main_lab] + [l for l in cck.label if l != main_lab]
    for l in s5[s5.test == "wh"].label:
        if l not in labs:
            labs.append(l)
    pos = {main_lab: 0}
    for l in labs:
        if l not in pos:
            pos[l] = len(pos)
    nrow = len(labs)
    finals = [("full sample (reference)", "Main spec, bootstrap SE"), ("8b GPT-4 date (2023-03-14)", "GPT-4 date"),
              ("8c without the 7 largest tech companies", "Without 7 largest tech"),
              ("8d liquidity-weighted market", "Liquidity-weighted market")]
    head_y = nrow + 0.6
    fin_y = {a: nrow + 1.7 + i for i, (a, _) in enumerate(finals)}

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True, gridspec_kw={"width_ratios": [1, 1]})
    store_rows = {}
    for ax, test, colr, ttl in ((axes[0], "cck", CCK, "Standard test (CCK)"), (axes[1], "wh", WH, "Wang-Hudson test")):
        style_ax(ax, grid=False)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        d = s5[s5.test == test]
        rows = []
        for _, r in d.iterrows():
            y = pos[r.label]
            sig = r.g5_p < 0.05
            ci = 1.96 * r.g5_se
            ax.errorbar(r.g5, y, xerr=ci, fmt="o", color=colr, ms=8, mfc=colr if sig else "white", mec=colr, mew=1.8,
                        elinewidth=1.5, capsize=3, zorder=3)
            rows.append({"label": r.label.replace("\n", " "), "primary": bool(r.primary), "g5": float(r.g5), "g5_se": float(r.g5_se),
                         "g5_p": float(r.g5_p), "ci_lo": float(r.g5 - ci), "ci_hi": float(r.g5 + ci), "significant_5pct": bool(sig)})
        f = s8[(s8.method == "boot") & (s8.term == "g5") & (s8.test == test)].set_index("analysis")
        frows = []
        for a, nm in finals:
            r = f.loc[a]
            y = fin_y[a]
            sig = r.p_two_sided < 0.05
            ci = 1.96 * r.se
            ax.errorbar(r.coef, y, xerr=ci, fmt="s", color=colr, ms=8, mfc=colr if sig else "white", mec=colr, mew=1.8,
                        elinewidth=1.5, capsize=3, zorder=3)
            frows.append({"analysis": a, "label": nm, "coef": float(r.coef), "se": float(r.se), "p_two_sided": float(r.p_two_sided),
                          "p_one_sided": float(r.p_one_sided), "ci_lo": float(r.coef - ci), "ci_hi": float(r.coef + ci),
                          "significant_5pct": bool(sig)})
        store_rows[test] = {"step5_rows": rows, "final_checks": frows}
        ax.axvline(0, color=MUTED, lw=1.5, zorder=1)
        ax.axhline(nrow + 0.1, color=GRID, lw=1.2)
        ax.set_title(ttl, fontsize=16, fontweight="bold", color=INK, loc="left")
        ax.set_xlabel("g5 (95% CI)")
        ax.text(0.0, head_y, "Final checks (bootstrap 95% CI)", transform=ax.get_yaxis_transform(), fontsize=13,
                fontweight="bold", color=INK, ha="left", va="center")
    ylabels = [""] * (nrow)
    for l, i in pos.items():
        ylabels[i] = l
    ticks = list(range(nrow)) + [fin_y[a] for a, _ in finals]
    tl = ylabels + [nm for _, nm in finals]
    axes[0].set_yticks(ticks)
    axes[0].set_yticklabels(tl, fontsize=11)
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    axes[0].get_yticklabels()[0].set_text("MAIN SPECIFICATION")
    tl[0] = "MAIN SPECIFICATION"
    axes[0].set_yticklabels(tl, fontsize=11)
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    for t in axes[0].get_yticklabels():
        t.set_color(INK)
    axes[0].set_ylim(fin_y[finals[-1][0]] + 0.8, -0.8)
    axes[0].tick_params(axis="y", length=0)
    axes[1].tick_params(axis="y", length=0)
    axes[1].spines["left"].set_visible(False)
    axes[0].spines["left"].set_visible(False)
    leg = [Line2D([], [], marker="o", ls="", color=INK2, ms=8, mfc=INK2, label="significant at 5%"),
           Line2D([], [], marker="o", ls="", color=INK2, ms=8, mfc="white", mew=1.8, label="not significant")]
    fig.legend(handles=leg, loc="upper right", bbox_to_anchor=(0.985, 0.875), ncol=2, fontsize=13, frameon=False)
    titles(fig, "H1 predicted g5 < 0. Across 25 regressions the answer flips sign.",
           f"{n_neg} significantly negative, {n_pos} significantly positive, the rest not significant. Lines: 95% confidence intervals.")
    fig.text(0.01, 0.005, "Wang-Hudson intervals are not trustworthy: the test fails our false-alarm check.",
             fontsize=12, color=INK2, ha="left", va="bottom")
    fig.subplots_adjust(top=0.78, left=0.36, right=0.985, bottom=0.14, wspace=0.08)
    store("c_g5_forest", {"sources": "data/step5_main_results.csv; results/step8_results.csv (method=boot, term=g5)",
                          "n_rows_step5": int(n_rows), "n_significant_negative": n_neg, "n_significant_positive": n_pos,
                          "n_not_significant": int(n_rows - n_neg - n_pos), **store_rows})
    save(fig, "c_g5_forest.png")


# ================================================================ (d)
def fig_d():
    h = pd.read_csv(ROOT / "data" / "step4_h3_results.csv")
    h = h[(h.primary == True) & (h.split == "terciles")].set_index("test")
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE)
    out = {}
    for ax, test, ttl in ((axes[0], "cck", "Standard test (CCK)"), (axes[1], "wh", "Wang-Hudson test")):
        style_ax(ax)
        r = h.loc[test]
        vals = [(r.g5_high, r.g5_high_se, r.g5_high_p, HIGH, "High-attention stocks"),
                (r.g5_low, r.g5_low_se, r.g5_low_p, LOW, "Low-attention stocks")]
        lo_lim = min(v - 1.96 * s for v, s, *_ in vals)
        hi_lim = max(0, max(v + 1.96 * s for v, s, *_ in vals))
        rng = hi_lim - lo_lim
        for i, (v, s, p, colr, nm) in enumerate(vals):
            ax.bar(i, v, width=0.6, color=colr, edgecolor=INK, lw=0.8, zorder=2)
            ax.errorbar(i, v, yerr=1.96 * s, color=INK, elinewidth=1.5, capsize=5, capthick=1.5, zorder=3)
            end = v - 1.96 * s if v < 0 else v + 1.96 * s
            ax.text(i, end - 0.03 * rng if v < 0 else end + 0.03 * rng, f"{v:.2f} ({p_text(p, 3 if p < 0.01 else 2)})",
                    ha="center", va="top" if v < 0 else "bottom", fontsize=13, color=INK)
            out[f"{test}|{nm}"] = {"g5": float(v), "se": float(s), "p": float(p), "ci_lo": float(v - 1.96 * s), "ci_hi": float(v + 1.96 * s)}
        ax.axhline(0, color=INK, lw=1.5, zorder=4)
        ax.set_ylim(lo_lim - 0.22 * rng, hi_lim + 0.12 * rng)
        ax.set_xlim(-0.6, 1.6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["High-attention\nstocks", "Low-attention\nstocks"], fontsize=13, color=INK)
        ax.tick_params(axis="x", length=0)
        ax.set_title(ttl, fontsize=16, fontweight="bold", color=INK, loc="left")
        ax.set_xlabel(f"High minus Low = {r['diff']:+.2f} ({p_text(r.diff_p)})", fontsize=13, color=INK2, labelpad=12)
        out[f"{test}|diff"] = {"diff": float(r["diff"]), "diff_se": float(r.diff_se), "diff_p": float(r.diff_p)}
    axes[0].set_ylabel("Key coefficient g5")
    axes[1].set_ylabel("Key coefficient g5")
    titles(fig, "H3 predicted a bigger effect in high-attention stocks. The data show the opposite.",
           "Key coefficient g5 estimated separately for the most and least retail-attention thirds of stocks. Bars: 95% confidence intervals.")
    fig.subplots_adjust(top=0.82, left=0.08, right=0.985, bottom=0.17, wspace=0.28)
    store("d_h3_attention", {"source": "data/step4_h3_results.csv (primary, terciles)", **out})
    save(fig, "d_h3_attention.png")


# ================================================================ (e)
def fig_e():
    import simulate_herding_tests as sim
    import wang_hudson_variants as whv
    from robustness_wang_hudson import wang_hudson_scsad_regression
    cal = sim.load_calibration()
    R, _ = sim.simulate_returns(cal, "S1", 0, sim.rng_for("S1", 0), winsorize=False)
    c = whv.fast_csad(R, cal["dates"])
    fit = wang_hudson_scsad_regression(c)
    P = fit.params
    t3 = float(fit.tvalues["rm3"])

    sp = pd.read_csv(ROOT / "results" / "sim_size_power.csv")
    row = sp[(sp.winsorized == True) & (sp.scenario == "S5") & (sp.kappa == 0)].iloc[0]
    pp = pd.read_csv(ROOT / "results" / "wh_paper_e5_size_power.csv")
    pr = pp[(pp.winsorized == True) & (pp.scenario == "S5") & (pp.kappa == 0) & (pp.variant == "wh_paper")].iloc[0]
    rl = pd.read_csv(ROOT / "results" / "wh_rlm_size_summary.csv")
    rr = rl[(rl.scenario == "S5") & (rl.winsorized == True)].iloc[0]
    bars = [("Standard test (CCK)", float(row.cck_detect), CCK, "results/sim_size_power.csv cck_detect"),
            ("Wang-Hudson, our code", float(row.wh_detect), WH, "results/sim_size_power.csv wh_detect"),
            ("Wang-Hudson, exactly\nas published\n(OLS, robust SE)", float(pr.flag_one_sided), WH,
             "results/wh_paper_e5_size_power.csv flag_one_sided"),
            ("Wang-Hudson, exactly\nas published\n(Huber robust fit)", float(rr.false_alarm_one_sided), WH,
             "results/wh_rlm_size_summary.csv false_alarm_one_sided")]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIGSIZE, gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.6})
    style_ax(a1)
    x, y = c["mkt_ret"].values * 100, c["scsad"].values * 100
    a1.scatter(x, y, s=6, color=MUTED, alpha=0.5, zorder=2, lw=0)
    xs = np.linspace(c["mkt_ret"].min(), c["mkt_ret"].max(), 400)
    ys = P["const"] + P["mkt_ret"] * xs + P["rm2"] * xs ** 2 + P["rm3"] * xs ** 3
    a1.plot(xs * 100, ys * 100, color=WH, lw=2.5, zorder=4)
    a1.axvline(0, color=MUTED, lw=1, ls=":")
    a1.set_ylim(-3.9, 4.0)
    a1.annotate("Jump at a market\nmove of zero", xy=(0, 1.3), xytext=(-6.8, 1.9), fontsize=13, color=INK2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, shrinkA=2, shrinkB=4))
    a1.text(0.03, 0.97, f"Cubic term t = {t3:.2f}:\nreads as \"herding\"", transform=a1.transAxes, fontsize=13,
            color=INK, ha="left", va="top")
    a1.set_title("One simulated market with NO herding", fontsize=16, fontweight="bold", color=INK, loc="left")
    a1.set_xlabel("Market move, R_m (%)")
    a1.set_ylabel("Signed dispersion, SCSAD (%)")

    style_ax(a2, grid=False)
    a2.xaxis.grid(True, color=GRID, linewidth=0.8)
    a2.axvspan(3.6, 6.4, color="#d9d8d2", zorder=0, lw=0)
    for i, (nm, v, colr, src) in enumerate(bars):
        a2.barh(i, v * 100, height=0.6, color=colr, zorder=2)
        a2.text(v * 100 + 1.5, i, f"{v * 100:.1f}%" if v * 100 < 99.95 else "100%", va="center", ha="left", fontsize=13, color=INK)
    a2.set_yticks(range(len(bars)))
    a2.set_yticklabels([b[0] for b in bars], fontsize=12, color=INK)
    a2.invert_yaxis()
    a2.set_xlim(0, 108)
    a2.set_xticks([0, 20, 40, 60, 80, 100])
    a2.set_xlabel("Markets where the test reports herding (%)")
    a2.tick_params(axis="y", length=0)
    a2.text(7.5, 0.6, "Correct rate: about 5%", fontsize=13, color=INK2, ha="left", va="center")
    a2.set_ylim(len(bars) - 0.5, -0.6)
    a2.set_title("False alarms in 1,000 realistic\nno-herding markets", fontsize=16, fontweight="bold", color=INK, loc="left")
    titles(fig, "A published herding test says \"herding\" even when there is none",
           "Left: the signed measure jumps at a market move of zero, and a smooth curve bent across the jump looks like herding.\n"
           "Right: share of 1,000 simulated markets with no herding where each test reports herding.")
    fig.subplots_adjust(top=0.74, left=0.07, right=0.985, bottom=0.13)
    store("e_false_alarms", {
        "left_panel": {"scenario": "S1", "kappa": 0, "rep": 0, "winsorized": False, "cubic_term_t": t3,
                       "params": {k: float(v) for k, v in P.items()}, "n_days": int(len(c)),
                       "source": "simulate_herding_tests + wang_hudson_variants.fast_csad + robustness_wang_hudson"},
        "right_panel": {"scenario": "S5", "winsorized": True, "kappa": 0,
                        "bars": [{"label": b[0].replace("\n", " "), "rate": b[1], "source": b[3]} for b in bars]}})
    save(fig, "e_false_alarms.png")


# ================================================================ (f)
def fig_f():
    s5 = pd.read_csv(ROOT / "data" / "step5_main_results.csv")
    pc = json.loads((ROOT / "results" / "partC_summary.json").read_text())
    sp = pd.read_csv(ROOT / "results" / "sim_size_power.csv")
    cal = pd.read_csv(ROOT / "results" / "calibrated_test_results.csv").set_index("statistic")
    rs = pd.read_csv(ROOT / "results" / "real_se_comparison.csv")
    s8 = pd.read_csv(ROOT / "results" / "step8_results.csv")
    panel = pd.read_csv(ROOT / "data" / "return_panel_final.csv", usecols=["ticker"])
    n_stockdays, n_stocks = int(len(panel)), int(panel.ticker.nunique())
    n_versions = int(len(s5))
    n_markets = int(sp.reps.sum())
    wh_fa = float(sp[(sp.winsorized == True) & (sp.scenario == "S5") & (sp.kappa == 0)].wh_detect.iloc[0])
    p_placebo = float(pc["cck_empirical_p"])
    n_plac = int(pc["cck_n_identified_g5"])
    p_cal = float(cal.loc["cck_g5_t", "calibrated_p_one_sided"])
    p_boot = float(rs[(rs.test == "cck") & (rs.term == "g5") & (rs.method == "boot")].p_one_sided.iloc[0])
    fin = s8[(s8.test == "cck") & (s8.term == "g5") & (s8.method == "boot") & (s8.analysis != "full sample (reference)")].p_one_sided
    p_lo, p_hi = float(fin.min()), float(fin.max())
    nums = {"stock_days": (n_stockdays, "data/return_panel_final.csv rows"), "stocks": (n_stocks, "data/return_panel_final.csv unique tickers"),
            "regression_versions_x_tests": (n_versions, "data/step5_main_results.csv rows (all tests)"),
            "placebo_dates": (n_plac, "results/partC_summary.json cck_n_identified_g5"),
            "placebo_p": (p_placebo, "results/partC_summary.json cck_empirical_p"),
            "simulated_markets": (n_markets, "results/sim_size_power.csv sum of reps"),
            "wh_false_alarm_S5_wins": (wh_fa, "results/sim_size_power.csv wh_detect"),
            "calibrated_p": (p_cal, "results/calibrated_test_results.csv cck_g5_t calibrated_p_one_sided"),
            "bootstrap_p": (p_boot, "results/real_se_comparison.csv cck g5 boot p_one_sided"),
            "final_checks_p_min": (p_lo, "results/step8_results.csv cck g5 boot p_one_sided (8b-8d)"),
            "final_checks_p_max": (p_hi, "results/step8_results.csv cck g5 boot p_one_sided (8b-8d)")}
    # text, with file values substituted
    t = {
        "r1": [("1  Data", f"Russell 1000 stocks, 2016 to 2026\n{n_stockdays:,} stock-days, {n_stocks:,} stocks"),
               ("2  Herding measures", "CSAD (standard test)\nSCSAD (Wang-Hudson test)"),
               ("3  Who is entering?", "New-investor entry index\nGoogle Trends, IBKR, Schwab"),
               ("4  Main regression", f"g5 = Post × High-entry × R_m²\n{n_versions} versions, 2 tests")],
        "r2": [("Is it ChatGPT?", f"{n_plac} placebo dates: p = {p_placebo:.2f}\nGone with year-by-year slopes"),
               ("Can the tests be trusted?", f"{n_markets:,} simulated markets\nWang-Hudson: {wh_fa * 100:.0f}% false alarms"),
               ("Checked against the paper", "Same flaw in the published method\nPaper's own simulation hid it"),
               ("Honest p-values", f"Calibrated test: p = {p_cal:.2f}\nBootstrap SE: p = {p_boot:.2f}"),
               ("Final checks", f"GPT-4 date, no big tech,\nliquidity-weighted: p = {p_lo:.2f} to {p_hi:.2f}")]}
    import textwrap
    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    ax.text(1, 58.5, "How the project works", fontsize=21, fontweight="bold", color=INK, ha="left", va="top")

    def wrap(txt, n):
        N = chr(160)
        txt = txt.replace('p = ', 'p' + N + '=' + N).replace(', 1,280 stocks', ', 1,280' + N + 'stocks').replace(chr(10) + '2,260,838 stock-days,', chr(10) + '2,260,838' + N + 'stock-days,').replace('2016 to 2026', '2016' + N + 'to' + N + '2026')
        return "\n".join(w for line in txt.split("\n") for w in (textwrap.wrap(line, n) or [""]))

    def box(x, y, w, h, title, body, nt, nb, ec=INK2, lw=1.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc="white", ec=ec, lw=lw, zorder=2))
        tt = wrap(title, nt)
        ax.text(x + w / 2, y + h - 1.6, tt, fontsize=14, fontweight="bold", color=INK, ha="center", va="top", zorder=3, linespacing=1.2)
        off = 1.6 + 2.5 * (tt.count("\n") + 1) + 1.2
        ax.text(x + w / 2, y + h - off, wrap(body, nb), fontsize=12, color=INK2, ha="center", va="top", linespacing=1.35, zorder=3)

    def arrow(p, q):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=20, color=MUTED, lw=2, zorder=1, shrinkA=0, shrinkB=0))

    bw, gap, y1, bh = 23.2, 2.0, 40.5, 14
    xs = [1 + i * (bw + gap) for i in range(4)]
    for (ti, bo), x in zip(t["r1"], xs):
        box(x, y1, bw, bh, ti, bo, 99, 30)
    for i in range(3):
        arrow((xs[i] + bw + 0.2, y1 + bh / 2), (xs[i + 1] - 0.2, y1 + bh / 2))
    bw2, gap2, y2, bh2 = 18.4, 1.5, 19.5, 16.5
    xs2 = [1 + i * (bw2 + gap2) for i in range(5)]
    bus = 39.3
    ax.text(1, 37.6, "Checks", fontsize=14, fontweight="bold", color=INK, ha="left", va="center")
    c4 = xs[3] + bw / 2
    ax.plot([c4, c4], [y1 - 0.2, bus], color=MUTED, lw=2, zorder=1, solid_capstyle="butt")
    cs = [x + bw2 / 2 for x in xs2]
    ax.plot([cs[0], max(cs[-1], c4)], [bus, bus], color=MUTED, lw=2, zorder=1, solid_capstyle="butt")
    for i, ((ti, bo), x) in enumerate(zip(t["r2"], xs2)):
        flag = i == 1
        box(x, y2, bw2, bh2, ti, bo, 18, 25, ec=WH if flag else INK2, lw=2.5 if flag else 1.5)
        arrow((cs[i], bus), (cs[i], y2 + bh2 + 0.2))
    ax.add_patch(FancyBboxPatch((1, 3.5), 98, 11.5, boxstyle="round,pad=0,rounding_size=1.2", fc="white", ec=INK, lw=2, zorder=2))
    ax.text(50, 13.6, "What we found", fontsize=14, fontweight="bold", color=INK, ha="center", va="top", zorder=3)
    ax.text(50, 9.8, "Hypotheses H1 to H3 are not supported. A widely used herding test (Wang-Hudson) reports herding in markets\n"
                     "that have none, and we showed why.", fontsize=12, color=INK2, ha="center", va="top", linespacing=1.4, zorder=3)
    arrow((50, y2 - 0.2), (50, 15.2))
    store("f_pipeline", {"numbers": {k: {"value": v[0], "source": v[1]} for k, v in nums.items()}, "text": t,
                         "note": "text numbers are formatted from these file values"})
    save(fig, "f_pipeline.png")


FIGS = {"a": fig_a, "b": fig_b, "c": fig_c, "d": fig_d, "e": fig_e, "f": fig_f}

if __name__ == "__main__":
    which = [a.lower() for a in sys.argv[1:]] or list(FIGS)
    for k in which:
        FIGS[k]()
