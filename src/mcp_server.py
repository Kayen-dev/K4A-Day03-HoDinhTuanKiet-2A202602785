"""
Model Context Protocol server for the Travel Planning ReAct Agent.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class MCPTravelServer:
    """Small JSON-RPC style MCP facade around the travel tool registry."""

    def __init__(self, server_name: str = "travel-planning-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"

    def list_tools(self) -> List[Dict[str, Any]]:
        return TOOLS_SCHEMA

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_result = dispatch_tool_call(tool_name, arguments or {})
        try:
            content = json.loads(raw_result)
        except json.JSONDecodeError:
            content = {"status": "INVALID_JSON", "raw": raw_result}
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content,
        }


# Compatibility for the original lab app import.
MCPAcademicServer = MCPTravelServer


if __name__ == "__main__":
    print("==========================================================")
    print("KIEM THU MCP SERVER - Travel Planning ReAct Agent")
    print("==========================================================")

    server = MCPTravelServer()
    tools = server.list_tools()
    print(f"OK MCP Server: {server.server_name} (Version: {server.version})")
    print(f"Tools exposed: {len(tools)}")

    for tool in tools:
        print(f"- {tool['name']}: {tool.get('description', '')}")

    test_result = server.call_tool(
        "get_weather_forecast",
        {"destination": "Da Nang, Vietnam", "duration_days": 3},
    )
    print("\nSample JSON-RPC response:")
    print(json.dumps(test_result, ensure_ascii=False, indent=2))
