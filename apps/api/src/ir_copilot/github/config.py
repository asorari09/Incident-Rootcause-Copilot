"""Environment-backed configuration for the allowlisted GitHub repository."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RepositoryNotAllowedError(ValueError):
    """Raised when a caller attempts to operate outside the configured repo."""


@dataclass(frozen=True)
class GitHubSettings:
    token: str | None
    repository: str
    dry_run: bool = True
    outbox_dir: Path = Path("data/outbox")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "GitHubSettings":
        values = os.environ if environ is None else environ
        repository = values.get("GITHUB_REPO", "youruser/incident-response-copilot")
        if not _REPOSITORY_PATTERN.fullmatch(repository):
            raise ValueError("GITHUB_REPO must use the owner/name format")
        dry_run = values.get("GITHUB_DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}
        token = values.get("GITHUB_TOKEN") or None
        return cls(token=token, repository=repository, dry_run=dry_run)

    def assert_allowed_repository(self, repository: str | None = None) -> str:
        requested = repository or self.repository
        if requested != self.repository:
            raise RepositoryNotAllowedError(
                f"repository {requested!r} is not the allowlisted repository"
            )
        return requested
