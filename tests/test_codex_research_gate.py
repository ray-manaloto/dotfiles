# Copyright (c) 2026 Raymond Manaloto
"""Public hook-wire controls for the Codex research coverage gate."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, codex_research_gate, sdlc_team

HOOK = Path(__file__).parent.parent / "scripts" / "codex-research-gate.py"


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (b"{", "Research submission marker malformed."),
        (b"[]", "Research submission marker malformed."),
        (b"\xff", "Research submission marker malformed."),
        (b"{}", "Research submission digest invalid."),
        (b'{"prompt_sha256":null}', "Research submission digest invalid."),
        (
            b'{"prompt_sha256":"SYNTHETIC_BAD_DIGEST"}',
            "Research submission digest invalid.",
        ),
        (b'{"caller_scope":{}}', "Research submission digest invalid."),
        (None, "Research submission marker unreadable."),
    ],
)
def test_repeated_submit_reports_retained_evidence_failure_without_rewriting(
    tmp_path: Path,
    raw: bytes | None,
    reason: str,
) -> None:
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Research Codex hooks",
    }
    _invoke(tmp_path, event)
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    if raw is None:
        marker.unlink()
        marker.mkdir()
    else:
        marker.write_bytes(raw)
    assert _invoke(tmp_path, event) == {"decision": "block", "reason": reason}
    if raw is None:
        assert marker.is_dir()
    else:
        assert marker.read_bytes() == raw


@pytest.mark.parametrize("local", [False, True])
def test_valid_repeated_submit_distinguishes_same_and_different_prompts(
    tmp_path: Path,
    *,
    local: bool,
) -> None:
    prompt = (
        "[research-scope: local-only]\n" if local else ""
    ) + "Research Codex hooks"
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    _invoke(tmp_path, event)
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    original = marker.read_bytes()
    assert _invoke(tmp_path, event) == {}
    assert _invoke(tmp_path, {**event, "prompt": prompt + " again"}) == {
        "decision": "block",
        "reason": "Research scope already bound to a different submission.",
    }
    assert marker.read_bytes() == original


@pytest.mark.parametrize(
    "manifest_raw", [None, b'{"SYNTHETIC_PRIVATE_REASON":"unfinished"}']
)
@pytest.mark.parametrize(
    "message", ["Local edit completed.", "RESEARCH INCOMPLETE: prior coverage."]
)
def test_local_stop_states_authorization_without_inventing_research_requirement(
    tmp_path: Path,
    manifest_raw: bytes | None,
    message: str,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: local-only]\nUpdate a local document.",
        },
    )
    manifest = tmp_path / ".codex/research-coverage/session-1/turn-1/manifest.json"
    if manifest_raw is not None:
        manifest.write_bytes(manifest_raw)
    assert _invoke(
        tmp_path, {**base, "hook_event_name": "Stop", "last_assistant_message": message}
    ) == {
        "systemMessage": (
            "Caller authorized local work without a new provider run. "
            "This does not certify existing research. Retain any existing "
            "INCOMPLETE status. Provider calls remain outside that authorization."
        )
    }
    if manifest_raw is not None:
        assert manifest.read_bytes() == manifest_raw


@pytest.mark.parametrize("scope", ["local-only", "strict-five"])
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
    if scope == "local-only":
        assert "--strict-five" not in json.dumps(started)
        assert stopped.get("decision") != "block"
        assert "incomplete" in str(stopped["systemMessage"]).lower()
    else:
        assert "--strict-five" in json.dumps(started)
        assert stopped["decision"] == "block"


def test_caller_local_scope_finishes_on_first_stop_with_retained_incomplete(
    tmp_path: Path,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    started = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": (
                "[research-scope: local-only]\n"
                "Investigate the saved Codex research receipt locally. "
                "Do not launch providers."
            ),
        },
    )
    assert "research-fanout" not in json.dumps(started)
    directory = tmp_path / ".codex/research-coverage/session-1/turn-1"
    manifest = directory / "manifest.json"
    retained = b'{"strict_five":true,"request_id":"turn-1","sources":[]}'
    manifest.write_bytes(retained)
    result = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": "RESEARCH INCOMPLETE: Context7 monthly quota.",
        },
    )
    assert result.get("decision") != "block"
    assert "incomplete" in str(result.get("systemMessage", "")).lower()
    assert manifest.read_bytes() == retained


def test_same_turn_cannot_be_redeclared_local_after_research_submission(
    tmp_path: Path,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Research Codex hooks",
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
        "Research Codex hooks",
        "> [research-scope: local-only]\nResearch Codex hooks",
        "Quoted directive:\n[research-scope: local-only]\nResearch Codex hooks",
        "```\n[research-scope: local-only]\n```\nResearch Codex hooks",
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


@pytest.mark.parametrize(
    "change",
    [
        "stale-turn",
        "wrong-session",
        "changed-digest",
        "missing-marker",
        "malformed-marker",
    ],
)
def test_local_scope_requires_retained_matching_submission_evidence(
    tmp_path: Path,
    change: str,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: local-only]\nInvestigate local Codex research",
        },
    )
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    data = json.loads(marker.read_text())
    if change == "missing-marker":
        marker.unlink()
    elif change == "malformed-marker":
        marker.write_text("[]")
    else:
        field, value = {
            "stale-turn": ("turn_id", "turn-previous"),
            "wrong-session": ("session_id", "session-other"),
            "changed-digest": ("prompt_sha256", "0" * 64),
        }[change]
        data["caller_scope"][field] = value
        marker.write_text(json.dumps(data))
    result = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "last_assistant_message": "RESEARCH INCOMPLETE: local scope",
        },
    )
    assert result["decision"] == "block"


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
            "prompt": "Research Codex hooks",
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
        ("Compare uv and Poetry for Python dependency management.", "gated"),
        ("Find the latest fnox version.", "gated"),
        ("Research Codex agent workflows.", "gated"),
        ("Print the current directory.", "ordinary"),
        ("Rename the variable sources to inputs.", "ordinary"),
        ("Compare these two local functions.", "ordinary"),
    ],
)
def test_research_trigger_matches_external_requests(
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
            "prompt": "Research Codex hooks",
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
            "prompt": "Research Codex hooks",
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
            "prompt": "Research Codex hooks",
        },
        script,
    )
    specific = result["hookSpecificOutput"]
    assert isinstance(specific, dict)
    context = specific["additionalContext"]
    assert isinstance(context, str)
    assert len(context) <= 1000
    assert f"mise -C {root} run research-fanout" in context
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
            "prompt": "Research Codex hooks",
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
            "prompt": "Research Codex hooks",
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
            "Research receipt PROVISIONAL (credit-exhausted provider). "
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
        ("missing", "Research submission marker missing."),
        ("non-object", "Research submission marker malformed."),
        ("malformed", "Research submission marker malformed."),
        ("invalid-utf8", "Research submission marker malformed."),
        ("unreadable", "Research submission marker unreadable."),
        ("binding", "Caller research scope binding invalid."),
    ],
)
def test_invalid_submission_requires_first_refusal_then_honest_incomplete_stop(
    tmp_path: Path, change: str, reason: str
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Research Codex hooks",
        },
    )
    marker = tmp_path / ".codex/research-coverage/session-1/turn-1/required.json"
    marker.unlink()
    payloads = {
        "non-object": b"[]",
        "malformed": b"{SYNTHETIC_NONSECRET",
        "invalid-utf8": b"\xff",
        "binding": b'{"caller_scope":{"scope":"local-only"}}',
    }
    if change == "unreadable":
        marker.mkdir()
    elif change in payloads:
        marker.write_bytes(payloads[change])
    for active, message in (
        (False, "RESEARCH INCOMPLETE: unavailable evidence"),
        (True, "Research complete"),
        (True, "Summary: RESEARCH INCOMPLETE: unavailable evidence"),
    ):
        blocked = _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": active,
                "last_assistant_message": message,
            },
        )
        assert blocked == {"decision": "block", "reason": reason}
    completed = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "last_assistant_message": " \nRESEARCH INCOMPLETE: unavailable evidence",
        },
    )
    assert completed == {
        "systemMessage": f"Research coverage remains incomplete: {reason}"
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


@pytest.mark.parametrize("scope", ["implementation", "text-edit"])
def test_caller_implementation_directive_never_blocks_stop(
    tmp_path: Path, scope: str
) -> None:
    prompt = f"[research-scope: {scope}]\nResearch the latest uv releases."
    assert _turn(tmp_path, prompt, last_assistant_message="Done.") == {}


@pytest.mark.parametrize(
    "prompt",
    [
        "Research the latest uv releases and compare them with poetry",
        (_FIXTURES / "research-with-quoted-bypass.txt").read_text(encoding="utf-8"),
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


def test_unwritable_state_does_not_block_an_unbound_submission(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "research-coverage").write_text("not a directory")
    event: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Research the latest uv releases",
    }
    submitted = _invoke(tmp_path, event)
    assert "decision" not in submitted
    assert "not bound" in str(submitted["systemMessage"])
    stopped = _invoke(tmp_path, {**event, "hook_event_name": "Stop"})
    assert "decision" not in stopped


def _degrade(manifest: Path, codes: dict[str, str]) -> None:
    """Mark metered sources skipped before any call, with no transport evidence."""
    data = json.loads(manifest.read_text())
    for row in data["sources"]:
        if row["source"] in codes:
            for key in ("provisional", "attempts"):
                row.pop(key, None)
            row.update(
                status="skipped",
                items=[],
                skip_reason=codes[row["source"]],
                raw_file=None,
                raw_sha256=None,
            )
    manifest.write_text(json.dumps(data))


@pytest.mark.parametrize(
    "code",
    ["quota", "credential-missing", "auth-failed", "unavailable", "sandbox-denied"],
)
def test_preflight_skip_with_fallback_evidence_passes_provisional(
    tmp_path: Path, code: str
) -> None:
    prompt = "Research Codex hooks"
    _turn(tmp_path, prompt)
    manifest = _hook_manifest(tmp_path / "session-1" / "turn-1")
    _degrade(
        manifest,
        {"exa": code, "context7": "quota", "firecrawl-developer": "sandbox-denied"},
    )
    result = _turn(tmp_path, prompt, last_assistant_message="Findings.")
    assert "decision" not in result
    assert "PROVISIONAL" in str(result["systemMessage"])
    assert f"exa skipped: {code}" in str(result["systemMessage"])


@pytest.mark.parametrize(
    "codes",
    [
        {
            "exa": "credential-missing",
            "context7": "quota",
            "firecrawl-developer": "sandbox-denied",
            "firecrawl-search": "unavailable",
        },
        {"exa": "network-flake"},
        {"github-issues": "credential-missing"},
    ],
)
def test_preflight_skip_without_fallback_evidence_blocks(
    tmp_path: Path, codes: dict[str, str]
) -> None:
    prompt = "Research Codex hooks"
    _turn(tmp_path, prompt)
    _degrade(_hook_manifest(tmp_path / "session-1" / "turn-1"), codes)
    result = _turn(tmp_path, prompt, last_assistant_message="Findings.")
    assert result["decision"] == "block"
    assert "Research coverage failed" in str(result["reason"])
