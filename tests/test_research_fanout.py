# Copyright (c) 2026 Raymond Manaloto
"""Tests for the no-LLM multi-source research fetcher."""

from __future__ import annotations

import http.client
import json
import os
import signal
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_fanout import (
    Endpoint,
    FanoutRequest,
    Status,
    default_http,
    default_runner,
    fan_out,
    main,
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
        query = str(payload["query"])
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


def test_http_timeout_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
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

    assert result.status is Status.ERROR
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

    assert result.status is Status.ERROR
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

    assert result.status is Status.ERROR
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
    assert "first line | second line | third" in lines[1]


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
    started = time.monotonic()
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            default_runner(
                [sys.executable, "-c", parent, str(pid_file), descendant],
                timeout=0.2,
                env={},
            )
        elapsed = time.monotonic() - started
        detached_pid = int(pid_file.read_text())

        assert elapsed <= 3.2
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
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))

    def interrupt_when_child_runs() -> None:
        deadline = time.monotonic() + 3.0
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        os.kill(os.getpid(), signal.SIGINT)

    interruptor = threading.Thread(target=interrupt_when_child_runs)
    started = time.monotonic()
    interruptor.start()
    try:
        rc = main(
            ["topic", "--sources", "last30days", "--timeout", "10"],
            tmp_path,
            runner=default_runner,
            http=FakeHttp({}),
        )
        elapsed = time.monotonic() - started
        assert pid_file.is_file()
        child_pid = int(pid_file.read_text())

        assert rc == 130
        assert elapsed <= 3.0
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
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
        ("exa", Status.SKIPPED, "needs EXA_API_KEY"),
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
