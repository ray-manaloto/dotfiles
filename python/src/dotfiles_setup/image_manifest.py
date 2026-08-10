# Copyright (c) 2026 Raymond Manaloto
r"""Verify a published multi-architecture index against its per-architecture tags.

This is `build-publish.yml`'s **AC2**: every `:<sha>-<arch>` tag must resolve to
the *same image* the multi-architecture `:<sha>` index lists for that
architecture, and the architectures must be genuinely distinct.

## The defect this module exists to fix (#703)

AC2 shipped as inline bash comparing

    docker buildx imagetools inspect "$IMAGE:$sha-$suffix" \\
        --format '{{.Manifest.Digest}}'

against the digest the index lists for that architecture. **Those can never be
equal.** `dev-tag` creates the per-architecture tag with `docker buildx
imagetools create --tag`, and `--prefer-index` **defaults true**, so the tag is
an *index* wrapping the real manifest plus its attestation. `{{.Manifest.Digest}}`
returns the digest of that **outer index**; the multi-architecture index lists
the **inner manifest**. Measured against the live registry:

    :6d1f1df-amd64  {{.Manifest.Digest}} = sha256:9d9ab82…   (the outer index)
                    matching inner image = sha256:f52f092…   (what :6d1f1df lists)

So AC2 was **a check that can only fail** — in a step whose own comment cites
`.claude/rules/probes-need-a-control-arm.md` about exactly that class.

## What is asserted, and why it is not a shape check

The repaired assertion reads *through* whatever the tag is, via the OCI
document, and binds **the capability we depend on**:

1. the per-architecture tag resolves to **exactly one** real platform —
   `unknown/unknown` attestation entries never count as coverage;
2. that platform is `linux/<the arch in the tag suffix>`;
3. its digest is **the digest the multi-architecture index lists** for that
   architecture;
4. no two index entries share a digest (single-architecture wearing two labels).

Deliberately **not** "buildx emits an index". That would bind a buildx default
this project does not own, so an upstream flip would turn AC2 red without
anything actually breaking — `probes-need-a-control-arm.md` rule 9. Both shapes
are handled (index-wrapping-a-manifest *and* a bare manifest) and the observed
shape is *reported* into the step summary, so a default change is visible
rather than silently altering what ships.

The registry reads are injected as an :class:`Inspector` so the decision logic
is unit-testable without docker — the same seam
:func:`dotfiles_setup.image.decide_analysis_target` uses, and the only way this
gate can carry a FAIL arm at all, since the workflow step cannot run locally.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

__all__ = [
    "ArchTarget",
    "Inspector",
    "ResolvedTag",
    "docker_inspector",
    "parse_matrix",
    "real_platform_entries",
    "resolve_arch_tag",
    "verify_arch_tags",
]

#: Buildx writes an ``unknown/unknown`` attestation entry beside each real
#: platform, so entries are filtered rather than counted — an index of one image
#: and one attestation would otherwise look like two architectures.
UNKNOWN = "unknown"

#: Every architecture this project publishes is a Linux one; a tag that resolved
#: to some other OS would satisfy an arch-only comparison.
EXPECTED_OS = "linux"


@dataclasses.dataclass(frozen=True)
class ArchTarget:
    """One published architecture and the tag suffix that names it."""

    arch: str
    tag_suffix: str


@dataclasses.dataclass(frozen=True)
class ResolvedTag:
    """The single real image a per-architecture tag resolves to."""

    digest: str
    os: str
    architecture: str
    #: ``"index"`` or ``"manifest"`` — reported, never asserted on (see module
    #: docstring: asserting it would bind a buildx default we do not own).
    shape: str

    @property
    def platform(self) -> str:
        """``os/architecture``, the form every error message quotes."""
        return f"{self.os}/{self.architecture}"


@dataclasses.dataclass(frozen=True)
class Inspector:
    """The three registry reads AC2 needs, injected so the logic is testable.

    ``raw`` returns the OCI document itself (``--raw``); ``image_config``
    returns buildx's ``{{json .Image}}`` (a single config object for a
    single-platform ref, a platform-keyed map otherwise); ``manifest_digest``
    returns ``{{.Manifest.Digest}}``, the digest of whatever the tag points at.
    """

    raw: Callable[[str], str]
    image_config: Callable[[str], str]
    manifest_digest: Callable[[str], str]


def _inspect(ref: str, *args: str) -> str:
    return subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref, *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def docker_inspector() -> Inspector:
    """The real registry reader, backed by ``docker buildx imagetools``."""
    return Inspector(
        raw=lambda ref: _inspect(ref, "--raw"),
        image_config=lambda ref: _inspect(ref, "--format", "{{json .Image}}"),
        manifest_digest=lambda ref: _inspect(ref, "--format", "{{.Manifest.Digest}}"),
    )


def parse_matrix(text: str) -> tuple[ArchTarget, ...]:
    """Read the build matrix the legs fanned out over.

    Taking the targets from the *matrix* rather than from
    :data:`~dotfiles_setup.platform_target.PUBLISHED_ARCHES` keeps the check
    bound to what CI actually built — a published architecture cannot be
    silently left out of the verification the way a hard-coded list allows.
    """
    return tuple(
        ArchTarget(arch=entry["arch"], tag_suffix=entry["tag_suffix"])
        for entry in json.loads(text)
    )


def _is_real(platform: Mapping[str, Any]) -> bool:
    os_name = platform.get("os")
    arch = platform.get("architecture")
    return os_name not in (None, UNKNOWN) and arch not in (None, UNKNOWN)


def real_platform_entries(doc: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Index entries describing a real image, attestations excluded.

    Returns ``[]`` for a document that is not an index at all, which callers
    distinguish from "an index with no real entries" by checking ``manifests``
    themselves — the two mean very different things.
    """
    manifests = doc.get("manifests")
    if manifests is None:
        return []
    return [entry for entry in manifests if _is_real(entry.get("platform") or {})]


