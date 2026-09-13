"""
Real LLM provider adapters for Travel Planning ReAct Agent.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv


load_dotenv()


class BaseLLMProvider:
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider.")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = client.models.generate_content(model=self.model_name, contents=contents)
        return response.text or ""

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        function_declarations = [
            {"name": tool["name"], "description": tool.get("description", ""), "parameters": tool.get("parameters", {})}
            for tool in tools_schema
            if tool.get("name") and tool.get("parameters")
        ]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            tools=[{"function_declarations": function_declarations}] if function_declarations else None,
            temperature=0.2,
        )
        response = client.models.generate_content(model=self.model_name, contents=prompt, config=config)
        if response.function_calls:
            call = response.function_calls[0]
            args = dict(call.args) if hasattr(call, "args") and call.args else {}
            return {
                "type": "tool_call",
                "tool_name": call.name,
                "arguments": args,
                "thought": f"Gemini selected tool {call.name}.",
            }
        return {"type": "text", "content": response.text or "", "thought": "Gemini answered directly."}


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=self.model_name, messages=messages)
        return response.choices[0].message.content or ""

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            }
            for tool in tools_schema
            if tool.get("name")
        ]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            call = msg.tool_calls[0]
            args = json.loads(call.function.arguments) if call.function.arguments else {}
            return {
                "type": "tool_call",
                "tool_name": call.function.name,
                "arguments": args,
                "thought": f"OpenAI selected tool {call.function.name}.",
            }
        return {"type": "text", "content": msg.content or "", "thought": "OpenAI answered directly."}


def get_llm_provider() -> BaseLLMProvider:
    provider_type = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider_type == "openai":
        return OpenAIProvider()
    if provider_type == "gemini":
        return GeminiProvider()
    raise ValueError(f"Unsupported real LLM provider: {provider_type}")
