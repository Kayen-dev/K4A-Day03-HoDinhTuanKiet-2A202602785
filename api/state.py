from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from _shared import JsonHandlerMixin
from state_store import list_sessions, load_state, public_settings


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        state = load_state()
        self.send_json(
            {
                "profile": state["profile"],
                "settings": public_settings(state.get("settings")),
                "sessions": list_sessions(),
                "memories": state.get("memories", [])[:8],
            }
        )

    def do_OPTIONS(self):
        self.send_json({})
