"""Narrow, draft-only GitHub REST client.

Live fine-grained PAT scope: Metadata read; Issues read/write; Contents
read/write; and Pull requests read/write, all restricted to one demo repository.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import GitHubSettings

_API_ROOT = "https://api.github.com"
_DRAFT_LABEL = "ir-copilot-draft"


@dataclass(frozen=True)
class GitHubOperationResult:
    status: str
    url: str | None = None
    artifact_path: Path | None = None
    error: str | None = None
    already_exists: bool = False


class GitHubClient:
    """Read GitHub context and create only human-reviewable draft artifacts."""

    def __init__(self, settings: GitHubSettings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self._http_client = http_client

    def list_recent_commits(
        self, limit: int = 10, *, repository: str | None = None
    ) -> list[dict[str, Any]]:
        self.settings.assert_allowed_repository(repository)
        if self.settings.dry_run or not self.settings.token:
            return []
        response = self._request("GET", "/commits", params={"per_page": self._limit(limit)})
        if response is None:
            return []
        return [
            {
                "sha": commit.get("sha"),
                "message": commit.get("commit", {}).get("message", "").split("\n", 1)[0],
                "url": commit.get("html_url"),
            }
            for commit in response.json()
        ]

    def list_recent_issues(
        self, limit: int = 10, *, repository: str | None = None
    ) -> list[dict[str, Any]]:
        self.settings.assert_allowed_repository(repository)
        if self.settings.dry_run or not self.settings.token:
            return []
        response = self._request(
            "GET", "/issues", params={"state": "open", "per_page": self._limit(limit)}
        )
        if response is None:
            return []
        return [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
                "url": issue.get("html_url"),
            }
            for issue in response.json()
            if "pull_request" not in issue
        ]

    def create_draft_issue(
        self,
        title: str,
        body: str,
        labels: Iterable[str] = (),
        *,
        incident_id: str,
        repository: str | None = None,
    ) -> GitHubOperationResult:
        self.settings.assert_allowed_repository(repository)
        title, body = self._with_incident_id(title, body, incident_id)
        applied_labels = self._draft_labels(labels)
        if self.settings.dry_run:
            return self._write_outbox("issue", title, body, applied_labels, incident_id)

        existing = self._find_live_issue(incident_id)
        if existing:
            return GitHubOperationResult("existing", url=existing, already_exists=True)
        response = self._request("POST", "/issues", json={"title": title, "body": body, "labels": applied_labels})
        if response is None:
            return GitHubOperationResult("failed", error="GitHub issue creation failed")
        return GitHubOperationResult("created", url=response.json().get("html_url"))

    def create_draft_pr(
        self,
        title: str,
        body: str,
        *,
        incident_id: str,
        head: str,
        base: str = "main",
        template_patch: str,
        repository: str | None = None,
    ) -> GitHubOperationResult:
        """Create only a draft PR from a caller-provided, pre-authored patch template."""
        self.settings.assert_allowed_repository(repository)
        if not template_patch.strip():
            return GitHubOperationResult("failed", error="a pre-authored patch template is required")
        title, body = self._with_incident_id(title, body, incident_id)
        if self.settings.dry_run:
            return self._write_outbox(
                "pull-request",
                title,
                body,
                [_DRAFT_LABEL],
                incident_id,
                extra={
                    "head": head,
                    "base": base,
                    "draft": "true",
                    "template_patch": template_patch,
                },
            )

        response = self._request(
            "POST",
            "/pulls",
            json={"title": title, "body": body, "head": head, "base": base, "draft": True},
        )
        if response is None:
            return GitHubOperationResult("failed", error="GitHub draft PR creation failed")
        return GitHubOperationResult("created", url=response.json().get("html_url"))

    def _write_outbox(
        self,
        artifact_type: str,
        title: str,
        body: str,
        labels: list[str],
        incident_id: str,
        extra: dict[str, str] | None = None,
    ) -> GitHubOperationResult:
        outbox = self.settings.outbox_dir
        outbox.mkdir(parents=True, exist_ok=True)
        filename = f"{artifact_type}-{self._safe_filename(incident_id)}.md"
        path = outbox / filename
        if path.exists() and f"Incident ID: {incident_id}" in path.read_text(encoding="utf-8"):
            return GitHubOperationResult(
                "existing", url=str(path), artifact_path=path, already_exists=True
            )
        details = "\n".join(f"- {key}: {value}" for key, value in (extra or {}).items())
        contents = (
            f"# Draft GitHub {artifact_type.title()}\n\n"
            f"Repository: {self.settings.repository}\n\n"
            f"Incident ID: {incident_id}\n\n"
            f"Labels: {', '.join(labels)}\n\n"
            f"## Title\n\n{title}\n\n"
            f"## Proposed content\n\n{body}\n\n"
            "## Hypothesis\n\nTo be supplied from grounded incident evidence.\n\n"
            "## Evidence\n\nTo be supplied from detector and runbook evidence.\n"
        )
        if details:
            contents += f"\n## Draft parameters\n\n{details}\n"
        path.write_text(contents, encoding="utf-8")
        return GitHubOperationResult("dry_run", url=str(path), artifact_path=path)

    def _find_live_issue(self, incident_id: str) -> str | None:
        response = self._request(
            "GET", "/issues", params={"state": "open", "labels": _DRAFT_LABEL, "per_page": 100}
        )
        if response is None:
            return None
        marker = f"Incident ID: {incident_id}"
        for issue in response.json():
            if marker in (issue.get("body") or "") or incident_id in (issue.get("title") or ""):
                return issue.get("html_url")
        return None

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> httpx.Response | None:
        if not self.settings.token:
            return None
        client = self._http_client or httpx.Client(timeout=10.0)
        owns_client = self._http_client is None
        try:
            for attempt in range(2):
                response = client.request(
                    method,
                    f"{_API_ROOT}/repos/{self.settings.repository}{endpoint}",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {self.settings.token}",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    **kwargs,
                )
                if response.status_code not in {403, 429}:
                    response.raise_for_status()
                    return response
                if attempt == 0:
                    time.sleep(self.backoff_seconds(response.headers, attempt))
            return None
        except httpx.HTTPError:
            return None
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def backoff_seconds(headers: httpx.Headers | dict[str, str], attempt: int) -> float:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            return min(2.0**attempt, 30.0)
        return min(0.5 * (2.0**attempt), 30.0)

    @staticmethod
    def _with_incident_id(title: str, body: str, incident_id: str) -> tuple[str, str]:
        if not incident_id.strip():
            raise ValueError("incident_id is required")
        marker = f"Incident ID: {incident_id}"
        if incident_id not in title:
            title = f"[IR-Copilot {incident_id}] {title}"
        if marker not in body:
            body = f"{body.rstrip()}\n\n{marker}"
        return title, body

    @staticmethod
    def _draft_labels(labels: Iterable[str]) -> list[str]:
        return sorted({*labels, _DRAFT_LABEL})

    @staticmethod
    def _limit(limit: int) -> int:
        return max(1, min(limit, 100))

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "incident"
