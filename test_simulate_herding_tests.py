"""
Validation for simulate_herding_tests.py (Part B), written before the full
run as pre-specified in docs/addendum_2026-09-28.md (B8).

Each check states the pre-registered EXPECTATION. A failure here is a
result to report, not something to tune away: the addendum says
explicitly that the Wang-Hudson specification will not be changed to
make it pass.
"""
import numpy as np
import simulate_herding_tests as s

cal = s.load_calibration()
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"  {name}: {'PASS' if ok else 'FAIL'}  {detail}")


def detection_rates(scenario, kappa, reps, winsorize):
    t = np.array([[r["cck_t"], r["wh_t"]] for r in
                  (s.run_tests(*s.simulate_returns(cal, scenario, kappa, s.rng_for(scenario, i),
                                                   winsorize=winsorize), cal["dates"]) for i in range(reps))])
    return (t < s.ONE_SIDED_CRIT).mean(axis=0), t


print("=" * 70)
print("MACHINERY - generator and seeds (must pass; a failure here is a code bug)")
print("=" * 70)
rng_a, rng_b = s.rng_for("S5", 3), s.rng_for("S5", 3)
Ra, ma = s.simulate_returns(cal, "S5", 100, rng_a)
Rb, mb = s.simulate_returns(cal, "S5", 100, rng_b)
check("same seed -> identical simulated returns", np.array_equal(Ra, Rb) and np.array_equal(ma, mb))
check("same seed -> identical test results", s.one_market(cal, "S2", 30, 7) == s.one_market(cal, "S2", 30, 7))
R0, _ = s.simulate_returns(cal, "S2", 0, s.rng_for("S2", 1), winsorize=False)
rng = s.rng_for("S2", 1)
rm = s.block_bootstrap(cal["market_returns"], cal["n_days"], rng)
pick = rng.integers(0, len(cal["betas"]), size=cal["n_stocks_median"])
beta = np.asarray(cal["betas"])[pick]
z = rng.standard_normal((cal["n_days"], cal["n_stocks_median"]))
check("kappa = 0 reduces exactly to R = beta*Rm + eps",
      np.allclose(R0, beta[None, :] * rm[:, None] + z * cal["sigma_median"]))
Rw, mw = s.simulate_returns(cal, "S1", 0, s.rng_for("S1", 2))
check("market return the tests see = equal-weighted mean of simulated stocks", np.allclose(mw, Rw.mean(axis=1)))
check("block bootstrap draws only real market returns",
      np.isin(s.block_bootstrap(cal["market_returns"], 500, np.random.default_rng(0)), cal["market_returns"]).all())

print()
print("=" * 70)
print("PRE-REGISTERED EXPECTATIONS (B8) - a FAIL here is a finding")
print("=" * 70)
REPS = 200
for w in [True, False]:
    tag = "winsorized pipeline (as pre-registered)" if w else "no winsorization (diagnostic)"
    rate, t = detection_rates("S1", 0, REPS, w)
    print(f"\n  S1, kappa = 0, {REPS} markets, {tag}:")
    check("    CCK size near 5% (1%-10%)", 0.01 <= rate[0] <= 0.10, f"rate {rate[0]:.1%}, mean t {t[:, 0].mean():+.2f}")
    check("    Wang-Hudson size near 5% (1%-10%)", 0.01 <= rate[1] <= 0.10, f"rate {rate[1]:.1%}, mean t {t[:, 1].mean():+.2f}")
    rate, t = detection_rates("S1", 3000, 50, w)
    check("    kappa = 3000: CCK detects in >= 95%", rate[0] >= 0.95, f"rate {rate[0]:.1%}, mean t {t[:, 0].mean():+.2f}")
    check("    kappa = 3000: Wang-Hudson detects in >= 95%", rate[1] >= 0.95, f"rate {rate[1]:.1%}, mean t {t[:, 1].mean():+.2f}")

print()
print(f"{sum(ok for _, ok in results)}/{len(results)} checks passed")
