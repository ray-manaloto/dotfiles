# Copyright (c) 2026 Raymond Manaloto
"""Tests for the codegen toolchain (#1329): the pilot model and its gate."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import msgspec
import pytest
from dotfiles_setup import codec, codegen_check, main
from dotfiles_setup.codegen_check import (
    FORMATTER_FAILURE,
    CodegenConfigError,
    GeneratorRun,
    check,
    job_outputs,
    stale_files,
)
from dotfiles_setup.generated.drift_verdict import DriftVerdict

_REPO = Path(__file__).resolve().parent.parent
_GENERATED = "python/src/dotfiles_setup/generated"

_PYPROJECT = """\
[tool.datamodel-codegen]
output-model-type = "msgspec.Struct"

[tool.datamodel-codegen.jobs.drift-verdict]
input = "../schemas/drift-verdict.schema.json"
output = "src/dotfiles_setup/generated/drift_verdict.py"
"""


def _tree(tmp_path: Path, pyproject: str = _PYPROJECT) -> Path:
    """A repo with one job and its generated module, plus __init__.py."""
    (tmp_path / "python").mkdir()
    (tmp_path / "python/pyproject.toml").write_text(pyproject)
    generated = tmp_path / _GENERATED
    generated.mkdir(parents=True)
    (generated / "__init__.py").write_text('"""package."""\n')
    (generated / "drift_verdict.py").write_text("# generated\n")
    return tmp_path


def _generator(tmp_path: Path) -> Path:
    binary = tmp_path / "bin/datamodel-codegen"
    binary.parent.mkdir()
    binary.write_text("")
    return binary


# ── the pilot model ────────────────────────────────────────────────────


def test_the_generated_verdict_decodes_a_valid_exit_code() -> None:
    assert codec.decode(b"1", DriftVerdict) is DriftVerdict.DRIFT
    assert codec.decode(b"0", DriftVerdict) is DriftVerdict.IN_SYNC


def test_the_generated_verdict_rejects_an_exit_code_outside_the_set() -> None:
    with pytest.raises(msgspec.ValidationError):
        codec.decode(b"3", DriftVerdict)


def test_the_verdict_values_are_the_exit_codes_callers_branch_on() -> None:
    """A gate exits with these, and shell callers branch on the raw rc."""
    assert [int(v) for v in DriftVerdict] == [0, 1, 2]


# ── job outputs and the stale scan ─────────────────────────────────────


def test_job_outputs_resolve_relative_to_the_pyproject(tmp_path: Path) -> None:
    assert {str(p) for p in job_outputs(_tree(tmp_path))} == {
        f"{_GENERATED}/drift_verdict.py"
    }


def test_no_stale_file_when_every_module_has_a_job(tmp_path: Path) -> None:
    assert stale_files(_tree(tmp_path)) == []


@pytest.mark.parametrize(
    "orphan", ["orphan.py", "sub/__init__.py", "sub/models.py", "stub.pyi"]
)
def test_a_file_no_job_writes_is_stale_at_any_depth(
    tmp_path: Path, orphan: str
) -> None:
    root = _tree(tmp_path)
    path = root / _GENERATED / orphan
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n")
    assert [str(p) for p in stale_files(root)] == [f"{_GENERATED}/{orphan}"]


def test_bytecode_caches_are_not_stale(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    cache = root / _GENERATED / "__pycache__/drift_verdict.cpython-314.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"")
    assert stale_files(root) == []


@pytest.mark.parametrize(
    "pyproject",
    [
        "[tool.ruff]\n",
        '[[tool.datamodel-codegen.jobs]]\noutput = "src/x.py"\n',
        '[tool.datamodel-codegen.jobs.j]\ninput = "a.json"\n',
        "[tool.datamodel-codegen.jobs.j]\noutput = 5\n",
        '[tool.datamodel-codegen.jobs.j]\noutput = "src/dotfiles_setup/elsewhere.py"\n',
    ],
    ids=[
        "no-table",
        "array-of-jobs",
        "no-output",
        "non-string-output",
        "outside-generated",
    ],
)
def test_a_malformed_config_is_a_config_error(tmp_path: Path, pyproject: str) -> None:
    with pytest.raises(CodegenConfigError):
        job_outputs(_tree(tmp_path, pyproject))


# ── the combined verdict (native --check injected at the subprocess seam) ──


@pytest.mark.parametrize(
    ("native_rc", "orphans", "expected"),
    [
        (0, 0, DriftVerdict.IN_SYNC),
        (1, 0, DriftVerdict.DRIFT),
        (0, 1, DriftVerdict.DRIFT),
        (1, 1, DriftVerdict.DRIFT),
        (2, 0, DriftVerdict.ERROR),
        (2, 1, DriftVerdict.ERROR),
        (3, 0, DriftVerdict.ERROR),
        (-9, 0, DriftVerdict.ERROR),
    ],
)
def test_check_combines_the_native_rc_and_the_stale_scan(
    tmp_path: Path, native_rc: int, orphans: int, expected: DriftVerdict
) -> None:
    root = _tree(tmp_path)
    for index in range(orphans):
        (root / _GENERATED / f"orphan{index}.py").write_text("x\n")
    calls: list[list[str]] = []

    def run(argv: list[str], cwd: Path) -> GeneratorRun:
        calls.append(argv)
        assert cwd == root / "python"
        return GeneratorRun(native_rc, "")

    assert check(root, run, _generator(tmp_path)) is expected
    assert calls[0][1:] == ["--all-jobs", "--check"]


def test_a_formatter_failure_is_an_error_not_drift(tmp_path: Path) -> None:
    """The generator turns a ruff failure into a warning and reports a diff."""
    root = _tree(tmp_path)

    def run(argv: list[str], cwd: Path) -> GeneratorRun:
        del argv, cwd
        return GeneratorRun(1, f"UserWarning: {FORMATTER_FAILURE}: boom")

    assert check(root, run, _generator(tmp_path)) is DriftVerdict.ERROR


def _never(argv: list[str], cwd: Path) -> GeneratorRun:
    raise AssertionError((argv, cwd))


def test_a_missing_generator_is_an_error_not_drift(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    absent = tmp_path / "absent/datamodel-codegen"
    assert check(root, _never, absent) is DriftVerdict.ERROR


def test_a_stale_file_is_drift_even_without_the_generator(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / _GENERATED / "orphan.py").write_text("x\n")
    absent = tmp_path / "absent/datamodel-codegen"
    assert check(root, _never, absent) is DriftVerdict.DRIFT


def test_any_unanticipated_failure_is_an_error_not_drift(tmp_path: Path) -> None:
    root = _tree(tmp_path, '[[tool.datamodel-codegen.jobs]]\noutput = "x.py"\n')
    assert codegen_check.codegen_check_main(root) == DriftVerdict.ERROR


def test_a_gate_that_cannot_import_is_an_error_not_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deleted generated module must not read as drift (exit 1).

    `importlib.import_module` is the stdlib boundary the dispatcher crosses;
    patching it is the only way to make our own module fail to import.
    """

    def fail(name: str) -> object:
        raise ImportError(name)

    monkeypatch.setattr(main.importlib, "import_module", fail)
    assert main.run_codegen_check(tmp_path) == DriftVerdict.ERROR


