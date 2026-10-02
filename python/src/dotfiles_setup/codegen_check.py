# Copyright (c) 2026 Raymond Manaloto
"""Gate: generated models match their schemas, and none is stale (#1329).

Code generation is the only sanctioned way to produce NEW models and enums
(R16/D23). The generator is ``datamodel-codegen``, configured once in
``python/pyproject.toml`` ``[tool.datamodel-codegen]``; ``mise run codegen``
regenerates every job.

This gate adds what the native ``--all-jobs --check`` cannot see or say:

* a file left in ``generated/`` (at any depth, ``.py`` or ``.pyi``) that no
  job writes any more — knowledge-base measured that gap in the native check
  and closed it the same way (``kb_setup.guard_codegen``, recursive scan);
* a job whose ``output`` is outside ``generated/``, where a later removal of
  the job would leave an orphan no scan can see;
* a FORMATTER failure: the generator downgrades it to a ``UserWarning`` and
  writes unformatted code, so its ``--check`` reports a diff (rc 1) for what
  is really a broken toolchain.

Exit codes are the generated :class:`DriftVerdict` — this gate is the pilot's
first consumer: 0 in sync, 1 drift (a stale file, or a model that differs from
its schema), 2 the check itself could not decide. Anything the gate did not
anticipate is 2, never 1: reading a broken check as drift is the collapse the
verdict exists to end.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.generated.drift_verdict import DriftVerdict

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

#: The ``pyproject.toml`` that owns ``[tool.datamodel-codegen]``. Job paths in
#: it are relative to its own directory, which is also the generator's cwd.
PYPROJECT = Path("python/pyproject.toml")
#: The generator-owned package every job writes into.
GENERATED_DIR = Path("python/src/dotfiles_setup/generated")
#: The one hand-written file the generated package may hold.
PACKAGE_MARKER = GENERATED_DIR / "__init__.py"
#: The generator's own text when a formatter fails and it emits raw code
#: (datamodel_code_generator/parser/base.py `_format_body_safe`, 0.83.0).
FORMATTER_FAILURE = "Failed to format code"


@dataclass(frozen=True)
class GeneratorRun:
    """What the native ``--check`` subprocess returned."""

    returncode: int
    stderr: str


type Runner = Callable[[list[str], Path], GeneratorRun]


class CodegenConfigError(ValueError):
    """``[tool.datamodel-codegen]`` is not in the shape this gate reads."""


def job_outputs(root: Path) -> set[Path]:
    """Every job ``output`` in ``[tool.datamodel-codegen]``, repo-relative.

    Raises:
        CodegenConfigError: when the table is missing, not a table of tables,
            a job has no string ``output``, or an output leaves
            :data:`GENERATED_DIR`.
    """
    pyproject = root / PYPROJECT
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    jobs = config.get("tool", {}).get("datamodel-codegen", {}).get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        msg = "[tool.datamodel-codegen.jobs] must be a non-empty table of jobs"
        raise CodegenConfigError(msg)
    outputs: set[Path] = set()
    generated = (root / GENERATED_DIR).resolve()
    for name, job in jobs.items():
        output = job.get("output") if isinstance(job, dict) else None
        if not isinstance(output, str):
            msg = f"job {name!r} has no string `output`"
            raise CodegenConfigError(msg)
        target = (pyproject.parent / output).resolve()
        if not target.is_relative_to(generated):
            msg = (
                f"job {name!r} writes {output!r}, outside {GENERATED_DIR}; a "
                f"later removal of the job would leave an orphan no scan sees"
            )
            raise CodegenConfigError(msg)
        outputs.add(target.relative_to(root.resolve()))
    return outputs


def stale_files(root: Path) -> list[Path]:
    """Files under :data:`GENERATED_DIR` (any depth) that no job writes."""
    named = job_outputs(root)
    return sorted(
        path.relative_to(root)
        for path in (root / GENERATED_DIR).rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".pyi"}
        and "__pycache__" not in path.parts
        and path.relative_to(root) != PACKAGE_MARKER
        and path.relative_to(root) not in named
    )


def _run_generator_check(argv: list[str], cwd: Path) -> GeneratorRun:
    proc = subprocess.run(argv, cwd=cwd, check=False, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return GeneratorRun(proc.returncode, proc.stderr)


def generator_binary() -> Path:
    """The ``datamodel-codegen`` beside this interpreter, never a PATH copy.

    The mise tasks run this module under ``uv run --locked --group codegen``,
    so the locked generator sits in the same environment's ``bin``.
    """
    return Path(sys.executable).with_name("datamodel-codegen")


def check(
    root: Path,
    run: Runner = _run_generator_check,
    binary: Path | None = None,
) -> DriftVerdict:
    """Run the stale scan and the native check; return the combined verdict.

    `run` and `binary` are the subprocess seam and the generator location.
    A stale file is definite drift whether or not the generator can run.
    """
    stale = stale_files(root)
    for path in stale:
        sys.stderr.write(
            f"codegen-check: {path} is in the generated package but no "
            f"[tool.datamodel-codegen] job writes it — delete it or add its job\n"
        )
    generator = binary if binary is not None else generator_binary()
    if not generator.exists():
        sys.stderr.write(
            f"codegen-check: {generator} not found — run via `mise run "
            f"codegen-check` (uv run --locked --group codegen)\n"
        )
        return DriftVerdict.DRIFT if stale else DriftVerdict.ERROR
    result = run([str(generator), "--all-jobs", "--check"], (root / PYPROJECT).parent)
    if FORMATTER_FAILURE in result.stderr:
        sys.stderr.write(
            "codegen-check: the generator's formatter failed, so its diff is "
            "meaningless — fix ruff (config or install) first\n"
        )
        return DriftVerdict.ERROR
    if result.returncode not in {DriftVerdict.IN_SYNC, DriftVerdict.DRIFT}:
        sys.stderr.write(
            f"codegen-check: datamodel-codegen could not complete the check "
            f"(rc={result.returncode}: invalid schema or config, or a crash)\n"
        )
        return DriftVerdict.ERROR
    if stale or result.returncode == DriftVerdict.DRIFT:
        return DriftVerdict.DRIFT
    return DriftVerdict.IN_SYNC


def codegen_check_main(root: Path) -> int:
    """CLI entry point: ``dotfiles-setup codegen-check``.

    Every failure the gate did not anticipate is ERROR (2), never DRIFT (1).
    """
    try:
        verdict = check(root)
    except Exception:
        logger.exception("codegen-check: could not decide")
        return DriftVerdict.ERROR
    if verdict is DriftVerdict.IN_SYNC:
        sys.stdout.write("codegen-check: every generated module matches its job\n")
    return verdict
