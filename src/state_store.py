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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_PATH = os.path.join(DATA_DIR, "travel_agent_state.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")


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
    "settings": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "has_openai_key": False,
    },
    "sessions": [],
    "memories": [],
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
    if merged.get("settings", {}).get("provider") == "mock":
        merged["settings"]["provider"] = "openai"
    return merged


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


def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    provider = settings.get("provider") or state["settings"].get("provider", "openai")
    model = settings.get("model") or state["settings"].get("model", "gpt-4o-mini")
    openai_key = settings.get("openai_api_key", "").strip()

    state["settings"].update(
        {
            "provider": provider,
            "model": model,
            "has_openai_key": bool(openai_key) or state["settings"].get("has_openai_key", False),
        }
    )
    save_state(state)

    if openai_key:
        write_env_values({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": openai_key, "LLM_MODEL": model})
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = openai_key
        os.environ["LLM_MODEL"] = model
    else:
        os.environ["LLM_PROVIDER"] = provider
        os.environ["LLM_MODEL"] = model

    public_settings = dict(state["settings"])
    public_settings.pop("openai_api_key", None)
    return public_settings


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
    }
    state["sessions"].insert(0, session)
    save_state(state)
    return session


def get_session(session_id: str) -> Dict[str, Any]:
    state = load_state()
    for session in state["sessions"]:
        if session["id"] == session_id:
            return session
    return create_session()


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
