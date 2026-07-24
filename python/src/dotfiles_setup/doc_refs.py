"""Backtick doc-reference existence checker (#160 T13, validation J).

Agent docs (AGENTS.md/CLAUDE.md, rules, skills) cite repo files in backtick
spans (`.devcontainer/Dockerfile`, `ci.yml:93`, `mise run lint`). ~100 such
path refs are parsed by NOTHING today: agnix validates only @import stubs,
rumdl's MD057 only real [x](path) links. Stale spans are how doc rot ships
(three were found by hand in the 2026-07-05 clear-prep sweeps).

Extraction is deliberately conservative — a span must LOOK like a file path
(no spaces/globs/templates/URLs) before it is checked. Resolution:

1. exact repo-relative path exists on disk, else
2. basename matches any TRACKED file's basename (bare `ci.yml`-style
   citations are the dominant pattern, ~60 of ~100 refs), else
3. the ref is allowlisted (out-of-repo, gitignored-but-real, generic
   example, or documented-deleted — see _ALLOWED_ABSENT/_ALLOWED_PREFIXES).

Trailing `:line` / `:line-range` suffixes are stripped before resolution
(point-in-time citations move; existence is what this checks).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SPAN_RE = re.compile(r"`([^`\n]+)`")
_LINE_SUFFIX_RE = re.compile(r":[0-9][0-9,\-~]*$")
# A span qualifies as a path candidate when it has a directory separator or
# a recognized FILE extension, and none of the non-path markers below.
# The extension whitelist is what keeps dotted variables (`chezmoi.os`,
# `runner.arch`, `env.VAR`) and domains (`containers.dev`) out of scope.
_FILE_EXTENSIONS = frozenset(
    {
        "md",
        "py",
        "toml",
        "yml",
        "yaml",
        "json",
        "pkl",
        "hcl",
        "sh",
        "lock",
        "tmpl",
        "cfg",
        "txt",
        "bats",
        "deb",
        "gql",
        "sock",
        "pkl.d",
        "env",
        "asc",
        "sarif",
        "log",
    }
)
_NON_PATH_CHARS = re.compile(r"[\s*{}<>$()|\"'=@!,;]")

# Docs scoped by this check (git pathspecs).
DOC_PATHSPECS = (
    "AGENTS.md",
    "**/AGENTS.md",
    # The ONLY CLAUDE.md carrying real content: the root one is locked
    # byte-exactly to `@AGENTS.md` (claude_md_import_stub) and every subdir
    # CLAUDE.md is the same one-line stub, so `**/CLAUDE.md` would add only
    # stubs. `.claude/CLAUDE.md` is stub-EXEMPT precisely so Claude-specific
    # config can live there — including the fable-orchestrator trigger whose
    # absence went undetected for an unknown number of sessions (#354). An
    # uncovered file is exactly where the next stale ref hides.
    ".claude/CLAUDE.md",
    ".claude/rules/*.md",
    ".claude/skills/*/SKILL.md",
    # graphify's vendored SKILL.md cites its own runtime files
    # (`graphify-out/.graphify_*.json`, `.graphify_semantic.json`, …) which are
    # generated at graphify-run time, never committed. They are not repo doc
    # refs, so exclude the vendored skill — same rationale as the .agnix.toml
    # and md_budget exemptions for `.claude/skills/graphify/**` (#310-#318).
    ":!.claude/skills/graphify/SKILL.md",
)

# Refs that are intentionally absent from the working tree. Keep each entry
# justified; prefer fixing the doc over growing this list.
_ALLOWED_ABSENT = frozenset(
    {
        # Generic config examples, not citations of a real repo file.
        "action.yml",
        "devcontainer-feature.json",
        "ruff check --fix",
        # Out-of-repo by name: auto-memory files live under
        # ~/.claude/projects/<slug>/memory/ and are cited by bare name.
        "MEMORY.md",
        # In-image paths cited by bare name (COPY destinations / rendered
        # home files inside the container).
        "config.toml",
        "config.runtime.toml",
        "mise.runtime.lock",
        ".config/mise/config.toml",
        # CI/run artifacts fetched at runtime, never tracked.
        "autofix.json",
        "artifacts/build/devcontainer-metrics.json",
        # Remote docs-site / research-artifact EXAMPLE paths (mintlify +
        # research skills illustrate remote layouts).
        "jdx/mise/llms-full.txt",
        "docs/agent/workflows",
        "docs.json",
        "model-context-protocol.md",
        "state.json",
        "stages/verification.md",
        "report.md",
        # Documented-deleted (the doc narrates the deletion, PR #80).
        "home/AGENTS.md",
        "mise_snapshot.py",
        # Gitignored but real per-clone files.
        "mise.local.toml",
        "mise.*.local.toml",
        "doppler.env",
        ".mcp.json",
        # External repo file cited by name (octopus orchestrator).
        "orchestrate.sh",
        "lib/dispatch.sh",
        "lib/spawn.sh",
        "dispatch.sh",
        # External repo files cited by name (graphify, host-only pipx install).
        # do-not.md cites install.py for the ~/.claude mutation branches;
        # probes-need-a-control-arm.md cites llm.py:112 as the source that
        # refuted the stale issue #959. Neither is ours to track.
        "install.py",
        "llm.py",
        # Documented-retired files (docs narrate the retirement).
        "install.sh",
        "mise-system-resolved.json",
        ".chezmoiversion",
    }
)
# Prefixes that mark a ref as out-of-repo (container/home/absolute paths)
# or intentionally unresolvable.
_ALLOWED_PREFIXES = (
    "~/",
    "/",
    "$",
    "feedback_",
    "project_",
    "reference_",
    "user_",
    ".omc/",
    ".omg/",
    ".omx/",
    ".codex/",
    "session-",
)


@dataclass(frozen=True)
class UnresolvedRef:
    """A backtick path ref that resolved to nothing."""

    doc: str
    line: int
    ref: str


def _tracked_files(repo_root: Path, pathspecs: tuple[str, ...]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", *pathspecs],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _has_file_extension(name: str) -> bool:
    if "." not in name:
        return False
    return name.rsplit(".", 1)[-1].lower() in _FILE_EXTENSIONS


def _is_excluded_span(span: str, bare: str) -> bool:
    """Non-path markers: commands, URLs, flags, abbreviations, mentions."""
    if _NON_PATH_CHARS.search(span) or "://" in span or span.startswith("-"):
        return True
    # Abbreviated path (`python/.../p2996_hash.py`) — not resolvable.
    if "/.../" in span:
        return True
    if not bare or bare.endswith((".", "/")):
        return True
    # Extension mention (`.md`, `.tmpl`, `.sh.tmpl`) — not a citation.
    return (
        bare.startswith(".")
        and "/" not in bare
        and all(part in _FILE_EXTENSIONS for part in bare[1:].split("."))
    )


def _is_path_candidate(span: str, top_level: frozenset[str]) -> bool:
    bare = _LINE_SUFFIX_RE.sub("", span)
    if _is_excluded_span(span, bare):
        return False
    if "/" in bare:
        first = bare.split("/", 1)[0]
        # Domain-first spans (`containers.dev/llms.txt`,
        # `ghcr.io/devcontainers/...`) and owner/repo slugs (`jdx/mise`)
        # are not repo paths: require the first segment to be a real
        # top-level entry (dot-dirs included) unless it is dotted.
        if "." in first and not first.startswith("."):
            return False
        return first in top_level or _has_file_extension(Path(bare).name)
    return _has_file_extension(bare)


def _is_allowlisted(ref: str) -> bool:
    if ref in _ALLOWED_ABSENT:
        return True
    return any(ref.startswith(prefix) for prefix in _ALLOWED_PREFIXES)


def find_unresolved_refs(repo_root: Path) -> list[UnresolvedRef]:
    """Scan the scoped docs and return every unresolved path ref."""
    all_tracked = _tracked_files(repo_root, ("*",))
    basenames = {Path(p).name for p in all_tracked}
    top_level = frozenset(p.split("/", 1)[0] for p in all_tracked)
    unresolved: list[UnresolvedRef] = []
    for doc in _tracked_files(repo_root, DOC_PATHSPECS):
        text = (repo_root / doc).read_text()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for span in _SPAN_RE.findall(line):
                if not _is_path_candidate(span, top_level):
                    continue
                ref = _LINE_SUFFIX_RE.sub("", span)
                if _is_allowlisted(ref):
                    continue
                if (repo_root / ref).exists():
                    continue
                if "/" not in ref and ref in basenames:
                    continue
                # Suffix match: docs cite paths relative to their own dir
                # (tests/AGENTS.md says `infra/foundation.bats`) or to a
                # source root (`dotfiles_setup/__init__.py`).
                if any(p.endswith("/" + ref) for p in all_tracked):
                    continue
                unresolved.append(UnresolvedRef(doc=doc, line=lineno, ref=ref))
    return unresolved
