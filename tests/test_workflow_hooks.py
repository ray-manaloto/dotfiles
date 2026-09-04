# Copyright (c) 2026 Raymond Manaloto
"""Tests for the ADR-0001 enforcer (dotfiles_setup.workflow_hooks).

Seven layers, in the order they earn their keep:

1. **The four real cases**, read out of the actual `.github/` tree so the
   suite fails if reality drifts. Their verdicts come from
   `docs/adr/0001-hk-hooks-do-not-run-in-ci.md` and from each vendor's own
   documentation — never from re-running the predicate's own logic, which
   would be tautological (`tests/AGENTS.md`).
2. **Control arms on the FAIL direction**, in `tmp_path`. A gate verified only
   on a clean tree is decoration
   (`.claude/rules/probes-need-a-control-arm.md`): every "this passes"
   assertion below is paired with a synthetic tree that MUST fail.
3. **The real-tree guard + CLI wiring**, mirroring `test_bash_budget.py`.
4. **`workflow_hooks_main` in both directions** — the function the hk step and
   CI actually invoke. Layers 1-3 shipped without its FAIL arm, so it could be
   reduced to `violations = []` (never asking the question, always exiting 0)
   with everything still green: the exact #274 shape this module prevents.
5. **Route 3 both ways** — its negative arm (a quoted/commented mention is not
   an invocation), its recall arm over every registered entrypoint, and the
   DERIVATION of the mise half from `mise.toml`.
6. **The classification gaps** that stop the predicate's data rotting: an
   unregistered git write inside `python/`, and an opaque local action.
7. **Expansion depth + shell-tokenizing edges** the real tree cannot reach:
   depth >= 2 composites, a cycle, heredoc bodies, an unbalanced quote.

Layers 4-7 exist because each mechanism below was, at review time, mutable to
a permanently-blind version with the whole suite green. Every one is now pinned
by a mutation that was run and observed to fail.

The two negatives among the real cases are as load-bearing as the positives.
`autofix.yml`/autofix is the trap: it is the only job that installs the full
toolchain, so hk IS present and the git hooks ARE written, it sets a `git
config` identity, and it runs `hk run pre-commit --all` twice on purpose — and
it still does not write to git, because `autofix-ci/action` uploads a diff and
autofix.ci's own GitHub App makes the commit off-runner. Any predicate keyed on
"configures git identity", "has hk installed", or "touches GitHub" gets it
wrong, so it is pinned here as a permanent false-positive guard.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import workflow_hooks
from dotfiles_setup.main import setup_parser

REPO_ROOT = Path(__file__).parent.parent

# The ground truth, sourced independently of this module's code:
#
# - `gcc-sha-repair.yml`/repair, `refresh.yml`/lock-refresh and
#   `refresh.yml`/image-lock-pr (#887) commit and push a `git` command
#   directly onto a branch.
# - `refresh.yml`/tool-currency runs only `gh issue create/edit/close` — the
#   GitHub REST API, which never touches the index or a remote.
# - `autofix.yml`/autofix reaches `autofix-ci/action`, whose own `action.yml`
#   documents its `autofix_started` output as "changes have been sent to the
#   autofix server and a fix commit is coming up" — the commit is made by
#   their App, off-runner.
REAL_CASES: tuple[tuple[str, str, bool], ...] = (
    (".github/workflows/gcc-sha-repair.yml", "repair", True),
    (".github/workflows/refresh.yml", "lock-refresh", True),
    (".github/workflows/refresh.yml", "image-lock-pr", True),
    (".github/workflows/refresh.yml", "tool-currency", False),
    (".github/workflows/autofix.yml", "autofix", False),
)


# The complete job inventory of `.github/workflows/`, read out of the tree with
# `parse_jobs` and pinned as an exact set. A floor (`>= len(REAL_CASES)`) would
# let a parser silently drop most of these and still pass — the bad-bound shape
# `.claude/rules/probes-need-a-control-arm.md` names. Adding or losing a job is
# a deliberate, reviewable diff to this list. (#676 added `plan` + `manifest`;
# #887 added `image-lock-pr`.)
EXPECTED_JOBS: frozenset[tuple[str, str]] = frozenset(
    {
        (".github/workflows/autofix.yml", "autofix"),
        (".github/workflows/build-publish.yml", "base-prep"),
        (".github/workflows/build-publish.yml", "build"),
        (".github/workflows/build-publish.yml", "dev-prep"),
        (".github/workflows/build-publish.yml", "dev-tag"),
        (".github/workflows/build-publish.yml", "manifest"),
        (".github/workflows/build-publish.yml", "p2996-prep"),
        (".github/workflows/build-publish.yml", "plan"),
        (".github/workflows/build-publish.yml", "smoke-test"),
        (".github/workflows/ci.yml", "build-publish"),
        (".github/workflows/ci.yml", "changes"),
        (".github/workflows/ci.yml", "ci-gate"),
        (".github/workflows/ci.yml", "contract-preflight"),
        (".github/workflows/ci.yml", "failure-report"),
        (".github/workflows/ci.yml", "lint"),
        (".github/workflows/ci.yml", "promote"),
        (".github/workflows/gcc-sha-repair.yml", "repair"),
        (".github/workflows/ghcr-cleanup.yml", "cleanup"),
        (".github/workflows/image-analysis.yml", "analyze"),
        (".github/workflows/probe-tart-macos.yml", "probe"),
        (".github/workflows/refresh.yml", "image-lock-pr"),
        (".github/workflows/refresh.yml", "lock-refresh"),
        (".github/workflows/refresh.yml", "schema-refresh"),
        (".github/workflows/refresh.yml", "tool-currency"),
    }
)


# The seed plus what `mise_task_git_writers` derives from the real `mise.toml`
# today. Route-3 tests take this explicitly so they exercise the derived half
# without depending on a fixture tree.
ALL_WRITERS: tuple[tuple[str, ...], ...] = (
    *workflow_hooks.FIRST_PARTY_GIT_WRITERS,
    ("mise", "run", "ship"),
    ("mise", "run", "land"),
)


def _real_job(workflow: str, job_name: str) -> workflow_hooks.Job:
    """One job from the real tree, or fail loudly if it has been renamed."""
    path = REPO_ROOT / workflow
    jobs = workflow_hooks.parse_jobs(path, workflow, REPO_ROOT)
    for job in jobs:
        if job.name == job_name:
            return job
    message = f"{workflow} has no job `{job_name}` (found {[j.name for j in jobs]})"
    raise AssertionError(message)


def _hook_violations(root: Path) -> list[str]:
    """Only the HK_SKIP_HOOKS violations, dropping classification gaps.

    A synthetic `tmp_path` tree reaches none of the real repo's actions, so
    every :data:`ACTION_RUNS_GIT_LOCALLY` entry reports as stale there. Those
    gaps are real and tested separately; filtering them out here keeps each
    control arm asserting about the thing it is arming.
    """
    return [line for line in workflow_hooks.find_violations(root) if "job `" in line]


def _write_workflow(root: Path, name: str, body: str) -> None:
    directory = root / workflow_hooks.WORKFLOW_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


def _committing_workflow(env_block: str) -> str:
    """A minimal job that runs `git commit`/`git push` in its own shell."""
    return f"""
