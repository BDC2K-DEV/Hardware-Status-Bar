#!/bin/sh
# Downloads a fixed release, verifies its checksum, and extracts it. Does not execute downloaded code.
set -eu
version=v0.1.0
base="https://github.com/BDC2K-DEV/Hardware-Status-Bar/releases/download/$version"
archive=hardware-status-bar-linux.zip
for tool in curl sha256sum unzip mktemp; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool" >&2; exit 1; }
done
work=$(mktemp -d "${TMPDIR:-/tmp}/hardware-status-bar.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
curl --fail --location --proto '=https' --tlsv1.2 "$base/$archive" -o "$work/$archive"
curl --fail --location --proto '=https' --tlsv1.2 "$base/SHA256SUMS" -o "$work/SHA256SUMS"
(cd "$work" && sha256sum --check SHA256SUMS --ignore-missing)
destination="$PWD/hardware-status-bar-$version"
[ ! -e "$destination" ] || { echo "Already exists: $destination" >&2; exit 1; }
unzip -q "$work/$archive" -d "$destination"
printf 'Downloaded to: %s\nTo install, run: sh "%s/install.sh"\n' "$destination" "$destination"
