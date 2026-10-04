# Copyright (c) 2026 Raymond Manaloto
"""Dry-run every saved Claude Workflow script with the repo-pinned Bun."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

REPO_ROOT = Path(__file__).parent.parent.absolute()
WORKFLOWS = REPO_ROOT / ".claude" / "workflows"
AGENTS = REPO_ROOT / ".claude" / "agents"
SYNTAX_ERROR = REPO_ROOT / "tests" / "fixtures" / "workflows_js" / "syntax-error.js"

_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
#: Any quote style — single, double or a template literal — so a dispatch cannot
#: dodge the roster gate by its quoting (removal review finding 9).
_AGENT_TYPE_CALL_SITE_RE = re.compile(r"""agentType:\s*['"`]([^'"`]+)['"`]""")


#: Claude Code's built-in subagent types a saved workflow may dispatch without
#: a local agent file. Source: the harness docs' "Built-in subagents" section
#: (`knowledge-base/sources/agent-harness-docs/docs/claude-code/sub-agents.md`,
#: lines 31-84: Explore, Plan, general-purpose). `general-purpose` is also the
#: harness default when a call site omits `agentType`.
BUILTIN_AGENT_TYPES = frozenset({"general-purpose", "Explore", "Plan"})


def _declared_agent_names(agents_dir: Path) -> set[str]:
    """Frontmatter `name:` of every repo-local subagent file (the registry key)."""
    return {
        match.group(1)
        for path in sorted(agents_dir.glob("*.md"))
        for match in [_NAME_RE.search(path.read_text(encoding="utf-8"))]
        if match
    }


def undeclared_agent_types(workflows_dir: Path, agents_dir: Path) -> list[str]:
    """Every literal `agentType` a saved workflow names that nothing declares (#1313).

    Allowed: a built-in (:data:`BUILTIN_AGENT_TYPES`) or a repo-local agent's
    frontmatter `name:`. A plugin-qualified type (`plugin:agent`) is never
    allowed: a plugin's cache can be garbage-collected, and knowledge-base's
    tool-review workflow broke exactly that way on a plugin reviewer. Before
    #1313 the call-site literals were ADDED to the known set, so any name a
    workflow used certified itself.
    """
    allowed = _declared_agent_names(agents_dir) | BUILTIN_AGENT_TYPES
    return sorted(
        f"{path.name}: {match.group(1)}"
        for path in sorted(workflows_dir.glob("*.js"))
        for match in _AGENT_TYPE_CALL_SITE_RE.finditer(path.read_text(encoding="utf-8"))
        if match.group(1) not in allowed
    )


KNOWN_AGENT_TYPES = _declared_agent_names(AGENTS) | BUILTIN_AGENT_TYPES
KNOWN_LABEL_PREFIXES = {
    "gap",
    "load",
    "find",
    "verify",
    "synthesize",
    "critique",
    "codex-sol-implementer",
    "gate-runner",
    "cold-reviewer",
    "codex-sol-adversarial-critic",
    "graphify-researcher",
    "graphify-operator",
    "codex-sol-staleness-auditor",
    "plan+fetch",
    "triage",
    "read",
    "source-dive",
    "refute",
    "critic",
    "reconcile",
    "adjudicate",
    "read-link",
    "codex-sol-advisor",
    "deps",
    "mirror",
    "mirror-index",
    "plan-manifests",
    "retrospect",
    "retrospect-write",
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
        {"name": "rebuild", "cmd": "mise run graphify-rebuild", "expectRc": 0},
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
        "plugins": {"antigravity": "fixture"},
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
    "question": "is the fixture fixed upstream",
    "repo": "example/repo",
    "reportPath": str(REPO_ROOT / ".agent" / "research-sweep.md"),
    # exercises the caller-link reader node in the routing pin
    "links": ["https://link.test/"],
    "advisor": True,
}

#: JS helpers shared by every research-sweep stub. Since #1514 every mandatory
#: stage returns ONE copied `PROBE-JSON` line from a `research-fanout --probe-out`
#: command, so a stub answers as that probe would: it reads the shell words of the
#: command the workflow built (`--probe-out`, `--fanout-manifest`, `--mirror-url`,
#: ...) and echoes `probe_out`, which the workflow checks. `CS` turns a compact
#: code-search row into a probe row; `DEPS(prompt, overrides)` reports one
#: fan-out manifest per `--fanout-manifest` (query = the cross-direction NAME the
#: prompt gives, `q<k>` for question terms), the README control, the repo as
#: existing under the name its prompt checks, and the search-health control only
#: when its prompt asks for it.
_SWEEP_HELPERS = """
const shWord = (s) => {
  let out = ''
  let i = 0
  while (i < s.length && !/\\s/.test(s[i])) {
    if (s[i] === "'") {
      const j = s.indexOf("'", i + 1)
      out += s.slice(i + 1, j)
      i = j + 1
    }
    else if (s[i] === '\\\\') { out += s[i + 1]; i += 2 }
    else { out += s[i]; i += 1 }
  }
  return out
}
const argsOf = (prompt, flag) => prompt.split(` ${flag} `).slice(1).map(shWord)
const PROBE_LINE = (prompt, probes) => ({ line: 'PROBE-JSON ' + JSON.stringify({
  kind: 'probe', probe_out: argsOf(prompt, '--probe-out')[0],
  manifest: '/abs/probe.json', probes }) })
const CS = (rows) => rows.map((r) => ({
  kind: 'code-search', role: r.role, query: r.query, rc: r.rc,
  http_status: r.rc === 0 ? 200 : 403, count: r.count,
  rate_limited: r.rateLimited === true, incomplete_results: r.incomplete === true }))
const CODE_SEARCH_OK = [
  { query: 'filename:mise.toml hk', role: 'query', count: 3, rc: 0 },
  { query: 'repo:example/repo filename:README.md', role: 'must-hit', count: 1, rc: 0 },
  { query: 'fresh-nonsense-token', role: 'known-absent', count: 0, rc: 0 },
]
const PLAN_PROBE_OK = (prompt, rows) => PROBE_LINE(prompt, CS(rows))
const PLAN_MANIFEST_OK = (prompt, provisional = []) => PROBE_LINE(prompt,
  argsOf(prompt, '--fanout-manifest').map(path => ({ kind: 'fanout-manifest',
    path, exists: true, fresh: true, sources: {}, required_failed: [], provisional })))
const DEPS_QUERIES = (prompt) => prompt.split('mise run research-fanout -- "').slice(1)
  .map((part, k) => {
    const q = part.split('"')[0]
    return q.startsWith('<') ? `q${k}` : q
  })
const DEPS = (prompt, o = {}) => {
  const repo = argsOf(prompt, '--repo-check')[0]
  const runs = o.runs || DEPS_QUERIES(prompt).map((query) => ({ query }))
  const fanouts = argsOf(prompt, '--fanout-manifest').flatMap((path, k) => (runs[k] ? [{
    kind: 'fanout-manifest', path, exists: runs[k].exists !== false,
    query: runs[k].query, age_s: runs[k].age_s === undefined ? 5 : runs[k].age_s,
    fresh: runs[k].fresh !== false,
    sources: {}, required_failed: runs[k].requiredFailed || [],
    provisional: runs[k].provisional || [] }] : []))
  const control = o.control || { count: 7, rc: 0, rateLimited: false }
  const health = 'health' in o ? o.health
    : prompt.includes("'health=repo:cli/cli filename:README.md'")
      ? { count: 9, rc: 0, rateLimited: false } : undefined
  const exists = o.exists || { rc: 0, status: 200, fullName: repo }
  return PROBE_LINE(prompt, [
    ...fanouts,
    ...CS([{ query: `repo:${repo} filename:README.md`, role: 'readme', ...control }]),
    ...(health
      ? CS([{ query: 'repo:cli/cli filename:README.md', role: 'health', ...health }])
      : []),
    { kind: 'repo-check', repo, rc: exists.rc, http_status: exists.status,
      full_name: exists.fullName, has_issues: exists.hasIssues,
      has_pull_requests: exists.hasPullRequests,
      has_discussions: exists.hasDiscussions },
  ])
}
const DEPS_OK = (prompt) => DEPS(prompt)
const MIRROR_OK = (prompt, o = {}) => PROBE_LINE(prompt, [{ kind: 'mirror',
  url: argsOf(prompt, '--mirror-url')[0], path: argsOf(prompt, '--mirror-path')[0],
  rc: 0, bytes: 42, reason: '', ...o }])
const INDEX_OK = (prompt, written = true) => PROBE_LINE(prompt, [{ kind: 'mirror-index',
  path: '/abs/README.md', rows: 1, missing: 0, written }])
const RETRO_PATH_OF = (prompt) =>
  (prompt.match(/ to (\\/\\S+\\.md) EXACTLY/) || [])[1]
"""

_STUBS = (
    _SWEEP_HELPERS
    + r"""
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
  calls.push({
    label,
    agentType: options.agentType || 'general-purpose',
    model: options.model || '',
    effort: options.effort || '',
  })
  if (label === 'codex-sol-implementer') return 'CODEX REPORT\nCOMMIT: abcdef1234567'
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
  // research-sweep: non-empty stage outputs so the dry run reaches every phase,
  // not just the first node (an empty plan returns 'no-manifests' after one call).
  if (label === 'plan+fetch') {
    return {
      runs: [{ query: 'q', sources: ['exa'], manifest: '/tmp/m.json', rc: 0 }],
      codeSearchProbe: PLAN_PROBE_OK(_prompt, CODE_SEARCH_OK),
      sourceDive: true,
    }
  }
  // the mandatory stages: one copied PROBE-JSON line each (#1514)
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'plan-manifests') return PLAN_MANIFEST_OK(_prompt)
  if (label === 'mirror-index') return INDEX_OK(_prompt)
  if (label.startsWith('mirror')) return MIRROR_OK(_prompt)
  if (label === 'retrospect-write') {
    return { written: true, path: RETRO_PATH_OF(_prompt) }
  }
  if (label === 'triage') {
    return {
      read: [{ url: 'https://example.test', why: 'w' }],
      hits: [],
      unverifiedEmpty: [],
    }
  }
  if (label === 'synthesize') {
    return {
      reportPath: args.reportPath,
      loadBearing: [{ claim: 'c', source: 's' }],
    }
  }
  if (label.startsWith('refute')) {
    // flagged, so the routing pin also exercises the adjudicator
    return { claim: 'c', refuted: true, misleading: false,
      evidence: 'e', controlArm: 'k' }
  }
  return schemaValue(options.schema)
}
"""
)


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


def test_saved_workflows_only_dispatch_declared_agents() -> None:
    """The real workflows name only built-ins or repo-declared agents (#1313)."""
    assert undeclared_agent_types(WORKFLOWS, AGENTS) == []


def _roster_fixture(tmp_path: Path, agent_type: str, quote: str = "'") -> list[str]:
    workflows = tmp_path / "workflows"
    agents = tmp_path / "agents"
    workflows.mkdir(parents=True)
    agents.mkdir(parents=True)
    (agents / "cold-reviewer.md").write_text("---\nname: cold-reviewer\n---\n")
    (workflows / "w.js").write_text(
        f"await agent('x', {{ agentType: {quote}{agent_type}{quote}, label: 'x' }})\n"
    )
    return undeclared_agent_types(workflows, agents)


def test_roster_rejects_a_plugin_namespaced_agent(tmp_path: Path) -> None:
    """FAIL arm: the exact shape of the knowledge-base runtime break."""
    assert _roster_fixture(tmp_path, "example-plugin:codex-reviewer") == [
        "w.js: example-plugin:codex-reviewer"
    ]


def test_roster_rejects_a_double_quoted_plugin_agent(tmp_path: Path) -> None:
    """FAIL arm: the quoting a single-quote-only pattern would have missed."""
    for n, quote in enumerate(('"', "`")):
        found = _roster_fixture(
            tmp_path / str(n), "example-plugin:codex-reviewer", quote
        )
        assert found == ["w.js: example-plugin:codex-reviewer"], quote


def test_roster_rejects_an_undeclared_agent(tmp_path: Path) -> None:
    """FAIL arm: a name with no local agent file and no built-in."""
    assert _roster_fixture(tmp_path, "ghost-reviewer") == ["w.js: ghost-reviewer"]


def test_roster_accepts_builtins_and_declared_agents(tmp_path: Path) -> None:
    """PASS arms, same fixture shape: a built-in and a declared local agent."""
    assert _roster_fixture(tmp_path / "a", "general-purpose") == []
    assert _roster_fixture(tmp_path / "b", "cold-reviewer") == []


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
        "const parallel = async (tasks) => Promise.all(tasks.map((task) => task()))\n"
        + _SWEEP_HELPERS
        + "const agent = async (_prompt, options = {}) => {\n"
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
    f"if (label === 'codex-sol-implementer') return '{_NO_COMMIT_REPORT}'\n"
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
    assert "codex-sol-adversarial-critic" not in labels
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
        + f"  if (label === 'codex-sol-adversarial-critic') return {critic_ok}\n"
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
        "if (label === 'codex-sol-implementer') "
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


RESEARCH_SWEEP = WORKFLOWS / "research-sweep-run.js"


def _sub(text: str, old: str, new: str) -> str:
    """Replace EXACTLY one occurrence of `old`.

    A stub edit whose anchor no longer matches must fail loudly — a chained
    `str.replace` that silently no-ops leaves the default stub in place, so the
    test passes without ever exercising its scenario (#1514).
    """
    count = text.count(old)
    assert count == 1, f"stub anchor matched {count} time(s), want 1: {old!r}"
    return text.replace(old, new)


def test_sub_refuses_an_anchor_that_does_not_match_once() -> None:
    """Control arm for `_sub`: a vanished or duplicated anchor is an error."""
    assert _sub("a b", "a", "c") == "c b"
    for text in ("b", "a a"):
        with pytest.raises(AssertionError, match="stub anchor matched"):
            _sub(text, "a", "c")


# The cost routing IS the design of research-sweep (see the comment block at the
# top of the script): bulk reading on haiku as Explore (no CLAUDE.md payload),
# judgment on ONE opus node, the advisor on codex. A "tidy-up" that drops a model
# pin silently moves a node onto the inherited session model — this pins it.
_SWEEP_ROUTING = {
    "plan+fetch": ("general-purpose", "sonnet", "medium"),
    # tuned 2026-09-29b: triage gates every later read, so it left haiku
    "triage": ("Explore", "sonnet", "low"),
    "read": ("Explore", "haiku", ""),
    "source-dive": ("general-purpose", "sonnet", "medium"),
    "synthesize": ("general-purpose", "opus", "high"),
    "refute": ("general-purpose", "sonnet", "medium"),
    "critic": ("Explore", "sonnet", "medium"),
    # one tier above the refuters; runs only because the _STUBS refuter flags a claim
    "adjudicate": ("general-purpose", "opus", "high"),
    "read-link": ("Explore", "sonnet", "low"),
    "reconcile": ("general-purpose", "sonnet", "medium"),
    # the mandatory stages (2026-09-30): commands to run, so cheap and general-purpose
    "deps": ("general-purpose", "sonnet", "low"),
    "mirror": ("general-purpose", "haiku", ""),
    "mirror-index": ("general-purpose", "haiku", ""),
    "plan-manifests": ("general-purpose", "haiku", ""),
    "codex-sol-advisor": ("codex-sol-advisor", "", ""),
    # #1502: READ-ONLY by construction (Explore cannot edit), so it cannot tune
    # its own rules; the verbatim writer is a cheap general-purpose copy job
    "retrospect": ("Explore", "sonnet", "low"),
    "retrospect-write": ("general-purpose", "haiku", ""),
}


def test_research_sweep_reaches_every_phase_with_pinned_routing(tmp_path: Path) -> None:
    """Every research-sweep node runs once, on the model/effort its design names.

    FAIL arm: change `model: 'opus'` on the synthesize node (or delete any node's
    `model:`) and the routing assertion names that node.
    """
    result = _bun_run(RESEARCH_SWEEP.read_text(encoding="utf-8"), tmp_path / "sweep.js")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))
    run_result = cast("dict[str, object]", payload["result"])
    calls = cast("list[dict[str, str]]", payload["calls"])
    routing = {
        call["label"].split(":", 1)[0]: (
            call["agentType"],
            call["model"],
            call["effort"],
        )
        for call in calls
    }

    assert run_result["status"] == "complete"
    assert run_result["statuses"] == []
    assert routing == _SWEEP_ROUTING
    # The returned provenance names every dispatched node (one refuter per claim).
    provenance = cast("list[dict[str, str]]", run_result["routing"])
    assert [p["node"] for p in provenance] == [c["label"] for c in calls]
    phases = [
        e["title"]
        for e in cast("list[dict[str, str]]", payload["events"])
        if e["kind"] == "phase"
    ]
    assert phases[-1] == "Retrospect"


