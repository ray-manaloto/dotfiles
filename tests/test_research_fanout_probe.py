# Copyright (c) 2026 Raymond Manaloto
"""Probe mode of research-fanout (#1514, #1473): real exit codes, not typed ones.

The research-sweep workflow has no filesystem or shell of its own, so its
mandatory-stage checks used to read numbers an agent typed. Probe mode makes the
calls itself and records what they returned; these tests pin that record.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_fanout import ProbeTiming, main

_NOW = 1_800_000_000.0


def _gh_out(status: int, body: object, headers: dict[str, str] | None = None) -> bytes:
    reason = {200: "OK", 403: "Forbidden", 404: "Not Found", 422: "Unprocessable"}
    head = [f"HTTP/2.0 {status} {reason.get(status, 'X')}"]
    head += [f"{k}: {v}" for k, v in (headers or {}).items()]
    return ("\r\n".join(head) + "\r\n\r\n" + json.dumps(body)).encode()


@dataclass
class Runner:
    """Subprocess double: each argv is answered by the first matching handler."""

    handlers: list[Callable[[list[str]], subprocess.CompletedProcess[bytes] | None]]
    calls: list[list[str]] = field(default_factory=list)

    def __call__(
        self, argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        """Record the spawn and return the first handler's answer."""
        del timeout, env
        self.calls.append(argv)
        for handler in self.handlers:
            answer = handler(argv)
            if answer is not None:
                return answer
        message = f"unexpected subprocess call: {argv}"
        raise AssertionError(message)


def _done(
    argv: list[str], rc: int, out: bytes = b"", err: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(argv, rc, stdout=out, stderr=err)


@dataclass
class Timing:
    """A clock frozen at _NOW plus a recording sleeper."""

    slept: list[float] = field(default_factory=list)

    def timing(self) -> ProbeTiming:
        """Build the injectable boundary."""
        return ProbeTiming(self.slept.append, lambda: _NOW)


def _probe(
    tmp_path: Path,
    argv: list[str],
    runner: Runner,
    capsys: pytest.CaptureFixture[str],
    timing: Timing | None = None,
) -> tuple[int, dict[str, object]]:
    rc = main(
        ["--probe-out", "out/probe.json", *argv],
        tmp_path,
        runner=runner,
        timing=(timing or Timing()).timing(),
    )
    stdout = capsys.readouterr().out
    lines = [ln for ln in stdout.splitlines() if ln.startswith("PROBE-JSON ")]
    payload = json.loads(lines[-1].removeprefix("PROBE-JSON ")) if lines else {}
    return rc, payload


def _only(payload: dict[str, object]) -> dict[str, object]:
    probes = payload["probes"]
    assert isinstance(probes, list)
    assert len(probes) == 1
    return probes[0]


def test_code_search_records_the_real_count_and_echoes_the_probe_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = Runner([lambda a: _done(a, 0, _gh_out(200, {"total_count": 9}))])
    rc, payload = _probe(
        tmp_path,
        ["--code-search", "health=repo:cli/cli filename:README.md"],
        runner,
        capsys,
    )

    assert rc == 0
    # the exact string the workflow put in the command, so it can check it
    assert payload["probe_out"] == "out/probe.json"
    assert payload["manifest"] == str(tmp_path / "out/probe.json")
    on_disk = json.loads((tmp_path / "out/probe.json").read_text(encoding="utf-8"))
    assert on_disk == payload
    assert _only(payload) == {
        "kind": "code-search",
        "role": "health",
        "query": "repo:cli/cli filename:README.md",
        "rc": 0,
        "http_status": 200,
        "count": 9,
        "rate_limited": False,
    }
    argv = runner.calls[0]
    assert argv[:6] == ["gh", "api", "-i", "-X", "GET", "search/code"]
    assert argv[6:] == ["-f", "q=repo:cli/cli filename:README.md"]


@pytest.mark.parametrize(
    "case",
    [
        (403, {"X-Ratelimit-Remaining": "0"}, {"message": "x"}, True),
        (403, {}, {"message": "API rate limit exceeded for user"}, True),
        (429, {}, {"message": "slow down"}, True),
        # control arm: a plain 403 is FORBIDDEN, not a rate limit
        (
            403,
            {"X-Ratelimit-Remaining": "8"},
            {"message": "Resource not accessible"},
            False,
        ),
        (422, {}, {"message": "Validation Failed"}, False),
    ],
)
def test_failed_code_search_is_never_a_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: tuple[int, dict[str, str], object, bool],
) -> None:
    """A failed or rate-limited search is count -1 (no count), never 0."""
    status, headers, body, rate_limited = case
    runner = Runner([lambda a: _done(a, 1, _gh_out(status, body, headers))])
    _, payload = _probe(tmp_path, ["--code-search", "query=zz"], runner, capsys)
    row = _only(payload)

    assert row["count"] == -1
    assert row["http_status"] == status
    assert row["rate_limited"] is rate_limited
    assert len(runner.calls) == 1, "no reset header -> no retry"


