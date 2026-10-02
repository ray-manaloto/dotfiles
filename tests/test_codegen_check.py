# Copyright (c) 2026 Raymond Manaloto
"""Tests for the codegen toolchain (#1329): the pilot model and its gate."""

from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
import pytest
from dotfiles_setup import codec, codegen_check
from dotfiles_setup.codegen_check import check, job_outputs, stale_modules
from dotfiles_setup.generated.drift_verdict import DriftVerdict

if TYPE_CHECKING:
    from pathlib import Path

_PYPROJECT = """\
[tool.datamodel-codegen]
output-model-type = "msgspec.Struct"

[tool.datamodel-codegen.jobs.drift-verdict]
input = "../schemas/drift-verdict.schema.json"
output = "src/dotfiles_setup/generated/drift_verdict.py"
"""


def _tree(tmp_path: Path) -> Path:
    """A repo with one job and its generated module, plus __init__.py."""
    (tmp_path / "python").mkdir()
    (tmp_path / "python/pyproject.toml").write_text(_PYPROJECT)
    generated = tmp_path / "python/src/dotfiles_setup/generated"
    generated.mkdir(parents=True)
    (generated / "__init__.py").write_text('"""package."""\n')
    (generated / "drift_verdict.py").write_text("# generated\n")
    return tmp_path


# ── the pilot model ────────────────────────────────────────────────────


def test_the_generated_verdict_decodes_a_valid_exit_code() -> None:
    assert codec.decode(b"1", DriftVerdict) is DriftVerdict.DRIFT
    assert codec.decode(b"0", DriftVerdict) is DriftVerdict.IN_SYNC


def test_the_generated_verdict_rejects_an_exit_code_outside_the_set() -> None:
    with pytest.raises(msgspec.ValidationError):
        codec.decode(b"3", DriftVerdict)


def test_the_verdict_values_are_the_exit_codes_shell_callers_branch_on() -> None:
    """refresh.yml and hk read these as raw rcs, so the ints are the contract."""
    assert [int(v) for v in DriftVerdict] == [0, 1, 2]


# ── the stale-module scan ──────────────────────────────────────────────


def test_job_outputs_resolve_relative_to_the_pyproject(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert {str(p) for p in job_outputs(root)} == {
        "python/src/dotfiles_setup/generated/drift_verdict.py"
    }


def test_no_stale_module_when_every_module_has_a_job(tmp_path: Path) -> None:
    assert stale_modules(_tree(tmp_path)) == []


def test_a_module_no_job_writes_is_stale(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "python/src/dotfiles_setup/generated/orphan.py").write_text("x = 1\n")
    assert [str(p) for p in stale_modules(root)] == [
        "python/src/dotfiles_setup/generated/orphan.py"
    ]


# ── the combined verdict (native --check injected at the subprocess seam) ──


@pytest.fixture
def _generator_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "bin/datamodel-codegen"
    binary.parent.mkdir()
    binary.write_text("")
    monkeypatch.setattr(codegen_check, "generator_binary", lambda: binary)


@pytest.mark.usefixtures("_generator_present")
@pytest.mark.parametrize(
    ("native_rc", "orphans", "expected"),
    [
        (0, 0, DriftVerdict.IN_SYNC),
        (1, 0, DriftVerdict.DRIFT),
        (0, 1, DriftVerdict.DRIFT),
        (1, 1, DriftVerdict.DRIFT),
        (2, 0, DriftVerdict.ERROR),
        (2, 1, DriftVerdict.ERROR),
    ],
)
def test_check_combines_the_native_rc_and_the_stale_scan(
    tmp_path: Path, native_rc: int, orphans: int, expected: DriftVerdict
) -> None:
    root = _tree(tmp_path)
    for index in range(orphans):
        (root / f"python/src/dotfiles_setup/generated/orphan{index}.py").write_text(
            "x\n"
        )
    calls: list[list[str]] = []

    def run(argv: list[str], cwd: Path) -> int:
        calls.append(argv)
        assert cwd == root / "python"
        return native_rc

    assert check(root, run) is expected
    assert calls[0][1:] == ["--all-jobs", "--check"]


def test_a_missing_generator_is_an_error_not_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(tmp_path)
    monkeypatch.setattr(
        codegen_check, "generator_binary", lambda: tmp_path / "absent/datamodel-codegen"
    )

    def never(argv: list[str], cwd: Path) -> int:
        raise AssertionError((argv, cwd))

    assert check(root, never) is DriftVerdict.ERROR


def test_an_unreadable_config_is_an_error_not_drift(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "python/pyproject.toml").write_text("[tool.datamodel-codegen\n")
    assert codegen_check.codegen_check_main(root) == DriftVerdict.ERROR
