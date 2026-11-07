"""repotools zero-bash through its command line, in real git repositories."""

import json
import os
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from repotools.cli import main
from tests import run_python

REPO = Path(__file__).resolve().parents[3]
LONG_RUN = "[tasks.a]\nrun = '''\necho one\necho two\n'''\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # A pre-commit hook exports these, and they would point git at the real checkout.
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def add(root: Path, files: dict[str, str | bytes]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text if isinstance(text, bytes) else text.encode())
    subprocess.run(["git", "-C", root, "add", "-f", "."], check=True)


def report(capsys: pytest.CaptureFixture[str], *args: str) -> list[dict[str, str]]:
    main(["zero-bash", *args])
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_a_shell_script_is_reported_for_suffix_and_shebang(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"tasks/a.sh": "#!/usr/bin/env bash\necho hi\n"})
    assert report(capsys) == [
        {"path": "tasks/a.sh", "rule": "shell-file", "detail": ".sh"},
        {"path": "tasks/a.sh", "rule": "shell-shebang", "detail": "#!/usr/bin/env bash"},
    ]


SHELL_LINES = [
    "#!/bin/sh",
    "#!/bin/bash -e",
    "#! /usr/bin/env -S zsh",
    "#!/usr/bin/env bash -x",
    "#!/usr/bin/env -S /bin/bash -e",
    "#!/usr/bin/env -S/bin/bash",
    "#!/usr/bin/env -i PATH=/bin -u HOME sh",
    "#!/bin/ash",
    "#!/bin/csh -f",
    "#!/usr/bin/env fish",
    "#!/bin/busybox sh",
    '#!/usr/bin/env -S "/bin/sh" -c "exit 0"',
    '#!/usr/bin/env -S LABEL="two words" /bin/sh',
    "#!/usr/bin/env -S /bin/sh\\_-c\\_true",
    "#!/usr/bin/env -S '/bin/sh' -c \"echo it's\"",
]


@pytest.mark.parametrize("line", SHELL_LINES)
def test_shell_shebangs_without_a_suffix_are_reported(
    repo: Path, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    add(repo, {"bin/tool": f"{line}\n"})
    assert report(capsys) == [{"path": "bin/tool", "rule": "shell-shebang", "detail": line}]


def test_other_interpreters_and_binary_files_pass(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            "a": "#!/usr/bin/env python3\n",
            "b": "#!/bin/shiny\n",
            "c": b"\x00\xff\n",
            "d.py": "x = '#!/bin/sh'\n",
            "e": "#!/usr/bin/env -S python3 -I\n",
            "f": "#!/usr/bin/env\n",
            "g": "#!\n",
            "h": "#!/usr/bin/env -u\n",
            "j": "#!/usr/bin/env -S 'python3\\_x'\n",  # \_ stays inside single quotes
        },
    )
    assert report(capsys) == []


def test_zsh_startup_files_are_allowed_only_where_listed(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            "unix/home/.zshenv": "#!/bin/zsh\n",
            "unix/home/.zshrc": "#!/bin/zsh\n",
            "unix/home/.zshrc.d/10-a.zsh": "#!/bin/zsh\n",
            "unix/home/.config/zsh/path.zsh": "#!/bin/zsh\n",
            "tasks/x.zsh": "print hi\n",
        },
    )
    assert report(capsys) == [{"path": "tasks/x.zsh", "rule": "shell-file", "detail": ".zsh"}]


def test_a_multi_line_run_is_reported_with_its_toml_key(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            "mise.toml": LONG_RUN,
            "unix/home/.config/mise/config.toml": '[bootstrap.hooks.post]\nrun = ["true", "a\\nb"]\n',
            "steps.toml": "[[tasks.b.steps]]\n" + "run = 'a\nb'\n".replace("'", "'''"),
        },
    )
    assert report(capsys) == [
        {"path": "mise.toml", "rule": "multi-line-run", "detail": "tasks.a.run"},
        {"path": "steps.toml", "rule": "multi-line-run", "detail": "tasks.b.steps[0].run"},
        {"path": "unix/home/.config/mise/config.toml", "rule": "multi-line-run", "detail": "bootstrap.hooks.post.run"},
    ]


