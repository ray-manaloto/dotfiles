# Copyright (c) 2026 Raymond Manaloto
"""Dry-run every saved Claude Workflow script with the repo-pinned Bun."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

REPO_ROOT = Path(__file__).parent.parent.absolute()
WORKFLOWS = REPO_ROOT / ".claude" / "workflows"
AGENTS = REPO_ROOT / ".claude" / "agents"
SYNTAX_ERROR = REPO_ROOT / "tests" / "fixtures" / "workflows_js" / "syntax-error.js"

_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_AGENT_TYPE_CALL_SITE_RE = re.compile(r"agentType:\s*'([^']+)'")


def _known_agent_types() -> set[str]:
    """Derive the registry surface from the tree, never a hand-copied list.

    Two real sources feed a call's `agentType`, and a fixed literal set
    cannot see either drift: (1) a repo-local subagent file's frontmatter
    `name:` IS the registry key the harness reads (`sub-agents.md`), so a
    renamed or deleted `.claude/agents/*.md` changes this set automatically;
    (2) a plugin-qualified name (`fable-orchestrator:codex-implementer`) has
    no local file, so it is read from the literal `agentType: '...'` call
    sites in the saved workflow scripts themselves. `general-purpose` is kept
    unconditionally: it is the harness's own default agentType when a call
    site omits the option (`modernization-audit.js` never sets one), so no
    grep of an explicit literal can discover it.
    """
    names = {
        match.group(1)
        for path in sorted(AGENTS.glob("*.md"))
        for match in [_NAME_RE.search(path.read_text(encoding="utf-8"))]
        if match
    }
    call_sites = {
        match.group(1)
        for path in sorted(WORKFLOWS.glob("*.js"))
        for match in _AGENT_TYPE_CALL_SITE_RE.finditer(path.read_text(encoding="utf-8"))
    }
    return names | call_sites | {"general-purpose"}


KNOWN_AGENT_TYPES = _known_agent_types()
KNOWN_LABEL_PREFIXES = {
    "gap",
    "load",
    "find",
    "verify",
    "synthesize",
    "critique",
    "codex-implementer",
    "gate-runner",
    "cold-reviewer",
    "codex-adversarial-critic",
    "graphify-researcher",
    "graphify-operator",
    "codex-staleness-auditor",
}

ARGS = {
    "specFile": str(REPO_ROOT / ".agent" / "spec-A1.md"),
    "premises": "## PREMISES\n- L1 — fixture",
    "attestation": "",
    "effort": "xhigh",
    "timeout": 3600,
    "verify": ["mise run lint", "mise run verify"],
    "reviewRef": "",
    "criticProposal": "proposal text",
    "issue": "#994",
    "branch": "feat/test",
    "tasks": [
        {"name": "health", "cmd": "mise run graphify-health"},
        {"name": "update", "cmd": "mise run graphify-update", "expectRc": 0},
    ],
    "researchBrief": "inventory installed graphify",
    "staleTerms": ["old graphify claim"],
    "modules": [],
    "rules": [],
    "groups": [],
    "gapSources": [],
    "host": {
        "claudeCode": "fixture",
        "kbChangelogTop": "fixture",
        "codexCli": "fixture",
        "plugins": {"fable-orchestrator": "fixture"},
    },
    "pins": {},
    "corpus": {
        "claudeCodeDocs": str(REPO_ROOT),
        "codexDocs": str(REPO_ROOT),
        "toolTrees": {},
    },
    "repoRoot": str(REPO_ROOT),
    "stamp": "fixture",
    "epic": "#993",
    "auditDir": str(REPO_ROOT / ".agent" / "audit"),
    "rawDir": str(REPO_ROOT / ".agent" / "raw"),
    "reportMd": str(REPO_ROOT / ".agent" / "report.md"),
    "reportToml": str(REPO_ROOT / ".agent" / "report.toml"),
    "maxRounds": 1,
    "reuseFindings": False,
}

_STUBS = r"""
const calls = []
const events = []
const phase = (title) => events.push({ kind: 'phase', title })
const log = (message) => events.push({ kind: 'log', message })
const budget = () => ({ remaining: 1000 })
const workflow = async (fn) => fn()
const parallel = async (tasks) => Promise.all(tasks.map((task) => task()))
const pipeline = async (items, ...stages) => {
  const results = []
  for (let index = 0; index < items.length; index += 1) {
    let previous = await stages[0](items[index], index)
    for (let stage = 1; stage < stages.length; stage += 1) {
      previous = await stages[stage](previous, items[index], index)
    }
    results.push(previous)
  }
  return results
}
const schemaValue = (schema) => {
  if (!schema) return {}
  if (schema.type === 'string') return 'stub'
  if (schema.type === 'number') return 0
  if (schema.type === 'boolean') return true
  if (schema.type === 'array') return []
  if (schema.type === 'object') {
    const value = {}
    for (const key of schema.required || []) {
      value[key] = schemaValue(schema.properties[key])
    }
    return value
  }
  return null
}
const agent = async (_prompt, options = {}) => {
  if (options.schema !== undefined && options.schema.type !== 'object') {
    throw new Error(
      `agent() schema root must be type 'object', got '${options.schema.type}'`
    )
  }
  const label = options.label || 'general-purpose'
  calls.push({ label, agentType: options.agentType || 'general-purpose' })
  if (label === 'codex-implementer') return 'CODEX REPORT\nCOMMIT: abcdef1234567'
  if (label === 'gate-runner') {
    return {
      gates: args.verify.map((cmd, index) => ({
        cmd, rc: 0, log: `/tmp/gate-${index}.log`, firstFailure: '',
      })),
    }
  }
  if (label === 'graphify-operator') {
    return {
      tasks: args.tasks.map((task, index) => ({
        name: task.name,
        rc: task.expectRc || 0,
        log: `/tmp/task-${index}.log`,
        delta: '0/0/0',
      })),
    }
  }
  return schemaValue(options.schema)
}
"""


def _wrapped_source(source: str) -> str:
    """Wrap one saved script in an async dry-run runtime."""
    stripped = source.replace("export const meta", "const meta", 1)
    return (
        f"const args = {json.dumps(ARGS)}\n"
        + _STUBS
        + "\nconst run = async () => {\n"
        + stripped
        + "\n}\n"
        + "const result = await run()\n"
        + "console.log(JSON.stringify({ result, calls, events }))\n"
    )


def _bun_run(source: str, target: Path) -> subprocess.CompletedProcess[str]:
    """Execute generated JavaScript through the repository's Bun pin."""
    target.write_text(_wrapped_source(source), encoding="utf-8")
    return subprocess.run(
        ["mise", "exec", "--", "bun", "run", str(target)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_every_saved_workflow_dry_runs_with_known_agents(tmp_path: Path) -> None:
    """Saved scripts parse, execute, and call only known registry surfaces."""
    workflows = sorted(WORKFLOWS.glob("*.js"))
    assert workflows
    for index, workflow_path in enumerate(workflows):
        source = workflow_path.read_text(encoding="utf-8")
        assert source.startswith("export const meta = {")
        assert "Date.now()" not in source
        assert "Math.random()" not in source
        assert "new Date()" not in source

        result = _bun_run(source, tmp_path / f"workflow-{index}.js")

        assert result.returncode == 0, (
            f"{workflow_path.name} failed under pinned Bun\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        payload = cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))
        calls = cast("list[dict[str, str]]", payload["calls"])
        assert calls, f"{workflow_path.name} made no agent calls"
        for call in calls:
            assert call["agentType"] in KNOWN_AGENT_TYPES
            assert call["label"].split(":", 1)[0] in KNOWN_LABEL_PREFIXES


def test_top_level_syntax_error_fails_under_pinned_bun(tmp_path: Path) -> None:
    """The dry-run harness has a red arm; it cannot bless invalid JavaScript."""
    result = _bun_run(
        SYNTAX_ERROR.read_text(encoding="utf-8"), tmp_path / "syntax-error.js"
    )
    assert result.returncode != 0
    assert result.stderr


GATED_IMPLEMENTATION = WORKFLOWS / "gated-implementation.js"


def test_root_array_schema_is_rejected_at_agent_boundary(tmp_path: Path) -> None:
    """Guard negative arm: a root-array `agent()` schema must be rejected.

    Every shipped workflow already passes this guard with its object-rooted
    schema (`test_every_saved_workflow_dry_runs_with_known_agents` is the
    positive arm). This reproduces the actual regression class — GATES
    flipped back to a bare root array, exactly the shape that made
    `/gated-implementation` abort mid-run — with only the root `type`
    changed, and confirms the shared `agent()` stub rejects it before
    dispatch rather than accepting whatever it is handed.
    """
    source = GATED_IMPLEMENTATION.read_text(encoding="utf-8")
    mutated = source.replace(
        "const GATES = {\n  type: 'object',\n  required: ['gates'],\n",
        "const GATES = {\n  type: 'array',\n  required: ['gates'],\n",
        1,
    )
    assert mutated != source, "mutation must actually change the schema root"
    result = _bun_run(mutated, tmp_path / "gates-root-array.js")
    assert result.returncode != 0, "a root-array schema must fail, not dry-run clean"
    assert "type 'object'" in result.stderr


def _custom_stub_source(
    source: str, args: Mapping[str, object], agent_body: str
) -> str:
    """Wrap `source` in a minimal dry-run runtime with test-supplied `agent()`.

    For scenarios `_STUBS`'s fixed per-label branches cannot produce (a
    missing COMMIT line, a null gate/review result).
    """
    stripped = source.replace("export const meta", "const meta", 1)
    stub = (
        "\nconst calls = []\n"
        "const events = []\n"
        "const phase = (title) => events.push({ kind: 'phase', title })\n"
        "const log = (message) => events.push({ kind: 'log', message })\n"
        "const agent = async (_prompt, options = {}) => {\n"
        "  const label = options.label || 'general-purpose'\n"
        "  calls.push({ label, agentType: options.agentType || 'general-purpose' })\n"
        f"  {agent_body}\n"
        "}\n"
    )
    return (
        f"const args = {json.dumps(args)}\n"
        + stub
        + "\nconst run = async () => {\n"
        + stripped
        + "\n}\n"
        + "const result = await run()\n"
        + "console.log(JSON.stringify({ result, calls, events }))\n"
    )


def _bun_run_wrapped(wrapped: str, target: Path) -> subprocess.CompletedProcess[str]:
    """Execute already-wrapped JavaScript through the repository's Bun pin."""
    target.write_text(wrapped, encoding="utf-8")
    return subprocess.run(
        ["mise", "exec", "--", "bun", "run", str(target)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


_NO_COMMIT_REPORT = "CODEX REPORT\\n(no commit — apply failed)"
_GATES_OK_BODY = (
    f"if (label === 'codex-implementer') return '{_NO_COMMIT_REPORT}'\n"
    "  if (label === 'gate-runner') {\n"
    "    return { gates: args.verify.map((cmd, index) => (\n"
    "      { cmd, rc: 0, log: `/tmp/gate-${index}.log`, firstFailure: '' }\n"
    "    )) }\n"
    "  }\n"
)


def test_m1_missing_commit_and_no_review_ref_skips_review_and_critique(
    tmp_path: Path,
) -> None:
    """M1 FAIL arm (the bug as reported): no commit and no reviewRef.

    An implementer report with no `COMMIT:` line and no caller-supplied
    `reviewRef` must not dispatch a cold review of an empty ref, and the
    returned status must discriminate this from a real completed review.
    """
    args = {**ARGS, "reviewRef": ""}
    source = GATED_IMPLEMENTATION.read_text(encoding="utf-8")
    wrapped = _custom_stub_source(source, args, _GATES_OK_BODY + "  return null")
    result = _bun_run_wrapped(wrapped, tmp_path / "m1-no-commit.js")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))
    run_result = cast("dict[str, object]", payload["result"])
    calls = cast("list[dict[str, str]]", payload["calls"])
    labels = [call["label"] for call in calls]

    assert run_result["status"] == "implementer-no-commit"
    assert run_result["commit"] == ""
    assert run_result["review"] is None
    assert run_result["critic"] is None
    assert "cold-reviewer" not in labels, "must not review an empty ref"
    assert "codex-adversarial-critic" not in labels
    assert "gate-runner" in labels, "gates still run — evidence about the tree"


def test_m1_explicit_review_ref_still_dispatches_despite_missing_commit(
    tmp_path: Path,
) -> None:
    """Control arm: an explicit `reviewRef` still reaches the reviewer.

    Even when the implementer's own report carried no commit.
    """
    args = {**ARGS, "reviewRef": "deadbee1234567"}
    source = GATED_IMPLEMENTATION.read_text(encoding="utf-8")
    review_ok = "{ findings: [], reportPath: '/tmp/review.md' }"
    critic_ok = "{ verdicts: [], reportPath: '/tmp/critic.md' }"
    body = (
        _GATES_OK_BODY
        + f"  if (label === 'cold-reviewer') return {review_ok}\n"
        + f"  if (label === 'codex-adversarial-critic') return {critic_ok}\n"
        + "  return null"
    )
    wrapped = _custom_stub_source(source, args, body)
    result = _bun_run_wrapped(wrapped, tmp_path / "m1-explicit-ref.js")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))
    run_result = cast("dict[str, object]", payload["result"])
    calls = cast("list[dict[str, str]]", payload["calls"])
    labels = [call["label"] for call in calls]

    assert run_result["status"] == "complete"
    assert "cold-reviewer" in labels, "an explicit reviewRef must still be reviewed"


def test_n15_gates_null_takes_precedence_over_review_null(tmp_path: Path) -> None:
    """n15 FAIL arm: gates and review both null must report gates-null.

    The pre-fix ordering checked `review === null` before `gates === null`,
    so this combination reported `review-null`, hiding the earlier-phase
    failure behind the later-phase one.
    """
    args = {**ARGS, "reviewRef": "", "criticProposal": ""}
    source = GATED_IMPLEMENTATION.read_text(encoding="utf-8")
    body = (
        "if (label === 'codex-implementer') "
        "return 'CODEX REPORT\\nCOMMIT: abcdef1234567'\n"
        "  return null"
    )
    wrapped = _custom_stub_source(source, args, body)
    result = _bun_run_wrapped(wrapped, tmp_path / "n15-gates-and-review-null.js")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))
    run_result = cast("dict[str, object]", payload["result"])

    assert run_result["gates"] is None
    assert run_result["review"] is None
    assert run_result["status"] == "gates-null"