def test_research_sweep_rejects_a_relative_report_path(tmp_path: Path) -> None:
    """A relative reportPath would land wherever the synthesizer's cwd is."""
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "reportPath": "relative.md"},
        "  return null",
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-relative.js")
    assert result.returncode != 0
    assert "reportPath must be an absolute path" in result.stderr


_SWEEP_HAPPY_BODY = """
  if (label === 'plan+fetch') {
    return { runs: [{ query: 'q', sources: ['exa'], manifest: '/tmp/m.json', rc: 0 }],
      codeSearchProbe: PLAN_PROBE_OK(_prompt, CODE_SEARCH_OK), sourceDive: false }
  }
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'plan-manifests') return PLAN_MANIFEST_OK(_prompt)
  if (label === 'mirror-index') return INDEX_OK(_prompt)
  if (label.startsWith('mirror')) return MIRROR_OK(_prompt)
  if (label === 'triage') {
    return {
      read: [{ url: 'https://gone.test', why: 'w' }],
      hits: [],
      unverifiedEmpty: [],
    }
  }
  if (label.startsWith('read')) return null
  if (label === 'synthesize') {
    events.push({ kind: 'synth-prompt', prompt: _prompt })
    return { reportPath: args.reportPath, loadBearing: [] }
  }
  if (label.startsWith('refute')) return null
  if (label === 'critic') return { gaps: [] }
  return RECONCILE
"""


def _sweep_run(tmp_path: Path, reconcile: str, name: str) -> dict[str, object]:
    body = _sub(_SWEEP_HAPPY_BODY, "RECONCILE", reconcile)
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "advisor": False, "links": []},
        body,
    )
    result = _bun_run_wrapped(wrapped, tmp_path / name)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))


def test_research_sweep_failed_reader_becomes_a_named_gap(tmp_path: Path) -> None:
    """A null reader is reported, not dropped (codex review of 50ba9eec, finding 3).

    FAIL arm: restore `.filter(Boolean)` over the reader results and
    `failedReads` disappears from the result and the synthesis prompt.
    """
    payload = _sweep_run(tmp_path, "'ok'", "sweep-null-reader.js")
    run_result = cast("dict[str, object]", payload["result"])
    events = cast("list[dict[str, str]]", payload["events"])
    synth_prompt = next(e["prompt"] for e in events if e["kind"] == "synth-prompt")

    assert run_result["failedReads"] == ["https://gone.test"]
    assert "FAILED READS:" in synth_prompt
    assert "https://gone.test" in synth_prompt
    # Reconcile always runs now (Verification + full Provenance reach the report).
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    assert "reconcile" in labels
    assert run_result["status"] == "complete"


def test_research_sweep_unreconciled_report_is_not_complete(tmp_path: Path) -> None:
    """A refuted claim that never reaches the report must not return `complete`.

    FAIL arm: drop the reconcile node (or its null check) and status reads
    `complete` while the report on disk still asserts the refuted claim.
    """
    body = _sub(
        _SWEEP_HAPPY_BODY,
        "return { reportPath: args.reportPath, loadBearing: [] }",
        "return { reportPath: args.reportPath,"
        " loadBearing: [{ claim: 'c', source: 's' }] }",
    )
    body = _sub(
        body,
        "if (label.startsWith('refute')) return null\n",
        "if (label.startsWith('refute'))"
        " return { claim: 'c', refuted: true, evidence: 'e' }\n"
        "  if (label === 'adjudicate')"
        " return { verdicts: [{ claim: 'c', refuted: true, evidence: 'e' }] }\n",
    )
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "advisor": False},
        _sub(body, "RECONCILE", "null"),
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-reconcile-null-2.js")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    run_result = cast(
        "dict[str, object]", json.loads(result.stdout.splitlines()[-1])["result"]
    )
    assert run_result["status"] == "reconcile-null"


def _sweep_custom(
    tmp_path: Path, name: str, body: str, extra_args: Mapping[str, object] | None = None
) -> dict[str, object]:
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "advisor": False, **(extra_args or {})},
        body,
    )
    result = _bun_run_wrapped(wrapped, tmp_path / name)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return cast("dict[str, object]", json.loads(result.stdout.splitlines()[-1]))


_OK_VERDICT = (
    "{ claim: 'c', refuted: false, misleading: false, evidence: 'e', controlArm: 'k' }"
)
_FLAG_VERDICT = (
    "{ claim: 'c', refuted: true, misleading: false, evidence: 'e', controlArm: 'k' }"
)

_SWEEP_TUNING_BODY = """
  if (label === 'plan+fetch') {
    return { runs: [{ query: 'q', sources: ['exa'], manifest: '/tmp/m.json', rc: 0 }],
      codeSearchProbe: PLAN_PROBE_OK(_prompt, CODE_SEARCH_OK), sourceDive: false }
  }
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'plan-manifests') return PLAN_MANIFEST_OK(_prompt)
  if (label === 'mirror-index') return INDEX_OK(_prompt)
  if (label.startsWith('mirror')) return MIRROR_OK(_prompt)
  if (label === 'triage') {
    events.push({ kind: 'triage-prompt', prompt: _prompt })
    return { read: [
      { url: 'https://caller.test/a', why: 'dup of a caller link' },
      { url: 'https://t1.test', why: 'w' }, { url: 'https://t2.test', why: 'w' },
    ], hits: [], unverifiedEmpty: [] }
  }
  if (label.startsWith('read')) {
    events.push({ kind: 'read', label, prompt: _prompt })
    return { claims: [] }
  }
  if (label === 'synthesize') {
    return { reportPath: args.reportPath, loadBearing: [
      { claim: 'A ships X', source: 's1' },
      { claim: 'B does not use X', source: 's2', absence: true },
    ] }
  }
  if (label.startsWith('refute')) {
    events.push({ kind: 'refute', label, prompt: _prompt })
    return REFUTE
  }
  if (label === 'critic') return { gaps: [] }
  if (label === 'adjudicate') return ADJUDICATE
  return 'ok'
"""


def _tuning(refute: str, adjudicate: str = "null") -> str:
    return _sub(_sub(_SWEEP_TUNING_BODY, "REFUTE", refute), "ADJUDICATE", adjudicate)


def test_research_sweep_caller_links_bypass_triage_and_cap(tmp_path: Path) -> None:
    """Caller links are always read (sonnet), never ranked away or double-read.

    FAIL arm: feed LINKS through triage/READ_MAX instead of their own readers and
    `https://caller.test/b` is never read (readMax=1 keeps only one triaged URL).
    """
    payload = _sweep_custom(
        tmp_path,
        "sweep-links.js",
        _tuning(_OK_VERDICT),
        # a fragment/trailing-slash variant of /a must not be read twice
        {
            "links": [
                "https://caller.test/a",
                "https://caller.test/b",
                "https://caller.test/a/",
            ],
            "readMax": 1,
        },
    )
    events = cast("list[dict[str, str]]", payload["events"])
    reads = [e for e in events if e["kind"] == "read"]
    link_reads = [e for e in reads if e["label"].startswith("read-link")]
    triaged_reads = [e for e in reads if not e["label"].startswith("read-link")]

    assert len(link_reads) == 1
    # the trailing-slash duplicate of /a is read ONCE
    assert link_reads[0]["prompt"].count("- https://caller.test/a") == 1
    assert "https://caller.test/a" in link_reads[0]["prompt"]
    assert "https://caller.test/b" in link_reads[0]["prompt"]
    # the caller link triage also picked is not read twice, and readMax=1 applies
    # only to the triaged remainder
    assert len(triaged_reads) == 1
    assert "https://caller.test/a" not in triaged_reads[0]["prompt"]
    assert "https://t1.test" in triaged_reads[0]["prompt"]
    triage_prompt = next(e["prompt"] for e in events if e["kind"] == "triage-prompt")
    assert "https://caller.test/b" in triage_prompt


def test_research_sweep_refutes_each_claim_independently(tmp_path: Path) -> None:
    """One refuter per load-bearing claim; an absence claim gets the two-route brief.

    FAIL arm: go back to one refuter for all claims and there is one `refute`
    call, not two; drop the absence branch and neither prompt says SECOND.
    """
    payload = _sweep_custom(
        tmp_path, "sweep-per-claim.js", _tuning(_OK_VERDICT), {"links": []}
    )
    events = cast("list[dict[str, str]]", payload["events"])
    refutes = [e for e in events if e["kind"] == "refute"]
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]

    assert [e["label"] for e in refutes] == ["refute:1/2", "refute:2/2"]
    assert "SECOND route of a DIFFERENT KIND" not in refutes[0]["prompt"]
    assert "SECOND route of a DIFFERENT KIND" in refutes[1]["prompt"]
    # every refuter must also judge misleading-by-omission (the Omarchy class)
    assert all("MISLEADING-BY-OMISSION" in e["prompt"] for e in refutes)
    # nothing flagged: the adjudicator never runs; reconcile always does
    assert "adjudicate" not in labels
    assert "reconcile" in labels
    assert cast("dict[str, object]", payload["result"])["status"] == "complete"


def test_research_sweep_adjudicator_can_overturn_a_refutation(tmp_path: Path) -> None:
    """A refuter's 'refuted' is confirmed one tier up before it rewrites the report.

    FAIL arm: use the refuters' flags directly as `refuted` and the overturned
    claims come back as refuted.
    """
    body = _tuning(
        _FLAG_VERDICT,
        "{ verdicts: [{ index: 0, claim: 'x', refuted: false, evidence: 'overturned' },"
        " { index: 1, claim: 'y', refuted: false, evidence: 'overturned' }] }",
    )
    payload = _sweep_custom(tmp_path, "sweep-adjudicate.js", body, {"links": []})
    run_result = cast("dict[str, object]", payload["result"])
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]

    assert "adjudicate" in labels
    assert run_result["refuted"] == []
    # flagged claims still get a Verification section via reconcile
    assert "reconcile" in labels
    assert run_result["status"] == "complete"


def test_research_sweep_null_refuters_are_unverified_not_confirmed(
    tmp_path: Path,
) -> None:
    """Every refuter null -> verify-null; a null is never read as 'confirmed'.

    FAIL arm: treat a null verdict as refuted=false and status reads `complete`.
    """
    payload = _sweep_custom(
        tmp_path, "sweep-null-refuters.js", _tuning("null"), {"links": []}
    )
    run_result = cast("dict[str, object]", payload["result"])
    verdicts = cast("list[dict[str, object]]", run_result["verdicts"])

    assert [v["refuted"] for v in verdicts] == [None, None]
    assert run_result["status"] == "verify-null"


