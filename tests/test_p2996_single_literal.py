# Copyright (c) 2026 Raymond Manaloto
"""Gate the single clang-p2996 SHA literal and its Renovate ownership."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.p2996_hash import _extract_bake_variable

REPO_ROOT = Path(__file__).parent.parent.absolute()


def _bake_ref() -> str:
    ref = _extract_bake_variable(
        (REPO_ROOT / "docker-bake.hcl").read_text(), "CLANG_P2996_REF"
    )
    assert re.fullmatch(r"[0-9a-f]{40}", ref)
    return ref


def _clang_manager() -> dict:
    config = json.loads((REPO_ROOT / "renovate.json").read_text())
    matches = [
        manager
        for manager in config["customManagers"]
        if manager.get("depNameTemplate") == "bloomberg/clang-p2996"
    ]
    assert len(matches) == 1
    return matches[0]


def _py_pattern(match_string: str) -> re.Pattern[str]:
    """Compile a Python-re proxy for Renovate's per-file RE2 expression.

    Python validates the extraction shape only. The lint gate's
    renovate_config_validate step separately proves that RE2 accepts it.
    """
    translated = re.sub(r"\(\?<([A-Za-z_]\w*)>", r"(?P<\1>", match_string)
    return re.compile(translated)


def _tracked_nondoc_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked: list[str] = []
    for relative in result.stdout.split("\0"):
        if (
            not relative
            or relative.startswith(("docs/", "graphify-out/"))
            or relative.endswith(".md")
        ):
            continue
        try:
            (REPO_ROOT / relative).read_text(errors="ignore")
        except OSError:
            continue
        tracked.append(relative)
    return tracked


def test_bake_default_is_the_only_tracked_copy_of_the_sha() -> None:
    ref = _bake_ref()
    matches = [
        relative
        for relative in _tracked_nondoc_files()
        if ref in (REPO_ROOT / relative).read_text(errors="ignore")
    ]
    assert matches == ["docker-bake.hcl"]


def test_no_file_assigns_a_sha_literal_to_clang_p2996_ref() -> None:
    assignment = re.compile(r'CLANG_P2996_REF\s*[=:]\s*"?[0-9a-f]{40}')
    matches = [
        relative
        for relative in _tracked_nondoc_files()
        if assignment.search((REPO_ROOT / relative).read_text(errors="ignore"))
    ]
    assert matches == []


def test_dockerfile_arg_has_no_default() -> None:
    dockerfile = (REPO_ROOT / ".devcontainer" / "Dockerfile").read_text()
    declarations = re.findall(r"^ARG CLANG_P2996_REF\b.*$", dockerfile, re.MULTILINE)
    assert declarations == ["ARG CLANG_P2996_REF"]


def test_renovate_extracts_exactly_the_bake_pin() -> None:
    manager = _clang_manager()
    assert len(manager["matchStrings"]) == 1
    pattern = _py_pattern(manager["matchStrings"][0])
    matches = list(pattern.finditer((REPO_ROOT / "docker-bake.hcl").read_text()))
    assert len(matches) == 1
    assert matches[0].group("currentDigest") == _bake_ref()


def test_renovate_matchstring_rejects_arg_forwarding_and_dockerfile() -> None:
    pattern = _py_pattern(_clang_manager()["matchStrings"][0])
    assert pattern.findall("CLANG_P2996_REF = CLANG_P2996_REF") == []
    dockerfile = (REPO_ROOT / ".devcontainer" / "Dockerfile").read_text()
    assert pattern.findall(dockerfile) == []


def test_renovate_matchstring_tolerates_one_line_and_reflowed_blocks() -> None:
    pattern = _py_pattern(_clang_manager()["matchStrings"][0])
    digest = "a" * 40
    one_line = f'variable "CLANG_P2996_REF" {{ default = "{digest}" }}'
    reflowed = f'variable "CLANG_P2996_REF"\t{{\n\n\tdefault\t=\t"{digest}"\n}}'
    assert len(pattern.findall(one_line)) == 1
    assert len(pattern.findall(reflowed)) == 1


def test_renovate_manager_scoped_to_bake_only() -> None:
    manager = _clang_manager()
    assert manager["managerFilePatterns"] == [r"/(^|/)docker-bake\.hcl$/"]
    assert manager["datasourceTemplate"] == "git-refs"
    assert manager["currentValueTemplate"] == "p2996"


def test_clang_package_rule_leaves_the_image_group_after_it() -> None:
    config = json.loads((REPO_ROOT / "renovate.json").read_text())
    rules = config["packageRules"]
    image_index = next(
        index
        for index, rule in enumerate(rules)
        if rule.get("groupName") == "image-build inputs"
    )
    digest_index = next(
        index
        for index, rule in enumerate(rules)
        if rule.get("matchUpdateTypes") == ["minor", "patch", "digest"]
    )
    clang_index = next(
        index
        for index, rule in enumerate(rules)
        if rule.get("matchDepNames") == ["bloomberg/clang-p2996"]
    )
    rule = rules[clang_index]
    assert clang_index > image_index
    assert clang_index > digest_index
    assert "groupName" in rule
    assert rule["groupName"] is None
    assert rule["schedule"] == ["before 6am"]
    assert rule["automerge"] is True
    assert rule["automergeType"] == "pr"
    assert rule["platformAutomerge"] is True
