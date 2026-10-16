# Copyright (c) 2026 Raymond Manaloto
"""Public hook-wire controls for the Codex research coverage gate."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, codex_research_gate, sdlc_team

HOOK = Path(__file__).parent.parent / "scripts" / "codex-research-gate.py"
# Only this exact caller first line binds a turn as research (round 3).
_DIRECTIVE = "[research-scope: research]\n"
_RESEARCH = _DIRECTIVE + "Research Codex hooks"


# Round 4: Stop blocks only on a valid new-format research record; anything
# else passes, with this notice when the turn directory exists (r3 P3-3).
_NOTICE = "Research enforcement did not apply to this turn: "


@pytest.mark.parametrize(
    "raw",
    [
        b"{",
        b"[]",
        b"\xff",
        b"{}",
        b'{"prompt_sha256":null}',
        b'{"scope":[]}',
        b'{"caller_scope":{}}',
        None,
    ],
    ids=[
        "truncated",
        "array",
        "invalid-utf8",
        "empty",
        "null-digest",
        "list-scope",
        "caller-scope",
        "directory",
    ],
)
def test_research_submit_over_unusable_state_warns_without_rewriting(
    tmp_path: Path, raw: bytes | None
) -> None:
    """r3 P2-1, P3-3: retained state that is no research binding never blocks."""
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": _RESEARCH,
    }
    _invoke(tmp_path, event)
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    if raw is None:
        marker.unlink()
        marker.mkdir()
    else:
        marker.write_bytes(raw)
    result = _invoke(tmp_path, event)
    assert "decision" not in result
    assert "not enforced" in str(result["systemMessage"])
    if raw is None:
        assert marker.is_dir()
    else:
        assert marker.read_bytes() == raw


def test_valid_repeated_research_submit_distinguishes_same_and_different_prompts(
    tmp_path: Path,
) -> None:
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": _RESEARCH,
    }
    _invoke(tmp_path, event)
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    original = marker.read_bytes()
    assert _invoke(tmp_path, event) == {}
    assert _invoke(tmp_path, {**event, "prompt": _RESEARCH + " again"}) == {
        "decision": "block",
        "reason": "Research scope already bound to a different submission.",
    }
    assert marker.read_bytes() == original


@pytest.mark.parametrize("scope", ["implementation", "text-edit", "local-only"])
def test_non_research_directive_writes_no_state_and_never_blocks_a_later_prompt(
    tmp_path: Path, scope: str
) -> None:
    """r3 P2-1: a later, different prompt in the same turn is never refused."""
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    submit = {**base, "hook_event_name": "UserPromptSubmit"}
    first = f"[research-scope: {scope}]\nResearch the latest uv releases."
    _invoke(tmp_path, {**submit, "prompt": first})
    assert not (tmp_path / ".codex/research-coverage/session-1").exists()
    later = _invoke(tmp_path, {**submit, "prompt": "Also fix the README typo."})
    assert "decision" not in later
    stop: dict[str, object] = {
        **base,
        "hook_event_name": "Stop",
        "last_assistant_message": "Done.",
    }
    assert _invoke(tmp_path, stop) == {}


@pytest.mark.parametrize(
    "manifest_raw",
    [None, b'{"strict_five":true,"request_id":"turn-1","sources":[]}'],
)
def test_local_only_turn_never_blocks_and_keeps_a_retained_manifest(
    tmp_path: Path, manifest_raw: bytes | None
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    started = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: local-only]\nInvestigate the saved receipt.",
        },
    )
    assert "Do not launch providers" in json.dumps(started)
    assert "research-fanout" not in json.dumps(started)
    directory = tmp_path / ".codex/research-coverage/session-1/turn-1"
    manifest = directory / "manifest.json"
    if manifest_raw is not None:
        directory.mkdir(parents=True)
        manifest.write_bytes(manifest_raw)
    stopped = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": "RESEARCH INCOMPLETE: Context7 monthly quota.",
        },
    )
    if manifest_raw is None:
        assert stopped == {}
    else:
        assert stopped == {
            "systemMessage": _NOTICE + "research submission record missing."
        }
        assert manifest.read_bytes() == manifest_raw


@pytest.mark.parametrize(
    "scope", ["local-only", "strict-five", "implementation", "research"]
)
def test_rendered_sdlc_request_reaches_real_hook_submission_boundary(
    tmp_path: Path, scope: str
) -> None:
    request = codec.decode(
        json.dumps(
            {
                "spec_file": str(tmp_path / "spec.md"),
                "research_scope": scope,
                "task": "Investigate the retained Codex research receipt.",
            }
        ).encode(),
        sdlc_team.SdlcTeamRequest,
    )
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    prompt = sdlc_team.build_prompt(request, tmp_path)
    started = _invoke(
        tmp_path, {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt}
    )
    stopped = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": "RESEARCH INCOMPLETE: retained quota blocker.",
        },
    )
    if scope == "research":
        assert "--strict-five" in json.dumps(started)
        assert stopped["decision"] == "block"
    else:
        assert "--strict-five" not in json.dumps(started)
        assert stopped == {}


def test_same_turn_cannot_be_redeclared_local_after_research_submission(
    tmp_path: Path,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    original = marker.read_bytes()
    replay = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: local-only]\nResearch Codex hooks",
        },
    )
    assert replay["decision"] == "block"
    assert marker.read_bytes() == original
    assert _invoke(tmp_path, {**base, "hook_event_name": "Stop"})["decision"] == "block"


@pytest.mark.parametrize(
    "prompt",
    [
        _RESEARCH,
        _DIRECTIVE + "> [research-scope: local-only]\nResearch Codex hooks",
        _DIRECTIVE + "Quoted:\n[research-scope: local-only]\nResearch Codex hooks",
        _DIRECTIVE + "```\n[research-scope: local-only]\n```\nResearch Codex hooks",
    ],
)
def test_ordinary_research_ignores_misplaced_and_stop_declarations(
    tmp_path: Path,
    prompt: str,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    submit = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
            "research_scope": "local-only",
        },
    )
    assert "--strict-five" in json.dumps(submit)
    stop = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "research_scope": "local-only",
            "prompt": "[research-scope: local-only]\nResearch Codex hooks",
            "last_assistant_message": "[research-scope: local-only]",
        },
    )
    assert stop["decision"] == "block"
    assert "strict-five research command" in str(stop["reason"])


_RESEARCH_DIGEST = hashlib.sha256(_RESEARCH.encode()).hexdigest()
_VALID_RECORD: dict[str, object] = {
    "turn_id": "turn-1",
    "prompt_sha256": _RESEARCH_DIGEST,
    "scope": "research",
    "policy": "strict-five-v2",
}


@pytest.mark.parametrize(
    ("record", "notice"),
    [
        (
            {
                "turn_id": "turn-1",
                "prompt_sha256": _RESEARCH_DIGEST,
                "policy": "strict-five-v2",
            },
            False,
        ),
        ({"scope": "implementation"}, False),
        ({"caller_scope": {"scope": "local-only"}}, False),
        ({"scope": []}, True),
        ({"scope": {"research": 1}}, True),
        ({"scope": "research"}, True),
        ({**_VALID_RECORD, "turn_id": "turn-2"}, True),
        ({**_VALID_RECORD, "policy": "strict-five-v1"}, True),
        ({**_VALID_RECORD, "prompt_sha256": "SYNTHETIC_BAD_DIGEST"}, True),
        ({**_VALID_RECORD, "policy": ["strict-five-v2"]}, True),
    ],
    ids=[
        "legacy-hook-format",
        "work-scope",
        "caller-scope",
        "list-scope",
        "dict-scope",
        "research-no-identity",
        "other-turn",
        "old-policy",
        "bad-digest",
        "list-policy",
    ],
)
def test_stop_blocks_only_on_a_valid_research_record(
    tmp_path: Path, record: dict[str, object], *, notice: bool
) -> None:
    """r3 P3-3, security P3-1: no forged, legacy or malformed record can block."""
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path, {**base, "hook_event_name": "UserPromptSubmit", "prompt": _RESEARCH}
    )
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    marker.write_text(json.dumps(record))
    for active in (False, True):
        result = _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": active,
                "last_assistant_message": "Done.",
            },
        )
        if notice:
            assert result == {
                "systemMessage": _NOTICE + "research submission record malformed."
            }
        else:
            assert result == {}
    marker.write_text(json.dumps(_VALID_RECORD))
    assert _invoke(tmp_path, {**base, "hook_event_name": "Stop"})["decision"] == (
        "block"
    )


def _invoke(
    tmp_path: Path, event: dict[str, object], hook: Path = HOOK
) -> dict[str, object]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        # Cold subprocess startup under the AMD64 devcontainer can exceed 3s.
        # This is a hang guard, not a hook latency assertion.
        timeout=15,
        check=True,
    )
    return json.loads(result.stdout)


def test_research_turn_requires_receipt_and_allows_honest_failure(
    tmp_path: Path,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    started = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    submit_output = started["hookSpecificOutput"]
    assert isinstance(submit_output, dict)
    context = submit_output["additionalContext"]
    assert isinstance(context, str)
    assert "--strict-five" in context
    blocked = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert blocked["decision"] == "block"
    reason = blocked["reason"]
    assert isinstance(reason, str)
    assert "Research coverage failed" in reason
    incomplete = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "last_assistant_message": (
                "RESEARCH INCOMPLETE: Exa authentication failed."
            ),
        },
    )
    assert "systemMessage" in incomplete


def test_unrelated_turn_and_heartbeat_do_not_trigger_gate(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-2"}
    assert (
        _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Format this sentence",
            },
        )
        == {}
    )
    assert _invoke(tmp_path, {**base, "hook_event_name": "Stop"}) == {}
    assert (
        _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "<heartbeat>research</heartbeat>",
            },
        )
        == {}
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Compare uv and Poetry for Python dependency management.", "ordinary"),
        ("Find the latest fnox version.", "ordinary"),
        ("Bump codex to the newest version of the current tools.", "ordinary"),
        ("Investigate the failing test and fix it.", "ordinary"),
        ("Research Codex agent workflows.", "gated"),
        ("Look up the uv changelog.", "gated"),
        ("Search the web for mise release notes.", "gated"),
        ("Print the current directory.", "ordinary"),
        ("Rename the variable sources to inputs.", "ordinary"),
        ("Compare these two local functions.", "ordinary"),
    ],
)
def test_research_hint_triggers_only_on_research_verbs(
    tmp_path: Path, prompt: str, expected: str
) -> None:
    result = _invoke(
        tmp_path,
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        },
    )
    assert bool(result) is (expected == "gated")


def test_malformed_manifest_returns_block_decision(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    manifest = (
        tmp_path
        / ".codex"
        / "research-coverage"
        / "session-1"
        / "turn-1"
        / "manifest.json"
    )
    manifest.write_text("[]", encoding="utf-8")
    result = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert result["decision"] == "block"
    reason = result["reason"]
    assert isinstance(reason, str)
    assert "malformed research manifest" in reason


def _hook_manifest(directory: Path) -> Path:
    """Independent complete receipt with one hashed metered-provider envelope."""
    sources = {
        "github-issues": {"items": [{"html_url": "https://primary.test"}]},
        "github-discussions": {
            "data": {"search": {"nodes": [{"url": "https://primary.test"}]}}
        },
        "github-releases": [{"html_url": "https://primary.test"}],
        "exa": {"requestId": "r1", "results": [{"url": "https://primary.test"}]},
        "context7": "Context7 documentation",
        "firecrawl-developer": {
            "http_status": 402,
            "rc": None,
            "body": "",
            "stderr_redacted": "",
        },
        "firecrawl-search": {
            "success": True,
            "data": {"web": [{"url": "https://primary.test"}]},
        },
        "last30days": {"schema_version": "1.3", "source_status": {"reddit": "ok"}},
    }
    rows = []
    for source, payload in sources.items():
        raw = (
            payload.encode()
            if isinstance(payload, str)
            else json.dumps(payload).encode()
        )
        path = directory / f"{source}.raw"
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        row = {
            "source": source,
            "status": "ok",
            "items": [{"url": "https://primary.test"}],
            "raw_file": str(path),
            "raw_sha256": digest,
        }
        if source == "firecrawl-developer":
            primary = directory / "firecrawl-developer.primary.raw"
            primary.write_bytes(raw)
            row.update(
                status="skipped",
                items=[],
                skip_reason="credits-exhausted",
                provisional=True,
                attempts=[
                    {
                        "route": source,
                        "status": "skipped",
                        "http_status": 402,
                        "reason": "HTTP 402",
                        "raw_file": str(primary),
                        "raw_sha256": digest,
                    }
                ],
            )
        rows.append(row)
    path = directory / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "strict_five": True,
                "policy_version": "strict-five-v2",
                "request_id": "turn-1",
                "query": "hooks",
                "repo": "openai/codex",
                "sources": rows,
            }
        )
    )
    return path


def test_hook_provisional_pass_and_forged_evidence_block(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    directory = tmp_path / ".codex/research-coverage/session-1/turn-1"
    manifest = _hook_manifest(directory)
    result = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert result["decision"] == "block"
    assert "PROVISIONAL" in str(result["reason"])
    assert "firecrawl-developer" in str(result["reason"])
    data = json.loads(manifest.read_text())
    row = next(r for r in data["sources"] if r["source"] == "firecrawl-developer")
    forged = b'{"http_status":500,"rc":null,"body":"","stderr_redacted":""}'
    Path(row["attempts"][0]["raw_file"]).write_bytes(forged)
    row["attempts"][0]["raw_sha256"] = hashlib.sha256(forged).hexdigest()
    Path(row["raw_file"]).write_bytes(forged)
    row["raw_sha256"] = hashlib.sha256(forged).hexdigest()
    manifest.write_text(json.dumps(data))
    result = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert result["decision"] == "block"
    assert "does not re-derive" in str(result["reason"])


def test_submit_context_stays_compact_from_long_checkout(tmp_path: Path) -> None:
    root = tmp_path / ("long-checkout-" * 15)
    script = root / "scripts/codex-research-gate.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(HOOK, script)
    # The copied hook must use real package imports, never a mocked validator.
    imported = subprocess.run(
        [sys.executable, "-c", "import dotfiles_setup"],
        capture_output=True,
        check=False,
    )
    if imported.returncode != 0:
        shutil.copytree(HOOK.parent.parent / "python/src", root / "python/src")
    result = _invoke(
        tmp_path,
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
        script,
    )
    specific = result["hookSpecificOutput"]
    assert isinstance(specific, dict)
    context = specific["additionalContext"]
    assert isinstance(context, str)
    assert len(context) <= 1000
    assert f"mise -C ~/{root.relative_to(tmp_path)} run research-fanout" in context
    assert "PROVISIONAL" in context
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    assert json.loads(marker.read_text())["policy"] == "strict-five-v2"


@pytest.mark.parametrize(
    ("message", "active", "blocked"),
    [
        (None, False, True),
        ("firecrawl-developer; firecrawl-search via serper", False, True),
        ("PROVISIONAL firecrawl-search via serper", False, True),
        ("PROVISIONAL firecrawl-developer; firecrawl-search", False, True),
        ("PROVISIONAL firecrawl-developer; firecrawl-search via serpapi", False, True),
        ("PROVISIONAL firecrawl-developer; firecrawl-search via serper", False, False),
        (None, True, False),
        ("RESEARCH INCOMPLETE: earlier failure", True, False),
    ],
    ids=[
        "null",
        "missing-marker",
        "missing-source",
        "missing-route",
        "wrong-route",
        "named",
        "continued-null",
        "earlier-incomplete",
    ],
)
def test_provisional_stop_names_each_source_and_route_once(
    tmp_path: Path, message: str | None, *, active: bool, blocked: bool
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    directory = tmp_path / ".codex/research-coverage/session-1/turn-1"
    path = _hook_manifest(directory)
    data = json.loads(path.read_text())
    row = next(r for r in data["sources"] if r["source"] == "firecrawl-search")
    envelope = (
        b'{"http_status":null,"rc":1,"body":"",'
        b'"stderr_redacted":"Insufficient credits"}'
    )
    primary = directory / "firecrawl-search.primary.raw"
    primary.write_bytes(envelope)
    raw = b'{"organic":[{"link":"https://primary.test"}]}'
    winning = directory / "firecrawl-search.serper.raw"
    winning.write_bytes(raw)
    Path(row["raw_file"]).write_bytes(raw)
    row.update(
        route="serper",
        provisional=True,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        attempts=[
            {
                "route": "firecrawl-search",
                "status": "skipped",
                "reason": "Insufficient credits",
                "raw_file": str(primary),
                "raw_sha256": hashlib.sha256(envelope).hexdigest(),
            },
            {
                "route": "serper",
                "status": "ok",
                "raw_file": str(winning),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
            },
        ],
    )
    path.write_text(json.dumps(data))
    result = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": message,
            "stop_hook_active": active,
        },
    )
    if blocked:
        assert result["decision"] == "block"
        assert "firecrawl-developer" in str(result["reason"])
        assert "firecrawl-search via serper" in str(result["reason"])
        assert "PROVISIONAL" in str(result["reason"])
        # Codex sets stop_hook_active after continuing, even if still unnamed.
        continued = _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "Stop",
                "last_assistant_message": message,
                "stop_hook_active": True,
            },
        )
        assert "decision" not in continued
    else:
        assert result == {}


def _projection_receipt(tmp_path: Path, prose: str) -> tuple[dict[str, object], Path]:
    """Create bound evidence for the real hook, including a skipped fallback."""
    base: dict[str, object] = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    directory = tmp_path / ".codex/research-coverage/session-1/turn-1"
    path = _hook_manifest(directory)
    data = json.loads(path.read_text())
    row = next(r for r in data["sources"] if r["source"] == "firecrawl-search")
    attempts = []
    for route, payload, status, reason in (
        (
            "firecrawl-search",
            {
                "http_status": None,
                "rc": 1,
                "body": "",
                "stderr_redacted": "Insufficient credits " + prose,
            },
            "skipped",
            "Insufficient credits " + prose,
        ),
        (
            "serper",
            {
                "http_status": 400,
                "rc": None,
                "body": json.dumps({"message": "Not enough credits " + prose}),
                "stderr_redacted": "",
            },
            "skipped",
            "Not enough credits " + prose,
        ),
        (
            "serpapi",
            {"organic_results": [{"link": "https://primary.test"}]},
            "ok",
            None,
        ),
    ):
        raw = json.dumps(payload).encode()
        label = "primary" if route == "firecrawl-search" else route
        evidence = directory / f"firecrawl-search.{label}.raw"
        evidence.write_bytes(raw)
        attempts.append(
            {
                "route": route,
                "status": status,
                "reason": reason,
                "raw_file": str(evidence),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    Path(row["raw_file"]).write_bytes(raw)
    row.update(
        route="serpapi",
        provisional=True,
        reason=prose,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        attempts=attempts,
    )
    path.write_text(json.dumps(data))
    return base, path


def test_projection_stop_exact_reason_and_prose_invariance(tmp_path: Path) -> None:
    """T1/T2: transport and manifest prose never change the continuation."""
    reasons = []
    for n in range(2):
        sentinel = "hook-diagnostic-" + uuid.uuid4().hex
        base, _ = _projection_receipt(tmp_path / str(n), sentinel)
        result = _invoke(tmp_path / str(n), {**base, "hook_event_name": "Stop"})
        assert result["decision"] == "block"
        assert result["reason"] == (
            "Research receipt PROVISIONAL (skipped or substituted provider). "
            "Name PROVISIONAL and each of "
            "these in the answer: firecrawl-developer; firecrawl-search via serpapi."
        )
        assert sentinel not in json.dumps(result)
        reasons.append(result["reason"])
    assert reasons[0] == reasons[1]


@pytest.mark.parametrize("invalid", ["route", "source"])
def test_projection_stop_invalid_identifiers(tmp_path: Path, invalid: str) -> None:
    """T4: route and non-metered source controls pin distinct fixed errors."""
    sentinel = "invalid-id-" + uuid.uuid4().hex
    base, path = _projection_receipt(tmp_path, sentinel)
    data = json.loads(path.read_text())
    if invalid == "route":
        row = next(r for r in data["sources"] if r["source"] == "firecrawl-search")
        row["route"] = "serper; " + sentinel
        expected = "firecrawl-search invalid fallback route"
    else:
        row = next(r for r in data["sources"] if r["source"] == "github-issues")
        raw = b'{"http_status":402,"rc":null,"body":"","stderr_redacted":""}'
        primary = path.parent / "github-issues.primary.raw"
        primary.write_bytes(raw)
        Path(row["raw_file"]).write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        row.update(
            status="skipped",
            items=[],
            provisional=True,
            skip_reason="credits-exhausted",
            raw_sha256=digest,
            attempts=[
                {
                    "route": "github-issues",
                    "status": "skipped",
                    "raw_file": str(primary),
                    "raw_sha256": digest,
                }
            ],
        )
        expected = "github-issues invalid provisional source"
    path.write_text(json.dumps(data))
    result = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert result["decision"] == "block"
    assert str(result["reason"]).startswith(f"Research coverage failed: {expected}.")
    assert sentinel not in json.dumps(result)


@pytest.mark.parametrize(
    ("message", "active", "blocked"),
    [
        ("PROVISIONAL exactly", False, True),
        ("PROVISIONAL exa", False, False),
        (None, False, True),
        (None, True, False),
        ("RESEARCH INCOMPLETE: earlier failure", True, False),
    ],
)
def test_projection_stop_exa_token_boundary(
    tmp_path: Path, message: str | None, *, active: bool, blocked: bool
) -> None:
    """T3/T5: exactly cannot acknowledge exa through a substring match."""
    base, path = _projection_receipt(tmp_path, "ordinary prose")
    data = json.loads(path.read_text())
    for row in data["sources"]:
        if row["source"] in {"firecrawl-search", "firecrawl-developer"}:
            row.update(
                provisional=False,
                route=None,
                status="ok",
                skip_reason=None,
                items=[{"url": "https://primary.test"}],
            )
            payload = (
                {"success": True, "data": {"web": [{"url": "https://primary.test"}]}}
                if row["source"] == "firecrawl-search"
                else {"success": True, "results": [{"url": "https://primary.test"}]}
            )
            raw = json.dumps(payload).encode()
            Path(row["raw_file"]).write_bytes(raw)
            row["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        if row["source"] == "exa":
            raw = b'{"http_status":402,"rc":null,"body":"","stderr_redacted":""}'
            primary = path.parent / "exa.primary.raw"
            primary.write_bytes(raw)
            Path(row["raw_file"]).write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            row.update(
                status="skipped",
                items=[],
                provisional=True,
                skip_reason="credits-exhausted",
                raw_sha256=digest,
                attempts=[
                    {
                        "route": "exa",
                        "status": "skipped",
                        "raw_file": str(primary),
                        "raw_sha256": digest,
                    }
                ],
            )
    path.write_text(json.dumps(data))
    result = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": message,
            "stop_hook_active": active,
        },
    )
    assert (result.get("decision") == "block") is blocked


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("non-object", "malformed"),
        ("malformed", "malformed"),
        ("invalid-utf8", "malformed"),
        ("unreadable", "unreadable"),
        ("missing", "missing"),
    ],
)
def test_unusable_research_record_passes_stop_with_a_notice(
    tmp_path: Path, change: str, reason: str
) -> None:
    """Security P3-2: an unbound research turn passes Stop, visibly."""
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": _RESEARCH,
        },
    )
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    marker.unlink()
    payloads = {
        "non-object": b"[]",
        "malformed": b"{SYNTHETIC_NONSECRET",
        "invalid-utf8": b"\xff",
    }
    if change == "unreadable":
        marker.mkdir()
    elif change in payloads:
        marker.write_bytes(payloads[change])
    for active, message in (
        (False, "Done."),
        (True, "Research complete"),
        (True, "RESEARCH INCOMPLETE: unavailable evidence"),
    ):
        result = _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": active,
                "last_assistant_message": message,
            },
        )
        assert result == {
            "systemMessage": f"{_NOTICE}research submission record {reason}."
        }
    if change in payloads:
        assert marker.read_bytes() == payloads[change]
    elif change == "unreadable":
        assert marker.is_dir()
    else:
        assert not marker.exists()


@pytest.mark.parametrize("raw", ["", "[]", "null", '{"hook_event_name":"Stop"'])
def test_unparsable_or_nonobject_input_cannot_earn_incomplete_escape(
    tmp_path: Path, raw: str
) -> None:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw,
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(tmp_path)},
        timeout=15,
        check=True,
    )
    assert json.loads(result.stdout)["decision"] == "block"


_FIXTURES = Path(__file__).parent / "fixtures" / "codex_research_gate"
_BRIEFS = (
    "json-ticket-brief.txt",
    "fenced-ticket-brief.txt",
    "blockquote-ticket-brief.txt",
    "acceptance-list-brief.txt",
    "text-edit-brief.txt",
)


def _turn(state_root: Path, prompt: str, **stop: object) -> dict[str, object]:
    """Submit one prompt and return the same turn's Stop response via handle()."""
    base: dict[str, object] = {"session_id": "session-1", "turn_id": "turn-1"}
    repo = Path(__file__).parent.parent
    submit = {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt}
    codex_research_gate.handle(submit, state_root, repo_root=repo)
    event = {**base, "hook_event_name": "Stop", "stop_hook_active": False, **stop}
    return codex_research_gate.handle(event, state_root, repo_root=repo)


