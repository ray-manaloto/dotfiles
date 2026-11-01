"""p2996 source: reset the one source tree to the newest commit of P2996_BRANCH (or --commit) and patch it."""

from pathlib import Path

import anyio
from pydantic import TypeAdapter

from . import proc
from .config import PATCHES, checkout, git, last_build
from .log import P2996Error, log
from .models import CommitId, Config, Source


async def latest(cfg: Config) -> str:
    out = await proc.output("git", "ls-remote", "--exit-code", cfg.remote, f"refs/heads/{cfg.branch}")
    return TypeAdapter(CommitId).validate_python(out.split()[0])


async def run(cfg: Config, args: Source, patches: Path = PATCHES) -> None:
    commit = args.commit or await latest(cfg)
    # The tree is about to change, so nothing in it can be installed until a build succeeds on it.
    last_build(cfg).unlink(missing_ok=True)
    tree = checkout(cfg)
    tree.mkdir(parents=True, exist_ok=True)
    await prepare(tree, cfg, commit, patches)
    log.info("source ready", checkout=str(tree), commit=commit)


async def fetch(tree: Path, remote: str, commit: str) -> None:
    await git(tree, "init", "-q")
    await git(tree, "fetch", "--depth=1", "--no-tags", remote, commit)
    await git(tree, "-c", "advice.detachedHead=false", "checkout", "--force", "--detach", "FETCH_HEAD")
    await git(tree, "clean", "-ffdxq")


async def prepare(tree: Path, cfg: Config, commit: str, patches: Path) -> None:
    await fetch(tree, cfg.remote, commit)
    for patch in sorted([p async for p in anyio.Path(patches).glob("*.patch")]):
        if (await proc.run("git", "-C", tree, "apply", "--unidiff-zero", patch, check=False)).returncode != 0:
            msg = (
                f"p2996 source: {patch.name} no longer applies to {commit}; "
                "upstream may have fixed it (delete the patch) or moved the code (rebase it)"
            )
            raise P2996Error(msg)
        log.info("patch applied", patch=patch.name)
