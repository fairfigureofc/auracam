#!/bin/bash
set -euo pipefail
remote=${1:?Usage: bash run-pi-mac.sh YOUR_USER@radiopi.local}
case "$remote" in -*|*[!a-zA-Z0-9_@.:-]*) echo 'Invalid SSH destination' >&2; exit 2;; esac
cd "$(dirname "$0")"
ssh "$remote" 'mkdir -p ~/auracam-render'
scp index.html pi_capture.py "$remote:~/auracam-render/"
ssh "$remote" 'python3 -u ~/auracam-render/pi_capture.py' | while IFS= read -r line; do
 case "$line" in
 SAY:*) printf '\a%s\n' "${line#SAY:}"; /usr/bin/say "${line#SAY:}" & ;;
 *) printf '%s\n' "$line";;
 esac
done