def _flagged_run(
    tmp_path: Path, name: str, refute: str, adjudicate: str
) -> dict[str, object]:
    return _sweep_custom(tmp_path, name, _tuning(refute, adjudicate), {"links": []})


def test_research_sweep_null_adjudicator_upholds_every_flag(tmp_path: Path) -> None:
    """An unconfirmed refutation still rewrites the report (cold review row 1).

    FAIL arm: leave `refuted` empty when the adjudicator is null and both flagged
    claims survive into the Answer.
    """
    payload = _flagged_run(tmp_path, "sweep-adj-null.js", _FLAG_VERDICT, "null")
    run_result = cast("dict[str, object]", payload["result"])
    assert len(cast("list[object]", run_result["refuted"])) == 2


def test_research_sweep_adjudicator_omission_is_upheld_by_index(tmp_path: Path) -> None:
    """Verdicts are matched back by index; a skipped claim stays upheld (row 2).

    FAIL arm: filter the adjudicator's own verdict list instead and the skipped
    claim silently counts as overturned.
    """
    adjudicate = (
        "{ verdicts: [{ index: 0, claim: 'reworded',"
        " refuted: false, evidence: 'no' }] }"
    )
    payload = _flagged_run(tmp_path, "sweep-adj-skip.js", _FLAG_VERDICT, adjudicate)
    run_result = cast("dict[str, object]", payload["result"])
    refuted = cast("list[dict[str, str]]", run_result["refuted"])
    assert len(refuted) == 1
    assert refuted[0]["adjudicated"] == "not adjudicated — upheld by default"


def test_research_sweep_flags_a_true_but_misleading_claim(tmp_path: Path) -> None:
    """A TRUE claim that is misleading by omission still reaches the adjudicator.

    FAIL arm: flag only `refuted === true` and a misleading-but-true claim is
    confirmed without adjudication — the 2026-09-29b Omarchy failure class.
    """
    misleading = (
        "{ claim: 'c', refuted: false, misleading: true,"
        " omitted: 'documented workflow', evidence: 'e', controlArm: 'k' }"
    )
    payload = _flagged_run(tmp_path, "sweep-misleading.js", misleading, "null")
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    assert "adjudicate" in labels


_DEP_MANIFEST = (
    ".agent/kb/raw/research-fanout/research-sweep/deps/example--repo/1/manifest.json"
)


def test_research_sweep_caller_links_survive_a_null_plan(tmp_path: Path) -> None:
    """Links are read even when the planner returns null (row 3).

    FAIL arm: return 'plan-null' unconditionally and no link is read.
    """
    body = _sub(
        _tuning(_OK_VERDICT),
        "if (label === 'plan+fetch') {",
        "if (label === 'plan+fetch') { return null",
    )
    payload = _sweep_custom(
        tmp_path, "sweep-plan-null.js", body, {"links": ["https://l.test"]}
    )
    events = cast("list[dict[str, str]]", payload["events"])
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    assert any(e["kind"] == "read" and "https://l.test" in e["prompt"] for e in events)
    # the mandatory dependency stage still ran, so triage reads ITS manifests only
    assert "deps:example/repo" in labels
    triage_prompt = next(e["prompt"] for e in events if e["kind"] == "triage-prompt")
    assert _DEP_MANIFEST in triage_prompt
    assert "/m.json" not in triage_prompt
    # the failed stage is a named gap in synthesis and in the statuses (review N2) —
    # and the planner's null is ALSO a mandatory gap, which `links-only` used to
    # hide (#1513): status is the higher-precedence `mandatory-gap`
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["status"] == "mandatory-gap"
    assert run_result["statuses"] == ["mandatory-gap", "links-only"]
    assert run_result["stageGaps"] == [
        (
            "planner agent reported nothing (null) — no planner fan-out manifest"
            " reached triage"
        )
    ]
    assert "code search: planner agent reported nothing (null)" in cast(
        "list[str]", run_result["mandatoryGaps"]
    )


def test_research_sweep_some_null_refuters_is_partial_verify(tmp_path: Path) -> None:
    """One null refuter among several is not `complete` (row 13)."""
    body = _sub(
        _sub(
            _SWEEP_TUNING_BODY,
            "    return REFUTE",
            "    return label === 'refute:1/2' ? null : " + _OK_VERDICT,
        ),
        "ADJUDICATE",
        "null",
    )
    payload = _sweep_custom(tmp_path, "sweep-partial.js", body, {"links": []})
    assert cast("dict[str, object]", payload["result"])["status"] == "partial-verify"


def test_research_sweep_adjudicator_can_uphold_misleading(tmp_path: Path) -> None:
    """An adjudicator verdict {refuted: false, misleading: true} UPHOLDS (review N1).

    FAIL arm: join on `a.refuted` alone and the misleading claim is overturned —
    the Omarchy failure class the misleading verdict exists for.
    """
    misleading = (
        "{ claim: 'c', refuted: false, misleading: true,"
        " omitted: 'documented workflow', evidence: 'e', controlArm: 'k' }"
    )
    adjudicate = (
        "{ verdicts: [{ index: 0, claim: 'c', refuted: false, misleading: true,"
        " evidence: 'upheld', controlArm: 'k' }, { index: 1, claim: 'c',"
        " refuted: false, misleading: false, evidence: 'overturned',"
        " controlArm: 'k' }] }"
    )
    payload = _flagged_run(tmp_path, "sweep-adj-misleading.js", misleading, adjudicate)
    result = cast("dict[str, object]", payload["result"])
    refuted = cast("list[dict[str, str]]", result["refuted"])
    assert [r["adjudicated"] for r in refuted] == ["upheld"]


def test_research_sweep_keeps_a_section_fragment(tmp_path: Path) -> None:
    """A caller link's #anchor names the section to read; it is kept (review N3)."""
    payload = _sweep_custom(
        tmp_path,
        "sweep-fragment.js",
        _tuning(_OK_VERDICT),
        {"links": ["https://p.test/post/#on-omarchy"]},
    )
    events = cast("list[dict[str, str]]", payload["events"])
    link_read = next(
        e for e in events if e["kind"] == "read" and e["label"].startswith("read-link")
    )
    assert "https://p.test/post#on-omarchy" in link_read["prompt"]


# The mandatory stages (docs/specs/research-enforcement-2026-09-30.md): the tuning
# body records every mandatory-stage prompt so each test can pin what it dispatched.
# Every edit goes through `_sub`, so a renamed stub line fails here instead of
# silently leaving the default stub in place (#1514).
_SWEEP_MANDATORY_BODY = _SWEEP_TUNING_BODY
for _old, _new in (
    (
        "  if (label === 'plan-manifests') return PLAN_MANIFEST_OK(_prompt)\n",
        (
            "  if (label === 'plan-manifests') {\n"
            "    events.push({ kind: 'plan-manifests', label, prompt: _prompt })\n"
            "    return PLAN_MANIFEST_STUB\n"
            "  }\n"
        ),
    ),
    (
        "  if (label.startsWith('deps')) return DEPS_OK(_prompt)\n",
        (
            "  if (label.startsWith('deps')) {\n"
            "    events.push({ kind: 'deps', label, prompt: _prompt })\n"
            "    return DEPS_STUB\n"
            "  }\n"
        ),
    ),
    (
        "  if (label === 'mirror-index') return INDEX_OK(_prompt)\n",
        (
            "  if (label === 'mirror-index') {\n"
            "    events.push({ kind: 'mirror-index', label, prompt: _prompt })\n"
            "    return INDEX_STUB\n"
            "  }\n"
        ),
    ),
    (
        "  if (label.startsWith('mirror')) return MIRROR_OK(_prompt)\n",
        (
            "  if (label.startsWith('mirror')) {\n"
            "    events.push({ kind: 'mirror', label, prompt: _prompt })\n"
            "    return MIRROR_STUB\n"
            "  }\n"
        ),
    ),
    (
        "  if (label === 'plan+fetch') {\n",
        (
            "  if (label === 'plan+fetch') {\n"
            "    events.push({ kind: 'plan-prompt', prompt: _prompt })\n"
        ),
    ),
    (
        "  if (label === 'synthesize') {\n",
        (
            "  if (label === 'synthesize') {\n"
            "    events.push({ kind: 'synth-prompt', prompt: _prompt })\n"
        ),
    ),
    (
        "  return 'ok'\n",
        (
            "  if (label === 'reconcile')"
            " events.push({ kind: 'reconcile', prompt: _prompt })\n"
            "  if (label === 'retrospect') {\n"
            "    events.push({ kind: 'retrospect', prompt: _prompt })\n"
            "    return RETRO_STUB\n"
            "  }\n"
            "  if (label === 'retrospect-write') {\n"
            "    events.push({ kind: 'retrospect-write', prompt: _prompt })\n"
            "    return RETRO_WRITE_STUB\n"
            "  }\n"
            "  return 'ok'\n"
        ),
    ),
):
    _SWEEP_MANDATORY_BODY = _sub(_SWEEP_MANDATORY_BODY, _old, _new)


_PLAN_RUNS_OK = "[{ query: 'q', sources: ['exa'], manifest: '/tmp/m.json', rc: 0 }]"


def _mandatory_run(
    tmp_path: Path,
    name: str,
    extra_args: Mapping[str, object],
    stubs: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Run the sweep with the mandatory-stage stubs overridden by `stubs`."""
    stub = {
        "deps": "DEPS_OK(_prompt)",
        "mirror": "MIRROR_OK(_prompt)",
        "mirror_index": "INDEX_OK(_prompt)",
        "plan_manifests": "PLAN_MANIFEST_OK(_prompt)",
        "code_search": "CODE_SEARCH_OK",
        "plan_runs": _PLAN_RUNS_OK,
        "plan": "",
        "refute": _OK_VERDICT,
        "retro": "{ findings: [], proposals: [] }",
        "retro_write": "{ written: true, path: RETRO_PATH_OF(_prompt) }",
        **(stubs or {}),
    }
    body = _sub(_SWEEP_MANDATORY_BODY, "REFUTE", stub["refute"])
    body = _sub(body, "ADJUDICATE", "null")
    body = _sub(body, "return DEPS_STUB\n", f"return {stub['deps']}\n")
    body = _sub(body, "return MIRROR_STUB\n", f"return {stub['mirror']}\n")
    body = _sub(body, "return INDEX_STUB\n", f"return {stub['mirror_index']}\n")
    body = _sub(
        body, "return PLAN_MANIFEST_STUB\n", f"return {stub['plan_manifests']}\n"
    )
    body = _sub(body, "return RETRO_STUB\n", f"return {stub['retro']}\n")
    body = _sub(body, "return RETRO_WRITE_STUB\n", f"return {stub['retro_write']}\n")
    body = _sub(
        body,
        "PLAN_PROBE_OK(_prompt, CODE_SEARCH_OK)",
        f"PLAN_PROBE_OK(_prompt, {stub['code_search']})",
    )
    body = _sub(
        body,
        f"return {{ runs: {_PLAN_RUNS_OK},",
        f"return {{ runs: {stub['plan_runs']},",
    )
    if stub["plan"]:
        body = _sub(
            body,
            "if (label === 'plan+fetch') {",
            f"if (label === 'plan+fetch') {{ return {stub['plan']}",
        )
    return _sweep_custom(tmp_path, name, body, extra_args)


def _of_kind(payload: Mapping[str, object], kind: str) -> list[dict[str, str]]:
    events = cast("list[dict[str, str]]", payload["events"])
    return [e for e in events if e["kind"] == kind]


def _result(payload: Mapping[str, object]) -> dict[str, object]:
    return cast("dict[str, object]", payload["result"])


def _command(prompt: str, needle: str) -> list[str]:
    """The shell words of the one prompt line that carries `needle`."""
    return shlex.split(next(line for line in prompt.splitlines() if needle in line))


def test_research_sweep_mirrors_each_caller_link_once(tmp_path: Path) -> None:
    """One mirror agent per caller link, via a research-fanout probe, plus a README.

    FAIL arm: batch the links into one mirror prompt, or have the agent run a
    bare `firecrawl` and type rc/bytes back, and the per-link probe assertions fail.
    """
    links = ["https://a.test/x", "https://b.test/y"]
    payload = _mandatory_run(tmp_path, "sweep-mirror.js", {"links": links})
    mirrors = _of_kind(payload, "mirror")
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    raw = f"{REPO_ROOT}/docs/research/kb/raw/research-sweep/links"

    assert [m["label"] for m in mirrors] == ["mirror:1/2", "mirror:2/2"]
    for n, (m, url) in enumerate(zip(mirrors, links, strict=True), start=1):
        words = _command(m["prompt"], "--mirror-url")
        assert words == [
            "mise",
            "run",
            "research-fanout",
            "--",
            "--probe-out",
            f"{raw}/{n}.probe.json",
            "--mirror-url",
            url,
            "--mirror-path",
            f"{raw}/{n}.md",
        ]
        assert "PROBE-JSON" in m["prompt"]
        assert "firecrawl scrape" not in m["prompt"], (
            "the probe runs firecrawl, not the agent"
        )
        assert links[2 - n] not in m["prompt"], "one link per mirror agent"
    assert labels.count("mirror-index") == 1
    index = _of_kind(payload, "mirror-index")[0]["prompt"]
    words = _command(index, "--mirror-index")
    assert words[-4:] == ["--mirror-index", raw, "--mirror-count", "2"]
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert f"(mirror: {raw}/1.md, 42 bytes)" in link_read["prompt"]
    assert _result(payload)["status"] == "complete"


def test_research_sweep_provisional_mirror_keeps_validated_route(
    tmp_path: Path,
) -> None:
    """A successful fallback is read offline and disclosed in the final result.

    FAIL arms: retain the primary rc=1, drop provenance, or omit provisional
    from common/statuses; each loses a distinct public output below.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-provisional-mirror.js",
        {"links": ["https://caller.test/a"]},
        {
            "mirror": "MIRROR_OK(_prompt, { route: 'webclaw', provisional: true, "
            "primary_reason: 'Insufficient credits' })"
        },
    )
    run_result = _result(payload)
    route = "https://caller.test/a: mirrored via webclaw (Insufficient credits)"
    assert run_result["provisionalRoutes"] == [route]
    assert run_result["status"] == "provisional"
    assert run_result["statuses"] == ["provisional"]
    assert run_result["mirrorGaps"] == []
    mirror = cast("list[dict[str, object]]", run_result["mirror"])[0]
    assert mirror["route"] == "webclaw"
    assert mirror["primaryReason"] == "Insufficient credits"
    read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert "(mirror: " in read["prompt"]
    assert "(NO MIRROR:" not in read["prompt"]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    assert "PROVISIONAL ROUTES:" in synth
    assert route in synth


