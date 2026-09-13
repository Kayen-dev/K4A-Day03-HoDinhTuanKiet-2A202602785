from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
import uuid

from api._shared import JsonHandlerMixin


def _session_id_from_path(path: str, query: dict) -> str:
    if query.get("id"):
        return query["id"][0]
    marker = "/api/sessions/"
    if marker in path:
        return path.split(marker, 1)[1].strip("/")
    return ""


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_json({"sessions": [], "storage": "browser-session"})

    def do_POST(self):
        try:
            payload = self.read_json()
            now = datetime.now().isoformat(timespec="seconds")
            session = {
                "id": uuid.uuid4().hex[:12],
                "title": payload.get("title") or "New trip",
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
            self.send_json({"session": session, "storage": "browser-session"}, status=201)
        except Exception as exc:
            self.send_error_json(exc)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        session_id = _session_id_from_path(parsed.path, self.query_params())
        self.send_json({"deleted": bool(session_id), "session_id": session_id})

    def do_OPTIONS(self):
        self.send_json({})
