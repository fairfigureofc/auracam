# Experiment log · October 1, 2026

## Question

Does standing near a fixed antenna produce a repeatable FM power change larger than changes observed when the room remains empty?

Hardware: Raspberry Pi 4 Model B, RTL-SDR Blog V4, antenna. Software: Debian 13 (trixie), rtl-sdr tools, Python 3; macOS speech cues over SSH. The participant reported hearing the cues and reaching the marked spot on time in the pilot. Antenna model, exact distance, room geometry, and door-state compliance were not recorded. This limits replication and causal interpretation.

No audio, photographs, or phone identifiers were recorded. These files contain power spectra and timing metadata.

## Pilot

Three entries with empty-room measurements before and after each. Capture: 88–90.5 MHz, fixed 20.7 dB gain, one-second output. Analysis: 89.15–89.45 MHz; discard transitions and trim two seconds from each phase boundary. Average bin power in linear units before converting to dB; average those readings within each phase.

| Entry | Difference from preceding empty | Difference from following empty |
|---|---:|---:|
| 1 | +0.120 dB | +0.171 dB |
| 2 | +0.071 dB | +0.070 dB |
| 3 | +0.039 dB | +0.131 dB |

214 consecutive one-second rows; two untimestamped dropped-sample warnings. Small increases appeared in every entry, but baseline variability and drift warranted randomized controls.

Raw files: [spectrum](pilot/spectrum.csv), [phase timings](pilot/phases.json), [receiver log](pilot/receiver.log).

## Randomized follow-up

Two blocks of four trials, each containing two entries and two stay-outside controls in random order. Same frequency settings. The analysis band and method were saved before measurement. Each trial effect equals its measurement mean minus the average of its preceding and following empty means.

| Trial | Condition | Effect |
|---|---|---:|
| 1 | Person | +0.1112 dB |
| 2 | Control | +0.0999 dB |
| 3 | Control | +0.0486 dB |
| 4 | Person | +0.1156 dB |
| 5 | Person | +0.1730 dB |
| 6 | Control | +0.0108 dB |
| 7 | Person | +0.2084 dB |
| 8 | Control | −0.0697 dB |

Person mean: **+0.1521 dB**. Control mean: **+0.0224 dB**. Difference: **+0.1297 dB**.

All entry effects exceeded all control effects, but the closest separation was only 0.0113 dB. A two-sided randomization comparison over the 36 assignments allowed by the two balanced blocks gives **p = 2/36 ≈ 0.056**. This is descriptive preliminary evidence, not a validated detection threshold. Adjacent effects share empty baselines, and carryover remains possible; interpretation of the randomization comparison assumes no treatment carryover under the null.

490 consecutive one-second rows; six dropped-sample warnings without timestamps. No output timestamp gaps does not mean no underlying samples were lost. Each trimmed measurement contains 11 rows; each trimmed empty phase contains 16.

Raw files: [spectrum](randomized/spectrum.csv), [phase timings](randomized/phases.json), [receiver log](randomized/receiver.log).

## What we can and cannot say

This session is consistent with a small change associated with entering the room. It does not isolate body absorption from movement, reflections, door changes, nearby electronics, or antenna coupling. It does not establish person identity, biological emissions, or an aura. We have not measured out-of-sample classification performance.

Next planned step: repeat the same randomized protocol without tuning to these results. Later experiments can vary distance, antenna geometry, or station, with those exploratory changes documented separately.

## Reproduce the randomized analysis

From the repository root:

```bash
python3 scripts/analyze-control.py experiments/2026-10-01/randomized --output results.json
```

The analyzer drops the duplicated trailing CSV value beyond the declared upper frequency boundary, retains timestamps safely inside each phase, and uses trials as replicates. Reported frequencies use rtl_power's bin-start convention.
