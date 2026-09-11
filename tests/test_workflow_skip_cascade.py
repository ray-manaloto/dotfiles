# Copyright (c) 2026 Raymond Manaloto
"""Tests for the transitive-skip-cascade gate (dotfiles_setup.workflow_skip_cascade).

The class this module gates has shipped TWICE in this repo, at two different
depths of the same `needs:` chain (#982 for `smoke-test`, #995 for
`dev-tag`), both times with every gate green. The tests below therefore lean
hardest on the FAIL arm — `.claude/rules/probes-need-a-control-arm.md` rule
2 — by rebuilding the exact pre-fix `dev-tag` shape in a fixture and
requiring the gate to catch it, then requiring the real #995 rescue
(`!cancelled()`) to clear it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import workflow_skip_cascade as wsc

REPO_ROOT = Path(__file__).parent.parent


def _write_workflow(tmp_path: Path, body: str) -> Path:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    path = workflow_dir / "example.yml"
    path.write_text(body, encoding="utf-8")
    return path


# 1. The real tree is clean, post-fix.


def test_real_tree_is_clean() -> None:
    assert wsc.find_violations(REPO_ROOT) == []


# 2. The realistic regression: rebuild the PRE-FIX `dev-tag` shape and
# require a violation naming it.


_PRE_FIX_DEV_TAG_WORKFLOW = """
jobs:
  plan:
    runs-on: ubuntu-latest
    steps: []
  dev-prep:
    needs: [plan]
    if: inputs.tag_strategy == 'pr'
    runs-on: ubuntu-latest
    steps: []
  build:
    needs: [plan, dev-prep]
    if: |
      always()
      && (needs.dev-prep.result == 'skipped' || needs.dev-prep.result == 'success')
    runs-on: ubuntu-latest
    steps: []
  smoke-test:
    needs: [plan, build]
    if: |
      always()
      && needs.build.result == 'success'
    runs-on: ubuntu-latest
    steps: []
  dev-tag:
    needs: [plan, build, smoke-test]
    if: needs.smoke-test.result == 'success'
    runs-on: ubuntu-latest
    steps: []
"""


def test_pre_fix_dev_tag_shape_is_caught(tmp_path: Path) -> None:
    _write_workflow(tmp_path, _PRE_FIX_DEV_TAG_WORKFLOW)
    violations = wsc.find_violations(tmp_path)
    assert any("`dev-tag`" in line for line in violations), violations


# 3. A status function rescues it — both the real #995 fix and always().


_POST_FIX_DEV_TAG_WORKFLOW = _PRE_FIX_DEV_TAG_WORKFLOW.replace(
    "  dev-tag:\n    needs: [plan, build, smoke-test]\n"
    "    if: needs.smoke-test.result == 'success'\n",
    "  dev-tag:\n    needs: [plan, build, smoke-test]\n"
    "    if: |\n"
    "      !cancelled()\n"
    "      && needs.smoke-test.result == 'success'\n",
)


def test_cancelled_rescue_clears_the_violation(tmp_path: Path) -> None:
    _write_workflow(tmp_path, _POST_FIX_DEV_TAG_WORKFLOW)
    violations = wsc.find_violations(tmp_path)
    assert not any("`dev-tag`" in line for line in violations), violations


_ALWAYS_RESCUE_WORKFLOW = _PRE_FIX_DEV_TAG_WORKFLOW.replace(
    "  dev-tag:\n    needs: [plan, build, smoke-test]\n"
    "    if: needs.smoke-test.result == 'success'\n",
    "  dev-tag:\n    needs: [plan, build, smoke-test]\n"
    "    if: |\n"
    "      always()\n"
    "      && needs.smoke-test.result == 'success'\n",
)


def test_always_rescue_is_accepted(tmp_path: Path) -> None:
    _write_workflow(tmp_path, _ALWAYS_RESCUE_WORKFLOW)
    violations = wsc.find_violations(tmp_path)
    assert not any("`dev-tag`" in line for line in violations), violations


# 4. No false positive when nothing in the closure is skippable.


_NOTHING_SKIPPABLE_WORKFLOW = """
jobs:
  plan:
    runs-on: ubuntu-latest
    steps: []
  build:
    needs: [plan]
    runs-on: ubuntu-latest
    steps: []
  test:
    needs: [plan, build]
    runs-on: ubuntu-latest
    steps: []
