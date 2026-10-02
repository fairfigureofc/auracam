# Pi capture renderer

Install on Debian 13 as a regular user:

    sudo apt update
    sudo apt install -y rtl-sdr chromium chromium-driver python3-selenium

Keep index.html and pi_capture.py together. Run:

    python3 pi_capture.py

The sequence is 20 seconds to leave, 10 seconds receiver warmup, 12 seconds empty baseline, 10 seconds to enter, and 8 seconds RF capture. Text countdowns and terminal bells are used; this script does not speak. The receiver remains open with fixed gain throughout. Baseline boundaries are trimmed by two seconds. At least three readings per phase are required.

PNG files, capture.json, spectrum.csv, windows.json, and receiver.log are saved under ~/auracam-captures in a unique UTC-named directory. PNG defaults: black background, monochrome, 1080×1350. Rendering uses the exact shared JavaScript Canvas implementation. Font/rasterization can vary slightly between operating systems; bit-identical pixels are not guaranteed.

Person gains: ribbons 1.10, terrain 1.40, twist 1.00. Empty control gain: 0.20. These are artistic presets based on the capture protocol label, not an automatic presence classifier. RF measurements still shape the curves. Browser Advanced can override gain until the capture or style changes.

To rerender saved data without acquiring another baseline:

    python3 pi_capture.py --render-only ~/auracam-captures/RECORDING/capture.json

This shorter capture compares with the preceding empty baseline only; it is not the earlier randomized experiment with before/after controls. It cannot obtain an empty baseline with a person already in position. The iPhone BLE controller uses session_server.py; ESP32 firmware is an optional earlier prototype.

Pi hardware capture and Chromium rendering have been exercised in operator tests. The script does not disable Chromium's sandbox. Run as a normal user, not with sudo.

## Session controller (new)

From your Mac, run `bash start-session-mac.sh YOUR_USER@radiopi.local` in this directory. It copies the app and keeps a Pi SSH server process running. Open `http://radiopi.local:8080` on your Mac or phone on the same trusted local network. If mDNS is unavailable, substitute the Pi's LAN IP address. Existing Chromium/selenium/rtl-sdr dependencies are reused. This is a local prototype without authentication; do not forward the port to the internet.

1. Start session: 20-second survey of 88–108 MHz at fixed 20.7 dB gain. Candidate 300 kHz bands are ranked by mean power minus three times temporal standard deviation, separated by at least 600 kHz. This heuristic is not a station decoder or presence-sensitivity test.
2. Select and lock a candidate. The receiver stays running at that tuning and gain.
3. Measure baseline: three seconds to clear the area, followed by eight seconds of sampling. Review variation and previews; choose Lock or Rescan. No arbitrary quality threshold is claimed.
4. Capture: three seconds to reach the marked spot, eight seconds of measurement, then Pi rendering. Baseline measurements are reused and PNGs are re-rendered with matching settings in unique guest folders. The gallery links download originals.
5. Repeat Capture for the next guest. Recalibrate if antenna or surroundings change.

Browser speech starts after a button interaction and depends on the browser/device; keep the page foreground with sound enabled. Text cues always remain visible. No speech is played by the Pi itself.

Files persist under ~/auracam-sessions. Restarting the server requires a new session and baseline; old files remain on disk but session restoration is not yet implemented. Stop with Control-C. Only one hardware job runs at a time. Measurement windows require at least three consistent readings. RF logs are retained, but there is no automatic clipping/dropout quality classifier. Keep other rtl-sdr programs closed.

Validated locally with mocked hardware: baseline review/lock, paired gallery, reuse across guests, distinct output folders, rescan invalidation, and dynamic footer metadata. Operator tests exercised survey, baseline, capture, and rendering on the Pi; latency has not been systematically benchmarked.

For the native iPhone app, Bluetooth services, naming, compression, and historical library, follow [the iPhone setup guide](ios/README.md). Its countdown is silent and on-screen. Installers now include OptiPNG.
