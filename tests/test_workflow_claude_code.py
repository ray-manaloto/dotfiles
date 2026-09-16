# Copyright (c) 2026 Raymond Manaloto
"""Every CI job that runs hk's steps must install Claude Code first."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import workflow_claude_code as wcc
from dotfiles_setup.main import setup_parser

REPO_ROOT = Path(__file__).parent.parent.absolute()

_HK_PKL = """\
hooks {
  ["pre-commit"] {
    fix = true
    steps {
      ["no_commit_to_branch"] = Builtins.no_commit_to_branch
      ...allSteps
    }
  }
  ["check"] {
    steps {
      ...allSteps
    }
  }
  ["fix"] {
    fix = true
    steps {
      ...allSteps
    }
  }
  ["commit-msg"] {
    steps {
      ["check_conventional_commit"] = Builtins.check_conventional_commit
    }
  }
}
"""

_ALL_STEPS = """\
local allSteps: Mapping<String, Config.Step> = new Mapping {
  ["fnhook_gates"] {
    check = "uv run --project python dotfiles-setup fnhook-gates"
  }
}
"""

_MISE_TOML = """\
[tasks.lint]
run = "uv run --project python dotfiles-setup lint"

[tasks.fmt]
run = "hk fix"

[tasks.pre-commit]
run = "hk run pre-commit --all"

[tasks.check]
depends = ["pre-commit", "test"]

[tasks.test]
run = "uv run --project python pytest tests/ -x -q"

[tasks.lint-delta]
run = "uv run --project python dotfiles-setup lint-delta"
"""


def _tree(
    tmp_path: Path,
    workflows: dict[str, str],
    hk_pkl: str | None = None,
    mise_toml: str | None = _MISE_TOML,
) -> Path:
    """A minimal repo: one hk.pkl plus the named workflow files."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "hk.pkl").write_text(
        _ALL_STEPS + (hk_pkl if hk_pkl is not None else _HK_PKL), encoding="utf-8"
    )
    if mise_toml is not None:
        (tmp_path / "mise.toml").write_text(mise_toml, encoding="utf-8")
    directory = tmp_path / wcc.WORKFLOW_DIR
    directory.mkdir(parents=True)
    for name, body in workflows.items():
        (directory / name).write_text(body, encoding="utf-8")
    return tmp_path


def _job(run: str, *, installs: bool, install_after: bool = False) -> str:
    steps = ""
    if installs and not install_after:
        steps += f"      - uses: ./{wcc.SETUP_ACTION}\n"
    steps += f"      - run: {run}\n"
    if installs and install_after:
        steps += f"      - uses: ./{wcc.SETUP_ACTION}\n"
    return f"jobs:\n  build:\n    steps:\n{steps}"


def _uses_job(action: str, *, installs_before: bool = False) -> str:
    steps = ""
    if installs_before:
        steps += f"      - uses: ./{wcc.SETUP_ACTION}\n"
    steps += f"      - uses: ./.github/actions/{action}\n"
    return f"jobs:\n  build:\n    steps:\n{steps}"


def _composite(root: Path, name: str, steps: str) -> None:
    directory = root / ".github" / "actions" / name
    directory.mkdir(parents=True)
    (directory / "action.yml").write_text(
        f"name: fixture\nruns:\n  using: composite\n  steps:\n{steps}",
        encoding="utf-8",
    )


def test_a_job_running_hk_without_the_install_is_a_violation(tmp_path: Path) -> None:
    """The motivating case: autofix.yml ran the same hk steps and went red."""
    job = _job("hk run pre-commit --all", installs=False)
    root = _tree(tmp_path, {"autofix.yml": job})

    violations = wcc.find_violations(root)

    assert len(violations) == 1, violations
    assert "autofix.yml" in violations[0]
    assert wcc.SETUP_ACTION in violations[0]


def test_the_same_job_with_the_install_passes(tmp_path: Path) -> None:
    """Control arm: without it the failing arm above proves nothing."""
    job = _job("hk run pre-commit --all", installs=True)
    root = _tree(tmp_path, {"autofix.yml": job})

    assert wcc.find_violations(root) == []


