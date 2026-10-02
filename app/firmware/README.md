# AuraCam ESP32 controller

Archived prototype: the active operator interface is the native iPhone app in `../ios`. This controller remains useful for experimentation but is not required.

Target: E32R28T 2.8-inch resistive display, ILI9341 + XPT2046.
Build/upload with the included VS Code tasks or PlatformIO. Touch calibration is retained in Preferences across uploads.

On first boot, join `AuraCam-Setup` using the random password shown on the screen. Open `http://192.168.4.1`, enter the same 2.4 GHz Wi-Fi network used by the Pi, and set the Pi address to `radiopi.local:8080` (or its LAN IP plus `:8080`). Credentials are stored locally in ESP32 Preferences, not in the source. Rejoin your normal network after saving. Failed Wi-Fi connection returns to setup; the Wi-Fi Setup button also opens it.

Keep the Pi session server running. The controller polls `/api/state` and sends existing `/api/action` commands for survey, frequency lock, baseline measurement/lock, and capture. It joins an already active Pi session without starting another survey. New Session requires a second tap and preserves saved files. Large buttons use press-edge detection so holding a finger does not repeat actions.

Current firmware shows capture progress and the saved image count. Image gallery previews and render settings are not implemented on the display yet. Full PNGs remain available through the Pi web interface. HTTP requests have bounded timeouts, but the touch loop pauses during a network request. Use only on your trusted local network; the Pi API has no authentication.
