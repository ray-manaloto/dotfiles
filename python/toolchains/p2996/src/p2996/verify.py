"""p2996 verify: clang++-p2996 loads its default config, then compiles and runs reflection.cpp."""

import os
from pathlib import Path

import anyio

from . import proc
from .config import RESOURCES, bin_dir
from .log import P2996Error, log
from .models import Config, Verify


async def run(cfg: Config, _: Verify) -> None:
    await check(bin_dir(cfg) / "clang++-p2996")


async def check(cxx: Path, sample: Path = RESOURCES / "reflection.cpp", expect: str = "reflection value=43") -> None:
    env = {k: v for k, v in os.environ.items() if k not in ("SDKROOT", "CLANG_NO_DEFAULT_CONFIG")}
    version = await proc.output(cxx, "--version", env=env)
    if "/arm64-apple-darwin-clang++.cfg" not in version:
        msg = f"p2996 verify: {cxx} does not load arm64-apple-darwin-clang++.cfg"
        raise P2996Error(msg)
    async with anyio.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "reflection"
        await proc.run(cxx, "-std=c++26", "-freflection", sample, "-o", exe, env=env)
        out = await proc.output(exe)
    if out != expect:
        msg = f"p2996 verify: sample printed {out!r}"
        raise P2996Error(msg)
    log.info("verify ok", compiler=version.splitlines()[0])
