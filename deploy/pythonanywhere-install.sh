#!/usr/bin/env bash
set -euo pipefail
# Download this file from the GoTrip repository and run it in PythonAnywhere.
# The API token stays in the PythonAnywhere account and is not passed to GitHub.
installer="$(mktemp --suffix=.py)"
trap 'rm -f -- "$installer"' EXIT
curl --fail --show-error --location --proto '=https' \
  'https://raw.githubusercontent.com/DJbwji/GoTrip/main/deploy/pythonanywhere.py' \
  --output "$installer"
for candidate in python3.12 python3.11 python3.10 python3.13; do
  if command -v "$candidate" >/dev/null 2>&1; then
    "$candidate" "$installer" "$@"
    exit "$?"
  fi
done
printf '%s\n' 'Python 3.10+ is required.' >&2
exit 1
