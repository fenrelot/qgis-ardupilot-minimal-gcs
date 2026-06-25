# Build a QGIS LTR operator map for ArduPilot Rover/Boat with Mission Planner running

This ExecPlan is a living document. It must be maintained according to `.agent/PLANS.md` in this repository.

## Purpose / Big Picture

The goal is to build a Windows 11 development project that lets the user keep Mission Planner running for ArduPilot Rover/Boat telemetry, joystick control, setup, and safety backup, while QGIS LTR acts as the richer GIS/chartplotter-style operator map. After this work, the user can open QGIS, load raster and vector map data, see the live boat position and heading, inspect clicked coordinates, choose a point from the map or existing vector data, send that point as a Guided target, switch the vehicle into AUTO to start the already-loaded mission, and switch to LOITER, HOLD, GUIDED, or MANUAL.

The first proof should be in ArduPilot SITL, which means Software-In-The-Loop simulation. SITL runs the ArduPilot vehicle code on the computer without real hardware. The final development workflow must work on a Windows 11 VM with QGIS LTR installed natively and ArduPilot Rover SITL running through WSL2 by default.

## Progress

- [x] (2026-06-23 17:00 Europe/Vienna) Create initial repository structure and check in this ExecPlan.
- [x] (2026-06-23 21:19 Europe/Vienna) Implement idempotent Windows environment checker and installer script.
- [x] (2026-06-23 21:19 Europe/Vienna) Implement WSL2 ArduPilot Rover SITL setup/run script.
- [x] (2026-06-23 22:03 Europe/Vienna) Install Windows-side dependencies: Git for Windows, Python 3.12 with pip, QGIS 3.44 LTR, Mission Planner, MAVProxy, and project `.venv`.
- [x] (2026-06-24 17:50 Europe/Vienna) Enable WSL optional features, install Ubuntu 22.04 as WSL1 fallback, create the non-root `ardupilot` WSL user, and make it the default user.
- [x] (2026-06-24 18:05 Europe/Vienna) Install ArduPilot Rover SITL prerequisites in Ubuntu 22.04 WSL1 and build the Rover SITL binary at `/home/ardupilot/ardupilot/build/sitl/bin/ardurover`.
- [x] (2026-06-24 22:20 Europe/Vienna) Implement Python MAVLink bridge with localhost JSON API, telemetry state parsing, and safety-gated command paths.
- [x] (2026-06-24 22:20 Europe/Vienna) Add bridge unit tests for state parsing, command formatting/gating, and HTTP API responses.
- [x] (2026-06-24 22:47 Europe/Vienna) Implement QGIS plugin skeleton, metadata, dock panel, bridge polling client, development launcher, and headless-validated `ArduBoat Live` memory layer update path.
- [x] (2026-06-25 08:14 Europe/Vienna) Show live boat position and heading as a rotating marker in the QGIS plugin code, with headless layer validation complete and GUI/SITL manual acceptance still pending.
- [x] (2026-06-25 08:14 Europe/Vienna) Implement map click and active vector-layer target picking with CRS conversion to WGS84.
- [x] (2026-06-25 08:14 Europe/Vienna) Implement bridge-backed mode buttons: MANUAL, HOLD, LOITER, GUIDED, AUTO.
- [x] (2026-06-25 08:14 Europe/Vienna) Implement `Send target` and `Send target + GUIDED` plugin commands through the bridge guided-target API.
- [ ] Write user documentation for SITL and real boat telemetry-split workflows.
- [ ] Validate end-to-end with Rover SITL, Mission Planner, bridge, and QGIS.

## Surprises & Discoveries

- Observation: This Windows VM has `wsl.exe` and `codex.exe`, but Git, Python, pip, winget, QGIS LTR, Mission Planner, MAVProxy, and VS Code are not currently on PATH or found by the checker.
  Evidence: From the repository root, `.\scripts\bootstrap_windows.ps1 -CheckOnly` reports those tools as missing and reports Codex CLI under the user profile.

- Observation: WSL is present but an Ubuntu distro is not installed or cannot be listed, so the WSL bash scripts could not be executed in this environment.
  Evidence: `.\scripts\bootstrap_windows.ps1 -CheckOnly` reports `WSL Ubuntu: missing WSL found; distro listing failed. Install Ubuntu with: wsl --install -d Ubuntu`.

- Observation: The working VM is Windows 10 Enterprise LTSC 2021 21H2, not Windows 11. The Microsoft Store/App Installer path is incomplete on this image.
  Evidence: Registry `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion` reports `ProductName: Windows 10 Enterprise LTSC 2021`, `DisplayVersion: 21H2`, `CurrentBuild: 19044`, `EditionID: EnterpriseS`.

- Observation: `winget` can be sideloaded onto this LTSC image from the official Microsoft `winget-cli` MSIX release, but it is not runnable because Windows reports no applicable app license.
  Evidence: Running `winget --version` fails with `No applicable app licenses found`; the checker reports `winget: missing present but not runnable`.

- Observation: Ubuntu app registration is blocked because the Windows Subsystem for Linux optional feature is disabled.
  Evidence: Running `ubuntu.exe --help` attempts first-time registration and fails with `WslRegisterDistribution failed with error: 0x8007019e`, followed by `The Windows Subsystem for Linux has not been enabled`.

- Observation: QGIS 3.44 LTR bundles its own Python under `QGIS 3.44.11\bin`; adding QGIS `bin` to global PATH shadows the normal project Python.
  Evidence: With QGIS `bin` first on PATH, `python --version` reports Python 3.12.13 from QGIS. The bootstrap script was corrected to detect QGIS by path without adding QGIS `bin` to PATH.

- Observation: The official ArduPilot firmware tools directory exposes stable latest installer names for Mission Planner and MAVProxy.
  Evidence: `https://firmware.ardupilot.org/Tools/MissionPlanner/` lists `MissionPlanner-latest.msi`; `https://firmware.ardupilot.org/Tools/MAVProxy/` lists `MAVProxySetup-latest.exe`.

