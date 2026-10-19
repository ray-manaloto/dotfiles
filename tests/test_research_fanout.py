# Copyright (c) 2026 Raymond Manaloto
"""Tests for the no-LLM multi-source research fetcher."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import signal
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_research_gate
from dotfiles_setup.generated.research_skip_reason import SkipReason
from dotfiles_setup.research_fanout import (
    Endpoint,
    FanoutRequest,
    Http,
    ProbeTiming,
    Status,
    default_http,
    default_runner,
    failure_code,
    fan_out,
    is_credit_exhaustion,
    main,
    strict_five_verdict,
    validate_strict_five,
)
from dotfiles_setup.saved_searches import main as record_saved_searches


def _strict_manifest(tmp_path: Path) -> Path:
    sources = (
        "github-issues",
        "github-discussions",
        "github-releases",
        "exa",
        "context7",
        "firecrawl-developer",
        "firecrawl-search",
        "last30days",
    )
    rows = []
    for source in sources:
        raw = tmp_path / f"{source}.raw"
        payload: object = {
            "github-issues": {"items": [{"html_url": "https://example.test"}]},
            "github-discussions": {
                "data": {"search": {"nodes": [{"url": "https://example.test"}]}}
            },
            "github-releases": [{"html_url": "https://example.test"}],
            "exa": {
                "requestId": "test-request",
                "results": [{"url": "https://example.test"}],
            },
            "firecrawl-developer": {
                "success": True,
                "results": [{"url": "https://example.test"}],
            },
            "firecrawl-search": {
                "success": True,
                "data": {"web": [{"url": "https://example.test"}]},
            },
            "last30days": {"schema_version": "1.3", "source_status": {"reddit": "ok"}},
        }.get(source, "Context7 result")
        raw_bytes = (
            json.dumps(payload).encode() if source != "context7" else b"Context7 result"
        )
        raw.write_bytes(raw_bytes)
        rows.append(
            {
                "source": source,
                "status": "ok",
                "items": [{"url": "https://example.test"}],
                "control": None,
                "raw_file": str(raw),
                "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "strict_five": True,
                "policy_version": "strict-five-v2",
                "request_id": "turn-1",
                "query": "Codex hooks",
                "repo": "openai/codex",
                "sources": rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_strict_five_requires_every_source_and_bound_raw_evidence(
    tmp_path: Path,
) -> None:
    path = _strict_manifest(tmp_path)
    assert validate_strict_five(path, "turn-1") == (
        True,
        "all required sources completed",
    )
    assert validate_strict_five(path, "turn-2")[0] is False
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows["sources"][0]["status"] = "skipped"
    path.write_text(json.dumps(rows), encoding="utf-8")
    assert validate_strict_five(path, "turn-1")[0] is False
    rows["sources"][0]["status"] = "ok"
    path.write_text(json.dumps(rows), encoding="utf-8")
    (tmp_path / "exa.raw").write_text("altered", encoding="utf-8")
    assert validate_strict_five(path, "turn-1")[0] is False


def test_strict_five_rejects_missing_hash_bad_response_and_empty_control(
    tmp_path: Path,
) -> None:
    path = _strict_manifest(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    exa = next(row for row in manifest["sources"] if row["source"] == "exa")
    exa.pop("raw_sha256")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_strict_five(path, "turn-1")[0] is False
    assert "raw_sha256" not in json.loads(path.read_text())["sources"][3]

    raw = tmp_path / "exa.raw"
    raw.write_bytes(b"HTTP 401 Unauthorized")
    exa["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_strict_five(path, "turn-1")[0] is False

    raw.write_text('{"requestId":"test-request","results":[]}', encoding="utf-8")
    exa["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    releases = next(
        row for row in manifest["sources"] if row["source"] == "github-releases"
    )
    releases["status"] = "empty_verified"
    releases["items"] = []
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_strict_five(path, "turn-1") == (
        False,
        "github-releases empty result lacks a positive control",
    )


def test_strict_five_rejects_non_object_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")
    assert validate_strict_five(path, "turn-1") == (
        False,
        "malformed research manifest",
    )


def test_strict_five_rejects_degraded_last30days(tmp_path: Path) -> None:
    path = _strict_manifest(tmp_path)
    raw = tmp_path / "last30days.raw"
    raw.write_text(
        json.dumps({"schema_version": "1.3", "source_status": {"reddit": "error"}}),
        encoding="utf-8",
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    last30days = next(
        row for row in manifest["sources"] if row["source"] == "last30days"
    )
    last30days["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_strict_five(path, "turn-1") == (
        False,
        "last30days schema or internal source failure",
    )


def test_strict_five_rejects_malformed_discussions_search(tmp_path: Path) -> None:
    path = _strict_manifest(tmp_path)
    raw = tmp_path / "github-discussions.raw"
    raw.write_text('{"data":{}}', encoding="utf-8")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    discussions = next(
        row for row in manifest["sources"] if row["source"] == "github-discussions"
    )
    discussions["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_strict_five(path, "turn-1") == (
        False,
        "github-discussions raw evidence is not a successful response",
    )


def _completed(
    argv: list[str], rc: int, stdout: bytes = b"", stderr: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=stderr)


def _unused_runner(
    argv: list[str], *, timeout: float, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    del timeout, env
    message = f"unexpected subprocess call: {argv}"
    raise AssertionError(message)


@dataclass
class FakeHttp:
    """HTTP boundary double keyed by the submitted query."""

    responses: dict[str, tuple[int, bytes]]
    calls: list[tuple[Endpoint, dict[str, Any], dict[str, str], float]] = field(
        default_factory=list
    )

    def __call__(
        self,
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        """Record the request and return its query-keyed response."""
        payload = body if body is not None else params
        assert payload is not None
        query = str(payload.get("query", payload.get("q")))
        self.calls.append((endpoint, payload, headers, timeout))
        return self.responses[query]


@dataclass
class ScriptedRunner:
    """Subprocess boundary double returning responses in call order."""

    responses: list[subprocess.CompletedProcess[bytes]]
    calls: list[tuple[list[str], float, dict[str, str]]] = field(default_factory=list)

    def __call__(
        self, argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        """Record the spawn and return the next scripted completion."""
        self.calls.append((argv, timeout, env))
        assert self.responses, f"unexpected subprocess call: {argv}"
        return self.responses.pop(0)


@dataclass
class ChunkedResponse:
    """Minimal urllib response double that yields one chunk per read."""

    chunks: list[bytes]
    delay: float = 0.0
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    def __enter__(self) -> Self:
        """Return this response for the context-manager protocol."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Leave the response without suppressing exceptions."""

    def read(self, amount: int = -1) -> bytes:
        """Accumulate scripted chunks like a buffered HTTP response."""
        body = bytearray()
        while self.chunks and (amount < 0 or len(body) < amount):
            if self.delay:
                time.sleep(self.delay)
            chunk = self.chunks.pop(0)
            remaining = amount - len(body) if amount >= 0 else len(chunk)
            body.extend(chunk[:remaining])
            if len(chunk) > remaining:
                self.chunks.insert(0, chunk[remaining:])
        return bytes(body)

    def close(self) -> None:
        """Close the in-memory response."""


@contextmanager
def _local_http_body(
    body: bytes, *, declared_length: int | None = None, delay: float = 0.0
) -> Iterator[str]:
    """Serve one response over a real loopback socket."""

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            self.request.recv(4096)
            length = len(body) if declared_length is None else declared_length
            headers = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {length}\r\n"
                "Connection: close\r\n\r\n"
            ).encode()
            try:
                self.request.sendall(headers)
                for byte in body:
                    self.request.sendall(bytes((byte,)))
                    if delay:
                        time.sleep(delay)
            except OSError:
                return

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", 0), Handler) as server:
        host = server.server_address[0]
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://{host}:{port}/"
        finally:
            server.shutdown()
            thread.join(timeout=1.0)


def _install_path_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *names: str
) -> None:
    for name in names:
        tool = tmp_path / name
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))


@pytest.mark.parametrize(
    ("canary_results", "expected"),
    [
        # Fail arm: a zero-result canary cannot verify the primary empty result.
        (
            [{"title": "Python", "url": "https://example.test/python"}],
            Status.EMPTY_VERIFIED,
        ),
        ([], Status.EMPTY_UNVERIFIED),
    ],
)
def test_exa_empty_result_uses_control_arm(
    monkeypatch: pytest.MonkeyPatch,
    canary_results: list[dict[str, str]],
    expected: Status,
) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    http = FakeHttp(
        {
            "missing topic": (200, b'{"results": []}'),
            "python": (200, json.dumps({"results": canary_results}).encode()),
        }
    )

    [result] = fan_out(
        FanoutRequest("missing topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=http,
    )

    assert result.status is expected
    assert result.control is not None
    assert result.control.query == "python"
    assert result.control.count == len(canary_results)
    assert result.status is not Status.OK


@pytest.mark.parametrize(
    ("response", "expected_reason"),
    [
        # Fail arm: transport and parse failures are errors, never empty answers.
        ((503, b'{"results": []}'), "HTTP 503"),
        ((200, b"not-json"), "invalid JSON"),
    ],
)
def test_exa_failures_are_errors(
    monkeypatch: pytest.MonkeyPatch,
    response: tuple[int, bytes],
    expected_reason: str,
) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    http = FakeHttp({"topic": response})

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=http,
    )

    assert result.status is Status.ERROR
    assert result.reason == expected_reason
    assert result.control is None


def test_http_timeout_is_unavailable_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """D236: a metered provider that times out is skipped `unavailable`."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")

    def timeout_http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, body, headers, timeout
        raise TimeoutError

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=timeout_http,
    )

    assert (result.status, result.skip_reason) == (Status.SKIPPED, "unavailable")
    assert result.reason == "timed out"


def test_wrapped_socket_timeout_reports_timed_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: classifying all OSError instances alike says request failed."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")

    def timeout_http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, body, headers, timeout
        raise urllib.error.URLError(TimeoutError())

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=timeout_http,
    )

    assert (result.status, result.skip_reason) == (Status.SKIPPED, "unavailable")
    assert result.reason == "timed out"


def test_transport_failure_isolated_and_manifest_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: an uncaught HTTPException discards every concurrent result."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")

    def incomplete_exa(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del params, body, headers, timeout
        if endpoint is Endpoint.EXA_SEARCH:
            partial = b"partial"
            raise http.client.IncompleteRead(partial, 20)
        return 200, b'{"results":[{"title":"ok","url":"https://ok.test"}]}'

    out = tmp_path / "out"
    rc = main(
        [
            "topic",
            "--sources",
            "exa,firecrawl-developer",
            "--out",
            str(out),
        ],
        tmp_path,
        runner=_unused_runner,
        http=incomplete_exa,
    )
    manifest = json.loads((out / "manifest.json").read_text())

    assert rc == 0
    assert [(row["source"], row["status"]) for row in manifest["sources"]] == [
        ("exa", "error"),
        ("firecrawl-developer", "ok"),
    ]
    assert (out / "exa.json").is_file()
    assert (out / "firecrawl-developer.json").is_file()


@pytest.mark.parametrize(
    "failure",
    [http.client.BadStatusLine("bad status"), ValueError("bad transport")],
)
def test_canary_transport_failure_does_not_escape(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    """FAIL arm: primary-only exception handling lets a broken canary abort."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    calls = 0

    def failing_canary(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        del endpoint, params, body, headers, timeout
        calls += 1
        if calls == 1:
            return 200, b'{"results":[]}'
        raise failure

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=failing_canary,
    )

    assert result.status is Status.EMPTY_UNVERIFIED
    assert result.reason == "canary failed"
    assert result.control is not None
    assert result.control.count is None


