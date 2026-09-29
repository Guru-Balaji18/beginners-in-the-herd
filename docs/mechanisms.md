# Two strange behaviors of the herding tests, explained (Part G)

Both are shown on simulated markets where we control the truth. The
figures are in `results/`; the numbers are in `results/mech_*.json/csv`.

## 1. Why cleaning the data manufactured "herding" (`results/mech_winsorization.png`)

To stop a few bad prices from distorting results, we "winsorized" the
returns: any daily stock return beyond one shared cutoff was pulled back
to that cutoff. The cutoffs were the 0.1% and 99.9% points of *all*
returns pooled together, about -7.0% and +7.8% in the example market.

On a normal day almost no stock gets near those cutoffs. On a day when
the whole market jumps 9%, every stock jumps about 9% together, so most
of them land past the +7.8% cutoff:
- **74% of stocks** were cut back on that day;
- the day's spread between stocks (CSAD) shrank by **72%**, from 1.41%
  to 0.39%.

The herding test looks for exactly this pattern: stocks bunching
together on big-move days. So it "found" herding, CCK t = -5.09, in a
market built to have none. Without the cleaning step the same market
gives t = +2.31, meaning no herding.

The fix is to winsorize **each day separately**, at that day's own
0.1% and 99.9% points. That trims only the one or two most extreme
stocks relative to that day's market. It shaves the spread by the same
tiny amount (about 0.07%) on every day, big or quiet, and the test is
back to t = +2.31. Across 1,000 such no-herding markets, pooled
winsorization made the test cry "herding" in **100%** of them. Per-day
winsorization did so in **8.6%**, exactly the same as using no
winsorization at all. (That leftover 8.6%, against the 5% it should be,
is not caused by the cleaning step. The likely suspect is the standard
errors (Part H), but we have not tested that for this term.)

In the realistic scenario, where stocks have different betas, the
same pooled clipping still pushes the test toward "herding": the
median t falls from +10.3 to +1.1. There, though, the natural spread
between high- and low-beta stocks on big days hides the effect. So the
cleaning step biased our test toward herding in every scenario; it just
isn't visible in the final yes/no answer in all of them.

## 2. Why the standard test misses the strongest herding (`results/mech_cck_nonmonotonic.png`)

The standard (CCK) test fits a smooth U-shaped or upside-down-U-shaped
curve (a parabola in |R_m|) through the relationship between the spread
of stock returns (CSAD) and the size of the market move. It calls it
"herding" when the curve bends *downward*, i.e. the spread grows less
than it should, or shrinks, on big days.

In our simulation, herding pulls every stock toward the market by a
fraction that grows with the size of the move, so the true spread
falls like 1 / (1 + kappa x R_m^2):
- **Moderate herding (kappa = 100):** the spread only starts to fall
  on big days, forming a gentle dome. The parabola fits it well and
  bends downward, so herding is detected (t = -11.7).
- **Very strong herding (kappa = 3000):** the spread collapses almost
  to zero once the market moves more than about 1%, then stays flat
  near zero. The true curve is a sharp spike at zero with long flat
  tails. It bends *up* beyond about 1.05%, which covers 27% of the
  days.

A parabola cannot draw a spike with flat tails. The best it can do is
a steep V: a large negative slope in |R_m| (t = -144) that carries all
the herding, plus an upward bend (R_m^2 t = +31.6) to flatten the
tails. The test only looks at the bend, so the strongest herding in the
simulation reads as "no herding".

The test's sign convention is not wrong. The shape it assumes just
can't represent an extreme collapse in spread, so its power first
rises with herding strength and then falls.
