#!/usr/bin/env python3
"""Update the OpenClaw contribution section on Jingxiao Cai's personal site.

The script is intentionally small and dependency-free so it can run from cron.
It queries GitHub for merged PRs authored by @anyech in openclaw/openclaw,
regenerates the Open Source section, and optionally commits/pushes the change.
"""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "index.html"
GITHUB_REPO = "openclaw/openclaw"
GITHUB_AUTHOR = "anyech"
CONTRIBUTORS_URL = "https://openclaws.io/contributors/"
SITE_URL = "https://anyech.github.io/jingxiao-cai/"
LIVE_VERIFY_TIMEOUT_SECONDS = 120
LIVE_VERIFY_INTERVAL_SECONDS = 10

# Keep exact public-facing scopes for known PRs. Unknown future merged PRs must
# stop automatic publishing and request review instead of falling back to raw
# GitHub titles on the public personal site.
KNOWN_SCOPE = {
    88159: "logs-follow journal fallback retry",
    80947: "QMD session-recall gate diagnostics",
    84708: "message-tool mirror replay recovery",
    90487: "ChatGPT/Codex Responses SSE stream hardening",
    92362: "single-session row metadata context",
    89279: "Discord ACP thread completion delivery",
    86455: "sessions_yield abort lock release",
    85652: "Gateway prompt-history stream-error filtering",
    80042: "Discord verbose tool progress delivery",
    76052: "topic-suffixed session locks",
    70936: "PDF.js standard fonts",
    51329: "Codex extraction fallback",
}

SECTION_RE = re.compile(
    r"\n    <section class=\"container\">\n        <h2>Open Source</h2>.*?\n    </section>\n",
    re.DOTALL,
)
SKILLS_MARKER = '\n    <section class="container">\n        <h2>Skills</h2>'


