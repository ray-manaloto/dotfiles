"""repotools pr-create through its command line, in a real git repository with a real origin, and a gh stand-in."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

BODY = "## Summary\n\nOne change.\n"
GH_URL = "https://github.com/owner/repo/pull/7"
GH_EXISTS = f'a pull request for branch "topic" into branch "main" already exists:\n{GH_URL}\n'
GH_STAND_IN = """import json, sys
record, exists = sys.argv[1], sys.argv[2] == "1"
args = sys.argv[3:]
# gh pr create's flags as repotools passes them; anything else is gh's usage error.
if args[:3] != ["pr", "create", "--base"] or args[4] != "--title" or args[6:] != ["--body-file", "-"]:
    sys.stderr.write("unknown flag\\nUsage:  gh pr create [flags]\\n")
    sys.exit(1)
body = sys.stdin.buffer.read().decode()
open(record, "w").write(json.dumps({"base": args[3], "title": args[5], "body": body}))
if exists:
    sys.stderr.write(EXISTS)
    sys.exit(1)
sys.stdout.write(URL + "\\n")
"""


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clean_git_env(monkeypatch)
    # Beside the repository, untracked: the pull request body, which tests may rewrite.
    (tmp_path / "body.md").write_text(BODY)
    monkeypatch.setenv("TEST_BODY_FILE", str(tmp_path / "body.md"))
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", root], check=True)
    monkeypatch.chdir(root)
    (root / "a.py").write_text("one\n")
    commit()
    return root


def commit() -> None:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "c"], check=True)


def body(content: str = BODY) -> str:
    path = Path(os.environ["TEST_BODY_FILE"])
    path.write_text(content)
    return str(path)


def pr(title: str = "feat: one", body_file: str | None = None) -> list[str]:
    return ["--title", title, "--body-file", body() if body_file is None else body_file]


def pr_refusal_of(capsys: pytest.CaptureFixture[str], command: str, options: list[str]) -> str:
    capsys.readouterr()
    with pytest.raises(SystemExit) as stopped:
        main([command, *options])
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def origin(root: Path, branch: str = "trunk") -> None:
    """A real bare origin whose default branch is branch, pushed to and recorded as origin/HEAD by set-head."""
    remote = root.parent / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", branch, remote], check=True)
    subprocess.run(["git", "remote", "add", "origin", remote], check=True)
    subprocess.run(["git", "push", "-q", "origin", f"HEAD:{branch}"], check=True)
    subprocess.run(["git", "remote", "set-head", "origin", "--auto"], check=True, capture_output=True)


def fake_gh(root: Path, monkeypatch: pytest.MonkeyPatch, *, exists: bool = False) -> Path:
    """A gh first on PATH that checks its flags, reads the body from stdin and answers as gh pr create does.

    It prints the new pull request's URL, or gh's error when the branch already has one; it opens nothing.
    """
    record = root.parent / "gh.json"
    program = root.parent / "bin" / "gh"
    program.parent.mkdir()
    code = GH_STAND_IN.replace("EXISTS", repr(GH_EXISTS)).replace("URL", repr(GH_URL))
    (root.parent / "gh.py").write_text(code)
    flag = "1" if exists else "0"
    program.write_text(
        f"#!{sys.executable}\nimport runpy, sys\nsys.argv[1:1] = [{str(record)!r}, {flag!r}]\n"
        f"runpy.run_path({str(root.parent / 'gh.py')!r}, run_name='__main__')\n"
    )
    program.chmod(0o755)
    monkeypatch.setenv("PATH", f"{program.parent}{os.pathsep}{os.environ['PATH']}")
    return record


def test_pr_create_sends_the_text_to_gh(
    repo: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """capfd, not capsys: gh's own stdout passes straight through to the caller's. The base is origin's default."""
    record = fake_gh(repo, monkeypatch)
    origin(repo)
    main(["pr-create", *pr()])
    sent = {"base": "trunk", "title": "feat: one", "body": BODY}
    assert json.loads(record.read_text()) == sent
    assert capfd.readouterr().out == GH_URL + "\n"


def test_a_crlf_body_is_sent_as_its_bytes(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    crlf = Path(body()).with_name("crlf.md")
    crlf.write_bytes(b"## Summary\r\n\r\nOne change.\r\n")
    record = fake_gh(repo, monkeypatch)
    origin(repo)
    main(["pr-create", *pr(body_file=str(crlf))])
    assert json.loads(record.read_text())["body"] == "## Summary\r\n\r\nOne change.\r\n"


def test_gh_refusing_the_pull_request_is_a_named_failure(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(repo, monkeypatch, exists=True)
    origin(repo)
    assert pr_refusal_of(capsys, "pr-create", pr()) == f"gh failed: {GH_EXISTS}"


def test_pr_create_without_a_known_default_branch_never_runs_gh(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    record = fake_gh(repo, monkeypatch)
    assert "git remote set-head origin --auto" in pr_refusal_of(capsys, "pr-create", pr())
    assert not record.exists()


@pytest.mark.parametrize("title", ["feat: one\nmore", "feat: one\n", ""])
def test_a_title_that_is_not_one_line_is_refused(repo: Path, capsys: pytest.CaptureFixture[str], title: str) -> None:
    assert repo.exists()
    assert "title" in pr_refusal_of(capsys, "pr-create", pr(title=title))


def test_an_unknown_command_names_the_choices(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["nope"])
    assert "pr-create" in json.loads(capsys.readouterr().err)["error"]
