from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api._shared import JsonHandlerMixin


def _public_settings(payload):
    payload = payload or {}
    return {
        "provider": "auto",
        "gemini_model": payload.get("gemini_model") or "gemini-2.5-flash",
        "openai_model": payload.get("openai_model") or "gpt-4o-mini",
        "has_gemini_key": bool(str(payload.get("gemini_api_key") or "").strip()),
        "has_openai_key": bool(str(payload.get("openai_api_key") or "").strip()),
        "storage": "browser-session",
    }


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_json({"status": "ok", "method": "POST", "storage": "browser-session"})

    def do_POST(self):
        try:
            payload = self.read_json() or {}
            self.send_json({"settings": _public_settings(payload)})
        except Exception as exc:
            self.send_error_json(exc)

    def do_OPTIONS(self):
        self.send_json({})

