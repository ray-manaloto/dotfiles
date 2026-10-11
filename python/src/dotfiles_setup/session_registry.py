# Copyright (c) 2026 Raymond Manaloto
"""Read-only provider-qualified fleet inventory and authorized lane cards.

The dictionary aliases are public wire shapes, not handwritten model classes.
Harness labels never establish process death or coordinator ownership.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotfiles_setup import handoff_inbox, session_ledger
from dotfiles_setup.session_common import (
    SessionError,
    default_jobs_dir,
    main_checkout,
    state_lock,
    write_state,
)

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Iterable

    from dotfiles_setup.session_common import Runner

RegistrySnapshot = dict[str, Any]
CardWriteResult = dict[str, Any]
IssueIntent = dict[str, Any]
_TIMEOUT = 30
_MAX_CODEX_SOURCES = 10000
_MILLISECONDS_PER_SECOND = 1000
_ALLOWED_REPOS = {"ray-manaloto/dotfiles", "ray-manaloto/knowledge-base"}
_ISSUE_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+")


def _run(argv: list[str], runner: Runner | None) -> subprocess.CompletedProcess[str]:
    return (runner or subprocess.run)(
        argv, capture_output=True, text=True, check=False, timeout=_TIMEOUT
    )


def _stamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        return (
            parsed.astimezone(UTC)
            if parsed.tzinfo
            else datetime.min.replace(tzinfo=UTC)
        )
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def repository_topology(root: Path, *, runner: Runner | None = None) -> dict[str, Any]:
    """Resolve canonical main, remote identity and every registered worktree."""
    main = main_checkout(root, runner=runner)
    result = _run(["git", "-C", str(main), "worktree", "list", "--porcelain"], runner)
    if result.returncode:
        msg = f"worktree inventory exited {result.returncode}"
        raise SessionError(msg)
    worktrees: list[dict[str, str]] = []
    for block in result.stdout.strip().split("\n\n"):
        row: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            if key == "worktree":
                row["path"] = str(Path(value).resolve())
            elif key == "HEAD":
                row["head_sha"] = value
            elif key == "branch":
                row["branch"] = value.removeprefix("refs/heads/")
        if row.get("path"):
            row.setdefault("branch", "detached")
            row.setdefault("head_sha", "unknown")
            worktrees.append(row)
    remote = _run(["git", "-C", str(main), "remote", "get-url", "origin"], runner)
    match = (
        re.fullmatch(
            r"(?:git@github\.com:|https://github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?",
            remote.stdout.strip(),
        )
        if remote.returncode == 0
        else None
    )
    github_repo = match[1] if match else ""
    return {
        "repo_key": github_repo or f"unresolved:{main.name}",
        "github_repo": github_repo,
        "canonical_main": str(main),
        "worktrees": worktrees,
    }


def default_roots(root: Path, *, runner: Runner | None = None) -> tuple[Path, Path]:
    """Return the dotfiles main and sibling KB; topology establishes membership."""
    main = main_checkout(root, runner=runner)
    return main, main.parent / "knowledge-base"


def _role(name: object) -> str:
    if not isinstance(name, str) or not name:
        return "unknown"
    feature = name.rsplit(".", 1)[-1]
    if feature == "coordinator":
        return "coordinator"
    return "watcher" if feature in {"watch", "watcher"} else "lane"


def _started_at(row: dict[str, Any]) -> str:
    value = row.get("startedAt", row.get("timestamp", ""))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(
                value / _MILLISECONDS_PER_SECOND, UTC
            ).isoformat()
        except ValueError, OverflowError, OSError:
            return str(value)
    return str(value)


def _session(
    row: dict[str, Any], provider: str, repositories: list[dict[str, Any]], at: str
) -> dict[str, Any]:
    cwd = str(Path(str(row.get("cwd", ""))).resolve()) if row.get("cwd") else ""
    repo = next(
        (
            repo
            for repo in repositories
            if any(w["path"] == cwd for w in repo["worktrees"])
        ),
        None,
    )
    session_id = str(row.get("sessionId", row.get("id", "")))
    name = row.get("name") if isinstance(row.get("name"), str) else None
    raw_state = str(row.get("state", "unknown"))
    normalized = {"running": "working", "idle": "working", "completed": "done"}.get(
        raw_state, raw_state
    )
    if normalized not in {"working", "blocked", "stopped", "done"}:
        normalized = "unknown"
    return {
        "provider": provider,
        "session_id": session_id,
        "name": name,
        "role": _role(name),
        "repo_key": repo["repo_key"] if repo else None,
        "cwd": cwd,
        "started_at": _started_at(row),
        "raw_state": raw_state,
        "normalized_state": normalized,
        "liveness": {
            "status": "unknown",
            "observed_at": at,
            "probe_kind": "inventory-only",
            "process_identity": None,
        },
        "lineage": [],
        "task_refs": [],
        "issue_urls": [],
        "evidence_refs": [],
        "done_tasks": [],
        "open_tasks": [],
        "research_questions": [],
        "blockers": [],
        "suggestions": [],
        "source_timestamps": {},
    }


def _enrich(session: dict[str, Any], repo: dict[str, Any]) -> None:
    main = Path(repo["canonical_main"])
    name = session["name"]
    lane = name.rsplit(".", 1)[-1] if name else ""
    paths = [main / "task_plan.md"]
    if lane and re.fullmatch(r"[\w.-]+", lane):
        paths.append(main / ".agent/plans/handoff-inbox" / f"{lane}.md")
    fields = {
        "done": "done_tasks",
        "research": "research_questions",
        "question": "research_questions",
        "block": "blockers",
        "suggest": "suggestions",
    }
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
            modified = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        except OSError:
            continue
        session["evidence_refs"].append(str(path))
        session["source_timestamps"][str(path)] = modified
        section = "open_tasks"
        relevant = path.name != "task_plan.md"
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.startswith("#"):
                section = next(
                    (field for token, field in fields.items() if token in line.lower()),
                    "open_tasks",
                )
                relevant = path.name != "task_plan.md" or bool(lane and lane in line)
            if (
                not relevant
                and not (name and name in line)
                and not (lane and lane in line)
            ):
                continue
            session["issue_urls"].extend(_ISSUE_URL.findall(line))
            if line.startswith(("- ", "* ")):
                field = "done_tasks" if line.startswith("- [x]") else section
                session[field].append(line[:1024])
                session["task_refs"].append(f"{path}:{line_number}")
    session["issue_urls"] = sorted(set(session["issue_urls"]))


def _recorded_lineage(
    sessions: list[dict[str, Any]], repositories: list[dict[str, Any]]
) -> None:
    for repo in repositories:
        directory = Path(repo["canonical_main"]) / ".agent/state/coordinator-handoff"
        for path in sorted(directory.glob("*.json")):
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except OSError, ValueError:
                continue
            launch = state.get("launch") if isinstance(state, dict) else None
            if not isinstance(launch, dict) or not isinstance(
                launch.get("successor"), str
            ):
                continue
            predecessor = next(
                (
                    row
                    for row in sessions
                    if row["provider"] == "claude"
                    and row["session_id"] == path.stem
                    and row["repo_key"] == repo["repo_key"]
                ),
                None,
            )
            successors = [
                row
                for row in sessions
                if row["provider"] == "claude"
                and row["name"] == launch["successor"]
                and row["repo_key"] == repo["repo_key"]
            ]
            if predecessor and len(successors) == 1:
                successors[0]["lineage"].append(
                    {
                        "predecessor": f"claude:{predecessor['session_id']}",
                        "successor": f"claude:{successors[0]['session_id']}",
                        "evidence_ref": str(path),
                    }
                )


def collapse_chains(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse role summaries, preserving members and predecessor evidence."""
    connected: dict[str, str] = {}
    for session in sessions:
        for edge in session["lineage"]:
            connected[edge["successor"]] = edge["predecessor"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        identity = f"{session['provider']}:{session['session_id']}"
        seen = {identity}
        while identity in connected and connected[identity] not in seen:
            identity = connected[identity]
            seen.add(identity)
        role = session["role"]
        key = (
            f"{session['repo_key']}:{role}"
            if role in {"coordinator", "watcher"}
            else f"{session['repo_key']}:{identity}"
        )
        grouped.setdefault(key, []).append(session)
    chains = []
    for key, members in sorted(grouped.items()):
        ordered = sorted(
            members,
            key=lambda row: (
                _stamp(row["started_at"]),
                f"{row['provider']}:{row['session_id']}",
            ),
        )
        ids = [f"{row['provider']}:{row['session_id']}" for row in ordered]
        chains.append(
            {
                "stable_key": key,
                "repo_key": ordered[-1]["repo_key"],
                "role": ordered[-1]["role"],
                "member_session_ids": ids,
                "display_session_id": ids[-1],
                "predecessor_edges": [
                    edge for row in members for edge in row["lineage"]
                ],
                "ownership": "unknown",
                "conflicts": ids
                if sum(row["liveness"]["status"] == "live" for row in members) > 1
                else [],
            }
        )
    return chains


def _claude_inventory(
    repositories: list[dict[str, Any]],
    at: str,
    omissions: list[str],
    runner: Runner | None,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    try:
        result = _run(["claude", "agents", "--json", "--all"], runner)
        rows = json.loads(result.stdout) if result.returncode == 0 else None
        if not isinstance(rows, list):
            omissions.append(
                f"claude agents inventory unavailable: rc={result.returncode}"
            )
        else:
            for row in rows:
                if not isinstance(row, dict) or not all(
                    key in row
                    for key in ("cwd", "id", "kind", "sessionId", "startedAt", "state")
                ):
                    omissions.append("claude agents malformed inventory row")
                    continue
                session = _session(row, "claude", repositories, at)
                if session["repo_key"] is None:
                    omissions.append(
                        f"unregistered session cwd: claude:{session['session_id']}"
                    )
                sessions.append(session)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        omissions.append(f"claude agents inventory unavailable: {type(exc).__name__}")
    return sessions


def _codex_inventory(
    repositories: list[dict[str, Any]],
    at: str,
    omissions: list[str],
    bases: session_ledger.TranscriptBases,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    codex_base = (
        bases.codex if bases.codex is not None else session_ledger.codex_sessions_base()
    )
    try:
        if not codex_base.is_dir():
            omissions.append("codex inventory unavailable: sessions directory absent")
            return sessions
        paths = sorted(codex_base.rglob("*.jsonl"))
        if len(paths) > _MAX_CODEX_SOURCES:
            omissions.append(
                f"codex inventory truncated: {len(paths) - _MAX_CODEX_SOURCES} sources"
            )
        for path in paths[:_MAX_CODEX_SOURCES]:
            meta = session_ledger.first_session_meta(path)
            if meta is None:
                omissions.append("codex inventory missing session metadata")
                continue
            row = {
                **meta,
                "sessionId": meta.get("session_id", meta.get("id", "")),
                "state": "unknown",
            }
            session = _session(row, "codex", repositories, at)
            if session["repo_key"] is not None:
                sessions.append(session)
    except OSError:
        omissions.append("codex inventory unreadable")
    return sessions


def collect(
    roots: Iterable[Path],
    *,
    runner: Runner | None = None,
    bases: session_ledger.TranscriptBases = session_ledger.DEFAULT_TRANSCRIPT_BASES,
    clock: Callable[[], datetime] | None = None,
) -> RegistrySnapshot:
    """Collect bounded inventory; failures become explicit omissions."""
    at = (clock() if clock else datetime.now(UTC)).isoformat()
    repositories: list[dict[str, Any]] = []
    omissions: list[str] = []
    for root in roots:
        try:
            repo = repository_topology(root, runner=runner)
            if repo not in repositories:
                repositories.append(repo)
        except (SessionError, OSError, subprocess.TimeoutExpired) as exc:
            omissions.append(f"repository inventory unavailable: {root}: {exc}")
    sessions = _claude_inventory(repositories, at, omissions, runner)
    sessions.extend(_codex_inventory(repositories, at, omissions, bases))
    sessions = list(
        {f"{row['provider']}:{row['session_id']}": row for row in sessions}.values()
    )
    for session in sessions:
        repo = next(
            (repo for repo in repositories if repo["repo_key"] == session["repo_key"]),
            None,
        )
        if repo:
            _enrich(session, repo)
    _recorded_lineage(sessions, repositories)
    return {
        "schema_version": 1,
        "collected_at": at,
        "repositories": repositories,
        "sessions": sessions,
        "chains": collapse_chains(sessions),
        "omissions": omissions,
    }


def card_key(session: dict[str, Any], *, duplicate: bool = False) -> str:
    """A bounded single path component; arbitrary names never become a path."""
    identity = f"{session['provider']}:{session['session_id']}"
    raw = session["name"] or identity.replace(":", "-")
    key = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-")[:96] or "session"
    if duplicate or key != raw:
        key += "-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
    return key


def render_card(snapshot: RegistrySnapshot, session: dict[str, Any]) -> str:
    """Render state and unresolved work with local provenance."""
    repo = next(
        (
            repo
            for repo in snapshot["repositories"]
            if repo["repo_key"] == session["repo_key"]
        ),
        {},
    )
    worktree = next(
        (w for w in repo.get("worktrees", []) if w["path"] == session["cwd"]), {}
    )
    chain = next(
        chain
        for chain in snapshot["chains"]
        if f"{session['provider']}:{session['session_id']}"
        in chain["member_session_ids"]
    )
    lines = [
        f"# Lane: {session['name'] or card_key(session)}",
        "",
        f"- Repository: `{repo.get('canonical_main', 'unresolved')}`",
        f"- Worktree: `{session['cwd']}`",
        f"- HEAD: `{worktree.get('head_sha', 'unknown')}`",
        f"- Members: {', '.join(chain['member_session_ids'])}",
        f"- Role: {session['role']}; ownership: {chain['ownership']}",
        (
            f"- State: {session['raw_state']} ({session['normalized_state']}); "
            f"liveness: {session['liveness']['status']}"
        ),
        f"- Observed: {snapshot['collected_at']}; started: {session['started_at']}",
    ]
    for key, title in (
        ("done_tasks", "Done tasks"),
        ("open_tasks", "Open tasks"),
        ("research_questions", "Research questions"),
        ("blockers", "Blockers"),
        ("suggestions", "Suggestions"),
        ("issue_urls", "Issues"),
        ("evidence_refs", "Evidence"),
    ):
        lines.extend(
            ["", f"## {title}", *session[key]]
            if session[key]
            else ["", f"## {title}", "Unknown / no recorded evidence."]
        )
    lines.extend(
        [
            "",
            "## Source timestamps",
            json.dumps(session["source_timestamps"], sort_keys=True),
            "",
            "## Omissions",
            *snapshot["omissions"],
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_text(path: Path, text: str) -> None:
    if path.is_symlink():
        msg = "refused symlink card target"
        raise SessionError(msg)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".lane-", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_cards(
    snapshot: RegistrySnapshot,
    *,
    state_root: Path,
    authorize: Callable[[], str] | None = None,
) -> CardWriteResult:
    """Atomically publish one canonical repo's cards under an authorized state lock."""
    root = state_root.resolve()
    repo = next(
        (
            repo
            for repo in snapshot["repositories"]
            if repo["canonical_main"] == str(root)
        ),
        None,
    )
    if repo is None or repo["github_repo"] not in _ALLOWED_REPOS or authorize is None:
        msg = "unknown repository or unavailable writer authorization"
        raise SessionError(msg)
    if snapshot["omissions"]:
        return {"written": [], "archived": [], "omissions": snapshot["omissions"]}
    state = root / ".agent/state/session-registry/registry.json"
    if not state.parent.resolve().is_relative_to(root):
        message = "registry state directory escapes canonical main"
        raise SessionError(message)
    authorize()
    with state_lock(state):
        authorize()
        lanes = root / ".agent/lanes"
        lanes.mkdir(parents=True, exist_ok=True)
        if not lanes.resolve().is_relative_to(root):
            msg = "lane directory escapes canonical main"
            raise SessionError(msg)
        members = [
            row for row in snapshot["sessions"] if row["repo_key"] == repo["repo_key"]
        ]
        names = [card_key(row) for row in members]
        written = []
        for row in members:
            key = card_key(row, duplicate=names.count(card_key(row)) > 1)
            path = lanes / f"{key}.md"
            _atomic_text(path, render_card(snapshot, row))
            written.append(str(path))
        archived = []
        archive = (
            state.parent
            / "archive"
            / hashlib.sha256(snapshot["collected_at"].encode()).hexdigest()[:16]
        )
        for path in sorted(lanes.glob("*.md")):
            if str(path) not in written:
                if path.is_symlink():
                    msg = "refused symlink stale card"
                    raise SessionError(msg)
                archive.mkdir(parents=True, exist_ok=True)
                target = archive / path.name
                path.replace(target)
                archived.append(str(target))
        write_state(state, snapshot)
    return {"written": written, "archived": archived, "omissions": []}


def _issue_rows(repo: str, runner: Runner | None) -> list[dict[str, Any]] | None:
    try:
        result = _run(
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{repo}/issues?state=all&per_page=100",
            ],
            runner,
        )
        pages = json.loads(result.stdout) if result.returncode == 0 else None
        if not isinstance(pages, list) or not all(
            isinstance(page, list) for page in pages
        ):
            return None
        return [
            row
            for page in pages
            for row in page
            if isinstance(row, dict) and "pull_request" not in row
        ]
    except OSError, subprocess.TimeoutExpired, ValueError:
        return None


def issue_plan(
    snapshot: RegistrySnapshot, *, runner: Runner | None = None
) -> dict[str, Any]:
    """Preview marker/reference reuse, blocked creates and coordinator plan delta."""
    issues = {
        repo["repo_key"]: _issue_rows(repo["github_repo"], runner)
        if repo["github_repo"] in _ALLOWED_REPOS
        else None
        for repo in snapshot["repositories"]
    }
    intentions: list[IssueIntent] = []
    for chain in snapshot["chains"]:
        members = [
            row
            for row in snapshot["sessions"]
            if f"{row['provider']}:{row['session_id']}" in chain["member_session_ids"]
        ]
        eligible = [
            row
            for row in members
            if row["normalized_state"] in {"working", "blocked", "stopped"}
        ]
        if not eligible:
            continue
        repo = chain["repo_key"]
        rows = issues.get(repo)
        digest = hashlib.sha256(chain["stable_key"].encode()).hexdigest()
        marker = f"<!-- lane-registry:{digest} -->"
        refs = {url for row in members for url in row["issue_urls"]}
        found = next(
            (
                row
                for row in (rows or [])
                if marker in str(row.get("body", "")) or row.get("html_url") in refs
            ),
            None,
        )
        action = (
            "reuse"
            if found
            else "blocked"
            if rows is None or snapshot["omissions"] or chain["conflicts"]
            else "create"
        )
        label = (
            chain["role"]
            if chain["role"] in {"coordinator", "watcher"}
            else eligible[-1]["name"] or eligible[-1]["session_id"]
        )
        title = f"Unresolved lane: {label}"
        intentions.append(
            {
                "repo": repo,
                "stable_key": chain["stable_key"],
                "title": title,
                "body": marker
                + "\n\n"
                + "\n".join(render_card(snapshot, row) for row in eligible),
                "action": action,
                "issue_url": found.get("html_url") if found else None,
                "member_session_ids": chain["member_session_ids"],
                "source_refs": sorted(
                    {ref for row in members for ref in row["evidence_refs"]}
                ),
                "reason": "issue inventory or lane evidence unavailable"
                if action == "blocked"
                else "preview only",
            }
        )
    for repo in snapshot["repositories"]:
        if repo["github_repo"] != "ray-manaloto/dotfiles":
            continue
        rows = issues[repo["repo_key"]]
        for number in range(1715, 1722):
            found = next(
                (row for row in rows or [] if row.get("number") == number), None
            )
            intentions.append(
                {
                    "repo": repo["repo_key"],
                    "stable_key": f"request:{repo['repo_key']}:{number}",
                    "action": "reuse" if found else "blocked",
                    "issue_url": found.get("html_url") if found else None,
                    "title": f"Takeover request #{number}",
                    "body": "Existing architect-owned request; preview only.",
                    "member_session_ids": [],
                    "source_refs": [],
                }
            )
    delta = "# Coordinator plan delta (preview only)\n\n" + "\n".join(
        f"- [ ] `{intent['stable_key']}` — {intent['action']}: "
        f"{intent['issue_url'] or intent['title']}"
        for intent in intentions
    )
    return {
        "schema_version": 1,
        "collected_at": snapshot["collected_at"],
        "intentions": intentions,
        "plan_delta": delta + "\n",
        "omissions": snapshot["omissions"],
    }


def add_subcommand(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the fleet's mutually exclusive public preview/publication modes."""
    parser = subparsers.add_parser(
        "lane-cards", help="Provider-qualified fleet and lane card previews"
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--json", action="store_true")
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--issue-plan", action="store_true")
    parser.add_argument("--repo-root", type=Path, action="append", default=[])
    parser.add_argument("--jobs-dir", type=Path, default=None)
    parser.add_argument("--claims-dir", type=Path, default=None)


def main(
    args: argparse.Namespace,
    project_root: Path,
    *,
    runner: Runner | None = None,
    bases: session_ledger.TranscriptBases = session_ledger.DEFAULT_TRANSCRIPT_BASES,
) -> int:
    """A failed inventory always exits 2 while preserving the partial result."""
    try:

        def authorize() -> str:
            return handoff_inbox.require_newest_coordinator(
                os.environ, args.jobs_dir or default_jobs_dir(), claims_dir=claims_dir
            )

        if args.write:
            claims_dir = (
                args.claims_dir
                or main_checkout(project_root, runner=runner)
                / handoff_inbox.COORDINATOR_CLAIMS
            )
            authorize()
        roots = args.repo_root or default_roots(project_root, runner=runner)
        snapshot = collect(roots, runner=runner, bases=bases)
        if args.issue_plan:
            payload = issue_plan(snapshot, runner=runner)
        elif args.write:
            payload = [
                write_cards(
                    snapshot,
                    state_root=Path(repo["canonical_main"]),
                    authorize=authorize,
                )
                for repo in snapshot["repositories"]
            ]
        else:
            payload = snapshot
        text = (
            json.dumps(payload, indent=2, sort_keys=True)
            if args.json or args.issue_plan or args.write
            else "\n".join(render_card(snapshot, row) for row in snapshot["sessions"])
        )
        sys.stdout.write(text + "\n")
        return 2 if snapshot["omissions"] else 0
    except (SessionError, handoff_inbox.InboxError, OSError) as exc:
        sys.stdout.write(json.dumps({"omissions": [str(exc)]}) + "\n")
        return 2
