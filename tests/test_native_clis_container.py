# Copyright (c) 2026 Raymond Manaloto
"""Tests for the devcontainer's native claude / codex / agy install + provenance.

The fixtures mirror the layouts the vendor installers were MEASURED to leave in a
throwaway container on 2026-10-01 (``docs/specs/native-cli-devcontainer-2026-10-01.md``
§5): claude and codex are symlinks from ``~/.local/bin`` into the vendor's own
tree, agy is a flat binary. Every check is armed both ways — the native layout
passes, and each realistic regression (a stale shadow on PATH, a binary that is
not the vendor's, a mise copy still active) fails.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import native_clis_container as ncc
from dotfiles_setup.main import main

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_BY_NAME = {t.name: t for t in ncc.TOOLS}


def _exe(path: Path, body: str = 'echo "1.0.0"') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _vendor_install(home: Path, name: str) -> None:
    """Lay ONE tool out exactly as its vendor installer does."""
    bin_dir = home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    if name == "claude":
        (bin_dir / "claude").symlink_to(
            _exe(home / ".local/share/claude/versions/2.1.287")
        )
    elif name == "codex":
        release = (
            home
            / ".codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl"
        )
        _exe(release / "bin/codex")
        (home / ".codex/packages/standalone/current").symlink_to(release)
        (bin_dir / "codex").symlink_to(
            home / ".codex/packages/standalone/current/bin/codex"
        )
    else:
        _exe(bin_dir / name)


def _native_layout(home: Path) -> None:
    """Lay the three tools out exactly as the vendor installers do."""
    for tool in ncc.TOOLS:
        _vendor_install(home, tool.name)


def _env(home: Path, *extra_path: Path) -> dict[str, str]:
    path = ":".join([str(home / ".local/bin"), *map(str, extra_path), "/usr/bin:/bin"])
    return {"HOME": str(home), "PATH": path}


def _mise_bin(tmp: Path, payload: Mapping[str, object]) -> Path:
    tool_dir = tmp / "mise-bin"
    _exe(tool_dir / "mise", f"cat <<'EOF'\n{json.dumps(payload)}\nEOF")
    return tool_dir


def test_native_layout_passes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _native_layout(home)
    env = _env(home, _mise_bin(tmp_path, {"node": [], "npm:@google/gemini-cli": []}))
    assert ncc.check(home=home, environ=env) == 0


def test_stale_shadow_ahead_of_native_fails(tmp_path: Path) -> None:
    """A copy earlier on PATH than ~/.local/bin is the defect provenance exists for."""
    home = tmp_path / "home"
    _native_layout(home)
    shadow = tmp_path / "shims"
    _exe(shadow / "codex")
    env = _env(home)
    env["PATH"] = f"{shadow}:{env['PATH']}"
    findings = ncc.check_one(_BY_NAME["codex"], home=home, environ=env)
    assert findings
    assert "expected the native" in findings[0]


def test_non_vendor_binary_at_native_path_fails(tmp_path: Path) -> None:
    """A plain file where the vendor installs a symlink into its own tree."""
    home = tmp_path / "home"
    _native_layout(home)
    (home / ".local/bin/claude").unlink()
    _exe(home / ".local/bin/claude")
    findings = ncc.check_one(_BY_NAME["claude"], home=home, environ=_env(home))
    assert findings
    assert "outside the vendor root" in findings[0]


def test_missing_tool_fails(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _native_layout(home)
    (home / ".local/bin/agy").unlink()
    findings = ncc.check_one(_BY_NAME["agy"], home=home, environ=_env(home))
    assert findings == [f"agy: not on PATH (expected {home}/.local/bin/agy)"]


def test_version_failure_fails(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _native_layout(home)
    (home / ".local/bin/agy").write_text("#!/bin/sh\nexit 3\n")
    findings = ncc.check_one(_BY_NAME["agy"], home=home, environ=_env(home))
    assert findings
    assert "rc=3" in findings[0]


def _entry(install_path: Path | str) -> list[dict[str, object]]:
    """One `mise ls --json` entry, in the real shape (install_path + version)."""
    return [{"version": "1.0.0", "install_path": str(install_path), "installed": True}]


@pytest.mark.parametrize(
    "key",
    [
        "npm:@openai/codex",
        "claude-code",
        "aqua:anthropics/claude-code",
        "aqua:google-antigravity/antigravity-cli",
    ],
)
def test_a_mise_copy_in_the_home_overlay_fails(tmp_path: Path, key: str) -> None:
    """A copy the USER's overlay installed (under $HOME) is this change's defect."""
    home = tmp_path / "home"
    _native_layout(home)
    payload = {key: _entry(home / ".local/share/mise/installs/x/1.0.0")}
    assert ncc.mise_findings(payload) == [
        f"mise: `{key}` is a mise tool here; the native installer owns it"
    ]
    env = _env(home, _mise_bin(tmp_path, {**payload, "node": []}))
    assert ncc.check(home=home, environ=env) == 1


def test_a_base_image_that_predates_the_change_is_a_loud_skip(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Today's `:dev` bakes mise claude-code + npm codex outside $HOME.

    The fixture mirrors that real image (measured 2026-10-01: install paths under
    /usr/local/share/mise/installs) AND a container created from it, which never
    ran `native-clis install` — so every native assertion would fail. Ship's
    sync-full smokes exactly that container, so this must not fail the gate;
    the CI no-mount smoke is what fails a baked copy in a NEW image.
    """
    home = tmp_path / "home"
    payload = {
        "claude-code": _entry("/usr/local/share/mise/installs/claude-code/2.1.283"),
        "npm:@openai/codex": _entry(
            "/usr/local/share/mise/installs/npm-openai-codex/0.154.0"
        ),
        "node": _entry("/usr/local/share/mise/installs/node/24"),
    }
    assert ncc.baked_into_base(payload, home) == ["claude-code", "npm:@openai/codex"]
    env = _env(home, _mise_bin(tmp_path, payload))
    with caplog.at_level("WARNING"):
        assert ncc.check(home=home, environ=env) == 0
    assert "SKIP: this base image predates native claude/codex/agy" in caplog.text


