"""Serve the tax calculator and the course-proxy assistant on loopback."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from tax_app.proxy import ProxyConfigurationError
from tax_app.agent import ask
from tax_app.calculator import TaxInput, calculate_tax
from tax_app.retrieval import TaxRules


STATIC = Path(__file__).parent / "static"
ASSETS = {"/": ("index.html", "text/html"), "/calculator": ("index.html", "text/html"),
          "/tax.js": ("tax.js", "text/javascript"),
          "/tax.css": ("tax.css", "text/css")}


MAX_BODY = 8192
MAX_CHAT_BODY = 32768


class TaxHandler(BaseHTTPRequestHandler):
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
        if path in ASSETS:
            file, kind = ASSETS[path]
            content = (STATIC / file).read_bytes()
            if path == "/calculator":
                content = content.replace(b'data-page="chat"', b'data-page="calculator"', 1)
            self._send(200, content, kind)
        else:
            self._json(404, {"error": "ไม่พบหน้านี้"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/api/calculate", "/api/ask"):
            self._json(404, {"error": "ไม่พบ API นี้"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "ใช้ application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= (MAX_CHAT_BODY if path == "/api/ask" else MAX_BODY):
                raise ValueError("Invalid size.")
            body = self.rfile.read(length)
            if path == "/api/calculate":
                profile = TaxInput.model_validate_json(body)
                data = {"result": calculate_tax(profile),
                        "citations": self.server.rules.calculation_sources(profile)}
            else:
                payload = json.loads(body)
                if not isinstance(payload, dict) or "query" not in payload or (
                    payload.keys() - {"query", "history"}
                ):
                    raise ValueError("Expected query.")
                data = ask(self.server.rules, payload["query"], history=payload.get("history"))
        except ProxyConfigurationError:
            self._json(503, {"error": "ตั้งค่า OPENAI_API_KEY และ OPENAI_BASE_URL ใน .env ก่อนใช้แชต"})
            return
        except ValueError:
            self._json(400, {"error": "ตรวจปีภาษี รูปแบบข้อมูล และยอดเงินที่กรอก"})
            return
        except Exception:
            self._json(502, {"error": "เรียก class proxy ไม่สำเร็จ กรุณาตรวจค่าการเชื่อมต่อ"})
            return
        self._json(200, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    render_port = os.environ.get("PORT")
    parser.add_argument("--host", default="0.0.0.0" if render_port else "127.0.0.1")
    parser.add_argument("--port", type=int, default=render_port or 8001)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), TaxHandler) as server:
        server.rules = TaxRules()
        print(f"Thai Tax Assistant • http://{args.host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
