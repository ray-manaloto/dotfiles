"""repotools trust adds one Codex and one Claude Code trust entry for a real repository's main checkout."""

import json
import stat
import subprocess
import tomllib
from pathlib import Path

import pytest

from repotools.cli import main
from repotools.models import Trusted
from tests import clean_git_env


def git(*args: str | Path) -> None:
    subprocess.run(["git", *args], capture_output=True, check=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clean_git_env(monkeypatch)
    root = tmp_path / "repo"
    git("init", "-q", "-b", "main", root)
    git("-C", root, "-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "c")
    monkeypatch.chdir(root)
    return root.resolve()


@pytest.fixture
def homes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    codex, claude, state = tmp_path / "codex", tmp_path / "claude", tmp_path / "state"
    codex.mkdir()
    claude.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(codex))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    return codex / "config.toml", claude / ".claude.json", state


def lines(out: str) -> dict[str, Trusted]:
    found = [Trusted.model_validate_json(line) for line in out.splitlines()]
    return {entry.harness.value: entry for entry in found}


def test_adds_both_entries_to_existing_files_after_a_backup(
    repo: Path, homes: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    codex, claude, state = homes
    codex.write_text('model = "m"\n\n[projects."/elsewhere"]\ntrust_level = "trusted"\n')
    codex.chmod(0o600)
    claude.write_text(json.dumps({"numStartups": 3, "projects": {"/elsewhere": {"allowedTools": []}}}))
    claude.chmod(0o644)

    main(["trust"])

    out = lines(capsys.readouterr().out)
    assert {name: entry.action.value for name, entry in out.items()} == {"codex": "added", "claude": "added"}
    assert out["codex"].path == str(repo)
    assert out["codex"].file == str(codex)
    # The Codex file keeps what was there and gains one explicit table, as Codex itself writes it.
    text = codex.read_text()
    assert text.startswith('model = "m"\n\n[projects."/elsewhere"]\ntrust_level = "trusted"\n')
    assert f'[projects."{repo}"]\ntrust_level = "trusted"\n' in text
    assert tomllib.loads(text)["projects"][str(repo)] == {"trust_level": "trusted"}
    assert json.loads(claude.read_text()) == {
        "numStartups": 3,
        "projects": {"/elsewhere": {"allowedTools": []}, str(repo): {"hasTrustDialogAccepted": True}},
    }
    # Modes are kept: Codex's config stays private, Claude's stays as it was.
    assert stat.S_IMODE(codex.stat().st_mode) == 0o600
    assert stat.S_IMODE(claude.stat().st_mode) == 0o644
    # Each backup is the file as it was, under the state folder.
    for name, before in [
        ("codex", '"/elsewhere"]\ntrust_level = "trusted"\n'),
        ("claude", '"numStartups": 3'),
    ]:
        backup = Path(str(out[name].backup))
        assert backup.is_relative_to(state / "dotfiles" / "trust")
        assert before in backup.read_text()
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


@pytest.mark.usefixtures("repo")
def test_a_rerun_writes_nothing(homes: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    codex, claude, _ = homes
    main(["trust"])
    capsys.readouterr()
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (codex, claude)}

    main(["trust"])

    out = lines(capsys.readouterr().out)
    assert {name: (entry.action.value, entry.backup) for name, entry in out.items()} == {
        "codex": ("unchanged", None),
        "claude": ("unchanged", None),
    }
    assert {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (codex, claude)} == before


def test_missing_files_are_created_private_with_no_backup(
    repo: Path, homes: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    codex, claude, _ = homes

    main(["trust"])

    out = lines(capsys.readouterr().out)
    assert {name: (entry.action.value, entry.backup) for name, entry in out.items()} == {
        "codex": ("added", None),
        "claude": ("added", None),
    }
    assert codex.read_text() == f'[projects."{repo}"]\ntrust_level = "trusted"\n'
    assert (
        claude.read_text()
        == f'{{\n  "projects": {{\n    "{repo}": {{\n      "hasTrustDialogAccepted": true\n    }}\n  }}\n}}'
    )
    assert stat.S_IMODE(codex.stat().st_mode) == stat.S_IMODE(claude.stat().st_mode) == 0o600


def refused_in(folder: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> str:
    monkeypatch.chdir(folder)
    with pytest.raises(SystemExit):
        main(["trust"])
    captured = capsys.readouterr()
    assert captured.out == ""
    return json.loads(captured.err)["error"]


@pytest.mark.usefixtures("homes")
def test_a_worktree_trusts_its_main_checkout(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    git("-C", repo, "worktree", "add", "-q", "-b", "side", tmp_path / "side")
    monkeypatch.chdir(tmp_path / "side")

    main(["trust"])

    assert {entry.path for entry in lines(capsys.readouterr().out).values()} == {str(repo)}


def test_an_explicit_codex_no_is_left_alone_and_reported(
    repo: Path, homes: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    codex, claude, _ = homes
    text = f'[projects."{repo}"]\ntrust_level = "untrusted"\n'
    codex.write_text(text)

    with pytest.raises(SystemExit) as stopped:
        main(["trust"])

    assert stopped.value.code == 1
    captured = capsys.readouterr()
    assert {name: entry.action.value for name, entry in lines(captured.out).items()} == {
        "codex": "untrusted",
        "claude": "added",
    }
    assert json.loads(captured.err)["error"] == f"trust: Codex marks {repo} untrusted; left as it is"
    assert codex.read_text() == text
    assert json.loads(claude.read_text())["projects"][str(repo)] == {"hasTrustDialogAccepted": True}


def test_an_existing_codex_entry_keeps_its_other_keys(
    repo: Path, homes: tuple[Path, Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    codex, _, _ = homes
    codex.write_text(f'[projects."{repo}"]\nnote = "kept"\n')

    main(["trust"])

    assert lines(capsys.readouterr().out)["codex"].action.value == "added"
    assert tomllib.loads(codex.read_text())["projects"][str(repo)] == {"note": "kept", "trust_level": "trusted"}


@pytest.mark.usefixtures("repo", "homes")
def test_missing_config_folders_are_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "new" / "codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "new" / "claude"))

    main(["trust"])

    assert (tmp_path / "new" / "codex" / "config.toml").is_file()
    assert (tmp_path / "new" / "claude" / ".claude.json").is_file()


def test_a_symlinked_config_is_written_through_its_link(
    repo: Path, homes: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    codex, _, _ = homes
    target = tmp_path / "managed.toml"
    target.write_text("")
    codex.symlink_to(target)

    main(["trust"])

    assert codex.is_symlink()
    assert str(repo) in target.read_text()


@pytest.mark.usefixtures("homes")
def test_a_submodule_trusts_its_own_working_tree(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inner = tmp_path / "inner"
    git("init", "-q", "-b", "main", inner)
    git("-C", inner, "-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "c")
    git("-C", repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", inner, "sub")
    monkeypatch.chdir(repo / "sub")

    main(["trust"])

    assert {entry.path for entry in lines(capsys.readouterr().out).values()} == {str(repo / "sub")}


def test_a_bare_repository_is_refused(
    homes: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    codex, claude, _ = homes
    clean_git_env(monkeypatch)
    git("init", "-q", "--bare", tmp_path / "bare.git")
    monkeypatch.chdir(tmp_path / "bare.git")

    with pytest.raises(SystemExit):
        main(["trust"])

    assert "bare repository" in json.loads(capsys.readouterr().err)["error"]
    assert not codex.exists()
    assert not claude.exists()


def test_backups_of_two_files_with_one_name_both_survive(
    repo: Path, homes: tuple[Path, Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codex, claude, _ = homes
    for link, folder, text in [(codex, "a", 'model = "m"\n'), (claude, "b", '{"numStartups": 1}')]:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "same").write_text(text)
        link.symlink_to(tmp_path / folder / "same")

    main(["trust"])

    out = lines(capsys.readouterr().out)
    assert Path(str(out["codex"].backup)).read_text() == 'model = "m"\n'
    assert Path(str(out["claude"].backup)).read_text() == '{"numStartups": 1}'
    assert str(repo) in (tmp_path / "a" / "same").read_text()


def test_quotes_and_backslashes_stay_one_literal_key(
    homes: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex, claude, _ = homes
    clean_git_env(monkeypatch)
    root = tmp_path / "we\"ird\\na]me'x"
    git("init", "-q", "-b", "main", root)
    monkeypatch.chdir(root)
    key = str(root.resolve())
    codex.write_text('model = "m"\n\n[projects."/elsewhere"]\ntrust_level = "untrusted"\n')
    claude.write_text(json.dumps({"numStartups": 3, "projects": {"/elsewhere": {"allowedTools": ["x"]}}}))

    main(["trust"])

    assert tomllib.loads(codex.read_text()) == {
        "model": "m",
        "projects": {"/elsewhere": {"trust_level": "untrusted"}, key: {"trust_level": "trusted"}},
    }
    assert json.loads(claude.read_text()) == {
        "numStartups": 3,
        "projects": {"/elsewhere": {"allowedTools": ["x"]}, key: {"hasTrustDialogAccepted": True}},
    }


def separate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, store: str) -> Path:
    """A checkout made with --separate-git-dir <store>, and a linked worktree "side" beside it."""
    clean_git_env(monkeypatch)
    root = tmp_path / "checkout"
    (tmp_path / store).parent.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main", "--separate-git-dir", tmp_path / store, root)
    git("-C", root, "-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "c")
    git("-C", root, "worktree", "add", "-q", "-b", "side", tmp_path / "side")
    return root


@pytest.mark.usefixtures("homes")
def test_a_separate_git_dir_named_dot_git_trusts_the_key_codex_looks_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # From the worktree, Codex (trust.rs resolve_root) and Claude Code both take the folder above the common dir.
    root = separate(tmp_path, monkeypatch, "storage/project/.git")
    monkeypatch.chdir(root)
    main(["trust"])
    assert {entry.path for entry in lines(capsys.readouterr().out).values()} == {str(root.resolve())}

    monkeypatch.chdir(tmp_path / "side")
    main(["trust"])

    out = lines(capsys.readouterr().out)
    assert {entry.path for entry in out.values()} == {str((tmp_path / "storage" / "project").resolve())}
    assert {entry.action.value for entry in out.values()} == {"added"}


@pytest.mark.usefixtures("homes")
def test_a_worktree_whose_common_dir_has_no_main_root_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The common dir "store" is not a .git folder of its parent, so Codex resolves no trust root.
    separate(tmp_path, monkeypatch, "store")

    assert "no main checkout" in refused_in(tmp_path / "side", monkeypatch, capsys)
