#!/bin/bash
set -euo pipefail
if [ "$#" -lt 1 ]; then
  echo "Usage: bash scripts/run-mac.sh USER@HOST [pilot|randomized]" >&2
  exit 2
fi
remote=$1
case "$remote" in -*|*[!a-zA-Z0-9_@.:-]*) echo 'Invalid SSH destination' >&2; exit 2;; esac
case "${2:-randomized}" in
  pilot) script=presence-test.py;;
  randomized) script=presence-control-test.py;;
  *) echo 'Choose pilot or randomized' >&2; exit 2;;
esac
cd "$(dirname "$0")"
scp "$script" "$remote:~/$script"
ssh "$remote" "python3 -u ~/$script" | while IFS= read -r line; do
  case "$line" in
    SAY:*) printf '\a\n%s\n' "${line#SAY:}"; /usr/bin/say "${line#SAY:}" & ;;
    *) printf '%s\n' "$line" ;;
  esac
done
