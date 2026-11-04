"""repotools te-review collect through its command line, against TokenEconomizer-shaped state roots on disk."""

import errno
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from repotools.cli import main
from repotools.models import Collection

CHICAGO = ZoneInfo("America/Chicago")
# A past window, 2026-10-05..2026-10-11 in Chicago: [2026-10-05T00:00-05:00, 2026-10-12T00:00-05:00).
START = datetime(2026, 10, 5, tzinfo=CHICAGO).timestamp()
END = datetime(2026, 10, 12, tzinfo=CHICAGO).timestamp()
WINDOW = ["--since", "2026-10-05", "--until", "2026-10-11", "--tz", "America/Chicago"]


def session(session_id: str, ended: float | None, **extra: object) -> dict[str, Any]:
    """A session record with the keys TokenEconomizer 0.1.0's fold writes for a priced session."""
    return {
        "aborts": 0,
        "cache_creation_input_tokens": 10,
        "cache_read_input_tokens": 100,
        "effective_tokens": 1000.0,
        "ended": ended,
        "folded_at": (ended or START) + 60,
        "host": "claude",
        "injected_chars": 0,
        "injection": {"optimizer_tokens": 0.0, "rendered_chars": 0},
        "input_tokens": 5,
        "kind": "session",
        "model": "claude-opus-5-5",
        "nudges": 0,
        "output_tokens": 50,
        "overhead": {"optimizer_tokens": 0, "spiral_judge_tokens": 0.0, "spiral_nudge_writer_tokens": 0.0},
        "priced_by": "model",
        "prompts": 1,
        "repo": "o/r",
        "requests": 3,
        "session_id": session_id,
        "shadow": False,
        "started": (ended or START) - 600,
        "turns": 2,
        "untool": {"pending": False, "proposal": [], "restored": []},
        "untool_applied": [],
        **extra,
    }


def charge(session_id: str, job: str | None, at: float, tokens: float = 7.0) -> dict[str, Any]:
    """An overhead charge as TokenEconomizer 0.1.0's judge job writes it."""
    row: dict[str, Any] = {"at": at, "host": "claude", "job": job, "kind": "overhead", "session_id": session_id}
    row["overhead"] = {"spiral_judge_tokens": tokens, "spiral_nudge_writer_tokens": 0.0}
    if job is None:
        del row["job"]
    return row


def ledger(root: Path, store: str, rows: list[dict[str, Any]]) -> Path:
    path = root / "repos" / store / "claude" / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    return path


def collect(root: Path, out: Path, *window: str) -> None:
    main(["te-review", "collect", *(window or WINDOW), "--out", str(out), "--te-root", str(root)])


def classes(out: Path) -> list[tuple[str, str, str | None, str, int]]:
    rows = json.loads((out / "evidence.json").read_text())["rows"]
    return [(row["kind"], row["session_id"], row["job"], row["row_class"], row["count"]) for row in rows]


def test_a_session_ended_in_the_window_is_collected_into_a_private_complete_dir(tmp_path: Path) -> None:
    source = ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    out = tmp_path / "out"
    collect(tmp_path / "te", out)
    assert sorted(path.name for path in out.iterdir()) == ["COMPLETE", "collection.json", "evidence.json", "sources"]
    files = [path for path in out.rglob("*") if path.is_file()]
    assert {stat.S_IMODE(path.stat().st_mode) for path in files} == {0o600}
    folders = [out, *(path for path in out.rglob("*") if path.is_dir())]
    assert {stat.S_IMODE(path.stat().st_mode) for path in folders} == {0o700}
    assert (out / "sources" / "repos" / "a-1" / "claude" / "ledger.jsonl").read_bytes() == source.read_bytes()
    assert classes(out) == [("session", "s1", None, "in_window", 1)]
    (row,) = json.loads((out / "evidence.json").read_text())["rows"]
    assert row["store"] == "repos/a-1"
    assert row["lines"] == [{"source": "repos/a-1/claude/ledger.jsonl", "line": 1}]
    collection = json.loads((out / "collection.json").read_text())
    assert collection["window"]["start"] == "2026-10-05T00:00:00-05:00"
    assert collection["window"]["end"] == "2026-10-12T00:00:00-05:00"
    assert collection["label"] == "FINAL"
    data = source.read_bytes()
    assert collection["sources"] == [
        {
            "path": "repos/a-1/claude/ledger.jsonl",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "lines": 1,
        }
    ]
    assert (out / "COMPLETE").read_text() == collection["collection_id"] + "\n"
    assert collection["versions"]["schema"] == 1
    assert (
        Collection.model_validate_json((out / "collection.json").read_text()).collection_id
        == collection["collection_id"]
    )


