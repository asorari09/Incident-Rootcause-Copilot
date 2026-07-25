"""HTTP-layer settings kept separate from the graph's cost settings."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ApiSettings:
    app_env: str = "development"
    api_key: str | None = "dev-change-me"
    allow_fake_llm: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApiSettings:
        values = os.environ if environ is None else environ
        return cls(
            app_env=values.get("APP_ENV", "development"),
            api_key=values.get("API_KEY") or None,
            allow_fake_llm=values.get("ALLOW_FAKE_LLM", "false").lower() in {"1", "true", "yes", "on"},
        )

    @property
    def require_api_key(self) -> bool:
        # Free public demos (ALLOW_FAKE_LLM=true) stay unauthenticated so the SPA works.
        if self.allow_fake_llm:
            return False
        return self.app_env != "development" and self.api_key is not None

    @property
    def default_use_fake_llm(self) -> bool:
        return self.app_env == "development" or self.allow_fake_llm
