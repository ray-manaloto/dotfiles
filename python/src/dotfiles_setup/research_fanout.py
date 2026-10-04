# Copyright (c) 2026 Raymond Manaloto
"""Fetch research evidence concurrently without spending harness LLM tokens.

The default source set is deliberately mechanical: HTTPS APIs and local CLIs
return raw evidence, while a later Claude or Codex workflow decides what it
means. Empty answers carry a same-source control so absence is never confused
with a broken transport.

``last30days`` is opt-in because its ``pass`` password-store source has no
documented off-switch. Even though this module strips LLM-provider variables,
disables its dotenv file, and disables macOS Keychain lookup, an LLM key stored
in ``pass`` can still enable that plugin's internal planner. The default source
set therefore remains no-LLM; an explicit ``last30days`` request has this known
limit.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.client as http_client
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Never, Protocol

from dotfiles_setup import child_env

if TYPE_CHECKING:
    from email.message import Message

_DEFAULT_TIMEOUT = 60.0
_LAST30DAYS_TIMEOUT = 180.0
_MAX_SNIPPET = 500
_MAX_SLUG = 60
_MIN_RELEASE_TERM_LENGTH = 3
_MAX_HTTP_RESPONSE_BYTES = 8 * 1024 * 1024
_PROCESS_TERM_GRACE_S = 0.2
_PROCESS_KILL_DRAIN_S = 2.0
_PROCESS_CANCEL_POLL_S = 0.1
_HTTP_OK = 200
_HTTP_REDIRECT = 300
_HTTP_PAYMENT_REQUIRED = 402
_HTTP_QUOTA = 429
_RELEASE_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "from", "this", "that", "are", "was", "not", "you"}
)
_SOURCE_NAMES = (
    "github-issues",
    "github-discussions",
    "github-releases",
    "exa",
    "context7",
    "firecrawl-developer",
    "firecrawl-search",
    "last30days",
)
_DEFAULT_CANDIDATES = tuple(name for name in _SOURCE_NAMES if name != "last30days")
_GITHUB_QUERY = (
    "query($searchQuery:String!,$limit:Int!){"
    "search(type:DISCUSSION,query:$searchQuery,first:$limit){"
    "nodes{... on Discussion{title url bodyText createdAt}}}}"
)
_SOURCE_DETAILS = {
    "github-issues": ("gh api REST", "gh on PATH + --repo"),
    "github-discussions": ("gh api graphql", "gh on PATH + --repo"),
    "github-releases": ("gh api REST", "gh on PATH + --repo"),
    "exa": ("HTTPS POST", "EXA_API_KEY in process environment"),
    "context7": ("ctx7 CLI", "ctx7 on PATH"),
    "firecrawl-developer": ("HTTPS GET", "none"),
    "firecrawl-search": ("firecrawl CLI", "firecrawl on PATH"),
    "last30days": ("python3 script", "last30days script found"),
}
_LIVE_PROCESSES: set[subprocess.Popen[bytes]] = set()
_LIVE_PROCESSES_LOCK = threading.Lock()
_CANCEL_CHILDREN = threading.Event()


class Status(Enum):
    """Observable outcome of one source fetch."""

    OK = "ok"
    EMPTY_VERIFIED = "empty_verified"
    EMPTY_UNVERIFIED = "empty_unverified"
    ERROR = "error"
    SKIPPED = "skipped"


class SkipReason(Enum):
    """Why a source was deliberately skipped."""

    PREREQUISITE = "prerequisite"
    CREDITS_EXHAUSTED = "credits-exhausted"


class FailureCode(Enum):
    """Closed set of model-visible codes, independent of provider text."""

    CREDITS_EXHAUSTED = "credits-exhausted"
    PREREQUISITE = "prerequisite"
    HTTP_ERROR = "http-error"
    INVALID_JSON = "invalid-json"
    SHAPE_ERROR = "shape-error"
    PROVIDER_FAILURE = "provider-failure"
    PROCESS_FAILED = "process-failed"
    TIMEOUT = "timeout"
    REQUEST_FAILED = "request-failed"
    CREDENTIAL_INVALID = "credential-invalid"
    CANARY_FAILED = "canary-failed"
    CANARY_EMPTY = "canary-empty"
    NO_CANARY = "no-canary"
    NOT_FOUND = "not-found"
    REDIRECTED = "redirected"
    EMPTY_OUTPUT = "empty-output"
    IO_ERROR = "io-error"
    OTHER = "other"


_PREREQUISITE_TEXTS = frozenset(
    {
        "needs --repo",
        "needs gh",
        "EXA_API_KEY not inherited; run through fnox exec",
        "needs ctx7",
        "needs firecrawl",
        "needs last30days script",
        "SERPER_API_KEY not inherited; run through fnox exec",
        "SERP_API_KEY not inherited; run through fnox exec",
    }
)


def failure_code(
    reason: object, *, status: object, skip_reason: object = None
) -> FailureCode | None:
    """Project producer literals to finite codes; never return diagnostic text."""
    if status in (Status.OK.value, Status.EMPTY_VERIFIED.value):
        return None
    if skip_reason == SkipReason.CREDITS_EXHAUSTED.value:
        return FailureCode.CREDITS_EXHAUSTED
    if skip_reason == SkipReason.PREREQUISITE.value or (
        status == Status.SKIPPED.value
        and isinstance(reason, str)
        and reason in _PREREQUISITE_TEXTS
    ):
        return FailureCode.PREREQUISITE
    if not isinstance(reason, str):
        return FailureCode.OTHER
    if re.fullmatch(r"HTTP \d{3}", reason):
        return FailureCode.HTTP_ERROR
    literals = {
        "invalid JSON": FailureCode.INVALID_JSON,
        "unexpected response shape": FailureCode.SHAPE_ERROR,
        "unexpected discussions search shape": FailureCode.SHAPE_ERROR,
        "unexpected JSON shape": FailureCode.SHAPE_ERROR,
        "unexpected fallback response shape": FailureCode.SHAPE_ERROR,
        "response contained errors": FailureCode.SHAPE_ERROR,
        "provider reported failure": FailureCode.PROVIDER_FAILURE,
        "timed out": FailureCode.TIMEOUT,
        "request failed": FailureCode.REQUEST_FAILED,
        "response too large": FailureCode.REQUEST_FAILED,
        "incomplete response": FailureCode.REQUEST_FAILED,
        "canary failed": FailureCode.CANARY_FAILED,
        "canary returned 0 items": FailureCode.CANARY_EMPTY,
        "no canary": FailureCode.NO_CANARY,
        "script disappeared": FailureCode.NOT_FOUND,
        "unknown source": FailureCode.NOT_FOUND,
    }
    code = literals.get(reason, FailureCode.OTHER)
    if re.match(r"^exited -?\d+: ", reason):
        code = FailureCode.PROCESS_FAILED
    elif reason.startswith("invalid credential header for "):
        code = FailureCode.CREDENTIAL_INVALID
    return code


CREDIT_METERED_SOURCES = frozenset(
    {"exa", "context7", "firecrawl-developer", "firecrawl-search"}
)
_CREDIT_TEXT = re.compile(
    r"insufficient credits|payment required|out of credits|credits exhausted|"
    r"not enough credits|run out of searches",
    re.IGNORECASE,
)
_QUOTA_TEXT = re.compile(r"quota exceeded|exceeded your quota", re.IGNORECASE)
_FALLBACK_CREDIT_TEXT = re.compile(
    r"not enough credits|your account has run out of searches",
    re.IGNORECASE,
)
_CREDIT_STATUS = re.compile(
    r'(?:(?:"status"|"statusCode")\s*:\s*|'
    r"\bstatus(?:\s+code)?\s*[:=]?\s+|\bHTTP(?:/\d(?:\.\d)?)?\s+)(\d{3})\b",
    re.IGNORECASE,
)
_FALLBACK_ROUTES = MappingProxyType({"firecrawl-search": ("serper", "serpapi")})
_FALLBACK_KEYS = MappingProxyType(
    {"serper": "SERPER_API_KEY", "serpapi": "SERP_API_KEY"}
)


def is_credit_exhaustion(http_status: int | None, text: str) -> bool:
    """Distinguish exhausted quota from auth, transient limits and server errors."""
    if http_status is None and (match := _CREDIT_STATUS.search(text)):
        http_status = int(match[1])
    if http_status == _HTTP_PAYMENT_REQUIRED:
        return True
    if http_status == _HTTP_QUOTA:
        return bool(_CREDIT_TEXT.search(text) or _QUOTA_TEXT.search(text))
    if http_status is None:
        return bool(_CREDIT_TEXT.search(text))
    return False


def _fallback_credit(http_status: int | None, body: str) -> bool:
    """Re-derive fallback exhaustion from failing transport and top-level fields."""
    if http_status is None or _HTTP_OK <= http_status < _HTTP_REDIRECT:
        return False
    if is_credit_exhaustion(http_status, body):
        return True
    try:
        payload = json.loads(body)
    except ValueError:
        return False
    return isinstance(payload, dict) and any(
        isinstance(payload.get(key), str) and _FALLBACK_CREDIT_TEXT.search(payload[key])
        for key in ("message", "error")
    )


@dataclass(frozen=True)
class RouteAttempt:
    """A tried route and its independently hashed evidence."""

    route: str
    status: Status
    http_status: int | None
    reason: str | None
    raw_file: str | None
    raw_sha256: str | None


class Endpoint(Enum):
    """HTTP destinations accepted by the injected transport boundary."""

    EXA_SEARCH = "exa-search"
    FIRECRAWL_DEVELOPER = "firecrawl-developer"
    SERPER_SEARCH = "serper-search"
    SERPAPI_SEARCH = "serpapi-search"


@dataclass(frozen=True)
class Item:
    """One normalized search result."""

    title: str
    url: str
    snippet: str
    date: str | None


@dataclass(frozen=True)
class Control:
    """The same-source canary used to interpret an empty primary result."""

    query: str
    count: int | None


@dataclass(frozen=True)
class SourceResult:
    """One source's normalized outcome."""

    source: str
    status: Status
    items: tuple[Item, ...]
    elapsed_s: float
    reason: str | None
    control: Control | None
    raw_file: str | None
    raw_sha256: str | None = None
    skip_reason: SkipReason | None = None
    route: str | None = None
    provisional: bool = False
    attempts: tuple[RouteAttempt, ...] = ()


@dataclass(frozen=True)
class FanoutRequest:
    """Inputs shared by every source in a fanout."""

    query: str
    repo: str | None
    sources: tuple[str, ...]
    limit: int
    timeout: float | None
    last30days_plan: Path | None = None