@pytest.mark.parametrize("source", ["planner", "dependency"])
def test_research_sweep_manifest_provisional_is_probe_derived(
    tmp_path: Path, source: str
) -> None:
    """An agent's planner runs lack route fields; only the probe supplies them.

    FAIL arm: trust planner metadata, or omit dependency probe rows, and the
    corresponding literal route disappears from the returned result.
    """
    line = "firecrawl-search via serper (credits-exhausted: Insufficient credits)"
    planner_manifest = str(tmp_path / "planner" / "manifest.json")
    stubs = {
        "plan_runs": json.dumps(
            [{"query": "q", "sources": ["exa"], "manifest": planner_manifest, "rc": 0}]
        )
    }
    if source == "planner":
        stubs["plan_manifests"] = f"PLAN_MANIFEST_OK(_prompt, [{json.dumps(line)}])"
        manifest = planner_manifest
    else:
        stubs["deps"] = (
            "DEPS(_prompt, { runs: [{ query: 'q0', provisional: ["
            f"{json.dumps(line)}] }}] }})"
        )
        manifest = (
            ".agent/kb/raw/research-fanout/research-sweep/deps/"
            "example--repo/1/manifest.json"
        )
    payload = _mandatory_run(
        tmp_path, f"sweep-provisional-{source}.js", {"links": []}, stubs
    )
    run_result = _result(payload)
    assert run_result["provisionalRoutes"] == [f"{manifest}: {line}"]
    assert run_result["status"] == "provisional"
    assert run_result["statuses"] == ["provisional"]
    assert f"{manifest}: {line}" in _of_kind(payload, "synth-prompt")[0]["prompt"]
    planner = _of_kind(payload, "plan-manifests")[0]["prompt"]
    words = _command(planner, "--fanout-manifest")
    assert words[words.index("--probe-out") + 1] == (
        ".agent/kb/raw/research-fanout/research-sweep/plan/manifests.json"
    )
    assert words[words.index("--fanout-manifest") + 1] == planner_manifest


def test_research_sweep_primary_routes_remain_complete(tmp_path: Path) -> None:
    """Control: ordinary mirrors and all-ok manifests never claim provisional."""
    payload = _mandatory_run(
        tmp_path, "sweep-primary-complete.js", {"links": ["https://caller.test/a"]}
    )
    run_result = _result(payload)
    assert run_result["provisionalRoutes"] == []
    assert run_result["statuses"] == []
    assert run_result["status"] == "complete"
    assert "PROVISIONAL ROUTES:" not in _of_kind(payload, "synth-prompt")[0]["prompt"]


@pytest.mark.parametrize("status", ["complete", "provisional", "mandatory-gap"])
def test_research_sweep_retrospect_calls_provisional_run_completed(
    tmp_path: Path, status: str
) -> None:
    stubs = (
        {
            "mirror": "MIRROR_OK(_prompt, { route: 'webclaw', provisional: true, "
            "primary_reason: 'Insufficient credits' })"
        }
        if status == "provisional"
        else {"plan_manifests": "null"}
        if status == "mandatory-gap"
        else {}
    )
    payload = _mandatory_run(
        tmp_path,
        f"sweep-retro-{status}.js",
        {"links": ["https://caller.test/a"]},
        stubs,
    )
    assert _result(payload)["status"] == status
    prompt = _of_kind(payload, "retrospect")[0]["prompt"]
    assert ("the run did not complete" in prompt) is (status == "mandatory-gap")


@pytest.mark.parametrize(
    "probe",
    [
        "null",
        "{ line: 'not-json' }",
        (
            "{ line: 'PROBE-JSON ' + JSON.stringify({ kind: 'probe', "
            "probe_out: '/elsewhere/probe.json', probes: [] }) }"
        ),
    ],
    ids=["not-run", "malformed", "wrong-output-path"],
)
def test_research_sweep_missing_planner_probe_is_mandatory_gap(
    tmp_path: Path, probe: str
) -> None:
    """Missing or copied planner evidence must degrade the run's status."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-missing-planner-probe.js",
        {"links": []},
        {"plan_manifests": probe},
    )
    run_result = _result(payload)
    assert run_result["fanoutGaps"] == ["planner provisional check did not run"]
    assert run_result["mandatoryGaps"] == ["planner provisional check did not run"]
    assert run_result["provisionalRoutes"] == []
    assert run_result["status"] == "mandatory-gap"
    assert run_result["statuses"] == ["mandatory-gap"]


@pytest.mark.parametrize(
    ("stubs", "status"),
    [
        ({"refute": "null"}, "verify-null"),
        (
            {"refute": f"label === 'refute:1/2' ? null : {_OK_VERDICT}"},
            "partial-verify",
        ),
        (
            {
                "deps": "DEPS(_prompt, { runs: [{ query: 'q0', "
                "requiredFailed: ['github-issues: error (HTTP 403)'] }] })"
            },
            "mandatory-gap",
        ),
        ({"plan_runs": "[]"}, "links-only"),
    ],
)
def test_research_sweep_degraded_status_precedes_provisional(
    tmp_path: Path, stubs: dict[str, str], status: str
) -> None:
    """Appending provisional must never replace a more serious degraded status."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-provisional-precedence.js",
        {"links": ["https://caller.test/a"]},
        {
            **stubs,
            "mirror": "MIRROR_OK(_prompt, { route: 'webclaw', provisional: true, "
            "primary_reason: 'Insufficient credits' })",
        },
    )
    run_result = _result(payload)
    assert run_result["status"] == status
    assert run_result["statuses"] == [status, "provisional"]


def test_research_sweep_unfetchable_link_is_a_named_gap(tmp_path: Path) -> None:
    """A link firecrawl cannot fetch is a named gap and is read live, not dropped."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-mirror-fail.js",
        {"links": ["https://dead.test"]},
        {"mirror": "MIRROR_OK(_prompt, { rc: 1, bytes: 0, reason: 'HTTP 404' })"},
    )
    run_result = _result(payload)
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )

    assert run_result["mirrorGaps"] == ["https://dead.test: not mirrored (HTTP 404)"]
    assert "MIRROR GAPS:" in synth
    assert "(NO MIRROR: HTTP 404)" in link_read["prompt"]
    # the stage RAN; the world said no — not a mandatory gap
    assert run_result["status"] == "complete"


def test_research_sweep_mirror_probe_must_be_the_one_requested(tmp_path: Path) -> None:
    """A copied line for ANOTHER manifest (or no line) is not the mirror (#1514).

    FAIL arm: accept any parseable PROBE-JSON line and an agent that pasted a
    different probe's output reads as a successful mirror.
    """
    other = (
        "{ line: 'PROBE-JSON ' + JSON.stringify({ kind: 'probe',"
        " probe_out: '/elsewhere/1.probe.json', probes: [{ kind: 'mirror',"
        " url: 'https://l.test', path: '/elsewhere/1.md', rc: 0, bytes: 9,"
        " reason: '' }] }) }"
    )
    for n, stub in enumerate([other, "{ line: 'rc=0, 42 bytes' }"]):
        payload = _mandatory_run(
            tmp_path,
            f"sweep-mirror-other-{n}.js",
            {"links": ["https://l.test"]},
            {"mirror": stub},
        )
        gaps = cast("list[str]", _result(payload)["mandatoryGaps"])
        assert gaps == [
            (
                "mirror stage for https://l.test: no PROBE-JSON line for"
                f" {REPO_ROOT}/docs/research/kb/raw/research-sweep/links/1.probe.json"
            )
        ]


def test_research_sweep_dependency_stage_runs_per_repo_both_directions(
    tmp_path: Path,
) -> None:
    """Every repo gets the three github sources, each relationship from both sides.

    FAIL arm: leave the github-* runs to the planner and no `deps:` agent runs.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-deps.js", {"links": [], "relatedRepos": ["other/tool"]}
    )
    deps = {e["label"]: e["prompt"] for e in _of_kind(payload, "deps")}
    sources = "--sources github-issues,github-discussions,github-releases"

    assert sorted(deps) == ["deps:example/repo", "deps:other/tool"]
    main_prompt, other_prompt = deps["deps:example/repo"], deps["deps:other/tool"]
    assert main_prompt.count(sources) == 2
    assert '"tool" --repo example/repo' in main_prompt
    assert other_prompt.count(sources) == 1
    assert '"repo" --repo other/tool' in other_prompt
    # one --out per run: every related repo's query is the same name, so a shared
    # default slug dir would let concurrent runs unlink each other's files (M8)
    out = "--out '.agent/kb/raw/research-fanout/research-sweep/deps"
    assert f"{out}/example--repo/1'" in main_prompt
    assert f"{out}/example--repo/2'" in main_prompt
    assert f"{out}/other--tool/1'" in other_prompt
    # the probe re-reads EVERY run's manifest and requires all three sources (#1473)
    probe = _command(main_prompt, "--probe-out")
    assert probe.count("--fanout-manifest") == 2
    assert probe[probe.index("--require") + 1] == (
        "github-issues,github-discussions,github-releases"
    )
    assert probe[probe.index("--repo-check") + 1] == "example/repo"
    run_result = _result(payload)
    runs = cast("list[dict[str, object]]", run_result["dependencyRuns"])
    assert [(r["repo"], r["query"]) for r in runs] == [
        ("example/repo", "q0"),
        ("example/repo", "tool"),
        ("other/tool", "repo"),
    ]
    assert run_result["status"] == "complete"


def test_research_sweep_dependency_run_whose_issues_search_failed_is_a_gap(
    tmp_path: Path,
) -> None:
    """#1473: releases answering must not make a failed issues search a success.

    The fan-out's own rc was 0 (one source answered); only the manifest's per-source
    status shows github-issues failed. FAIL arm: trust the run and drop the
    `required_failed` check, and this reads `complete`.
    """
    failed = (
        "DEPS(_prompt, { runs: [{ query: 'q0',"
        " requiredFailed: ['github-issues: error (exited 1: HTTP 422)'] }] })"
    )
    payload = _mandatory_run(tmp_path, "sweep-1473.js", {"links": []}, {"deps": failed})
    run_result = _result(payload)
    assert run_result["mandatoryGaps"] == [
        (
            'dependency-repo stage for example/repo: "q0" —'
            " github-issues: error (exited 1: HTTP 422)"
        )
    ]
    runs = cast("list[dict[str, object]]", run_result["dependencyRuns"])
    assert runs[0]["ok"] is False
    assert run_result["status"] == "mandatory-gap"


def test_research_sweep_stale_dependency_manifest_is_not_this_runs_evidence(
    tmp_path: Path,
) -> None:
    """An agent that skipped its run leaves the PREVIOUS sweep's manifest behind."""
    stale = "DEPS(_prompt, { runs: [{ query: 'q0', fresh: false, age_s: 7200 }] })"
    payload = _mandatory_run(tmp_path, "sweep-stale.js", {"links": []}, {"deps": stale})
    # ...and it is never handed to triage as this run's evidence (review a09aa247)
    assert _DEP_MANIFEST not in _of_kind(payload, "triage-prompt")[0]["prompt"]
    assert _result(payload)["mandatoryGaps"] == [
        (
            f"dependency-repo stage for example/repo: {_DEP_MANIFEST} is 7200s old"
            " — not written by this run"
        )
    ]


