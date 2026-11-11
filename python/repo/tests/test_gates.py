"""review:python, review:python:approved and privacy:scan through `mise run`, in a copy of this checkout."""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

REPO = Path(__file__).resolve().parents[3]
USER = "gatetester"
REFUSAL = "review:python has not passed on the staged python/ files; stage them, then mise run review:python"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"
REPORT = "Reviewed.\nclean: R1, R2\nVERDICT: PASS\n"
# Codex's place in review:python: records what it was given, then writes the report where --output-last-message= says.
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
# Only the one-word form: real codex exits 2 on -o -report, reading -report as options.
out = next(a for a in args if a.startswith("--output-last-message=")).split("=", 1)[1]
Path(out).write_bytes(os.environb[b"STANDIN_REPORT"])
sys.exit(int(os.environ.get("STANDIN_EXIT", "0")))
"""


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
        "argv": [
            "exec",
            "-C",
            ".",
            "-c",
            'sandbox_mode="read-only"',
            "-c",
            'approval_policy="never"',
            "-c",
            "features.multi_agent_v2.max_concurrent_threads_per_session=7",
            "--output-last-message=.git/review-python.md",
            "-",
        ],
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


def review_bytes(*args: str) -> tuple[int, bytes]:
    """review:python's exit code and stdout as bytes: text mode would turn a \\r into \\n."""
    done = subprocess.run(["mise", "run", "review:python", *args], capture_output=True, check=False)
    return done.returncode, done.stdout


@pytest.mark.parametrize(
    ("report", "expected"),
    [
        ("VERDICT: PASS\r\n", (1, b"VERDICT: PASS\r\n")),
        ("VERDICT: PASS\rmore\n", (1, b"VERDICT: PASS\rmore\n")),
        ("\udcff\nVERDICT: PASS\n", (0, b"VERDICT: PASS\n")),
    ],
    ids=["crlf", "bare-cr", "not-utf8"],
)
def test_the_verdict_is_an_exact_line_of_bytes(
    copy: Path, monkeypatch: pytest.MonkeyPatch, report: str, expected: tuple[int, bytes]
) -> None:
    # As grep -qx and tail -n 1 read it: a \r is part of the line, and the report need not be UTF-8.
    monkeypatch.setenv("STANDIN_REPORT", report)  # \udcff reaches the stand-in as the byte 0xff
    assert review_bytes() == expected
    assert recorded(copy) == (expected[0] == 0)


def test_a_stamp_with_a_carriage_return_is_refused(copy: Path) -> None:
    assert mise("review:python").returncode == 0
    stamp = copy / ".git" / "review-python.approved"
    stamp.write_bytes(stamp.read_bytes().replace(b"\n", b"\r\n"))
    refused = mise("review:python:approved")
    assert (refused.returncode, said(refused, "review:python has")) == (1, [REFUSAL])
    stamp.write_bytes(stamp.read_bytes().replace(b"\r\n", b"\n\n"))  # $(cat) dropped trailing newlines
    assert mise("review:python:approved").returncode == 0


def test_values_that_start_with_a_dash_reach_the_reviewer(copy: Path) -> None:
    done = mise("review:python", "--commit=-value", "--out=-report", "--", "-dir")
    assert (done.returncode, done.stdout) == (0, "VERDICT: PASS\n")
    assert codex()["argv"] == [
        "exec",
        "-C",
        ".",
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        'approval_policy="never"',
        "-c",
        "features.multi_agent_v2.max_concurrent_threads_per_session=7",
        "--output-last-message=-report",
        "-",
    ]
    assert codex()["stdin"] == prompt("-dir", "-value")
    assert (copy / "-report").read_text() == REPORT


def test_the_path_commit_and_out_reach_the_reviewer(copy: Path) -> None:
    done = mise("review:python", "cpp", "--commit", "HEAD", "--out", "report.md")
    assert (done.returncode, done.stdout) == (0, "VERDICT: PASS\n")
    assert codex()["argv"] == [
        "exec",
        "-C",
        ".",
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        'approval_policy="never"',
        "-c",
        "features.multi_agent_v2.max_concurrent_threads_per_session=7",
        "--output-last-message=report.md",
        "-",
    ]
    assert codex()["stdin"] == prompt("cpp", "HEAD")
    assert (copy / "report.md").read_text() == REPORT
    assert not recorded(copy)


