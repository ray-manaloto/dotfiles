"""Tests for image smoke test script generation and size parsing."""

from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import json

import pytest
from dotfiles_setup.image import (
    _TIER1_IDENTITY_BLOCK,
    _TIER1_PYTHON_DEFAULT,
    _TIER3_COMPILER_BODY,
    _TIER3_DEFAULT_CLANG,
    IDENTITY_IMAGE_PATHS,
    AnalysisTarget,
    _count_tools_from_mise_ls,
    _format_bytes,
    _format_duration,
    _format_identity_lines,
    _is_emulated,
    _lookup_pr_number,
    _parse_apt_llvm_version,
    _parse_build_timing,
    _parse_human_size,
    _repo_without_tag,
    _sum_manifest_layer_sizes,
    base_currency_blob,
    build_smoke_docker_cmd,
    build_smoke_script,
    build_tier1_script,
    build_tier3_script,
    classify_layer_source,
    compare_payloads,
    decide_analysis_target,
    estimate_pull_time_s,
    identity_expected_hash,
    metrics_summary,
    parse_declared_tools,
    render_metrics_summary,
    resolve_analysis_ref_main,
    resolve_declared_tools,
    resolve_declared_tools_at_base,
    resolve_expected_identity_at_base,
    resolve_expected_identity_head,
    resolve_expected_llvm_version,
    resolve_expected_llvm_version_at_base,
    resolve_expected_p2996_ref,
    resolve_expected_p2996_ref_at_base,
    smoke_script_main,
)

# Named constant for plain byte values in size parsing tests.
_PLAIN_BYTES_VALUE = 512

# A syntactically valid 40-hex git SHA + a non-SHA ref, for the
# clang-p2996 ref-pin check tests.
_FAKE_P2996_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
_NON_SHA_REF = "p2996-branch"

# A fake apt LLVM release for the #294 default-clang + utility version guards.
_FAKE_LLVM_VERSION = "22.1.8"

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


def test_smoke_script_probes_standalone_llvm_tools() -> None:
    """#294: the standalone LLVM tools now ship (llvm-22 .deb) and are probed.

    Inverts the pre-#294 guardrail (commits 61e0ec3/82e9a22, "validate the
    shipped toolchain, not an imagined superset"): back then the conda-narrow
    image did NOT ship llvm-cov/profdata/symbolizer, so requiring them
    false-FAILed. Since #222/#251 adopted the full apt.llvm.org suite, all
    three ship in the declared ``llvm-22`` package, so the smoke asserts them —
    exactly the "update alongside actual toolchain changes" the guardrail
    sanctioned.
    """
    script = build_smoke_script(
        _FAKE_P2996_SHA, expected_llvm_version=_FAKE_LLVM_VERSION
    )

    for util in ("llvm-cov", "llvm-profdata", "llvm-symbolizer", "opt", "llc"):
        assert util in script


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
    assert "\n/tmp/refl-gcc ||" in script
    assert "/opt/clang-p2996/bin/clang++" in script
    assert "-o /tmp/refl-clang" in script
    assert "\n/tmp/refl-clang ||" in script


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

    assert "\n/tmp/refl-clang ||" in script
    assert "\n/tmp/refl-gcc ||" in script


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


# --- #294: apt LLVM version resolution + tier-3 functional probes ---


def test_parse_apt_llvm_version_strips_epoch_and_suffix() -> None:
    """The release is the MAJOR.MINOR.PATCH past the epoch, before the snapshot.

    Independent-literal expectation (not recomputed the parser's way): a real
    apt.llvm.org pin shape with epoch + `~++<snapshot>` suffix must yield the
    bare release.
    """
    cfg = (
        "[bootstrap.packages]\n"
        '"apt:clang-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~x"\n'
    )
    assert _parse_apt_llvm_version(cfg) == "22.1.8"


def test_parse_apt_llvm_version_rejects_missing_pin() -> None:
    """A missing apt:clang-22 pin fails loud, never a silent empty version."""
    with pytest.raises(TypeError):
        _parse_apt_llvm_version('[bootstrap.packages]\n"apt:curl" = "latest"\n')


def test_resolve_expected_llvm_version_is_release_triple() -> None:
    """HEAD resolver returns a real MAJOR.MINOR.PATCH from mise-system.toml."""
    ver = resolve_expected_llvm_version()
    parts = ver.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_resolve_expected_llvm_version_at_base_is_release_triple() -> None:
    """Merge-base resolver returns a real MAJOR.MINOR.PATCH (== HEAD on main)."""
    ver = resolve_expected_llvm_version_at_base()
    parts = ver.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_tier3_injects_llvm_version_and_guards_dormant_without_it() -> None:
    """The version var is injected; unset leaves the version guards SKIP-dormant."""
    with_ver = build_tier3_script(
        expected_p2996_ref=_FAKE_P2996_SHA,
        emulated=True,
        expected_llvm_version=_FAKE_LLVM_VERSION,
    )
    assert f"EXPECTED_LLVM_VERSION={_FAKE_LLVM_VERSION}\n" in with_ver

    without_ver = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=True)
    assert "EXPECTED_LLVM_VERSION=''\n" in without_ver
    assert "clang version guard dormant" in without_ver


def test_tier3_probes_openmp_lld_flang_libclc() -> None:
    """The functional probes (#294) are present and RUN, not just compile."""
    s = build_tier3_script(
        expected_p2996_ref=_FAKE_P2996_SHA,
        emulated=True,
        expected_llvm_version=_FAKE_LLVM_VERSION,
    )
    # openmp: compile + RUN (RUN fires even under emulation, like asan/ubsan).
    assert "clang++ -fopenmp /tmp/omp.cpp -o /tmp/omp" in s
    assert "\n/tmp/omp >/dev/null" in s
    # lld: exercised as a linker, not merely present.
    assert "clang++ -fuse-ld=lld /tmp/sanitizer.cpp -o /tmp/lld-linked" in s
    # flang: Fortran compile + RUN, with flang|flang-new fallback.
    assert "command -v flang 2>/dev/null || command -v flang-new" in s
    assert "\n/tmp/flang-hello >/dev/null" in s
    # libclc: bitcode presence across candidate roots (location-robust).
    assert "-name '*.bc'" in s
    # The `|| true` is load-bearing (regression: container smoke #294) — find
    # exits non-zero on a missing start dir, and under `set -e` a bare
    # `clc_bc=$(find ...)` would abort the script BEFORE the presence check,
    # dying silently instead of reporting. Guard that it never regresses.
    assert "-name '*.bc' 2>/dev/null | head -n1 || true" in s


