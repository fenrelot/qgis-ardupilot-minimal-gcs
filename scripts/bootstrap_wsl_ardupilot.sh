#!/usr/bin/env bash
#
# Bootstrap ArduPilot Rover SITL dependencies inside WSL Ubuntu.
#
# Working directory when called from Windows:
#   repository root as mounted into WSL
#
# The ArduPilot checkout is created at ${ARDUPILOT_DIR:-$HOME/ardupilot}.

set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_REPO="${ARDUPILOT_REPO:-https://github.com/ArduPilot/ardupilot.git}"
export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"
export APT_LISTCHANGES_FRONTEND="${APT_LISTCHANGES_FRONTEND:-none}"

if [ "$(id -u)" -eq 0 ]; then
    SUDO=()
else
    SUDO=(sudo)
fi

run_apt_get() {
    local err_file
    err_file="$(mktemp)"
    set +e
    "${SUDO[@]}" apt-get "$@" 2> >(tee "$err_file" >&2)
    local rc
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        rm -f "$err_file"
        return 0
    fi

    if grep -q "tcsetattr" "$err_file" &&
        ! grep -v "tcsetattr" "$err_file" | grep -q "." &&
        [ -z "$(dpkg --audit)" ]; then
        echo "Ignoring WSL1 apt-get tcsetattr artifact after successful package configuration." >&2
        rm -f "$err_file"
        return 0
    fi

    rm -f "$err_file"
    return "$rc"
}

if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "Warning: this does not look like WSL. Continuing because a normal Ubuntu host can also run SITL."
fi

if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required. Install sudo or run from a standard Ubuntu user account." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get is required. This script targets Ubuntu or another apt-based WSL distro." >&2
    exit 1
fi

echo "Working directory: $(pwd)"
echo "ArduPilot directory: $ARDUPILOT_DIR"

echo "Installing bootstrap packages with apt if needed..."
run_apt_get update
run_apt_get install -y git ca-certificates curl lsb-release python3 python3-pip

if [ -d "$ARDUPILOT_DIR/.git" ]; then
    echo "ArduPilot checkout already exists. Leaving branch and local changes untouched."
elif [ -e "$ARDUPILOT_DIR" ]; then
    echo "$ARDUPILOT_DIR exists but is not a Git checkout. Move it aside or set ARDUPILOT_DIR." >&2
    exit 1
else
    echo "Cloning ArduPilot from $ARDUPILOT_REPO..."
    git clone --recurse-submodules "$ARDUPILOT_REPO" "$ARDUPILOT_DIR"
fi

cd "$ARDUPILOT_DIR"

echo "Initializing/updating ArduPilot submodules..."
git submodule update --init --recursive

echo "Running ArduPilot Ubuntu prerequisite installer..."
if grep -qi microsoft /proc/version 2>/dev/null && [ "${ARDUPILOT_WSL_APT_TTY_WORKAROUND:-1}" = "1" ]; then
    sudo() {
        if [ "${1:-}" = "apt-get" ]; then
            local err_file
            err_file="$(mktemp)"
            set +e
            command sudo "$@" 2> >(tee "$err_file" >&2)
            local rc
            rc=$?
            set -e
            if [ "$rc" -eq 0 ]; then
                rm -f "$err_file"
                return 0
            fi

            if grep -q "tcsetattr" "$err_file" &&
                ! grep -v "tcsetattr" "$err_file" | grep -q "." &&
                [ -z "$(dpkg --audit)" ]; then
                echo "Ignoring WSL1 apt-get tcsetattr artifact after successful package configuration." >&2
                rm -f "$err_file"
                return 0
            fi

            rm -f "$err_file"
            return "$rc"
        fi

        command sudo "$@"
    }
    export -f sudo
fi

Tools/environment_install/install-prereqs-ubuntu.sh -y

cat <<'EOF'

ArduPilot SITL prerequisites are installed.

Close and reopen the WSL shell, or run:
  source ~/.profile

Then start Rover SITL from the repository root with:
  bash scripts/run_sitl_rover_wsl.sh

If WSL2 mirrored networking is enabled and UDP output does not reach Windows,
try:
  WINDOWS_HOST_IP=127.0.0.1 bash scripts/run_sitl_rover_wsl.sh

EOF
