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
``{type:"tool_use", name:"Bash", input:{command:"…"}}`` block, answered by a
later ``type:"user"`` line carrying the matching ``tool_result``. That schema is
community-reverse-engineered, not an officially versioned contract, so every
field access here is defensive (a malformed line is skipped, never fatal).

A transcript records ATTEMPTS, not executions: the ``tool_use`` block is
written whether or not the command ran, because a PreToolUse deny lands *after*
the model emits it. So an attempt is paired to its result (see
:func:`_executed_ids`) to tell "the guard blocked this" from "this evaded the
guard" — two outcomes that are otherwise byte-identical in the transcript.

Classification (first match wins). The three rule-matching classes exist
because a bare "matched a deny rule" verdict is almost pure noise — measured
over 3,615 real calls on 2026-07-14: 155 matched a rule, 147 predated it, 3 were
denials, and **0** were bypasses:

- ``bypass`` — matched a rule that ALREADY EXISTED (``timestamp > rule.since``)
  *and* actually executed. A real evasion. The only alarm worth raising.
- ``blocked`` — matched a live rule and did NOT run: the guard working. Audit
  these for FALSE POSITIVES; a denial cancels the WHOLE compound command, so a
  wrong one is not just noise. This bucket is what MEASURED #265 and then what
  proved it fixed: 2 of the guard's 3 denials were quoted-regex false positives
  (``grep -iE "…|devcontainer up|…"``), and after
  :func:`dotfiles_setup.hook_guard._inert_masked` landed the bucket fell to the
  1 denial that was always correct. It stays the place to look — no measurement,
  no next defect.
- ``pre_rule`` — matched a rule that post-dates it: history from before the
  guard existed. No action; NOT a one-off (it has a mise task today).
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
    """One Bash invocation recovered from a transcript.

    ``executed`` says the command really RAN, as opposed to being refused by
    the permission layer before execution. It has no default on purpose: the
    field decides whether a rule-matching command reads as a guard bypass or as
    the guard working, so every construction site must state it outright.
    """

    command: str
    session: str
    timestamp: str
    executed: bool


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


def _bash_blocks(content: object) -> Iterator[tuple[str, str]]:
    """Yield ``(tool_use_id, command)`` for Bash calls in one line's content."""
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
                    yield str(block.get("id", "")), cmd


