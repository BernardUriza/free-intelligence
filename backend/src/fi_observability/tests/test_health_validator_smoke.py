from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from backend.src.fi_observability.health_validator import main
from pathlib import Path

from ._fixtures import repo_root, write_policy_json


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/health", "/deep"}:
            payload = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, _fmt: str, *_args: object) -> None:
        # Avoid noisy server logs in tests.
        return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_health_validator_smoke(tmp_path: Path) -> None:
    policy_path = write_policy_json(tmp_path)
    out_dir = tmp_path / "artifacts"

    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), _Handler)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        code = main(
            [
                "--base-path",
                str(repo_root()),
                "--slo-policy",
                str(policy_path),
                "--environment",
                "local",
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--shallow-paths",
                "/health",
                "--deep-paths",
                "/deep",
                "--requests",
                "10",
                "--concurrency",
                "2",
                "--out-dir",
                str(out_dir),
            ]
        )
        assert code == 0

        json_path = out_dir / "health_report.json"
        assert json_path.exists()
        assert (out_dir / "health_report.json.sha256").exists()

        report = json.loads(json_path.read_text(encoding="utf-8"))
        assert report["tool"] == "health_validator"
        assert report["mode"] == "read_only"
        assert report["probes"]
    finally:
        server.shutdown()
        server.server_close()
