import math

from pymavlink import mavutil

from bridge.state import VehicleState


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class FakeMsg:
    def __init__(
        self,
        message_type: str,
        source_system: int = 1,
        source_component: int = 1,
        **fields,
    ) -> None:
        self._message_type = message_type
        self._source_system = source_system
        self._source_component = source_component
        for name, value in fields.items():
            setattr(self, name, value)

    def get_type(self) -> str:
        return self._message_type

    def get_srcSystem(self) -> int:
        return self._source_system

    def get_srcComponent(self) -> int:
        return self._source_component


def test_status_snapshot_converts_common_mavlink_units() -> None:
    clock = FakeClock()
    state = VehicleState(clock=clock)

    state.update_from_message(
        FakeMsg(
            "HEARTBEAT",
            custom_mode=0,
            base_mode=mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED,
        )
    )
    state.update_from_message(
        FakeMsg(
            "GLOBAL_POSITION_INT",
            lat=482082000,
            lon=163738000,
            hdg=9120,
            vx=300,
            vy=400,
        )
    )
    state.update_from_message(
        FakeMsg("GPS_RAW_INT", fix_type=3, satellites_visible=15)
    )
    state.update_from_message(FakeMsg("SYS_STATUS", voltage_battery=15600))
    state.update_from_message(FakeMsg("STATUSTEXT", text=b"Ready\x00\x00"))

    status = state.snapshot()

    assert status["connected"] is True
    assert status["target_system"] == 1
    assert status["target_component"] == 1
    assert status["mode"] == "MANUAL"
    assert status["mode_number"] == 0
    assert status["armed"] is True
    assert status["lat"] == 48.2082
    assert status["lon"] == 16.3738
    assert status["heading_deg"] == 91.2
    assert status["ground_speed_m_s"] == 5.0
    assert status["gps_fix_type"] == 3
    assert status["satellites_visible"] == 15
    assert status["battery_voltage_v"] == 15.6
    assert status["last_statustext"] == "Ready"


def test_attitude_yaw_is_normalized_to_degrees() -> None:
    state = VehicleState()

    state.update_from_message(FakeMsg("ATTITUDE", yaw=-math.pi / 2))

    assert state.snapshot()["heading_deg"] == 270.0


def test_heartbeat_goes_stale_after_timeout() -> None:
    clock = FakeClock()
    state = VehicleState(clock=clock, heartbeat_timeout_s=3.0)

    state.update_from_message(FakeMsg("HEARTBEAT", custom_mode=15, base_mode=0))
    clock.now += 3.5

    status = state.snapshot()
    assert status["connected"] is False
    assert status["last_heartbeat_age_s"] == 3.5

