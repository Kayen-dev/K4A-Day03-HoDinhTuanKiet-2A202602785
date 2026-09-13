# Travel Planning ReAct Agent - Plan & Architecture

## Goal

Build a local web app for a personalized travel assistant that combines:

- LLM/GPT final synthesis
- ReAct-style tool observations
- MCP JSON-RPC tool server
- External APIs for live travel data
- Local chat windows and memory
- First-run user profile onboarding

## External APIs

| Capability | Tool | External API |
|---|---|---|
| Weather forecast | `get_weather_forecast` | Open-Meteo Geocoding + Forecast |
| Places discovery | `search_travel_places` | Wikipedia GeoSearch |
| Route estimate | `estimate_route_distance` | OSRM public routing |
| Memory action | `save_travel_plan` | Local JSON memory |

## User Flow

1. User opens `http://127.0.0.1:7860`.
2. User fills basic profile: name, origin city, travel style, budget, interests, food/mobility notes.
3. User enters OpenAI API key in Settings. This is required for final GPT synthesis.
4. User chats in a trip window.
5. Agent extracts destination, duration, dates, budget, interests and origin city.
6. Agent calls MCP tools to get observations.
7. Agent synthesizes an itinerary using GPT through OpenAI API. If no key is configured, the app stops with a clear configuration message instead of using mock output.
8. Conversation, trace and memory are saved locally.

## Local Data

Runtime state is saved at:

```text
data/travel_agent_state.json
```

Waterfall trace is saved at:

```text
docs/trace_waterfall.json
```

OpenAI settings are written to:

```text
.env
```

This project is configured for real API mode only. It does not use mock LLM answers.

## Run

```powershell
py src\web_app.py
```

Open:

```text
http://127.0.0.1:7860
```

CLI alternatives:

```powershell
py src\app.py --interactive
py src\app.py --all
```
