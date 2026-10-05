# Copyright (c) 2026 Raymond Manaloto
"""Saved-search behavior through files, the CLI and injected network/time seams."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
import tomli_w

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_fanout import ProbeTiming
from dotfiles_setup.saved_searches import GENERATED_HEADER, load, main, shape_of

_ROOT = Path(__file__).parent.parent
_FIXTURES = _ROOT / "tests/fixtures/saved_searches"
_NOW = datetime(2026, 10, 3, tzinfo=UTC).timestamp()
_HEALTH = "repo:cli/cli filename:README.md"
_QUERY = "missing repo:a/b language:rust"
_HIT = "present repo:a/b language:rust"
# Canonical (HEAD-pinned) blob URLs: what a snapshot stores for a code hit.
_OLD_URL = "https://github.com/a/b/blob/HEAD/old.rs"
_NEW_URL = "https://github.com/a/b/blob/HEAD/new.rs"


@dataclass
class _Timing:
    now: float = _NOW
    sleeps: list[float] = field(default_factory=list)

    def boundaries(self) -> ProbeTiming:
        """Return a clock and sleeper whose values the test owns."""
        return ProbeTiming(self.sleeps.append, lambda: self.now)


@dataclass
class _Runner:
    replies: dict[str, dict[str, object]] = field(default_factory=dict)
    calls: list[list[str]] = field(default_factory=list)
    absent_count: int = 0
    raw: dict[str, bytes | None] = field(default_factory=dict)
    plain: dict[str, object] = field(default_factory=dict)

    def __call__(
        self, argv: list[str], *, timeout: float, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        """Answer gh at its process boundary; an unexpected call fails closed."""
        del timeout, env
        self.calls.append(argv)
        if argv[2] in self.raw:
            content = self.raw[argv[2]]
            return subprocess.CompletedProcess(
                argv, int(content is None), content or b"", b""
            )
        if "-i" not in argv:
            payload = self.plain[argv[2]]
            if payload is None:
                # a gh failure at the process boundary
                return subprocess.CompletedProcess(argv, 1, b"", b"HTTP 502")
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(payload).encode(), b""
            )
        if "search/code" in argv:
            query = next(value[2:] for value in argv if value.startswith("q="))
        elif "graphql" in argv:
            query = next(
                value.removeprefix("searchQuery=")
                for value in argv
                if value.startswith("searchQuery=")
            )
        else:
            endpoint = next(
                value for value in argv if value.startswith("search/issues?")
            )
            query = parse_qs(urlsplit(endpoint).query)["q"][0]
        response = self.replies.get(query)
        if response is None and '"zz' in query:
            response = {"count": self.absent_count}
        if response is None:
            message = f"unexpected query: {query}"
            raise AssertionError(message)
        if "pages" in response:
            # one reply per `page=N` (absent = page 1), each its own HTTP/items pair
            page = next((int(arg[5:]) for arg in argv if arg.startswith("page=")), 1)
            pages = cast("list[dict[str, object]]", response["pages"])
            response = {"count": response.get("count", 1), **pages[page - 1]}
        status = response.get("http", 200)
        body = response.get(
            "body",
            {
                "total_count": response.get("count", 1),
                "incomplete_results": response.get("incomplete", False),
                "items": response.get("items", []),
            },
        )
        headers = "x-ratelimit-remaining: 0\r\n" if status == 403 else ""
        output = (
            f"HTTP/2.0 {status} X\r\n{headers}\r\n".encode() + json.dumps(body).encode()
        )
        return subprocess.CompletedProcess(argv, int(status != 200), output, b"")


def _watch(
    identifier: str = "query", query: str = _QUERY, **fields: object
) -> dict[str, object]:
    # Most tests pin top-window behaviour, so a code watch says `top` unless the
    # test passes `collect` itself; the DEFAULT (`all` for code queries) is pinned
    # by test_code_query_defaults_to_collect_all, which builds its rows raw.
    if fields.get("kind", "code") == "code":
        fields.setdefault("collect", "top")
    return {"id": identifier, "kind": "code", "queries": [query], **fields}


def _write(path: Path, watches: list[dict[str, object]], **fields: object) -> None:
    path.write_text(
        tomli_w.dumps({"schema_version": 1, "watch": watches, **fields}),
        encoding="utf-8",
    )


def _receipt(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1].startswith("SAVED-SEARCH-JSON ")
    return cast(
        "dict[str, object]", json.loads(lines[-1].removeprefix("SAVED-SEARCH-JSON "))
    )


def _snapshot(tmp_path: Path) -> dict[str, object]:
    files = sorted((tmp_path / ".agent/kb/raw/saved-searches/search").glob("*.json"))
    return cast("dict[str, object]", json.loads(files[-1].read_bytes()))


def _rows(snapshot: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(row["id"]): row
        for row in cast("list[dict[str, object]]", snapshot["watches"])
    }


def test_record_never_saves_known_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Real manifests record all GitHub kinds and skip spent probe nonces.

    FAIL arm: broaden _probe_record's CodeRole gate to include known-absent.
    """
    extended = json.loads((_FIXTURES / "fanout-items.json").read_bytes())
    extended["sources"].append({"source": "exa", "items": [], "status": "ok"})
    extra = tmp_path / "extended.json"
    extra.write_text(json.dumps(extended), encoding="utf-8")
    args = [
        "record",
        "--out",
        "saved.toml",
        "--fanout-manifest",
        str(extra),
        "--fanout-manifest",
        str(_FIXTURES / "fanout-empty.json"),
        "--probe-manifest",
        str(_FIXTURES / "probe.json"),
    ]
    assert main(args, tmp_path) == 0
    receipt = _receipt(capsys)
    assert receipt["written"] is True
    assert receipt["watches"] == 10
    assert receipt["added"] == 10
    assert receipt["skipped_sources"] == 1
    assert receipt["missing"] == []
    saved = tomllib.loads((tmp_path / "saved.toml").read_text(encoding="utf-8"))
    assert {row["kind"] for row in saved["watch"]} == {
        "issues",
        "discussions",
        "releases",
        "code",
    }
    assert {row.get("role") for row in saved["watch"] if row["kind"] == "code"} == {
        "query",
        "must-hit",
        "health",
        "readme",
    }
    assert len(saved["result"]) == 10
    assert "question" not in saved
    assert "origin" not in saved
    assert "spent-fixture-nonce" not in (tmp_path / "saved.toml").read_text(
        encoding="utf-8"
    )
    issues = next(
        row
        for row in saved["watch"]
        if row["kind"] == "issues" and row["queries"] == ["llvm-project"]
    )
    baseline = next(row for row in saved["result"] if row["watch_id"] == issues["id"])
    assert baseline["count"] == 3
    assert baseline["urls"][0] == "https://github.com/jdx/mise/pull/13566"