- Observation: WSL management commands on this VM return `Access is denied` from a normal PowerShell, but work from an elevated PowerShell process.
  Evidence: Non-elevated `wsl.exe --status` and `wsl.exe -l -v` return `Access is denied`; elevated `wsl.exe --status` reports a default WSL version and elevated `wsl.exe -l -v` lists distros.

- Observation: WSL2 cannot start in this VM because nested virtualization is not exposed.
  Evidence: Installing Ubuntu 24.04 as WSL2 failed with `HCS_E_HYPERV_NOT_INSTALLED` and the message `WSL2 is unable to start since virtualization is not enabled on this machine`.

- Observation: Ubuntu 24.04 WSL1 registered successfully but is not a good SITL target on this VM because some `systemd` packages fail to configure under the old WSL1 kernel.
  Evidence: The ArduPilot prerequisite install in Ubuntu 24.04 WSL1 failed while configuring `systemd`, `udev`, `systemd-resolved`, `systemd-sysv`, `libpam-systemd`, and `libnss-systemd`.

- Observation: Ubuntu 22.04 WSL1 works for ArduPilot SITL on this VM after handling a WSL1 apt terminal-control artifact.
  Evidence: `scripts/bootstrap_wsl_ardupilot.sh` completed in Ubuntu 22.04 WSL1, `scripts/check_wsl_sitl.sh` reports `Python MAVLink tooling: ok`, and `scripts/build_sitl_rover_wsl.sh` finished with `'rover' finished successfully`.

- Observation: The noninteractive WSL install initially launches Ubuntu as `root`, but ArduPilot's prerequisite script refuses root.
  Evidence: `Tools/environment_install/install-prereqs-ubuntu.sh -y` printed `Please do not run this script as root; don't sudo it!`.

- Observation: Plain `python -m pytest` initially tried to collect an access-denied generated directory named `pytest-cache-files-mgmlqzlc`.
  Evidence: Pytest failed during collection with `PermissionError: [WinError 5] Access is denied: 'C:\\qgisarduboat\\pytest-cache-files-mgmlqzlc'`. Adding `pytest.ini` with `testpaths = tests`, `norecursedirs = .venv pytest-cache-files-*`, and disabling the cache provider made plain `python -m pytest` collect only project tests.

- Observation: Ruff checks pass, but this restricted workspace denies writing `.ruff_cache`.
  Evidence: `.\.venv\Scripts\ruff.exe check bridge tests` reports `All checks passed!` and warnings about failing to write cache files under `.ruff_cache`.

- Observation: The QGIS `python-qgis-ltr.bat` launcher did not set the Qt DLL search path correctly when invoked from this shell, but explicit QGIS DLL directories make command-line PyQGIS import validation work.
  Evidence: Importing `qgis.PyQt.QtCore` through `python-qgis-ltr.bat` failed with `DLL load failed while importing QtCore`; rerunning with `os.add_dll_directory()` for QGIS `bin`, `apps\Qt5\bin`, and `apps\qgis-ltr\bin` successfully imported the plugin modules.

- Observation: Headless PyQGIS validation can create and update the live memory layer in this environment, but QGIS prints restricted-process warnings on exit.
  Evidence: A `QgsApplication` script created `ArduBoat Live` with one feature and the expected fields, then printed `QFSFileEngine::open: No file name specified` and `QProcess: CreateFile failed. (Access is denied.)` while still exiting 0.

- Observation: Running QGIS's bundled `python.exe` directly does not automatically expose the `qgis` Python package, but adding QGIS's Python package directories and DLL directories makes plugin import validation work.
  Evidence: A direct import attempt failed with `ModuleNotFoundError: No module named 'qgis'`; rerunning with `qgis-ltr\python`, QGIS DLL directories, and `QGIS_PREFIX_PATH` injected printed `qgis plugin import ok`.

- Observation: A headless Qt dock-widget smoke test can construct the `ArduBoat Control` dock without opening QGIS, but the standalone QGIS Python process prints font-prefix warnings in this shell.
  Evidence: The smoke test printed `ArduBoat Control False False`, confirming the dock constructed and target-send buttons were disabled while disconnected, followed by `Could not find platform independent libraries <prefix>` and `QFontDatabase: Cannot find font directory /fonts` warnings while still exiting 0.

## Decision Log

- Decision: Use a small Python localhost bridge rather than importing PyMAVLink directly inside QGIS.
  Rationale: QGIS ships its own Python environment on Windows. Keeping MAVLink I/O in a normal Python virtual environment avoids dependency conflicts and lets the QGIS plugin stay small, using only QGIS/PyQt and Python standard-library HTTP requests.
  Date/Author: 2026-06-23 / ChatGPT

- Decision: Keep Mission Planner in the control workflow and make QGIS an auxiliary operator map and light command panel.
  Rationale: The user explicitly wants Mission Planner to remain running for telemetry and Xbox joystick control. This also preserves a proven GCS and safety fallback while the QGIS integration is developed.
  Date/Author: 2026-06-23 / ChatGPT

- Decision: Use WSL2 for ArduPilot SITL by default, but also document Mission Planner's built-in SITL as a fallback.
  Rationale: ArduPilot's development tooling is Linux-oriented and `sim_vehicle.py` is intended to run from Linux or WSL2. Mission Planner also provides a built-in simulation path that is useful when the user wants a quick non-development test.
  Date/Author: 2026-06-23 / ChatGPT

- Decision: Do not implement arming, disarming, parameter writes, joystick control, or RC override in QGIS v1.
  Rationale: The desired feature set does not require these actions, and excluding them reduces safety risk. Mission Planner and the real RC/joystick path remain responsible for those functions.
  Date/Author: 2026-06-23 / ChatGPT

- Decision: Make `scripts/bootstrap_windows.ps1` report-only unless explicit install or create flags are passed.
  Rationale: Several install paths can require administrator approval or network downloads. A non-destructive `-CheckOnly` path gives the user a clear environment report before any changes.
  Date/Author: 2026-06-23 / Codex

