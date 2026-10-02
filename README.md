# AuraCam

**A portrait of how you change the invisible world around you.**

AuraCam is an experimental radio-driven photography project. An antenna listens to ambient radio broadcasts. We measure the room empty, then measure it with a person near the antenna. The idea is to turn that difference into a luminous, distorted, generative treatment around a photographic portrait.

Think spectral ribbons, interference halos, and color fields shaped by a real capture—not a random filter.

> “Aura” is the artistic concept. This project does not measure a spiritual aura, personality, health, or emotion. We are testing whether this inexpensive setup can detect repeatable changes associated with a person entering a room.

## What exists today

- Working Raspberry Pi + RTL-SDR V4 capture scripts.
- Spoken enter / hold still / leave cues from a Mac.
- A pilot protocol and a randomized presence-versus-empty control protocol.
- Raw recordings, phase timestamps, receiver logs, and reproducible analysis.

The iPhone camera integration, ESP32 interface, and final portrait renderer are **planned**, not implemented here. An early generative visual explored mapping spectrum power to ribbons; the current focus is validating the sensing.

## The instrument

```text
FM broadcasts → antenna → RTL-SDR V4 → Raspberry Pi 4
                                            │
                          Wi-Fi → iPhone camera + art engine (planned)
                                            │
                          Wi-Fi → ESP32 + LCD controls (planned)
```

The Pi hosts the SDR over USB. The ESP32-WROOM-32E is intended as a display/controller, not the SDR's USB host. No breadboard is required for the current experiment.

## First results: promising, preliminary

On October 1, 2026, we ran a three-entry pilot followed by eight shuffled rounds: four entries and four stay-outside controls. The randomized test kept the band, gain, and analysis rule fixed beforehand.

| Randomized test | Mean change from surrounding empty periods |
|---|---:|
| Person present | +0.152 dB |
| Stay-outside controls | +0.022 dB |
| Difference | **+0.130 dB** |

All four entry effects exceeded all four controls in this recording. The closest pair was only about 0.011 dB apart. Eight rounds are not enough to establish a reliable detector, and environmental drift and sample loss remain concerns. The next planned experiment is an unchanged repeat, not a tuned demonstration.

Read the [experiment log](experiments/2026-10-01/README.md), including every trial, limitations, and raw data.

## Try it

### Hardware and setup

- Raspberry Pi 4 Model B with Raspberry Pi OS Lite / Debian 13, network access, SSH, and Python 3.
- RTL-SDR Blog V4 and an antenna appropriate for the FM band.
- Mac on the same network for spoken cues; keep it outside the measurement room.

On the Pi:

```bash
sudo apt update
sudo apt install -y rtl-sdr
rtl_test -s 2400000
```

Stop the test with Control-C after roughly ten seconds. Confirm that the output recognizes **RTL-SDR Blog V4**. Our Debian 13 installation supplied a compatible driver. For other installations, consult the [V4 driver guide](https://www.rtl-sdr.com/V4/).

On your Mac, clone this repository, enter it, and run the randomized test (replace the SSH destination):

```bash
git clone https://github.com/fairfigureofc/auracam.git
cd auracam
bash scripts/run-mac.sh YOUR_USER@radiopi.local randomized
```

You may be asked for your Pi password twice: once to copy the script, once to run it. No passwords are saved by these scripts.

The **8½-minute** sequence gives you 20 seconds to leave, warms up the receiver, records two empty periods, and runs eight rounds. Each half contains two person rounds and two control rounds, shuffled independently. Each round has a 10-second transition, a 15-second measurement, a 10-second exit transition, and 20 seconds empty.

Keep the antenna and cable fixed. Mark a standing spot. Keep the door position unchanged and your phone outside. Follow the spoken cues. On control rounds, stay outside. A Mac is needed only for speech; the Python scripts can run directly on the Pi with text cues.

For the shorter original test:

```bash
bash scripts/run-mac.sh YOUR_USER@radiopi.local pilot
```

### Retrieve and analyze

At completion, the script prints a `RESULT:` directory on the Pi. Copy that directory to your computer, replacing the example path with the actual one:

```bash
scp -r YOUR_USER@radiopi.local:/home/YOUR_USER/presence-control-test-TIMESTAMP ./my-recording
python3 scripts/analyze-control.py ./my-recording --output ./my-results.json
```

The analyzer currently supports the supplied eight-round randomized protocol, with its fixed 89.15–89.45 MHz analysis band. It uses only the Python standard library. Run the published example without hardware:

```bash
python3 scripts/analyze-control.py experiments/2026-10-01/randomized
```

Recordings contain `spectrum.csv`, `phases.json`, and `receiver.log`. Measurements are uncalibrated relative power; do not interpret them as absolute dBm. Timestamps are the Pi's local clock, without a timezone offset.

## Why controls matter

Broadcast content, multipath, other movement, antenna coupling, receiver drift, and dropped samples can all change a measurement. This is a single-receiver power experiment, not a spatial image or a calibrated passive radar. Strongest station does not necessarily mean best presence sensor.

We analyze a band around the station rather than selecting whichever individual bin looks most convincing afterward. Power is averaged in linear units before conversion back to dB. Each trial is compared with its surrounding empty periods. The eight trials—not hundreds of one-second readings—are the experimental replicates.

The capture band is currently fixed at **88–90.5 MHz**, with **20.7 dB gain** and one-second reporting. These settings came from our local initial scan. They may not be useful at your location. If you change them, document the change and choose the analysis band before collecting a confirmatory test.

## Where this could go

1. Repeat the controlled result and improve capture reliability.
2. Build a capture API on the Pi, with fresh empty-scene calibration.
3. Synchronize an iPhone portrait with several seconds of RF measurements.
4. Map measured differences into an expressive visual treatment.
5. Add the ESP32's 2.8-inch display as the physical shutter and spectrum monitor.

Contributions are welcome: replications, documented null results, receiver diagnostics, and visual experiments. Include hardware, antenna placement, room setup, protocol changes, and raw logs. Please remove credentials and personal paths before sharing recordings.

## References and license

- [RTL-SDR V4 setup](https://www.rtl-sdr.com/V4/)
- [rtl_power command reference](https://manpages.debian.org/trixie/rtl-sdr/rtl_power.1.en.html)
- [Research context: device-free RF sensing](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2024.1344841/full)

See the repository's existing [GPL-3.0 license](LICENSE).
