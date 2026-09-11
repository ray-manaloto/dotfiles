# Copyright (c) 2026 Raymond Manaloto
"""Gate the transitive-skip class: a status rescue only saves ITS OWN job.

A GitHub Actions job whose `if:` contains no status-check function
(`always()`, `!cancelled()`, `failure()`, `success()`) is skipped whenever ANY
job in its transitive `needs` closure is skipped — the implicit `success()`
GitHub ANDs onto every `if:` propagates the skip down the whole chain, and a
rescue on an UPSTREAM job saves only that job, never its descendants.

This repo has shipped that exact defect TWICE, both in
`.github/workflows/build-publish.yml`, both with every gate green because
nothing inspected the `needs` DAG:

- **#982** fixed it for `smoke-test`: `dev-prep` is skipped by design on the
  nightly (`if: inputs.tag_strategy == 'pr'`), and `smoke-test` had no status
  function, so it silently skipped downstream of a job three hops upstream
  that was *working as intended*.
- **#995** fixed it for `dev-tag`, ONE JOB DOWNSTREAM of #982's fix. `build`
  and `smoke-test` each gained their own `always()` rescue, which saves only
  THEMSELVES — `dev-tag`'s `if: needs.smoke-test.result == 'success'` carried
  no status function of its own, so the nightly's `dev-prep` skip kept
  flowing straight through `build` and `smoke-test` (both genuinely
  `success`) and landed on `dev-tag`, which then evaluated the implicit
  `success()` against a graph that was never asked to fail — and skipped.
  `:dev` silently stopped getting its currency marker while the run reported
  `success`. Confirmed on schedule run 34474060289
  (`.github/workflows/build-publish.yml:1054-1072`).

Both incidents are the SAME defect at different depths in the same chain, and
neither was caught by reading the file — a human tracking five jobs' worth of
`always()`/`!cancelled()` rescues by eye is exactly the task a graph walk
does reliably and a person does not. Hence this module: read every workflow's
job graph, and fail when a job downstream of a skippable job carries no
status-check function.

**Skippable is deliberately conservative**: a job counts the moment it
declares an `if:` key at all, regardless of what the condition says. Trying
to evaluate whether a given expression can actually resolve to `false` would
require modelling GitHub's expression language (`inputs.*`, `github.*`,
`needs.*.outputs.*`) — the exact homegrown-parser trap
`.claude/rules/use-tool-builtins.md` warns against. A job that declares `if:
always()` is therefore itself "skippable" by this module's definition even
though it practically never skips; the cost is a small amount of predicate
looseness upstream, not a missed cascade downstream, and looseness in the
SOURCE of a closer flags nothing — it only widens which jobs get checked for
a rescue, and every job in this repo's real closures that is skippable in the
loose sense is also skippable in the strict one (`dev-prep`).

Detecting the rescue itself is a syntactic call check — the identifier
immediately followed by `(` — not a substring search: `needs.x.result ==
'cancelled'` mentions the word `cancelled` but is a plain string comparison,
not a call, and does not rescue anything (that is that shape's own near-miss,
proven in the tests below).

Per `.claude/rules/probes-need-a-control-arm.md` rule 9, this check must
carry its own control arm on every run rather than trusting that its
predicate still discriminates: :func:`assert_predicate_is_live` feeds the
shared violation-finder an in-memory canary reproducing the #995 shape (a
rescue-free job downstream of a skippable one) and requires it to be
flagged, plus the same canary WITH a rescue added and requires it to be
clean. A predicate that stops catching either arm raises before it can ever
report a quiet "OK" — the same failure mode the renovate-config-validator
canary in `.claude/rules/probes-need-a-control-arm.md` rule 9 was built to
close.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``workflow-skip-cascade`` CLI
subcommand and the ``workflow_skip_cascade`` hk step are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOW_DIR = ".github/workflows"

# The four functions GitHub Actions recognises as status-check functions —
# https://docs.github.com/actions/reference/workflows-and-actions/expressions
# lists exactly these under "status check functions". Each one, called, ANDs
# a value other than the implicit success() into the job's evaluation, which
# is what stops a skip upstream from propagating unconditionally.
STATUS_FUNCTIONS: frozenset[str] = frozenset(
    {"always", "cancelled", "failure", "success"}
)

# A CALL, not a mention: the function name immediately followed by `(`
# (optional whitespace between, matching how `if: |` block text can wrap).
# `needs.x.result == 'cancelled'` does not match — `cancelled` there is not
# followed by `(` — which is the near-miss the spec requires this module to
# reject rather than accept.
_STATUS_FN_CALL_RE = re.compile(
    r"\b(?:" + "|".join(sorted(STATUS_FUNCTIONS)) + r")\s*\("
)


@dataclass(frozen=True)
class JobNode:
    """One workflow job, flattened to what the DAG walk below needs."""

    workflow: str
    """Repo-relative path, e.g. `.github/workflows/build-publish.yml`."""

    name: str
    """The job's key, e.g. `dev-tag`."""

    needs: tuple[str, ...]
    """Job keys this job depends on, in declaration order. Empty if none."""

    if_text: str = ""
    """The job's `if:` condition text, verbatim. `""` when the key is absent."""


