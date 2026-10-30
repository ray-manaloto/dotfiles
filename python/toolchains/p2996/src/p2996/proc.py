"""Child processes through AnyIO (DL-762)."""

import subprocess
from collections.abc import Mapping
from os import PathLike

import anyio


async def run(
    *cmd: str | PathLike[str],
    env: Mapping[str, str] | None = None,
    check: bool = True,
    capture: bool = True,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run cmd; capture=False streams its output (cmake, codex) instead of keeping it."""
    pipe = subprocess.PIPE if capture else None
    return await anyio.run_process(
        [str(part) for part in cmd],
        input=stdin.encode() if stdin is not None else None,
        stdout=pipe,
        stderr=pipe,
        check=check,
        env=env,
    )


async def output(*cmd: str | PathLike[str], env: Mapping[str, str] | None = None) -> str:
    return (await run(*cmd, env=env)).stdout.decode().strip()
