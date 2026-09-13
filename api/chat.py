from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from _shared import JsonHandlerMixin
from state_store import create_session, get_session
from travel_agent import answer_travel_request


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_POST(self):
        payload = self.read_json()
        session_id = payload.get("session_id") or create_session("New trip")["id"]
        message = payload.get("message", "").strip()
        if not message:
            self.send_json({"error": "Message is required"}, status=400)
            return

        result = answer_travel_request(session_id, message)
        self.send_json({"session": get_session(session_id), **result})

    def do_OPTIONS(self):
        self.send_json({})
