"""Development HTTP wrapper for the explore engine (v1.md §14.3/§14.5)."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from src.api import handle_explore
from src.crop_profiles import load_crop_profiles
from src.error_contract import build_error_response
from src.local_power import load_local_power
from src.request_validation import RequestValidationError, validate_explore_request

PROFILE_FILENAME = "fosol_cycle_rajshahi_crop_dataset.csv"
POWER_FILENAME = "NASA_RAJ_DATA_2000_2026.csv"
MAX_BODY_BYTES = 64 * 1024
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "Data"
DEFAULT_CONFIG = {
    "max_initial_wait_days": 180,
    "max_waiting_days": None,
    "analysis_start_year": 2000,
    "analysis_end_year": 2025,
    "max_branches": None,
}


class ExploreHandler(BaseHTTPRequestHandler):
    """Small JSON HTTP surface; no provider calls happen here."""

    server_version = "FosolCycle/1"

    def do_GET(self) -> None:
        if self._path() == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self._path() != "/api/explore":
            self._send_json(404, {"error": "not_found"})
            return

        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            self._send_error(415, "Content-Type must be application/json.")
            return

        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            self._send_error(400, "Content-Length is required.")
            return
        if length < 0:
            self._send_error(400, "Content-Length is invalid.")
            return
        if length > MAX_BODY_BYTES:
            self._send_error(413, "Request body is too large.")
            return

        raw = self.rfile.read(length)
        if len(raw) != length:
            self._send_error(400, "Request body is incomplete.")
            return
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error(400, "Request body must be valid JSON.")
            return
        if not isinstance(payload, dict):
            self._send_error(400, "Request payload must be a JSON object.")
            return

        try:
            validate_explore_request(payload, self.server.profiles)
        except RequestValidationError as exc:
            self._send_json(400, build_error_response(exc))
            return

        status, body = handle_explore(
            payload,
            explore_fn=self.server.explore_fn,
            profiles=self.server.profiles,
            config=self.server.config,
            environment=self.server.environment,
        )
        self._send_json(status, body)

    def do_OPTIONS(self) -> None:
        if self._path() not in ("/api/explore", "/health"):
            self._send_json(404, {"error": "not_found"})
            return
        origin = self.headers.get("Origin")
        if origin is None:
            self._send_empty(204)
            return
        if origin not in self._allowed_origins():
            self._send_error(403, "CORS origin is not allowed.")
            return
        self._send_empty(204, self._cors_headers(origin))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _path(self) -> str:
        return urlsplit(self.path).path

    def _allowed_origins(self) -> set[str]:
        port = self.server.server_address[1]
        return {
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
        }

    def _cors_headers(self, origin: str | None = None) -> dict[str, str]:
        origin = origin or self.headers.get("Origin")
        if origin not in self._allowed_origins():
            return {}
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Vary": "Origin",
        }

    def _send_error(self, status: int, message: str) -> None:
        exc = RequestValidationError(message, None)
        self._send_json(status, build_error_response(exc))

    def _send_json(self, status: int, body: object) -> None:
        data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for name, value in self._cors_headers().items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def _send_empty(self, status: int, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    data_dir: str | Path | None = None,
    explore_fn=None,
) -> ThreadingHTTPServer:
    """Build a server from the local crop profiles; providers are untouched."""
    directory = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    profiles = load_crop_profiles(directory / PROFILE_FILENAME)
    environment = load_local_power(directory / POWER_FILENAME)
    server = ThreadingHTTPServer((host, port), ExploreHandler)
    server.daemon_threads = True
    server.explore_fn = explore_fn
    server.profiles = profiles
    server.config = dict(DEFAULT_CONFIG)
    server.environment = environment
    server.data_dir = str(directory)
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Fosol-Cycle explore API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.data_dir)
    print(f"Listening on http://{args.host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
