from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from _shared import JsonHandlerMixin
from state_store import update_settings


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_POST(self):
        payload = self.read_json()
        self.send_json({"settings": update_settings(payload)})

    def do_OPTIONS(self):
        self.send_json({})
