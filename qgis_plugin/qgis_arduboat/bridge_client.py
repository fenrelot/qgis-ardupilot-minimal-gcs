from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class BridgeClientError(RuntimeError):
    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload


class BridgeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", timeout_s: float = 1.0):
        self.base_url = _normalize_base_url(base_url)
        self.timeout_s = timeout_s

    def set_base_url(self, base_url: str) -> None:
        self.base_url = _normalize_base_url(base_url)

    def get_status(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/status")

    def set_mode(self, mode: str | None = None, mode_number: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if mode is not None:
            body["mode"] = mode
        if mode_number is not None:
            body["mode_number"] = mode_number
        return self._request_json("POST", "/api/mode", body, accepted_statuses={200, 409})

    def send_guided_target(
        self,
        lat: float,
        lon: float,
        set_guided: bool = True,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/guided_target",
            {"lat": lat, "lon": lon, "set_guided": set_guided},
            accepted_statuses={200, 409},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        accepted_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        if accepted_statuses is None:
            accepted_statuses = {200}
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in accepted_statuses:
                return _decode_json_object(detail)
            error_payload = _decode_json_object_or_none(detail)
            raise BridgeClientError(
                f"HTTP {exc.code}: {detail}",
                payload=error_payload,
            ) from exc
        except urllib.error.URLError as exc:
            raise BridgeClientError(str(exc.reason)) from exc
        except TimeoutError as exc:
            raise BridgeClientError("request timed out") from exc

        return _decode_json_object(payload)


def _decode_json_object(payload: str) -> dict[str, Any]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise BridgeClientError(f"invalid JSON response: {exc}") from exc
    if not isinstance(decoded, dict):
        raise BridgeClientError("JSON response was not an object")
    return decoded


def _decode_json_object_or_none(payload: str) -> dict[str, Any] | None:
    try:
        return _decode_json_object(payload)
    except BridgeClientError:
        return None


def _normalize_base_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        raise BridgeClientError("bridge URL is empty")
    return cleaned
