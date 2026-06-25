import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from qgis_plugin.qgis_arduboat.bridge_client import BridgeClient


def test_qgis_bridge_client_reads_status_json() -> None:
    with running_json_server({"connected": False, "mode": None}) as base_url:
        status = BridgeClient(base_url=base_url).get_status()

    assert status == {"connected": False, "mode": None}


def test_qgis_bridge_client_returns_command_rejection_payload() -> None:
    payload = {
        "accepted_to_send": False,
        "reason": "heartbeat is stale",
        "mode": "MANUAL",
        "mode_number": 0,
    }
    with running_json_server(payload, post_status=409) as base_url:
        result = BridgeClient(base_url=base_url).set_mode(mode="GUIDED")

    assert result == payload


class running_json_server:
    def __init__(self, payload: dict, post_status: int = 200) -> None:
        self.payload = payload
        self.post_status = post_status
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _make_handler(self):
        payload = self.payload
        post_status = self.post_status

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/api/status":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path != "/api/mode":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(payload).encode("utf-8")
                self.send_response(post_status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *args):
                return

        return Handler
