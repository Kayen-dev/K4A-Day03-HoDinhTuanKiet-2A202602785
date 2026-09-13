"""
Travel tool definitions and execution backend.

The tools are intentionally API-backed where possible so the MCP server can
observe live data instead of answering from a fixed prompt.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


HTTP_TIMEOUT = 12


TOOLS_SCHEMA = [
    {
        "name": "get_weather_forecast",
        "description": "Lay du bao thoi tiet theo diem den, ngay bat dau va so ngay du lich bang Open-Meteo.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Thanh pho hoac dia diem du lich, vi du: Da Nang, Vietnam",
                },
                "start_date": {
                    "type": "string",
                    "description": "Ngay bat dau theo dinh dang YYYY-MM-DD. Co the bo trong de dung ngay hien tai.",
                },
                "duration_days": {
                    "type": "integer",
                    "description": "So ngay can du bao, thuong tu 1 den 7.",
                },
            },
            "required": ["destination"],
        },
    },
    {
        "name": "search_travel_places",
        "description": "Tim dia diem du lich gan thanh pho theo so thich bang Wikipedia GeoSearch.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Thanh pho hoac dia diem du lich.",
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sach so thich: beach, food, culture, nature, history, nightlife, family.",
                },
                "limit": {
                    "type": "integer",
                    "description": "So dia diem toi da can tra ve.",
                },
            },
            "required": ["destination"],
        },
    },
    {
        "name": "estimate_route_distance",
        "description": "Uoc tinh khoang cach duong bo giua hai dia diem bang OSRM neu co du lieu toa do.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Diem xuat phat."},
                "destination": {"type": "string", "description": "Diem den."},
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "save_travel_plan",
        "description": "Luu tom tat ke hoach du lich da duoc agent lap de dung lai trong memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Ma phien chat hien tai."},
                "destination": {"type": "string", "description": "Diem den chinh."},
                "summary": {"type": "string", "description": "Tom tat lich trinh va quyet dinh quan trong."},
            },
            "required": ["session_id", "destination", "summary"],
        },
    },
]


SAVED_PLANS: List[Dict[str, Any]] = []


def _json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _parse_start_date(start_date: Optional[str]) -> date:
    if not start_date:
        return date.today()
    try:
        return datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _geocode(destination: str) -> Optional[Dict[str, Any]]:
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    response = requests.get(
        geo_url,
        params={"name": destination, "count": 1, "language": "vi", "format": "json"},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    first = results[0]
    return {
        "name": first.get("name", destination),
        "country": first.get("country", ""),
        "latitude": first["latitude"],
        "longitude": first["longitude"],
        "timezone": first.get("timezone", "auto"),
    }


def execute_get_weather_forecast(destination: str, start_date: str = "", duration_days: int = 3) -> str:
    try:
        place = _geocode(destination)
        if not place:
            return _json({"status": "NOT_FOUND", "message": f"Khong tim thay toa do cho '{destination}'."})

        start = _parse_start_date(start_date)
        duration = max(1, min(int(duration_days or 3), 7))
        end = start + timedelta(days=duration - 1)
        forecast_url = "https://api.open-meteo.com/v1/forecast"
        response = requests.get(
            forecast_url,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": place["timezone"],
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        daily = response.json().get("daily", {})
        days = []
        for idx, day in enumerate(daily.get("time", [])):
            rain_probability = daily.get("precipitation_probability_max", [None] * duration)[idx]
            days.append(
                {
                    "date": day,
                    "temp_min_c": daily.get("temperature_2m_min", [None] * duration)[idx],
                    "temp_max_c": daily.get("temperature_2m_max", [None] * duration)[idx],
                    "rain_probability_percent": rain_probability,
                    "weather_code": daily.get("weather_code", [None] * duration)[idx],
                    "planning_hint": "Uu tien hoat dong trong nha" if rain_probability and rain_probability >= 55 else "Phu hop hoat dong ngoai troi",
                }
            )
        return _json({"status": "SUCCESS", "source": "Open-Meteo", "place": place, "forecast": days})
    except Exception as exc:
        return _json({"status": "API_ERROR", "tool": "get_weather_forecast", "error": str(exc)})


def execute_search_travel_places(destination: str, interests: Optional[List[str]] = None, limit: int = 6) -> str:
    interests = interests or []
    limit = max(3, min(int(limit or 6), 10))
    places: List[Dict[str, Any]] = []
    source = "Wikipedia GeoSearch"
    try:
        place = _geocode(destination)
        if place:
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "geosearch",
                    "gscoord": f"{place['latitude']}|{place['longitude']}",
                    "gsradius": 10000,
                    "gslimit": limit,
                    "format": "json",
                },
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": "TravelPlanningReActAgent/1.0"},
            )
            response.raise_for_status()
            for item in response.json().get("query", {}).get("geosearch", []):
                title = item.get("title", "")
                weak_terms = ["hospital", "university", "diocese", "stadium"]
                if any(term in title.lower() for term in weak_terms):
                    continue
                places.append(
                    {
                        "name": title,
                        "distance_m": item.get("dist"),
                        "tags": interests,
                        "why": "Dia diem gan khu vuc du lich, can xep theo thoi tiet va so thich.",
                    }
                )
    except Exception as exc:
        return _json({"status": "API_ERROR", "tool": "search_travel_places", "error": str(exc)})

    if not places:
        return _json({"status": "NOT_FOUND", "source": source, "destination": destination, "message": "Wikipedia GeoSearch khong tra ve dia diem phu hop."})

    return _json({"status": "SUCCESS", "source": source, "destination": destination, "interests": interests, "places": places[:limit]})


def execute_estimate_route_distance(origin: str, destination: str) -> str:
    try:
        start = _geocode(origin)
        end = _geocode(destination)
        if not start or not end:
            return _json({"status": "NOT_FOUND", "message": "Khong tim thay toa do diem di hoac diem den."})
        route_url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start['longitude']},{start['latitude']};{end['longitude']},{end['latitude']}"
        )
        response = requests.get(route_url, params={"overview": "false"}, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        routes = response.json().get("routes") or []
        if routes:
            route = routes[0]
            return _json(
                {
                    "status": "SUCCESS",
                    "source": "OSRM",
                    "origin": start,
                    "destination": end,
                    "distance_km": round(route.get("distance", 0) / 1000, 1),
                    "duration_minutes": round(route.get("duration", 0) / 60),
                }
            )
        return _json({"status": "NOT_FOUND", "source": "OSRM", "message": "OSRM khong tra ve route phu hop.", "origin": start, "destination": end})
    except Exception as exc:
        return _json({"status": "API_ERROR", "tool": "estimate_route_distance", "error": str(exc)})


def execute_save_travel_plan(session_id: str, destination: str, summary: str) -> str:
    item = {
        "session_id": session_id,
        "destination": destination,
        "summary": summary,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    SAVED_PLANS.append(item)
    return _json({"status": "SUCCESS", "message": "Da luu ke hoach vao memory cua phien.", "plan": item})


TOOL_ROUTER = {
    "get_weather_forecast": execute_get_weather_forecast,
    "search_travel_places": execute_search_travel_places,
    "estimate_route_distance": execute_estimate_route_distance,
    "save_travel_plan": execute_save_travel_plan,
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as exc:
            return _json({"status": "EXECUTION_ERROR", "error": str(exc)})
    return _json({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' khong ton tai."})
