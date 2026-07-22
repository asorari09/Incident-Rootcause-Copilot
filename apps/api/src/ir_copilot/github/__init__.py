"""Draft-only GitHub integration with a safe local dry-run mode."""

from .client import GitHubClient, GitHubOperationResult
from .config import GitHubSettings, RepositoryNotAllowedError

__all__ = [
    "GitHubClient",
    "GitHubOperationResult",
    "GitHubSettings",
    "RepositoryNotAllowedError",
]
