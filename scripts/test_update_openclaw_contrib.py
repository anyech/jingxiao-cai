#!/usr/bin/env python3
"""Focused regression tests for the OpenClaw contribution updater."""

from __future__ import annotations

import html
import unittest
from unittest import mock

import update_openclaw_contrib as updater


class OpenClawContribUpdaterTests(unittest.TestCase):
    def pr(self, number: int, title: str = "raw GitHub title") -> dict[str, str | int]:
        return {
            "number": number,
            "title": title,
            "url": f"https://github.com/{updater.GITHUB_REPO}/pull/{number}",
            "merged_at": "2026-06-22T17:49:58Z",
        }

    def test_latest_reviewed_pr_has_public_scope_label(self) -> None:
        pr = self.pr(131669, "fix(workers): honor session tool policies on cloud sessions")

        rendered = updater.pr_link(pr)

        self.assertIn("#131669", rendered)
        self.assertIn("cloud-worker session-tool policy enforcement", rendered)
        self.assertNotIn("honor session tool policies on cloud sessions", html.unescape(rendered))

    def test_unknown_prs_fail_closed_before_public_section_generation(self) -> None:
        unknown = self.pr(999999, "private or raw PR title should not leak")

        self.assertEqual(updater.unknown_scope_prs([unknown]), [unknown])
        with self.assertRaisesRegex(RuntimeError, "missing from KNOWN_SCOPE"):
            updater.pr_link(unknown)

    def test_build_section_uses_approved_labels_and_count(self) -> None:
        prs = [self.pr(128078), self.pr(90487, "raw title")]

        section = updater.build_section(prs)

        self.assertIn("Contributed 2 merged upstream PRs", section)
        self.assertIn("sqlite-vec KNN isolation and reindex safety", section)
        self.assertIn("ChatGPT/Codex Responses SSE stream hardening", section)
        self.assertNotIn("raw title", section)

    @mock.patch.object(updater.subprocess, "run")
    def test_sync_blog_delegates_with_bounded_freshness(self, run_mock) -> None:
        run_mock.return_value = mock.Mock(returncode=0, stdout='{"ok": true}\n', stderr="")

        coordinator = mock.Mock()
        coordinator.is_file.return_value = True
        coordinator.parent.parent = updater.REPO_ROOT
        with mock.patch.object(updater, "BLOG_COORDINATOR", coordinator), mock.patch.object(
            updater.sys.stdout,
            "write",
        ):
            code = updater.delegate_public_surface_sync(
                pull=True,
                commit_push=True,
                json_output=True,
                max_age_days=30,
            )

        self.assertEqual(code, 0)
        argv = run_mock.call_args.args[0]
        self.assertIn("--pull", argv)
        self.assertIn("--commit-push", argv)
        self.assertIn("--json", argv)
        self.assertEqual(argv[argv.index("--max-age-days") + 1], "30")


if __name__ == "__main__":
    unittest.main()
