"""The committed tools install and repair themselves through real git, mise and uv."""

import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from repotools.cli import main
from repotools.models import ToolInstalled, ToolReceipt

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.usefixtures("candidate", "tool_env")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout.strip()


def commit(subject: str) -> None:
    git("add", "-A")
    git("commit", "-qm", subject)


@pytest.fixture
def candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    listed = subprocess.run(
        ["git", "-C", REPO, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    root = tmp_path / "copy"
    for name in sorted(set(listed.split("\0")[:-1])):
        source = REPO / name
        if source.is_symlink() or source.exists():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, root / name, follow_symlinks=False)
    subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
    monkeypatch.chdir(root)
    git("config", "user.name", "Tools Tester")
    git("config", "user.email", "tools@example.com")
    commit("candidate")
    monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(root))
    monkeypatch.setenv("UV_OFFLINE", "1")
    return root


@pytest.fixture
def tool_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("UV_TOOL_DIR", str(tmp_path / "uv" / "tools"))
    monkeypatch.setenv("UV_TOOL_BIN_DIR", str(tmp_path / "uv" / "bin"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path


def snapshot(*roots: Path) -> dict[str, tuple[str, str, int, int]]:
    result = {}
    for root in roots:
        paths = [root]
        for directory, directories, files in os.walk(root, followlinks=False):
            paths.extend(Path(directory) / name for name in [*directories, *files])
        for path in paths:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                kind, content = "link", str(path.readlink())
            elif stat.S_ISREG(info.st_mode):
                kind, content = "file", hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                kind, content = "directory", ""
            result[str(path)] = (kind, content, info.st_mtime_ns, info.st_mode)
    return result


def events(stdout: str) -> list[ToolInstalled]:
    return [ToolInstalled.model_validate_json(line) for line in stdout.splitlines()]


def installed(capsys: pytest.CaptureFixture[str]) -> list[ToolInstalled]:
    main(["tools-install"])
    captured = capsys.readouterr()
    assert captured.err == ""
    result = events(captured.out)
    assert [event.tool for event in result] == ["workflowtools", "repotools"]
    return result


def repaired(capsys: pytest.CaptureFixture[str]) -> list[str]:
    """Run once more: workflowtools is reinstalled, repotools is not; return the JSON error events."""
    main(["tools-install"])
    captured = capsys.readouterr()
    assert [event.action for event in events(captured.out)] == ["installed", "unchanged"]
    return [json.loads(line)["error"] for line in captured.err.splitlines()]


def receipt(root: Path, name: str = "workflowtools") -> Path:
    return root / "state" / "dotfiles" / "tools" / f"{name}.json"


def record(root: Path) -> Path:
    tool = root / "uv" / "tools" / "workflowtools"
    return next(tool.glob("lib/python*/site-packages/workflowtools-*.dist-info/RECORD"))


def test_a_second_run_changes_nothing(tool_env: Path) -> None:
    first = subprocess.run(["mise", "run", "//repo:tools-install"], capture_output=True, check=True, text=True)
    assert [event.action for event in events(first.stdout)] == ["installed", "installed"]
    assert first.stderr.count('{"error"') == 0
    roots = (tool_env / "uv" / "tools", tool_env / "uv" / "bin", tool_env / "state")
    before = snapshot(*roots)
    second = subprocess.run(["mise", "run", "//repo:tools-install"], capture_output=True, check=True, text=True)
    assert [event.action for event in events(second.stdout)] == ["unchanged", "unchanged"]
    assert second.stderr.count('{"error"') == 0
    assert snapshot(*roots) == before


def test_both_tools_run_from_outside_the_checkout(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = installed(capsys)
    elsewhere = tool_env / "elsewhere"
    elsewhere.mkdir()
    git("init", "-q", str(elsewhere))
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    for event, command in zip(result, ("frontmatter", "zero-bash"), strict=True):
        assert Path(event.bin) == tool_env / "uv" / "bin" / event.tool
        done = subprocess.run([event.bin, command], cwd=elsewhere, env=env, capture_output=True, check=False, text=True)
        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_a_new_commit_in_one_package_reinstalls_only_that_tool(capsys: pytest.CaptureFixture[str]) -> None:
    first = installed(capsys)
    readme = Path("python/workflow/pyproject.toml")
    readme.write_text(readme.read_text() + "\n# A new committed source tree.\n")
    commit("workflow change")
    second = installed(capsys)
    assert [event.action for event in second] == ["installed", "unchanged"]
    assert second[0].tree != first[0].tree
    assert second[1].tree == first[1].tree


def test_uncommitted_changes_refuse_before_installing_anything(
    tool_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = Path("python/repo/pyproject.toml")
    source.write_text(source.read_text() + "\n# Dirty.\n")
    with pytest.raises(SystemExit) as error:
        main(["tools-install"])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"] == (
        "tools-install: python/repo has uncommitted changes; the installed copy must match a commit"
    )
    assert not (tool_env / "uv" / "tools").exists()


def test_a_missing_receipt_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    receipt(tool_env).unlink()
    assert repaired(capsys) == []
    assert ToolReceipt.model_validate_json(receipt(tool_env).read_text()).name == "workflowtools"


def test_a_corrupt_receipt_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    receipt(tool_env).write_text("{broken")
    assert repaired(capsys) == [
        "tools-install: workflowtools: its receipt is invalid: Invalid JSON: key must be a string at line 1 column 2"
    ]


def test_a_receipt_with_invalid_utf8_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    path = receipt(tool_env)
    path.write_bytes(path.read_bytes().replace(b"workflowtools", b"\xff"))
    [problem] = repaired(capsys)
    assert problem.startswith("tools-install: workflowtools: its receipt is invalid: ")
    assert ToolReceipt.model_validate_json(path.read_bytes()).name == "workflowtools"


def test_a_changed_record_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    path = record(tool_env)
    path.write_bytes(path.read_bytes() + b"\n")
    assert repaired(capsys) == ["tools-install: workflowtools: its RECORD changed since the receipt"]
    saved = ToolReceipt.model_validate_json(receipt(tool_env).read_text())
    assert saved.record_sha256 == hashlib.sha256(record(tool_env).read_bytes()).hexdigest()


def test_a_pruned_python_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    python = tool_env / "uv" / "tools" / "workflowtools" / "bin" / "python"
    python.unlink()
    python.symlink_to(tool_env / "pruned" / "python3")
    # With its interpreter gone the console script exits 126 (observed on macOS) rather than raising OSError.
    executable = tool_env / "uv" / "bin" / "workflowtools"
    assert repaired(capsys) == [f"tools-install: workflowtools: {executable} did not answer the start probe (exit 126)"]
    assert python.exists()


def test_a_missing_console_script_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    executable = tool_env / "uv" / "bin" / "workflowtools"
    executable.unlink()
    assert repaired(capsys) == [f"tools-install: workflowtools: {executable} is missing"]
    assert executable.is_file()


def test_a_missing_record_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    record(tool_env).unlink()
    assert repaired(capsys) == ["tools-install: workflowtools: its RECORD is missing"]
    assert record(tool_env).is_file()


def test_a_deleted_tool_with_its_receipt_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    shutil.rmtree(tool_env / "uv" / "tools" / "workflowtools")
    assert repaired(capsys) == ["tools-install: workflowtools: its RECORD is missing"]
    assert record(tool_env).is_file()


def test_two_record_files_reinstall_into_a_fresh_environment(
    tool_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installed(capsys)
    extra = record(tool_env).parent.with_name("workflowtools-9.9.dist-info")
    extra.mkdir()
    (extra / "RECORD").write_text("")
    assert repaired(capsys) == ["tools-install: workflowtools: it has two RECORD files"]
    assert not extra.exists()


def test_a_console_script_without_execute_permission_reinstalls(
    tool_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installed(capsys)
    executable = tool_env / "uv" / "bin" / "workflowtools"
    target = executable.resolve()
    content = target.read_bytes()
    target.unlink()
    target.write_bytes(content)
    target.chmod(0o644)
    [problem] = repaired(capsys)
    assert problem.startswith(f"tools-install: workflowtools: {executable} did not start: ")


def test_the_probe_writes_no_bytecode(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    installed(capsys)
    for name in ("workflowtools", "repotools"):
        package = next((tool_env / "uv" / "tools" / name).glob(f"lib/python*/site-packages/{name}"))
        assert not list(package.rglob("__pycache__"))


@pytest.mark.parametrize("xdg", [None, ""])
def test_xdg_state_home_unset_uses_local_state(
    tool_env: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], xdg: str | None
) -> None:
    for name, args in (("UV_CACHE_DIR", ["cache", "dir"]), ("UV_PYTHON_INSTALL_DIR", ["python", "dir"])):
        location = subprocess.run(["mise", "exec", "--", "uv", *args], capture_output=True, check=True, text=True)
        monkeypatch.setenv(name, location.stdout.strip())
    if xdg is None:
        monkeypatch.delenv("XDG_STATE_HOME")
    else:
        monkeypatch.setenv("XDG_STATE_HOME", xdg)
    monkeypatch.setenv("HOME", str(tool_env / "home"))
    installed(capsys)
    for name in ("workflowtools", "repotools"):
        path = tool_env / "home" / ".local" / "state" / "dotfiles" / "tools" / f"{name}.json"
        assert ToolReceipt.model_validate_json(path.read_text()).name == name


def test_uv_failing_is_a_failure(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    Path("python/workflow/pyproject.toml").write_text("invalid = [")
    commit("broken package")
    with pytest.raises(SystemExit) as error:
        main(["tools-install"])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"].startswith("uv failed:")
    assert not receipt(tool_env).exists()


@pytest.mark.parametrize("previously_installed", [False, True])
def test_an_install_that_does_not_start_writes_no_receipt(
    tool_env: Path, capsys: pytest.CaptureFixture[str], *, previously_installed: bool
) -> None:
    if previously_installed:
        installed(capsys)
    source = Path("python/workflow/src/workflowtools/cli.py")
    source.write_text("raise SystemExit(3)\n" + source.read_text())
    commit("broken entry point")
    with pytest.raises(SystemExit) as error:
        main(["tools-install"])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"].startswith("tools-install: uv installed workflowtools but ")
    assert not receipt(tool_env).exists()


@pytest.mark.parametrize(
    ("prefix", "problem"),
    [
        (
            "import sys\nsys.stderr.write('not json\\n')\nraise SystemExit(1)\n",
            "did not return the expected start refusal",
        ),
        (
            'import sys\nsys.stderr.write(\'{"error":"a different refusal"}\\n\')\nraise SystemExit(1)\n',
            "did not return the expected start refusal",
        ),
        ("print('unexpected stdout')\n", "did not answer the start probe (exit 1)"),
        (
            "import sys\nsys.stderr.buffer.write(b'\\xff\\n')\nraise SystemExit(1)\n",
            "did not return the expected start refusal",
        ),
        (
            "import sys\nsys.stdout.buffer.write(b'\\xff\\n')\nraise SystemExit(1)\n",
            "did not answer the start probe (exit 1)",
        ),
    ],
)
def test_an_unexpected_probe_answer_repairs_the_copy(
    tool_env: Path, capsys: pytest.CaptureFixture[str], prefix: str, problem: str
) -> None:
    installed(capsys)
    source = next((tool_env / "uv" / "tools" / "workflowtools").glob("lib/python*/site-packages/workflowtools/cli.py"))
    # Replace the installed file rather than writing through uv's possible hardlink into its cache.
    original = source.read_text()
    source.unlink()
    source.write_text(prefix + original)
    executable = tool_env / "uv" / "bin" / "workflowtools"
    assert repaired(capsys) == [f"tools-install: workflowtools: {executable} {problem}"]


def test_a_receipt_for_another_tool_reinstalls(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installed(capsys)
    receipt(tool_env).write_bytes(receipt(tool_env, "repotools").read_bytes())
    assert repaired(capsys) == ["tools-install: workflowtools: its receipt names repotools"]
    assert ToolReceipt.model_validate_json(receipt(tool_env).read_text()).name == "workflowtools"


def test_a_second_tool_failure_preserves_the_first_receipt(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = Path("python/repo/src/repotools/cli.py")
    source.write_text("raise SystemExit(3)\n" + source.read_text())
    commit("broken second entry point")
    with pytest.raises(SystemExit) as error:
        main(["tools-install"])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert [event.tool for event in events(captured.out)] == ["workflowtools"]
    assert json.loads(captured.err)["error"].startswith("tools-install: uv installed repotools but ")
    assert receipt(tool_env).is_file()
    assert not receipt(tool_env, "repotools").exists()


def test_tools_install_refuses_options(tool_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["tools-install", "--anything"])
    assert error.value.code == 1
    assert "unrecognized arguments: --anything" in json.loads(capsys.readouterr().err)["error"]
    assert not (tool_env / "uv" / "tools").exists()