def merge_side(*, on_main: bool) -> None:
    """An uncommitted merge of side, which adds taken.py, resolved.py and a name with a newline; both change ours.py
    and theirs.py, which the merge resolves to side's version."""
    git("switch", "-q", "-c", "side")
    write({"python/taken.py": "x = 1\n", "python/resolved.py": "x = 1\n", "python/ours.py": "x = 1\n"})
    write({"python/theirs.py": "x = 1\n"})
    write({"python/a\nMerged: python/resolved.py": "x = 1\n"})
    side = commit("side")
    if on_main:
        git("update-ref", "refs/remotes/origin/main", side)
    git("switch", "-q", "main")
    write({"python/ours.py": "x = 2\n", "python/theirs.py": "x = 2\n"})
    commit("main")
    git("merge", "-q", "--no-commit", "--no-ff", "-X", "ours", "side")
    write({"python/resolved.py": "x = 3\n", "python/theirs.py": "x = 1\n"})


@pytest.mark.usefixtures("copy")
def test_a_merge_of_main_leaves_out_the_files_it_brings_in_unchanged() -> None:
    merge_side(on_main=True)
    assert mise("review:python").stdout == "VERDICT: PASS\n"
    # resolved.py differs from both sides; ours.py, kept by -X ours, from neither; theirs.py drops this branch's
    # change, a decision to review. A name holding a newline stays one quoted line, so it cannot pose as another.
    merged = 'Merged: "python/a\\nMerged: python/resolved.py"\nMerged: python/taken.py\n'
    assert codex()["stdin"] == prompt("python", "none") + merged


@pytest.mark.usefixtures("copy")
def test_a_merge_keeps_a_file_an_earlier_merge_changed() -> None:
    git("switch", "-q", "-c", "side")
    write({"python/p.py": "x = 1\n"})
    commit("side")
    git("switch", "-q", "main")
    git("merge", "-q", "--no-commit", "--no-ff", "side")
    # The branch's only edit of p.py is in this merge, which no commit of its own repeats.
    write({"python/p.py": "x = 2\n"})
    commit("merge side")
    git("switch", "-q", "side")
    write({"python/p.py": "x = 3\n", "python/q.py": "x = 1\n"})
    git("update-ref", "refs/remotes/origin/main", commit("side again"))
    git("switch", "-q", "main")
    git("merge", "-q", "--no-commit", "--no-ff", "-X", "theirs", "side")
    assert mise("review:python").stdout == "VERDICT: PASS\n"
    assert codex()["stdin"] == prompt("python", "none") + "Merged: python/q.py\n"


@pytest.mark.usefixtures("copy")
def test_a_merge_keeps_a_file_an_earlier_merge_kept_from_main() -> None:
    write({"python/p.py": "x = 0\n"})
    commit("base")
    git("switch", "-q", "-c", "side")
    write({"python/p.py": "x = 1\n"})
    commit("side")
    git("switch", "-q", "main")
    write({"python/q.py": "x = 1\n"})
    commit("main")
    git("merge", "-q", "--no-commit", "--no-ff", "side")
    # This merge rejects side's change and matches its branch parent; dense mode would drop it.
    write({"python/p.py": "x = 0\n"})
    commit("merge side")
    git("switch", "-q", "side")
    write({"python/p.py": "x = 2\n", "python/r.py": "x = 1\n"})
    git("update-ref", "refs/remotes/origin/main", commit("side again"))
    git("switch", "-q", "main")
    git("merge", "-q", "--no-commit", "--no-ff", "-X", "theirs", "side")
    assert mise("review:python").stdout == "VERDICT: PASS\n"
    assert codex()["stdin"] == prompt("python", "none") + "Merged: python/r.py\n"


@pytest.mark.usefixtures("copy")
def test_a_merge_of_a_commit_main_does_not_hold_is_reviewed_whole() -> None:
    merge_side(on_main=False)
    assert mise("review:python").stdout == "VERDICT: PASS\n"
    assert codex()["stdin"] == prompt("python", "none")


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


def test_pane_pin_passes_a_hostile_transcript_path_through_mise_inert(copy: Path, tmp_path: Path) -> None:
    """The --subagent path reaches repotools as one argument: no word split, no command or variable expansion."""
    # The file name must be agent-<id>.jsonl, so the hostile part is the folder; any folder name is valid.
    folder = tmp_path / 'sub agents $HOME $(touch ran1) `touch ran2`; touch ran3 "q" *'
    folder.mkdir()
    transcript = folder / "agent-a1.jsonl"
    transcript.write_text("")
    done = mise("//repo:pane-pin", "--subagent", str(transcript))
    assert done.returncode == 0, done.stderr
    pinned = Path(git("rev-parse", "--git-path", "review-python.pane-session").strip())
    assert pinned.read_text() == f"{transcript.resolve()}\n"
    assert not [path for path in (copy, tmp_path) for name in ("ran1", "ran2", "ran3") if (path / name).exists()]
