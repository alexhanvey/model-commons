#!/usr/bin/env python3
"""Send a small tool-calling request to an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import json
from typing import Any

from openai import OpenAI

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search project documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--api-key", default="local")
    parser.add_argument("--prompt", default="What's the weather in Paris in celsius?")
    args = parser.parse_args()

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": "You are a precise tool-calling assistant."},
            {"role": "user", "content": args.prompt},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.0,
        max_tokens=256,
    )

    message = response.choices[0].message
    print(json.dumps(message.model_dump(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
