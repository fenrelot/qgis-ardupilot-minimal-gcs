#!/usr/bin/env bash
#
# Start ArduPilot Rover SITL in WSL and send MAVLink UDP output to Windows.
#
# Working directory when called from Windows:
#   repository root as mounted into WSL
#
# Environment variables:
#   ARDUPILOT_DIR   default: ~/ardupilot
#   WINDOWS_HOST_IP auto-detected from the WSL default route
#   MP_PORT         default: 14550 for Mission Planner
#   BRIDGE_PORT     default: 14551 for the Python bridge
#   LOCATION        optional ArduPilot location name
#   SHOW_MAVPROXY_UI set to 1 to request MAVProxy --map and --console

set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
MP_PORT="${MP_PORT:-14550}"
BRIDGE_PORT="${BRIDGE_PORT:-14551}"
WINDOWS_HOST_IP="${WINDOWS_HOST_IP:-}"

if [ -f "$HOME/.profile" ]; then
    # shellcheck disable=SC1091
    source "$HOME/.profile"
fi

if [ -z "$WINDOWS_HOST_IP" ]; then
    kernel_release="$(uname -r)"
    if printf "%s" "$kernel_release" | grep -qi "microsoft" &&
        ! printf "%s" "$kernel_release" | grep -qi "WSL2"; then
        WINDOWS_HOST_IP="127.0.0.1"
    else
        WINDOWS_HOST_IP="$(ip route show default 2>/dev/null | awk '/default/ {print $3; exit}')"
    fi
fi

if [ -z "$WINDOWS_HOST_IP" ]; then
    echo "Could not detect the Windows host IP from WSL routing." >&2
    echo "Retry with WINDOWS_HOST_IP=127.0.0.1 if WSL mirrored networking is enabled." >&2
    exit 1
fi

if [ ! -d "$ARDUPILOT_DIR" ]; then
    echo "ArduPilot directory not found: $ARDUPILOT_DIR" >&2
    echo "Run: bash scripts/bootstrap_wsl_ardupilot.sh" >&2
    exit 1
fi

if [ ! -x "$ARDUPILOT_DIR/Tools/autotest/sim_vehicle.py" ]; then
    echo "sim_vehicle.py was not found or is not executable under $ARDUPILOT_DIR." >&2
    echo "Run: cd '$ARDUPILOT_DIR' && git submodule update --init --recursive" >&2
    exit 1
fi

location_args=()
if [ -n "${LOCATION:-}" ]; then
    location_args=(--location "$LOCATION")
fi

ui_args=()
if [ "${SHOW_MAVPROXY_UI:-0}" = "1" ]; then
    ui_args=(--map --console)
fi

echo "Working directory: $ARDUPILOT_DIR"
echo "Windows host IP: $WINDOWS_HOST_IP"
echo "Mission Planner UDP output: udp:$WINDOWS_HOST_IP:$MP_PORT"
echo "Bridge UDP output: udp:$WINDOWS_HOST_IP:$BRIDGE_PORT"
echo ""
echo "Mission Planner should connect to UDP port $MP_PORT."
echo "The future bridge default will listen on udpin:0.0.0.0:$BRIDGE_PORT."
echo "If UDP traffic does not reach Windows, retry with WINDOWS_HOST_IP=127.0.0.1 or append ArduPilot networking options such as --no-wsl2-network."
echo ""

cd "$ARDUPILOT_DIR"

./Tools/autotest/sim_vehicle.py \
    -v Rover \
    "${location_args[@]}" \
    "${ui_args[@]}" \
    --out="udp:$WINDOWS_HOST_IP:$MP_PORT" \
    --out="udp:$WINDOWS_HOST_IP:$BRIDGE_PORT" \
    "$@"