@pytest.mark.parametrize("brief", _BRIEFS)
def test_implementation_brief_quoting_research_words_never_blocks_stop(
    tmp_path: Path, brief: str
) -> None:
    prompt = (_FIXTURES / brief).read_text(encoding="utf-8")
    assert _turn(tmp_path, prompt, last_assistant_message="Done.") == {}


@pytest.mark.parametrize(
    "prompt",
    [
        _DIRECTIVE + "Research the latest uv releases and compare them with poetry",
        _DIRECTIVE
        + (_FIXTURES / "research-with-quoted-bypass.txt").read_text(encoding="utf-8"),
        "[research-scope: research]\nImplement the bump after checking uv.",
    ],
)
def test_genuine_research_request_without_evidence_still_blocks(
    tmp_path: Path, prompt: str
) -> None:
    result = _turn(tmp_path, prompt, last_assistant_message="Done.")
    assert result["decision"] == "block"
    assert "strict-five research command" in str(result["reason"])


def test_script_entry_lets_quoted_ticket_brief_finish(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    prompt = (_FIXTURES / "json-ticket-brief.txt").read_text(encoding="utf-8")
    _invoke(tmp_path, {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt})
    stop = {**base, "hook_event_name": "Stop", "stop_hook_active": False}
    assert "decision" not in _invoke(tmp_path, {**stop, "last_assistant_message": ""})


def test_unwritable_state_warns_and_never_blocks_a_research_submission(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "research-coverage").write_text("not a directory")
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": _DIRECTIVE + "Research the latest uv releases",
    }
    submitted = _invoke(tmp_path, event)
    assert "decision" not in submitted
    assert "cannot enforce" in str(submitted["systemMessage"])
    assert "--strict-five" in json.dumps(submitted["hookSpecificOutput"])
    stopped = _invoke(tmp_path, {**event, "hook_event_name": "Stop"})
    assert "decision" not in stopped