name: synthetic
on: workflow_dispatch
jobs:
  writer:
    runs-on: ubuntu-latest
{env_block}    steps:
      - run: |
          git commit -m "bump"
          git push origin HEAD
"""


# ---------------------------------------------------------------------------
# Layer 1 — the four real cases.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("workflow", "job_name", "expected"), REAL_CASES)
def test_real_case_verdicts(workflow: str, job_name: str, *, expected: bool) -> None:
    """Each of the four ground-truth jobs is classified as documented."""
    assert workflow_hooks.job_writes_to_git(_real_job(workflow, job_name)) is expected


def test_lock_refresh_is_reached_only_through_composite_expansion() -> None:
    """The regression that matters most: local-composite expansion, on the real tree.

    `refresh.yml`/lock-refresh is the job ADR-0001 was written about, and it
    contains no `git` command of its own. It reaches
    `peter-evans/create-pull-request` as

        refresh.yml -> $/.github/actions/open-refresh-pr
                    -> peter-evans/create-pull-request

    (`$/` is GitHub's self-repository `uses:` syntax; zizmor 1.30.0's
    `self-repository` audit rewrote this and every other in-repo reference in
    the tree from `./` to `$/` on 2026-08-31 — see `action_id`/`_expand_local`
    in `workflow_hooks.py`, which treat the two prefixes identically.)

    so a check that read only the job's own steps would answer "does not write
    to git" for the single most important case in the repo. The `uses:` list
    is read straight out of the YAML here, independently of `parse_jobs`, so
    the assertion cannot be satisfied by the expansion it is testing.

    Scope, stated so this claims only what it proves: those two edges are ONE
    level of expansion (job -> composite -> vendor leaf), and no composite in
    this repo uses another local composite, so this cannot exercise recursion.
    `test_composite_expansion_recurses_past_one_hop` supplies that depth on a
    fixture tree.
    """
    workflow = ".github/workflows/refresh.yml"
    document = yaml.safe_load((REPO_ROOT / workflow).read_text(encoding="utf-8"))
    own_uses = [
        step.get("uses")
        for step in document["jobs"]["lock-refresh"]["steps"]
        if isinstance(step, dict)
    ]
    assert "peter-evans/create-pull-request" not in own_uses
    assert "$/.github/actions/open-refresh-pr" in own_uses

    job = _real_job(workflow, "lock-refresh")
    assert workflow_hooks.git_write_subcommands(job.run_text) == set()
    assert workflow_hooks.committing_actions(job) == {"peter-evans/create-pull-request"}


def test_gcc_sha_repair_is_reached_through_its_own_shell() -> None:
    """The other positive arrives by a different route: a literal git verb."""
    job = _real_job(".github/workflows/gcc-sha-repair.yml", "repair")
    assert workflow_hooks.git_write_subcommands(job.run_text) == {"commit", "push"}
    assert workflow_hooks.committing_actions(job) == set()


def test_autofix_defeats_every_cheaper_predicate() -> None:
    """The trap case: every surface signal says "writes to git", and it does not.

    Pinned as a false-positive guard — if a future predicate starts keying on
    a `git config` identity or on hk being installed, this fails.
    """
    job = _real_job(".github/workflows/autofix.yml", "autofix")
    assert "git config" in job.run_text
    assert "hk run pre-commit" in job.run_text
    assert any(workflow_hooks.action_id(u) == "autofix-ci/action" for u in job.uses)
    assert workflow_hooks.job_writes_to_git(job) is False


def test_tool_currency_uses_the_github_api_not_git() -> None:
    """`gh issue` is the API — no index, no remote, so no hook can fire."""
    job = _real_job(".github/workflows/refresh.yml", "tool-currency")
    assert "gh issue" in job.run_text
    assert workflow_hooks.job_writes_to_git(job) is False


def test_both_positive_real_jobs_already_declare_the_skip() -> None:
    """The ADR's decision is in force today for both jobs it named."""
    for workflow, job_name, expected in REAL_CASES:
        if expected:
            job = _real_job(workflow, job_name)
            assert job.env[workflow_hooks.SKIP_ENV] == "pre-commit,pre-push"
            assert workflow_hooks.skips_required_hooks(job) is True