def _one_real_platform(ref: str, entries: Sequence[Mapping[str, Any]]) -> ValueError:
    found = [
        f"{(e.get('platform') or {}).get('os')}/"
        f"{(e.get('platform') or {}).get('architecture')}"
        for e in entries
    ]
    offer = ", ".join(found) if found else "none"
    msg = (
        f"FAIL: {ref} resolves to {len(entries)} real platforms ({offer}) — a "
        f"per-architecture tag must resolve to exactly one image, or a caller "
        f"pulling it gets whichever the registry picks"
    )
    return ValueError(msg)


def resolve_arch_tag(ref: str, *, inspector: Inspector) -> ResolvedTag:
    """The one real image ``ref`` resolves to, whatever document shape it is.

    An **index** (buildx's current default for ``imagetools create``) is read
    through to its single non-attestation entry. A bare **manifest** carries no
    platform of its own, so the platform comes from the image config and the
    digest from the tag's own descriptor — the tag *is* the image there.
    """
    doc = json.loads(inspector.raw(ref))
    if doc.get("manifests") is not None:
        entries = real_platform_entries(doc)
        if len(entries) != 1:
            raise _one_real_platform(ref, entries)
        platform = entries[0]["platform"]
        return ResolvedTag(
            digest=entries[0]["digest"],
            os=platform["os"],
            architecture=platform["architecture"],
            shape="index",
        )
    config = json.loads(inspector.image_config(ref))
    if "architecture" not in config:
        # `{{json .Image}}` is a platform-keyed MAP for a multi-platform ref,
        # so a missing `architecture` key is the same breach as an index with
        # two real entries — reported through one message, not two.
        raise _one_real_platform(
            ref,
            [
                {
                    "platform": {
                        "os": key.split("/")[0],
                        "architecture": key.split("/")[1],
                    }
                }
                for key in config
                if "/" in key
            ],
        )
    return ResolvedTag(
        digest=inspector.manifest_digest(ref),
        os=config["os"],
        architecture=config["architecture"],
        shape="manifest",
    )


def _index_entry_digest(
    entries: Sequence[Mapping[str, Any]], arch: str, index_ref: str
) -> str:
    matches = [
        entry
        for entry in entries
        if entry["platform"].get("os") == EXPECTED_OS
        and entry["platform"].get("architecture") == arch
    ]
    offer = (
        ", ".join(
            f"{entry['platform'].get('os')}/{entry['platform'].get('architecture')}"
            for entry in entries
        )
        or "none"
    )
    if not matches:
        msg = (
            f"FAIL: no {arch} entry in {index_ref} "
            f"(expected {EXPECTED_OS}/{arch}; present: {offer})"
        )
        raise ValueError(msg)
    if len(matches) != 1:
        msg = (
            f"FAIL: expected exactly one {EXPECTED_OS}/{arch} entry in "
            f"{index_ref}, found {len(matches)} (present: {offer})"
        )
        raise ValueError(msg)
    return str(matches[0]["digest"])


def verify_arch_tags(
    *,
    index_ref: str,
    targets: Sequence[ArchTarget],
    inspector: Inspector,
) -> list[str]:
    """Assert AC2 across every published architecture; return the report lines.

    Per-architecture tags are derived as ``<index_ref>-<tag_suffix>``, which is
    exactly how the ``merge`` step above constructs them.

    Raises:
        ValueError: on the first breach, with a message naming both digests —
            the four conditions are in the module docstring.
    """
    index_doc = json.loads(inspector.raw(index_ref))
    entries = real_platform_entries(index_doc)
    expected_platforms = {(EXPECTED_OS, target.arch) for target in targets}
    unexpected = [
        entry
        for entry in entries
        if (
            entry["platform"].get("os"),
            entry["platform"].get("architecture"),
        )
        not in expected_platforms
    ]
    if unexpected:
        offer = ", ".join(
            f"{entry['platform'].get('os')}/{entry['platform'].get('architecture')}"
            for entry in unexpected
        )
        msg = f"FAIL: unexpected real platform entries in {index_ref}: {offer}"
        raise ValueError(msg)
    lines: list[str] = []
    digests: list[str] = []
    for target in targets:
        entry_digest = _index_entry_digest(entries, target.arch, index_ref)
        tag = f"{index_ref}-{target.tag_suffix}"
        resolved = resolve_arch_tag(tag, inspector=inspector)
        expected_platform = f"{EXPECTED_OS}/{target.arch}"
        if resolved.platform != expected_platform:
            msg = (
                f"FAIL: {tag} resolves to {resolved.platform}, not "
                f"{expected_platform} — the tag suffix does not describe what a "
                f"caller pulling it actually gets"
            )
            raise ValueError(msg)
        if resolved.digest != entry_digest:
            msg = (
                f"FAIL: {tag} resolves to {resolved.digest} but the index's "
                f"{target.arch} entry is {entry_digest}"
            )
            raise ValueError(msg)
        digests.append(entry_digest)
        lines.append(f"{target.arch}: {entry_digest} (tag shape: {resolved.shape})")
    if len(set(digests)) != len(digests):
        msg = "FAIL: index entries share a digest — not really multi-architecture"
        raise ValueError(msg)
    return lines
