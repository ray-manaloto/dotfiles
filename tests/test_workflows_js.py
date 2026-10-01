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

#: JS helpers shared by every research-sweep stub: a code search that satisfies
#: all three mandatory roles, and a dependency agent that reports one run per
#: `mise run research-fanout` command its prompt names — the cross-direction NAME
#: where the prompt gives one, `q<k>` for question terms — the repo as existing
#: under the very name its prompt checks (a different `fullName` is a rename),
#: and the search-health control only when its prompt asks for it.
_SWEEP_HELPERS = """
const CODE_SEARCH_OK = [
  { query: 'filename:mise.toml hk', role: 'query', count: 3, rc: 0 },
  { query: 'repo:example/repo filename:README.md', role: 'must-hit', count: 1, rc: 0 },
  { query: 'fresh-nonsense-token', role: 'known-absent', count: 0, rc: 0 },
]
const DEPS_OK = (prompt) => ({
  runs: prompt.split('mise run research-fanout -- "').slice(1).map((part, k) => {
    const query = part.split('"')[0]
    return { query: query.startsWith('<') ? `q${k}` : query,
      manifest: `.agent/deps/${k}/manifest.json`, rc: 0 }
  }),
  control: { count: 7, rc: 0, rateLimited: false },
  exists: { rc: 0, status: 200,
    fullName: (prompt.split('gh api -i repos/')[1] || '').split(' ')[0] },
  ...(prompt.includes("q='repo:cli/cli filename:README.md'")
    ? { health: { count: 9, rc: 0, rateLimited: false } } : {}),
})
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
      codeSearch: CODE_SEARCH_OK,
      sourceDive: true,
    }
  }
  // the mandatory stages: one fan-out run per command the prompt names
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'mirror-index') return { written: true }
  if (label.startsWith('mirror')) return { rc: 0, bytes: 42 }
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
    "codex-sol-advisor": ("codex-sol-advisor", "", ""),
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
    assert routing == _SWEEP_ROUTING
    # The returned provenance names every dispatched node (one refuter per claim).
    provenance = cast("list[dict[str, str]]", run_result["routing"])
    assert [p["node"] for p in provenance] == [c["label"] for c in calls]


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
      codeSearch: CODE_SEARCH_OK, sourceDive: false }
  }
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'mirror-index') return { written: true }
  if (label.startsWith('mirror')) return { rc: 0, bytes: 42 }
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
    body = _SWEEP_HAPPY_BODY.replace("RECONCILE", reconcile)
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
    wrapped = _custom_stub_source(
        RESEARCH_SWEEP.read_text(encoding="utf-8"),
        {**ARGS, "advisor": False},
        _SWEEP_HAPPY_BODY.replace(
            "return { reportPath: args.reportPath, loadBearing: [] }",
            "return { reportPath: args.reportPath,"
            " loadBearing: [{ claim: 'c', source: 's' }] }",
        )
        .replace(
            "if (label.startsWith('refute')) return null\n",
            "if (label.startsWith('refute'))"
            " return { claim: 'c', refuted: true, evidence: 'e' }\n"
            "  if (label === 'adjudicate')"
            " return { verdicts: [{ claim: 'c', refuted: true, evidence: 'e' }] }\n",
        )
        .replace("RECONCILE", "null"),
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
      codeSearch: CODE_SEARCH_OK, sourceDive: false }
  }
  if (label.startsWith('deps')) return DEPS_OK(_prompt)
  if (label === 'mirror-index') return { written: true }
  if (label.startsWith('mirror')) return { rc: 0, bytes: 42 }
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


def test_research_sweep_caller_links_bypass_triage_and_cap(tmp_path: Path) -> None:
    """Caller links are always read (sonnet), never ranked away or double-read.

    FAIL arm: feed LINKS through triage/READ_MAX instead of their own readers and
    `https://caller.test/b` is never read (readMax=1 keeps only one triaged URL).
    """
    body = _SWEEP_TUNING_BODY.replace("REFUTE", _OK_VERDICT).replace(
        "ADJUDICATE", "null"
    )
    payload = _sweep_custom(
        tmp_path,
        "sweep-links.js",
        body,
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
    body = _SWEEP_TUNING_BODY.replace("REFUTE", _OK_VERDICT).replace(
        "ADJUDICATE", "null"
    )
    payload = _sweep_custom(tmp_path, "sweep-per-claim.js", body, {"links": []})
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
    body = _SWEEP_TUNING_BODY.replace(
        "REFUTE",
        _FLAG_VERDICT,
    ).replace(
        "ADJUDICATE",
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
    body = _SWEEP_TUNING_BODY.replace("REFUTE", "null").replace("ADJUDICATE", "null")
    payload = _sweep_custom(tmp_path, "sweep-null-refuters.js", body, {"links": []})
    run_result = cast("dict[str, object]", payload["result"])
    verdicts = cast("list[dict[str, object]]", run_result["verdicts"])

    assert [v["refuted"] for v in verdicts] == [None, None]
    assert run_result["status"] == "verify-null"


def _flagged_run(
    tmp_path: Path, name: str, refute: str, adjudicate: str
) -> dict[str, object]:
    body = _SWEEP_TUNING_BODY.replace("REFUTE", refute).replace(
        "ADJUDICATE", adjudicate
    )
    return _sweep_custom(tmp_path, name, body, {"links": []})


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


def test_research_sweep_caller_links_survive_a_null_plan(tmp_path: Path) -> None:
    """Links are read even when the planner returns null (row 3).

    FAIL arm: return 'plan-null' unconditionally and no link is read.
    """
    body = (
        _SWEEP_TUNING_BODY.replace(
            "if (label === 'plan+fetch') {", "if (label === 'plan+fetch') { return null"
        )
        .replace("REFUTE", _OK_VERDICT)
        .replace("ADJUDICATE", "null")
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
    assert ".agent/deps/0/manifest.json" in triage_prompt
    assert "/m.json" not in triage_prompt
    # the failed stage is a named gap in synthesis and in the status (review N2)
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["status"] == "links-only"
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
    body = _SWEEP_TUNING_BODY.replace(
        "    return REFUTE",
        "    return label === 'refute:1/2' ? null : " + _OK_VERDICT,
    ).replace("ADJUDICATE", "null")
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
    body = _SWEEP_TUNING_BODY.replace("REFUTE", _OK_VERDICT).replace(
        "ADJUDICATE", "null"
    )
    payload = _sweep_custom(
        tmp_path,
        "sweep-fragment.js",
        body,
        {"links": ["https://p.test/post/#on-omarchy"]},
    )
    events = cast("list[dict[str, str]]", payload["events"])
    link_read = next(
        e for e in events if e["kind"] == "read" and e["label"].startswith("read-link")
    )
    assert "https://p.test/post#on-omarchy" in link_read["prompt"]


# The mandatory stages (docs/specs/research-enforcement-2026-09-30.md): the tuning
# body records every mandatory-stage prompt so each test can pin what it dispatched.
_SWEEP_MANDATORY_BODY = (
    _SWEEP_TUNING_BODY.replace(
        "  if (label.startsWith('deps')) return DEPS_OK(_prompt)\n",
        "  if (label.startsWith('deps')) {\n"
        "    events.push({ kind: 'deps', label, prompt: _prompt })\n"
        "    return DEPS\n"
        "  }\n",
    )
    .replace(
        "  if (label.startsWith('mirror')) return { rc: 0, bytes: 42 }\n",
        "  if (label.startsWith('mirror')) {\n"
        "    events.push({ kind: 'mirror', label, prompt: _prompt })\n"
        "    return MIRROR\n"
        "  }\n",
    )
    .replace(
        "  if (label === 'synthesize') {\n",
        "  if (label === 'synthesize') {\n"
        "    events.push({ kind: 'synth-prompt', prompt: _prompt })\n",
    )
    .replace(
        "  return 'ok'\n",
        "  if (label === 'reconcile')"
        " events.push({ kind: 'reconcile', prompt: _prompt })\n"
        "  return 'ok'\n",
    )
)


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
        "mirror": "{ rc: 0, bytes: 42 }",
        "mirror_index": "{ written: true }",
        "code_search": "CODE_SEARCH_OK",
        "plan_runs": _PLAN_RUNS_OK,
        "plan": "",
        **(stubs or {}),
    }
    deps, mirror, code_search = stub["deps"], stub["mirror"], stub["code_search"]
    body = (
        _SWEEP_MANDATORY_BODY.replace("REFUTE", _OK_VERDICT)
        .replace("ADJUDICATE", "null")
        .replace("return DEPS\n", f"return {deps}\n")
        .replace("return MIRROR\n", f"return {mirror}\n")
        .replace(
            "if (label === 'mirror-index') return { written: true }",
            f"if (label === 'mirror-index') return {stub['mirror_index']}",
        )
        .replace("codeSearch: CODE_SEARCH_OK", f"codeSearch: {code_search}")
        .replace(
            f"return {{ runs: {_PLAN_RUNS_OK},", f"return {{ runs: {stub['plan_runs']},"
        )
    )
    if stub["plan"]:
        body = body.replace(
            "if (label === 'plan+fetch') {",
            f"if (label === 'plan+fetch') {{ return {stub['plan']}",
        )
    return _sweep_custom(tmp_path, name, body, extra_args)


def _of_kind(payload: Mapping[str, object], kind: str) -> list[dict[str, str]]:
    events = cast("list[dict[str, str]]", payload["events"])
    return [e for e in events if e["kind"] == kind]


def test_research_sweep_mirrors_each_caller_link_once(tmp_path: Path) -> None:
    """One mirror agent per caller link, via the mise-pinned firecrawl, plus a README.

    FAIL arm: batch the links into one mirror prompt, or call a bare `firecrawl`,
    and the per-link count or the `mise exec -- firecrawl` assertion fails.
    """
    links = ["https://a.test/x", "https://b.test/y"]
    payload = _mandatory_run(tmp_path, "sweep-mirror.js", {"links": links})
    mirrors = _of_kind(payload, "mirror")
    labels = [c["label"] for c in cast("list[dict[str, str]]", payload["calls"])]
    raw = f"{REPO_ROOT}/docs/research/kb/raw/research-sweep/links"

    assert [m["label"] for m in mirrors] == ["mirror:1/2", "mirror:2/2"]
    for n, (m, url) in enumerate(zip(mirrors, links, strict=True), start=1):
        assert f"mise exec -- firecrawl scrape '{url}'" in m["prompt"]
        assert "--format markdown --only-main-content" in m["prompt"]
        assert f"-o '{raw}/{n}.md'" in m["prompt"]
        assert links[2 - n] not in m["prompt"], "one link per mirror agent"
    assert labels.count("mirror-index") == 1
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert f"(mirror: {raw}/1.md, 42 bytes)" in link_read["prompt"]
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["status"] == "complete"


def test_research_sweep_unfetchable_link_is_a_named_gap(tmp_path: Path) -> None:
    """A link firecrawl cannot fetch is a named gap and is read live, not dropped."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-mirror-fail.js",
        {"links": ["https://dead.test"]},
        {"mirror": "{ rc: 1, bytes: 0, reason: 'HTTP 404' }"},
    )
    run_result = cast("dict[str, object]", payload["result"])
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )

    assert run_result["mirrorGaps"] == ["https://dead.test: not mirrored (HTTP 404)"]
    assert "MIRROR GAPS:" in synth
    assert "(NO MIRROR: HTTP 404)" in link_read["prompt"]
    # the stage RAN; the world said no — not a mandatory gap
    assert run_result["status"] == "complete"


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
    out = "--out .agent/kb/raw/research-fanout/research-sweep/deps"
    assert f"{out}/example--repo/1" in main_prompt
    assert f"{out}/example--repo/2" in main_prompt
    assert f"{out}/other--tool/1" in other_prompt
    run_result = cast("dict[str, object]", payload["result"])
    assert len(cast("list[object]", run_result["dependencyRuns"])) == 3
    assert run_result["status"] == "complete"


