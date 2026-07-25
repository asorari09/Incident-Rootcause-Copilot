"""Small application settings shared by the fixed incident graph."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

ALLOWED_OPENAI_MODELS = {"gpt-4o-mini"}


@dataclass(frozen=True)
class AppSettings:
    openai_api_key: str | None
    app_version: str = "0.1.0"
    openai_model: str = "gpt-4o-mini"
    max_llm_calls_per_run: int = 3
    llm_temperature: float = 0.0
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None

    def __post_init__(self) -> None:
        if self.openai_model not in ALLOWED_OPENAI_MODELS:
            raise ValueError(f"OPENAI_MODEL must be one of {sorted(ALLOWED_OPENAI_MODELS)}")
        if self.max_llm_calls_per_run < 1 or self.max_llm_calls_per_run > 3:
            raise ValueError("MAX_LLM_CALLS_PER_RUN must be between 1 and 3")
        if self.llm_temperature != 0:
            raise ValueError("LLM_TEMPERATURE must be 0 for incident reasoning")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AppSettings:
        values = os.environ if environ is None else environ
        return cls(
            openai_api_key=values.get("OPENAI_API_KEY") or None,
            app_version=values.get("APP_VERSION", "0.1.0"),
            openai_model=values.get("OPENAI_MODEL", "gpt-4o-mini"),
            max_llm_calls_per_run=int(values.get("MAX_LLM_CALLS_PER_RUN", "3")),
            llm_temperature=float(values.get("LLM_TEMPERATURE", "0")),
            langfuse_enabled=values.get("LANGFUSE_ENABLED", "false").lower() == "true",
            langfuse_public_key=values.get("LANGFUSE_PUBLIC_KEY") or None,
            langfuse_secret_key=values.get("LANGFUSE_SECRET_KEY") or None,
            langfuse_host=values.get("LANGFUSE_HOST") or None,
        )
