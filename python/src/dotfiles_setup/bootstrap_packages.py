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

import json
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

APT_PREFIX = "apt:"
_BAD_STATES = ("missing", "version_mismatch")


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


def gap_report_failures(status_json: str, mise_system_toml: Path) -> list[str]:
    """Check a `mise bootstrap packages status --json` report; return failures.

    The CI gap report (#160 T7) must fail on conditions the build-time
    `status --missing` exit code cannot see:

    - the apt manager unexpectedly unavailable (`available: false`) —
      unavailable managers emit state "skipped" and do NOT trip `--missing`;
    - any package in state "missing" or "version_mismatch";
    - the reported package set drifting from the declared
      `[bootstrap.packages]` set — a config-discovery failure inside the
      image would otherwise produce an empty, trivially-green report.
    """
    failures: list[str] = []
    report = json.loads(status_json)
    apt = report.get("apt")
    if apt is None:
        return [f"no 'apt' manager in status report (managers: {sorted(report)})"]
    if not apt.get("available", False):
        reason = apt.get("reason", "no reason given")
        failures.append(f"apt manager unexpectedly unavailable: {reason}")
    packages = apt.get("packages", [])
    for entry in packages:
        state = entry.get("state")
        if state in _BAD_STATES:
            failures.append(
                f"{entry.get('package')}: {state} "
                f"(requested {entry.get('requested_version')}, "
                f"installed {entry.get('installed_version')})"
            )
    declared = set(apt_packages_from_bootstrap(mise_system_toml))
    reported = {entry.get("package") for entry in packages}
    failures.extend(
        f"{name}: declared in [bootstrap.packages] but absent from status report"
        for name in sorted(declared - reported)
    )
    failures.extend(
        f"{name}: reported by status but not declared in [bootstrap.packages]"
        for name in sorted(reported - declared)
    )
    return failures
