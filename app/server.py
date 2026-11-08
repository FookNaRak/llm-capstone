"""Local HTTP interface for the catalog checker and proxy-backed assistant."""

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from app.agent import ProxyConfigurationError, run_agent
from app.catalog import Catalog
from app.checker import check_compatibility


STATIC = Path(__file__).parent / "static"
ASSETS = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
}
MAX_BODY = 8192
LOGGER = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, content, media_type):
        self.send_response(status)
        self.send_header("Content-Type", media_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status, payload):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/parts":
            parts = [{"id": part["id"], "name": part["name"], "kind": part["kind"]}
                     for part in self.server.catalog.parts.values()]
            self._json(200, {"parts": parts})
        elif path in ASSETS:
            filename, media_type = ASSETS[path]
            self._send(200, (STATIC / filename).read_bytes(), media_type)
        else:
            self._json(404, {"error": "Unknown endpoint."})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/api/check", "/api/ask"):
            self._json(404, {"error": "Unknown endpoint."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Expected application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("Invalid request size.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object.")
            if path == "/api/ask":
                if data.keys() != {"query"}:
                    raise ValueError("Send only the query field.")
                result = run_agent(self.server.catalog, data["query"])
            else:
                if data.keys() - {"motherboard", "cpu", "memory", "bios"} or any(
                    value is not None and (not isinstance(value, str) or len(value) > 300)
                    for value in data.values()
                ):
                    raise ValueError("Invalid compatibility fields.")
                result = check_compatibility(self.server.catalog, **data)
        except ProxyConfigurationError as error:
            self._json(503, {"error": str(error)})
            return
        except (UnicodeError, ValueError) as error:
            self._json(400, {"error": str(error)})
            return
        except Exception as error:
            LOGGER.warning("Request failed (%s)", type(error).__name__)
            self._json(502, {"error": "The proxy request failed. Check the course URL and key."})
            return
        self._json(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.catalog = Catalog()
        print(f"PC Parts Check • http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
