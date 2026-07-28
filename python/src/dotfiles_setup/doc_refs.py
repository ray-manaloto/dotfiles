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
import tomllib
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
        # fnox config files, all out-of-repo: the real one is the user root
        # `~/.config/fnox/config.toml`, and the two `.local` names are the
        # project-scoped override layer the secrets rule PROBED and found is
        # not honoured at that root. This repo has no fnox config of its own.
        "config.local.toml",
        "fnox.toml",
        "fnox.local.toml",
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
        # graphify's generated graph, cited by `.claude/CLAUDE.md` as the thing
        # to query before grepping. `graphify-out/` is gitignored and rebuilt
        # per-clone, so it exists locally and never in CI — the divergence that
        # failed PR #359's first run. Same rationale as the vendored graphify
        # SKILL.md exclusion in DOC_PATHSPECS.
        "graphify-out/graph.json",
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
    ".agent/",
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


def find_local_only_refs(repo_root: Path) -> list[UnresolvedRef]:
    """Return refs that resolve ONLY because the file exists on THIS machine.

    :func:`find_unresolved_refs` accepts a ref when ``(repo_root / ref).exists()``,
    which is a filesystem stat — so a **gitignored** artifact present locally
    resolves here and vanishes in a fresh CI checkout. That is a silent
    local/CI divergence of exactly the shape `.claude/rules/clean-git-state.md`
    exists to prevent, and it shipped one: adding `.claude/CLAUDE.md` to
    :data:`DOC_PATHSPECS` passed locally and failed CI on its
    ``graphify-out/graph.json`` citation (PR #359).

    A ref is local-only when it exists on disk but is neither a tracked file nor
    a directory containing one. Callers should require every such ref to be
    allowlisted; the test suite pins that, so the divergence fails locally
    instead of in CI.
    """
    all_tracked = _tracked_files(repo_root, ("*",))
    tracked = set(all_tracked)
    local_only: list[UnresolvedRef] = []
    top_level = frozenset(p.split("/", 1)[0] for p in all_tracked)
    for doc in _tracked_files(repo_root, DOC_PATHSPECS):
        text = (repo_root / doc).read_text()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for span in _SPAN_RE.findall(line):
                if not _is_path_candidate(span, top_level):
                    continue
                ref = _LINE_SUFFIX_RE.sub("", span)
                if _is_allowlisted(ref) or not (repo_root / ref).exists():
                    continue
                # `git ls-files` never emits a leading "./", but docs write it
                # (do-not.md contrasts `./CLAUDE.md` with `~/.claude/CLAUDE.md`).
                # Without this, three tracked files read as local-only.
                bare = ref.removeprefix("./")
                if bare in tracked:
                    continue
                if any(p.startswith(bare + "/") for p in all_tracked):
                    continue
                local_only.append(UnresolvedRef(doc=doc, line=lineno, ref=ref))
    return local_only


# ---------------------------------------------------------------------------
# Named-artifact refs (#354 PR 1) — tasks and skills cited by NAME
# ---------------------------------------------------------------------------
#
# The path checker above can only see spans that look like a file path. A span
# containing whitespace is disqualified by `_NON_PATH_CHARS`, and a bare name
# with no extension and no `/` never becomes a candidate — so `mise run <task>`
# and a skill cited by name are both structurally invisible to it. They are
# also the two most common ways this repo's docs cite something executable:
# `.claude/rules/mise-tasks-only.md` is a table of task names, and the rules
# cross-reference skills constantly. A renamed task or a deleted skill leaves
# the citation behind, silently, which is the #354 defect class exactly.

_TASK_RE = re.compile(r"\bmise run ([A-Za-z0-9][A-Za-z0-9:_.-]*)")
_SKILL_RE = re.compile(r"`([A-Za-z0-9][A-Za-z0-9:_.-]*)`\s+skill\b")
_WIKILINK_RE = re.compile(r"\[\[([^\]|`]+)\]\]")
_FENCE_RE = re.compile(r"^\s*```")

# Task names cited here that belong to a DIFFERENT repo. Keep each justified;
# prefer fixing the doc over growing this list.
_EXTERNAL_TASKS = frozenset(
    {
        # `mise-tasks-only.md` routes knowledge-base PRs to the KB repo's own
        # tasks, and says so on the same line. They are correct citations of
        # something this repo deliberately does not define.
        "kb-ship",
        "kb-land",
    }
)

# Skills cited by name that this repo does not (and should not) ship.
_EXTERNAL_SKILLS = frozenset(
    {
        # A Claude Code built-in, cited by `mise-tasks-only.md` as the inverse
        # of `command-audit`. Not a project skill and never will be.
        "fewer-permission-prompts",
        # Lives in the knowledge-base repo; `.claude/CLAUDE.md` names the repo
        # on the same line.
        "orchestrator-routing",
    }
)


