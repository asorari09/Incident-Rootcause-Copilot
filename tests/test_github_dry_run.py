"""Offline tests for the draft-only GitHub boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ir_copilot.github import GitHubClient, GitHubSettings, RepositoryNotAllowedError


class GitHubDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_dir = tempfile.TemporaryDirectory()
        self.outbox = Path(self.temporary_dir.name) / "outbox"
        self.settings = GitHubSettings(
            token=None,
            repository="demo-owner/incident-response-copilot",
            dry_run=True,
            outbox_dir=self.outbox,
        )
        self.client = GitHubClient(self.settings)

    def tearDown(self) -> None:
        self.temporary_dir.cleanup()

    def test_dry_run_issue_writes_traceable_markdown_artifact(self) -> None:
        result = self.client.create_draft_issue(
            "Database pool exhausted",
            "Detector identified high database pool utilization.",
            labels=["severity:high"],
            incident_id="inc-123",
        )

        self.assertEqual(result.status, "dry_run")
        self.assertIsNotNone(result.artifact_path)
        content = result.artifact_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        self.assertIn("Incident ID: inc-123", content)
        self.assertIn("ir-copilot-draft", content)
        self.assertIn("## Hypothesis", content)
        self.assertIn("## Evidence", content)

    def test_dry_run_is_idempotent_by_incident_id(self) -> None:
        first = self.client.create_draft_issue("First", "body", incident_id="inc-123")
        second = self.client.create_draft_issue("Second", "body", incident_id="inc-123")

        self.assertEqual(first.status, "dry_run")
        self.assertEqual(second.status, "existing")
        self.assertTrue(second.already_exists)

    def test_dry_run_pr_requires_and_records_a_template_patch(self) -> None:
        result = self.client.create_draft_pr(
            "Revert known regression",
            "Prepared for human review.",
            incident_id="inc-pr-1",
            head="ir-copilot/inc-pr-1",
            template_patch="diff --git a/example b/example",
        )

        content = result.artifact_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        self.assertEqual(result.status, "dry_run")
        self.assertIn("- draft: true", content)
        self.assertIn("template_patch", content)

    def test_allowlist_rejects_repo_override(self) -> None:
        with self.assertRaises(RepositoryNotAllowedError):
            self.client.create_draft_issue(
                "Unexpected repository",
                "body",
                incident_id="inc-456",
                repository="other-owner/other-repo",
            )

    def test_dry_run_reads_are_empty_and_network_free(self) -> None:
        self.assertEqual(self.client.list_recent_commits(), [])
        self.assertEqual(self.client.list_recent_issues(), [])

    def test_github_package_contains_no_forbidden_mutation_tools(self) -> None:
        package_dir = Path(__file__).resolve().parents[1] / "apps/api/src/ir_copilot/github"
        source = "\n".join(path.read_text(encoding="utf-8") for path in package_dir.glob("*.py"))
        for forbidden in ("merge_pull_request", "force_push", "kubectl_", "delete_"):
            self.assertNotIn(forbidden, source)
