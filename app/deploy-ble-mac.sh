#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
remote=${1:?Usage: bash deploy-ble-mac.sh YOUR_USER@radiopi.local}
case "$remote" in -*|*[!a-zA-Z0-9_@.:-]*) echo 'Invalid SSH destination' >&2; exit 2;; esac
# Materialize cloud-backed Documents files before asking scp to upload them.
staging_dir=$(mktemp -d /private/tmp/auracam-deploy.XXXXXX)
trap 'rm -rf "$staging_dir"' EXIT
python3 - "$staging_dir" <<'PY_STAGE'
import sys
from pathlib import Path
out=Path(sys.argv[1])
for name in ['index.html','pi_capture.py','session_server.py','session.html','ble_server.py','ble_protocol.py','install-ble-pi.sh']:
    try:
        content=Path(name).read_bytes()
        (out/name).write_bytes(content)
    except OSError as error:
        raise SystemExit(f"Could not read {name}: {error}. In Finder, download the auracam-prototype folder locally, then retry.")
print('Local deployment files ready.')
PY_STAGE
ssh "$remote" 'mkdir -p ~/auracam-render'
scp "$staging_dir/"* "$remote:~/auracam-render/"
ssh -t "$remote" 'cd ~/auracam-render && bash install-ble-pi.sh'
