"""Tests for image smoke test script generation and size parsing."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import json

import pytest

from dotfiles_setup.image import (
    _is_emulated,
    _parse_human_size,
    _repo_without_tag,
    _sum_manifest_layer_sizes,
    build_smoke_docker_cmd,
    build_smoke_script,
    resolve_expected_config_sha256,
    resolve_expected_p2996_ref,
)

# Named constant for plain byte values in size parsing tests.
_PLAIN_BYTES_VALUE = 512

# A syntactically valid 40-hex git SHA + a non-SHA ref, for the
# clang-p2996 ref-pin check tests.
_FAKE_P2996_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
_NON_SHA_REF = "p2996-branch"

# A fake 64-hex SHA-256 for the image-identity (config-hash) tests.
_FAKE_CONFIG_SHA256 = "0" * 64

# Length of a hex-encoded SHA-256 digest.
_SHA256_HEXLEN = 64

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


def test_smoke_script_p2996_reflection_links_and_runs() -> None:
    """Gap C (#141): reflection is compiled AND the emitted binary is run."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # static_assert still forces enumerators_of(^^Color) to be evaluated at
    # compile time, so a broken reflection front-end fails the build...
    assert "static_assert(count_enumerators() == 3);" in script
    assert "enumerators_of(^^Color)" in script
    # ...and both reflection compilers now link (-o) + RUN their binary,
    # replacing the old -fsyntax-only-only smoke entirely.
    assert "-fsyntax-only" not in script
    assert "/opt/gcc-latest/bin/g++" in script
    assert "-o /tmp/refl-gcc" in script
    assert "/tmp/refl-gcc ||" in script
    assert "/opt/clang-p2996/bin/clang++" in script
    assert "-o /tmp/refl-clang" in script
    assert "/tmp/refl-clang ||" in script


def test_smoke_script_p2996_reflection_rpath_discovers_libcxx() -> None:
    """Gap C (#141): clang-p2996 links with an rpath at the discovered libc++."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # The libc++ dir is discovered at runtime (not hard-coded) so a triple
    # rename can't silently break the rpath, then baked into the binary.
    assert "find /opt/clang-p2996/lib -name 'libc++.so.1'" in script
    assert '-Wl,-rpath,"$P2996_LIBCXX_DIR"' in script


def test_smoke_script_p2996_reflection_runs_even_under_emulation() -> None:
    """Gap C (#141): the reflection RUN is not emulation-gated.

    Unlike TSan (gap B), a clang-p2996 -stdlib=libc++ binary runs fine under
    Rosetta/QEMU, so the RUN must fire even when ``emulated=True``.
    """
    script = build_smoke_script(_FAKE_P2996_SHA, emulated=True)

    assert "/tmp/refl-clang ||" in script
    assert "/tmp/refl-gcc ||" in script


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


def test_smoke_script_injects_config_identity_check() -> None:
    """Gap A: an injected config hash activates the image-identity guard."""
    script = build_smoke_script(
        _FAKE_P2996_SHA, expected_config_sha256=_FAKE_CONFIG_SHA256
    )

    assert f"EXPECTED_CONFIG_SHA256={_FAKE_CONFIG_SHA256}\n" in script
    # The guard compares the in-image config.toml hash against the repo's.
    assert 'sha256sum "$MISE_CFG"' in script
    assert '"$actual_config_sha256" != "$EXPECTED_CONFIG_SHA256"' in script


def test_smoke_script_identity_reads_system_config_not_config_dir() -> None:
    """#148: identity/policy checks hash the base SYSTEM config, not MISE_CONFIG_DIR.

    MISE_CONFIG_DIR is overridden at runtime (Dockerfile.host-user +
    devcontainer.json) to the user config dir, a chezmoi-rendered file that
    would false-fail identity on a current base. The check must read
    $MISE_SYSTEM_CONFIG_FILE (the Dockerfile COPY target).
    """
    script = build_smoke_script(_FAKE_P2996_SHA)

    assert (
        'MISE_CFG="${MISE_SYSTEM_CONFIG_FILE:-/usr/local/share/mise/config.toml}"'
        in script
    )
    assert "MISE_CONFIG_DIR:-/usr/local/share/mise}/config.toml" not in script


def test_smoke_script_config_identity_dormant_without_hash() -> None:
    """Without a hash the identity guard is present but dormant (empty var)."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # shlex.quote renders an empty string as ''.
    assert "EXPECTED_CONFIG_SHA256=''\n" in script
    assert 'if [ -n "$EXPECTED_CONFIG_SHA256" ]; then' in script


def test_smoke_script_tsan_runs_when_native() -> None:
    """Gap B: on a native host the TSan binary is both compiled and run."""
    script = build_smoke_script(_FAKE_P2996_SHA, emulated=False)

    assert "TSAN_RUN_SKIP=''\n" in script
    assert "clang++ -fsanitize=thread /tmp/sanitizer.cpp -o /tmp/san-tsan" in script
    assert "/tmp/san-tsan >/dev/null" in script


def test_smoke_script_tsan_run_skipped_when_emulated() -> None:
    """Gap B: under emulation TSan is still compiled but the RUN is guarded."""
    script = build_smoke_script(_FAKE_P2996_SHA, emulated=True)

    assert "TSAN_RUN_SKIP=1\n" in script
    # The compile still happens (proves the toolchain)...
    assert "clang++ -fsanitize=thread /tmp/sanitizer.cpp -o /tmp/san-tsan" in script
    # ...but the RUN is gated behind the skip flag.
    assert 'if [ -n "$TSAN_RUN_SKIP" ]; then' in script
    assert "ThreadSanitizer RUN skipped under emulation" in script


def test_is_emulated_arm_host_amd64_target() -> None:
    """An arm64 host running an amd64 image is emulated."""
    assert _is_emulated("linux/amd64/v2") is (os.uname().machine.lower() != "x86_64")


def test_is_emulated_matching_arch_is_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching host/target arch is not emulated."""
    fake_uname = os.uname_result(("Linux", "h", "r", "v", "x86_64"))
    monkeypatch.setattr(os, "uname", lambda: fake_uname)

    assert _is_emulated("linux/amd64/v2") is False


def test_is_emulated_mismatched_arch_is_emulated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An arm64 host with an amd64 target is emulated."""
    fake_uname = os.uname_result(("Linux", "h", "r", "v", "arm64"))
    monkeypatch.setattr(os, "uname", lambda: fake_uname)

    assert _is_emulated("linux/amd64/v2") is True


def test_resolve_expected_config_sha256_is_hex_digest() -> None:
    """The repo's mise-system.toml hashes to a 64-hex SHA-256 digest."""
    digest = resolve_expected_config_sha256()

    assert len(digest) == _SHA256_HEXLEN
    assert all(c in "0123456789abcdef" for c in digest)


def test_smoke_docker_cmd_injects_config_hash() -> None:
    """build_smoke_docker_cmd resolves and injects the real config hash."""
    cmd = build_smoke_docker_cmd(
        "ghcr.io/ray-manaloto/dotfiles-devcontainer:test",
        expected_p2996_ref=_FAKE_P2996_SHA,
    )
    script = cmd[-1]

    assert f"EXPECTED_CONFIG_SHA256={resolve_expected_config_sha256()}\n" in script


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
