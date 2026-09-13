from __future__ import annotations

from http.server import BaseHTTPRequestHandler

import os

from api._shared import JsonHandlerMixin


class handler(JsonHandlerMixin, BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_json(
            {
                "profile": {},
                "settings": {
                    "provider": "auto",
                    "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
                    "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
                    "storage": "browser-session",
                },
                "sessions": [],
                "memories": [],
            }
        )

    def do_OPTIONS(self):
        self.send_json({})
