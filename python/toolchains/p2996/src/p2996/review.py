"""p2996 review-log: a read-only Codex team reports every warning, error and skipped part of a build log."""

from . import proc
from .config import PROJECT, RESOURCES, checkout
from .log import log
from .models import Config, ReviewLog


async def run(cfg: Config, args: ReviewLog) -> None:
    build_log = args.log.resolve()
    out = args.out or build_log.with_name(build_log.name + ".review.md")
    prompt = (RESOURCES / "review-log.md").read_text()
    prompt = prompt.replace("@LOG@", str(build_log)).replace("@SRC@", str(checkout(cfg)))
    # Never -s, --ephemeral or --dangerously-bypass-hook-trust: the sandbox and approval policy come from config keys.
    await proc.run(
        "codex",
        "exec",
        "-C",
        PROJECT,
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        'approval_policy="never"',
        "-o",
        out,
        "-",
        stdin=prompt,
        capture=False,
    )
    log.info("review written", report=str(out))