@pytest.mark.parametrize(
    "command",
    [
        "mise run lint",
        "mise run lint -- --timeout 900",
        "mise r lint",
        "mise run fmt",
        "mise run pre-commit",
        "mise run check",
        "hk check --all",
        "hk fix",
        "hk c --all",
        "hk f",
        "hk r check --all",
        "hk --cd . run check --all",
        "hk -j 4 run check",
        "hk --profile slow fix",
        "hk -s check",
        "uv run --project python dotfiles-setup lint",
    ],
)
def test_every_supported_route_to_a_gated_hook_is_seen(
    command: str, tmp_path: Path
) -> None:
    """Each spelling reaches check/fix/pre-commit and needs the setup action."""
    root = _tree(tmp_path, {"ci.yml": _job(command, installs=False)})

    violations = wcc.find_violations(root)

    assert len(violations) == 1, (command, violations)


@pytest.mark.parametrize(
    "command",
    [
        "mise run lint-delta",
        "mise run test",
        "mise reshim",
        "hk validate",
        "hk config",
        "hk completion",
        "hk run commit-msg",
    ],
)
def test_non_hook_routes_and_ungated_hooks_are_not_flagged(
    command: str, tmp_path: Path
) -> None:
    """Token prefixes and unrelated tasks must not create false positives."""
    root = _tree(tmp_path, {"ci.yml": _job(command, installs=False)})

    assert wcc.find_violations(root) == []


@pytest.mark.parametrize("hook", ["check", "pre-commit"])
def test_every_hook_carrying_the_gate_is_covered(hook: str, tmp_path: Path) -> None:
    """`pre-commit` is here because a nested step once hid it from the scan.

    The first version of `hook_bodies` split on the next `["name"]` match, so
    `pre-commit`'s own `["no_commit_to_branch"]` step read as a sibling hook
    and took `...allSteps` with it — leaving `pre-commit` uncovered, which is
    exactly the job this check was written for.
    """
    root = _tree(tmp_path, {"ci.yml": _job(f"hk run {hook} --all", installs=False)})

    assert len(wcc.find_violations(root)) == 1


def test_a_job_that_only_validates_is_not_flagged(tmp_path: Path) -> None:
    """`hk validate` parses the config and runs no steps, so it needs nothing.

    Without this, the check would demand a Claude Code install from a job that
    never invokes the binary — a false positive erodes trust in the gate.
    """
    root = _tree(tmp_path, {"ci.yml": _job("hk validate", installs=False)})

    assert wcc.find_violations(root) == []


def test_a_hook_without_the_gate_step_is_not_flagged(tmp_path: Path) -> None:
    """`commit-msg` does not spread allSteps, so it never runs `claude`."""
    root = _tree(tmp_path, {"ci.yml": _job("hk run commit-msg", installs=False)})

    assert wcc.find_violations(root) == []


def test_a_local_composite_route_is_expanded_in_place(tmp_path: Path) -> None:
    """A job can reach hk entirely through its local composite action."""
    root = _tree(tmp_path, {"ci.yml": _uses_job("x")})
    _composite(root, "x", "    - run: hk fix\n")

    violations = wcc.find_violations(root)

    assert len(violations) == 1, violations


def test_setup_before_a_local_composite_route_passes(tmp_path: Path) -> None:
    """The retained outer setup use precedes the expanded hk step."""
    root = _tree(tmp_path, {"ci.yml": _uses_job("x", installs_before=True)})
    _composite(root, "x", "    - run: hk fix\n")

    assert wcc.find_violations(root) == []


def test_setup_inside_a_composite_after_hk_is_too_late(tmp_path: Path) -> None:
    """Expansion must keep nested ordering, not just collect both step kinds."""
    root = _tree(tmp_path, {"ci.yml": _uses_job("x")})
    _composite(
        root,
        "x",
        f"    - run: hk fix\n    - uses: ./{wcc.SETUP_ACTION}\n",
    )

    violations = wcc.find_violations(root)

    assert len(violations) == 1, violations
    assert "too late" in violations[0]


def test_an_install_after_the_hk_step_is_a_named_order_violation(
    tmp_path: Path,
) -> None:
    """Presence alone is insufficient: Claude must exist when hk starts."""
    job = _job("hk run check --all", installs=True, install_after=True)
    root = _tree(tmp_path, {"ci.yml": job})

    violations = wcc.find_violations(root)

    assert len(violations) == 1, violations
    assert "AFTER the first hk step" in violations[0]
    assert "comes too late" in violations[0]


