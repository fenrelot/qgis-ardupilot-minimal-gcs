# Real BlueBoat Test Workflow

Use this checklist for the first real BlueBoat validation. It assumes the Toughbook deployment in `docs/toughbook_blueboat_deployment.md` is complete.

## Pre-Test

Working directory: repository root in Windows PowerShell.

    cd C:\qgisarduboat
    .\scripts\bootstrap_windows.ps1 -CheckOnly
    .\scripts\check_blueboat_network.ps1

Open `http://192.168.2.2` or `http://blueos.local` and confirm BlueOS is reachable.

Confirm BlueOS MAVLink Endpoints includes a UDP client endpoint to:

    udp://192.168.2.1:14552

Open the primary GCS and confirm normal telemetry and manual recovery. Blue Robotics recommends QGroundControl for BlueBoat setup; use Mission Planner only if it is already configured and tested with your BlueBoat.

## Bridge Check

Start the bridge:

    .\scripts\run_blueboat_bridge.ps1

From a second PowerShell:

    Invoke-RestMethod http://127.0.0.1:8765/api/status

Acceptance:

- `connected` is `true`
- `mode` is not empty
- `lat`, `lon`, and `heading_deg` are numeric
- `last_heartbeat_age_s` stays below the bridge heartbeat timeout

## QGIS Check

Open QGIS normally and enable/open `ArduBoat Control`.

Acceptance:

- `ArduBoat Live` appears and follows the boat.
- The marker is a clear arrow and rotates with heading.
- `ArduBoat Track` gains samples while telemetry arrives.
- `Start text log` creates a text/CSV file with timestamped location rows.
- `Save track as...` exports the track to Shapefile or GeoPackage.

## Command Check

Perform command checks only with manual recovery ready.

1. Press `GUIDED`, then confirm the primary GCS shows GUIDED.
2. Press `HOLD / STOP`, then confirm the primary GCS shows HOLD.
3. Press `MANUAL`, then confirm manual control is available.
4. Pick a nearby safe target in QGIS.
5. Press `Send target + GUIDED`.
6. Confirm the boat starts moving toward the target and can be stopped from the primary GCS.

Abort criteria:

- QGIS status disconnects or heartbeat age grows stale.
- Primary GCS telemetry is missing or inconsistent.
- Boat response does not match the commanded mode.
- Manual recovery is not immediately available.