"""


def test_no_false_positive_when_nothing_is_skippable(tmp_path: Path) -> None:
    _write_workflow(tmp_path, _NOTHING_SKIPPABLE_WORKFLOW)
    assert wsc.find_violations(tmp_path) == []


# 5. A near-miss — a string comparison mentioning "cancelled" is NOT a call.


_NEAR_MISS_WORKFLOW = """
jobs:
  plan:
    runs-on: ubuntu-latest
    steps: []
  dev-prep:
    needs: [plan]
    if: inputs.tag_strategy == 'pr'
    runs-on: ubuntu-latest
    steps: []
  victim:
    needs: [plan, dev-prep]
    if: needs.dev-prep.result == 'cancelled'
    runs-on: ubuntu-latest
    steps: []
"""


def test_string_mention_of_a_status_word_does_not_count_as_a_call(
    tmp_path: Path,
) -> None:
    _write_workflow(tmp_path, _NEAR_MISS_WORKFLOW)
    violations = wsc.find_violations(tmp_path)
    assert any("`victim`" in line for line in violations), violations


def test_status_function_call_regex_rejects_bare_mention() -> None:
    assert not wsc.has_status_function("needs.dev-prep.result == 'cancelled'")
    assert wsc.has_status_function("!cancelled()")
    assert wsc.has_status_function("always() && needs.x.result == 'success'")


# 6. Both `needs:` YAML forms parse — bare string and list.


def test_needs_bare_string_form_parses(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  plan:
    runs-on: ubuntu-latest
    steps: []
  build:
    needs: plan
    runs-on: ubuntu-latest
    steps: []
""",
    )
    graph = wsc.parse_job_graph(path, ".github/workflows/example.yml")
    assert graph["build"].needs == ("plan",)


def test_needs_list_form_parses(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  plan:
    runs-on: ubuntu-latest
    steps: []
  gate:
    runs-on: ubuntu-latest
    steps: []
  build:
    needs: [plan, gate]
    runs-on: ubuntu-latest
    steps: []
""",
    )
    graph = wsc.parse_job_graph(path, ".github/workflows/example.yml")
    assert graph["build"].needs == ("plan", "gate")


# 7. Malformed YAML yields no jobs, not a crash.


def test_malformed_yaml_yields_no_jobs(tmp_path: Path) -> None:
    path = _write_workflow(tmp_path, "jobs: [this is not a mapping")
    graph = wsc.parse_job_graph(path, ".github/workflows/example.yml")
    assert graph == {}
    assert wsc.find_violations(tmp_path) == []


def test_non_dict_document_yields_no_jobs(tmp_path: Path) -> None:
    path = _write_workflow(tmp_path, "- just\n- a\n- list\n")
    graph = wsc.parse_job_graph(path, ".github/workflows/example.yml")
    assert graph == {}


def test_missing_jobs_key_yields_no_jobs(tmp_path: Path) -> None:
    path = _write_workflow(tmp_path, "name: no-jobs-key\n")
    graph = wsc.parse_job_graph(path, ".github/workflows/example.yml")
    assert graph == {}


# The predicate's own control arm — proved directly, not just via its effect
# on find_violations, so a change that neuters assert_predicate_is_live
# itself (rather than the predicate it guards) is also caught.


def test_control_arm_canary_broken_form_is_flagged() -> None:
    violations = wsc.graph_violations(wsc.canary_graph(rescued=False))
    assert any("`victim`" in line for line in violations)


def test_control_arm_canary_rescued_form_is_clean() -> None:
    violations = wsc.graph_violations(wsc.canary_graph(rescued=True))
    assert not any("`victim`" in line for line in violations)


def test_assert_predicate_is_live_passes_on_the_real_predicate() -> None:
    # Must not raise.
    wsc.assert_predicate_is_live()


def test_find_violations_runs_the_control_arm_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sabotage the control arm by monkeypatching the canary to something the
    # real predicate does NOT flag, proving find_violations calls it (and
    # would raise) rather than merely defining it unused.
    _write_workflow(tmp_path, _NOTHING_SKIPPABLE_WORKFLOW)

    def _neutered_canary(*, rescued: bool) -> dict[str, wsc.JobNode]:
        del rescued
        return {"plan": wsc.JobNode("canary", "plan", ())}

    monkeypatch.setattr(wsc, "canary_graph", _neutered_canary)
    with pytest.raises(RuntimeError, match="control-arm FAILED"):
        wsc.find_violations(tmp_path)


def test_main_exits_zero_on_clean_and_one_on_violation(tmp_path: Path) -> None:
    _write_workflow(tmp_path, _NOTHING_SKIPPABLE_WORKFLOW)
    assert wsc.workflow_skip_cascade_main(tmp_path) == 0

    other = tmp_path / "bad"
    _write_workflow(other, _PRE_FIX_DEV_TAG_WORKFLOW)
    assert wsc.workflow_skip_cascade_main(other) == 1
