# QGIS ArduBoat Operator Map

Auxiliary QGIS operator map and light command panel for ArduPilot Rover/Boat systems while a normal ground-control station remains open.

Early alpha state.

Current Windows development baseline:

- Mission Planner 1.3.83
- QGIS LTR 3.44
- Python 3.10 or newer
- MAVProxy 1.8.74
- pymavlink >2.4

Current field deployment target:

- Panasonic Toughbook running Windows 11
- QGIS LTR
- Blue Robotics BlueBoat / BlueOS
- BlueOS MAVLink UDP endpoint to the local bridge on `udp://192.168.2.1:14552`

Start with:

- `docs/operator_quickstart.md`
- `docs/toughbook_blueboat_deployment.md`
- `docs/real_boat_workflow.md`

Useful commands from the repository root:

    .\scripts\bootstrap_windows.ps1 -CheckOnly
    .\scripts\install_qgis_plugin.ps1
    .\scripts\check_blueboat_network.ps1
    .\scripts\run_blueboat_bridge.ps1