_ENVELOPES: dict[str, dict[str, object]] = {
    "auth-failed": {"http_status": 401, "rc": None, "body": "", "stderr_redacted": ""},
    "quota": {
        "http_status": 429,
        "rc": None,
        "body": "rate limit",
        "stderr_redacted": "",
    },
    "unavailable": {"error_class": "ConnectionRefusedError", "errno": 61},
    "sandbox-denied": {"error_class": "PermissionError", "errno": 1},
    "credits-exhausted": {
        "http_status": 402,
        "rc": None,
        "body": "",
        "stderr_redacted": "",
    },
}


def _skip(manifest: Path, source: str, code: str, **override: object) -> None:
    """Rewrite one metered row as the producer writes a coded routeless skip."""
    data = json.loads(manifest.read_text())
    row = next(r for r in data["sources"] if r["source"] == source)
    for key in ("route", "control"):
        row.pop(key, None)
    if code == "credential-missing":
        row.update(
            status="skipped",
            items=[],
            skip_reason=code,
            provisional=True,
            reason="EXA_API_KEY not inherited; run through fnox exec",
            raw_file=None,
            raw_sha256=None,
            attempts=[],
        )
    else:
        raw = json.dumps(override.pop("envelope", _ENVELOPES[code])).encode()
        digest = hashlib.sha256(raw).hexdigest()
        primary = manifest.parent / f"{source}.primary.raw"
        primary.write_bytes(raw)
        (manifest.parent / f"{source}.raw").write_bytes(raw)
        row.update(
            status="skipped",
            items=[],
            skip_reason=code,
            provisional=True,
            reason=code,
            raw_file=str(manifest.parent / f"{source}.raw"),
            raw_sha256=digest,
            attempts=[
                {
                    "route": source,
                    "status": "skipped",
                    "http_status": None,
                    "reason": code,
                    "raw_file": str(primary),
                    "raw_sha256": digest,
                }
            ],
        )
    row.update(override)
    manifest.write_text(json.dumps(data))


