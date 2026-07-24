"""Verification suite runner with TOML manifest."""

from __future__ import annotations

import json
import logging
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

from dotfiles_setup import _project_root

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Raised when a verification check fails."""


def load_manifest(path: Path) -> list[dict[str, Any]]:
    """Load verification suites from a TOML manifest.

    Args:
        path: Path to the TOML manifest file.

    Returns:
        List of suite entry dictionaries.
    """
    with path.open("rb") as f:
        data = tomllib.load(f)
    suites: list[dict[str, Any]] = data.get("suite", [])
    return suites


def _missing_paths(entry: dict[str, Any]) -> list[str]:
    """Return the entry's declared paths that do not exist on disk."""
    root = _project_root()
    return [raw for raw in entry.get("paths", []) if not (root / raw).exists()]


def run_suite(
    entry: dict[str, Any],
    *,
    handlers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single verification suite entry.

    A declared path that no longer exists FAILS the suite unless the entry
    opts out with ``paths_required = false``. This is enforced here — before
    dispatch — rather than inside any one handler, because *partial* path loss
    is invisible from inside: every handler resolves its paths through
    :func:`_resolve_paths`, which silently drops what is gone, so a suite
    naming two files keeps passing on the strength of the one that survives.
    Proven both arms on 2026-07-16 (delete one of two -> still PASSED; delete
    both -> correctly failed, so the probe discriminated). Spec #299.

    Default-strict rather than opt-in: at the time of the change **0 of 97**
    suites declared a missing path, so it was a no-op then and a gate since —
    and a suite written later is protected without its author remembering.

    Args:
        entry: Suite entry dictionary with name and handler keys.
        handlers: Optional handler map; defaults to built-in HANDLERS.

    Returns:
        Result dictionary with name, status, and optional reason.
    """
    name: str = entry["name"]
    handler_name: str = entry.get("handler", name.replace(".", "_").replace("-", "_"))
    all_handlers = handlers if handlers is not None else HANDLERS

    if handler_name not in all_handlers:
        return {
            "name": name,
            "status": "failed",
            "reason": f"Handler '{handler_name}' not found",
        }

    if entry.get("paths_required", True):
        missing = _missing_paths(entry)
        if missing:
            description = entry.get("description", "")
            reason = f"required path(s) missing: {', '.join(missing)}"
            return {
                "name": name,
                "status": "failed",
                "reason": f"{description}: {reason}" if description else reason,
            }

    try:
        result: dict[str, Any] = all_handlers[handler_name](entry)
        result.setdefault("name", name)
        result.setdefault("status", "passed")
    except VerificationError as exc:
        return {"name": name, "status": "failed", "reason": str(exc)}
    except (TypeError, ValueError, KeyError, OSError, RuntimeError) as exc:
        return {"name": name, "status": "failed", "reason": f"Unexpected: {exc}"}
    else:
        return result


def fail(reason: str) -> None:
    """Raise a VerificationError.

    Args:
        reason: Human-readable failure description.

    Raises:
        VerificationError: Always raised with the given reason.
    """
    raise VerificationError(reason)


def _resolve_paths(entry: dict[str, Any]) -> list[Path]:
    """Resolve paths from a suite entry relative to the project root.

    Args:
        entry: Suite entry with a 'paths' key.

    Returns:
        List of existing Path objects.
    """
    root = _project_root()
    return [p for p in (root / raw for raw in entry.get("paths", [])) if p.exists()]


# ---------------------------------------------------------------------------
# Generic handlers — all parameterized via TOML entry fields
# ---------------------------------------------------------------------------


def forbid_tokens(
    paths: list[Path],
    tokens: list[str],
    *,
    description: str = "",
    allowlist: list[str] | None = None,
    strip_comments: bool = True,
) -> dict[str, Any]:
    """Check that none of the given tokens appear in the given files.

    Args:
        paths: Files to scan.
        tokens: Strings that must not appear.
        description: Optional description for error messages.
        allowlist: Regex patterns; lines matching any are skipped.
        strip_comments: Strip text after '#' before matching (default
            True; set False for JSON/YAML-string content — finding [23]).

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If any token is found in any file.
    """
    allowlist_patterns = [re.compile(p) for p in (allowlist or [])]
    violations: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        lines = path.read_text().splitlines()
        for line in lines:
            # Review finding [23]: '#' starts a comment in TOML/shell but
            # NOT in JSON/YAML-strings — stripping there creates false
            # negatives. strip_comments=False disables it per-contract.
            content = line.split("#", 1)[0] if strip_comments else line
            if any(p.search(line) for p in allowlist_patterns):
                continue
            violations.extend(
                f"{path}: contains '{token}'" for token in tokens if token in content
            )
    if violations:
        fail(
            f"{description}: " + "; ".join(violations)
            if description
            else "; ".join(violations)
        )
    return {"status": "passed"}


def require_tokens(
    paths: list[Path],
    tokens: list[str],
    *,
    description: str = "",
) -> dict[str, Any]:
    """Check that all given tokens appear in at least one of the given files.

    Args:
        paths: Files to scan.
        tokens: Strings that must appear.
        description: Optional description for error messages.

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If any token is missing from all files.
    """
    if not paths:
        fail(
            f"{description}: no target files found"
            if description
            else "no target files found"
        )

    combined = "\n".join(p.read_text() for p in paths if p.exists())
    missing = [t for t in tokens if t not in combined]
    if missing:
        msg = "; ".join(f"missing '{t}'" for t in missing)
        fail(f"{description}: {msg}" if description else msg)
    return {"status": "passed"}


def _normalise(line: str) -> str:
    """Collapse every run of whitespace to one space and strip the ends."""
    return " ".join(line.split())


def require_lines(
    paths: list[Path],
    lines: list[str],
    *,
    description: str = "",
    per_path_lines: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Check that whole LINES are present, matched exactly modulo whitespace.

    Why this is not :func:`require_tokens` (#354 PR 1). The bug that opened
    #354 was an absent orchestrator *trigger line*. Substring binding notices
    that absence — but it equally accepts the sentence quoted inside prose that
    *narrates* the declaration instead of making it, which is the state the
    repo was actually in. `feedback_forbid_tokens_substring_fragile` and the
    `per_path_tokens` lesson (#299) both say the same thing from the other
    direction: a substring is the wrong binding for a sentence. A declaration
    is a whole line or it is not that declaration.

    Whitespace is normalised, and only whitespace. Re-indenting a list item or
    reflowing the spaces inside it changes bytes, not meaning, so a gate that
    fired on that would be a formatter tripwire nobody keeps. Rewording is a
    different matter and must fail — both directions are pinned in
    ``tests/test_verify.py``.

    **A bare ``lines`` list must hold in EVERY listed path.** This inverts
    :func:`require_tokens`'s union default deliberately. That union is the
    footgun `per_path_tokens` had to be retrofitted to work around — a suite
    naming two files had no opinion about either, and
    ``build.path-includes-mise-shims`` stayed green for ~3.5 months on the
    strength of a file that was not the one it meant. This handler is new, so
    the strict reading is free; ``per_path_lines`` covers the asymmetric case.

    Args:
        paths: Files to scan.
        lines: Lines that must appear in every one of ``paths``.
        description: Optional description for error messages.
        per_path_lines: Repo-relative path -> lines that THAT file must carry.

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If any required line is missing from any file it
            was bound to.
    """
    problems: list[str] = []

    if per_path_lines:
        root = _project_root()
        for raw, wanted in per_path_lines.items():
            target = root / raw
            present = (
                {_normalise(one) for one in target.read_text().splitlines()}
                if target.exists()
                else set()
            )
            problems.extend(
                f"{raw}: missing line '{one}'"
                for one in wanted
                if _normalise(one) not in present
            )

    if lines:
        if not paths:
            fail(
                f"{description}: no target files found"
                if description
                else "no target files found"
            )
        for path in paths:
            present = {_normalise(one) for one in path.read_text().splitlines()}
            problems.extend(
                f"{path}: missing line '{one}'"
                for one in lines
                if _normalise(one) not in present
            )

    if problems:
        joined = "; ".join(problems)
        fail(f"{description}: {joined}" if description else joined)
    return {"status": "passed"}


def regex_match(
    paths: list[Path],
    pattern: str,
    *,
    description: str = "",
    match_all_paths: bool = False,
) -> dict[str, Any]:
    """Check that a regex pattern matches in at least one of the given files.

    Args:
        paths: Files to scan.
        pattern: Regex pattern that must match.
        description: Optional description for error messages.
        match_all_paths: Require the pattern in EVERY listed path
            (finding [22]); default False = any one path.

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If pattern does not match in any file.
    """
    if not paths:
        fail(
            f"{description}: no target files found"
            if description
            else "no target files found"
        )

    compiled = re.compile(pattern, re.MULTILINE)
    if match_all_paths:
        # Review finding [22]: 'in both files' contracts need every path
        # to match, not any one of them.
        misses = [
            str(path)
            for path in paths
            if not (path.exists() and compiled.search(path.read_text()))
        ]
        if misses:
            fail(
                f"{description}: pattern '{pattern}' not found in: " + ", ".join(misses)
            )
        return {"status": "passed"}
    for path in paths:
        if path.exists() and compiled.search(path.read_text()):
            return {"status": "passed"}
    fail(
        f"{description}: pattern '{pattern}' not found"
        if description
        else f"pattern '{pattern}' not found"
    )
    return {"status": "failed"}  # unreachable, but satisfies type checker


def regex_forbid(
    paths: list[Path],
    pattern: str,
    *,
    description: str = "",
    allowlist: list[str] | None = None,
) -> dict[str, Any]:
    """Check that a regex pattern does NOT match in any of the given files.

    Args:
        paths: Files to scan.
        pattern: Regex pattern that must not match.
        description: Optional description for error messages.
        allowlist: Regex patterns; lines matching any are skipped.

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If pattern matches in any file.
    """
    compiled = re.compile(pattern, re.MULTILINE)
    allowlist_patterns = [re.compile(p) for p in (allowlist or [])]
    violations: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            content = line.split("#", 1)[0]
            if any(p.search(line) for p in allowlist_patterns):
                continue
            if compiled.search(content):
                violations.append(f"{path}:{i}")
    if violations:
        msg = f"pattern '{pattern}' found at: " + ", ".join(violations)
        fail(f"{description}: {msg}" if description else msg)
    return {"status": "passed"}


def dockerfile_structure(
    path: Path,
    before: str,
    after: str,
    *,
    description: str = "",
) -> dict[str, Any]:
    """Verify that 'before' appears before 'after' in a Dockerfile.

    Args:
        path: Dockerfile to check.
        before: Token that must appear first.
        after: Token that must appear second.
        description: Optional description for error messages.

    Returns:
        Result dictionary with status key.

    Raises:
        VerificationError: If ordering is violated.
    """
    if not path.exists():
        fail(f"{description}: {path} not found" if description else f"{path} not found")

    text = path.read_text()
    before_pos = text.find(before)
    after_pos = text.find(after)

    if before_pos == -1:
        fail(
            f"{description}: '{before}' not found in {path}"
            if description
            else f"'{before}' not found in {path}"
        )
    if after_pos == -1:
        fail(
            f"{description}: '{after}' not found in {path}"
            if description
            else f"'{after}' not found in {path}"
        )
    if before_pos > after_pos:
        fail(
            f"{description}: '{before}' must appear before '{after}'"
            if description
            else f"'{before}' must appear before '{after}'"
        )
    return {"status": "passed"}


def policy_doc(entry: dict[str, Any]) -> dict[str, Any]:
    """Non-automatable policy check — always returns skipped.

    Args:
        entry: Suite entry with reference key pointing to policy doc.

    Returns:
        Result dictionary with skipped status.
    """
    ref = entry.get("reference", "unknown")
    return {"status": "skipped", "reason": f"Human-only policy (see {ref})"}


# ---------------------------------------------------------------------------
# Handler dispatch — wraps generic functions with entry-based parameter extraction
# ---------------------------------------------------------------------------


def _handle_forbid_tokens(entry: dict[str, Any]) -> dict[str, Any]:
    paths = _resolve_paths(entry)
    return forbid_tokens(
        paths,
        entry.get("tokens", []),
        description=entry.get("description", ""),
        allowlist=entry.get("allowlist"),
        strip_comments=entry.get("strip_comments", True),
    )


def _handle_require_tokens(entry: dict[str, Any]) -> dict[str, Any]:
    description = entry.get("description", "")
    # Review finding [21] (a listed path that no longer exists must FAIL) is
    # enforced for EVERY handler in run_suite, default-strict — see spec #299.
    # Review findings [19]/[22]: per-path token requirements — combined-text
    # semantics let a token in ANY listed file satisfy the contract, so
    # "wired in settings.json" could be satisfied by the rule doc alone.
    per_path = entry.get("per_path_tokens", {})
    if per_path:
        root = _project_root()
        problems: list[str] = []
        for raw, tokens in per_path.items():
            target = root / raw
            text = target.read_text() if target.exists() else ""
            problems.extend(
                f"{raw}: missing '{tok}'" for tok in tokens if tok not in text
            )
        if problems:
            fail(f"{description}: " + "; ".join(problems))
    paths = _resolve_paths(entry)
    return require_tokens(
        paths,
        entry.get("tokens", []),
        description=description,
    )


def _handle_require_lines(entry: dict[str, Any]) -> dict[str, Any]:
    paths = _resolve_paths(entry)
    return require_lines(
        paths,
        entry.get("lines", []),
        description=entry.get("description", ""),
        per_path_lines=entry.get("per_path_lines"),
    )


def _handle_regex_match(entry: dict[str, Any]) -> dict[str, Any]:
    paths = _resolve_paths(entry)
    return regex_match(
        paths,
        entry.get("pattern", ""),
        description=entry.get("description", ""),
        match_all_paths=entry.get("match_all_paths", False),
    )


def _handle_regex_forbid(entry: dict[str, Any]) -> dict[str, Any]:
    paths = _resolve_paths(entry)
    return regex_forbid(
        paths,
        entry.get("pattern", ""),
        description=entry.get("description", ""),
        allowlist=entry.get("allowlist"),
    )


def _handle_dockerfile_structure(entry: dict[str, Any]) -> dict[str, Any]:
    # Review finding [26]: resolve against the project root (like every
    # other handler), not the invoker's cwd.
    root = _project_root()
    paths = entry.get("paths", [])
    path = root / paths[0] if paths else root / ".devcontainer" / "Dockerfile"
    return dockerfile_structure(
        path,
        entry.get("before", ""),
        entry.get("after", ""),
        description=entry.get("description", ""),
    )


def _handle_no_vscode_user(entry: dict[str, Any]) -> dict[str, Any]:
    """Legacy handler — delegates to forbid_tokens with expanded paths."""
    return _handle_forbid_tokens(entry)


HANDLERS: dict[str, Any] = {
    "forbid_tokens": _handle_forbid_tokens,
    "require_tokens": _handle_require_tokens,
    "require_lines": _handle_require_lines,
    "regex_match": _handle_regex_match,
    "regex_forbid": _handle_regex_forbid,
    "dockerfile_structure": _handle_dockerfile_structure,
    "policy_doc": policy_doc,
    "no_vscode_user": _handle_no_vscode_user,
}


def main(
    manifest_path: Path | None = None,
    *,
    suite_filter: str | None = None,
    category_filter: list[str] | None = None,
    output_json: bool = False,
    list_only: bool = False,
) -> int:
    """Run verification suites and report results.

    Args:
        manifest_path: Path to suites.toml manifest.
            Defaults to python/verification/suites.toml.
        suite_filter: If set, only run the suite with this name.
        category_filter: If set, only run suites matching these categories.
        output_json: If True, output results as JSON to stdout.
        list_only: If True, list suites instead of running them.

    Returns:
        Exit code: 0 if all passed, 1 if any failed.
    """
    if manifest_path is None:
        # Resolve relative to package location -> python/verification/
        manifest_path = (
            Path(__file__).parent.parent.parent / "verification" / "suites.toml"
        )

    if not manifest_path.exists():
        logger.error("Manifest not found: %s", manifest_path)
        return 1

    suites = load_manifest(manifest_path)
    if suite_filter:
        suites = [s for s in suites if s["name"] == suite_filter]
    if category_filter:
        suites = [s for s in suites if s.get("category") in category_filter]

    if list_only:
        sys.stderr.write(f"{'NAME':<40} {'CATEGORY':<15} {'HANDLER':<20} DESCRIPTION\n")
        sys.stderr.write("-" * 100 + "\n")
        for s in suites:
            sys.stderr.write(
                f"{s['name']:<40} {s.get('category', '-'):<15} "
                f"{s.get('handler', '-'):<20} {s.get('description', '')}\n"
            )
        sys.stderr.write(f"\n{len(suites)} constraint(s)\n")
        return 0

    results = [run_suite(entry) for entry in suites]
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    if output_json:
        json.dump(
            {
                "results": results,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        for r in results:
            status = r["status"].upper()
            reason = f" :: {r.get('reason', '')}" if r.get("reason") else ""
            sys.stderr.write(f"{status} {r['name']}{reason}\n")
        sys.stderr.write(f"\n{passed} passed, {failed} failed, {skipped} skipped\n")

    return 1 if failed > 0 else 0
