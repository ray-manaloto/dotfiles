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
        if response.status == _HTTP_OK and isinstance(full_name, str)
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
    }
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        rows = manifest["sources"]
        statuses = {r["source"]: (r["status"], r.get("reason")) for r in rows}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        reason = "no manifest" if isinstance(exc, FileNotFoundError) else "unreadable"
        row["required_failed"] = [f"{name}: {reason}" for name in required]
        return row
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
    row["sources"] = {name: status for name, (status, _) in statuses.items()}
    successful = {Status.OK.value, Status.EMPTY_VERIFIED.value}
    failed = []
    for name in required:
        status, reason = statuses.get(name, (None, None))
        if status not in successful:
            detail = f" ({reason})" if reason else ""
            failed.append(f"{name}: {status or 'not run'}{detail}")
    row["required_failed"] = failed
    return row


def _mirror_probe(
    url: str, path: Path, *, runner: Runner, timeout: float
) -> dict[str, object]:
    """Save one caller link with the pinned firecrawl and measure what landed.

    `--json` carries the page's HTTP status: firecrawl exits 0 and returns a
    full body for a 404 (measured 2026-10-02: a 328-byte "Error 404" page), so a
    size check alone saves an error page as a successful mirror.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # A failed scrape must not leave an EARLIER sweep's file to be measured.
        path.unlink(missing_ok=True)
    except OSError as exc:
        return {
            "kind": "mirror",
            "url": url,
            "path": str(path),
            "rc": 1,
            "http_status": 0,
            "bytes": 0,
            "reason": f"cannot prepare {path}: {type(exc).__name__}",
        }
    env = child_env.clean_env(keep=frozenset({"FIRECRAWL_API_KEY"}))
    argv = [
        "firecrawl",
        "scrape",
        url,
        "--format",
        "markdown",
        "--only-main-content",
        "--json",
    ]
    status = 0
    try:
        completed = runner(argv, timeout=timeout, env=env)
        rc = completed.returncode
        # _subprocess_error redacts credentials and joins stderr lines with " | ".
        redacted = _subprocess_error(completed, env).partition(": ")[2]
        reason = next((p.strip() for p in redacted.split(" | ") if p.strip()), "")
        if rc == 0:
            status, markdown, reason = _scrape_payload(completed.stdout or b"")
            # An error page is never saved: later sweeps grep these mirrors.
            if markdown and not reason:
                path.write_text(markdown, encoding="utf-8")
    except subprocess.TimeoutExpired:
        rc, reason = _RC_TIMEOUT, "timed out"
    except FileNotFoundError:
        rc, reason = _RC_NOT_FOUND, "firecrawl not found on PATH"
    size = path.stat().st_size if path.is_file() else 0
    if not reason and not (rc == 0 and size > 0):
        reason = f"rc={rc}, {size} bytes"
    return {
        "kind": "mirror",
        "url": url,
        "path": str(path),
        "rc": rc,
        "http_status": status,
        "bytes": size,
        "reason": reason,
    }


def _scrape_payload(raw: bytes) -> tuple[int, str, str]:
    """(HTTP status, markdown, failure reason) from `firecrawl scrape --json`."""
    try:
        payload = _decode_json(raw)
    except ValueError:
        return 0, "", "firecrawl output was not JSON"
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return 0, "", "unexpected firecrawl JSON shape"
    metadata = data.get("metadata")
    status = metadata.get("statusCode") if isinstance(metadata, dict) else None
    status = status if isinstance(status, int) else 0
    markdown = data.get("markdown")
    markdown = markdown if isinstance(markdown, str) else ""
    reason = f"HTTP {status}" if status >= _HTTP_CLIENT_ERROR else ""
    return status, markdown, reason


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


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
                    mirror["reason"],
                )
            )
        except OSError, ValueError, KeyError, TypeError, StopIteration:
            missing += 1
            rows.append(
                (n, "(unknown)", f"{n}.md", "", 0, "mirror probe missing or unreadable")
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
            "`<n>.probe.json` beside it."
        ),
        "",
        "| n | url | file | rc | bytes | failure reason |",
        "|---|---|---|---|---|---|",
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
        reason = f"  [{result.reason}]" if result.reason else ""
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
