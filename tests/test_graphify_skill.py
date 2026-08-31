# Copyright (c) 2026 Raymond Manaloto
"""Tests for the repo-owned graphify skill installer (`dotfiles_setup.graphify_skill`).

`graphify.install` itself is never patched to *run* — this module never calls
any of its install functions. What IS patched, at the module boundary, is the
read-only source of truth it reads: `_PLATFORM_CONFIG` plus the package root
`__file__` resolves from, so tests are hermetic and do not depend on whatever
graphify version happens to be pinned when they run (`tests/AGENTS.md`:
"mock at system boundaries only").

Every "confined to project_dir" claim is control-armed: a fixture also plants
an AGENTS.md and a `.claude/CLAUDE.md` in the target tree, and each install
test asserts their bytes are UNCHANGED — the whole reason this module can
exist where `graphify install` cannot (do-not.md #8).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import graphify_skill


@pytest.fixture
def fake_package(tmp_path: Path) -> Path:
    """A synthetic graphify package: skill files + one references bundle."""
    pkg = tmp_path / "fake_graphify_pkg"
    pkg.mkdir()
    (pkg / "skill.md").write_text("claude bundle body", encoding="utf-8")
    (pkg / "skill-codex.md").write_text("codex bundle body", encoding="utf-8")
    (pkg / "skill-agents.md").write_text("agents bundle body", encoding="utf-8")
    refs = pkg / "skills" / "claude" / "references"
    refs.mkdir(parents=True)
    (refs / "one.md").write_text("reference one", encoding="utf-8")
    return pkg


@pytest.fixture
def patched_graphify(
    monkeypatch: pytest.MonkeyPatch, fake_package: Path
) -> types.SimpleNamespace:
    """Point `graphify_skill._graphify_install` at the synthetic package above."""
    cfg = {
        "claude": {
            "skill_file": "skill.md",
            "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
            "skill_refs": "claude",
        },
        "codex": {
            "skill_file": "skill-codex.md",
            "skill_dst": Path(".codex") / "skills" / "graphify" / "SKILL.md",
            # No skill_refs -> monolith, matches graphify's real codex entry.
        },
        "agents": {
            "skill_file": "skill-agents.md",
            "skill_dst": Path(".agents") / "skills" / "graphify" / "SKILL.md",
        },
    }
    fake = types.SimpleNamespace(
        __file__=str(fake_package / "install.py"), _PLATFORM_CONFIG=cfg
    )
    monkeypatch.setattr(graphify_skill, "_graphify_install", fake)
    return fake


def _plant_governed_files(project_dir: Path) -> dict[str, str]:
    """Files an install must never touch — the control arm for confinement."""
    agents_md = project_dir / "AGENTS.md"
    agents_md.write_text("original AGENTS.md content\n", encoding="utf-8")
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("@AGENTS.md\n", encoding="utf-8")
    return {
        str(agents_md): agents_md.read_text(encoding="utf-8"),
        str(claude_md): claude_md.read_text(encoding="utf-8"),
    }


def _assert_governed_files_untouched(before: dict[str, str]) -> None:
    for path_str, content in before.items():
        assert Path(path_str).read_text(encoding="utf-8") == content, (
            f"{path_str} changed — the installer touched something outside "
            f"its own skill_dst.parent"
        )


# --------------------------------------------------------------------------- #
# known_platforms / resolve_placement
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("patched_graphify")
def test_known_platforms_reads_from_the_installed_packages_table() -> None:
    assert graphify_skill.known_platforms() == ("agents", "claude", "codex")


def test_known_platforms_raises_when_graphify_is_not_importable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(graphify_skill, "_graphify_install", None)
    monkeypatch.setattr(graphify_skill, "_IMPORT_ERROR", ImportError("boom"))
    with pytest.raises(ModuleNotFoundError):
        graphify_skill.known_platforms()


@pytest.mark.usefixtures("patched_graphify")
def test_resolve_placement_computes_the_project_relative_destination(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    placement = graphify_skill.resolve_placement("codex", project_dir=project_dir)
    assert (
        placement.skill_dst
        == project_dir / ".codex" / "skills" / "graphify" / "SKILL.md"
    )
    assert placement.skill_src.name == "skill-codex.md"
    # codex has no skill_refs in the fixture, matching graphify's real entry.
    assert placement.refs_src is None


@pytest.mark.usefixtures("patched_graphify")
def test_resolve_placement_finds_the_references_sidecar_when_declared(
    tmp_path: Path,
) -> None:
    placement = graphify_skill.resolve_placement("claude", project_dir=tmp_path)
    assert placement.refs_src is not None
    assert placement.refs_src.is_dir()
    assert (placement.refs_src / "one.md").is_file()


@pytest.mark.usefixtures("patched_graphify")
def test_resolve_placement_raises_on_an_unknown_platform(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        graphify_skill.resolve_placement("not-a-real-platform", project_dir=tmp_path)


# --------------------------------------------------------------------------- #
# install_skill
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_writes_skill_and_version_stamp(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    before = _plant_governed_files(project_dir)

    dst = graphify_skill.install_skill("codex", project_dir=project_dir)

    assert dst == project_dir / ".codex" / "skills" / "graphify" / "SKILL.md"
    assert dst.read_text(encoding="utf-8") == "codex bundle body"
    stamp = dst.parent / ".graphify_version"
    assert stamp.is_file()
    _assert_governed_files_untouched(before)


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_installs_the_references_sidecar_for_a_progressive_platform(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    dst = graphify_skill.install_skill("claude", project_dir=project_dir)

    refs = dst.parent / "references"
    assert (refs / "one.md").read_text(encoding="utf-8") == "reference one"


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_writes_nothing_outside_its_own_skill_dir(
    tmp_path: Path,
) -> None:
    """The confinement claim, proven by enumeration rather than by absence."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    before = _plant_governed_files(project_dir)

    graphify_skill.install_skill("agents", project_dir=project_dir)

    written = {
        p.relative_to(project_dir) for p in project_dir.rglob("*") if p.is_file()
    }
    expected_new = {
        Path("AGENTS.md"),
        Path(".claude") / "CLAUDE.md",
        Path(".agents") / "skills" / "graphify" / "SKILL.md",
        Path(".agents") / "skills" / "graphify" / ".graphify_version",
    }
    assert written == expected_new
    _assert_governed_files_untouched(before)


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_backs_up_a_differing_existing_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    dst = project_dir / ".codex" / "skills" / "graphify" / "SKILL.md"
    dst.parent.mkdir(parents=True)
    dst.write_text("a hand-edited local copy", encoding="utf-8")

    graphify_skill.install_skill("codex", project_dir=project_dir)

    backup = dst.parent / "SKILL.md.bak"
    assert backup.read_text(encoding="utf-8") == "a hand-edited local copy"
    assert dst.read_text(encoding="utf-8") == "codex bundle body"


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_does_not_back_up_an_identical_existing_file(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    dst = project_dir / ".codex" / "skills" / "graphify" / "SKILL.md"
    dst.parent.mkdir(parents=True)
    dst.write_text("codex bundle body", encoding="utf-8")

    graphify_skill.install_skill("codex", project_dir=project_dir)

    assert not (dst.parent / "SKILL.md.bak").exists()


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_raises_on_an_unknown_platform(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        graphify_skill.install_skill("not-a-real-platform", project_dir=tmp_path)


@pytest.mark.usefixtures("patched_graphify")
def test_install_skill_raises_when_the_packaged_source_is_missing(
    tmp_path: Path, fake_package: Path
) -> None:
    (fake_package / "skill-codex.md").unlink()
    with pytest.raises(FileNotFoundError):
        graphify_skill.install_skill("codex", project_dir=tmp_path)


# --------------------------------------------------------------------------- #
# graphify_skill_install_main (CLI layer)
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("patched_graphify")
def test_main_defaults_project_dir_to_project_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = graphify_skill.graphify_skill_install_main(tmp_path, platform="codex")
    assert rc == 0
    assert (tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md").is_file()
    assert "graphify skill installed ->" in capsys.readouterr().out


@pytest.mark.usefixtures("patched_graphify")
def test_main_honors_an_explicit_project_dir(tmp_path: Path) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    rc = graphify_skill.graphify_skill_install_main(
        tmp_path, platform="codex", project_dir=other
    )
    assert rc == 0
    assert (other / ".codex" / "skills" / "graphify" / "SKILL.md").is_file()
    assert not (tmp_path / ".codex").exists()


@pytest.mark.usefixtures("patched_graphify")
def test_main_reports_an_unknown_platform_and_lists_the_known_ones(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = graphify_skill.graphify_skill_install_main(
        tmp_path, platform="not-a-real-platform"
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "not-a-real-platform" in err
    assert "claude" in err  # one of the known platforms is named in the error


def test_main_reports_a_missing_graphify_import(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(graphify_skill, "_graphify_install", None)
    monkeypatch.setattr(graphify_skill, "_IMPORT_ERROR", ImportError("boom"))
    rc = graphify_skill.graphify_skill_install_main(tmp_path, platform="claude")
    assert rc == 1
    assert "graphify" in capsys.readouterr().err
