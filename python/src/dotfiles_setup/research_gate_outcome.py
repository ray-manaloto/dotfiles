# Copyright (c) 2026 Raymond Manaloto
"""Private, request-bound records of honest incomplete research termination."""

from __future__ import annotations

import json
import os
import secrets
import stat
from typing import TYPE_CHECKING

from dotfiles_setup.research_fanout import Status

if TYPE_CHECKING:
    from pathlib import Path

_PROVIDERS = frozenset(
    {
        "github-issues",
        "github-discussions",
        "github-releases",
        "exa",
        "context7",
        "firecrawl-developer",
        "firecrawl-search",
        "last30days",
    }
)
_INVOCATION_ERRORS = frozenset(
    {
        "ProcessExitError",
        "OSError",
        "FileNotFoundError",
        "PermissionError",
        "TimeoutError",
    }
)
_MANIFEST_LIMIT = 1024 * 1024


def valid_outcome(record: dict[str, object]) -> bool:
    """Accept only the closed, nonsecret INCOMPLETE outcome vocabulary."""
    outcome = record.get("outcome")
    if not isinstance(outcome, dict) or set(outcome) != {
        "status",
        "coverage_complete",
        "request_id",
        "failed_routes",
    }:
        return False
    failures = outcome.get("failed_routes")
    return (
        outcome.get("status") == "INCOMPLETE"
        and outcome.get("coverage_complete") is False
        and outcome.get("request_id") == record.get("turn_id")
        and isinstance(failures, list)
        and 1 <= len(failures) <= len(_PROVIDERS) + 1
        and all(_valid_failure(row) for row in failures)
    )


def _valid_failure(row: object) -> bool:
    if not isinstance(row, dict) or set(row) != {"route", "error_class"}:
        return False
    route, error = row.get("route"), row.get("error_class")
    return (
        isinstance(route, str)
        and isinstance(error, str)
        and (
            (route in _PROVIDERS and error == "ProviderError")
            or (route == "fnox" and error in _INVOCATION_ERRORS)
            or (route == "gate-validation" and error == "ReceiptValidationError")
        )
    )


def persist(
    marker: Path, record: dict[str, object], failures: list[dict[str, str]]
) -> None:
    """Atomically replace a binding with a private record retaining that binding."""
    updated = {
        **record,
        "outcome": {
            "status": "INCOMPLETE",
            "coverage_complete": False,
            "request_id": record["turn_id"],
            "failed_routes": failures,
        },
    }
    if not valid_outcome(updated):
        message = "invalid incomplete outcome"
        raise ValueError(message)
    staged = marker.with_name(f".{marker.name}.{secrets.token_hex(8)}.incomplete")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        with os.fdopen(os.open(staged, flags, 0o600), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(updated))
        staged.replace(marker)
    finally:
        staged.unlink(missing_ok=True)


def failed_routes(manifest: Path, request_id: str) -> list[dict[str, str]]:
    """Keep the observed invocation failure plus retained same-request history."""
    fallback = [{"route": "fnox", "error_class": "ProcessExitError"}]
    try:
        flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
        with os.fdopen(os.open(manifest, flags), "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > _MANIFEST_LIMIT:
                return fallback
            raw = handle.read(_MANIFEST_LIMIT + 1)
        data = json.loads(raw) if len(raw) <= _MANIFEST_LIMIT else None
        if (
            not isinstance(data, dict)
            or data.get("request_id") != request_id
            or data.get("policy_version") != "strict-five-v2"
            or data.get("strict_five") is not True
            or not isinstance(data.get("sources"), list)
        ):
            return fallback
        providers = {
            row["source"]
            for row in data["sources"]
            if isinstance(row, dict)
            and isinstance(row.get("source"), str)
            and row["source"] in _PROVIDERS
            and row.get("status")
            in (Status.ERROR.value, Status.SKIPPED.value, Status.EMPTY_UNVERIFIED.value)
        }
        return fallback + [
            {"route": source, "error_class": "ProviderError"}
            for source in sorted(providers)
        ]
    except OSError, ValueError, RecursionError:
        return fallback
