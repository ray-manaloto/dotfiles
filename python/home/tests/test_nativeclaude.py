"""claude-doctor through the hometools CLI, against a scratch HOME."""

import json
from pathlib import Path

import pytest

from hometools.cli import main

PACKAGE = "lib/node_modules/@anthropic-ai/claude-code"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in ("MISE_DATA_DIR", "XDG_DATA_HOME", "MISE_INSTALLS_DIR", "MISE_INSTALL_STORE_DIR", "MISE_SHIMS_DIR"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def doctor(capfd: pytest.CaptureFixture[str]) -> tuple[int, str, list[str]]:
    try:
        main(["claude-doctor"])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, json.loads(err)["error"].splitlines() if err else []


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_a_native_only_home_passes(home: Path, capfd: pytest.CaptureFixture[str]) -> None:
    write(home / ".config/fish/conf.d/uv.env.fish", '\nsource "$HOME/.local/bin/env.fish"\n')  # uv's own line
    write(home / ".profile", 'export PATH="$HOME/.local/bin:$PATH"\n')
    (home / ".local/share/mise/installs/node-a/bin").mkdir(parents=True)
    assert doctor(capfd) == (0, "claude:doctor OK: only the native claude, no installer PATH lines\n", [])


def test_npm_copies_and_installer_lines_are_each_named(home: Path, capfd: pytest.CaptureFixture[str]) -> None:
    package = home / ".local/share/mise/installs/node-a" / PACKAGE
    package.mkdir(parents=True)
    command = home / ".local/share/mise/installs/node-a/bin/claude"
    command.parent.mkdir(parents=True)
    command.symlink_to("../lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe")  # dangling still counts
    shim = write(home / ".local/share/mise/shims/claude", "")
    zshrc = write(home / ".config/zsh/.zshrc", 'unset x\n\n. "$HOME/.local/share/../bin/env"\n')
    fish = write(home / ".config/fish/conf.d/uv.env.fish", 'source "$HOME/.local/share/../bin/env.fish"\n')
    code, out, errors = doctor(capfd)
    assert (code, out) == (1, "")
    fix = " with that node's npm)"
    assert errors == [
        *(f"{path}: Claude Code outside its native install; remove it (`npm uninstall -g @anthropic-ai/claude-code`"
          f"{fix}" for path in sorted([command, package, shim])),
        f"{zshrc}: an installer's PATH line (`.../../bin/env`); remove that line",
        f"{fish}: an installer's PATH line (`.../../bin/env`); remove that line",
    ]  # fmt: skip


def test_mise_data_dir_is_where_it_looks(
    home: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = home / "elsewhere"
    monkeypatch.setenv("MISE_DATA_DIR", str(data))
    (data / "installs/node-b" / PACKAGE).mkdir(parents=True)
    code, _, errors = doctor(capfd)
    assert code == 1
    assert errors[0].startswith(f"{data / 'installs/node-b' / PACKAGE}: ")


@pytest.mark.parametrize(
    ("variables", "where"),
    [
        ({"XDG_DATA_HOME": "data"}, "data/mise/installs/node-c"),
        ({"MISE_INSTALLS_DIR": "installs"}, "installs/node-c"),
        ({"MISE_INSTALL_STORE_DIR": "store"}, "store/node-c"),
    ],
)
def test_mise_folder_variables_are_followed(
    home: Path,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    variables: dict[str, str],
    where: str,
) -> None:
    for name, value in variables.items():
        monkeypatch.setenv(name, str(home / value))
    (home / where / PACKAGE).mkdir(parents=True)
    code, _, errors = doctor(capfd)
    assert code == 1
    assert errors[0].startswith(f"{home / where / PACKAGE}: ")


def test_a_shim_in_mise_shims_dir_is_found(
    home: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MISE_SHIMS_DIR", str(home / "shims"))
    shim = write(home / "shims/claude", "")
    assert doctor(capfd)[2][0].startswith(f"{shim}: ")
