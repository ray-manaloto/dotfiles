"""p2996 source: check out the newest commit of P2996_BRANCH (or --commit) and apply the patches."""

import subprocess
from pathlib import Path

from .config import RESOURCES, git, src
from .models import Config


def latest(cfg: Config) -> str:
    out = subprocess.run(
        ["git", "ls-remote", "--exit-code", cfg.remote, f"refs/heads/{cfg.branch}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return out.split()[0]


def run(cfg: Config, commit: str | None, patches: Path = RESOURCES / "patches") -> None:
    commit = commit or latest(cfg)
    checkout = src(cfg)
    if not (checkout / ".git").is_dir():
        checkout.mkdir(parents=True, exist_ok=True)
        git(checkout, "init", "-q")
        git(checkout, "remote", "add", "origin", cfg.remote)
    if git(checkout, "rev-parse", "-q", "--verify", "HEAD", check=False) != commit:
        git(checkout, "fetch", "--depth=1", "--no-tags", "origin", commit)
        # --force drops the previous commit's patches; they are applied again below.
        git(checkout, "-c", "advice.detachedHead=false", "checkout", "--force", "--detach", "FETCH_HEAD")
    apply = ["git", "-C", str(checkout), "apply", "--unidiff-zero"]
    for patch in sorted(patches.glob("*.patch")):
        if subprocess.run([*apply, "--reverse", "--check", patch], capture_output=True, check=False).returncode == 0:
            print(f"applied already: {patch.name}")
        elif subprocess.run([*apply, patch], check=False).returncode == 0:
            print(f"applied: {patch.name}")
        else:
            msg = (
                f"p2996 source: {patch.name} no longer applies to {commit}; "
                "upstream may have fixed it (delete the patch) or moved the code (rebase it)"
            )
            raise SystemExit(msg)
    print(f"p2996 source: {checkout} at {commit}")