def test_tier3_utility_version_smoke_covers_the_standalone_llvm_tools() -> None:
    """#294 (Ray): opt/llc/llvm-cov/profdata/symbolizer/bolt/mlir-opt all probed."""
    s = build_tier3_script(
        expected_p2996_ref=_FAKE_P2996_SHA,
        emulated=True,
        expected_llvm_version=_FAKE_LLVM_VERSION,
    )
    assert (
        "for util in opt llc llvm-cov llvm-profdata llvm-symbolizer "
        "llvm-bolt mlir-opt" in s
    )


def test_tier3_driver_presence_is_in_shared_body_not_ci_only() -> None:
    """#294: the 7-driver PATH loop moved into the SHARED tier-3 substrate.

    Regression guard: it used to live only in ``build_smoke_script``'s CI tail,
    so ``verify-container-latest`` (which runs ``build_tier3_script``) never saw
    it. It must now be in the shared body, and the old CI-only header must be
    gone (no duplication).
    """
    tier3 = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=True)
    assert "for tool in clang clang++ clangd clang-tidy clang-format lld lldb" in tier3
    # The pre-#294 CI-only section header is retired.
    ci = build_smoke_script(_FAKE_P2996_SHA)
    assert "=== clang tooling checks ===" not in ci


def test_build_smoke_docker_cmd_injects_real_llvm_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CI docker command injects the resolved release (not the dormant '')."""
    monkeypatch.delenv("CLANG_P2996_REF", raising=False)
    cmd = build_smoke_docker_cmd("ghcr.io/ray-manaloto/dotfiles-devcontainer:test")
    script = cmd[-1]
    assert "EXPECTED_LLVM_VERSION=''" not in script
    assert f"EXPECTED_LLVM_VERSION={resolve_expected_llvm_version()}" in script


def _run_default_clang_block(
    tmp_path: Path, clang_real: str, clang_ver_line: str, want_ver: str
) -> subprocess.CompletedProcess:
    """Run just the #294 default-clang gate against a stubbed clang++ via bash.

    Stubs ``clang++`` (its ``--version`` prints ``clang_ver_line``) and
    ``readlink`` (echoes ``clang_real``) on PATH, so the gate's resolution +
    version assertions run in both directions without a real toolchain. Mirrors
    ``_run_python_block``.
    """
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    clang = bin_dir / "clang++"
    clang.write_text(
        "#!/usr/bin/env bash\n"
        f'case "$*" in *--version*) echo {shlex.quote(clang_ver_line)} ;; esac\n'
    )
    clang.chmod(0o755)
    readlink = bin_dir / "readlink"
    readlink.write_text(f"#!/usr/bin/env bash\necho {shlex.quote(clang_real)}\n")
    readlink.chmod(0o755)
    harness = (
        "set -euo pipefail\n"
        f"PATH={shlex.quote(str(bin_dir))}:$PATH\n"
        f"EXPECTED_LLVM_VERSION={shlex.quote(want_ver)}\n" + _TIER3_DEFAULT_CLANG
    )
    return subprocess.run(
        ["bash", "-c", harness], capture_output=True, text=True, check=False
    )


def test_default_clang_block_passes_for_apt_llvm(tmp_path: Path) -> None:
    """Happy path: clang++ under /usr/lib/llvm-22, --version reports the release."""
    r = _run_default_clang_block(
        tmp_path,
        "/usr/lib/llvm-22/bin/clang",
        "Ubuntu clang version 22.1.8 (++2026...)",
        "22.1.8",
    )
    assert r.returncode == 0, r.stderr
    assert "OK: default clang++ is LLVM 22.1.8" in r.stdout


def test_default_clang_block_fails_on_wrong_version(tmp_path: Path) -> None:
    """FAIL arm: right location, wrong release — the version pin is enforced."""
    r = _run_default_clang_block(
        tmp_path,
        "/usr/lib/llvm-22/bin/clang",
        "Ubuntu clang version 21.1.0 (++2026...)",
        "22.1.8",
    )
    assert r.returncode == 1
    assert "not LLVM 22.1.8" in r.stdout


def test_default_clang_block_fails_on_non_apt_clang(tmp_path: Path) -> None:
    """FAIL arm: a p2996/conda clang taking bare clang++ is caught."""
    r = _run_default_clang_block(
        tmp_path,
        "/opt/clang-p2996/bin/clang",
        "clang version 22.1.8",
        "22.1.8",
    )
    assert r.returncode == 1
    assert "not apt /usr/lib/llvm-*" in r.stdout


def test_default_clang_block_dormant_when_version_unset(tmp_path: Path) -> None:
    """Unset version => the version guard SKIPs (path check still runs)."""
    r = _run_default_clang_block(
        tmp_path, "/usr/lib/llvm-22/bin/clang", "clang version 22.1.8", ""
    )
    assert r.returncode == 0
    assert "SKIP" in r.stdout


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


def test_smoke_script_injects_identity_lines() -> None:
    """#223: injected identity lines (repo_rel<TAB>img_rel<TAB>hash) all appear.

    The unified identity block replaces the two per-file scalar guards with one
    loop over $EXPECTED_IDENTITY covering all three verbatim-COPYd build inputs.
    """
    ident = dict.fromkeys(IDENTITY_IMAGE_PATHS, _FAKE_CONFIG_SHA256)
    script = build_smoke_script(_FAKE_P2996_SHA, expected_identity=ident)

    assert "EXPECTED_IDENTITY=" in script
    # Every build input's line is injected: repo_rel<TAB>img_rel<TAB>hash.
    for repo_rel, img_rel in IDENTITY_IMAGE_PATHS.items():
        assert f"{repo_rel}\t{img_rel}\t{_FAKE_CONFIG_SHA256}" in script
    # The loop hashes the resolved in-image file and fails on mismatch.
    assert 'sha256sum "$img_file"' in script
    assert '"$actual_identity_sha256" != "$want"' in script


def test_smoke_script_identity_sys_sentinel_reads_system_config() -> None:
    """#223/#148: the @SYS@ sentinel resolves to $MISE_CFG (the COPY target)."""
    ident = dict.fromkeys(IDENTITY_IMAGE_PATHS, _FAKE_CONFIG_SHA256)
    script = build_smoke_script(_FAKE_P2996_SHA, expected_identity=ident)

    assert ".devcontainer/mise-system.toml\t@SYS@\t" in script
    assert 'if [ "$img_rel" = "@SYS@" ]; then' in script
    assert 'img_file="$MISE_CFG"' in script


