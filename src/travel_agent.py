"""
Application-level Travel ReAct service used by the web UI and CLI.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

from mcp_server import MCPTravelServer
from prompts import FINAL_TRAVEL_SYNTHESIS_PROMPT, REACT_AGENT_SYSTEM_PROMPT
from providers import OpenAIProvider
from state_store import add_memory, append_message, load_state, recent_memories


load_dotenv()


DESTINATION_HINTS = [
    "Đà Nẵng",
    "Da Nang",
    "Hội An",
    "Hoi An",
    "Hà Nội",
    "Ha Noi",
    "Sapa",
    "Đà Lạt",
    "Da Lat",
    "Nha Trang",
    "Phú Quốc",
    "Phu Quoc",
    "Huế",
    "Hue",
    "Bangkok",
    "Singapore",
    "Tokyo",
    "Seoul",
]

INTEREST_KEYWORDS = {
    "biển": "beach",
    "beach": "beach",
    "đồ ăn": "food",
    "ăn": "food",
    "food": "food",
    "ẩm thực": "food",
    "văn hóa": "culture",
    "culture": "culture",
    "lịch sử": "history",
    "history": "history",
    "thiên nhiên": "nature",
    "nature": "nature",
    "nightlife": "nightlife",
    "bar": "nightlife",
    "gia đình": "family",
    "family": "family",
}


def _extract_destination(text: str, profile: Dict[str, Any]) -> str:
    lowered = text.lower()
    for hint in DESTINATION_HINTS:
        if hint.lower() in lowered:
            return hint
    patterns = [
        r"(?:đi|den|đến|toi|tới)\s+([A-ZÀ-Ỵa-zà-ỵ\s]{2,40}?)(?:\s+\d|\s+trong|\s+ngân|\s+ngan|,|\.|$)",
        r"(?:ở|o)\s+([A-ZÀ-Ỵa-zà-ỵ\s]{2,40}?)(?:\s+\d|\s+trong|\s+ngân|\s+ngan|,|\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return profile.get("last_destination") or "Da Nang, Vietnam"


def _extract_duration(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:ngày|ngay|days?)", text, flags=re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 7))
    match = re.search(r"(\d+)\s*(?:đêm|dem|nights?)", text, flags=re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)) + 1, 7))
    return 3


def _extract_start_date(text: str) -> str:
    iso = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    slash = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](20\d{2})", text)
    if slash:
        day, month, year = slash.groups()
        try:
            return datetime(int(year), int(month), int(day)).date().isoformat()
        except ValueError:
            pass
    return date.today().isoformat()


def _extract_budget(text: str, profile: Dict[str, Any]) -> str:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|m)", text, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1).replace(',', '.')} triệu VND/người"
    match = re.search(r"(\d[\d.,]*)\s*(?:vnd|đ|dong)", text, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)} VND/người"
    return profile.get("budget_level", "mid-range")


def _extract_interests(text: str, profile: Dict[str, Any]) -> List[str]:
    lowered = text.lower()
    found = []
    for keyword, tag in INTEREST_KEYWORDS.items():
        if keyword in lowered and tag not in found:
            found.append(tag)
    for item in profile.get("interests", []):
        if item and item not in found:
            found.append(item)
    return found or ["food", "culture"]


def _call_tool(server: MCPTravelServer, trace: List[Dict[str, Any]], name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    started = time.time()
    result = server.call_tool(name, args).get("result", {})
    trace.append(
        {
            "step": len(trace) + 1,
            "action_type": "TOOL_EXECUTION",
            "tool_name": name,
            "arguments": args,
            "observation": result,
            "latency_ms": round((time.time() - started) * 1000, 2),
        }
    )
    return result


def answer_travel_request(session_id: str, user_message: str) -> Dict[str, Any]:
    state = load_state()
    profile = state["profile"]
    settings = state["settings"]
    server = MCPTravelServer()
    append_message(session_id, "user", user_message)

    intent = {
        "destination": _extract_destination(user_message, profile),
        "duration_days": _extract_duration(user_message),
        "start_date": _extract_start_date(user_message),
        "budget": _extract_budget(user_message, profile),
        "interests": _extract_interests(user_message, profile),
        "origin": profile.get("home_city") or "",
    }

    trace: List[Dict[str, Any]] = [
        {
            "step": 1,
            "action_type": "THOUGHT",
            "thought": "Phan tich yeu cau du lich, profile va memory de chon tool MCP can goi.",
            "intent": intent,
            "latency_ms": 0,
        }
    ]

    weather = _call_tool(
        server,
        trace,
        "get_weather_forecast",
        {
            "destination": intent["destination"],
            "start_date": intent["start_date"],
            "duration_days": intent["duration_days"],
        },
    )
    places = _call_tool(
        server,
        trace,
        "search_travel_places",
        {"destination": intent["destination"], "interests": intent["interests"], "limit": 7},
    )
    route = {}
    if intent["origin"]:
        route = _call_tool(server, trace, "estimate_route_distance", {"origin": intent["origin"], "destination": intent["destination"]})

    observations = {"weather": weather, "places": places, "route": route}
    memories = recent_memories()
    synthesis_payload = {
        "profile": profile,
        "recent_memories": memories,
        "user_request": user_message,
        "intent": intent,
        "observations": observations,
    }

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key or openai_key == "your_openai_api_key_here":
        final_answer = (
            "Chưa cấu hình OpenAI API key nên mình không sinh lịch trình bằng GPT. "
            "Các MCP tools đã sẵn sàng dùng API thật; hãy mở Settings và nhập OpenAI API key, "
            "hoặc thêm OPENAI_API_KEY vào file .env rồi gửi lại yêu cầu."
        )
        trace.append(
            {
                "step": len(trace) + 1,
                "action_type": "CONFIG_REQUIRED",
                "thought": "Dung xu ly vi che do real API yeu cau OpenAI API key, khong dung mock.",
                "output": final_answer,
                "latency_ms": 0,
            }
        )
        append_message(session_id, "assistant", final_answer, trace)
        save_waterfall_trace(trace)
        return {"answer": final_answer, "trace": trace, "intent": intent, "observations": observations}

    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_MODEL"] = settings.get("model", "gpt-4o-mini")
    provider = OpenAIProvider(api_key=openai_key, model=settings.get("model", "gpt-4o-mini"))
    final_answer = provider.generate(
        json.dumps(synthesis_payload, ensure_ascii=False, indent=2),
        system_prompt=f"{REACT_AGENT_SYSTEM_PROMPT}\n\n{FINAL_TRAVEL_SYNTHESIS_PROMPT}",
    )

    summary = f"{intent['destination']} | {intent['duration_days']} ngày | {intent['budget']} | {', '.join(intent['interests'])}"
    saved = _call_tool(
        server,
        trace,
        "save_travel_plan",
        {"session_id": session_id, "destination": intent["destination"], "summary": summary},
    )
    add_memory(session_id, "travel_plan", summary, {"destination": intent["destination"], "tool_save": saved})

    trace.append(
        {
            "step": len(trace) + 1,
            "action_type": "FINAL_ANSWER",
            "thought": "Tong hop Observation, profile va memory thanh cau tra loi cuoi cung.",
            "output": final_answer,
            "latency_ms": 0,
        }
    )

    append_message(session_id, "assistant", final_answer, trace)
    save_waterfall_trace(trace)
    return {"answer": final_answer, "trace": trace, "intent": intent, "observations": observations}


def save_waterfall_trace(trace_data: List[Dict[str, Any]]) -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
