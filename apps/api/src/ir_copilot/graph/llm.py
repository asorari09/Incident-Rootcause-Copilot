"""Structured LLM boundary with an offline fake implementation for tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel


class StructuredLLM(Protocol):
    def generate_json(self, task: str, prompt: str, schema: type[BaseModel]) -> dict[str, Any]: ...


class UnavailableLLM:
    def generate_json(self, task: str, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        del task, prompt, schema
        raise RuntimeError("OPENAI_API_KEY is not configured; provide a FakeLLM for offline execution")


class FakeLLM:
    """Deterministic structured responses for unit tests and the explicit CLI fake mode."""

    def __init__(self, responses: dict[str, Any] | Callable[[str, str], dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def generate_json(self, task: str, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        del schema
        self.calls.append(task)
        if callable(self.responses):
            return self.responses(task, prompt)
        response = self.responses[task]
        if isinstance(response, list):
            return response.pop(0)
        return response


class OpenAIStructuredLLM:
    """The only live LLM adapter: gpt-4o-mini, temperature 0, typed responses."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_json(self, task: str, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        max_tokens = 600 if task == "hypothesize" else 800
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            temperature=0,
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("model returned no structured response")
        return parsed.model_dump()