def test_format_identity_lines_rejects_unknown_build_input() -> None:
    """An unknown build-input key is a hard error, never a silent drop.

    A dropped identity line would be an invisible false-green, so the formatter
    refuses inputs outside IDENTITY_IMAGE_PATHS.
    """
    with pytest.raises(ValueError, match="unknown identity build-input"):
        _format_identity_lines({"not/a/real/input.toml": _FAKE_CONFIG_SHA256})


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
    """Without identity data the guard is present but dormant (empty var)."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    # shlex.quote renders an empty string as ''.
    assert "EXPECTED_IDENTITY=''\n" in script
    assert 'if [ -n "$EXPECTED_IDENTITY" ]; then' in script
    assert "SKIP: no expected identity injected" in script


def test_smoke_script_tsan_runs_when_native() -> None:
    """Gap B: on a native host the TSan binary is both compiled and run."""
    script = build_smoke_script(_FAKE_P2996_SHA, emulated=False)

    assert "TSAN_RUN_SKIP=''\n" in script
    assert "clang++ -fsanitize=thread /tmp/sanitizer.cpp -o /tmp/san-tsan" in script
    assert "  /tmp/san-tsan >/dev/null" in script


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


def test_resolve_expected_identity_head_are_hex_digests() -> None:
    """Each verbatim-COPYd build input hashes to a 64-hex SHA-256 (HEAD)."""
    head = resolve_expected_identity_head()

    assert set(head) == set(IDENTITY_IMAGE_PATHS)
    for digest in head.values():
        assert len(digest) == _SHA256_HEXLEN
        assert all(c in "0123456789abcdef" for c in digest)


def test_resolve_expected_identity_at_base_covers_all_inputs() -> None:
    """The merge-base resolver returns a hex digest per build input.

    The HEAD-vs-merge-base branching itself is covered by the
    identity_expected_hash tests; here we assert coverage + shape.
    """
    at_base = resolve_expected_identity_at_base()

    assert set(at_base) == set(IDENTITY_IMAGE_PATHS)
    for digest in at_base.values():
        assert len(digest) == _SHA256_HEXLEN


def test_smoke_docker_cmd_injects_real_identity() -> None:
    """build_smoke_docker_cmd resolves and injects the real HEAD identity.

    Guards against a no-op: the CI smoke's identity data must be ACTIVE (real
    hashes present), not the dormant empty var.
    """
    cmd = build_smoke_docker_cmd(
        "ghcr.io/ray-manaloto/dotfiles-devcontainer:test",
        expected_p2996_ref=_FAKE_P2996_SHA,
    )
    script = cmd[-1]

    head = resolve_expected_identity_head()
    assert "EXPECTED_IDENTITY=''" not in script
    for repo_rel, digest in head.items():
        assert f"{repo_rel}\t{IDENTITY_IMAGE_PATHS[repo_rel]}\t{digest}" in script


# --- #143: exact tool-set assertion ---

# A minimal mise-system.toml covering both [tools] value forms.
_SAMPLE_MISE_TOML = """\
[tools]
python = "latest"
"conda:llvm" = "latest"
"npm:@google/gemini-cli" = { version = "latest", depends = ["node"] }
pinned = "1.2.3"

[settings]
experimental = true
"""


def test_parse_declared_tools_handles_both_value_forms() -> None:
    """Bare string and table ({version,...}) [tools] entries both parse."""
    declared = parse_declared_tools(_SAMPLE_MISE_TOML)

    assert declared == {
        "python": "latest",
        "conda:llvm": "latest",
        "npm:@google/gemini-cli": "latest",
        "pinned": "1.2.3",
    }


def test_smoke_script_injects_tool_set_assertion() -> None:
    """#143: declared tools are injected and the jq/diff assertion block present."""
    script = build_smoke_script(
        _FAKE_P2996_SHA,
        expected_tools={"python": "latest", "conda:llvm": "latest"},
    )

    # Sorted key<TAB>version blob injected as data...
    assert "EXPECTED_TOOL_REQUESTS=" in script
    assert "conda:llvm\tlatest" in script
    assert "python\tlatest" in script
    # ...and the mechanical set-diff (no logic in bash).
    assert 'if [ -n "$EXPECTED_TOOL_REQUESTS" ]; then' in script
    assert "mise ls --json" in script
    assert "jq -r --arg cfg" in script
    assert (
        "select((.source.path == $cfg or .source.path == $shared\n"
        "              or .source.path == $runtime) and .installed == true)" in script
    )


def test_smoke_script_tool_set_guard_dormant_without_tools() -> None:
    """Without an expected set the guard is present but dormant (empty var)."""
    script = build_smoke_script(_FAKE_P2996_SHA)

    assert "EXPECTED_TOOL_REQUESTS=''\n" in script
    assert "tool-set guard dormant" in script


def test_smoke_docker_cmd_injects_real_declared_tools() -> None:
    """build_smoke_docker_cmd resolves and injects the repo's real [tools]."""
    cmd = build_smoke_docker_cmd(
        "ghcr.io/ray-manaloto/dotfiles-devcontainer:test",
        expected_p2996_ref=_FAKE_P2996_SHA,
    )
    script = cmd[-1]

    # A representative real tool from .devcontainer/mise-system.toml [tools]...
    assert "node\tlatest" in script
    # ...and from the merged shared conf.d fragment (#160 T5), exact-pinned.
    assert "python\t3.14.6" in script


def test_resolve_declared_tools_merges_system_and_shared() -> None:
    """The image's declared set merges mise-system.toml with the shared fragment.

    mise-system.toml [tools] MERGED with the shared conf.d fragment (#160 T5).
    """
    declared = resolve_declared_tools()

    # From the shared fragment, exact-pinned.
    assert declared["python"] == "3.14.6"
    assert declared["hk"] == "1.50.0"
    # From mise-system.toml [tools].
    assert declared["node"] == "latest"
    # A representative conda build tool still declared via mise (#222 PR-C moved
    # the LLVM-family conda tools — conda:llvm/clang/lld/lldb/... — to the apt
    # LLVM-22 packages in [bootstrap.packages], so they are no longer mise tools).
    assert "conda:cmake" in declared
    assert all(isinstance(v, str) for v in declared.values())


# ------------------------------------------ #223: shared tier-1 core (identity)


def test_build_tier1_script_is_core_without_ci_tail() -> None:
    """The tier-1 script has the shared core but NOT the CI-only tail.

    The devcontainer runs only tier-1 identity + tool-set via this script;
    sanitizers/reflection/AI-CLI/zero-warning stay in the CI no-mount smoke and
    (for the devcontainer) in tiers 2/3 of the bash script.
    """
    ident = dict.fromkeys(IDENTITY_IMAGE_PATHS, _FAKE_CONFIG_SHA256)
    script = build_tier1_script(
        expected_identity=ident, expected_tools={"python": "3.14.6"}
    )

    assert script.startswith("set -euo pipefail\n")
    # Core present.
    assert 'echo "=== image identity (build-input hashes) ==="' in script
    assert 'echo "=== exact tool-set assertion' in script
    # CI-only tail absent.
    assert "reflection compiler checks" not in script
    assert "sanitizer compile checks" not in script
    assert "hk validate" not in script
    assert "AI CLI checks" not in script


