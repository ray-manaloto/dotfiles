# Copyright (c) 2026 Raymond Manaloto
"""Bind explicit caller scope at the native prompt-submission boundary.

The native event is the authority, not a later declaration file or model text.
Persisted bindings are integrity records, not protection against a process with
write access to hook state. Native client qualification must establish delivery
of the caller's original prompt to UserPromptSubmit.
"""

from __future__ import annotations

import hashlib
import json
import re

LOCAL_ONLY_DIRECTIVE = "[research-scope: local-only]"
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def bind_submission(
    prompt: str, session_id: str, turn_id: str
) -> dict[str, str] | None:
    """Bind only an exact first-line directive supplied in the caller prompt."""
    if prompt.partition("\n")[0] != LOCAL_ONLY_DIRECTIVE:
        return None
    binding = {
        "source": "UserPromptSubmit",
        "scope": "local-only",
        "session_id": session_id,
        "turn_id": turn_id,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }
    return {**binding, "binding_sha256": _binding_digest(binding)}


def _binding_digest(binding: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validates_binding(
    binding: object, session_id: str, turn_id: str, prompt: str | None = None
) -> bool:
    """Reject incomplete, changed or differently bound submission records.

    An optional native prompt checks the full request digest. The checksum detects
    corruption; it is deliberately not described as a caller-authentication token.
    """
    if not isinstance(binding, dict) or set(binding) != {
        "source",
        "scope",
        "session_id",
        "turn_id",
        "prompt_sha256",
        "binding_sha256",
    }:
        return False
    if not all(isinstance(value, str) for value in binding.values()):
        return False
    fields = {key: str(value) for key, value in binding.items()}
    checksum = fields.pop("binding_sha256")
    return (
        fields["source"] == "UserPromptSubmit"
        and fields["scope"] == "local-only"
        and fields["session_id"] == session_id
        and fields["turn_id"] == turn_id
        and _DIGEST.fullmatch(fields["prompt_sha256"]) is not None
        and checksum == _binding_digest(fields)
        and (prompt is None or bind_submission(prompt, session_id, turn_id) == binding)
    )
