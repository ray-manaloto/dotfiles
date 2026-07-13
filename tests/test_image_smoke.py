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
    _TIER3_COMPILER_BODY,
    IDENTITY_IMAGE_PATHS,
    _count_tools_from_mise_ls,
    _format_bytes,
    _format_duration,
    _format_identity_lines,
    _is_emulated,
    _parse_build_timing,
    _parse_human_size,
    _repo_without_tag,
    _sum_manifest_layer_sizes,
    base_currency_blob,
    build_smoke_docker_cmd,
    build_smoke_script,
    build_tier1_script,
    build_tier3_script,
    diff_tool_sets,
    identity_expected_hash,
    installed_tools_from_mise_ls,
    metrics_summary,
    parse_declared_tools,
    render_metrics_summary,
    resolve_declared_tools,
    resolve_declared_tools_at_base,
    resolve_expected_identity_at_base,
    resolve_expected_identity_head,
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

# The in-image system mise config path (mise ls --json source.path).
_SYS_CFG = "/usr/local/share/mise/config.toml"

# Missing + extra + version-drift = three distinct diff-line classes.
_EXPECTED_DIFF_CLASSES = 3

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


def _mise_ls_json(entries: dict[str, dict[str, object]]) -> str:
    """Build a mise ls --json payload from the given entries.

    Each entry maps key -> {version, requested, source, installed}.
    """
    doc = {
        key: [
            {
                "version": e.get("version", "9.9.9"),
                "requested_version": e.get("requested", "latest"),
                "source": {"type": "mise.toml", "path": e.get("source", _SYS_CFG)},
                "installed": e.get("installed", True),
            }
        ]
        for key, e in entries.items()
    }
    return json.dumps(doc)


def test_parse_declared_tools_handles_both_value_forms() -> None:
    """Bare string and table ({version,...}) [tools] entries both parse."""
    declared = parse_declared_tools(_SAMPLE_MISE_TOML)

    assert declared == {
        "python": "latest",
        "conda:llvm": "latest",
        "npm:@google/gemini-cli": "latest",
        "pinned": "1.2.3",
    }


def test_installed_tools_filters_by_source_and_installed() -> None:
    """Only tools sourced from the system config AND installed are returned."""
    payload = _mise_ls_json(
        {
            "python": {"requested": "latest"},
            "user-tool": {"source": "/home/x/.config/mise/config.toml"},
            "half-installed": {"installed": False},
        }
    )

    installed = installed_tools_from_mise_ls(payload, (_SYS_CFG,))

    assert installed == {"python": "latest"}


def test_installed_tools_default_sources_cover_all_three_tiers() -> None:
    """The default source tuple must accept system, shared AND runtime configs.

    verify_tools_main relies on the default; a 2-tuple override made all 23
    runtime-tier tools diff as declared-but-not-installed in the devcontainer
    (PR #169).
    """
    payload = _mise_ls_json(
        {
            "python": {"source": _SYS_CFG},
            "hk": {"source": "/usr/local/share/mise/conf.d/shared.toml"},
            "github:cli/cli": {"source": "/usr/local/share/mise/config.runtime.toml"},
            "user-tool": {"source": "/home/x/.config/mise/config.toml"},
        }
    )

    installed = installed_tools_from_mise_ls(payload)

    assert set(installed) == {"python", "hk", "github:cli/cli"}


def test_diff_tool_sets_exact_match_is_empty() -> None:
    """Identical declared/installed maps produce no diff lines."""
    both = {"python": "latest", "conda:llvm": "latest"}

    assert diff_tool_sets(both, dict(both)) == []


def test_diff_tool_sets_reports_missing_extra_and_drift() -> None:
    """Missing, extra, and version-drift each surface a distinct diff line."""
    declared = {"python": "latest", "dropped": "latest", "pinned": "1.2.3"}
    installed = {"python": "latest", "added": "latest", "pinned": "9.9.9"}

    diffs = diff_tool_sets(declared, installed)

    assert any(line.startswith("+ added:") for line in diffs)
    assert any(line.startswith("- dropped:") for line in diffs)
    assert any(line.startswith("~ pinned:") for line in diffs)
    assert len(diffs) == _EXPECTED_DIFF_CLASSES


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
    assert "conda:llvm" in declared
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
    HEAD comparison false-fails verify-tools on the bumped tool (#178).
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
