"""p2996 review-log: a read-only Codex team reports every warning, error and skipped part of a build log."""

import subprocess
from pathlib import Path

from .config import PROJECT, RESOURCES, src
from .models import Config


def run(cfg: Config, log: Path, out: Path | None) -> None:
    log = log.resolve()
    out = out or log.with_name(log.name + ".review.md")
    prompt = (RESOURCES / "review-log.md").read_text().replace("@LOG@", str(log)).replace("@SRC@", str(src(cfg)))
    # Never -s, --ephemeral or --dangerously-bypass-hook-trust: the sandbox comes from the config key.
    subprocess.run(
        ["codex", "exec", "-C", str(PROJECT), "-c", 'sandbox_mode="read-only"', "-o", str(out), "-"],
        input=prompt,
        text=True,
        check=True,
    )
    print(f"p2996 review-log: report in {out}")
