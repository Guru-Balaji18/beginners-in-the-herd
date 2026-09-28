# Deviations from the 2026-09-28 addendum

Each entry is committed **before** the analysis it describes is run. The
addendum itself (`docs/addendum_2026-09-28.md`, commit ed63759) is never
edited after registration.

---

## D1 — 2026-09-28: add a no-winsorization run to Part B (in addition to, not instead of, the registered run)

**What happened.** The pre-registered validation (B8,
`test_simulate_herding_tests.py`) was run before the full simulation.
S1 is the textbook scenario, with no herding (kappa = 0) and 200
simulated markets:

| Pipeline | Standard CCK: "herding" found | Wang-Hudson: "herding" found |
|---|---|---|
| winsorized, as registered | 100% (mean t = -5.90) | 100% (mean t = -9.61) |
| no winsorization | 6.5% (mean t = -0.03) | 100% (mean t = -7.44) |

Two separate problems show up:

1. **Pooled winsorization manufactures false herding.** The registered
   pipeline copies `build_panel.py`: it clips all returns at the pooled
   0.1/99.9 percentiles. On an extreme market day most stocks fall past
   that shared cutoff and get clipped to the same value, which flattens
   that day's dispersion. On the worst simulated day, 45% of stocks were
   clipped. CCK then reads the flattening as herding.
2. **Our Wang-Hudson implementation over-rejects regardless**, exactly as
   predicted in addendum B7 (the SCSAD sign flip makes a jump at
   R_m = 0).

**Deviation.** The registered winsorized run goes ahead unchanged and
stays the primary Part B result. We **add** an identical run with
winsorization switched off:
- same scenarios, kappa grid, 1,000 markets per cell, seeds and
  decision rules;
- results tagged `winsorized = False`.

Reason: with winsorization on, the simulation can't tell "which test is
right" apart from "our cleaning step distorts both tests".

**Also found in validation (reported, not changed).** The registered
sign check (B6) fails for CCK: at kappa = 3000 in S1, CCK's quadratic
coefficient is strongly **positive** (mean t = +29 unwinsorized). A
follow-up on 6 simulated markets per kappa shows why. The quadratic
term detects herding at moderate strength (mean t = -4.6 at kappa = 10,
-13.3 at kappa = 100), then flips sign at extreme strength (+5.7 at
kappa = 1000, +37.7 at kappa = 3000). By then the decline has moved into
the |R_m| term (t = -44, -124). The CCK sign convention is therefore
right, but its power is **non-monotonic** in kappa under this
data-generating process. That is reported as a result.

## D2 — 2026-09-28: post-hoc real-data check of winsorization (not in the addendum; exploratory)

D1 implies the **real** pipeline's pooled winsorization could bias the
real CCK and Wang-Hudson base-herding statistics. Before looking at any
new numbers, we define the check:

- Count, per real trading day, the share of stocks clipped at the
  pooled bounds. Report the 10 worst days.
- Recompute returns without clipping: per-ticker `pct_change` of the
  cleaned close prices in `return_panel_final.csv`, i.e. the pipeline
  minus the clip.
- Rerun `compute_csad`, `standard_cck_regression` and
  `wang_hudson_scsad_regression` unchanged, and report the base t-stats
  next to the winsorized ones.

This is labeled post-hoc and exploratory. It does not change any
registered decision rule.