def test_one_line_runs_pass_even_with_a_final_newline(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {"mise.toml": '[tasks.a]\nrun = "echo hi"\n[tasks.b]\nrun = ["a", "b"]\n[tasks.c]\nrun = """\necho hi\n"""\n'},
    )
    assert report(capsys) == []


CONTINUED = '"""\ntool --one \\ \n  --two\n"""'


def test_a_run_joined_by_line_ending_backslashes_is_reported(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            "a.toml": f"[tasks.a]\nrun = {CONTINUED}\n",
            "b.toml": f'[tasks.b]\nrun = ["true", {CONTINUED}]\n',
            "c.toml": f'[tasks.c]\n"run" = {CONTINUED}\n',
            "d.toml": f"tasks.d.run = {CONTINUED}\n",
        },
    )
    assert report(capsys) == [
        {"path": f"{name}.toml", "rule": "multi-line-run", "detail": f"tasks.{name}.run"} for name in "abcd"
    ]


def test_backslashes_that_join_no_lines_pass(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    escaped = '[tasks.a]\nrun = """\na \\\\\n"""\n'  # an escaped backslash, then the closing newline
    literal = "[tasks.b]\nrun = '''a \\'''\n"  # no escapes in a literal string
    example = f"[tasks.c]\ndescription = '''run = {CONTINUED}'''\nrun = \"true\"\n"  # not a run value
    add(repo, {"mise.toml": escaped + literal + example})
    assert report(capsys) == []


def test_the_index_is_checked_not_the_working_tree(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"gone.sh": "#!/bin/sh\n", "tool": "#!/usr/bin/env python3\n"})
    (repo / "gone.sh").unlink()
    (repo / "tool").write_text("#!/bin/sh\n")
    assert report(capsys) == [
        {"path": "gone.sh", "rule": "shell-file", "detail": ".sh"},
        {"path": "gone.sh", "rule": "shell-shebang", "detail": "#!/bin/sh"},
    ]


def test_links_and_submodules_are_checked_by_name_only(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "dangling.sh").symlink_to("nowhere")
    (repo / "run.toml").symlink_to("#!/bin/sh")
    add(repo, {})  # before the gitlink: `git add .` would drop it, with no folder behind it
    gitlink = "160000," + "0" * 39 + "1,vendor.sh"  # a submodule entry; git never reads its commit here
    subprocess.run(["git", "update-index", "--add", "--cacheinfo", gitlink], check=True)
    assert report(capsys) == [
        {"path": "dangling.sh", "rule": "shell-file", "detail": ".sh"},
        {"path": "vendor.sh", "rule": "shell-file", "detail": ".sh"},
    ]


def test_untracked_files_are_ignored(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "scratch.sh").write_text("#!/bin/sh\n")
    assert report(capsys) == []


def test_strict_exits_1_after_printing_the_leftovers(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"a.sh": "\n"})
    with pytest.raises(SystemExit) as stopped:
        main(["zero-bash", "--strict"])
    assert stopped.value.code == 1
    assert json.loads(capsys.readouterr().out)["path"] == "a.sh"


def test_strict_passes_a_clean_repository(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"a.py": "\n"})
    assert report(capsys, "--strict") == []


def test_outside_a_repository_is_an_error_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as stopped:
        main(["zero-bash"])
    assert stopped.value.code == 1
    assert "git failed" in json.loads(capsys.readouterr().err)["error"]


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("mise.toml", "[tasks\n"),
        ("open-quote", '#!/usr/bin/env -S "python3\n'),  # env refuses this too
        ("lone-backslash", "#!/usr/bin/env -S python3 \\\n"),
    ],
)
def test_an_unreadable_file_is_an_error_event_naming_it(
    repo: Path, capsys: pytest.CaptureFixture[str], name: str, text: str
) -> None:
    add(repo, {name: text})
    with pytest.raises(SystemExit) as stopped:
        main(["zero-bash"])
    assert stopped.value.code == 1
    assert json.loads(capsys.readouterr().err)["error"].startswith(f"{name}: ")


