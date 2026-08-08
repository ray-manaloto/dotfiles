# Copyright (c) 2026 Raymond Manaloto
"""This repo's eval cases — tier 1 (reachability, PR 2) and tier 2 (fixtures, PR 3).

The RUNNER is :mod:`kb_setup.evals`, shared with knowledge-base and consumed
here as the SHA-pinned ``kb-setup`` dependency — the ``kb_setup.currency`` /
``kb_setup.md_budget`` precedent (D2/G4: one implementation, never a second copy
that drifts). Only the CASES are per-repo, because what "resolves" means differs.

Tier 0 (``suites.toml`` ``orchestration.*`` / ``eval.*``) asks *is it declared?*
These ask the next question: **does it resolve?** The two are genuinely
different, and #354 is what the gap costs — a lane can be named in doctrine, in
both repos, with a passing contract, while its CLI is not installed and nothing
says what happens instead.

Tier 2 asks it once more, of the PreToolUse guard: not *is the rule declared*
(tier 0) and not *is the guard wired* (``hook_selfcheck``, which stays and is
this case's precondition), but **does the wired guard DECIDE correctly?**
:data:`GUARD_FIXTURES` is the corpus.

Every gated case carries a ``control`` that must come back FAIL, and the runner
refuses to count a gated case whose control does not fail. Note the trap the KB
side hit first: **a control that returns SKIP is not armed.** Pointing a probe
at something absent usually yields SKIP by design, so the controls below build a
genuinely broken fixture and drive the same code path against it.
"""

from __future__ import annotations

import importlib
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from kb_setup import evals

from dotfiles_setup import hook_guard

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Lane CLIs the orchestration doctrine names in `.claude/CLAUDE.md`. `grok` is
#: deliberately included and is NOT installed (control-armed: `codex`, `agy`,
#: `claude`, `graphify` all resolve; `grok` does not). The doctrine's position is
#: that availability is discovered at run time, so the case asserts the
#: DEGRADATION PATH IS DECLARED — not that grok exists.
DECLARED_LANES = ("codex", "agy", "grok")

#: Tokens whose presence in the doctrine doc constitutes a declared degradation
#: path. `.claude/CLAUDE.md` says grok "is NOT installed, so `codex` is the only
#: viable fixed mode and cross-family review falls to antigravity or Claude".
FALLBACK_TOKENS = ("NOT installed", "fall")

#: The fable-orchestrator plugin's own lane doctor. Version-pinned inside the
#: plugin cache, so it can vanish on plugin GC — hence a LOUD skip, never silent.
DOCTOR_SCRIPT = Path.home().joinpath(
    ".claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.14.0/scripts/doctor.sh"
)

#: A liveness question for the local graph. Deliberately not phrased by echoing
#: node labels — that grades lexical overlap and reports a win that isn't there.
CANARY_QUESTION = "how does the devcontainer get built?"

#: The launcher subcommands the `cc` / `cc-doctor` mise tasks dispatch to. Both
#: live in `kb_setup.launch` and are reached through the pinned CLI's own
#: dispatch chain, which is the thing #391 found broken.
LAUNCHER_SUBCOMMANDS = ("cc", "cc-doctor")

#: What a launcher subcommand prints when dispatch REACHED it and the required
#: argument is absent. Both refuse on a missing `--sibling` before preflight
#: runs, so driving them this way exercises real dispatch and launches nothing,
#: kills no tmux server, and touches no repo.
LAUNCHER_REACHED_MARKER = "--sibling <path> is required"

_MISSING_BINARY = "definitely-not-a-real-binary-xyz"
_MISSING_SUBCOMMAND = "definitely-not-a-subcommand"

_D = evals.GuardFixture
_DENY = evals.Decision.DENY
_ALLOW = evals.Decision.ALLOW

