from __future__ import annotations

import time
from typing import Any

from pymavlink import mavutil

from bridge.state import ROVER_MODE_NAMES, VehicleState

ROVER_MODES = {name: number for number, name in ROVER_MODE_NAMES.items()}
GUIDED_TARGET_TYPE_MASK = 3580


def resolve_mode(mode: str | None = None, mode_number: int | None = None) -> int:
    if mode_number is not None:
        number = int(mode_number)
        if number not in ROVER_MODE_NAMES:
            raise ValueError(f"unsupported Rover mode number: {number}")
        return number
    if not mode:
        raise ValueError("mode or mode_number is required")
    name = str(mode).strip().upper()
    if name not in ROVER_MODES:
        raise ValueError(f"unsupported Rover mode: {mode}")
    return ROVER_MODES[name]


def send_mode(
    master: Any,
    state: VehicleState,
    mode: str | None = None,
    mode_number: int | None = None,
) -> dict[str, Any]:
    try:
        number = resolve_mode(mode=mode, mode_number=mode_number)
    except ValueError as exc:
        return _result(False, str(exc), state)

    ready, reason, target_system, target_component = state.command_target()
    if not ready:
        return _result(False, reason, state)
    if master is None:
        return _result(False, "MAVLink connection is not open", state)

    _send_mode_number(master, target_system, target_component, number)
    return _result(True, "mode command sent", state, requested_mode=ROVER_MODE_NAMES[number])


def send_guided_target(
    master: Any,
    state: VehicleState,
    lat: float,
    lon: float,
    set_guided: bool = True,
) -> dict[str, Any]:
    try:
        lat_float, lon_float = _validate_lat_lon(lat, lon)
    except ValueError as exc:
        return _result(False, str(exc), state)

    ready, reason, target_system, target_component = state.command_target()
    if not ready:
        return _result(False, reason, state)
    if master is None:
        return _result(False, "MAVLink connection is not open", state)

    if set_guided:
        _send_mode_number(master, target_system, target_component, ROVER_MODES["GUIDED"])

    master.mav.set_position_target_global_int_send(
        int(time.monotonic() * 1000) & 0xFFFFFFFF,
        target_system,
        target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        GUIDED_TARGET_TYPE_MASK,
        int(round(lat_float * 10_000_000)),
        int(round(lon_float * 10_000_000)),
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    return _result(True, "guided target command sent", state)


def _send_mode_number(
    master: Any,
    target_system: int,
    target_component: int,
    mode_number: int,
) -> None:
    master.mav.command_long_send(
        target_system,
        target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_number,
        0,
        0,
        0,
        0,
        0,
    )


def _validate_lat_lon(lat: float, lon: float) -> tuple[float, float]:
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (TypeError, ValueError) as exc:
        raise ValueError("lat and lon must be numeric") from exc

    if not -90.0 <= lat_float <= 90.0:
        raise ValueError("lat must be between -90 and 90")
    if not -180.0 <= lon_float <= 180.0:
        raise ValueError("lon must be between -180 and 180")
    return lat_float, lon_float


def _result(
    accepted: bool,
    reason: str,
    state: VehicleState,
    requested_mode: str | None = None,
) -> dict[str, Any]:
    status = state.snapshot()
    result = {
        "accepted_to_send": accepted,
        "reason": reason,
        "mode": status["mode"],
        "mode_number": status["mode_number"],
    }
    if requested_mode is not None:
        result["requested_mode"] = requested_mode
    return result