def test_a_base_without_copies_is_enforced_not_skipped(tmp_path: Path) -> None:
    """Control arm: a NEW base with the natives missing must still FAIL.

    The skip is scoped to an old base only.
    """
    home = tmp_path / "home"
    payload = {"node": _entry("/usr/local/share/mise/installs/node/24")}
    assert ncc.baked_into_base(payload, home) == []
    env = _env(home, _mise_bin(tmp_path, payload))
    assert ncc.check(home=home, environ=env) == 1


@pytest.mark.parametrize(
    "key", ["npm:claude-code-lint", "npm:oh-my-codex", "npm:@google/gemini-cli"]
)
def test_lookalike_mise_keys_pass(key: str) -> None:
    assert ncc.mise_findings({key: _entry("/x")}) == []


def test_unreadable_mise_is_a_finding_not_a_pass(tmp_path: Path) -> None:
    tool_dir = tmp_path / "mise-bin"
    _exe(tool_dir / "mise", "echo not-json")
    payload, findings = ncc.mise_tools(environ=_env(tmp_path, tool_dir))
    assert payload == {}
    assert findings
    assert "was not JSON" in findings[0]
    home = tmp_path / "home"
    _native_layout(home)
    assert ncc.check(home=home, environ=_env(home, tool_dir)) == 1


class _FakeInstall:
    """Stand-in runner: curl writes a script, the installer creates the binary."""

    def __init__(
        self, home: Path, tool: str, *, fetch_rc: int = 0, install_rc: int = 0
    ) -> None:
        self.home = home
        self.tool = tool
        self.fetch_rc = fetch_rc
        self.install_rc = install_rc
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def __call__(self, argv: Sequence[str], env: Mapping[str, str]) -> tuple[int, str]:
        self.calls.append((list(argv), dict(env)))
        if Path(argv[0]).name == "curl":
            Path(argv[argv.index("-o") + 1]).write_text("#!/bin/sh\n")
            return self.fetch_rc, ""
        if self.install_rc == 0:
            _vendor_install(self.home, self.tool)
        return self.install_rc, "installed"