def _normalize_needs(raw: object) -> tuple[str, ...]:
    """`needs:` accepts a bare string OR a list — both forms parse here."""
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    return ()


def parse_job_graph(workflow_path: Path, repo_relative: str) -> dict[str, JobNode]:
    """One workflow file's jobs, keyed by job name.

    Parsed with ``yaml.safe_load`` — never grepped, per
    ``.claude/rules/use-tool-builtins.md`` and the same call
    ``workflow_hooks.parse_jobs`` makes. A file that does not parse, or that
    carries no ``jobs:`` mapping, yields an empty graph rather than raising:
    ``actionlint`` already gates workflow syntax in both CI and hk, so a
    parse error here would be a duplicate failure with a worse message, and a
    job graph than cannot be walked has nothing for THIS check to say about
    the skip-cascade invariant specifically.
    """
    try:
        doc = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    except yaml.YAMLError, OSError, UnicodeDecodeError:
        return {}
    if not isinstance(doc, dict):
        return {}
    jobs_raw = doc.get("jobs")
    if not isinstance(jobs_raw, dict):
        return {}

    graph: dict[str, JobNode] = {}
    for job_name, job_body in jobs_raw.items():
        if not isinstance(job_body, dict):
            continue
        if_raw = job_body.get("if")
        graph[str(job_name)] = JobNode(
            workflow=repo_relative,
            name=str(job_name),
            needs=_normalize_needs(job_body.get("needs")),
            if_text="" if if_raw is None else str(if_raw),
        )
    return graph


def skippable_jobs(graph: dict[str, JobNode]) -> set[str]:
    """Job names that declare an `if:` key at all (see module docstring)."""
    return {name for name, node in graph.items() if node.if_text != ""}


def has_status_function(if_text: str) -> bool:
    """True when `if_text` CALLS a status-check function.

    A call, never a mention: `needs.x.result == 'cancelled'` names one of the
    four functions but is a plain string comparison and rescues nothing, so it
    must read False here. That near-miss is the whole reason this is a regex on
    `name(` rather than a substring test.
    """
    return bool(_STATUS_FN_CALL_RE.search(if_text))


def _transitive_needs(graph: dict[str, JobNode], name: str) -> set[str]:
    """Every job (not including ``name`` itself) reachable via `needs:`."""
    closure: set[str] = set()
    stack = list(graph.get(name, JobNode("", "", ())).needs)
    while stack:
        dep = stack.pop()
        if dep in closure:
            continue
        closure.add(dep)
        node = graph.get(dep)
        if node is not None:
            stack.extend(node.needs)
    return closure


def graph_violations(graph: dict[str, JobNode]) -> list[str]:
    """The invariant, applied to one already-parsed job graph.

    Kept separate from :func:`find_violations` (which walks the filesystem)
    so :func:`assert_predicate_is_live` can exercise the exact same logic
    against an in-memory canary — no tmp_path, no real workflow file needed
    for the control arm that runs on every invocation.
    """
    skippable = skippable_jobs(graph)
    violations: list[str] = []
    for name, node in sorted(graph.items()):
        if not node.needs:
            continue
        closure = _transitive_needs(graph, name)
        skippable_upstream = closure & skippable
        if skippable_upstream and not has_status_function(node.if_text):
            violations.append(
                f"{node.workflow}: job `{name}` is downstream of skippable "
                f"job(s) {', '.join(sorted(skippable_upstream))} but its "
                f"`if:` carries no status-check function "
                f"({'/'.join(f'{fn}()' for fn in sorted(STATUS_FUNCTIONS))}). "
                f"A skip cascades transitively through `needs:` and a rescue "
                f"on an upstream job saves only that job, never `{name}` — "
                f"see #982 and #995."
            )
    return violations


