from datetime import datetime, timezone
from io import StringIO

from qgis_plugin.qgis_arduboat.track_log import TrackTextLogger, sample_from_status


def test_sample_from_status_requires_connected_position() -> None:
    assert sample_from_status({"connected": False, "lat": 48.0, "lon": 16.0}) is None
    assert sample_from_status({"connected": True, "lat": None, "lon": 16.0}) is None


def test_sample_from_status_formats_timestamp_and_values() -> None:
    sample = sample_from_status(
        {
            "connected": True,
            "lat": "48.2082",
            "lon": "16.3738",
            "heading_deg": "91.2",
            "ground_speed_m_s": "1.5",
            "mode": "GUIDED",
        },
        timestamp=datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc),
    )

    assert sample is not None
    assert sample.timestamp_utc == "2026-06-25T08:00:00Z"
    assert sample.csv_row() == [
        "2026-06-25T08:00:00Z",
        "48.20820000",
        "16.37380000",
        "91.200",
        "1.500",
        "GUIDED",
    ]


def test_track_text_logger_writes_header_and_appends() -> None:
    sample = sample_from_status(
        {
            "connected": True,
            "lat": 48.2082,
            "lon": 16.3738,
            "heading_deg": 91.2,
            "ground_speed_m_s": 1.5,
            "mode": "GUIDED",
        },
        timestamp=datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc),
    )
    assert sample is not None

    stream = StringIO()
    logger = TrackTextLogger()
    logger.start_stream(stream)
    logger.append(sample)

    assert stream.getvalue().splitlines() == [
        "timestamp_utc,lat,lon,heading_deg,ground_speed_m_s,mode",
        "2026-06-25T08:00:00Z,48.20820000,16.37380000,91.200,1.500,GUIDED",
    ]