def test_record_merge_and_curated_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Repeat observations replace results while previous searches survive.

    FAIL arm: replace rather than update watches, or drop the generated-header guard.
    """
    path = tmp_path / "saved.toml"
    args = [
        "record",
        "--out",
        str(path),
        "--fanout-manifest",
        str(_FIXTURES / "fanout-items.json"),
    ]
    assert main(args, tmp_path) == 0
    first = load(path)
    _receipt(capsys)
    updated = json.loads((_FIXTURES / "fanout-items.json").read_bytes())
    updated["generated_at"] = "2026-10-04T00:00:00Z"
    updated["sources"][0]["items"] = []
    manifest = tmp_path / "new.json"
    manifest.write_text(json.dumps(updated), encoding="utf-8")
    assert (
        main(
            [
                "record",
                "--out",
                str(path),
                "--fanout-manifest",
                str(manifest),
                "--code-search",
                "query=other",
            ],
            tmp_path,
        )
        == 0
    )
    receipt = _receipt(capsys)
    assert (receipt["added"], receipt["updated"], receipt["watches"]) == (1, 3, 4)
    saved = tomllib.loads(path.read_text(encoding="utf-8"))
    assert [row["id"] for row in saved["watch"][:3]] == [
        watch.id for watch in first.watch
    ]
    assert saved["result"][0]["count"] == 0
    assert len(saved["result"]) == 3
    curated = tmp_path / "curated.toml"
    curated.write_bytes(b"schema_version = 1\nwatch = []\n")
    before = curated.read_bytes()
    assert (
        main(["record", "--out", str(curated), "--code-search", "query=x"], tmp_path)
        == 1
    )
    assert curated.read_bytes() == before
    assert _receipt(capsys)["reason"] == "refused: not a generated file"
    # A tracked TOML stays world-readable (NamedTemporaryFile creates 0600).
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    # Nothing readable from this run: no rewrite and no `written: true` (F8).
    saved_bytes = path.read_bytes()
    assert (
        main(["record", "--out", str(path), "--fanout-manifest", "gone.json"], tmp_path)
        == 1
    )
    receipt = _receipt(capsys)
    assert (receipt["written"], receipt["reason"]) == (
        False,
        "no readable input from this run",
    )
    assert path.read_bytes() == saved_bytes


def test_record_no_inputs_echoes_relative_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing or malformed inputs yield a no-op receipt and no empty file.

    FAIL arm: omit record_main's finally receipt or write an empty watch list.
    """
    (tmp_path / "bad.json").write_text("{bad", encoding="utf-8")
    output = "nested/relative.toml"
    assert (
        main(
            [
                "record",
                "--out",
                output,
                "--fanout-manifest",
                "missing.json",
                "--probe-manifest",
                "bad.json",
            ],
            tmp_path,
        )
        == 1
    )
    receipt = _receipt(capsys)
    assert receipt["out"] == output
    assert receipt["path"] == str(tmp_path / output)
    assert receipt["written"] is False
    assert receipt["reason"] == "no watches"
    assert receipt["missing"] == ["missing.json", "bad.json"]
    assert not (tmp_path / output).exists()


def test_record_refuses_known_absent_import(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Manual imports have the same role gate as probe manifests.

    FAIL arm: accept a spent known-absent role in _record.
    """
    assert (
        main(
            ["record", "--out", "saved.toml", "--code-search", "known-absent=spent"],
            tmp_path,
        )
        == 2
    )
    assert _receipt(capsys)["written"] is False
    assert not (tmp_path / "saved.toml").exists()


def test_record_classifies_failed_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed probe or fan-out row is recorded as `error` with count -1, never as 0.

    FAIL arm: replace `_probe_record`'s `good` check with True, or record a failed
    fan-out source as `count=len(items)` (cold review M3, F5).
    """
    probe = {
        "kind": "probe",
        "generated_at": "2026-10-03T00:00:00+00:00",
        "probes": [
            {"kind": "code-search", "role": "query", "query": q, **row}
            for q, row in [
                ("ok-q", {"rc": 0, "count": 4}),
                ("failed-q", {"rc": 1, "count": -1}),
                ("limited-q", {"rc": 0, "count": 0, "rate_limited": True}),
                ("timeout-q", {"rc": 0, "count": 0, "incomplete_results": True}),
            ]
        ],
    }
    fanout = json.loads((_FIXTURES / "fanout-items.json").read_bytes())
    fanout["sources"][0]["status"] = "error"
    fanout["sources"][1]["status"] = "empty_verified"
    fanout["sources"][1]["items"] = []
    (tmp_path / "probe.json").write_text(json.dumps(probe), encoding="utf-8")
    (tmp_path / "fanout.json").write_text(json.dumps(fanout), encoding="utf-8")
    args = ["record", "--out", "saved.toml", "--probe-manifest", "probe.json"]
    assert main([*args, "--fanout-manifest", "fanout.json"], tmp_path) == 0
    _receipt(capsys)
    saved = tomllib.loads((tmp_path / "saved.toml").read_text(encoding="utf-8"))
    query_of = {row["id"]: row["queries"][0] for row in saved["watch"]}
    code = {
        query_of[row["watch_id"]]: (row["status"], row["count"])
        for row in saved["result"]
        if query_of[row["watch_id"]].endswith("-q")
    }
    assert code == {
        "ok-q": ("ok", 4),
        "failed-q": ("error", -1),
        "limited-q": ("error", -1),
        "timeout-q": ("error", -1),
    }
    statuses = [row["status"] for row in saved["result"] if row["status"] != "ok"]
    # fan-out statuses use the rerun's vocabulary; a failed one has no count
    assert "empty-verified" in statuses
    assert "empty_verified" not in statuses
    failed = [row for row in saved["result"] if row["status"] == "error"]
    assert any(row["count"] == -1 and row["urls"] for row in failed)


@pytest.mark.parametrize(
    ("date_literal", "expected"),
    [
        ("2026-10-02", "2026-10-02T00:00:00+00:00"),
        ("2026-10-02T17:03:11Z", "2026-10-02T17:03:11+00:00"),
    ],
)
def test_loader_accepts_real_draft_and_bare_dates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    date_literal: str,
    expected: str,
) -> None:
    """The existing curated draft loads unchanged, including extra result fields.

    FAIL arm: decode draft Result extras without filtering, or JSON-encode a bare date.
    """
    draft = _ROOT / "docs/research/saved-searches/orchestration-2026-10-02.toml"
    before = draft.read_bytes()
    assert load(draft).watch
    assert draft.read_bytes() == before
    assert "_controls-code" in capsys.readouterr().err
    path = tmp_path / "date.toml"
    path.write_text(
        'schema_version=1\n[[watch]]\nid="a"\nkind="code"\nqueries=["x"]\n'
        '[[result]]\nwatch_id="a"\n'
        f'date_run={date_literal}\ntotal_count=4\nexamples=["extra"]\n',
        encoding="utf-8",
    )
    assert main(["status", str(path)], tmp_path, timing=_Timing().boundaries()) == 0
    assert expected in capsys.readouterr().out


