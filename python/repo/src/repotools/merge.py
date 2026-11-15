"""pr-merge: a lead's self-merge, done only once every gate the owner named holds, in the one merge form allowed."""

# The gates are the owner's self-merge ruling's (2026-11-15): local hk check --all passes on the exact head, the
# reviewer approved that head and the pull request's text, then `gh pr merge --merge --match-head-commit <sha>` with
# the account's noreply address as the merge author. Before this, only the reviewer gates ran in code (commit-msg
# and pr-create); the rest were prose.

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import pane_approval
from .git import git
from .models import Merged, PrMerge, PrText

# The merging account's noreply address (merge-author-noreply ruling): never a personal email on a public repository.
NOREPLY = "1428022+sortakool@users.noreply.github.com"
# CodeRabbit appends its release notes to a pull request's body between these markers (seen on dotfiles #720).
BOT_OPEN = "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->"
BOT_CLOSE = "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, check=True, text=True).stdout


def view(number: int, fields: str) -> dict[str, Any]:
    return json.loads(gh("pr", "view", str(number), "--json", fields))


def shown_body(live: str, approved: str) -> bool:
    """Whether GitHub's body is the approved one, or it with only CodeRabbit's release-notes block appended after."""
    if live == approved:
        return True
    rest = live.removeprefix(approved)
    added = rest.strip("\n")
    return (
        rest != live
        and added.startswith(BOT_OPEN)
        and added.endswith(BOT_CLOSE)
        and added.count(BOT_OPEN) == added.count(BOT_CLOSE) == 1
    )


def gates(options: PrMerge, head: str) -> None:
    """Every gate but hk: a clean checkout at head, and an open pull request into GitHub's default branch whose head
    is head, whose text is the one the reviewer approved at head."""
    if git("status", "--porcelain"):
        msg = "the checkout has changes or untracked files, so hk check --all would not test the head alone"
        raise ValueError(msg)
    if git("rev-parse", "HEAD").strip() != head:
        msg = f"this checkout's HEAD moved from {head} while pr-merge ran"
        raise ValueError(msg)
    pr = view(options.number, "headRefOid,state,baseRefName,title,body")
    default = gh("repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name").strip()
    number = f"pull request #{options.number}"
    sent = Path(options.body_file).read_bytes()  # read once: GitHub's body and the approval are checked against it
    approved = sent.decode()
    refusals = [
        (pr["state"] != "OPEN", f"{number} is {pr['state']}, not open"),
        (pr["baseRefName"] != default, f"{number} goes into {pr['baseRefName']}, not {default}"),
        (pr["headRefOid"] != head, f"{number}'s head is {pr['headRefOid']}, but this checkout's HEAD is {head}"),
        (pr["title"] != options.title, f"{number}'s title on GitHub is not the approved title"),
        (not shown_body(pr["body"], approved), f"{number}'s body on GitHub is not the approved body"),
    ]
    for refused, msg in refusals:
        if refused:
            raise ValueError(msg)
    # The pull request fingerprint holds HEAD, so this is the reviewer's approval of this head and of the text.
    pane_approval.check(PrText(title=options.title, body_file=options.body_file), sent)


def merge(options: PrMerge) -> None:
    """Refuse at the first gate that fails; merge only after all of them, then check the merge commit's author."""
    head = git("rev-parse", "HEAD").strip()
    gates(options, head)
    # hk's own output passes through: a failure shows the step that failed.
    checked = subprocess.run(["hk", "check", "--all"], check=False).returncode
    if checked != 0:
        msg = f"hk check --all failed (exit {checked}) on {head}"
        raise ValueError(msg)
    # hk runs for minutes: the checkout, the pull request or the approval may have changed meanwhile, so every gate is
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