_ALL_SKIPPED = {
    "exa": "credential-missing",
    "context7": "unavailable",
    "firecrawl-developer": "auth-failed",
    "firecrawl-search": "sandbox-denied",
}


@pytest.mark.parametrize(
    "codes",
    [
        {"exa": "credential-missing"},
        {"context7": "quota"},
        {"firecrawl-developer": "unavailable"},
        {"firecrawl-search": "sandbox-denied"},
        _ALL_SKIPPED,
    ],
    ids=["credential", "quota", "unavailable", "sandbox", "all-metered"],
)
def test_coded_skip_passes_provisional_once_answer_names_it(
    tmp_path: Path, codes: dict[str, str]
) -> None:
    """D236 / R-A F2: skipped providers never block once the answer names them."""
    prompt = _RESEARCH
    _turn(tmp_path, prompt)
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    for source, code in codes.items():
        _skip(manifest, source, code)
    names = sorted({*codes, "firecrawl-developer"})
    unnamed = _turn(tmp_path, prompt, last_assistant_message="Findings.")
    assert unnamed["decision"] == "block"
    for source in names:
        assert source in str(unnamed["reason"])
    continued = _turn(
        tmp_path, prompt, last_assistant_message="Findings.", stop_hook_active=True
    )
    assert "decision" not in continued
    named = _turn(
        tmp_path,
        prompt,
        last_assistant_message="PROVISIONAL: skipped " + "; ".join(names),
    )
    assert "decision" not in named


