# Operator Quickstart

This is the short startup checklist for the QGIS ArduBoat operator map. The detailed Toughbook and BlueBoat setup is in `docs/toughbook_blueboat_deployment.md`; the real-hardware validation checklist is in `docs/real_boat_workflow.md`.

## Development / SITL

Working directory: repository root in Windows PowerShell.

    cd C:\qgisarduboat
    .\scripts\bootstrap_windows.ps1 -CheckOnly
    .\.venv\Scripts\python.exe -m pytest

Start Rover SITL from elevated PowerShell if normal `wsl.exe` returns `Access is denied`:

    wsl.exe -d Ubuntu-22.04 -- bash -lc 'cd /mnt/c/qgisarduboat && BRIDGE_PORT=14552 bash scripts/run_sitl_rover_wsl.sh'

Start the bridge:

    .\scripts\run_bridge.ps1 -Connect udpin:0.0.0.0:14552

Start QGIS with the development plugin path:

    .\scripts\run_qgis_plugin_dev.ps1

## Toughbook / BlueBoat

Blue Robotics default network values:

- Toughbook/control computer: `192.168.2.1`
- BlueOS: `192.168.2.2` or `blueos.local`
- BaseStation router: `192.168.2.3`
- BlueBoat router: `192.168.2.4`

In BlueOS, add a MAVLink UDP client endpoint to:

    udp://192.168.2.1:14552

Install/update the QGIS plugin into the user profile:

    cd C:\qgisarduboat
    .\scripts\install_qgis_plugin.ps1

Check BlueBoat network reachability:

    .\scripts\check_blueboat_network.ps1

Start the bridge:

    .\scripts\run_blueboat_bridge.ps1

Open QGIS normally from the Start Menu and enable `ArduBoat Control` from the QGIS Plugin Manager.

## Acceptance

Before command tests, verify:

- `Invoke-RestMethod http://127.0.0.1:8765/api/status` returns `connected: true`.
- QGIS shows `ArduBoat Live` with an arrow marker.
- QGIS creates `ArduBoat Track` while telemetry arrives.
- The normal ground-control station still has telemetry and manual recovery.

Do not test new commands first on water. Bench test first, then validate at low speed with the normal GCS ready.