def test_build_tier1_script_shares_core_with_smoke_script() -> None:
    """#223: the CI smoke and the tier-1 script embed the SAME core verbatim.

    Byte-for-byte reuse is what makes the two paths unable to diverge.
    """
    ident = dict.fromkeys(IDENTITY_IMAGE_PATHS, _FAKE_CONFIG_SHA256)
    tools = {"python": "3.14.6", "node": "latest"}
    tier1 = build_tier1_script(expected_identity=ident, expected_tools=tools)
    smoke = build_smoke_script(
        _FAKE_P2996_SHA, expected_identity=ident, expected_tools=tools
    )

    # The identity block + the tool-set block are identical substrings in both.
    core_start = 'echo "=== image identity (build-input hashes) ==="'
    core_end_marker = 'echo "=== hk validate ==="'
    smoke_core = smoke[smoke.index(core_start) : smoke.index(core_end_marker)]
    tier1_core = tier1[tier1.index(core_start) :]
    assert smoke_core == tier1_core


def _run_identity_block(
    sysfile: Path, repo_rel: str, img_rel: str, want_hash: str
) -> subprocess.CompletedProcess:
    """Run just the tier-1 identity block against a real file via bash.

    ``img_rel`` is ``@SYS@`` (system config → $MISE_CFG) or a path relative to
    $MISE_DIR (shared/runtime tiers → the else branch).
    """
    blob = f"{repo_rel}\t{img_rel}\t{want_hash}"
    harness = (
        "set -euo pipefail\n"
        f"MISE_CFG={shlex.quote(str(sysfile))}\n"
        'MISE_DIR="$(dirname "$MISE_CFG")"\n'
        f"EXPECTED_IDENTITY={shlex.quote(blob)}\n" + _TIER1_IDENTITY_BLOCK
    )
    return subprocess.run(
        ["bash", "-c", harness], capture_output=True, text=True, check=False
    )


def test_tier1_identity_block_sys_branch_catches_mismatch(tmp_path: Path) -> None:
    """#223 no-op guard (@SYS@ branch): PASSES a correct hash, FAILS a wrong one.

    The asymmetric false-green risk is a check that silently stops running: this
    proves the generated bash actually hashes the system config and gates on the
    result, not that it merely contains the right substrings.
    """
    sysfile = tmp_path / "config.toml"
    sysfile.write_text("hello mise-system\n")
    good = hashlib.sha256(sysfile.read_bytes()).hexdigest()

    ok = _run_identity_block(sysfile, ".devcontainer/mise-system.toml", "@SYS@", good)
    bad = _run_identity_block(
        sysfile, ".devcontainer/mise-system.toml", "@SYS@", "0" * _SHA256_HEXLEN
    )

    assert ok.returncode == 0, ok.stderr
    assert "OK: image built from current" in ok.stdout
    assert bad.returncode == 1
    assert "stale image — rebuild" in bad.stdout


def test_tier1_identity_block_mise_dir_branch_catches_mismatch(tmp_path: Path) -> None:
    """#223 no-op guard (else branch): the $MISE_DIR/$img_rel resolution gates too.

    This is the NEW shared/runtime tier coverage (#223 extended CI identity from
    2 files to 3); the else branch resolves a non-@SYS@ img_rel relative to the
    mise dir. Proves it hashes the resolved file and fails on a wrong hash.
    """
    sysfile = tmp_path / "config.toml"
    sysfile.write_text("system\n")
    shared = tmp_path / "conf.d" / "shared.toml"
    shared.parent.mkdir()
    shared.write_text("hello shared\n")
    good = hashlib.sha256(shared.read_bytes()).hexdigest()
    rel = ".config/mise/conf.d/shared.toml"

    ok = _run_identity_block(sysfile, rel, "conf.d/shared.toml", good)
    bad = _run_identity_block(sysfile, rel, "conf.d/shared.toml", "0" * _SHA256_HEXLEN)

    assert ok.returncode == 0, ok.stderr
    assert f"OK: image built from current {rel}" in ok.stdout
    assert bad.returncode == 1
    assert "stale image — rebuild" in bad.stdout


