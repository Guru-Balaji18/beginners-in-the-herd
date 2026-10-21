D7 — Robust-regression reading of Wang & Hudson Solution 2 (pre-registered 2026-10-21, before code).
Question: Does Solution 2 still over-reject when fitted with a robust M-estimator instead of OLS?
Specification: SCSAD_t on a constant, R_m, R_m², R_m³, fitted with statsmodels RLM, Huber-T norm (t = 1.345), default MAD scale and default covariance. Herding = γ3 < 0. Report the one-sided 5% rule and the paper’s two-sided rule. Log returns; days with R_m = 0 dropped (as in D6).
Runs: κ = 0; S1 and S5, winsorized and unwinsorized; 1,000 markets each; same seeds as Part E.
Prediction: false alarms stay above 50% in all four runs, because the bias comes from the jump c·sign(R), which shifts every observation near R_m = 0 rather than a few outliers.
Decision rule: all four runs ≥ 50% → the loophole is closed. Any run ≤ 10% → RLM avoids the bias there; report it, add RLM as a comparison method, and narrow the claim to the OLS reading for that setting. Between 10% and 50% → report the rates as they are.
Validation first: test_rlm.py must recover known coefficients on clean data and on data with injected outliers.
