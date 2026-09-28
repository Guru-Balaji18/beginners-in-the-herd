"""
Test build_membership.py's ticker-cleaning logic against hand-built cases
with known correct answers, same philosophy as the other test_*.py files.
"""
import pandas as pd
from build_membership import resolve_alternate_ticker_codes

print("="*70)
print("TEST 1 — alternate (SEDOL-style) ticker codes resolve by name match")
print("="*70)
raw = pd.DataFrame([
    # AFLAC reported under a leaked alt-code in early snapshots, real
    # ticker "AFL" in later ones -> both should end up as "AFL"
    {"ticker": "8686", "name": "AFLAC INC", "weight_pct": 1.0, "snapshot_date": "2013-01-31"},
    {"ticker": "8686", "name": "AFLAC INC", "weight_pct": 1.0, "snapshot_date": "2013-02-28"},
    # NOTE: deliberately dated well past the early_cutoff (2014-04-30) --
    # the cutoff window itself is inclusive/early, so "clean era" evidence
    # has to come from strictly after it, same as real production data
    # (every real clean-ticker case has many years of later snapshots).
    {"ticker": "AFL", "name": "AFLAC INC", "weight_pct": 1.0, "snapshot_date": "2015-01-30"},
    {"ticker": "AFL", "name": "AFLAC INC", "weight_pct": 1.0, "snapshot_date": "2015-02-27"},
    # A pseudo-ticker that's the company's own NAME, not a digit code
    # ("VISA", not "8686"-style) -- confirms the fix isn't digit-specific.
    # Uses the SAME exact name string throughout, unlike the real Visa
    # case: see TEST 2 below for what happens when the name itself also
    # changes between eras (deliberately NOT auto-resolved).
    {"ticker": "VISA", "name": "VISA INC", "weight_pct": 1.0, "snapshot_date": "2013-01-31"},
    {"ticker": "V", "name": "VISA INC", "weight_pct": 1.0, "snapshot_date": "2015-01-30"},
    {"ticker": "V", "name": "VISA INC", "weight_pct": 1.0, "snapshot_date": "2015-02-27"},
    # a name with NO clean-ticker snapshot anywhere -> should stay as-is,
    # reported as unresolved (e.g. acquired before the clean-ticker era)
    {"ticker": "T3W1", "name": "TIME WARNER CABLE-A", "weight_pct": 1.0, "snapshot_date": "2013-01-31"},
    # an already-clean ticker should pass through untouched
    {"ticker": "MSFT", "name": "MICROSOFT CORP", "weight_pct": 1.0, "snapshot_date": "2013-01-31"},
    # a ticker seen AFTER the early cutoff should never be touched even if
    # it looks unusual (guards against over-eager remapping outside the
    # known-buggy window)
    {"ticker": "RXO WI", "name": "RXO INC WHEN ISSUED", "weight_pct": 1.0, "snapshot_date": "2022-11-30"},
])
raw["snapshot_date"] = pd.to_datetime(raw["snapshot_date"])
fixed = resolve_alternate_ticker_codes(raw)

aflac_tickers = set(fixed[fixed.name == "AFLAC INC"]["ticker"])
visa_tickers = set(fixed[fixed.name == "VISA INC"]["ticker"])
twc_tickers = set(fixed[fixed.name == "TIME WARNER CABLE-A"]["ticker"])
msft_tickers = set(fixed[fixed.name == "MICROSOFT CORP"]["ticker"])
wi_tickers = set(fixed[fixed.name == "RXO INC WHEN ISSUED"]["ticker"])

print(f"  AFLAC rows all resolve to ticker(s): {aflac_tickers} (expect {{'AFL'}})")
print(f"  VISA (non-digit alt-code, same name throughout) resolves to: {visa_tickers} (expect {{'V'}})")
print(f"  TWC (unresolvable) stays as: {twc_tickers} (expect {{'T3W1'}})")
print(f"  Clean MSFT ticker untouched: {msft_tickers} (expect {{'MSFT'}})")
print(f"  Post-cutoff 'RXO WI' left untouched: {wi_tickers} (expect {{'RXO WI'}})")

ok = (aflac_tickers == {"AFL"} and visa_tickers == {"V"} and twc_tickers == {"T3W1"}
      and msft_tickers == {"MSFT"} and wi_tickers == {"RXO WI"})
print(f"\nAlternate ticker codes resolved correctly: {'PASS' if ok else 'FAIL'}")

print()
print("="*70)
print("TEST 2 — a name that ALSO changes between eras is NOT auto-merged")
print("="*70)
# Mirrors the real Visa case: early name "VISA INC", later name "VISA INC
# CLASS A" -- different strings, so exact-match deliberately leaves both
# alone rather than risk a fuzzy/normalized match. A normalized-name
# version of this fix was tried and reverted (see resolve_alternate_
# ticker_codes' docstring): it silently merged genuinely distinct dual-
# class securities like GOOGL/GOOG, so this conservative behavior is the
# intended trade-off, not a bug to fix later.
raw2 = pd.DataFrame([
    {"ticker": "VISA", "name": "VISA INC", "weight_pct": 1.0, "snapshot_date": "2013-01-31"},
    {"ticker": "V", "name": "VISA INC CLASS A", "weight_pct": 1.0, "snapshot_date": "2015-01-30"},
    {"ticker": "V", "name": "VISA INC CLASS A", "weight_pct": 1.0, "snapshot_date": "2015-02-27"},
])
raw2["snapshot_date"] = pd.to_datetime(raw2["snapshot_date"])
fixed2 = resolve_alternate_ticker_codes(raw2)
visa_early_ticker = set(fixed2[fixed2.name == "VISA INC"]["ticker"])
print(f"  Early-name 'VISA INC' row stays as: {visa_early_ticker} (expect {{'VISA'}} -- "
      f"left unresolved by design, not silently merged into 'V')")
ok2 = visa_early_ticker == {"VISA"}
print(f"\nName-format changes are correctly left unresolved (not guessed at): {'PASS' if ok2 else 'FAIL'}")