def test_the_console_script_reads_its_arguments(repo: Path) -> None:
    add(repo, {"a.sh": "\n"})
    script = Path(sys.executable).parent / "repotools"  # what uv installed from [project.scripts]
    done = subprocess.run([script, "zero-bash", "--strict"], capture_output=True, check=False, text=True)
    assert done.returncode == 1
    assert [json.loads(line)["path"] for line in done.stdout.splitlines()] == ["a.sh"]


def test_a_subfolder_reports_the_whole_repository(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    add(repo, {"a.sh": "\n", "sub/b.py": "\n"})
    monkeypatch.chdir(repo / "sub")
    assert [finding["path"] for finding in report(capsys)] == ["a.sh"]


def real_git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout


def test_this_repository_reports_no_zsh_startup_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.chdir(REPO)
    # The scan reads a copy of this checkout's index with one probe added, so the proof that it read
    # the real repository depends on no leftover there. The probe's blob goes to a temporary object
    # folder that borrows the real one as an alternate: the checkout's index and objects stay untouched.
    copy, objects, probe = tmp_path / "index", tmp_path / "objects", tmp_path / "probe.sh"
    shutil.copyfile(real_git("rev-parse", "--path-format=absolute", "--git-path", "index").strip(), copy)
    real_objects = real_git("rev-parse", "--path-format=absolute", "--git-path", "objects").strip()
    objects.mkdir()
    monkeypatch.setenv("GIT_INDEX_FILE", str(copy))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(objects))
    monkeypatch.setenv("GIT_ALTERNATE_OBJECT_DIRECTORIES", real_objects)
    startup = ("unix/home/.z", "unix/home/.config/zsh/")
    assert [path for path in real_git("ls-files", "--full-name", ":/").splitlines() if path.startswith(startup)]
    probe.write_text("#!/bin/sh\n")  # the shebang finding needs the scan's cat-file to read this blob
    blob = real_git("hash-object", "-w", str(probe)).strip()
    real_git("update-index", "--add", "--cacheinfo", f"100644,{blob},probe/run.sh")
    found = report(capsys)
    assert [finding for finding in found if finding["path"] == "probe/run.sh"] == [
        {"path": "probe/run.sh", "rule": "shell-file", "detail": ".sh"},
        {"path": "probe/run.sh", "rule": "shell-shebang", "detail": "#!/bin/sh"},
    ]
    assert not [finding for finding in found if finding["path"].startswith(startup)]


def test_large_index_and_blob_output_finish_without_a_pipe_deadlock(repo: Path) -> None:
    # 2,048 SHA-1 request lines exceed 64 KiB. The first blob fills stdout before Git drains stdin.
    files: dict[str, str | bytes] = {f"files/{number:04}.txt": b"plain\x00text\r\n\xff\n" for number in range(2048)}
    files["files/0000.txt"] *= 8192
    files["zz-last.sh"] = b"echo last\n"
    add(repo, files)
    (repo / "files/0000.txt").write_bytes(b"#!/bin/sh\n")  # Only staged bytes may affect the scan.
    (repo / "zz-last.sh").unlink()
    done = run_python("from repotools.cli import main\nmain(['zero-bash', '--strict'])\n")
    assert done.returncode == 1, done.stderr.decode(errors="replace")
    assert [json.loads(line) for line in done.stdout.splitlines()] == [
        {"path": "zz-last.sh", "rule": "shell-file", "detail": ".sh"}
    ]


def test_an_early_batch_failure_reports_git_error_instead_of_a_broken_pipe(repo: Path) -> None:
    add(repo, {f"files/{number:04}.txt": "object content\n" for number in range(2048)})
    oid = subprocess.run(["git", "ls-files", "-s"], capture_output=True, check=True, text=True).stdout.split()[1]
    # ls-files still reads the index, but cat-file fails on its first object while requests fill stdin.
    blob = repo / ".git" / "objects" / oid[:2] / oid[2:]
    blob.unlink()  # Git's object is read-only; replace it in this disposable repository.
    blob.write_bytes(zlib.compress(b"blob 65536\x00" + b"x" * 65536)[:-4])
    done = run_python("from repotools.cli import main\nmain(['zero-bash', '--strict'])\n")
    assert done.returncode == 1
    assert done.stdout == b""
    event = json.loads(done.stderr)
    assert set(event) == {"error"}
    assert event["error"].startswith("git failed: ")