@pytest.mark.parametrize("source", ["exa", "firecrawl-developer"])
def test_default_http_deadline_covers_real_streaming_body(
    monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """FAIL arm: a per-read timeout accepts a real slow trickle indefinitely."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    original_urlopen = urllib.request.urlopen
    body = b'{"results":[{"title":"slow","url":"https://slow.test"}]}'
    with _local_http_body(body, delay=0.03) as url:

        def local_urlopen(_request: object, *, timeout: float) -> object:
            return original_urlopen(url, timeout=timeout)

        monkeypatch.setattr(urllib.request, "urlopen", local_urlopen)
        started = time.monotonic()
        [result] = fan_out(
            FanoutRequest("topic", None, (source,), 10, 0.15),
            runner=_unused_runner,
            http=default_http,
        )
        elapsed = time.monotonic() - started

    assert (result.status, result.skip_reason) == (Status.SKIPPED, "unavailable")
    assert result.reason == "timed out"
    assert elapsed <= 1.15


def test_default_http_rejects_short_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: decoding a short body misreports transport truncation as JSON."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    original_urlopen = urllib.request.urlopen
    body = b'{"results":[]}'
    with _local_http_body(body, declared_length=len(body) + 10) as url:

        def local_urlopen(_request: object, *, timeout: float) -> object:
            return original_urlopen(url, timeout=timeout)

        monkeypatch.setattr(urllib.request, "urlopen", local_urlopen)
        [result] = fan_out(
            FanoutRequest("topic", None, ("exa",), 10, 1.0),
            runner=_unused_runner,
            http=default_http,
        )

    assert result.status is Status.ERROR
    assert result.reason == "incomplete response"


def test_default_http_rejects_response_over_eight_mib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: removing the byte cap accepts an unbounded response body."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    chunk = b"x" * (64 * 1024)
    response = ChunkedResponse([chunk] * 129)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: response)

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=default_http,
    )

    assert result.status is Status.ERROR
    assert result.reason == "response too large"


def test_canary_timeout_leaves_empty_result_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    calls = 0

    def primary_then_timeout(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        del endpoint, params, body, headers, timeout
        calls += 1
        if calls == 1:
            return 200, b'{"results": []}'
        raise TimeoutError

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 5.0),
        runner=_unused_runner,
        http=primary_then_timeout,
    )

    assert result.status is Status.EMPTY_UNVERIFIED
    assert result.control is not None
    assert result.control.count is None
    assert result.reason == "canary failed"


def test_primary_and_canary_share_one_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: giving the canary a fresh deadline makes both timeouts equal."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    timeouts: list[float] = []

    def delayed_primary(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, headers
        timeouts.append(timeout)
        assert body is not None
        if body["query"] == "topic":
            time.sleep(0.04)
            return 200, b'{"results":[]}'
        return 200, b'{"results":[{"title":"ok","url":"https://ok.test"}]}'

    [result] = fan_out(
        FanoutRequest("topic", None, ("exa",), 10, 1.0),
        runner=_unused_runner,
        http=delayed_primary,
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert len(timeouts) == 2
    assert timeouts[1] < timeouts[0] - 0.03


def test_nonzero_subprocess_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_path_tools(tmp_path, monkeypatch, "firecrawl")
    credential = "diagnostic-secret"
    monkeypatch.setenv("FIRECRAWL_API_KEY", credential)
    runner = ScriptedRunner(
        [
            _completed(
                ["firecrawl"],
                7,
                stderr=(b"x" * 320) + credential.encode() + b" final detail",
            )
        ]
    )

    [result] = fan_out(
        FanoutRequest("topic", None, ("firecrawl-search",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.ERROR
    assert result.reason is not None
    assert result.reason.startswith("exited 7: ")
    assert result.reason.endswith("[REDACTED] final detail")
    assert credential not in result.reason
    assert len(result.reason.removeprefix("exited 7: ")) == 300
    assert result.status not in {Status.EMPTY_VERIFIED, Status.EMPTY_UNVERIFIED}


def test_multiline_stderr_keeps_summary_to_one_line_per_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FAIL arm: preserving stderr newlines splits one source across lines."""
    _install_path_tools(tmp_path, monkeypatch, "firecrawl")
    runner = ScriptedRunner(
        [_completed(["firecrawl"], 7, stderr=b"first line\nsecond line\nthird")]
    )

    rc = main(
        [
            "topic",
            "--sources",
            "firecrawl-search",
            "--out",
            str(tmp_path / "out"),
        ],
        tmp_path,
        runner=runner,
        http=FakeHttp({}),
    )
    lines = capsys.readouterr().out.splitlines()

    assert rc == 1
    assert len(lines) == 2
    assert "[process-failed]" in lines[1]


def test_default_runner_neutralises_color_forcing_in_real_child() -> None:
    """FAIL arm: env=env leaks all forcing names and omits NO_COLOR."""
    script = (
        "import os; "
        "print(' '.join(name for name in "
        "('FORCE_COLOR', 'CLICOLOR_FORCE', 'GH_FORCE_TTY', 'PYTHON_COLORS') "
        "if name in os.environ)); "
        "print(os.environ.get('NO_COLOR', '<absent>'))"
    )

    result = default_runner(
        [sys.executable, "-c", script],
        timeout=5.0,
        env={
            "FORCE_COLOR": "3",
            "CLICOLOR_FORCE": "1",
            "GH_FORCE_TTY": "1",
            "PYTHON_COLORS": "1",
            "PATH": os.environ["PATH"],
        },
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [b"", b"1"]


def test_default_runner_bounds_drain_when_detached_descendant_holds_pipe(
    tmp_path: Path,
) -> None:
    """FAIL arm: an unbounded final communicate waits for the detached child."""
    pid_file = tmp_path / "detached.pid"
    descendant = "import time; time.sleep(30)"
    parent = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', sys.argv[2]], "
        "stdout=sys.stdout, stderr=sys.stderr, start_new_session=True); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
        "time.sleep(30)"
    )
    detached_pid: int | None = None
    # The parent must start, spawn and record the child BEFORE the timeout
    # fires; 0.2s lost that race 3 of 6 times in the amd64 devcontainer
    # (Python starts slower there), so the timeout, not the bound, was flaky.
    timeout = 2.0
    started = time.monotonic()
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            default_runner(
                [sys.executable, "-c", parent, str(pid_file), descendant],
                timeout=timeout,
                env={},
            )
        elapsed = time.monotonic() - started
        detached_pid = int(pid_file.read_text())

        assert elapsed <= timeout + 3.0
    finally:
        if detached_pid is not None:
            with suppress(ProcessLookupError):
                os.kill(detached_pid, signal.SIGKILL)


def test_default_runner_tolerates_killpg_failures_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: PermissionError from either group signal escapes cleanup."""
    signals: list[signal.Signals] = []

    class TimeoutProcess:
        args = ("tool",)
        pid = 4321
        returncode: int | None = None
        stdout = None
        stderr = None
        communicates = 0

        def communicate(self, *, timeout: float | None = None) -> tuple[bytes, bytes]:
            self.communicates += 1
            assert timeout is not None
            if self.communicates == 1:
                raise subprocess.TimeoutExpired(self.args, timeout)
            self.returncode = -signal.SIGKILL
            return b"", b""

        def kill(self) -> None:
            self.returncode = -signal.SIGKILL

        def wait(self, *, timeout: float | None = None) -> int:
            assert timeout is not None
            assert self.returncode is not None
            return self.returncode

    process = TimeoutProcess()

    def fake_popen(argv: list[str], **_options: object) -> TimeoutProcess:
        assert argv == ["tool"]
        return process

    def denied_killpg(_pid: int, sent_signal: signal.Signals) -> None:
        signals.append(sent_signal)
        if sent_signal is signal.SIGTERM:
            raise ProcessLookupError
        raise PermissionError

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("dotfiles_setup.research_fanout.os.killpg", denied_killpg)

    with pytest.raises(subprocess.TimeoutExpired):
        default_runner(["tool"], timeout=0.0, env={})

    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert process.returncode == -signal.SIGKILL


def test_main_ctrl_c_terminates_real_child_and_returns_130(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: executor shutdown waits for the isolated child after Ctrl-C."""
    pid_file = tmp_path / "child.pid"
    script = tmp_path / "last30days.py"
    script.write_text(
        "import os, time\n"
        "from pathlib import Path\n"
        f"pid_path = Path({str(pid_file)!r})\n"
        "pending_path = pid_path.with_suffix('.pending')\n"
        "pending_path.write_text(str(os.getpid()))\n"
        "pending_path.replace(pid_path)\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))

    stop_interruptor = threading.Event()
    signal_sent_at: list[float] = []

    def interrupt_when_child_runs() -> None:
        deadline = time.monotonic() + 8.0
        while not stop_interruptor.is_set() and time.monotonic() < deadline:
            if pid_file.is_file():
                signal_sent_at.append(time.monotonic())
                os.kill(os.getpid(), signal.SIGINT)
                return
            stop_interruptor.wait(0.01)

    interruptor = threading.Thread(target=interrupt_when_child_runs)
    interruptor.start()
    try:
        rc = main(
            ["topic", "--sources", "last30days", "--timeout", "10"],
            tmp_path,
            runner=default_runner,
            http=FakeHttp({}),
        )
        finished_at = time.monotonic()
        assert signal_sent_at, "child PID was not published"
        assert pid_file.is_file()
        child_pid = int(pid_file.read_text())

        assert rc == 130
        assert finished_at - signal_sent_at[0] <= 3.0
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        stop_interruptor.set()
        interruptor.join(timeout=1.0)
        if pid_file.is_file():
            with suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)


def test_missing_prerequisite_and_repo_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    results = fan_out(
        FanoutRequest("topic", None, ("exa", "github-issues"), 10, 5.0),
        runner=_unused_runner,
        http=FakeHttp({}),
    )

    assert [(result.source, result.status, result.reason) for result in results] == [
        ("exa", Status.SKIPPED, "EXA_API_KEY not inherited; run through fnox exec"),
        ("github-issues", Status.SKIPPED, "needs --repo"),
    ]


@pytest.mark.parametrize(
    "case",
    [
        (
            "github-issues",
            (
                b'{"items":[{"title":"Issue","url":'
                b'"https://api.github.test/repos/o/r/issues/1","html_url":'
                b'"https://github.test/i/1","body":"body",'
                b'"created_at":"2026-09-01"}]}'
            ),
            "Issue",
            "https://github.test/i/1",
        ),
        (
            "github-discussions",
            (
                b'{"data":{"search":{"nodes":[{"title":"Discussion",'
                b'"url":"https://github.test/d/1","bodyText":"body",'
                b'"createdAt":"2026-09-02"}]}}}'
            ),
            "Discussion",
            "https://github.test/d/1",
        ),
        (
            "github-releases",
            (
                b'[{"tag_name":"v1.2.3","html_url":'
                b'"https://github.test/r/1","body":"topic fixed",'
                b'"published_at":"2026-09-03"}]'
            ),
            "v1.2.3",
            "https://github.test/r/1",
        ),
        (
            "firecrawl-search",
            b'{"data":[{"title":"Search","url":"https://search.test/1","description":"body"}]}',
            "Search",
            "https://search.test/1",
        ),
    ],
)
def test_subprocess_sources_normalize_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, bytes, str, str],
) -> None:
    """FAIL arm: preferring REST `url` exposes the GitHub API URL."""
    source, stdout, expected_title, expected_url = case
    tool = "firecrawl" if source == "firecrawl-search" else "gh"
    _install_path_tools(tmp_path, monkeypatch, tool)
    runner = ScriptedRunner([_completed([tool], 0, stdout)])

    [result] = fan_out(
        FanoutRequest("topic", "owner/project", (source,), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert result.items[0].title == expected_title
    assert result.items[0].url == expected_url
    assert len(result.items[0].snippet) <= 500


def test_github_issues_query_and_per_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: changing the repo qualifier or dropping per_page changes argv."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner(
        [
            _completed(
                ["gh"],
                0,
                b'{"items":[{"title":"Issue","html_url":"https://web.test"}]}',
            )
        ]
    )

    [result] = fan_out(
        FanoutRequest("tracked configs", "owner/project", ("github-issues",), 7, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert runner.calls[0][0] == [
        "gh",
        "api",
        "/search/issues?q=repo:owner/project+tracked+configs&per_page=7",
    ]


def test_github_source_checks_gh_presence(monkeypatch: pytest.MonkeyPatch) -> None:
    """FAIL arm: removing shutil.which tries to execute an absent gh binary."""
    monkeypatch.setenv("PATH", "")

    [result] = fan_out(
        FanoutRequest("topic", "owner/project", ("github-issues",), 10, 5.0),
        runner=_unused_runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.SKIPPED
    assert result.reason == "needs gh"


@pytest.mark.parametrize(
    "case",
    [
        (
            "github-issues",
            b'{"items":[]}',
            b'{"items":[{"title":"Project","html_url":"https://issue.test"}]}',
            "/search/issues?q=repo:owner/project+project&per_page=10",
        ),
        (
            "github-discussions",
            b'{"data":{"search":{"nodes":[]}}}',
            (
                b'{"data":{"search":{"nodes":[{"title":"Project",'
                b'"url":"https://discussion.test"}]}}}'
            ),
            "searchQuery=repo:owner/project project",
        ),
    ],
)
def test_github_empty_canary_uses_repo_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, bytes, bytes, str],
) -> None:
    """FAIL arm: replacing the repo-name canary with junk leaves empty unverified."""
    source, primary, canary, expected_fragment = case
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner(
        [_completed(["gh"], 0, primary), _completed(["gh"], 0, canary)]
    )

    [result] = fan_out(
        FanoutRequest("missing topic", "owner/project", (source,), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert result.control is not None
    assert result.control.query == "project"
    assert expected_fragment in " ".join(runner.calls[1][0])


def test_github_release_empty_checks_repo_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner(
        [
            _completed(
                ["gh"],
                0,
                b'[{"tag_name":"v1","name":"Routine","body":"housekeeping",'
                b'"html_url":"https://release.test/v1"}]',
            ),
            _completed(["gh"], 0, b'{"name":"project"}'),
        ]
    )

    [result] = fan_out(
        FanoutRequest("missing topic", "owner/project", ("github-releases",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert result.control is not None
    assert result.control.count == 1
    assert runner.calls[0][0][-1] == "repos/owner/project/releases?per_page=100"
    assert runner.calls[1][0][-1] == "repos/owner/project"


def test_github_release_repo_control_failure_is_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: assuming the repo exists turns a failed canary into verification."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner(
        [
            _completed(["gh"], 0, b"[]"),
            _completed(["gh"], 4, stderr=b"repository unavailable"),
        ]
    )

    [result] = fan_out(
        FanoutRequest("missing topic", "owner/project", ("github-releases",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_UNVERIFIED
    assert result.control is not None
    assert result.control.count is None
    assert result.reason == "canary failed"


def test_github_releases_filter_whole_words_and_stopwords(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: ANY-term matching admits releases missing a required term."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    payload = [
        {
            "tag_name": "v-tracked-1",
            "name": "Routine",
            "body": "",
            "html_url": "https://release.test/tag",
        },
        {
            "tag_name": "v2",
            "name": "Routine",
            "body": "untracked configuration only",
            "html_url": "https://release.test/substrings",
        },
        {
            "tag_name": "v3",
            "name": "The and with",
            "body": "the and with",
            "html_url": "https://release.test/stopwords",
        },
        {
            "tag_name": "v4",
            "name": "Config support",
            "body": "",
            "html_url": "https://release.test/name",
        },
        {
            "tag_name": "v5",
            "name": "Routine",
            "body": "Tracked config shipped",
            "html_url": "https://release.test/body",
        },
        {
            "tag_name": "tracked-v6",
            "name": "Config support",
            "body": "",
            "html_url": "https://release.test/split-fields",
        },
    ]
    runner = ScriptedRunner([_completed(["gh"], 0, json.dumps(payload).encode())])

    [result] = fan_out(
        FanoutRequest(
            "the tracked config",
            "owner/project",
            ("github-releases",),
            3,
            5.0,
        ),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert [item.url for item in result.items] == [
        "https://release.test/body",
        "https://release.test/split-fields",
    ]
    assert [item.snippet for item in result.items] == [
        "release body mentions a query term: yes",
        "release body mentions a query term: no",
    ]
    assert runner.calls[0][0][-1] == "repos/owner/project/releases?per_page=100"


def test_github_releases_ignore_terms_shorter_than_three_letters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: retaining the two-letter term makes the matching release vanish."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    payload = [
        {
            "tag_name": "v1",
            "name": "Fix shipped",
            "body": "",
            "html_url": "https://release.test/fix",
        }
    ]
    runner = ScriptedRunner([_completed(["gh"], 0, json.dumps(payload).encode())])

    [result] = fan_out(
        FanoutRequest("is fix", "owner/project", ("github-releases",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert [item.url for item in result.items] == ["https://release.test/fix"]


def test_github_releases_require_every_retained_query_term(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: ANY-term matching accepts `fixed` without `python`."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    releases = [
        {
            "tag_name": "v1",
            "name": "Fixed release",
            "body": "The issue is fixed.",
            "html_url": "https://release.test/fixed",
        }
    ]
    runner = ScriptedRunner(
        [
            _completed(["gh"], 0, json.dumps(releases).encode()),
            _completed(["gh"], 0, b'{"name":"project"}'),
        ]
    )

    [result] = fan_out(
        FanoutRequest(
            "is python fixed",
            "owner/project",
            ("github-releases",),
            10,
            5.0,
        ),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert result.items == ()


def test_context7_real_runner_resolves_library_under_forced_color(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: ANSI reset bytes enter the ID and make ctx7 docs reject it."""
    _install_path_tools(tmp_path, monkeypatch, "ctx7")
    (tmp_path / "ctx7").write_text(
        r"""#!/bin/sh
case "$1" in
    library)
        if [ -n "${FORCE_COLOR:-}" ] && [ "${NO_COLOR+x}" != x ]; then
            printf '\033[36mContext7-compatible library ID: /owner/library\033[39m\n'
        else
            printf 'Context7-compatible library ID: /owner/library\n'
        fi
        ;;
    docs)
        if [ "$2" != /owner/library ]; then
            printf '✖ Library "%s" not found\n' "$2" >&2
            exit 1
        fi
        printf '### Title\nSource: https://docs.test/x\nbody\n'
        ;;
esac
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FORCE_COLOR", "3")
    monkeypatch.delenv("NO_COLOR", raising=False)

    [result] = fan_out(
        FanoutRequest("topic", "owner/library", ("context7",), 10, 5.0),
        runner=default_runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert len(result.items) == 1
    assert result.items[0].title == "Title"
    assert result.items[0].url == "https://docs.test/x"


def test_context7_uses_first_library_and_parses_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_path_tools(tmp_path, monkeypatch, "ctx7")
    runner = ScriptedRunner(
        [
            _completed(
                ["ctx7"],
                0,
                b"1. Library\nContext7-compatible library ID: /owner/library\n"
                b"2. Other\nContext7-compatible library ID: /other/library\n",
            ),
            _completed(
                ["ctx7"],
                0,
                b"### Configuration\nSource: https://docs.test/config\nUse the API.\n"
                b"### Commands\nSource: https://docs.test/commands\nRun the CLI.\n",
            ),
        ]
    )

    [result] = fan_out(
        FanoutRequest("topic", None, ("context7",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert [item.title for item in result.items] == ["Configuration", "Commands"]
    assert runner.calls[0][0] == ["ctx7", "library", "topic"]
    assert runner.calls[1][0] == ["ctx7", "docs", "/owner/library", "topic"]


def test_context7_uses_repo_name_for_library_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: resolving from the research query selects an unrelated library."""
    _install_path_tools(tmp_path, monkeypatch, "ctx7")
    runner = ScriptedRunner(
        [
            _completed(
                ["ctx7"],
                0,
                b"1. Mise\nContext7-compatible library ID: /jdx/mise\n",
            ),
            _completed(
                ["ctx7"],
                0,
                b"### Config\nSource: https://mise.test/config\nTracked configs.\n",
            ),
        ]
    )

    [result] = fan_out(
        FanoutRequest("tracked configs", "jdx/mise", ("context7",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert runner.calls[0][0] == ["ctx7", "library", "mise"]
    assert runner.calls[1][0] == [
        "ctx7",
        "docs",
        "/jdx/mise",
        "tracked configs",
    ]


def test_context7_canary_resolves_python_independently_of_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: reusing the repo library does not test context7's Python path."""
    _install_path_tools(tmp_path, monkeypatch, "ctx7")
    runner = ScriptedRunner(
        [
            _completed(
                ["ctx7"],
                0,
                b"1. Mise\nContext7-compatible library ID: /jdx/mise\n",
            ),
            _completed(["ctx7"], 0, b"no matching sections"),
            _completed(
                ["ctx7"],
                0,
                b"1. Python\nContext7-compatible library ID: /python/cpython\n",
            ),
            _completed(
                ["ctx7"],
                0,
                b"### Python\nSource: https://python.test/docs\nLanguage docs.\n",
            ),
        ]
    )

    [result] = fan_out(
        FanoutRequest("missing topic", "jdx/mise", ("context7",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert result.control is not None
    assert result.control.query == "python"
    assert runner.calls[2][0] == ["ctx7", "library", "python"]
    assert runner.calls[3][0] == [
        "ctx7",
        "docs",
        "/python/cpython",
        "python",
    ]


@pytest.mark.parametrize("failure_site", ["library", "docs"])
def test_context7_reports_both_subprocess_error_sites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_site: str,
) -> None:
    """FAIL arm: either context7 failure site can lose its stderr diagnostic."""
    _install_path_tools(tmp_path, monkeypatch, "ctx7")
    library = _completed(
        ["ctx7"],
        0 if failure_site == "docs" else 6,
        b"1. Python\nContext7-compatible library ID: /python/cpython\n",
        b"library failed",
    )
    responses = [library]
    if failure_site == "docs":
        responses.append(_completed(["ctx7"], 7, stderr=b"docs failed"))
    runner = ScriptedRunner(responses)

    [result] = fan_out(
        FanoutRequest("topic", None, ("context7",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    expected = (
        "exited 6: library failed"
        if failure_site == "library"
        else "exited 7: docs failed"
    )
    assert result.status is Status.ERROR
    assert result.reason == expected


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"errors": []}, "response contained errors"),
        ([], "unexpected response shape"),
        ({"data": {}}, "unexpected discussions search shape"),
    ],
)
def test_github_discussions_rejects_graphql_error_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    reason: str,
) -> None:
    """FAIL arm: truthiness or a combined branch mislabels GraphQL responses."""
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner([_completed(["gh"], 0, json.dumps(payload).encode())])

    [result] = fan_out(
        FanoutRequest("topic", "owner/project", ("github-discussions",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.ERROR
    assert result.reason == reason


def test_firecrawl_developer_canary_keeps_repo_scope() -> None:
    http = FakeHttp(
        {
            "missing": (200, b'{"data": []}'),
            "project": (
                200,
                b'{"data":[{"title":"Project","url":"https://project.test"}]}',
            ),
        }
    )

    [result] = fan_out(
        FanoutRequest("missing", "owner/project", ("firecrawl-developer",), 10, 5.0),
        runner=_unused_runner,
        http=http,
    )

    assert result.status is Status.EMPTY_VERIFIED
    assert [call[1]["repos"] for call in http.calls] == [
        "owner/project",
        "owner/project",
    ]


def test_cli_child_environments_keep_only_required_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: passing os.environ leaks the non-kept credential sentinel."""
    _install_path_tools(tmp_path, monkeypatch, "gh", "firecrawl", "ctx7")
    credentials = {
        "GITHUB_TOKEN": "github-token",
        "GH_TOKEN": "gh-token",
        "FIRECRAWL_API_KEY": "firecrawl-key",
        "CONTEXT7_API_KEY": "context7-key",
        "EXA_API_KEY": "exa-key",
    }
    for name, value in credentials.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "non-kept-sentinel")

    gh_runner = ScriptedRunner(
        [
            _completed(
                ["gh"],
                0,
                b'{"items":[{"title":"Issue","html_url":"https://issue.test"}]}',
            )
        ]
    )
    firecrawl_runner = ScriptedRunner(
        [
            _completed(
                ["firecrawl"],
                0,
                b'{"data":{"web":[{"title":"Web","url":"https://web.test"}]}}',
            )
        ]
    )
    context7_runner = ScriptedRunner(
        [
            _completed(
                ["ctx7"],
                0,
                b"1. Library\nContext7-compatible library ID: /owner/library\n",
            ),
            _completed(
                ["ctx7"],
                0,
                b"### Docs\nSource: https://docs.test\nBody.\n",
            ),
        ]
    )

    fan_out(
        FanoutRequest("topic", "owner/project", ("github-issues",), 10, 5.0),
        runner=gh_runner,
        http=FakeHttp({}),
    )
    fan_out(
        FanoutRequest("topic", None, ("firecrawl-search",), 10, 5.0),
        runner=firecrawl_runner,
        http=FakeHttp({}),
    )
    fan_out(
        FanoutRequest("topic", None, ("context7",), 10, 5.0),
        runner=context7_runner,
        http=FakeHttp({}),
    )

    expected_by_runner = (
        (gh_runner, {"GITHUB_TOKEN", "GH_TOKEN"}),
        (firecrawl_runner, {"FIRECRAWL_API_KEY"}),
        (context7_runner, {"CONTEXT7_API_KEY"}),
    )
    credential_names = set(credentials)
    for runner, expected in expected_by_runner:
        for _argv, _timeout, env in runner.calls:
            assert credential_names.intersection(env) == expected
            assert "AWS_SECRET_ACCESS_KEY" not in env
            for name in expected:
                assert env[name] == credentials[name]


def test_last30days_is_opt_in_and_scrubs_llm_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "last30days.py"
    script.write_text("# test boundary\n", encoding="utf-8")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    github_credential = str(tmp_path / "github-credential")
    monkeypatch.setenv("GITHUB_TOKEN", github_credential)
    monkeypatch.setenv("SCRAPECREATORS_API_KEY", "scrape-key")
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    monkeypatch.setenv("PARALLEL_API_KEY", "parallel-key")
    monkeypatch.setenv("BRAVE_API_KEY", "brave-key")
    monkeypatch.setenv("OPENAI_API_KEY", "llm-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "non-kept-sentinel")
    monkeypatch.setenv("LAST30DAYS_TRUST_PROJECT_CONFIG", "1")
    runner = ScriptedRunner(
        [
            _completed(
                ["python3"],
                0,
                b'{"results":[{"title":"Recent","url":"https://recent.test/1","summary":"body","published_at":"2026-09-04"}]}',
            )
        ]
    )

    [result] = fan_out(
        FanoutRequest("topic", "owner/project", ("last30days",), 10, None),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    argv, timeout, env = runner.calls[0]
    assert argv == [
        "python3",
        str(script),
        "topic",
        "--emit=json",
        "--github-repo=owner/project",
    ]
    assert timeout == pytest.approx(180.0, abs=0.1)
    expected_kept = {
        "GITHUB_TOKEN": github_credential,
        "SCRAPECREATORS_API_KEY": "scrape-key",
        "EXA_API_KEY": "exa-key",
        "PARALLEL_API_KEY": "parallel-key",
        "BRAVE_API_KEY": "brave-key",
    }
    for name, value in expected_kept.items():
        assert env[name] == value
    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "LAST30DAYS_TRUST_PROJECT_CONFIG" not in env
    assert env["LAST30DAYS_CONFIG_DIR"] == ""
    assert env["LAST30DAYS_SKIP_KEYCHAIN"] == "1"


def test_last30days_discovers_highest_numeric_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LAST30DAYS_SCRIPT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    relative = Path("skills/last30days/scripts/last30days.py")
    scripts = []
    for version in ("3.9.0", "3.10.0"):
        script = (
            tmp_path
            / ".claude/plugins/cache/last30days-skill/last30days"
            / version
            / relative
        )
        script.parent.mkdir(parents=True)
        script.write_text("# test boundary\n", encoding="utf-8")
        scripts.append(script)
    runner = ScriptedRunner(
        [
            _completed(
                ["python3"],
                0,
                b'{"results":[{"title":"Recent","url":"https://recent.test"}]}',
            )
        ]
    )

    [result] = fan_out(
        FanoutRequest("topic", None, ("last30days",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert runner.calls[0][0][1] == str(scripts[1])


def test_last30days_empty_has_no_canary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "last30days.py"
    script.write_text("# test boundary\n", encoding="utf-8")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    runner = ScriptedRunner([_completed(["python3"], 0, b'{"results": []}')])

    [result] = fan_out(
        FanoutRequest("missing", None, ("last30days",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.EMPTY_UNVERIFIED
    assert result.reason == "no canary"
    assert result.control is not None
    assert result.control.query == ""
    assert result.control.count is None
    assert len(runner.calls) == 1


def test_secret_value_reaches_header_but_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = "SENTINEL-secret-value"
    monkeypatch.setenv("EXA_API_KEY", sentinel)
    expected_raw = (
        b'{"results":[{"title":"Result","url":"https://example.test/1","text":"body"}]}'
    )
    http = FakeHttp({"topic": (200, expected_raw)})
    out = tmp_path / "out"

    rc = main(
        ["topic", "--sources", "exa", "--out", str(out)],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert http.calls[0][2]["x-api-key"] == sentinel
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    assert all(sentinel not in path.read_text() for path in out.iterdir())
    assert (out / "exa.raw").read_bytes() == expected_raw
    manifest = json.loads((out / "manifest.json").read_text())
    assert (
        manifest["sources"][0]["raw_sha256"] == hashlib.sha256(expected_raw).hexdigest()
    )


@pytest.mark.parametrize(
    "credential",
    [
        "SENTINEL-invalid-header\r\nX-Injected: 1",
        "SENTINEL-invalid-header-\N{SNOWMAN}",
    ],
)
@pytest.mark.parametrize(
    "header_case",
    [
        ("exa", "EXA_API_KEY"),
        ("firecrawl-developer", "FIRECRAWL_API_KEY"),
    ],
)
def test_invalid_credential_header_never_leaks_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    credential: str,
    header_case: tuple[str, str],
) -> None:
    """FAIL arm: bypassing either header validator leaks the credential value."""
    source, credential_name = header_case
    sentinel = "SENTINEL-invalid-header"
    monkeypatch.setenv(credential_name, credential)
    http = FakeHttp({})
    out = tmp_path / "out"

    rc = main(
        ["topic", "--sources", source, "--out", str(out)],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )
    captured = capsys.readouterr()
    manifest = json.loads((out / "manifest.json").read_text())

    assert rc == 1
    assert http.calls == []
    assert manifest["sources"][0]["reason"] == (
        f"invalid credential header for {credential_name}"
    )
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    assert all(sentinel.encode() not in path.read_bytes() for path in out.iterdir())


@pytest.mark.parametrize(
    "case",
    [
        (
            ["topic", "--sources", "exa"],
            True,
            (200, b'{"results":[{"title":"ok","url":"https://example.test"}]}'),
            0,
        ),
        # Fail arm: an explicitly unavailable source leaves no verified success.
        (["topic", "--sources", "exa"], False, (200, b"{}"), 1),
        (["topic", "--sources", "unknown"], False, (200, b"{}"), 2),
    ],
)
def test_main_exit_code_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[list[str], bool, tuple[int, bytes], int],
) -> None:
    argv, has_key, http_response, expected = case
    if has_key:
        monkeypatch.setenv("EXA_API_KEY", "test-key")
    else:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
    http = FakeHttp({"topic": http_response})

    rc = main(
        [*argv, "--out", str(tmp_path / "out")],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )

    assert rc == expected


def test_main_returns_one_when_every_result_is_empty_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: counting empty_unverified as success incorrectly returns zero."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    http = FakeHttp(
        {
            "topic": (200, b'{"results":[]}'),
            "python": (200, b'{"results":[]}'),
        }
    )

    rc = main(
        ["topic", "--sources", "exa", "--out", str(tmp_path / "out")],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )

    assert rc == 1


def test_reused_output_directory_clears_only_owned_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: omitting cleanup leaves an unrequested stale source beside manifest."""
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    out = tmp_path / "out"
    out.mkdir()
    source_names = (
        "github-issues",
        "github-discussions",
        "github-releases",
        "exa",
        "context7",
        "firecrawl-developer",
        "firecrawl-search",
        "last30days",
    )
    (out / "manifest.json").write_text("stale", encoding="utf-8")
    for source in source_names:
        (out / f"{source}.json").write_text("stale", encoding="utf-8")
        (out / f"{source}.raw").write_text("stale", encoding="utf-8")
    unrelated = out / "operator-notes.txt"
    unrelated.write_text("keep", encoding="utf-8")
    http = FakeHttp(
        {
            "topic": (
                200,
                b'{"results":[{"title":"ok","url":"https://result.test"}]}',
            )
        }
    )

    rc = main(
        ["topic", "--sources", "exa", "--out", str(out)],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )

    assert rc == 0
    assert (out / "exa.json").is_file()
    assert (out / "exa.raw").is_file()
    for source in source_names:
        if source != "exa":
            assert not (out / f"{source}.json").exists()
            assert not (out / f"{source}.raw").exists()
    assert unrelated.read_text() == "keep"


def test_default_output_slug_is_truncated_to_sixty_characters(tmp_path: Path) -> None:
    """FAIL arm: removing slug truncation creates a longer output directory."""
    query = "A" * 75
    http = FakeHttp(
        {
            query: (
                200,
                b'{"results":[{"title":"ok","url":"https://result.test"}]}',
            )
        }
    )

    rc = main(
        [query, "--sources", "firecrawl-developer"],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )
    expected = tmp_path / ".agent/kb/raw/research-fanout" / ("a" * 60) / "manifest.json"

    assert rc == 0
    assert expected.is_file()


def test_list_sources_names_every_source_without_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EXA_API_KEY", "SECRET-not-for-stdout")

    rc = main(
        ["--list-sources"],
        tmp_path,
        runner=_unused_runner,
        http=FakeHttp({}),
    )
    captured = capsys.readouterr()

    assert rc == 0
    for source in (
        "github-issues",
        "github-discussions",
        "github-releases",
        "exa",
        "context7",
        "firecrawl-developer",
        "firecrawl-search",
        "last30days",
    ):
        assert source in captured.out
    assert "SECRET-not-for-stdout" not in captured.out


def _github_presence(
    argv: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> set[str]:
    rc = main(argv, tmp_path, runner=_unused_runner, http=FakeHttp({}))
    assert rc == 0
    return {
        line.rsplit("  ", 1)[1]
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("github-")
    }


def test_list_sources_github_needs_repo_when_gh_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With gh but no --repo: `needs --repo`, never `absent` (2026-09-30).

    FAIL arm: map every unmet prerequisite to `absent` again and a planner
    reading this list drops every github-* source.
    """
    _install_path_tools(tmp_path, monkeypatch, "gh")

    assert _github_presence(["--list-sources"], tmp_path, capsys) == {"needs --repo"}
    # control arms: a repo makes them present; no gh makes them absent
    assert _github_presence(
        ["--list-sources", "--repo", "cli/cli"], tmp_path, capsys
    ) == {"present"}
    monkeypatch.setenv("PATH", "")
    assert _github_presence(["--list-sources"], tmp_path, capsys) == {"absent"}


def test_default_sources_exclude_last30days(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: adding last30days to defaults invokes the hermetic fake script."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path))
    script = tmp_path / "last30days.py"
    script.write_text("# opt-in fail arm\n", encoding="utf-8")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    for name in (
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    http = FakeHttp(
        {
            "topic": (
                200,
                b'{"data":[{"title":"Developer","url":"https://developer.test/1"}]}',
            )
        }
    )
    out = tmp_path / "out"

    rc = main(
        ["topic", "--out", str(out)],
        tmp_path,
        runner=_unused_runner,
        http=http,
    )
    manifest = json.loads((out / "manifest.json").read_text())

    assert rc == 0
    assert [source["source"] for source in manifest["sources"]] == [
        "firecrawl-developer"
    ]


def test_two_sources_run_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    delay = 0.2
    monkeypatch.setenv("EXA_API_KEY", "test-key")

    def slow_http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, body, headers, timeout
        time.sleep(delay)
        return 200, b'{"results":[{"title":"ok","url":"https://example.test"}]}'

    started = time.monotonic()
    results = fan_out(
        FanoutRequest("topic", None, ("exa", "firecrawl-developer"), 10, 5.0),
        runner=_unused_runner,
        http=slow_http,
    )
    elapsed = time.monotonic() - started

    assert all(result.status is Status.OK for result in results)
    assert elapsed < 2 * delay


# Real response shapes, trimmed from live calls on 2026-09-26. The earlier
# fixtures used an invented `{"data": [...]}` shape, so both firecrawl sources
# passed here while failing live (HTTP 400 on `limit`; the CLI's default
# `web,alexandria` returned the tool catalog under `data.tools`).
_FIRECRAWL_DEVELOPER_LIVE = json.dumps(
    {
        "success": True,
        "partial": False,
        "results": [
            {
                "id": "pull_request:jdx/mise#7997",
                "url": "https://github.com/jdx/mise/issues/7997",
                "title": "jdx/mise#7997",
                "passages": [{"text": "## Summary\n- tracked configs during upgrade"}],
            }
        ],
        "repos": [],
    }
).encode()
_FIRECRAWL_SEARCH_LIVE = json.dumps(
    {
        "success": True,
        "data": {
            "web": [
                {
                    "url": "https://mise.jdx.dev/cli/config.html",
                    "title": "mise config | mise-en-place",
                    "description": "--tracked-configs — List all tracked config files.",
                }
            ]
        },
    }
).encode()


def test_firecrawl_developer_live_shape_and_k_param() -> None:
    """FAIL arm: send `limit` (a live 400) or drop the passages fallback."""
    http = FakeHttp({"tracked configs": (200, _FIRECRAWL_DEVELOPER_LIVE)})

    [result] = fan_out(
        FanoutRequest("tracked configs", "jdx/mise", ("firecrawl-developer",), 7, 5.0),
        runner=_unused_runner,
        http=http,
    )

    assert result.status is Status.OK
    assert result.items[0].url == "https://github.com/jdx/mise/issues/7997"
    assert "tracked configs during upgrade" in result.items[0].snippet
    params = http.calls[0][1]
    assert params["k"] == 7
    assert "limit" not in params


def test_firecrawl_search_restricts_to_web_and_parses_web_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FAIL arm: drop `--sources web` or the `web` key and this goes red."""
    _install_path_tools(tmp_path, monkeypatch, "firecrawl")
    runner = ScriptedRunner([_completed(["firecrawl"], 0, _FIRECRAWL_SEARCH_LIVE)])

    [result] = fan_out(
        FanoutRequest("tracked configs", None, ("firecrawl-search",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.OK
    assert result.items[0].title == "mise config | mise-en-place"
    argv = runner.calls[0][0]
    assert argv[argv.index("--sources") + 1] == "web"


_CREDIT_FIXTURES = Path(__file__).parent / "fixtures/research_fanout"
# Coordinator f9467b, 2026-10-03 22:2x CDT; fc402/rc.txt records both rc=1:
# mise exec -- firecrawl search "mise tasks" --limit 1
# mise exec -- firecrawl scrape https://mise.jdx.dev/ --format markdown
_CAPTURED_CREDIT_RC = 1


@pytest.fixture
def credit_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate all metered keys and CLI discovery from the interactive shell."""
    for name in (
        "SERPER_API_KEY",
        "SERP_API_KEY",
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
        "CONTEXT7_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    binary = tmp_path / "bin"
    binary.mkdir()
    for name in ("firecrawl", "webclaw", "ctx7", "gh"):
        executable = binary / name
        executable.write_text("#!/bin/sh\nexit 99\n")
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary))


@pytest.mark.parametrize(
    ("status", "text", "expected"),
    [
        (402, "", True),
        (429, "quota exceeded", True),
        (429, "rate limit", False),
        (401, "Insufficient credits", False),
        (403, "out of credits", False),
        (500, "payment required", False),
        (200, "Insufficient credits", False),
        (None, "connection reset", False),
        (None, "billing", False),
        (401, "Not enough credits", False),
        (None, 'Error: {"status":402}', True),
        (None, '{"statusCode": 402}', True),
        (None, "status code 402", True),
        (None, "HTTP 402", True),
        (None, "HTTP/1.1 402 Payment Required", True),
        (None, "HTTP 429 quota exceeded", True),
        (None, '{"status":429,"error":"exceeded your quota"}', True),
        (None, "HTTP 429 rate limit", False),
        (None, "quota exceeded", False),
        (None, "exceeded your quota", False),
        (None, "https://primary.test/issues/402", False),
        (None, "index.js:402:17", False),
        (None, "request id 402, query=429", False),
        (None, "Insufficient credits", True),
        (None, "credits exhausted", True),
        (None, "Not enough credits", True),
        (None, "run out of searches", True),
        (None, "payment required", True),
        (None, "out of credits", True),
        (None, "HTTP 401 Not enough credits", False),
    ],
)
def test_credit_classifier_status_table(
    status: int | None, text: str, *, expected: bool
) -> None:
    assert is_credit_exhaustion(status, text) is expected


@pytest.mark.parametrize("route", ["search", "scrape"])
def test_credit_classifier_live_fixtures(route: str) -> None:
    assert is_credit_exhaustion(
        None, (_CREDIT_FIXTURES / f"firecrawl-402-{route}.err").read_text()
    )


@pytest.mark.parametrize("body", [b"", b"Insufficient credits"])
def test_credit_http_402_is_skipped_without_fallback(
    tmp_path: Path, credit_env: None, body: bytes
) -> None:
    del credit_env
    http = FakeHttp({"topic": (402, body)})
    assert (
        main(
            ["topic", "--sources", "firecrawl-developer", "--out", str(tmp_path)],
            tmp_path,
            http=http,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        "credits-exhausted",
        True,
    )
    assert len(http.calls) == 1
    _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(tmp_path / "manifest.json", "turn-1")[0] is True


def _merge_credit_manifest(directory: Path, row: dict[str, Any]) -> Path:
    preserved = {p: p.read_bytes() for p in directory.glob(f"{row['source']}*.raw")}
    path = _strict_manifest(directory)
    for raw, content in preserved.items():
        raw.write_bytes(content)
    manifest = json.loads(path.read_text())
    manifest["sources"] = [
        row if r["source"] == row["source"] else r for r in manifest["sources"]
    ]
    path.write_text(json.dumps(manifest))
    return path


def test_credit_http_500_stays_error(tmp_path: Path, credit_env: None) -> None:
    del credit_env
    http = FakeHttp({"topic": (500, b"payment required")})
    assert (
        main(
            ["topic", "--sources", "firecrawl-developer", "--out", str(tmp_path)],
            tmp_path,
            http=http,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["reason"], row["provisional"], row["attempts"]) == (
        "error",
        "HTTP 500",
        False,
        [],
    )
    assert len(http.calls) == 1


@pytest.mark.parametrize("defensive", [False, True])
def test_credit_search_substitution_redacts_and_binds_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    credit_env: None,
    *,
    defensive: bool,
) -> None:
    del credit_env
    sentinel = "SERPER-sentinel-never-persist"
    monkeypatch.setenv("SERPER_API_KEY", sentinel)
    runner = ScriptedRunner(
        [
            _completed(
                [], 0, b'{"success":false,"error":"Insufficient credits","status":402}'
            )
            if defensive
            else _completed(
                [],
                _CAPTURED_CREDIT_RC,
                (_CREDIT_FIXTURES / "firecrawl-402-search.out").read_bytes(),
                (_CREDIT_FIXTURES / "firecrawl-402-search.err").read_bytes(),
            )
        ]
    )
    http = FakeHttp(
        {
            "topic": (
                200,
                json.dumps(
                    {
                        "organic": [
                            {
                                "title": "Result",
                                "link": "https://primary.test/doc",
                                "snippet": sentinel
                                + " https://google.serper.dev/search?api_key="
                                + sentinel,
                            }
                        ]
                    }
                ).encode(),
            )
        }
    )
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 0
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["route"], row["provisional"]) == ("ok", "serper", True)
    assert row["items"][0]["url"] == "https://primary.test/doc"
    assert http.calls[0][0] is Endpoint.SERPER_SEARCH
    assert http.calls[0][1] == {"q": "topic", "num": 10}
    assert http.calls[0][2]["X-API-KEY"] == sentinel
    envelope = json.loads((tmp_path / "firecrawl-search.primary.raw").read_bytes())
    assert envelope["rc"] == (0 if defensive else _CAPTURED_CREDIT_RC)
    if not defensive:
        assert "https://firecrawl.dev/pricing" in envelope["stderr_redacted"]
    output = capsys.readouterr().out
    assert "provisional" in output
    assert sentinel not in output
    for path in tmp_path.glob("*.json"):
        assert sentinel not in path.read_text()
    for path in tmp_path.glob("*.raw"):
        assert sentinel.encode() not in path.read_bytes()
        assert b"https://google.serper.dev/search" not in path.read_bytes()
    manifest = _merge_credit_manifest(tmp_path, row)
    passed, reason = validate_strict_five(manifest, "turn-1")
    assert passed
    assert reason.startswith("provisional: firecrawl-search via serper")


def test_credit_search_chain_uses_serpapi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del credit_env
    sentinel = "SERPAPI-sentinel-never-persist"
    monkeypatch.setenv("SERP_API_KEY", sentinel)
    runner = ScriptedRunner(
        [
            _completed(
                [],
                1,
                stderr=(_CREDIT_FIXTURES / "firecrawl-402-search.err").read_bytes(),
            )
        ]
    )
    http = FakeHttp(
        {"topic": (200, b'{"organic_results":[{"link":"https://primary.test/api"}]}')}
    )
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 0
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["route"] == "serpapi"
    assert row["attempts"][1]["status"] == "skipped"
    assert "not inherited" in row["attempts"][1]["reason"]
    assert http.calls[0][0] is Endpoint.SERPAPI_SEARCH
    assert http.calls[0][1] == {"engine": "google", "q": "topic", "api_key": sentinel}
    assert sentinel not in capsys.readouterr().out
    assert all(sentinel.encode() not in p.read_bytes() for p in tmp_path.glob("*.raw"))
    assert sentinel not in (tmp_path / "manifest.json").read_text()


def test_credit_fallback_genuine_error_is_not_laundered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "sentinel")
    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    http = FakeHttp({"topic": (500, b"payment required")})
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["status"] == "error"
    assert row["attempts"][1]["status"] == "error"
    assert row["provisional"] is False


@pytest.mark.parametrize("source", ["firecrawl-search", "firecrawl-developer"])
def test_credit_strict_forgery_rederives_http_and_cli(
    tmp_path: Path, credit_env: None, source: str
) -> None:
    del credit_env
    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    http = FakeHttp({"topic": (402, b"")})
    main(
        ["topic", "--sources", source, "--out", str(tmp_path)],
        tmp_path,
        runner=runner,
        http=http,
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    manifest = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(manifest, "turn-1")[0]
    envelope = json.dumps(
        {
            "http_status": 500 if source == "firecrawl-developer" else None,
            "rc": None if source == "firecrawl-developer" else 1,
            "body": "",
            "stderr_redacted": "Unauthorized",
        }
    ).encode()
    Path(row["attempts"][0]["raw_file"]).write_bytes(envelope)
    row["attempts"][0]["raw_sha256"] = hashlib.sha256(envelope).hexdigest()
    row["attempts"][0]["http_status"] = 402
    Path(row["raw_file"]).write_bytes(envelope)
    row["raw_sha256"] = hashlib.sha256(envelope).hexdigest()
    data = json.loads(manifest.read_text())
    data["sources"] = [row if r["source"] == source else r for r in data["sources"]]
    manifest.write_text(json.dumps(data))
    assert validate_strict_five(manifest, "turn-1") == (
        False,
        f"{source} credit-exhaustion evidence does not re-derive",
    )


def test_credit_strict_rejects_v1_and_github_exception(tmp_path: Path) -> None:
    path = _strict_manifest(tmp_path)
    data = json.loads(path.read_text())
    data["policy_version"] = "strict-five-v1"
    path.write_text(json.dumps(data))
    assert validate_strict_five(path, "turn-1") == (
        False,
        "request identity or policy mismatch",
    )
    data["policy_version"] = "strict-five-v2"
    data["sources"][0].update(
        status="skipped", skip_reason="credits-exhausted", provisional=True
    )
    path.write_text(json.dumps(data))
    assert validate_strict_five(path, "turn-1")[0] is False
    data["sources"][0].update(skip_reason="prerequisite", provisional=False)
    path.write_text(json.dumps(data))
    assert validate_strict_five(path, "turn-1")[0] is False


def test_credit_reuse_clears_attempt_files_and_lists_fallbacks(
    tmp_path: Path, credit_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    del credit_env
    for name in (
        "firecrawl-search.primary.raw",
        "firecrawl-search.serper.raw",
        "firecrawl-search.serpapi.raw",
    ):
        (tmp_path / name).write_text("old")
    main(
        ["topic", "--sources", "firecrawl-developer", "--out", str(tmp_path)],
        tmp_path,
        http=FakeHttp({"topic": (500, b"")}),
    )
    assert not (tmp_path / "firecrawl-search.primary.raw").exists()
    assert not (tmp_path / "firecrawl-search.serper.raw").exists()
    assert not (tmp_path / "firecrawl-search.serpapi.raw").exists()
    capsys.readouterr()
    assert main(["--list-sources"], tmp_path) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 11
    assert lines[-3:] == [
        "fallback:serper  HTTPS POST  SERPER_API_KEY in process environment  absent",
        "fallback:serpapi  HTTPS GET  SERP_API_KEY in process environment  absent",
        "fallback:webclaw  webclaw CLI  webclaw on PATH  present",
    ]


def test_credit_http_reason_redacts_request_urls_and_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del credit_env
    sentinel = "exa-sentinel-secret"
    monkeypatch.setenv("EXA_API_KEY", sentinel)
    body = (
        f"Insufficient credits {sentinel} "
        f"https://serpapi.com/search.json?api_key={sentinel} "
        "https://firecrawl.dev/pricing"
    ).encode()
    assert (
        main(
            ["topic", "--sources", "exa", "--out", str(tmp_path)],
            tmp_path,
            http=FakeHttp({"topic": (402, body)}),
        )
        == 1
    )
    output = capsys.readouterr().out
    assert sentinel not in output
    assert "https://serpapi.com/search.json" not in output
    assert "https://firecrawl.dev/pricing" not in output
    assert "https://firecrawl.dev/pricing" in (tmp_path / "exa.json").read_text()
    for file in (*tmp_path.glob("*.json"), *tmp_path.glob("*.raw")):
        assert sentinel.encode() not in file.read_bytes()
        assert b"https://serpapi.com/search.json" not in file.read_bytes()


@pytest.mark.parametrize(
    "response",
    [
        (500, b"payment required"),
        (200, b"invalid JSON Insufficient credits"),
    ],
)
def test_credit_genuine_primary_errors_do_not_try_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    response: tuple[int, bytes],
) -> None:
    del credit_env
    monkeypatch.setenv("EXA_API_KEY", "exa-sentinel")
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    http = FakeHttp({"topic": response})
    assert (
        main(["topic", "--sources", "exa", "--out", str(tmp_path)], tmp_path, http=http)
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["status"] == "error"
    assert row["provisional"] is False
    assert row["attempts"] == []
    assert len(http.calls) == 1


def test_credit_fallback_empty_requires_positive_same_route_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    http = FakeHttp(
        {
            "topic": (200, b'{"organic":[]}'),
            "python": (200, b'{"organic":[{"link":"https://python.org"}]}'),
        }
    )
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 0
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["status"] == "empty_verified"
    assert row["control"] == {"query": "python", "count": 1}
    assert [call[0] for call in http.calls] == [
        Endpoint.SERPER_SEARCH,
        Endpoint.SERPER_SEARCH,
    ]
    path = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(path, "turn-1")[0] is True
    data = json.loads(path.read_text())
    source = next(r for r in data["sources"] if r["source"] == "firecrawl-search")
    source["control"]["count"] = 0
    path.write_text(json.dumps(data))
    assert validate_strict_five(path, "turn-1") == (
        False,
        "firecrawl-search empty result lacks a positive control",
    )


def test_credit_earlier_fallback_error_survives_later_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    monkeypatch.setenv("SERP_API_KEY", "serpapi-sentinel")
    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    calls = []

    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del params, body, headers, timeout
        calls.append(endpoint)
        return (
            (500, b"failure")
            if endpoint is Endpoint.SERPER_SEARCH
            else (200, b'{"organic_results":[{"link":"https://primary.test"}]}')
        )

    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 0
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["route"] == "serpapi"
    assert row["attempts"][1]["status"] == "error"
    assert "serper: http-error" in capsys.readouterr().out
    assert calls == [Endpoint.SERPER_SEARCH, Endpoint.SERPAPI_SEARCH]
    path = _merge_credit_manifest(tmp_path, row)
    assert "serper: http-error" in validate_strict_five(path, "turn-1")[1]


def test_credit_cli_full_stderr_classifies_before_reason_cut(
    tmp_path: Path, credit_env: None
) -> None:
    del credit_env
    runner = ScriptedRunner(
        [
            _completed(
                [], 1, stderr=b"Insufficient credits\n" + b"diagnostic details " * 100
            )
        ]
    )
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["skip_reason"] == "credits-exhausted"
    assert len(row["reason"]) <= 300
    assert len(row["attempts"][0]["reason"]) <= 300
    assert (
        "Insufficient credits"
        in json.loads((tmp_path / "firecrawl-search.primary.raw").read_bytes())[
            "stderr_redacted"
        ]
    )


@pytest.mark.parametrize("route", ["serper", "serpapi"])
def test_credit_fallback_default_transport_uses_primary_doc_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, route: str
) -> None:
    del credit_env
    monkeypatch.setenv(
        "SERPER_API_KEY" if route == "serper" else "SERP_API_KEY", "fallback-sentinel"
    )
    calls = []
    payload = (
        b'{"organic":[{"link":"https://primary.test"}]}'
        if route == "serper"
        else b'{"organic_results":[{"link":"https://primary.test"}]}'
    )

    def urlopen(request: urllib.request.Request, *, timeout: float) -> ChunkedResponse:
        assert timeout > 0
        calls.append(request)
        return ChunkedResponse([payload])

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=default_http,
        )
        == 0
    )
    assert len(calls) == 1
    request = calls[0]
    if route == "serper":
        assert request.full_url == "https://google.serper.dev/search"
        assert request.get_method() == "POST"
        assert request.get_header("X-api-key") == "fallback-sentinel"
        assert isinstance(request.data, bytes)
        assert json.loads(request.data) == {"q": "topic", "num": 10}
    else:
        assert request.get_method() == "GET"
        assert request.full_url == (
            "https://serpapi.com/search.json?engine=google&"
            "q=topic&api_key=fallback-sentinel"
        )
        assert request.data is None


def test_credit_later_quota_does_not_replace_genuine_error_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    monkeypatch.setenv("SERP_API_KEY", "serpapi-sentinel")

    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del params, body, headers, timeout
        return (
            (500, b"server unavailable")
            if endpoint is Endpoint.SERPER_SEARCH
            else (402, b"Insufficient credits")
        )

    runner = ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")])
    assert (
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=http,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["status"] == "error"
    assert row["reason"] == "HTTP 500"
    assert row["provisional"] is False
    assert (tmp_path / "firecrawl-search.raw").read_bytes() == b"server unavailable"
    assert row["attempts"][2]["status"] == "skipped"


def test_credit_all_metered_sources_form_provisional_strict_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("EXA_API_KEY", "exa-sentinel")
    runner = ScriptedRunner(
        [_completed([], 1, stderr=b"Insufficient credits") for _ in range(2)]
    )
    sources = "exa,context7,firecrawl-developer,firecrawl-search"
    assert (
        main(
            ["topic", "--sources", sources, "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
            http=FakeHttp({"topic": (402, b"")}),
        )
        == 1
    )
    credit_rows = json.loads((tmp_path / "manifest.json").read_text())["sources"]
    assert [row["status"] for row in credit_rows] == ["skipped"] * 4
    evidence = {path: path.read_bytes() for path in tmp_path.glob("*.raw")}
    path = _strict_manifest(tmp_path)
    for raw, content in evidence.items():
        raw.write_bytes(content)
    data = json.loads(path.read_text())
    replacements = {row["source"]: row for row in credit_rows}
    data["sources"] = [replacements.get(row["source"], row) for row in data["sources"]]
    path.write_text(json.dumps(data))
    passed, reason = validate_strict_five(path, "turn-1")
    assert passed
    assert reason.startswith("provisional: ")
    for source in sources.split(","):
        assert f"{source} skipped: credits-exhausted" in reason


@pytest.mark.parametrize("source", ["firecrawl-search", "context7"])
@pytest.mark.parametrize(
    "stderr",
    [
        b"request failed: https://primary.test/issues/402",
        b"quota exceeded",
        b"index.js:402:17",
    ],
)
def test_credit_cli_unstructured_numbers_and_quota_stay_errors(
    tmp_path: Path, credit_env: None, source: str, stderr: bytes
) -> None:
    del credit_env
    runner = ScriptedRunner([_completed([], 1, stderr=stderr)])
    assert (
        main(
            ["topic", "--sources", source, "--out", str(tmp_path)],
            tmp_path,
            runner=runner,
        )
        == 1
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["provisional"], row["attempts"]) == ("error", False, [])
    assert len(runner.calls) == 1


@pytest.mark.parametrize("source", ["github-issues", "firecrawl-search"])
@pytest.mark.parametrize(
    "url",
    [
        "https://serpapi.com/search.json?q=x",
        "https://google.serper.dev/search?q=x",
        "https://serpapi.com/docs",
    ],
)
def test_provider_json_preserves_quoted_search_urls(
    tmp_path: Path, credit_env: None, source: str, url: str
) -> None:
    del credit_env
    record = {
        "html_url": "https://primary.test",
        "url": "https://primary.test",
        "body": f'<a href="{url}">link</a>',
    }
    payload = (
        {"items": [record]}
        if source == "github-issues"
        else {"success": True, "data": {"web": [record]}}
    )
    raw = json.dumps(payload).encode()
    assert (
        main(
            [
                "topic",
                "--repo",
                "owner/repo",
                "--sources",
                source,
                "--out",
                str(tmp_path),
            ],
            tmp_path,
            runner=ScriptedRunner([_completed([], 0, raw)]),
        )
        == 0
    )
    assert json.loads((tmp_path / f"{source}.raw").read_bytes()) == payload


def test_cli_stdout_credential_is_redacted_before_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    sentinel = "gh-stdout-credential-sentinel"
    monkeypatch.setenv("GH_TOKEN", sentinel)
    raw = json.dumps(
        {"items": [{"html_url": "https://primary.test", "title": sentinel}]}
    ).encode()
    assert (
        main(
            [
                "topic",
                "--repo",
                "owner/repo",
                "--sources",
                "github-issues",
                "--out",
                str(tmp_path),
            ],
            tmp_path,
            runner=ScriptedRunner([_completed([], 0, raw)]),
        )
        == 0
    )
    persisted = json.loads((tmp_path / "github-issues.raw").read_bytes())
    assert persisted["items"][0]["title"] == "[REDACTED]"
    assert all(
        sentinel.encode() not in p.read_bytes()
        for p in tmp_path.glob("*")
        if p.is_file()
    )


@pytest.mark.parametrize(
    "case",
    [
        ("serper", (400, b'{"message":"Not enough credits"}')),
        ("serpapi", (403, b'{"error":"Your account has run out of searches."}')),
        ("serpapi", (429, b'{"error":"Your account has run out of searches."}')),
    ],
)
def test_fallback_provider_exhaustion_is_status_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    capsys: pytest.CaptureFixture[str],
    case: tuple[str, tuple[int, bytes]],
) -> None:
    del credit_env
    route, response = case
    # SerpApi: https://serpapi.com/api-status-and-error-codes. Serper's status
    # is intentionally unverified; the ratified fallback rule accepts its text.
    monkeypatch.setenv(
        "SERPER_API_KEY" if route == "serper" else "SERP_API_KEY", "fallback-sentinel"
    )
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({"topic": response}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    attempt = next(a for a in row["attempts"] if a["route"] == route)
    assert (row["status"], attempt["status"]) == ("skipped", "skipped")
    assert response[1].decode() == attempt["reason"]
    output = capsys.readouterr().out
    assert response[1].decode() not in output
    assert "credits-exhausted" in output
    assert f"{'serpapi' if route == 'serper' else 'serper'}: prerequisite" in output
    assert "no fallback route" not in output
    path = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(path, "turn-1")[0]


@pytest.mark.parametrize("positive_control", [True, False])
def test_serpapi_documented_empty_state_requires_same_route_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    *,
    positive_control: bool,
) -> None:
    del credit_env
    monkeypatch.setenv("SERP_API_KEY", "fallback-sentinel")
    # Trimmed documented empty search, https://serpapi.com/api-status-and-error-codes.
    empty = (_CREDIT_FIXTURES / "serpapi-empty-search.json").read_bytes()
    control = (
        b'{"organic_results":[{"link":"https://python.org"}]}'
        if positive_control
        else empty
    )
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({"topic": (200, empty), "python": (200, control)}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["status"] == ("empty_verified" if positive_control else "error")
    attempt = row["attempts"][-1]
    assert attempt["status"] == (
        "empty_verified" if positive_control else "empty_unverified"
    )
    path = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(path, "turn-1")[0] is positive_control


@pytest.mark.parametrize("route", ["serper", "serpapi"])
def test_fallback_limit_and_escaped_url_redaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, route: str
) -> None:
    del credit_env
    monkeypatch.setenv(
        "SERPER_API_KEY" if route == "serper" else "SERP_API_KEY", "fallback-sentinel"
    )
    records = [
        {
            "link": f"https://primary.test/{i}",
            "snippet": '<a href="https://serpapi.com/search.json?q=x">link</a>',
        }
        for i in range(3)
    ]
    raw = json.dumps(
        {"organic" if route == "serper" else "organic_results": records}
    ).encode()
    assert (
        main(
            [
                "topic",
                "--sources",
                "firecrawl-search",
                "--limit",
                "1",
                "--out",
                str(tmp_path),
            ],
            tmp_path,
            runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
            http=FakeHttp({"topic": (200, raw)}),
        )
        == 0
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert len(row["items"]) == 1
    assert row["items"][0]["snippet"] == '<a href="[REDACTED REQUEST URL]">link</a>'
    persisted = (tmp_path / "firecrawl-search.raw").read_bytes()
    assert (
        len(
            json.loads(persisted)["organic" if route == "serper" else "organic_results"]
        )
        == 3
    )
    assert row["raw_sha256"] == hashlib.sha256(persisted).hexdigest()
    assert validate_strict_five(_merge_credit_manifest(tmp_path, row), "turn-1")[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "skip-bytes",
        "primary-path",
        "output-path",
        "winning-path",
        "winning-hash",
        "ok-empty",
    ],
)
def test_credit_receipt_rejects_unbound_or_divergent_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, mutation: str
) -> None:
    del credit_env
    if mutation != "skip-bytes":
        monkeypatch.setenv("SERPER_API_KEY", "fallback-sentinel")
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp(
            {"topic": (200, b'{"organic":[{"link":"https://primary.test"}]}')}
        ),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    path = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(path, "turn-1")[0]
    if mutation.endswith("path"):
        target = (
            row["attempts"][0]
            if mutation == "primary-path"
            else row["attempts"][1]
            if mutation == "winning-path"
            else row
        )
        moved = tmp_path / "other" / Path(target["raw_file"]).name
        moved.parent.mkdir()
        moved.write_bytes(Path(target["raw_file"]).read_bytes())
        target["raw_file"] = str(moved)
    else:
        raw = (
            b'{"different":true}'
            if mutation == "skip-bytes"
            else b'{"organic":[]}'
            if mutation == "ok-empty"
            else b'{"organic":[{"link":"https://different.test"}]}'
        )
        Path(row["raw_file"]).write_bytes(raw)
        row["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        if mutation == "ok-empty":
            winning = row["attempts"][1]
            Path(winning["raw_file"]).write_bytes(raw)
            winning["raw_sha256"] = row["raw_sha256"]
    manifest = json.loads(path.read_text())
    manifest["sources"] = [
        row if r["source"] == row["source"] else r for r in manifest["sources"]
    ]
    path.write_text(json.dumps(manifest))
    passed, reason = validate_strict_five(path, "turn-1")
    assert passed is False
    expected = (
        "unbound raw evidence"
        if mutation.endswith("path")
        else "invalid credit skip evidence"
        if mutation == "skip-bytes"
        else "raw evidence is not a successful fallback response"
        if mutation == "ok-empty"
        else "missing winning route evidence"
    )
    assert reason == f"firecrawl-search {expected}"


def test_fallback_invalid_credential_keeps_specific_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "bad\ncredential-sentinel")
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["reason"] == "invalid credential header for SERPER_API_KEY"
    assert row["attempts"][1]["reason"] == row["reason"]


def test_fallback_incomplete_body_keeps_specific_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "fallback-sentinel")
    original_urlopen = urllib.request.urlopen
    with _local_http_body(b'{"organic":[]}', declared_length=100) as url:

        def local_urlopen(_request: object, *, timeout: float) -> object:
            return original_urlopen(url, timeout=timeout)

        monkeypatch.setattr(urllib.request, "urlopen", local_urlopen)
        main(
            ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
            tmp_path,
            runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
            http=default_http,
        )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert row["reason"] == "incomplete response"
    assert row["attempts"][1]["reason"] == "incomplete response"


def test_out_expands_quoted_home_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (
        main(
            [
                "topic",
                "--repo",
                "owner/repo",
                "--sources",
                "github-issues",
                "--out",
                "~/coverage",
            ],
            tmp_path,
            runner=ScriptedRunner(
                [_completed([], 0, b'{"items":[{"html_url":"https://primary.test"}]}')]
            ),
        )
        == 0
    )
    assert (tmp_path / "coverage/manifest.json").is_file()
    assert not (tmp_path / "~").exists()


@pytest.mark.parametrize("route", ["serper", "serpapi"])
@pytest.mark.parametrize(
    "arm",
    ["200-credit-shape", "200-shape", "200-valid", "credit", "nested", "plain", "list"],
)
def test_projection_fallback_transport_and_top_level_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    route: str,
    arm: str,
) -> None:
    """T6/T8: failure transport and top-level text are independent axes."""
    del credit_env
    monkeypatch.setenv(
        "SERPER_API_KEY" if route == "serper" else "SERP_API_KEY", "fixture-key"
    )
    field = "message" if route == "serper" else "error"
    status = 400 if route == "serper" else 403
    if arm == "200-credit-shape":
        status, payload = (
            200,
            {
                "knowledgeGraph": {"description": "Not enough credits"},
                field: "Not enough credits",
            },
        )
    elif arm == "200-shape":
        status, payload = 200, {"knowledgeGraph": {"description": "ordinary text"}}
    elif arm == "200-valid":
        status = 200
        payload = {
            "organic" if route == "serper" else "organic_results": [
                {
                    "title": "doc",
                    "link": "https://primary.test",
                    "snippet": "Not enough credits",
                }
            ]
        }
    elif arm == "credit":
        payload = {field: "Not enough credits"}
    elif arm == "nested":
        payload = {"detail": {field: "Not enough credits"}}
    elif arm == "list":
        payload = [{field: "Not enough credits"}]
    else:
        payload = None
    body = b"Not enough credits" if payload is None else json.dumps(payload).encode()
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({"topic": (status, body)}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    attempt = next(a for a in row["attempts"] if a["route"] == route)
    assert attempt["http_status"] == status
    expected = "ok" if arm == "200-valid" else "skipped" if arm == "credit" else "error"
    assert attempt["status"] == expected
    if arm in {"200-credit-shape", "200-shape"}:
        assert attempt["reason"] == "unexpected fallback response shape"
    verdict = validate_strict_five(_merge_credit_manifest(tmp_path, row), "turn-1")
    assert verdict[0] is (arm in {"credit", "200-valid"})
    if arm == "credit":
        envelope = json.loads(Path(attempt["raw_file"]).read_text())
        assert envelope == {
            "http_status": status,
            "rc": None,
            "body": body.decode(),
            "stderr_redacted": "",
        }


@pytest.mark.parametrize(
    "evidence", ["genuine", "bare", "200-credit", "400-no-credit", "malformed", "cli"]
)
def test_projection_fallback_skip_rederives_bound_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    evidence: str,
) -> None:
    """T7: hash validity alone cannot establish a fallback credit skip."""
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "fixture-key")
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({"topic": (400, b'{"message":"Not enough credits"}')}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    attempt = row["attempts"][1]
    bodies = {
        "bare": {"message": "Not enough credits"},
        "200-credit": {
            "http_status": 200,
            "rc": None,
            "body": '{"message":"Not enough credits"}',
            "stderr_redacted": "",
        },
        "400-no-credit": {
            "http_status": 400,
            "rc": None,
            "body": '{"message":"invalid query"}',
            "stderr_redacted": "",
        },
        "malformed": {
            "http_status": 400,
            "rc": None,
            "body": [],
            "stderr_redacted": "",
        },
        "cli": {
            "http_status": None,
            "rc": 1,
            "body": '{"message":"Not enough credits"}',
            "stderr_redacted": "",
        },
    }
    if evidence != "genuine":
        raw = json.dumps(bodies[evidence]).encode()
        Path(attempt["raw_file"]).write_bytes(raw)
        attempt["raw_sha256"] = hashlib.sha256(raw).hexdigest()
    verdict = validate_strict_five(_merge_credit_manifest(tmp_path, row), "turn-1")
    if evidence == "genuine":
        assert verdict[0] is True
    else:
        assert verdict == (
            False,
            "firecrawl-search fallback credit skip does not re-derive",
        )


@pytest.mark.parametrize(
    "reason", ["SERPER_API_KEY not inherited; run through fnox exec", "key gone"]
)
def test_projection_fallback_prerequisite_exact_literal(
    tmp_path: Path,
    credit_env: None,
    reason: str,
) -> None:
    del credit_env
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    row["attempts"][1]["reason"] = reason
    verdict = validate_strict_five(_merge_credit_manifest(tmp_path, row), "turn-1")
    if reason == "key gone":
        assert verdict == (False, "firecrawl-search invalid fallback prerequisite skip")
    else:
        assert verdict[0] is True


@pytest.mark.parametrize("arm", ["credit", "process", "http", "prerequisite"])
def test_projection_cli_preserves_diagnostics_only_in_evidence(
    tmp_path: Path,
    credit_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arm: str,
) -> None:
    """T9: public CLI projection has a separate evidence-preservation control."""
    del credit_env
    sentinel = "cli-diagnostic-" + uuid.uuid4().hex
    source = "exa" if arm in {"http", "prerequisite"} else "firecrawl-search"
    if arm == "http":
        monkeypatch.setenv("EXA_API_KEY", "fixture-key")
    if arm == "prerequisite":
        monkeypatch.delenv("EXA_API_KEY", raising=False)
    runner = ScriptedRunner(
        [
            _completed(
                [],
                1,
                stderr=(
                    "Insufficient credits " + sentinel if arm == "credit" else sentinel
                ).encode(),
            )
        ]
    )
    main(
        ["topic", "--sources", source, "--out", str(tmp_path)],
        tmp_path,
        runner=runner,
        http=FakeHttp({"topic": (500, sentinel.encode())}),
    )
    output = capsys.readouterr().out
    assert sentinel not in output
    expected = {
        "credit": "credits-exhausted",
        "process": "[process-failed]",
        "http": "[http-error]",
        "prerequisite": "[skipped: credential-missing; EXA_API_KEY not inherited; "
        "run through fnox exec]",
    }
    assert expected[arm] in output
    if arm in {"credit", "http"}:
        assert sentinel in (tmp_path / f"{source}.raw").read_text()
    if arm in {"credit", "process"}:
        assert sentinel in (tmp_path / f"{source}.json").read_text()
    if arm == "credit":
        row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
        passed, reason = validate_strict_five(
            _merge_credit_manifest(tmp_path, row), "turn-1"
        )
        assert passed is True
        assert sentinel not in reason
        assert "serper: prerequisite; serpapi: prerequisite" in reason


def test_projection_fallback_reason_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
) -> None:
    """T16: the fallback manifest keeps the final 300 diagnostic characters."""
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "fixture-key")
    sentinel = "cap-diagnostic-" + uuid.uuid4().hex
    body = json.dumps(
        {"message": "Not enough credits " + "x" * 400 + sentinel}
    ).encode()
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, stderr=b"Insufficient credits")]),
        http=FakeHttp({"topic": (400, body)}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert len(row["attempts"][1]["reason"]) == 300
    assert row["attempts"][1]["reason"].endswith(sentinel + '"}')


@pytest.mark.parametrize(
    ("reason", "status", "skip", "expected"),
    [
        ("diagnostic", "ok", "credits-exhausted", None),
        ("diagnostic", "empty_verified", None, None),
        ("HTTP 500", "skipped", "credits-exhausted", "credits-exhausted"),
        ("diagnostic", "skipped", "prerequisite", "prerequisite"),
        ("needs gh", "skipped", None, "prerequisite"),
        ("needs gh", "error", None, "other"),
        ("HTTP 500", "error", None, "http-error"),
        ("HTTP 500 diagnostic", "error", None, "other"),
        ("invalid JSON", "error", None, "invalid-json"),
        ("unexpected response shape", "error", None, "shape-error"),
        ("unexpected discussions search shape", "error", None, "shape-error"),
        ("unexpected JSON shape", "error", None, "shape-error"),
        ("unexpected fallback response shape", "error", None, "shape-error"),
        ("response contained errors", "error", None, "shape-error"),
        ("provider reported failure", "error", None, "provider-failure"),
        ("exited -1: diagnostic", "error", None, "process-failed"),
        ("timed out", "error", None, "timeout"),
        ("request failed", "error", None, "request-failed"),
        ("response too large", "error", None, "request-failed"),
        ("incomplete response", "error", None, "request-failed"),
        (
            "invalid credential header for EXA_API_KEY",
            "error",
            None,
            "credential-invalid",
        ),
        ("canary failed", "empty_unverified", None, "canary-failed"),
        ("canary returned 0 items", "empty_unverified", None, "canary-empty"),
        ("no canary", "empty_unverified", None, "no-canary"),
        ("script disappeared", "error", None, "not-found"),
        ("unknown source", "error", None, "not-found"),
        (None, "error", None, "other"),
        ([], "error", None, "other"),
    ],
)
def test_projection_failure_code_public_mapping(
    reason: object,
    status: str,
    skip: str | None,
    expected: str | None,
) -> None:
    result = failure_code(reason, status=status, skip_reason=skip)
    assert (result.value if result else None) == expected


def test_projection_strict_cli_line_contains_no_diagnostics(
    tmp_path: Path,
    credit_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T9: execute the real strict-five producer path with isolated boundaries."""
    del credit_env
    sentinel = "strict-diagnostic-" + uuid.uuid4().hex
    monkeypatch.setenv("EXA_API_KEY", "fixture-key")
    script = tmp_path / "last30days.py"
    script.write_text("fixture only")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    plan = tmp_path / "plan.json"
    plan.write_text(
        '{"subqueries":[{"search_query":"topic","sources":["hackernews"]}]}'
    )

    def runner(
        argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        del timeout, env
        if argv[0] in {"ctx7", "firecrawl"}:
            return _completed(
                argv, 1, stderr=("Insufficient credits " + sentinel).encode()
            )
        if argv[0] == "python3":
            payload = {
                "schema_version": "1.3",
                "source_status": {"hackernews": "ok"},
                "results": [{"url": "https://primary.test"}],
            }
        elif "graphql" in argv:
            payload = {"data": {"search": {"nodes": [{"url": "https://primary.test"}]}}}
        elif any("/releases" in arg for arg in argv):
            payload = [{"html_url": "https://primary.test", "name": "topic"}]
        else:
            payload = {"items": [{"html_url": "https://primary.test"}]}
        return _completed(argv, 0, json.dumps(payload).encode())

    assert (
        main(
            [
                "topic",
                "--repo",
                "owner/repo",
                "--strict-five",
                "--policy-version",
                "strict-five-v2",
                "--request-id",
                "turn-1",
                "--last30days-plan",
                str(plan),
                "--out",
                str(tmp_path),
            ],
            tmp_path,
            runner=runner,
            http=FakeHttp({"topic": (402, sentinel.encode())}),
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "strict-five  pass  [provisional: " in output
    assert sentinel not in output
    manifest = (tmp_path / "manifest.json").read_text()
    assert sentinel in manifest
    assert sentinel in (tmp_path / "firecrawl-search.json").read_text()


def _raising_http(error: BaseException) -> Http:
    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, body, headers, timeout
        raise error

    return http


def _relabel(manifest: Path, source: str, code: str) -> None:
    data = json.loads(manifest.read_text())
    next(r for r in data["sources"] if r["source"] == source)["skip_reason"] = code
    manifest.write_text(json.dumps(data))


@pytest.mark.parametrize(
    "case",
    [
        ((401, b"Insufficient credits"), "auth-failed", "quota"),
        ((403, b""), "auth-failed", "credits-exhausted"),
        ((429, b"rate limit"), "quota", "auth-failed"),
    ],
)
def test_metered_http_skip_code_rederives_from_hashed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    case: tuple[tuple[int, bytes], str, str],
) -> None:
    """D236: 401/403 auth-failed and 429 quota skip with their HTTP evidence."""
    del credit_env
    response, code, forged = case
    monkeypatch.setenv("EXA_API_KEY", "exa-sentinel")
    http = FakeHttp({"topic": response})
    main(["topic", "--sources", "exa", "--out", str(tmp_path)], tmp_path, http=http)
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        code,
        True,
    )
    assert len(http.calls) == 1
    manifest = _merge_credit_manifest(tmp_path, row)
    passed, reason = validate_strict_five(manifest, "turn-1")
    assert passed
    assert f"exa skipped: {code}" in reason
    _relabel(manifest, "exa", forged)
    assert validate_strict_five(manifest, "turn-1")[0] is False


@pytest.mark.parametrize(
    "case",
    [
        (TimeoutError(), "unavailable", "timed out"),
        (urllib.error.URLError(TimeoutError()), "unavailable", "timed out"),
        (ConnectionRefusedError(61, "refused"), "unavailable", "request failed"),
        (
            urllib.error.URLError(socket.gaierror(8, "dns")),
            "unavailable",
            "request failed",
        ),
        (PermissionError(1, "denied"), "sandbox-denied", "request failed"),
        (
            urllib.error.URLError(OSError(1, "denied")),
            "sandbox-denied",
            "request failed",
        ),
    ],
)
def test_metered_transport_failure_skips_with_error_class_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    case: tuple[BaseException, str, str],
) -> None:
    """D236: connection, DNS and timeout are unavailable; EPERM is sandbox-denied."""
    del credit_env
    error, code, reason = case
    monkeypatch.setenv("EXA_API_KEY", "exa-sentinel")
    main(
        ["topic", "--sources", "exa", "--out", str(tmp_path)],
        tmp_path,
        http=_raising_http(error),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["skip_reason"], row["reason"]) == (
        "skipped",
        code,
        reason,
    )
    evidence = json.loads(Path(row["raw_file"]).read_bytes())
    assert set(evidence) == {"error_class", "errno"}
    manifest = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(manifest, "turn-1")[0] is True
    _relabel(manifest, "exa", "quota" if code == "unavailable" else "unavailable")
    assert validate_strict_five(manifest, "turn-1")[0] is False


def test_metered_cli_permission_error_is_sandbox_denied(
    tmp_path: Path, credit_env: None
) -> None:
    del credit_env

    def denied(
        argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        del argv, timeout, env
        raise PermissionError(1, "denied")

    main(
        ["topic", "--sources", "context7", "--out", str(tmp_path)],
        tmp_path,
        runner=denied,
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["skip_reason"]) == ("skipped", "sandbox-denied")
    assert validate_strict_five(_merge_credit_manifest(tmp_path, row), "turn-1")[0]


def test_missing_exa_key_is_a_credential_missing_skip(
    tmp_path: Path, credit_env: None
) -> None:
    """Cold review P2-2: the producer writes the code, not prerequisite."""
    del credit_env
    main(
        ["topic", "--sources", "exa", "--out", str(tmp_path)],
        tmp_path,
        http=FakeHttp({}),
    )
    row = json.loads((tmp_path / "manifest.json").read_text())["sources"][0]
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        "credential-missing",
        True,
    )
    assert row["reason"] == "EXA_API_KEY not inherited; run through fnox exec"
    manifest = _merge_credit_manifest(tmp_path, row)
    passed, reason = validate_strict_five(manifest, "turn-1")
    assert passed
    assert "exa skipped: credential-missing" in reason


def test_non_metered_transport_failure_stays_error(credit_env: None) -> None:
    """GitHub and Last30Days are the fallback chain itself, never skipped."""
    del credit_env

    def denied(
        argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        del argv, timeout, env
        raise PermissionError(1, "denied")

    [result] = fan_out(
        FanoutRequest("topic", "openai/codex", ("github-issues",), 10, 5.0),
        runner=denied,
        http=FakeHttp({}),
    )
    assert (result.status, result.skip_reason) == (Status.ERROR, None)


def test_every_skip_reason_projects_to_its_own_failure_code() -> None:
    """Cold review P3: no skip code collapses to `other`."""
    for reason in SkipReason:
        code = failure_code("diagnostic", status="skipped", skip_reason=reason.value)
        assert code is not None
        assert code.value == reason.value


def _only_row(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "manifest.json").read_text())["sources"][0]


_SERPER_OK = (
    200,
    json.dumps(
        {"organic": [{"title": "R", "link": "https://primary.test/doc"}]}
    ).encode(),
)


@pytest.mark.parametrize(
    "error",
    [
        ssl.SSLError(1, "tls alert"),
        ssl.SSLCertVerificationError(1, "certificate verify failed"),
        urllib.error.URLError(ssl.SSLEOFError(8, "eof")),
    ],
    ids=["ssl-errno-1", "cert-verify", "ssl-eof"],
)
def test_tls_failure_is_unavailable_not_sandbox_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    error: BaseException,
) -> None:
    """Round 3 (b): errno 1 on a TLS error is not EPERM; only PermissionError is."""
    del credit_env
    monkeypatch.setenv("EXA_API_KEY", "exa-sentinel")
    main(
        ["topic", "--sources", "exa", "--out", str(tmp_path)],
        tmp_path,
        http=_raising_http(error),
    )
    row = _only_row(tmp_path)
    assert (row["status"], row["skip_reason"]) == ("skipped", "unavailable")
    manifest = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(manifest, "turn-1")[0] is True
    _relabel(manifest, "exa", "sandbox-denied")
    assert validate_strict_five(manifest, "turn-1")[0] is False


@pytest.mark.parametrize(
    ("source", "cli"), [("context7", "ctx7"), ("firecrawl-search", "firecrawl")]
)
def test_missing_metered_cli_is_an_unavailable_skip(
    tmp_path: Path, credit_env: None, source: str, cli: str
) -> None:
    """Round 3 (d): a missing ctx7 or firecrawl CLI is coded, not a blocker."""
    del credit_env
    (tmp_path / "bin" / cli).unlink()
    main(["topic", "--sources", source, "--out", str(tmp_path)], tmp_path)
    row = _only_row(tmp_path)
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        "unavailable",
        True,
    )
    assert row["reason"] == f"needs {cli}"
    passed, reason = validate_strict_five(
        _merge_credit_manifest(tmp_path, row), "turn-1"
    )
    assert passed
    assert f"{source} skipped: unavailable" in reason


def test_missing_firecrawl_cli_still_routes_to_serper_with_its_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    (tmp_path / "bin" / "firecrawl").unlink()
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        http=FakeHttp({"topic": _SERPER_OK}),
    )
    row = _only_row(tmp_path)
    assert (row["status"], row["route"], row["skip_reason"]) == (
        "ok",
        "serper",
        "unavailable",
    )
    passed, reason = validate_strict_five(
        _merge_credit_manifest(tmp_path, row), "turn-1"
    )
    assert passed
    assert reason.startswith("provisional: firecrawl-search via serper (unavailable)")


@pytest.mark.parametrize(
    ("stderr", "code"),
    [
        (b"Error: HTTP 429 Too Many Requests", "quota"),
        (b"rate limited; retry later", "quota"),
        (b"Error: too many requests", "quota"),
        (b"Request failed with status code 401", "auth-failed"),
        (b"Error: HTTP 500", None),
        (b"Error: exited after 429 lines", None),
    ],
)
def test_cli_status_or_rate_limit_with_nonzero_exit_is_coded(
    tmp_path: Path, credit_env: None, stderr: bytes, code: str | None
) -> None:
    """Round 3 (e): a CLI rate limit with a non-zero exit is a quota skip."""
    del credit_env
    main(
        ["topic", "--sources", "context7", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, b"", stderr)]),
    )
    row = _only_row(tmp_path)
    if code is None:
        assert (row["status"], row.get("skip_reason")) == ("error", None)
        return
    assert (row["status"], row["skip_reason"]) == ("skipped", code)
    manifest = _merge_credit_manifest(tmp_path, row)
    assert validate_strict_five(manifest, "turn-1")[0] is True
    _relabel(manifest, "context7", "unavailable")
    assert validate_strict_five(manifest, "turn-1")[0] is False


def test_substituted_route_carries_its_real_skip_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    """Round 3 (a): a quota-limited primary routed to serper names quota."""
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=ScriptedRunner([_completed([], 1, b"", b"Error: HTTP 429")]),
        http=FakeHttp({"topic": _SERPER_OK}),
    )
    row = _only_row(tmp_path)
    assert (row["status"], row["route"], row["skip_reason"]) == (
        "ok",
        "serper",
        "quota",
    )
    manifest = _merge_credit_manifest(tmp_path, row)
    passed, reason = validate_strict_five(manifest, "turn-1")
    assert passed
    assert reason.startswith("provisional: firecrawl-search via serper (quota)")
    _relabel(manifest, "firecrawl-search", "auth-failed")
    assert validate_strict_five(manifest, "turn-1")[0] is False


@pytest.mark.parametrize("skip_reason", [["quota"], {"quota": 1}, 7])
def test_non_string_skip_reason_projects_to_other(skip_reason: object) -> None:
    """Round 3 (c): an unhashable or non-string skip_reason never crashes."""
    code = failure_code(None, status="skipped", skip_reason=skip_reason)
    assert code is not None
    assert code.value == "other"


def _break_last30days(manifest: Path) -> None:
    data = json.loads(manifest.read_text())
    row = next(r for r in data["sources"] if r["source"] == "last30days")
    row.update(status="error", items=[], reason="needs last30days script")
    manifest.write_text(json.dumps(data))


def test_web_route_covers_a_missing_last30days_as_provisional(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    """Round 4 (r3 P3-1): GitHub plus a Serper route passes without Last30Days."""
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-sentinel")
    (tmp_path / "bin" / "firecrawl").unlink()
    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        http=FakeHttp({"topic": _SERPER_OK}),
    )
    manifest = _merge_credit_manifest(tmp_path, _only_row(tmp_path))
    _break_last30days(manifest)
    verdict = strict_five_verdict(manifest, "turn-1")
    assert verdict.passed
    assert any(line.startswith("last30days skipped") for line in verdict.provisional)
    assert ("last30days", None) in {
        (entry.source, entry.route) for entry in verdict.provisional_entries
    }


def test_missing_last30days_without_a_web_route_still_fails(tmp_path: Path) -> None:
    manifest = _strict_manifest(tmp_path)
    _break_last30days(manifest)
    assert validate_strict_five(manifest, "turn-1") == (
        False,
        "last30days did not complete",
    )


@pytest.mark.parametrize("prefix", ["status", "status code", "Status:", "HTTP"])
def test_credit_status_scan_is_linear_on_blank_runs(prefix: str) -> None:
    """Security P3-4: long blank runs after a status word stay linear."""
    text = (prefix + " " * 20_000 + "x ") * 3
    started = time.perf_counter()
    assert is_credit_exhaustion(None, text) is False
    assert time.perf_counter() - started < 0.2


def test_credit_scan_reads_a_bounded_prefix() -> None:
    assert is_credit_exhaustion(None, "Error: HTTP 402") is True
    assert is_credit_exhaustion(None, "a" * 200_000 + " HTTP 402") is False


_MANIFEST_CAP = 1024 * 1024
_RAW_CAP = 8 * 1024 * 1024


def _bounded_receipt(directory: Path, lane: str) -> tuple[Path, Path, int]:
    directory.mkdir(exist_ok=True)
    manifest = _strict_manifest(directory)
    target = manifest if lane == "manifest" else directory / "context7.raw"
    if lane in {"provisional", "attempt"}:
        data = json.loads(manifest.read_text())
        raw = json.dumps(
            {"http_status": 402, "rc": None, "body": "", "stderr_redacted": ""}
        ).encode()
        primary = directory / "firecrawl-developer.primary.raw"
        primary.write_bytes(raw)
        top = directory / "firecrawl-developer.raw"
        top.write_bytes(raw)
        row = next(r for r in data["sources"] if r["source"] == "firecrawl-developer")
        row.update(
            status="skipped",
            items=[],
            provisional=True,
            skip_reason="credits-exhausted",
            raw_sha256=hashlib.sha256(raw).hexdigest(),
            attempts=[
                {
                    "route": "firecrawl-developer",
                    "status": "skipped",
                    "http_status": 402,
                    "reason": "HTTP 402",
                    "raw_file": str(primary),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                }
            ],
        )
        manifest.write_text(json.dumps(data))
        target = primary if lane == "attempt" else top
    assert strict_five_verdict(manifest, "turn-1").passed
    return manifest, target, _MANIFEST_CAP if lane == "manifest" else _RAW_CAP


def _pad_bound_evidence(manifest: Path, target: Path, size: int) -> None:
    raw = target.read_bytes()
    target.write_bytes(raw + b" " * (size - len(raw)))
    if target == manifest:
        return
    data = json.loads(manifest.read_text())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    for row in data["sources"]:
        evidence_rows = (row, *row.get("attempts", []))
        paired_envelope = row.get("provisional") and any(
            evidence.get("raw_file") == str(target) for evidence in evidence_rows
        )
        for evidence in evidence_rows:
            if paired_envelope:
                Path(evidence["raw_file"]).write_bytes(target.read_bytes())
            if paired_envelope or evidence.get("raw_file") == str(target):
                evidence["raw_sha256"] = digest
    manifest.write_text(json.dumps(data))


def _verdict_process(manifest: Path) -> subprocess.CompletedProcess[str]:
    program = (
        "import sys;from pathlib import Path;"
        "from dotfiles_setup.research_fanout import strict_five_verdict;"
        "print(strict_five_verdict(Path(sys.argv[1]),'turn-1').passed)"
    )
    return subprocess.run(
        [sys.executable, "-c", program, str(manifest)],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).parent.parent / "python/src"),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )


@pytest.mark.parametrize("lane", ["manifest", "strict", "provisional", "attempt"])
@pytest.mark.parametrize(
    "kind", ["regular", "exact-cap", "oversize", "symlink", "directory", "fifo"]
)
def test_receipt_reads_are_bounded_regular_and_never_follow_leaf_links(
    tmp_path: Path, lane: str, kind: str
) -> None:
    """CG-36c F4: every receipt lane has a passing control and a bounded failure."""
    manifest, target, cap = _bounded_receipt(tmp_path / "evidence", lane)
    if kind in {"exact-cap", "oversize"}:
        _pad_bound_evidence(manifest, target, cap + (kind == "oversize"))
    elif kind == "symlink":
        saved = target.with_suffix(".saved")
        target.rename(saved)
        target.symlink_to(saved)
    elif kind in {"directory", "fifo"}:
        target.unlink()
        target.mkdir() if kind == "directory" else os.mkfifo(target)
    result = _verdict_process(manifest)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(kind in {"regular", "exact-cap"})


def test_receipt_rejects_a_symlink_in_any_parent(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    manifest = _strict_manifest(link)
    result = _verdict_process(manifest)
    assert result.returncode == 0
    assert result.stdout.strip() == "False"


@pytest.mark.parametrize("lane", ["manifest", "provisional", "attempt"])
def test_deeply_nested_evidence_is_refused_without_crashing(
    tmp_path: Path, lane: str
) -> None:
    manifest, target, _ = _bounded_receipt(tmp_path / "evidence", lane)
    target.write_bytes(b"[" * 1100 + b"]" * 1100)
    _pad_bound_evidence(manifest, target, target.stat().st_size)
    result = _verdict_process(manifest)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


# D381 axes: policy x eight arms x transport evidence x identity/integrity x
# completion. These fixtures extend, rather than relabel, the v2 fixtures above.
_D381_POLICY = "strict-five-v3-d381"
_D381_SOURCES = (
    "github-issues",
    "github-discussions",
    "github-releases",
    "exa",
    "context7",
    "firecrawl-developer",
    "firecrawl-search",
    "last30days",
)
_D381_NOW = datetime(2026, 10, 18, 12, tzinfo=UTC)
_D381_RENEWAL = "2026-11-01T00:00:00+00:00"
_D381_REASON_CAP = 300


def _d381_manifest(
    directory: Path,
    source: str = "exa",
    *,
    envelope: dict[str, object] | None = None,
    code: str = "credits-exhausted",
) -> Path:
    """Independent literal receipt: one bound refusal and seven real-shaped hits."""
    path = _strict_manifest(directory)
    data = json.loads(path.read_text())
    data.update(
        policy_version=_D381_POLICY,
        generated_at=_D381_NOW.isoformat(),
        disposition="complete",
        skipped_sources=[source],
        failed_sources=[],
    )
    proof = (
        envelope
        if envelope is not None
        else {
            "http_status": 402,
            "rc": None,
            "body": "Insufficient credits",
            "stderr_redacted": "",
        }
    )
    raw = json.dumps(proof).encode()
    digest = hashlib.sha256(raw).hexdigest()
    for label in (source, f"{source}.primary"):
        (directory / f"{label}.raw").write_bytes(raw)
    for row in data["sources"]:
        row["provisional"] = False
        if row["source"] == source:
            row.update(
                status="skipped",
                items=[],
                control=None,
                reason=code,
                skip_reason=code,
                raw_sha256=digest,
                attempts=[
                    {
                        "route": source,
                        "status": "skipped",
                        "http_status": proof.get("http_status"),
                        "reason": code,
                        "raw_file": str(directory / f"{source}.primary.raw"),
                        "raw_sha256": digest,
                    }
                ],
            )
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize(
    ("envelope", "code"),
    [
        (
            {"http_status": 402, "rc": None, "body": "", "stderr_redacted": ""},
            "credits-exhausted",
        ),
        (
            {
                "http_status": 429,
                "rc": None,
                "body": "Monthly quota exhausted",
                "stderr_redacted": "",
            },
            "quota",
        ),
        (
            {
                "http_status": None,
                "rc": 0,
                "body": "Monthly quota reached",
                "stderr_redacted": "",
            },
            "quota",
        ),
    ],
    ids=["payment-required", "quota-exhausted", "rc0-quota-refusal"],
)
def test_d381_verdict_accepts_only_evidenced_exhaustion_without_provisional(
    tmp_path: Path, source: str, envelope: dict[str, object], code: str
) -> None:
    manifest = _d381_manifest(tmp_path, source, envelope=envelope, code=code)
    verdict = strict_five_verdict(manifest, "turn-1")
    assert verdict.passed, verdict.reason
    assert verdict.provisional == ()
    assert verdict.provisional_entries == ()
    assert "provisional" not in verdict.reason.lower()
    assert validate_strict_five(manifest, "turn-1")[0] is True


def test_d381_all_eight_exhausted_arms_are_skips_without_successful_items(
    tmp_path: Path,
) -> None:
    rows = []
    evidence: dict[Path, bytes] = {}
    for source in _D381_SOURCES:
        manifest = _d381_manifest(tmp_path, source)
        rows.append(
            next(
                row
                for row in json.loads(manifest.read_text())["sources"]
                if row["source"] == source
            )
        )
        for label in (source, f"{source}.primary"):
            raw = tmp_path / f"{label}.raw"
            evidence[raw] = raw.read_bytes()
    for raw, content in evidence.items():
        raw.write_bytes(content)
    data = json.loads(manifest.read_text())
    data.update(sources=rows, skipped_sources=list(_D381_SOURCES))
    manifest.write_text(json.dumps(data))
    verdict = strict_five_verdict(manifest, "turn-1")
    assert verdict.passed, verdict.reason
    assert verdict.provisional == ()
    assert verdict.provisional_entries == ()
    assert all(row["items"] == [] for row in rows)


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize(
    ("envelope", "code"),
    [
        (
            {
                "http_status": 401,
                "rc": None,
                "body": "Insufficient credits",
                "stderr_redacted": "",
            },
            "auth-failed",
        ),
        (
            {"http_status": 403, "rc": None, "body": "", "stderr_redacted": ""},
            "auth-failed",
        ),
        ({"error_class": "FileNotFoundError", "errno": 2}, "unavailable"),
        ({"error_class": "PermissionError", "errno": 1}, "sandbox-denied"),
        ({"error_class": "TimeoutExpired"}, "unavailable"),
    ],
    ids=["auth401-credit-decoy", "auth403", "missing-cli", "sandbox", "timeout"],
)
def test_d381_verdict_keeps_nonexhaustion_incomplete(
    tmp_path: Path, source: str, envelope: dict[str, object], code: str
) -> None:
    manifest = _d381_manifest(tmp_path, source)
    # The positive arm prevents an unimplemented-policy rejection masquerading
    # as successful authentication/unrunnable coverage.
    assert strict_five_verdict(manifest, "turn-1").passed
    _d381_manifest(tmp_path, source, envelope=envelope, code=code)
    verdict = strict_five_verdict(manifest, "turn-1")
    assert not verdict.passed
    assert source in verdict.reason


@pytest.mark.parametrize(
    "corruption",
    [
        "hash",
        "primary-hash",
        "bare",
        "auth-relabel",
        "items",
        "reason",
        "wrong-turn",
        "unknown-policy",
        "missing-arm",
        "duplicate-arm",
        "empty-unverified",
        "empty-without-control",
        "raw-path",
    ],
)
def test_d381_verdict_does_not_trust_skip_labels_or_summary(
    tmp_path: Path, corruption: str
) -> None:
    manifest = _d381_manifest(tmp_path)
    assert strict_five_verdict(manifest, "turn-1").passed
    data = json.loads(manifest.read_text())
    row = next(r for r in data["sources"] if r["source"] == "exa")
    overrides = {
        "primary-hash": {"attempts": [{**row["attempts"][0], "raw_sha256": "0" * 64}]},
        "bare": {"raw_file": None, "raw_sha256": None, "attempts": []},
        "items": {"items": [{"url": "https://fabricated.test"}]},
        "reason": {"skip_reason": "arbitrary-waiver"},
        "raw-path": {"raw_file": str(tmp_path / "exa.primary.raw")},
    }
    if corruption in overrides:
        row.update(overrides[corruption])
    elif corruption == "hash":
        (tmp_path / "exa.raw").write_bytes(b"altered")
    elif corruption == "auth-relabel":
        _d381_manifest(
            tmp_path,
            envelope={
                "http_status": 401,
                "rc": None,
                "body": "Insufficient credits",
                "stderr_redacted": "",
            },
        )
        data = json.loads(manifest.read_text())
    elif corruption == "wrong-turn":
        data["request_id"] = "other-turn"
    elif corruption == "unknown-policy":
        data["policy_version"] = "strict-five-v999"
    elif corruption == "missing-arm":
        data["sources"].pop()
    elif corruption == "duplicate-arm":
        data["sources"][-1] = data["sources"][0]
    else:
        sibling = data["sources"][0]
        sibling.update(
            status=(
                "empty_unverified"
                if corruption == "empty-unverified"
                else "empty_verified"
            ),
            items=[],
            control=None,
        )
    manifest.write_text(json.dumps(data))
    assert not strict_five_verdict(manifest, "turn-1").passed


@pytest.mark.parametrize("damage", ["count", "query"])
def test_d381_verified_empty_accepts_bound_positive_control_then_rejects_corruption(
    tmp_path: Path, damage: str
) -> None:
    manifest = _d381_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    row = next(r for r in data["sources"] if r["source"] == "github-releases")
    raw = tmp_path / "github-releases.raw"
    raw.write_bytes(b"[]")
    row.update(
        status="empty_verified",
        items=[],
        raw_sha256=hashlib.sha256(b"[]").hexdigest(),
        control={"query": "python/cpython", "count": 1},
    )
    manifest.write_text(json.dumps(data))
    verdict = strict_five_verdict(manifest, "turn-1")
    assert verdict.passed, verdict.reason
    assert verdict.provisional == ()
    row["control"][damage] = 0 if damage == "count" else ""
    manifest.write_text(json.dumps(data))
    verdict = strict_five_verdict(manifest, "turn-1")
    assert not verdict.passed
    assert "github-releases" in verdict.reason


@dataclass(frozen=True)
class _D381Refusal:
    source: str | None = None
    message: bytes = b"Insufficient credits"
    rc: int = 1
    http_status: int = 402
    inherited_exa: bool = True
    command: str | None = None


def _d381_command_response(argv: list[str]) -> tuple[str, bytes]:
    if argv[0] == "ctx7":
        return "context7", (
            b"Context7-compatible library ID: /owner/topic"
            if argv[1] == "library"
            else b"### Topic documentation\nSource: https://primary.test/docs\nExample"
        )
    if argv[0] == "firecrawl":
        return (
            "firecrawl-search",
            b'{"success":true,"data":{"web":[{"url":"https://primary.test"}]}}',
        )
    if argv[0] == "python3":
        return "last30days", (
            b'{"schema_version":"1.3","source_status":{"hackernews":"ok"},'
            b'"results":[{"url":"https://primary.test"}]}'
        )
    if "graphql" in argv:
        return (
            "github-discussions",
            b'{"data":{"search":{"nodes":[{"url":"https://primary.test"}]}}}',
        )
    if any("/releases" in arg for arg in argv):
        return (
            "github-releases",
            b'[{"html_url":"https://primary.test","name":"topic"}]',
        )
    return "github-issues", b'{"items":[{"html_url":"https://primary.test"}]}'


def _d381_produce(
    directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    refusal: _D381Refusal | None = None,
    exhausted_sources: tuple[str, ...] = (),
    extra: tuple[str, ...] = (),
) -> tuple[int, list[tuple[str, str]]]:
    """Use the real CLI/persistence with only process and HTTP doubles."""
    refusal = refusal or _D381Refusal()
    monkeypatch.setenv("EXA_API_KEY", "fixture-key")
    if not refusal.inherited_exa:
        monkeypatch.delenv("EXA_API_KEY")
    monkeypatch.setenv("GH_TOKEN", "fixture-key")
    monkeypatch.setenv("GITHUB_TOKEN", "fixture-key")
    script = directory / "last30days.py"
    script.write_text("# fixture; never executed\n")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    plan = directory / "plan.json"
    plan.write_text(
        '{"subqueries":[{"search_query":"topic","sources":["hackernews"]}]}'
    )
    calls: list[tuple[str, str]] = []

    def runner(
        argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        del timeout, env
        source, payload = _d381_command_response(argv)
        calls.append((source, "process"))
        if (
            source == refusal.source
            and (refusal.command is None or argv[1] == refusal.command)
        ) or source in exhausted_sources:
            return _completed(
                argv,
                refusal.rc,
                refusal.message if refusal.rc == 0 else b"",
                refusal.message if refusal.rc else b"",
            )
        return _completed(argv, 0, payload)

    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del params, body, headers, timeout
        source = {
            Endpoint.EXA_SEARCH: "exa",
            Endpoint.FIRECRAWL_DEVELOPER: "firecrawl-developer",
        }[endpoint]
        calls.append((source, "http"))
        if source == refusal.source or source in exhausted_sources:
            return refusal.http_status, refusal.message
        if source == "exa":
            return (
                200,
                b'{"requestId":"fixture","results":[{"url":"https://primary.test"}]}',
            )
        return 200, b'{"success":true,"results":[{"url":"https://primary.test"}]}'

    rc = main(
        [
            "topic",
            "--repo",
            "owner/repo",
            "--strict-five",
            "--request-id",
            "turn-1",
            "--last30days-plan",
            str(plan),
            "--out",
            str(directory / "out"),
            *extra,
        ],
        directory,
        runner=runner,
        http=http,
    )
    return rc, calls


def test_d381_offline_boundary_fixture_can_complete_all_eight_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    """A green control proves producer reds are not broken success fixtures."""
    del credit_env
    rc, calls = _d381_produce(tmp_path, monkeypatch)
    assert rc == 0
    rows = json.loads((tmp_path / "out/manifest.json").read_text())["sources"]
    assert {row["source"] for row in rows} == set(_D381_SOURCES)
    assert all(row["status"] == "ok" for row in rows)
    assert {name for name, _ in calls} == set(_D381_SOURCES)


def test_d381_all_eight_exhausted_producer_receipt_passes_stop_without_naming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    state = tmp_path / "state"
    base = {"session_id": "fixture", "turn_id": "turn-1"}
    codex_research_gate.handle(
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: research]\nResearch the fixture.",
        },
        state,
        repo_root=tmp_path,
    )
    stop: dict[str, object] = {
        **base,
        "hook_event_name": "Stop",
        "last_assistant_message": "Results are ready.",
    }
    assert codex_research_gate.handle(stop, state, repo_root=tmp_path)["decision"] == (
        "block"
    )
    output = state / "fixture/turn-1"
    rc, calls = _d381_produce(
        tmp_path,
        monkeypatch,
        exhausted_sources=_D381_SOURCES,
        extra=("--out", str(output)),
    )
    counts = {
        source: sum(name == source for name, _ in calls) for source in _D381_SOURCES
    }
    assert counts == dict.fromkeys(_D381_SOURCES, 1)
    assert rc == 0
    data = json.loads((output / "manifest.json").read_text())
    assert data["policy_version"] == _D381_POLICY
    assert data["disposition"] == "complete"
    assert set(data["skipped_sources"]) == set(_D381_SOURCES)
    assert data["failed_sources"] == []
    rows = data["sources"]
    assert len(rows) == len(_D381_SOURCES)
    assert {row["source"] for row in rows} == set(_D381_SOURCES)
    assert all(row["status"] == "skipped" for row in rows)
    assert all(row["provisional"] is False and row["items"] == [] for row in rows)
    assert all(row["status"] != "ok" for row in rows)
    verdict = strict_five_verdict(output / "manifest.json", "turn-1")
    assert verdict.passed, verdict.reason
    assert verdict.provisional == verdict.provisional_entries == ()
    assert codex_research_gate.handle(stop, state, repo_root=tmp_path) == {}
    (output / "exa.raw").write_bytes(b"altered")
    assert codex_research_gate.handle(stop, state, repo_root=tmp_path)["decision"] == (
        "block"
    )


@pytest.mark.parametrize("gap", ["auth401", "auth403", "missing-key", "missing-cli"])
def test_d381_producer_does_not_complete_with_auth_or_prerequisite_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, gap: str
) -> None:
    del credit_env
    if gap == "missing-cli":
        (tmp_path / "bin/ctx7").unlink()
    rc, _ = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal(
            source="exa" if gap.startswith("auth") else None,
            http_status=401 if gap == "auth401" else 403,
            message=b"Unauthorized",
            inherited_exa=gap != "missing-key",
        ),
    )
    assert rc == 1
    data = json.loads((tmp_path / "out/manifest.json").read_text())
    assert data["policy_version"] == _D381_POLICY
    assert data["disposition"] == "incomplete"
    assert ("context7" if gap == "missing-cli" else "exa") in data["failed_sources"]


@pytest.mark.parametrize("source", _D381_SOURCES)
def test_d381_producer_exhaustion_is_nonblocking_and_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, source: str
) -> None:
    del credit_env
    rc, calls = _d381_produce(tmp_path, monkeypatch, refusal=_D381Refusal(source))
    assert sum(name == source for name, _ in calls) == 1
    assert rc == 0
    data = json.loads((tmp_path / "out/manifest.json").read_text())
    assert data["policy_version"] == _D381_POLICY
    assert {r["source"] for r in data["sources"]} == set(_D381_SOURCES)
    row = next(r for r in data["sources"] if r["source"] == source)
    assert (row["status"], row["provisional"]) == ("skipped", False)
    assert row["items"] == []
    assert 0 < len(row["reason"]) <= _D381_REASON_CAP
    assert (data["disposition"], data["skipped_sources"], data["failed_sources"]) == (
        "complete",
        [source],
        [],
    )
    assert strict_five_verdict(tmp_path / "out/manifest.json", "turn-1").passed


def test_d381_context7_rc0_monthly_quota_does_not_run_empty_canary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    rc, calls = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal("context7", b"Monthly quota reached", 0),
    )
    assert [name for name, _ in calls].count("context7") == 1
    assert rc == 0
    row = json.loads((tmp_path / "out/manifest.json").read_text())["sources"][4]
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        "quota",
        False,
    )


def test_d381_context7_docs_rc0_quota_preserves_transport_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    rc, calls = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal("context7", b"Monthly quota reached", 0, command="docs"),
    )
    assert rc == 0
    assert [name for name, _ in calls].count("context7") == 2
    manifest = tmp_path / "out/manifest.json"
    row = json.loads(manifest.read_text())["sources"][4]
    assert (row["status"], row["skip_reason"], row["provisional"]) == (
        "skipped",
        "quota",
        False,
    )
    assert row["items"] == []
    assert json.loads(Path(row["raw_file"]).read_text())["rc"] == 0
    assert strict_five_verdict(manifest, "turn-1").passed


def test_d381_exhaustion_reason_is_bounded_without_fabricating_renewal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None
) -> None:
    del credit_env
    rc, _ = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal(
            "github-issues", b"Insufficient credits\n" + b"detail " * 1000
        ),
    )
    assert rc == 0
    data = json.loads((tmp_path / "out/manifest.json").read_text())
    row = next(r for r in data["sources"] if r["source"] == "github-issues")
    assert 0 < len(row["reason"]) <= _D381_REASON_CAP
    assert "\n" not in row["reason"]
    assert row.get("renewal_at") is None


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize("remaining", [0, None, 5])
@pytest.mark.usefixtures("credit_env")
def test_d381_preflight_minimizes_balance_evidence_and_skips_only_known_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source: str,
    remaining: int | None,
) -> None:
    """Selected additive CLI seam: --preflight-manifest, never an account call.

    research-preflight/v1 binds source, request, policy and hashed balance input.
    Only remaining/renewal_at may survive normalization. Unknown is not zero.
    """
    account_marker = "UNRELATED-ACCOUNT-FIELD-MUST-NOT-PERSIST"
    credential_marker = "CREDENTIAL-SENTINEL-MUST-NOT-PERSIST"
    extra_marker = "ARBITRARY-EXTRA-FIELD-MUST-NOT-PERSIST"
    raw = json.dumps(
        {
            "remaining": remaining,
            "renewal_at": _D381_RENEWAL,
            "account_email": account_marker,
            "account_id": account_marker,
            "billing": {"card": account_marker},
            "api_key": credential_marker,
            "authorization": credential_marker,
            "unrecognized": {"nested": [extra_marker, credential_marker]},
        }
    ).encode()
    proof = tmp_path / "balance-input.json"
    proof.write_bytes(raw)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(
        json.dumps(
            {
                "schema": "research-preflight/v1",
                "policy_version": _D381_POLICY,
                "request_id": "turn-1",
                "sources": [
                    {
                        "source": source,
                        "raw_file": str(proof),
                        "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
            }
        )
    )
    rc, calls = _d381_produce(
        tmp_path, monkeypatch, extra=("--preflight-manifest", str(preflight))
    )
    captured = capsys.readouterr()
    output = tmp_path / "out"
    emitted = [captured.out.encode(), captured.err.encode()]
    emitted.extend(path.read_bytes() for path in output.rglob("*") if path.is_file())
    for content in emitted:
        for forbidden in (
            account_marker,
            credential_marker,
            extra_marker,
            "account_email",
            "account_id",
            '"billing"',
            '"api_key"',
            '"authorization"',
            '"unrecognized"',
        ):
            assert forbidden.encode() not in content
    assert rc == 0
    assert any(name == source for name, _ in calls) is (remaining != 0)
    data = json.loads((output / "manifest.json").read_text())
    row = next(r for r in data["sources"] if r["source"] == source)
    assert row["status"] == ("skipped" if remaining == 0 else "ok")
    proof_metadata = row["preflight"]
    proof_bytes = Path(proof_metadata["raw_file"]).read_bytes()
    assert json.loads(proof_bytes) == {
        "schema": "research-preflight-proof/v1",
        "request_id": "turn-1",
        "source": source,
        "policy_version": _D381_POLICY,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "balances": {"remaining": remaining, "renewal_at": _D381_RENEWAL},
    }
    assert proof_metadata["raw_sha256"] == hashlib.sha256(proof_bytes).hexdigest()
    if remaining == 0:
        assert row["renewal_at"] == _D381_RENEWAL
        assert row["provisional"] is False
        assert row["raw_sha256"]
        assert row["raw_sha256"] != hashlib.sha256(raw).hexdigest()
        normalized = Path(row["raw_file"]).read_bytes()
        assert json.loads(normalized) == {
            "schema": "research-preflight-proof/v1",
            "request_id": "turn-1",
            "source": source,
            "policy_version": _D381_POLICY,
            "input_sha256": hashlib.sha256(raw).hexdigest(),
            "balances": {"remaining": 0, "renewal_at": _D381_RENEWAL},
        }
        assert row["raw_sha256"] == hashlib.sha256(normalized).hexdigest()
    assert strict_five_verdict(output / "manifest.json", "turn-1").passed


@pytest.mark.parametrize(
    "damage",
    [
        "hash",
        "turn",
        "source",
        "negative",
        "string",
        "policy",
        "schema",
        "duplicate-source",
        "false",
        "true",
        "renewal-type",
        "renewal-format",
    ],
)
def test_d381_invalid_preflight_cannot_waive_a_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    capsys: pytest.CaptureFixture[str],
    damage: str,
) -> None:
    del credit_env
    balances = {"negative": -1, "string": "0", "false": False, "true": True}
    balance: dict[str, object] = {"remaining": balances.get(damage, 0)}
    if damage.startswith("renewal-"):
        balance["renewal_at"] = (
            {"date": _D381_RENEWAL} if damage == "renewal-type" else "not-a-date"
        )
    raw = json.dumps(balance).encode()
    proof = tmp_path / "balance-input.json"
    proof.write_bytes(raw)
    preflight = tmp_path / "preflight.json"
    row = {
        "source": "invented" if damage == "source" else "exa",
        "raw_file": str(proof),
        "raw_sha256": "0" * 64 if damage == "hash" else hashlib.sha256(raw).hexdigest(),
    }
    preflight.write_text(
        json.dumps(
            {
                "schema": "research-preflight/v999"
                if damage == "schema"
                else "research-preflight/v1",
                "policy_version": "strict-five-v2"
                if damage == "policy"
                else _D381_POLICY,
                "request_id": "wrong-turn" if damage == "turn" else "turn-1",
                "sources": [row, dict(row)] if damage == "duplicate-source" else [row],
            }
        )
    )
    rc, _ = _d381_produce(
        tmp_path, monkeypatch, extra=("--preflight-manifest", str(preflight))
    )
    # A malformed preflight is usage/prerequisite failure, never completion.
    assert rc in {1, 2}
    assert "unrecognized arguments" not in capsys.readouterr().err
    manifest = tmp_path / "out/manifest.json"
    assert not manifest.exists() or not strict_five_verdict(manifest, "turn-1").passed


@pytest.mark.parametrize("damage", [None, "hash", "turn", "stale", "auth"])
def test_d381_probe_projects_only_validated_fresh_exhaustion_as_nonblocking(
    tmp_path: Path, damage: str | None
) -> None:
    manifest = _d381_manifest(tmp_path)
    if damage == "hash":
        (tmp_path / "exa.raw").write_bytes(b"altered")
    elif damage == "auth":
        _d381_manifest(
            tmp_path,
            envelope={
                "http_status": 401,
                "rc": None,
                "body": "",
                "stderr_redacted": "",
            },
            code="auth-failed",
        )
    elif damage in {"turn", "stale"}:
        data = json.loads(manifest.read_text())
        data["request_id" if damage == "turn" else "generated_at"] = (
            "other-turn" if damage == "turn" else "2025-01-01T00:00:00+00:00"
        )
        manifest.write_text(json.dumps(data))
    output = tmp_path / "probe.json"
    assert (
        main(
            [
                "--probe-out",
                str(output),
                "--fanout-manifest",
                str(manifest),
                "--require",
                "exa",
                "--expect-request-id",
                "turn-1",
                "--max-age",
                "60",
            ],
            tmp_path,
            runner=_unused_runner,
            timing=ProbeTiming(lambda _: None, _D381_NOW.timestamp),
        )
        == 0
    )
    row = json.loads(output.read_text())["probes"][0]
    if damage is None:
        assert row["required_failed"] == []
        assert row["provisional"] == []
        assert row["fresh"] is True
        assert row["sources"]["exa"] == "skipped"
    elif damage in {"turn", "stale"}:
        assert row["fresh"] is False
    else:
        assert row["required_failed"]


@pytest.mark.parametrize(
    "policy", ["strict-five-v999", "strict-five-v2", None, "missing"]
)
@pytest.mark.parametrize("require", [False, True])
def test_d381_probe_unknown_explicit_policy_is_mandatory_gap(
    tmp_path: Path, policy: str | None, *, require: bool
) -> None:
    manifest = _d381_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    if policy == "missing":
        data.pop("policy_version")
    else:
        data["policy_version"] = policy
    manifest.write_text(json.dumps(data))
    output = tmp_path / "probe.json"
    assert (
        main(
            [
                "--probe-out",
                str(output),
                "--fanout-manifest",
                str(manifest),
                *(["--require", "exa"] if require else []),
            ],
            tmp_path,
            runner=_unused_runner,
            timing=ProbeTiming(lambda _: None, _D381_NOW.timestamp),
        )
        == 0
    )
    row = json.loads(output.read_text())["probes"][0]
    assert row["fresh"] is True
    if policy == "missing":
        assert "policy_version" not in row
    if policy not in {"strict-five-v2", "missing"}:
        assert row["required_failed"]
        assert row["disposition"] == "incomplete"
        assert row["skipped_sources"] == []
        assert row["failed_sources"]
    elif require:
        assert row["required_failed"] == ["exa: skipped (credits-exhausted)"]
    else:
        assert row["required_failed"] == []


@pytest.mark.parametrize(
    "outcome", ["credit-alternative-ok", "credit-alternative-fails", "auth"]
)
def test_d381_mirror_retains_route_and_genuine_failure_without_credit_provisional(
    tmp_path: Path, outcome: str
) -> None:
    url = "https://primary.test/docs"
    responses = [
        _completed(
            [],
            1,
            stderr=(
                b"HTTP 401 Unauthorized"
                if outcome == "auth"
                else b"Insufficient credits"
            ),
        )
    ]
    if outcome != "auth":
        responses.append(
            _completed(
                [],
                1 if outcome.endswith("fails") else 0,
                json.dumps(
                    {
                        "metadata": {"url": url},
                        "content": {"markdown": "# Primary documentation"},
                    }
                ).encode(),
            )
        )
    runner = ScriptedRunner(responses)
    output, mirror = tmp_path / "probe.json", tmp_path / "mirror.md"
    assert (
        main(
            [
                "--probe-out",
                str(output),
                "--mirror-url",
                url,
                "--mirror-path",
                str(mirror),
            ],
            tmp_path,
            runner=runner,
        )
        == 0
    )
    row = json.loads(output.read_text())["probes"][0]
    assert row["provisional"] is False
    if outcome == "credit-alternative-ok":
        assert (row["route"], row["rc"]) == ("webclaw", 0)
        assert mirror.read_text() == "# Primary documentation"
    elif outcome == "credit-alternative-fails":
        assert row["rc"] != 0
        assert row["code"]
    else:
        assert (row["route"], row["rc"]) == ("firecrawl", 1)
        assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "gap", ["primary-auth", "primary-missing-cli", "fallback-auth"]
)
def test_d381_successful_substitute_cannot_erase_an_incomplete_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit_env: None, gap: str
) -> None:
    del credit_env
    monkeypatch.setenv("SERPER_API_KEY", "serper-fixture")
    monkeypatch.setenv("SERP_API_KEY", "serpapi-fixture")
    if gap == "primary-missing-cli":
        (tmp_path / "bin/firecrawl").unlink()
    refusal = (
        b"HTTP 401 Unauthorized" if gap == "primary-auth" else b"Insufficient credits"
    )
    runner = ScriptedRunner([_completed([], 1, stderr=refusal)])

    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del params, body, headers, timeout
        if endpoint is Endpoint.SERPER_SEARCH:
            return (
                (401, b"Unauthorized")
                if gap == "fallback-auth"
                else (200, b'{"organic":[{"link":"https://primary.test"}]}')
            )
        assert endpoint is Endpoint.SERPAPI_SEARCH
        return 200, b'{"organic_results":[{"link":"https://primary.test"}]}'

    main(
        ["topic", "--sources", "firecrawl-search", "--out", str(tmp_path)],
        tmp_path,
        runner=runner,
        http=http,
    )
    row = _only_row(tmp_path)
    manifest = _merge_credit_manifest(tmp_path, row)
    data = json.loads(manifest.read_text())
    data["policy_version"] = _D381_POLICY
    for candidate in data["sources"]:
        candidate["provisional"] = False
    manifest.write_text(json.dumps(data))
    verdict = strict_five_verdict(manifest, "turn-1")
    assert not verdict.passed
    assert "firecrawl-search" in verdict.reason


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize("refusal", ["transient429", "auth-credit-decoy"])
def test_d381_unknown_limit_and_auth_credit_decoy_remain_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    source: str,
    refusal: str,
) -> None:
    del credit_env
    message = (
        b"HTTP 429 Too Many Requests"
        if refusal == "transient429"
        else b"HTTP 401 Unauthorized Insufficient credits"
    )
    status = 429 if refusal == "transient429" else 401
    rc, calls = _d381_produce(
        tmp_path, monkeypatch, refusal=_D381Refusal(source, message, 1, status)
    )
    assert rc == 1
    assert sum(name == source for name, _ in calls) == 1
    data = json.loads((tmp_path / "out/manifest.json").read_text())
    assert source in data["failed_sources"]
    assert source not in data["skipped_sources"]
    assert data["disposition"] == "incomplete"


def test_d381_intentional_v2_path_keeps_historical_provisional(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
) -> None:
    del credit_env
    exhausted = ("exa", "context7", "firecrawl-developer", "firecrawl-search")
    rc, _ = _d381_produce(
        tmp_path,
        monkeypatch,
        exhausted_sources=exhausted,
        extra=("--policy-version", "strict-five-v2"),
    )
    assert rc == 0
    data = json.loads((tmp_path / "out/manifest.json").read_text())
    assert data["policy_version"] == "strict-five-v2"
    verdict = strict_five_verdict(tmp_path / "out/manifest.json", "turn-1")
    assert verdict.passed
    assert len(verdict.provisional_entries) == 4


def test_d381_successful_receipt_cannot_hide_prior_failure_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
) -> None:
    del credit_env
    rc, _ = _d381_produce(tmp_path, monkeypatch)
    assert rc == 0
    path = tmp_path / "out/manifest.json"
    assert strict_five_verdict(path, "turn-1").passed
    data = json.loads(path.read_text())
    data["sources"][0]["attempts"] = [{"route": "github-issues", "status": "error"}]
    path.write_text(json.dumps(data))
    assert not strict_five_verdict(path, "turn-1").passed


@pytest.mark.parametrize("malformed", [{}, {"exa": {}}, ["exa"]])
def test_d381_malformed_current_policy_probe_is_explicit_gap(
    tmp_path: Path,
    malformed: object,
) -> None:
    path = _d381_manifest(tmp_path)
    data = json.loads(path.read_text())
    data["sources"] = malformed
    path.write_text(json.dumps(data))
    target = tmp_path / "probe.json"
    assert (
        main(
            ["--probe-out", str(target), "--fanout-manifest", str(path)],
            tmp_path,
            runner=_unused_runner,
        )
        == 0
    )
    row = json.loads(target.read_text())["probes"][0]
    assert row["disposition"] == "incomplete"
    assert row["required_failed"]
    assert row["skipped_sources"] == []


def _d381_security_preflight(directory: Path, remaining: int | None = 0) -> Path:
    raw = (
        b'{"remaining": null}'
        if remaining is None
        else json.dumps({"remaining": remaining}).encode()
    )
    balance = directory / "balance-input.json"
    balance.write_bytes(raw)
    path = directory / "preflight.json"
    path.write_text(
        json.dumps(
            {
                "schema": "research-preflight/v1",
                "request_id": "turn-1",
                "policy_version": _D381_POLICY,
                "sources": [
                    {
                        "source": "exa",
                        "raw_file": str(balance),
                        "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
            }
        )
    )
    return path


@pytest.mark.parametrize("remaining", [0, None, 5])
@pytest.mark.parametrize(
    "damage",
    [
        "request_id",
        "source",
        "policy_version",
        "input_sha256",
        "schema",
        "missing-request_id",
        "missing-source",
        "missing-policy_version",
        "missing-input_sha256",
        "receipt-relabel",
        "proof-hash",
        "proof-binding",
        "proof-extra",
        "proof-missing-binding",
    ],
)
def test_d381_security_preflight_retains_and_revalidates_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    credit_env: None,
    remaining: int | None,
    damage: str,
) -> None:
    del credit_env
    preflight = _d381_security_preflight(tmp_path, remaining)
    rc, _ = _d381_produce(
        tmp_path, monkeypatch, extra=("--preflight-manifest", str(preflight))
    )
    assert rc == 0
    manifest = tmp_path / "out/manifest.json"
    assert strict_five_verdict(manifest, "turn-1").passed
    data = json.loads(manifest.read_bytes())
    row = next(row for row in data["sources"] if row["source"] == "exa")
    metadata = row["preflight"]
    request_id = "turn-1"
    if damage.startswith("missing-"):
        metadata.pop(damage.removeprefix("missing-"), None)
    elif damage == "receipt-relabel":
        request_id = "relabelled-turn"
        data["request_id"] = request_id
    elif damage == "proof-hash":
        Path(metadata["raw_file"]).write_bytes(b'{"remaining": 0}')
    elif damage.startswith("proof-"):
        proof_path = Path(metadata["raw_file"])
        proof = json.loads(proof_path.read_bytes())
        if damage == "proof-binding":
            proof["request_id"] = "prior-turn"
        elif damage == "proof-missing-binding":
            proof.pop("request_id", None)
        else:
            proof["unexpected"] = "FAKE-EXTRA"
        raw = json.dumps(proof).encode()
        proof_path.write_bytes(raw)
        metadata["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        if remaining == 0:
            for key in ("raw_file",):
                Path(row[key]).write_bytes(raw)
            Path(row["attempts"][0]["raw_file"]).write_bytes(raw)
            row["raw_sha256"] = row["attempts"][0]["raw_sha256"] = metadata[
                "raw_sha256"
            ]
    else:
        metadata[damage] = "0" * 64 if damage == "input_sha256" else "wrong-binding"
    manifest.write_text(json.dumps(data))
    assert not strict_five_verdict(manifest, request_id).passed


_D381_SECURITY_FAILURES = [
    (1, b"Authentication failed: invalid API key. Insufficient credits."),
    (124, b"Timed out; Monthly quota reached"),
    (127, b"command not found; Monthly quota reached"),
    (126, b"Permission denied; Insufficient credits"),
    (1, b"Missing prerequisite; Monthly quota reached"),
    (1, b"Connection refused; Insufficient credits"),
]


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize(("rc", "message"), _D381_SECURITY_FAILURES)
def test_d381_security_verdict_route_failure_precedes_credit_prose(
    tmp_path: Path, source: str, rc: int, message: bytes
) -> None:
    manifest = _d381_manifest(tmp_path, source)
    assert strict_five_verdict(manifest, "turn-1").passed
    for envelope_key in ("body", "stderr_redacted"):
        envelope: dict[str, object] = {
            "http_status": None,
            "rc": rc,
            "body": "",
            "stderr_redacted": "",
        }
        envelope[envelope_key] = message.decode()
        manifest = _d381_manifest(
            tmp_path,
            source,
            envelope=envelope,
            code="quota" if b"quota" in message else "credits-exhausted",
        )
        assert not strict_five_verdict(manifest, "turn-1").passed


@pytest.mark.usefixtures("credit_env")
@pytest.mark.parametrize(
    "source", [s for s in _D381_SOURCES if s not in {"exa", "firecrawl-developer"}]
)
@pytest.mark.parametrize(("rc", "message"), _D381_SECURITY_FAILURES)
def test_d381_security_producer_route_failure_precedes_credit_prose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    rc: int,
    message: bytes,
) -> None:
    result, calls = _d381_produce(
        tmp_path, monkeypatch, refusal=_D381Refusal(source, rc=rc, message=message)
    )
    assert result == 1
    assert sum(name == source for name, _ in calls) == 1
    data = json.loads((tmp_path / "out/manifest.json").read_bytes())
    assert source in data["failed_sources"]
    assert data["disposition"] == "incomplete"
    assert not strict_five_verdict(tmp_path / "out/manifest.json", "turn-1").passed


_D381_MISSING_CREDENTIALS = [
    "Missing API key",
    "API key is missing",
    "Unset API-key",
    "API-key is unset",
    "Absent API_key",
    "API_key is absent",
    "Required API key",
    "API key is required",
    "Missing credential",
    "Credential is missing",
    "Unset credentials",
    "Credentials are unset",
    "Absent credentials",
    "Credentials are absent",
    "Required credentials",
    "Credentials are required",
    "Missing EXA_API_KEY",
    "FIRECRAWL_API_KEY is required",
    "No API key provided",
    "API key not set",
    "API key not found",
    "Credentials not configured",
    "API key failure",
    "Credential error",
]


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize("credential_failure", _D381_MISSING_CREDENTIALS)
@pytest.mark.parametrize(
    "scenario",
    [
        ("Monthly quota reached", True),
        ("Monthly quota reached", False),
        ("Insufficient credits", True),
        ("Insufficient credits", False),
    ],
)
def test_d381_missing_key_verdict_precedes_exhaustion_prose(
    tmp_path: Path,
    source: str,
    credential_failure: str,
    scenario: tuple[str, bool],
) -> None:
    exhaustion, failure_first = scenario
    manifest = _d381_manifest(tmp_path, source)
    assert strict_five_verdict(manifest, "turn-1").passed
    message = (
        f"{credential_failure}; {exhaustion}"
        if failure_first
        else f"{exhaustion}; {credential_failure}"
    )
    for envelope_key in ("body", "stderr_redacted"):
        envelope: dict[str, object] = {
            "http_status": None,
            "rc": 1,
            "body": "",
            "stderr_redacted": "",
        }
        envelope[envelope_key] = message
        manifest = _d381_manifest(
            tmp_path,
            source,
            envelope=envelope,
            code="quota"
            if exhaustion == "Monthly quota reached"
            else "credits-exhausted",
        )
        assert not strict_five_verdict(manifest, "turn-1").passed


@pytest.mark.usefixtures("credit_env")
@pytest.mark.parametrize(
    "source", [s for s in _D381_SOURCES if s not in {"exa", "firecrawl-developer"}]
)
@pytest.mark.parametrize("credential_failure", _D381_MISSING_CREDENTIALS)
@pytest.mark.parametrize(
    "scenario",
    [
        ("Monthly quota reached", True),
        ("Monthly quota reached", False),
        ("Insufficient credits", True),
        ("Insufficient credits", False),
    ],
)
def test_d381_missing_key_producer_precedes_exhaustion_prose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    credential_failure: str,
    scenario: tuple[str, bool],
) -> None:
    exhaustion, failure_first = scenario
    message = (
        f"{credential_failure}; {exhaustion}"
        if failure_first
        else f"{exhaustion}; {credential_failure}"
    ).encode()
    rc, calls = _d381_produce(
        tmp_path, monkeypatch, refusal=_D381Refusal(source, rc=1, message=message)
    )
    assert rc == 1
    assert sum(name == source for name, _ in calls) == 1
    manifest = tmp_path / "out/manifest.json"
    data = json.loads(manifest.read_bytes())
    assert source in data["failed_sources"]
    assert data["disposition"] == "incomplete"
    assert not strict_five_verdict(manifest, "turn-1").passed


def _d381_security_damage_file(path: Path, damage: str) -> None:
    if damage == "oversize":
        with path.open("ab") as handle:
            handle.write(b" " * (8 * 1024 * 1024 + 1))
        return
    original = path.with_suffix(".original")
    path.rename(original)
    if damage == "fifo":
        os.mkfifo(path)
    elif damage == "directory":
        path.mkdir()
    else:
        path.symlink_to(original)


@pytest.mark.parametrize(
    "damage",
    [
        "manifest-fifo",
        "manifest-symlink",
        "manifest-directory",
        "manifest-oversize",
        "raw-fifo",
        "raw-symlink",
        "raw-directory",
        "raw-oversize",
        "raw-relative-escape",
        "raw-absolute-escape",
        "raw-parent-symlink",
    ],
)
def test_d381_security_preflight_safe_bounded_file_admission(
    tmp_path: Path,
    damage: str,
) -> None:
    admitted = tmp_path / "admitted"
    admitted.mkdir()
    manifest = _d381_security_preflight(admitted)
    data = json.loads(manifest.read_bytes())
    raw = admitted / "balance-input.json"
    if damage.startswith("manifest-"):
        _d381_security_damage_file(manifest, damage.removeprefix("manifest-"))
    elif damage in {"raw-oversize", "raw-fifo", "raw-directory", "raw-symlink"}:
        _d381_security_damage_file(raw, damage.removeprefix("raw-"))
    else:
        outside = tmp_path / "fake-outside.json"
        outside.write_bytes(raw.read_bytes())
        if damage == "raw-relative-escape":
            data["sources"][0]["raw_file"] = "../fake-outside.json"
        elif damage == "raw-absolute-escape":
            data["sources"][0]["raw_file"] = str(outside)
        else:
            link = admitted / "parent-link"
            link.symlink_to(tmp_path, target_is_directory=True)
            data["sources"][0]["raw_file"] = str(link / outside.name)
        manifest.write_text(json.dumps(data))
    # A subprocess timeout bounds the unfixed FIFO reader without leaving a thread.
    script = """
import sys
from pathlib import Path
from dotfiles_setup.research_fanout import main

def forbidden(*args, **kwargs):
    raise AssertionError('FAKE-ROUTE-MUST-NOT-RUN')

raise SystemExit(main(sys.argv[1:], Path.cwd(), runner=forbidden, http=forbidden))
"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                script,
                "topic",
                "--repo",
                "owner/repo",
                "--sources",
                "exa",
                "--policy-version",
                _D381_POLICY,
                "--request-id",
                "turn-1",
                "--preflight-manifest",
                str(manifest),
                "--out",
                str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("preflight file admission blocked")
    assert result.returncode == 2
    assert result.stdout == ""
    assert (
        result.stderr
        == "research-fanout: invalid preflight manifest or balance evidence\n"
    )
    assert not (tmp_path / "out").exists()


_REPAIR_FAILURES = (
    None,
    "Invalid API key",
    "Missing API key",
    "Connection refused",
    "Permission denied",
    "command not found",
)


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize("http_status", [None, 200, 401, 402, 429])
@pytest.mark.parametrize("failure", _REPAIR_FAILURES)
@pytest.mark.parametrize("channel", ["body", "stderr_redacted"])
def test_d381_repair_status_axis_cannot_waive_failure_at_verdict_and_stop(
    tmp_path: Path,
    source: str,
    http_status: int | None,
    failure: str | None,
    channel: str,
) -> None:
    state = tmp_path / "state"
    event = {"session_id": "fixture", "turn_id": "turn-1"}
    codex_research_gate.handle(
        {
            **event,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: research]\nResearch the fixture.",
        },
        state,
        repo_root=tmp_path,
    )
    directory = state / "fixture/turn-1"
    exhaustion = (
        "Insufficient credits" if http_status == 402 else "Monthly quota reached"
    )
    envelope: dict[str, object] = {
        "http_status": http_status,
        "rc": 1 if http_status is None else None,
        "body": "",
        "stderr_redacted": "",
    }
    envelope[channel] = f"{failure}; {exhaustion}" if failure else exhaustion
    manifest = _d381_manifest(
        directory,
        source,
        envelope=envelope,
        code="credits-exhausted" if http_status == 402 else "quota",
    )
    expected = failure is None and http_status in (None, 402, 429)
    verdict = strict_five_verdict(manifest, "turn-1")
    assert verdict.passed is expected
    stopped = codex_research_gate.handle(
        {
            **event,
            "hook_event_name": "Stop",
            "last_assistant_message": "Results ready.",
        },
        state,
        repo_root=tmp_path,
    )
    assert (stopped.get("decision") != "block") is expected
    assert verdict.provisional == ()


@pytest.mark.parametrize("source", ["exa", "firecrawl-developer"])
@pytest.mark.parametrize("failure", _REPAIR_FAILURES)
@pytest.mark.parametrize(
    "scenario",
    [(status, quota) for status in (200, 401, 402, 429) for quota in (False, True)],
)
@pytest.mark.usefixtures("credit_env")
def test_d381_repair_status_axis_producer_keeps_refusals_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    failure: str | None,
    scenario: tuple[int, bool],
) -> None:
    http_status, quota = scenario
    exhaustion = (
        "Insufficient credits" if http_status == 402 else "Monthly quota reached"
    )
    message = "; ".join(
        part for part in (failure, exhaustion if quota else None) if part
    )
    rc, _ = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal(source, message.encode(), 1, http_status),
    )
    expected = failure is None and (
        http_status == 402 or (http_status == 429 and quota)
    )
    manifest = json.loads((tmp_path / "out/manifest.json").read_bytes())
    row = next(row for row in manifest["sources"] if row["source"] == source)
    assert rc == (0 if expected else 1)
    assert row["status"] == ("skipped" if expected else "error")
    assert (source in manifest["failed_sources"]) is (not expected)
    assert (source in manifest["skipped_sources"]) is expected


@pytest.mark.parametrize("outcome", ["success", "exhausted"])
def test_d381_repair_nonstrict_no_repo_projects_and_imports_real_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    monkeypatch.setenv("EXA_API_KEY", "fixture-key")

    def http(
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        del endpoint, params, body, headers, timeout
        return (
            (429, b"Monthly quota reached")
            if outcome == "exhausted"
            else (
                200,
                b'{"requestId":"fixture","results":[{"url":"https://primary.test"}]}',
            )
        )

    output = tmp_path / "output"
    assert (
        main(
            [
                "topic",
                "--sources",
                "exa",
                "--policy-version",
                _D381_POLICY,
                "--out",
                str(output),
            ],
            tmp_path,
            runner=_unused_runner,
            http=http,
        )
        == 0
    )
    manifest = output / "manifest.json"
    probe = tmp_path / "probe.json"
    assert (
        main(
            ["--probe-out", str(probe), "--fanout-manifest", str(manifest)],
            tmp_path,
            runner=_unused_runner,
        )
        == 0
    )
    row = json.loads(probe.read_bytes())["probes"][0]
    assert row["disposition"] == "complete"
    assert row["required_failed"] == []
    assert row["skipped_sources"] == (["exa"] if outcome == "exhausted" else [])
    capsys.readouterr()
    # Exa is intentionally not a GitHub watch; valid ignored input is not missing input.
    assert (
        record_saved_searches(
            [
                "record",
                "--fanout-manifest",
                str(manifest),
                "--out",
                str(tmp_path / "saved.toml"),
            ],
            tmp_path,
        )
        == 1
    )
    line = next(
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("SAVED-SEARCH-JSON ")
    )
    receipt = json.loads(line.removeprefix("SAVED-SEARCH-JSON "))
    assert receipt["missing"] == []
    assert receipt["reason"] == "no watches"
    assert receipt["skipped_sources"] == 1


@pytest.mark.parametrize(
    "source", ["github-issues", "github-discussions", "github-releases"]
)
def test_d381_repair_missing_repo_still_refuses_github_manifest(
    tmp_path: Path,
    source: str,
) -> None:
    manifest = _d381_manifest(tmp_path, source)
    data = json.loads(manifest.read_bytes())
    data["repo"] = None
    manifest.write_text(json.dumps(data))
    assert not strict_five_verdict(manifest, "turn-1").passed
    data.update(
        strict_five=False,
        sources=[row for row in data["sources"] if row["source"] == source],
    )
    manifest.write_text(json.dumps(data))
    probe = tmp_path / "probe.json"
    assert (
        main(
            ["--probe-out", str(probe), "--fanout-manifest", str(manifest)],
            tmp_path,
            runner=_unused_runner,
        )
        == 0
    )
    assert json.loads(probe.read_bytes())["probes"][0]["disposition"] == "incomplete"


@pytest.mark.parametrize("kind", ["canonical", "leaf", "parent", "ancestor"])
def test_d381_repair_preflight_never_follows_any_manifest_component(
    tmp_path: Path,
    kind: str,
) -> None:
    admitted = tmp_path / "admitted"
    admitted.mkdir()
    nested = admitted / "nested"
    nested.mkdir()
    manifest = _d381_security_preflight(nested)
    data = json.loads(manifest.read_bytes())
    data["sources"][0]["raw_file"] = "balance-input.json"
    manifest.write_text(json.dumps(data))
    if kind == "leaf":
        alias = nested / "manifest-link.json"
        alias.symlink_to(manifest)
        manifest = alias
    elif kind == "parent":
        alias = admitted / "parent-link"
        alias.symlink_to(nested, target_is_directory=True)
        manifest = alias / manifest.name
    elif kind == "ancestor":
        alias = tmp_path / "ancestor-link"
        alias.symlink_to(admitted, target_is_directory=True)
        manifest = alias / "nested" / manifest.name
    output = tmp_path / "output"
    rc = main(
        [
            "topic",
            "--sources",
            "exa",
            "--policy-version",
            _D381_POLICY,
            "--request-id",
            "turn-1",
            "--preflight-manifest",
            str(manifest),
            "--out",
            str(output),
        ],
        tmp_path,
        runner=_unused_runner,
    )
    assert rc == (0 if kind == "canonical" else 2)
    assert output.exists() is (kind == "canonical")


_REPAIR2_CREDENTIAL_REFUSALS = (
    None,
    "API key is invalid",
    "API key has expired",
    "API key invalid",
    "API key is expired",
    "API key was revoked",
    "API key has been revoked",
    "API key is not valid",
    "API key is no longer valid",
    "Invalid API key",
    "Expired API key",
    "Revoked API key",
    "Invalid API-key",
    "API_key has expired",
    "EXA_API_KEY is invalid",
    "EXA_API_KEY has been revoked",
    "Credentials are invalid",
    "Credentials have expired",
    "Credential was revoked",
    "Invalid credentials",
    "Expired credentials",
    "Revoked credentials",
    "Token is invalid",
    "Token has expired",
    "Token has been revoked",
    "Invalid token",
    "Expired token",
    "Revoked token",
    "Access token is invalid",
    "Access token has expired",
    "Access token was revoked",
    "Invalid access token",
    "Expired access token",
    "Revoked access token",
    "Authentication is invalid",
    "Authentication has expired",
    "Authentication was revoked",
    "Invalid authentication",
    "Expired authorization",
    "Authorization has been revoked",
    "Auth is invalid",
    "Bearer token is invalid",
    "Refresh token has expired",
)


@pytest.mark.usefixtures("credit_env")
@pytest.mark.parametrize("source", ["exa", "firecrawl-developer"])
@pytest.mark.parametrize("failure", _REPAIR2_CREDENTIAL_REFUSALS)
@pytest.mark.parametrize(
    "scenario",
    [(status, first) for status in (401, 402, 429) for first in (False, True)],
)
def test_d381_repair2_explicit_credential_refusal_never_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    failure: str | None,
    scenario: tuple[int, bool],
) -> None:
    status, failure_first = scenario
    exhaustion = "Insufficient credits" if status == 402 else "Monthly quota reached"
    text = (
        exhaustion
        if failure is None
        else (
            f"{failure}; {exhaustion}" if failure_first else f"{exhaustion}; {failure}"
        )
    )
    state = tmp_path / "state"
    event = {"session_id": "fixture", "turn_id": "turn-1"}
    codex_research_gate.handle(
        {
            **event,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "[research-scope: research]\nResearch the fixture.",
        },
        state,
        repo_root=tmp_path,
    )
    output = state / "fixture/turn-1"
    rc, _ = _d381_produce(
        tmp_path,
        monkeypatch,
        refusal=_D381Refusal(source, text.encode(), 1, status),
        extra=("--out", str(output)),
    )
    manifest = output / "manifest.json"
    data = json.loads(manifest.read_bytes())
    row = next(row for row in data["sources"] if row["source"] == source)
    verdict = strict_five_verdict(manifest, "turn-1")
    stop = codex_research_gate.handle(
        {
            **event,
            "hook_event_name": "Stop",
            "last_assistant_message": "Results ready.",
        },
        state,
        repo_root=tmp_path,
    )
    allowed = failure is None and status in (402, 429)
    assert (
        rc,
        row["status"],
        data["disposition"],
        verdict.passed,
        stop.get("decision"),
    ) == (
        (0, "skipped", "complete", True, None)
        if allowed
        else (1, "error", "incomplete", False, "block")
    )
    assert row["provisional"] is False
    assert verdict.provisional == ()


@pytest.mark.parametrize("source", _D381_SOURCES)
@pytest.mark.parametrize("status", [None, 402, 429])
@pytest.mark.parametrize("failure", ["API key is invalid", "API key has expired"])
@pytest.mark.parametrize("channel", ["body", "stderr_redacted"])
def test_d381_repair2_saved_skip_rederives_suffix_refusal_for_every_arm(
    tmp_path: Path,
    source: str,
    status: int | None,
    failure: str,
    channel: str,
) -> None:
    envelope: dict[str, object] = {
        "http_status": status,
        "rc": 1 if status is None else None,
        "body": "",
        "stderr_redacted": "",
    }
    envelope[channel] = f"{failure}; Monthly quota reached"
    manifest = _d381_manifest(
        tmp_path,
        source,
        envelope=envelope,
        code="credits-exhausted" if status == 402 else "quota",
    )
    assert not strict_five_verdict(manifest, "turn-1").passed


@pytest.mark.usefixtures("credit_env")
@pytest.mark.parametrize("status", [402, 429])
@pytest.mark.parametrize(
    "code",
    [
        "quota_exhausted",
        "invalid_api_key",
        "api_key_expired",
        "revoked_access_token",
        "authentication_invalid",
    ],
)
def test_d381_repair2_structured_credential_error_is_not_a_quota_waiver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    code: str,
) -> None:
    raw = json.dumps(
        {"success": False, "error": {"code": code, "message": "Monthly quota reached"}}
    ).encode()
    rc, _ = _d381_produce(
        tmp_path, monkeypatch, refusal=_D381Refusal("exa", raw, 1, status)
    )
    path = tmp_path / "out/manifest.json"
    verdict = strict_five_verdict(path, "turn-1")
    data = json.loads(path.read_bytes())
    assert (rc, data["disposition"], verdict.passed) == (
        (0, "complete", True) if code == "quota_exhausted" else (1, "incomplete", False)
    )
