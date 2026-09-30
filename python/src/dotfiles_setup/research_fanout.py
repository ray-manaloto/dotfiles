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


class Endpoint(Enum):
    """HTTP destinations accepted by the injected transport boundary."""

    EXA_SEARCH = "exa-search"
    FIRECRAWL_DEVELOPER = "firecrawl-developer"


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


@dataclass(frozen=True)
class _Fetch:
    result: SourceResult
    raw: bytes | None


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
    message = f"unsupported endpoint: {endpoint.value}"
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
) -> tuple[object | None, bytes, str | None]:
    completed = runner(argv, timeout=deadline.remaining(), env=env)
    raw = completed.stdout or b""
    if completed.returncode != 0:
        return None, raw, _subprocess_error(completed, env)
    try:
        return _decode_json(raw), raw, None
    except ValueError:
        return None, raw, "invalid JSON"


def _gh_env() -> dict[str, str]:
    return child_env.clean_env(keep=frozenset({"GITHUB_TOKEN", "GH_TOKEN"}))


def _subprocess_error(
    completed: subprocess.CompletedProcess[bytes], env: dict[str, str]
) -> str:
    stderr = (completed.stderr or b"").decode(errors="replace")
    credential_values = sorted(
        (
            value
            for name, value in env.items()
            if value and child_env.is_credential(name)
        ),
        key=len,
        reverse=True,
    )
    for value in credential_values:
        stderr = stderr.replace(value, "[REDACTED]")
    stderr = stderr.replace("\r\n", "\n").replace("\r", "\n")
    stderr = stderr.replace("\n", " | ")
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
    payload, raw, error = _run_json(
        ["gh", "api", endpoint], runner=runner, deadline=deadline, env=_gh_env()
    )
    if error:
        return _Attempt((), raw, error)
    return _Attempt(_items_from_payload(payload, limit=request.limit), raw)


def _github_discussions(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    repo = _required_repo(request)
    payload, raw, error = _run_json(
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
        return _Attempt((), raw, error)
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
    payload, raw, error = _run_json(
        ["gh", "api", f"repos/{repo}/releases?per_page=100"],
        runner=runner,
        deadline=deadline,
        env=_gh_env(),
    )
    if error:
        return _Attempt((), raw, error)
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
    payload, _raw, error = _run_json(
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
        return _Attempt((), raw, f"HTTP {status}")
    try:
        payload = _decode_json(raw)
    except ValueError:
        return _Attempt((), raw, "invalid JSON")
    return _Attempt(_items_from_payload(payload, limit=request.limit), raw)


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


def _firecrawl_search(
    query: str,
    request: FanoutRequest,
    *,
    runner: Runner,
    deadline: _Deadline,
) -> _Attempt:
    payload, raw, error = _run_json(
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
        return _Attempt((), raw, error)
    return _Attempt(_items_from_payload(payload, limit=request.limit), raw)


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
        return _Attempt((), library_raw, _subprocess_error(library, env))
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
        return _Attempt((), docs_raw, _subprocess_error(docs, env))
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
    payload, raw, error = _run_json(
        argv,
        runner=runner,
        deadline=deadline,
        env=_last30days_env(),
    )
    if error:
        return _Attempt((), raw, error)
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
    if source == "github-issues":
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
    if source in {"exa", "context7", "firecrawl-developer", "firecrawl-search"}:
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
    return parser


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
        owned_names.extend((f"{source}.json", f"{source}.raw"))
    for name in owned_names:
        (out_dir / name).unlink(missing_ok=True)
    results: list[SourceResult] = []
    for outcome in fetched:
        raw_path: Path | None = None
        if outcome.raw is not None:
            raw_path = out_dir / f"{outcome.result.source}.raw"
            raw_path.write_bytes(outcome.raw)
        result = replace(
            outcome.result,
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
            "policy_version": "strict-five-v1" if strict_five else None,
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


def validate_strict_five(manifest_path: Path, request_id: str) -> tuple[bool, str]:
    """Reject partial or reused five-provider evidence after it is persisted."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False, "malformed research manifest"
        if (
            not manifest.get("strict_five")
            or manifest.get("policy_version") != "strict-five-v1"
            or manifest.get("request_id") != request_id
            or not manifest.get("query")
            or not manifest.get("repo")
        ):
            return False, "request identity or policy mismatch"
        rows = manifest["sources"]
        if (
            not isinstance(rows, list)
            or len(rows) != len(_SOURCE_NAMES)
            or any(not isinstance(row, dict) for row in rows)
            or {row["source"] for row in rows} != set(_SOURCE_NAMES)
        ):
            return False, "required source missing or duplicated"
        for row in rows:
            if reason := _validate_strict_row(row, manifest_path):
                return False, reason
    except OSError, ValueError, KeyError, TypeError, AttributeError:
        return False, "malformed or unreadable research evidence"
    return True, "all required sources completed"


def _print_summary(manifest_path: Path, results: list[SourceResult]) -> None:
    sys.stdout.write(f"{manifest_path}\n")
    for result in results:
        reason = f"  [{result.reason}]" if result.reason else ""
        sys.stdout.write(
            f"{result.source}  {result.status.value}  {len(result.items)} items  "
            f"{result.elapsed_s:.3f}s{reason}\n"
        )


def main(
    argv: list[str],
    repo_root: Path,
    *,
    runner: Runner = default_runner,
    http: Http = default_http,
) -> int:
    """Run the research fanout CLI and return its process exit code."""
    try:
        args = _parser().parse_args(argv)
        sources = _parse_sources(args.sources, args.repo)
        _validate_args(args)
        if args.list_sources:
            _list_sources(args.repo)
            return 0
    except _UsageError as exc:
        sys.stderr.write(f"research-fanout: {exc}\n")
        return 2
    out_dir = args.out or (
        repo_root / ".agent/kb/raw/research-fanout" / _slug(args.query)
    )
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


def _repo_root() -> Path:
    return Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], _repo_root()))
