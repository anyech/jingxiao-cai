#!/usr/bin/env python3
"""Focused regression tests for the OpenClaw contribution updater."""

from __future__ import annotations

import html
import unittest

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
        pr = self.pr(84708, "fix(agents): recover message-tool mirror replay poison")

        rendered = updater.pr_link(pr)

        self.assertIn("#84708", rendered)
        self.assertIn("message-tool mirror replay recovery", rendered)
        self.assertNotIn("recover message-tool mirror replay poison", html.unescape(rendered))

    def test_unknown_prs_fail_closed_before_public_section_generation(self) -> None:
        unknown = self.pr(999999, "private or raw PR title should not leak")

        self.assertEqual(updater.unknown_scope_prs([unknown]), [unknown])
        with self.assertRaisesRegex(RuntimeError, "missing from KNOWN_SCOPE"):
            updater.pr_link(unknown)

    def test_build_section_uses_approved_labels_and_count(self) -> None:
        prs = [self.pr(84708), self.pr(90487, "raw title")]

        section = updater.build_section(prs)

        self.assertIn("Contributed 2 merged upstream PRs", section)
        self.assertIn("message-tool mirror replay recovery", section)
        self.assertIn("ChatGPT/Codex Responses SSE stream hardening", section)
        self.assertNotIn("raw title", section)


if __name__ == "__main__":
    unittest.main()