# ---------------------------------------------------------------------------
# Layer 2 — control arms: the FAIL direction, on synthetic trees.
# ---------------------------------------------------------------------------


def test_new_committing_job_without_the_skip_fails(tmp_path: Path) -> None:
    """The whole point of the ADR's open gap: a NEW job is caught by shape.

    Nothing about this workflow is registered anywhere — it is not
    `refresh.yml` or `gcc-sha-repair.yml`, and no name is pinned in the
    module. A check that fixed the two known cases by name would pass here,
    which is exactly the weakness the ADR complains about.
    """
    _write_workflow(tmp_path, "brand-new.yml", _committing_workflow(""))
    violations = _hook_violations(tmp_path)
    assert len(violations) == 1
    assert "brand-new.yml" in violations[0]
    assert "job `writer`" in violations[0]
    assert workflow_hooks.SKIP_ENV in violations[0]


def test_same_job_with_the_full_skip_passes(tmp_path: Path) -> None:
    """The paired PASS arm: identical job, one env line, no violation."""
    _write_workflow(
        tmp_path,
        "brand-new.yml",
        _committing_workflow("    env:\n      HK_SKIP_HOOKS: pre-commit,pre-push\n"),
    )
    assert _hook_violations(tmp_path) == []


def test_partial_skip_still_fails(tmp_path: Path) -> None:
    """`pre-commit` alone is what PR #274 shipped — green, and still broken.

    The failing hk steps are `pre-push`'s, and `create-pull-request` pushes as
    well as commits. This is the single most important negative in the suite:
    the previous fix passed every gate the repo had.
    """
    _write_workflow(
        tmp_path,
        "partial.yml",
        _committing_workflow("    env:\n      HK_SKIP_HOOKS: pre-commit\n"),
    )
    assert len(_hook_violations(tmp_path)) == 1


def test_skip_value_is_an_order_independent_union() -> None:
    """Hk unions the value, so order and whitespace must not matter."""

    def job_with(value: str) -> workflow_hooks.Job:
        return workflow_hooks.Job(
            workflow="w.yml",
            name="j",
            run_text="",
            uses=(),
            env={workflow_hooks.SKIP_ENV: value},
        )

    for value in (
        "pre-push,pre-commit",
        " pre-commit , pre-push ",
        "commit-msg,pre-commit,pre-push",
    ):
        assert workflow_hooks.skips_required_hooks(job_with(value)), value
    for value in ("", "pre-push", "pre-commit", "commit-msg"):
        assert not workflow_hooks.skips_required_hooks(job_with(value)), value