class Runner(Protocol):
    """Injected subprocess boundary."""

    def __call__(
        self,
        argv: list[str],
        *,
        timeout: float,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[bytes]:
        """Run one bounded child process."""
        ...


class Http(Protocol):
    """Injected HTTP boundary whose callers select a fixed endpoint."""

    def __call__(
        self,
        endpoint: Endpoint,
        *,
        params: dict[str, str | int] | None,
        body: dict[str, object] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        """Return an HTTP status and the unmodified response body."""
        ...


class _ReadableResponse(Protocol):
    @property
    def headers(self) -> Message[str, str]:
        """Return the parsed response headers."""
        ...

    def read(self, amount: int = -1, /) -> bytes:
        """Read at most ``amount`` response bytes."""
        ...

    def close(self) -> None:
        """Close the response stream."""
        ...


@dataclass(frozen=True)
class _Attempt:
    items: tuple[Item, ...]
    raw: bytes
    error: str | None = None
    http_status: int | None = None
    rc: int | None = None
    stderr_redacted: str = ""


@dataclass(frozen=True)
class _Fetch:
    result: SourceResult
    raw: bytes | None
    attempt_raw: tuple[bytes | None, ...] = ()


@dataclass(frozen=True)
class _Boundaries:
    runner: Runner
    http: Http


@dataclass(frozen=True)
class _HttpJsonRequest:
    endpoint: Endpoint
    params: dict[str, str | int] | None
    body: dict[str, object] | None
    headers: dict[str, str]
    limit: int


@dataclass(frozen=True)
class _Deadline:
    expires_at: float

    @classmethod
    def after(cls, seconds: float) -> _Deadline:
        return cls(time.monotonic() + seconds)

    def remaining(self) -> float:
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        return remaining


class _UsageError(ValueError):
    """A command-line error that maps to exit code 2."""


class _CredentialHeaderError(ValueError):
    """A credential cannot safely be represented in an HTTP header."""

    def __init__(self, name: str) -> None:
        super().__init__(f"invalid credential header for {name}")


class _HttpBodyError(ValueError):
    """An HTTP body failed a bounded-read invariant."""

    reason: str


class _ResponseTooLargeError(_HttpBodyError):
    """An HTTP response exceeded the bounded in-memory body size."""

    reason = "response too large"


class _IncompleteResponseError(_HttpBodyError):
    """An HTTP body ended before its declared content length."""

    reason = "incomplete response"


class _ProcessCancelledError(RuntimeError):
    """A live child was stopped because the fan-out was interrupted."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise _UsageError(message)


def _signal_process_group(
    process: subprocess.Popen[bytes], sent_signal: signal.Signals
) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, sent_signal)


def _close_process_pipes(process: subprocess.Popen[bytes]) -> None:
    for pipe in (process.stdout, process.stderr):
        if pipe is not None:
            with contextlib.suppress(OSError):
                pipe.close()


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Stop a process group, bound pipe draining, and reap the direct child."""
    _signal_process_group(process, signal.SIGTERM)
    try:
        process.communicate(timeout=_PROCESS_TERM_GRACE_S)
    except subprocess.TimeoutExpired:
        _signal_process_group(process, signal.SIGKILL)
    else:
        return
    try:
        process.communicate(timeout=_PROCESS_KILL_DRAIN_S)
    except subprocess.TimeoutExpired:
        _close_process_pipes(process)
    else:
        return
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        process.wait(timeout=_PROCESS_TERM_GRACE_S)


def _communicate_until(
    process: subprocess.Popen[bytes], timeout: float
) -> tuple[bytes, bytes]:
    expires_at = time.monotonic() + timeout
    while True:
        if _CANCEL_CHILDREN.is_set():
            raise _ProcessCancelledError
        remaining = expires_at - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        try:
            return process.communicate(timeout=min(remaining, _PROCESS_CANCEL_POLL_S))
        except subprocess.TimeoutExpired:
            if time.monotonic() >= expires_at:
                raise


def _cancel_live_processes() -> None:
    _CANCEL_CHILDREN.set()
    with _LIVE_PROCESSES_LOCK:
        processes = tuple(_LIVE_PROCESSES)
    for process in processes:
        _signal_process_group(process, signal.SIGTERM)


def default_runner(
    argv: list[str], *, timeout: float, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    """Run one bounded process group with captured byte streams."""
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    with _LIVE_PROCESSES_LOCK:
        _LIVE_PROCESSES.add(process)
    try:
        try:
            stdout, stderr = _communicate_until(process, timeout)
        except (
            subprocess.TimeoutExpired,
            _ProcessCancelledError,
            KeyboardInterrupt,
        ):
            _terminate_process_group(process)
            raise
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    finally:
        with _LIVE_PROCESSES_LOCK:
            _LIVE_PROCESSES.discard(process)


def _read_http_body(response: _ReadableResponse, deadline: _Deadline) -> bytes:
    outcomes: queue.Queue[bytes | Exception] = queue.Queue()

    def read_body() -> None:
        try:
            content_length = response.headers.get("Content-Length")
            expected = int(content_length) if content_length is not None else None
            if expected is not None and expected > _MAX_HTTP_RESPONSE_BYTES:
                raise _ResponseTooLargeError
            try:
                body = response.read(_MAX_HTTP_RESPONSE_BYTES + 1)
            except http_client.IncompleteRead as exc:
                if expected is not None:
                    raise _IncompleteResponseError from exc
                raise
            if len(body) > _MAX_HTTP_RESPONSE_BYTES:
                raise _ResponseTooLargeError
            if expected is not None and len(body) < expected:
                raise _IncompleteResponseError
            outcomes.put(body)
        except (http_client.HTTPException, ValueError, OSError, AttributeError) as exc:
            outcomes.put(exc)

    worker = threading.Thread(target=read_body, daemon=True)
    worker.start()
    try:
        outcome = outcomes.get(timeout=deadline.remaining())
    except queue.Empty as exc:
        threading.Thread(target=response.close, daemon=True).start()
        raise TimeoutError from exc
    worker.join(timeout=deadline.remaining())
    response.close()
    deadline.remaining()
    if isinstance(outcome, Exception):
        raise outcome
    return outcome


def default_http(
    endpoint: Endpoint,
    *,
    params: dict[str, str | int] | None,
    body: dict[str, object] | None,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, bytes]:
    """Call one fixed HTTPS API and preserve its response bytes."""
    deadline = _Deadline.after(timeout)
    if endpoint is Endpoint.EXA_SEARCH:
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.exa.ai/search",
                    data=json.dumps(body or {}).encode(),
                    headers=headers,
                    method="POST",
                ),
                timeout=deadline.remaining(),
            )
            return response.status, _read_http_body(response, deadline)
        except urllib.error.HTTPError as exc:
            return exc.code, _read_http_body(exc, deadline)
    if endpoint is Endpoint.FIRECRAWL_DEVELOPER:
        query = urllib.parse.urlencode(params or {})
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.firecrawl.dev/v2/search/developer?{query}",
                    headers=headers,
                    method="GET",
                ),
                timeout=deadline.remaining(),
            )
            return response.status, _read_http_body(response, deadline)
        except urllib.error.HTTPError as exc:
            return exc.code, _read_http_body(exc, deadline)
    if endpoint in {Endpoint.SERPER_SEARCH, Endpoint.SERPAPI_SEARCH}:
        return _fallback_http(
            endpoint, params=params, body=body, headers=headers, deadline=deadline
        )
    message = f"unsupported endpoint: {endpoint.value}"
    raise ValueError(message)


def _fallback_http(
    endpoint: Endpoint,
    *,
    params: dict[str, str | int] | None,
    body: dict[str, object] | None,
    headers: dict[str, str],
    deadline: _Deadline,
) -> tuple[int, bytes]:
    if endpoint is Endpoint.SERPER_SEARCH:
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    "https://google.serper.dev/search",
                    data=json.dumps(body or {}).encode(),
                    headers=headers,
                    method="POST",
                ),
                timeout=deadline.remaining(),
            )
            return response.status, _read_http_body(response, deadline)
        except urllib.error.HTTPError as exc:
            return exc.code, _read_http_body(exc, deadline)
    if endpoint is Endpoint.SERPAPI_SEARCH:
        query = urllib.parse.urlencode(params or {})
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    f"https://serpapi.com/search.json?{query}",
                    headers=headers,
                    method="GET",
                ),
                timeout=deadline.remaining(),
            )
            return response.status, _read_http_body(response, deadline)
        except urllib.error.HTTPError as exc:
            return exc.code, _read_http_body(exc, deadline)
    message = "unsupported fallback endpoint"
    raise ValueError(message)


def _first_passage(record: dict[str, object]) -> str | None:
    """The firecrawl developer index puts its excerpt in `passages[0].text`."""
    passages = record.get("passages")
    if isinstance(passages, list) and passages and isinstance(passages[0], dict):
        text = passages[0].get("text")
        return text if isinstance(text, str) else None
    return None


def _record_item(record: object) -> Item | None:
    if not isinstance(record, dict):
        return None
    url = record.get("html_url") or record.get("url")
    if not isinstance(url, str) or not url:
        return None
    title_value = record.get("title") or record.get("name") or url
    snippet_value = (
        record.get("text")
        or _first_passage(record)
        or record.get("summary")
        or record.get("snippet")
        or record.get("description")
        or record.get("bodyText")
        or record.get("body")
        or ""
    )
    date_value = (
        record.get("publishedDate")
        or record.get("published_at")
        or record.get("createdAt")
        or record.get("created_at")
        or record.get("date")
    )
    return Item(
        title=str(title_value),
        url=url,
        snippet=str(snippet_value)[:_MAX_SNIPPET],
        date=str(date_value) if date_value is not None else None,
    )


def _records(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "data", "web"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        nested = _records(value)
        if nested:
            return nested
    return []


def _items_from_payload(payload: object, *, limit: int) -> tuple[Item, ...]:
    return tuple(
        item
        for record in _records(payload)[:limit]
        if (item := _record_item(record)) is not None
    )


def _decode_json(raw: bytes) -> object:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = "invalid JSON"
        raise ValueError(message) from exc


def _timeout_for(source: str, requested: float | None) -> float:
    if requested is not None:
        return requested
    return _LAST30DAYS_TIMEOUT if source == "last30days" else _DEFAULT_TIMEOUT


def _run_json(
    argv: list[str],
    *,
    runner: Runner,
    deadline: _Deadline,
    env: dict[str, str],
) -> tuple[object | None, bytes, str | None, int, str]:
    completed = runner(argv, timeout=deadline.remaining(), env=env)
    raw = _redact_text((completed.stdout or b"").decode(errors="replace"), env).encode()
    stderr = _redacted_stderr(completed, env)
    if completed.returncode != 0:
        return (
            None,
            raw,
            _subprocess_error(completed, env),
            completed.returncode,
            stderr,
        )
    try:
        return _decode_json(raw), raw, None, completed.returncode, stderr
    except ValueError:
        return None, raw, "invalid JSON", completed.returncode, stderr


def _gh_env() -> dict[str, str]:
    return child_env.clean_env(keep=frozenset({"GITHUB_TOKEN", "GH_TOKEN"}))


def _redact_text(text: str, env: dict[str, str]) -> str:
    values = sorted(
        (
            value
            for name, value in env.items()
            if value and child_env.is_credential(name)
        ),
        key=len,
        reverse=True,
    )
    for value in values:
        text = text.replace(value, "[REDACTED]")
    return text


def _redact_request_text(text: str, env: dict[str, str]) -> str:
    # Request URLs can carry SerpApi keys; provider pricing links are evidence.
    # Exclude JSON escape backslashes so a closing escaped quote stays intact.
    return re.sub(
        r"https://(?:google\.serper\.dev/search|serpapi\.com/search\.json)[^\s\"<>\\]*",
        "[REDACTED REQUEST URL]",
        _redact_text(text, env),
    )


def _redacted_stderr(
    completed: subprocess.CompletedProcess[bytes], env: dict[str, str]
) -> str:
    return _redact_request_text((completed.stderr or b"").decode(errors="replace"), env)


def _subprocess_error(
    completed: subprocess.CompletedProcess[bytes], env: dict[str, str]
) -> str:
    stderr = _redacted_stderr(completed, env)
    stderr = stderr.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " | ")
    return f"exited {completed.returncode}: {stderr.strip()[-300:]}"


def _credential_header(name: str, value: str) -> str:
    if "\r" in value or "\n" in value:
        raise _CredentialHeaderError(name)
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        raise _CredentialHeaderError(name) from None
    return value


def _required_repo(request: FanoutRequest) -> str:
    if request.repo is None:
        message = "repository is required for this source"
        raise RuntimeError(message)
    return request.repo


def _github_issues(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    repo = _required_repo(request)
    encoded = urllib.parse.quote_plus(query)
    endpoint = f"/search/issues?q=repo:{repo}+{encoded}&per_page={request.limit}"
    payload, raw, error, rc, stderr = _run_json(
        ["gh", "api", endpoint], runner=runner, deadline=deadline, env=_gh_env()
    )
    if error:
        return _Attempt((), raw, error, rc=rc, stderr_redacted=stderr)
    return _Attempt(_items_from_payload(payload, limit=request.limit), raw)


def _github_discussions(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    repo = _required_repo(request)
    payload, raw, error, rc, stderr = _run_json(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_GITHUB_QUERY}",
            "-f",
            f"searchQuery=repo:{repo} {query}",
            "-F",
            f"limit={request.limit}",
        ],
        runner=runner,
        deadline=deadline,
        env=_gh_env(),
    )
    if error:
        return _Attempt((), raw, error, rc=rc, stderr_redacted=stderr)
    if not isinstance(payload, dict):
        return _Attempt((), raw, "unexpected response shape")
    if "errors" in payload:
        return _Attempt((), raw, "response contained errors")
    data = payload.get("data")
    search = data.get("search") if isinstance(data, dict) else None
    nodes = search.get("nodes") if isinstance(search, dict) else None
    if not isinstance(nodes, list):
        return _Attempt((), raw, "unexpected discussions search shape")
    items = tuple(
        item
        for record in nodes[: request.limit]
        if (item := _record_item(record)) is not None
    )
    return _Attempt(items, raw)


