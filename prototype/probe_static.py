#!/usr/bin/env python3
"""PROTOTYPE — the mechanism-bet arms that cost no agent spend.

Two of the five claims are settleable from the installed binary and the vendor
docs alone. Running them FIRST is the point: a probe you can answer for free
should never be paid for with agent spend.

Every check reports BOTH arms. A bare count is an opinion; a count next to a
control is evidence.

Throwaway. Run via `mise run proto-mechanisms`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

DOCS = Path.home() / (
    "dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code"
)

BOLD, DIM, RESET = "\x1b[1m", "\x1b[2m", "\x1b[0m"


def _hits(needle: str, path: Path) -> int:
    """Count lines containing `needle`, binary-safe."""
    data = path.read_bytes()
    return data.count(needle.encode())


def claim_3_teammate_idle() -> None:
    """Is `TeammateIdle` reachable from the CLI, or TypeScript-SDK-only?

    The SDK hook-compatibility table marks it Python-SDK: No / TypeScript: Yes,
    while the CLI hooks page lists it unqualified. That contradiction decides
    half of the enforcement design, so ask the shipped binary rather than either
    document.
    """
    print(f"\n{BOLD}CLAIM 3{RESET} — is TeammateIdle reachable from the CLI?")
    cli = shutil.which("claude")
    if cli is None:
        print("  SKIP — no `claude` on PATH")
        return
    real = Path(os.path.realpath(cli))
    print(f"  {DIM}binary: {real}{RESET}")

    # Two known-present controls and one invented absent control. The invented
    # term is fresh: a control string that has been written down is now IN the
    # corpus and stops discriminating.
    probes = {
        "TeammateIdle": "under test",
        "SubagentStop": "CONTROL (known CLI event, expect > 0)",
        "TaskCompleted": "CONTROL (known CLI event, expect > 0)",
        "Qwlfbz9NotAnEvent": "CONTROL (invented, expect 0)",
    }
    for token, role in probes.items():
        print(f"  {token:<20} {_hits(token, real):>5}   {DIM}{role}{RESET}")


def claim_5_plugin_scoped_fields() -> None:
    """Are permissionMode / hooks / mcpServers really ignored for plugin subagents?

    Marked UNVERIFIED in the framework review because the assertion came from a
    third-party repo's own verifier. It turns out the vendor doc states it
    outright, so this needs no live probe at all.
    """
    print(f"\n{BOLD}CLAIM 5{RESET} — are fields ignored for plugin-scoped subagents?")
    page = DOCS / "sub-agents.md"
    if not page.exists():
        print(f"  SKIP — {page} not present")
        return

    needle = "Ignored for [plugin subagents]"
    lines = [
        (n, ln.split("|")[1].strip())
        for n, ln in enumerate(page.read_text(encoding="utf-8").splitlines(), 1)
        if needle in ln
    ]
    for n, field in lines:
        print(f"  sub-agents.md:{n:<5} {field}")
    print(f"  {DIM}fields stated as ignored: {len(lines)}{RESET}")

    # Control: a phrase known to be in the same table. If this returns 0 the
    # grep is not reaching the table and the result above means nothing.
    ctrl = _hits("Maximum number of agentic turns", page)
    print(f"  {DIM}CONTROL 'Maximum number of agentic turns' in same table: {ctrl}{RESET}")


def workflow_enabled() -> None:
    """Is the Workflow tool even switched on? Claim 1 is meaningless if not."""
    print(f"\n{BOLD}CLAIM 1 preflight{RESET} — is the Workflow tool available?")
    for var in ("CLAUDE_CODE_DISABLE_WORKFLOWS",):
        # Presence only. Never interpolate a value into a format string.
        print(f"  {var:<34} {'SET' if os.environ.get(var) else 'ABSENT'}")
    saved = Path(".claude/workflows")
    print(f"  .claude/workflows/ exists              {saved.is_dir()}")
    try:
        ver = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=20, check=False
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        ver = f"<unavailable: {type(exc).__name__}>"
    print(f"  {DIM}claude --version: {ver}  (workflows need >= 2.1.154){RESET}")


def main() -> int:
    print(f"{BOLD}PROTOTYPE — agent-team mechanism bets, free arms{RESET}")
    print(f"{DIM}Claims 2 and 4 need live agents and are driven from the session, not here.{RESET}")
    claim_3_teammate_idle()
    claim_5_plugin_scoped_fields()
    workflow_enabled()
    print(f"\n{DIM}Verdicts land in prototype/RESULTS.md{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
