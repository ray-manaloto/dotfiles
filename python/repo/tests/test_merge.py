"""repotools pr-merge through its command line: a real git checkout and hk, and a gh stand-in."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from repotools.cli import main
from repotools.merge import BOT_CLOSE, BOT_OPEN, NOREPLY

from . import test_gates
from .test_gates import copy, mise, said
from .test_pr_create import commit, origin, pr, pr_refusal_of, repo

__all__ = ["copy", "repo"]  # the fixtures, used by name
HK_PKL = Path(__file__).resolve().parents[3] / "hk.pkl"

# A gh that answers from a scenario file and logs every call; it reaches no network. Once hk's step has left the
# file ../hk-ran, the scenario's "after" entries replace its own: GitHub as it is after the minutes hk takes.
GH = """import json, os, sys
scenario, log = json.load(open(sys.argv[1])), sys.argv[2]
if os.path.exists(os.path.join(os.path.dirname(sys.argv[1]), "hk-ran")):
    scenario |= scenario.get("after", {})
args = sys.argv[3:]
open(log, "a").write(json.dumps(args) + "\\n")
if args[:2] == ["pr", "view"] and args[3:] == ["--json", "headRefOid,state,baseRefName,title,body"]:
    print(json.dumps(scenario["pr"]))
elif args == ["repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"]:
    print(scenario["default"])
elif args[:2] == ["pr", "merge"]:
    if scenario.get("refuse"):
        sys.stderr.write(scenario["refuse"])
        sys.exit(1)
elif args[:2] == ["pr", "view"] and args[3:] == ["--json", "mergeCommit"]:
    print(json.dumps({"mergeCommit": {"oid": "f00d"}}))
elif args[:2] == ["api", "repos/{owner}/{repo}/commits/f00d"] and args[2:] == ["--jq", ".commit.author.email"]:
    print(scenario["email"])
else:
    sys.stderr.write("unknown command\\n")
    sys.exit(1)
"""
BODY = "## Summary\n\nOne change.\n"  # pr()'s body file
NOTES = f"\n\n{BOT_OPEN}\n\n## Summary by CodeRabbit\n\n* One change.\n\n{BOT_CLOSE}"
HK_RAN = "touch ../hk-ran"


def pkl_string(text: str) -> str:
    """text as a Pkl string literal: a backslash or a double quote is escaped, so neither ends or bends it."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def hk_config(step: str) -> str:
    """This repository's hk.pkl header (its pinned hk package) with one check step that runs step."""
    head = HK_PKL.read_text().splitlines()[0]
    steps = f'        steps {{\n            ["t"] {{ check = {pkl_string(step)} }}\n        }}\n'
    return f'{head}\n\nhooks {{\n    ["check"] {{\n{steps}    }}\n}}\n'


def install_gh(folder: Path, scenario: Path, log: Path) -> Path:
    """The gh stand-in as folder/gh, reading scenario and appending its calls to log."""
    (folder.parent / "gh.py").write_text(GH)
    program = folder / "gh"
    program.write_text(
        f"#!{sys.executable}\nimport runpy, sys\nsys.argv[1:1] = [{str(scenario)!r}, {str(log)!r}]\n"
        f"runpy.run_path({str(folder.parent / 'gh.py')!r}, run_name='__main__')\n"
    )
    program.chmod(0o755)
    return program


