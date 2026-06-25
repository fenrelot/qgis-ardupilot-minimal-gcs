from __future__ import annotations

import threading
from typing import Any

from pymavlink import mavutil

from bridge.commands import send_guided_target, send_mode
from bridge.config import BridgeConfig
from bridge.state import VehicleState


class MavlinkClient:
    def __init__(self, config: BridgeConfig, state: VehicleState) -> None:
        self.config = config
        self.state = state
        self._master: Any = None
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._send_lock = threading.Lock()

    def start(self) -> None:
        self._master = mavutil.mavlink_connection(
            self.config.connect,
            source_system=self.config.source_system,
        )
        self._reader_thread = threading.Thread(
            target=self._read_loop,
            name="mavlink-reader",
            daemon=True,
        )
        self._reader_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        if self._master is not None:
            close = getattr(self._master, "close", None)
            if callable(close):
                close()

    def set_mode(
        self,
        mode: str | None = None,
        mode_number: int | None = None,
    ) -> dict[str, Any]:
        with self._send_lock:
            return send_mode(self._master, self.state, mode=mode, mode_number=mode_number)

    def send_guided_target(
        self,
        lat: float,
        lon: float,
        set_guided: bool = True,
    ) -> dict[str, Any]:
        with self._send_lock:
            return send_guided_target(
                self._master,
                self.state,
                lat=lat,
                lon=lon,
                set_guided=set_guided,
            )

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                msg = self._master.recv_match(blocking=True, timeout=0.5)
            except Exception as exc:  # pragma: no cover - depends on live transports
                self.state.set_warning(f"MAVLink read error: {exc}")
                continue

            if msg is None:
                continue
            try:
                self.state.update_from_message(msg)
                self.state.clear_warning()
            except Exception as exc:  # pragma: no cover - defensive for malformed input
                self.state.set_warning(f"MAVLink parse error: {exc}")

