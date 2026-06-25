from pymavlink import mavutil

from bridge.commands import ROVER_MODES, resolve_mode, send_guided_target, send_mode
from bridge.state import VehicleState
from tests.test_state_parsing import FakeMsg


class FakeMav:
    def __init__(self) -> None:
        self.command_long_calls = []
        self.target_calls = []

    def command_long_send(self, *args) -> None:
        self.command_long_calls.append(args)

    def set_position_target_global_int_send(self, *args) -> None:
        self.target_calls.append(args)


class FakeMaster:
    def __init__(self) -> None:
        self.mav = FakeMav()


def fresh_state() -> VehicleState:
    state = VehicleState()
    state.update_from_message(FakeMsg("HEARTBEAT", custom_mode=0, base_mode=0))
    return state


def test_mode_resolution_accepts_names_and_numbers() -> None:
    assert resolve_mode(mode="guided") == ROVER_MODES["GUIDED"]
    assert resolve_mode(mode_number=10) == ROVER_MODES["AUTO"]


def test_mode_command_refuses_without_fresh_heartbeat() -> None:
    master = FakeMaster()
    state = VehicleState()

    result = send_mode(master, state, mode="GUIDED")

    assert result["accepted_to_send"] is False
    assert "heartbeat" in result["reason"]
    assert master.mav.command_long_calls == []


def test_mode_command_sends_command_long_when_ready() -> None:
    master = FakeMaster()
    state = fresh_state()

    result = send_mode(master, state, mode="GUIDED")

    assert result["accepted_to_send"] is True
    call = master.mav.command_long_calls[0]
    assert call[0] == 1
    assert call[1] == 1
    assert call[2] == mavutil.mavlink.MAV_CMD_DO_SET_MODE
    assert call[4] == mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    assert call[5] == ROVER_MODES["GUIDED"]


def test_guided_target_optionally_sets_guided_then_sends_target() -> None:
    master = FakeMaster()
    state = fresh_state()

    result = send_guided_target(
        master,
        state,
        lat=48.2082,
        lon=16.3738,
        set_guided=True,
    )

    assert result["accepted_to_send"] is True
    assert master.mav.command_long_calls[0][5] == ROVER_MODES["GUIDED"]
    target_call = master.mav.target_calls[0]
    assert target_call[1] == 1
    assert target_call[2] == 1
    assert target_call[3] == mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
    assert target_call[4] == 3580
    assert target_call[5] == 482082000
    assert target_call[6] == 163738000

