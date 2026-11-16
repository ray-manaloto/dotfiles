"""Child processes through AnyIO (DL-762)."""

import os
import subprocess
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

import anyio
from anyio.abc import ByteReceiveStream


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


async def tee(*cmd: str | PathLike[str], env: Mapping[str, str], watch: bytes, copy: Path) -> tuple[int, bool]:
    """Run cmd with its output passed on to this process's stdout and stderr and written to copy; its exit
    code, and whether watch appeared in either stream.
    """
    seen = False
    log = os.open(copy, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    def write(fd: int, chunk: bytes) -> None:
        os.write(fd, chunk)
        os.write(log, chunk)

    async def pump(stream: ByteReceiveStream, fd: int) -> None:
        nonlocal seen
        tail = b""
        async for chunk in stream:
            await anyio.to_thread.run_sync(write, fd, chunk)
            # The tail keeps a watch split across two chunks.
            data = tail + chunk
            seen = seen or watch in data
            tail = data[-len(watch) :]

    try:
        async with await anyio.open_process(
            [str(part) for part in cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        ) as process:
            async with anyio.create_task_group() as group:
                group.start_soon(pump, process.stdout, 1)
                group.start_soon(pump, process.stderr, 2)
            return await process.wait(), seen
    finally:
        os.close(log)