def test_rate_limit_waits_for_the_reset_then_retries_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reset inside one window is waited out; a second limit is recorded, not looped.

    FAIL arm: drop the retry and the first 403 is the recorded answer.
    """
    limited = _gh_out(
        403,
        {"message": "x"},
        {"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": str(int(_NOW) + 20)},
    )
    answers = [_done([], 1, limited), _done([], 0, _gh_out(200, {"total_count": 4}))]
    runner = Runner([lambda _a: answers.pop(0)])
    timing = Timing()
    _, payload = _probe(tmp_path, ["--code-search", "query=x"], runner, capsys, timing)

    assert timing.slept == [21.0]
    assert _only(payload)["count"] == 4

    # a reset beyond the cap is a different limit: recorded, never slept on
    far = _gh_out(
        403,
        {"message": "x"},
        {"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": str(int(_NOW) + 3600)},
    )
    runner = Runner([lambda a: _done(a, 1, far)])
    timing = Timing()
    _, payload = _probe(tmp_path, ["--code-search", "query=x"], runner, capsys, timing)
    assert timing.slept == []
    assert _only(payload)["rate_limited"] is True

    # two limits in a row: one wait, one retry, then the limit is the answer
    runner = Runner([lambda a: _done(a, 1, limited)])
    timing = Timing()
    _, payload = _probe(tmp_path, ["--code-search", "query=x"], runner, capsys, timing)
    assert timing.slept == [21.0]
    assert len(runner.calls) == 2
    assert _only(payload)["count"] == -1


@pytest.mark.parametrize(
    ("answer", "status", "full_name"),
    [
        # a trailing newline must never read as a rename (round-4 L5)
        (_done([], 0, _gh_out(200, {"full_name": "jdx/mise\n"})), 200, "jdx/mise"),
        (_done([], 1, _gh_out(404, {"message": "Not Found"})), 404, ""),
        # no -i output at all: the status still comes from gh's own error line
        (_done([], 1, b"", b"gh: Not Found (HTTP 404)\n"), 404, ""),
        (_done([], 1, b"", b"error connecting to api.github.com\n"), 0, ""),
    ],
)
def test_repo_check_records_status_and_trimmed_full_name(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    answer: subprocess.CompletedProcess[bytes],
    status: int,
    full_name: str,
) -> None:
    runner = Runner([lambda _a: answer])
    _, payload = _probe(tmp_path, ["--repo-check", "jdx/rtx"], runner, capsys)
    row = _only(payload)

    assert runner.calls[0] == ["gh", "api", "-i", "repos/jdx/rtx"]
    assert row["http_status"] == status
    assert row["full_name"] == full_name
    assert row["rc"] == answer.returncode


def _fanout_manifest(path: Path, statuses: dict[str, str], age_s: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(_NOW - age_s, UTC).isoformat()
    rows = [
        {
            "source": s,
            "status": st,
            "reason": "exited 1: HTTP 422" if st == "error" else None,
        }
        for s, st in statuses.items()
    ]
    path.write_text(
        json.dumps({"query": "mise", "generated_at": stamp, "sources": rows}),
        encoding="utf-8",
    )


_DEP = "github-issues,github-discussions,github-releases"


def test_fanout_manifest_names_a_required_source_that_failed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#1473: releases answering must not hide an issues search that errored.

    The process rc of that fan-out was 0 (one source answered). FAIL arm: read
    only "did any source answer" and required_failed is empty.
    """
    manifest = tmp_path / "deps/1/manifest.json"
    _fanout_manifest(
        manifest,
        {
            "github-issues": "error",
            "github-discussions": "empty_verified",
            "github-releases": "ok",
        },
        age_s=10,
    )
    _, payload = _probe(
        tmp_path,
        ["--fanout-manifest", "deps/1/manifest.json", "--require", _DEP],
        Runner([]),
        capsys,
    )
    row = _only(payload)

    assert row["exists"] is True
    assert row["query"] == "mise"
    assert row["fresh"] is True
    assert row["required_failed"] == ["github-issues: error (exited 1: HTTP 422)"]

    # control arm: every required source answered -> nothing failed
    _fanout_manifest(manifest, dict.fromkeys(_DEP.split(","), "ok"), age_s=10)
    _, payload = _probe(
        tmp_path,
        ["--fanout-manifest", "deps/1/manifest.json", "--require", _DEP],
        Runner([]),
        capsys,
    )
    assert _only(payload)["required_failed"] == []


def test_fanout_manifest_missing_or_stale_is_not_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A skipped run leaves the PREVIOUS sweep's manifest: age decides freshness."""
    manifest = tmp_path / "deps/1/manifest.json"
    _fanout_manifest(manifest, dict.fromkeys(_DEP.split(","), "ok"), age_s=7200)
    _, payload = _probe(
        tmp_path,
        ["--fanout-manifest", str(manifest), "--require", _DEP],
        Runner([]),
        capsys,
    )
    assert _only(payload)["fresh"] is False
    assert _only(payload)["age_s"] == 7200.0

    _, payload = _probe(
        tmp_path,
        ["--fanout-manifest", "deps/2/manifest.json", "--require", "github-issues"],
        Runner([]),
        capsys,
    )
    row = _only(payload)
    assert row["exists"] is False
    assert row["required_failed"] == ["github-issues: no manifest"]


