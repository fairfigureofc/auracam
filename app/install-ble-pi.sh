#!/bin/bash
# Run as your normal Pi user, from ~/auracam-render.
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$EUID" = 0 ]]; then echo 'Run this as your normal Pi user, not sudo.' >&2; exit 1; fi
capture_user=$(id -un)
capture_dir=$(pwd)
case "$capture_dir" in *' '*|*'%'*|*'"'*) echo 'Install in a simple path such as ~/auracam-render.' >&2; exit 1;; esac
sudo apt-get update
sudo apt-get install -y bluez python3-dbus python3-gi rtl-sdr chromium chromium-driver python3-selenium optipng
sudo rfkill unblock bluetooth
sudo systemctl enable --now bluetooth
# An update restarts only AuraCam's managed services; saved captures stay intact.
if systemctl is-active --quiet auracam-session.service; then
  sudo systemctl stop auracam-ble.service auracam-session.service
fi
# Ensure the foreground session server is stopped before starting the managed service.
if ss -ltn | awk '{print $4}' | grep -q ':8080$'; then
  echo 'Port 8080 is in use. Stop the old foreground server with Ctrl-C, then rerun this installer.'
  exit 1
fi
session_unit=$(mktemp)
bridge_unit=$(mktemp)
trap 'rm -f "$session_unit" "$bridge_unit"' EXIT
cat > "$session_unit" <<UNIT
[Unit]
Description=AuraCam RF session and renderer
After=bluetooth.service
[Service]
User=$capture_user
WorkingDirectory=$capture_dir
ExecStart=/usr/bin/python3 -u $capture_dir/session_server.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
cat > "$bridge_unit" <<UNIT
[Unit]
Description=AuraCam BLE controller bridge
Requires=bluetooth.service auracam-session.service
After=bluetooth.service auracam-session.service
[Service]
WorkingDirectory=$capture_dir
ExecStart=/usr/bin/python3 -u $capture_dir/ble_server.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
sudo install -m 644 "$session_unit" /etc/systemd/system/auracam-session.service
sudo install -m 644 "$bridge_unit" /etc/systemd/system/auracam-ble.service
sudo systemctl daemon-reload
sudo systemctl enable --now auracam-session auracam-ble
sudo systemctl --no-pager --full status auracam-session auracam-ble