- Decision: Verify winget package IDs at runtime with `winget search` before using `winget install`.
  Rationale: Package IDs can change. Runtime verification keeps the script idempotent and avoids installing a guessed package.
  Date/Author: 2026-06-23 / Codex

- Decision: Keep the Codex CLI missing-install branch advisory-only for now.
  Rationale: Codex CLI is already installed in this VM, and no stable unattended Windows install command was embedded. The script reports the official Codex download path for missing installs and suggests `codex update` when Codex is already present.
  Date/Author: 2026-06-23 / Codex

- Decision: On Windows 10 LTSC, prefer direct official installers over `winget` when `winget` is missing or not runnable.
  Rationale: The LTSC image lacks a working App Installer license path. Direct installers successfully installed Git, Python, QGIS, Mission Planner, and MAVProxy without relying on Store infrastructure.
  Date/Author: 2026-06-23 / Codex

- Decision: Use Python 3.12.10 for the project Python install.
  Rationale: The Python FTP index lists later 3.12 source releases, but 3.12.10 is the latest verified 3.12 directory in the index with a Windows `python-3.12.10-amd64.exe` installer.
  Date/Author: 2026-06-23 / Codex

- Decision: Use Ubuntu 22.04 WSL1 for SITL on this VM instead of Ubuntu 24.04 WSL2.
  Rationale: WSL2 is blocked by missing nested virtualization. Ubuntu 24.04 WSL1 registers, but its `systemd` package configuration fails under this WSL1 kernel. Ubuntu 22.04 WSL1 completes ArduPilot prerequisites and builds Rover SITL.
  Date/Author: 2026-06-24 / Codex

- Decision: Add `scripts/bootstrap_wsl_user.sh`, `scripts/check_wsl_sitl.sh`, and `scripts/build_sitl_rover_wsl.sh`.
  Rationale: The WSL distro needed a non-root `ardupilot` user, repeatable validation commands, and a direct `waf` build path because this ArduPilot version does not provide `sim_vehicle.py --build-only`.
  Date/Author: 2026-06-24 / Codex

- Decision: Default the WSL SITL run script to `127.0.0.1` on WSL1 and make MAVProxy `--map --console` opt-in with `SHOW_MAVPROXY_UI=1`.
  Rationale: WSL1 shares localhost with Windows and this VM does not provide WSL GUI support. Mission Planner and QGIS provide the operator map, so MAVProxy GUI windows are not required for the normal workflow.
  Date/Author: 2026-06-24 / Codex

- Decision: Keep the bridge HTTP API on Python standard library `http.server` and keep all MAVLink I/O in the bridge process.
  Rationale: This satisfies the minimal-dependency requirement and keeps QGIS isolated from PyMAVLink and its Windows packaging concerns.
  Date/Author: 2026-06-24 / Codex

- Decision: Gate bridge command sends in the command module, not only in the future QGIS UI.
  Rationale: MAVLink commands are safety-relevant. The API must refuse stale heartbeat or unknown target system/component even if a caller bypasses the QGIS plugin.
  Date/Author: 2026-06-24 / Codex

- Decision: Load the development plugin through `QGIS_PLUGINPATH` instead of copying files into the QGIS user profile during development.
  Rationale: Keeping QGIS pointed at `qgis_plugin/` preserves repository-relative paths and avoids manual file synchronization while the plugin is still changing.
  Date/Author: 2026-06-24 / Codex

- Decision: Keep all QGIS command buttons as bridge HTTP calls and keep the plugin-side checks as user-interface gates only.
  Rationale: The bridge already enforces the safety-critical heartbeat and target-system/component gates. The plugin adds clearer operator feedback, disables controls while disconnected, refuses plain `Send target` unless the current mode is already GUIDED, and asks for confirmation for targets more than 1000 m from the current boat position.
  Date/Author: 2026-06-25 / Codex

## Outcomes & Retrospective

Milestone 1 is implemented. The repository now has requirements files, placeholder skeleton directories, `scripts/bootstrap_windows.ps1`, `scripts/bootstrap_wsl_ardupilot.sh`, and `scripts/run_sitl_rover_wsl.sh`.

The Windows checker has been validated in `-CheckOnly` mode from the repository root. It prints the working directory, administrator status, a tool-by-tool report, and next commands without installing anything. On this VM, the current installed state is: Git for Windows 2.54.0, Python 3.12.10 with pip, QGIS 3.44.11 LTR, Mission Planner, MAVProxy 1.8.74, Codex CLI, and the project `.venv` with `pymavlink`, `pytest`, and `ruff`.

The WSL setup has now been executed on this VM using Ubuntu 22.04 as a WSL1 fallback. WSL2 remains unavailable because nested virtualization is not exposed to the VM. Ubuntu 24.04 was installed but is not the active SITL target because `systemd` packages failed to configure under WSL1. Ubuntu 22.04 is the default WSL distro, the default Linux user is `ardupilot`, ArduPilot is cloned at `/home/ardupilot/ardupilot`, the ArduPilot prerequisite script completed, and Rover SITL was built successfully.

The next milestone is the Python MAVLink bridge. The next manual SITL validation is to start Rover SITL with `bash scripts/run_sitl_rover_wsl.sh`, connect Mission Planner to UDP 14550, and later connect the bridge to UDP 14551.

The Python bridge milestone is implemented. The bridge can be started with `.\scripts\run_bridge.ps1` or `.\.venv\Scripts\python.exe -m bridge.main --connect udpin:0.0.0.0:14551`. It exposes `GET /api/status`, `POST /api/mode`, and `POST /api/guided_target`. Command sends are refused unless a fresh heartbeat has identified a target system/component. Automated tests pass for state parsing, command formatting/gating, and HTTP API behavior. A runtime smoke test started the bridge on port 8766 and confirmed `/api/status` returns well-formed disconnected JSON before SITL is running.