@pytest.mark.parametrize(
    ("change", "field_name"),
    [
        ({"unexpected": True}, "unexpected"),
        ({"id": "Bad_Id"}, "id"),
        ({"id": ""}, "id"),
        ({"id": "a" * 81}, "id"),
        ({"kind": "pulls"}, "kind"),
        ({"role": "known-absent"}, "role"),
        ({"queries": []}, "queries"),
        ({"kind": "issues", "queries": []}, "queries"),
        ({"kind": "discussions", "queries": []}, "queries"),
        ({"kind": "releases"}, "repo"),
        ({"repo": "bad"}, "repo"),
        ({"repo": "../.."}, "repo"),
        ({"repo": "a/."}, "repo"),
        ({"repo": ".../b"}, "repo"),
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"control_absent": "spent"}, "control_absent"),
        ({"control_absent": ""}, "control_absent"),
        *[
            ({name: "["}, name)
            for name in (
                "grep",
                "path_grep",
                "control_hit_grep",
                "control_hit_path_grep",
            )
        ],
    ],
)
def test_loader_validation_precedes_network(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    change: dict[str, object],
    field_name: str,
) -> None:
    """Every validation axis names its file, id and offending field.

    FAIL arm: remove the corresponding schema rule or _validate_watch predicate.
    """
    path = tmp_path / "bad.toml"
    _write(path, [{**_watch(), **change}])
    runner = _Runner()
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 2
    )
    error = capsys.readouterr().err
    assert str(path) in error
    assert str(change.get("id", "query")) in error
    assert field_name in error
    assert runner.calls == []


@pytest.mark.parametrize("axis", ["duplicate", "version"])
def test_loader_duplicate_and_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], axis: str
) -> None:
    """File-level constraints reject duplicates and future schema versions.

    FAIL arm: remove the duplicate-id set or schema_version Literal[1].
    """
    path = tmp_path / "bad.toml"
    _write(path, [_watch(), _watch()] if axis == "duplicate" else [_watch()])
    if axis == "version":
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "schema_version = 1", "schema_version = 2"
            ),
            encoding="utf-8",
        )
    assert main(["rerun", str(path)], tmp_path, runner=_Runner()) == 2
    error = capsys.readouterr().err
    assert "id" in error
    assert ("duplicate" if axis == "duplicate" else "schema_version") in error


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("repo:a/b language:rust foo", "language:rust repo:a/b"),
        ("foo OR bar language:toml", "OR language:toml"),
        ("(foo) and bar -repo:A/B", "() -repo:a/b"),
    ],
)
def test_shape_matches_workflow(query: str, expected: str) -> None:
    """Known workflow examples pin qualifiers, uppercase booleans and parens.

    FAIL arm: drop booleans/qualifiers, or promote lowercase 'and' to a boolean.
    """
    assert shape_of(query) == expected


@pytest.mark.parametrize(
    ("with_hit", "absent_count", "expected", "rc"),
    [
        (True, 0, "empty-verified", 0),
        (False, 0, "empty-unarmed", 1),
        (True, 1, "empty-unarmed", 1),
    ],
)
def test_code_zero_requires_both_shape_controls(
    tmp_path: Path, absent_count: int, expected: str, rc: int, *, with_hit: bool
) -> None:
    """A zero is evidence only beside a discriminating positive/negative pair.

    FAIL arm: _run_code arms from endpoint health alone or ignores absent >0.
    """
    path = tmp_path / "search.toml"
    watches = [_watch()]
    if with_hit:
        watches.append(_watch("hit", _HIT, role="must-hit"))
    _write(path, watches)
    runner = _Runner(
        {_HEALTH: {"count": 1}, _QUERY: {"count": 0}, _HIT: {"count": 2}},
        absent_count=absent_count,
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == rc
    )
    assert _rows(_snapshot(tmp_path))["query"]["status"] == expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"http": 403, "count": 0}, "rate-limited"),
        ({"incomplete": True, "count": 0}, "incomplete"),
        ({"body": {}}, "error"),
    ],
)
def test_failed_code_search_never_becomes_zero(
    tmp_path: Path, response: dict[str, object], expected: str
) -> None:
    """Limited, incomplete and malformed direct calls retain no-count -1.

    FAIL arm: _direct coerces missing/failed counts to zero.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    runner = _Runner({_HEALTH: {"count": 1}, _QUERY: response})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 1
    )
    row = _rows(_snapshot(tmp_path))["query"]
    assert row["status"] == expected
    assert row["count"] == -1


def test_health_zero_invalidates_all_code(tmp_path: Path) -> None:
    """Broken endpoint health makes even apparently positive searches errors.

    FAIL arm: omit _run_code's unhealthy override.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch(), _watch("hit", _HIT, role="must-hit")])
    runner = _Runner({_HEALTH: {"count": 0}, _QUERY: {"count": 2}, _HIT: {"count": 3}})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 1
    )
    assert all(
        row["status"] == "error" and row["reason"] == "code search unhealthy"
        for row in _rows(_snapshot(tmp_path)).values()
    )


