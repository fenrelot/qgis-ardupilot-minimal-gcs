# Panasonic Toughbook BlueBoat Deployment

This guide installs the QGIS ArduBoat operator map on a Panasonic Toughbook running Windows 11 and connects it to a Blue Robotics BlueBoat. QGIS remains an auxiliary operator map and light command panel. Keep the normal ground-control station open for setup, telemetry, joystick/manual control, failsafe awareness, and recovery.

Sources checked on 2026-06-25:

- BlueBoat Software Setup: https://bluerobotics.com/learn/blueboat-software-setup/
- BlueOS Advanced Usage / MAVLink Endpoints: https://blueos.cloud/docs/latest/usage/advanced/#mavlink-endpoints

## Network Defaults

Blue Robotics' BlueBoat setup guide uses this default topside network:

- Toughbook/control computer: `192.168.2.1`
- BlueOS web UI: `192.168.2.2` or `blueos.local`
- BaseStation router: `192.168.2.3`
- BlueBoat router: `192.168.2.4`
- Subnet mask: `255.255.255.0`

The QGIS bridge default for the BlueBoat deployment is UDP port `14552`. In BlueOS, add or configure a MAVLink UDP client endpoint to:

    udp://192.168.2.1:14552

Use `14552` instead of the common `14550`/`14551` ports so QGroundControl or Mission Planner can keep their normal connection without occupying the bridge port.

## Install On The Toughbook

Working directory: repository root in Windows PowerShell.

If you are preparing the project on another computer, create a clean zip first:

    cd C:\qgisarduboat
    .\scripts\new_deployment_bundle.ps1

Copy `tmp\qgisarduboat_blueboat_deployment.zip` to the Toughbook, extract it to `C:\qgisarduboat`, then continue from the Toughbook.

First check the environment:

    cd C:\qgisarduboat
    .\scripts\bootstrap_windows.ps1 -CheckOnly

Install missing Windows dependencies if needed:

    .\scripts\bootstrap_windows.ps1 -InstallTools -InstallQgis -InstallMissionPlanner -CreateVenv

Install or update only the Python virtual environment:

    .\scripts\bootstrap_windows.ps1 -CreateVenv

Install the QGIS plugin into the current user's QGIS profile:

    .\scripts\install_qgis_plugin.ps1 -CheckOnly
    .\scripts\install_qgis_plugin.ps1

Restart QGIS, open `Plugins > Manage and Install Plugins`, and enable `ArduBoat Control`.

## Windows Firewall

If the bridge starts but never receives BlueBoat telemetry, add an inbound Windows Defender Firewall rule for the bridge UDP port. This requires an elevated Administrator PowerShell:

    cd C:\qgisarduboat
    .\scripts\add_blueboat_firewall_rule.ps1 -CheckOnly
    .\scripts\add_blueboat_firewall_rule.ps1

The rule allows inbound UDP `14552` only from `192.168.2.0/24`.

## BlueBoat / BlueOS Setup

1. Power the BaseStation and BlueBoat.
2. Connect the Toughbook to the BaseStation by USB Ethernet or BaseStation Wi-Fi.
3. If using USB Ethernet, set the Toughbook BaseStation adapter IPv4 address to `192.168.2.1` with subnet mask `255.255.255.0`.
4. Open `http://192.168.2.2` or `http://blueos.local` in a browser.
5. In BlueOS, use MAVLink Endpoints to add a UDP client endpoint to `udp://192.168.2.1:14552`.
6. Keep your normal GCS open. Blue Robotics documents QGroundControl as the recommended BlueBoat GCS; Mission Planner can still be used when it is already part of your operating workflow and has a working BlueBoat connection.

Run the network check:

    cd C:\qgisarduboat
    .\scripts\check_blueboat_network.ps1

Expected useful signs:

- local IP `192.168.2.1` is present on one adapter
- `192.168.2.2` answers ping or HTTP
- the script prints `udp://192.168.2.1:14552` as the MAVLink endpoint target

## Start The QGIS Bridge

Working directory: repository root in Windows PowerShell.

    cd C:\qgisarduboat
    .\scripts\run_blueboat_bridge.ps1

The bridge prints:

    Bridge API: http://127.0.0.1:8765
    MAVLink: udpin:0.0.0.0:14552

Verify status from another PowerShell:

    Invoke-RestMethod http://127.0.0.1:8765/api/status

Expected after the BlueOS endpoint is sending telemetry:

- `connected: true`
- non-empty `mode`
- numeric `lat`, `lon`, and `heading_deg`

## Start QGIS

Open QGIS normally from the Start Menu after installing the plugin into the profile. Open `Plugins > ArduBoat Control > ArduBoat Control` if the dock is not already visible.

Expected QGIS behavior:

- `ArduBoat Live` appears with an arrow marker.
- `ArduBoat Track` appears after telemetry samples arrive.
- The dock shows connected status, mode, position, heading, GPS, and battery data when available.
- The `Track` section can save the track as GeoPackage or Shapefile.
- `Start text log` writes timestamped CSV-style rows to the selected file until stopped.

## Field Safety Sequence

Do not test new command behavior first on water.

1. Bench test with the boat restrained and propulsion safe.
2. Confirm the normal GCS has manual control and telemetry.
3. Start the QGIS bridge and QGIS.
4. Confirm QGIS receives telemetry before enabling any command tests.
5. Test mode buttons with the boat safe.
6. Test `Send target + GUIDED` only in a controlled low-speed area, with the normal GCS and manual recovery ready.

QGIS v1 intentionally does not implement arming, disarming, parameter writes, joystick control, or RC override.
