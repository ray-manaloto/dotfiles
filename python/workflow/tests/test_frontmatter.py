"""workflowtools frontmatter, on what the index holds."""

from pathlib import Path

import pytest

from .conftest import add, report, write

SKILL = "---\nname: grill\ndescription: Ask hard questions\n---\nbody\n"
CONCEPT = "---\ntype: decision\n---\nbody\n"


def check(detail: str, path: str) -> dict[str, str]:
    return {"path": path, "check": "frontmatter", "detail": detail}


def test_good_files_pass(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            "skills/grill/SKILL.md": SKILL,
            "unix/home/.config/agents/workflow/plan.md": CONCEPT,
            "unix/home/.config/agents/workflow/index.md": "a map\n",
            "docs/research/log.md": "",
            "README.md": "no block\n",
            "a.yml": "key: value\n",
            "b.yaml": "- one\n",
            "k8s.yaml": "kind: A\n---\nkind: B\n",
        },
    )
    assert report(capsys, "frontmatter") == [{"exit": "0"}]


@pytest.mark.parametrize(
    ("text", "detail"),
    [
        ("", "SKILL.md has no frontmatter block"),
        ("# Grill\n", "SKILL.md has no frontmatter block"),
        ("---\nname: grill\n", "unterminated frontmatter block"),
        ("---\nname: grill\n---\n", "frontmatter description: Field required"),
        ('---\nname: ""\ndescription: d\n---\n', "frontmatter name: String should have at least 1 character"),
        ("---\n- a list\n---\n", "frontmatter block: Input should be a valid dictionary"),
        ("---\nname: [\n---\n", "invalid YAML: "),
    ],
)
def test_a_bad_skill_header_is_reported(repo: Path, capsys: pytest.CaptureFixture[str], text: str, detail: str) -> None:
    add(repo, {"skills/grill/SKILL.md": text})
    [found, end] = report(capsys, "frontmatter")
    assert found["path"] == "skills/grill/SKILL.md"
    assert found["detail"].startswith(detail)
    assert end == {"exit": "1"}


def test_an_okf_concept_needs_a_typed_block(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"docs/research/a.md": "no block\n", "unix/home/.config/agents/workflow/b.md": "---\ntitle: b\n---\n"})
    assert report(capsys, "frontmatter") == [
        check("okf concept file has no frontmatter block", "docs/research/a.md"),
        check("frontmatter type: Field required", "unix/home/.config/agents/workflow/b.md"),
        {"exit": "1"},
    ]


def test_yaml_that_does_not_parse_is_reported(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"ci.yml": "a: [\n"})
    [found, _] = report(capsys, "frontmatter")
    assert found["detail"].startswith("invalid YAML: while parsing")


def test_the_index_copy_is_checked_not_the_worktree(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"skills/grill/SKILL.md": "# none\n"})
    write(repo, {"skills/grill/SKILL.md": SKILL, "skills/new/SKILL.md": "# untracked\n"})
    assert report(capsys, "frontmatter") == [
        check("SKILL.md has no frontmatter block", "skills/grill/SKILL.md"),
        {"exit": "1"},
    ]