def test_pacing_covers_every_code_call(tmp_path: Path) -> None:
    """Each actual code API call after the first has a 6.5-second pace.

    FAIL arm: pace only primary searches and controls collide in the same bucket.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch(), _watch("hit", _HIT, role="must-hit")])
    timing = _Timing()
    runner = _Runner({_HEALTH: {"count": 1}, _QUERY: {"count": 0}, _HIT: {"count": 1}})
    assert (
        main(["rerun", str(path)], tmp_path, runner=runner, timing=timing.boundaries())
        == 0
    )
    searches = [call for call in runner.calls if "search/code" in call]
    assert len(searches) == 4
    assert timing.sleeps == [6.5, 6.5, 6.5]


@pytest.mark.parametrize("content", [b"wanted text", b"wrong", None])
def test_draft_controls_and_confirmed_grep(
    tmp_path: Path, content: bytes | None
) -> None:
    """Per-watch draft controls can arm a different shape; raw misses cannot.

    FAIL arm: use shape controls for drafts or ignore control_hit_grep confirmation.
    """
    path = tmp_path / "search.toml"
    item = {"html_url": _NEW_URL, "url": "raw-url", "path": "new.rs"}
    _write(
        path,
        [
            _watch(
                control_hit="control filename:README.md",
                control_absent='"{nonce}" filename:README.md',
                control_hit_grep="wanted",
                control_hit_path_grep=r"\.rs$",
                grep="wanted",
                path_grep=r"\.rs$",
            )
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _QUERY: {"count": 0},
            "control filename:README.md": {"count": 1, "items": [item]},
        },
        raw={"raw-url": content},
    )
    rc = main(
        ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
    )
    assert rc == (0 if content == b"wanted text" else 1)
    row = _rows(_snapshot(tmp_path))["query"]
    assert row["status"] == ("empty-verified" if rc == 0 else "empty-unarmed")
    assert row["confirmed"] == 0


def test_draft_confirmation_counts_all_patterns_and_failures(tmp_path: Path) -> None:
    """Returned code items need both content and path, with failed fetches unconfirmed.

    FAIL arm: count API totals as confirmed hits or OR content/path patterns.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch(grep="wanted", path_grep=r"\.rs$")])
    items = [
        {
            "html_url": f"https://example.test/{index}",
            "url": f"raw-{index}",
            "path": name,
        }
        for index, name in enumerate(["yes.rs", "no.toml", "fail.rs"])
    ]
    runner = _Runner(
        {_HEALTH: {"count": 1}, _QUERY: {"count": 99, "items": items}},
        raw={"raw-0": b"wanted", "raw-1": b"wanted", "raw-2": None},
    )
    timing = _Timing()
    assert (
        main(["rerun", str(path)], tmp_path, runner=runner, timing=timing.boundaries())
        == 0
    )
    row = _rows(_snapshot(tmp_path))["query"]
    assert row["confirmed"] == 1
    assert row["count"] == 99
    assert timing.sleeps == [6.5, 6.5]


def test_nonce_freshness_and_no_toml_mutation(tmp_path: Path) -> None:
    """Two reruns get different absent nonces and preserve tracked bytes.

    FAIL arm: replace secrets.token_hex with a constant or persist controls in TOML.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    before = path.read_bytes()
    timing = _Timing()
    queries: list[str] = []
    for _ in range(2):
        runner = _Runner({_HEALTH: {"count": 1}, _QUERY: {"count": 2}})
        assert (
            main(
                ["rerun", str(path)],
                tmp_path,
                runner=runner,
                timing=timing.boundaries(),
            )
            == 0
        )
        queries.extend(
            next(arg[2:] for arg in call if arg.startswith("q="))
            for call in runner.calls
            if any(arg.startswith('q="zz') for arg in call)
        )
        timing.now += 2
    assert len(queries) == 2
    assert queries[0] != queries[1]
    assert all(query.encode() not in path.read_bytes() for query in queries)
    assert path.read_bytes() == before


def test_shape_absent_drops_booleans_and_parentheses(tmp_path: Path) -> None:
    """A shape's negative control retains qualifiers without grouping operators.

    FAIL arm: _absent keeps a closing parenthesis or copies the OR term expression.
    """
    path = tmp_path / "search.toml"
    query = "foo OR (bar language:rust) repo:a/b"
    hit = "present OR (known language:rust) repo:a/b"
    _write(path, [_watch(query=query), _watch("hit", hit, role="must-hit")])
    runner = _Runner({_HEALTH: {"count": 1}, query: {"count": 0}, hit: {"count": 1}})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    controls = cast("list[dict[str, object]]", _snapshot(tmp_path)["controls"])
    negative = next(row for row in controls if row["role"] == "known-absent")
    words = str(negative["query"]).split()
    assert words[0].startswith('"zz')
    assert words[1:] == ["language:rust", "repo:a/b"]
    assert _rows(_snapshot(tmp_path))["query"]["status"] == "empty-verified"


@pytest.mark.parametrize("report", ["search.toml", "nested/../search.toml", "alias.md"])
def test_rerun_report_cannot_overwrite_input(tmp_path: Path, report: str) -> None:
    """Report aliases of the input are usage errors before any network activity.

    FAIL arm: remove rerun_main's resolved report-path guard and clobber the TOML.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    (tmp_path / "nested").mkdir()
    (tmp_path / "alias.md").symlink_to(path)
    before = path.read_bytes()
    runner = _Runner()
    assert main(["rerun", str(path), "--report", report], tmp_path, runner=runner) == 2
    assert runner.calls == []
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", ["code", "issues"])
@pytest.mark.parametrize(
    "counts", [{"total_count": 7}, {"count": 7, "total_count": 99}]
)
def test_diff_uses_snapshot_then_baseline_total_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    counts: dict[str, int],
) -> None:
    """The first diff uses draft totals; later diffs report NEW and GONE URLs.

    FAIL arm: ignore total_count, prefer it over count, or diff the new snapshot.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [_watch(kind=kind)],
        result=[
            {
                "watch_id": "query",
                "date_run": "2026-10-02",
                **counts,
                "urls": [_OLD_URL],
                "status": "ok",
            }
        ],
    )
    timing = _Timing()
    runner = _Runner(
        {_HEALTH: {"count": 1}, _QUERY: {"count": 2, "items": [{"html_url": _NEW_URL}]}}
    )
    assert (
        main(
            ["rerun", str(path), "--report", "diff.md"],
            tmp_path,
            runner=runner,
            timing=timing.boundaries(),
        )
        == 0
    )
    first = capsys.readouterr().out
    assert "Previous: baseline" in first
    assert "7 → 2" in first
    assert f"| {_NEW_URL} | {_OLD_URL} |" in first
    assert (tmp_path / "diff.md").read_text(encoding="utf-8") == first
    timing.now += 2
    runner.replies[_QUERY] = {"count": 3, "items": [{"html_url": _OLD_URL}]}
    assert (
        main(["rerun", str(path)], tmp_path, runner=runner, timing=timing.boundaries())
        == 0
    )
    second = capsys.readouterr().out
    assert "Previous: snapshot " in second
    assert "2 → 3" in second
    assert f"| {_OLD_URL} | {_NEW_URL} |" in second


@pytest.mark.parametrize(
    ("reply", "status"),
    [
        ({"http": 500, "body": {"message": "boom"}}, "error"),
        # a 0 with no same-shape must-hit is unarmed: no URLs, but not "vanished"
        ({"count": 0}, "empty-unarmed"),
    ],
)
def test_unanswered_rerun_never_reports_gone(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    reply: dict[str, object],
    status: str,
) -> None:
    """A failed or unarmed rerun shows n/a, not every previous URL as GONE.

    FAIL arm: drop the `answered` guard in `_report` (cold review M1).
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [_watch()],
        result=[
            {
                "watch_id": "query",
                "date_run": "2026-10-02",
                "count": 1,
                "urls": [_OLD_URL],
            }
        ],
    )
    runner = _Runner({_HEALTH: {"count": 1}, _QUERY: reply})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 1
    )
    row = next(
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("| query |")
    )
    assert status in row
    assert _OLD_URL not in row
    assert row.endswith("| n/a | n/a |")