def test_research_sweep_empty_code_search_still_records_the_query(
    tmp_path: Path,
) -> None:
    """A zero-count code search is evidence: its query reaches synthesis + result."""
    empty = (
        "[{ query: 'filename:nothing.toml zz', role: 'query', count: 0, rc: 0 },"
        " CODE_SEARCH_OK[1], CODE_SEARCH_OK[2]]"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-code-empty.js", {"links": []}, {"code_search": empty}
    )
    run_result = cast("dict[str, object]", payload["result"])
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    code = cast("list[dict[str, object]]", run_result["codeSearch"])

    assert code[0] == {
        "query": "filename:nothing.toml zz",
        "role": "query",
        "count": 0,
        "rc": 0,
        "source": "planner",
        "rateLimited": False,
    }
    assert "filename:nothing.toml zz" in synth
    assert '"Code search" (query |' in synth
    assert run_result["status"] == "complete"


def test_research_sweep_missing_dependency_stage_is_a_mandatory_gap(
    tmp_path: Path,
) -> None:
    """The §4 control arm: the dependency stage stubbed out never reads `complete`.

    FAIL arm: drop the null check on a dependency agent and status is `complete`.
    """
    payload = _mandatory_run(
        tmp_path, "sweep-deps-null.js", {"links": []}, {"deps": "null"}
    )
    run_result = cast("dict[str, object]", payload["result"])

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


