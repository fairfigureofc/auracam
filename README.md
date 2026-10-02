# AuraCam

**A portrait of how you change the invisible world around you.**

AuraCam is an experimental camera-free, radio-driven art project. An antenna listens to ambient radio broadcasts. We measure the room empty, then measure it with a person near the antenna. The idea is to turn that difference into layered, generative waveforms—without taking a photograph.

Like pectral ribbons, interference halos, and color fields shaped by captures and what evvvvverrrr.

I'm also just a bit bored and a bit curious. If you are too, feel free to contribute. 



## What exists today

- Native iPhone app with BLE controls, silent 3–2–1 capture, names, a capture library, and local image storage.
- Raspberry Pi session engine: FM survey, frequency lock, empty baseline, repeat captures, and six paired PNGs per person.
- Pi-side rendering using the shared Canvas art engine, with optional lossless OptiPNG optimization.
- AirDrop/Messages through the iOS share sheet and Save to Photos. The operator chooses the recipient and sends.
- Historical controlled RF experiments with raw data and reproducible analysis.
- An archived ESP32 touchscreen controller prototype; it is not required for the iPhone workflow.

This is a working prototype, not a proven presence detector or a measurement of an aura. Geometry and color are artistic mappings of RF changes. The three baseline images are deliberately minimal; the three presence images use different artistic amplitude presets.

## Run the iPhone + Pi instrument

Use a Raspberry Pi 4, RTL-SDR Blog V4, antenna, a suitable power supply, and an iPhone with iOS 17 or later. Xcode on a Mac is required to build/install the app; choose your own development signing team.

```bash
git clone https://github.com/fairfigureofc/auracam.git
cd auracam
bash app/deploy-ble-mac.sh YOUR_USER@radiopi.local
open app/ios/AuraCam.xcodeproj
```

Initial installation uses SSH/network access to install dependencies. The Pi services then start on boot; capture and image transfer use BLE without a shared Wi-Fi network. AirDrop separately requires Wi-Fi and Bluetooth enabled on the phones. Image messages use an image-capable Messages transport, not plain SMS.

On iPhone: connect → survey → select frequency → measure/lock baseline → capture → name → Library → download/share. The Library lists completed six-image captures across saved sessions, newest first. Deleting a capture on the Pi requires confirmation and leaves downloaded iPhone copies intact.

Read the [iPhone/BLE setup and limitations](app/ios/README.md), [Pi workflow](app/PI-SETUP.md), and [ESP32 prototype notes](app/firmware/README.md). Updates restart the active Pi session; start a new baseline afterward. Saved captures remain on disk.

## Open the waveform app

Open [`app/index.html`](app/index.html) in your browser after cloning. No installation, server, or external dependencies are required. On macOS:

```bash
open app/index.html
```

Choose a recorded round, line treatment, background, and color amount. Export PNG at 1080×1920 (story), 1080×1350 (portrait post), or 1080×1080 (square). The footer includes capture/analysis bands and the selected round's start as Unix seconds. The source clock timezone was not recorded: the UI explicitly assumes Cancún (UTC−05) and also offers UTC. Confirm that setting before treating the exported timestamp as authoritative.

The app uses eight embedded recordings from the [October 2 dresser experiment](experiments/2026-10-02/README.md). Depth, color, and geometry are artistic mappings, not measured spatial structure. Preview work is bounded, redraws are coalesced, and rendering uses no blur or animation loop.

## The instrument

```text
FM broadcasts → antenna → RTL-SDR V4 → Raspberry Pi 4
                                      │ measurements + PNG rendering
                                      └─ BLE → iPhone controls + library
                                                └─ Photos / AirDrop / Messages
```

The Pi hosts the SDR over USB. The ESP32 is optional archived controller work, not the SDR host. No breadboard is required.

## First results: promising, preliminary

On October 1, 2026, we ran a three-entry pilot followed by eight shuffled rounds: four entries and four stay-outside controls. The randomized test kept the band, gain, and analysis rule fixed beforehand.

| Randomized test | Mean change from surrounding empty periods |
|---|---:|
| Person present | +0.152 dB |
| Stay-outside controls | +0.022 dB |
| Difference | **+0.130 dB** |

All four entry effects exceeded all four controls in this recording. The closest pair was only about 0.011 dB apart. Eight rounds are not enough to establish a reliable detector, and environmental drift and sample loss remain concerns. An October 2 run at a new dresser placement produced a larger separation; see the follow-up below.

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

The historical controlled experiment uses a band fixed at **88–90.5 MHz**, with **20.7 dB gain** and one-second reporting. These settings came from our local initial scan. They may not be useful at your location. If you change them, document the change and choose the analysis band before collecting a confirmatory test.

## Where this could go

1. Repeat controlled experiments and improve capture reliability.
2. Add transfer throughput measurements, thumbnails, and resumable/background downloads.
3. Add wireless printing and a portable enclosure/power system.
4. Harden BLE ownership and add session recovery after reboot.

## Development checks

```bash
python3 -m unittest discover -s tests
python3 -m unittest discover -s app -p 'test_*.py'
xcodebuild -project app/ios/AuraCam.xcodeproj -scheme AuraCam \
  -sdk iphonesimulator -derivedDataPath /tmp/auracam-build CODE_SIGNING_ALLOWED=NO build
```

Tests exercise protocol transport, capture-library isolation/deletion, and the historical randomized experiment without radio hardware. Real RF measurements, Bluetooth pairing/throughput, Photos permissions, and guest sharing still require device testing. The Pi HTTP interface is unauthenticated and intended only for a trusted LAN; do not expose it publicly. BLE uses encrypted characteristics and Just Works pairing; exclusive control is not an authenticated owner system.

Contributions are welcome: replications, documented null results, receiver diagnostics, and visual experiments. Include hardware, antenna placement, room setup, protocol changes, and raw logs. Please remove credentials and personal paths before sharing recordings.

## References and license

- [RTL-SDR V4 setup](https://www.rtl-sdr.com/V4/)
- [rtl_power command reference](https://manpages.debian.org/trixie/rtl-sdr/rtl_power.1.en.html)
- [Research context: device-free RF sensing](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2024.1344841/full)

See the repository's existing [GPL-3.0 license](LICENSE).