def test_research_sweep_zero_code_search_needs_a_same_shape_must_hit(
    tmp_path: Path,
) -> None:
    """#1471: a planner query's 0 is evidence ONLY beside a same-shape must-hit.

    S4: `foo OR bar language:toml` = 0 and the known-absent = 0, with no planner
    must-hit; the README control proves the endpoint answers for ITS shape only,
    so the run used to read `complete`. FAIL arm: let any must-hit arm the zero
    (the old `ok(codeSearch, 'must-hit', n > 0)`) and S4 reads `complete` again.
    """
    s4 = (
        "[{ query: 'foo OR bar language:toml', role: 'query', count: 0, rc: 0 },"
        " CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-s4.js", {"links": []}, {"code_search": s4}
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert code[0] == {
        "query": "foo OR bar language:toml",
        "role": "query",
        "source": "planner",
        "count": 0,
        "rc": 0,
        "rateLimited": False,
        "armed": False,
    }
    assert run_result["codeSearchGaps"] == [
        (
            'planner query "foo OR bar language:toml" returned 0 with no same-shape'
            " must-hit (qualifiers: OR language:toml) — an unarmed negative: a gap, not"
            " evidence of absence"
        )
    ]
    assert "CODE SEARCH GAPS:" in synth
    assert run_result["mandatoryGaps"] == [
        (
            "code search: no planner query ran with rc=0 and produced evidence (a hit,"
            " or a 0 armed by a same-shape must-hit)"
        )
    ]
    assert run_result["status"] == "mandatory-gap"

    # the issue's own example: a must-hit with the qualifier but WITHOUT the OR
    # is another shape; one that also uses OR arms it
    for must_hit, status in (
        ("mise language:toml", "mandatory-gap"),
        ("mise OR toml language:toml", "complete"),
    ):
        rows = (
            "[{ query: 'foo OR bar language:toml', role: 'query', count: 0, rc: 0 },"
            f" {{ query: '{must_hit}', role: 'must-hit', count: 4, rc: 0 }},"
            " CODE_SEARCH_OK[2]]"
        )
        payload = _mandatory_run(
            tmp_path, f"sweep-s4-or-{status}.js", {"links": []}, {"code_search": rows}
        )
        assert _result(payload)["status"] == status, must_hit

    # a must-hit of ANOTHER shape still does not arm it
    other_shape = (
        "[{ query: 'filename:nothing.toml zz', role: 'query', count: 0, rc: 0 },"
        " CODE_SEARCH_OK[1], CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-s4-other.js", {"links": []}, {"code_search": other_shape}
    )
    assert _result(payload)["status"] == "mandatory-gap"

    # control arm: the SAME qualifiers with a known term arm the zero
    armed = (
        "[{ query: 'filename:nothing.toml zz', role: 'query', count: 0, rc: 0 },"
        " { query: 'FILENAME:nothing.toml mise', role: 'must-hit', count: 2, rc: 0 },"
        " CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-s4-armed.js", {"links": []}, {"code_search": armed}
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    assert code[0]["armed"] is True
    assert run_result["codeSearchGaps"] == []
    assert run_result["status"] == "complete"


def test_research_sweep_planner_runs_code_search_through_a_probe(
    tmp_path: Path,
) -> None:
    """The planner hands back a probe line; it never types a count (#1514).

    FAIL arm: accept a planner line for another manifest and a pasted or invented
    count satisfies the mandatory code-search stage.
    """
    payload = _mandatory_run(tmp_path, "sweep-plan-probe.js", {"links": []})
    plan_prompt = _of_kind(payload, "plan-prompt")[0]["prompt"]
    probe = _command(plan_prompt, "--probe-out")
    want = ".agent/kb/raw/research-fanout/research-sweep/plan/code-search.json"
    assert probe[probe.index("--probe-out") + 1] == want
    assert "same-shape must-hit" in plan_prompt or "SAME qualifiers" in plan_prompt
    assert (
        "health"
        not in plan_prompt.split("Roles:", 1)[1].split("The workflow also", 1)[0]
    )

    wrong = (
        "{ runs: " + _PLAN_RUNS_OK + ", sourceDive: false, codeSearchProbe: { line:"
        " 'PROBE-JSON ' + JSON.stringify({ kind: 'probe', probe_out: 'other.json',"
        " probes: CS(CODE_SEARCH_OK) }) } }"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-plan-wrong.js", {"links": []}, {"plan": wrong}
    )
    assert _result(payload)["mandatoryGaps"] == [
        (
            f"code search: no PROBE-JSON line for {want} — the planner's"
            " code-search probe"
            " did not run or its line was not copied"
        )
    ]


def test_research_sweep_missing_dependency_stage_is_a_mandatory_gap(
    tmp_path: Path,
) -> None:
    """The §4 control arm: the dependency stage stubbed out never reads `complete`.

    FAIL arm: drop the null check on a dependency agent and status is `complete`.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-deps-null.js", {"links": []}, {"deps": "null"}
    )
    run_result = _result(payload)

    gap = "dependency-repo stage for example/repo: agent reported nothing (null)"
    assert run_result["status"] == "mandatory-gap"
    assert run_result["mandatoryGaps"] == [gap]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    assert "MANDATORY GAPS:" in synth
    # the only lines that make the REPORT TEXT say INCOMPLETE (cold review M5, M6)
    assert "the Answer must say the sweep is INCOMPLETE" in synth
    reconcile = _of_kind(payload, "reconcile")[0]["prompt"]
    assert (
        "MANDATORY GAPS (keep each in Gaps; if any, the Answer must say the sweep"
        in reconcile
    )
    assert gap in reconcile


_README_ZERO = "DEPS(_prompt, { control: { count: 0, rc: 0, rateLimited: false } })"
_README_CONTROL = "repo:example/repo filename:README.md"


def test_research_sweep_planner_must_hit_miss_is_a_note_not_a_gap(
    tmp_path: Path,
) -> None:
    """A planner's guessed must-hit of 0 is a NOTE; the README control carries it.

    Live run wf_b74e66f5-ca3: `filename:skills.rs repo:jdx/mise` returned 0 and the
    sweep read `mandatory-gap`. FAIL arm: drop the workflow-built control and this
    run is `mandatory-gap` again.
    """
    guessed = (
        "[CODE_SEARCH_OK[0], { query: 'filename:skills.rs repo:example/repo',"
        " role: 'must-hit', count: 0, rc: 0 }, CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-guess.js", {"links": []}, {"code_search": guessed}
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    notes = cast("list[str]", run_result["codeSearchNotes"])
    deps_prompt = _of_kind(payload, "deps")[0]["prompt"]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert f"--code-search 'readme={_README_CONTROL}'" in deps_prompt
    assert {
        "query": _README_CONTROL,
        "role": "must-hit",
        "source": "workflow",
        "count": 7,
        "rc": 0,
        "rateLimited": False,
    } in code
    assert len(notes) == 1
    assert notes[0].startswith('planner must-hit control "filename:skills.rs')
    assert "CODE SEARCH NOTES:" in synth
    assert run_result["mandatoryGaps"] == []
    assert run_result["status"] == "complete"


_HEALTH_CONTROL = "repo:cli/cli filename:README.md"


def test_research_sweep_readme_zero_for_an_existing_repo_is_a_note(
    tmp_path: Path,
) -> None:
    """A README control of 0 for a repo that EXISTS is a note, not an auth gap (F3).

    Measured 2026-09-30: `repo:virajp/mise filename:README.md` returns 0 although the
    fork's README.md exists (not indexed), and `sphinx-doc/sphinx` returns 0 because
    its README is README.rst — the note names both causes (round-3 R3). FAIL arm:
    treat the README 0 as a gap again and this run reads `mandatory-gap`.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-readme-fork.js", {"links": []}, {"deps": _README_ZERO}
    )
    run_result = _result(payload)
    deps_prompt = _of_kind(payload, "deps")[0]["prompt"]

    assert "--repo-check example/repo" in deps_prompt
    assert run_result["mandatoryGaps"] == []
    assert run_result["codeSearchNotes"] == [
        (
            f'"{_README_CONTROL}" returned 0 although example/repo exists — either'
            " code search does not index it (e.g. a low-star fork) or it has no"
            " README.md (e.g. README.rst); not a gap"
        )
    ]
    assert run_result["status"] == "complete"


def test_research_sweep_search_health_is_asked_once_and_its_zero_is_a_gap(
    tmp_path: Path,
) -> None:
    """The health control runs on the FIRST dependency agent only; a 0 there is a gap.

    FAIL arm: drop the health check and a search that answers nothing reads
    `complete` whenever a planner must-hit happened to hit.
    """
    zero = "DEPS(_prompt, { health: { count: 0, rc: 0, rateLimited: false } })"
    payload = _mandatory_run(
        tmp_path,
        "sweep-health-zero.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": zero},
    )
    run_result = _result(payload)
    deps = {e["label"]: e["prompt"] for e in _of_kind(payload, "deps")}
    code = cast("list[dict[str, object]]", run_result["codeSearch"])

    assert f"--code-search 'health={_HEALTH_CONTROL}'" in deps["deps:example/repo"]
    assert _HEALTH_CONTROL not in deps["deps:other/tool"]
    assert [c["query"] for c in code if c["source"] == "workflow"] == [
        _HEALTH_CONTROL,
        _README_CONTROL,
        "repo:other/tool filename:README.md",
    ]
    assert run_result["mandatoryGaps"] == [
        (
            f'code search: search-health control "{_HEALTH_CONTROL}" returned count=0'
            " rc=0 — gh auth, rate-limit or search is broken"
        )
    ]
    assert run_result["status"] == "mandatory-gap"


def test_research_sweep_blames_auth_for_a_readme_failure_only_when_health_failed(
    tmp_path: Path,
) -> None:
    """A rate-limited README control blames gh/auth only beside a failed health one."""
    both = (
        "DEPS(_prompt, { control: { count: -1, rc: 1, rateLimited: true },"
        " health: { count: -1, rc: 1, rateLimited: true } })"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-health-403.js", {"links": []}, {"deps": both}
    )
    gaps = cast("list[str]", _result(payload)["mandatoryGaps"])
    assert (
        f'code search: README control "{_README_CONTROL}" was RATE-LIMITED'
        " (HTTP 403/429), not 0 — gh auth, rate-limit or search is broken"
    ) in gaps


@pytest.mark.parametrize(
    ("exists", "expected"),
    [
        (
            "{ rc: 1, status: 404, fullName: '' }",
            ["dependency repo example/repo not found via the repos API (HTTP 404)"],
        ),
        (
            "{ rc: 1, status: 403, fullName: '' }",
            [
                (
                    "could not check example/repo via the repos API"
                    " (HTTP 403 — rate-limited or forbidden)"
                )
            ],
        ),
        (
            "{ rc: 1, status: 429, fullName: '' }",
            [
                (
                    "could not check example/repo via the repos API"
                    " (HTTP 429 — rate-limited or forbidden)"
                )
            ],
        ),
        (
            "{ rc: 1, status: 500, fullName: '' }",
            ["could not check example/repo via the repos API (HTTP 500)"],
        ),
        # round-4 L5: a 200 that gh still failed, and a 200 with no name
        (
            "{ rc: 1, status: 200, fullName: 'example/repo' }",
            [
                (
                    "could not check example/repo via the repos API"
                    ' (HTTP 200, rc=1, fullName "example/repo")'
                )
            ],
        ),
        (
            "{ rc: 0, status: 200, fullName: '  ' }",
            [
                (
                    "could not check example/repo via the repos API"
                    ' (HTTP 200, rc=0, fullName "")'
                )
            ],
        ),
        # an untrimmed name is the SAME repo, never a self-redirect
        ("{ rc: 0, status: 200, fullName: 'example/repo\\n' }", []),
    ],
    ids=["404", "403", "429", "500", "200-rc1", "200-empty", "200-untrimmed"],
)
def test_research_sweep_unchecked_dependency_repo_is_one_gap(
    tmp_path: Path, exists: str, expected: list[str]
) -> None:
    """Only a 404 is "not found"; a 403/429/other is "could not check" (round-3 R6).

    Reported ONCE, never also as an auth failure or a not-indexed note. FAIL arm:
    call every non-zero rc "not found" and a rate-limited check sends the operator
    hunting for a typo.
    """
    missing = (
        f"DEPS(_prompt, {{ exists: {exists},"
        " control: { count: 0, rc: 0, rateLimited: false } })"
    )
    payload = _mandatory_run(
        tmp_path, f"sweep-repo-{len(expected)}.js", {"links": []}, {"deps": missing}
    )
    run_result = _result(payload)

    assert run_result["mandatoryGaps"] == expected
    assert len(cast("list[str]", run_result["codeSearchNotes"])) == (
        0 if expected else 1
    )
    assert run_result["status"] == ("mandatory-gap" if expected else "complete")


@pytest.mark.parametrize(
    ("full_name", "gaps"),
    [
        # the live case: repos/jdx/rtx -> jdx/mise (rc=0), README search 0
        (
            "example/renamed",
            [
                (
                    "dependency repo example/repo redirects to example/renamed — re-run"
                    " with repo/relatedRepos set to example/renamed"
                )
            ],
        ),
        # control arm: GitHub names are case-insensitive, so case alone is no rename
        ("Example/Repo", []),
    ],
)
def test_research_sweep_renamed_repo_is_a_gap_not_a_note(
    tmp_path: Path, full_name: str, gaps: list[str]
) -> None:
    """A repo the API resolves under ANOTHER name is not the repo asked for (R2).

    FAIL arm: never compare `fullName` with the requested repo and the renamed repo's
    README 0 reads `complete` with a "not indexed" note.
    """
    renamed = (
        f"DEPS(_prompt, {{ exists: {{ rc: 0, status: 200, fullName: '{full_name}' }},"
        " control: { count: 0, rc: 0, rateLimited: false } })"
    )
    payload = _mandatory_run(
        tmp_path, f"sweep-rename-{full_name[0]}.js", {"links": []}, {"deps": renamed}
    )
    run_result = _result(payload)
    notes = cast("list[str]", run_result["codeSearchNotes"])

    assert run_result["mandatoryGaps"] == gaps
    assert len(notes) == (0 if gaps else 1)
    assert run_result["status"] == ("mandatory-gap" if gaps else "complete")


