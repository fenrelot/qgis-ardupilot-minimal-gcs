#!/usr/bin/env bash
#
# Create the non-root Ubuntu user used for ArduPilot SITL work.
#
# Run from Windows with:
#   wsl.exe -d Ubuntu-24.04 -u root -- bash /mnt/c/qgisarduboat/scripts/bootstrap_wsl_user.sh

set -euo pipefail

ARDUPILOT_WSL_USER="${ARDUPILOT_WSL_USER:-ardupilot}"
USER_HOME="/home/$ARDUPILOT_WSL_USER"
ROOT_CHECKOUT="/root/ardupilot"
USER_CHECKOUT="$USER_HOME/ardupilot"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run as root because it creates a WSL user and sudoers entry." >&2
    exit 1
fi

if ! id "$ARDUPILOT_WSL_USER" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$ARDUPILOT_WSL_USER"
fi

usermod -aG sudo "$ARDUPILOT_WSL_USER"
printf "%s ALL=(ALL) NOPASSWD:ALL\n" "$ARDUPILOT_WSL_USER" > "/etc/sudoers.d/90-$ARDUPILOT_WSL_USER-nopasswd"
chmod 440 "/etc/sudoers.d/90-$ARDUPILOT_WSL_USER-nopasswd"

install -d -o "$ARDUPILOT_WSL_USER" -g "$ARDUPILOT_WSL_USER" "$USER_HOME"

if [ -d "$ROOT_CHECKOUT/.git" ] && [ ! -e "$USER_CHECKOUT" ]; then
    mv "$ROOT_CHECKOUT" "$USER_CHECKOUT"
fi

if [ -e "$USER_CHECKOUT" ]; then
    chown -R "$ARDUPILOT_WSL_USER:$ARDUPILOT_WSL_USER" "$USER_CHECKOUT"
fi

if [ ! -f /etc/wsl.conf ]; then
    printf "[user]\ndefault=%s\n" "$ARDUPILOT_WSL_USER" > /etc/wsl.conf
elif ! grep -q "^\[user\]" /etc/wsl.conf; then
    printf "\n[user]\ndefault=%s\n" "$ARDUPILOT_WSL_USER" >> /etc/wsl.conf
elif ! awk '
    /^\[user\]/ { in_user = 1; next }
    /^\[/ { in_user = 0 }
    in_user && /^default[[:space:]]*=/ { found = 1 }
    END { exit(found ? 0 : 1) }
' /etc/wsl.conf; then
    echo "wsl.conf already has a [user] section without a default entry; leaving it unchanged." >&2
fi

echo "WSL user ready: $ARDUPILOT_WSL_USER"
id "$ARDUPILOT_WSL_USER"
ls -ld "$USER_HOME" "$USER_CHECKOUT" 2>/dev/null || true
