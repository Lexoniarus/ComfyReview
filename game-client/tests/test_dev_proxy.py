"""Behavior tests for the standalone local Cocos development proxy."""

import tempfile
import unittest
from collections.abc import Callable
from http.server import (
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from runpy import run_path
from threading import Thread
from typing import cast
from urllib.request import urlopen

# The "game-client" directory is not an importable Python package.
# Load the standalone script by path without altering global sys.path.
_scripts = Path(__file__).resolve().parents[1] / "scripts"
_exports = run_path(str(_scripts / "dev_proxy.py"))
build_handler = cast(
    Callable[[Path, str], type[SimpleHTTPRequestHandler]],
    _exports["build_handler"],
)
is_backend_request = cast(
    Callable[[str], bool], _exports["is_backend_request"]
)


class QuietBackend(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/files/"):
            response = b"123"
            content_type = "image/png"
        else:
            response = b'{"image_uid":"img-1"}'
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        pass


class DevProxyTest(unittest.TestCase):
    def test_only_allowed_prefixes_go_to_backend(self) -> None:
        self.assertTrue(is_backend_request("/api/v2/images/img-1?foo=bar"))
        self.assertTrue(is_backend_request("/files/image%20one.png"))
        for other in (
            "/",
            "/index.html",
            "/admin",
            "/files-other/secret.png",
            "https://remote.invalid/api/v2/images/x",
        ):
            self.assertFalse(is_backend_request(other))

    def test_serves_static_files_and_proxies_api_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            index = directory / "index.html"
            index.write_text("Cocos demo", encoding="utf-8")
            backend = ThreadingHTTPServer(("127.0.0.1", 0), QuietBackend)
            backend_thread = Thread(target=backend.serve_forever, daemon=True)
            backend_thread.start()
            proxy = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                build_handler(
                    directory, f"http://127.0.0.1:{backend.server_port}"
                ),
            )
            proxy_thread = Thread(target=proxy.serve_forever, daemon=True)
            proxy_thread.start()
            try:
                root = f"http://127.0.0.1:{proxy.server_port}"
                with urlopen(root + "/") as response:
                    self.assertIn(b"Cocos demo", response.read())
                with urlopen(root + "/api/v2/images/img-1") as response:
                    self.assertEqual(response.read(), b'{"image_uid":"img-1"}')
                with urlopen(root + "/files/test.png") as response:
                    self.assertEqual(response.read(), b"123")
            finally:
                proxy.shutdown()
                backend.shutdown()
                proxy.server_close()
                backend.server_close()
                proxy_thread.join(timeout=2)
                backend_thread.join(timeout=2)

    def test_requires_actual_web_build_and_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            with self.assertRaises(ValueError):
                build_handler(build, "http://127.0.0.1:8000")
            (build / "index.html").write_text("test", encoding="utf-8")
            build_handler(build, "http://127.0.0.1:8000")
            for invalid in ("not-url", "http://127.0.0.1:8000/foo"):
                with self.assertRaises(ValueError):
                    build_handler(build, invalid)


if __name__ == "__main__":
    unittest.main()
