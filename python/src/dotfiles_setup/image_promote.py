# Copyright (c) 2026 Raymond Manaloto
r"""Prove a `:pr-N` candidate is content-CURRENT before `promote` retags it (#1007).

## The defect this module exists to fix

`promote` (`ci.yml`'s `promote` job) retags `${IMAGE}:pr-${PR_NUMBER}` as
`:dev`/`:latest` after verifying the retag was *faithful* — same digest in,
same digest out. Nothing ever asked whether the SOURCE was *current*. When a
second PR merges shortly after a first, but its `:pr-N` image was built
*before* the first PR landed, promote republishes an image missing the first
PR's changes and `:dev` silently regresses.

Measured 2026-09-11: `:dev` carried pre-#1004 bytes for ~3h45m (stale
`shared.toml`, codex `0.152.1`, `minimum_release_age` absent) while `:pr-1004`
already had the correct content. The regression surfaced downstream, in `mise
run land`'s smoke tier-1 identity check — the local gate worked; the publish
path did not check itself.

## The signal: the existing smoke-validated marker, not a re-derivation

CI already publishes the proof this guard needs.  `build-publish.yml`'s
`dev-tag` job pushes `${IMAGE}:dev-<dev-hash>` **only after smoke-test
passes** — the "built AND smoke-validated at this exact content hash" marker.
So eligibility is provable with registry reads alone:

1. compute `dev-hash` for the checked-out `github.sha`, per architecture
   (`compute_repo_dev_hash`, which resolves `PLATFORM` the same way bake does);
2. resolve `${IMAGE}:dev-<that hash>` — the marker CI would have pushed if,
   and only if, an image built from this exact content passed smoke;
3. require its digest to equal the candidate `:pr-N` index's digest for that
   architecture, for **every** published architecture.

Registry-metadata reads only (`docker buildx imagetools inspect`, reusing
:mod:`dotfiles_setup.image_manifest`'s `Inspector` seam) — never a `docker
pull` (a candidate content re-derivation would cost a ~21GB pull per promote,
and no `crane`/`skopeo`/`oras`/`regctl` is pinned in this repo), and never a
new `org.opencontainers.image.revision`-style label (it would be legitimately
"wrong" on every dev-cache-hit reuse, since a cache hit retags an
already-validated image instead of rebuilding one for the new commit).

## Coverage gap — stated, not silently inherited

`dev-hash` covers a superset of the three tier-1 identity files (base
`mise-system.toml` + `shared.toml`, `mise-runtime.toml`) but **not** the whole
Bake model: `docker-bake.hcl`'s `_common` target and its `COMPRESSION_OUTPUT`
variable sit outside the hashed `dev` block
(:func:`dotfiles_setup.p2996_hash.gather_dev_inputs` reads only the `dev`
target). A change confined to those inputs would not move the hash, and this
guard would not catch it. This is a real, documented gap in what "current"
means here — not a claim of exhaustive Bake-input coverage.

## Failure classification — four cases, kept distinct (rule 9,
## `probes-need-a-control-arm.md`)

| condition | verdict |
|---|---|
| candidate digest differs from the expected marker's | STALE — never retag |
| expected marker tag does not exist | UNPROVABLE — never retag |
| malformed shape, wrong platform, auth/network failure | **raised**, not staleness |
| candidate and every per-arch marker match | ELIGIBLE — retag |

Collapsing an operational error into "stale" would make an outage look like a
correctness breach (and a correctness breach look like a transient outage) —
so :func:`check_promote_eligibility` returns a :class:`PromoteVerdict` for
only the first, second and fourth rows. The third row is not a verdict at
all: it propagates as whatever exception the registry read (or
:mod:`dotfiles_setup.image_manifest`'s shape assertions) raised, uncaught —
the same contract :func:`dotfiles_setup.image_manifest.resolve_arch_tag`
already uses for shape breaches.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from typing import TYPE_CHECKING, Literal

from dotfiles_setup.image_manifest import (
    EXPECTED_OS,
    Inspector,
    index_entry_digest,
    real_platform_entries,
    resolve_arch_tag,
)
from dotfiles_setup.p2996_hash import compute_repo_dev_hash
from dotfiles_setup.platform_target import published_targets

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from dotfiles_setup.image_manifest import ResolvedTag
    from dotfiles_setup.platform_target import PublishTarget

__all__ = [
    "ManifestNotFoundError",
    "PromoteVerdict",
    "check_promote_eligibility",
    "marker_ref",
]

#: Substrings `docker buildx imagetools inspect` uses for "this tag does not
#: exist" — mirrors the classification `ci.yml`'s own source-probe step
#: already applies to the SAME command, so a miss reads identically on both
#: sides of the guard.
_MISS_PATTERNS = ("manifest unknown", "not found", "no such manifest")


class ManifestNotFoundError(LookupError):
    """The expected `:dev-<hash>` marker tag does not exist in the registry.

    The ONE registry-read failure :func:`check_promote_eligibility`
    classifies as UNPROVABLE rather than letting it propagate — every other
    failure (auth, network, a malformed document) is a hard failure, per the
    module docstring's failure table.
    """


@dataclasses.dataclass(frozen=True)
class PromoteVerdict:
    """Whether a candidate `:pr-N` image may be retagged as `:dev`/`:latest`."""

    eligible: bool
    status: Literal["eligible", "stale", "unprovable"]
    #: One line per architecture already checked when the verdict was
    #: reached — the marker ref, expected hash, and both digests on a stale
    #: or eligible arm; the missing marker ref alone on an unprovable one.
    lines: tuple[str, ...]


def marker_ref(image: str, dev_hash: str) -> str:
    """The smoke-validated marker tag `dev-tag` pushes for one dev-hash."""
    return f"{image}:dev-{dev_hash}"


def _image_base(ref: str) -> str:
    """`ghcr.io/x/y` from `ghcr.io/x/y:pr-1005` — what a new tag replaces.

    Raises:
        ValueError: `ref` has no `:<tag>` suffix to derive a sibling tag from.
    """
    base, sep, _tag = ref.rpartition(":")
    if not sep:
        msg = f"{ref!r} has no ':<tag>' suffix to derive the marker image from"
        raise ValueError(msg)
    return base


def _resolve_marker(ref: str, *, inspector: Inspector) -> ResolvedTag:
    """`resolve_arch_tag(ref)`, reclassifying a missing tag as `ManifestNotFoundError`.

    Every OTHER failure (a `CalledProcessError` whose stderr does not match
    the miss patterns, a shape breach `resolve_arch_tag` itself raises)
    propagates completely unchanged — this function narrows exactly one
    condition, on purpose.
    """
    try:
        return resolve_arch_tag(ref, inspector=inspector)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if any(pattern in stderr.lower() for pattern in _MISS_PATTERNS):
            raise ManifestNotFoundError(ref) from exc
        raise


def check_promote_eligibility(
    *,
    repo_root: Path,
    candidate_ref: str,
    inspector: Inspector,
    targets: Sequence[PublishTarget] | None = None,
    clang_p2996_ref: str | None = None,
) -> PromoteVerdict:
    """Prove `candidate_ref` is content-identical to the smoke-validated marker.

    `candidate_ref` is the multi-architecture `:pr-N` index. For every
    architecture in `targets` (default: :func:`published_targets`, i.e. every
    architecture the index actually needs to publish):

    1. compute the expected `dev-hash` for `repo_root` at that architecture;
    2. resolve `${IMAGE}:dev-<that hash>` through the SAME registry seam
       `verify_arch_tags` (AC2) uses;
    3. compare its digest against the candidate index's entry for that
       architecture (:func:`~dotfiles_setup.image_manifest.index_entry_digest`,
       the identical AC2 reader — no second registry client).

    `clang_p2996_ref` mirrors `dev-hash`'s own override (`CLANG_P2996_REF`):
    an on-demand overridden-ref build must be judged against the marker THAT
    build would have pushed, not the pinned-ref one.

    Returns:
        PromoteVerdict: ``eligible`` (all architectures matched, retag is
            safe), ``stale`` (a real digest mismatch — never retag), or
            ``unprovable`` (the expected marker does not exist — never
            retag, and never treated as "current" by default).

    Raises:
        subprocess.CalledProcessError: a registry read failed for any reason
            OTHER than "this tag does not exist" (auth, network, transient
            registry error) — never reinterpreted as staleness.
        ValueError: the candidate index or the marker tag has a shape this
            module cannot read through (two real platforms, wrong OS, an
            architecture the marker does not actually cover) — a hard
            failure, not a correctness verdict.
    """
    resolved_targets = tuple(targets) if targets is not None else published_targets()
    image = _image_base(candidate_ref)

    candidate_doc = json.loads(inspector.raw(candidate_ref))
    candidate_entries = real_platform_entries(candidate_doc)

    lines: list[str] = []
    for target in resolved_targets:
        expected_hash = compute_repo_dev_hash(
            repo_root,
            platform=target.platform,
            clang_p2996_ref=clang_p2996_ref,
        )
        expected_marker = marker_ref(image, expected_hash)
        candidate_digest = index_entry_digest(
            candidate_entries, target.arch, candidate_ref
        )
        try:
            marker = _resolve_marker(expected_marker, inspector=inspector)
        except ManifestNotFoundError:
            line = (
                f"{target.arch}: expected marker {expected_marker} does not "
                f"exist — eligibility unprovable, never treated as current"
            )
            return PromoteVerdict(
                eligible=False, status="unprovable", lines=(*lines, line)
            )
        expected_platform = f"{EXPECTED_OS}/{target.arch}"
        if marker.platform != expected_platform:
            msg = (
                f"FAIL: marker {expected_marker} resolves to {marker.platform}, "
                f"not {expected_platform} — cannot use it to prove {target.arch} "
                f"eligibility (hard failure, not a staleness verdict)"
            )
            raise ValueError(msg)
        if marker.digest != candidate_digest:
            line = (
                f"{target.arch}: STALE — {candidate_ref} is {candidate_digest}, "
                f"but the smoke-validated content for this commit is "
                f"{expected_marker} -> {marker.digest} (dev-hash {expected_hash})"
            )
            return PromoteVerdict(eligible=False, status="stale", lines=(*lines, line))
        lines.append(
            f"{target.arch}: {candidate_digest} == {expected_marker} "
            f"(dev-hash {expected_hash}) — current"
        )
    return PromoteVerdict(eligible=True, status="eligible", lines=tuple(lines))
