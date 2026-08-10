# Copyright (c) 2026 Raymond Manaloto
"""Tests for `build-publish.yml`'s AC2 verifier (dotfiles_setup.image_manifest).

The workflow step this backs **cannot be run locally** — it reads a registry
that only CI publishes to — so these are the only place its FAIL direction can
exist at all. A gate verified only on a passing case is decoration
(`.claude/rules/probes-need-a-control-arm.md`), and AC2 shipped as a check that
could only FAIL precisely because nothing ever exercised it.

Four layers:

1. **The real documents**, transcribed from `docker buildx imagetools inspect`
   against the live registry for run 31392477720 — the run whose `manifest` job
   failed. The repaired verifier must PASS on them, because nothing was ever
   wrong with what was published.
2. **The defect, pinned.** The pre-#703 reader (`{{.Manifest.Digest}}` on the
   per-architecture tag) is asserted to disagree with the index on those same
   real documents, so a revert to it fails here rather than in CI. The fake
   inspector additionally *raises* if the index path ever consults that reader.
3. **Eight FAIL arms** — wrong tag architecture, digest mismatch, two real tag
   platforms, shared digests, missing entry, duplicate architecture, wrong OS,
   and an unexpected Linux architecture. Each is a breach a caller would
   actually suffer, not a synthetic mutation.
4. **Shape-agnosticism** — a bare manifest (what buildx would publish if
   `--prefer-index` ever defaulted false) passes unchanged, proving the
   assertion binds the capability and not a buildx default; plus the CLI and
   workflow wiring, so the module cannot be perfect and unreachable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.image_manifest import (
    ArchTarget,
    Inspector,
    parse_matrix,
    real_platform_entries,
    resolve_arch_tag,
    verify_arch_tags,
)
from dotfiles_setup.main import handle_image, setup_parser

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Layer 1 — the real documents, run 31392477720, read from the live registry.
# ---------------------------------------------------------------------------

INDEX_REF = "ghcr.io/ray-manaloto/dotfiles-devcontainer:6d1f1df"

AMD64_INNER = "sha256:f52f0929713a14eae5027b6989bb13db9cefa8530f957753541531b0c5d615db"
AMD64_ATTEST = "sha256:336dda29032f03dc8186f82741671498bcd5734121155268ef0cafac6c6990e6"
#: What `{{.Manifest.Digest}}` returns for `:6d1f1df-amd64` — the OUTER index
#: buildx wrapped around the manifest. The pre-#703 assertion compared this to
#: AMD64_INNER, which is why it could only fail.
AMD64_OUTER = "sha256:9d9ab82afdc66e2b45e869e97e4cb5a641dee46e488f58b033b6513ebe2e2d4b"
ARM64_INNER = "sha256:2d80ab60cd7a9518eda22935c442497b81fb33f6839310190391705471787379"
ARM64_ATTEST = "sha256:e3118f56d6c33d83c41fac3b4d638ca4bef68e3366d6030134dc1258fc985da4"

MATRIX = json.dumps(
    [
        {"arch": "amd64", "tag_suffix": "amd64"},
        {"arch": "arm64", "tag_suffix": "arm64"},
    ]
)

TARGETS = (
    ArchTarget(arch="amd64", tag_suffix="amd64"),
    ArchTarget(arch="arm64", tag_suffix="arm64"),
)


def _index(*entries: dict[str, object]) -> str:
    return json.dumps(
        {
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": list(entries),
        }
    )


def _entry(
    digest: str,
    arch: str,
    *,
    os_name: str = "linux",
    variant: str | None = None,
) -> dict[str, object]:
    platform: dict[str, object] = {"architecture": arch, "os": os_name}
    if variant:
        platform["variant"] = variant
    return {"digest": digest, "platform": platform}


def _attestation(digest: str) -> dict[str, object]:
    return {"digest": digest, "platform": {"architecture": "unknown", "os": "unknown"}}


#: The multi-architecture index `:6d1f1df`, verbatim in structure.
REAL_INDEX = _index(
    _entry(AMD64_INNER, "amd64", variant="v2"),
    _attestation(AMD64_ATTEST),
    _entry(ARM64_INNER, "arm64"),
    _attestation(ARM64_ATTEST),
)

#: The per-architecture tags, each an index wrapping one manifest + attestation.
REAL_RAW = {
    INDEX_REF: REAL_INDEX,
    f"{INDEX_REF}-amd64": _index(
        _entry(AMD64_INNER, "amd64", variant="v2"), _attestation(AMD64_ATTEST)
    ),
    f"{INDEX_REF}-arm64": _index(
        _entry(ARM64_INNER, "arm64"), _attestation(ARM64_ATTEST)
    ),
}


def _inspector(
    raw: dict[str, str],
    *,
    image_config: dict[str, str] | None = None,
    manifest_digest: dict[str, str] | None = None,
) -> Inspector:
    """A fake registry.

    ``image_config`` / ``manifest_digest`` default to raising. That is the
    point: for an index-shaped tag the verifier must read THROUGH the index,
    and consulting `{{.Manifest.Digest}}` is exactly the pre-#703 defect. A
    regression to it fails here loudly instead of silently passing a fake.
    """

    def _missing(kind: str) -> Callable[[str], str]:
        def _raise(ref: str) -> str:
            msg = f"the verifier consulted {kind} for {ref}; it must not"
            raise AssertionError(msg)

        return _raise

    return Inspector(
        raw=lambda ref: raw[ref],
        image_config=(
            (lambda ref: image_config[ref])
            if image_config is not None
            else _missing("{{json .Image}}")
        ),
        manifest_digest=(
            (lambda ref: manifest_digest[ref])
            if manifest_digest is not None
            else _missing("{{.Manifest.Digest}}")
        ),
    )


def test_real_published_documents_pass() -> None:
    """The run that failed AC2 had published a perfectly correct index."""
    lines = verify_arch_tags(
        index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(REAL_RAW)
    )
    assert lines == [
        f"amd64: {AMD64_INNER} (tag shape: index)",
        f"arm64: {ARM64_INNER} (tag shape: index)",
    ]


def test_matrix_parses_to_the_published_targets() -> None:
    assert parse_matrix(MATRIX) == TARGETS


# ---------------------------------------------------------------------------
# Layer 2 — the defect itself, pinned so a revert fails here, not in CI.
# ---------------------------------------------------------------------------


def test_the_pre_703_reader_disagrees_with_the_index() -> None:
    """`{{.Manifest.Digest}}` on a per-architecture tag is the OUTER index.

    This is the whole defect in one assertion: on documents that are correct,
    the old comparison is false. Any change that reintroduces that reader has
    to make this test lie first.
    """
    index_entries = real_platform_entries(json.loads(REAL_INDEX))
    listed = next(
        e["digest"] for e in index_entries if e["platform"]["architecture"] == "amd64"
    )
    assert listed == AMD64_INNER
    assert listed != AMD64_OUTER


def test_attestations_never_count_as_coverage() -> None:
    """An index of one image + one attestation is ONE architecture, not two."""
    entries = real_platform_entries(json.loads(REAL_RAW[f"{INDEX_REF}-amd64"]))
    assert [e["digest"] for e in entries] == [AMD64_INNER]


# ---------------------------------------------------------------------------
# Layer 3 — the FAIL arms.
# ---------------------------------------------------------------------------


def test_fails_when_a_tag_resolves_to_the_wrong_architecture() -> None:
    """`:sha-arm64` actually serving amd64 — every `docker pull` still works."""
    raw = dict(REAL_RAW)
    raw[f"{INDEX_REF}-arm64"] = _index(
        _entry(ARM64_INNER, "amd64"), _attestation(ARM64_ATTEST)
    )
    with pytest.raises(ValueError, match=r"resolves to linux/amd64, not linux/arm64"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_tag_and_the_index_disagree() -> None:
    """The tag was never re-pointed after a rebuild — AC2's actual purpose."""
    stale = "sha256:" + "0" * 64
    raw = dict(REAL_RAW)
    raw[f"{INDEX_REF}-amd64"] = _index(
        _entry(stale, "amd64", variant="v2"), _attestation(AMD64_ATTEST)
    )
    with pytest.raises(ValueError, match=r"but the index's amd64 entry is"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_a_per_arch_tag_carries_two_real_platforms() -> None:
    """A per-architecture tag must name one image, or a pull is a coin flip."""
    raw = dict(REAL_RAW)
    raw[f"{INDEX_REF}-amd64"] = _index(
        _entry(AMD64_INNER, "amd64", variant="v2"), _entry(ARM64_INNER, "arm64")
    )
    with pytest.raises(ValueError, match=r"resolves to 2 real platforms"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_index_is_one_image_wearing_two_labels() -> None:
    """The silent failure every "did the pull succeed" check passes."""
    shared = _index(
        _entry(AMD64_INNER, "amd64"),
        _entry(AMD64_INNER, "arm64"),
    )
    raw = {
        INDEX_REF: shared,
        f"{INDEX_REF}-amd64": _index(_entry(AMD64_INNER, "amd64")),
        f"{INDEX_REF}-arm64": _index(_entry(AMD64_INNER, "arm64")),
    }
    with pytest.raises(ValueError, match=r"index entries share a digest"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_index_omits_a_published_architecture() -> None:
    """The matrix built it, so the index must list it."""
    raw = dict(REAL_RAW)
    raw[INDEX_REF] = _index(
        _entry(AMD64_INNER, "amd64", variant="v2"), _attestation(AMD64_ATTEST)
    )
    with pytest.raises(
        ValueError,
        match=r"no arm64 entry in .*\(expected linux/arm64; present: linux/amd64\)",
    ):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_index_duplicates_a_published_architecture() -> None:
    """Two amd64 descriptors make the merged index ambiguous for callers."""
    duplicate = "sha256:" + "1" * 64
    raw = dict(REAL_RAW)
    raw[INDEX_REF] = _index(
        _entry(AMD64_INNER, "amd64", variant="v2"),
        _entry(duplicate, "amd64"),
        _entry(ARM64_INNER, "arm64"),
    )
    with pytest.raises(ValueError, match=r"exactly one linux/amd64 entry"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_index_descriptor_has_the_wrong_os() -> None:
    """An architecture label is insufficient when the descriptor is Windows."""
    raw = dict(REAL_RAW)
    raw[INDEX_REF] = _index(
        _entry(AMD64_INNER, "amd64", os_name="windows"),
        _entry(ARM64_INNER, "arm64"),
    )
    with pytest.raises(ValueError, match=r"unexpected real platform.*windows/amd64"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


def test_fails_when_the_index_has_an_unexpected_linux_architecture() -> None:
    """The merged index must contain only the architectures the matrix built."""
    extra = "sha256:" + "2" * 64
    raw = dict(REAL_RAW)
    raw[INDEX_REF] = _index(
        _entry(AMD64_INNER, "amd64", variant="v2"),
        _entry(ARM64_INNER, "arm64"),
        _entry(extra, "riscv64"),
    )
    with pytest.raises(ValueError, match=r"unexpected real platform.*linux/riscv64"):
        verify_arch_tags(
            index_ref=INDEX_REF, targets=TARGETS, inspector=_inspector(raw)
        )


# ---------------------------------------------------------------------------
# Layer 4 — shape-agnosticism, and the wiring.
# ---------------------------------------------------------------------------


def test_a_bare_manifest_tag_passes_unchanged() -> None:
    """If buildx ever stops preferring an index, AC2 must not go red.

    The capability is identical — one real platform, matching the suffix, at
    the digest the index lists — so binding "it is an index" would have failed
    on an upstream default flip that broke nothing
    (`probes-need-a-control-arm.md` rule 9). The shape is reported, not
    asserted.
    """
    raw = dict(REAL_RAW)
    raw[f"{INDEX_REF}-amd64"] = json.dumps(
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": "sha256:" + "a" * 64},
            "layers": [],
        }
    )
    lines = verify_arch_tags(
        index_ref=INDEX_REF,
        targets=TARGETS,
        inspector=_inspector(
            raw,
            image_config={
                f"{INDEX_REF}-amd64": json.dumps(
                    {"architecture": "amd64", "os": "linux"}
                )
            },
            manifest_digest={f"{INDEX_REF}-amd64": AMD64_INNER},
        ),
    )
    assert lines[0] == f"amd64: {AMD64_INNER} (tag shape: manifest)"


def test_a_multi_platform_image_config_map_is_the_same_breach() -> None:
    """`{{json .Image}}` is a platform-keyed MAP for a multi-platform ref."""
    inspector = _inspector(
        {"ref": json.dumps({"mediaType": "x", "layers": []})},
        image_config={
            "ref": json.dumps(
                {"linux/amd64": {"architecture": "amd64"}, "linux/arm64": {}}
            )
        },
    )
    with pytest.raises(ValueError, match=r"resolves to 2 real platforms"):
        resolve_arch_tag("ref", inspector=inspector)


def test_cli_parses_and_routes_verify_arch_tags() -> None:
    """The subcommand exists and carries both arguments the step passes."""
    parser = setup_parser()
    args = parser.parse_args(
        ["image", "verify-arch-tags", "--image-ref", INDEX_REF, "--matrix", MATRIX]
    )
    assert args.image_command == "verify-arch-tags"
    assert args.image_ref == INDEX_REF
    assert parse_matrix(args.matrix) == TARGETS


def test_public_cli_executes_the_verifier(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Prove both CLI dispatch layers reach the registry verifier."""
    monkeypatch.setattr(
        "dotfiles_setup.image.docker_inspector", lambda: _inspector(REAL_RAW)
    )
    args = setup_parser().parse_args(
        ["image", "verify-arch-tags", "--image-ref", INDEX_REF, "--matrix", MATRIX]
    )

    with pytest.raises(SystemExit) as exit_info:
        handle_image(args)

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.splitlines() == [
        f"amd64: {AMD64_INNER} (tag shape: index)",
        f"arm64: {ARM64_INNER} (tag shape: index)",
    ]


def _ac2_run_block() -> str:
    """The EXECUTABLE lines of the AC2 step, shell comments stripped.

    Stripping comments is what stops this being satisfiable by prose: the step
    documents the old reader by name, so a plain substring search for
    `{{.Manifest.Digest}}` would match the explanation and the assertion below
    could never fail (`python/AGENTS.md` — 11 of 33 contract tokens were once
    met by a comment).
    """
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/build-publish.yml").read_text()
    )
    steps = workflow["jobs"]["manifest"]["steps"]
    step = next(s for s in steps if "(AC2)" in s.get("name", ""))
    return "\n".join(
        line for line in step["run"].splitlines() if not line.strip().startswith("#")
    )


def test_the_workflow_step_invokes_the_verifier() -> None:
    assert "dotfiles-setup image verify-arch-tags" in _ac2_run_block()


def test_the_workflow_step_no_longer_reads_the_outer_digest() -> None:
    """The pre-#703 reader must not come back through an executable line."""
    assert "{{.Manifest.Digest}}" not in _ac2_run_block()
