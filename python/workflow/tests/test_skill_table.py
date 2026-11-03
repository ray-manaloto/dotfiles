"""workflowtools skill-table, against a plugin install under a scratch HOME."""

import json
from pathlib import Path

import pytest

from workflowtools.cli import main

from .conftest import add, report, write

SHA = "a" * 40
TABLE = "docs/workflow/skills.md"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def install(home: Path, records: list[dict[str, str]]) -> None:
    plugins = {"plugins": {"mattpocock-skills@mattpocock": records}}
    write(home, {".claude/plugins/installed_plugins.json": json.dumps(plugins)})


def plugin(root: Path) -> dict[str, str]:
    write(
        root,
        {
            ".claude-plugin/plugin.json": json.dumps({"skills": ["./skills/grill", "./skills/tdd", "./skills/plain"]}),
            "skills/grill/SKILL.md": "---\nname: grill\ndisable-model-invocation: true\n---\n",
            "skills/tdd/SKILL.md": "---\nname: tdd\ndisable-model-invocation: false\n---\n",
            "skills/plain/SKILL.md": "no block\n",
        },
    )
    return {"projectPath": str(Path.cwd()), "installPath": str(root), "gitCommitSha": SHA}


def table(rows: str, pin: str = SHA) -> str:
    return f'---\nupstream_commit: "{pin}"\n---\n| skill | who |\n|---|---|\n{rows}'


def skipped() -> list[dict[str, str]]:
    reason = "mattpocock-skills@mattpocock is not installed for this checkout"
    return [{"check": "skill-table", "reason": reason}, {"exit": "0"}]


@pytest.mark.usefixtures("repo", "home")
def test_no_install_record_skips(capsys: pytest.CaptureFixture[str]) -> None:
    assert report(capsys, "skill-table") == skipped()


@pytest.mark.usefixtures("repo")
def test_an_install_for_another_project_skips(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [{"installPath": "/x"}, {"projectPath": "/elsewhere", "installPath": "/x"}])
    assert report(capsys, "skill-table") == skipped()


@pytest.mark.usefixtures("repo")
def test_an_install_whose_files_are_gone_skips(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [{"projectPath": str(Path.cwd()), "installPath": str(home / "gone")}])
    assert report(capsys, "skill-table") == skipped()


def test_a_matching_table_passes(repo: Path, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [plugin(home / "plugin")])
    add(repo, {TABLE: table("| `grill` | user-only |\n| `plain` | model |\n| `tdd` | model |\n")})
    assert report(capsys, "skill-table") == [{"exit": "0"}]


def test_a_table_without_a_pin_is_reported(repo: Path, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [plugin(home / "plugin")])
    add(repo, {TABLE: "| `grill` | user-only |\n"})
    assert report(capsys, "skill-table") == [
        {"path": TABLE, "check": "skill-table", "detail": "no full upstream_commit in its frontmatter"},
        {"exit": "1"},
    ]


def test_a_moved_install_is_reported(repo: Path, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [plugin(home / "plugin")])
    add(repo, {TABLE: table("", pin="b" * 40)})
    [found, _] = report(capsys, "skill-table")
    assert found["detail"].startswith(f"installed plugin is {SHA}, the table pins {'b' * 40}")


def test_rows_that_disagree_are_reported(repo: Path, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(home, [plugin(home / "plugin")])
    add(repo, {TABLE: table("| `grill` | model |\n| `tdd` | model |\n| `gone` | model |\n")})
    assert [line.get("detail") for line in report(capsys, "skill-table")] == [
        "grill: the table says model, SKILL.md says user-only",
        "plain: the table says nothing, SKILL.md says model",
        "gone: in the table, not in the plugin",
        None,
    ]


def test_an_installed_skill_with_broken_yaml_is_a_failure(
    repo: Path, home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    install(home, [plugin(home / "plugin")])
    write(home / "plugin", {"skills/tdd/SKILL.md": "---\nname: [\n---\n"})
    add(repo, {TABLE: table("")})
    with pytest.raises(SystemExit):
        main(["skill-table"])
    assert json.loads(capsys.readouterr().err)["error"].startswith("while parsing")
