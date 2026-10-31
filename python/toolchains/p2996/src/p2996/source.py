"""p2996 source: check out the newest commit of P2996_BRANCH (or --commit) and apply the patches."""

import contextlib
from pathlib import Path

import anyio

from . import proc
from .config import BOOTSTRAP, PATCHES, checkout, git, identity, src
from .log import P2996Error, log
from .models import Config, Source


async def latest(cfg: Config) -> str:
    out = await proc.output("git", "ls-remote", "--exit-code", cfg.remote, f"refs/heads/{cfg.branch}")
    return out.split()[0]


async def run(cfg: Config, args: Source, patches: Path = PATCHES, bootstrap: Path = BOOTSTRAP) -> None:
    commit = args.commit or await latest(cfg)
    name = identity(commit, patches, bootstrap)
    tree = checkout(cfg, name)
    if not await anyio.Path(tree).is_dir():
        src(cfg).mkdir(parents=True, exist_ok=True)
        async with anyio.TemporaryDirectory(dir=str(src(cfg)), prefix=".new-") as tmp:
            new = Path(tmp) / name
            new.mkdir()
            await prepare(new, cfg, commit, patches)
            # A second run of this commit may have got there first; its tree is just as good.
            with contextlib.suppress(OSError):
                new.rename(tree)
            await git(tree, "rev-parse", "HEAD")  # Any other rename failure left no tree; stop here.
    log.info("source ready", checkout=str(tree), commit=commit)


async def prepare(tree: Path, cfg: Config, commit: str, patches: Path) -> None:
    await git(tree, "init", "-q")
    await git(tree, "fetch", "--depth=1", "--no-tags", cfg.remote, commit)
    await git(tree, "-c", "advice.detachedHead=false", "checkout", "--detach", "FETCH_HEAD")
    for patch in sorted([p async for p in anyio.Path(patches).glob("*.patch")]):
        if (await proc.run("git", "-C", tree, "apply", "--unidiff-zero", patch, check=False)).returncode != 0:
            msg = (
                f"p2996 source: {patch.name} no longer applies to {commit}; "
                "upstream may have fixed it (delete the patch) or moved the code (rebase it)"
            )
            raise P2996Error(msg)
        log.info("patch applied", patch=patch.name)