def test_an_install_before_the_hk_step_satisfies_order(tmp_path: Path) -> None:
    """Control arm for the late-install violation."""
    job = _job("hk run check --all", installs=True)
    root = _tree(tmp_path, {"ci.yml": job})

    assert wcc.find_violations(root) == []


def test_mise_dependency_cycles_terminate_and_preserve_reachable_hooks(
    tmp_path: Path,
) -> None:
    """A hookless a↔b cycle stays empty; c can reach fix through that cycle."""
    hookless_toml = """\
[tasks.a]
depends = ["b"]

[tasks.b]
depends = ["a"]

[tasks.c]
depends = ["a"]
"""
    reaching_toml = """\
[tasks.a]
run = "hk fix"
depends = ["b"]

[tasks.b]
depends = ["a"]

[tasks.c]
depends = ["a"]
"""
    hookless_root = _tree(tmp_path / "hookless", {}, mise_toml=hookless_toml)
    reaching_root = _tree(tmp_path / "reaching", {}, mise_toml=reaching_toml)

    hookless_routes = wcc.mise_task_hooks(hookless_root)
    reaching_routes = wcc.mise_task_hooks(reaching_root)

    assert hookless_routes == {}
    assert reaching_routes["c"] == frozenset({"fix"})


def test_mise_run_list_shape_is_supported(tmp_path: Path) -> None:
    """A list-valued task body contributes every command without raising."""
    mise_toml = """\
[tasks.multi]
run = ["printf harmless", "hk fix"]
"""
    root = _tree(
        tmp_path,
        {"ci.yml": _job("mise run multi", installs=False)},
        mise_toml=mise_toml,
    )

    assert len(wcc.find_violations(root)) == 1