def test_previous_is_chosen_per_watch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """After `rerun --id a`, a full rerun still diffs b against b's own baseline.

    FAIL arm: choose the newest snapshot per FILE in `_previous` (cold review M2).
    """
    path = tmp_path / "search.toml"
    other = "other repo:a/b language:rust"
    _write(
        path,
        [_watch("a"), _watch("b", other)],
        result=[
            {"watch_id": "b", "date_run": "2026-10-02", "count": 5, "urls": [_OLD_URL]}
        ],
    )
    timing = _Timing()
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _QUERY: {"count": 2},
            other: {"count": 5, "items": [{"html_url": _OLD_URL}]},
        }
    )
    args = ["rerun", str(path)]
    assert (
        main([*args, "--id", "a"], tmp_path, runner=runner, timing=timing.boundaries())
        == 0
    )
    capsys.readouterr()
    timing.now += 2
    assert main(args, tmp_path, runner=runner, timing=timing.boundaries()) == 0
    out = capsys.readouterr().out
    row_b = next(line for line in out.splitlines() if line.startswith("| b |"))
    assert "5 → 5" in row_b
    assert row_b.endswith("|  |  |")
    row_a = next(line for line in out.splitlines() if line.startswith("| a |"))
    assert "2 → 2" in row_a


def test_code_urls_key_on_repo_and_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file whose commit sha moved is the SAME hit, not a NEW one and a GONE one.

    search/code returns `/blob/<sha>/<path>`; measured live 2026-10-03, every rerun
    reported every hit as NEW and the baseline's URL as GONE.
    FAIL arm: return `url` unchanged from `_canonical` (saved_searches.py).
    """
    path = tmp_path / "search.toml"
    sha_url = "https://github.com/a/b/blob/{}/same.rs"
    _write(
        path,
        [_watch()],
        result=[
            {
                "watch_id": "query",
                "date_run": "2026-10-02",
                "count": 1,
                "urls": [sha_url.format("aaa111")],
            }
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _QUERY: {"count": 1, "items": [{"html_url": sha_url.format("bbb222")}]},
        }
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    out = capsys.readouterr().out
    assert _rows(_snapshot(tmp_path))["query"]["urls"] == [sha_url.format("HEAD")]
    assert "| 1 → 1 | ok |  |  |" in out


@pytest.mark.parametrize(
    ("returned", "stored"),
    [
        # only the ref right after the first /blob/ is pinned; a later /blob/ stays
        (
            "https://github.com/a/b/blob/c0ffee/docs/blob/x.md",
            "https://github.com/a/b/blob/HEAD/docs/blob/x.md",
        ),
        # a repo NAMED blob is not a /blob/ segment
        (
            "https://github.com/a/blob/blob/c0ffee/x.md",
            "https://github.com/a/blob/blob/HEAD/x.md",
        ),
        (
            "https://github.com/a/b/blob/main/x.md",
            "https://github.com/a/b/blob/HEAD/x.md",
        ),
        # issue, PR and release URLs carry no commit ref and pass through
        ("https://github.com/a/b/issues/7", "https://github.com/a/b/issues/7"),
        ("https://github.com/a/b/pull/8", "https://github.com/a/b/pull/8"),
        (
            "https://github.com/a/b/releases/tag/v1.2",
            "https://github.com/a/b/releases/tag/v1.2",
        ),
    ],
)
def test_url_canonical_edge_cases(tmp_path: Path, returned: str, stored: str) -> None:
    """Only a blob URL's commit ref is rewritten (diff-identity review, 2026-10-03).

    FAIL arm: drop the `^` anchor or the owner/repo segments from `_BLOB_REF`.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    runner = _Runner(
        {_HEALTH: {"count": 1}, _QUERY: {"count": 1, "items": [{"html_url": returned}]}}
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    assert _rows(_snapshot(tmp_path))["query"]["urls"] == [stored]


def test_report_flags_a_truncated_window(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run keeping fewer URLs than it matched says so (NEW/GONE may be ranking).

    FAIL arm: delete the `top N of M` suffix in `_report`.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _QUERY: {"count": 221, "items": [{"html_url": _NEW_URL}]},
        }
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    assert "first run → 221 (top 1 of 221)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "case",
    [
        # (kind, control_hit count, shape known-absent count, rc, status)
        ("code", 1, 0, 0, "empty-verified"),
        # the shape's fresh known-absent answered: this shape cannot discriminate
        ("code", 1, 1, 1, "empty-unarmed"),
        # the watch's own positive control found nothing
        ("code", 0, 0, 1, "empty-unarmed"),
        # issues have no per-shape absent, so a lone control_hit can never arm them
        ("issues", 1, 0, 1, "empty-unarmed"),
    ],
)
def test_control_hit_without_absent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: tuple[str, int, int, int, str],
) -> None:
    """A draft watch with only `control_hit` borrows the shape's fresh known-absent.

    Live 2026-10-03: hand-curated code watches with control_hit and no
    control_absent made every rerun exit 1 with no reason printed.
    FAIL arm: in `_draft_armed`, return False whenever `control_absent` is empty.
    """
    kind, hit_count, absent_count, rc, status = case
    path = tmp_path / "search.toml"
    hit = "control filename:README.md"
    _write(path, [_watch(kind=kind, control_hit=hit)])
    runner = _Runner(
        {_HEALTH: {"count": 1}, _QUERY: {"count": 0}, hit: {"count": hit_count}},
        absent_count=absent_count,
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == rc
    )
    out = capsys.readouterr().out
    assert _rows(_snapshot(tmp_path))["query"]["status"] == status
    if kind == "code":
        # the report names the control that decided it, so an rc 1 is explainable
        assert f"| must-hit | {hit} | {hit_count} | ok |" in out