def _scrape_json(status: int, markdown: str) -> bytes:
    """`firecrawl scrape --json` output, as measured live 2026-10-02."""
    return json.dumps(
        {"markdown": markdown, "metadata": {"statusCode": status}}
    ).encode()


def test_mirror_measures_what_landed_and_never_a_stale_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FAIL arm: drop the unlink and a failed scrape measures the OLD file's bytes."""
    target = tmp_path / "raw/links/1.md"
    runner = Runner([lambda a: _done(a, 0, _scrape_json(200, "# page\n"))])
    _, payload = _probe(
        tmp_path,
        ["--mirror-url", "https://ex.test/it's", "--mirror-path", "raw/links/1.md"],
        runner,
        capsys,
    )
    assert runner.calls[0] == [
        "firecrawl",
        "scrape",
        "https://ex.test/it's",
        "--format",
        "markdown",
        "--only-main-content",
        "--json",
    ]
    assert _only(payload) == {
        "kind": "mirror",
        "url": "https://ex.test/it's",
        "path": str(target),
        "rc": 0,
        "http_status": 200,
        "bytes": 7,
        "reason": "",
    }
    assert target.read_text(encoding="utf-8") == "# page\n"

    runner = Runner([lambda a: _done(a, 1, b"", b"Error: request failed\nmore\n")])
    _, payload = _probe(
        tmp_path,
        ["--mirror-url", "https://ex.test/gone", "--mirror-path", "raw/links/1.md"],
        runner,
        capsys,
    )
    row = _only(payload)
    assert row["bytes"] == 0
    assert row["rc"] == 1
    assert row["reason"] == "Error: request failed"


def test_mirror_of_an_error_page_is_not_a_mirror(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Firecrawl exits 0 with a full body for a 404: the STATUS decides, not size.

    Measured live 2026-10-02: `https://mise.jdx.dev/zz-no-such-page-qq` came back
    rc=0, 328 bytes of "Error 404", statusCode 404. FAIL arm: judge by rc and
    size alone and the error page is a successful mirror.
    """
    runner = Runner([lambda a: _done(a, 0, _scrape_json(404, "# Error 404\n"))])
    _, payload = _probe(
        tmp_path,
        ["--mirror-url", "https://ex.test/404", "--mirror-path", "raw/links/2.md"],
        runner,
        capsys,
    )
    row = _only(payload)
    assert row["rc"] == 0
    assert row["bytes"] == len("# Error 404\n")
    assert row["http_status"] == 404
    assert row["reason"] == "HTTP 404"

    runner = Runner([lambda a: _done(a, 0, b"not json")])
    _, payload = _probe(
        tmp_path,
        ["--mirror-url", "https://ex.test/x", "--mirror-path", "raw/links/3.md"],
        runner,
        capsys,
    )
    assert _only(payload)["reason"] == "firecrawl output was not JSON"


def test_mirror_index_is_written_from_the_probe_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    links = tmp_path / "raw/report-slug/links"
    links.mkdir(parents=True)
    probe = {
        "probes": [
            {
                "kind": "mirror",
                "url": "https://a.test/x|y",
                "path": str(links / "1.md"),
                "rc": 0,
                "bytes": 42,
                "reason": "",
            }
        ]
    }
    (links / "1.probe.json").write_text(json.dumps(probe), encoding="utf-8")

    _, payload = _probe(
        tmp_path,
        ["--mirror-index", str(links), "--mirror-count", "2"],
        Runner([]),
        capsys,
    )
    row = _only(payload)
    readme = (links / "README.md").read_text(encoding="utf-8")

    assert row == {
        "kind": "mirror-index",
        "path": str(links / "README.md"),
        "rows": 2,
        "missing": 1,
        "written": True,
    }
    assert readme.startswith("# Offline mirrors — report-slug\n")
    assert "| 1 | https://a.test/x\\|y | 1.md | 0 | 42 |  |" in readme
    assert (
        "| 2 | (unknown) | 2.md |  | 0 | mirror probe missing or unreadable |" in readme
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--probe-out", "p.json", "a query", "--code-search", "query=x"],
        ["--probe-out", "p.json", "--code-search", "nonsense=x"],
        ["--probe-out", "p.json", "--code-search", "query="],
        ["--probe-out", "p.json", "--repo-check", "../.."],
        ["--probe-out", "p.json", "--repo-check", "o;x/t"],
        ["--probe-out", "p.json", "--require", "github-issues"],
        ["--probe-out", "p.json", "--fanout-manifest", "m.json", "--require", "nope"],
        ["--probe-out", "p.json", "--mirror-url", "https://a.test"],
        ["--probe-out", "p.json", "--mirror-index", "d"],
        ["--probe-out", "p.json"],
        # a probe flag outside probe mode is a usage error, not silently ignored
        ["topic", "--code-search", "query=x"],
    ],
)
def test_probe_usage_errors_exit_two(tmp_path: Path, argv: list[str]) -> None:
    assert main(argv, tmp_path, runner=Runner([]), timing=Timing().timing()) == 2
    assert not (tmp_path / "p.json").exists()
