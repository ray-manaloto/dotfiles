# Copyright (c) 2026 Raymond Manaloto
"""Read the caller's research scope from the native prompt submission.

The native event is the authority, not a later declaration file or model text.
Only the research scope writes hook state (round 4); its record is an
integrity record, not protection against a process with write access to hook
state. Native client qualification must establish delivery of the caller's
original prompt to UserPromptSubmit.
"""

from __future__ import annotations

import re
import unicodedata

LOCAL_ONLY_DIRECTIVE = "[research-scope: local-only]"
RESEARCH_DIRECTIVE = "[research-scope: research]"
IMPLEMENTATION_DIRECTIVE = "[research-scope: implementation]"
# Only research requires a receipt; the other scopes write no hook state.
SCOPES = frozenset({"local-only", "implementation", "text-edit", "research"})
_DIRECTIVE = re.compile(r"\[research-scope: ([a-z-]+)\]")
_NEAR_MISS_PREFIX = "[research-scope"


def _first_line(prompt: str) -> str:
    return prompt.partition("\n")[0].removesuffix("\r")


def directive(prompt: str) -> str | None:
    """Return the scope an exact caller first line declares, else None.

    A CRLF line ending is accepted; case, spacing and lookalikes are not.
    """
    match = _DIRECTIVE.fullmatch(_first_line(prompt))
    return match[1] if match is not None and match[1] in SCOPES else None


def near_miss(prompt: str) -> bool:
    """Whether line 1 looks like a directive but is not an exact one.

    Leading blanks and a BOM are dropped, then a bounded head is NFKC-folded
    (fullwidth brackets) and casefolded; each step is linear.
    """
    if directive(prompt) is not None:
        return False
    head = _first_line(prompt).lstrip().lstrip("﻿").lstrip()[:64]
    folded = unicodedata.normalize("NFKC", head).casefold()
    return folded.startswith(_NEAR_MISS_PREFIX)