@pytest.mark.parametrize(
    ("cadence", "date_run", "stale"),
    [
        ("daily", "2026-10-01", True),
        ("daily", "2026-10-03", False),
        ("weekly", "2026-09-25", True),
        ("weekly", "2026-09-26", False),
    ],
)
def test_status_ages_baseline_by_cadence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    cadence: str,
    date_run: str,
    *,
    stale: bool,
) -> None:
    """Baseline age uses the shortest watch cadence and strict greater-than.

    FAIL arm: use a fixed cadence or mark age == cadence stale.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [_watch(cadence=cadence)],
        result=[{"watch_id": "query", "date_run": date_run}],
    )
    assert main(["status", str(path)], tmp_path, timing=_Timing().boundaries()) == 0
    assert ("STALE" in capsys.readouterr().out) is stale


def test_status_prefers_fresh_snapshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A rerun makes an old daily baseline fresh without rewriting it.

    FAIL arm: age status from the baseline even after a snapshot exists.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [_watch(cadence="daily")],
        result=[{"watch_id": "query", "date_run": "2026-01-01"}],
    )
    runner = _Runner({_HEALTH: {"count": 1}, _QUERY: {"count": 1}})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    capsys.readouterr()
    assert main(["status", str(path)], tmp_path, timing=_Timing().boundaries()) == 0
    assert "STALE" not in capsys.readouterr().out


def test_repo_fanout_uses_returned_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injected fan-outs have a fake gh prerequisite and count only returned items.

    FAIL arm: use total_count for a repo watch, or omit the PATH prerequisite fixture.
    """
    tool = tmp_path / "gh"
    tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {
                "id": "issue",
                "kind": "issues",
                "repo": "a/b",
                "queries": ["term"],
                "limit": 1,
            }
        ],
    )
    runner = _Runner(
        plain={
            "/search/issues?q=repo:a/b+term&per_page=1": {
                "total_count": 99,
                "items": [{"title": "one", "html_url": _NEW_URL, "body": "text"}],
            }
        }
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    assert _rows(_snapshot(tmp_path))["issue"]["count"] == 1


def test_failed_fanout_rerun_counts_minus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed repo-scoped fetch records count -1, not a measured drop to 0.

    FAIL arm: set `count = len(result.items)` unconditionally in `_run_other`
    (codex lens P2, 2026-10-03).
    """
    tool = tmp_path / "gh"
    tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    path = tmp_path / "search.toml"
    _write(
        path,
        [{"id": "issue", "kind": "issues", "repo": "a/b", "queries": ["term"]}],
    )
    runner = _Runner(plain={"/search/issues?q=repo:a/b+term&per_page=10": None})
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 1
    )
    row = _rows(_snapshot(tmp_path))["issue"]
    assert (row["status"], row["count"]) == ("error", -1)


def test_draft_issues_use_total_count_and_controls(tmp_path: Path) -> None:
    """Draft issues preserve total_count rather than the truncated item count.

    FAIL arm: use fan_out for draft queries or replace total_count with len(items).
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {
                "id": "issue",
                "kind": "issues",
                "queries": ["term"],
                "control_hit": "present",
                "control_absent": '"{nonce}"',
            }
        ],
    )
    runner = _Runner(
        {
            "term": {"count": 99, "items": [{"html_url": _NEW_URL}]},
            "present": {"count": 1},
        }
    )
    assert (
        main(
            ["rerun", str(path)], tmp_path, runner=runner, timing=_Timing().boundaries()
        )
        == 0
    )
    assert _rows(_snapshot(tmp_path))["issue"]["count"] == 99
    assert not any("search/code" in call for call in runner.calls)


def test_unknown_id_is_usage_error_before_network(tmp_path: Path) -> None:
    """Selecting an absent id fails before even the endpoint health control.

    FAIL arm: ignore unknown selectors and report an empty successful rerun.
    """
    path = tmp_path / "search.toml"
    _write(path, [_watch()])
    runner = _Runner()
    assert main(["rerun", str(path), "--id", "absent"], tmp_path, runner=runner) == 2
    assert runner.calls == []


def test_fixture_paths_are_neutral() -> None:
    """Real fixture copies retain provenance without tracking home paths.

    FAIL arm: copy the original manifests without rewriting out_dir/raw_file.
    """
    for path in _FIXTURES.glob("*.json"):
        assert "/Users/" not in path.read_text(encoding="utf-8")
    assert GENERATED_HEADER.startswith("# generated by research-saved-search record")


# --- collect = "all" (newer-examples research, 2026-10-03) ---------------------------

_HIT_SHAPE = "present repo:a/b language:rust"


