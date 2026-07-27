"""Tests for the PreToolUse mise-tasks-only guard (dotfiles_setup.hook_guard)."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import hook_guard


@pytest.mark.parametrize(
    ("command", "redirect_hint"),
    [
        ("npx agnix .", "mise-installed binary"),
        ("cd /tmp && npx cowsay hi", "mise-installed binary"),
        ("chezmoi apply", "devcontainer"),
        ("chezmoi update -v", "devcontainer"),
        ("hk run pre-commit --all --stash none", "mise run lint"),
        ("hk run check --all", "mise run lint"),
        ("devcontainer up --workspace-folder .", "mise run up"),
        ("devcontainer build --workspace-folder .", "mise run dev-rebuild"),
        (
            "docker pull ghcr.io/ray-manaloto/dotfiles-devcontainer:dev",
            "mise run sync",
        ),
        ("gh pr create --fill", "mise run ship"),
        ("gh pr merge 42 --squash", "mise run land"),
        # Hand-rolled task detachment + CI-watch observation (workflow shapes
        # that ship/land own) — the gaps a 2026-07-14 session fell through.
        ("nohup mise run land -- 256 > /tmp/x 2>&1 &", "harness background"),
        ("env FOO=1 nohup mise run verify-local &", "harness background"),
        ("gh run watch 123 --exit-status", "gh run view"),
        ("gh pr checks 172 --watch", "mise run ship"),
        ("gh pr checks 172 --watch --interval 30", "mise run ship"),
        # Evidence discipline (_V3). A gate command piped into a pager reports
        # the PAGER's exit code — the shape that made a 7-hour wedged hk run
        # read as a pass.
        ("mise run lint 2>&1 | tail -40", "rc"),
        ("mise run lint | head -20", "rc"),
        ("mise run verify | tail", "rc"),
        ("mise run verify-local 2>&1 | tail -n 50", "rc"),
        ("uv run --project python pytest tests/ -x -q | tail -30", "rc"),
        ("pytest tests/ | tail", "rc"),
        ("dotfiles-setup verify run | head -5", "rc"),
        ("hk run check --all | tail -40", "mise run lint"),
        # An intermediate filter must not launder the pipe.
        ("mise run test 2>&1 | grep -i fail | tail -5", "rc"),
        # Hand-detachment via a trailing `&` — the `nohup` rule's sibling.
        ("mise run verify-local &", "harness background"),
        ("mise run land -- 256 > /tmp/x 2>&1 &", "harness background"),
        ("mise run bakeoff  &  ", "harness background"),
        ("mise run lint &\necho started", "harness background"),
    ],
)
def test_one_off_commands_denied_with_redirect(
    command: str, redirect_hint: str
) -> None:
    reason = hook_guard.decide(command)
    assert reason is not None
    assert redirect_hint in reason


@pytest.mark.parametrize(
    "command",
    [
        # Diagnostics and reads stay direct.
        "docker ps --filter label=x",
        "gh pr view 172 --json state",
        # One-shot CI reads stay allowed — only the --watch/run-watch forms
        # (workflow observation ship/land own) are redirected.
        "gh pr checks 172 --json state,bucket",
        "gh run view 123 --json conclusion",
        # The canonical land command itself — only hand-detaching it is denied.
        "mise run land -- 256",
        # Prose: `nohup mise run` inside a quoted string is not at command
        # position, so the detachment rule must not fire.
        "echo 'use nohup mise run for long tasks? no'",
        "chezmoi diff",
        "chezmoi execute-template < a.tmpl",
        "git status --porcelain",
        # The canonical forms themselves.
        "mise run lint",
        "mise run ship -- --title x",
        "uv run --project python pytest tests/test_pr.py -x -q",
        # The unwrapped form the permission engine hands the hook for the
        # canonical uv pytest command — MUST stay allowed (probe 2026-07-07).
        "pytest tests/ -x -q",
        # Substrings that must NOT false-positive.
        "docker pull ubuntu:24.04",
        "echo 'gh pr merge is wrapped by land'",
        "rg 'npx' docs/",
        "hk validate",
        # Prose mentions inside a commit message (probe 2026-07-07: the
        # unanchored chezmoi rule denied its own documenting commit).
        "git commit -m 'docs: chezmoi apply/update stays devcontainer-only'",
        # --- control arms for the _V3 pipe rule -------------------------------
        # A pager on a NON-gate command is ordinary diagnostics.
        "git log --oneline | head -5",
        "docker ps --filter label=x | tail -3",
        "ls .agent/plans/ | tail -15",
        # The gate commands themselves, unpiped — the canonical form.
        # (`mise run lint` itself is already pinned above.)
        "uv run --project python pytest tests/ -x -q",
        "mise run verify-local",
        # The PRESCRIBED replacement must not itself be denied: redirect to a
        # file, record the rc, then read the file.
        'mise run lint > /tmp/out.log 2>&1; echo "rc=$?" >> /tmp/out.log',
        "mise run lint > /tmp/out.log 2>&1\ntail -40 /tmp/out.log",
        # `[^;&\n]*` must not run past the gate's own segment: the pager here
        # belongs to an unrelated later command.
        "mise run lint; git log | head -5",
        "mise run lint && docker ps | tail -3",
        # `pytest` as prose, not at command position (the token most likely to
        # false-positive — it appears throughout this repo's docs).
        "rg 'pytest' docs/ | head -20",
        "grep -rn pytest .claude/rules/ | tail",
        # Quoted mention of the denied shape itself — masking must neuter the
        # pipe, per the module's "test a new rule against a quoted mention".
        "echo 'never run mise run lint | tail -40'",
        # --- control arms for the _V3 backgrounding rule ----------------------
        # `&&` is not a background operator.
        "mise run lint && mise run test",
        "mise run lint && echo ok",
        # A `2>&1` fd-dup is not a background operator either.
        "mise run lint > /tmp/x 2>&1",
        # Backgrounding a NON-mise command is out of scope.
        "sleep 5 &",
        "docker logs -f x &",
        # Quoted mention of the denied shape.
        "echo 'do not run mise run verify-local &'",
    ],
)
def test_legitimate_commands_allowed(command: str) -> None:
    assert hook_guard.decide(command) is None


def test_pretooluse_emits_deny_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hook_guard, "_read_command", lambda: "gh pr create")
    assert hook_guard.pretooluse_main() == 0
    out = capsys.readouterr().out
    assert '"permissionDecision": "deny"' in out
    assert "mise run ship" in out


def test_pretooluse_silent_on_allowed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hook_guard, "_read_command", lambda: "git status")
    assert hook_guard.pretooluse_main() == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "command",
    [
        # Review findings [13][14]: newline separators + wrapper prefixes.
        "echo hi\ngh pr merge 42 --squash",
        "env GH_PAGER= gh pr create --fill",
        "GH_TOKEN=x gh pr merge 42",
        "exec gh pr create",
        "timeout 30 devcontainer up --workspace-folder .",
        "nohup npx cowsay hi",
        # [16]: `docker image pull` variant.
        "docker image pull ghcr.io/ray-manaloto/dotfiles-devcontainer:dev",
    ],
)
def test_bypass_routes_denied(command: str) -> None:
    assert hook_guard.decide(command) is not None


@pytest.mark.parametrize(
    ("command", "redirect_hint"),
    [
        ("cd /x && gh pr create --fill", "mise run ship"),
        ("cd /x && gh pr merge 42 --squash", "mise run land"),
        # No space around the separator, and `;`/newline variants.
        ("cd /x&&gh pr create --fill", "mise run ship"),
        ("cd /x ; gh pr merge 42 --squash", "mise run land"),
        ("cd /x\ngh run watch 123 --exit-status", "gh run view"),
        # Stacked prefixes, a `~` path, a subshell, and an interposed command.
        ("cd /a && cd /b && hk run pre-commit --all", "mise run lint"),
        ("cd ~/dev && devcontainer up --workspace-folder .", "mise run up"),
        ("(cd /x && gh pr create --fill)", "mise run ship"),
        ("cd /x && echo starting && gh pr create --fill", "mise run ship"),
    ],
)
def test_cd_prefixed_one_offs_denied(command: str, redirect_hint: str) -> None:
    """A leading `cd <path> &&` must never hide the operative command.

    These pass WITHOUT a cd-unwrap in `decide()` (probe 2026-07-14, refuting
    the research report's predicted "chained-command evasion"): the `cd` prefix
    always ends in a separator `_CMD` re-anchors on. Pinned so a future
    narrowing of `_CMD`'s separator class fails here instead of silently
    opening the bypass. See the "NO `cd`-prefix unwrap" note in hook_guard.py.
    """
    reason = hook_guard.decide(command)
    assert reason is not None
    assert redirect_hint in reason


def test_pull_rule_does_not_span_separators() -> None:
    # [16]: an unrelated pull followed by a mention must not be denied.
    cmd = "docker pull ubuntu:24.04 && echo dotfiles-devcontainer"
    assert hook_guard.decide(cmd) is None


# --- repo-aware gh pr create/merge (2026-07-23) -----------------------------
#
# Before this, `gh pr merge -R ray-manaloto/knowledge-base` was denied and
# redirected to `mise run land` — a DOTFILES task with no repo parameter that
# watches dotfiles' main CI. The guard blocked the only working command and
# named a task that cannot do the job; KB PRs #1 and #2 were hand-merged
# because of it. Each arm below is paired with its opposite: a dispatch table
# tested in only one direction proves nothing about the others.
@pytest.mark.parametrize(
    ("command", "redirect_hint"),
    [
        # No -R at all => cwd => dotfiles. The pre-existing behaviour, pinned so
        # the new lookahead cannot silently stop denying the common case.
        ("gh pr create --fill", "mise run ship"),
        ("gh pr merge 42 --squash", "mise run land"),
        # Explicit dotfiles target routes the same way.
        ("gh pr create -R ray-manaloto/dotfiles --fill", "mise run ship"),
        ("gh pr merge 42 -R ray-manaloto/dotfiles --squash", "mise run land"),
        ("gh pr merge 42 --repo ray-manaloto/dotfiles", "mise run land"),
        # knowledge-base target routes to the KB tasks, in all flag spellings.
        ("gh pr create -R ray-manaloto/knowledge-base --fill", "mise run kb-ship"),
        ("gh pr merge 3 -R ray-manaloto/knowledge-base --squash", "mise run kb-land"),
        ("gh pr merge 3 --repo ray-manaloto/knowledge-base", "mise run kb-land"),
        ("gh pr merge 3 --repo=ray-manaloto/knowledge-base", "mise run kb-land"),
    ],
)
def test_gh_pr_routes_by_target_repo(command: str, redirect_hint: str) -> None:
    reason = hook_guard.decide(command)
    assert reason is not None, f"expected a deny for {command!r}"
    assert redirect_hint in reason


@pytest.mark.parametrize(
    "command",
    [
        # A sibling repo has no canonical task to redirect to, so denying would
        # block real work while pointing at nothing. CONTROL ARM for the table
        # above: the same verbs, allowed purely because of the target repo.
        "gh pr create -R ray-manaloto/symphony-cpp --fill",
        "gh pr merge 7 -R ray-manaloto/symphony-cpp --squash",
        "gh pr merge 7 --repo someone-else/their-repo",
        "gh pr create --repo=octocat/hello-world --fill",
    ],
)
def test_gh_pr_allowed_for_other_repos(command: str) -> None:
    assert hook_guard.decide(command) is None, f"expected ALLOW for {command!r}"


# --- #369: `gh pr merge --auto` routes by PR PROVENANCE ---------------------
#
# Same defect shape as the repo-aware split above, one axis over. A bot-opened
# PR never runs ship, so nothing armed auto-merge on it; `land` refuses an OPEN
# PR; `gh pr merge` was denied and redirected to `land`. The guard denied the
# only working command and named a task that cannot do the job — #138, #236 and
# #386 sat green and unmergeable. `--auto` names the ARMING intent exactly, so
# it gets the precise redirect; the generic merge rule still has to name a verb
# for each provenance.
@pytest.mark.parametrize(
    ("command", "rule_name"),
    [
        ("gh pr merge 236 --auto --squash", "gh pr merge --auto"),
        ("gh pr merge 236 --squash --auto", "gh pr merge --auto"),
        ("gh pr merge 236 -R ray-manaloto/dotfiles --auto", "gh pr merge --auto"),
        # The KB rule is ordered first, so a KB `--auto` still routes to kb-land
        # rather than to a dotfiles task that has no repo parameter (#349).
        (
            "gh pr merge 3 --auto -R ray-manaloto/knowledge-base",
            "gh pr merge (knowledge-base)",
        ),
    ],
)
def test_gh_pr_merge_auto_routes_to_automerge(command: str, rule_name: str) -> None:
    """Bound to the RULE, not to a substring of its reason.

    A reason-substring assertion could not see this rule being deleted: the
    generic merge rule names `mise run automerge` too, so it would match the
    command and satisfy the substring. Matching on rule identity is what makes
    deletion (the realistic regression) fail here.
    """
    rule = hook_guard.match(command)
    assert rule is not None, f"expected a deny for {command!r}"
    assert rule.name == rule_name
    assert "mise run automerge" in rule.reason or "kb-land" in rule.reason


@pytest.mark.parametrize(
    "command",
    [
        # CONTROL ARM: the arming shape is only guarded where a canonical verb
        # exists. A sibling repo has none, in either flag order.
        "gh pr merge 5 --auto -R some-other/repo",
        "gh pr merge -R some-other/repo 5 --auto",
        # The redirect TARGETS must not be denied — that is the outage this
        # whole rule exists to end.
        "mise run automerge -- 236",
        "uv run --project python dotfiles-setup pr automerge 236",
        # Prose describing the ban stays allowed (the #265 class).
        'echo "gh pr merge 1 --auto is denied"',
    ],
)
def test_automerge_arming_control_arm(command: str) -> None:
    assert hook_guard.decide(command) is None, f"expected ALLOW for {command!r}"


def test_generic_merge_rule_still_names_every_provenance() -> None:
    """A bare `gh pr merge` must name ship, automerge AND land.

    Before #369 it named only `land`, which cannot merge — the redirect had no
    working target for a bot PR. The three verbs are the whole dispatch table,
    so losing any one of them re-opens the outage for that provenance.
    """
    reason = hook_guard.decide("gh pr merge 42 --squash")
    assert reason is not None
    for verb in ("mise run ship", "mise run automerge", "mise run land"):
        assert verb in reason, f"{verb!r} missing from the generic merge redirect"


def test_foreign_repo_lookahead_does_not_span_separators() -> None:
    r"""A later command's `-R` must not license an earlier dotfiles `gh pr`.

    Without the `[^;&|\n]*` bound, the lookahead would scan past the separator,
    see a foreign `-R`, and stop denying a genuine dotfiles `gh pr create`.
    """
    cmd = "gh pr create --fill && gh issue list -R octocat/hello-world"
    reason = hook_guard.decide(cmd)
    assert reason is not None
    assert "mise run ship" in reason


# --- #265: a separator inside an INERT span is not a separator --------------
#
# The two shapes below are the guard's ONLY measured false positives, recovered
# verbatim from the transcripts (2026-07-13/14) rather than from the audit's
# grouped table — the group row names the rule that fired, not the command.
# Both are read-only diagnostics denied because a `|` inside a quoted regex
# re-anchored `_CMD`. A deny cancels the WHOLE compound command, so these did
# not merely warn: they silently skipped the rest of the pipeline.
_REAL_FALSE_POSITIVES = [
    pytest.param(
        'ps aux | grep -iE "mise run land|dotfiles-setup pr land|devcontainer'
        ' up|[d]evcontainers/cli" | grep -v grep | head',
        id="real-ps-grep-quoted-regex",
    ),
    pytest.param(
        'pgrep -fl "mise run land|dotfiles-setup pr|devcontainer up|verify-local'
        '|verify-ssh" | grep -vi "helper" | head',
        id="real-pgrep-quoted-regex",
    ),
]


@pytest.mark.parametrize(
    "command",
    [
        *_REAL_FALSE_POSITIVES,
        # Single quotes are inert too, and bash gives them no escape semantics.
        pytest.param(
            "rg 'x|gh pr create' docs/",
            id="single-quoted-pipe",
        ),
        # Every separator in the class, not just `|`.
        pytest.param('echo "a;gh pr create"', id="quoted-semicolon"),
        pytest.param('echo "a&&gh pr merge 42"', id="quoted-andand"),
        # A newline inside a quoted span: the shape of a commit message whose
        # body documents the ban on its own line.
        pytest.param(
            "git commit -m 'docs: enforcement\n\nhk run pre-commit --all is banned'",
            id="quoted-newline-commit-body",
        ),
        # A heredoc body is inert text, never commands — the same defect, the
        # other half of the rule doc's "heredoc/quoted CONTENT". Measured live
        # 2026-07-14: appending a note that QUOTED the npx finding was denied.
        pytest.param(
            "cat >> notes.md <<'EOF'\nfallback: || npx --yes foo\nEOF",
            id="heredoc-quoted-delimiter",
        ),
        # The literal must sit at LINE START inside the body: that is the shape
        # the newline separator anchors on, and therefore the only one that is
        # red before the fix. (`<<EOF\nrun: gh pr create` passes even unfixed —
        # `_CMD` needs the separator immediately before the literal, so the
        # `run: ` prefix already spared it. A fixture like that asserts nothing.)
        pytest.param(
            "cat > x.md <<EOF\ngh pr create --fill\nEOF",
            id="heredoc-bare-delimiter",
        ),
        # `<<-` strips leading TABS from the body and the delimiter line — and
        # `_CMD`'s `\\s*` eats that tab, so indenting does not spare it either.
        pytest.param(
            "cat <<-EOF\n\tdevcontainer up --workspace-folder .\n\tEOF",
            id="heredoc-dash-tab-indented",
        ),
    ],
)
def test_separators_inside_inert_spans_do_not_anchor(command: str) -> None:
    r"""A `|`/`;`/`&&`/newline inside quotes or a heredoc is DATA, not syntax.

    `_CMD` anchors on `[;&|\n]`, which made the guard quoting-blind (#265): a
    denied literal after such a character was treated as being at command
    position when no command position existed. Evasion has been measured at 0
    for the guard's whole lifetime while 2 of its 3 denials were this shape, so
    the trade runs one way only — recall for precision, never the reverse.
    """
    assert hook_guard.decide(command) is None


def test_real_npx_denial_was_a_true_positive() -> None:
    """The third measured denial is CORRECT and must survive the #265 fix.

    Recovered verbatim (2026-07-14T19:24:48Z). Unlike its two siblings, the
    `||` here sits OUTSIDE any quote: `npx` really is at command position, a
    fallback invocation after the mise-pinned binary. Pinned separately because
    the audit's grouped table reports "3 denials" as one number — a fix that
    drove the `blocked` bucket to 0 would have looked like a total success while
    silently destroying the guard's only correct denial. The bar is 3 -> 1.
    """
    cmd = (
        "mise exec -- renovate-config-validator --strict 2>&1 | tail -20 "
        "|| npx --yes renovate-config-validator --strict 2>&1 | tail -20"
    )
    reason = hook_guard.decide(cmd)
    assert reason is not None
    assert "mise-installed binary" in reason


def test_masking_trades_the_incidental_eval_catch() -> None:
    """The `eval`/`sh -c` class loses an ACCIDENTAL catch. Deliberate, measured.

    Before #265, `eval "echo x; gh pr create"` was denied — not because the
    guard understood `eval`, but because the quoted `;` anchored `_CMD`. Masking
    removes that, and the third assertion is why it costs nothing real: the bare
    `eval "gh pr create"` was ALREADY allowed, so the class was never covered —
    only its separator-bearing variant was, which no one could have relied on.

    The module has always declared `sh -c`/`eval`/`$(…)`/base64 fail-open (a
    redirect guard, not a sandbox), evasion has measured 0 across the guard's
    lifetime while false positives were 2 of its 3 denials, and the direction
    set for this fix was precision over recall. So this is the trade working as
    intended — pinned here so it stays a decision. If these are ever re-denied,
    it should be because someone chose to guard `eval` properly, not by
    accident.
    """
    assert hook_guard.decide('eval "echo x; gh pr create"') is None
    assert hook_guard.decide('bash -c "cd /x && gh pr merge 42"') is None
    # Never covered even BEFORE the fix — the proof the catch above was
    # incidental rather than a capability this change gave up.
    assert hook_guard.decide('eval "gh pr create"') is None


@pytest.mark.parametrize(
    ("command", "redirect_hint"),
    [
        # A real invocation is never INSIDE a span, so redaction cannot hide it:
        # a quoted ARGUMENT to a denied command keeps the command exposed.
        ("gh pr create --title 'fix: a|b'", "mise run ship"),
        ('gh pr merge 42 --subject "a;b"', "mise run land"),
        # The pull rule matches a literal that may legitimately be quoted — the
        # span's CONTENT must stay readable, so only its separators are neutered.
        (
            'docker pull "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"',
            "mise run sync",
        ),
        # A real separator BEFORE a quoted span still anchors what follows it.
        ('echo "a|b" && gh pr create --fill', "mise run ship"),
        ('echo "a|b" ; devcontainer up --workspace-folder .', "mise run up"),
        # An unterminated quote is not a licence to smuggle: no span is closed,
        # so nothing is redacted and the real separator still anchors.
        ('echo "oops && gh pr create --fill', "mise run ship"),
    ],
)
def test_inert_span_redaction_never_costs_a_true_positive(
    command: str, redirect_hint: str
) -> None:
    """Quoting an ARGUMENT must not launder the command that owns it."""
    reason = hook_guard.decide(command)
    assert reason is not None
    assert redirect_hint in reason


@pytest.mark.parametrize("rule", hook_guard.rules(), ids=lambda r: r.name)
def test_every_rule_carries_a_usable_since_date(rule: hook_guard.Rule) -> None:
    """A rule with no (or a malformed) `since` reports as history forever.

    `command_audit.classify` compares an ISO timestamp prefix against this
    field, so a wrong shape doesn't crash — it silently classifies every
    match as `pre_rule` and the bypass alarm goes dark. Pinned here so a rule
    added without a date fails loudly at authoring time instead.
    """
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", rule.since), rule.since
    # A real date, not just the right shape (e.g. not 2026-13-45).
    landed = dt.date.fromisoformat(rule.since)
    assert landed >= dt.date(2026, 7, 7), "no rule predates the guard itself"
    assert landed <= dt.datetime.now(dt.UTC).date(), "since must not be a future date"


def test_rule_names_are_unique_and_nonempty() -> None:
    """Denials group by rule name in the audit report — collisions merge rows."""
    names = [r.name for r in hook_guard.rules()]
    assert all(names)
    assert len(set(names)) == len(names)


def test_match_returns_the_rule_behind_the_reason() -> None:
    rule = hook_guard.match("gh pr create --fill")
    assert rule is not None
    assert rule.name == "gh pr create"
    assert rule.reason == hook_guard.decide("gh pr create --fill")
    assert hook_guard.match("git status") is None


def test_read_command_real_hook_payload() -> None:
    """[17]: exercise the ACTUAL stdin contract through the CLI subprocess."""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr create --fill"}}
    )
    res = subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", "hook", "pretooluse"],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).parent.parent,
        timeout=120,
    )
    assert res.returncode == 0
    assert '"permissionDecision": "deny"' in res.stdout
    assert "mise run ship" in res.stdout