#: The tier-2 corpus for `dotfiles_setup.hook_guard`: every row a real command
#: shape, with the decision it MUST get. Both halves are mandatory (the engine
#: fails a single-direction table) and the control arm runs this table inverted.
#:
#: THE MUST-ALLOW HALF IS THE POINT. Measured over this guard's whole lifetime:
#: bypasses **0**, false positives **2 of 3 recorded denials** (#265 — a `|`
#: inside a quoted regex read as a shell separator). A deny-only corpus would
#: grade the one direction that has never failed, so the allow rows below are
#: chosen to be the shapes a careless narrowing of `_CMD`, `_GATE`, `_WRAPPER`
#: or `_inert_masked` would break first.
#:
#: Every row was probed against the real `decide` before being written down —
#: none is an expectation asserted from reading the regex.
GUARD_FIXTURES: tuple[evals.GuardFixture, ...] = (
    # --- must DENY: one row per rule shape, so a rule cannot silently die
    _D("npx agnix", _DENY, "npx — use the mise-pinned binary"),
    _D("chezmoi apply", _DENY, "chezmoi apply is devcontainer-only"),
    _D("chezmoi update", _DENY, "chezmoi update is devcontainer-only"),
    _D("hk run check --all", _DENY, "raw hk has no timeout — use `mise run lint`"),
    _D("hk run pre-commit --all --stash none", _DENY, "the 7-hour-hang shape"),
    _D(
        "devcontainer up --workspace-folder .",
        _DENY,
        "misses the task's env + hash guard",
    ),
    _D(
        "devcontainer build --workspace-folder .",
        _DENY,
        "overlay build needs the task env",
    ),
    _D(
        "docker pull ghcr.io/ray-manaloto/dotfiles-devcontainer:dev",
        _DENY,
        "classic pull wedges on the ~38GB blob — use `mise run sync`",
    ),
    _D("gh pr create --fill", _DENY, "dotfiles PR — `mise run ship`"),
    _D("gh pr merge 123 --squash", _DENY, "dotfiles PR — `mise run land`"),
    _D(
        "gh pr merge 236 --auto --squash",
        _DENY,
        "the ARMING shape (#369) — must redirect to `mise run automerge`, the "
        "one thing `land` cannot do; until that verb existed this redirect "
        "pointed at a task that refuses an OPEN PR",
    ),
    _D(
        "gh pr create -R ray-manaloto/knowledge-base --fill",
        _DENY,
        "KB PR — must redirect to kb-ship, NOT ship (the #349 defect)",
    ),
    _D(
        "gh pr merge -R ray-manaloto/knowledge-base 3 --squash",
        _DENY,
        "KB PR — must redirect to kb-land, NOT land (the #349 defect)",
    ),
    _D(
        "cd /tmp && gh pr create --fill",
        _DENY,
        "a cd prefix does not launder it (#264)",
    ),
    _D("nohup mise run lint > /tmp/lint.log 2>&1", _DENY, "hand-detached mise task"),
    _D("mise run ship &", _DENY, "`&`-detached Mac-side task gets REAPED when idle"),
    _D("gh run watch 1234567890", _DENY, "reports prematurely — see gh-cli-watch.md"),
    _D("gh pr checks 123 --watch", _DENY, "ship/land already watch"),
    _D(
        "mise run lint 2>&1 | tail -40",
        _DENY,
        "the pipe returns tail's 0, masking a failed or killed gate",
    ),
    _D(
        "uv run --project python pytest tests/ -x -q | tail -20",
        _DENY,
        "same, reached through the canonical uv runner prefix",
    ),
    _D("dotfiles-setup verify run | head -30", _DENY, "same, for the contract engine"),
    # --- must ALLOW: the false-positive surface, plus the canonical commands
    _D(
        'grep -iE "npx|devcontainer up|gh pr create" docs/',
        _ALLOW,
        "#265 VERBATIM — a `|` inside a quoted regex is not a shell separator; "
        "2 of this guard's 3 all-time denials were this shape",
    ),
    _D('echo "gh pr merge is denied here"', _ALLOW, "prose describing the ban"),
    _D(
        "cat <<'EOF' > /tmp/note.md\ngh pr merge 1 --squash\nEOF",
        _ALLOW,
        "a heredoc BODY is stdin data, never a command position",
    ),
    _D("git log --oneline | head -20", _ALLOW, "a non-gate pipe is untouched"),
    _D(
        "rg 'pytest' docs/ | head",
        _ALLOW,
        "`pytest` is the one _GATE token that is also ordinary prose here",
    ),
    _D(
        "mise run lint && docker ps | tail -5",
        _ALLOW,
        "the pager rule must not run PAST the gate's own segment",
    ),
    _D(
        'mise run lint > /tmp/out.log 2>&1; echo "rc=$?" >> /tmp/out.log',
        _ALLOW,
        "the PRESCRIBED replacement shape — denying it would redirect to nothing",
    ),
    _D(
        "gh pr create -R some-other/repo --fill",
        _ALLOW,
        "a sibling repo has NO canonical task, so a deny would block real work",
    ),
    _D("gh pr merge -R some-other/repo 5", _ALLOW, "same, for merge"),
    _D("gh pr view 123 --json state", _ALLOW, "read-only gh is untouched"),
    _D(
        "gh pr checks 123 --json bucket",
        _ALLOW,
        "the one-shot read IS the prescribed form",
    ),
    _D("chezmoi diff", _ALLOW, "read-only chezmoi is fine on the host"),
    _D("chezmoi cat ~/.zshrc", _ALLOW, "read-only chezmoi is fine on the host"),
    _D(
        "docker pull python:3.14-slim",
        _ALLOW,
        "only the devcontainer image is guarded",
    ),
    _D("docker ps", _ALLOW, "diagnostic docker is untouched"),
    _D("mise run lint", _ALLOW, "the canonical gate itself"),
    _D("mise run ship", _ALLOW, "the canonical PR task itself"),
    _D("mise run fmt", _ALLOW, "the canonical fix path"),
    _D(
        "uv run --project python pytest tests/ -x -q",
        _ALLOW,
        "the documented runner — the permission engine UNWRAPS it, so a pytest "
        "rule would deny exactly this (why no such rule exists)",
    ),
    _D("git status --short", _ALLOW, "an unrelated command is untouched"),
)


