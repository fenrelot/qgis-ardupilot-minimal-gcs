# AGENTS.md

This repository is for a Windows 11 QGIS + ArduPilot Rover/Boat operator-map prototype. The end user wants Mission Planner to remain open for normal GCS, telemetry, joystick, setup, and failsafe awareness, while QGIS LTR shows the map, vector data, the boat position and heading, status, and a small set of commands: pick a map/vector point, send it as a Guided target, start the already-loaded mission by switching to AUTO, switch to LOITER, HOLD, GUIDED, or MANUAL.

## ExecPlans

For any complex feature, refactor, environment setup, or SITL workflow, use an ExecPlan as described in `.agent/PLANS.md`. The active project ExecPlan is `.agent/execplans/qgis_arduboat_control_execplan.md`. Keep it updated as a living document from design through implementation.

## Development rules

- Work incrementally. Prefer a working display-only version before adding commands.
- Do not remove Mission Planner from the workflow. QGIS is an auxiliary operator map and light command panel, not the only GCS.
- Do not add arming, disarming, parameter writing, joystick control, or RC override in QGIS v1.
- Treat MAVLink commands as safety-relevant. Gate all command-sending paths behind fresh heartbeat, known target system/component, and clear UI feedback.
- Keep all install scripts idempotent: checking for an installed tool must happen before installing it.
- Prefer Windows-native QGIS LTR and Windows-native QGIS plugin development. Use WSL2 for ArduPilot SITL unless the user explicitly chooses Mission Planner’s built-in simulator.
- Prefer a small localhost HTTP bridge written with Python standard library plus `pymavlink` instead of putting PyMAVLink directly into QGIS’s bundled Python environment.
- Use repository-relative paths in all instructions, code comments, and plan updates.
- Include a concise manual test after each milestone. A change is not complete until the user can see something useful in QGIS or verify it with SITL.
- Keep external dependencies minimal and documented in `requirements.txt`, install scripts, and the ExecPlan.
- When running shell commands, state the working directory in the ExecPlan or command comments.
- If a step needs administrator rights, make that explicit and provide a non-destructive dry-run or check-only mode where practical.

## Target repository layout

The intended layout is:

- `bridge/` for the Python MAVLink-to-localhost bridge.
- `qgis_plugin/qgis_arduboat/` for the QGIS Python plugin.
- `scripts/` for PowerShell and WSL setup/run scripts.
- `tests/` for Python tests of the bridge and geometry/coordinate helpers.
- `.agent/PLANS.md` for ExecPlan rules.
- `.agent/execplans/` for active and completed ExecPlans.
- `docs/` for user-facing setup and operation notes.

Create these directories when implementing the ExecPlan if they do not already exist.

## Windows and SITL assumptions

- Primary OS: Windows 11 VM.
- QGIS: latest Long Term Release; as of 2026-06-23 this is QGIS 3.44 LTR.
- Mission Planner: Windows-native install.
- SITL: ArduPilot Rover SITL through WSL2 by default, with Mission Planner and the bridge receiving MAVLink UDP outputs.
- Real boat path later: MAVProxy on Windows splits the real telemetry port to Mission Planner and the QGIS bridge.

## Acceptance style

Describe success as an observable behavior. Examples:

- “After starting SITL and the bridge, `http://127.0.0.1:8765/api/status` returns JSON with `connected: true`, a non-empty `mode`, and numeric `lat`, `lon`, and `heading_deg`.”
- “After enabling the plugin in QGIS, a layer named `ArduBoat Live` appears and an arrow marker moves/rotates as SITL moves.”
- “After clicking a point and pressing `Send target + GUIDED`, SITL switches to GUIDED and the Rover starts moving toward the clicked WGS84 coordinate.”