def test_smoke_script_main_tier1_emits_identity_and_tools(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI emits a runnable tier-1 script with ACTIVE identity + tool-set."""
    rc = smoke_script_main(1)
    out = capsys.readouterr().out

    assert rc == 0
    assert out.startswith("set -euo pipefail\n")
    assert "EXPECTED_IDENTITY=''" not in out  # active, not dormant
    assert ".devcontainer/mise-system.toml\t@SYS@\t" in out
    assert 'echo "=== exact tool-set assertion' in out


def test_smoke_script_main_rejects_tier2_and_none() -> None:
    """Tiers 1 and 3 are python-generated; tier 2 and an unset tier are refused."""
    assert smoke_script_main(2) == 2
    assert smoke_script_main(None) == 2


# ------------------------------------------ #223: shared tier-3 compiler substrate


def test_build_tier3_script_is_substrate_without_tier1_or_ci_tail() -> None:
    """The tier-3 script has the shared compiler substrate but NOTHING else.

    No tier-1 core (identity/tool-set), no CI-only tail (hk validate, AI CLI,
    zero-warning), and none of the mount/SSH-dependent tier-3 checks (which stay
    bash-only in scripts/devcontainer-smoke.sh).
    """
    script = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=True)

    assert script.startswith("set -euo pipefail\n")
    # Substrate present.
    assert 'echo "=== sanitizer compile checks ==="' in script
    assert 'echo "=== reflection compiler checks ==="' in script
    assert "bloomberg/clang-p2996" in script
    # Tier-1 core absent.
    assert "image identity" not in script
    assert "exact tool-set assertion" not in script
    # CI-only tail absent.
    assert "hk validate" not in script
    assert "AI CLI checks" not in script
    assert "zero-warning" not in script
    # Mount/SSH-dependent tier-3 checks are NOT in the shared substrate.
    assert "home volume" not in script
    assert "ssh-add" not in script
    assert "TMPDIR" not in script


def test_build_tier3_script_shares_substrate_with_smoke_script() -> None:
    """#223: the CI smoke and the tier-3 script embed the SAME substrate verbatim.

    Byte-for-byte reuse (the same :data:`_TIER3_COMPILER_BODY` object) is what
    makes the sanitizer/reflection logic unable to diverge between the paths.
    """
    smoke = build_smoke_script(_FAKE_P2996_SHA)
    tier3 = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=False)

    assert _TIER3_COMPILER_BODY in smoke
    assert _TIER3_COMPILER_BODY in tier3


def test_build_tier3_script_tsan_run_gated_by_emulation() -> None:
    """The TSan RUN is skipped under emulation; the compile always fires."""
    native = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=False)
    emulated = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=True)

    # Compile is unconditional in both (proves the toolchain).
    for script in (native, emulated):
        assert "clang++ -fsanitize=thread /tmp/sanitizer.cpp -o /tmp/san-tsan" in script
    # RUN gate flips with emulation.
    assert "TSAN_RUN_SKIP=''\n" in native
    assert "TSAN_RUN_SKIP=1\n" in emulated


def test_build_tier3_script_injects_ref_and_strict_flag() -> None:
    """A 40-hex ref triggers strict equality; a non-SHA keeps the real-build guard."""
    strict = build_tier3_script(expected_p2996_ref=_FAKE_P2996_SHA, emulated=True)
    loose = build_tier3_script(expected_p2996_ref=_NON_SHA_REF, emulated=True)

    assert f"EXPECTED_P2996_REF={_FAKE_P2996_SHA}\n" in strict
    assert "P2996_REF_STRICT=1\n" in strict
    assert f"EXPECTED_P2996_REF={_NON_SHA_REF}\n" in loose
    assert "P2996_REF_STRICT=''\n" in loose


def test_smoke_script_main_tier3_emits_substrate_and_skips_tsan(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI emits a runnable tier-3 substrate with an ACTIVE ref, TSan skipped.

    The devcontainer always forces the TSan RUN skip (the amd64 container reports
    x86_64 under Rosetta so emulation is invisible from inside; CI's native
    runner covers the RUN).
    """
    rc = smoke_script_main(3)
    out = capsys.readouterr().out

    assert rc == 0
    assert out.startswith("set -euo pipefail\n")
    assert 'echo "=== sanitizer compile checks ==="' in out
    # Ref is active (a real 40-hex pin from docker-bake.hcl), not empty.
    assert "EXPECTED_P2996_REF=''" not in out
    assert "TSAN_RUN_SKIP=1\n" in out


def test_resolve_expected_p2996_ref_at_base_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CLANG_P2996_REF env override wins over the merge-base docker-bake pin."""
    monkeypatch.setenv("CLANG_P2996_REF", _FAKE_P2996_SHA)

    assert resolve_expected_p2996_ref_at_base() == _FAKE_P2996_SHA


def test_resolve_expected_p2996_ref_at_base_reads_merge_base_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no override, the (merge-base) docker-bake.hcl pin is a 40-hex SHA."""
    monkeypatch.delenv("CLANG_P2996_REF", raising=False)

    ref = resolve_expected_p2996_ref_at_base()

    assert len(ref) == 40
    assert all(c in "0123456789abcdef" for c in ref)


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


# --------------------------------------- tier-1 identity (merge-base aware)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )


def _identity_fixture_repo(tmp_path: Path) -> Path:
    """A repo where origin/main pins config.toml at its ORIGINAL content."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "config.toml").write_text("original\n")
    (repo / "other.toml").write_text("untouched\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def test_identity_expected_unchanged_file_uses_worktree(tmp_path: Path) -> None:
    repo = _identity_fixture_repo(tmp_path)
    expected = hashlib.sha256(b"untouched\n").hexdigest()
    assert identity_expected_hash(repo, "other.toml") == expected


def test_identity_expected_branch_change_uses_merge_base(tmp_path: Path) -> None:
    """A branch that changes an image input expects the MERGE-BASE blob.

    The local base can never be built from the branch's config (that base
    is built by the branch's own PR CI), so tier-1 identity must expect
    the integrated content — the exact ship-gate deadlock of the #178
    follow-up (jq CVE bump PR).
    """
    repo = _identity_fixture_repo(tmp_path)
    _git(repo, "checkout", "-b", "bump")
    (repo / "config.toml").write_text("bumped\n")
    _git(repo, "commit", "-am", "bump config")
    expected = hashlib.sha256(b"original\n").hexdigest()
    assert identity_expected_hash(repo, "config.toml") == expected


def test_identity_expected_on_main_equals_worktree(tmp_path: Path) -> None:
    """On main (merge-base == HEAD) the expectation is the committed file."""
    repo = _identity_fixture_repo(tmp_path)
    expected = hashlib.sha256(b"original\n").hexdigest()
    assert identity_expected_hash(repo, "config.toml") == expected


def test_identity_expected_falls_back_without_origin_main(tmp_path: Path) -> None:
    repo = tmp_path / "bare-checkout"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "config.toml").write_text("only-local\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "no origin")
    expected = hashlib.sha256(b"only-local\n").hexdigest()
    assert identity_expected_hash(repo, "config.toml") == expected


# --------------------------- tool-set base-currency (merge-base declared)


def _tool_config_fixture_repo(tmp_path: Path) -> Path:
    """A repo whose origin/main pins the three image tool-config tiers."""
    repo = tmp_path / "toolrepo"
    (repo / ".devcontainer").mkdir(parents=True)
    (repo / ".config" / "mise" / "conf.d").mkdir(parents=True)
    (repo / ".devcontainer" / "mise-system.toml").write_text(
        '[tools]\npython = "3.14.6"\n'
    )
    (repo / ".config" / "mise" / "conf.d" / "shared.toml").write_text(
        '[tools]\njq = "1.8.1"\n'
    )
    (repo / ".devcontainer" / "mise-runtime.toml").write_text(
        '[tools]\nfd = "10.4.2"\n'
    )
    _git(repo, "init", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base tool configs")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def test_resolve_declared_tools_at_base_uses_merge_base(tmp_path: Path) -> None:
    """A branch bump reports the MERGE-BASE version, not the branch HEAD.

    The exact deadlock this closes: the local base predates the bump, so a
    HEAD comparison would false-fail the tier-1 smoke tool-set assertion
    (``smoke_script_main`` / ``build_tier1_script``) on the bumped tool (#178).
    """
    repo = _tool_config_fixture_repo(tmp_path)
    _git(repo, "checkout", "-b", "bump")
    (repo / ".config" / "mise" / "conf.d" / "shared.toml").write_text(
        '[tools]\njq = "1.8.2"\n'
    )
    _git(repo, "commit", "-am", "bump jq")
    declared = resolve_declared_tools_at_base(repo)
    assert declared["jq"] == "1.8.1"  # merge-base, not the branch's 1.8.2
    assert declared["python"] == "3.14.6"
    assert declared["fd"] == "10.4.2"


def test_resolve_declared_tools_at_base_on_main_is_worktree(tmp_path: Path) -> None:
    repo = _tool_config_fixture_repo(tmp_path)
    declared = resolve_declared_tools_at_base(repo)
    assert declared["jq"] == "1.8.1"


def test_base_currency_blob_returns_bytes(tmp_path: Path) -> None:
    repo = _identity_fixture_repo(tmp_path)
    assert base_currency_blob(repo, "config.toml") == b"original\n"


# --- #17 build-metrics: tool-count, build-time, step-summary ---------------

# Expected tool-entry count for the mise-ls fixture below (jq: 1, python: 2).
_EXPECTED_TOOL_ENTRIES = 3

# Expected wall-clock seconds for the two-job jobs fixture (12:00:05 → 12:10:05).
_EXPECTED_WALL_SECONDS = 600.0

# One gibibyte, for the byte-format assertion.
_ONE_GIB = 1024**3


def test_count_tools_from_mise_ls_sums_version_entries() -> None:
    raw = json.dumps(
        {
            "jq": [{"version": "1.8.1", "installed": True}],
            "python": [
                {"version": "3.14.0", "installed": True},
                {"version": "3.13.0", "installed": True},
            ],
        }
    )
    assert _count_tools_from_mise_ls(raw) == _EXPECTED_TOOL_ENTRIES


def test_parse_build_timing_computes_wall_clock_and_per_job() -> None:
    jobs = json.dumps(
        {
            "jobs": [
                {
                    "name": "base-prep",
                    "conclusion": "success",
                    "started_at": "2026-07-13T12:00:05Z",
                    "completed_at": "2026-07-13T12:00:25Z",
                },
                {
                    "name": "build",
                    "conclusion": "success",
                    "started_at": "2026-07-13T12:00:30Z",
                    "completed_at": "2026-07-13T12:10:05Z",
                },
                {
                    "name": "still-running",
                    "conclusion": None,
                    "started_at": "2026-07-13T12:10:00Z",
                    "completed_at": None,
                },
            ]
        }
    )
    timing = _parse_build_timing(jobs)
    # Wall clock spans earliest start (12:00:05) to latest completion (12:10:05).
    assert timing["total_wall_s"] == _EXPECTED_WALL_SECONDS
    # The still-running job (null completed_at) is skipped.
    assert [job["name"] for job in timing["jobs"]] == ["base-prep", "build"]


def test_parse_build_timing_empty_is_zero() -> None:
    timing = _parse_build_timing(json.dumps({"jobs": []}))
    assert timing["total_wall_s"] == 0.0
    assert timing["jobs"] == []


def test_format_bytes_scales_units() -> None:
    assert _format_bytes(512) == "512 B"
    assert _format_bytes(_ONE_GIB) == "1.00 GB"


def test_format_duration_renders_hms() -> None:
    assert _format_duration(45) == "45s"
    assert _format_duration(605) == "10m 5s"
    assert _format_duration(3661) == "1h 1m 1s"


def test_render_metrics_summary_includes_all_sections() -> None:
    payload = {
        "image_ref": "ghcr.io/owner/repo:abc1234",
        "compressed_size_bytes": _ONE_GIB,
        "image_size_bytes": 2 * _ONE_GIB,
        "tool_count": 107,
        "result": "pass",
        "top_layers": [{"created_by": "RUN mise install", "size_bytes": _ONE_GIB}],
    }
    timing = {
        "total_wall_s": _EXPECTED_WALL_SECONDS,
        "jobs": [{"name": "build", "conclusion": "success", "duration_s": 300.0}],
    }
    markdown = render_metrics_summary(payload, timing)
    assert "Devcontainer image metrics" in markdown
    assert "ghcr.io/owner/repo:abc1234" in markdown
    assert "| Installed tools | 107 |" in markdown
    assert "| Smoke result | PASS |" in markdown
    assert "| CI build time (wall) | 10m 0s |" in markdown
    assert "### Largest layers" in markdown
    assert "### CI job timings" in markdown


def test_render_metrics_summary_without_timing_omits_ci_sections() -> None:
    payload = {
        "image_ref": "ghcr.io/owner/repo:abc1234",
        "compressed_size_bytes": _ONE_GIB,
        "image_size_bytes": _ONE_GIB,
        "result": "pass",
        "top_layers": [],
    }
    markdown = render_metrics_summary(payload, None)
    assert "CI build time" not in markdown
    assert "### CI job timings" not in markdown


def test_metrics_summary_appends_to_summary_path(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "image_ref": "ghcr.io/owner/repo:abc1234",
                "compressed_size_bytes": _ONE_GIB,
                "image_size_bytes": _ONE_GIB,
                "tool_count": 42,
                "result": "pass",
                "top_layers": [],
            }
        ),
        encoding="utf-8",
    )
    summary = tmp_path / "summary.md"
    summary.write_text("pre-existing\n", encoding="utf-8")
    returned = metrics_summary(metrics, summary_path=summary)
    written = summary.read_text(encoding="utf-8")
    # Appends (does not truncate) and returns the same markdown it wrote.
    assert written.startswith("pre-existing\n")
    assert "| Installed tools | 42 |" in written
    assert returned in written


# --------------------------------------- #231 scope-(b): layer attribution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("created_by", "expected"),
    [
        ("RUN /opt/clang-p2996/bin/clang++ ...", "clang-p2996"),
        ("RUN cmake --build p2996 ...", "clang-p2996"),
        ("COPY /opt/gcc-latest /opt/gcc-latest", "gcc-latest"),
        ("RUN cargo install --locked ripgrep", "cargo"),
        ("RUN mise install", "mise-tools"),
        ("RUN apt-get install -y build-essential", "apt"),
        ("RUN npm install -g @anthropic-ai/claude-code", "node/npm"),
        ("RUN echo hello > /etc/motd", "other"),
        ("", "other"),
    ],
)
def test_classify_layer_source_buckets(created_by: str, expected: str) -> None:
    assert classify_layer_source(created_by) == expected


def test_classify_layer_source_specific_before_generic() -> None:
    """A clang-p2996 build step that also runs via mise files as clang-p2996."""
    assert (
        classify_layer_source("RUN mise exec -- build /opt/clang-p2996")
        == "clang-p2996"
    )


# --------------------------------------- #231 scope-(b): modeled pull-time
# ---------------------------------------------------------------------------

# 25 MB at 200 Mbps (200*125_000 B/s) = 1.0s download; 500 MiB at 500 MiB/s
# = 1.0s decompress — chosen so the model yields round numbers.
_COMPRESSED_1S_BYTES = 25_000_000
_UNCOMPRESSED_1S_BYTES = 500 * 1024 * 1024
_EXPECTED_DOWNLOAD_S = 1.0
_EXPECTED_TOTAL_PULL_S = 2.0


def test_estimate_pull_time_splits_download_and_decompress() -> None:
    estimate = estimate_pull_time_s(_COMPRESSED_1S_BYTES, _UNCOMPRESSED_1S_BYTES)
    assert estimate["download_s"] == _EXPECTED_DOWNLOAD_S
    assert estimate["decompress_s"] == _EXPECTED_DOWNLOAD_S
    assert estimate["total_s"] == _EXPECTED_TOTAL_PULL_S
    # The model assumptions are echoed back so the number is interpretable.
    assert estimate["bandwidth_mbps"] > 0
    assert estimate["decompress_mb_s"] > 0


def test_estimate_pull_time_guards_against_zero_bandwidth() -> None:
    """A hostile zero override falls back to the default, never divides by 0."""
    estimate = estimate_pull_time_s(
        _COMPRESSED_1S_BYTES, _UNCOMPRESSED_1S_BYTES, bandwidth_mbps=0
    )
    assert estimate["total_s"] > 0


# --------------------------------------- #231 scope-(b): trend comparison
# ---------------------------------------------------------------------------

_BASE_GIB = 1024**3


def _bench_payload(*, compressed: int, uncompressed: int, pull_total: float) -> dict:
    return {
        "image_size_bytes": uncompressed,
        "compressed_size_bytes": compressed,
        "pull_time_estimate": {"total_s": pull_total},
        "timings_s": {"smoke_wall": 1.0, "total_wall": 2.0},
    }


def test_compare_payloads_reports_signed_deltas() -> None:
    baseline = _bench_payload(
        compressed=_BASE_GIB, uncompressed=_BASE_GIB, pull_total=10.0
    )
    candidate = _bench_payload(
        compressed=_BASE_GIB - 100, uncompressed=_BASE_GIB, pull_total=8.5
    )
    deltas = compare_payloads(baseline, candidate)
    assert deltas["compressed_size_delta"] == -100
    assert deltas["pull_time_total_delta"] == -1.5


def test_compare_payloads_tolerates_pre_schema3_baseline() -> None:
    """A baseline written before #231 (no pull_time_estimate) is treated as 0."""
    baseline = {
        "image_size_bytes": _BASE_GIB,
        "compressed_size_bytes": _BASE_GIB,
        "timings_s": {"smoke_wall": 1.0, "total_wall": 2.0},
    }
    candidate = _bench_payload(
        compressed=_BASE_GIB, uncompressed=_BASE_GIB, pull_total=5.0
    )
    deltas = compare_payloads(baseline, candidate)
    assert deltas["pull_time_total_delta"] == 5.0


def test_render_metrics_summary_shows_pull_time_and_source() -> None:
    payload = {
        "image_ref": "ghcr.io/owner/repo:pr-231",
        "compressed_size_bytes": _ONE_GIB,
        "image_size_bytes": 2 * _ONE_GIB,
        "pull_time_estimate": {"total_s": 90.0, "bandwidth_mbps": 200.0},
        "result": "pass",
        "top_layers": [
            {
                "created_by": "RUN cargo install x",
                "source": "cargo",
                "size_bytes": _ONE_GIB,
            }
        ],
    }
    markdown = render_metrics_summary(payload, None)
    assert "Modeled pull time" in markdown
    assert "| Size | Source | Created by |" in markdown
    assert "| cargo |" in markdown


def test_render_metrics_summary_renders_trend_when_comparison_given() -> None:
    payload = {
        "image_ref": "ghcr.io/owner/repo:pr-231",
        "compressed_size_bytes": _ONE_GIB,
        "image_size_bytes": _ONE_GIB,
        "result": "pass",
        "top_layers": [],
    }
    comparison = {
        "compressed_size_delta": -_ONE_GIB,
        "image_size_delta": _ONE_GIB,
        "pull_time_total_delta": -3.2,
    }
    markdown = render_metrics_summary(payload, None, comparison)
    assert "### Trend vs baseline" in markdown
    assert "-1.00 GB" in markdown
    assert "+1.00 GB" in markdown
    assert "-3.20s" in markdown


def test_render_metrics_summary_omits_trend_without_comparison() -> None:
    payload = {
        "image_ref": "ghcr.io/owner/repo:pr-231",
        "compressed_size_bytes": _ONE_GIB,
        "image_size_bytes": _ONE_GIB,
        "result": "pass",
        "top_layers": [],
    }
    assert "### Trend vs baseline" not in render_metrics_summary(payload, None)


def test_metrics_summary_renders_trend_against_baseline_file(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            _bench_payload(
                compressed=2 * _ONE_GIB, uncompressed=2 * _ONE_GIB, pull_total=12.0
            )
        ),
        encoding="utf-8",
    )
    metrics = tmp_path / "metrics.json"
    payload = _bench_payload(compressed=_ONE_GIB, uncompressed=_ONE_GIB, pull_total=6.0)
    payload["image_ref"] = "ghcr.io/owner/repo:pr-231"
    payload["result"] = "pass"
    payload["top_layers"] = []
    metrics.write_text(json.dumps(payload), encoding="utf-8")
    markdown = metrics_summary(metrics, baseline_path=baseline)
    assert "### Trend vs baseline" in markdown
    # candidate 6.0s - baseline 12.0s = -6.00s modeled pull-time.
    assert "-6.00s" in markdown


def test_metrics_summary_missing_baseline_omits_trend(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    payload = _bench_payload(compressed=_ONE_GIB, uncompressed=_ONE_GIB, pull_total=6.0)
    payload["image_ref"] = "ghcr.io/owner/repo:pr-231"
    payload["result"] = "pass"
    payload["top_layers"] = []
    metrics.write_text(json.dumps(payload), encoding="utf-8")
    markdown = metrics_summary(metrics, baseline_path=tmp_path / "nope.json")
    assert "### Trend vs baseline" not in markdown


# --------------------------------------- #231 scope-(a): analysis-ref resolver
# ---------------------------------------------------------------------------

_IMAGE_BASE = "ghcr.io/ray-manaloto/dotfiles-devcontainer"
_PR_HEAD_SHA = "24a68c8c901595858c78261ad547f724cdd0a8b3"
_MAIN_SHA = "058f337abc0000000000000000000000000000ff"
_PR_NUMBER = 237


def test_decide_analysis_target_pr_present_analyzes_pr_tag() -> None:
    target = decide_analysis_target(
        event="pull_request",
        head_sha=_PR_HEAD_SHA,
        pr_number=_PR_NUMBER,
        image_base=_IMAGE_BASE,
        tag_exists=lambda ref: ref == f"{_IMAGE_BASE}:pr-{_PR_NUMBER}",
    )
    assert target.present is True
    assert target.fail is False
    assert target.ref == f"{_IMAGE_BASE}:pr-{_PR_NUMBER}"


def test_decide_analysis_target_pr_absent_quiet_skips() -> None:
    """PR resolved but :pr-NNN absent = docs/path-gated PR -> quiet green skip."""
    target = decide_analysis_target(
        event="pull_request",
        head_sha=_PR_HEAD_SHA,
        pr_number=238,
        image_base=_IMAGE_BASE,
        tag_exists=lambda _ref: False,
    )
    assert target.present is False
    assert target.fail is False
    assert target.ref is None


def test_decide_analysis_target_pr_unresolved_fails_loud() -> None:
    """The #231 signature: a pull_request run with no resolvable PR -> FAIL."""
    target = decide_analysis_target(
        event="pull_request",
        head_sha=_PR_HEAD_SHA,
        pr_number=None,
        image_base=_IMAGE_BASE,
        tag_exists=lambda _ref: False,
    )
    assert target.fail is True
    assert target.present is False
    assert target.ref is None


def test_decide_analysis_target_schedule_uses_bare_sha() -> None:
    target = decide_analysis_target(
        event="schedule",
        head_sha=_MAIN_SHA,
        pr_number=None,
        image_base=_IMAGE_BASE,
        tag_exists=lambda ref: ref == f"{_IMAGE_BASE}:{_MAIN_SHA[:7]}",
    )
    assert target.present is True
    assert target.fail is False
    assert target.ref == f"{_IMAGE_BASE}:{_MAIN_SHA[:7]}"


def test_decide_analysis_target_schedule_absent_quiet_skips() -> None:
    target = decide_analysis_target(
        event="workflow_dispatch",
        head_sha=_MAIN_SHA,
        pr_number=None,
        image_base=_IMAGE_BASE,
        tag_exists=lambda _ref: False,
    )
    assert target.present is False
    assert target.fail is False


def test_lookup_pr_number_parses_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "dotfiles_setup.image._run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout="237\n", stderr=""),
    )
    assert _lookup_pr_number("owner/repo", _PR_HEAD_SHA) == _PR_NUMBER


def test_lookup_pr_number_empty_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """The empty pull_requests[] trap: jq on an empty array prints 'null'."""
    monkeypatch.setattr(
        "dotfiles_setup.image._run",
        lambda *_a, **_k: subprocess.CompletedProcess(
            [], 0, stdout="null\n", stderr=""
        ),
    )
    assert _lookup_pr_number("owner/repo", _PR_HEAD_SHA) is None


def test_resolve_analysis_ref_main_emits_outputs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "dotfiles_setup.image.resolve_analysis_target",
        lambda **_k: AnalysisTarget(
            ref=f"{_IMAGE_BASE}:pr-237", present=True, fail=False, reason="ok"
        ),
    )
    rc = resolve_analysis_ref_main(
        event="pull_request",
        head_sha=_PR_HEAD_SHA,
        repo="owner/repo",
        image_base=_IMAGE_BASE,
    )
    out = capsys.readouterr()
    assert rc == 0
    assert "present=true" in out.out
    assert f"ref={_IMAGE_BASE}:pr-237" in out.out


