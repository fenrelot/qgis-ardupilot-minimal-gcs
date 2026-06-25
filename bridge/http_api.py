from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bridge.state import VehicleState


def make_server(
    host: str,
    port: int,
    state: VehicleState,
    command_client: Any,
) -> ThreadingHTTPServer:
    handler = _make_handler(state, command_client)
    return ThreadingHTTPServer((host, port), handler)


def _make_handler(state: VehicleState, command_client: Any) -> type[BaseHTTPRequestHandler]:
    class BridgeRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/api/status":
                self._send_json(HTTPStatus.OK, state.snapshot())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path == "/api/mode":
                body = self._read_json_body()
                if body is None:
                    return
                result = command_client.set_mode(
                    mode=body.get("mode"),
                    mode_number=body.get("mode_number"),
                )
                self._send_command_result(result)
                return

            if self.path == "/api/guided_target":
                body = self._read_json_body()
                if body is None:
                    return
                result = command_client.send_guided_target(
                    lat=body.get("lat"),
                    lon=body.get("lon"),
                    set_guided=bool(body.get("set_guided", True)),
                )
                self._send_command_result(result)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _read_json_body(self) -> dict[str, Any] | None:
            content_length = self.headers.get("Content-Length", "0")
            try:
                length = int(content_length)
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid Content-Length"})
                return None

            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid JSON: {exc}"})
                return None

            if not isinstance(body, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON body must be an object"})
                return None
            return body

        def _send_command_result(self, result: dict[str, Any]) -> None:
            status = (
                HTTPStatus.OK
                if result.get("accepted_to_send")
                else HTTPStatus.CONFLICT
            )
            self._send_json(status, result)

        def _send_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            payload = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return BridgeRequestHandler