class World:
    """A committed hk.pkl whose check --all runs step, and gh first on PATH, reading a scenario and logging calls."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch, step: str) -> None:
        # hk's own settings from an outer hk run must not reach the inner one.
        for name in [name for name in os.environ if name.startswith("HK_")]:
            monkeypatch.delenv(name)
        (root / "hk.pkl").write_text(hk_config(step))
        commit()
        self.ran = root.parent / "hk-ran"
        self.scenario = root.parent / "scenario.json"
        self.log = root.parent / "calls.jsonl"
        folder = root.parent / "bin"
        folder.mkdir()
        install_gh(folder, self.scenario, self.log)
        monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
        origin(root)
        done = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True)
        self.head = done.stdout.strip()
        self.set(pr=self.pr(), default="trunk", email=NOREPLY)

    def pr(self) -> dict[str, str]:
        return {"headRefOid": self.head, "state": "OPEN", "baseRefName": "trunk", "title": "feat: one", "body": BODY}

    def set(self, **changes: object) -> None:
        old = json.loads(self.scenario.read_text()) if self.scenario.exists() else {}
        self.scenario.write_text(json.dumps(old | changes))

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def merged(self) -> bool:
        return any(call[:2] == ["pr", "merge"] for call in self.calls())


@pytest.fixture
def world(repo: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return World(repo, monkeypatch, HK_RAN)


def merge_args() -> list[str]:
    return ["--number", "7", *pr()]


@pytest.mark.parametrize("shown", [BODY, BODY + NOTES], ids=["as-sent", "with-coderabbit-notes"])
def test_every_gate_holding_merges_in_the_one_form_and_reports_the_author(
    world: World, capsys: pytest.CaptureFixture[str], shown: str
) -> None:
    world.set(pr=world.pr() | {"body": shown})
    main(["pr-merge", *merge_args()])
    assert json.loads(capsys.readouterr().out) == {"number": 7, "merge_commit": "f00d", "author_email": NOREPLY}
    assert world.ran.exists()  # the real hk check --all ran the checkout's step
    merge = ["pr", "merge", "7", "--merge", "--match-head-commit", world.head, "--author-email", NOREPLY]
    assert merge in world.calls()


def test_a_dirty_checkout_is_refused_before_anything_runs(
    world: World, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "notes.md").write_text("untracked\n")
    assert "untracked files" in pr_refusal_of(capsys, "pr-merge", merge_args())
    assert world.calls() == []
    assert not world.ran.exists()


PR_REFUSALS = [
    ({"state": "MERGED"}, "is MERGED, not open"),
    ({"baseRefName": "dev"}, "goes into dev, not trunk"),
    ({"headRefOid": "beef"}, "head is beef, but this checkout's HEAD is"),
    ({"title": "feat: edited"}, "title on GitHub is not the given title"),
    ({"body": "## Summary\n\nEdited.\n"}, "body on GitHub is not the given body"),
    ({"body": BODY + "\n\nAdded by hand."}, "body on GitHub is not the given body"),
    ({"body": BODY + NOTES + "\nAdded after the notes."}, "body on GitHub is not the given body"),
    ({"body": BODY + NOTES + NOTES}, "body on GitHub is not the given body"),
    ({"body": "Before.\n" + BODY + NOTES}, "body on GitHub is not the given body"),
]


@pytest.mark.parametrize(("change", "said"), PR_REFUSALS)
def test_a_pull_request_unlike_the_given_one_is_refused_before_hk(
    world: World, capsys: pytest.CaptureFixture[str], change: dict[str, str], said: str
) -> None:
    world.set(pr=world.pr() | change)
    assert said in pr_refusal_of(capsys, "pr-merge", merge_args())
    assert not world.ran.exists()
    assert not world.merged()


@pytest.mark.parametrize(("change", "said"), PR_REFUSALS)
def test_a_pull_request_changed_while_hk_ran_is_refused(
    world: World, capsys: pytest.CaptureFixture[str], change: dict[str, str], said: str
) -> None:
    world.set(after={"pr": world.pr() | change})
    assert said in pr_refusal_of(capsys, "pr-merge", merge_args())
    assert world.ran.exists()
    assert not world.merged()


def test_a_default_branch_renamed_on_github_is_refused(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    world.set(default="main")
    assert "goes into trunk, not main" in pr_refusal_of(capsys, "pr-merge", merge_args())


@pytest.mark.parametrize(
    ("step", "said"),
    [
        (f"{HK_RAN} && echo more >> a.py", "the checkout has changes"),
        (f"{HK_RAN} && git -c user.name=t -c user.email=t@e commit -q --allow-empty -m x", "HEAD moved from"),
    ],
    ids=["edited", "committed"],
)
def test_a_checkout_changed_while_hk_ran_is_refused(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], step: str, said: str
) -> None:
    made = World(repo, monkeypatch, step)
    assert said in pr_refusal_of(capsys, "pr-merge", merge_args())
    assert not made.merged()


def test_a_failing_hk_check_all_stops_the_merge(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    made = World(repo, monkeypatch, "exit 3")
    assert pr_refusal_of(capsys, "pr-merge", merge_args()) == f"hk check --pr failed (exit 3) on {made.head}"
    assert not made.merged()


def test_gh_refusing_the_merge_is_a_named_failure(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    world.set(refuse="Head branch was modified. Review and try the merge again.\n")
    said = pr_refusal_of(capsys, "pr-merge", merge_args())
    assert said == "gh failed: Head branch was modified. Review and try the merge again.\n"


def test_a_merge_commit_with_another_author_is_reported(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    world.set(email="someone@example.com")
    said = pr_refusal_of(capsys, "pr-merge", merge_args())
    assert said == f"merge commit f00d has author someone@example.com, not {NOREPLY}: report it to the owner"


def test_the_task_runs_the_installed_repotools_with_hostile_text_as_inert_arguments(
    copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The task hands its three arguments, full of shell syntax, whole to the real repotools in uv's tool bin folder
    (where //repo:tools-install puts main's), never the branch venv's, and nothing in them runs.

    The pull request on the gh stand-in carries that very title and body, so repotools passes the title and body checks
    only if both arrived intact, and stops at the next gate: the copy's hk check --all exits 3.
    """
    tools = copy.parent / "tool-bin"
    tools.mkdir()
    (tools / "repotools").symlink_to(Path(sys.executable).parent / "repotools")
    monkeypatch.setenv("UV_TOOL_BIN_DIR", str(tools))
    # The branch's own repotools, which the venv the task activates puts first on PATH: it must never run.
    branch = copy / "python" / "repo" / ".venv" / "bin" / "repotools"
    branch.parent.mkdir(parents=True)
    branch.write_text(f"#!{sys.executable}\nopen({str(copy.parent / 'pwned-branch')!r}, 'w')\n")
    branch.chmod(0o755)
    (copy.parent / "bin").mkdir()
    gh = install_gh(copy.parent / "bin", copy.parent / "scenario.json", copy.parent / "calls.jsonl")
    # gh is a mise tool, which mise puts ahead of PATH in a task; the copy's own wrapper runs the stand-in instead.
    with (copy / "mise.local.toml").open("a") as local:
        local.write(f'\n[wrappers.gh]\ncommand = "{gh}"\n')
    title = 'feat: it\'s "$(touch pwned)" `touch pwned2`; touch pwned3 && echo $HOME'
    body_file = "body; touch pwned4.md"  # beside the copy's files, and ignored by its allowlisted .gitignore
    (copy / body_file).write_text(BODY)
    for name in [name for name in os.environ if name.startswith("HK_")]:
        monkeypatch.delenv(name)
    (copy / "hk.pkl").write_text(hk_config("exit 3"))
    head = test_gates.commit("hk exits 3")
    shown = {"headRefOid": head, "state": "OPEN", "baseRefName": "main", "title": title, "body": BODY}
    (copy.parent / "scenario.json").write_text(json.dumps({"pr": shown, "default": "main"}))
    done = mise("//repo:pr-merge", "7", title, body_file)
    assert done.returncode == 1
    (error,) = said(done, "{")  # mise adds its own task lines around repotools' one JSON error
    assert json.loads(error)["error"] == f"hk check --pr failed (exit 3) on {head}"
    assert not list(copy.parent.rglob("pwned*"))
