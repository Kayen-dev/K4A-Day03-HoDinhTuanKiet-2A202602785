from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from _shared import JsonHandlerMixin
from state_store import create_session, get_session, list_sessions


def _session_id_from_path(path: str, query: dict) -> str:
    if query.get("id"):
        return query["id"][0]
    marker = "/api/sessions/"
    if marker in path:
        return path.split(marker, 1)[1].strip("/")
    return ""


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = self.query_params()
        session_id = _session_id_from_path(parsed.path, query)
        if session_id:
            self.send_json({"session": get_session(session_id)})
            return
        self.send_json({"sessions": list_sessions()})

    def do_POST(self):
        payload = self.read_json()
        title = payload.get("title", "New trip")
        self.send_json({"session": create_session(title)}, status=201)

    def do_OPTIONS(self):
        self.send_json({})