def run(cmd: list[str], *, cwd: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    credential_file = Path.home() / ".openclaw" / "credentials" / "github" / "token"
    if not credential_file.exists():
        return None
    for raw_line in credential_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("GITHUB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'") or None
        return line
    return None


def fetch_merged_prs() -> list[dict[str, str | int]]:
    query = f"repo:{GITHUB_REPO} author:{GITHUB_AUTHOR} type:pr is:merged"
    params = urllib.parse.urlencode({"q": query, "per_page": 100, "sort": "updated", "order": "desc"})
    url = f"https://api.github.com/search/issues?{params}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "jingxiao-cai-site-openclaw-contrib-updater",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)

    prs: list[dict[str, str | int]] = []
    for item in data.get("items", []):
        pull = item.get("pull_request") or {}
        merged_at = pull.get("merged_at") or item.get("closed_at") or ""
        number = int(item["number"])
        prs.append(
            {
                "number": number,
                "title": str(item.get("title") or f"PR #{number}"),
                "url": str(item.get("html_url") or pull.get("html_url") or f"https://github.com/{GITHUB_REPO}/pull/{number}"),
                "merged_at": str(merged_at),
            }
        )
    prs.sort(key=lambda pr: str(pr["merged_at"]), reverse=True)
    return prs


def pr_link(pr: dict[str, str | int]) -> str:
    number = int(pr["number"])
    url = html.escape(str(pr["url"]), quote=True)
    if number not in KNOWN_SCOPE:
        raise RuntimeError(f"PR #{number} is missing from KNOWN_SCOPE; refusing public auto-publish")
    label = html.escape(KNOWN_SCOPE[number], quote=False)
    return f'<a href="{url}" target="_blank" style="color: var(--primary);">#{number}</a> ({label})'


def unknown_scope_prs(prs: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
    return [pr for pr in prs if int(pr["number"]) not in KNOWN_SCOPE]


def build_section(prs: list[dict[str, str | int]]) -> str:
    if not prs:
        raise RuntimeError("GitHub returned zero merged OpenClaw PRs for @anyech; refusing to erase section")

    count = len(prs)
    pr_word = "PR" if count == 1 else "PRs"
    selected = prs[:6]
    selected_intro = "selected PR" if len(selected) == 1 else "selected PRs"
    selected_links = ", ".join(pr_link(pr) for pr in selected)
    if len(prs) > len(selected):
        selected_links += f", and {len(prs) - len(selected)} more"

    return f'''
    <section class="container">
        <h2>Open Source</h2>
        <!-- openclaw-contrib:auto-generated by scripts/update_openclaw_contrib.py -->
        <div class="experience-item">
            <div class="exp-header">
                <div>
                    <div class="exp-title">Upstream Contributor</div>
                    <div class="exp-company">OpenClaw · AI-agent / personal-assistant platform</div>
                </div>
                <div class="exp-date">2026</div>
            </div>
            <div class="exp-description">
                <ul>
                    <li>Contributed {count} merged upstream {pr_word} to OpenClaw with regression coverage, focused on AI-agent gateway/runtime reliability, tool-progress delivery, and document extraction correctness; {selected_intro}: {selected_links}.</li>
                    <li>Listed as <a href="{CONTRIBUTORS_URL}" target="_blank" style="color: var(--primary);">@anyech</a> on the official contributors page; work includes TypeScript gateway/runtime correctness, Discord/tool-progress delivery, PDF.js/package-layout handling, and LLM-integrated document extraction.</li>
                </ul>
            </div>
        </div>
    </section>
'''


def update_index(prs: list[dict[str, str | int]]) -> bool:
    text = INDEX_HTML.read_text()
    section = build_section(prs).strip("\n")
    without_old, replacements = SECTION_RE.subn("\n", text, count=1)
    if replacements != 1:
        raise RuntimeError("Expected exactly one Open Source section to replace")
    if SKILLS_MARKER not in without_old:
        raise RuntimeError("Could not find Skills section insertion point")

    # Keep the section after Experience and before Skills without accumulating blank lines
    # on repeated idempotency runs.
    without_old = re.sub(
        r"\n{3,}(?=    <section class=\"container\">\n        <h2>Skills</h2>)",
        "\n\n",
        without_old,
    )
    updated = without_old.replace(SKILLS_MARKER, "\n" + section + SKILLS_MARKER, 1)
    updated = re.sub(
        r"\n{3,}(?=    <section class=\"container\">\n        <h2>Open Source</h2>)",
        "\n\n",
        updated,
    )
    updated = re.sub(
        r"(</section>)\n{3,}(?=    <section class=\"container\">\n        <h2>Skills</h2>)",
        r"\1\n\n",
        updated,
    )
    if not updated.endswith("\n"):
        updated += "\n"
    if updated == text:
        return False
    INDEX_HTML.write_text(updated)
    return True


def basic_validate() -> None:
    text = INDEX_HTML.read_text()
    checks = {
        "single_body_close": text.count("</body>") == 1,
        "single_html_close": text.count("</html>") == 1,
        "open_source_section": "<h2>Open Source</h2>" in text,
        "skills_after_open_source": text.index("<h2>Open Source</h2>") < text.index("<h2>Skills</h2>"),
        "experience_before_open_source": text.index("<h2>Experience</h2>") < text.index("<h2>Open Source</h2>"),
        "no_corrupt_tail": "</html>ml>" not in text and "</html>footer>" not in text,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError(f"index.html validation failed: {', '.join(failed)}")
    diff_check = run(["git", "diff", "--check"])
    if diff_check.stdout.strip():
        print(diff_check.stdout, file=sys.stderr)
    run([sys.executable, "scripts/test_update_openclaw_contrib.py"])


def commit_and_push() -> tuple[bool, str | None]:
    managed_paths = [
        "index.html",
        "scripts/update_openclaw_contrib.py",
        "scripts/test_update_openclaw_contrib.py",
    ]
    status = run(["git", "status", "--short", "--", *managed_paths]).stdout.strip()
    if not status:
        return False, None
    run(["git", "add", *managed_paths])
    msg = "Update OpenClaw contributor highlight"
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "main"])
    commit = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    return True, commit


def verify_live_site(prs: list[dict[str, str | int]]) -> dict[str, object]:
    """Fetch GitHub Pages after push and verify the refreshed section is live."""

    expected_count = len(prs)
    selected = prs[:6]
    deadline = time.monotonic() + LIVE_VERIFY_TIMEOUT_SECONDS
    attempts = 0
    last_error = ""
    last_checks: dict[str, bool] = {}
    url = SITE_URL

    while True:
        attempts += 1
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "User-Agent": "jingxiao-cai-site-openclaw-contrib-live-verify",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                status = getattr(response, "status", response.getcode())
                body = response.read().decode("utf-8", errors="replace")
            if status != 200:
                raise RuntimeError(f"HTTP {status}")

            selected_links_ok = all(
                f"https://github.com/{GITHUB_REPO}/pull/{int(pr['number'])}" in body
                for pr in selected
            )
            selected_scope_labels_ok = all(
                KNOWN_SCOPE[int(pr["number"])] in body
                for pr in selected
            )
            last_checks = {
                "http_200": True,
                "open_source_section": "<h2>Open Source</h2>" in body,
                "expected_count": re.search(
                    rf"Contributed\s+{expected_count}\s+merged upstream PRs?",
                    body,
                )
                is not None,
                "latest_pr_link": f"https://github.com/{GITHUB_REPO}/pull/{int(prs[0]['number'])}" in body,
                "selected_pr_links": selected_links_ok,
                "selected_scope_labels": selected_scope_labels_ok,
            }
            if all(last_checks.values()):
                return {"ok": True, "url": url, "attempts": attempts, "checks": last_checks}
            failed = ", ".join(name for name, ok in last_checks.items() if not ok)
            last_error = f"failed checks: {failed}"
        except Exception as exc:  # pragma: no cover - exercised by live cron
            last_error = str(exc)
            if not last_checks:
                last_checks = {"http_200": False}

        if time.monotonic() >= deadline:
            return {
                "ok": False,
                "url": url,
                "attempts": attempts,
                "checks": last_checks,
                "error": last_error,
            }
        time.sleep(LIVE_VERIFY_INTERVAL_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit-push", action="store_true", help="Commit and push if index.html changes")
    parser.add_argument("--pull", action="store_true", help="Fast-forward from origin/main before updating")
    parser.add_argument("--json", action="store_true", help="Emit a compact JSON summary")
    args = parser.parse_args()

    if args.pull:
        run(["git", "pull", "--ff-only", "origin", "main"])

    prs = fetch_merged_prs()
    unknown = unknown_scope_prs(prs)
    if unknown:
        summary = {
            "ok": True,
            "reviewNeeded": True,
            "reason": "unknown_pr_scope",
            "mergedPrCount": len(prs),
            "latestPr": prs[0] if prs else None,
            "unknownPrs": unknown,
            "changed": False,
            "pushed": False,
            "commit": None,
            "liveVerification": None,
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(summary)
        return 0

    changed = update_index(prs)
    basic_validate()
    pushed = False
    commit = None
    live_verification = None
    if args.commit_push:
        should_verify_existing_live = changed
        pushed, commit = commit_and_push()
        if pushed:
            live_verification = verify_live_site(prs)
        elif should_verify_existing_live:
            live_verification = verify_live_site(prs)

    summary = {
        "ok": not live_verification or bool(live_verification.get("ok")),
        "reviewNeeded": False,
        "mergedPrCount": len(prs),
        "latestPr": prs[0] if prs else None,
        "changed": changed,
        "pushed": pushed,
        "commit": commit,
        "liveVerification": live_verification,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(summary)
    if live_verification and not live_verification.get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
