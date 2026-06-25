from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin, sqrt
from typing import Any

EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class TargetMetrics:
    distance_m: float | None
    bearing_deg: float | None


def target_metrics(
    status: dict[str, Any],
    target_lat: float,
    target_lon: float,
) -> TargetMetrics:
    boat_lat = _as_float(status.get("lat"))
    boat_lon = _as_float(status.get("lon"))
    if boat_lat is None or boat_lon is None:
        return TargetMetrics(distance_m=None, bearing_deg=None)

    return TargetMetrics(
        distance_m=distance_m(boat_lat, boat_lon, target_lat, target_lon),
        bearing_deg=bearing_deg(boat_lat, boat_lon, target_lat, target_lon),
    )


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = (
        sin(delta_phi / 2.0) * sin(delta_phi / 2.0)
        + cos(phi1) * cos(phi2) * sin(delta_lambda / 2.0) * sin(delta_lambda / 2.0)
    )
    return EARTH_RADIUS_M * 2.0 * atan2(sqrt(a), sqrt(1.0 - a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_lambda = radians(lon2 - lon1)

    y = sin(delta_lambda) * cos(phi2)
    x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(delta_lambda)
    return (degrees(atan2(y, x)) + 360.0) % 360.0


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
