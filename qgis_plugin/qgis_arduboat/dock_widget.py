from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .bridge_client import BridgeClient, BridgeClientError
from .live_layer import LiveBoatLayer
from .map_tools import SelectedTarget, TargetMapTool
from .targeting import target_metrics
from .track_layer import TrackExportError, TrackLayer, format_track_export_path
from .track_log import TrackTextLogger, sample_from_status

TARGET_CONFIRM_DISTANCE_M = 1000.0
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = REPO_ROOT / "logs"


class ArduBoatDockWidget(QDockWidget):
    def __init__(self, parent=None, iface=None) -> None:
        super().__init__("ArduBoat Control", parent)
        self.iface = iface
        self.client = BridgeClient()
        self.live_layer = LiveBoatLayer()
        self.track_layer = TrackLayer()
        self.track_logger = TrackTextLogger()
        self.map_tool: TargetMapTool | None = None
        self.selected_target: SelectedTarget | None = None
        self.last_status: dict[str, Any] = {"connected": False}
        self._target_distance_m: float | None = None
        self._labels: dict[str, QLabel] = {}
        self._target_labels: dict[str, QLabel] = {}
        self._command_buttons: list[QPushButton] = []

        self._build_ui()
        self._update_button_states()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.poll_status)
        self.timer.start()
        self.poll_status()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.track_logger.stop()
        self._deactivate_map_tool()
        super().closeEvent(event)

    def poll_status(self) -> None:
        try:
            status = self.client.get_status()
        except BridgeClientError as exc:
            self._set_status_error(str(exc), exc.payload)
            return

        self.last_status = status
        self._update_status_fields(status)
        self._update_target_fields()
        self._update_button_states()
        self.raw_status.setPlainText(json.dumps(status, indent=2, sort_keys=True))
        self.live_layer.update_from_status(status)
        self._capture_track_sample(status)
        if self.iface is not None:
            canvas = self.iface.mapCanvas()
            if canvas is not None:
                canvas.refresh()

    def activate_pick_tool(self) -> None:
        if self.iface is None or self.iface.mapCanvas() is None:
            self.last_warning.setText("QGIS map canvas is not available")
            return
        canvas = self.iface.mapCanvas()
        if self.map_tool is None:
            self.map_tool = TargetMapTool(canvas, self.set_target, self.iface)
        canvas.setMapTool(self.map_tool)
        self.last_warning.setText("Target picker active")

    def set_target(self, target: SelectedTarget) -> None:
        self.selected_target = target
        self._update_target_fields()
        self._update_button_states()
        source = target.source
        if target.layer_name:
            source = f"{source}: {target.layer_name}"
        self.last_warning.setText(f"Target selected from {source}")

    def clear_target(self) -> None:
        self.selected_target = None
        self._target_distance_m = None
        if self.map_tool is not None:
            self.map_tool.clear_marker()
        self._update_target_fields()
        self._update_button_states()
        self.last_warning.setText("Target cleared")

    def _build_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit(self.client.base_url)
        self.url_edit.setToolTip("Bridge base URL")
        apply_url = QPushButton("Apply")
        apply_url.clicked.connect(self._apply_bridge_url)
        url_row.addWidget(QLabel("Bridge"))
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(apply_url)
        layout.addLayout(url_row)

        layout.addWidget(self._build_status_group())
        layout.addWidget(self._build_track_group())
        layout.addWidget(self._build_target_group())
        layout.addWidget(self._build_command_group())

        form = QFormLayout()
        self.last_warning = QLabel("")
        self.last_warning.setWordWrap(True)
        form.addRow("Warning", self.last_warning)
        self.command_result = QLabel("")
        self.command_result.setWordWrap(True)
        form.addRow("Command", self.command_result)
        layout.addLayout(form)

        self.raw_status = QPlainTextEdit()
        self.raw_status.setReadOnly(True)
        self.raw_status.setMinimumHeight(150)
        layout.addWidget(QLabel("Raw status"))
        layout.addWidget(self.raw_status, 1)

        self.setWidget(container)

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("Status")
        status_grid = QGridLayout(group)
        fields = [
            ("connected", "Connected"),
            ("mode", "Mode"),
            ("armed", "Armed"),
            ("lat", "Latitude"),
            ("lon", "Longitude"),
            ("heading_deg", "Heading"),
            ("ground_speed_m_s", "Ground speed"),
            ("gps", "GPS"),
            ("battery_voltage_v", "Battery"),
            ("last_statustext", "Status text"),
        ]
        for row, (key, title) in enumerate(fields):
            status_grid.addWidget(QLabel(title), row, 0)
            value = QLabel("")
            value.setTextInteractionFlags(value.textInteractionFlags())
            status_grid.addWidget(value, row, 1)
            self._labels[key] = value
        return group

    def _build_track_group(self) -> QGroupBox:
        group = QGroupBox("Track")
        layout = QVBoxLayout(group)

        save_row = QHBoxLayout()
        self.track_format_combo = QComboBox()
        self.track_format_combo.addItem("GeoPackage (.gpkg)", "GPKG")
        self.track_format_combo.addItem("ESRI Shapefile (.shp)", "ESRI Shapefile")
        self.save_track_button = QPushButton("Save track as...")
        self.save_track_button.clicked.connect(self._save_track)
        self.clear_track_button = QPushButton("Clear track")
        self.clear_track_button.clicked.connect(self._clear_track)
        save_row.addWidget(self.track_format_combo, 1)
        save_row.addWidget(self.save_track_button)
        save_row.addWidget(self.clear_track_button)
        layout.addLayout(save_row)

        log_row = QHBoxLayout()
        self.text_log_button = QPushButton("Start text log")
        self.text_log_button.setCheckable(True)
        self.text_log_button.toggled.connect(self._toggle_text_log)
        log_row.addWidget(self.text_log_button)
        layout.addLayout(log_row)

        form = QFormLayout()
        self.track_count_label = QLabel("0")
        form.addRow("Samples", self.track_count_label)
        self.text_log_status = QLabel("off")
        self.text_log_status.setWordWrap(True)
        form.addRow("Text log", self.text_log_status)
        layout.addLayout(form)

        self._update_track_fields()
        return group

    def _build_target_group(self) -> QGroupBox:
        group = QGroupBox("Target")
        layout = QVBoxLayout(group)

        button_row = QHBoxLayout()
        self.pick_target_button = QPushButton("Pick target")
        self.pick_target_button.clicked.connect(self.activate_pick_tool)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_target)
        button_row.addWidget(self.pick_target_button)
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

        target_grid = QGridLayout()
        fields = [
            ("source", "Source"),
            ("lat", "WGS84 lat"),
            ("lon", "WGS84 lon"),
            ("project_x", "Project X"),
            ("project_y", "Project Y"),
            ("distance", "Distance"),
            ("bearing", "Bearing"),
        ]
        for row, (key, title) in enumerate(fields):
            target_grid.addWidget(QLabel(title), row, 0)
            value = QLabel("-")
            value.setTextInteractionFlags(value.textInteractionFlags())
            target_grid.addWidget(value, row, 1)
            self._target_labels[key] = value
        layout.addLayout(target_grid)
        return group

    def _build_command_group(self) -> QGroupBox:
        group = QGroupBox("Commands")
        layout = QGridLayout(group)

        self.send_target_button = QPushButton("Send target")
        self.send_target_button.setToolTip("Requires current mode GUIDED")
        self.send_target_button.clicked.connect(partial(self._send_selected_target, False))
        self.send_target_guided_button = QPushButton("Send target + GUIDED")
        self.send_target_guided_button.clicked.connect(
            partial(self._send_selected_target, True)
        )
        layout.addWidget(self.send_target_button, 0, 0)
        layout.addWidget(self.send_target_guided_button, 0, 1)
        self._command_buttons.extend(
            [self.send_target_button, self.send_target_guided_button]
        )

        mode_buttons = [
            ("Start mission AUTO", "AUTO"),
            ("GUIDED", "GUIDED"),
            ("LOITER", "LOITER"),
            ("HOLD / STOP", "HOLD"),
            ("MANUAL", "MANUAL"),
        ]
        for index, (title, mode) in enumerate(mode_buttons, start=2):
            button = QPushButton(title)
            button.clicked.connect(partial(self._send_mode, mode))
            row = index // 2
            column = index % 2
            layout.addWidget(button, row, column)
            self._command_buttons.append(button)
        return group

    def _apply_bridge_url(self) -> None:
        try:
            self.client.set_base_url(self.url_edit.text())
        except BridgeClientError as exc:
            self._set_status_error(str(exc), exc.payload)
            return
        self.poll_status()

    def _set_status_error(
        self,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.last_status = {
            "connected": False,
            "last_warning": message,
        }
        self._labels["connected"].setText("false")
        self.last_warning.setText(message)
        self._update_target_fields()
        self._update_button_states()
        self.raw_status.setPlainText(
            json.dumps(
                payload
                or {
                    "connected": False,
                    "last_warning": message,
                },
                indent=2,
                sort_keys=True,
            )
        )

    def _update_status_fields(self, status: dict[str, Any]) -> None:
        self._labels["connected"].setText(str(bool(status.get("connected"))).lower())
        self._labels["mode"].setText(_display(status.get("mode")))
        self._labels["armed"].setText(str(bool(status.get("armed"))).lower())
        self._labels["lat"].setText(_display_float(status.get("lat"), 7))
        self._labels["lon"].setText(_display_float(status.get("lon"), 7))
        self._labels["heading_deg"].setText(_display_float(status.get("heading_deg"), 1))
        self._labels["ground_speed_m_s"].setText(
            _display_float(status.get("ground_speed_m_s"), 2)
        )
        fix = _display(status.get("gps_fix_type"))
        sats = _display(status.get("satellites_visible"))
        self._labels["gps"].setText(f"fix {fix}, sats {sats}")
        self._labels["battery_voltage_v"].setText(
            _display_float(status.get("battery_voltage_v"), 2)
        )
        self._labels["last_statustext"].setText(_display(status.get("last_statustext")))
        self.last_warning.setText(_display(status.get("last_warning")))

    def _update_target_fields(self) -> None:
        target = self.selected_target
        if target is None:
            for label in self._target_labels.values():
                label.setText("-")
            self._target_distance_m = None
            return

        metrics = target_metrics(self.last_status, target.lat, target.lon)
        self._target_distance_m = metrics.distance_m
        source = target.source
        if target.layer_name:
            source = f"{source}: {target.layer_name}"
        self._target_labels["source"].setText(source)
        self._target_labels["lat"].setText(_display_float(target.lat, 7))
        self._target_labels["lon"].setText(_display_float(target.lon, 7))
        self._target_labels["project_x"].setText(_display_float(target.project_x, 3))
        self._target_labels["project_y"].setText(_display_float(target.project_y, 3))
        self._target_labels["distance"].setText(
            _display_measure(metrics.distance_m, "m", 1)
        )
        self._target_labels["bearing"].setText(
            _display_measure(metrics.bearing_deg, "deg", 1)
        )

    def _update_button_states(self) -> None:
        connected = bool(self.last_status.get("connected"))
        has_target = self.selected_target is not None
        for button in self._command_buttons:
            button.setEnabled(connected)
        self.send_target_button.setEnabled(connected and has_target)
        self.send_target_guided_button.setEnabled(connected and has_target)
        self._update_track_fields()

    def _capture_track_sample(self, status: dict[str, Any]) -> None:
        sample = sample_from_status(status)
        if sample is None:
            return
        try:
            self.track_layer.append_sample(sample)
        except Exception as exc:
            self.last_warning.setText(f"Track update failed: {exc}")
            return
        if self.track_logger.is_active:
            try:
                self.track_logger.append(sample)
            except OSError as exc:
                self.track_logger.stop()
                self.text_log_button.setChecked(False)
                self.last_warning.setText(f"Text log stopped: {exc}")
        self._update_track_fields()

    def _save_track(self) -> None:
        DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        driver_name = str(self.track_format_combo.currentData())
        if driver_name == "GPKG":
            file_filter = "GeoPackage (*.gpkg)"
            default_path = DEFAULT_LOG_DIR / "arduboat_track.gpkg"
        else:
            file_filter = "ESRI Shapefile (*.shp)"
            default_path = DEFAULT_LOG_DIR / "arduboat_track.shp"

        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save ArduBoat track",
            str(default_path),
            file_filter,
        )
        if not path:
            return
        path = format_track_export_path(path, driver_name)
        try:
            self.track_layer.export_to(path, driver_name)
        except TrackExportError as exc:
            self.last_warning.setText(f"Track save failed: {exc}")
            return
        self.last_warning.setText(f"Track saved: {path}")

    def _clear_track(self) -> None:
        self.track_layer.clear()
        self._update_track_fields()
        self.last_warning.setText("Track cleared")

    def _toggle_text_log(self, checked: bool) -> None:
        if checked:
            self._start_text_log()
        else:
            self._stop_text_log()

    def _start_text_log(self) -> None:
        DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        default_path = DEFAULT_LOG_DIR / "arduboat_location_log.csv"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Start text location log",
            str(default_path),
            "CSV text (*.csv);;Text files (*.txt);;All files (*.*)",
        )
        if not path:
            self.text_log_button.setChecked(False)
            return
        if "." not in Path(path).name:
            path = f"{path}.csv"
        try:
            self.track_logger.start(path)
        except OSError as exc:
            self.text_log_button.setChecked(False)
            self.last_warning.setText(f"Text log start failed: {exc}")
            return
        self.text_log_button.setText("Stop text log")
        self.text_log_status.setText(str(self.track_logger.path))
        self.last_warning.setText("Text location logging started")

    def _stop_text_log(self) -> None:
        was_active = self.track_logger.is_active
        self.track_logger.stop()
        self.text_log_button.setText("Start text log")
        self.text_log_status.setText("off")
        if was_active:
            self.last_warning.setText("Text location logging stopped")

    def _update_track_fields(self) -> None:
        count = self.track_layer.sample_count()
        self.track_count_label.setText(str(count))
        has_samples = count > 0
        self.save_track_button.setEnabled(has_samples)
        self.clear_track_button.setEnabled(has_samples)

    def _send_mode(self, mode: str) -> None:
        try:
            result = self.client.set_mode(mode=mode)
        except BridgeClientError as exc:
            self._show_command_error(exc)
            return
        self._show_command_result(result)
        self.poll_status()

    def _send_selected_target(self, set_guided: bool) -> None:
        target = self.selected_target
        if target is None:
            self.command_result.setText("rejected: no target selected")
            return
        if not set_guided and self._current_mode() != "GUIDED":
            self.command_result.setText(
                "rejected: current mode is not GUIDED; use Send target + GUIDED"
            )
            return
        if not self._confirm_distant_target():
            self.command_result.setText("cancelled: target distance confirmation declined")
            return

        try:
            result = self.client.send_guided_target(
                target.lat,
                target.lon,
                set_guided=set_guided,
            )
        except BridgeClientError as exc:
            self._show_command_error(exc)
            return
        self._show_command_result(result)
        self.poll_status()

    def _confirm_distant_target(self) -> bool:
        distance = self._target_distance_m
        if distance is None or distance <= TARGET_CONFIRM_DISTANCE_M:
            return True
        reply = QMessageBox.question(
            self,
            "Confirm target",
            f"Target is {distance:.0f} m from the current boat position. Send command?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _show_command_result(self, result: dict[str, Any]) -> None:
        accepted = bool(result.get("accepted_to_send"))
        state = "sent" if accepted else "rejected"
        reason = result.get("reason") or result.get("error") or "no reason returned"
        requested_mode = result.get("requested_mode")
        if requested_mode:
            self.command_result.setText(f"{state}: {reason} ({requested_mode})")
        else:
            self.command_result.setText(f"{state}: {reason}")

    def _show_command_error(self, exc: BridgeClientError) -> None:
        if exc.payload:
            self._show_command_result(exc.payload)
            return
        self.command_result.setText(f"error: {exc}")

    def _current_mode(self) -> str:
        return str(self.last_status.get("mode") or "").upper()

    def _deactivate_map_tool(self) -> None:
        if self.map_tool is None:
            return
        if self.iface is not None and self.iface.mapCanvas() is not None:
            canvas = self.iface.mapCanvas()
            if canvas.mapTool() == self.map_tool:
                try:
                    canvas.unsetMapTool(self.map_tool)
                except AttributeError:
                    pass
        self.map_tool.clear_marker()


def _display(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _display_float(value: Any, digits: int) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _display_measure(value: float | None, unit: str, digits: int) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f} {unit}"
