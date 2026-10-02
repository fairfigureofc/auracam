#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
remote=${1:?Usage: bash start-session-mac.sh YOUR_USER@radiopi.local}
case "$remote" in -*|*[!a-zA-Z0-9_@.:-]*) echo 'Invalid SSH destination' >&2; exit 2;; esac
ssh "$remote" 'mkdir -p ~/auracam-render'
scp index.html pi_capture.py session_server.py session.html "$remote:~/auracam-render/"
printf '\nOpen http://radiopi.local:8080 in your browser. Keep this Terminal open.\n'
ssh "$remote" 'python3 -u ~/auracam-render/session_server.py'
