"""HTTP-layer settings kept separate from the graph's cost settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ApiSettings:
    app_env: str = "development"
    api_key: str | None = "dev-change-me"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "ApiSettings":
        values = os.environ if environ is None else environ
        return cls(
            app_env=values.get("APP_ENV", "development"),
            api_key=values.get("API_KEY") or None,
        )

    @property
    def require_api_key(self) -> bool:
        return self.app_env != "development" and self.api_key is not None
