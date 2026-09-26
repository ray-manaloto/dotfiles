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
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Never, Protocol

from dotfiles_setup import child_env

_DEFAULT_TIMEOUT = 60.0
_LAST30DAYS_TIMEOUT = 180.0
_MAX_SNIPPET = 500
_MAX_SLUG = 60
_HTTP_OK = 200
_HTTP_REDIRECT = 300
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
    "exa": ("HTTPS POST", "EXA_API_KEY set"),
    "context7": ("ctx7 CLI", "ctx7 on PATH"),
    "firecrawl-developer": ("HTTPS GET", "none"),
    "firecrawl-search": ("firecrawl CLI", "firecrawl on PATH"),
    "last30days": ("python3 script", "last30days script found"),
}


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


@dataclass(frozen=True)
class FanoutRequest:
    """Inputs shared by every source in a fanout."""

    query: str
    repo: str | None
    sources: tuple[str, ...]
    limit: int
    timeout: float | None


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


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise _UsageError(message)


def default_runner(
    argv: list[str], *, timeout: float, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    """Run one child with captured byte streams and an explicit timeout."""
    return subprocess.run(
        argv,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def default_http(
    endpoint: Endpoint,
    *,
    params: dict[str, str | int] | None,
    body: dict[str, object] | None,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, bytes]:
    """Call one fixed HTTPS API and preserve its response bytes."""
    if endpoint is Endpoint.EXA_SEARCH:
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.exa.ai/search",
                    data=json.dumps(body or {}).encode(),
                    headers=headers,
                    method="POST",
                ),
                timeout=timeout,
            ) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
    if endpoint is Endpoint.FIRECRAWL_DEVELOPER:
        query = urllib.parse.urlencode(params or {})
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.firecrawl.dev/v2/search/developer?{query}",
                    headers=headers,
                    method="GET",
                ),
                timeout=timeout,
            ) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
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
    url = record.get("url") or record.get("html_url")
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
        return None, raw, f"exited {completed.returncode}"
    try:
        return _decode_json(raw), raw, None
    except ValueError:
        return None, raw, "invalid JSON"


def _gh_env() -> dict[str, str]:
    return child_env.clean_env(keep=frozenset({"GITHUB_TOKEN", "GH_TOKEN"}))


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
    if not isinstance(payload, dict) or payload.get("errors"):
        return _Attempt((), raw, "GraphQL response contained errors")
    data = payload.get("data")
    search = data.get("search") if isinstance(data, dict) else None
    nodes = search.get("nodes") if isinstance(search, dict) else None
    records = nodes if isinstance(nodes, list) else []
    items = tuple(
        item
        for record in records[: request.limit]
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
        ["gh", "api", f"repos/{repo}/releases?per_page={request.limit}"],
        runner=runner,
        deadline=deadline,
        env=_gh_env(),
    )
    if error:
        return _Attempt((), raw, error)
    if not isinstance(payload, list):
        return _Attempt((), raw, "unexpected JSON shape")
    terms = re.findall(r"[a-z0-9]+", query.casefold())
    items: list[Item] = []
    for record in payload[: request.limit]:
        if not isinstance(record, dict):
            continue
        url = record.get("html_url")
        if not isinstance(url, str) or not url:
            continue
        tag = str(record.get("tag_name") or record.get("name") or url)
        body = str(record.get("body") or "").casefold()
        mentions = any(term in body for term in terms)
        date = record.get("published_at") or record.get("created_at")
        items.append(
            Item(
                tag,
                url,
                f"release body mentions a query term: {'yes' if mentions else 'no'}",
                str(date) if date is not None else None,
            )
        )
    return _Attempt(tuple(items), raw)


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
                "x-api-key": os.environ.get("EXA_API_KEY", ""),
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
        headers["Authorization"] = f"Bearer {key}"
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
    library = runner(["ctx7", "library", query], timeout=deadline.remaining(), env=env)
    library_raw = library.stdout or b""
    if library.returncode != 0:
        return _Attempt((), library_raw, f"exited {library.returncode}")
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
        return _Attempt((), docs_raw, f"exited {docs.returncode}")
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
        reason = "needs EXA_API_KEY"
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
        attempt = _primary_attempt(
            source,
            query,
            request,
            boundaries=boundaries,
            deadline=deadline,
        )
    except TimeoutError, subprocess.TimeoutExpired, OSError:
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
    except TimeoutError, subprocess.TimeoutExpired:
        status = Status.ERROR
        reason = "timed out"
        control = None
        items = ()
    except OSError:
        status = Status.ERROR
        reason = "request failed"
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


def _fan_out_with_raw(
    request: FanoutRequest,
    *,
    runner: Runner,
    http: Http,
) -> list[_Fetch]:
    if not request.sources:
        return []
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
        return [future.result() for future in futures]


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


def _list_sources(repo: str | None) -> None:
    probe = FanoutRequest("", repo, (), 10, None)
    for source in _SOURCE_NAMES:
        transport, prerequisite = _SOURCE_DETAILS[source]
        presence = (
            "present" if _prerequisite_reason(source, probe) is None else "absent"
        )
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
    query: str,
    repo: str | None,
    fetched: list[_Fetch],
) -> tuple[Path, list[SourceResult]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[SourceResult] = []
    for outcome in fetched:
        raw_path: Path | None = None
        if outcome.raw is not None:
            raw_path = out_dir / f"{outcome.result.source}.raw"
            raw_path.write_bytes(outcome.raw)
        result = replace(
            outcome.result,
            raw_file=str(raw_path) if raw_path is not None else None,
        )
        _write_json(out_dir / f"{result.source}.json", asdict(result))
        results.append(result)
    manifest_path = out_dir / "manifest.json"
    _write_json(
        manifest_path,
        {
            "query": query,
            "repo": repo,
            "sources": [asdict(result) for result in results],
            "out_dir": str(out_dir),
        },
    )
    return manifest_path, results


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
    request = FanoutRequest(args.query, args.repo, sources, args.limit, args.timeout)
    fetched = _fan_out_with_raw(request, runner=runner, http=http)
    try:
        manifest_path, results = _persist(out_dir, args.query, args.repo, fetched)
    except OSError as exc:
        sys.stderr.write(
            f"research-fanout: could not write output ({type(exc).__name__})\n"
        )
        return 1
    _print_summary(manifest_path, results)
    successful = {Status.OK, Status.EMPTY_VERIFIED}
    return 0 if any(result.status in successful for result in results) else 1


def _repo_root() -> Path:
    return Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], _repo_root()))