def _items(count: int, start: int = 0) -> list[dict[str, object]]:
    return [
        {"html_url": f"https://github.com/o/r{i}/blob/sha{i}/f.rs", "url": f"raw-{i}"}
        for i in range(start, start + count)
    ]


def _all_watch() -> list[dict[str, object]]:
    return [_watch(collect="all"), _watch("hit", _HIT_SHAPE, role="must-hit")]


def _paged(*pages: list[dict[str, object]], count: int = 141) -> dict[str, object]:
    return {"count": count, "pages": [{"items": items} for items in pages]}


def _search_calls(runner: _Runner, query: str) -> list[list[str]]:
    return [call for call in runner.calls if f"q={query}" in call]


def _rerun(tmp_path: Path, path: Path, runner: _Runner, timing: _Timing) -> int:
    return main(
        ["rerun", str(path)], tmp_path, runner=runner, timing=timing.boundaries()
    )


def _query_line(out: str) -> str:
    return next(line for line in out.splitlines() if line.startswith("| query |"))


def test_collect_all_pages_until_a_short_page(tmp_path: Path) -> None:
    """141 hits are collected over 2 pages of 100, and the count is what was collected.

    FAIL arm: call `_direct` once in `_search_code` (no page loop) and only the
    first page comes back.
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), _items(41, 100)),
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 0
    row = _rows(_snapshot(tmp_path))["query"]
    urls = cast("list[str]", row["urls"])
    assert (row["count"], len(urls), row["complete"]) == (141, 141, True)
    calls = _search_calls(runner, _QUERY)
    assert len(calls) == 2
    assert "per_page=100" in calls[0]
    assert "page=2" in calls[1]


def test_collect_all_reports_a_low_ranked_new_example(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file new to the index at rank 120 shows as NEW; a reshuffle shows nothing.

    FAIL arm: drop `collect = "all"` from the watch — the top-10 window never sees
    rank 120, and a reshuffle reports 10 NEW and 10 GONE.
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    timing = _Timing()
    base = _items(141)
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(base[:100], base[100:]),
        }
    )
    assert _rerun(tmp_path, path, runner, timing) == 0
    capsys.readouterr()
    # the same 141 keys in a different order, with moved commit shas
    shuffled = [
        {**item, "html_url": str(item["html_url"]).replace("/sha", "/new")}
        for item in reversed(base)
    ]
    timing.now += 2
    runner.replies[_QUERY] = _paged(shuffled[:100], shuffled[100:])
    assert _rerun(tmp_path, path, runner, timing) == 0
    assert _query_line(capsys.readouterr().out).endswith("|  |  |")
    grown = [*base[:119], *_items(1, 999), *base[119:]]
    timing.now += 2
    runner.replies[_QUERY] = _paged(grown[:100], grown[100:], count=142)
    assert _rerun(tmp_path, path, runner, timing) == 0
    row = _query_line(capsys.readouterr().out)
    assert "141 → 142 (all collected)" in row
    assert row.endswith("| https://github.com/o/r999/blob/HEAD/f.rs |  |")


def test_default_all_over_cap_falls_back_to_top_window(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default `all` above the cap keeps page 1's top 10 with rc 0 and a label.

    FAIL arm: delete the default fallback branch — `uncollectable` returns rc 1.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {"id": "query", "kind": "code", "queries": [_QUERY]},
            {"id": "hit", "kind": "code", "queries": [_HIT_SHAPE], "role": "must-hit"},
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), count=1500),
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 0
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["count"]) == ("ok", 1500)
    assert "complete" not in row
    assert row["urls"] == [
        f"https://github.com/o/r{index}/blob/HEAD/f.rs" for index in range(10)
    ]
    assert row["reason"] == (
        "over the 1000-result cap: top 10 of 1500, not all collected — "
        "narrow the query to collect all"
    )
    assert len(_search_calls(runner, _QUERY)) == 1
    line = _query_line(capsys.readouterr().out)
    assert "(top 10 of 1500)" in line
    assert "1000-result cap" in line


def test_cap_crossed_mid_collection_falls_back_not_complete(tmp_path: Path) -> None:
    """A default collection crossing the cap on page 2 keeps only page 1's window.

    FAIL arm: drop the per-page cap recheck, or build the window from page 2.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {"id": "query", "kind": "code", "queries": [_QUERY]},
            {"id": "hit", "kind": "code", "queries": [_HIT_SHAPE], "role": "must-hit"},
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: {
                "pages": [
                    {"count": 900, "items": _items(100)},
                    {"count": 1100, "items": _items(100, 100)},
                ]
            },
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 0
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["count"]) == ("ok", 1100)
    assert "complete" not in row
    assert row["urls"] == [
        f"https://github.com/o/r{index}/blob/HEAD/f.rs" for index in range(10)
    ]
    assert row["reason"] == (
        "over the 1000-result cap: top 10 of 1100, not all collected — "
        "narrow the query to collect all"
    )
    assert len(_search_calls(runner, _QUERY)) == 2


def test_window_after_full_collection_does_not_diff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A default full collection followed by a cap window cannot report NEW/GONE.

    FAIL arm: remove only the window-after-full guard — 131 URLs read as GONE.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {"id": "query", "kind": "code", "queries": [_QUERY]},
            {"id": "hit", "kind": "code", "queries": [_HIT_SHAPE], "role": "must-hit"},
        ],
    )
    timing = _Timing()
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), _items(41, 100)),
        }
    )
    assert _rerun(tmp_path, path, runner, timing) == 0
    first = _rows(_snapshot(tmp_path))["query"]
    assert (first["count"], first["complete"]) == (141, True)
    assert len(cast("list[str]", first["urls"])) == 141
    capsys.readouterr()
    timing.now += 2
    runner.replies[_QUERY] = _paged(_items(100), count=1500)
    assert _rerun(tmp_path, path, runner, timing) == 0
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["count"]) == ("ok", 1500)
    assert "complete" not in row
    window = "n/a (window after full collection)"
    assert _query_line(capsys.readouterr().out).endswith(f"| {window} | {window} |")