The QGIS plugin skeleton milestone is implemented. The plugin directory has metadata, a `classFactory`, a menu/toolbar action, a dock widget named `ArduBoat Control`, a standard-library bridge HTTP client, a one-second status polling timer, raw JSON display, status labels, and an `ArduBoat Live` EPSG:4326 memory point layer updater. The marker layer has `heading_deg` as an attribute and uses a triangle symbol with data-defined angle rotation. The plugin can be launched for development with `.\scripts\run_qgis_plugin_dev.ps1`, which sets `QGIS_PLUGINPATH` to `qgis_plugin/` before starting QGIS.

The target picking and command-button milestone is implemented in code. The dock now has target controls, WGS84 and project-CRS target readouts, distance and bearing calculations from the current boat status, bridge-backed mode buttons for AUTO, GUIDED, LOITER, HOLD, and MANUAL, and target-send buttons. The map tool captures map clicks in the canvas CRS, transforms them to EPSG:4326, and when the active layer is a vector layer it prefers an active point feature or nearest active-layer vertex before falling back to the map click. `Send target` refuses locally unless the last known mode is GUIDED. `Send target + GUIDED` calls the bridge with `set_guided=true`; the bridge remains responsible for MAVLink heartbeat and target-system safety gates.

## Context and Orientation

This repository starts as an empty or nearly empty project. Create the following structure if it does not exist:

    bridge/
    qgis_plugin/qgis_arduboat/
    scripts/
    tests/
    docs/
    .agent/execplans/

Current milestone state:

    requirements.txt
    requirements-dev.txt
    bridge/.gitkeep
    qgis_plugin/qgis_arduboat/.gitkeep
    tests/.gitkeep
    scripts/bootstrap_windows.ps1
    scripts/bootstrap_wsl_user.sh
    scripts/bootstrap_wsl_ardupilot.sh
    scripts/build_sitl_rover_wsl.sh
    scripts/check_wsl_sitl.sh
    scripts/run_sitl_rover_wsl.sh
    scripts/run_bridge.ps1
    scripts/run_qgis_plugin_dev.ps1
    bridge/__init__.py
    bridge/config.py
    bridge/commands.py
    bridge/http_api.py
    bridge/main.py
    bridge/mavlink_client.py
    bridge/state.py
    qgis_plugin/qgis_arduboat/__init__.py
    qgis_plugin/qgis_arduboat/metadata.txt
    qgis_plugin/qgis_arduboat/plugin.py
    qgis_plugin/qgis_arduboat/dock_widget.py
    qgis_plugin/qgis_arduboat/bridge_client.py
    qgis_plugin/qgis_arduboat/live_layer.py
    qgis_plugin/qgis_arduboat/targeting.py
    qgis_plugin/qgis_arduboat/map_tools.py
    tests/test_commands.py
    tests/test_http_api.py
    tests/test_plugin_bridge_client.py
    tests/test_state_parsing.py
    tests/test_targeting.py
    pytest.ini

Installed local environment state as of 2026-06-23 22:03 Europe/Vienna:

    Git for Windows: installed and detected
    Python: installed as user Python 3.12.10 with pip
    Project venv: .venv created and requirements-dev.txt installed
    QGIS LTR: installed at QGIS 3.44.11
    Mission Planner: installed
    MAVProxy: installed at Program Files (x86)\MAVProxy
    winget: app alias exists but is not runnable on this LTSC image
    WSL Ubuntu: Ubuntu package alias exists, but registration is blocked until WSL is enabled

Installed WSL/SITL environment state as of 2026-06-24 18:05 Europe/Vienna:

    WSL optional features: enabled
    WSL2: unavailable in this VM because virtualization is not exposed
    Ubuntu 22.04: installed as WSL1 and set as the default distro
    Ubuntu 24.04: installed as WSL1 but not used for SITL because systemd package configuration failed
    WSL default user for Ubuntu 22.04: ardupilot
    ArduPilot checkout: /home/ardupilot/ardupilot
    ArduPilot commit checked by validation: 845b9b3c86
    MAVProxy in WSL: 1.8.74
    Rover SITL binary: /home/ardupilot/ardupilot/build/sitl/bin/ardurover

MAVLink is the message protocol used by ArduPilot vehicles and ground-control stations. Mission Planner, MAVProxy, and the new Python bridge all speak MAVLink. QGIS is the GIS desktop application that will display georeferenced raster/vector data and the live boat marker. CRS means coordinate reference system. QGIS projects may use projected CRSs such as UTM or Austrian coordinate systems, but MAVLink global target commands require WGS84 latitude/longitude.

The target architecture is:

    ArduPilot Rover SITL in WSL2
        -> MAVProxy UDP output 14550 to Mission Planner on Windows
        -> MAVProxy UDP output 14551 to Python bridge on Windows

    Python bridge on Windows
        -> receives MAVLink telemetry
        -> sends MAVLink mode and guided-target commands
        -> exposes localhost HTTP API on http://127.0.0.1:8765

    QGIS LTR on Windows
        -> runs qgis_arduboat plugin
        -> polls bridge HTTP API for status
        -> displays live boat marker with heading
        -> sends mode/target commands to bridge by HTTP POST

For a real boat later, use MAVProxy on Windows to split the telemetry radio or serial link:

    mavproxy.exe --master=COM7 --baudrate 57600 --out=127.0.0.1:14550 --out=127.0.0.1:14551

Mission Planner connects to UDP 14550. The bridge connects to UDP 14551. COM port and baudrate are examples and must be configurable.

Important external facts embedded in this plan:

- QGIS latest LTR at plan creation time is 3.44 LTR. Prefer QGIS LTR over latest QGIS 4.x because plugin compatibility matters.
- QGIS Python plugins are supported and are searched through QGIS plugin paths. For development on Windows, the plugin can be installed into the user QGIS profile plugin directory or loaded by setting `QGIS_PLUGINPATH` to the repository's `qgis_plugin` directory.
- ArduPilot SITL can run with `sim_vehicle.py` from Linux or WSL2, and `sim_vehicle.py` starts MAVProxy automatically.
- MAVProxy on Windows is available as `MAVProxySetup-latest.exe`, and on Linux/WSL it can be installed with Python/pip after installing prerequisites.
- ArduPilot Rover/Boat Guided mode supports `SET_POSITION_TARGET_GLOBAL_INT` for WGS84 latitude/longitude targets.
- ArduPilot flight mode changes can be requested with `MAV_CMD_DO_SET_MODE` in a `COMMAND_LONG` message using `param1 = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED` and `param2 = the Rover mode number`.
- Rover mode numbers needed here are: MANUAL 0, HOLD 4, LOITER 5, AUTO 10, GUIDED 15.
- `GLOBAL_POSITION_INT.hdg` is heading in centidegrees when available; if it is unavailable, use `VFR_HUD.heading` or `ATTITUDE.yaw` as fallback.
- The bridge should use a GCS MAVLink source system that does not collide with Mission Planner if practical. Use `source_system=245` by default. Warn in status if `SYSID_ENFORCE` appears to block commands or if commands are denied.

## Plan of Work

First, create a repository skeleton with an environment checker. The Windows PowerShell script should detect Git, Python, pip, QGIS LTR, Mission Planner, MAVProxy, WSL2 Ubuntu, and Codex CLI. It should install or guide installation for missing components. The script must support a dry-run/check-only mode, because install steps can need administrator permission.

Second, add a WSL setup script for ArduPilot Rover SITL. It should clone ArduPilot if missing, initialize submodules, run the ArduPilot Ubuntu prerequisite installer, and provide a run command that starts Rover SITL with MAVProxy outputs to Windows UDP ports 14550 and 14551. Because WSL networking differs between NAT and mirrored networking, the script must detect the Windows host IP and allow an override.

Third, implement the Python bridge. It should be a normal Windows Python package or simple script under `bridge/`. It should use `pymavlink` for MAVLink and Python standard library `http.server` for the local API. It must run without QGIS. It must read telemetry messages in a background thread, maintain a thread-safe state object, and expose HTTP endpoints for status and commands.

Fourth, implement the QGIS plugin. It should create a dock panel named `ArduBoat Control`, a memory point layer named `ArduBoat Live`, and a timer that polls `http://127.0.0.1:8765/api/status`. It should update the marker position and rotate the symbol by `heading_deg`. It should show connection, mode, armed, GPS fix, satellite count, heading, ground speed, battery voltage if available, and last warning text.

Fifth, implement the QGIS target picking workflow. A map tool based on QGIS map-canvas tools should capture a click, transform the clicked project coordinate to WGS84 EPSG:4326, display both coordinate sets, and compute distance/bearing from the current boat position. Add a vector-pick helper that can use selected point features directly, use nearest vertex for line/polygon features, or use feature centroid when requested.

Sixth, implement safe commands. The QGIS plugin sends HTTP POST requests to the bridge; the bridge sends MAVLink. Commands are refused when no heartbeat has arrived in the last three seconds, when target system/component are unknown, or when a clicked target is missing. Add optional confirmation in the plugin if the target is farther than a configurable threshold such as 200 m.

Seventh, document and validate. The docs must show a SITL flow and a real-boat telemetry-split flow. The validation must demonstrate Mission Planner and QGIS running together.

## Concrete Steps

### 1. Create repository skeleton

Working directory: repository root.

Run:

    mkdir bridge qgis_plugin scripts tests docs 2>$null
    mkdir qgis_plugin\qgis_arduboat 2>$null
    New-Item -ItemType File -Force requirements.txt
    New-Item -ItemType File -Force requirements-dev.txt

Expected result: the directories exist and `git status` shows new files/directories.

### 2. Add requirements

Create `requirements.txt` with:

    pymavlink>=2.4

Create `requirements-dev.txt` with:

    -r requirements.txt
    pytest>=8
    ruff>=0.6

Do not add Flask/FastAPI/WebSocket dependencies for v1 unless there is a strong reason. The bridge API can use Python standard library HTTP.

### 3. Implement Windows bootstrap script

Create `scripts/bootstrap_windows.ps1`.

Required features:

- Parameters:

    [switch]$CheckOnly
    [switch]$InstallTools
    [switch]$InstallWinget
    [switch]$InstallQgis
    [switch]$InstallMissionPlanner
    [switch]$InstallMavproxy
    [switch]$InstallCodexCli
    [switch]$InstallWslSitl
    [switch]$CreateVenv

- Detect commands with `Get-Command`: `git`, `python`, `py`, `pip`, `mavproxy.exe`, `codex`, `wsl`, `winget`.
- Detect QGIS by checking common install paths such as `C:\Program Files\QGIS 3.44*`, `C:\OSGeo4W\apps\qgis-ltr`, and Apps & Features registry entries if needed.
- Detect Mission Planner by checking common install paths and/or Apps & Features registry entries.
- If `winget` is available, use it for Git, Python, VS Code, and QGIS LTR when possible. Use package IDs only after verifying with `winget search` in the script or after documenting fallback. Known likely package IDs to try are `Git.Git`, `Microsoft.VisualStudioCode`, `Python.Python.3.12`, and `OSGeo.QGIS_LTR`.
- For Mission Planner, download the latest official MSI from ArduPilot firmware tools if not installed, then run it interactively or with MSI quiet flags only after confirming the file exists. Do not invent a winget ID unless `winget search` confirms it.
- For MAVProxy on Windows, prefer the official `MAVProxySetup-latest.exe` download. Alternatively, support `python -m pip install --user --upgrade mavproxy pymavlink` as a fallback and report that the Windows executable may be named `mavproxy.exe`.
- For Codex CLI, run the official Windows PowerShell install command only when `-InstallCodexCli` is passed and the user accepts. If this is not possible, print the command for the user to run.
- Create `.venv` and install requirements when `-CreateVenv` is passed.
- Print a final environment report with installed/missing status and next commands.

Acceptance for this step:

    PS C:\work\qgis-arduboat> .\scripts\bootstrap_windows.ps1 -CheckOnly
    QGIS LTR: found or missing
    Mission Planner: found or missing
    MAVProxy: found or missing
    Python: found
    WSL: found or missing