def _broken_graph_canary() -> evals.Outcome:
    """Control arm: drive the canary against a graph that cannot answer.

    A directory holding a present-but-meaningless ``graph.json`` passes the
    existence gate — so this is NOT a skip — and then makes the real
    ``graphify query`` fail, which is the branch the canary must be shown to
    reach.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph = root / "graphify-out" / "graph.json"
        graph.parent.mkdir(parents=True)
        graph.write_text("not a graph")
        return evals.graphify_canary(root, CANARY_QUESTION, timeout=30)


def _broken_doctor() -> evals.Outcome:
    """Control arm: a doctor script that reports a failing lane.

    Deliberately distinct from the absent-script case. "We could not look"
    (SKIP) and "we looked and a lane is broken" (FAIL) must never collapse into
    each other — the first is the inert declaration wearing a green badge.
    """
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "doctor.sh"
        script.write_text(
            "#!/usr/bin/env bash\necho '0 ok, 0 warnings, 1 failures'\nexit 1\n"
        )
        return evals.doctor_health(script, timeout=30)


def _launcher_dispatches(subcommands: Sequence[str]) -> evals.Outcome:
    """Does the pinned ``kb-setup`` CLI actually route each subcommand?

    #391: this repo's pin named a revision that predates ``kb_setup/launch.py``,
    so ``mise run cc`` had never once worked — while every gate stayed green,
    because a pin is a DECLARATION and no gate ever invoked the thing.

    The rc is **2 in both directions** — the handler's missing-argument refusal
    and the CLI's own ``unknown command`` both exit 2 — so grading rc here would
    be a probe that cannot fail. :data:`LAUNCHER_REACHED_MARKER` is the only
    discriminator, and it is printed by the handler itself.
    """
    exe = shutil.which("kb-setup")
    if exe is None:
        return evals.fail(
            "kb-setup does not resolve — the `cc` task runs it through "
            "`uv run --project python`, so this is the launcher being dead"
        )
    unreachable = []
    for sub in subcommands:
        rc, out = evals.run_command([exe, sub])
        if LAUNCHER_REACHED_MARKER not in out:
            first = next(iter(out.strip().splitlines()), "(no output)")
            unreachable.append(f"{sub} (rc={rc}): {first}")
    if unreachable:
        return evals.fail(
            "the pinned kb-setup CLI does not dispatch: " + "; ".join(unreachable)
        )
    return evals.ok(
        f"{len(subcommands)} launcher subcommand(s) dispatch through {exe}: "
        + ", ".join(subcommands)
    )


def _launcher_dispatch_control() -> evals.Outcome:
    """Control arm: the same probe against a subcommand that cannot exist.

    This is #391's measured failure verbatim — ``kb-setup: unknown command`` —
    so the control reproduces the real regression rather than a mutation that
    could not happen.
    """
    return _launcher_dispatches((_MISSING_SUBCOMMAND,))


def _graphify_installed() -> evals.Outcome | None:
    """Environment gate: graphify is HOST-ONLY, so the canary cannot run in-container.

    Found by `sync-full` (the devcontainer smoke): inside the container this
    case failed with `rc=-2, No such file or directory: 'graphify'` and took
    the whole postCreate run with it. That is "does not apply here", not "the
    graph is broken".

    It must be a PRECONDITION, not a SKIP inside the probe: the control arm
    drives the same code path, so it would skip too, and the runner would
    correctly mark the case UNARMED and turn the run red. The precondition is
    evaluated BEFORE the control-arm rule for exactly this reason.
    """
    if shutil.which("graphify") is None:
        return evals.skip(
            "graphify is not installed in this environment — it is host-only in "
            "this repo (mise.toml), so the canary cannot look, which is not the "
            "same as the graph having nothing to say"
        )
    return None


def cases(repo_root: Path, *, doctor_script: Path | None = None) -> list[evals.Case]:
    """Build this repo's tier-1 cases."""
    doctor = doctor_script if doctor_script is not None else DOCTOR_SCRIPT
    fallback_doc = repo_root / ".claude" / "CLAUDE.md"

    return [
        evals.Case(
            name="tier1.lanes-declared-or-degraded",
            description=(
                "every lane the doctrine names either resolves on PATH, or its "
                "degradation path is written down"
            ),
            probe=lambda: evals.declared_lanes_reconcile(
                DECLARED_LANES,
                fallback_doc=fallback_doc,
                fallback_tokens=FALLBACK_TOKENS,
            ),
            # The fallback doc pointed at a file that does not exist: "we cannot
            # read the fallback" must never resolve to "the fallback is declared".
            control=lambda: evals.declared_lanes_reconcile(
                (_MISSING_BINARY,),
                fallback_doc=repo_root / ".claude" / "does-not-exist.md",
                fallback_tokens=FALLBACK_TOKENS,
            ),
        ),
        evals.Case(
            name="tier1.shared-engine-resolves",
            description=(
                "the SHARED kb_setup engine this repo depends on is importable — "
                "md_budget and the eval runner both come from it, so a broken pin "
                "silently disarms two gates at once"
            ),
            probe=_kb_setup_importable,
            control=_kb_setup_import_control,
        ),
        evals.Case(
            name="tier1.cc-subcommand-dispatches",
            description=(
                "the `cc` / `cc-doctor` mise tasks reach a real handler in the "
                "PINNED kb-setup — #391: the pin predated `launch.py`, so the "
                "launcher was dead for its whole life and no gate noticed, "
                "because every gate graded the declaration"
            ),
            probe=lambda: _launcher_dispatches(LAUNCHER_SUBCOMMANDS),
            control=_launcher_dispatch_control,
        ),
        evals.Case(
            name="tier1.graph-answers",
            description=(
                "the local graph does not merely exist — it returns a non-empty "
                "answer (rc=0 with empty output is a graph that reads as healthy "
                "and knows nothing)"
            ),
            probe=lambda: evals.graphify_canary(repo_root, CANARY_QUESTION),
            control=_broken_graph_canary,
            precondition=_graphify_installed,
        ),
        evals.Case(
            name="tier1.lane-health",
            description=(
                "the plugin's own doctor.sh reports every installed lane "
                "authenticated with model access"
            ),
            probe=lambda: evals.doctor_health(doctor),
            control=_broken_doctor,
            # doctor.sh has NO offline mode: whenever a lane's CLI is present it
            # fires a real API call, and it exits `[ FAIL -eq 0 ]` so warnings
            # pass. It is the live half ENTIRELY and can never join the free
            # gated tier — the offline probes above are that tier.
            live=True,
        ),
        evals.guard_table_case(
            "tier2.guard-fixtures",
            "the PreToolUse guard decides every fixture row as declared — both "
            "directions, since false positives are the only defect class ever "
            "measured in it (bypasses all-time: 0)",
            GUARD_FIXTURES,
            hook_guard.decide,
        ),
    ]


#: The shared entry points this repo consumes from the pinned kb_setup package.
#: Both gates depend on them: `md_size_budget` shells out to `kb-setup
#: md-budget`, and `mise run eval` imports the runner.
SHARED_MODULES = ("kb_setup.evals", "kb_setup.md_budget")


def _importable(names: Sequence[str]) -> evals.Outcome:
    """FAIL naming every module in ``names`` that cannot be imported."""
    missing = []
    for name in names:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        return evals.fail(f"kb_setup module(s) not importable: {', '.join(missing)}")
    return evals.ok(f"{len(names)} shared module(s) import: {', '.join(names)}")


def _kb_setup_importable() -> evals.Outcome:
    """Both shared entry points must actually be reachable, not just pinned.

    Asserting the pin exists is tier 0's job and is not the same question: a pin
    can name a commit that predates the module, and then `md_size_budget` and
    `mise run eval` both fail at the seam rather than at the declaration.
    """
    return _importable(SHARED_MODULES)


def _kb_setup_import_control() -> evals.Outcome:
    """Control arm: the same probe against a module that cannot exist."""
    return _importable(("kb_setup.definitely_not_a_module",))
