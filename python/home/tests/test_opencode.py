"""opencode-jouet, in-process, against real files: the real jouet when it is on PATH, a stand-in otherwise."""

# jouet itself is a local binary, not "hours long, paid, networked" (CODING_STANDARDS 2), so a real
# jouet on PATH answers `jouet skill --format agents-md` for real; tests/stand_in.py stands in for the
# two paths a real jouet cannot be driven into on demand: missing entirely, and failing.

import json
import os
import shutil
import stat
from pathlib import Path

import pytest

from hometools import opencode
from hometools.cli import main

STAND_IN = Path(__file__).with_name("stand_in.py")
REAL_JOUET = shutil.which("jouet")


def hometools(capfd: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    try:
        main(["opencode-jouet"])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def error(err: str) -> str:
    """The Failure event the command ended with."""
    return json.loads(err.splitlines()[-1])["error"]


@pytest.fixture
def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return tmp_path / ".config/opencode/AGENTS.md"


@pytest.fixture
def real_jouet(monkeypatch: pytest.MonkeyPatch) -> None:
    if REAL_JOUET is None:
        pytest.skip("no jouet on PATH")
    monkeypatch.setenv("PATH", str(Path(REAL_JOUET).parent))


@pytest.fixture
def stand_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A `jouet` on PATH driven by $STAND_IN/script.json, ahead of any real jouet."""
    folder = tmp_path / "stand-in"
    folder.mkdir()
    (folder / "jouet").symlink_to(STAND_IN)
    # The stand-in's own shebang (`env -S python3 -I`) still needs a real python3 on PATH to run.
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STAND_IN", str(folder))
    return folder


def answer(folder: Path, call: list[str], reply: dict[str, object]) -> None:
    (folder / "script.json").write_text(json.dumps({json.dumps(call): reply}))


SKILL_CALL = ["jouet", "skill", "--format", "agents-md"]


def test_creates_a_missing_file_with_the_block(
    target: Path, real_jouet: None, capfd: pytest.CaptureFixture[str]
) -> None:
    assert real_jouet is None  # the fixture's only job is putting a real jouet on PATH
    code, out, err = hometools(capfd)
    assert (code, out, err) == (0, "", "")
    written = target.read_text()
    assert written.startswith("<!-- jouet:start -->\n")
    assert written.rstrip("\n").endswith("<!-- jouet:end -->")
    assert written.count("<!-- jouet:start -->") == 1
    assert written.count("<!-- jouet:end -->") == 1


def test_appends_to_existing_content_separated_by_one_blank_line(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("## herdr\n\nhand-written.\n")
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert target.read_text() == ("## herdr\n\nhand-written.\n\n<!-- jouet:start -->\nguidance\n<!-- jouet:end -->\n")


def test_appends_to_an_empty_file_with_no_leading_blank_line(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("")
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert target.read_text() == "<!-- jouet:start -->\nguidance\n<!-- jouet:end -->\n"


def test_replaces_an_existing_block_in_place_keeping_surrounding_content(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("before\n\n<!-- jouet:start -->\nold guidance\n<!-- jouet:end -->\n\nafter\n")
    answer(stand_in, SKILL_CALL, {"stdout": "new guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert target.read_text() == ("before\n\n<!-- jouet:start -->\nnew guidance\n<!-- jouet:end -->\n\nafter\n")


@pytest.mark.parametrize(
    "existing",
    [
        "<!-- jouet:start -->\nonly a start\n",
        "only an end\n<!-- jouet:end -->\n",
        "<!-- jouet:start -->\na\n<!-- jouet:start -->\nb\n<!-- jouet:end -->\n",
        "<!-- jouet:start -->\na\n<!-- jouet:end -->\nb\n<!-- jouet:end -->\n",
        "<!-- jouet:end -->\nbefore the start\n<!-- jouet:start -->\n",
    ],
    ids=["only-start", "only-end", "duplicate-start", "duplicate-end", "end-before-start"],
)
def test_malformed_markers_leave_the_file_untouched(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str], existing: str
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text(existing)
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, out, err = hometools(capfd)
    assert (code, out) == (1, "")
    assert "jouet markers are malformed" in error(err)
    assert target.read_text() == existing


def test_jouet_missing_leaves_the_file_untouched(
    target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, out, err = hometools(capfd)
    assert (code, out) == (1, "")
    assert error(err).startswith("jouet: ")
    assert not target.exists()


def test_jouet_failing_leaves_the_file_untouched(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(stand_in, SKILL_CALL, {"stderr": "jouet: skill agents-md: broken\n", "code": 3})
    code, out, err = hometools(capfd)
    assert (code, out) == (1, "")
    assert error(err) == ("jouet skill --format agents-md exited 3: jouet: skill agents-md: broken")
    assert not target.exists()


def test_unchanged_content_is_not_rewritten(target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("<!-- jouet:start -->\nguidance\n<!-- jouet:end -->\n")
    before = target.stat().st_ino
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert target.stat().st_ino == before


def test_file_mode_is_preserved_across_a_rewrite(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("old\n")
    target.chmod(0o640)
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_no_leftover_temp_file_after_a_successful_run(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert [path.name for path in target.parent.iterdir()] == [target.name]


def test_replaces_a_block_at_end_of_file_with_no_trailing_newline(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    target.parent.mkdir(parents=True)
    target.write_text("before\n\n<!-- jouet:start -->\nold\n<!-- jouet:end -->")
    answer(stand_in, SKILL_CALL, {"stdout": "new\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert target.read_text() == "before\n\n<!-- jouet:start -->\nnew\n<!-- jouet:end -->\n"


def test_xdg_config_home_is_honoured_as_opencode_does(
    target: Path, tmp_path: Path, stand_in: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, _out, err = hometools(capfd)
    assert (code, err) == (0, "")
    assert (xdg / "opencode/AGENTS.md").read_text() == "<!-- jouet:start -->\nguidance\n<!-- jouet:end -->\n"
    assert not target.exists()


def test_a_failed_write_ends_with_one_error_and_leaves_no_temp_file(
    target: Path, stand_in: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    # A folder where the file goes: it reads as a directory, so the read fails before any temp file.
    target.mkdir(parents=True)
    answer(stand_in, SKILL_CALL, {"stdout": "guidance\n"})
    code, out, err = hometools(capfd)
    assert (code, out) == (1, "")
    assert error(err).startswith(f"{target}: ")
    assert list(target.iterdir()) == []
    assert [path.name for path in target.parent.iterdir()] == [target.name]


def test_write_atomic_removes_its_temp_file_when_the_rename_fails(tmp_path: Path) -> None:
    # Renaming a file onto a non-empty folder fails for real (EISDIR/ENOTEMPTY).
    folder = tmp_path / "AGENTS.md"
    (folder / "inside").mkdir(parents=True)
    with pytest.raises(OSError, match=r"AGENTS\.md"):
        opencode.write_atomic(folder, "guidance\n")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["AGENTS.md"]