def test_the_derivation_refuses_a_vacuous_pass(tmp_path: Path) -> None:
    """A missing gate step raises instead of exempting every workflow.

    An empty hook set would make `find_violations` return `[]` for any tree —
    a check that can only pass (`probes-need-a-control-arm.md`).
    """
    root = _tree(tmp_path, {}, hk_pkl=_HK_PKL)
    (root / "hk.pkl").write_text(
        _ALL_STEPS.replace("fnhook_gates", "some_other_step") + _HK_PKL,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fnhook_gates"):
        wcc.find_violations(root)


def test_hook_names_come_from_hk_pkl_not_a_hardcoded_list() -> None:
    """The real hk.pkl must yield exactly the hooks that spread the mapping.

    Stated as a property of the file rather than as a literal set, so adding a
    fourth hook that spreads `allSteps` extends coverage automatically instead
    of silently falling outside a frozen list.
    """
    source = (REPO_ROOT / "hk.pkl").read_text(encoding="utf-8")
    spreading = {
        name for name, body in wcc.hook_bodies(source) if "...allSteps" in body
    }

    assert wcc.hooks_running_the_gate(REPO_ROOT) == spreading
    assert "pre-commit" in spreading, "the nested-step parse regression is back"


def test_live_mise_task_routes_are_derived_from_the_tracked_graph() -> None:
    """Live task reachability comes from mise.toml, not a frozen name list.

    ``check`` is the only live task with a ``depends`` key, so its inherited
    ``pre-commit`` hook is the sole live witness that the dependency walk ran.
    """
    routes = wcc.mise_task_hooks(REPO_ROOT)

    assert routes["lint"] == frozenset({"check"})
    assert routes["fmt"] == frozenset({"fix"})
    assert routes["pre-commit"] == frozenset({"pre-commit"})
    assert routes["check"] == frozenset({"pre-commit"})
    for task in ("lint-delta", "test", "rule-sync", "tool-currency", "lock-image"):
        assert task not in routes


def test_a_mise_toml_less_root_has_no_task_routes(tmp_path: Path) -> None:
    """Existing isolated fixtures need no tracked task file to remain valid."""
    root = _tree(
        tmp_path,
        {"ci.yml": _job("hk run check --all", installs=False)},
        mise_toml=None,
    )

    assert wcc.mise_task_hooks(root) == {}
    assert len(wcc.find_violations(root)) == 1


def test_the_live_repo_satisfies_its_own_gate() -> None:
    """Both workflows that run hk install Claude Code today."""
    assert wcc.find_violations(REPO_ROOT) == []


@pytest.mark.parametrize(
    ("workflow_name", "job_name"),
    [("ci.yml", "lint"), ("autofix.yml", "autofix")],
)
def test_live_composite_expansion_retains_setup_before_the_first_gate(
    workflow_name: str, job_name: str
) -> None:
    """Retain-style splicing keeps both live setup uses visible and ordered."""
    path = REPO_ROOT / wcc.WORKFLOW_DIR / workflow_name
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = next(
        job
        for job in wcc.parse_jobs(document, f"{wcc.WORKFLOW_DIR}/{workflow_name}")
        if job.name == job_name
    )
    resolved = wcc.resolve_job(parsed, REPO_ROOT, wcc.mise_task_hooks(REPO_ROOT))
    hooks = wcc.hooks_running_the_gate(REPO_ROOT)

    assert wcc.job_runs_the_gate(resolved, hooks)
    assert wcc.job_installs_claude_code(resolved)
    assert wcc.job_installs_before_gate(resolved, hooks)


def test_the_entry_point_returns_nonzero_on_a_violation(tmp_path: Path) -> None:
    """Bind the seam the hk step actually runs, not just `find_violations`.

    Stubbing a main to return 0 is the classic way a wired gate stops biting
    while every logic test stays green.
    """
    root = _tree(tmp_path, {"ci.yml": _job("hk run check --all", installs=False)})

    assert wcc.workflow_claude_code_main(root) == 1
    assert wcc.workflow_claude_code_main(REPO_ROOT) == 0


def test_malformed_workflow_is_named_without_hiding_another_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail-open YAML handling remains observable and scans later files."""
    root = _tree(
        tmp_path,
        {
            "broken.yml": "jobs: [\n",
            "ci.yml": _job("hk fix", installs=False),
        },
    )

    result = wcc.scan_workflows(root)
    exit_code = wcc.workflow_claude_code_main(root)
    output = capsys.readouterr().out

    assert len(result.violations) == 1
    assert exit_code == 1
    assert ".github/workflows/broken.yml" in output
    assert "ParserError" in output
    assert ".github/workflows/ci.yml" in output


def test_only_a_malformed_workflow_still_returns_zero_and_names_the_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skipped syntax stays actionlint-owned, so it does not determine rc."""
    root = _tree(tmp_path, {"broken.yml": "jobs: [\n"})

    exit_code = wcc.workflow_claude_code_main(root)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert ".github/workflows/broken.yml" in output
    assert "ParserError" in output


def test_the_cli_subcommand_is_registered() -> None:
    """A module nobody can invoke is not a gate."""
    parser = setup_parser()

    args = parser.parse_args(["workflow-claude-code"])

    assert args.command == "workflow-claude-code"


def test_the_hk_step_is_wired_to_the_cli() -> None:
    """hk.pkl must shell out to the subcommand and watch every derivation.

    Each source is in the glob because an edit can change the route map without
    touching this module: hook spreads, tracked tasks, or lint's HK_COMMAND.
    """
    source = (REPO_ROOT / "hk.pkl").read_text(encoding="utf-8")

    assert '["workflow_claude_code"] {' in source
    assert "dotfiles-setup workflow-claude-code" in source
    start = source.index('["workflow_claude_code"] {')
    body = source[start : source.index("check = ", start)]
    assert '"hk.pkl"' in body, "the glob must include hk.pkl — the hooks come from it"
    assert '"mise.toml"' in body, "the glob must include the tracked task graph"
    assert '"python/src/dotfiles_setup/lint.py"' in body, (
        "the glob must include lint.py — dotfiles-setup lint's hook comes from it"
    )


def test_the_composite_action_exists_and_reads_the_pin() -> None:
    """The remedy the violation text names must be a real action.

    A gate whose fix instruction points at nothing is the "redirect to
    nothing" shape `.claude/rules/mise-tasks-only.md` records.
    """
    action = REPO_ROOT / wcc.SETUP_ACTION / "action.yml"

    assert action.is_file(), f"{action} — the violation message points here"
    body = action.read_text(encoding="utf-8")
    assert "schema-vendor pin --tool claude-code" in body, (
        "the composite must READ the pin; a version restated in YAML is the "
        "second pin site pin_parity rejects"
    )
    assert "set -euo pipefail" in body, (
        "a curl|bash without pipefail returns bash's status, so a failed "
        "download would install nothing and report success"
    )