@pytest.mark.parametrize(
    ("source", "code", "override"),
    [
        (
            "exa",
            "auth-failed",
            {
                "envelope": {
                    "http_status": 500,
                    "rc": None,
                    "body": "",
                    "stderr_redacted": "",
                }
            },
        ),
        ("exa", "sandbox-denied", {"envelope": _ENVELOPES["unavailable"]}),
        (
            "context7",
            "unavailable",
            {"envelope": {"error_class": "ValueError", "errno": None}},
        ),
        ("exa", "credits-exhausted", {"items": [{"url": "https://fabricated.test"}]}),
        ("exa", "credential-missing", {"reason": "no key"}),
        ("context7", "credential-missing", {}),
        ("exa", "credential-missing", {"items": [{"url": "https://fabricated.test"}]}),
        ("exa", "prerequisite", {"envelope": _ENVELOPES["quota"]}),
        ("exa", "network-flake", {"envelope": _ENVELOPES["unavailable"]}),
    ],
    ids=[
        "relabelled-500",
        "relabelled-class",
        "unknown-class",
        "fabricated-items",
        "credential-text",
        "credential-source",
        "credential-items",
        "prerequisite",
        "unknown-code",
    ],
)
def test_coded_skip_without_rederivable_evidence_blocks(
    tmp_path: Path, source: str, code: str, override: dict[str, object]
) -> None:
    prompt = _RESEARCH
    _turn(tmp_path, prompt)
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    if code in {"prerequisite", "network-flake"}:
        _skip(manifest, source, "quota", **override)
        data = json.loads(manifest.read_text())
        next(r for r in data["sources"] if r["source"] == source)["skip_reason"] = code
        manifest.write_text(json.dumps(data))
    else:
        _skip(manifest, source, code, **override)
    named = f"PROVISIONAL {source}; firecrawl-developer"
    result = _turn(tmp_path, prompt, last_assistant_message=named)
    assert result["decision"] == "block"
    assert "Research coverage failed" in str(result["reason"])


