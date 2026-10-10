"""LOCAL-ONLY Cocos Web Desktop preview and ComfyReview reverse proxy.

Serves an editor-generated Cocos web build from --build, routing requests to
/api/v2/ and /files/ to the existing FastAPI server. No backend modifications,
CORS exceptions, or browser security workarounds needed for this smoke test.
NOT a production gateway; deliberately bound to 127.0.0.1 with no auth.
"""

from __future__ import annotations

import argparse
from http.client import HTTPConnection, HTTPSConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


BACKEND_ROUTES = ("/api/v2/", "/files/")


def is_backend_request(path: str) -> bool:
    parsed = urlsplit(path)
    return not parsed.scheme and not parsed.netloc and any(
        parsed.path.startswith(prefix) for prefix in BACKEND_ROUTES
    )


def build_handler(build_dir: Path, backend_url: str):
    backend = urlsplit(backend_url)
    if backend.scheme not in ("http", "https") or not backend.hostname:
        raise ValueError("Backend URL must be an HTTP(S) URL")
    if backend.path not in ("", "/") or backend.query or backend.fragment:
        raise ValueError("Backend URL must be an origin without path or query")
    directory = Path(build_dir).resolve()
    if not (directory / "index.html").is_file():
        raise ValueError(f"Expected Cocos Web Desktop index.html in {directory}")

    class LocalDevHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def do_GET(self):
            if is_backend_request(self.path):
                self.forward_request("GET")
            else:
                super().do_GET()

        def do_HEAD(self):
            if is_backend_request(self.path):
                self.forward_request("HEAD")
            else:
                super().do_HEAD()

        def forward_request(self, method: str) -> None:
            connection_class = (
                HTTPSConnection if backend.scheme == "https" else HTTPConnection
            )
            conn = connection_class(backend.hostname, backend.port, timeout=12)
            headers_sent = False
            try:
                conn.request(method, self.path, headers={"Accept": "*/*"})
                reply = conn.getresponse()
                self.send_response(reply.status)
                for header in ("Content-Type", "Content-Length", "Cache-Control"):
                    value = reply.getheader(header)
                    if value:
                        self.send_header(header, value)
                self.end_headers()
                headers_sent = True
                if method == "GET":
                    while chunk := reply.read(64 * 1024):
                        self.wfile.write(chunk)
            except (OSError, TimeoutError, ValueError):
                # A disconnected backend must be visible as a gateway failure.
                if not headers_sent and not self.wfile.closed:
                    try:
                        self.send_error(502, "Local ComfyReview backend unavailable")
                    except (OSError, ValueError):
                        pass
            finally:
                conn.close()

    return LocalDevHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    handler = build_handler(args.build, args.backend)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Cocos preview: http://127.0.0.1:{args.port}/", flush=True)
        print(f"Forwarding /api/v2/ and /files/ to {args.backend}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