def test_research_sweep_readme_note_needs_a_passing_health_control(
    tmp_path: Path,
) -> None:
    """A README 0 says nothing about indexing unless search was shown to answer (R4).

    FAIL arm: emit the note whatever the health outcome and the report says both
    "search is broken" and "this repo is not indexed".
    """
    zero_both = (
        "DEPS(_prompt, { control: { count: 0, rc: 0, rateLimited: false },"
        " health: { count: 0, rc: 0, rateLimited: false } })"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-note-health0.js", {"links": []}, {"deps": zero_both}
    )
    assert _result(payload)["codeSearchNotes"] == []

    # the first deps agent null: health never ran, so other/tool's 0 gets no
    # not-indexed note
    first_null = (
        "_prompt.includes('--repo example/repo') ? null : DEPS(_prompt,"
        " { control: { count: 0, rc: 0, rateLimited: false } })"
    )
    payload = _mandatory_run(
        tmp_path,
        "sweep-note-unrun.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": first_null},
    )
    run_result = _result(payload)
    # ...but the uninterpretable 0 is SAID to be, never recorded silently
    assert run_result["codeSearchNotes"] == [
        (
            '"repo:other/tool filename:README.md" returned 0, but whether code search'
            " answers at all is unknown (no passing health control), so that 0 cannot"
            " be read either way"
        )
    ]
    assert run_result["mandatoryGaps"] == [
        "dependency-repo stage for example/repo: agent reported nothing (null)"
    ]


def test_research_sweep_health_row_never_satisfies_the_must_hit(
    tmp_path: Path,
) -> None:
    """Health OK + an unindexed repo + no planner must-hit is NOT complete (R1).

    Round-3 review N3: the health row carried role must-hit, so it satisfied the
    must-hit requirement on every healthy run. FAIL arm: give the health row role
    `must-hit` again and this reads `complete`.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-r1.js",
        {"links": []},
        {
            "code_search": "[CODE_SEARCH_OK[0], CODE_SEARCH_OK[2]]",
            "deps": _README_ZERO,
        },
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    health = next(c for c in code if c["query"] == _HEALTH_CONTROL)
    assert health["role"] == "health"
    assert health["count"] == 9
    assert f'"query":"{_HEALTH_CONTROL}","role":"health"' in synth
    assert run_result["mandatoryGaps"] == [
        (
            "code search: no must-hit control returned a hit, so the search is not"
            " shown to discriminate"
        )
    ]
    assert run_result["status"] == "mandatory-gap"


def test_research_sweep_rate_limit_is_never_a_zero(tmp_path: Path) -> None:
    """A 403 is reported as RATE-LIMITED, never as count 0 (row and gap text).

    FAIL arm: drop `rateLimited` from the workflow control row and the report
    shows a README count, which reads as a real zero.
    """
    limited = "DEPS(_prompt, { control: { count: -1, rc: 1, rateLimited: true } })"
    payload = _mandatory_run(tmp_path, "sweep-403.js", {"links": []}, {"deps": limited})
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    row = next(
        c for c in code if c["query"] == _README_CONTROL and c["source"] == "workflow"
    )
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert row["rateLimited"] is True
    assert row["count"] != 0
    # health answered, so the README failure is not blamed on gh/auth
    assert run_result["mandatoryGaps"] == [
        (
            f'code search: README control "{_README_CONTROL}" was RATE-LIMITED'
            " (HTTP 403/429), not 0"
        )
    ]
    assert "write RATE-LIMITED, never 0" in synth


# The tuning triage picks 3 URLs, all read by non-null readers.
_TRIAGED_READ = "3 deep-read triaged URL(s)"


@pytest.mark.parametrize(
    ("links", "statuses"),
    [([], ["stage-gap"]), (["https://l.test"], ["links-only"])],
    ids=["no-link", "one-link"],
)
def test_research_sweep_planner_fanout_without_manifests_is_not_complete(
    tmp_path: Path, links: list[str], statuses: list[str]
) -> None:
    """Dependency manifests must not mask a planner fan-out that wrote none (F1, S2).

    Cold review 836983e3 S2: a planner whose every run failed read `complete`,
    because the dependency manifests satisfied the manifest count. FAIL arm: count
    the planner and dependency manifests together again and this reads `complete`.
    With no caller link it is `stage-gap`, never `links-only` (#1513).
    """
    failed = "[{ query: 'q', sources: ['exa'], manifest: '', rc: 1 }]"
    payload = _mandatory_run(
        tmp_path, "sweep-s2.js", {"links": links}, {"plan_runs": failed}
    )
    run_result = _result(payload)
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert run_result["status"] == statuses[0]
    assert run_result["statuses"] == statuses
    assert run_result["stageGaps"] == [
        (
            "planner fan-out produced no manifests (q rc=1) —"
            " exa/context7/firecrawl/github evidence from the planner is missing"
        )
    ]
    assert run_result["fanoutGaps"] == ['planner fan-out "q" rc=1, no manifest']
    assert "FANOUT GAPS" in synth
    base = (
        f"hits triaged from the dependency-repo manifests + {_TRIAGED_READ}"
        " + the answered code-search rows"
    )
    if links:
        base = "the 1 caller link(s) read + " + base
    assert f"say the evidence base is: {base})" in synth
    assert (
        '"consequence":"no planner fan-out (exa/context7/firecrawl/github) result is'
        ' in the evidence"' in synth
    )


def test_research_sweep_null_planner_without_links_reads_dependency_manifests(
    tmp_path: Path,
) -> None:
    """S1: a null planner with no links still triages the dependency manifests (F2).

    FAIL arm: feed triage only the planner's manifests and it gets none at all.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-s1.js",
        {"links": []},
        {"plan": "null"},
    )
    run_result = _result(payload)
    triage = _of_kind(payload, "triage-prompt")[0]["prompt"]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    assert _DEP_MANIFEST in triage
    assert "/m.json" not in triage
    assert (
        "say the evidence base is: hits triaged from the dependency-repo manifests"
        f" + {_TRIAGED_READ} + the answered code-search rows)" in synth
    )
    # the planner's null is a MANDATORY gap too; #1513 made it outrank stage-gap
    assert run_result["status"] == "mandatory-gap"
    assert run_result["statuses"] == ["mandatory-gap", "stage-gap"]
    assert run_result["stageGaps"] == [
        (
            "planner agent reported nothing (null) — no planner fan-out manifest"
            " reached triage"
        )
    ]


def test_research_sweep_status_never_hides_a_mandatory_gap(tmp_path: Path) -> None:
    """#1513: a mandatory gap outranks partial-verify, and every status is listed.

    FAIL arm: restore the old ternary (partial-verify before mandatory-gap) and
    this run reads `partial-verify` with its mandatory gap invisible in `status`.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-1513.js",
        {"links": []},
        {
            "deps": "null",
            "refute": "label === 'refute:1/2' ? null : " + _OK_VERDICT,
        },
    )
    run_result = _result(payload)
    assert run_result["status"] == "mandatory-gap"
    assert run_result["statuses"] == ["mandatory-gap", "partial-verify"]


def test_research_sweep_partial_planner_failure_is_a_gap_not_a_status(
    tmp_path: Path,
) -> None:
    """One failed planner run beside a good one is a FANOUT GAP; status is unchanged."""
    partial = (
        "[{ query: 'q', sources: ['exa'], manifest: '/tmp/m.json', rc: 0 },"
        " { query: 'q2', sources: ['context7'], manifest: '/tmp/m2.json', rc: 2 },"
        " { query: 'q3', sources: ['exa'], manifest: '', rc: 0 }]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-partial-plan.js", {"links": []}, {"plan_runs": partial}
    )
    run_result = _result(payload)
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert run_result["fanoutGaps"] == [
        'planner fan-out "q2" rc=2',
        'planner fan-out "q3" rc=0, no manifest',
    ]
    assert 'planner fan-out \\"q2\\" rc=2' in synth
    assert run_result["stageGaps"] == []
    assert run_result["status"] == "complete"


def test_research_sweep_cross_direction_query_must_be_the_one_that_ran(
    tmp_path: Path,
) -> None:
    """The dependency check pins WHICH query ran — read from the manifest (F6, S3).

    FAIL arm: keep only a run-count check and an agent that swapped the
    cross-direction NAME for question terms reads `complete`.
    """
    swapped = "DEPS(_prompt, { runs: [{ query: 'terms0' }, { query: 'terms1' }] })"
    payload = _mandatory_run(
        tmp_path,
        "sweep-s3.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": swapped},
    )
    run_result = _result(payload)
    assert run_result["mandatoryGaps"] == [
        (
            "dependency-repo stage for example/repo:"
            ' cross-direction query "tool" not run (got "terms1")'
        ),
        (
            'dependency-repo stage for other/tool: cross-direction query "repo" not run'
            ' (got "terms0")'
        ),
    ]
    assert run_result["status"] == "mandatory-gap"

    short = "DEPS(_prompt, { runs: [{ query: 'q0' }] })"
    payload = _mandatory_run(
        tmp_path,
        "sweep-s3-short.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": short},
    )
    gaps = cast("list[str]", _result(payload)["mandatoryGaps"])
    assert gaps == [
        (
            "dependency-repo stage for example/repo: run 2 wrote no manifest"
            " (.agent/kb/raw/research-fanout/research-sweep/deps/example--repo/2/"
            "manifest.json)"
        ),
        (
            'dependency-repo stage for other/tool: cross-direction query "repo" not run'
            ' (got "q0")'
        ),
    ]


def test_research_sweep_link_is_one_shell_word(tmp_path: Path) -> None:
    """A caller URL carrying `'` stays ONE quoted word in the mirror command (F8, S11).

    FAIL arm: interpolate the URL inside bare single quotes again and the `'`
    ends the quote, so `;touch` becomes a separate command.
    """
    url = "https://ex.test/it's;touch${IFS}/tmp/pwn;'"
    payload = _mandatory_run(tmp_path, "sweep-s11.js", {"links": [url]})
    prompt = _of_kind(payload, "mirror")[0]["prompt"]
    raw = f"{REPO_ROOT}/docs/research/kb/raw/research-sweep/links"

    assert _command(prompt, "--mirror-url") == [
        "mise",
        "run",
        "research-fanout",
        "--",
        "--probe-out",
        f"{raw}/1.probe.json",
        "--mirror-url",
        url,
        "--mirror-path",
        f"{raw}/1.md",
    ]


def test_research_sweep_triaged_url_is_one_shell_word(tmp_path: Path) -> None:
    """Round-4 L6: a triaged URL reaches a reader as a pre-quoted `fetch:` command.

    FAIL arm: drop the `fetch:` line and the reader builds `firecrawl scrape <url>`
    from a third-party URL itself — the F8 class outside the mirror stage.
    """
    url = "https://ex.test/a'b;touch /tmp/pwn"
    body = _sub(
        _tuning(_OK_VERDICT),
        "{ url: 'https://t1.test', why: 'w' }",
        "{ url: " + json.dumps(url) + ", why: 'w' }",
    )
    payload = _sweep_custom(tmp_path, "sweep-l6.js", body, {"links": []})
    reader = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read:")
    )
    words = shlex.split(
        next(
            ln
            for ln in reader["prompt"].splitlines()
            if url[:14] in ln and "fetch:" in ln
        )
    )
    assert words == [
        "fetch:",
        "mise",
        "exec",
        "--",
        "firecrawl",
        "scrape",
        url,
        "--format",
        "markdown",
        "--only-main-content",
    ]
    assert "never retype, re-quote or interpolate a URL" in reader["prompt"]


def test_research_sweep_empty_mirror_is_not_read_as_a_mirror(tmp_path: Path) -> None:
    """rc=0 with 0 bytes is NO MIRROR: the reader reads the link live (M7)."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-mirror-empty.js",
        {"links": ["https://l.test"]},
        {"mirror": "MIRROR_OK(_prompt, { rc: 0, bytes: 0 })"},
    )
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert "(NO MIRROR: rc=0, 0 bytes)" in link_read["prompt"]
    assert "(mirror: " not in link_read["prompt"]