def test_collect_all_over_the_cap_is_uncollectable(tmp_path: Path) -> None:
    """EXPLICIT `collect = "all"` above 1000 stays strict: one call, `uncollectable`.

    FAIL arm: make the fallback ignore explicitness — the run returns rc 0.
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    pages = [_items(100, 100 * index) for index in range(10)]
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(*pages, count=1500),
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 1
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["count"], row["urls"]) == ("uncollectable", -1, [])
    assert len(_search_calls(runner, _QUERY)) == 1


def test_collect_all_failed_page_never_reports_gone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A 403 on page 2 fails the whole run: no partial set, no false GONE.

    FAIL arm: keep the page-1 items when a later page fails — 41 previous URLs
    would read as GONE.
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    timing = _Timing()
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), _items(41, 100)),
        }
    )
    assert _rerun(tmp_path, path, runner, timing) == 0
    capsys.readouterr()
    timing.now += 2
    runner.replies[_QUERY] = {
        "count": 141,
        "pages": [
            {"items": _items(100)},
            {"http": 403, "body": {"message": "rate limit"}},
        ],
    }
    assert _rerun(tmp_path, path, runner, timing) == 1
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["urls"]) == ("rate-limited", [])
    assert _query_line(capsys.readouterr().out).endswith("| n/a | n/a |")


def test_collect_all_is_paced_and_confirmation_is_bounded(tmp_path: Path) -> None:
    """Every later search/code call waits 6.5 s; grep re-fetches stay <= limit.

    FAIL arm: confirm every collected item in `_search_code` — 141 raw fetches,
    not 10.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            _watch(collect="all", grep="x"),
            _watch("hit", _HIT_SHAPE, role="must-hit"),
        ],
    )
    items = _items(141)
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(items[:100], items[100:]),
        },
        raw={f"raw-{index}": b"x" for index in range(141)},
    )
    timing = _Timing()
    assert _rerun(tmp_path, path, runner, timing) == 0
    searches = [call for call in runner.calls if "search/code" in call]
    assert len(timing.sleeps) == len(searches) - 1
    assert set(timing.sleeps) == {6.5}
    fetched = [call for call in runner.calls if call[2].startswith("raw-")]
    assert len(fetched) == 10
    assert _rows(_snapshot(tmp_path))["query"]["confirmed"] == 10


def test_first_full_collection_does_not_diff_a_top_window(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Switching a watch to `all` after a top-10 run diffs nothing on that first run.

    FAIL arm: delete the `not before.complete` branch in `_row` — 131 hits outside
    the old window read as NEW.
    """
    path = tmp_path / "search.toml"
    top = [str(item["html_url"]) for item in _items(10)]
    _write(
        path,
        _all_watch(),
        result=[
            {"watch_id": "query", "date_run": "2026-10-02", "count": 141, "urls": top}
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), _items(41, 100)),
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 0
    first = "n/a (first full collection)"
    assert _query_line(capsys.readouterr().out).endswith(f"| {first} | {first} |")


def test_collect_all_cap_rechecked_on_every_page(tmp_path: Path) -> None:
    """A total that grows past 1000 after page 1 is `uncollectable`, not complete.

    FAIL arm: guard the cap with `page == 1 and` again (codex lens P2).
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: {
                "pages": [
                    {"count": 900, "items": _items(100)},
                    {"count": 1200, "items": _items(100, 100)},
                ]
            },
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 1
    row = _rows(_snapshot(tmp_path))["query"]
    assert (row["status"], row["urls"]) == ("uncollectable", [])
    assert len(_search_calls(runner, _QUERY)) == 2


def test_failed_rerun_keeps_last_answered_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """{A} ok, then a failure, then {A,B}: B is NEW against {A}, not hidden.

    FAIL arm: drop the `if str(run.status) in _COMPARABLE` filter in `_previous`
    (codex lens P2).
    """
    path = tmp_path / "search.toml"
    _write(path, _all_watch())
    timing = _Timing()
    runner = _Runner(
        {_HEALTH: {"count": 1}, _HIT_SHAPE: {"count": 1}, _QUERY: _paged(_items(1))}
    )
    assert _rerun(tmp_path, path, runner, timing) == 0
    timing.now += 2
    runner.replies[_QUERY] = {"http": 500, "body": {"message": "boom"}}
    assert _rerun(tmp_path, path, runner, timing) == 1
    timing.now += 2
    runner.replies[_QUERY] = _paged(_items(2))
    capsys.readouterr()
    assert _rerun(tmp_path, path, runner, timing) == 0
    row = _query_line(capsys.readouterr().out)
    assert row.endswith("| https://github.com/o/r1/blob/HEAD/f.rs |  |")


def test_code_query_defaults_to_collect_all(tmp_path: Path) -> None:
    """With no `collect`, a code QUERY pages every hit; its must-hit control does not.

    FAIL arm: return `Collect.top` for an unset `collect` in `collect_mode`.
    """
    path = tmp_path / "search.toml"
    _write(
        path,
        [
            {"id": "query", "kind": "code", "queries": [_QUERY]},
            {"id": "hit", "kind": "code", "queries": [_HIT_SHAPE], "role": "must-hit"},
        ],
    )
    runner = _Runner(
        {
            _HEALTH: {"count": 1},
            _HIT_SHAPE: {"count": 1},
            _QUERY: _paged(_items(100), _items(41, 100)),
        }
    )
    assert _rerun(tmp_path, path, runner, _Timing()) == 0
    rows = _rows(_snapshot(tmp_path))
    assert (rows["query"]["count"], rows["query"].get("complete")) == (141, True)
    assert rows["hit"].get("complete") is None
    assert len(_search_calls(runner, _QUERY)) == 2
    assert len(_search_calls(runner, _HIT_SHAPE)) == 1


@pytest.mark.parametrize(
    "watch",
    [
        {"id": "x", "kind": "issues", "queries": ["q"], "collect": "all"},
        {
            "id": "x",
            "kind": "code",
            "queries": ["q"],
            "role": "must-hit",
            "collect": "all",
        },
    ],
)
def test_collect_all_only_on_code_query_watches(
    tmp_path: Path, watch: dict[str, object]
) -> None:
    """`collect = "all"` is refused before any network call where it means nothing.

    FAIL arm: delete the collect check in `_validate_watch`.
    """
    path = tmp_path / "search.toml"
    _write(path, [watch])
    runner = _Runner()
    assert main(["rerun", str(path)], tmp_path, runner=runner) == 2
    assert runner.calls == []