Observed validation in this VM from the repository root:

    PS> .\scripts\bootstrap_windows.ps1 -CheckOnly
    Working directory: repository root
    Administrator: no
    Git: found
    Python: found Python 3.12.10
    QGIS LTR: found QGIS 3.44.11
    Mission Planner: found
    MAVProxy: found
    WSL Ubuntu: missing WSL found; distro listing failed. Install Ubuntu with: wsl --install -d Ubuntu
    Codex CLI: found under the user profile

Additional validation after installation:

    PS> .\scripts\bootstrap_windows.ps1 -CheckOnly
    Git: found
    Python: found Python 3.12.10
    pip: found
    QGIS LTR: found QGIS 3.44.11
    Mission Planner: found
    MAVProxy: found

    PS> .venv\Scripts\python.exe -c "import pymavlink; import pytest; import ruff; print('venv ok')"
    venv ok

    PS> "QGIS 3.44.11\bin\qgis-ltr-bin.exe" --version
    QGIS 3.44.11-Solothurn 'Solothurn'

    PS> "Program Files (x86)\MAVProxy\mavproxy.exe" --version
    MAVProxy Version: 1.8.74

### 4. Implement WSL SITL scripts

Create `scripts/bootstrap_wsl_user.sh`, `scripts/bootstrap_wsl_ardupilot.sh`, `scripts/build_sitl_rover_wsl.sh`, `scripts/check_wsl_sitl.sh`, and `scripts/run_sitl_rover_wsl.sh`.

`bootstrap_wsl_user.sh` must:

- Run as root inside the target Ubuntu WSL distro.
- Create a non-root user named `ardupilot` if missing.
- Add the user to the `sudo` group and install a WSL-local passwordless sudoers entry for automation.
- Move an accidental root-owned `/root/ardupilot` checkout to `/home/ardupilot/ardupilot` when safe to do so.
- Set the WSL default user to `ardupilot` through `/etc/wsl.conf` when no conflicting setting exists.

`bootstrap_wsl_ardupilot.sh` must:

- Run from WSL Ubuntu.
- Run as a non-root user.
- Install apt packages required by ArduPilot's Ubuntu prerequisites or call ArduPilot's `install-prereqs-ubuntu.sh` after cloning.
- Clone `https://github.com/ArduPilot/ardupilot.git` into `~/ardupilot` if missing.
- Initialize submodules.
- Run `Tools/environment_install/install-prereqs-ubuntu.sh -y`.
- Remind the user to restart the WSL shell or source the profile.
- In WSL1, tolerate the known `apt-get` `tcsetattr` terminal-control artifact only when package configuration is clean.

`build_sitl_rover_wsl.sh` must:

- Source the WSL user's profile.
- Run `./waf configure --board sitl`.
- Run `./waf rover`.

`check_wsl_sitl.sh` must:

- Source the WSL user's profile.
- Print the ArduPilot checkout path, commit, Python version, MAVProxy version, and a short `sim_vehicle.py --help` excerpt.

`run_sitl_rover_wsl.sh` must:

- Accept `WINDOWS_HOST_IP`, `MP_PORT`, `BRIDGE_PORT`, and `LOCATION` environment variables.
- Default `MP_PORT=14550`, `BRIDGE_PORT=14551`.
- Detect Windows host IP with `ip route show | awk '/default/ {print $3}'`, but allow override. On WSL1, default to `127.0.0.1`.
- Accept `SHOW_MAVPROXY_UI=1` to request MAVProxy `--map --console`; default to no MAVProxy GUI windows on WSL1.
- Start Rover SITL from `~/ardupilot` with a command similar to:

    cd ~/ardupilot
    ./Tools/autotest/sim_vehicle.py -v Rover --out=udp:${WINDOWS_HOST_IP}:${MP_PORT} --out=udp:${WINDOWS_HOST_IP}:${BRIDGE_PORT}

- Document that if WSL2 mirrored networking is configured and networking fails, try `127.0.0.1` or the ArduPilot `--no-wsl2-network` option.

Acceptance for this step: Mission Planner on Windows can connect to UDP 14550 while the bridge later receives UDP 14551.

Implementation status for this step: Ubuntu 22.04 WSL1 has been installed, the `ardupilot` user has been created, ArduPilot prerequisites have been installed, and Rover SITL has been built.

Observed validation in this VM from elevated PowerShell:

    PS> wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/check_wsl_sitl.sh
    ArduPilot directory: /home/ardupilot/ardupilot
    ArduPilot commit: 845b9b3c86
    Python 3.10.12
    Python MAVLink tooling: ok
    MAVProxy Version: 1.8.74
    Usage: sim_vehicle.py

    PS> wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/build_sitl_rover_wsl.sh
    'rover' finished successfully (8m3.173s)

Historical WSL2 recovery commands: run these from an elevated Administrator PowerShell, then reboot if Windows requests it:

    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    wsl.exe --set-default-version 2
    ubuntu.exe

If WSL2 cannot be enabled because nested virtualization is unavailable in the VM, use Ubuntu 22.04 WSL1 for SITL dependencies if ArduPilot works acceptably, or switch to Mission Planner's built-in simulator for early bridge/plugin validation. On this VM, WSL2 is unavailable and Ubuntu 22.04 WSL1 is the working SITL path. If normal `wsl.exe` commands return `Access is denied`, run the same WSL command from an elevated Administrator PowerShell.

### 5. Implement the Python bridge

Create these files:

    bridge/__init__.py
    bridge/config.py
    bridge/mavlink_client.py
    bridge/state.py
    bridge/http_api.py
    bridge/main.py
    bridge/commands.py

Bridge behavior:

