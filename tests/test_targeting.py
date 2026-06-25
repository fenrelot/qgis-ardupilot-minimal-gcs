from qgis_plugin.qgis_arduboat.targeting import bearing_deg, distance_m, target_metrics


def test_target_distance_and_bearing_due_east() -> None:
    distance = distance_m(48.0, 16.0, 48.0, 16.01)
    bearing = bearing_deg(48.0, 16.0, 48.0, 16.01)

    assert 740.0 < distance < 750.0
    assert 89.0 < bearing < 91.0


def test_target_metrics_are_empty_without_boat_position() -> None:
    metrics = target_metrics({"connected": True, "lat": None, "lon": None}, 48.0, 16.0)

    assert metrics.distance_m is None
    assert metrics.bearing_deg is None