def test_resolve_analysis_ref_main_fail_exits_nonzero_no_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "dotfiles_setup.image.resolve_analysis_target",
        lambda **_k: AnalysisTarget(
            ref=None, present=False, fail=True, reason="FAIL: no PR"
        ),
    )
    rc = resolve_analysis_ref_main(
        event="pull_request",
        head_sha=_PR_HEAD_SHA,
        repo="owner/repo",
        image_base=_IMAGE_BASE,
    )
    out = capsys.readouterr()
    assert rc == 1
    # No GITHUB_OUTPUT lines on failure (stdout is redirected to $GITHUB_OUTPUT).
    assert out.out == ""
    assert "FAIL" in out.err


def _run_python_block(
    mise_dir: Path, py_exe: str, py_ver: str, want_ver: str
) -> subprocess.CompletedProcess:
    """Run just the tier-1 python block against a fake `python3` via bash.

    A stub `python3` on PATH reports `py_exe`/`py_ver`, so the block's two
    assertions (resolution under $MISE_DIR/installs/python, exact version) can
    be driven in both directions without a real interpreter.
    """
    bin_dir = mise_dir / "stub-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "python3"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'case "$*" in *sys.executable*) echo {shlex.quote(py_exe)} ;; '
        f"*python_version*) echo {shlex.quote(py_ver)} ;; esac\n"
    )
    stub.chmod(0o755)
    harness = (
        "set -euo pipefail\n"
        f"MISE_DIR={shlex.quote(str(mise_dir))}\n"
        f"PATH={shlex.quote(str(bin_dir))}:$PATH\n"
        f"EXPECTED_PYTHON_VERSION={shlex.quote(want_ver)}\n" + _TIER1_PYTHON_DEFAULT
    )
    return subprocess.run(
        ["bash", "-c", harness], capture_output=True, text=True, check=False
    )