- Default MAVLink connection string: `udpin:0.0.0.0:14551`.
- Default HTTP bind: `127.0.0.1:8765`.
- Use `mavutil.mavlink_connection(connection_string, source_system=245)`.
- Wait for first heartbeat and store target system/component from it.
- Read messages continuously in a daemon thread.
- Parse at least `HEARTBEAT`, `GLOBAL_POSITION_INT`, `GPS_RAW_INT`, `VFR_HUD`, `ATTITUDE`, `SYS_STATUS`, `BATTERY_STATUS`, and `STATUSTEXT`.
- Convert units:
  - lat/lon from integer degrees times 1e7 to decimal degrees.
  - heading from centidegrees to degrees when `GLOBAL_POSITION_INT.hdg` is not 65535.
  - yaw from radians to degrees normalized to 0..360.
  - ground speed from cm/s to m/s where applicable.
- Expose JSON status:

    GET /api/status

    {
      "connected": true,
      "last_heartbeat_age_s": 0.5,
      "target_system": 1,
      "target_component": 1,
      "mode": "MANUAL",
      "mode_number": 0,
      "armed": false,
      "lat": 48.2082,
      "lon": 16.3738,
      "heading_deg": 91.2,
      "ground_speed_m_s": 0.0,
      "gps_fix_type": 3,
      "satellites_visible": 15,
      "battery_voltage_v": 15.6,
      "last_statustext": ""
    }

- Expose commands:

    POST /api/mode
    Body: {"mode":"MANUAL"} or {"mode_number":0}

    POST /api/guided_target
    Body: {"lat":48.2082,"lon":16.3738,"set_guided":true}

- Mode mapping for Rover:

    MANUAL = 0
    HOLD = 4
    LOITER = 5
    AUTO = 10
    GUIDED = 15

- To set mode, send `COMMAND_LONG` with `MAV_CMD_DO_SET_MODE`, `MAV_MODE_FLAG_CUSTOM_MODE_ENABLED`, and the mode number.
- To send a Guided target, optionally set GUIDED first, then send `SET_POSITION_TARGET_GLOBAL_INT` with position mask 3580, latitude and longitude multiplied by 1e7, and altitude 0 using a global-relative frame suitable for Rover/Boat.
- Refuse command with HTTP 409 if heartbeat is stale or target system/component is unknown.
- Return JSON command result with `accepted_to_send: true/false`, reason, and current mode.

Acceptance for this step:

    PS C:\work\qgis-arduboat> .\.venv\Scripts\python.exe -m bridge.main --connect udpin:0.0.0.0:14551
    Bridge listening on http://127.0.0.1:8765

    PS C:\work\qgis-arduboat> Invoke-RestMethod http://127.0.0.1:8765/api/status

The status returns `connected: true` when SITL is running.

### 6. Add bridge tests

Create tests under `tests/`:

- `tests/test_state_parsing.py` for unit conversion and status JSON shape.
- `tests/test_commands.py` for mode mapping and command refusal when heartbeat is stale.
- `tests/test_http_api.py` for basic `/api/status` without a real MAVLink connection if the API is factored so it can be tested with fake state.

Run:

    .\.venv\Scripts\python.exe -m pytest

Expected result: all tests pass.

### 7. Implement QGIS plugin skeleton

Create `qgis_plugin/qgis_arduboat/` with:

    __init__.py
    metadata.txt
    plugin.py
    dock_widget.py
    map_tools.py
    bridge_client.py
    live_layer.py

`metadata.txt` must declare the plugin name, description, version, QGIS minimum version, author, and category. Use a minimum QGIS version compatible with QGIS 3.44.

The plugin must:

- Add a menu action and toolbar button named `ArduBoat Control`.
- Open a dock widget.
- Provide a configurable bridge URL, default `http://127.0.0.1:8765`.
- Poll `/api/status` with a `QTimer`, initially every 500 ms or 1000 ms.
- Show status fields.
- Create or update a memory vector layer named `ArduBoat Live` in EPSG:4326.
- Style the live feature as an arrow or triangle rotated by attribute `heading_deg`.

Acceptance for this step: QGIS plugin loads without traceback, shows the dock widget, and displays raw status from the bridge.

### 8. Implement map and vector picking

In `map_tools.py`, implement a click tool using QGIS map canvas APIs. The tool should:

- Capture the clicked map coordinate in the current project/map CRS.
- Transform it to EPSG:4326 using QGIS coordinate transform APIs.
- Send the selected target to the dock widget.
- Draw a temporary marker or rubber band at the clicked point.

In `dock_widget.py`, display:

    Target WGS84 lat/lon
    Target project CRS x/y
    Distance from boat
    Bearing from boat

For vector data support, implement one of these v1 behaviors:

- If the active layer is a point vector layer and a feature is clicked/selected, use that point.
- If the active layer is a line or polygon layer, use the nearest vertex to the click when available.
- If nearest vertex cannot be determined, use centroid and clearly label it as centroid.

Acceptance for this step: in QGIS, clicking anywhere on the map shows WGS84 coordinates and distance/bearing when boat status is available.

### 9. Implement QGIS command buttons

Add buttons:

    Send target
    Send target + GUIDED
    Start mission AUTO
    GUIDED
    LOITER
    HOLD / STOP
    MANUAL

The buttons must call the bridge API, not PyMAVLink directly. The plugin must show success/failure returned by the bridge. Disable `Send target` buttons until a target exists. Disable all command buttons when bridge status says disconnected.

`Send target` should send `/api/guided_target` with `set_guided=false` only if current mode is already GUIDED, otherwise warn or refuse in the plugin. `Send target + GUIDED` should send `set_guided=true`.

Acceptance for this step: in SITL, pressing mode buttons changes the mode observed in Mission Planner and in QGIS status.

### 10. End-to-end SITL validation

Working directory: repository root in Windows PowerShell, plus WSL Ubuntu terminal.

Start SITL in WSL:

    cd /mnt/c/qgisarduboat
    bash scripts/run_sitl_rover_wsl.sh

On this VM, use elevated Windows PowerShell if normal `wsl.exe` returns `Access is denied`:

    wsl.exe -d Ubuntu-22.04 -- bash -lc 'cd /mnt/c/qgisarduboat && bash scripts/run_sitl_rover_wsl.sh'