def test_research_sweep_error_page_mirror_is_not_read_as_a_mirror(
    tmp_path: Path,
) -> None:
    """A 404 page comes back rc=0 WITH bytes; the probe's reason makes it NO MIRROR.

    FAIL arm: judge a mirror by rc and bytes alone and the reader is pointed at
    a saved error page as if it were the link.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-mirror-404.js",
        {"links": ["https://l.test"]},
        {"mirror": "MIRROR_OK(_prompt, { bytes: 328, reason: 'HTTP 404' })"},
    )
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert "(NO MIRROR: HTTP 404)" in link_read["prompt"]
    assert "(mirror: " not in link_read["prompt"]
    assert _result(payload)["mirrorGaps"] == ["https://l.test: not mirrored (HTTP 404)"]


def test_research_sweep_failed_stage_clause_names_what_was_read(
    tmp_path: Path,
) -> None:
    """FAILED STAGES carries each stage's own consequence and what was READ (R5, L3).

    Round-3 review N1/N1c: one fixed sentence claimed dependency manifests were read
    after triage failed, and in a repo-less sweep that had none. Round-4 L3: the
    base named what was DISPATCHED (a null reader, a code search with no answered
    row). FAIL arm: go back to a fixed sentence, or count dispatched readers, and
    these clauses name evidence that was never read.
    """
    body = _sub(
        _sub(_SWEEP_MANDATORY_BODY, "REFUTE", _OK_VERDICT), "ADJUDICATE", "null"
    )
    for old, new in (
        ("return DEPS_STUB\n", "return DEPS_OK(_prompt)\n"),
        ("return MIRROR_STUB\n", "return MIRROR_OK(_prompt)\n"),
        ("return INDEX_STUB\n", "return INDEX_OK(_prompt)\n"),
        ("return PLAN_MANIFEST_STUB\n", "return PLAN_MANIFEST_OK(_prompt)\n"),
        ("return RETRO_STUB\n", "return null\n"),
        ("return RETRO_WRITE_STUB\n", "return null\n"),
        ("if (label === 'triage') {", "if (label === 'triage') { return null"),
    ):
        body = _sub(body, old, new)
    triage_null = _sweep_custom(
        tmp_path, "sweep-r5-triage.js", body, {"links": ["https://l.test"]}
    )
    synth = _of_kind(triage_null, "synth-prompt")[0]["prompt"]
    assert (
        "say the evidence base is: the 1 caller link(s) read + the answered"
        " code-search rows)" in synth
    )
    assert (
        '"consequence":"no hit from any fan-out manifest (planner or dependency-repo)'
        ' was triaged or read"' in synth
    )

    # repo-less, planner null: no code-search row answered, so none is evidence
    repo_less = _mandatory_run(
        tmp_path,
        "sweep-r5-norepo.js",
        {"links": ["https://l.test"], "repo": ""},
        {"plan": "null"},
    )
    synth = _of_kind(repo_less, "synth-prompt")[0]["prompt"]
    assert "say the evidence base is: the 1 caller link(s) read)" in synth
    assert "dependency-repo manifests" not in synth.split("FAILED STAGES", 1)[1]

    # the link's reader returned null: the caller link was NOT read, so it is
    # not in the base although its reader was dispatched
    body = _sub(
        body,
        "if (label === 'triage') { return null",
        "if (label === 'triage') { return null }"
        " if (label.startsWith('read')) { return null",
    )
    null_reader = _sweep_custom(
        tmp_path, "sweep-l3-null.js", body, {"links": ["https://l.test"]}
    )
    synth = _of_kind(null_reader, "synth-prompt")[0]["prompt"]
    assert "say the evidence base is: the answered code-search rows)" in synth


@pytest.mark.parametrize(
    "bad",
    [
        {"repo": "o;x/t"},
        {"repo": "o'x/t"},
        {"repo": "o x/t"},
        {"relatedRepos": ["o'x/t$(id)"]},
        {"reportPath": f"{REPO_ROOT}/docs/research/it's.md"},
    ],
    ids=["repo-semicolon", "repo-quote", "repo-space", "related-quote", "slug-quote"],
)
def test_research_sweep_rejects_an_unsafe_shell_argument(
    tmp_path: Path, bad: dict[str, object]
) -> None:
    """Repo names and the report slug reach shell commands: shape-checked (R7)."""
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"), {**ARGS, **bad}, "  return null"
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-unsafe.js")
    assert result.returncode != 0
    assert "must be" in result.stderr
    assert "[A-Za-z0-9_.-]" in result.stderr


@pytest.mark.parametrize(
    "bad",
    [{"repo": "../.."}, {"relatedRepos": ["a/.."]}],
    ids=["repo-dot-dot", "related-dot-dot"],
)
def test_research_sweep_rejects_a_dot_only_repo_segment(
    tmp_path: Path, bad: dict[str, object]
) -> None:
    """A `..` segment passes the character class but rewrites `repos/<r>`.

    Round-4 dissent 1: `../..` turns `repos/../..` into another API path. FAIL
    arm: drop the dot-only clause from `repoOk` and this dry-runs clean.
    """
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"), {**ARGS, **bad}, "  return null"
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-dots.js")
    assert result.returncode != 0
    assert "no dot-only segment" in result.stderr


@pytest.mark.parametrize(
    ("report_path", "message"),
    [
        # a `..` path segment would move every derived path (#1513)
        (f"{REPO_ROOT}/docs/../escape.md", 'must not contain a "." or ".." segment'),
        # a dot-only SLUG (`...md` -> `..`) would put mirrors in raw/../links (L2b)
        (f"{REPO_ROOT}/.agent/...md", "not dot-only"),
    ],
    ids=["dotdot-segment", "dot-only-slug"],
)
def test_research_sweep_rejects_a_dot_report_slug(
    tmp_path: Path, report_path: str, message: str
) -> None:
    """FAIL arm: drop either guard and this dry-runs clean with a traversing path."""
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "reportPath": report_path},
        "  return null",
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-dot-slug.js")
    assert result.returncode != 0
    assert message in result.stderr


def test_research_sweep_report_slug_is_unique_per_report(tmp_path: Path) -> None:
    """Two runs' `report.md` must not share a mirror directory (#1513).

    FAIL arm: go back to the basename slug and both runs mirror into
    `raw/report/links`, the later sweep overwriting the earlier one.
    """
    dirs = []
    for run_dir in ("research-a", "research-b"):
        report = f"{REPO_ROOT}/docs/research/runs/{run_dir}/report.md"
        payload = _mandatory_run(
            tmp_path,
            f"sweep-slug-{run_dir}.js",
            {"links": ["https://l.test"], "reportPath": report},
        )
        words = _command(_of_kind(payload, "mirror")[0]["prompt"], "--mirror-url")
        dirs.append(words[words.index("--mirror-path") + 1])
    assert dirs == [
        f"{REPO_ROOT}/docs/research/kb/raw/research--runs--research-a--report/links/1.md",
        f"{REPO_ROOT}/docs/research/kb/raw/research--runs--research-b--report/links/1.md",
    ]


def test_research_sweep_accepts_a_dotted_repo_name(tmp_path: Path) -> None:
    """Control arm: a name that merely CONTAINS dots (`owner/.github`) is legal.

    FAIL arm: widen the dot-only check to any dot and this throws at arg parse.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-dotted.js", {"links": [], "relatedRepos": ["owner/.github"]}
    )
    deps = _of_kind(payload, "deps")
    assert any("--repo-check owner/.github" in d["prompt"] for d in deps)


def test_research_sweep_planner_workflow_role_is_inert(tmp_path: Path) -> None:
    """Round-4 L1: a planner row tagged `health` FAILS CLOSED — inert, never `query`.

    FAIL arm: normalise a stray `health` row to `query` (the old behaviour) and
    the second run reads `complete` on a health-shaped row the planner never
    meant as its own query.
    """
    stray = "{ query: 'planner-health', role: 'health', count: 3, rc: 0 }"
    payload = _mandatory_run(
        tmp_path,
        "sweep-plan-roles.js",
        {"links": []},
        {"code_search": f"[...CODE_SEARCH_OK, {stray}]"},
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    stray_row = next(c for c in code if c["query"] == "planner-health")
    assert stray_row["role"] == "inert"
    assert stray_row["declaredRole"] == "health"
    assert [(c["query"], c["source"]) for c in code if c["role"] == "health"] == [
        (_HEALTH_CONTROL, "workflow")
    ]
    assert any(
        "recorded as inert" in n
        for n in cast("list[str]", run_result["codeSearchNotes"])
    )

    only_stray = f"[{stray}, CODE_SEARCH_OK[1], CODE_SEARCH_OK[2]]"
    payload = _mandatory_run(
        tmp_path, "sweep-plan-roles-2.js", {"links": []}, {"code_search": only_stray}
    )
    assert _result(payload)["status"] == "mandatory-gap"


@pytest.mark.parametrize(
    "terms",
    ['"tool"', "TOOL", "other/tool", "'Other/Tool'"],
    ids=["quoted", "upper", "slug", "quoted-slug"],
)
def test_research_sweep_question_slot_must_not_be_a_repo_name(
    tmp_path: Path, terms: str
) -> None:
    """F6 in the other direction: a NAME in the question-terms slot is a gap (R8, L4).

    Case-insensitive, quote-trimmed, and a slug counts as its name. FAIL arm:
    compare case-sensitively or skip the slug's name and REPO's tracker is never
    searched for the QUESTION while the run reads `complete`.
    """
    runs = f"[{{ query: {json.dumps(terms)} }}, {{ query: 'tool' }}]"
    stub = f"DEPS(_prompt, {{ runs: {runs} }})"
    payload = _mandatory_run(
        tmp_path,
        f"sweep-r8-{len(terms)}.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": stub},
    )
    gaps = cast("list[str]", _result(payload)["mandatoryGaps"])
    bare = terms.strip("'\"")
    assert (
        "dependency-repo stage for example/repo:"
        f' question-terms query "{bare}" is a repo name, so example/repo was not'
        " searched for the QUESTION"
    ) in gaps


def test_research_sweep_mirror_paths_are_quoted(tmp_path: Path) -> None:
    """ROOT and the mirror paths are quoted like the URL (R10, L2).

    A repoRoot may carry `'`.
    """
    root = f"{tmp_path}/it's root"
    payload = _mandatory_run(
        tmp_path, "sweep-root-quote.js", {"links": ["https://l.test"], "repoRoot": root}
    )
    words = _command(_of_kind(payload, "mirror")[0]["prompt"], "--mirror-url")
    raw = f"{root}/docs/research/kb/raw/research-sweep/links"
    # no `cd ROOT` (review of a09aa247): research-fanout is THIS repo's task, so a
    # ROOT in another repo must not change where it runs
    assert words[:4] == ["mise", "run", "research-fanout", "--"]
    assert words[words.index("--probe-out") + 1] == f"{raw}/1.probe.json"
    assert words[-1] == f"{raw}/1.md"


def test_research_sweep_mandatory_log_counts_the_readme_index_gap(
    tmp_path: Path,
) -> None:
    """The Mandatory log runs after the README-index gap can be appended (R10)."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-log.js",
        {"links": ["https://l.test"]},
        {"mirror_index": "INDEX_OK(_prompt, false)"},
    )
    logs = [e["message"] for e in _of_kind(payload, "log")]
    mandatory = next(m for m in logs if m.startswith("Mandatory:"))
    assert mandatory.endswith("; 1 mandatory gap(s)")


def test_research_sweep_no_manifests_return_carries_fanout_gaps(
    tmp_path: Path,
) -> None:
    """`no-manifests` still names each failed planner run (R10)."""
    failed = "[{ query: 'q', sources: ['exa'], manifest: '', rc: 1 }]"
    payload = _mandatory_run(
        tmp_path,
        "sweep-no-manifests.js",
        {"links": [], "repo": ""},
        {"plan_runs": failed},
    )
    run_result = _result(payload)
    assert run_result["status"] == "no-manifests"
    assert run_result["statuses"] == ["no-manifests", "mandatory-gap"]
    assert run_result["fanoutGaps"] == ['planner fan-out "q" rc=1, no manifest']


def test_research_sweep_planner_with_no_runs_says_so(tmp_path: Path) -> None:
    """A planner that ran nothing is named `(no runs)`, not an empty list (R10)."""
    payload = _mandatory_run(
        tmp_path, "sweep-no-runs.js", {"links": []}, {"plan_runs": "[]"}
    )
    assert _result(payload)["stageGaps"] == [
        (
            "planner fan-out produced no manifests (no runs) —"
            " exa/context7/firecrawl/github evidence from the planner is missing"
        )
    ]


def test_research_sweep_synthesis_section_list_is_one_line(tmp_path: Path) -> None:
    """#1513: Provenance and the repos-touched heading stay IN the section list.

    FAIL arm: split the list again with the evidence-table block and no single
    line names all seven sections.
    """
    payload = _mandatory_run(tmp_path, "sweep-sections.js", {"links": []})
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    sections = (
        "Answer",
        "Evidence",
        "Conflicts resolved",
        "Gaps",
        "Recommendation",
        "Provenance",
        "## GitHub repos touched",
    )
    lines = [ln for ln in synth.splitlines() if ln.startswith("Sections")]
    assert len(lines) == 1
    assert all(s in lines[0] for s in sections)


def test_research_sweep_other_missing_stages_are_mandatory_gaps(
    tmp_path: Path,
) -> None:
    """No code search, no controls, a failed fan-out, a null mirror, no repo at all."""
    cases: list[tuple[dict[str, object], dict[str, str], str]] = [
        ({"links": []}, {"code_search": "[]"}, "code search: no planner query ran"),
        (
            {"links": []},
            {
                "code_search": "[CODE_SEARCH_OK[0], CODE_SEARCH_OK[2]]",
                "deps": _README_ZERO,
            },
            "code search: no must-hit control",
        ),
        (
            {"links": []},
            {"code_search": "[CODE_SEARCH_OK[0], CODE_SEARCH_OK[1]]"},
            "code search: no fresh known-absent control",
        ),
        (
            {"links": []},
            {"deps": "DEPS(_prompt, { runs: [] })"},
            "dependency-repo stage for example/repo: run 1 wrote no manifest",
        ),
        (
            {"links": []},
            {"deps": "DEPS(_prompt, { runs: [{ query: 'q0', exists: false }] })"},
            "dependency-repo stage for example/repo: run 1 wrote no manifest",
        ),
        (
            {"links": []},
            # a self-reported rate limit with a count is still not an answer (M2)
            {
                "deps": "DEPS(_prompt,"
                " { control: { count: 7, rc: 0, rateLimited: true } })"
            },
            f'code search: README control "{_README_CONTROL}" was RATE-LIMITED',
        ),
        (
            {"links": []},
            {"deps": "DEPS(_prompt, { health: undefined })"},
            f'code search: search-health control "{_HEALTH_CONTROL}" was not run',
        ),
        (
            {"links": []},
            # an agent that typed a summary instead of copying the probe line
            {"deps": "{ line: 'rc=0, 3 runs ok' }"},
            "dependency-repo stage for example/repo: no PROBE-JSON line for",
        ),
        (
            {"links": ["https://l.test"]},
            {"mirror": "null"},
            "mirror stage for https://l.test: agent reported nothing (null)",
        ),
        (
            {"links": ["https://l.test"]},
            {"mirror_index": "INDEX_OK(_prompt, false)"},
            "mirror stage: README index ",
        ),
        ({"links": [], "repo": ""}, {}, "dependency-repo stage: no args.repo"),
    ]
    for n, (extra, stubs, expected) in enumerate(cases):
        payload = _mandatory_run(tmp_path, f"sweep-gap-{n}.js", extra, stubs)
        run_result = _result(payload)
        gaps = cast("list[str]", run_result["mandatoryGaps"])
        assert run_result["status"] == "mandatory-gap", (n, gaps)
        assert any(g.startswith(expected) for g in gaps), (n, gaps)


# Retrospect (#1502): a proposal file only, written by a verbatim writer from what
# a READ-ONLY agent proposed; it can never change the run's status.
_RETRO_FINDINGS = (
    "{ findings: ['github-discussions was empty_unverified'], proposals: [{ target:"
    " '.claude/workflows/research-sweep-run.js', change: 'probe has_discussions first',"
    " why: 'a disabled tracker reads as a gap' }] }"
)


def test_research_sweep_retrospect_writes_a_proposal_file_only(tmp_path: Path) -> None:
    """The retrospect is Explore (cannot edit); the writer may write ONE path.

    The proposal targets the workflow itself, and no agent is ever asked to edit
    it: the writer's prompt names only the `.retrospect.md` path beside the report.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-retro.js", {"links": []}, {"retro": _RETRO_FINDINGS}
    )
    run_result = _result(payload)
    calls = cast("list[dict[str, str]]", payload["calls"])
    retro_call = next(c for c in calls if c["label"] == "retrospect")
    write = _of_kind(payload, "retrospect-write")[0]["prompt"]
    # the tracked findings tree, named by the unique report slug (#1502)
    want = str(
        REPO_ROOT
        / "docs/research/kb/reports/agents/research-sweep-retrospect-research-sweep.md"
    )

    assert retro_call["agentType"] == "Explore"
    assert "READ-ONLY" in _of_kind(payload, "retrospect")[0]["prompt"]
    assert write.splitlines()[0].startswith(
        f"Write the text between the two marker lines below to {want} EXACTLY"
    )
    assert "Create, edit or delete NO other file" in write
    text = write.split("<<<RETROSPECT\n", 1)[1].split("\nRETROSPECT>>>", 1)[0]
    assert text.startswith(
        "# Research-sweep retrospect — research-sweep (PROPOSAL ONLY)"
    )
    assert "Nothing here has been applied" in text
    assert "- github-discussions was empty_unverified" in text
    assert (
        "| .claude/workflows/research-sweep-run.js | probe has_discussions first |"
        in text
    )
    assert run_result["retrospect"] == {
        "status": "written",
        "path": want,
        "findings": 1,
        "proposals": 1,
    }
    assert run_result["status"] == "complete"