def declared_mise_tasks(repo_root: Path) -> set[str]:
    """Every task name and alias this REPO declares, read from its own config.

    Deliberately not ``mise tasks``: that merges the invoking user's global
    config, so it reports names no file in this repo defines (this Mac's global
    config contributes four ``update:*`` tasks). A doc in this repo must cite a
    task this repo declares, so the tracked config is the correct binding — and
    it keeps the check offline, which is what lets it ride the existing
    pre-commit step instead of needing a mise subprocess.

    Aliases count: ``down`` is an alias of ``stop`` and three docs cite it, so
    dropping aliases would report three correct citations as broken.
    """
    names: set[str] = set()
    conf_d = repo_root / ".config" / "mise" / "conf.d"
    configs = [repo_root / "mise.toml", *sorted(conf_d.glob("*.toml"))]
    for config in configs:
        if not config.exists():
            continue
        tasks = tomllib.loads(config.read_text()).get("tasks", {})
        for name, body in tasks.items():
            names.add(name)
            alias = body.get("alias") if isinstance(body, dict) else None
            if isinstance(alias, str):
                names.add(alias)
            elif isinstance(alias, list):
                names.update(a for a in alias if isinstance(a, str))
    return names


def declared_skills(repo_root: Path) -> set[str]:
    """Project skill names — the directories Claude Code's loader scans."""
    skills = repo_root / ".claude" / "skills"
    if not skills.is_dir():
        return set()
    return {p.name for p in skills.iterdir() if (p / "SKILL.md").exists()}


def _declared_rules(repo_root: Path) -> set[str]:
    return {p.stem for p in (repo_root / ".claude" / "rules").glob("*.md")}


def _doc_lines(repo_root: Path, doc: str) -> list[tuple[int, str, bool]]:
    """Yield (lineno, text, in_fence) for one doc."""
    out: list[tuple[int, str, bool]] = []
    in_fence = False
    for lineno, line in enumerate((repo_root / doc).read_text().splitlines(), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        out.append((lineno, line, in_fence))
    return out


def find_unresolved_task_refs(repo_root: Path) -> list[UnresolvedRef]:
    """Return every ``mise run <task>`` citation naming a task that is absent.

    Scans inline backtick spans AND fenced code blocks. The fence half is not
    optional: the repo's own Quick Start lists a dozen tasks inside a ```bash
    fence, so an inline-only scan would leave the most-read task list in the
    repo unguarded.

    A bare ``mise run`` mention (no task name inside the span) is prose — the
    next word is not a task. Without that distinction ``mise-tasks-only.md``'s
    "add a `mise run` task" reports a task named ``task``, and a gate that
    invents violations is a gate someone switches off.
    """
    declared = declared_mise_tasks(repo_root)
    unresolved: list[UnresolvedRef] = []
    for doc in _tracked_files(repo_root, DOC_PATHSPECS):
        for lineno, line, in_fence in _doc_lines(repo_root, doc):
            candidates = [line] if in_fence else _SPAN_RE.findall(line)
            for candidate in candidates:
                for match in _TASK_RE.finditer(candidate):
                    task = match.group(1)
                    if task in declared or task in _EXTERNAL_TASKS:
                        continue
                    unresolved.append(UnresolvedRef(doc=doc, line=lineno, ref=task))
    return unresolved


def find_unresolved_skill_refs(repo_root: Path) -> list[UnresolvedRef]:
    """Return every skill cited by NAME that has no ``SKILL.md`` on disk.

    Two citation forms are in live use: ``` `name` skill ``` and ``[[name]]``.
    Wikilinks resolve against rules as well as skills — ``[[zero-skip-policy]]``
    is a rule, and resolving them against skills alone would report every one
    of them as broken.

    Two exclusions, both from running this against the live tree before wiring
    it up. A backticked ``[[wikilink]]`` NAMES the syntax rather than citing
    anything (``memory-index-curation`` does exactly that), and a
    ``plugin:skill`` name belongs to an installed plugin, so a repo-local
    existence check on it can only be wrong.
    """
    known = declared_skills(repo_root) | _declared_rules(repo_root)
    unresolved: list[UnresolvedRef] = []
    for doc in _tracked_files(repo_root, DOC_PATHSPECS):
        for lineno, line, _in_fence in _doc_lines(repo_root, doc):
            refs = [m.group(1) for m in _SKILL_RE.finditer(line)]
            # A wikilink inside a backtick span is a syntax mention.
            stripped = _SPAN_RE.sub(" ", line)
            refs += [m.group(1) for m in _WIKILINK_RE.finditer(stripped)]
            for ref in refs:
                if ":" in ref or ref in known or ref in _EXTERNAL_SKILLS:
                    continue
                unresolved.append(UnresolvedRef(doc=doc, line=lineno, ref=ref))
    return unresolved


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
