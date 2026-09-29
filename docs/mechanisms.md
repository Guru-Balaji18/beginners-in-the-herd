# Why the herding tests misbehave — plain-English explanations for judges

Each mechanism was shown on simulated stock markets where we know the
truth. Each has one explanation paragraph, one figure, and the numbers
behind it. Parts G and E of `docs/addendum2_2026-09-28.md`.

## 1. Cleaning the data manufactured "herding" — `results/mech_winsorization.png`

To limit bad prices, we "winsorized" returns: every daily stock return
beyond one shared cutoff, set from all days pooled together (about -7%
and +7.8%), was pulled back to that cutoff. On a quiet day no stock gets
near those cutoffs. On a day when the whole market jumps 9%, every stock
jumps about 9% with it, so most of them cross the cutoff and are all cut
back to the same value. That squeezes the day's spread between stocks
exactly on the big-move days, which is the pattern the herding test
looks for. The test therefore "found" herding in every one of 1,000
markets built to have none. Winsorizing each day at its own cutoffs
trims only the one or two most extreme stocks that day and removes the
problem completely. SE_SENTENCE

| One no-herding market (S1) | Value |
|---|---|
| Stocks clipped, quiet half of days / biggest 10% of days / the +9% day | 0.005% / 1.9% / **74%** |
| Spread (CSAD) on the +9% day: before, after clipping | 1.41% → **0.39%** (-72%) |
| Herding t-statistic (below -1.645 = "herding"): no clipping, pooled, per-day | +2.31, **-5.09**, +2.31 |
| False-alarm rate in 1,000 no-herding markets: pooled, per-day, none | **100%**, 8.6%, 8.6% |

## 2. The standard test misses the strongest herding — `results/mech_cck_nonmonotonic.png`

The standard (CCK) test fits a parabola through "spread between stocks"
against "size of the market move". It calls it herding when that
parabola bends downward, meaning spread falls behind on big days.
Moderate herding gives a gentle dome, which a parabola fits well, so it
is detected. Very strong herding makes the spread collapse to almost
zero once the market moves more than about 1%, and then stay flat. That
spike with flat tails is a shape a parabola cannot draw. The closest it
can get is a steep V with an upward bend at the ends. All the herding
ends up in the V's slope, which the test ignores, and the bend it does
read points the "no herding" way. So the test's power first rises with
herding strength, then falls.

| Same market, herding strength kappa | 0 | 100 | 3000 |
|---|---|---|---|
| Parabola's bend, t (below -1.645 = "herding") | +2.3 | **-11.7** | **+31.6** |
| V-slope term, t | -1.7 | -8.4 | **-144** |
| Days where the true curve bends upward | — | 0.3% | 27% |

## 3. Our Wang-Hudson test always says "herding" (from Part E) — `results/wh_e4_diagnosis.png`

Our version of the Wang-Hudson test flips the sign of the spread on
down-market days: +spread on up days, -spread on down days. Spread is
always positive, so this creates a cliff at a market return of exactly
zero: the value jumps from about -1.4% to +1.4%. The test then fits a
smooth S-shaped cubic curve through the data, and a smooth curve
crossing a cliff has to overshoot and bend back. That bend-back is
exactly the negative cubic term the test reads as herding. A made-up
dataset containing nothing but the cliff produces the same "herding"
coefficient, and giving the regression one extra term that allows a
jump at zero makes the false herding disappear. This is a property of
**our implementation**. Whether the published Wang & Hudson method
handles the jump differently can only be checked against the paper,
which we could not access.

| One no-herding market (S1, no winsorization) | Value |
|---|---|
| Jump in signed spread at R_m = 0 | 2.81 points = **2.00 x** average spread |
| Our WH cubic coefficient, t | -202.6, **t = -5.46** ("herding") |
| Same regression fitted to the cliff alone (no data) | -203.3 (100% of the above) |
| With a jump term added: cubic coefficient, t | +0.8, t = +2.49 (no herding) |
