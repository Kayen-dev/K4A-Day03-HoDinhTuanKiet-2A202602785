from __future__ import annotations

from http.server import BaseHTTPRequestHandler

import os

from api._shared import JsonHandlerMixin
from travel_agent import generate_travel_response


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            payload = self.read_json()
            message = str(payload.get("message") or "").strip()
            if not message:
                self.send_json({"error": "Message is required"}, status=400)
                return

            settings = dict(payload.get("settings") or {})
            settings["gemini_api_key"] = settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
            settings["openai_api_key"] = settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
            result = generate_travel_response(
                user_message=message,
                profile=payload.get("profile") or {},
                settings=settings,
                memory_items=payload.get("memories") or [],
                conversation_history=payload.get("conversation_history") or [],
                session_id=str(payload.get("session_id") or "browser-session"),
            )
            self.send_json(result)
        except Exception as exc:
            self.send_error_json(exc)

    def do_OPTIONS(self):
        self.send_json({})
