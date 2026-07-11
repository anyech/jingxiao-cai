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
        pr = self.pr(98021, "feat: support GPT-5.6 Ultra across OpenClaw and Codex runtimes")

        rendered = updater.pr_link(pr)

        self.assertIn("#98021", rendered)
        self.assertIn("GPT-5.6 Ultra cross-runtime integration", rendered)
        self.assertNotIn("support GPT-5.6 Ultra across OpenClaw and Codex runtimes", html.unescape(rendered))

    def test_unknown_prs_fail_closed_before_public_section_generation(self) -> None:
        unknown = self.pr(999999, "private or raw PR title should not leak")

        self.assertEqual(updater.unknown_scope_prs([unknown]), [unknown])
        with self.assertRaisesRegex(RuntimeError, "missing from KNOWN_SCOPE"):
            updater.pr_link(unknown)

    def test_build_section_uses_approved_labels_and_count(self) -> None:
        prs = [self.pr(98021), self.pr(90487, "raw title")]

        section = updater.build_section(prs)

        self.assertIn("Contributed 2 merged upstream PRs", section)
        self.assertIn("GPT-5.6 Ultra cross-runtime integration", section)
        self.assertIn("ChatGPT/Codex Responses SSE stream hardening", section)
        self.assertNotIn("raw title", section)


if __name__ == "__main__":
    unittest.main()
