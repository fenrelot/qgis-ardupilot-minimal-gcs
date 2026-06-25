from __future__ import annotations

import math
import threading
import time
from typing import Any

from pymavlink import mavutil

ROVER_MODE_NAMES = {
    0: "MANUAL",
    4: "HOLD",
    5: "LOITER",
    10: "AUTO",
    15: "GUIDED",
}


class VehicleState:
    def __init__(
        self,
        heartbeat_timeout_s: float = 3.0,
        clock: Any = time.monotonic,
    ) -> None:
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self._clock = clock
        self._lock = threading.RLock()
        self._last_heartbeat_monotonic: float | None = None
        self._target_system: int | None = None
        self._target_component: int | None = None
        self._mode: str | None = None
        self._mode_number: int | None = None
        self._armed = False
        self._lat: float | None = None
        self._lon: float | None = None
        self._heading_deg: float | None = None
        self._ground_speed_m_s: float | None = None
        self._gps_fix_type: int | None = None
        self._satellites_visible: int | None = None
        self._battery_voltage_v: float | None = None
        self._last_statustext = ""
        self._last_warning = ""

    def update_from_message(self, msg: Any) -> None:
        message_type = msg.get_type()
        with self._lock:
            if message_type == "HEARTBEAT":
                self._update_heartbeat(msg)
            elif message_type == "GLOBAL_POSITION_INT":
                self._update_global_position_int(msg)
            elif message_type == "GPS_RAW_INT":
                self._gps_fix_type = _optional_int(getattr(msg, "fix_type", None))
                self._satellites_visible = _optional_int(
                    getattr(msg, "satellites_visible", None)
                )
            elif message_type == "VFR_HUD":
                self._update_vfr_hud(msg)
            elif message_type == "ATTITUDE":
                self._update_attitude(msg)
            elif message_type == "SYS_STATUS":
                voltage = _millivolts_to_volts(getattr(msg, "voltage_battery", None))
                if voltage is not None:
                    self._battery_voltage_v = voltage
            elif message_type == "BATTERY_STATUS":
                voltage = _battery_status_voltage(getattr(msg, "voltages", None))
                if voltage is not None:
                    self._battery_voltage_v = voltage
            elif message_type == "STATUSTEXT":
                self._last_statustext = _clean_text(getattr(msg, "text", ""))

    def set_warning(self, warning: str) -> None:
        with self._lock:
            self._last_warning = warning

    def clear_warning(self) -> None:
        with self._lock:
            self._last_warning = ""

    def command_target(self) -> tuple[bool, str, int | None, int | None]:
        with self._lock:
            age = self._heartbeat_age_unlocked()
            if age is None:
                return False, "no heartbeat received", None, None
            if age > self.heartbeat_timeout_s:
                return False, f"heartbeat stale ({age:.1f}s old)", None, None
            if self._target_system is None or self._target_component is None:
                return False, "target system/component unknown", None, None
            return True, "ready", self._target_system, self._target_component

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            age = self._heartbeat_age_unlocked()
            connected = age is not None and age <= self.heartbeat_timeout_s
            return {
                "connected": connected,
                "last_heartbeat_age_s": _rounded(age),
                "target_system": self._target_system,
                "target_component": self._target_component,
                "mode": self._mode,
                "mode_number": self._mode_number,
                "armed": self._armed,
                "lat": self._lat,
                "lon": self._lon,
                "heading_deg": _rounded(self._heading_deg),
                "ground_speed_m_s": _rounded(self._ground_speed_m_s),
                "gps_fix_type": self._gps_fix_type,
                "satellites_visible": self._satellites_visible,
                "battery_voltage_v": _rounded(self._battery_voltage_v),
                "last_statustext": self._last_statustext,
                "last_warning": self._last_warning,
            }

    def _update_heartbeat(self, msg: Any) -> None:
        self._last_heartbeat_monotonic = self._clock()
        self._target_system = _source_value(msg, "get_srcSystem")
        self._target_component = _source_value(msg, "get_srcComponent")
        self._mode_number = _optional_int(getattr(msg, "custom_mode", None))
        self._mode = ROVER_MODE_NAMES.get(self._mode_number, str(self._mode_number))
        base_mode = int(getattr(msg, "base_mode", 0) or 0)
        self._armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

    def _update_global_position_int(self, msg: Any) -> None:
        lat = _scaled_degrees(getattr(msg, "lat", None), limit=90.0)
        lon = _scaled_degrees(getattr(msg, "lon", None), limit=180.0)
        if lat is not None:
            self._lat = lat
        if lon is not None:
            self._lon = lon

        hdg = _optional_int(getattr(msg, "hdg", None))
        if hdg is not None and hdg != 65535:
            self._heading_deg = _normalize_degrees(hdg / 100.0)

        vx = _optional_float(getattr(msg, "vx", None))
        vy = _optional_float(getattr(msg, "vy", None))
        if vx is not None and vy is not None:
            self._ground_speed_m_s = math.hypot(vx, vy) / 100.0

    def _update_vfr_hud(self, msg: Any) -> None:
        heading = _optional_float(getattr(msg, "heading", None))
        if heading is not None:
            self._heading_deg = _normalize_degrees(heading)
        ground_speed = _optional_float(getattr(msg, "groundspeed", None))
        if ground_speed is not None:
            self._ground_speed_m_s = ground_speed

    def _update_attitude(self, msg: Any) -> None:
        yaw = _optional_float(getattr(msg, "yaw", None))
        if yaw is not None:
            self._heading_deg = _normalize_degrees(math.degrees(yaw))

    def _heartbeat_age_unlocked(self) -> float | None:
        if self._last_heartbeat_monotonic is None:
            return None
        return max(0.0, self._clock() - self._last_heartbeat_monotonic)


def _source_value(msg: Any, method_name: str) -> int | None:
    method = getattr(msg, method_name, None)
    if not callable(method):
        return None
    return _optional_int(method())


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scaled_degrees(value: Any, limit: float) -> float | None:
    raw = _optional_float(value)
    if raw is None:
        return None
    degrees = raw / 10_000_000.0
    if abs(degrees) > limit:
        return None
    return degrees


def _normalize_degrees(value: float) -> float:
    return value % 360.0


def _millivolts_to_volts(value: Any) -> float | None:
    millivolts = _optional_float(value)
    if millivolts is None or millivolts <= 0 or millivolts >= 65535:
        return None
    return millivolts / 1000.0


def _battery_status_voltage(voltages: Any) -> float | None:
    if not voltages:
        return None
    valid = [
        float(cell)
        for cell in voltages
        if _optional_float(cell) is not None and 0 < float(cell) < 65535
    ]
    if not valid:
        return None
    return sum(valid) / 1000.0


def _clean_text(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return str(value).rstrip("\x00").strip()


def _rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)