@pytest.mark.parametrize("code", ["quota", "auth-failed", "unavailable"])
def test_bare_skip_row_without_evidence_blocks(tmp_path: Path, code: str) -> None:
    """Security P1-1: a self-asserted skip code with no evidence is no receipt."""
    prompt = _RESEARCH
    _turn(tmp_path, prompt)
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    data = json.loads(manifest.read_text())
    for row in data["sources"]:
        if row["source"] == "exa":
            row.clear()
            row.update(source="exa", status="skipped", skip_reason=code, items=[])
    manifest.write_text(json.dumps(data))
    named = "PROVISIONAL exa; firecrawl-developer"
    result = _turn(tmp_path, prompt, last_assistant_message=named)
    assert result["decision"] == "block"
    assert "Research coverage failed" in str(result["reason"])


@pytest.mark.parametrize("prefix", ["status", "status code", "Status:"])
def test_long_blank_stderr_evidence_cannot_stall_stop(
    tmp_path: Path, prefix: str
) -> None:
    """Security P3-4: forged stderr with long blank runs stays linear at Stop."""
    prompt = _RESEARCH
    _turn(tmp_path, prompt)
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    envelope = {
        "http_status": None,
        "rc": 1,
        "body": "",
        "stderr_redacted": (prefix + " " * 20_000 + "x ") * 3,
    }
    _skip(manifest, "context7", "quota", envelope=envelope)
    started = time.perf_counter()
    named = "PROVISIONAL context7; firecrawl-developer"
    result = _turn(tmp_path, prompt, last_assistant_message=named)
    assert time.perf_counter() - started < 0.5
    assert result["decision"] == "block"


