# Copyright (c) 2026 Raymond Manaloto
"""Every CI job that runs hk's steps must install Claude Code first."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def _tree(tmp_path: Path, workflows: dict[str, str], hk_pkl: str | None = None) -> Path:
    """A minimal repo: one hk.pkl plus the named workflow files."""
    (tmp_path / "hk.pkl").write_text(
        _ALL_STEPS + (hk_pkl if hk_pkl is not None else _HK_PKL), encoding="utf-8"
    )
    directory = tmp_path / wcc.WORKFLOW_DIR
    directory.mkdir(parents=True)
    for name, body in workflows.items():
        (directory / name).write_text(body, encoding="utf-8")
    return tmp_path


def _job(run: str, *, installs: bool) -> str:
    steps = ""
    if installs:
        steps += f"      - uses: ./{wcc.SETUP_ACTION}\n"
    steps += f"      - run: {run}\n"
    return f"jobs:\n  build:\n    steps:\n{steps}"


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


def test_the_live_repo_satisfies_its_own_gate() -> None:
    """Both workflows that run hk install Claude Code today."""
    assert wcc.find_violations(REPO_ROOT) == []


def test_the_entry_point_returns_nonzero_on_a_violation(tmp_path: Path) -> None:
    """Bind the seam the hk step actually runs, not just `find_violations`.

    Stubbing a main to return 0 is the classic way a wired gate stops biting
    while every logic test stays green.
    """
    root = _tree(tmp_path, {"ci.yml": _job("hk run check --all", installs=False)})

    assert wcc.workflow_claude_code_main(root) == 1
    assert wcc.workflow_claude_code_main(REPO_ROOT) == 0


def test_the_cli_subcommand_is_registered() -> None:
    """A module nobody can invoke is not a gate."""
    parser = setup_parser()

    args = parser.parse_args(["workflow-claude-code"])

    assert args.command == "workflow-claude-code"


def test_the_hk_step_is_wired_to_the_cli() -> None:
    """hk.pkl must shell out to the subcommand, and watch hk.pkl itself.

    hk.pkl is in the glob because the hook set is DERIVED from it — an edit
    that makes a new hook spread `allSteps` has to re-run this check.
    """
    source = (REPO_ROOT / "hk.pkl").read_text(encoding="utf-8")

    assert '["workflow_claude_code"] {' in source
    assert "dotfiles-setup workflow-claude-code" in source
    start = source.index('["workflow_claude_code"] {')
    body = source[start : source.index("check = ", start)]
    assert '"hk.pkl"' in body, "the glob must include hk.pkl — the hooks come from it"


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
