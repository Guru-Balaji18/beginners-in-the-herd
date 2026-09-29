"""Machinery checks for calibrated_test.py (Part F). Must all pass
before the simulation is run; a failure is a code bug."""
import numpy as np
import pandas as pd

import calibrated_test as ct
import main_regression as mr
import simulate_herding_tests as sim
from build_csad import compute_csad

cal = sim.load_calibration()
ctx = ct.load_context(cal)
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


# 1. On the REAL data, the same route reproduces the Step 5 primary g5/g7 t
panel = pd.read_csv(mr.OUT_DIR / "return_panel_final.csv", parse_dates=["date"])
market = pd.read_csv(mr.OUT_DIR / "market_returns_final.csv", parse_dates=["date"])
csad = compute_csad(panel, market).set_index("date")
ctrl = mr.controls_frame(csad.index, csad["mkt_ret"].values, ctx["vix"], ctx["fomc"], ctx["cpi"])
df = csad.join(ctx["entry"]).dropna(subset=["high", "low"])
got = ct.textbook_stats(csad, df, ctrl.reindex(df.index))
real = ct.real_stats()
for s in ct.STATS:
    check(f"real-data {s} reproduced", np.isclose(got[s], real[s], atol=1e-6), f"{got[s]:.4f} vs {real[s]:.4f}")

# 2. determinism and new seeds
a = ct.one_market(cal, ctx, ct.PART_NULL, "S5", 0, 0)
b = ct.one_market(cal, ctx, ct.PART_NULL, "S5", 0, 0)
check("same seed -> identical statistics", a == b)
Rf, _ = sim.simulate_returns(cal, "S5", 0, ct.rng_for(ct.PART_NULL, "S5", 0))
Rb, _ = sim.simulate_returns(cal, "S5", 0, sim.rng_for("S5", 0))
Rh, _ = sim.simulate_returns(cal, "S5", 0, ct.rng_for(ct.PART_HELDOUT, "S5", 0))
check("null seeds differ from Part B seeds", not np.allclose(Rf, Rb))
check("null seeds differ from held-out seeds", not np.allclose(Rf, Rh))
check("entry dummies present on post-ChatGPT High days", int((df["post"] * df["high"]).sum()) > 0)

# 3. calibrated p
check("calibrated p = share of null <= t", ct.calibrated_p([-3, -2, -1, 0], -2) == 0.5)
print(f"\n{sum(results)}/{len(results)} checks passed")
