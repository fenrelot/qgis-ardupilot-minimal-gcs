#!/usr/bin/env bash
#
# Validate the WSL ArduPilot SITL checkout and Python tooling.
#
# Run from Windows with:
#   wsl.exe -d Ubuntu-22.04 -u ardupilot -- bash /mnt/c/qgisarduboat/scripts/check_wsl_sitl.sh

set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"

if [ -f "$HOME/.profile" ]; then
    # shellcheck disable=SC1091
    source "$HOME/.profile"
fi

cd "$ARDUPILOT_DIR"

echo "ArduPilot directory: $ARDUPILOT_DIR"
echo "ArduPilot commit: $(git rev-parse --short HEAD)"
python3 --version
python3 -c 'import pymavlink; import MAVProxy; print("Python MAVLink tooling: ok")'
mavproxy.py --version
./Tools/autotest/sim_vehicle.py --help | head -n 20
