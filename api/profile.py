from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api._shared import JsonHandlerMixin


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_json({"profile": {}, "storage": "browser-session"})

    def do_POST(self):
        try:
            profile = self.read_json() or {}
            self.send_json({"profile": profile, "storage": "browser-session"})
        except Exception as exc:
            self.send_error_json(exc)

    def do_OPTIONS(self):
        self.send_json({})

