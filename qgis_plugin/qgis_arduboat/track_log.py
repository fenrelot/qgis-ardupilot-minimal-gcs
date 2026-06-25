from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


CSV_HEADER = [
    "timestamp_utc",
    "lat",
    "lon",
    "heading_deg",
    "ground_speed_m_s",
    "mode",
]


@dataclass(frozen=True)
class TrackSample:
    timestamp_utc: str
    lat: float
    lon: float
    heading_deg: float | None
    ground_speed_m_s: float | None
    mode: str

    def csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            f"{self.lat:.8f}",
            f"{self.lon:.8f}",
            _optional_float_text(self.heading_deg),
            _optional_float_text(self.ground_speed_m_s),
            self.mode,
        ]


class TrackTextLogger:
    def __init__(self) -> None:
        self.path: Path | None = None
        self._file: TextIO | None = None
        self._writer: csv.writer | None = None

    @property
    def is_active(self) -> bool:
        return self._file is not None

    def start(self, path: str | Path) -> None:
        self.stop()
        log_path = Path(path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not log_path.exists() or log_path.stat().st_size == 0
        stream = log_path.open("a", encoding="utf-8", newline="")
        self.start_stream(stream, path=log_path, write_header=needs_header)

    def start_stream(
        self,
        stream: TextIO,
        path: str | Path | None = None,
        write_header: bool = True,
    ) -> None:
        self.stop()
        self._file = stream
        self._writer = csv.writer(self._file)
        self.path = Path(path) if path is not None else None
        if write_header:
            self._writer.writerow(CSV_HEADER)
            self._file.flush()

    def append(self, sample: TrackSample) -> None:
        if self._file is None or self._writer is None:
            return
        self._writer.writerow(sample.csv_row())
        self._file.flush()

    def stop(self) -> None:
        if self._file is not None:
            self._file.close()
        self._file = None
        self._writer = None
        self.path = None


def sample_from_status(
    status: dict[str, Any],
    timestamp: datetime | None = None,
) -> TrackSample | None:
    if not status.get("connected"):
        return None
    lat = _as_float(status.get("lat"))
    lon = _as_float(status.get("lon"))
    if lat is None or lon is None:
        return None
    return TrackSample(
        timestamp_utc=_timestamp_text(timestamp),
        lat=lat,
        lon=lon,
        heading_deg=_as_float(status.get("heading_deg")),
        ground_speed_m_s=_as_float(status.get("ground_speed_m_s")),
        mode=str(status.get("mode") or ""),
    )


def _timestamp_text(timestamp: datetime | None) -> str:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc).replace(microsecond=0)
    return timestamp.isoformat().replace("+00:00", "Z")


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_float_text(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"