def _curl_env(tmp_path: Path, home: Path) -> dict[str, str]:
    curl_dir = tmp_path / "curl-bin"
    _exe(curl_dir / "curl")
    env = _env(home, curl_dir)
    # A credential NAME the container really carries; the value is a canary
    # derived from the path so no literal looks like a password.
    env["DOPPLER_TOKEN"] = tmp_path.name
    env["MISE_SYSTEM_CONFIG_DIR"] = "/usr/local/share/mise"
    env["HTTPS_PROXY"] = "http://proxy.invalid:3128"
    # The REAL leak shape: Doppler injects MISE_GITHUB_TOKEN, and the MISE_*
    # passthrough must not carry it (cold review of 93d70c96, finding 1).
    env["MISE_GITHUB_TOKEN"] = tmp_path.name
    return env


def test_install_fetches_https_only_and_strips_credentials(tmp_path: Path) -> None:
    home = tmp_path / "home"
    run = _FakeInstall(home, "codex")
    tool = _BY_NAME["codex"]
    rc = ncc.install_one(tool, home=home, environ=_curl_env(tmp_path, home), run=run)
    assert rc == 0
    (fetch_argv, fetch_env), (install_argv, install_env) = run.calls
    assert fetch_argv[1:3] == ["--proto", "=https"]
    assert fetch_argv[-1] == "https://chatgpt.com/codex/install.sh"
    assert install_argv[0] == "sh"
    assert "DOPPLER_TOKEN" not in fetch_env
    assert "DOPPLER_TOKEN" not in install_env
    assert install_env["CODEX_NON_INTERACTIVE"] == "1"
    assert install_env["MISE_SYSTEM_CONFIG_DIR"] == "/usr/local/share/mise", (
        "the container's curl is a mise shim; it needs the MISE_* settings"
    )
    assert install_env["HTTPS_PROXY"] == "http://proxy.invalid:3128"
    assert "MISE_GITHUB_TOKEN" not in fetch_env
    assert "MISE_GITHUB_TOKEN" not in install_env


def test_existing_volume_chezmoi_wrapper_is_moved_aside_and_replaced(
    tmp_path: Path,
) -> None:
    """Every pre-change home volume holds the retired `mise exec claude-code` wrapper.

    It sits exactly at the native path, so a presence check would skip claude
    forever and the vendor installer would never run.
    """
    home = tmp_path / "home"
    wrapper = _exe(home / ".local/bin/claude", "exec mise exec claude-code -- claude")
    wrapper_text = wrapper.read_text()
    run = _FakeInstall(home, "claude")
    rc = ncc.install_one(
        _BY_NAME["claude"], home=home, environ=_curl_env(tmp_path, home), run=run
    )
    assert rc == 0
    assert len(run.calls) == 2, "the vendor installer must run"
    (aside,) = (home / ".local/bin").glob(".claude.pre-native-*")
    assert aside.read_text() == wrapper_text
    assert ncc.vendor_finding(_BY_NAME["claude"], home) is None


def test_flat_agy_symlinked_elsewhere_fails(tmp_path: Path) -> None:
    """A link at agy's path resolves its own root through itself — it must fail."""
    home = tmp_path / "home"
    _native_layout(home)
    (home / ".local/bin/agy").unlink()
    elsewhere = _exe(tmp_path / "mise/installs/antigravity-cli/1.2.14/agy")
    (home / ".local/bin/agy").symlink_to(elsewhere)
    findings = ncc.check_one(_BY_NAME["agy"], home=home, environ=_env(home))
    assert findings
    assert "not a link" in findings[0]


