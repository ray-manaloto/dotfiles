"""p2996 source: check out the newest commit of P2996_BRANCH (or --commit) and apply the patches."""

from pathlib import Path

import anyio

from . import proc
from .config import RESOURCES, git, src
from .log import P2996Error, log
from .models import Config, Source


async def latest(cfg: Config) -> str:
    out = await proc.output("git", "ls-remote", "--exit-code", cfg.remote, f"refs/heads/{cfg.branch}")
    return out.split()[0]


async def run(cfg: Config, args: Source, patches: Path = RESOURCES / "patches") -> None:
    commit = args.commit or await latest(cfg)
    checkout = src(cfg)
    if not (checkout / ".git").is_dir():
        checkout.mkdir(parents=True, exist_ok=True)
        await git(checkout, "init", "-q")
        await git(checkout, "remote", "add", "origin", cfg.remote)
    head = await proc.run("git", "-C", checkout, "rev-parse", "-q", "--verify", "HEAD", check=False)
    if head.stdout.decode().strip() != commit:
        await git(checkout, "fetch", "--depth=1", "--no-tags", "origin", commit)
        # --force drops the previous commit's patches; they are applied again below.
        await git(checkout, "-c", "advice.detachedHead=false", "checkout", "--force", "--detach", "FETCH_HEAD")
    apply = ("git", "-C", checkout, "apply", "--unidiff-zero")
    for patch in sorted([p async for p in anyio.Path(patches).glob("*.patch")]):
        if (await proc.run(*apply, "--reverse", "--check", patch, check=False)).returncode == 0:
            log.info("patch applied already", patch=patch.name)
        elif (await proc.run(*apply, patch, check=False)).returncode == 0:
            log.info("patch applied", patch=patch.name)
        else:
            msg = (
                f"p2996 source: {patch.name} no longer applies to {commit}; "
                "upstream may have fixed it (delete the patch) or moved the code (rebase it)"
            )
            raise P2996Error(msg)
    log.info("source ready", checkout=str(checkout), commit=commit)
