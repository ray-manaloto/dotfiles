# Copyright (c) 2026 Raymond Manaloto
"""Strip credentials from the environment of processes this repo spawns.

`fnox activate` exports real credentials into the interactive shell, and mise
records the whole delta in ``__MISE_DIFF`` (zlib+base64) so it can undo it on
directory exit. Both are inherited by every child process — including external
tools that write artifacts we then commit.

This is containment, not the fix. The fix is fnox's own ``env = "exec"``
(v1.30.0+), which keeps the secrets out of the shell in the first place; see
`.claude/rules/secrets-out-of-the-shell-env.md`. Until that is set, a tool this
repo launches has no business inheriting an AWS secret key, so it does not.

Two strengths, because they carry different risk:

- :func:`without_env_diff` drops **only** ``__MISE_DIFF``. Nothing but mise
  reads it, and mise re-derives it, so this is safe at every boundary and is
  what the spawn sites use by default. It removes the whole blob — the single
  variable that carries every other secret in one opaque field.
- :func:`clean_env` additionally drops every credential-shaped NAME. That can
  break a child that genuinely needs one, so it is opt-in per call site, with
  an explicit ``keep`` for the exceptions.

**Neither touches your shell.** Both build a copy handed to
:func:`subprocess.run`; mise still gets its ``__MISE_DIFF`` for directory exit.
"""

from __future__ import annotations

import os
import re

# The compressed env delta. Its entire content is the leak, and no child reads
# it — mise recomputes it from config.
ENV_DIFF_NAME = "__MISE_DIFF"

# Names that carry a credential. Matched on the NAME, so a provider we have
# never heard of is covered as long as it follows the usual convention.
CREDENTIAL_NAME = re.compile(
    r"(?:^|_)(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY|"
    r"CREDENTIAL|CREDENTIALS|APP_PASSWORD|CLIENT_SECRET)(?:_|$)"
)


def is_credential(name: str) -> bool:
    """True when the variable NAME marks it as carrying a credential."""
    return name == ENV_DIFF_NAME or bool(CREDENTIAL_NAME.search(name))


def without_env_diff(base: dict[str, str] | None = None) -> dict[str, str]:
    """A copy of the environment with ``__MISE_DIFF`` removed, nothing else.

    The default strength for a spawn site: it cannot break a child, because no
    child reads the variable, and it removes the one field that carries every
    secret at once.
    """
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k != ENV_DIFF_NAME}


def clean_env(
    base: dict[str, str] | None = None, *, keep: frozenset[str] = frozenset()
) -> dict[str, str]:
    """A copy of the environment with every credential-bearing name removed.

    Args:
        base: Environment to filter. Defaults to the current process's.
        keep: Names to preserve even though they look like credentials — for a
            child that genuinely needs one. Pass it at the call site so the
            exception is visible in review rather than buried in a constant.

    Returns:
        A new dict. The caller's environment is never modified.
    """
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k in keep or not is_credential(k)}


def dropped_names(base: dict[str, str] | None = None) -> list[str]:
    """The names :func:`clean_env` would remove — for logging. Never values."""
    source = os.environ if base is None else base
    return sorted(k for k in source if is_credential(k))
