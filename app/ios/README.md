# AuraCam for iPhone

Native SwiftUI operator app (iOS 17+), with a Core Bluetooth connection to a Raspberry Pi 4. No shared Wi-Fi or internet is required for capture or Pi-to-phone transfers after setup. The Pi runs the existing RTL-SDR session engine and Chromium renderer. The ESP32 is not needed.

## Build / install

Open `AuraCam.xcodeproj` in Xcode, select your development team under Signing & Capabilities, choose your connected iPhone, and Run. Allow Bluetooth when prompted. The simulator can preview the interface but does not test this Pi Bluetooth link. `project.yml` can regenerate the project with XcodeGen. The repository does not embed a personal signing team.

## Install on the Pi once

Run the Mac commands below from the cloned repository root.

Stop the previous foreground session server with Ctrl-C in its Terminal first; this ends the current session but leaves PNG files intact. From a **Mac** Terminal:

```bash
bash app/deploy-ble-mac.sh YOUR_USER@radiopi.local
```

The script copies the server and BLE bridge, installs Debian packages, and enables `auracam-session` and `auracam-ble` as services. SSH/Wi-Fi and internet are needed for this initial installation, not for operating at a party. The renderer runs as the normal Pi user; the small BlueZ bridge runs as root for D-Bus access. Both start at boot. Do not run the old foreground server alongside the service.

To update an existing service installation, stop the services before running the installer:

```bash
sudo systemctl stop auracam-ble auracam-session
```

Diagnostics on the **Pi**:

```bash
sudo journalctl -u auracam-session -u auracam-ble -n 80 --no-pager
```

## Party workflow

1. Power the Pi and SDR from a suitable supply; keep the antenna fixed.
2. Open AuraCam and connect to the advertised instrument. Approve Bluetooth pairing if iOS asks.
3. Start a session, select a frequency, clear the capture area, measure the empty baseline, then lock it.
4. Capture a guest; a silent on-screen 3–2–1 precedes the recording.
5. Optionally name the capture; leaving it blank keeps its generated name. Under **On Pi**, download desired originals. Keep the app open; progress reports each transfer. Full PNGs over BLE can take a while; speed has not been measured on this hardware.
6. Under **Saved**, open an image and share via the iOS share sheet or save to Photos. Downloads survive app restarts. Removing the app removes its private collection unless exported to Photos/Files.

Sharing opens a composer/recipient picker, never sends automatically. Image messages use the available image-capable Messages transport (e.g. iMessage/MMS/RCS), not a plain SMS text. AirDrop still requires Wi-Fi and Bluetooth enabled on the phones; it does not use the Pi BLE link. Guests do not need AuraCam to receive an image.

Render settings include black/white background, RF chromatic color, square/portrait/story export, and advanced presence amplitude. Empty amplitude stays at 0.20. Changes apply to the next baseline or guest; a guest's empty partner is re-rendered with the same settings. Captures retain frequency and Unix-time footers. These are artistic transformations of measured RF differences, not images of a measured human energy field.

## BLE protocol

Service UUID `9d7a0001-64d8-4ef1-9b9e-7127ba10ca00`. Command characteristic ends `0002`, response ends `0003`.

Commands are UTF-8 JSON followed by newline, fragmented into acknowledged writes at the negotiated maximum size. Only one operation is outstanding. `state`, `action`, and `image` prepare an immutable response and return `{length, sha256}` (or `{error}`). `read` with an absolute offset retrieves up to 480 bytes. Repeating an offset is idempotent. Original downloads are SHA-256 verified and written atomically. Failed downloads can be restarted by tapping Download again; partial downloads are not persisted. UI polling pauses during transfer. No Base64 inflation, public file endpoint, or whole-image GATT value is needed.

The BlueZ bridge uses encrypted characteristics and a Just Works pairing agent (no display/passkey authentication), with one active controller owner at a time. This prototype is not access-controlled against nearby strangers pairing when no owner is connected. The existing HTTP UI remains a trusted-LAN interface without authentication. Harden ownership/pairing before unattended public use.

## Verification and current limits

- iOS simulator build and visual inspection passed.
- Signed device build passed and installed on the paired iPhone 14.
- Protocol tests cover a 1 MiB binary transfer, offset retries, checksum, rejected paths, command allowlist, and settings validation.
- Existing mocked session tests cover baseline lock/rescan, six-image pairing, baseline reuse, and unique guest records.
- Operator testing confirmed iPhone/Pi connection, capture, and image transfer. Transfer throughput and all sharing paths have not been comprehensively benchmarked.
- No automatic background BLE transfers, thumbnail streaming, phone-triggered wireless printing, or session recovery across Pi restarts yet.
- The Library exposes historical completed six-image captures. Image previews appear after downloading an original.

References: [Apple Core Bluetooth](https://developer.apple.com/documentation/corebluetooth), [BlueZ GATT API](https://bluez.readthedocs.io/en/latest/gatt-api/), [Apple AirDrop](https://support.apple.com/en-ie/119857).

PNG outputs now use optional OptiPNG lossless optimization (`-o2`, 20-second limit per image). Originals survive optimizer errors/timeouts, and larger results are discarded. The Pi installer installs OptiPNG. Actual size savings and transfer improvements have not yet been benchmarked on the Pi.

### Bond-repair diagnosis

A service-update incident left the phone/Pi bond unusable: iOS reported invalid handles then insufficient encryption. The Pi still reported Paired/Bonded, but debug logs showed `user_confirm_request_callback(confirm_hint=1)` immediately followed by `btd_adapter_confirm_reply(success=0)`, with no agent callback. In BlueZ 5.82, `JustWorksRepairing=never` rejects an existing peer's repair before consulting the agent. Temporarily selecting `confirm` allowed AuraCam's existing pairing agent to authorize repair and the phone connected. The original configuration was restored immediately afterward. Do not disable encrypted GATT permissions or leave `always` enabled as a workaround. The original cause of the bond mismatch has not been established.

The iPhone client now handles service invalidation and pauses requests on authentication/encryption errors, rather than repeatedly issuing rejected commands. Verify a successful status exchange before considering Bluetooth connected. Temporary debug SSH access must be removed after diagnosis.

Follow-up verification: after restoring `JustWorksRepairing=never` and restarting Bluetooth, the reconnected iPhone link reported `AUTH ENCRYPT` in the controller connection state. The RF session service remained active. This confirms encrypted reconnection without retaining the temporary repair-policy change.

## Capture library

The iPhone Library tab requests the Pi's completed captures across all saved sessions, ordered newest first, showing saved names, capture timestamps, and IDs. Each detail page groups three empty partners with three presence images. Downloaded images can be previewed and shared; previews require downloading an original. Refresh retrieves changes made on other clients. The Saved tab is the independent offline iPhone collection.

Deleting requires an explicit capture-specific confirmation. The server accepts only an exact catalog ID and removes that capture's six PNGs and measurement JSON. Baseline source folders and other captures are preserved; deleting the current gallery restores the locked baseline. iPhone downloads are not deleted. Deletion is rejected during a hardware/render job. No captures are deleted by the installer or by opening the library.

The BLE protocol now supports `library` and the `delete` action. Image authorization includes historical catalog entries. Update the Pi with `deploy-ble-mac.sh` for these endpoints; this restarts the live session services but preserves saved captures and does not alter Bluetooth security configuration. Legacy captures with fewer than six image files are excluded from this paired-capture library.
