"""
Test robustness_wang_hudson.py's regression mechanics against synthetic
data built from KNOWN coefficients, same philosophy as test_panel.py /
test_csad.py: construct data where the "true" answer is known by
construction, then check the fitted model recovers it.

This validates the regression *code* (OLS setup, HAC fitting, coefficient
extraction, herding-flag logic) -- it does not validate Wang & Hudson's
economic theory, which isn't something a unit test can check.
"""
import numpy as np
import pandas as pd
from robustness_wang_hudson import standard_cck_regression, wang_hudson_scsad_regression

rng = np.random.default_rng(42)
n = 3000
dates = pd.bdate_range("2016-01-01", periods=n)
rm = rng.uniform(-0.04, 0.04, n)
post = (dates >= pd.Timestamp("2022-11-30")).astype(int)
tiny_noise = rng.normal(0, 1e-6, n)  # small enough not to swamp the signal

print("="*70)
print("TEST 1 -- standard CCK regression recovers known coefficients")
print("="*70)

# Case 1a: genuine herding, and it worsens post-ChatGPT (d2, d3 both < 0)
true_d0, true_d1, true_d2, true_d3 = 0.010, 2.0, -30.0, -20.0
csad_herd = true_d0 + true_d1*np.abs(rm) + true_d2*rm**2 + true_d3*(rm**2)*post + tiny_noise
df_herd = pd.DataFrame({"mkt_ret": rm, "csad": csad_herd, "post": post})
res = standard_cck_regression(df_herd)
print("Herding case (true d2=-30, d3=-20):")
print(f"  fitted abs_rm={res.params['abs_rm']:.3f} (true {true_d1}), "
      f"rm2={res.params['rm2']:.3f} (true {true_d2}), "
      f"rm2_post={res.params['rm2_post']:.3f} (true {true_d3})")
ok1a = (np.isclose(res.params["abs_rm"], true_d1, atol=0.1) and
        np.isclose(res.params["rm2"], true_d2, atol=1.0) and
        np.isclose(res.params["rm2_post"], true_d3, atol=1.0) and
        res.pvalues["rm2"] < 0.05 and res.pvalues["rm2_post"] < 0.05)
print(f"  Recovers true coefficients + flags significant: {'PASS' if ok1a else 'FAIL'}")

# Case 1b: no herding at all (d2 = d3 = 0 exactly)
csad_flat = true_d0 + true_d1*np.abs(rm) + tiny_noise
df_flat = pd.DataFrame({"mkt_ret": rm, "csad": csad_flat, "post": post})
res2 = standard_cck_regression(df_flat)
print("\nNo-herding case (true d2=0, d3=0):")
print(f"  fitted rm2={res2.params['rm2']:.5f} (p={res2.pvalues['rm2']:.3f}), "
      f"rm2_post={res2.params['rm2_post']:.5f} (p={res2.pvalues['rm2_post']:.3f})")
ok1b = res2.pvalues["rm2"] > 0.05 and res2.pvalues["rm2_post"] > 0.05
print(f"  Correctly finds NO significant curvature: {'PASS' if ok1b else 'FAIL'}")

print()
print("="*70)
print("TEST 2 -- Wang-Hudson SCSAD regression recovers known coefficients")
print("="*70)

# Case 2a: genuine herding under the corrected test (g3, g4 both < 0)
true_a, true_g1, true_g2, true_g3, true_g4 = 0.010, 1.5, 5.0, -400.0, -300.0
scsad_herd = (true_a + true_g1*rm + true_g2*rm**2 + true_g3*rm**3
              + true_g4*(rm**3)*post + tiny_noise)
df_wh_herd = pd.DataFrame({"mkt_ret": rm, "scsad": scsad_herd, "post": post})
res3 = wang_hudson_scsad_regression(df_wh_herd)
print("Herding case (true g3=-400, g4=-300):")
print(f"  fitted mkt_ret={res3.params['mkt_ret']:.3f} (true {true_g1}), "
      f"rm2={res3.params['rm2']:.3f} (true {true_g2}), "
      f"rm3={res3.params['rm3']:.3f} (true {true_g3}), "
      f"rm3_post={res3.params['rm3_post']:.3f} (true {true_g4})")
ok2a = (np.isclose(res3.params["rm3"], true_g3, atol=15.0) and
        np.isclose(res3.params["rm3_post"], true_g4, atol=15.0) and
        res3.pvalues["rm3"] < 0.05 and res3.pvalues["rm3_post"] < 0.05)
print(f"  Recovers true coefficients + flags significant: {'PASS' if ok2a else 'FAIL'}")

# Case 2b: no herding (g3 = g4 = 0 exactly)
scsad_flat = true_a + true_g1*rm + true_g2*rm**2 + tiny_noise
df_wh_flat = pd.DataFrame({"mkt_ret": rm, "scsad": scsad_flat, "post": post})
res4 = wang_hudson_scsad_regression(df_wh_flat)
print("\nNo-herding case (true g3=0, g4=0):")
print(f"  fitted rm3={res4.params['rm3']:.5f} (p={res4.pvalues['rm3']:.3f}), "
      f"rm3_post={res4.params['rm3_post']:.5f} (p={res4.pvalues['rm3_post']:.3f})")
ok2b = res4.pvalues["rm3"] > 0.05 and res4.pvalues["rm3_post"] > 0.05
print(f"  Correctly finds NO significant cubic term: {'PASS' if ok2b else 'FAIL'}")

