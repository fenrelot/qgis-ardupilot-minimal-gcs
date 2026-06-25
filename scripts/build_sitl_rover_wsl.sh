#!/usr/bin/env bash
#
# Build the ArduPilot Rover SITL binary inside WSL without starting MAVProxy.
#
# Run from Windows with:
#   wsl.exe -d Ubuntu-22.04 -u ardupilot -- bash /mnt/c/qgisarduboat/scripts/build_sitl_rover_wsl.sh

set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"

if [ -f "$HOME/.profile" ]; then
    # shellcheck disable=SC1091
    source "$HOME/.profile"
fi

cd "$ARDUPILOT_DIR"
./waf configure --board sitl
./waf rover "$@"