_README_ZERO = (
    "{ ...DEPS_OK(_prompt), control: { count: 0, rc: 0, rateLimited: false } }"
)
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
    run_result = cast("dict[str, object]", payload["result"])
    code = cast("list[dict[str, object]]", run_result["codeSearch"])
    notes = cast("list[str]", run_result["codeSearchNotes"])
    deps_prompt = _of_kind(payload, "deps")[0]["prompt"]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert f"-f q='{_README_CONTROL}' --jq .total_count" in deps_prompt
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
    run_result = cast("dict[str, object]", payload["result"])
    deps_prompt = _of_kind(payload, "deps")[0]["prompt"]

    assert "gh api -i repos/example/repo --jq .full_name" in deps_prompt
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
    zero = "{ ...DEPS_OK(_prompt), health: { count: 0, rc: 0, rateLimited: false } }"
    payload = _mandatory_run(
        tmp_path,
        "sweep-health-zero.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": zero},
    )
    run_result = cast("dict[str, object]", payload["result"])
    deps = {e["label"]: e["prompt"] for e in _of_kind(payload, "deps")}
    code = cast("list[dict[str, object]]", run_result["codeSearch"])

    assert f"-f q='{_HEALTH_CONTROL}'" in deps["deps:example/repo"]
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
        "{ ...DEPS_OK(_prompt), control: { count: -1, rc: 1, rateLimited: true },"
        " health: { count: -1, rc: 1, rateLimited: true } }"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-health-403.js", {"links": []}, {"deps": both}
    )
    gaps = cast(
        "list[str]", cast("dict[str, object]", payload["result"])["mandatoryGaps"]
    )
    assert (
        f'code search: README control "{_README_CONTROL}" was RATE-LIMITED (HTTP 403),'
        " not 0 — gh auth, rate-limit or search is broken"
    ) in gaps


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, "dependency repo example/repo not found via the repos API (HTTP 404)"),
        (
            403,
            (
                "could not check example/repo via the repos API"
                " (HTTP 403 — rate-limited or forbidden)"
            ),
        ),
        (
            429,
            (
                "could not check example/repo via the repos API"
                " (HTTP 429 — rate-limited or forbidden)"
            ),
        ),
        (500, "could not check example/repo via the repos API (HTTP 500)"),
    ],
)
def test_research_sweep_unchecked_dependency_repo_is_one_gap(
    tmp_path: Path, status: int, expected: str
) -> None:
    """Only a 404 is "not found"; a 403/429/other is "could not check" (round-3 R6).

    Reported ONCE, never also as an auth failure or a not-indexed note. FAIL arm:
    call every non-zero rc "not found" and a rate-limited check sends the operator
    hunting for a typo.
    """
    missing = (
        f"{{ ...DEPS_OK(_prompt), exists: {{ rc: 1, status: {status}, fullName: '' }},"
        " control: { count: 0, rc: 0, rateLimited: false } }"
    )
    payload = _mandatory_run(
        tmp_path, f"sweep-repo-{status}.js", {"links": []}, {"deps": missing}
    )
    run_result = cast("dict[str, object]", payload["result"])

    assert run_result["mandatoryGaps"] == [expected]
    assert run_result["codeSearchNotes"] == []
    assert run_result["status"] == "mandatory-gap"


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
        f"{{ ...DEPS_OK(_prompt), exists: {{ rc: 0, status: 200,"
        f" fullName: '{full_name}' }},"
        " control: { count: 0, rc: 0, rateLimited: false } }"
    )
    payload = _mandatory_run(
        tmp_path, f"sweep-rename-{full_name[0]}.js", {"links": []}, {"deps": renamed}
    )
    run_result = cast("dict[str, object]", payload["result"])
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
        "{ ...DEPS_OK(_prompt), control: { count: 0, rc: 0, rateLimited: false },"
        " health: { count: 0, rc: 0, rateLimited: false } }"
    )
    payload = _mandatory_run(
        tmp_path, "sweep-note-health0.js", {"links": []}, {"deps": zero_both}
    )
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["codeSearchNotes"] == []

    # the first deps agent null: health never ran, so other/tool's 0 gets no note
    first_null = (
        "_prompt.includes('--repo example/repo') ? null : { ...DEPS_OK(_prompt),"
        " control: { count: 0, rc: 0, rateLimited: false } }"
    )
    payload = _mandatory_run(
        tmp_path,
        "sweep-note-unrun.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": first_null},
    )
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["codeSearchNotes"] == []
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
    run_result = cast("dict[str, object]", payload["result"])
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
    limited = (
        "{ ...DEPS_OK(_prompt), control: { count: -1, rc: 1, rateLimited: true } }"
    )
    payload = _mandatory_run(tmp_path, "sweep-403.js", {"links": []}, {"deps": limited})
    run_result = cast("dict[str, object]", payload["result"])
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
            " (HTTP 403), not 0"
        )
    ]
    assert "write RATE-LIMITED, never 0" in synth