Set `SHOW_MAVPROXY_UI=1` only if a WSL GUI path is available and MAVProxy map/console windows are wanted.

Start Mission Planner on Windows and connect to UDP 14550.

Start bridge:

    .\.venv\Scripts\python.exe -m bridge.main --connect udpin:0.0.0.0:14551

Start QGIS LTR. Enable/load the plugin. Open a QGIS project with any map layer or an empty basemap. Verify:

- QGIS shows `connected` and current mode.
- `ArduBoat Live` marker appears at SITL location.
- Heading rotates when SITL turns.
- Clicking map shows WGS84 coordinates.
- `GUIDED`, `LOITER`, `HOLD`, `MANUAL`, and `AUTO` buttons change mode in SITL/Mission Planner.
- `Send target + GUIDED` sends the clicked target and the Rover starts moving toward it in SITL.

## Validation and Acceptance

Automated validation:

- `python -m pytest` passes.
- `python -m bridge.main --help` prints options.
- `python -m bridge.main --connect udpin:0.0.0.0:14551` starts without exception.
- `GET /api/status` returns well-formed JSON even before MAVLink is connected, with `connected: false`.
- Current milestone validation: `.\scripts\bootstrap_windows.ps1 -CheckOnly` exits 0 and reports installed/missing tools without installing anything.
- Current environment validation: `.\scripts\bootstrap_windows.ps1 -CheckOnly` reports Git, Python, pip, QGIS LTR, Mission Planner, and MAVProxy as found. Because normal `wsl.exe` returns `Access is denied` on this VM, the checker reports WSL commands must be run from elevated PowerShell.
- Current bridge and plugin validation: `.\.venv\Scripts\python.exe -m pytest` passes 13 tests. `.\.venv\Scripts\ruff.exe check bridge qgis_plugin tests` reports `All checks passed!` with only cache-write warnings caused by this restricted workspace. `.\.venv\Scripts\python.exe -m bridge.main --help` prints command-line options. A runtime smoke test started `bridge.main` on HTTP port 8766 and `GET /api/status` returned well-formed JSON with `connected: false`. A QGIS Python import check imported the plugin modules successfully after adding QGIS DLL directories, QGIS Python paths, and `QGIS_PREFIX_PATH` explicitly for the shell. A headless `QgsApplication` smoke test created an `ArduBoat Live` layer with one feature and fields `name`, `mode`, `heading_deg`, and `ground_speed_m_s`. A headless Qt smoke test constructed the `ArduBoat Control` dock with no bridge running and confirmed both target-send buttons were disabled.
- Current WSL/SITL validation: `wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/check_wsl_sitl.sh` reports ArduPilot commit `845b9b3c86`, Python MAVLink tooling ok, and MAVProxy 1.8.74. `wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/build_sitl_rover_wsl.sh` builds `bin/ardurover` successfully.

Manual SITL acceptance:

- Mission Planner and the bridge can both receive telemetry from the same SITL session.
- QGIS displays a live boat marker and heading.
- QGIS status mode matches Mission Planner mode.
- Clicking the QGIS map shows WGS84 coordinates and distance/bearing.
- Mode buttons work in SITL and are reflected in Mission Planner.
- Guided target command moves Rover SITL toward the selected point.

Safety acceptance:

- With SITL stopped, command buttons are disabled or API commands return HTTP 409 with a clear reason.
- With no selected target, `Send target` is disabled.
- If target distance exceeds the configured threshold, the plugin requires confirmation.
- There is no arming/disarming, parameter writing, joystick, or RC override code in the plugin.

## Idempotence and Recovery

All setup scripts must be safe to rerun. They should check before installing. If a tool installation fails, print the direct manual installation path and continue checking the rest of the environment.

The QGIS plugin should be loadable from the repository path via `QGIS_PLUGINPATH` during development. It should also be copyable into the normal QGIS user plugin directory. If the plugin fails to load, the user can disable it from the QGIS Plugin Manager and continue using QGIS normally.

The bridge should exit cleanly on Ctrl+C. If UDP ports are already in use, print which port failed and suggest changing `--connect` or stopping the other process.

The SITL script should not delete an existing `~/ardupilot` clone. If the clone exists, update submodules rather than recloning. If dependencies fail, the script should point the user to rerun the ArduPilot prerequisite script manually inside WSL.

For real boat testing, never test new QGIS command features first on water. Validate in SITL, then on the bench with props/thrusters safe, then at low speed with Mission Planner and manual control ready.

## Artifacts and Notes

Expected deliverables after implementation:

- `scripts/bootstrap_windows.ps1`
- `scripts/bootstrap_wsl_user.sh`
- `scripts/bootstrap_wsl_ardupilot.sh`
- `scripts/build_sitl_rover_wsl.sh`
- `scripts/check_wsl_sitl.sh`
- `scripts/run_sitl_rover_wsl.sh`
- `scripts/run_bridge.ps1`
- `scripts/run_qgis_plugin_dev.ps1`
- `bridge/` Python package
- `qgis_plugin/qgis_arduboat/` QGIS plugin
- `tests/` automated tests
- `docs/windows_setup.md`
- `docs/sitl_test_workflow.md`
- `docs/real_boat_workflow.md`

Useful command summary for the final README:

    # Windows PowerShell, repository root
    .\scripts\bootstrap_windows.ps1 -CheckOnly
    .\scripts\bootstrap_windows.ps1 -CreateVenv
    .\.venv\Scripts\python.exe -m pytest
    .\.venv\Scripts\python.exe -m bridge.main --connect udpin:0.0.0.0:14551
    .\scripts\run_qgis_plugin_dev.ps1

    # WSL Ubuntu 22.04 on this VM; use elevated PowerShell if normal wsl.exe returns Access is denied
    wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/check_wsl_sitl.sh
    wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/qgisarduboat/scripts/build_sitl_rover_wsl.sh
    wsl.exe -d Ubuntu-22.04 -- bash -lc 'cd /mnt/c/qgisarduboat && bash scripts/run_sitl_rover_wsl.sh'