def test_the_collection_id_can_be_recomputed_from_the_bundle_alone(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    ledger(tmp_path / "te", "b-2", [session("s2", START), charge("s2", "j", START)])
    out = tmp_path / "out"
    collect(tmp_path / "te", out)
    shutil.rmtree(tmp_path / "te")  # the ledgers are gone; the bundle must hold every input of the id

    def framed(data: bytes) -> bytes:
        return len(data).to_bytes(8, "big") + data

    collection = Collection.model_validate_json((out / "collection.json").read_text())
    digest = hashlib.sha256(
        framed(collection.window.model_dump_json().encode())
        + framed(collection.versions.model_dump_json(by_alias=True).encode())
    )
    for source in collection.sources:
        data = (out / "sources" / source.path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source.sha256
        digest.update(framed(source.path.encode()) + framed(data))
    digest.update(framed((out / "evidence.json").read_bytes()))
    assert digest.hexdigest() == collection.collection_id


def test_the_window_includes_its_first_instant_and_excludes_the_day_after_until(tmp_path: Path) -> None:
    rows = [session("before", START - 0.001), session("start", START), session("last", END - 0.001)]
    ledger(tmp_path / "te", "a-1", [*rows, session("end", END)])
    collect(tmp_path / "te", tmp_path / "out")
    assert [(sid, row_class) for _, sid, _, row_class, _ in classes(tmp_path / "out")] == [
        ("before", "outside_window"),
        ("start", "in_window"),
        ("last", "in_window"),
        ("end", "outside_window"),
    ]


def test_the_calendar_days_are_read_in_the_given_time_zone(tmp_path: Path) -> None:
    # 2026-10-05T02:00Z is still 2026-10-04 in Chicago, and already 2026-10-05 in Berlin.
    ledger(tmp_path / "te", "a-1", [session("s1", datetime(2026, 10, 5, 2, tzinfo=ZoneInfo("UTC")).timestamp())])
    collect(tmp_path / "te", tmp_path / "chicago")
    collect(tmp_path / "te", tmp_path / "berlin", *WINDOW[:4], "--tz", "Europe/Berlin")
    assert classes(tmp_path / "chicago")[0][3] == "outside_window"
    assert classes(tmp_path / "berlin")[0][3] == "in_window"
    berlin = json.loads((tmp_path / "berlin" / "collection.json").read_text())["window"]
    assert (berlin["start"], berlin["end"]) == ("2026-10-05T00:00:00+02:00", "2026-10-12T00:00:00+02:00")


def test_a_collection_before_the_window_ends_is_interim(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    collect(tmp_path / "te", tmp_path / "out", "--since", "2026-10-05", "--until", "2999-12-31", "--tz", "UTC")
    assert json.loads((tmp_path / "out" / "collection.json").read_text())["label"] == "INTERIM"


def test_a_session_without_a_valid_end_is_kept_as_missing_end(tmp_path: Path) -> None:
    # json.dumps writes NaN, and TokenEconomizer's fold writes with json.dumps.
    nan = session("s2", START) | {"ended": math.nan}
    ledger(tmp_path / "te", "a-1", [session("s1", None, error="transcript unreadable"), nan])
    collect(tmp_path / "te", tmp_path / "out")
    assert [row_class for *_, row_class, _ in classes(tmp_path / "out")] == ["missing_end", "missing_end"]


def test_every_charge_for_a_selected_session_is_matched_whatever_its_time(tmp_path: Path) -> None:
    rows = [session("s1", START + 60), charge("s1", "j1", END + 86400), charge("s1", "j2", START - 86400)]
    ledger(tmp_path / "te", "a-1", [*rows, session("s2", END + 60), charge("s2", "j3", START + 60)])
    collect(tmp_path / "te", tmp_path / "out")
    assert classes(tmp_path / "out") == [
        ("session", "s1", None, "in_window", 1),
        ("overhead", "s1", "j1", "matched", 1),
        ("overhead", "s1", "j2", "matched", 1),
        ("session", "s2", None, "outside_window", 1),
        ("overhead", "s2", "j3", "not_selected", 1),
    ]


def test_identical_repeats_collapse_and_differing_payloads_are_quarantined(tmp_path: Path) -> None:
    one = session("s1", START + 60)
    rows = [one, charge("s1", "j1", START), one, charge("s1", "j1", START), charge("s1", "j1", START + 1)]
    ledger(tmp_path / "te", "a-1", [*rows, session("s2", START), session("s2", START, turns=9)])
    collect(tmp_path / "te", tmp_path / "out")
    assert classes(tmp_path / "out") == [
        ("session", "s1", None, "in_window", 2),
        ("overhead", "s1", "j1", "conflict", 2),
        ("overhead", "s1", "j1", "conflict", 1),
        ("session", "s2", None, "conflict", 1),
        ("session", "s2", None, "conflict", 1),
    ]
    rows = json.loads((tmp_path / "out" / "evidence.json").read_text())["rows"]
    assert [place["line"] for place in rows[0]["lines"]] == [1, 3]
    assert len({row["ref"] for row in rows}) == 5


def test_a_charge_without_a_job_or_a_session_is_ambiguous_or_unmatched(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START), charge("s1", None, START), charge("gone", "j1", START)])
    collect(tmp_path / "te", tmp_path / "out")
    assert classes(tmp_path / "out") == [
        ("session", "s1", None, "in_window", 1),
        ("overhead", "s1", None, "ambiguous", 1),
        ("overhead", "gone", "j1", "unmatched", 1),
    ]


def test_one_session_id_in_two_stores_is_ambiguous_with_its_charges(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START), charge("s1", "j1", START)])
    ledger(tmp_path / "te", "b-2", [session("s1", START)])
    collect(tmp_path / "te", tmp_path / "out")
    assert classes(tmp_path / "out") == [
        ("session", "s1", None, "ambiguous", 1),
        ("overhead", "s1", "j1", "ambiguous", 1),
        ("session", "s1", None, "ambiguous", 1),
    ]
    sources = json.loads((tmp_path / "out" / "collection.json").read_text())["sources"]
    assert [source["path"] for source in sources] == ["repos/a-1/claude/ledger.jsonl", "repos/b-2/claude/ledger.jsonl"]