def _github_releases(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    repo = _required_repo(request)
    payload, raw, error, rc, stderr = _run_json(
        ["gh", "api", f"repos/{repo}/releases?per_page=100"],
        runner=runner,
        deadline=deadline,
        env=_gh_env(),
    )
    if error:
        return _Attempt((), raw, error, rc=rc, stderr_redacted=stderr)
    if not isinstance(payload, list):
        return _Attempt((), raw, "unexpected JSON shape")
    terms = tuple(
        term
        for term in dict.fromkeys(re.findall(r"[a-z0-9]+", query.casefold()))
        if len(term) >= _MIN_RELEASE_TERM_LENGTH and term not in _RELEASE_STOPWORDS
    )
    items: list[Item] = []
    for record in payload:
        if not isinstance(record, dict):
            continue
        url = record.get("html_url")
        if not isinstance(url, str) or not url:
            continue
        tag = str(record.get("tag_name") or "")
        name = str(record.get("name") or "")
        body = str(record.get("body") or "")
        values = (tag, name, body)
        if not terms or not all(
            any(_contains_release_term(value, term) for value in values)
            for term in terms
        ):
            continue
        body_mentions = any(_contains_release_term(body, term) for term in terms)
        date = record.get("published_at") or record.get("created_at")
        items.append(
            Item(
                tag or name or url,
                url,
                "release body mentions a query term: "
                f"{'yes' if body_mentions else 'no'}",
                str(date) if date is not None else None,
            )
        )
        if len(items) == request.limit:
            break
    return _Attempt(tuple(items), raw)


def _contains_release_term(value: str, term: str) -> bool:
    folded = value.casefold()
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", folded) is not None


def _github_repo_control(
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> tuple[int | None, str | None]:
    repo = _required_repo(request)
    payload, _raw, error, _rc, _stderr = _run_json(
        ["gh", "api", f"repos/{repo}"],
        runner=runner,
        deadline=deadline,
        env=_gh_env(),
    )
    if error or not isinstance(payload, dict):
        return None, error or "unexpected JSON shape"
    return 1, None


def _http_json(
    request: _HttpJsonRequest,
    *,
    http: Http,
    deadline: _Deadline,
) -> _Attempt:
    status, raw = http(
        request.endpoint,
        params=request.params,
        body=request.body,
        headers=request.headers,
        timeout=deadline.remaining(),
    )
    if not _HTTP_OK <= status < _HTTP_REDIRECT:
        return _Attempt((), raw, f"HTTP {status}", http_status=status)
    try:
        payload = _decode_json(raw)
    except ValueError:
        return _Attempt((), raw, "invalid JSON", http_status=status)
    return _Attempt(
        _items_from_payload(payload, limit=request.limit), raw, http_status=status
    )


def _exa(
    query: str,
    request: FanoutRequest,
    *,
    http: Http,
    deadline: _Deadline,
) -> _Attempt:
    return _http_json(
        _HttpJsonRequest(
            Endpoint.EXA_SEARCH,
            None,
            {"query": query, "numResults": request.limit},
            {
                "Content-Type": "application/json",
                "x-api-key": _credential_header(
                    "EXA_API_KEY", os.environ.get("EXA_API_KEY", "")
                ),
            },
            request.limit,
        ),
        http=http,
        deadline=deadline,
    )


def _firecrawl_developer(
    query: str,
    request: FanoutRequest,
    *,
    http: Http,
    deadline: _Deadline,
) -> _Attempt:
    # The developer index takes `k` for the result count; `limit` is a 400
    # ("Unrecognized key"), measured live 2026-09-26.
    params: dict[str, str | int] = {"query": query, "k": request.limit}
    if request.repo:
        params["repos"] = request.repo
    headers: dict[str, str] = {}
    if key := os.environ.get("FIRECRAWL_API_KEY"):
        headers["Authorization"] = (
            f"Bearer {_credential_header('FIRECRAWL_API_KEY', key)}"
        )
    return _http_json(
        _HttpJsonRequest(
            Endpoint.FIRECRAWL_DEVELOPER,
            params,
            None,
            headers,
            request.limit,
        ),
        http=http,
        deadline=deadline,
    )


def _fallback_records(payload: object, route: str) -> list[object] | None:
    if not isinstance(payload, dict):
        return None
    field = "organic" if route == "serper" else "organic_results"
    records = payload.get(field)
    if isinstance(records, list):
        return records
    # https://serpapi.com/api-status-and-error-codes documents Success with
    # Fully empty and no organic_results; it still needs a same-route control.
    metadata, information = (
        payload.get("search_metadata"),
        payload.get("search_information"),
    )
    if (
        route == "serpapi"
        and field not in payload
        and isinstance(metadata, dict)
        and metadata.get("status") == "Success"
        and isinstance(information, dict)
        and information.get("organic_results_state") == "Fully empty"
    ):
        return []
    return None


def _fallback_search(
    route: str, query: str, request: FanoutRequest, *, http: Http, deadline: _Deadline
) -> _Attempt:
    name = _FALLBACK_KEYS[route]
    key = _credential_header(name, os.environ.get(name, ""))
    endpoint = Endpoint.SERPER_SEARCH if route == "serper" else Endpoint.SERPAPI_SEARCH
    status, raw = http(
        endpoint,
        params={"engine": "google", "q": query, "api_key": key}
        if route == "serpapi"
        else None,
        body={"q": query, "num": request.limit} if route == "serper" else None,
        headers={"X-API-KEY": key, "Content-Type": "application/json"}
        if route == "serper"
        else {},
        timeout=deadline.remaining(),
    )
    # SerpApi discontinued num; respect the limit locally (provider docs).
    raw = _redact_request_text(raw.decode(errors="replace"), dict(os.environ)).encode()
    if not _HTTP_OK <= status < _HTTP_REDIRECT:
        return _Attempt((), raw, f"HTTP {status}", http_status=status)
    try:
        payload = _decode_json(raw)
    except ValueError:
        return _Attempt((), raw, "invalid JSON", http_status=status)
    records = _fallback_records(payload, route)
    if records is None:
        return _Attempt(
            (), raw, "unexpected fallback response shape", http_status=status
        )
    items = tuple(
        item
        for record in records[: request.limit]
        if isinstance(record, dict)
        and (
            item := _record_item(
                {
                    "url": record.get("link"),
                    "title": record.get("title"),
                    "snippet": record.get("snippet"),
                    "date": record.get("date"),
                }
            )
        )
        is not None
    )
    return _Attempt(items, raw, http_status=status)


def _firecrawl_search(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    payload, raw, error, rc, stderr = _run_json(
        [
            "firecrawl",
            "search",
            query,
            # The CLI default is `web,alexandria`: without this the result is the
            # Alexandria TOOL catalog, not web pages (measured live 2026-09-26).
            "--sources",
            "web",
            "--json",
            "--limit",
            str(request.limit),
        ],
        runner=runner,
        deadline=deadline,
        env=child_env.clean_env(keep=frozenset({"FIRECRAWL_API_KEY"})),
    )
    if error:
        return _Attempt((), raw, error, rc=rc, stderr_redacted=stderr)
    if isinstance(payload, dict) and payload.get("success") is False:
        return _Attempt(
            (), raw, "provider reported failure", rc=rc, stderr_redacted=stderr
        )
    return _Attempt(
        _items_from_payload(payload, limit=request.limit),
        raw,
        rc=rc,
        stderr_redacted=stderr,
    )


def _context7_library_id(raw: bytes) -> str | None:
    text = raw.decode(errors="replace")
    match = re.search(r"Context7-compatible library ID:\s*(\S+)", text)
    if match:
        return match.group(1)
    fallback = re.search(r"^\s*\d+[.)]\s+(\/\S+)", text, re.MULTILINE)
    return fallback.group(1) if fallback else None


def _context7_items(raw: bytes, *, limit: int) -> tuple[Item, ...]:
    text = raw.decode(errors="replace")
    sections = re.finditer(
        r"^###\s+(.+?)\s*$\n(.*?)(?=^###\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    items: list[Item] = []
    for section in sections:
        body = section.group(2).strip()
        source = re.search(r"^Source:\s*(\S+)", body, re.MULTILINE)
        if source is None:
            continue
        items.append(
            Item(
                section.group(1).strip(),
                source.group(1).strip("<>"),
                body[:_MAX_SNIPPET],
                None,
            )
        )
        if len(items) == limit:
            break
    return tuple(items)


def _context7(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    env = child_env.clean_env(keep=frozenset({"CONTEXT7_API_KEY"}))
    library_name = request.repo.rsplit("/", maxsplit=1)[-1] if request.repo else query
    library = runner(
        ["ctx7", "library", library_name],
        timeout=deadline.remaining(),
        env=env,
    )
    library_raw = library.stdout or b""
    if library.returncode != 0:
        return _Attempt(
            (),
            library_raw,
            _subprocess_error(library, env),
            rc=library.returncode,
            stderr_redacted=_redacted_stderr(library, env),
        )
    library_id = _context7_library_id(library_raw)
    if library_id is None:
        return _Attempt((), library_raw)
    docs = runner(
        ["ctx7", "docs", library_id, query],
        timeout=deadline.remaining(),
        env=env,
    )
    docs_raw = docs.stdout or b""
    if docs.returncode != 0:
        return _Attempt(
            (),
            docs_raw,
            _subprocess_error(docs, env),
            rc=docs.returncode,
            stderr_redacted=_redacted_stderr(docs, env),
        )
    return _Attempt(_context7_items(docs_raw, limit=request.limit), docs_raw)


def _numeric_version(value: str) -> tuple[int, ...] | None:
    parts = value.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _last30days_script() -> Path | None:
    if configured := os.environ.get("LAST30DAYS_SCRIPT"):
        candidate = Path(configured).expanduser()
        return candidate if candidate.is_file() else None
    relative = Path("skills/last30days/scripts/last30days.py")
    roots = (
        Path.home() / ".claude/plugins/cache/last30days-skill/last30days",
        Path.home() / ".codex/plugins/cache/last30days-skill/last30days",
    )
    for root in roots:
        candidates = [
            (version, path / relative)
            for path in root.glob("*")
            if (version := _numeric_version(path.name)) is not None
            and (path / relative).is_file()
        ]
        if candidates:
            return max(candidates, key=lambda row: row[0])[1]
    return None


def _last30days_env() -> dict[str, str]:
    keep = frozenset(
        {
            "GITHUB_TOKEN",
            "SCRAPECREATORS_API_KEY",
            "EXA_API_KEY",
            "PARALLEL_API_KEY",
            "BRAVE_API_KEY",
        }
    )
    env = child_env.clean_env(keep=keep)
    env.pop("LAST30DAYS_TRUST_PROJECT_CONFIG", None)
    env["LAST30DAYS_CONFIG_DIR"] = ""
    env["LAST30DAYS_SKIP_KEYCHAIN"] = "1"
    return env


def _last30days(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    script = _last30days_script()
    if script is None:
        return _Attempt((), b"", "script disappeared")
    argv = ["python3", str(script), query, "--emit=json"]
    if request.last30days_plan is not None:
        argv.extend(("--plan", str(request.last30days_plan), "--web-backend=exa"))
    if request.repo:
        argv.append(f"--github-repo={request.repo}")
    payload, raw, error, rc, stderr = _run_json(
        argv,
        runner=runner,
        deadline=deadline,
        env=_last30days_env(),
    )
    if error:
        return _Attempt((), raw, error, rc=rc, stderr_redacted=stderr)
    return _Attempt(_items_from_payload(payload, limit=request.limit), raw)


def _prerequisite_reason(source: str, request: FanoutRequest) -> str | None:
    reason: str | None = None
    if source.startswith("github-"):
        if request.repo is None:
            reason = "needs --repo"
        elif shutil.which("gh") is None:
            reason = "needs gh"
    elif source == "exa" and not os.environ.get("EXA_API_KEY"):
        # A noninteractive shell does not run the fnox prompt hook. Absence
        # here means "not inherited", never "the user has no Exa key".
        # Run this task through native `fnox exec` to inject it into the child.
        reason = "EXA_API_KEY not inherited; run through fnox exec"
    elif source == "context7" and shutil.which("ctx7") is None:
        reason = "needs ctx7"
    elif source == "firecrawl-search" and shutil.which("firecrawl") is None:
        reason = "needs firecrawl"
    elif source == "last30days" and _last30days_script() is None:
        reason = "needs last30days script"
    return reason


def _primary_attempt(
    source: str,
    query: str,
    request: FanoutRequest,
    *,
    boundaries: _Boundaries,
    deadline: _Deadline,
) -> _Attempt:
    if source in _FALLBACK_KEYS:
        attempt = _fallback_search(
            source, query, request, http=boundaries.http, deadline=deadline
        )
    elif source == "github-issues":
        attempt = _github_issues(
            query, request, runner=boundaries.runner, deadline=deadline
        )
    elif source == "github-discussions":
        attempt = _github_discussions(
            query, request, runner=boundaries.runner, deadline=deadline
        )
    elif source == "github-releases":
        attempt = _github_releases(
            query, request, runner=boundaries.runner, deadline=deadline
        )
    elif source == "exa":
        attempt = _exa(query, request, http=boundaries.http, deadline=deadline)
    elif source == "context7":
        attempt = _context7(query, request, runner=boundaries.runner, deadline=deadline)
    elif source == "firecrawl-developer":
        attempt = _firecrawl_developer(
            query, request, http=boundaries.http, deadline=deadline
        )
    elif source == "firecrawl-search":
        attempt = _firecrawl_search(
            query, request, runner=boundaries.runner, deadline=deadline
        )
    elif source == "last30days":
        attempt = _last30days(
            query, request, runner=boundaries.runner, deadline=deadline
        )
    else:
        attempt = _Attempt((), b"", "unknown source")
    return attempt


def _control_query(source: str, request: FanoutRequest) -> str | None:
    if source in {"github-issues", "github-discussions"}:
        return _required_repo(request).rsplit("/", maxsplit=1)[-1]
    if source == "firecrawl-developer" and request.repo:
        return request.repo.rsplit("/", maxsplit=1)[-1]
    if source in {
        "exa",
        "context7",
        "firecrawl-developer",
        "firecrawl-search",
        "serper",
        "serpapi",
    }:
        return "python"
    return None


def _empty_control(
    source: str,
    request: FanoutRequest,
    *,
    boundaries: _Boundaries,
    deadline: _Deadline,
) -> tuple[Control, str | None]:
    query = (
        request.repo or ""
        if source == "github-releases"
        else _control_query(source, request)
    )
    if query is None:
        return Control("", None), "no canary"
    try:
        if source == "github-releases":
            count, error = _github_repo_control(
                request, runner=boundaries.runner, deadline=deadline
            )
            return Control(query, count), error
        control_request = (
            replace(request, repo=None) if source == "context7" else request
        )
        attempt = _primary_attempt(
            source,
            query,
            control_request,
            boundaries=boundaries,
            deadline=deadline,
        )
    except (
        http_client.HTTPException,
        ValueError,
        OSError,
        subprocess.TimeoutExpired,
    ):
        return Control(query, None), "canary failed"
    count = None if attempt.error else len(attempt.items)
    return Control(query, count), attempt.error


def _attempt_credit(attempt: _Attempt) -> bool:
    text = attempt.stderr_redacted + "\n" + attempt.raw.decode(errors="replace")
    status = attempt.http_status
    if status is None and attempt.rc == 0:
        try:
            payload = _decode_json(attempt.raw)
        except ValueError:
            return False
        if isinstance(payload, dict) and payload.get("success") is False:
            claimed = payload.get("status")
            status = claimed if isinstance(claimed, int) else None
    return is_credit_exhaustion(status, text)


def _transport_envelope(attempt: _Attempt) -> bytes:
    return json.dumps(
        {
            "http_status": attempt.http_status,
            "rc": attempt.rc,
            "body": _redact_request_text(
                attempt.raw.decode(errors="replace"), dict(os.environ)
            ),
            "stderr_redacted": _redact_request_text(
                attempt.stderr_redacted, dict(os.environ)
            ),
        },
        sort_keys=True,
    ).encode()


@dataclass(frozen=True)
class _CreditRun:
    boundaries: _Boundaries
    deadline: _Deadline
    started: float


def _fallback_attempt(route: str, request: FanoutRequest, run: _CreditRun) -> _Attempt:
    try:
        return _primary_attempt(
            route,
            request.query,
            request,
            boundaries=run.boundaries,
            deadline=run.deadline,
        )
    except _CredentialHeaderError as exc:
        return _Attempt((), b"", str(exc))
    except _HttpBodyError as exc:
        return _Attempt((), b"", exc.reason)
    except (
        OSError,
        ValueError,
        http_client.HTTPException,
        subprocess.TimeoutExpired,
    ) as exc:
        return _Attempt(
            (), b"", "timed out" if _is_timeout_failure(exc) else "request failed"
        )


def _credit_result(
    source: str, request: FanoutRequest, primary: _Attempt, run: _CreditRun
) -> _Fetch:
    boundaries, deadline, started = run.boundaries, run.deadline, run.started
    envelope = _transport_envelope(primary)
    reason = _redact_request_text(
        primary.stderr_redacted.strip()
        or primary.raw.decode(errors="replace").strip()
        or primary.error
        or "credits-exhausted",
        dict(os.environ),
    ).replace("\n", " | ")[-300:]
    attempts = [
        RouteAttempt(source, Status.SKIPPED, primary.http_status, reason, None, None)
    ]
    evidence: list[bytes | None] = [envelope]
    final = primary
    status = Status.SKIPPED
    route = None
    control = None
    genuine_error = None
    genuine_raw = None
    for fallback in _FALLBACK_ROUTES.get(source, ()):
        key = _FALLBACK_KEYS[fallback]
        if not os.environ.get(key):
            attempts.append(
                RouteAttempt(
                    fallback,
                    Status.SKIPPED,
                    None,
                    f"{key} not inherited; run through fnox exec",
                    None,
                    None,
                )
            )
            evidence.append(None)
            continue
        final = _fallback_attempt(fallback, request, run)
        fallback_status = Status.ERROR
        fallback_reason = final.error
        body_text = final.raw.decode(errors="replace")
        if final.error and _fallback_credit(final.http_status, body_text):
            fallback_status = Status.SKIPPED
            fallback_reason = (
                final.raw.decode(errors="replace").strip() or final.error
            )[-300:]
        elif final.error:
            genuine_error = final.error
            genuine_raw = final.raw
        elif final.items:
            fallback_status = Status.OK
        else:
            control, _error = _empty_control(
                fallback, request, boundaries=boundaries, deadline=deadline
            )
            fallback_status = (
                Status.EMPTY_VERIFIED if control.count else Status.EMPTY_UNVERIFIED
            )
            fallback_reason = None if control.count else "canary failed"
            if not control.count:
                genuine_error = fallback_reason
                genuine_raw = final.raw
        attempts.append(
            RouteAttempt(
                fallback,
                fallback_status,
                final.http_status,
                fallback_reason,
                None,
                None,
            )
        )
        evidence.append(
            _transport_envelope(final)
            if fallback_status is Status.SKIPPED
            else final.raw
        )
        if fallback_status in {Status.OK, Status.EMPTY_VERIFIED}:
            status, route, reason = fallback_status, fallback, None
            break
    if route is None and genuine_error:
        status, reason = Status.ERROR, genuine_error
    result = SourceResult(
        source,
        status,
        final.items if route else (),
        time.monotonic() - started,
        reason,
        control if route else None,
        None,
        skip_reason=SkipReason.CREDITS_EXHAUSTED if status is Status.SKIPPED else None,
        route=route,
        provisional=status is Status.SKIPPED or route is not None,
        attempts=tuple(attempts),
    )
    return _Fetch(
        result,
        final.raw if route else genuine_raw if status is Status.ERROR else envelope,
        tuple(evidence),
    )


def _source_result(
    source: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    http: Http,
) -> _Fetch:
    started = time.monotonic()
    boundaries = _Boundaries(runner, http)
    prerequisite = _prerequisite_reason(source, request)
    if prerequisite:
        result = SourceResult(
            source,
            Status.SKIPPED,
            (),
            time.monotonic() - started,
            prerequisite,
            None,
            None,
            skip_reason=SkipReason.PREREQUISITE,
        )
        return _Fetch(result, None)
    deadline = _Deadline.after(_timeout_for(source, request.timeout))
    raw: bytes | None = None
    try:
        attempt = _primary_attempt(
            source,
            request.query,
            request,
            boundaries=boundaries,
            deadline=deadline,
        )
        raw = attempt.raw
        if (
            source in CREDIT_METERED_SOURCES
            and attempt.error
            and _attempt_credit(attempt)
        ):
            return _credit_result(
                source, request, attempt, _CreditRun(boundaries, deadline, started)
            )
        if attempt.error:
            status = Status.ERROR
            reason = attempt.error
            control = None
        elif attempt.items:
            status = Status.OK
            reason = None
            control = None
        else:
            control, canary_error = _empty_control(
                source,
                request,
                boundaries=boundaries,
                deadline=deadline,
            )
            if control.count:
                status = Status.EMPTY_VERIFIED
                reason = None
            else:
                status = Status.EMPTY_UNVERIFIED
                reason = (
                    "no canary"
                    if source == "last30days"
                    else "canary failed"
                    if canary_error
                    else "canary returned 0 items"
                )
        items = attempt.items
    except _CredentialHeaderError as exc:
        status = Status.ERROR
        reason = str(exc)
        control = None
        items = ()
    except _HttpBodyError as exc:
        status = Status.ERROR
        reason = exc.reason
        control = None
        items = ()
    except TimeoutError, subprocess.TimeoutExpired:
        status = Status.ERROR
        reason = "timed out"
        control = None
        items = ()
    except (http_client.HTTPException, ValueError, OSError) as exc:
        status = Status.ERROR
        reason = "timed out" if _is_timeout_failure(exc) else "request failed"
        control = None
        items = ()
    result = SourceResult(
        source,
        status,
        items,
        time.monotonic() - started,
        reason,
        control,
        None,
    )
    return _Fetch(result, raw)


def _is_timeout_failure(exc: BaseException) -> bool:
    return isinstance(exc, TimeoutError | subprocess.TimeoutExpired) or isinstance(
        getattr(exc, "reason", None), TimeoutError
    )


def _fan_out_with_raw(
    request: FanoutRequest,
    *,
    runner: Runner,
    http: Http,
) -> list[_Fetch]:
    if not request.sources:
        return []
    try:
        with ThreadPoolExecutor(max_workers=len(request.sources)) as executor:
            futures = [
                executor.submit(
                    _source_result,
                    source,
                    request,
                    runner=runner,
                    http=http,
                )
                for source in request.sources
            ]
            try:
                return [future.result() for future in futures]
            except KeyboardInterrupt:
                _cancel_live_processes()
                for future in futures:
                    future.cancel()
                raise
    finally:
        _CANCEL_CHILDREN.clear()


def fan_out(
    request: FanoutRequest,
    *,
    runner: Runner = default_runner,
    http: Http = default_http,
) -> list[SourceResult]:
    """Fetch all requested sources concurrently in request order."""
    return [
        fetched.result
        for fetched in _fan_out_with_raw(request, runner=runner, http=http)
    ]


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="research-fanout")
    parser.add_argument("query", metavar="QUERY", nargs="?")
    parser.add_argument("--repo")
    parser.add_argument("--sources")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--strict-five", action="store_true")
    parser.add_argument("--request-id")
    parser.add_argument("--last30days-plan", type=Path)
    # Probe mode (#1514): record real exit codes instead of agent-typed ones.
    parser.add_argument("--probe-out")
    parser.add_argument("--code-search", action="append", metavar="ROLE=QUERY")
    parser.add_argument("--repo-check", action="append", metavar="OWNER/REPO")
    parser.add_argument("--fanout-manifest", action="append", type=Path)
    parser.add_argument("--require", metavar="SOURCES")
    parser.add_argument("--max-age", type=float, metavar="SECONDS")
    parser.add_argument("--expect-request-id", metavar="ID")
    parser.add_argument("--mirror-url")
    parser.add_argument("--mirror-path", type=Path)
    parser.add_argument("--mirror-index", type=Path, metavar="DIR")
    parser.add_argument("--mirror-count", type=int)
    return parser


_PROBE_ONLY_FLAGS = (
    "code_search",
    "repo_check",
    "fanout_manifest",
    "require",
    "max_age",
    "expect_request_id",
    "mirror_url",
    "mirror_path",
    "mirror_index",
    "mirror_count",
)


def _parse_sources(value: str | None, repo: str | None) -> tuple[str, ...]:
    if value is None:
        probe = FanoutRequest("", repo, (), 10, None)
        return tuple(
            source
            for source in _DEFAULT_CANDIDATES
            if _prerequisite_reason(source, probe) is None
        )
    requested = tuple(dict.fromkeys(part.strip() for part in value.split(",")))
    if not requested or "" in requested:
        message = "--sources must contain at least one source name"
        raise _UsageError(message)
    unknown = [source for source in requested if source not in _SOURCE_NAMES]
    if unknown:
        message = f"unknown source(s): {', '.join(unknown)}"
        raise _UsageError(message)
    return requested


def _presence(source: str, request: FanoutRequest) -> str:
    """`present`, `needs --repo` (gh works, no repo given) or `absent`.

    A github source with gh on PATH is usable the moment a repo is named, so
    reporting it `absent` made planners drop GitHub entirely (2026-09-30).
    """
    reason = _prerequisite_reason(source, request)
    if reason is None:
        return "present"
    if reason == "needs --repo" and shutil.which("gh") is not None:
        return "needs --repo"
    return "absent"


def _list_sources(repo: str | None) -> None:
    probe = FanoutRequest("", repo, (), 10, None)
    for source in _SOURCE_NAMES:
        transport, prerequisite = _SOURCE_DETAILS[source]
        presence = _presence(source, probe)
        sys.stdout.write(f"{source}  {transport}  {prerequisite}  {presence}\n")
    for route, transport in (("serper", "HTTPS POST"), ("serpapi", "HTTPS GET")):
        key = _FALLBACK_KEYS[route]
        presence = "present" if os.environ.get(key) else "absent"
        sys.stdout.write(
            f"fallback:{route}  {transport}  {key} in process environment  {presence}\n"
        )
    presence = "present" if shutil.which("webclaw") else "absent"
    sys.stdout.write(f"fallback:webclaw  webclaw CLI  webclaw on PATH  {presence}\n")


def _validate_args(args: argparse.Namespace) -> None:
    if args.list_sources:
        return
    if not args.query:
        message = "QUERY is required unless --list-sources"
        raise _UsageError(message)
    if args.limit <= 0:
        message = "--limit must be greater than zero"
        raise _UsageError(message)
    if args.timeout is not None and args.timeout <= 0:
        message = "--timeout must be greater than zero"
        raise _UsageError(message)
    if args.strict_five:
        if not args.repo or not args.request_id or args.last30days_plan is None:
            message = (
                "--strict-five requires --repo, --request-id, and --last30days-plan"
            )
            raise _UsageError(message)
        if args.sources is not None and set(args.sources.split(",")) != set(
            _SOURCE_NAMES
        ):
            message = "--strict-five requires every named source"
            raise _UsageError(message)
        try:
            plan = json.loads(args.last30days_plan.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            message = "--last30days-plan must be readable JSON"
            raise _UsageError(message) from exc
        if not isinstance(plan, dict) or not plan.get("subqueries"):
            message = "--last30days-plan needs subqueries"
            raise _UsageError(message)


def _slug(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.casefold()).strip("-")
    return (slug or "research")[:_MAX_SLUG].rstrip("-")


def _json_default(value: object) -> str:
    if isinstance(value, Enum):
        return value.value
    message = f"cannot serialize {type(value).__name__}"
    raise TypeError(message)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, default=_json_default, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _persist(
    out_dir: Path,
    request: FanoutRequest,
    fetched: list[_Fetch],
    *,
    request_id: str | None = None,
    strict_five: bool = False,
) -> tuple[Path, list[SourceResult]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    owned_names = ["manifest.json"]
    for source in _SOURCE_NAMES:
        owned_names.extend((f"{source}.json", f"{source}.raw", f"{source}.primary.raw"))
        owned_names.extend(
            f"{source}.{route}.raw" for route in _FALLBACK_ROUTES.get(source, ())
        )
    for name in owned_names:
        (out_dir / name).unlink(missing_ok=True)
    results: list[SourceResult] = []
    for outcome in fetched:
        raw_path: Path | None = None
        if outcome.raw is not None:
            raw_path = out_dir / f"{outcome.result.source}.raw"
            raw_path.write_bytes(outcome.raw)
        persisted_attempts = []
        for attempt, evidence in zip(
            outcome.result.attempts, outcome.attempt_raw, strict=True
        ):
            attempt_path = None
            if evidence is not None:
                label = (
                    "primary"
                    if attempt.route == outcome.result.source
                    else attempt.route
                )
                attempt_path = out_dir / f"{outcome.result.source}.{label}.raw"
                attempt_path.write_bytes(evidence)
            persisted_attempts.append(
                replace(
                    attempt,
                    raw_file=str(attempt_path) if attempt_path else None,
                    raw_sha256=hashlib.sha256(evidence).hexdigest()
                    if evidence is not None
                    else None,
                )
            )
        result = replace(
            outcome.result,
            attempts=tuple(persisted_attempts),
            raw_file=str(raw_path) if raw_path is not None else None,
            raw_sha256=(
                hashlib.sha256(outcome.raw).hexdigest()
                if outcome.raw is not None
                else None
            ),
        )
        _write_json(out_dir / f"{result.source}.json", asdict(result))
        results.append(result)
    manifest_path = out_dir / "manifest.json"
    _write_json(
        manifest_path,
        {
            "query": request.query,
            "repo": request.repo,
            "request_id": request_id,
            "strict_five": strict_five,
            "policy_version": "strict-five-v2" if strict_five else None,
            "generated_at": datetime.now(UTC).isoformat(),
            "sources": [asdict(result) for result in results],
            "out_dir": str(out_dir),
        },
    )
    return manifest_path, results


def _validate_row_status(row: dict[str, object]) -> str | None:
    source = row["source"]
    status = row["status"]
    if status not in {Status.OK.value, Status.EMPTY_VERIFIED.value}:
        return f"{source} did not complete"
    items = row.get("items")
    if not isinstance(items, list):
        return f"{source} has no normalized result list"
    if status == Status.OK.value and not items:
        return f"{source} has no results despite ok status"
    if status == Status.EMPTY_VERIFIED.value:
        control = row.get("control")
        if (
            items
            or not isinstance(control, dict)
            or not isinstance(control.get("query"), str)
            or not control["query"]
            or not isinstance(control.get("count"), int)
            or control["count"] <= 0
        ):
            return f"{source} empty result lacks a positive control"
    return None


def _valid_json_response(source: str, payload: object, status: object) -> bool:
    if source == "github-releases":
        return isinstance(payload, list)
    if not isinstance(payload, dict):
        return False
    list_key = {
        "github-issues": "items",
        "exa": "results",
        "firecrawl-developer": "results",
    }.get(source)
    if source == "firecrawl-search":
        data = payload.get("data")
        web = data.get("web") if isinstance(data, dict) else None
        valid = isinstance(web, list) and (status != Status.OK.value or bool(web))
    elif list_key is not None:
        raw_items = payload.get(list_key)
        valid = isinstance(raw_items, list) and (
            status != Status.OK.value or bool(raw_items)
        )
    else:
        data = payload.get("data")
        search = data.get("search") if isinstance(data, dict) else None
        valid = (
            source == "github-discussions"
            and isinstance(search, dict)
            and isinstance(search.get("nodes"), list)
            and not payload.get("errors")
        )
    if source == "exa":
        valid = valid and bool(payload.get("requestId"))
    if source in {"firecrawl-developer", "firecrawl-search"}:
        valid = valid and payload.get("success") is True
    return valid


def _valid_last30days_response(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    source_status = payload.get("source_status")
    return bool(
        payload.get("schema_version")
        and isinstance(source_status, dict)
        and source_status
        and all(status == "ok" for status in source_status.values())
    )


def _validate_raw_response(source: str, raw: bytes, status: object) -> str | None:
    if source == "context7":
        return None
    payload = json.loads(raw)
    if source == "last30days":
        if not _valid_last30days_response(payload):
            return "last30days schema or internal source failure"
    elif not _valid_json_response(source, payload, status):
        return f"{source} raw evidence is not a successful response"
    return None


def _validate_strict_row(row: dict[str, object], manifest_path: Path) -> str | None:
    source = row["source"]
    if not isinstance(source, str):
        return "research source name is malformed"
    if reason := _validate_row_status(row):
        return reason
    raw_file = row.get("raw_file")
    if not isinstance(raw_file, str) or Path(raw_file) != (
        manifest_path.parent / f"{source}.raw"
    ):
        return f"{source} has no bound raw evidence"
    raw = Path(raw_file).read_bytes()
    if not raw:
        return f"{source} raw evidence is empty"
    if row.get("raw_sha256") != hashlib.sha256(raw).hexdigest():
        return f"{source} raw evidence hash is missing or changed"
    return _validate_raw_response(source, raw, row["status"])


@dataclass(frozen=True)
class ProvisionalEntry:
    """Validated source and optional winning route for answer enforcement."""

    source: str
    route: str | None


@dataclass(frozen=True)
class StrictVerdict:
    """A validated receipt, including explicit provisional provenance."""

    passed: bool
    provisional: tuple[str, ...]
    reason: str
    provisional_entries: tuple[ProvisionalEntry, ...] = ()


def _provisional_line(row: dict[str, object]) -> str:
    source = str(row.get("source", "unknown"))
    attempts = row.get("attempts")
    errors = []
    if isinstance(attempts, list) and attempts:
        for attempt in attempts[1:]:
            if not isinstance(attempt, dict) or attempt.get("status") not in {
                Status.ERROR.value,
                Status.SKIPPED.value,
            }:
                continue
            if attempt.get("status") == Status.SKIPPED.value:
                code = (
                    FailureCode.CREDITS_EXHAUSTED
                    if attempt.get("raw_file")
                    else FailureCode.PREREQUISITE
                )
            else:
                code = failure_code(attempt.get("reason"), status=attempt.get("status"))
            errors.append(f"{attempt.get('route')}: {code.value if code else ''}")
    line = (
        f"{source} via {row['route']} (credits-exhausted)"
        if row.get("route")
        else f"{source} skipped: credits-exhausted; "
        + (
            "no fallback succeeded"
            if _FALLBACK_ROUTES.get(source)
            else "no fallback route"
        )
    )
    return line + ("; " + "; ".join(errors) if errors else "")


class _ReceiptError(ValueError):
    """A specific validation failure safe to report to the caller."""


def _bound_raw(file: object, digest: object, expected: Path) -> bytes:
    if not isinstance(file, str) or Path(file) != expected:
        message = "unbound raw evidence"
        raise _ReceiptError(message)
    raw = Path(file).read_bytes()
    if digest != hashlib.sha256(raw).hexdigest():
        message = "raw evidence hash is missing or changed"
        raise _ReceiptError(message)
    return raw


def _validate_credit_status(row: dict[str, object]) -> None:
    source = str(row["source"])
    route = row.get("route")
    if row.get("provisional") is not True or source not in CREDIT_METERED_SOURCES:
        message = "invalid provisional source"
        raise _ReceiptError(message)
    if route:
        if route not in _FALLBACK_ROUTES.get(source, ()):
            message = "invalid fallback route"
            raise _ReceiptError(message)
        if reason := _validate_row_status(row):
            raise _ReceiptError(reason.removeprefix(source + " "))
    elif (
        row.get("status") != Status.SKIPPED.value
        or row.get("skip_reason") != SkipReason.CREDITS_EXHAUSTED.value
    ):
        message = "invalid credit skip"
        raise _ReceiptError(message)


def _credit_attempts(
    row: dict[str, object], directory: Path
) -> tuple[list[dict[str, object]], bytes]:
    source = str(row["source"])
    attempts = row.get("attempts")
    if (
        not isinstance(attempts, list)
        or not attempts
        or not isinstance(attempts[0], dict)
        or attempts[0].get("route") != source
    ):
        message = "missing primary attempt"
        raise _ReceiptError(message)
    allowed = (source, *_FALLBACK_ROUTES.get(source, ()))
    seen = []
    primary_raw = b""
    for attempt in attempts:
        if not isinstance(attempt, dict) or attempt.get("route") not in allowed:
            message = "invalid attempt route"
            raise _ReceiptError(message)
        route = attempt["route"]
        if route in seen:
            message = "duplicated attempt route"
            raise _ReceiptError(message)
        seen.append(route)
        if attempt.get("raw_file") is None:
            if route == source:
                message = "missing attempt evidence"
                raise _ReceiptError(message)
            _validate_fallback_prerequisite(attempt, str(route))
            continue
        label = "primary" if route == source else route
        raw = _bound_raw(
            attempt.get("raw_file"),
            attempt.get("raw_sha256"),
            directory / f"{source}.{label}.raw",
        )
        if route == source:
            primary_raw = raw
        elif attempt.get("status") == Status.SKIPPED.value:
            _validate_fallback_credit(raw)
    return attempts, primary_raw


def _validate_fallback_prerequisite(attempt: dict[str, object], route: str) -> None:
    if (
        attempt.get("raw_sha256") is not None
        or attempt.get("status") != Status.SKIPPED.value
        or attempt.get("reason")
        != f"{_FALLBACK_KEYS[route]} not inherited; run through fnox exec"
    ):
        message = "invalid fallback prerequisite skip"
        raise _ReceiptError(message)


def _validate_fallback_credit(raw: bytes) -> None:
    try:
        transport = _decode_transport_envelope(raw)
    except ValueError:
        message = "fallback credit skip does not re-derive"
        raise _ReceiptError(message) from None
    if (
        type(transport.http_status) is not int
        or transport.rc is not None
        or not _fallback_credit(
            transport.http_status, transport.raw.decode(errors="replace")
        )
    ):
        message = "fallback credit skip does not re-derive"
        raise _ReceiptError(message)


def _decode_transport_envelope(raw: bytes) -> _Attempt:
    envelope = _decode_json(raw)
    if (
        not isinstance(envelope, dict)
        or not isinstance(envelope.get("body"), str)
        or not isinstance(envelope.get("stderr_redacted"), str)
    ):
        message = "malformed primary envelope"
        raise _ReceiptError(message)
    status, rc = envelope.get("http_status"), envelope.get("rc")
    if (status is not None and (type(status) is not int or rc is not None)) or (
        status is None and type(rc) is not int
    ):
        message = "malformed primary transport"
        raise _ReceiptError(message)
    return _Attempt(
        (),
        envelope["body"].encode(),
        "provider failure",
        http_status=status,
        rc=rc,
        stderr_redacted=envelope["stderr_redacted"],
    )


def _credit_envelope(raw: bytes) -> _Attempt:
    attempt = _decode_transport_envelope(raw)
    if not _attempt_credit(attempt):
        message = "credit-exhaustion evidence does not re-derive"
        raise _ReceiptError(message)
    return attempt


def _validate_credit_output(
    row: dict[str, object],
    attempts: list[dict[str, object]],
    raw: bytes,
    primary_raw: bytes,
) -> None:
    route = row.get("route")
    if not route:
        if raw != primary_raw or any(
            a.get("status") in {Status.ERROR.value, Status.EMPTY_UNVERIFIED.value}
            for a in attempts
        ):
            message = "invalid credit skip evidence"
            raise _ReceiptError(message)
        return
    winning = next((a for a in attempts if a.get("route") == route), None)
    if (
        not winning
        or winning.get("status") != row["status"]
        or winning.get("raw_sha256") != row.get("raw_sha256")
    ):
        message = "missing winning route evidence"
        raise _ReceiptError(message)
    payload = _decode_json(raw)
    records = _fallback_records(payload, str(route))
    if records is None or (row["status"] == Status.OK.value and not records):
        message = "raw evidence is not a successful fallback response"
        raise _ReceiptError(message)


def _validate_provisional_row(
    row: dict[str, object], manifest_path: Path
) -> str | None:
    source = str(row["source"])
    try:
        _validate_credit_status(row)
        attempts, primary_raw = _credit_attempts(row, manifest_path.parent)
        _credit_envelope(primary_raw)
        raw = _bound_raw(
            row.get("raw_file"),
            row.get("raw_sha256"),
            manifest_path.parent / f"{source}.raw",
        )
        _validate_credit_output(row, attempts, raw, primary_raw)
    except _ReceiptError as exc:
        return f"{source} {exc}"
    return None


def strict_five_verdict(manifest_path: Path, request_id: str) -> StrictVerdict:
    """Validate same-turn hashed evidence and re-derive every credit exception."""
    provisional = []
    provisional_entries = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return StrictVerdict(
                passed=False, provisional=(), reason="malformed research manifest"
            )
        if (
            not manifest.get("strict_five")
            or manifest.get("policy_version") != "strict-five-v2"
            or manifest.get("request_id") != request_id
            or not manifest.get("query")
            or not manifest.get("repo")
        ):
            return StrictVerdict(
                passed=False,
                provisional=(),
                reason="request identity or policy mismatch",
            )
        rows = manifest["sources"]
        if (
            not isinstance(rows, list)
            or len(rows) != len(_SOURCE_NAMES)
            or any(not isinstance(row, dict) for row in rows)
            or {row["source"] for row in rows} != set(_SOURCE_NAMES)
        ):
            return StrictVerdict(
                passed=False,
                provisional=(),
                reason="required source missing or duplicated",
            )
        for row in rows:
            reason = (
                _validate_provisional_row(row, manifest_path)
                if row.get("provisional")
                or row.get("route")
                or row.get("skip_reason") == SkipReason.CREDITS_EXHAUSTED.value
                else _validate_strict_row(row, manifest_path)
            )
            if reason:
                return StrictVerdict(passed=False, provisional=(), reason=reason)
            if row.get("provisional"):
                provisional.append(_provisional_line(row))
                provisional_entries.append(
                    ProvisionalEntry(row["source"], row.get("route"))
                )
    except OSError, ValueError, KeyError, TypeError, AttributeError:
        return StrictVerdict(
            passed=False,
            provisional=(),
            reason="malformed or unreadable research evidence",
        )
    reason = (
        "provisional: " + "; ".join(provisional)
        if provisional
        else "all required sources completed"
    )
    return StrictVerdict(
        passed=True,
        provisional=tuple(provisional),
        reason=reason,
        provisional_entries=tuple(provisional_entries),
    )


def validate_strict_five(manifest_path: Path, request_id: str) -> tuple[bool, str]:
    """Keep the existing verdict-pair interface for callers."""
    verdict = strict_five_verdict(manifest_path, request_id)
    return verdict.passed, verdict.reason


# Probe mode (#1514). A saved workflow has no filesystem or shell of its own
# (`$CC/workflows.md:355`), so its mandatory-stage checks used to read numbers an
# agent TYPED after running gh/firecrawl itself — an rc, a count, a byte size, an
# HTTP status read off a header. Probe mode runs those calls here and records
# what they really returned; the agent's whole job shrinks to running one
# workflow-built command and copying its final `PROBE-JSON` line verbatim.
_PROBE_ROLES = frozenset({"query", "must-hit", "known-absent", "health", "readme"})
_PROBE_JSON_PREFIX = "PROBE-JSON "
_DEFAULT_MANIFEST_MAX_AGE_S = 3600.0
_MANIFEST_CLOCK_SKEW_S = 60.0
# GitHub's code-search bucket is 10 requests/min; a wait longer than one window
# means a different limit, so the probe records it instead of sleeping on it.
_RATE_LIMIT_WAIT_CAP_S = 60.0
_HTTP_CLIENT_ERROR = 400
_HTTP_FORBIDDEN = 403
_HTTP_TOO_MANY = 429
_RC_TIMEOUT = 124
_RC_NOT_FOUND = 127
_REPO_SHAPE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_STATUS_LINE = re.compile(r"^HTTP/\S+\s+(\d{3})")
_GH_HTTP_ERROR = re.compile(r"\(HTTP (\d{3})\)")
_HEAD_BODY_SPLIT = re.compile(r"\r?\n\r?\n")


class Sleeper(Protocol):
    """Injected wait boundary (rate-limit backoff)."""

    def __call__(self, seconds: float, /) -> None:
        """Block for ``seconds``."""
        ...


class Clock(Protocol):
    """Injected wall clock (rate-limit reset and manifest age)."""

    def __call__(self) -> float:
        """Return the current UNIX time in seconds."""
        ...


@dataclass(frozen=True)
class _ProbeSpec:
    probe_out: str
    manifest: Path
    code_searches: tuple[tuple[str, str], ...]
    repo_checks: tuple[str, ...]
    fanout_manifests: tuple[Path, ...]
    required: tuple[str, ...]
    max_age_s: float
    expect_request_id: str | None
    mirror: tuple[str, Path] | None
    mirror_index: tuple[Path, int] | None
    timeout: float


@dataclass(frozen=True)
class ProbeTiming:
    """The wait and clock boundaries probe mode reads; injected by tests."""

    sleep: Sleeper
    clock: Clock


_REAL_TIMING = ProbeTiming(time.sleep, time.time)


@dataclass(frozen=True)
class _ProbeBoundaries:
    runner: Runner
    sleep: Sleeper
    clock: Clock


@dataclass(frozen=True)
class _GhResponse:
    rc: int
    status: int
    body: object | None
    rate_limited: bool


def _repo_ok(repo: str) -> bool:
    # A dot-only segment is shell-safe but turns `repos/<r>` into another API path.
    return bool(_REPO_SHAPE.match(repo)) and not any(
        re.fullmatch(r"\.+", part) for part in repo.split("/")
    )


def _parse_gh_include(
    completed: subprocess.CompletedProcess[bytes],
) -> tuple[int, dict[str, str], object | None, str]:
    """Split `gh api -i` output into status, lower-cased headers, JSON body, text."""
    out = (completed.stdout or b"").decode(errors="replace")
    err = (completed.stderr or b"").decode(errors="replace")
    head, body = (*_HEAD_BODY_SPLIT.split(out, maxsplit=1), "")[:2]
    lines = head.splitlines()
    status_match = _STATUS_LINE.match(lines[0]) if lines else None
    fallback = _GH_HTTP_ERROR.search(err)
    status = int(
        status_match.group(1) if status_match else fallback.group(1) if fallback else 0
    )
    headers = {
        name.strip().lower(): value.strip()
        for name, sep, value in (line.partition(":") for line in lines[1:])
        if sep
    }
    try:
        payload: object | None = _decode_json(body.encode()) if body.strip() else None
    except ValueError:
        payload = None
    return status, headers, payload, f"{body}\n{err}"


def _rate_limit_wait(headers: dict[str, str], clock: Clock) -> float | None:
    retry_after = headers.get("retry-after", "")
    if retry_after.isdigit():
        return float(retry_after)
    reset = headers.get("x-ratelimit-reset", "")
    if reset.isdigit():
        return max(0.0, float(reset) - clock())
    return None


def _gh_include(
    tail: list[str], *, boundaries: _ProbeBoundaries, timeout: float
) -> _GhResponse:
    """One `gh api -i` call, retried ONCE after a short documented rate-limit wait."""
    for attempt in range(2):
        try:
            completed = boundaries.runner(
                ["gh", "api", "-i", *tail], timeout=timeout, env=_gh_env()
            )
        except subprocess.TimeoutExpired:
            return _GhResponse(_RC_TIMEOUT, 0, None, rate_limited=False)
        except FileNotFoundError:
            return _GhResponse(_RC_NOT_FOUND, 0, None, rate_limited=False)
        status, headers, payload, text = _parse_gh_include(completed)
        rate_limited = status == _HTTP_TOO_MANY or (
            status == _HTTP_FORBIDDEN
            and (
                headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in text.casefold()
            )
        )
        wait = _rate_limit_wait(headers, boundaries.clock) if rate_limited else None
        if attempt == 0 and wait is not None and wait <= _RATE_LIMIT_WAIT_CAP_S:
            boundaries.sleep(wait + 1.0)
            continue
        return _GhResponse(completed.returncode, status, payload, rate_limited)
    message = "unreachable: the retry loop always returns"
    raise AssertionError(message)


def _code_search_probe(
    role: str, query: str, *, boundaries: _ProbeBoundaries, timeout: float
) -> dict[str, object]:
    response = _gh_include(
        ["-X", "GET", "search/code", "-f", f"q={query}"],
        boundaries=boundaries,
        timeout=timeout,
    )
    total = (
        response.body.get("total_count") if isinstance(response.body, dict) else None
    )
    # -1 = "no count": a failed or rate-limited search is never a zero.
    count = total if response.rc == 0 and isinstance(total, int) else -1
    return {
        "kind": "code-search",
        "role": role,
        "query": query,
        "rc": response.rc,
        "http_status": response.status,
        "count": count,
        "rate_limited": response.rate_limited,
        # GitHub sets this when the search timed out: its total (often 0) is
        # not an answer, so the workflow never reads it as absence.
        "incomplete_results": isinstance(response.body, dict)
        and response.body.get("incomplete_results") is True,
    }


def _repo_check_probe(
    repo: str, *, boundaries: _ProbeBoundaries, timeout: float
) -> dict[str, object]:
    response = _gh_include([f"repos/{repo}"], boundaries=boundaries, timeout=timeout)
    body = response.body if isinstance(response.body, dict) else {}
    full_name = body.get("full_name")
    return {
        "kind": "repo-check",
        "repo": repo,
        "rc": response.rc,
        "http_status": response.status,
        # Trimmed: a stray newline must never read as a rename (round-4 L5).
        "full_name": full_name.strip()
        if response.status == _HTTP_OK
        and isinstance(full_name, str)
        and _REPO_SHAPE.fullmatch(full_name.strip())
        else "",
        "rate_limited": response.rate_limited,
        # A DISABLED tracker is the world, not a failed search: a repo with
        # Discussions off answers empty_unverified forever (cold review F1).
        "has_issues": body.get("has_issues")
        if isinstance(body.get("has_issues"), bool)
        else None,
        # search/issues also returns PRs, so issues off + PRs on is still live.
        "has_pull_requests": body.get("has_pull_requests")
        if isinstance(body.get("has_pull_requests"), bool)
        else None,
        "has_discussions": body.get("has_discussions")
        if isinstance(body.get("has_discussions"), bool)
        else None,
    }


def _manifest_age(manifest: dict[str, object], clock: Clock) -> float | None:
    stamp = manifest.get("generated_at")
    if not isinstance(stamp, str):
        return None
    try:
        return clock() - datetime.fromisoformat(stamp).timestamp()
    except ValueError:
        return None


def _fanout_manifest_probe(
    path: Path,
    required: tuple[str, ...],
    *,
    max_age_s: float,
    clock: Clock,
    expect_request_id: str | None,
) -> dict[str, object]:
    """Read one fan-out manifest: which query REALLY ran, and each source's status.

    The process rc of `research-fanout` is 0 when ANY source answered, so a
    dependency run whose github-issues search failed read as a success (#1473).
    """
    row: dict[str, object] = {
        "kind": "fanout-manifest",
        "path": str(path),
        "exists": path.is_file(),
        "query": None,
        "age_s": None,
        "fresh": False,
        "sources": {},
        "required_failed": [],
        "provisional": [],
        "provisional_invalid": False,
    }
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        rows = manifest["sources"]
        statuses = {
            r["source"]: (r["status"], r.get("reason"), r.get("skip_reason"))
            for r in rows
            if isinstance(r, dict)
            and isinstance(r.get("source"), str)
            and r["source"] in _SOURCE_NAMES
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        reason = "no manifest" if isinstance(exc, FileNotFoundError) else "unreadable"
        row["required_failed"] = [f"{name}: {reason}" for name in required]
        return row
    provisional = []
    for candidate in rows:
        if not isinstance(candidate, dict) or candidate.get("provisional") is not True:
            continue
        source, route = candidate.get("source"), candidate.get("route")
        if (
            isinstance(source, str)
            and source in CREDIT_METERED_SOURCES
            and (route is None or route in _FALLBACK_ROUTES.get(source, ()))
        ):
            provisional.append({"source": source, "route": route})
        else:
            row["provisional_invalid"] = True
    row["provisional"] = provisional[: len(_SOURCE_NAMES)]
    age = _manifest_age(manifest, clock)
    row["query"] = manifest.get("query")
    row["age_s"] = None if age is None else round(age, 1)
    # An agent that skipped its run leaves the PREVIOUS sweep's manifest behind.
    # With a per-run request id, "fresh" means THIS run's, not merely recent.
    row["request_id"] = manifest.get("request_id")
    row["fresh"] = (
        age is not None
        and -_MANIFEST_CLOCK_SKEW_S <= age <= max_age_s
        and (expect_request_id is None or row["request_id"] == expect_request_id)
    )
    status_values = tuple(s.value for s in Status)
    row["sources"] = {
        name: status if status in status_values else "invalid"
        for name, (status, _, _) in statuses.items()
    }
    successful = {Status.OK.value, Status.EMPTY_VERIFIED.value}
    failed = []
    for name in required:
        status, reason, skip = statuses.get(name, (None, None, None))
        if status not in tuple(successful):
            projected_status = (
                "not run"
                if status is None
                else status
                if status in status_values
                else "invalid"
            )
            code = failure_code(reason, status=status, skip_reason=skip)
            detail = f" ({code.value})" if code else ""
            failed.append(f"{name}: {projected_status}{detail}")
    row["required_failed"] = failed[: len(_SOURCE_NAMES)]
    return row


def _webclaw_mirror(
    url: str, path: Path, runner: Runner, timeout: float
) -> tuple[int, str, str]:
    try:
        completed = runner(
            ["webclaw", "-f", "json", url], timeout=timeout, env=child_env.clean_env()
        )
    except FileNotFoundError:
        return (
            _RC_NOT_FOUND,
            "credits-exhausted; webclaw not found on PATH",
            FailureCode.NOT_FOUND.value,
        )
    except subprocess.TimeoutExpired:
        return (
            _RC_TIMEOUT,
            "credits-exhausted; webclaw timed out",
            FailureCode.TIMEOUT.value,
        )
    if completed.returncode != 0:
        return (
            completed.returncode,
            f"credits-exhausted; webclaw rc={completed.returncode}",
            FailureCode.PROCESS_FAILED.value,
        )
    return _write_webclaw_mirror(completed.stdout or b"", url, path)


def _write_webclaw_mirror(raw: bytes, url: str, path: Path) -> tuple[int, str, str]:
    try:
        payload = _decode_json(raw)
        content = payload.get("content") if isinstance(payload, dict) else None
        metadata = payload.get("metadata") if isinstance(payload, dict) else None
        markdown = content.get("markdown") if isinstance(content, dict) else None
        final = metadata.get("url") if isinstance(metadata, dict) else None
        requested = urllib.parse.urlsplit(url)
        actual = urllib.parse.urlsplit(final) if isinstance(final, str) else None
        if actual is None or (
            requested.scheme.casefold(),
            requested.netloc.casefold(),
            requested.path.rstrip("/"),
        ) != (
            actual.scheme.casefold(),
            actual.netloc.casefold(),
            actual.path.rstrip("/"),
        ):
            return (
                0,
                "credits-exhausted; webclaw redirected to "
                + _redact_text(str(final), dict(os.environ)),
                FailureCode.REDIRECTED.value,
            )
        if not isinstance(markdown, str) or not markdown.strip():
            return (
                0,
                "credits-exhausted; webclaw rc=0, empty markdown",
                FailureCode.EMPTY_OUTPUT.value,
            )
        path.write_text(_redact_text(markdown, dict(os.environ)), encoding="utf-8")
    except ValueError:
        return (
            0,
            "credits-exhausted; webclaw output was not JSON",
            FailureCode.INVALID_JSON.value,
        )
    return 0, "", ""


def _mirror_probe(
    url: str, path: Path, *, runner: Runner, timeout: float
) -> dict[str, object]:
    """Persist a validated native scrape, or a credit-triggered webclaw mirror."""
    row: dict[str, object] = {
        "kind": "mirror",
        "url": url,
        "path": str(path),
        "route": "firecrawl",
        "provisional": False,
        "detail": {"reason": "", "primary_reason": ""},
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
    except OSError as exc:
        return {
            **row,
            "rc": 1,
            "http_status": 0,
            "bytes": 0,
            "code": FailureCode.IO_ERROR.value,
            "detail": {
                "reason": f"cannot prepare {path}: {type(exc).__name__}",
                "primary_reason": "",
            },
        }
    env = child_env.clean_env(keep=frozenset({"FIRECRAWL_API_KEY"}))
    status = 0
    primary_reason = ""
    deadline = _Deadline.after(timeout)
    try:
        completed = runner(
            [
                "firecrawl",
                "scrape",
                url,
                "--format",
                "markdown",
                "--only-main-content",
                "--json",
            ],
            timeout=deadline.remaining(),
            env=env,
        )
        rc = completed.returncode
        redacted = _redacted_stderr(completed, env)
        raw = _redact_text(
            (completed.stdout or b"").decode(errors="replace"), env
        ).encode()
        reason = next((p.strip() for p in redacted.splitlines() if p.strip()), "")
        code = FailureCode.PROCESS_FAILED.value if rc else ""
        failure_payload = False
        claimed_status = None
        if rc == 0:
            status, markdown, reason, code = _scrape_payload(raw)
            try:
                payload = _decode_json(raw)
                failure_payload = (
                    isinstance(payload, dict) and payload.get("success") is False
                )
                if (
                    failure_payload
                    and isinstance(payload, dict)
                    and isinstance(payload.get("status"), int)
                ):
                    claimed_status = payload["status"]
            except ValueError:
                pass
            if markdown and not reason:
                path.write_text(markdown, encoding="utf-8")
        credit = (rc != 0 or failure_payload) and is_credit_exhaustion(
            claimed_status, redacted + "\n" + raw.decode(errors="replace")
        )
        if credit:
            primary_reason = (redacted.strip() or raw.decode(errors="replace")).replace(
                "\n", " | "
            )[-300:]
            row["route"] = "webclaw"
            rc, reason, code = _webclaw_mirror(url, path, runner, deadline.remaining())
            status = 0
            row["provisional"] = rc == 0 and not reason
    except subprocess.TimeoutExpired, TimeoutError:
        rc, reason = _RC_TIMEOUT, "timed out"
        code = FailureCode.TIMEOUT.value
    except FileNotFoundError:
        rc, reason = _RC_NOT_FOUND, "firecrawl not found on PATH"
        code = FailureCode.NOT_FOUND.value
    size = path.stat().st_size if path.is_file() else 0
    if not reason and not (rc == 0 and size > 0):
        reason = f"rc={rc}, {size} bytes"
        code = (
            FailureCode.EMPTY_OUTPUT.value
            if rc == 0
            else FailureCode.PROCESS_FAILED.value
        )
    return {
        **row,
        "rc": rc,
        "http_status": status,
        "bytes": size,
        "code": code,
        "detail": {"reason": reason, "primary_reason": primary_reason},
    }


def _scrape_payload(raw: bytes) -> tuple[int, str, str, str]:
    """(HTTP status, markdown, failure reason) from `firecrawl scrape --json`."""
    try:
        payload = _decode_json(raw)
    except ValueError:
        return 0, "", "firecrawl output was not JSON", FailureCode.INVALID_JSON.value
    if isinstance(payload, dict) and payload.get("success") is False:
        return 0, "", "firecrawl reported failure", FailureCode.PROVIDER_FAILURE.value
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return 0, "", "unexpected firecrawl JSON shape", FailureCode.SHAPE_ERROR.value
    metadata = data.get("metadata")
    status = metadata.get("statusCode") if isinstance(metadata, dict) else None
    status = status if isinstance(status, int) else 0
    markdown = data.get("markdown")
    markdown = markdown if isinstance(markdown, str) else ""
    reason = f"HTTP {status}" if status >= _HTTP_CLIENT_ERROR else ""
    return status, markdown, reason, FailureCode.HTTP_ERROR.value if reason else ""


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _mirror_code(row: dict[str, object]) -> str:
    code = row.get("code")
    if not isinstance(code, str) or code not in ("", *(c.value for c in FailureCode)):
        message = "invalid mirror code"
        raise ValueError(message)
    return code


def _mirror_index_probe(
    directory: Path, count: int, *, clock: Clock, max_age_s: float
) -> dict[str, object]:
    """Write the mirror README from the mirror probes on disk, not from agent rows.

    A probe file older than ``max_age_s`` is an EARLIER sweep's (its mirror agent
    did not run this time), so it is listed as missing, never as a mirror.
    """
    rows = []
    missing = 0
    for n in range(1, count + 1):
        try:
            data = json.loads((directory / f"{n}.probe.json").read_text("utf-8"))
            mirror = next(p for p in data["probes"] if p["kind"] == "mirror")
            code = _mirror_code(mirror)
            age = _manifest_age(data, clock)
            if age is None or not -_MANIFEST_CLOCK_SKEW_S <= age <= max_age_s:
                missing += 1
                rows.append(
                    (
                        n,
                        mirror["url"],
                        f"{n}.md",
                        "",
                        0,
                        "stale probe from an earlier run",
                        "",
                    )
                )
                continue
            rows.append(
                (
                    n,
                    mirror["url"],
                    Path(mirror["path"]).name,
                    mirror["rc"],
                    mirror["bytes"],
                    code,
                    mirror.get("route", ""),
                )
            )
        except OSError, ValueError, KeyError, TypeError, StopIteration:
            missing += 1
            rows.append(
                (
                    n,
                    "(unknown)",
                    f"{n}.md",
                    "",
                    0,
                    "mirror probe missing or unreadable",
                    "",
                )
            )
    readme = directory / "README.md"
    lines = [
        f"# Offline mirrors — {directory.parent.name}",
        "",
        (
            "Caller links fetched with `firecrawl scrape <url> --format markdown "
            "--only-main-content --json` (the pinned binary, via `mise run "
            "research-fanout -- --probe-out`); a page answering HTTP >= 400 is a "
            "failure whatever its size. Every value below is read from the "
            "`<n>.probe.json` beside it. When firecrawl answered credit exhaustion "
            "the link was fetched with `webclaw -f json` instead "
            "(route `webclaw`, provisional). The failure code is a fixed value; "
            "diagnostics are in each "
            "`<n>.probe.json` `detail`."
        ),
        "",
        "| n | url | file | rc | bytes | failure code | route |",
        "|---|---|---|---|---|---|---|",
        *("| " + " | ".join(_cell(v) for v in row) + " |" for row in rows),
    ]
    try:
        directory.mkdir(parents=True, exist_ok=True)
        readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written = True
    except OSError:
        written = False
    return {
        "kind": "mirror-index",
        "path": str(readme),
        "rows": count,
        "missing": missing,
        "written": written,
    }


def _probe_code_searches(args: argparse.Namespace) -> tuple[tuple[str, str], ...]:
    searches = []
    for item in args.code_search or ():
        role, sep, query = item.partition("=")
        if not sep or role not in _PROBE_ROLES or not query.strip():
            message = (
                f"--code-search must be ROLE=QUERY, ROLE in {sorted(_PROBE_ROLES)}"
            )
            raise _UsageError(message)
        searches.append((role, query))
    return tuple(searches)


def _probe_required(args: argparse.Namespace) -> tuple[str, ...]:
    required = tuple(r for r in (args.require or "").split(",") if r)
    if unknown := [r for r in required if r not in _SOURCE_NAMES]:
        message = f"unknown --require source(s): {', '.join(unknown)}"
        raise _UsageError(message)
    if required and not args.fanout_manifest:
        message = "--require needs --fanout-manifest"
        raise _UsageError(message)
    return required


def _probe_mirror_flags(args: argparse.Namespace) -> None:
    if (args.mirror_url is None) != (args.mirror_path is None):
        message = "--mirror-url and --mirror-path go together"
        raise _UsageError(message)
    if (args.mirror_index is None) != (args.mirror_count is None) or (
        args.mirror_count is not None and args.mirror_count < 0
    ):
        message = "--mirror-index needs --mirror-count >= 0 (and vice versa)"
        raise _UsageError(message)


def _probe_spec(args: argparse.Namespace, repo_root: Path) -> _ProbeSpec:
    """Validate probe-mode flags; every failure is a usage error (rc 2)."""

    def resolve(value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else repo_root / path

    fanout_only = (args.query, args.sources, args.repo, args.out, args.request_id)
    if any(fanout_only) or args.strict_five or args.list_sources:
        message = (
            "--probe-out takes no QUERY, --sources, --repo, --out, --request-id,"
            " --strict-five or --list-sources"
        )
        raise _UsageError(message)
    if args.last30days_plan is not None:
        message = "--probe-out takes no --last30days-plan"
        raise _UsageError(message)
    if (args.max_age is not None and args.max_age < 0) or (
        args.timeout is not None and args.timeout <= 0
    ):
        message = "--max-age must be >= 0 and --timeout > 0"
        raise _UsageError(message)
    searches = _probe_code_searches(args)
    repos = tuple(args.repo_check or ())
    if bad := [repo for repo in repos if not _repo_ok(repo)]:
        message = f"--repo-check must be owner/repo with no dot-only segment: {bad}"
        raise _UsageError(message)
    required = _probe_required(args)
    _probe_mirror_flags(args)
    mirror = (args.mirror_url, resolve(args.mirror_path)) if args.mirror_url else None
    index = (
        None
        if args.mirror_index is None
        else (resolve(args.mirror_index), args.mirror_count)
    )
    fanouts = tuple(resolve(p) for p in args.fanout_manifest or ())
    if not (searches or repos or fanouts or mirror or index):
        message = "--probe-out needs at least one probe"
        raise _UsageError(message)
    return _ProbeSpec(
        probe_out=args.probe_out,
        manifest=resolve(args.probe_out),
        code_searches=searches,
        repo_checks=repos,
        fanout_manifests=fanouts,
        required=required,
        max_age_s=_DEFAULT_MANIFEST_MAX_AGE_S if args.max_age is None else args.max_age,
        expect_request_id=args.expect_request_id,
        mirror=mirror,
        mirror_index=index,
        timeout=args.timeout or _DEFAULT_TIMEOUT,
    )


def run_probes(
    spec: _ProbeSpec, boundaries: _ProbeBoundaries
) -> list[dict[str, object]]:
    """Run this invocation's probes one after another (the search bucket is shared).

    Only WITHIN one invocation: the workflow runs several probe invocations at
    once, so the 10/min bucket is still shared across them; the one retry after
    a short documented reset is the mitigation (cold review F11).
    """
    probes: list[dict[str, object]] = [
        _code_search_probe(role, query, boundaries=boundaries, timeout=spec.timeout)
        for role, query in spec.code_searches
    ]
    probes += [
        _repo_check_probe(repo, boundaries=boundaries, timeout=spec.timeout)
        for repo in spec.repo_checks
    ]
    probes += [
        _fanout_manifest_probe(
            path,
            spec.required,
            max_age_s=spec.max_age_s,
            clock=boundaries.clock,
            expect_request_id=spec.expect_request_id,
        )
        for path in spec.fanout_manifests
    ]
    if spec.mirror is not None:
        url, path = spec.mirror
        probes.append(
            _mirror_probe(url, path, runner=boundaries.runner, timeout=spec.timeout)
        )
    if spec.mirror_index is not None:
        directory, count = spec.mirror_index
        probes.append(
            _mirror_index_probe(
                directory, count, clock=boundaries.clock, max_age_s=spec.max_age_s
            )
        )
    return probes


def _probe_main(spec: _ProbeSpec, boundaries: _ProbeBoundaries) -> int:
    probes = run_probes(spec, boundaries)
    payload = {
        "kind": "probe",
        # Exactly the string the caller passed, so a workflow can check that the
        # manifest an agent hands back is the one it asked for.
        "probe_out": spec.probe_out,
        "manifest": str(spec.manifest),
        "generated_at": datetime.fromtimestamp(boundaries.clock(), UTC).isoformat(),
        "probes": probes,
    }
    try:
        spec.manifest.parent.mkdir(parents=True, exist_ok=True)
        _write_json(spec.manifest, payload)
    except OSError as exc:
        sys.stderr.write(
            f"research-fanout: could not write probe output ({type(exc).__name__})\n"
        )
        return 1
    probes = [{k: v for k, v in probe.items() if k != "detail"} for probe in probes]
    payload["probes"] = probes
    sys.stdout.write(f"{spec.manifest}\n")
    for probe in probes:
        rest = {k: v for k, v in probe.items() if k != "kind"}
        sys.stdout.write(f"{probe['kind']}  {json.dumps(rest, sort_keys=True)}\n")
    sys.stdout.write(
        _PROBE_JSON_PREFIX
        + json.dumps(payload, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    return 0


def _print_summary(manifest_path: Path, results: list[SourceResult]) -> None:
    sys.stdout.write(f"{manifest_path}\n")
    for result in results:
        code = failure_code(
            result.reason,
            status=result.status.value,
            skip_reason=result.skip_reason.value if result.skip_reason else None,
        )
        detail = code.value if code else None
        if code is FailureCode.PREREQUISITE and result.reason in _PREREQUISITE_TEXTS:
            detail = f"prerequisite: {result.reason}"
        if result.provisional:
            row = json.loads(json.dumps(asdict(result), default=_json_default))
            line = _provisional_line(row)
            if result.route:
                detail = "provisional: " + line
            else:
                detail = line.removeprefix(result.source + " ")
        reason = f"  [{detail}]" if detail else ""
        sys.stdout.write(
            f"{result.source}  {result.status.value}  {len(result.items)} items  "
            f"{result.elapsed_s:.3f}s{reason}\n"
        )


def _validate_mode(args: argparse.Namespace) -> None:
    if given := [f for f in _PROBE_ONLY_FLAGS if getattr(args, f) is not None]:
        flags = ", ".join("--" + f.replace("_", "-") for f in given)
        message = f"{flags} only apply with --probe-out"
        raise _UsageError(message)


def _run_fanout(
    args: argparse.Namespace,
    sources: tuple[str, ...],
    repo_root: Path,
    *,
    runner: Runner,
    http: Http,
) -> int:
    out_dir = args.out or (
        repo_root / ".agent/kb/raw/research-fanout" / _slug(args.query)
    )
    out_dir = out_dir.expanduser()
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    if args.strict_five:
        sources = _SOURCE_NAMES
    request = FanoutRequest(
        args.query, args.repo, sources, args.limit, args.timeout, args.last30days_plan
    )
    try:
        fetched = _fan_out_with_raw(request, runner=runner, http=http)
    except KeyboardInterrupt:
        return 130
    try:
        manifest_path, results = _persist(
            out_dir,
            request,
            fetched,
            request_id=args.request_id,
            strict_five=args.strict_five,
        )
    except OSError as exc:
        sys.stderr.write(
            f"research-fanout: could not write output ({type(exc).__name__})\n"
        )
        return 1
    _print_summary(manifest_path, results)
    if args.strict_five:
        passed, reason = validate_strict_five(manifest_path, args.request_id)
        sys.stdout.write(f"strict-five  {'pass' if passed else 'fail'}  [{reason}]\n")
        return 0 if passed else 1
    successful = {Status.OK, Status.EMPTY_VERIFIED}
    return 0 if any(result.status in successful for result in results) else 1


def main(
    argv: list[str],
    repo_root: Path,
    *,
    runner: Runner = default_runner,
    http: Http = default_http,
    timing: ProbeTiming = _REAL_TIMING,
) -> int:
    """Run the research fanout CLI and return its process exit code."""
    try:
        args = _parser().parse_args(argv)
        if args.probe_out is not None:
            spec = _probe_spec(args, repo_root)
            return _probe_main(
                spec, _ProbeBoundaries(runner, timing.sleep, timing.clock)
            )
        _validate_mode(args)
        sources = _parse_sources(args.sources, args.repo)
        _validate_args(args)
        if args.list_sources:
            _list_sources(args.repo)
            return 0
    except _UsageError as exc:
        sys.stderr.write(f"research-fanout: {exc}\n")
        return 2
    return _run_fanout(args, sources, repo_root, runner=runner, http=http)


def _repo_root() -> Path:
    return Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], _repo_root()))