# ── real generator, through the locked codegen group (real-integration) ──


def _copy_codegen_inputs(dest: Path) -> Path:
    """The schema, the pyproject and the generated package, nothing else."""
    for relative in ("schemas/drift-verdict.schema.json", "python/pyproject.toml"):
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_REPO / relative, dest / relative)
    shutil.copytree(
        _REPO / _GENERATED,
        dest / _GENERATED,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return dest


def _real_check(root: Path) -> int:
    """`datamodel-codegen --all-jobs --check` from the locked codegen group."""
    argv = [
        "uv",
        "run",
        "--project",
        str(_REPO / "python"),
        "--locked",
        "--group",
        "codegen",
        "datamodel-codegen",
        "--all-jobs",
        "--check",
    ]
    return subprocess.run(
        argv, cwd=root / "python", check=False, capture_output=True
    ).returncode


def test_the_real_generator_passes_the_committed_tree_and_fails_a_hand_edit(
    tmp_path: Path,
) -> None:
    root = _copy_codegen_inputs(tmp_path)
    assert _real_check(root) == DriftVerdict.IN_SYNC
    module = root / _GENERATED / "drift_verdict.py"
    module.write_text(module.read_text() + "    EXTRA = 3\n")
    assert _real_check(root) == DriftVerdict.DRIFT


def test_the_real_generator_fails_a_schema_changed_without_regenerating(
    tmp_path: Path,
) -> None:
    root = _copy_codegen_inputs(tmp_path)
    schema = root / "schemas/drift-verdict.schema.json"
    schema.write_text(
        schema.read_text()
        .replace('"enum": [0, 1, 2]', '"enum": [0, 1, 2, 3]')
        .replace('"ERROR"]', '"ERROR", "UNKNOWN"]')
    )
    assert _real_check(root) == DriftVerdict.DRIFT


_STRUCT_SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Probe",
  "description": "A one-field struct for the forbid arm.",
  "type": "object",
  "properties": {"name": {"type": "string"}},
  "required": ["name"]
}
"""


def _generate_probe_struct(
    root: Path, *, drop: str | None = None
) -> type[msgspec.Struct]:
    """Generate a Struct with OUR [tool.datamodel-codegen] table; import it.

    `drop` removes one config line first — the control arm for the setting
    under test.
    """
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    (root / "schemas/probe.schema.json").write_text(_STRUCT_SCHEMA)
    pyproject = (_REPO / "python/pyproject.toml").read_text()
    if drop is not None:
        assert pyproject.count(f"\n{drop}\n") == 1
        pyproject = pyproject.replace(f"\n{drop}\n", "\n")
    (root / "python").mkdir(parents=True, exist_ok=True)
    (root / "python/pyproject.toml").write_text(
        pyproject
        + "\n[tool.datamodel-codegen.jobs.probe]\n"
        + 'input = "../schemas/probe.schema.json"\n'
        + 'output = "src/dotfiles_setup/generated/probe.py"\n'
    )
    argv = [
        "uv",
        "run",
        "--project",
        str(_REPO / "python"),
        "--locked",
        "--group",
        "codegen",
        "datamodel-codegen",
        "--job",
        "probe",
    ]
    subprocess.run(argv, cwd=root / "python", check=True, capture_output=True)
    module_path = root / "python/src/dotfiles_setup/generated/probe.py"
    spec = importlib.util.spec_from_file_location(f"probe_{id(root)}", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Probe


def test_generated_structs_reject_unknown_fields(tmp_path: Path) -> None:
    probe = _generate_probe_struct(tmp_path)
    assert codec.decode(b'{"name": "x"}', probe)
    with pytest.raises(msgspec.ValidationError):
        codec.decode(b'{"name": "x", "bogus": 1}', probe)


def test_without_the_generic_base_class_unknown_fields_decode_silently(
    tmp_path: Path,
) -> None:
    """Control arm: proves `use-generic-base-class` is what makes forbid work."""
    probe = _generate_probe_struct(tmp_path, drop="use-generic-base-class = true")
    assert codec.decode(b'{"name": "x", "bogus": 1}', probe)
