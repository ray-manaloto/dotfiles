# Copyright (c) 2026 Raymond Manaloto
"""Dry-run every saved Claude Workflow script with the repo-pinned Bun."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).parent.parent.absolute()
WORKFLOWS = REPO_ROOT / ".claude" / "workflows"
SYNTAX_ERROR = REPO_ROOT / "tests" / "fixtures" / "workflows_js" / "syntax-error.js"

KNOWN_AGENT_TYPES = {
    "general-purpose",
    "fable-orchestrator:codex-implementer",
    "gate-runner",
    "cold-reviewer",
    "codex-adversarial-critic",
    "graphify-researcher",
    "graphify-operator",
    "codex-staleness-auditor",
}
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
  const label = options.label || 'general-purpose'
  calls.push({ label, agentType: options.agentType || 'general-purpose' })
  if (label === 'codex-implementer') return 'CODEX REPORT\nCOMMIT: abcdef1234567'
  if (label === 'gate-runner') {
    return args.verify.map((cmd, index) => ({
      cmd, rc: 0, log: `/tmp/gate-${index}.log`, firstFailure: '',
    }))
  }
  if (label === 'graphify-operator') {
    return args.tasks.map((task, index) => ({
      name: task.name,
      rc: task.expectRc || 0,
      log: `/tmp/task-${index}.log`,
      delta: '0/0/0',
    }))
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
