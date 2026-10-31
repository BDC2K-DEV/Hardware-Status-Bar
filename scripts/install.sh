#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python 3 is required. Install it with your Linux software manager.' >&2
    exit 1
fi
exec python3 ./install.py "$@"
