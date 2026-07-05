"""Parse the declarative `[bootstrap.packages]` apt set.

`.devcontainer/mise-system.toml` `[bootstrap.packages]` is the single source
of truth for the image's apt packages: the Dockerfile base stage seeds only
curl + ca-certificates, then runs `mise bootstrap packages apply` against the
COPYd config (epic #160 T4, wagov-dtt pattern). Build-time drift is caught by
`mise bootstrap packages status --json --missing` (exits 1 on any missing or
version-mismatched package) in the same RUN block; the CI gap report (T7)
asserts the status JSON against this parsed set.

The Dockerfile-parsing half of this module (the old two-source anti-drift
sync) was deleted with the switch — there is no second list to drift.

mise renamed this feature from `[system.packages]` / `mise system` (2026.6.4)
to `[bootstrap.packages]` / `mise bootstrap packages` by 2026.7.0; the keys
are `manager:package` (e.g. `"apt:curl"`).
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

APT_PREFIX = "apt:"


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
