import json
import threading
import urllib.error
import urllib.request

from bridge.http_api import make_server
from bridge.state import VehicleState


class FakeCommandClient:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted
        self.mode_calls = []
        self.target_calls = []

    def set_mode(self, mode=None, mode_number=None):
        self.mode_calls.append((mode, mode_number))
        return {
            "accepted_to_send": self.accepted,
            "reason": "ok" if self.accepted else "no heartbeat received",
            "mode": None,
            "mode_number": None,
        }

    def send_guided_target(self, lat, lon, set_guided=True):
        self.target_calls.append((lat, lon, set_guided))
        return {
            "accepted_to_send": self.accepted,
            "reason": "ok" if self.accepted else "no heartbeat received",
            "mode": None,
            "mode_number": None,
        }


def test_status_endpoint_returns_json_when_disconnected() -> None:
    with running_server(VehicleState(), FakeCommandClient()) as base_url:
        with urllib.request.urlopen(f"{base_url}/api/status", timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))

    assert body["connected"] is False
    assert body["target_system"] is None


def test_mode_endpoint_returns_conflict_when_command_is_refused() -> None:
    fake_client = FakeCommandClient(accepted=False)
    with running_server(VehicleState(), fake_client) as base_url:
        request = urllib.request.Request(
            f"{base_url}/api/mode",
            data=json.dumps({"mode": "GUIDED"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            raise AssertionError("expected HTTP 409")
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            status = exc.code

    assert status == 409
    assert body["accepted_to_send"] is False
    assert fake_client.mode_calls == [("GUIDED", None)]


class running_server:
    def __init__(self, state: VehicleState, client: FakeCommandClient) -> None:
        self.server = make_server("127.0.0.1", 0, state, client)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
