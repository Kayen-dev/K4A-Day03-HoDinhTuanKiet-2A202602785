"""
Local JSON state for profile, chat windows, memories, and model settings.
"""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_PATH = os.path.join(DATA_DIR, "travel_agent_state.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


DEFAULT_STATE: Dict[str, Any] = {
    "profile": {
        "name": "",
        "home_city": "",
        "travel_style": "balanced",
        "budget_level": "mid-range",
        "interests": [],
        "dietary_notes": "",
        "mobility_notes": "",
        "preferred_language": "vi",
    },
    "settings": {},
    "sessions": [],
    "memories": [],
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "provider": "auto",
    "openai_model": "gpt-4o-mini",
    "gemini_model": "gemini-2.5-flash",
    "model": "gemini-2.5-flash",
    "openai_api_key": "",
    "gemini_api_key": "",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_state() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STATE_PATH):
        save_state(deepcopy(DEFAULT_STATE))
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    merged = deepcopy(DEFAULT_STATE)
    merged.update(state)
    for key, value in DEFAULT_STATE.items():
        if isinstance(value, dict):
            merged[key] = {**value, **state.get(key, {})}
    merged["settings"] = {**DEFAULT_SETTINGS, **merged.get("settings", {})}
    if merged.get("settings", {}).get("provider") in ["mock", "openai", "gemini"]:
        merged["settings"]["provider"] = "auto"
    for session in merged.get("sessions", []):
        session["settings"] = {**DEFAULT_SETTINGS, **session.get("settings", {})}
        if session["settings"].get("provider") in ["mock", "openai", "gemini"]:
            session["settings"]["provider"] = "auto"
    return merged


def _has_key(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value) and not value.startswith("your_")


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def update_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    clean = {**state["profile"], **profile}
    interests = clean.get("interests", [])
    if isinstance(interests, str):
        interests = [item.strip() for item in interests.split(",") if item.strip()]
    clean["interests"] = interests
    state["profile"] = clean
    save_state(state)
    return clean


def public_settings(settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    current = {**DEFAULT_SETTINGS, **(settings or {})}
    return {
        "provider": "auto",
        "model": current.get("model") or current.get("gemini_model", "gemini-2.5-flash"),
        "openai_model": current.get("openai_model", "gpt-4o-mini"),
        "gemini_model": current.get("gemini_model", "gemini-2.5-flash"),
        "has_openai_key": bool(current.get("openai_api_key")),
        "has_gemini_key": bool(current.get("gemini_api_key")),
    }


def public_session(session: Dict[str, Any]) -> Dict[str, Any]:
    clean = {k: v for k, v in session.items() if k != "settings"}
    clean["settings"] = public_settings(session.get("settings"))
    return clean


def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    session_id = settings.get("session_id", "")
    provider = "auto"
    base_settings = state["settings"]
    target_session = None
    for session in state["sessions"]:
        if session.get("id") == session_id:
            target_session = session
            base_settings = session.get("settings", DEFAULT_SETTINGS)
            break

    openai_model = settings.get("openai_model") or settings.get("model") or base_settings.get("openai_model", "gpt-4o-mini")
    gemini_model = settings.get("gemini_model") or base_settings.get("gemini_model", "gemini-2.5-flash")
    openai_key = settings.get("openai_api_key", "").strip()
    gemini_key = settings.get("gemini_api_key", "").strip()
    updated = {
        **DEFAULT_SETTINGS,
        **base_settings,
        "provider": provider,
        "model": gemini_model,
        "openai_model": openai_model,
        "gemini_model": gemini_model,
    }
    if openai_key:
        updated["openai_api_key"] = openai_key
    if gemini_key:
        updated["gemini_api_key"] = gemini_key

    if target_session:
        target_session["settings"] = updated
        save_state(state)
        return public_settings(updated)

    state["settings"] = updated
    save_state(state)
    env_values = {"LLM_PROVIDER": "auto", "OPENAI_MODEL": openai_model, "GEMINI_MODEL": gemini_model}
    if openai_key:
        env_values["OPENAI_API_KEY"] = openai_key
    if gemini_key:
        env_values["GEMINI_API_KEY"] = gemini_key
    write_env_values(env_values)
    return public_settings(updated)


def write_env_values(values: Dict[str, str]) -> None:
    lines: List[str] = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    existing = {}
    for index, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            existing[key] = index
    for key, value in values.items():
        line = f"{key}={value}"
        if key in existing:
            lines[existing[key]] = line
        else:
            lines.append(line)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def list_sessions() -> List[Dict[str, Any]]:
    state = load_state()
    return [
        {
            "id": session["id"],
            "title": session.get("title", "New trip"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "message_count": len(session.get("messages", [])),
        }
        for session in state["sessions"]
    ]


def create_session(title: str = "New trip") -> Dict[str, Any]:
    state = load_state()
    session = {
        "id": uuid.uuid4().hex[:12],
        "title": title or "New trip",
        "created_at": _now(),
        "updated_at": _now(),
        "messages": [],
        "settings": deepcopy(DEFAULT_SETTINGS),
    }
    state["sessions"].insert(0, session)
    save_state(state)
    return public_session(session)


def get_session(session_id: str) -> Dict[str, Any]:
    session = get_session_private(session_id)
    return public_session(session)


def get_session_private(session_id: str) -> Dict[str, Any]:
    state = load_state()
    for session in state["sessions"]:
        if session["id"] == session_id:
            return session
    created = create_session()
    return get_session_private(created["id"])


def append_message(session_id: str, role: str, content: str, trace: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    state = load_state()
    session = None
    for item in state["sessions"]:
        if item["id"] == session_id:
            session = item
            break
    if not session:
        session = create_session()
        state = load_state()
        session = state["sessions"][0]
    message = {"id": uuid.uuid4().hex[:10], "role": role, "content": content, "created_at": _now()}
    if trace is not None:
        message["trace"] = trace
    session["messages"].append(message)
    session["updated_at"] = _now()
    if role == "user" and session.get("title") in ["New trip", ""]:
        session["title"] = content[:46] + ("..." if len(content) > 46 else "")
    save_state(state)
    return message


def add_memory(session_id: str, kind: str, content: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    state = load_state()
    memory = {
        "id": uuid.uuid4().hex[:10],
        "session_id": session_id,
        "kind": kind,
        "content": content,
        "metadata": metadata or {},
        "created_at": _now(),
    }
    state["memories"].insert(0, memory)
    state["memories"] = state["memories"][:50]
    save_state(state)
    return memory


def recent_memories(limit: int = 8) -> List[Dict[str, Any]]:
    return load_state().get("memories", [])[:limit]
