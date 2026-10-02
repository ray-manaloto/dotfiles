# Copyright (c) 2026 Raymond Manaloto
"""Gate: generated models match their schemas, and none is stale (#1329).

Code generation is the only way models and enums are produced (R16/D23). The
generator is ``datamodel-codegen``, configured once in ``python/pyproject.toml``
``[tool.datamodel-codegen]``; ``mise run codegen`` regenerates every job.

This gate adds one thing the native ``--all-jobs --check`` cannot see: a
module left in ``generated/`` that no job names any more (a renamed or removed
job). knowledge-base measured that gap against its own tree before wrapping
its check the same way (``kb_setup.guard_codegen``). The directory is
generator-owned, so any module in it other than ``__init__.py`` must be some
job's ``output``.

Exit codes are the generated :class:`DriftVerdict` — this gate is the pilot's
first consumer: 0 in sync, 1 drift (a stale module or a model that differs
from its schema), 2 the check itself could not decide.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.generated.drift_verdict import DriftVerdict

if TYPE_CHECKING:
    from collections.abc import Callable

#: The ``pyproject.toml`` that owns ``[tool.datamodel-codegen]``. Job paths in
#: it are relative to its own directory, which is also the generator's cwd.
PYPROJECT = Path("python/pyproject.toml")
#: The generator-owned package every job writes into.
GENERATED_DIR = Path("python/src/dotfiles_setup/generated")

type Runner = Callable[[list[str], Path], int]


def job_outputs(root: Path) -> set[Path]:
    """Every job ``output`` in ``[tool.datamodel-codegen]``, repo-relative."""
    pyproject = root / PYPROJECT
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    jobs = config["tool"]["datamodel-codegen"]["jobs"]
    base = pyproject.parent
    return {
        (base / job["output"]).resolve().relative_to(root.resolve())
        for job in jobs.values()
    }


def stale_modules(root: Path) -> list[Path]:
    """Modules in :data:`GENERATED_DIR` that no job writes, sorted."""
    named = job_outputs(root)
    return sorted(
        path.relative_to(root)
        for path in (root / GENERATED_DIR).glob("*.py")
        if path.name != "__init__.py" and path.relative_to(root) not in named
    )


def _run_generator_check(argv: list[str], cwd: Path) -> int:
    return subprocess.run(argv, cwd=cwd, check=False).returncode


def generator_binary() -> Path:
    """The ``datamodel-codegen`` beside this interpreter, never a PATH copy.

    The mise tasks run this module under ``uv run --locked --group codegen``,
    so the locked generator sits in the same environment's ``bin``.
    """
    return Path(sys.executable).with_name("datamodel-codegen")


def check(root: Path, run: Runner = _run_generator_check) -> DriftVerdict:
    """Run the stale scan and the native check; return the combined verdict.

    `run` is a test seam for the native ``--all-jobs --check`` subprocess.
    """
    stale = stale_modules(root)
    for path in stale:
        sys.stderr.write(
            f"codegen-check: {path} is in the generated package but no "
            f"[tool.datamodel-codegen] job writes it — delete it or add its job\n"
        )
    binary = generator_binary()
    if not binary.exists():
        sys.stderr.write(
            f"codegen-check: {binary} not found — run via `mise run "
            f"codegen-check` (uv run --locked --group codegen)\n"
        )
        return DriftVerdict.ERROR
    rc = run([str(binary), "--all-jobs", "--check"], (root / PYPROJECT).parent)
    if rc not in {DriftVerdict.IN_SYNC, DriftVerdict.DRIFT}:
        sys.stderr.write(f"codegen-check: the generator itself failed (rc={rc})\n")
        return DriftVerdict.ERROR
    if stale or rc == DriftVerdict.DRIFT:
        return DriftVerdict.DRIFT
    return DriftVerdict.IN_SYNC


def codegen_check_main(root: Path) -> int:
    """CLI entry point: ``dotfiles-setup codegen-check``."""
    try:
        verdict = check(root)
    except (OSError, KeyError, tomllib.TOMLDecodeError, ValueError) as exc:
        sys.stderr.write(f"codegen-check: could not decide: {exc}\n")
        return DriftVerdict.ERROR
    if verdict is DriftVerdict.IN_SYNC:
        sys.stdout.write("codegen-check: every generated module matches its job\n")
    return verdict
