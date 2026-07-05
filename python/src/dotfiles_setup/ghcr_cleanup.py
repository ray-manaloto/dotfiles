"""GHCR retention planning for the devcontainer package (#160 T12.5, #13).

The three-tier probe cache accretes one `:base-<hash16>` / `:p2996-<hash16>`
/ `:dev-<hash16>` tag per content-hash epoch, forever. This module plans a
SAFE cleanup:

- keep the newest N versions per hash-prefix family;
- ALWAYS keep versions carrying a protected tag (`dev`, `latest`, `:sha`/
  `:pr-` tags stay out of scope entirely — only hash-family tags are ever
  prunable);
- NEVER touch untagged versions — on GHCR those are attestation/child
  manifests referenced by kept image indexes; deleting them corrupts the
  referrers of images we keep.

The planner is a pure function over the GitHub package-versions API JSON so
it is unit-testable; the CLI handler (`dotfiles-setup ghcr-cleanup`) shells
out to `gh api` and is dry-run by default — the workflow must opt in to
deletion explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Tag families produced by the content-hash probe cache. Only these are
# ever prunable; each keeps its own newest-N.
PRUNABLE_FAMILIES = ("base-", "p2996-", "dev-")
_HASH_TAG_RE = re.compile(r"^(base|p2996|dev)-[0-9a-f]{16}$")
# Tags that unconditionally protect a version.
PROTECTED_TAGS = frozenset({"dev", "latest"})
DEFAULT_KEEP_PER_FAMILY = 3


@dataclass(frozen=True)
class CleanupPlan:
    """Partition of package versions into kept and deletable."""

    delete: list[dict[str, Any]] = field(default_factory=list)
    keep_reasons: dict[int, str] = field(default_factory=dict)


def _family(tag: str) -> str | None:
    match = _HASH_TAG_RE.match(tag)
    return match.group(1) if match else None


def plan_cleanup(
    versions: list[dict[str, Any]],
    *,
    keep_per_family: int = DEFAULT_KEEP_PER_FAMILY,
) -> CleanupPlan:
    """Partition package versions into kept and deletable.

    A version is deletable ONLY when every one of its tags is a hash-family
    tag past that family's newest-``keep_per_family`` window. Untagged
    versions, protected tags, and any unrecognized tag all keep the
    version.
    """
    plan = CleanupPlan()
    # Newest first (the API returns newest first, but do not rely on it).
    ordered = sorted(versions, key=lambda v: v.get("created_at", ""), reverse=True)
    family_counts: dict[str, int] = dict.fromkeys(
        (f.rstrip("-") for f in PRUNABLE_FAMILIES), 0
    )
    for version in ordered:
        version_id = version.get("id", 0)
        tags = version.get("metadata", {}).get("container", {}).get("tags", [])
        if not tags:
            plan.keep_reasons[version_id] = (
                "untagged (attestation/child manifest of a kept index)"
            )
            continue
        if any(tag in PROTECTED_TAGS for tag in tags):
            plan.keep_reasons[version_id] = f"protected tag ({tags})"
            continue
        families = [_family(tag) for tag in tags]
        if any(fam is None for fam in families):
            plan.keep_reasons[version_id] = f"non-hash-family tag ({tags})"
            continue
        # All tags are hash-family tags; keep while within every family's
        # newest-N window, delete once every tag is past its window.
        within_window = False
        for fam in families:
            if fam is not None and family_counts[fam] < keep_per_family:
                within_window = True
            if fam is not None:
                family_counts[fam] += 1
        if within_window:
            plan.keep_reasons[version_id] = f"newest-{keep_per_family} window ({tags})"
        else:
            plan.delete.append(version)
    return plan
