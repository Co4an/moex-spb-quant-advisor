#!/usr/bin/env python3
"""
Local HTTP Server for the MOEX & SPBEX Investment Dashboard (`serve_dashboard.py`).

Serves `dashboard/` at http://127.0.0.1:8765 and provides:
- `GET /api/data` -> live JSON bundle
- `POST /api/refresh` -> triggers `scripts/run_pipeline.py` to pull fresh quotes from MOEX ISS & SPBEX
"""
from __future__ import annotations

import http.server
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"


class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/data":
            val_path = ROOT_DIR / "data" / "processed" / "quant_valuation_matrix.json"
            payload = val_path.read_bytes() if val_path.exists() else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/refresh":
            subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "run_pipeline.py")], cwd=str(ROOT_DIR), check=True)
            resp = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return
        self.send_error(404, "Endpoint not found")


def main(port: int = 8765) -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DashboardRequestHandler)
    print(f"Терминал MOEX & SPBEX запущен: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка сервера.")


if __name__ == "__main__":
    main()
