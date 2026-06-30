"""Tests for image smoke test script generation and size parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import json

import pytest

from dotfiles_setup.image import (
    _parse_human_size,
    _repo_without_tag,
    _sum_manifest_layer_sizes,
    build_smoke_docker_cmd,
    build_smoke_script,
    resolve_expected_p2996_ref,
)

# Named constant for plain byte values in size parsing tests.
_PLAIN_BYTES_VALUE = 512

# A syntactically valid 40-hex git SHA + a non-SHA ref, for the
# clang-p2996 ref-pin check tests.
_FAKE_P2996_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
_NON_SHA_REF = "p2996-branch"

# Layer sizes (compressed bytes) used by the manifest-sum tests.
_LAYER_A_BYTES = 1000
_LAYER_B_BYTES = 2500
_LAYERS_TOTAL_BYTES = _LAYER_A_BYTES + _LAYER_B_BYTES


def test_smoke_script_pins_hk_file() -> None:
    """Verify the smoke script sets HK_FILE for hk validate."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    assert "HK_FILE=/etc/hk/hk.pkl hk validate" in script


def test_smoke_docker_cmd_no_volume_mount() -> None:
    """Verify the docker command does not include volume mounts."""
    cmd = build_smoke_docker_cmd(
        "ghcr.io/ray-manaloto/dotfiles-devcontainer:test",
        expected_p2996_ref=_FAKE_P2996_SHA,
    )

    assert "--volume" not in cmd


def test_smoke_script_does_not_require_llvm_symbolizer() -> None:
    """Verify the smoke script does not check for llvm-symbolizer."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    assert "llvm-symbolizer" not in script


def test_smoke_script_does_not_require_standalone_llvm_tools() -> None:
    """Verify the smoke script does not check for standalone LLVM tools."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    assert "llvm-cov" not in script
    assert "llvm-profdata" not in script


def test_smoke_script_injects_p2996_ref_and_strict_match() -> None:
    """A 40-hex ref is injected and triggers the strict equality check."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # shlex.quote leaves shell-safe hex/digit values unquoted.
    assert f"EXPECTED_P2996_REF={_FAKE_P2996_SHA}\n" in script
    assert "P2996_REF_STRICT=1\n" in script
    # The strict comparison + the "not a p2996 build" guard must be present.
    assert 'ACTUAL_P2996_REF" != "$EXPECTED_P2996_REF' in script
    assert "bloomberg/clang-p2996" in script


def test_smoke_script_p2996_reflection_is_evaluated_at_compile_time() -> None:
    """The reflection check forces compile-time evaluation via static_assert."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # static_assert forces enumerators_of(^^Color) to be evaluated, so a
    # broken reflection front-end fails the -fsyntax-only compile.
    assert "static_assert(count_enumerators() == 3);" in script
    assert "enumerators_of(^^Color)" in script
    # Both reflection compilers are exercised.
    assert "/opt/gcc-latest/bin/g++" in script
    assert "/opt/clang-p2996/bin/clang++" in script


def test_smoke_script_non_sha_ref_skips_strict_match() -> None:
    """A non-SHA dispatch override keeps the real-build guard but not strict."""
    script = build_smoke_script(_NON_SHA_REF)

    # 'p2996-branch' is shell-safe so shlex leaves it unquoted; the empty
    # strict flag IS quoted by shlex as ''.
    assert f"EXPECTED_P2996_REF={_NON_SHA_REF}\n" in script
    assert "P2996_REF_STRICT=''\n" in script
    # Still asserts it is a genuine p2996 build even without a SHA to match.
    assert "bloomberg/clang-p2996" in script


def test_resolve_expected_p2996_ref_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLANG_P2996_REF env override wins over the docker-bake.hcl pin."""
    monkeypatch.setenv("CLANG_P2996_REF", _FAKE_P2996_SHA)

    assert resolve_expected_p2996_ref() == _FAKE_P2996_SHA


def test_resolve_expected_p2996_ref_reads_bake_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no override, the committed docker-bake.hcl pin is used."""
    monkeypatch.delenv("CLANG_P2996_REF", raising=False)

    ref = resolve_expected_p2996_ref()

    # The pin is a 40-hex git SHA.
    assert len(ref) == 40
    assert all(c in "0123456789abcdef" for c in ref)


def test_parse_human_size_handles_gigabytes_before_bytes_suffix() -> None:
    """Verify GB suffix is parsed correctly."""
    assert _parse_human_size("12.3GB") == int(12.3 * 1024**3)


def test_parse_human_size_handles_lowercase_kilobytes() -> None:
    """Verify kB suffix is parsed correctly."""
    assert _parse_human_size("1.17kB") == int(1.17 * 1024)


def test_parse_human_size_handles_plain_bytes() -> None:
    """Verify plain byte strings without suffix are parsed correctly."""
    assert _parse_human_size("512") == _PLAIN_BYTES_VALUE


def test_repo_without_tag_strips_tag() -> None:
    """A :tag suffix is removed, leaving the bare repo."""
    assert (
        _repo_without_tag("ghcr.io/ray-manaloto/dotfiles-devcontainer:abc1234")
        == "ghcr.io/ray-manaloto/dotfiles-devcontainer"
    )


def test_repo_without_tag_preserves_registry_port() -> None:
    """A registry :port (colon before the last slash) is not mistaken for a tag."""
    assert _repo_without_tag("localhost:5000/img") == "localhost:5000/img"


def test_repo_without_tag_strips_digest() -> None:
    """An @digest suffix is removed."""
    assert (
        _repo_without_tag("ghcr.io/owner/repo@sha256:deadbeef") == "ghcr.io/owner/repo"
    )


def test_sum_manifest_layer_sizes_single_manifest() -> None:
    """Compressed size is the sum of a single manifest's layer sizes."""
    raw = json.dumps(
        {
            "layers": [
                {
                    "size": _LAYER_A_BYTES,
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                },
                {
                    "size": _LAYER_B_BYTES,
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                },
            ]
        }
    )
    assert (
        _sum_manifest_layer_sizes(raw, "ghcr.io/owner/repo:tag") == _LAYERS_TOTAL_BYTES
    )
