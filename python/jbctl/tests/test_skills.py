"""skills: bundled skills copied out of a stand-in Toolbox install's jars, into a stand-in home folder."""

import hashlib
import json
import os
import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from .conftest import install, launcher, product_info, run

DEBUGGER = {
    "SKILL.md": "---\nname: fake-debugger\n---\nDebug with the fake IDE.\n",
    "metadata.json": '{"version": "1.0.0"}',
    "reference/tools.md": "The tools.\n",
}


def jar(app: Path, name: str, entries: dict[str, str]) -> Path:
    """A plugin jar in the app, in the layout the IDEs ship (plugins/<plugin>/lib/modules/<module>.jar)."""
    path = app / "Contents/plugins/air-plugin/lib/modules" / f"{name}.jar"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for entry, text in entries.items():
            archive.writestr(entry, text)
    return path


def bundled(name: str, files: dict[str, str], prefix: str = "bundledSkills/") -> dict[str, str]:
    return {f"{prefix}{name}/{path}": text for path, text in files.items()}


@pytest.fixture
def home(toolbox: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The home folder skills writes to, and fake.app shipping fake-debugger, as the IDEs ship clion-debugger."""
    folder = toolbox / "home"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    jar(toolbox / "fake.app", "contrib", {"META-INF/MANIFEST.MF": "", **bundled("fake-debugger", DEBUGGER)})
    return folder


def tree(folder: Path) -> dict[str, str]:
    """A folder's files and their text, the marker left out."""
    files = (path for path in folder.rglob("*") if path.is_file() and path.name != ".jbctl-skill.json")
    return {path.relative_to(folder).as_posix(): path.read_text() for path in files}


def copy(home: Path, agent: str, state: str, **extra: str) -> dict[str, str]:
    """The event skills prints for fake-debugger from the install fake."""
    path = home / (".agents" if agent == "codex" else ".claude") / "skills/fake-debugger"
    event = {"skill": "fake-debugger", "agent": agent, "state": state, "path": str(path), "install": "fake"}
    return {**event, "build": "263.1.2", "version": "1.0.0", **extra}


def test_copies_a_bundled_skill_for_codex_and_links_it_for_claude(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    code, events, error = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    assert (code, error) == (0, "")
    assert events == [{"skill": copy(home, "codex", "copied")}, {"skill": copy(home, "claude", "copied")}]
    folder = home / ".agents/skills/fake-debugger"
    assert tree(folder) == DEBUGGER
    link = home / ".claude/skills/fake-debugger"
    # Relative, as `skills add -g` links the skills it installs.
    assert link.readlink() == Path("../../.agents/skills/fake-debugger")
    assert link.resolve() == folder.resolve()
    marker = json.loads((folder / ".jbctl-skill.json").read_text())
    assert (marker["install"], marker["build"], marker["version"]) == ("fake", "263.1.2", "1.0.0")
    assert sorted(marker["files"]) == sorted(DEBUGGER)


def test_a_second_run_finds_both_copies_current(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    folder = home / ".agents/skills/fake-debugger"
    written = (folder / "SKILL.md").stat().st_mtime_ns
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (
        0,
        [{"skill": copy(home, "codex", "unchanged")}, {"skill": copy(home, "claude", "unchanged")}],
        "",
    )
    assert (folder / "SKILL.md").stat().st_mtime_ns == written


def test_an_updated_ide_updates_an_unchanged_copy(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    # The IDE updated: the skill's text changed, a file went, and its version moved on.
    newer = {"SKILL.md": "---\nname: fake-debugger\n---\nDebug better.\n", "metadata.json": '{"version": "1.1.0"}'}
    jar(home.parent / "fake.app", "contrib", bundled("fake-debugger", newer))
    expected = {"version": "1.1.0", "previous_version": "1.0.0"}
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (
        0,
        [{"skill": copy(home, "codex", "updated", **expected)}, {"skill": copy(home, "claude", "updated", **expected)}],
        "",
    )
    assert tree(home / ".claude/skills/fake-debugger") == newer
    assert [path.name for path in (home / ".agents/skills").iterdir()] == ["fake-debugger"]


def test_a_changed_copy_is_left_alone(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    folder = home / ".agents/skills/fake-debugger"
    (folder / "SKILL.md").write_text("My own notes.\n")
    (folder / "reference/tools.md").unlink()
    (folder / "notes.md").write_text("Mine.\n")
    reason = "changed since jbctl wrote it: SKILL.md, notes.md, reference/tools.md"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (
        1,
        [
            {"skill": copy(home, "codex", "modified", reason=reason)},
            {"skill": copy(home, "claude", "modified", reason=reason)},
        ],
        "",
    )
    assert tree(folder) == {
        "SKILL.md": "My own notes.\n",
        "metadata.json": DEBUGGER["metadata.json"],
        "notes.md": "Mine.\n",
    }


def test_check_writes_nothing_and_fails_until_the_copies_are_current(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    check = ("skills", "--ide", "fake", "--skill", "fake-debugger", "--check")
    assert run(capsys, *check) == (
        1,
        [{"skill": copy(home, "codex", "copied")}, {"skill": copy(home, "claude", "copied")}],
        "",
    )
    assert list(home.iterdir()) == []
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    assert run(capsys, *check) == (
        0,
        [{"skill": copy(home, "codex", "unchanged")}, {"skill": copy(home, "claude", "unchanged")}],
        "",
    )


def test_an_unknown_skill_fails_with_the_skills_the_install_ships(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    # A Rider-style skill at the jar's root, and a SKILL.md deeper down that is not a bundled skill.
    jar(home.parent / "fake.app", "rider", {"fake-tests/SKILL.md": "", "docs/guide/fake/SKILL.md": ""})
    error = "fake ships no bundled skill named nope; it ships fake-debugger, fake-tests"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "nope") == (1, [], error)
    assert list(home.iterdir()) == []


def test_a_skill_in_two_places_fails_without_guessing(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    other = jar(home.parent / "fake.app", "rider", {"fake-debugger/SKILL.md": ""})
    contrib = other.with_name("contrib.jar")
    error = f"fake ships fake-debugger in 2 places: {contrib}!bundledSkills/fake-debugger, {other}!fake-debugger"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (1, [], error)
    assert list(home.iterdir()) == []


def test_copies_several_skills_and_one_at_a_jar_root_without_a_version(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    jar(home.parent / "fake.app", "rider", bundled("fake-tests", {"SKILL.md": "Find tests.\n"}, prefix=""))
    code, events, _ = run(capsys, "skills", "--ide", "fake", "--skill", "fake-tests", "--skill", "fake-debugger")
    tests = {"skill": "fake-tests", "install": "fake", "build": "263.1.2", "state": "copied"}
    assert (code, events[:2]) == (
        0,
        [
            {"skill": {**tests, "agent": "codex", "path": str(home / ".agents/skills/fake-tests")}},
            {"skill": {**tests, "agent": "claude", "path": str(home / ".claude/skills/fake-tests")}},
        ],
    )
    assert [event["skill"]["skill"] for event in events[2:]] == ["fake-debugger", "fake-debugger"]
    assert tree(home / ".claude/skills/fake-tests") == {"SKILL.md": "Find tests.\n"}


@pytest.mark.parametrize(
    ("picks", "error"),
    [
        ((), "skills needs --ide or --product"),
        (("--ide", "fake", "--product", "Fake"), "skills takes --ide or --product, not both"),
        # Both installs of the product could supply the skill, and skills does not ask which one runs.
        (("--product", "Fake"), "Fake has 2 installs (fake, fake1); pick one with --ide"),
        (("--product", "Nope"), "Toolbox has no IDE with tool id Nope; its tool ids are Fake"),
    ],
)
def test_one_install_must_be_named(
    capsys: pytest.CaptureFixture[str], home: Path, picks: tuple[str, ...], error: str
) -> None:
    assert run(capsys, "skills", *picks, "--skill", "fake-debugger") == (1, [], error)
    assert list(home.iterdir()) == []


def test_all_is_not_an_option(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    code, events, error = run(capsys, "skills", "--all", "--skill", "fake-debugger")
    assert (code, events, list(home.iterdir())) == (1, [], [])
    assert "all" in error


def test_a_product_with_one_install_names_it(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    toolbox = home.parent
    app = toolbox / "solo.app"
    for folder in ("Resources", "MacOS", "bin", "plugins/station-plugin"):
        (app / "Contents" / folder).mkdir(parents=True)
    (app / "Contents/bin/fake.vmoptions").write_text("")
    product_info(app)
    launcher(app)
    install(toolbox / "toolbox", "solo", app, "solo", tool_id="Solo")
    jar(app, "contrib", bundled("fake-debugger", DEBUGGER))
    code, events, _ = run(capsys, "skills", "--product", "Solo", "--skill", "fake-debugger")
    assert (code, [event["skill"]["install"] for event in events]) == (0, ["solo", "solo"])


def symlink(path: Path, target: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)


def folder(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("Someone else's.\n")


NEEDS = "needs jbctl's copy in {home}/.agents/skills, which it does not have"
NOT_JBCTL = "not written by jbctl"


@pytest.mark.parametrize(
    ("setup", "codex", "claude"),
    [
        # A skill linked into ~/.agents/skills from a repository, as macos-agent-permissions is.
        (
            lambda home: symlink(home / ".agents/skills/fake-debugger", home / "repo/fake-debugger"),
            ("unmanaged", "a symlink to {home}/repo/fake-debugger, not jbctl's copy"),
            ("unmanaged", NEEDS),
        ),
        (lambda home: folder(home / ".agents/skills/fake-debugger"), ("unmanaged", NOT_JBCTL), ("unmanaged", NEEDS)),
        (
            lambda home: (
                (home / ".agents/skills").mkdir(parents=True) or (home / ".agents/skills/fake-debugger").touch()
            ),
            ("unmanaged", NOT_JBCTL),
            ("unmanaged", NEEDS),
        ),
        # Codex reads ~/.codex/skills too, and would find two skills of one name.
        (
            lambda home: folder(home / ".codex/skills/fake-debugger"),
            ("unmanaged", "Codex would also find {home}/.codex/skills/fake-debugger"),
            ("unmanaged", NEEDS),
        ),
        (lambda home: folder(home / ".claude/skills/fake-debugger"), ("copied", None), ("unmanaged", NOT_JBCTL)),
        (
            lambda home: symlink(home / ".claude/skills/fake-debugger", home / "repo/fake-debugger"),
            ("copied", None),
            ("unmanaged", "a symlink to {home}/repo/fake-debugger, not to jbctl's copy"),
        ),
    ],
    ids=["agents-symlink", "agents-folder", "agents-file", "codex-skills", "claude-folder", "claude-symlink"],
)
def test_a_path_someone_else_owns_is_left_alone(
    capsys: pytest.CaptureFixture[str],
    home: Path,
    setup: Callable[[Path], None],
    codex: tuple[str, str | None],
    claude: tuple[str, str | None],
) -> None:
    setup(home)
    before = sorted(str(path) for path in home.rglob("*"))
    events = []
    for agent, (state, reason) in (("codex", codex), ("claude", claude)):
        extra = {"reason": reason.format(home=home)} if reason else {}
        events.append({"skill": copy(home, agent, state, **extra)})
    for check in (("--check",), ()):
        assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger", *check)[:2] == (1, events)
    if codex[0] == "unmanaged":
        assert sorted(str(path) for path in home.rglob("*")) == before


def test_a_copy_deleted_by_hand_is_copied_again(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    shutil.rmtree(home / ".agents/skills/fake-debugger")
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (
        0,
        [{"skill": copy(home, "codex", "copied")}, {"skill": copy(home, "claude", "copied")}],
        "",
    )
    assert tree(home / ".claude/skills/fake-debugger") == DEBUGGER


def old_copy(home: Path, files: dict[str, str]) -> Path:
    """A copy the earlier clion:skills task wrote into ~/.claude/skills, with its marker."""
    folder = home / ".claude/skills/fake-debugger"
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    hashes = {path: hashlib.sha256(text.encode()).hexdigest() for path, text in files.items()}
    marker = {"jar": "/old/contrib.jar", "version": "0.9.0", "hash": "sha256:0", "files": hashes}
    (folder / ".dotfiles-clion-skills.json").write_text(json.dumps(marker))
    return folder


def test_an_unchanged_copy_from_the_old_task_is_adopted(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    old = old_copy(home, {**DEBUGGER, "SKILL.md": "The old text.\n"})
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (
        0,
        [{"skill": copy(home, "codex", "copied")}, {"skill": copy(home, "claude", "adopted")}],
        "",
    )
    assert old.is_symlink()
    assert tree(old) == DEBUGGER
    assert sorted(path.name for path in (home / ".claude/skills").iterdir()) == ["fake-debugger"]


def test_a_changed_copy_from_the_old_task_is_left_alone(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    old = old_copy(home, DEBUGGER)
    (old / "SKILL.md").write_text("My own notes.\n")
    reason = "changed since the clion:skills task wrote it: SKILL.md"
    for check in (("--check",), ()):
        assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger", *check)[:2] == (
            1,
            [{"skill": copy(home, "codex", "copied")}, {"skill": copy(home, "claude", "modified", reason=reason)}],
        )
    assert not old.is_symlink()
    assert (old / "SKILL.md").read_text() == "My own notes.\n"


def leftover(path: Path, entry: Callable[[Path], object] | None = None) -> Path:
    """A folder as a killed run leaves it: marked as jbctl's, holding the skill's entry (or nothing)."""
    path.mkdir(parents=True)
    (path / ".jbctl-leftover").touch()
    if entry:
        entry(path / "fake-debugger")
    return path


def own_copy(path: Path, files: dict[str, str] = DEBUGGER) -> None:
    """A copy as jbctl writes it: the files and a .jbctl-skill.json that records them."""
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}
    marker = {"install": "fake", "build": "263.1.2", "jar": "/fake.jar", "files": hashes}
    (path / ".jbctl-skill.json").write_text(json.dumps(marker))


def test_a_run_clears_what_a_killed_run_left_behind(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    agents, claude = home / ".agents/skills", home / ".claude/skills"
    # Only what holds nothing anyone changed: an empty staging folder, a staged link, a copy that matches its marker.
    left = [
        leftover(agents / ".fake-debugger.jbctl-a1b2c3d4"),
        # The link as jbctl stages it for Claude, relative to ~/.claude/skills.
        leftover(
            claude / ".fake-debugger.jbctl-e5f6g7h8", lambda path: path.symlink_to("../../.agents/skills/fake-debugger")
        ),
        leftover(agents / ".fake-debugger.jbctl-i9j0k1l2", own_copy),
    ]
    # Kept, and each reported: it may hold someone's work.
    reported = {
        # A copy swapped out by a run killed before it was checked, and edited since.
        leftover(
            agents / ".fake-debugger.jbctl-m3n4o5p6",
            lambda path: own_copy(path) or (path / "SKILL.md").write_text("Mine.\n"),
        ): "holds a copy changed since its marker was written: SKILL.md",
        leftover(agents / ".fake-debugger.jbctl-q7r8s9t0", folder): "holds a folder with no marker",
        leftover(
            claude / ".fake-debugger.jbctl-u1v2w3x4", lambda path: path.symlink_to("../elsewhere")
        ): "holds a symlink jbctl did not stage",
        leftover(
            agents / ".fake-debugger.jbctl-y5z6a7b8",
            lambda path: own_copy(path) or (path / ".jbctl-skill.json").write_text("not json"),
        ): "holds a copy whose .jbctl-skill.json does not parse",
        leftover(
            agents / ".fake-debugger.jbctl-c9d0e1f2", lambda path: (path.parent / "notes.md").touch()
        ): "holds notes.md, which jbctl did not put there",
    }
    # Not jbctl's to report: another skill's leftover, a folder of the user's own, and one named like a leftover
    # that jbctl did not mark.
    kept = [
        leftover(agents / ".other.jbctl-a1b2c3d4"),
        claude / ".fake-debugger-notes",
        agents / ".fake-debugger.jbctl-backup",
        agents / ".fake-debugger.jbctl-g3h4i5j6",  # marked as jbctl's only by a symlink to a marker file
    ]
    (agents / "marker").touch()
    agents_marked = kept[-1]
    agents_marked.mkdir()
    (agents_marked / ".jbctl-leftover").symlink_to(agents / "marker")
    for path in kept[-3:-1]:
        folder(path / "fake-debugger")
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger", "--check")
    assert all(path.exists() for path in [*left, *reported, *kept])
    code, events, _ = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    assert code == 0
    assert sorted((event["leftover"]["path"], event["leftover"]["reason"]) for event in events[2:]) == sorted(
        (str(path), reason) for path, reason in reported.items()
    )
    assert [path.exists() for path in [*left, *reported, *kept]] == [False] * len(left) + [True] * (
        len(reported) + len(kept)
    )


def test_a_jar_entry_that_leaves_the_skill_folder_fails(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    entries = bundled("fake-debugger", {**DEBUGGER, "../../../../escaped.md": "Out.\n"})
    contrib = jar(home.parent / "fake.app", "contrib", entries)
    error = f"{contrib}!bundledSkills/fake-debugger/../../../../escaped.md leaves the skill's folder"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (1, [], error)
    assert (list(home.iterdir()), (home.parent / "escaped.md").exists()) == ([], False)


def test_a_version_with_quotes_and_a_newline_stays_one_json_value(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    hostile = '1.0" , "state": "unchanged"\n{"x": 1}'
    metadata = json.dumps({"version": hostile})
    jar(home.parent / "fake.app", "contrib", bundled("fake-debugger", {**DEBUGGER, "metadata.json": metadata}))
    code, events, _ = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    # run() parses each stdout line as JSON: two lines, two events, each with the version as one string.
    assert (code, [(event["skill"]["state"], event["skill"]["version"]) for event in events]) == (
        0,
        [("copied", hostile), ("copied", hostile)],
    )
    marker = json.loads((home / ".agents/skills/fake-debugger/.jbctl-skill.json").read_text())
    assert marker["version"] == hostile


def marker_behind_a_symlink(copy: Path) -> None:
    (copy.parent / "marker.json").write_bytes((copy / ".jbctl-skill.json").read_bytes())
    (copy / ".jbctl-skill.json").unlink()
    (copy / ".jbctl-skill.json").symlink_to(copy.parent / "marker.json")


@pytest.mark.parametrize(
    ("change", "what"),
    [
        # The same bytes, but a symlink: an update would delete the user's link.
        (
            lambda copy: (
                (copy / "reference/tools.md").unlink()
                or (copy / "reference/tools.md").symlink_to(copy.parent / "tools.md")
            ),
            "reference/tools.md",
        ),
        (lambda copy: (copy / "extra").mkdir(), "extra"),
        (lambda copy: os.mkfifo(copy / "pipe"), "pipe"),
        # jbctl's own marker, as the same JSON behind a symlink; and the old task's marker name, added.
        (
            marker_behind_a_symlink,
            ".jbctl-skill.json",
        ),
        (lambda copy: (copy / ".dotfiles-clion-skills.json").write_text("{}"), ".dotfiles-clion-skills.json"),
    ],
    ids=[
        "file-replaced-by-symlink",
        "empty-folder-added",
        "fifo-added",
        "marker-replaced-by-symlink",
        "old-marker-added",
    ],
)
def test_an_entry_the_user_added_counts_as_a_change(
    capsys: pytest.CaptureFixture[str], home: Path, change: Callable[[Path], None], what: str
) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    copy_folder = home / ".agents/skills/fake-debugger"
    (copy_folder.parent / "tools.md").write_text(DEBUGGER["reference/tools.md"])
    change(copy_folder)
    jar(home.parent / "fake.app", "contrib", bundled("fake-debugger", {**DEBUGGER, "SKILL.md": "Newer.\n"}))
    reason = f"changed since jbctl wrote it: {what}"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")[:2] == (
        1,
        [
            {"skill": copy(home, "codex", "modified", reason=reason)},
            {"skill": copy(home, "claude", "modified", reason=reason)},
        ],
    )
    assert (copy_folder / what).exists() or (copy_folder / what).is_symlink()


def test_a_symlinked_skills_folder_is_left_alone(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    # ~/.agents/skills pointing into ~/.codex/skills would put the copy where Codex reads it twice.
    (home / ".codex/skills").mkdir(parents=True)
    symlink(home / ".agents/skills", home / ".codex/skills")
    symlink(home / ".claude/skills", home / "synced/skills")
    (home / "synced/skills").mkdir(parents=True)
    # Marked leftovers in the targets: jbctl clears leftovers only in skill folders that are where they seem.
    targets = [
        leftover(home / ".codex/skills/.fake-debugger.jbctl-a1b2c3d4"),
        leftover(home / "synced/skills/.fake-debugger.jbctl-e5f6g7h8"),
    ]
    agents = f"{home}/.agents/skills resolves to {home}/.codex/skills"
    claude = f"{home}/.claude/skills resolves to {home}/synced/skills"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")[:2] == (
        1,
        [
            {"skill": copy(home, "codex", "unmanaged", reason=agents)},
            {"skill": copy(home, "claude", "unmanaged", reason=claude)},
        ],
    )
    assert (list((home / ".codex/skills").iterdir()), list((home / "synced/skills").iterdir())) == (
        targets[:1],
        targets[1:],
    )


def test_a_jar_file_named_like_a_marker_fails_at_the_root_and_is_copied_deeper(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    nested = {**DEBUGGER, "reference/.jbctl-skill.json": "{}", "reference/.dotfiles-clion-skills.json": "{}"}
    jar(home.parent / "fake.app", "contrib", bundled("fake-debugger", nested))
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")[0] == 0
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")[:2] == (
        0,
        [{"skill": copy(home, "codex", "unchanged")}, {"skill": copy(home, "claude", "unchanged")}],
    )
    contrib = jar(
        home.parent / "fake.app", "contrib", bundled("fake-debugger", {**DEBUGGER, ".jbctl-skill.json": "{}"})
    )
    error = f"{contrib}!bundledSkills/fake-debugger/.jbctl-skill.json has a name jbctl keeps for its own files"
    assert run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger") == (1, [], error)


def test_a_damaged_marker_is_not_jbctls_and_the_run_goes_on(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    jar(home.parent / "fake.app", "rider", bundled("fake-tests", {"SKILL.md": "Find tests.\n"}, prefix=""))
    folder(home / ".agents/skills/fake-debugger")
    (home / ".agents/skills/fake-debugger/.jbctl-skill.json").write_text("not json")
    old = old_copy(home, DEBUGGER)
    (old / ".dotfiles-clion-skills.json").write_text('{"files": 3}')
    code, events, error = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger", "--skill", "fake-tests")
    assert (code, error, events[:2]) == (
        1,
        "",
        [
            {"skill": copy(home, "codex", "unmanaged", reason="its .jbctl-skill.json is not one jbctl wrote")},
            {
                "skill": copy(
                    home,
                    "claude",
                    "unmanaged",
                    reason="its .dotfiles-clion-skills.json is not one the clion:skills task wrote",
                )
            },
        ],
    )
    assert [event["skill"]["state"] for event in events[2:]] == ["copied", "copied"]


def test_a_copy_jbctl_cannot_read_fails_the_run_and_stays(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    jar(home.parent / "fake.app", "contrib", bundled("fake-debugger", {**DEBUGGER, "SKILL.md": "Newer.\n"}))
    unreadable = home / ".agents/skills/fake-debugger/SKILL.md"
    unreadable.chmod(0)
    try:
        code, events, error = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger")
    finally:
        unreadable.chmod(0o644)
    assert (code, events, "Permission denied" in error) == (1, [], True)
    assert tree(home / ".agents/skills/fake-debugger") == DEBUGGER
    assert [path.name for path in (home / ".agents/skills").iterdir()] == ["fake-debugger"]


def test_a_marker_that_is_not_utf8_is_not_jbctls(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    jar(home.parent / "fake.app", "rider", bundled("fake-tests", {"SKILL.md": "Find tests.\n"}, prefix=""))
    folder(home / ".agents/skills/fake-debugger")
    (home / ".agents/skills/fake-debugger/.jbctl-skill.json").write_bytes(bytes([255]))
    code, events, error = run(capsys, "skills", "--ide", "fake", "--skill", "fake-debugger", "--skill", "fake-tests")
    assert (code, error, [event["skill"]["state"] for event in events]) == (
        1,
        "",
        ["unmanaged", "unmanaged", "copied", "copied"],
    )
    assert events[0]["skill"]["reason"] == "its .jbctl-skill.json is not one jbctl wrote"
