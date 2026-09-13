from __future__ import annotations

import json
import os
import sys
from urllib.parse import parse_qs, urlparse


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


class JsonHandlerMixin:
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length_header = (
                self.headers.get("content-length")
                or self.headers.get("Content-Length")
                or self.headers.get("CONTENT_LENGTH")
                or "0"
            )
            length = int(length_header)
        except (ValueError, TypeError):
            length = 0

        if not length or length <= 0:
            return {}

        try:
            raw = self.rfile.read(length)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            raw = (raw or "").strip()
            if not raw:
                return {}
            return json.loads(raw)
        except Exception:
            return {}

    def query_params(self):
        return parse_qs(urlparse(self.path).query)

    def send_error_json(self, exc, status=500):
        message = str(exc).strip() or exc.__class__.__name__
        self.send_json({"error": message}, status=status)

