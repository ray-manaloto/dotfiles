"""review:python, review:python:approved and privacy:scan through `mise run`, in a copy of this checkout."""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
USER = "gatetester"
REFUSAL = "review:python has not passed on the staged python/ files; stage them, then mise run review:python"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"
REPORT = "Reviewed.\nclean: R1, R2\nVERDICT: PASS\n"
# Codex's place in review:python: records what it was given, then writes the report where -o says.
CODEX = """
import json, os, subprocess, sys
from collections.abc import Mapping
from pathlib import Path
args = sys.argv[1:]
log = {"argv": args, "cwd": os.getcwd(), "stdin": sys.stdin.read()}
Path(os.environ["STANDIN_LOG"]).write_text(json.dumps(log))
if os.environ.get("STANDIN_STAGE"):
    Path(os.environ["STANDIN_STAGE"]).write_text("staged while the reviewer read\\n")
    subprocess.run(["git", "add", os.environ["STANDIN_STAGE"]], check=True)
Path(args[args.index("-o") + 1]).write_text(os.environ["STANDIN_REPORT"])
sys.exit(int(os.environ.get("STANDIN_EXIT", "0")))
"""


@pytest.fixture
def copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repository holding this checkout's working tree, committed and already on its remote."""
    # A pre-commit hook exports GIT_*, which would point git at the real checkout.
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
        if source.is_symlink() or source.exists():  # a file deleted but not yet staged is gone
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, root / name, follow_symlinks=False)
    subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
    monkeypatch.chdir(root)
    subprocess.run(["git", "config", "user.name", "Gate Tester"], check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.com"], check=True)
    commit("base")
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "codex").write_text(f"#!{sys.executable}\n{CODEX}")
    (bin_dir / "codex").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STANDIN_LOG", str(tmp_path / "codex.json"))
    monkeypatch.setenv("STANDIN_REPORT", REPORT)
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


def codex() -> dict[str, object]:
    return json.loads(Path(os.environ["STANDIN_LOG"]).read_text())


def said(done: subprocess.CompletedProcess[str], prefix: str) -> list[str]:
    """The task's own stderr lines, without mise's task header and the venv notice uv may print."""
    return [line for line in done.stderr.splitlines() if line.startswith(prefix)]


def prompt(path: str, commit: str) -> str:
    return (REPO / "tasks" / "review" / "python.md").read_text() + f"Path: {path}\nCommit: {commit}\n"


def recorded(root: Path) -> bool:
    return (root / ".git" / "review-python.approved").exists()


def test_a_pass_prints_the_verdict_and_approves_the_staged_python_files(copy: Path) -> None:
    write({"python/new.py": "x = 1\n"})
    done = mise("review:python")
    assert (done.returncode, done.stdout) == (0, "VERDICT: PASS\n")
    assert codex() == {
        "argv": ["exec", "-C", ".", "-c", 'sandbox_mode="read-only"', "-o", ".git/review-python.md", "-"],
        "cwd": str(copy),
        "stdin": prompt("python", "none"),
    }
    assert (copy / ".git" / "review-python.md").read_text() == REPORT
    assert mise("review:python:approved").returncode == 0
    write({"python/new.py": "x = 2\n"})
    refused = mise("review:python:approved")
    assert refused.returncode == 1
    assert said(refused, "review:python has") == [REFUSAL]


def test_without_a_review_the_staged_files_are_refused(copy: Path) -> None:
    assert not recorded(copy)
    refused = mise("review:python:approved")
    assert refused.returncode == 1
    assert said(refused, "review:python has") == [REFUSAL]


def test_changes_exit_1_and_approve_nothing(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STANDIN_REPORT", "R3 python/a.py:1 - x - y\nVERDICT: CHANGES\n")
    done = mise("review:python")
    assert (done.returncode, done.stdout) == (1, "VERDICT: CHANGES\n")
    assert not recorded(copy)


def test_a_pass_line_anywhere_in_the_report_passes(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STANDIN_REPORT", "VERDICT: PASS\nA closing remark.")
    done = mise("review:python")
    assert (done.returncode, done.stdout) == (0, "A closing remark.\n")
    assert recorded(copy)


def test_an_empty_last_line_is_printed_as_empty(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STANDIN_REPORT", "VERDICT: CHANGES\n\n")
    done = mise("review:python")
    assert (done.returncode, done.stdout) == (1, "\n")
    assert not recorded(copy)


def test_codex_failing_stops_with_its_exit_code(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STANDIN_EXIT", "3")
    done = mise("review:python")
    assert (done.returncode, done.stdout) == (3, "")
    assert not recorded(copy)


def test_the_path_commit_and_out_reach_the_reviewer(copy: Path) -> None:
    done = mise("review:python", "cpp", "--commit", "HEAD", "--out", "report.md")
    assert (done.returncode, done.stdout) == (0, "VERDICT: PASS\n")
    assert codex()["argv"] == ["exec", "-C", ".", "-c", 'sandbox_mode="read-only"', "-o", "report.md", "-"]
    assert codex()["stdin"] == prompt("cpp", "HEAD")
    assert (copy / "report.md").read_text() == REPORT
    assert not recorded(copy)


@pytest.mark.parametrize(
    ("args", "files"),
    [
        (["python", "--commit", "HEAD"], {}),
        ([], {"python/new.py": "x = 2\n"}),
        ([], {"python/scratch.py": "untracked\n"}),
    ],
    ids=["a-commit", "unstaged", "untracked"],
)
def test_a_pass_approves_only_the_index_the_reviewer_saw(copy: Path, args: list[str], files: dict[str, str]) -> None:
    write({"python/new.py": "x = 1\n"})
    write(files, add=False)
    done = mise("review:python", *args)
    assert (done.returncode, done.stdout) == (0, "VERDICT: PASS\n")
    assert not recorded(copy)


def test_files_staged_during_the_review_stay_unapproved(copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write({"python/new.py": "x = 1\n"})
    monkeypatch.setenv("STANDIN_STAGE", "python/late.py")
    assert mise("review:python").returncode == 0
    assert recorded(copy)
    refused = mise("review:python:approved")
    assert refused.returncode == 1
    assert said(refused, "review:python has") == [REFUSAL]


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
        "privacy:scan: crlf.txt:2 holds a private path",
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