def test_research_sweep_retrospect_writer_that_strays_fails_the_phase(
    tmp_path: Path,
) -> None:
    """FAIL arm of #1502: a writer reporting ANY other path failed the phase.

    And a failed retrospect never turns a failed run into `complete`: the
    mandatory-gap run stays `mandatory-gap` with the same `statuses`.
    """
    strays = "{ written: true, path: '.claude/workflows/research-sweep-run.js' }"
    payload = _mandatory_run(
        tmp_path,
        "sweep-retro-stray.js",
        {"links": []},
        {"retro": _RETRO_FINDINGS, "retro_write": strays, "deps": "null"},
    )
    run_result = _result(payload)
    retro = cast("dict[str, object]", run_result["retrospect"])
    assert retro["status"] == "write-mismatch"
    assert run_result["status"] == "mandatory-gap"
    assert run_result["statuses"] == ["mandatory-gap"]

    for stub, status in (("null", "retrospect-null"), ("'ok'", "retrospect-null")):
        payload = _mandatory_run(
            tmp_path, f"sweep-retro-{status}.js", {"links": []}, {"retro": stub}
        )
        run_result = _result(payload)
        assert cast("dict[str, object]", run_result["retrospect"])["status"] == status
        assert run_result["status"] == "complete"
        labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
        assert "retrospect-write" not in labels


def test_research_sweep_retrospect_runs_on_an_early_exit(tmp_path: Path) -> None:
    """A run that stopped at a null stage still records what was hard (#1502)."""
    failed = "[{ query: 'q', sources: ['exa'], manifest: '', rc: 1 }]"
    payload = _mandatory_run(
        tmp_path,
        "sweep-retro-early.js",
        {"links": [], "repo": ""},
        {"plan_runs": failed, "retro": _RETRO_FINDINGS},
    )
    run_result = _result(payload)
    assert run_result["status"] == "no-manifests"
    assert cast("dict[str, object]", run_result["retrospect"])["status"] == "written"
    facts = _of_kind(payload, "retrospect")[0]["prompt"]
    assert '"status":"no-manifests"' in facts
    assert "may be missing or partial" in facts

    payload = _mandatory_run(
        tmp_path, "sweep-retro-off.js", {"links": [], "retrospect": False}
    )
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    assert "retrospect" not in labels
    assert _result(payload)["retrospect"] == {"status": "skipped", "path": None}


def test_research_sweep_repo_root_is_normalised_and_dot_segments_refused(
    tmp_path: Path,
) -> None:
    """A `//` repoRoot is collapsed (python echoes it normalised); `..` is refused.

    FAIL arm: keep `//` and every mirror's echoed path mismatches, so each reads as
    "no PROBE-JSON line"; drop the `..` check and MIRROR_DIR escapes the repo.
    """
    payload = _mandatory_run(
        tmp_path,
        "sweep-root-slashes.js",
        {
            "links": ["https://l.test"],
            "repoRoot": f"{REPO_ROOT.parent}//{REPO_ROOT.name}/",
        },
    )
    words = _command(_of_kind(payload, "mirror")[0]["prompt"], "--mirror-url")
    assert words[words.index("--mirror-path") + 1] == (
        f"{REPO_ROOT}/docs/research/kb/raw/research-sweep/links/1.md"
    )

    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "repoRoot": f"{REPO_ROOT}/../elsewhere"},
        "  return null",
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-root-dotdot.js")
    assert result.returncode != 0
    assert 'repoRoot must not contain a "." or ".." segment' in result.stderr


def test_research_sweep_disabled_tracker_is_a_note_not_a_gap(tmp_path: Path) -> None:
    """Cold review F1: a repo with Discussions DISABLED can never answer that search.

    Live: rhysd/actionlint (has_discussions=false) -> empty_unverified forever.
    FAIL arm: ignore the repos API flags and every such repo is a permanent
    mandatory gap. Control arm: the same failure on a repo WITH discussions on is
    still a gap.
    """
    failed = ["github-discussions: empty_unverified (canary returned 0 items)"]
    for has, gaps in ((False, 0), (True, 1)):
        stub = (
            "DEPS(_prompt, { runs: [{ query: 'q0', requiredFailed: "
            f"{json.dumps(failed)} }}],"
            f" exists: {{ rc: 0, status: 200, fullName: 'example/repo',"
            f" hasIssues: true, hasDiscussions: {json.dumps(has)} }} }})"
        )
        payload = _mandatory_run(
            tmp_path, f"sweep-f1-{has}.js", {"links": []}, {"deps": stub}
        )
        run_result = _result(payload)
        assert len(cast("list[str]", run_result["mandatoryGaps"])) == gaps, has
        notes = cast("list[str]", run_result["codeSearchNotes"])
        assert any("has discussions disabled" in n for n in notes) is (not has)


def test_research_sweep_run_id_stamps_and_requires_this_runs_manifests(
    tmp_path: Path,
) -> None:
    """Cold review F3: with args.runId, freshness means THIS run, not "recent"."""
    payload = _mandatory_run(tmp_path, "sweep-f3.js", {"links": [], "runId": "run-42"})
    prompt = _of_kind(payload, "deps")[0]["prompt"]
    fanout = _command(prompt, "--sources")
    probe = _command(prompt, "--probe-out")
    assert fanout[fanout.index("--request-id") + 1] == "run-42"
    assert probe[probe.index("--expect-request-id") + 1] == "run-42"

    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "runId": "x;y"},
        "  return null",
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-f3-bad.js")
    assert result.returncode != 0
    assert "args.runId must be" in result.stderr


def test_research_sweep_placeholder_query_is_a_gap(tmp_path: Path) -> None:
    """Cold review F12: the literal placeholder is not the QUESTION's terms."""
    placeholder = "<2-4 short search terms from the QUESTION>"
    stub = f"DEPS(_prompt, {{ runs: [{{ query: '{placeholder}' }}] }})"
    payload = _mandatory_run(tmp_path, "sweep-f12.js", {"links": []}, {"deps": stub})
    gaps = cast("list[str]", _result(payload)["mandatoryGaps"])
    assert any("placeholder" in g and "ran verbatim" in g for g in gaps), gaps


def test_research_sweep_incomplete_search_is_never_evidence(tmp_path: Path) -> None:
    """Cold review F17: a timed-out search (incomplete_results) is not a 0."""
    rows = (
        "[{ query: 'filename:x.toml zz', role: 'query', count: 0, rc: 0,"
        " incomplete: true },"
        " { query: 'filename:x.toml mise', role: 'must-hit', count: 3, rc: 0 },"
        " CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-f17.js", {"links": []}, {"code_search": rows}
    )
    run_result = _result(payload)
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    assert code[0]["incomplete"] is True
    assert run_result["status"] == "mandatory-gap"


def test_research_sweep_repos_dedupe_case_insensitively(tmp_path: Path) -> None:
    """Cold review F18: `example/Repo` and `example/repo` are one repo, one deps dir."""
    payload = _mandatory_run(
        tmp_path, "sweep-f18.js", {"links": [], "relatedRepos": ["Example/Repo"]}
    )
    assert [e["label"] for e in _of_kind(payload, "deps")] == ["deps:example/repo"]


def test_research_sweep_early_exit_lists_the_stage_status(tmp_path: Path) -> None:
    """Cold review F13: `synth-null` with stage gaps still lists `stage-gap`."""
    body = _sub(
        _sub(_SWEEP_MANDATORY_BODY, "REFUTE", _OK_VERDICT), "ADJUDICATE", "null"
    )
    for old, new in (
        ("return DEPS_STUB\n", "return DEPS_OK(_prompt)\n"),
        ("return MIRROR_STUB\n", "return MIRROR_OK(_prompt)\n"),
        ("return INDEX_STUB\n", "return INDEX_OK(_prompt)\n"),
        ("return PLAN_MANIFEST_STUB\n", "return PLAN_MANIFEST_OK(_prompt)\n"),
        ("return RETRO_STUB\n", "return null\n"),
        ("return RETRO_WRITE_STUB\n", "return null\n"),
        ("if (label === 'plan+fetch') {", "if (label === 'plan+fetch') { return null"),
        (
            "  if (label === 'synthesize') {\n",
            "  if (label === 'synthesize') { return null\n",
        ),
    ):
        body = _sub(body, old, new)
    payload = _sweep_custom(tmp_path, "sweep-f13.js", body, {"links": []})
    run_result = _result(payload)
    assert run_result["status"] == "synth-null"
    assert run_result["statuses"] == ["synth-null", "mandatory-gap", "stage-gap"]


@pytest.mark.parametrize(
    ("has_issues", "has_prs", "gaps"),
    [(False, False, 0), (False, True, 1), (True, True, 1)],
    ids=["issues-and-prs-off", "issues-off-prs-on", "both-on"],
)
def test_research_sweep_issues_exemption_needs_prs_off_too(
    tmp_path: Path, *, has_issues: bool, has_prs: bool, gaps: int
) -> None:
    """Round-2 N1: github-issues hits search/issues, which returns PRs too.

    Live: apache/kafka (issues off, PRs on) answers ok, so a FAILED issues search
    there is a real failure. FAIL arm: exempt on has_issues alone and the
    issues-off-prs-on case hides a failed search (#1473 re-opened).
    """
    failed = ["github-issues: error (exited 1: HTTP 403)"]
    stub = (
        "DEPS(_prompt, { runs: [{ query: 'q0', requiredFailed: "
        f"{json.dumps(failed)} }}], exists: {{ rc: 0, status: 200,"
        f" fullName: 'example/repo', hasIssues: {json.dumps(has_issues)},"
        f" hasPullRequests: {json.dumps(has_prs)}, hasDiscussions: true }} }})"
    )
    payload = _mandatory_run(
        tmp_path, f"sweep-n1-{has_issues}-{has_prs}.js", {"links": []}, {"deps": stub}
    )
    assert len(cast("list[str]", _result(payload)["mandatoryGaps"])) == gaps


def test_research_sweep_round2_small_fixes(tmp_path: Path) -> None:
    """Round-2 F9 (derived ROOT normalised), N3 (runId cannot be a flag), N8."""
    report = f"{REPO_ROOT.parent}//{REPO_ROOT.name}/docs/research/runs/r9/report.md"
    payload = _mandatory_run(
        tmp_path,
        "sweep-r2-f9.js",
        {"links": ["https://l.test"], "reportPath": report, "repoRoot": None},
    )
    words = _command(_of_kind(payload, "mirror")[0]["prompt"], "--mirror-url")
    assert words[words.index("--mirror-path") + 1].startswith(
        f"{REPO_ROOT}/docs/research/kb/raw/"
    )

    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "runId": "-x"},
        "  return null",
    )
    result = _bun_run_wrapped(wrapped, tmp_path / "sweep-r2-n3.js")
    assert result.returncode != 0
    assert "args.runId must be" in result.stderr

    payload = _mandatory_run(
        tmp_path, "sweep-r2-n8.js", {"links": [], "relatedRepos": ["Example/Repo"]}
    )
    prompt = _of_kind(payload, "deps")[0]["prompt"]
    assert prompt.count("--sources") == 1, "REPO is never searched for its own name"
