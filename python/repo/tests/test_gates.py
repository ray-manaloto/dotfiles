"""privacy:scan through `mise run`, in a copy of this checkout."""

import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

REPO = Path(__file__).resolve().parents[3]
USER = "gatetester"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"


@pytest.fixture
def copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repository holding this checkout's working tree, committed and already on its remote."""
    clean_git_env(monkeypatch)
    listed = subprocess.run(
        ["git", "-C", REPO, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    root = tmp_path / "copy"
    for name in sorted(set(listed.split("\0")[:-1])):
        source = REPO / name
        if source.is_symlink() or source.exists():  # a file deleted but not yet staged is gone
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, root / name, follow_symlinks=False)
    subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
    monkeypatch.chdir(root)
    subprocess.run(["git", "config", "user.name", "Gate Tester"], check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.com"], check=True)
    commit("base")
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(root))
    monkeypatch.setenv("UV_OFFLINE", "1")
    # The private_user var: the scan then looks for this user under /Users and /home.
    monkeypatch.setenv("USER", USER)
    return root


def commit(subject: str, *args: str) -> str:
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", subject, *args], check=True)
    return git("rev-parse", "HEAD")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout.strip()


def write(files: Mapping[str, str | bytes], *, add: bool = True) -> None:
    for name, text in files.items():
        Path(name).parent.mkdir(parents=True, exist_ok=True)
        Path(name).write_bytes(text if isinstance(text, bytes) else text.encode())
        if add:
            subprocess.run(["git", "add", "-f", name], check=True)


def mise(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["mise", "run", *args], capture_output=True, check=False, text=True)


def said(done: subprocess.CompletedProcess[str], prefix: str) -> list[str]:
    """The task's own stderr lines, without mise's task header and the venv notice uv may print."""
    return [line for line in done.stderr.splitlines() if line.startswith(prefix)]


def test_a_clean_copy_passes_both_scans(copy: Path) -> None:
    for args in [[], ["--outgoing"]]:
        done = mise("privacy:scan", *args)
        assert (done.returncode, said(done, "privacy:scan:")) == (0, [])
    assert copy.exists()


@pytest.mark.usefixtures("copy")
def test_every_tracked_file_is_scanned_line_by_line() -> None:
    write(
        {
            "a.txt": f"one\n/Users/{USER}/x\n/home/{USER}/y and /Users/{USER}/z\n",
            "notes/b c.md": f"/home/{USER}/w\n",
            "crlf.txt": f"x\r\n/Users/{USER}/end",
            "binary.dat": f"\0/Users/{USER}/x\n".encode(),
            "late-nul.dat": f"/Users/{USER}/x\n".encode() + b"x" * 100_000 + b"\0",
            "clean.txt": f"/Users/{USER}\n",
        }
    )
    Path("link.txt").symlink_to("a.txt")
    subprocess.run(["git", "add", "-f", "link.txt"], check=True)
    write({"untracked.txt": f"/Users/{USER}/x\n"}, add=False)
    done = mise("privacy:scan")
    assert done.returncode == 1
    assert said(done, "privacy:scan:") == [
        "privacy:scan: a.txt:2 holds a private path",
        "privacy:scan: a.txt:3 holds a private path",
        "privacy:scan: binary.dat:1 holds a private path",
        "privacy:scan: crlf.txt:2 holds a private path",
        "privacy:scan: late-nul.dat:1 holds a private path",
        "privacy:scan: link.txt:2 holds a private path",
        "privacy:scan: link.txt:3 holds a private path",
        "privacy:scan: notes/b c.md:1 holds a private path",
        HINT,
    ]


def test_the_files_hk_passes_are_scanned_as_given(copy: Path) -> None:
    write({"tracked.txt": f"/Users/{USER}/x\n", "with space/it's.txt": f"\n/home/{USER}/q\n"}, add=False)
    (copy / "folder").mkdir()
    done = mise("privacy:scan", "--", "with space/it's.txt", "missing.txt", "folder", "tracked.txt")
    assert done.returncode == 1
    assert said(done, "privacy:scan:") == [
        "privacy:scan: with space/it's.txt:2 holds a private path",
        "privacy:scan: tracked.txt:1 holds a private path",
        HINT,
    ]


def test_quoted_file_names_split_as_the_shell_split_them(copy: Path) -> None:
    # mise hands the files over as one usage_file string in POSIX quotes; the old script eval'ed it.
    names = ['dq"x.txt', "$HOME.txt", "back\\slash.txt", "star*.txt", "a b/'q'.txt"]
    write(dict.fromkeys(names, f"/Users/{USER}/x\n"), add=False)
    done = mise("privacy:scan", "--", *names)
    assert done.returncode == 1
    assert said(done, "privacy:scan:") == [f"privacy:scan: {name}:1 holds a private path" for name in names] + [HINT]
    assert copy.exists()


def scan_bytes(*args: str) -> tuple[int, list[bytes]]:
    """privacy:scan's exit code and its own lines, as bytes: text mode would turn a \\r in a name into \\n."""
    done = subprocess.run(["mise", "run", "privacy:scan", *args], capture_output=True, check=False)
    return done.returncode, [line for line in done.stderr.split(b"\n") if line.startswith(b"privacy:scan:")]


def stage(mode: str, name: bytes, text: str) -> None:
    """Track an object under a name in the index only, without a file in the working tree."""
    kind = ["-t", "commit", "--literally"] if mode == "160000" else []
    hashing = ["git", "hash-object", "-w", *kind, "--stdin"]
    made = subprocess.run(hashing, input=text.encode(), capture_output=True, check=True)
    entry = f"{mode},{made.stdout.decode().strip()},".encode() + name
    subprocess.run([b"git", b"update-index", b"--add", b"--cacheinfo", entry], check=True)


@pytest.mark.usefixtures("copy")
def test_a_tracked_name_with_a_carriage_return_is_scanned() -> None:
    write({"cr\rname.txt": f"/Users/{USER}/x\n"})
    # Given by hk too: usage-lib leaves a \r unquoted and bash's eval did not split at it.
    for args in [[], ["--", "cr\rname.txt"]]:
        assert scan_bytes(*args) == (1, [b"privacy:scan: cr\rname.txt:1 holds a private path", HINT.encode()])


@pytest.mark.usefixtures("copy")
def test_a_tracked_name_that_is_not_utf8_is_scanned() -> None:
    # macOS refuses such a name on disk, so the file is only in the index, which the scan then reads.
    stage("100644", b"bad\xff.txt", f"/Users/{USER}/x\n")
    assert scan_bytes() == (1, [b"privacy:scan: bad\xff.txt:1 holds a private path", HINT.encode()])


@pytest.mark.usefixtures("copy")
def test_a_tracked_file_gone_from_the_working_tree_is_scanned_as_staged() -> None:
    # The shell scan skipped it; git still holds it. A submodule is another repository's and stays skipped.
    write({"gone.txt": f"\n/home/{USER}/x\n"})
    Path("gone.txt").unlink()
    stage("160000", b"sub", f"tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904\n\n/Users/{USER}/x\n")
    assert scan_bytes() == (1, [b"privacy:scan: gone.txt:2 holds a private path", HINT.encode()])


@pytest.mark.usefixtures("copy")
def test_a_file_whose_name_starts_with_a_dash_is_scanned() -> None:
    write({"-dash.txt": f"/Users/{USER}/x\n"}, add=False)
    done = mise("privacy:scan", "--", "-dash.txt")
    assert done.returncode == 1
    assert said(done, "privacy:scan:") == ["privacy:scan: -dash.txt:1 holds a private path", HINT]


def test_an_unreadable_file_fails_the_scan(copy: Path) -> None:
    # The shell scan let grep's error pass and exited 0; a file the scan cannot read now fails it.
    write({"locked.txt": f"/Users/{USER}/x\n"}, add=False)
    (copy / "locked.txt").chmod(0)
    done = mise("privacy:scan", "--", "locked.txt")
    (copy / "locked.txt").chmod(0o644)
    assert done.returncode == 1
    assert said(done, '{"error":') == ['{"error":"[Errno 13] Permission denied: \'locked.txt\'"}']


def test_no_pattern_of_8_characters_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    # Unreachable through the task, which always renders /Users/<user>/; repotools is called here directly.
    with pytest.raises(SystemExit) as stopped:
        main(["privacy-scan", "--patterns", "/x/\n\n/home//"])
    assert (stopped.value.code, capsys.readouterr().err) == (2, "privacy:scan: no patterns rendered\n")


def test_short_patterns_are_dropped(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "")  # /home// is 7 characters and dropped; /Users// is 8 and kept
    write({"a.txt": "/home//x\n/Users//y\n"})
    done = mise("privacy:scan", "--", "a.txt")
    assert done.returncode == 1
    assert said(done, "privacy:scan:") == ["privacy:scan: a.txt:2 holds a private path", HINT]
    assert copy.exists()


@pytest.mark.usefixtures("copy")
def test_outgoing_scans_every_unpushed_commit_on_branches_and_tags() -> None:
    pushed = commit(f"pushed: /Users/{USER}/old")
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", pushed], check=True)
    commit("clean")
    message = commit(f"docs: mention /Users/{USER}/notes")
    write({"notes.txt": f"/home/{USER}/x\n"})
    content = commit("chore: add notes")
    author = commit("feat: by someone", f"--author=Someone </home/{USER}/mail>")
    subprocess.run(["git", "switch", "-q", "-c", "side"], check=True)
    tagged = commit(f"tagged: /Users/{USER}/t")
    subprocess.run(["git", "tag", "v1"], check=True)
    subprocess.run(["git", "switch", "-q", "main"], check=True)
    subprocess.run(["git", "branch", "-q", "-D", "side"], check=True)
    done = mise("privacy:scan", "--outgoing")
    assert done.returncode == 1
    lines = said(done, "privacy:scan:")
    assert lines[-1] == HINT
    expected = [
        f"privacy:scan: commit {git('rev-parse', '--short', sha)} {subject} holds a private path"
        for sha, subject in [
            (message, f"docs: mention /Users/{USER}/notes"),
            (content, "chore: add notes"),
            (author, "feat: by someone"),
            (tagged, f"tagged: /Users/{USER}/t"),
        ]
    ]
    assert sorted(lines[:-1]) == sorted(expected)