def test_workflow_level_env_satisfies_a_job(tmp_path: Path) -> None:
    """A workflow-level env block covers its jobs; the job-level one wins."""
    _write_workflow(
        tmp_path,
        "top-level-env.yml",
        """
name: synthetic
on: workflow_dispatch
env:
  HK_SKIP_HOOKS: pre-commit,pre-push
jobs:
  writer:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin HEAD
""",
    )
    assert _hook_violations(tmp_path) == []


def test_job_env_overrides_a_sufficient_workflow_env(tmp_path: Path) -> None:
    """Control arm for the merge order: a narrowing job env must lose the pass."""
    _write_workflow(
        tmp_path,
        "override.yml",
        """
name: synthetic
on: workflow_dispatch
env:
  HK_SKIP_HOOKS: pre-commit,pre-push
jobs:
  writer:
    runs-on: ubuntu-latest
    env:
      HK_SKIP_HOOKS: pre-commit
    steps:
      - run: git push origin HEAD
""",
    )
    assert len(_hook_violations(tmp_path)) == 1


@pytest.mark.parametrize(
    "run_text",
    [
        "git config --global user.name bot",
        "git add -A",
        "git status --porcelain",
        "git diff --quiet",
        "git merge-base origin/main HEAD",
        "git rev-parse HEAD",
        'echo "remember to git push"',
        "# git commit is what this would do",
        "git commit --no-verify -m x",
        "git push --no-verify origin HEAD",
    ],
)
def test_non_hook_firing_shell_is_not_flagged(run_text: str) -> None:
    """Reads, quoted mentions, and git's own documented bypass are not writes.

    `merge-base` is pinned deliberately: this repo really runs it, and a
    prefix match rather than a token match would read it as `merge`.
    """
    assert workflow_hooks.git_write_subcommands(run_text) == set()


@pytest.mark.parametrize(
    ("run_text", "expected"),
    [
        ("git commit -m x", {"commit"}),
        ("git push", {"push"}),
        ("git -C sub commit -m x", {"commit"}),
        ("git commit -m x\ngit push origin HEAD", {"commit", "push"}),
        ("if ! git push; then exit 1; fi", {"push"}),
        ("GIT_AUTHOR_NAME=bot git commit -m x", {"commit"}),
        ("/usr/bin/git push origin HEAD", {"push"}),
        ("git add -A && git commit -m x", {"commit"}),
    ],
)
def test_hook_firing_shell_is_detected(run_text: str, expected: set[str]) -> None:
    """The recall arm for every shape the negatives above could have masked."""
    assert workflow_hooks.git_write_subcommands(run_text) == expected


def test_first_party_entrypoint_counts_as_a_write(tmp_path: Path) -> None:
    """Route 3: `mise run ship` reaches pr.py's git push, so it needs the skip.

    zero-bash-logic and mise-tasks-only actively steer git writes off the
    shell and behind a task, so without this route finishing that migration
    would silently turn a true positive into a false negative.
    """
    _write_workflow(
        tmp_path,
        "shipper.yml",
        """
name: synthetic
on: workflow_dispatch
jobs:
  shipper:
    runs-on: ubuntu-latest
    steps:
      - run: uv run --project python dotfiles-setup pr ship
""",
    )
    assert len(_hook_violations(tmp_path)) == 1


def test_unknown_action_is_a_classification_gap_not_a_skip_violation(
    tmp_path: Path,
) -> None:
    """An unrecognised action must NOT be answered with "add the env var".

    The env var also silences an explicit `hk run <hook>`, so training an
    operator to set it unconditionally would both dissolve this check and
    turn `autofix.yml`'s two deliberate `hk run pre-commit` steps into
    no-ops. The remedy is a one-line reviewable verdict instead.
    """
    _write_workflow(
        tmp_path,
        "unknown.yml",
        """
name: synthetic
on: workflow_dispatch
jobs:
  mystery:
    runs-on: ubuntu-latest
    steps:
      - uses: some-vendor/some-action@v1
""",
    )
    lines = workflow_hooks.find_violations(tmp_path)
    gaps = [line for line in lines if "some-vendor/some-action" in line]
    assert len(gaps) == 1
    assert "ACTION_RUNS_GIT_LOCALLY" in gaps[0]
    assert workflow_hooks.SKIP_ENV not in gaps[0]
    assert _hook_violations(tmp_path) == []


def test_stale_action_verdict_is_reported(tmp_path: Path) -> None:
    """A verdict nothing exercises rots — mirrors bash_budget's `stale` kind."""
    _write_workflow(
        tmp_path,
        "empty.yml",
        "name: synthetic\non: workflow_dispatch\njobs:\n  noop:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
    )
    lines = workflow_hooks.find_violations(tmp_path)
    assert any("is stale" in line and "actions/checkout" in line for line in lines)