# Round 3: only the exact first line `[research-scope: research]` binds research.
# Both round-2 reviewers' probe sets: work briefs that mention research words, and
# research lead-ins a verb classifier missed. Without the directive none blocks.
_WORK_PROMPTS = (
    "Investigate the failing test in tests/test_currency.py and fix it.",
    "Look into the flaky test_research_fanout case and make it deterministic.",
    "Find out which test fails on main and fix it.",
    (
        "Look up the definition of _turn_scope in codex_research_gate.py and add a "
        "docstring."
    ),
    "Fix the bug: investigate the manifest reader and correct its error code.",
    "Evaluate the agents config in .codex/agents and fix the model field.",
    "Recommend a fix for the mise task, then apply it.",
    "Rename the Best practices heading to Guidelines in docs/hooks.md.",
    "Update the README to say we follow best practices for hooks.",
    "Reword the README line that says: research the latest uv releases weekly.",
    "Implement CG-12. Ticket title: Research the latest versions of uv and poetry.",
    "title: Research the latest versions of uv",
    (
        "You are the reviewer. Read the diff; compare it with the ticket acceptance "
        "criteria and the AGENTS.md rules for agents."
    ),
    "Write tests that search the web fallback path in research_fanout.py.",
    (
        "Apply the review: P2 says to research the skip codes; implement it in "
        "research_fanout.py."
    ),
    (
        "Fix the flaky test.\n- Investigate the failing test in tests/test_x.py and "
        "patch it."
    ),
    "Fix the bug. First, investigate the stack trace in logs/err.txt.",
    "Please look into the CI failure on this branch and fix it.",
    "Find out which test fails, then fix the code.",
    "Look up the definition of parse_args in src/cli.py and rename it.",
    "Refactor the model class; recommend a name for the agent field.",
    "Apply our best practices doc to src/x.py.",
)
_RESEARCH_PROMPTS = (
    "Kindly research the latest uv releases.",
    "We should research the latest uv releases before pinning.",
    "Go research the newest Codex release.",
    "Let's research uv releases this week.",
    "Can someone investigate the newest mise release?",
    "Please do some research on the newest mise releases.",
    "Research: latest mise releases and their breaking changes.",
    "Research: uv vs poetry for this repo",
    "Do some research on the latest uv releases",
    "Check the latest uv release notes",
    "'tis urgent; research the latest uv releases, see the users' guide",
    'Mount note: the 27" monitor. Research the latest uv releases and "pin" them.',
)


def _marker(state_root: Path) -> Path:
    return state_root / "session-1" / "turn-1" / "required.json"


@pytest.mark.parametrize("prompt", _WORK_PROMPTS + _RESEARCH_PROMPTS)
def test_prompt_without_directive_never_blocks(tmp_path: Path, prompt: str) -> None:
    """R2 cold and security reviews: no keyword or verb binds a turn as research."""
    assert _turn(tmp_path, prompt, last_assistant_message="Done.") == {}
    assert not _marker(tmp_path).exists()


@pytest.mark.parametrize("prompt", _RESEARCH_PROMPTS)
def test_directive_research_blocks_then_passes_on_fallback_evidence(
    tmp_path: Path, prompt: str
) -> None:
    """With the directive, a missing receipt blocks; coded fallback skips pass."""
    prompt = _DIRECTIVE + prompt
    blocked = _turn(tmp_path, prompt, last_assistant_message="Done.")
    assert blocked["decision"] == "block"
    assert "strict-five research command" in str(blocked["reason"])
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    for source, code in _ALL_SKIPPED.items():
        _skip(manifest, source, code)
    answer = "PROVISIONAL: skipped " + "; ".join(sorted(_ALL_SKIPPED))
    assert _turn(tmp_path, prompt, last_assistant_message=answer) == {}


@pytest.mark.parametrize(
    "prompt",
    [
        "> [research-scope: research]\nResearch the latest uv releases.",
        "Ticket:\n[research-scope: research]\nResearch the latest uv releases.",
        "```\n[research-scope: research]\n```\nResearch the latest uv releases.",
        " [research-scope: research]\nResearch the latest uv releases.",
        "`[research-scope: research]`\nResearch the latest uv releases.",
    ],
    ids=["blockquote", "second-line", "fenced", "leading-space", "code-span"],
)
def test_quoted_or_misplaced_research_directive_never_binds(
    tmp_path: Path, prompt: str
) -> None:
    assert _turn(tmp_path, prompt, last_assistant_message="Done.") == {}
    assert not _marker(tmp_path).exists()


def test_crlf_research_directive_binds(tmp_path: Path) -> None:
    prompt = "[research-scope: research]\r\nFix the typo in README.md."
    assert _turn(tmp_path, prompt, last_assistant_message="Done.")["decision"] == (
        "block"
    )
    assert json.loads(_marker(tmp_path).read_text())["scope"] == "research"


def test_research_hint_without_directive_is_advisory_only(tmp_path: Path) -> None:
    submit: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Research the latest uv releases.",
    }
    repo = Path(__file__).parent.parent
    result = codex_research_gate.handle(submit, tmp_path, repo_root=repo)
    context = str(json.dumps(result))
    # r3 P3-4, security P3-6: a pointer only, never a provider command.
    for absent in ("--strict-five", "fnox", "codex_research", "research-fanout"):
        assert absent not in context
    assert "[research-scope: research]" in context
    assert "not research-enforced" in context
    assert "paid" in context
    assert len(context) < 600
    assert not _marker(tmp_path).exists()


