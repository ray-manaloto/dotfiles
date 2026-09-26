# Copyright (c) 2026 Raymond Manaloto
"""Tests for the no-LLM multi-source research fetcher."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_fanout import (
    Endpoint,
    FanoutRequest,
    Status,
    fan_out,
    main,
)


def _completed(
    argv: list[str], rc: int, stdout: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=b"")


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


def test_nonzero_subprocess_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_path_tools(tmp_path, monkeypatch, "firecrawl")
    runner = ScriptedRunner([_completed(["firecrawl"], 7)])

    [result] = fan_out(
        FanoutRequest("topic", None, ("firecrawl-search",), 10, 5.0),
        runner=runner,
        http=FakeHttp({}),
    )

    assert result.status is Status.ERROR
    assert result.reason == "exited 7"
    assert result.status not in {Status.EMPTY_VERIFIED, Status.EMPTY_UNVERIFIED}


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
    ("source", "stdout", "expected_title"),
    [
        (
            "github-issues",
            (
                b'{"items":[{"title":"Issue","html_url":'
                b'"https://github.test/i/1","body":"body",'
                b'"created_at":"2026-09-01"}]}'
            ),
            "Issue",
        ),
        (
            "github-discussions",
            (
                b'{"data":{"search":{"nodes":[{"title":"Discussion",'
                b'"url":"https://github.test/d/1","bodyText":"body",'
                b'"createdAt":"2026-09-02"}]}}}'
            ),
            "Discussion",
        ),
        (
            "github-releases",
            (
                b'[{"tag_name":"v1.2.3","html_url":'
                b'"https://github.test/r/1","body":"topic fixed",'
                b'"published_at":"2026-09-03"}]'
            ),
            "v1.2.3",
        ),
        (
            "firecrawl-search",
            b'{"data":[{"title":"Search","url":"https://search.test/1","description":"body"}]}',
            "Search",
        ),
    ],
)
def test_subprocess_sources_normalize_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    stdout: bytes,
    expected_title: str,
) -> None:
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
    assert len(result.items[0].snippet) <= 500


def test_github_release_empty_checks_repo_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_path_tools(tmp_path, monkeypatch, "gh")
    runner = ScriptedRunner(
        [
            _completed(["gh"], 0, b"[]"),
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
    assert runner.calls[1][0] == ["ctx7", "docs", "/owner/library", "topic"]


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


def test_last30days_is_opt_in_and_scrubs_llm_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "last30days.py"
    script.write_text("# test boundary\n", encoding="utf-8")
    monkeypatch.setenv("LAST30DAYS_SCRIPT", str(script))
    github_credential = str(tmp_path / "github-credential")
    monkeypatch.setenv("GITHUB_TOKEN", github_credential)
    monkeypatch.setenv("OPENAI_API_KEY", "llm-secret")
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
    assert env["GITHUB_TOKEN"] == github_credential
    assert "OPENAI_API_KEY" not in env
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
    monkeypatch.setenv("PATH", "")
    for name in (
        "EXA_API_KEY",
        "LAST30DAYS_SCRIPT",
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