def _json_lines(path: Path) -> list[dict[str, object]]:
    """Every well-formed JSON object line in ``path`` (bad lines skipped)."""
    try:
        raw = path.read_text(errors="replace")
    except OSError:
        return []
    objs: list[dict[str, object]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objs.append(obj)
    return objs


def _content_blocks(obj: dict[str, object]) -> object:
    """The ``message.content`` of a transcript line, if it has one."""
    message = obj.get("message")
    return message.get("content") if isinstance(message, dict) else None


def _executed_ids(objs: Iterable[dict[str, object]]) -> set[str]:
    """The ``tool_use`` ids whose result proves the command actually ran.

    A Bash result line carries ``toolUseResult``: a **dict** with a ``stdout``
    key when the command executed, or a bare **str** (``"Error: <reason>"``)
    when the permission layer refused it first. Probed against 3,618 real
    results (2026-07-14): ``stdout`` is present in every executed variant —
    plain, ``backgroundTaskId``, ``gitOperation``, ``persistedOutputPath``,
    ``returnCodeInterpretation`` — and the 80 refusals are the only non-dicts,
    so the dict-with-stdout test is a structural signal, not a string match on
    the reason. Each line holds exactly one ``tool_result`` block (6,822/6,822
    probed), so the line-level ``toolUseResult`` maps to it unambiguously.

    An id absent from the returned set is treated as NOT executed — a result
    can be missing for the final in-flight call of a session. That direction is
    deliberate: proof-of-execution is required to cry bypass, so an unknown
    outcome stays quiet rather than inventing an alarm.
    """
    ids: set[str] = set()
    for obj in objs:
        result = obj.get("toolUseResult")
        if not (isinstance(result, dict) and "stdout" in result):
            continue
        content = _content_blocks(obj)
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                uid = block.get("tool_use_id")
                if isinstance(uid, str):
                    ids.add(uid)
    return ids


def iter_bash_commands(paths: Iterable[Path]) -> Iterator[BashCommand]:
    """Every Bash command across the transcripts, parsed defensively.

    Two passes per file: results can only be paired to attempts once the whole
    file is read (the ``tool_result`` always lands on a later line than its
    ``tool_use``). The file is read into memory either way.
    """
    for path in paths:
        objs = _json_lines(path)
        executed = _executed_ids(objs)
        for obj in objs:
            if obj.get("type") != "assistant":
                continue
            session = str(obj.get("sessionId", ""))
            timestamp = str(obj.get("timestamp", ""))
            for uid, cmd in _bash_blocks(_content_blocks(obj)):
                yield BashCommand(
                    cmd,
                    session=session,
                    timestamp=timestamp,
                    executed=uid in executed,
                )


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


def classify(bc: BashCommand) -> str:
    """The class of one command: see the module docstring (first match wins).

    A command matching a rule that post-dates it is ``pre_rule`` and stops
    there — it is NOT a one-off, because it has a canonical mise task today;
    telling the reader to "package it as a mise task" would be wrong.

    The cutoff compares dates, and a command from the rule's own landing DAY
    counts as pre-rule: the rule may have merged later that day, and a false
    bypass alarm costs more than a missed same-day one. Every later day is
    exact. An empty/short timestamp likewise reads as pre-rule — no alarm
    without evidence.
    """
    rule = hook_guard.match(bc.command)
    if rule is not None:
        if bc.timestamp[:10] <= rule.since:
            return "pre_rule"
        return "bypass" if bc.executed else "blocked"
    if is_mise_backed(bc.command):
        return "mise"
    if is_diagnostic(bc.command):
        return "diagnostic"
    return "one_off"


def group_key(command: str) -> str:
    """A normalized ``head sub`` grouping key (mirrors fewer-permission-prompts)."""
    head, sub = _head_and_sub(command)
    return f"{head} {sub}".strip() if head else "(empty)"


def _group_name(bc: BashCommand, kind: str) -> str:
    """The group a command reports under: rule name for denials, else shape."""
    if kind == "blocked":
        rule = hook_guard.match(bc.command)
        if rule is not None:
            return rule.name
    return group_key(bc.command)


@dataclass(frozen=True)
class AuditResult:
    """The classified + grouped outcome of a scan."""

    counts: dict[str, int]
    bypass_groups: list[tuple[str, int, str]]
    blocked_groups: list[tuple[str, int, str]]
    one_off_groups: list[tuple[str, int, str]]
    sessions: int
    total: int


# Grouped classes, and how each one names a group. Guard denials group by the
# RULE that fired, not by command shape: a denial's head names nothing useful —
# the guard's one real denial is a `cd`+`echo` preamble whose operative `npx`
# sits behind a `||`, so it heads as `echo` — whereas the rule identity is
# exactly what the reader must audit.
_GROUPED = ("bypass", "blocked", "one_off")


def audit(commands: Iterable[BashCommand], *, sessions: int) -> AuditResult:
    """Classify + frequency-rank the commands into an :class:`AuditResult`."""
    counts: Counter[str] = Counter()
    group_counts: dict[str, Counter[str]] = {k: Counter() for k in _GROUPED}
    examples: dict[str, dict[str, str]] = {k: {} for k in _GROUPED}
    total = 0
    for bc in commands:
        total += 1
        kind = classify(bc)
        counts[kind] += 1
        if kind in group_counts:
            key = _group_name(bc, kind)
            group_counts[kind][key] += 1
            examples[kind].setdefault(key, bc.command)

    def ranked(kind: str) -> list[tuple[str, int, str]]:
        return [
            (key, n, examples[kind][key]) for key, n in group_counts[kind].most_common()
        ]

    return AuditResult(
        counts=dict(counts),
        bypass_groups=ranked("bypass"),
        blocked_groups=ranked("blocked"),
        one_off_groups=ranked("one_off"),
        sessions=sessions,
        total=total,
    )


def _truncate(text: str, width: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def _table(groups: list[tuple[str, int, str]], label: str) -> list[str]:
    """A ranked ``count | <label> | example`` markdown table."""
    return [
        f"| count | {label} | example |",
        "|---:|---|---|",
        *(f"| {n} | `{key}` | `{_truncate(ex)}` |" for key, n, ex in groups),
        "",
    ]


def render_report(result: AuditResult) -> str:
    """A frequency-ranked markdown report for human review of the refine loop."""
    c = result.counts
    lines = [
        "# Command audit — one-off Bash culprits",
        "",
        f"Scanned **{result.sessions}** recent session(s), "
        f"**{result.total}** Bash command(s).",
        "",
        "| class | count | meaning |",
        "|---|---:|---|",
        f"| bypass | {c.get('bypass', 0)} | ran DESPITE a live guard rule — "
        "a real evasion, investigate |",
        f"| blocked | {c.get('blocked', 0)} | guard denied it (working) — "
        "audit for false positives |",
        f"| pre_rule | {c.get('pre_rule', 0)} | matched a rule that post-dates "
        "it — history, no action |",
        f"| one_off | {c.get('one_off', 0)} | mutating hand-run — package as a "
        "mise task |",
        f"| mise | {c.get('mise', 0)} | already via a mise task / dotfiles_setup CLI |",
        f"| diagnostic | {c.get('diagnostic', 0)} | read-only, legitimately direct |",
        "",
        "## 🚨 Bypasses (ran despite a live guard rule)",
        "",
    ]
    if result.bypass_groups:
        lines += _table(result.bypass_groups, "shape")
    else:
        lines += [
            "_None — nothing has evaded the guard since its rule landed._",
            "",
        ]
    if result.blocked_groups:
        lines += [
            "## Guard denials (the guard working — audit for false positives)",
            "",
            "A denial is only correct if the command really was the shape the "
            "rule names — a deny cancels the WHOLE compound command, so a wrong "
            "one silently skips the rest. Separators inside quotes and heredoc "
            "bodies no longer count as command positions (#265), which is what "
            "emptied this bucket of its false positives; anything left should "
            "be a real invocation. Grouped by the rule that fired, because a "
            "denial's own head names nothing useful.",
            "",
            *_table(result.blocked_groups, "rule"),
        ]
    lines += [
        "## One-off culprits (candidates for a mise task + python function)",
        "",
    ]
    if result.one_off_groups:
        lines += _table(result.one_off_groups, "shape")
    else:
        lines += ["_None — no un-wrapped one-off commands found._", ""]
    lines += [
        "Refine loop: for a high-frequency one-off shape, add a `mise run <task>` "
        "wrapping a `dotfiles_setup` function (zero-bash-logic), and if it's a "
        "known bad shape, add a `hook_guard._RULES` redirect — with a `since` "
        "date, or its first scan reports as history. See "
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
        f"{result.counts.get('bypass', 0)} bypass, "
        f"{result.counts.get('blocked', 0)} guard-denied)\n"
    )
    return 0
