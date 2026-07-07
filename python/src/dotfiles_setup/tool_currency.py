"""Daily tool-currency signal: what moved upstream, with release links.

``dotfiles-setup tool-currency`` (wrapped by ``mise run tool-currency``,
run daily by refresh.yml's ``tool-currency`` job) renders
``mise outdated --json`` into a markdown report whose rows link straight
to each tool's release notes. The report feeds the self-learning loop
Ray asked for (2026-07-07): fast-moving tools (mise/hk/chezmoi/docker/
uv/ruff/ty/…) get their release notes REVIEWED — by the
``tool-currency-check`` skill locally — before bumps are adopted, and
the daily issue the workflow upserts is that skill's standing input.

This module only produces the signal. Judgment (adopt/retire/defer,
native-feature supersedes custom code) stays with the skill per
``.claude/rules/tool-currency-and-native-first.md``.
"""

from __future__ import annotations

import json
import subprocess
import sys

_OUTDATED_TIMEOUT_S = 300.0

_REGISTRY_URL = "https://mise.jdx.dev/registry.html"


def release_link(tool_key: str) -> str:
    """Best-effort release-notes URL for a mise tool key.

    Backend-prefixed keys encode their source; short registry names fall
    back to the mise registry page (which links each tool's homepage).
    """
    backend, _, rest = tool_key.partition(":")
    if backend in ("github", "aqua", "ubi") and "/" in rest:
        return f"https://github.com/{rest}/releases"
    if backend == "npm":
        return f"https://www.npmjs.com/package/{rest}?activeTab=versions"
    if backend in ("pipx", "uvx"):
        return f"https://pypi.org/project/{rest.partition('[')[0]}/#history"
    if backend == "cargo":
        return f"https://crates.io/crates/{rest}/versions"
    return _REGISTRY_URL


def render_report(outdated: dict[str, dict[str, str]]) -> str:
    """Markdown report from the ``mise outdated --json`` mapping."""
    if not outdated:
        return "All pinned tools are current — nothing moved upstream.\n"
    lines = [
        "# Tool currency report",
        "",
        "Review each release-notes link BEFORE adopting a bump — and ask",
        "whether a new native feature supersedes custom code",
        "(`.claude/rules/tool-currency-and-native-first.md`; run the",
        "`tool-currency-check` skill for the full retire/bump pass).",
        "",
        "| tool | current | latest | release notes |",
        "|---|---|---|---|",
    ]
    for key in sorted(outdated):
        info = outdated[key]
        current = info.get("current") or info.get("requested") or "?"
        latest = info.get("latest") or info.get("bump") or "?"
        lines.append(f"| `{key}` | {current} | {latest} | {release_link(key)} |")
    lines += [
        "",
        f"{len(outdated)} tool(s) have upstream movement.",
        "",
    ]
    return "\n".join(lines)


def tool_currency_main() -> int:
    """CLI entry: print the markdown report; rc 1 only on probe failure.

    An outdated tool is a SIGNAL, not an error — the daily workflow gates
    issue-upsert on report content, not exit code, so a busy upstream day
    never turns the cron red.
    """
    res = subprocess.run(
        ["mise", "outdated", "--json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=_OUTDATED_TIMEOUT_S,
    )
    if res.returncode != 0:
        sys.stderr.write(f"mise outdated failed: {res.stderr.strip()}\n")
        return 1
    outdated = json.loads(res.stdout or "{}")
    sys.stdout.write(render_report(outdated))
    return 0
