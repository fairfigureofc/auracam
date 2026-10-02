# October 2, 2026 · Dresser placement

The participant moved the antenna from the previous setup to a wooden dresser for greater physical stability. This is a new-placement experiment, not an unchanged replication. Placement and day changed together.

Same eight-round balanced randomized protocol, fixed 20.7 dB gain, 88–90.5 MHz capture band, 89.15–89.45 MHz analysis band, and two-second phase-boundary trimming. Differences below compare each round with the average of its preceding and following empty periods.

| Round | Condition | Change (dB) |
|---|---|---:|
| 1 | Person | −0.4865 |
| 2 | Control | +0.0111 |
| 3 | Person | −0.7970 |
| 4 | Control | −0.0442 |
| 5 | Person | −0.6955 |
| 6 | Person | −0.7926 |
| 7 | Control | −0.0558 |
| 8 | Control | −0.0081 |

Person mean: −0.6929 dB. Control mean: −0.0243 dB. Difference: **−0.6686 dB**. All four entries had a larger reduction than any control. There were 490 consecutive one-second readings, no timestamp gaps, and no dropped-sample warnings in the receiver log.

The effect reversed direction relative to October 1 and grew in magnitude. This supports further exploration at this placement, not a universal threshold or identification of a biological aura. Four entries remain a small sample. The block-constrained two-sided randomization comparison is 2/36 ≈ 0.056, subject to the same no-carryover limitation as the earlier experiment.

Further testing was deferred to build the artistic prototype. The renderer is camera-free: RF differences inform abstract line geometry, not measured anatomy or a literal 3D field reconstruction.

## Files and reproduction

[dresser/spectrum.csv](dresser/spectrum.csv), [dresser/phases.json](dresser/phases.json), [dresser/receiver.log](dresser/receiver.log).

```bash
python3 scripts/analyze-control.py experiments/2026-10-02/dresser
```

The recording contains local timestamps without an offset. The browser's Unix footer assumes America/Cancun (UTC−05) unless changed to UTC; this is an explicit assumption, not verified Pi timezone metadata.