def test_malformed_yaml_yields_no_jobs(tmp_path: Path) -> None:
    """Actionlint owns workflow syntax, so this fails OPEN rather than twice."""
    broken = tmp_path / "broken.yml"
    broken.write_text("jobs: [unclosed\n", encoding="utf-8")
    assert workflow_hooks.parse_jobs(broken, "broken.yml", tmp_path) == []


# ---------------------------------------------------------------------------
# Layer 3 — the real tree, and the CLI seam.
# ---------------------------------------------------------------------------


def test_repo_currently_compliant() -> None:
    """Today's tree passes — the arm the control arms above make meaningful."""
    assert workflow_hooks.find_violations(REPO_ROOT) == []


def test_every_real_job_is_parsed() -> None:
    """The FULL job inventory is pinned, not a floor.

    A `>= len(REAL_CASES)` bound would only rule out near-total loss: a parser
    that silently dropped 15 of the 19 jobs would still pass it. That is the
    bad-bound shape `.claude/rules/probes-need-a-control-arm.md` names — "not
    at this depth" read as "not present". So the exact set is asserted, and
    adding or losing a job is a deliberate, reviewable diff.
    """
    parsed = {
        (job.workflow, job.name)
        for path in sorted((REPO_ROOT / workflow_hooks.WORKFLOW_DIR).glob("*.y*ml"))
        for job in workflow_hooks.parse_jobs(
            path, f"{workflow_hooks.WORKFLOW_DIR}/{path.name}", REPO_ROOT
        )
    }
    assert parsed == EXPECTED_JOBS
    for workflow, job_name, _ in REAL_CASES:
        assert (workflow, job_name) in parsed


def test_cli_wires_end_to_end() -> None:
    """The `workflow-hooks` subcommand runs through main.py and passes clean.

    Kept as the argparse-REGISTRATION seam only; the behavioural rc=0/rc=1
    arms are in-process below, so the gate's verdict does not depend on a `uv`
    sync succeeding. stdout is asserted too: a subcommand that printed nothing
    would otherwise pass.
    """
    result = subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", "workflow-hooks"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "workflow-hooks OK" in result.stdout


def test_subcommand_is_registered_on_the_parser() -> None:
    """`main.setup_parser` really carries the subcommand.

    Deleting the `subparsers.add_parser("workflow-hooks", …)` block leaves the
    dispatch-dict entry intact, so the contract's two main.py tokens stay
    satisfied while the CLI subcommand no longer exists. This is the arm that
    fails on that deletion — argparse exits 2 on an unknown choice.
    """
    args = setup_parser().parse_args(["workflow-hooks"])
    assert args.command == "workflow-hooks"


# ---------------------------------------------------------------------------
# Layer 4 — the entrypoint CI actually runs, in BOTH directions.
# ---------------------------------------------------------------------------


def test_main_returns_zero_on_the_real_tree(capsys: pytest.CaptureFixture[str]) -> None:
    """The PASS arm of the function the hk step and CI invoke."""
    assert workflow_hooks.workflow_hooks_main(REPO_ROOT) == 0
    assert "workflow-hooks OK" in capsys.readouterr().out


