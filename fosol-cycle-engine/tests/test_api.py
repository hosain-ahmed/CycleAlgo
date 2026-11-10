"""Tests for the thin HTTP API and local server (v1.md §14.3/§14.5)."""

import contextlib
import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from src.api import handle_explore
from src.error_contract import build_error_response
from src.request_validation import RequestValidationError
from src.server import MAX_BODY_BYTES, create_server

DATA_DIR = Path(__file__).resolve().parents[2] / "Data"
VALID_PAYLOAD = {
    "district_id": "rajshahi",
    "start_date": "2026-11-06",
    "first_crop_id": None,
    "water_access": "unknown",
    "preference": "fastest_completion",
}


def _fake_explore(payload, *, profiles=None, config=None, **kwargs):
    return {
        "schema_version": "1",
        "status": "ok",
        "request": payload,
        "config": config,
        "has_profiles": bool(profiles),
    }


@contextlib.contextmanager
def _running_server(explore_fn):
    server = create_server(
        "127.0.0.1", 0, data_dir=DATA_DIR, explore_fn=explore_fn
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _http(port, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        return (
            response.status,
            {name.lower(): value for name, value in response.getheaders()},
            data,
        )
    finally:
        connection.close()


def _json_body(payload):
    return json.dumps(payload).encode("utf-8")


class ApiHandlerTests(unittest.TestCase):
    def test_request_validation_error_is_400(self) -> None:
        """Spec §14.3 | Bug it catches: RequestValidationError becomes a 500 or loses its field."""
        def fake(payload, **kwargs):
            raise RequestValidationError("district_id is required.", "district_id")

        status, body = handle_explore({}, explore_fn=fake)
        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            build_error_response(
                RequestValidationError("district_id is required.", "district_id")
            ),
        )

    def test_unexpected_error_is_generic_500_without_secrets(self) -> None:
        """Spec §14.3 | Bug it catches: stack, token, or exception text leaks on 500."""
        def fake(payload, **kwargs):
            raise RuntimeError("SECRET_TOKEN=abc123\\nTraceback: internal")

        status, body = handle_explore(VALID_PAYLOAD, explore_fn=fake)
        self.assertEqual(status, 500)
        self.assertEqual(
            body,
            {
                "schema_version": "1",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error.",
                    "field": None,
                },
            },
        )
        encoded = json.dumps(body)
        self.assertNotIn("SECRET", encoded)
        self.assertNotIn("Traceback", encoded)
        self.assertNotIn("RuntimeError", encoded)

    def test_success_and_kwargs_pass_through(self) -> None:
        """Spec §14.3 | Bug it catches: successful results are wrapped or engine kwargs are dropped."""
        seen = {}

        def fake(payload, *, profiles=None, config=None, **kwargs):
            seen["profiles"] = profiles
            seen["config"] = config
            return {"schema_version": "1", "status": "ok", "request": payload}

        profiles = {"crop_a": {}}
        config = {"max_initial_wait_days": 180}
        status, body = handle_explore(
            VALID_PAYLOAD,
            explore_fn=fake,
            profiles=profiles,
            config=config,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIs(seen["profiles"], profiles)
        self.assertIs(seen["config"], config)


class ApiServerTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        """Spec §14.3 | Bug it catches: health route is missing or not JSON."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, data = _http(port, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), {"status": "ok"})

    def test_real_explore_request_uses_local_profiles_and_config(self) -> None:
        """Spec §14.2/§14.3 | Bug it catches: server does not pass profiles/default config."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, data = _http(
                port,
                "POST",
                "/api/explore",
                _json_body(VALID_PAYLOAD),
                {"Content-Type": "application/json"},
            )
        self.assertEqual(status, 200)
        body = json.loads(data)
        self.assertTrue(body["has_profiles"])
        self.assertEqual(body["config"]["max_initial_wait_days"], 180)
        self.assertIsNone(body["config"]["max_waiting_days"])
        self.assertEqual(body["config"]["analysis_start_year"], 2000)
        self.assertEqual(body["config"]["analysis_end_year"], 2025)

    def test_cors_allowlist_and_preflight(self) -> None:
        """Spec §14.5 | Bug it catches: wildcard CORS or disallowed origin is accepted."""
        with _running_server(_fake_explore) as (port, _server):
            allowed = f"http://127.0.0.1:{port}"
            status, headers, _data = _http(
                port,
                "OPTIONS",
                "/api/explore",
                headers={"Origin": allowed},
            )
            self.assertEqual(status, 204)
            self.assertEqual(headers.get("access-control-allow-origin"), allowed)

            status, headers, _data = _http(
                port,
                "OPTIONS",
                "/api/explore",
                headers={"Origin": "http://evil.example"},
            )
            self.assertEqual(status, 403)
            self.assertNotIn("access-control-allow-origin", headers)

            status, headers, _data = _http(
                port,
                "POST",
                "/api/explore",
                _json_body(VALID_PAYLOAD),
                {"Content-Type": "application/json", "Origin": allowed},
            )
            self.assertEqual(status, 200)
            self.assertEqual(headers.get("access-control-allow-origin"), allowed)
            self.assertNotEqual(headers.get("access-control-allow-origin"), "*")

    def test_unknown_route_is_404(self) -> None:
        """Spec §14.5 | Bug it catches: unknown routes are treated as explore or health."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, _data = _http(port, "GET", "/nope")
        self.assertEqual(status, 404)

    def test_malformed_json_is_400(self) -> None:
        """Spec §14.3 | Bug it catches: malformed JSON crashes or returns a non-error body."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, data = _http(
                port,
                "POST",
                "/api/explore",
                b"{",
                {"Content-Type": "application/json"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(data)["error"]["code"], "INVALID_REQUEST")

    def test_invalid_payload_is_400_before_explore(self) -> None:
        """Spec §14.2 | Bug it catches: server bypasses request validation."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, data = _http(
                port,
                "POST",
                "/api/explore",
                _json_body({}),
                {"Content-Type": "application/json"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(data)["error"]["field"], "district_id")

    def test_content_type_and_body_size_limits(self) -> None:
        """Spec §14.3 | Bug it catches: wrong content type or oversized body is accepted."""
        with _running_server(_fake_explore) as (port, _server):
            status, _headers, _data = _http(
                port,
                "POST",
                "/api/explore",
                b"{}",
                {"Content-Type": "text/plain"},
            )
            self.assertEqual(status, 415)

            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                connection.putrequest("POST", "/api/explore")
                connection.putheader("Content-Type", "application/json")
                connection.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
                connection.endheaders()
                response = connection.getresponse()
                status = response.status
                response.read()
            finally:
                connection.close()
            self.assertEqual(status, 413)

    def test_server_internal_error_is_generic(self) -> None:
        """Spec §14.3 | Bug it catches: server returns stack or secret text on engine failure."""
        def fake(payload, **kwargs):
            raise RuntimeError("SECRET_TOKEN=server")

        with _running_server(fake) as (port, _server):
            status, _headers, data = _http(
                port,
                "POST",
                "/api/explore",
                _json_body(VALID_PAYLOAD),
                {"Content-Type": "application/json"},
            )
        self.assertEqual(status, 500)
        body = json.loads(data)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("SECRET", data.decode("utf-8"))
        self.assertNotIn("Traceback", data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
