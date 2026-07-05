"""Keep `[bootstrap.packages]` in sync with the Dockerfile's apt-get list.

apt-get in `.devcontainer/Dockerfile` stays the REAL base installer (stable,
no experimental risk on the ~30-min layer). `[bootstrap.packages]` in
`.devcontainer/mise-system.toml` is the single declarative source that drives
mise's native package management for a SHADOW verify — CI runs
`mise bootstrap packages status --json` against the built image and publishes
the per-package gap report as an artifact (epic #160 T7), answering over time
"is mise's native package management mature enough to replace apt-get?".

Because the list lives in two places (the real apt-get RUN block and the
declarative section), this module extracts both and a test asserts they match,
so neither drifts. See `tests/test_bootstrap_packages.py`.

mise renamed this feature from `[system.packages]` / `mise system` (2026.6.4)
to `[bootstrap.packages]` / `mise bootstrap packages` by 2026.7.0; the keys are
`manager:package` (e.g. `"apt:curl"`).
"""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

APT_PREFIX = "apt:"
# The real installer RUN block: packages sit between the install invocation and
# the cache-cleanup `&& rm -rf`, one per backslash-continued line.
_APT_INSTALL_MARKER = "apt-get install -y --no-install-recommends"
_APT_BLOCK_END = "&& rm -rf"


def apt_packages_from_bootstrap(mise_system_toml: Path) -> list[str]:
    """Return sorted apt package names from `[bootstrap.packages]`.

    Only `apt:` keys are returned (the `system_packages.managers` scope), with
    the `apt:` prefix stripped.
    """
    data = tomllib.loads(mise_system_toml.read_text())
    packages = data.get("bootstrap", {}).get("packages", {})
    return sorted(
        key[len(APT_PREFIX) :] for key in packages if key.startswith(APT_PREFIX)
    )


def apt_packages_from_dockerfile(dockerfile: Path) -> list[str]:
    """Return sorted package names from the Dockerfile's real apt-get block.

    Raises:
        ValueError: when the apt-get install marker or its terminating
            `&& rm -rf` is absent (the block moved or the format changed —
            fail loud rather than silently returning an empty set).
    """
    text = dockerfile.read_text()
    start = text.find(_APT_INSTALL_MARKER)
    if start < 0:
        msg = f"apt-get install marker not found in {dockerfile}"
        raise ValueError(msg)
    body_start = start + len(_APT_INSTALL_MARKER)
    end = text.find(_APT_BLOCK_END, body_start)
    if end < 0:
        msg = f"apt-get block terminator {_APT_BLOCK_END!r} not found in {dockerfile}"
        raise ValueError(msg)
    block = text[body_start:end]
    # Each package is a bare token on its own continuation line; strip the
    # line-continuation backslashes and shell noise, keep valid package names.
    return sorted(
        raw
        for raw in block.replace("\\", " ").split()
        if re.fullmatch(r"[a-z0-9][a-z0-9.+-]*", raw)
    )
