# Beginners in the Herd

STEM fair research project (Mathematics: Probability & Statistics) by Guru
Balaji and Yuvraj Sharma, Middleton High School, Tampa FL.

**Question:** Did ChatGPT's release (Nov 30, 2022) increase stock-market
herding during periods of heavy new-investor entry?

**What we found so far:**
- The pre-registered hypotheses are not supported. The post-2022 change
  is not specific to ChatGPT's release, as the placebo break dates show,
  and it disappears with year-specific slopes.
- The lead finding is methodological. A published herding test (Wang &
  Hudson's signed-CSAD "Solution 2") reports herding in 100% of simulated
  markets that have none. The cause is the jump its sign flip creates at
  a market return of zero, which we traced and checked against the paper
  itself.

## Where things are
- `notes/`: the shared Obsidian notes. Start at `notes/Home.md` and
  `notes/Handoff.md`.
- `docs/`: the pre-registration trail (addenda, the deviations log D1–D7),
  the Wang-Hudson specification check, and the plain-English mechanisms.
- `*.py`: the pipeline and analyses. `test_*.py` are the validation tests.
- `results/`: simulation outputs and figures.
- `data/`: raw and processed data, not in git (rebuild with the scripts).

The whole repo opens as an Obsidian vault. See `notes/How to sync.md`.

The paper `wang_hudson_2022.pdf` is the authors' CC-BY submitted manuscript
(Hull repository), included for reference.
