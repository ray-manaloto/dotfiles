"""Renovate (Mend hosted) status signal.

``dotfiles-setup renovate-status`` (wrapped by ``mise run renovate-status``)
reports the health of the Mend-hosted Renovate app on this repo in one
auditable, read-only command — replacing ad-hoc ``gh``/``git`` polling
(skill -> mise task -> this module), per ``.claude/rules/mise-tasks-only.md``.

It answers three questions:

1. Is the ``renovate`` GitHub App (app id 2740 — Mend's hosted Renovate,
   NOT a separate "Mend" app) installed on the repo's org with the
   privileges Renovate needs?
2. What update PRs are currently open (the live queue)?
3. What did Renovate recently merge (automerge activity)?

The scan cadence itself is Mend-side (this tool only observes GitHub
state); see the ``renovate.json`` ``schedule`` config and docs.mend.io
for run frequency.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field

# Mend's hosted Renovate GitHub App. The "renovate" app IS "the Mend app"
# for dependency PRs; there is no separate Mend app to install for this.
_RENOVATE_APP_SLUG = "renovate"
RENOVATE_APP_ID = 2740

# The permissions Renovate must hold to open/merge PRs, manage branches,
# post the Dependency Dashboard issue, and set check statuses.
REQUIRED_PERMISSIONS: dict[str, str] = {
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "checks": "write",
    "statuses": "write",
}

_GH_TIMEOUT_S = 60.0


@dataclass
class RenovateStatus:
    """A snapshot of Renovate's install + queue state from GitHub."""

    repo: str
    owner: str
    installed: bool
    app_id: int | None = None
    repository_selection: str | None = None
    missing_permissions: list[str] = field(default_factory=list)
    open_prs: list[dict[str, str]] = field(default_factory=list)
    merged_prs: list[dict[str, str]] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        """True when the app is installed AND fully privileged."""
        return self.installed and not self.missing_permissions


def _gh(args: list[str]) -> str:
    """Run a ``gh`` command and return stdout (empty string on failure)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=_GH_TIMEOUT_S,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def _repo_slug() -> str:
    """Return ``owner/repo`` for the current repo via ``gh``."""
    out = _gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    return out.strip()


def _installation(owner: str) -> dict[str, object] | None:
    """Return the Renovate app installation record for ``owner``, or None."""
    out = _gh(
        [
            "api",
            f"/orgs/{owner}/installations",
            "--jq",
            f'.installations[]? | select(.app_slug=="{_RENOVATE_APP_SLUG}")',
        ]
    ).strip()
    if not out:
        return None
    try:
        record = json.loads(out)
    except json.JSONDecodeError:
        return None
    return record if isinstance(record, dict) else None


def permission_gaps(install: dict[str, object]) -> list[str]:
    """Return required permissions the installation does not satisfy."""
    perms = install.get("permissions")
    if not isinstance(perms, dict):
        perms = {}
    return [
        f"{name}={want}"
        for name, want in REQUIRED_PERMISSIONS.items()
        if perms.get(name) != want
    ]


def _pr_rows(state: str, limit: int) -> list[dict[str, str]]:
    """Return Renovate-authored PRs in ``state`` as {number,title} rows."""
    out = _gh(
        [
            "pr",
            "list",
            "--state",
            state,
            "--author",
            "app/renovate",
            "--limit",
            str(limit),
            "--json",
            "number,title",
        ]
    ).strip()
    if not out:
        return []
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [
        {"number": str(row.get("number", "?")), "title": str(row.get("title", ""))}
        for row in rows
        if isinstance(row, dict)
    ]


def collect_status() -> RenovateStatus:
    """Gather the full Renovate status snapshot from GitHub."""
    slug = _repo_slug()
    owner = slug.split("/", 1)[0] if "/" in slug else ""
    install = _installation(owner) if owner else None
    if install is None:
        return RenovateStatus(repo=slug, owner=owner, installed=False)
    app_id = install.get("app_id")
    selection = install.get("repository_selection")
    return RenovateStatus(
        repo=slug,
        owner=owner,
        installed=True,
        app_id=app_id if isinstance(app_id, int) else None,
        repository_selection=selection if isinstance(selection, str) else None,
        missing_permissions=permission_gaps(install),
        open_prs=_pr_rows("open", 50),
        merged_prs=_pr_rows("merged", 10),
    )


def render_report(status: RenovateStatus) -> str:
    """Render the status snapshot as a readable report."""
    repo = status.repo or "(unknown repo)"
    lines: list[str] = [f"Renovate status — {repo}", ""]

    if not status.installed:
        lines.append(
            f"✗ App NOT installed: the '{_RENOVATE_APP_SLUG}' app "
            f"(id {RENOVATE_APP_ID}) is not on org '{status.owner}'."
        )
        lines.append("  Install: https://github.com/apps/renovate")
        return "\n".join(lines)

    if status.app_id == RENOVATE_APP_ID:
        lines.append(
            f"✓ App installed: {_RENOVATE_APP_SLUG} (app id {status.app_id} — "
            f"verified Mend-hosted Renovate; no separate Mend app needed)"
        )
    else:
        lines.append(
            f"⚠ App '{_RENOVATE_APP_SLUG}' installed but app id is "
            f"{status.app_id}, not the expected {RENOVATE_APP_ID} "
            f"(Mend Renovate) — verify this is the right app."
        )
    lines.append(f"  repository_selection: {status.repository_selection}")
    if status.missing_permissions:
        lines.append(f"  ✗ MISSING privileges: {', '.join(status.missing_permissions)}")
    else:
        req = ", ".join(f"{k}={v}" for k, v in REQUIRED_PERMISSIONS.items())
        lines.append(f"  ✓ privileges present: {req}")

    lines.append("")
    lines.append(f"Open update PRs ({len(status.open_prs)}):")
    lines.extend(f"  #{pr['number']} {pr['title']}" for pr in status.open_prs)
    lines.append("")
    lines.append(f"Recently merged ({len(status.merged_prs)}):")
    lines.extend(f"  #{pr['number']} {pr['title']}" for pr in status.merged_prs)
    return "\n".join(lines)


def renovate_status_main(*, json_output: bool = False) -> int:
    """Entry point for ``dotfiles-setup renovate-status``.

    Exit non-zero only when the app is absent or under-privileged, so the
    command doubles as a gate the way ``lint``/``verify`` do.
    """
    status = collect_status()
    if json_output:
        sys.stdout.write(json.dumps(asdict(status), indent=2) + "\n")
    else:
        sys.stdout.write(render_report(status) + "\n")
    return 0 if status.healthy else 1
