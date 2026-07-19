from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
API_BASE = os.getenv("AGENT_MENTOR_API_BASE", "http://api:8000")


class FrontendHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith(("/api/", "/health/")):
            self.proxy()
            return
        self.serve_static()

    def do_POST(self) -> None:
        if self.path.startswith(("/api/", "/health/")):
            self.proxy()
            return
        self.send_error(404)

    def do_DELETE(self) -> None:
        if self.path.startswith(("/api/", "/health/")):
            self.proxy()
            return
        self.send_error(404)

    def proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        request = Request(
            f"{API_BASE}{self.path}",
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header(
                    "Content-Type", response.headers.get("Content-Type", "application/json")
                )
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except HTTPError as error:
            payload = error.read()
            self.send_response(error.code)
            self.send_header("Content-Type", error.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as error:
            payload = json.dumps({"message": str(error)}, ensure_ascii=False).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def serve_static(self) -> None:
        path = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        target = (ROOT / path).resolve()
        if not str(target).startswith(str(ROOT.resolve())) or not target.exists():
            target = ROOT / "index.html"
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 3000), FrontendHandler)
    server.serve_forever()
