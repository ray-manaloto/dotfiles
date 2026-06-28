"""Tests for image smoke test script generation and size parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import json

from dotfiles_setup.image import (
    _parse_human_size,
    _repo_without_tag,
    _sum_manifest_layer_sizes,
    build_smoke_docker_cmd,
    build_smoke_script,
)

# Named constant for plain byte values in size parsing tests.
_PLAIN_BYTES_VALUE = 512

# Layer sizes (compressed bytes) used by the manifest-sum tests.
_LAYER_A_BYTES = 1000
_LAYER_B_BYTES = 2500
_LAYERS_TOTAL_BYTES = _LAYER_A_BYTES + _LAYER_B_BYTES


def test_smoke_script_pins_hk_file() -> None:
    """Verify the smoke script sets HK_FILE for hk validate."""
    script = build_smoke_script()

    assert "HK_FILE=/etc/hk/hk.pkl hk validate" in script


def test_smoke_docker_cmd_no_volume_mount() -> None:
    """Verify the docker command does not include volume mounts."""
    cmd = build_smoke_docker_cmd("ghcr.io/ray-manaloto/dotfiles-devcontainer:test")

    assert "--volume" not in cmd


def test_smoke_script_does_not_require_llvm_symbolizer() -> None:
    """Verify the smoke script does not check for llvm-symbolizer."""
    script = build_smoke_script()

    assert "llvm-symbolizer" not in script


def test_smoke_script_does_not_require_standalone_llvm_tools() -> None:
    """Verify the smoke script does not check for standalone LLVM tools."""
    script = build_smoke_script()

    assert "llvm-cov" not in script
    assert "llvm-profdata" not in script


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
