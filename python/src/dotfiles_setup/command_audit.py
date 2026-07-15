"""Command-audit scanner: mine Claude Code transcripts for one-off Bash culprits.

The self-learning half of the mise-tasks-only enforcement loop. The PreToolUse
guard (:mod:`dotfiles_setup.hook_guard`) DENIES a fixed set of one-off command
shapes; this scanner finds the shapes it does NOT yet cover — mutating,
hand-run commands that should become mise tasks — so the rules/hooks/docs can
be refined over time. It is the *inverse* of Claude Code's official
``fewer-permission-prompts`` skill (which mines the same transcripts to
allow-list read-only commands); same input + grouping, opposite verdict.

Capture is 100% native — no logging hook, no OTel collector. Every Bash call is
already recorded verbatim in the session transcript JSONL
(``$CLAUDE_CONFIG_DIR/projects/<encoded-cwd>/<session>.jsonl``, default
``~/.claude``): an ``type:"assistant"`` line whose ``message.content`` holds a
``{type:"tool_use", name:"Bash", input:{command:"…"}}`` block. That schema is
community-reverse-engineered, not an officially versioned contract, so every
field access here is defensive (a malformed line is skipped, never fatal).

Classification (first match wins):

- ``denied`` — :func:`hook_guard.decide` returns a reason. A KNOWN one-off that
  still ran ⇒ the guard was bypassed or the command predates the rule. Highest
  signal.
- ``mise`` — already goes through a mise task / the ``dotfiles_setup`` CLI /
  canonical pytest. Good; no action.
- ``diagnostic`` — a read-only/allowlisted shape (ls, cat, git status, docker
  ps, …) that legitimately stays direct.
- ``one_off`` — everything else: a mutating hand-run command with no mise task.
  The refine-loop candidates. Over-inclusion is fine — a human reviews.

``dotfiles-setup command-audit`` (→ ``mise run command-audit``) renders a
frequency-ranked markdown report grouped by command+subcommand.

The loop is RECURRING, not remember-to-run: a ``SessionEnd`` hook in
``.claude/settings.json`` refreshes ``.omc/command-audit.md`` via ``--output``
once per session. SessionEnd (not ``Stop``) is the right event — it fires once
per session at termination and *cannot block*, whereas ``Stop`` fires every
turn and can block (exit 2 continues the conversation), which would put a
transcript scan on the per-turn path and risk a stop-loop. The scan is local by
nature (it reads ``~/.claude`` transcripts), so this is a local hook and never
a CI job — a GHA runner has no transcripts to read.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import hook_guard

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

# Most-recent sessions to scan by default (mirrors fewer-permission-prompts' cap).
DEFAULT_SESSION_LIMIT = 50

# A command already routed through a mise task / the dotfiles_setup CLI / the
# canonical pytest form (the mise tasks themselves wrap these — stay direct).
_MISE_BACKED = re.compile(
    r"^\s*(?:env\s+)?(?:\w+=\S*\s+)*"
    r"(?:mise\s|uv\s+run\s+--project\s+python\s+(?:dotfiles-setup|pytest)\b)"
)

# Read-only command heads that legitimately stay direct (mise-tasks-only.md:
# "diagnostic/read-only commands are NOT wrapped"). Bare heads are read-only.
_DIAGNOSTIC_HEADS = frozenset(
    {
        "ls",
        "cat",
        "bat",
        "echo",
        "printf",
        "pwd",
        "cd",
        "head",
        "tail",
        "wc",
        "grep",
        "rg",
        "fd",
        "find",
        "which",
        "type",
        "file",
        "stat",
        "tree",
        "jq",
        "yq",
        "sort",
        "uniq",
        "cut",
        "awk",
        "sed",
        "diff",
        "test",
        "true",
        "env",
        "date",
        "whoami",
        "uname",
        "hostname",
        "df",
        "du",
        "ps",
        "top",
        "read",
        "column",
        "tr",
        "basename",
        "dirname",
        "realpath",
        "readlink",
    }
)

# Sub-command allowlists for multi-verb tools: only these are read-only.
_READ_SUBCOMMANDS: dict[str, frozenset[str]] = {
    "git": frozenset(
        {
            "status",
            "log",
            "diff",
            "show",
            "branch",
            "rev-parse",
            "ls-files",
            "blame",
            "describe",
            "remote",
            "config",
            "tag",
            "shortlog",
            "reflog",
            "cat-file",
            "grep",
            "for-each-ref",
            "merge-base",
            "rev-list",
            "name-rev",
        }
    ),
    "docker": frozenset(
        {
            "ps",
            "images",
            "logs",
            "inspect",
            "info",
            "version",
            "context",
            "history",
            "image",
            "system",
            "top",
            "port",
            "stats",
            "manifest",
        }
    ),
    "gh": frozenset({"pr", "run", "issue", "api", "repo", "release", "workflow"}),
    "mise": frozenset({}),  # handled by _MISE_BACKED, never reaches here
    "uv": frozenset({}),
    "kubectl": frozenset({"get", "describe", "logs", "top", "version"}),
    "cargo": frozenset({"tree", "metadata"}),
}

# `gh <x> …` is read-only only for these value shapes (view/checks/list/--json).
_GH_READ_MARKERS = re.compile(r"\b(view|checks|list|status|--json)\b")


@dataclass(frozen=True)
class BashCommand:
    """One Bash invocation recovered from a transcript."""

    command: str
    session: str
    timestamp: str


def transcripts_base(
    env: dict[str, str] | None = None, home: Path | None = None
) -> Path:
    """The Claude Code projects dir (env-aware; never hardcoded)."""
    env = env if env is not None else dict(os.environ)
    home = home if home is not None else Path.home()
    config_dir = env.get("CLAUDE_CONFIG_DIR")
    base = Path(config_dir) if config_dir else home / ".claude"
    return base / "projects"


def encode_cwd(cwd: Path) -> str:
    """Claude Code's project-dir encoding of an absolute path (``/``,``.`` → ``-``)."""
    return re.sub(r"[/.]", "-", str(cwd))