def test_present_tool_is_left_to_its_updater(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _native_layout(home)
    run = _FakeInstall(home, "claude")
    assert ncc.install(home=home, environ=_curl_env(tmp_path, home), run=run) == 0
    assert run.calls == []


def test_fetch_failure_is_loud(tmp_path: Path) -> None:
    home = tmp_path / "home"
    run = _FakeInstall(home, "agy", fetch_rc=56)
    rc = ncc.install_one(
        _BY_NAME["agy"], home=home, environ=_curl_env(tmp_path, home), run=run
    )
    assert rc == 56
    assert len(run.calls) == 1, "the installer must not run after a failed fetch"


def test_installer_failure_is_loud(tmp_path: Path) -> None:
    home = tmp_path / "home"
    run = _FakeInstall(home, "agy", install_rc=2)
    rc = ncc.install_one(
        _BY_NAME["agy"], home=home, environ=_curl_env(tmp_path, home), run=run
    )
    assert rc == 2


def test_installer_rc0_without_binary_fails(tmp_path: Path) -> None:
    home = tmp_path / "home"

    def run(argv: Sequence[str], env: Mapping[str, str]) -> tuple[int, str]:
        del env
        if Path(argv[0]).name == "curl":
            Path(argv[argv.index("-o") + 1]).write_text("")
        return 0, ""

    rc = ncc.install_one(
        _BY_NAME["claude"], home=home, environ=_curl_env(tmp_path, home), run=run
    )
    assert rc == 1


def test_cli_reaches_check(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(ncc, "main", lambda command: seen.append(command) or 0)
    monkeypatch.setattr(
        sys, "argv", ["dotfiles-setup", "devcontainer", "native-clis", "check"]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert seen == ["check"]


def test_version_probe_switches_updaters_off_and_drops_credentials(
    tmp_path: Path,
) -> None:
    """The probe-only switches reach `--version`; no credential does."""
    home = tmp_path / "home"
    _native_layout(home)
    env = _env(home)
    env["MISE_GITHUB_TOKEN"] = tmp_path.name
    env["DOPPLER_TOKEN"] = tmp_path.name
    seen: list[dict[str, str]] = []

    def run(argv: Sequence[str], probe_env: Mapping[str, str]) -> tuple[int, str]:
        del argv
        seen.append(dict(probe_env))
        return 0, "1.0.0"

    assert ncc.check_one(_BY_NAME["agy"], home=home, environ=env, run=run) == []
    (probe_env,) = seen
    assert probe_env["DISABLE_AUTOUPDATER"] == "1"
    assert probe_env["AGY_CLI_DISABLE_AUTO_UPDATE"] == "true"
    assert "MISE_GITHUB_TOKEN" not in probe_env
    assert "DOPPLER_TOKEN" not in probe_env


def test_a_second_move_aside_keeps_the_first_backup(tmp_path: Path) -> None:
    home = tmp_path / "home"
    first = home / ".local/bin/.claude.pre-native-20260101T000000Z"
    _exe(first, "echo first")
    _exe(home / ".local/bin/claude", "echo wrapper")
    run = _FakeInstall(home, "claude")
    rc = ncc.install_one(
        _BY_NAME["claude"], home=home, environ=_curl_env(tmp_path, home), run=run
    )
    assert rc == 0
    assert first.read_text() == "#!/bin/sh\necho first\n"
    assert len(list((home / ".local/bin").glob(".claude.pre-native-*"))) == 2


def test_on_create_installs_before_chezmoi_and_never_fails_on_create() -> None:
    """ORDER, which no require_tokens contract can see (round-2 cold review N1).

    The agy installer appends PATH lines to the chezmoi-managed rc files, so the
    install must precede `chezmoi init --apply --force`. And it must not fail
    onCreate: that would skip postCreate (R1 keys) and postStart (R2 chown).
    """
    root = Path(__file__).resolve().parent.parent
    script = (root / ".devcontainer/scripts/on-create.sh").read_text()
    install = script.index("devcontainer native-clis install")
    chezmoi = script.index("chezmoi init --apply")
    assert install < chezmoi
    install_line = script[install : script.index("\n", install)]
    assert install_line.rstrip().endswith("||"), "a failed install must not abort"


def test_path_spelled_differently_still_counts_as_native(tmp_path: Path) -> None:
    """A PATH entry naming ~/.local/bin through a symlink is still the native dir."""
    home = tmp_path / "home"
    _native_layout(home)
    alias = tmp_path / "alias-bin"
    alias.symlink_to(home / ".local/bin")
    env = {"HOME": str(home), "PATH": f"{alias}:/usr/bin:/bin"}
    assert ncc.check_one(_BY_NAME["claude"], home=home, environ=env) == []
