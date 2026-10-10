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

HOOK = Path(__file__).parent.parent / "scripts" / "codex-research-gate.py"


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