# ---------------------------------------------------------------------------
# Control arm (probes-need-a-control-arm.md rule 9): assert the CAPABILITY on
# every run, never trust that a green result means the predicate still
# discriminates. The canary reproduces the #995 shape exactly — a job with an
# `if:` downstream, through one hop, of a job that declares its own `if:` —
# and is checked in both the broken and the fixed form.
# ---------------------------------------------------------------------------


def canary_graph(*, rescued: bool) -> dict[str, JobNode]:
    """The #995 shape as an in-memory graph, broken or rescued.

    `victim` sits downstream of `gate` (which declares its own `if:`, so it is
    skippable) via `build`. With `rescued=False` it carries the exact condition
    `dev-tag` shipped with and MUST be flagged; with `rescued=True` it gains
    `!cancelled()` and MUST come back clean. Both arms are asserted on every
    run by :func:`assert_predicate_is_live` — a checker that cannot still catch
    its own motivating defect has no business reporting anything clean.
    """
    gate_if = "github.event.inputs.tag_strategy == 'pr'"
    victim_if = (
        "!cancelled() && needs.build.result == 'success'"
        if rescued
        else "needs.build.result == 'success'"
    )
    return {
        "plan": JobNode("canary", "plan", ()),
        "gate": JobNode("canary", "gate", ("plan",), gate_if),
        "build": JobNode(
            "canary",
            "build",
            ("plan", "gate"),
            "always() && needs.gate.result != 'failure'",
        ),
        "victim": JobNode("canary", "victim", ("plan", "build", "gate"), victim_if),
    }


def assert_predicate_is_live() -> None:
    """Raise if the predicate stops catching the #995 shape, either arm.

    This is the assertion, not a symptom sniff: it does not check a version
    number or a log string that could drift out from under the real logic —
    it feeds the SAME `graph_violations` the real workflows go through a
    fixture engineered to need exactly one true positive and one true
    negative, and requires both.
    """
    broken = graph_violations(canary_graph(rescued=False))
    if not any("`victim`" in line for line in broken):
        false_negative_msg = (
            "workflow-skip-cascade: control-arm FAILED — the predicate did "
            "not flag a canary reproducing the #995 shape (a job downstream "
            "of a skippable job, no status-check function of its own). The "
            "checker is neutered; fix the predicate before trusting any "
            "clean result from it."
        )
        raise RuntimeError(false_negative_msg)
    fixed = graph_violations(canary_graph(rescued=True))
    if any("`victim`" in line for line in fixed):
        false_positive_msg = (
            "workflow-skip-cascade: control-arm FAILED — the predicate still "
            "flagged the canary after adding `!cancelled()`, its documented "
            "rescue. The checker would report a false positive on every real "
            "rescued job; fix the predicate before trusting any result."
        )
        raise RuntimeError(false_positive_msg)


def find_violations(root: Path) -> list[str]:
    """Human-readable violation lines across every workflow; empty is clean.

    Runs :func:`assert_predicate_is_live` first on every call — the control
    arm is not a separate opt-in step, it is load-bearing on the same path
    the hk step and CI take.
    """
    assert_predicate_is_live()
    workflow_dir = root / WORKFLOW_DIR
    violations: list[str] = []
    for path in sorted(workflow_dir.glob("*.y*ml")):
        repo_relative = f"{WORKFLOW_DIR}/{path.name}"
        graph = parse_job_graph(path, repo_relative)
        violations.extend(graph_violations(graph))
    return violations


def workflow_skip_cascade_main(root: Path) -> int:
    """CLI entry: 0 when no job is exposed to an unrescued skip cascade."""
    violations = find_violations(root)
    if not violations:
        sys.stdout.write(
            "workflow-skip-cascade OK: every job downstream of a skippable "
            "job carries a status-check function\n"
        )
        return 0
    sys.stdout.write("workflow-skip-cascade: transitive-skip violations\n\n")
    for line in violations:
        sys.stdout.write(f"  - {line}\n")
    sys.stdout.write(f"\n{len(violations)} violation(s). See #982 and #995.\n")
    return 1