@pytest.mark.parametrize("links", [[], ["https://l.test"]], ids=["no-link", "one-link"])
def test_research_sweep_planner_fanout_without_manifests_is_not_complete(
    tmp_path: Path, links: list[str]
) -> None:
    """Dependency manifests must not mask a planner fan-out that wrote none (F1, S2).

    Cold review 836983e3 S2: a planner whose every run failed read `complete`,
    because the dependency manifests satisfied the manifest count. FAIL arm: count
    the planner and dependency manifests together again and this reads `complete`.
    """
    failed = "[{ query: 'q', sources: ['exa'], manifest: '', rc: 1 }]"
    payload = _mandatory_run(
        tmp_path, "sweep-s2.js", {"links": links}, {"plan_runs": failed}
    )
    run_result = cast("dict[str, object]", payload["result"])
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]

    assert run_result["status"] == "links-only"
    assert run_result["stageGaps"] == [
        (
            "planner fan-out produced no manifests (q rc=1) —"
            " exa/context7/firecrawl/github evidence from the planner is missing"
        )
    ]
    assert run_result["fanoutGaps"] == ['planner fan-out "q" rc=1, no manifest']
    assert "FANOUT GAPS" in synth
    base = "hits triaged from the dependency-repo manifests + the code-search rows"
    if links:
        base = "the 1 caller link(s) + " + base
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
    run_result = cast("dict[str, object]", payload["result"])
    triage = _of_kind(payload, "triage-prompt")[0]["prompt"]
    synth = _of_kind(payload, "synth-prompt")[0]["prompt"]
    assert ".agent/deps/0/manifest.json" in triage
    assert "/m.json" not in triage
    assert (
        "say the evidence base is: hits triaged from the dependency-repo manifests"
        " + the code-search rows)" in synth
    )
    assert run_result["status"] == "links-only"
    assert run_result["stageGaps"] == [
        (
            "planner agent reported nothing (null) — no planner fan-out manifest"
            " reached triage"
        )
    ]


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
    run_result = cast("dict[str, object]", payload["result"])
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
    """The dependency check pins WHICH query ran, not just how many (F6, S3).

    FAIL arm: keep only the run-count check and an agent that swapped the
    cross-direction NAME for question terms reads `complete`.
    """
    swapped = (
        "{ ...DEPS_OK(_prompt), runs: DEPS_OK(_prompt).runs"
        ".map((x, k) => ({ ...x, query: `terms${k}` })) }"
    )
    payload = _mandatory_run(
        tmp_path,
        "sweep-s3.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": swapped},
    )
    run_result = cast("dict[str, object]", payload["result"])
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

    short = "{ ...DEPS_OK(_prompt), runs: DEPS_OK(_prompt).runs.slice(0, 1) }"
    payload = _mandatory_run(
        tmp_path,
        "sweep-s3-short.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": short},
    )
    gaps = cast(
        "list[str]", cast("dict[str, object]", payload["result"])["mandatoryGaps"]
    )
    assert gaps == [
        "dependency-repo stage for example/repo: 1 of 2 run(s) reported",
        (
            "dependency-repo stage for example/repo:"
            ' cross-direction query "tool" not run (got "missing")'
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
    command = next(line for line in prompt.splitlines() if "firecrawl scrape" in line)
    raw = f"{REPO_ROOT}/docs/research/kb/raw/research-sweep/links"

    assert shlex.split(command) == [
        "mkdir",
        "-p",
        raw,
        "&&",
        "mise",
        "exec",
        "--",
        "firecrawl",
        "scrape",
        url,
        "--format",
        "markdown",
        "--only-main-content",
        "-o",
        f"{raw}/1.md",
    ]


def test_research_sweep_empty_mirror_is_not_read_as_a_mirror(tmp_path: Path) -> None:
    """rc=0 with 0 bytes is NO MIRROR: the reader reads the link live (M7)."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-mirror-empty.js",
        {"links": ["https://l.test"]},
        {"mirror": "{ rc: 0, bytes: 0 }"},
    )
    link_read = next(
        e for e in _of_kind(payload, "read") if e["label"].startswith("read-link")
    )
    assert "(NO MIRROR: rc=0, 0 bytes)" in link_read["prompt"]
    assert "(mirror: " not in link_read["prompt"]


def test_research_sweep_failed_stage_clause_names_what_was_read(
    tmp_path: Path,
) -> None:
    """FAILED STAGES carries each stage's own consequence and the real evidence (R5).

    Round-3 review N1/N1c: one fixed sentence claimed dependency manifests were read
    after triage failed, and in a repo-less sweep that had none. FAIL arm: go back to
    a fixed sentence and these clauses name evidence that was never read.
    """
    # triage null needs its own stub: swap the triage branch for a null return
    body = (
        _SWEEP_MANDATORY_BODY.replace("REFUTE", _OK_VERDICT)
        .replace("ADJUDICATE", "null")
        .replace("return DEPS\n", "return DEPS_OK(_prompt)\n")
        .replace("return MIRROR\n", "return { rc: 0, bytes: 42 }\n")
        .replace("if (label === 'triage') {", "if (label === 'triage') { return null")
    )
    triage_null = _sweep_custom(
        tmp_path, "sweep-r5-triage.js", body, {"links": ["https://l.test"]}
    )
    synth = _of_kind(triage_null, "synth-prompt")[0]["prompt"]
    assert (
        "say the evidence base is: the 1 caller link(s) + the code-search rows)"
        in synth
    )
    assert (
        '"consequence":"no hit from any fan-out manifest (planner or dependency-repo)'
        ' was triaged or read"' in synth
    )

    repo_less = _mandatory_run(
        tmp_path,
        "sweep-r5-norepo.js",
        {"links": ["https://l.test"], "repo": ""},
        {"plan": "null"},
    )
    synth = _of_kind(repo_less, "synth-prompt")[0]["prompt"]
    assert (
        "say the evidence base is: the 1 caller link(s) + the code-search rows)"
        in synth
    )
    assert "dependency-repo manifests" not in synth.split("FAILED STAGES", 1)[1]


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


def test_research_sweep_question_slot_must_not_be_a_repo_name(tmp_path: Path) -> None:
    """F6 in the other direction: a NAME in the question-terms slot is a gap (R8).

    And an echoed `"tool"` (with its quotes) is the query that ran, not a miss.
    FAIL arm: check only the cross-direction slot and REPO's tracker is never
    searched for the QUESTION while the run reads `complete`.
    """
    both_names = (
        "{ ...DEPS_OK(_prompt), runs: DEPS_OK(_prompt).runs"
        ".map(x => ({ ...x, query: '\"tool\"' })) }"
    )
    payload = _mandatory_run(
        tmp_path,
        "sweep-r8.js",
        {"links": [], "relatedRepos": ["other/tool"]},
        {"deps": both_names},
    )
    gaps = cast(
        "list[str]", cast("dict[str, object]", payload["result"])["mandatoryGaps"]
    )
    assert gaps == [
        (
            "dependency-repo stage for example/repo:"
            ' question-terms query "tool" is a repo name, so example/repo was not'
            " searched for the QUESTION"
        ),
        (
            'dependency-repo stage for other/tool: cross-direction query "repo" not run'
            ' (got "tool")'
        ),
    ]


def test_research_sweep_mirror_paths_are_quoted(tmp_path: Path) -> None:
    """The mirror DIRECTORY is quoted like the URL: a repoRoot may carry `'` (R10)."""
    root = f"{tmp_path}/it's root"
    payload = _mandatory_run(
        tmp_path, "sweep-root-quote.js", {"links": ["https://l.test"], "repoRoot": root}
    )
    prompt = _of_kind(payload, "mirror")[0]["prompt"]
    command = next(line for line in prompt.splitlines() if "firecrawl scrape" in line)
    raw = f"{root}/docs/research/kb/raw/research-sweep/links"
    words = shlex.split(command)
    assert words[2] == raw
    assert words[-1] == f"{raw}/1.md"


def test_research_sweep_mandatory_log_counts_the_readme_index_gap(
    tmp_path: Path,
) -> None:
    """The Mandatory log runs after the README-index gap can be appended (R10)."""
    payload = _mandatory_run(
        tmp_path,
        "sweep-log.js",
        {"links": ["https://l.test"]},
        {"mirror_index": "{ written: false }"},
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
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["status"] == "no-manifests"
    assert run_result["fanoutGaps"] == ['planner fan-out "q" rc=1, no manifest']


def test_research_sweep_planner_with_no_runs_says_so(tmp_path: Path) -> None:
    """A planner that ran nothing is named `(no runs)`, not an empty list (R10)."""
    payload = _mandatory_run(
        tmp_path, "sweep-no-runs.js", {"links": []}, {"plan_runs": "[]"}
    )
    run_result = cast("dict[str, object]", payload["result"])
    assert run_result["stageGaps"] == [
        (
            "planner fan-out produced no manifests (no runs) —"
            " exa/context7/firecrawl/github evidence from the planner is missing"
        )
    ]


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
            {
                "deps": "{ ...DEPS_OK(_prompt),"
                " runs: [{ query: 'q', manifest: '/tmp/d.json', rc: 1 }] }"
            },
            'dependency-repo stage for example/repo: "q" rc=1',
        ),
        (
            {"links": []},
            {"deps": "{ ...DEPS_OK(_prompt), runs: [] }"},
            "dependency-repo stage for example/repo: 0 of 1 run(s) reported",
        ),
        (
            {"links": []},
            # a self-reported rate limit with a count is still not an answer (M2)
            {
                "deps": "{ ...DEPS_OK(_prompt),"
                " control: { count: 7, rc: 0, rateLimited: true } }"
            },
            f'code search: README control "{_README_CONTROL}" was RATE-LIMITED',
        ),
        (
            {"links": []},
            {"deps": "{ ...DEPS_OK(_prompt), health: undefined }"},
            f'code search: search-health control "{_HEALTH_CONTROL}" was not run',
        ),
        (
            {"links": ["https://l.test"]},
            {"mirror": "null"},
            "mirror stage for https://l.test: agent reported nothing (null)",
        ),
        (
            {"links": ["https://l.test"]},
            {"mirror_index": "{ written: false }"},
            "mirror stage: README index ",
        ),
        ({"links": [], "repo": ""}, {}, "dependency-repo stage: no args.repo"),
    ]
    for n, (extra, stubs, expected) in enumerate(cases):
        payload = _mandatory_run(tmp_path, f"sweep-gap-{n}.js", extra, stubs)
        run_result = cast("dict[str, object]", payload["result"])
        gaps = cast("list[str]", run_result["mandatoryGaps"])
        assert run_result["status"] == "mandatory-gap", (n, gaps)
        assert any(g.startswith(expected) for g in gaps), (n, gaps)