def test_main_returns_one_and_names_the_job(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The FAIL arm — the one missing arm that let the entrypoint be gutted.

    `workflow_hooks_main` could be reduced to `violations = []` (never asking
    the question, always returning 0) with the whole suite still green, because
    nothing exercised its rc=1 branch. That is the #274 shape this module
    exists to prevent: a green, vacuous gate.
    """
    _write_workflow(tmp_path, "brand-new.yml", _committing_workflow(""))
    assert workflow_hooks.workflow_hooks_main(tmp_path) == 1
    out = capsys.readouterr().out
    assert workflow_hooks.SKIP_ENV in out
    assert "job `writer`" in out
    assert "ADR-0001" in out


# ---------------------------------------------------------------------------
# Layer 5 — route 3: first-party entrypoints, and their DERIVATION.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "run_text",
    [
        'echo "remember to mise run ship later"',
        "# mise run land",
        "mise run lint",
        "mise run test",
        "echo dotfiles-setup pr ship > /tmp/note",
    ],
)
def test_route_three_ignores_mentions_that_are_not_commands(run_text: str) -> None:
    """The negative arm route 3 was missing entirely.

    Without it, degrading `first_party_git_writers` from command-position
    matching to a naive `entrypoint in run_text` substring test passes the
    whole suite — the module's docstring claims quoted/commented mentions
    cannot trigger it, and nothing checked that claim.
    """
    assert workflow_hooks.first_party_git_writers(run_text, ALL_WRITERS) == set()


@pytest.mark.parametrize(
    ("run_text", "expected"),
    [
        ("mise run ship", "mise run ship"),
        ("mise run land -- 42", "mise run land"),
        ("uv run --project python dotfiles-setup pr land", "dotfiles-setup pr"),
        ("dotfiles-setup pr ship", "dotfiles-setup pr"),
    ],
)
def test_route_three_recall_covers_every_registered_entrypoint(
    run_text: str, expected: str
) -> None:
    """The paired recall arm: a typo in any entry must not be invisible."""
    assert workflow_hooks.first_party_git_writers(run_text, ALL_WRITERS) == {expected}


def _mise_project(root: Path, toml_body: str) -> None:
    (root / "mise.toml").write_text(toml_body, encoding="utf-8")


def test_mise_task_writers_are_derived_not_listed(tmp_path: Path) -> None:
    """A NEW task aliasing a registered writer is caught, transitively.

    Listing `mise run ship`/`mise run land` by name reproduced ADR-0001's own
    complaint one level up: `mise run release`, a thin caller of the SAME
    `dotfiles-setup pr ship`, was a silent false negative that no
    classification gap could report (`pr` is already registered, so nothing
    could fire). The derivation resolves the chain instead.
    """
    _mise_project(
        tmp_path,
        '[tasks.ship]\nrun = "uv run --project python dotfiles-setup pr ship"\n'
        '[tasks.release]\nrun = "mise run ship -- --title x"\n'
        '[tasks.tagger]\nrun = "git push origin --tags"\n'
        '[tasks.nightly]\ndepends = ["release"]\nrun = "echo done"\n'
        '[tasks.lint]\nrun = "uv run --project python dotfiles-setup lint"\n',
    )
    derived = workflow_hooks.mise_task_git_writers(tmp_path)
    assert derived == (
        ("mise", "run", "nightly"),
        ("mise", "run", "release"),
        ("mise", "run", "ship"),
        ("mise", "run", "tagger"),
    )
    assert ("mise", "run", "lint") not in derived


def test_session_review_writer_registration_is_only_the_credential_mutant() -> None:
    """The historical push payload must not classify sibling gate commands."""
    writers = workflow_hooks.mise_task_git_writers(REPO_ROOT)
    assert ("mise", "run", "session-review-mutation-credential-launcher") in writers
    assert ("mise", "run", "session-review-mutation-git-hook-contamination") not in (
        writers
    )
    assert ("mise", "run", "session-review-focused-gate") not in writers
    assert ("mise", "run", "session-review-gate") not in writers


def test_new_task_alias_job_is_flagged(tmp_path: Path) -> None:
    """End-to-end for the derivation: the invented `cut-release` job fails."""
    _mise_project(
        tmp_path,
        '[tasks.ship]\nrun = "uv run --project python dotfiles-setup pr ship"\n'
        '[tasks.release]\nrun = "mise run ship -- --title x"\n'
        '[tasks.lint]\nrun = "uv run --project python dotfiles-setup lint"\n',
    )
    body = """
name: synthetic
on: workflow_dispatch
jobs:
  cut-release:
    runs-on: ubuntu-latest
    steps:
      - run: {command}
"""
    _write_workflow(tmp_path, "cut.yml", body.format(command="mise run release"))
    assert len(_hook_violations(tmp_path)) == 1

    # Control arm: byte-identical job, one non-writing task instead.
    _write_workflow(tmp_path, "cut.yml", body.format(command="mise run lint"))
    assert _hook_violations(tmp_path) == []


def test_derivation_matches_the_real_tree_today() -> None:
    """The real repo derives `automerge`, `land` and `ship`.

    It was `ship`/`land` — the old hand-list — until #369 added `automerge`,
    and the derivation picked the new task up with no edit here. That is the
    mechanism working: `[tasks.automerge]` is a thin caller of
    `dotfiles-setup pr`, an already-registered git-write module, so the chain
    resolves without anyone remembering to extend a list. The classification is
    also correct on the merits — arming auto-merge makes GitHub squash-merge
    and delete the head branch, so it must not be reachable from a workflow.
    """
    assert workflow_hooks.mise_task_git_writers(REPO_ROOT) == (
        ("mise", "run", "automerge"),
        ("mise", "run", "land"),
        ("mise", "run", "session-review-mutation-credential-launcher"),
        ("mise", "run", "ship"),
    )


# ---------------------------------------------------------------------------
# Layer 6 — the classification gaps that stop the data rotting.
# ---------------------------------------------------------------------------


def _python_project(root: Path, module: str, source: str) -> None:
    package = root / "python/src/dotfiles_setup"
    package.mkdir(parents=True, exist_ok=True)
    (package / f"{module}.py").write_text(source, encoding="utf-8")
    (root / workflow_hooks.WORKFLOW_DIR).mkdir(parents=True, exist_ok=True)


def test_unregistered_python_git_write_is_a_gap(tmp_path: Path) -> None:
    """Route 3's "hard stop" really stops — it was untestable in both arms.

    `_python_git_write_modules` could be made to `return set()` unconditionally
    (blind forever) with all tests green, so the mechanism that keeps
    FIRST_PARTY_GIT_WRITERS from falling behind the code had no control arm at
    all. The write verb is assembled at runtime so this file cannot match its
    own detector.
    """
    verb = "pu" + "sh"
    _python_project(
        tmp_path, "releaser", f'ARGV = ["git", "{verb}", "origin", "HEAD"]\n'
    )
    gaps = [
        line
        for line in workflow_hooks.classification_gaps(tmp_path)
        if "releaser" in line
    ]
    assert len(gaps) == 1
    assert "GIT_WRITING_MODULES" in gaps[0]


def test_git_reads_in_python_are_not_a_gap(tmp_path: Path) -> None:
    """The paired negative, which also pins `merge-base` != `merge`.

    A prefix match rather than a quote-delimited alternation would read
    `merge-base` as `merge` and report a gap for every module that computes a
    merge base — which this repo really does.
    """
    _python_project(
        tmp_path,
        "reader",
        'A = ["git", "merge-base", "origin/main", "HEAD"]\n'
        'B = ["git", "status", "--porcelain"]\n'
        'C = ["git", "rev-parse", "HEAD"]\n',
    )
    assert [
        line
        for line in workflow_hooks.classification_gaps(tmp_path)
        if "reader" in line
    ] == []


def test_opaque_local_action_is_a_gap(tmp_path: Path) -> None:
    """A first-party node/docker action must be a reported hole, not silence.

    `_expand_local` reads a local action only through its composite `steps:`,
    and `action_id` returns "" for a `./` reference — so a `runs.using: node20`
    action produced no run_text, no uses AND no gap. It was the module's only
    route where an unrecognised writer answered False in silence.
    """
    _write_workflow(
        tmp_path,
        "tag.yml",
        "name: synthetic\non: workflow_dispatch\njobs:\n  tag:\n"
        "    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: ./.github/actions/push-tag\n",
    )
    action = tmp_path / ".github/actions/push-tag"
    action.mkdir(parents=True)
    (action / "action.yml").write_text(
        "name: push-tag\nruns:\n  using: node20\n  main: dist/index.js\n",
        encoding="utf-8",
    )
    gaps = [
        line for line in workflow_hooks.find_violations(tmp_path) if "push-tag" in line
    ]
    assert len(gaps) == 1
    assert "composite" in gaps[0]
    assert workflow_hooks.SKIP_ENV not in gaps[0]

    # Control arm: the SAME action as a composite is read, and its git push
    # becomes an ordinary HK_SKIP_HOOKS violation with no gap.
    (action / "action.yml").write_text(
        "name: push-tag\nruns:\n  using: composite\n  steps:\n"
        "    - run: git push origin --tags\n      shell: bash\n",
        encoding="utf-8",
    )
    assert [
        line for line in workflow_hooks.find_violations(tmp_path) if "push-tag" in line
    ] == []
    assert len(_hook_violations(tmp_path)) == 1


# ---------------------------------------------------------------------------
# Layer 7 — composite expansion depth, and shell-tokenizing edge cases.
# ---------------------------------------------------------------------------


def _composite(root: Path, name: str, body: str) -> None:
    directory = root / ".github/actions" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "action.yml").write_text(body, encoding="utf-8")


def test_composite_expansion_recurses_past_one_hop(tmp_path: Path) -> None:
    """Depth >= 2, which the real tree cannot exercise.

    `refresh.yml` reaches its vendor in ONE level of expansion (job ->
    composite -> vendor), and no composite in this repo uses another local
    composite — so deleting `_expand_local`'s recursive self-call left the
    suite green. This fixture supplies the depth the tree lacks.
    """
    _write_workflow(
        tmp_path,
        "nested.yml",
        "name: synthetic\non: workflow_dispatch\njobs:\n  j:\n"
        "    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: ./.github/actions/outer\n",
    )
    _composite(
        tmp_path,
        "outer",
        "name: o\nruns:\n  using: composite\n  steps:\n"
        "    - uses: ./.github/actions/inner\n",
    )
    _composite(
        tmp_path,
        "inner",
        "name: i\nruns:\n  using: composite\n  steps:\n"
        "    - uses: peter-evans/create-pull-request@v8\n",
    )
    job = workflow_hooks.parse_jobs(
        tmp_path / workflow_hooks.WORKFLOW_DIR / "nested.yml", "nested.yml", tmp_path
    )[0]
    assert workflow_hooks.committing_actions(job) == {"peter-evans/create-pull-request"}


def test_self_repository_syntax_expands_like_dot_slash(tmp_path: Path) -> None:
    """`$/` self-repository `uses:` syntax must expand like `./`.

    It references the same in-tree action, just resolved without depending
    on runtime filesystem state. zizmor 1.30.0's `self-repository` audit
    rewrote every in-repo reference in this tree from `./` to `$/`
    (2026-08-31); before `_expand_local`/`action_id` learned the prefix, a
    `$/`-referenced vendor write was silently invisible to this classifier.
    """
    _write_workflow(
        tmp_path,
        "dollar.yml",
        "name: synthetic\non: workflow_dispatch\njobs:\n  j:\n"
        "    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: $/.github/actions/outer\n",
    )
    _composite(
        tmp_path,
        "outer",
        "name: o\nruns:\n  using: composite\n  steps:\n"
        "    - uses: peter-evans/create-pull-request@v8\n",
    )
    job = workflow_hooks.parse_jobs(
        tmp_path / workflow_hooks.WORKFLOW_DIR / "dollar.yml", "dollar.yml", tmp_path
    )[0]
    assert workflow_hooks.committing_actions(job) == {"peter-evans/create-pull-request"}


def test_composite_expansion_terminates_on_a_cycle(tmp_path: Path) -> None:
    """The `seen` guard: a self-referential pair must not recurse forever."""
    _write_workflow(
        tmp_path,
        "cyclic.yml",
        "name: synthetic\non: workflow_dispatch\njobs:\n  j:\n"
        "    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: ./.github/actions/a\n",
    )
    _composite(
        tmp_path,
        "a",
        "name: a\nruns:\n  using: composite\n  steps:\n"
        "    - uses: ./.github/actions/b\n",
    )
    _composite(
        tmp_path,
        "b",
        "name: b\nruns:\n  using: composite\n  steps:\n"
        "    - uses: ./.github/actions/a\n    - run: git push\n      shell: bash\n",
    )
    job = workflow_hooks.parse_jobs(
        tmp_path / workflow_hooks.WORKFLOW_DIR / "cyclic.yml", "cyclic.yml", tmp_path
    )[0]
    assert workflow_hooks.git_write_subcommands(job.run_text) == {"push"}


def test_heredoc_body_is_data_not_commands() -> None:
    """Remediation prose in an issue body is not a git write.

    A heredoc body is UNQUOTED stdin data whose newlines are real newlines, so
    it tokenizes exactly like two commands — the false-positive class
    `hook_guard._inert_masked` fixed for the PreToolUse guard in #265. The
    printed remedy for a violation is a free-looking env line, so a false
    positive here trains operators to set the skip unconditionally, after which
    a genuinely new git-writing job passes too.
    """
    body = (
        "gh issue create --body-file - <<'EOF'\n"
        "To fix locally:\n"
        "git commit -am fix\n"
        "git push origin HEAD\n"
        "EOF\n"
    )
    assert workflow_hooks.git_write_subcommands(body) == set()
    written = "cat > /tmp/fix.sh <<'SH'\ngit commit -m x\ngit push origin HEAD\nSH\n"
    assert workflow_hooks.git_write_subcommands(written) == set()


def test_heredoc_fed_to_a_shell_is_still_detected() -> None:
    """The recall arm that stops the fix becoming an under-detect.

    `bash <<'SH' … git push … SH` really does execute its body, so blanket
    redaction would trade a loud false positive for a silent miss — the
    direction that reopens the gap.
    """
    assert workflow_hooks.git_write_subcommands("bash <<'SH'\ngit push\nSH\n") == {
        "push"
    }
    assert workflow_hooks.git_write_subcommands("sh <<EOF\ngit commit -m x\nEOF\n") == {
        "commit"
    }
    assert workflow_hooks.git_write_subcommands("git commit -m x\ngit push") == {
        "commit",
        "push",
    }


def test_unbalanced_quote_falls_open_toward_detecting() -> None:
    """`shell_tokens`' documented fail-open direction, previously unchecked.

    The docstring makes a directional safety claim about the `ValueError`
    branch (miss toward DETECTING a write). A fallback that instead returned
    `[]` — silently classifying every malformed run block as "no git write" —
    would have been invisible.
    """
    malformed = 'git push origin HEAD && echo "unterminated'
    assert "push" in workflow_hooks.shell_tokens(malformed)
    assert workflow_hooks.git_write_subcommands(malformed) == {"push"}