def refused(capsys: pytest.CaptureFixture[str], root: Path, out: Path, *window: str) -> dict[str, str]:
    """Run a collect that must fail; nothing may be left beside --out."""
    before = sorted(out.parent.iterdir())
    with pytest.raises(SystemExit) as stop:
        collect(root, out, *window)
    assert stop.value.code == 1
    assert sorted(out.parent.iterdir()) == before
    return json.loads(capsys.readouterr().err)


def test_a_malformed_or_truncated_line_fails_the_collection(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = ledger(tmp_path / "te", "a-1", [session("s1", START)])
    path.write_bytes(path.read_bytes() + b"{not json\n")
    assert refused(capsys, tmp_path / "te", tmp_path / "out")["code"] == "MALFORMED_LINE"
    path.write_bytes(path.read_bytes().replace(b"{not json\n", b'{"kind": "session"'))
    error = refused(capsys, tmp_path / "te", tmp_path / "out")
    assert error == {"code": "TRUNCATED_LINE", "error": "repos/a-1/claude/ledger.jsonl:2 has no line end"}


@pytest.mark.parametrize(
    "row",
    [
        session("s1", START, cost_usd=1.0),  # a key TokenEconomizer 0.1.0 does not write
        {k: v for k, v in session("s1", START).items() if k != "overhead"},
        session("s1", START, host="codex"),
        {"kind": "notice", "session_id": "s1"},
        ["session"],
    ],
)
def test_a_row_of_an_unknown_schema_fails_the_collection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], row: object
) -> None:
    path = tmp_path / "te" / "repos" / "a-1" / "claude" / "ledger.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(row) + "\n")
    error = refused(capsys, tmp_path / "te", tmp_path / "out")
    assert error["code"] == "UNKNOWN_SCHEMA"
    assert error["error"].startswith("repos/a-1/claude/ledger.jsonl:1 has unknown schema fingerprint ")


def test_an_unreadable_ledger_fails_the_collection(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    ledger(tmp_path / "te", "b-2", [session("s2", START)]).chmod(0)
    assert refused(capsys, tmp_path / "te", tmp_path / "out")["code"] == "UNREADABLE"


@pytest.mark.parametrize("folder", ["repos/b-2", "repos"])
def test_an_unreadable_store_or_repos_folder_fails_rather_than_being_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], folder: str
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    ledger(tmp_path / "te", "b-2", [session("s2", START)])
    (tmp_path / "te" / folder).chmod(0)
    try:
        error = refused(capsys, tmp_path / "te", tmp_path / "out")
    finally:
        (tmp_path / "te" / folder).chmod(0o700)
    assert error["code"] == "UNREADABLE"


