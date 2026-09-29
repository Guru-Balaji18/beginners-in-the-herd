"""Machinery checks for wang_hudson_variants.py (D5). Must pass before E5 runs."""
import numpy as np
import pandas as pd

import simulate_herding_tests as sim
import wang_hudson_variants as whv
from build_csad import compute_csad

cal = sim.load_calibration()
b = pd.read_csv(sim.RAW_PATH)
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


worst = 0.0
for sc, k, rep, w in [("S1", 0, 0, True), ("S5", 100, 3, False), ("S3", 3000, 7, True), ("S2", 0, 11, False)]:
    R, mkt = sim.simulate_returns(cal, sc, k, sim.rng_for(sc, rep), winsorize=w)
    slow = compute_csad(*sim.to_frames(R, mkt, cal["dates"]))
    fast = whv.fast_csad(R, cal["dates"])
    for col in ["csad", "scsad", "mkt_ret", "post"]:
        worst = max(worst, float(np.abs(slow[col].values - fast[col].values).max()))
    got = whv.all_variants(fast)
    ref = b[(b.scenario == sc) & (b.kappa == k) & (b.rep == rep) & (b.winsorized == w)].iloc[0]
    check(f"{sc} k={k} rep={rep} w={w}: wh_old and cck reproduce Part B",
          np.isclose(got["wh_old_t"], ref["wh_t"], atol=1e-8) and np.isclose(got["cck_t"], ref["cck_t"], atol=1e-8),
          f"wh {got['wh_old_t']:.6f} vs {ref['wh_t']:.6f}")
check("numpy CSAD/SCSAD/market/Post == compute_csad to 1e-12", worst <= 1e-12, f"max diff {worst:.2e}")

c = whv.fast_csad(*[sim.simulate_returns(cal, "S1", 0, sim.rng_for("S1", 0))[0], cal["dates"]])
r = whv.cck_zero_intercept(c)
check("cck_zero_intercept has no constant", "const" not in r.params.index)
check("wh_no_intercept has no constant", "const" not in whv.wh_no_intercept(c).params.index)
check("wh_sign_term has constant and sign term", {"const", "sign_rm"} <= set(whv.wh_sign_term(c).params.index))
print(f"\n{sum(results)}/{len(results)} checks passed")