def project_transcripts(base: Path, cwd: Path, *, limit: int) -> list[Path]:
    """The ``limit`` most-recent transcript files for ``cwd`` (newest first)."""
    project_dir = base / encode_cwd(cwd)
    if not project_dir.is_dir():
        return []
    files = [p for p in project_dir.glob("*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _bash_blocks(content: object) -> Iterator[str]:
    """Yield Bash ``input.command`` strings from an assistant line's content."""
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            command = block.get("input", {})
            if isinstance(command, dict):
                cmd = command.get("command")
                if isinstance(cmd, str) and cmd.strip():
                    yield cmd


def iter_bash_commands(paths: Iterable[Path]) -> Iterator[BashCommand]:
    """Every Bash command across the transcripts, parsed defensively."""
    for path in paths:
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict) or obj.get("type") != "assistant":
                continue
            message = obj.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            session = str(obj.get("sessionId", ""))
            timestamp = str(obj.get("timestamp", ""))
            for cmd in _bash_blocks(content):
                yield BashCommand(cmd, session=session, timestamp=timestamp)


# A leading `cd <path> &&|;|newline` prefix hides the operative command from
# first-token classification/grouping (the same chained-command shape the
# research flagged as guard-evasion). Strip it (repeatedly) so `cd repo &&
# git commit` classifies as `git commit`, not as a `cd` diagnostic.
_CD_PREFIX = re.compile(r"^\s*cd\s+\S+\s*(?:&&|;|\n)\s*")


def _operative(command: str) -> str:
    """The command with any leading ``cd <path> &&|;`` prefix(es) stripped."""
    prev = None
    cur = command
    while cur != prev:
        prev = cur
        cur = _CD_PREFIX.sub("", cur, count=1)
    return cur or command


def is_mise_backed(command: str) -> bool:
    """True when ``command`` already runs via mise / the dotfiles_setup CLI."""
    return bool(_MISE_BACKED.match(_operative(command)))


def _head_and_sub(command: str) -> tuple[str, str]:
    """The command head and its first sub-token, past ``cd`` + ``env VAR=x``."""
    tokens = _operative(command).split()
    i = 0
    while i < len(tokens) and (tokens[i] == "env" or "=" in tokens[i]):
        i += 1
    head = tokens[i] if i < len(tokens) else ""
    sub = tokens[i + 1] if i + 1 < len(tokens) else ""
    return head, sub


def is_diagnostic(command: str) -> bool:
    """True for read-only/allowlisted shapes that legitimately stay direct."""
    head, sub = _head_and_sub(command)
    if head in _DIAGNOSTIC_HEADS:
        return True
    reads = _READ_SUBCOMMANDS.get(head)
    if reads is None:
        return False
    if head == "gh":
        # gh is read-only only in its view/checks/list/--json shapes.
        return bool(_GH_READ_MARKERS.search(command))
    return sub in reads


def classify(command: str) -> str:
    """One of ``denied`` / ``mise`` / ``diagnostic`` / ``one_off`` (first match)."""
    if hook_guard.decide(command) is not None:
        return "denied"
    if is_mise_backed(command):
        return "mise"
    if is_diagnostic(command):
        return "diagnostic"
    return "one_off"


def group_key(command: str) -> str:
    """A normalized ``head sub`` grouping key (mirrors fewer-permission-prompts)."""
    head, sub = _head_and_sub(command)
    return f"{head} {sub}".strip() if head else "(empty)"


@dataclass(frozen=True)
class AuditResult:
    """The classified + grouped outcome of a scan."""

    counts: dict[str, int]
    denied_groups: list[tuple[str, int, str]]
    one_off_groups: list[tuple[str, int, str]]
    sessions: int
    total: int


def audit(commands: Iterable[BashCommand], *, sessions: int) -> AuditResult:
    """Classify + frequency-rank the commands into an :class:`AuditResult`."""
    counts: Counter[str] = Counter()
    group_counts: dict[str, Counter[str]] = {"denied": Counter(), "one_off": Counter()}
    examples: dict[str, dict[str, str]] = {"denied": {}, "one_off": {}}
    total = 0
    for bc in commands:
        total += 1
        kind = classify(bc.command)
        counts[kind] += 1
        if kind in group_counts:
            key = group_key(bc.command)
            group_counts[kind][key] += 1
            examples[kind].setdefault(key, bc.command)

    def ranked(kind: str) -> list[tuple[str, int, str]]:
        return [
            (key, n, examples[kind][key]) for key, n in group_counts[kind].most_common()
        ]

    return AuditResult(
        counts=dict(counts),
        denied_groups=ranked("denied"),
        one_off_groups=ranked("one_off"),
        sessions=sessions,
        total=total,
    )


def _truncate(text: str, width: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def render_report(result: AuditResult) -> str:
    """A frequency-ranked markdown report for human review of the refine loop."""
    c = result.counts
    n_one_off = c.get("one_off", 0)
    n_denied = c.get("denied", 0)
    n_mise = c.get("mise", 0)
    n_diag = c.get("diagnostic", 0)
    lines = [
        "# Command audit — one-off Bash culprits",
        "",
        f"Scanned **{result.sessions}** recent session(s), "
        f"**{result.total}** Bash command(s).",
        "",
        "| class | count | meaning |",
        "|---|---:|---|",
        f"| one_off | {n_one_off} | mutating hand-run — package as a mise task |",
        f"| denied | {n_denied} | already-denied shape that ran (bypass / pre-rule) |",
        f"| mise | {n_mise} | already via a mise task / dotfiles_setup CLI |",
        f"| diagnostic | {n_diag} | read-only, legitimately direct |",
        "",
    ]
    if result.denied_groups:
        lines += [
            "## ⚠️ Denied-but-ran (investigate — guard bypass or pre-rule history)",
            "",
            "| count | shape | example |",
            "|---:|---|---|",
            *(
                f"| {n} | `{key}` | `{_truncate(ex)}` |"
                for key, n, ex in result.denied_groups
            ),
            "",
        ]
    lines += [
        "## One-off culprits (candidates for a mise task + python function)",
        "",
    ]
    if result.one_off_groups:
        lines += [
            "| count | shape | example |",
            "|---:|---|---|",
            *(
                f"| {n} | `{key}` | `{_truncate(ex)}` |"
                for key, n, ex in result.one_off_groups
            ),
        ]
    else:
        lines.append("_None — no un-wrapped one-off commands found._")
    lines += [
        "",
        "Refine loop: for a high-frequency one-off shape, add a `mise run <task>` "
        "wrapping a `dotfiles_setup` function (zero-bash-logic), and if it's a "
        "known bad shape, add a `hook_guard._RULES` redirect. See "
        ".claude/rules/mise-tasks-only.md.",
    ]
    return "\n".join(lines) + "\n"


def write_report(text: str, project_root: Path, output: Path) -> Path:
    """Write ``text`` to ``output`` (relative paths resolve against the repo).

    Python owns the path resolution + parent creation so the SessionEnd hook
    stays a pure invocation with no shell redirect (zero-bash-logic), and so
    the destination does not depend on the hook's cwd.
    """
    dest = output if output.is_absolute() else project_root / output
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest


def command_audit_main(
    project_root: Path,
    *,
    limit: int = DEFAULT_SESSION_LIMIT,
    output: Path | None = None,
) -> int:
    """Scan this project's recent transcripts; report to stdout or ``output``.

    ``--output`` is what the SessionEnd hook (``.claude/settings.json``) uses to
    refresh ``.omc/command-audit.md`` once per session, making the refine loop
    recurring instead of remember-to-run. The no-transcripts branch deliberately
    leaves any existing report untouched rather than clobbering it with a
    notice — and it cannot fire from the hook anyway, since a SessionEnd
    implies this project has a transcript.
    """
    base = transcripts_base()
    transcripts = project_transcripts(base, project_root, limit=limit)
    if not transcripts:
        sys.stdout.write(
            f"command-audit: no transcripts for {project_root} under {base} "
            "(set CLAUDE_CONFIG_DIR if your Claude config lives elsewhere)\n"
        )
        return 0
    result = audit(iter_bash_commands(transcripts), sessions=len(transcripts))
    text = render_report(result)
    if output is None:
        sys.stdout.write(text)
        return 0
    dest = write_report(text, project_root, output)
    sys.stdout.write(
        f"command-audit: wrote {dest} "
        f"({result.counts.get('one_off', 0)} one-off, "
        f"{result.counts.get('denied', 0)} denied-but-ran)\n"
    )
    return 0
