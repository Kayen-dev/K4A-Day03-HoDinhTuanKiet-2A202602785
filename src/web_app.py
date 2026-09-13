"""
Tiny local web server for the Travel Planning ReAct Agent.

Run:
    python src/web_app.py
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from state_store import create_session, get_session, list_sessions, load_state, public_settings, update_profile, update_settings
from travel_agent import answer_travel_request


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "web")
HOST = "127.0.0.1"
PORT = int(os.getenv("TRAVEL_WEB_PORT", "7860"))


class TravelWebHandler(BaseHTTPRequestHandler):
    server_version = "TravelPlanningAgent/1.0"

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        safe = os.path.normpath(unquote(path).lstrip("/"))
        file_path = os.path.join(STATIC_DIR, safe)
        if not os.path.abspath(file_path).startswith(os.path.abspath(STATIC_DIR)) or not os.path.exists(file_path):
            self.send_error(404, "Not found")
            return
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/state":
            state = load_state()
            public = {
                "profile": state["profile"],
                "settings": public_settings(state.get("settings")),
                "sessions": list_sessions(),
                "memories": state.get("memories", [])[:8],
            }
            return self._send_json(public)
        if path == "/api/sessions":
            return self._send_json({"sessions": list_sessions()})
        if path.startswith("/api/sessions/"):
            session_id = path.rsplit("/", 1)[-1]
            return self._send_json({"session": get_session(session_id)})
        return self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
            if path == "/api/profile":
                return self._send_json({"profile": update_profile(payload)})
            if path == "/api/settings":
                return self._send_json({"settings": update_settings(payload)})
            if path == "/api/sessions":
                title = payload.get("title", "New trip")
                return self._send_json({"session": create_session(title)}, status=201)
            if path == "/api/chat":
                session_id = payload.get("session_id") or create_session("New trip")["id"]
                message = payload.get("message", "").strip()
                if not message:
                    return self._send_json({"error": "Message is required"}, status=400)
                result = answer_travel_request(session_id, message)
                return self._send_json({"session": get_session(session_id), **result})
            return self._send_json({"error": "Unknown endpoint"}, status=404)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format, *args):
        print(f"[web] {self.address_string()} - {format % args}")


def main():
    os.makedirs(STATIC_DIR, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), TravelWebHandler)
    print("==========================================================")
    print("Travel Planning ReAct Agent Web UI")
    print("==========================================================")
    print(f"Open: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