def test_a_ledger_that_changes_while_it_is_read_fails_midway_and_leaves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A FIFO hands the read one text and the re-read another. The second text waits until the first
    # reader has gone (opening a FIFO with no reader fails with ENXIO), so it can't join the first read.
    path = tmp_path / "te" / "repos" / "a-1" / "claude" / "ledger.jsonl"
    path.parent.mkdir(parents=True)
    os.mkfifo(path)
    first = json.dumps(session("s1", START)) + "\n"
    second = first + json.dumps(charge("s1", "late", END)) + "\n"
    done = threading.Event()

    def writer() -> None:
        with path.open("w") as fifo:  # blocks until the read opens it
            fifo.write(first)
        gone = False
        while not done.is_set():
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as error:
                if error.errno != errno.ENXIO:
                    raise
                gone = True
            else:
                # A reader before ENXIO may be the re-read already: closing gives it no bytes, a change too.
                os.write(descriptor, second.encode() if gone else b"")
                os.close(descriptor)
                if gone:
                    return
            time.sleep(0.001)

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    try:
        error = refused(capsys, tmp_path / "te", tmp_path / "out")
    finally:
        done.set()
        thread.join(5)
    assert error == {"code": "SOURCE_CHANGED", "error": "repos/a-1/claude/ledger.jsonl changed while it was read"}


def test_an_existing_out_dir_is_refused_and_left_unchanged(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    collect(tmp_path / "te", tmp_path / "out")
    before = {path: path.read_bytes() for path in (tmp_path / "out").rglob("*") if path.is_file()}
    ledger(tmp_path / "te", "a-1", [session("s1", START), session("s2", START)])
    assert refused(capsys, tmp_path / "te", tmp_path / "out")["code"] == "OUT_EXISTS"
    assert {path: path.read_bytes() for path in (tmp_path / "out").rglob("*") if path.is_file()} == before


@pytest.mark.parametrize(
    ("window", "code"),
    [
        (["--since", "2026-10-05", "--until", "2026-10-04", "--tz", "UTC"], "BAD_WINDOW"),
        (["--since", "2026-10-05", "--until", "2026-10-05", "--tz", "Mars/Olympus"], "BAD_TIMEZONE"),
        (["--since", "2026-10-05", "--until", "2026-10-05", "--tz", "../UTC"], "BAD_TIMEZONE"),
    ],
)
def test_a_bad_window_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], window: list[str], code: str
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    assert refused(capsys, tmp_path / "te", tmp_path / "out", *window)["code"] == code


def test_a_root_without_claude_ledgers_is_refused_rather_than_read_as_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "te" / "repos" / "a-1" / "codex").mkdir(parents=True)
    (tmp_path / "te" / "repos" / "a-1" / "codex" / "ledger.jsonl").write_text("")
    assert refused(capsys, tmp_path / "te", tmp_path / "out")["code"] == "NO_LEDGER"


def test_the_root_is_te_root_then_tokeneconomizer_home_then_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger(tmp_path / "home" / ".tokeneconomizer", "a-1", [session("default", START)])
    ledger(tmp_path / "env", "a-1", [session("env", START)])
    ledger(tmp_path / "flag", "a-1", [session("flag", START)])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("TOKENECONOMIZER_HOME", raising=False)
    main(["te-review", "collect", *WINDOW, "--out", str(tmp_path / "1")])
    monkeypatch.setenv("TOKENECONOMIZER_HOME", str(tmp_path / "env"))
    main(["te-review", "collect", *WINDOW, "--out", str(tmp_path / "2")])
    collect(tmp_path / "flag", tmp_path / "3")
    assert [classes(tmp_path / name)[0][1] for name in ("1", "2", "3")] == ["default", "env", "flag"]


def test_the_collection_id_covers_the_sources_and_window_but_not_the_time(tmp_path: Path) -> None:
    path = ledger(tmp_path / "te", "a-1", [session("s1", START)])
    collect(tmp_path / "te", tmp_path / "1")
    collect(tmp_path / "te", tmp_path / "2")
    path.write_text(path.read_text() + json.dumps(session("old", START - 86400)) + "\n")
    collect(tmp_path / "te", tmp_path / "3")
    collect(tmp_path / "te", tmp_path / "4", *WINDOW[:4], "--tz", "UTC")
    ids = [json.loads((tmp_path / name / "collection.json").read_text())["collection_id"] for name in "1234"]
    assert ids[0] == ids[1]
    assert len(set(ids)) == 3


def test_te_review_needs_a_known_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["te-review"], ["te-review", "carry"]):
        with pytest.raises(SystemExit):
            main(argv)
        assert json.loads(capsys.readouterr().err) == {
            "error": "repotools te-review: the next argument is one of collect, report"
        }


def test_the_installed_command_prints_a_coded_failure(tmp_path: Path) -> None:
    script = Path(sys.executable).parent / "repotools"  # what uv installed from [project.scripts]
    done = subprocess.run(
        [script, "te-review", "collect", *WINDOW, "--out", tmp_path / "out", "--te-root", tmp_path / "none"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert json.loads(done.stderr)["code"] == "NO_LEDGER"
