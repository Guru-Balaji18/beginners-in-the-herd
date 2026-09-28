"""
Robustness check: does the Yahoo delisted-data gap actually matter for
the herding conclusions?

Runs BOTH the standard CCK/CSAD test and the Wang-Hudson SCSAD test on
two versions of the panel:
  (a) data/return_panel.csv + market_returns.csv
      -- strict native-Yahoo-data-only panel (no renames, no Stooq)
  (b) data/return_panel_recovered.csv + market_returns_recovered.csv
      -- (a) plus every ticker recoverable via Yahoo rename-search and/or
      the Stooq bulk archive (see rebuild_panel_with_recovery.py)

Compares the key interaction coefficients (the two-way Post_t
interaction -- rm2_post in the standard test, rm3_post in Wang-Hudson;
the full three-way Post*High interaction from the main model can't be
run yet since Step 3's new-investor entry index doesn't exist). If they
move only modestly and agree in sign/significance, the data gap likely
doesn't change the paper's conclusions. If they diverge, the gap matters
and needs to be addressed before drawing conclusions from either version.
"""
import pandas as pd
from pathlib import Path

from build_csad import compute_csad
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression

OUT_DIR = Path("data")


def run_both_tests(panel_path, market_path, label):
    panel = pd.read_csv(panel_path)
    market = pd.read_csv(market_path)
    csad = compute_csad(panel, market)

    cck = standard_cck_regression(csad)
    wh = wang_hudson_scsad_regression(csad)

    print(f"\n{'='*70}\n{label}  (n={len(csad)} days, {panel['ticker'].nunique()} tickers)\n{'='*70}")
    print("Standard CCK:")
    for term in ["abs_rm", "rm2", "rm2_post"]:
        print(f"  {term:10s} = {cck.params[term]:+.6f}  (p={cck.pvalues[term]:.4f})")
    print("Wang-Hudson SCSAD:")
    for term in ["mkt_ret", "rm2", "rm3", "rm3_post"]:
        print(f"  {term:10s} = {wh.params[term]:+.6f}  (p={wh.pvalues[term]:.4f})")

    return {
        "label": label, "n_days": len(csad), "n_tickers": panel["ticker"].nunique(),
        "cck_rm2": cck.params["rm2"], "cck_rm2_p": cck.pvalues["rm2"],
        "cck_rm2_post": cck.params["rm2_post"], "cck_rm2_post_p": cck.pvalues["rm2_post"],
        "wh_rm3": wh.params["rm3"], "wh_rm3_p": wh.pvalues["rm3"],
        "wh_rm3_post": wh.params["rm3_post"], "wh_rm3_post_p": wh.pvalues["rm3_post"],
    }


if __name__ == "__main__":
    a = run_both_tests(OUT_DIR / "return_panel.csv", OUT_DIR / "market_returns.csv",
                        "(a) STRICT native-Yahoo-only panel")
    b = run_both_tests(OUT_DIR / "return_panel_recovered.csv", OUT_DIR / "market_returns_recovered.csv",
                        "(b) FULL panel incl. rename/Stooq recoveries")

    print(f"\n{'='*70}\nCOMPARISON -- does the data gap change the core interaction coefficient?\n{'='*70}")
    for metric, coef_key, p_key in [("Standard CCK Post-interaction (rm2_post)", "cck_rm2_post", "cck_rm2_post_p"),
                                      ("Wang-Hudson Post-interaction (rm3_post)", "wh_rm3_post", "wh_rm3_post_p")]:
        va, pa = a[coef_key], a[p_key]
        vb, pb = b[coef_key], b[p_key]
        pct_change = abs(vb - va) / abs(va) * 100 if va != 0 else float("nan")
        sig_a = pa < 0.05
        sig_b = pb < 0.05
        print(f"\n{metric}:")
        print(f"  (a) strict Yahoo:  {va:+.6f} (p={pa:.4f}, {'significant' if sig_a else 'not significant'})")
        print(f"  (b) with recovery: {vb:+.6f} (p={pb:.4f}, {'significant' if sig_b else 'not significant'})")
        print(f"  magnitude change: {pct_change:.1f}%")
        if sig_a == sig_b and (va < 0) == (vb < 0):
            print(f"  -> AGREE in sign and significance -- the data gap does not appear to change this conclusion.")
        else:
            print(f"  -> DISAGREE in sign or significance -- the data gap MATTERS for this conclusion.")