def test_tier1_python_block_passes_for_mise_python(tmp_path: Path) -> None:
    """The happy path: python3 under mise's installs at the declared version."""
    exe = f"{tmp_path}/installs/python/3.14.6/bin/python3"
    r = _run_python_block(tmp_path, exe, "3.14.6", "3.14.6")
    assert r.returncode == 0, r.stderr
    assert "OK: default python3 is mise's 3.14.6" in r.stdout


def test_tier1_python_block_fails_on_distro_python(tmp_path: Path) -> None:
    """FAIL arm: the distro python taking the PATH is caught.

    This is the regression the block exists for — the image ships Ubuntu's
    /usr/bin/python3 as a hard Depends: of clang-format-22/lldb-22, so a shim
    or PATH break silently hands `python3` to a DIFFERENT interpreter. Without
    this arm the block would be a probe that can only pass.
    """
    r = _run_python_block(tmp_path, "/usr/bin/python3", "3.14.4", "3.14.6")
    assert r.returncode == 1
    assert "not a mise install" in r.stdout


def test_tier1_python_block_fails_on_version_drift(tmp_path: Path) -> None:
    """FAIL arm: right location, wrong version — the pin is enforced too."""
    exe = f"{tmp_path}/installs/python/3.14.4/bin/python3"
    r = _run_python_block(tmp_path, exe, "3.14.4", "3.14.6")
    assert r.returncode == 1
    assert "declared 3.14.6" in r.stdout


def test_tier1_python_block_dormant_when_unset(tmp_path: Path) -> None:
    """An unpopulated call is a no-op SKIP, never a false green."""
    r = _run_python_block(tmp_path, "/usr/bin/python3", "3.14.4", "")
    assert r.returncode == 0
    assert "SKIP" in r.stdout


def test_build_tier1_script_injects_python_version() -> None:
    """`build_tier1_script` threads the declared version into the script."""
    s = build_tier1_script(expected_python="3.14.6")
    assert "EXPECTED_PYTHON_VERSION=3.14.6" in s
    assert "not a mise install under" in s


def test_build_tier1_script_python_guard_dormant_without_data() -> None:
    """No python version => the guard is emitted but inert."""
    s = build_tier1_script()
    assert "EXPECTED_PYTHON_VERSION=''" in s