@pytest.mark.parametrize("mode", ["implement", "review"])
@pytest.mark.parametrize("scope", [None, "strict-five", "implementation"])
def test_sdlc_implement_and_review_dispatch_never_binds_research(
    tmp_path: Path, mode: str, scope: str | None
) -> None:
    """r3 P1-1, D236: an SDLC coding or review lane is never a research turn."""
    fields: dict[str, object] = {
        "spec_file": str(tmp_path / "spec.md"),
        "task": "Implement ticket CG-36 test-first; keep research failures.",
        "mode": mode,
    }
    if scope is not None:
        fields["research_scope"] = scope
    request = codec.decode(json.dumps(fields).encode(), sdlc_team.SdlcTeamRequest)
    prompt = sdlc_team.build_prompt(request, tmp_path)
    assert prompt.partition("\n")[0] == "[research-scope: implementation]"
    assert _turn(tmp_path, prompt, last_assistant_message="Done.") == {}
    assert not _marker(tmp_path).exists()


@pytest.mark.parametrize("mode", ["implement", "review"])
def test_sdlc_explicit_research_scope_dispatch_binds_research(
    tmp_path: Path, mode: str
) -> None:
    request = codec.decode(
        json.dumps(
            {
                "spec_file": str(tmp_path / "spec.md"),
                "task": "Research the latest uv releases.",
                "mode": mode,
                "research_scope": "research",
            }
        ).encode(),
        sdlc_team.SdlcTeamRequest,
    )
    prompt = sdlc_team.build_prompt(request, tmp_path)
    assert prompt.partition("\n")[0] == "[research-scope: research]"
    assert _turn(tmp_path, prompt, last_assistant_message="Done.")["decision"] == (
        "block"
    )


_ACCEPTED_FORMS = tuple(
    f"`[research-scope: {scope}]`"
    for scope in ("research", "implementation", "text-edit", "local-only")
)


@pytest.mark.parametrize(
    "first",
    [
        " [research-scope: research]",
        "\ufeff[research-scope: research]",
        "\u00a0[research-scope: research]",
        "[Research-Scope: research]",
        "\uff3bresearch-scope: research\uff3d",
        "[research-scope: research] now",
        "[research-scope: researc]",
        "[research-scope:research]",
        "[research-scope: research]\rFix it.",
        "[research-scope: research]\u2028Fix it.",
    ],
    ids=[
        "leading-space",
        "bom",
        "nbsp",
        "capitalized",
        "fullwidth",
        "trailing-text",
        "typo",
        "no-space",
        "lone-cr",
        "line-separator",
    ],
)
def test_near_miss_directive_warns_and_binds_nothing(
    tmp_path: Path, first: str
) -> None:
    """Security P3-3: a mistyped directive is visible to the caller."""
    submit: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": first + "\nFix the README typo.",
    }
    repo = Path(__file__).parent.parent
    result = codex_research_gate.handle(submit, tmp_path, repo_root=repo)
    assert "decision" not in result
    message = str(result["systemMessage"])
    assert "not enforced" in message
    for form in _ACCEPTED_FORMS:
        assert form in message
    assert not _marker(tmp_path).exists()


@pytest.mark.parametrize(
    "prompt",
    [
        "Ticket:\n[research-scope: research]\nFix it.",
        "Fix the research-scope note in the README.",
        "[research] notes on the README",
        "[research-scope: implementation]\nFix it.",
    ],
)
def test_exact_or_absent_directive_gets_no_near_miss_notice(
    tmp_path: Path, prompt: str
) -> None:
    submit: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    repo = Path(__file__).parent.parent
    result = codex_research_gate.handle(submit, tmp_path, repo_root=repo)
    assert "systemMessage" not in result


@pytest.mark.parametrize(
    "filler",
    [
        *("\n", " ", "\t.", "`", '"', "'", "> ", "```\n", "a ", "\r\n"),
        *("\u201c", "\u201e", "\u201cab ", "\u201e\u201c' "),
    ],
)
def test_research_hint_is_linear_on_long_prompts(tmp_path: Path, filler: str) -> None:
    """Security P2-2: the hint scan stays linear; 32000 repeats stay under 0.5 s."""
    submit: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": filler * 32000 + "Research the latest uv releases.",
    }
    repo = Path(__file__).parent.parent
    started = time.perf_counter()
    result = codex_research_gate.handle(submit, tmp_path, repo_root=repo)
    elapsed = time.perf_counter() - started
    assert "not research-enforced" in json.dumps(result)
    assert not _marker(tmp_path).exists()
    assert elapsed < 0.5


def test_leftover_turn_directory_without_marker_never_blocks(tmp_path: Path) -> None:
    """Decision 7, security P3-2: no retained submission passes, with a notice."""
    directory = tmp_path / "session-1" / "turn-1"
    directory.mkdir(parents=True)
    _hook_manifest(directory)
    stop: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "last_assistant_message": "Done.",
    }
    repo = Path(__file__).parent.parent
    result = codex_research_gate.handle(stop, tmp_path, repo_root=repo)
    assert result == {"systemMessage": _NOTICE + "research submission record missing."}


@pytest.mark.parametrize(
    "agent", [{"agent_id": "agent-1"}, {"agent_type": "worker"}, {"subagent": "x"}]
)
def test_subagent_turn_is_exempt(tmp_path: Path, agent: dict[str, str]) -> None:
    """codex-rs/hooks/src/schema.rs:567-583 (rust-v0.163.0): agent_id, agent_type."""
    base: dict[str, object] = {"session_id": "session-1", "turn_id": "turn-1", **agent}
    repo = Path(__file__).parent.parent
    submit = {**base, "hook_event_name": "UserPromptSubmit", "prompt": _RESEARCH}
    assert codex_research_gate.handle(submit, tmp_path, repo_root=repo) == {}
    assert not (tmp_path / "session-1").exists()
    stop = {**base, "hook_event_name": "Stop", "last_assistant_message": "Done."}
    assert codex_research_gate.handle(stop, tmp_path, repo_root=repo) == {}
