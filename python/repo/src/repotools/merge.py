"""pr-create opens a pull request; pr-merge is a lead's self-merge, done only once every gate holds, in one form."""

# The gates are the owner's self-merge ruling's (2026-11-15): local hk check --all passes on the exact head, then
# `gh pr merge --merge --match-head-commit <sha>` with the account's noreply address as the merge author. No review
# is required (owner ruling, 2026-11-17).

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from . import process
from .git import git
from .models import Merged, PrMerge, PrText

# The merging account's noreply address (merge-author-noreply ruling): never a personal email on a public repository.
NOREPLY = "1428022+sortakool@users.noreply.github.com"
# CodeRabbit appends its release notes to a pull request's body between these markers (seen on dotfiles #720).
BOT_OPEN = "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->"
BOT_CLOSE = "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, check=True, text=True).stdout


def base() -> str:
    """The branch a pull request goes into: origin's default branch, as this clone recorded it."""
    ref = "refs/remotes/origin/HEAD"
    done = subprocess.run(["git", "symbolic-ref", "--short", ref], capture_output=True, check=False, text=True)
    if done.returncode != 0:
        msg = f"{ref} is not set, so origin's default branch is unknown; run git remote set-head origin --auto"
        raise ValueError(msg)
    return done.stdout.strip().removeprefix("origin/")


def create(text: PrText) -> None:
    """Open the pull request, its body piped to gh as the file's bytes."""
    body = Path(text.body_file).read_bytes()
    command = ["gh", "pr", "create", "--base", base(), "--title", text.title, "--body-file", "-"]
    done = process.run(command, body, capture_stdout=False)
    # The helper always captures stderr; only stdout may be None.
    sys.stderr.write(cast("bytes", done.stderr).decode(errors="replace"))


def view(number: int, fields: str) -> dict[str, Any]:
    return json.loads(gh("pr", "view", str(number), "--json", fields))


def shown_body(live: str, given: str) -> bool:
    """Whether GitHub's body is the given one, or it with only CodeRabbit's release-notes block appended after."""
    if live == given:
        return True
    rest = live.removeprefix(given)
    added = rest.strip("\n")
    return (
        rest != live
        and added.startswith(BOT_OPEN)
        and added.endswith(BOT_CLOSE)
        and added.count(BOT_OPEN) == added.count(BOT_CLOSE) == 1
    )


def gates(options: PrMerge, head: str) -> None:
    """Every gate but hk: a clean checkout at head, and an open pull request into GitHub's default branch whose head
    is head, whose title and body are the given ones."""
    if git("status", "--porcelain"):
        msg = "the checkout has changes or untracked files, so hk check --all would not test the head alone"
        raise ValueError(msg)
    if git("rev-parse", "HEAD").strip() != head:
        msg = f"this checkout's HEAD moved from {head} while pr-merge ran"
        raise ValueError(msg)
    pr = view(options.number, "headRefOid,state,baseRefName,title,body")
    default = gh("repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name").strip()
    number = f"pull request #{options.number}"
    given = Path(options.body_file).read_bytes().decode()  # bytes: text mode would turn a CRLF body into LF
    refusals = [
        (pr["state"] != "OPEN", f"{number} is {pr['state']}, not open"),
        (pr["baseRefName"] != default, f"{number} goes into {pr['baseRefName']}, not {default}"),
        (pr["headRefOid"] != head, f"{number}'s head is {pr['headRefOid']}, but this checkout's HEAD is {head}"),
        (pr["title"] != options.title, f"{number}'s title on GitHub is not the given title"),
        (not shown_body(pr["body"], given), f"{number}'s body on GitHub is not the given body"),
    ]
    for refused, msg in refusals:
        if refused:
            raise ValueError(msg)


def merge(options: PrMerge) -> None:
    """Refuse at the first gate that fails; merge only after all of them, then check the merge commit's author."""
    head = git("rev-parse", "HEAD").strip()
    gates(options, head)
    # hk's own output passes through: a failure shows the step that failed.
    checked = subprocess.run(["hk", "check", "--all"], check=False).returncode
    if checked != 0:
        msg = f"hk check --all failed (exit {checked}) on {head}"
        raise ValueError(msg)
    # hk runs for minutes: the checkout or the pull request may have changed meanwhile, so every gate is
    # checked again. What is left between this and the merge is GitHub's to hold: --match-head-commit refuses a moved
    # head; a retarget or text edit within that last request is not caught.
    gates(options, head)
    gh("pr", "merge", str(options.number), "--merge", "--match-head-commit", head, "--author-email", NOREPLY)
    commit = view(options.number, "mergeCommit")["mergeCommit"]["oid"]
    email = gh("api", f"repos/{{owner}}/{{repo}}/commits/{commit}", "--jq", ".commit.author.email").strip()
    if email != NOREPLY:
        msg = f"merge commit {commit} has author {email}, not {NOREPLY}: report it to the owner"
        raise ValueError(msg)
    merged = Merged(number=options.number, merge_commit=commit, author_email=email)
    sys.stdout.write(merged.model_dump_json() + "\n")
