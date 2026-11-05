"""repotools te-review report through its command line, on collections te-review collect froze on disk."""

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main
from repotools.models import PrivateReport

from .test_te_review import START, WINDOW, charge, collect, ledger, session
from .test_te_review_judgment import DAY, cadence_receipt, receipts, run

REPO = Path(__file__).resolve().parents[3]


def frozen(tmp_path: Path, *rows: dict[str, Any]) -> Path:
    """A collection of one store holding rows."""
    ledger(tmp_path / "te", "a-1", list(rows))
    collect(tmp_path / "te", tmp_path / "out")
    return tmp_path / "out"


def report(capsys: pytest.CaptureFixture[str], evidence: Path, *mode: str) -> dict[str, Any]:
    main(["te-review", "report", "--evidence", str(evidence), *mode])
    return json.loads(capsys.readouterr().out)


def test_without_receipts_the_headline_cohort_is_empty_and_its_share_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START + 60), charge("s1", "j1", START + 120, tokens=10.0))
    shown = report(capsys, out)
    assert shown["scope"] == "recorded charges"
    assert (shown["label"], shown["since"], shown["until"]) == ("FINAL", "2026-10-05", "2026-10-11")
    headline = shown["headline"]
    assert (headline["sessions"], headline["charges"], headline["share"]) == (0, 0, None)
    assert (headline["status"], headline["above_5_percent"]) == ("UNKNOWN", "UNKNOWN")
    assert shown["session_classes"] == [
        {"session_class": "real_work", "sessions": 0},
        {"session_class": "synthetic", "sessions": 0},
        {"session_class": "unknown", "sessions": 1},
    ]
    # D1: the selected share is private only; D9: the public excluded rows give counts, never tokens.
    assert "selected" not in shown
    assert {key for row in shown["excluded"] for key in row} == {"reason", "rows", "sessions"}
    # The non-headline basis: 1000 effective, 10 overhead.
    selected = private(capsys, out)["selected"]
    assert (selected["sessions"], selected["charges"]) == (1, 1)
    assert (selected["effective_tokens"], selected["overhead_tokens"]) == (1000.0, 10.0)
    assert selected["share"] == pytest.approx(10 / 1010)
    assert (selected["status"], selected["above_5_percent"]) == ("KNOWN", "NO")
    assert selected["components"]["spiral_judge_tokens"] == 10.0
    assert shown["cadence"] == "UNKNOWN"
    assert shown["policy_era_candidates"] == [{"folded_on": "2026-10-05", "sessions": 1}]
    first = {row["reason"]: row["rows"] for row in shown["excluded"]}
    assert first["UNCLASSIFIED"] == 1
    assert first["SESSION_EXCLUDED"] == 1
    assert sum(first.values()) == 2


MIXED = (
    # D1 and D5: unclassified, fallback-priced and failed sessions with their charges, and an unmatched charge.
    (
        session("s1", START, effective_tokens=1000.0),
        charge("s1", "j1", START, tokens=13.0),
        session("s2", START, priced_by="fallback", effective_tokens=700.0),
        charge("s2", "j2", START, tokens=29.0),
        charge("s2", "j3", START, tokens=3.0),
        session("s3", START, error="Traceback", effective_tokens=400.0),
        charge("s3", "j4", START, tokens=17.0),
        charge("gone", "j5", START, tokens=5.0),
    ),
    62 / 2162,
    {
        "UNMATCHED": (1, 0),
        "ERROR": (1, 1),
        "FALLBACK_PRICING": (1, 1),
        "UNCLASSIFIED": (1, 1),
        "SESSION_EXCLUDED": (4, 0),
    },
)
NO_USAGE = (
    # D6: sessions with no recorded usage bring only their charges, which alone would be the selected numerator.
    (
        session("s1", START, effective_tokens=1000.0),
        session("s2", START, priced_by="no_usage", effective_tokens=None),
        charge("s2", "j1", START, tokens=13.0),
        session("s3", START, error="transcript unreadable", effective_tokens=None),
        charge("s3", "j2", START, tokens=7.0),
    ),
    20 / 1020,
    {"MISSING_USAGE": (1, 1), "ERROR": (1, 1), "UNCLASSIFIED": (1, 1), "SESSION_EXCLUDED": (2, 0)},
)
HEADLINE_BESIDE = (
    # D9: a receipted session and an uncharged unclassified one. Under D5/D6 the UNCLASSIFIED total, 500, was
    # pure effective, so headline overhead / (headline effective + overhead + 500) = 10 / 1510 rebuilt the share.
    (
        session("s1", START, effective_tokens=1000.0),
        charge("s1", "j1", START, tokens=10.0),
        session("s2", START, effective_tokens=500.0),
    ),
    10 / 1510,
    {"UNCLASSIFIED": (1, 1)},
)


@pytest.mark.parametrize(
    ("case", "receipted"),
    [(MIXED, ()), (NO_USAGE, ()), (HEADLINE_BESIDE, ("s1",))],
    ids=["mixed-reasons", "no-usage", "headline-beside-unclassified"],
)
def test_no_public_number_or_ratio_of_public_numbers_gives_back_the_private_selected_share(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: tuple[tuple[dict[str, Any], ...], float, dict[str, tuple[int, int]]],
    receipted: tuple[str, ...],
) -> None:
    rows, fraction, counts = case
    te = tmp_path / "te"
    ledger(te, "a-1", list(rows))
    out = tmp_path / "out"
    flags = (
        ("--receipts", str(receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": [*receipted]}))))
        if receipted
        else ()
    )
    run(te, out, *flags)
    full = private(capsys, out)
    assert full["selected"]["share"] == pytest.approx(fraction)
    assert full["excluded"][0].keys() >= {"effective_tokens", "overhead_tokens"}
    shown = report(capsys, out)
    assert shown["headline"]["sessions"] == len(receipted)
    # D9: excluded rows carry row and session counts, never tokens; each session counts once, by its first reason.
    assert {key for row in shown["excluded"] for key in row} == {"reason", "rows", "sessions"}
    assert {row["reason"]: (row["rows"], row["sessions"]) for row in shown["excluded"] if row["rows"]} == counts
    assert shown["withheld"] == "excluded rows show counts only; their spend is only in --private"
    seen = [n for n in numbers(shown) if n]
    assert not [n for n in seen if n == pytest.approx(fraction)]
    for a in seen:
        for b in seen:
            assert a / b != pytest.approx(fraction)
            assert a / (a + b) != pytest.approx(fraction)
            for c in seen:
                assert a / (b + c) != pytest.approx(fraction)
                assert a / (a + b + c) != pytest.approx(fraction)


def test_public_coverage_counts_headline_and_selected_sessions_and_those_with_no_recorded_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # D3: two selected sessions, one whose transcript failed; none is in the headline without a real_work receipt.
    out = frozen(tmp_path, session("s1", START), session("s2", START, error="Traceback"), charge("s2", "j1", START))
    assert report(capsys, out)["coverage"] == {"headline_sessions": 0, "selected_sessions": 2, "no_recorded_usage": 1}


def test_receipted_real_work_makes_the_headline_and_its_proven_cadence_labels_the_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    rows = [session("work", START + DAY + 3600), charge("work", "j1", START + DAY + 3700, tokens=100.0)]
    ledger(te, "a-1", [*rows, session("probe", START + DAY + 3600), session("other", START + DAY + 3600)])
    real = receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["work"]}))
    synthetic = receipts(tmp_path / "s", "m.json", ("synthetic", {"sessions": ["probe"]}))
    proof = cadence_receipt(tmp_path / "c", ["work", "probe", "other"])
    out = tmp_path / "out"
    run(te, out, "--receipts", str(real), "--synthetic-manifest", str(synthetic), "--cadence-receipt", str(proof))
    shown = report(capsys, out)
    headline = shown["headline"]
    assert (headline["sessions"], headline["charges"], headline["share"]) == (1, 1, pytest.approx(100 / 1100))
    assert headline["above_5_percent"] == "YES"
    assert shown["session_classes"] == [
        {"session_class": "real_work", "sessions": 1},
        {"session_class": "synthetic", "sessions": 1},
        {"session_class": "unknown", "sessions": 1},
    ]
    assert {row["reason"]: row["rows"] for row in shown["excluded"] if row["rows"]} == {
        "SYNTHETIC": 1,
        "UNCLASSIFIED": 1,
    }
    # Every headline session was folded under the proven cadence 1.
    assert shown["cadence"] == "1"
    assert shown["coverage"] == {"headline_sessions": 1, "selected_sessions": 3, "no_recorded_usage": 0}


def test_headline_sessions_under_different_or_unproven_cadences_leave_the_cadence_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("before", START + 3600), session("after", START + DAY + 3600)])
    real = receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["before", "after"]}))
    out = tmp_path / "out"
    run(
        te, out, "--receipts", str(real), "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["before", "after"]))
    )
    assert report(capsys, out)["cadence"] == "UNKNOWN"


def private(capsys: pytest.CaptureFixture[str], evidence: Path) -> dict[str, Any]:
    return report(capsys, evidence, "--private")


def reasons(shown: dict[str, Any]) -> list[list[str]]:
    return [row["reasons"] for row in shown["rows"]]


def first(shown: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The excluded counts that are not empty, by reason."""
    return {row.pop("reason"): row for row in shown["excluded"] if row["rows"]}


def test_a_finite_positive_fallback_priced_session_stays_outside_the_headline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START, priced_by="fallback", effective_tokens=500.0))
    shown = private(capsys, out)
    assert reasons(shown) == [["FALLBACK_PRICING", "UNCLASSIFIED"]]
    assert shown["report"]["headline"]["effective_tokens"] == 0.0
    assert first(shown) == {
        "FALLBACK_PRICING": {"rows": 1, "effective_tokens": 500.0, "overhead_tokens": 0.0, "invalid_amounts": 0}
    }


def test_a_row_with_overlapping_reasons_is_counted_once_under_the_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    row = session("s1", START, imported=True, priced_by="no_usage", effective_tokens=None)
    shown = private(capsys, frozen(tmp_path, row, session("s2", START, priced_by="estimate")))
    assert reasons(shown) == [
        ["IMPORTED", "MISSING_USAGE", "UNCLASSIFIED"],
        ["UNKNOWN_PRICING_STATUS", "UNCLASSIFIED"],
    ]
    counts = first(shown)
    assert {reason: count["rows"] for reason, count in counts.items()} == {"IMPORTED": 1, "UNKNOWN_PRICING_STATUS": 1}
    # The imported session is out of the selected basis too, as TokenEconomizer's summarize leaves it out.
    assert shown["selected"]["sessions"] == 1
    assert shown["report"]["session_classes"][2] == {"session_class": "unknown", "sessions": 1}


def test_a_negative_charge_excludes_itself_and_its_session_but_its_spend_stays_visible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START), charge("s1", "j1", START, tokens=-5.0))
    shown = private(capsys, out)
    assert reasons(shown) == [["UNCLASSIFIED", "CHARGE_EXCLUDED"], ["BAD_AMOUNT", "SESSION_EXCLUDED"]]
    assert first(shown)["BAD_AMOUNT"] == {
        "rows": 1,
        "effective_tokens": 0.0,
        "overhead_tokens": -5.0,
        "invalid_amounts": 0,
    }


def test_a_bad_charge_takes_its_receipted_session_and_every_sibling_charge_out_of_the_headline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    at = START + DAY + 3600
    ledger(
        te, "a-1", [session("work", at), charge("work", "j1", at, tokens=-5.0), charge("work", "j2", at, tokens=13.0)]
    )
    out = tmp_path / "out"
    run(te, out, "--receipts", str(receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["work"]}))))
    shown = private(capsys, out)
    assert reasons(shown) == [["CHARGE_EXCLUDED"], ["BAD_AMOUNT", "SESSION_EXCLUDED"], ["SESSION_EXCLUDED"]]
    headline = shown["report"]["headline"]
    assert (headline["sessions"], headline["charges"], headline["share"]) == (0, 0, None)
    assert headline["above_5_percent"] == "UNKNOWN"


def test_a_non_finite_amount_is_bad_and_makes_the_selected_share_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # json.dumps writes Infinity and NaN, as TokenEconomizer's fold would.
    out = frozen(tmp_path, session("s1", START, effective_tokens=math.inf), session("s2", START, effective_tokens=-1))
    shown = private(capsys, out)
    assert PrivateReport.model_validate(shown).selected.effective_tokens is None
    assert reasons(shown) == [["BAD_AMOUNT", "UNCLASSIFIED"], ["BAD_AMOUNT", "UNCLASSIFIED"]]
    assert first(shown)["BAD_AMOUNT"] == {
        "rows": 2,
        "effective_tokens": -1.0,
        "overhead_tokens": 0.0,
        "invalid_amounts": 1,
    }
    selected = shown["selected"]
    assert (selected["status"], selected["share"], selected["above_5_percent"]) == ("UNKNOWN", None, "UNKNOWN")
    # JSON has no Infinity: the sum shows as null, which the report's own schema accepts.
    assert selected["effective_tokens"] is None


def test_a_session_whose_transcript_failed_is_counted_as_an_error_with_its_spend(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START, error="Traceback", effective_tokens=700.0))
    shown = private(capsys, out)
    assert reasons(shown) == [["ERROR", "UNCLASSIFIED"]]
    assert first(shown) == {
        "ERROR": {"rows": 1, "effective_tokens": 700.0, "overhead_tokens": 0.0, "invalid_amounts": 0}
    }


def test_a_zero_denominator_gives_an_unknown_share(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    shown = private(capsys, frozen(tmp_path, session("s1", START, effective_tokens=0.0)))
    assert (shown["selected"]["sessions"], shown["selected"]["status"]) == (1, "UNKNOWN")


def test_an_unclassified_session_is_excluded_as_unclassified_not_imported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shown = private(capsys, frozen(tmp_path, session("s1", START, imported=False)))
    assert reasons(shown) == [["UNCLASSIFIED"]]
    assert first(shown) == {
        "UNCLASSIFIED": {"rows": 1, "effective_tokens": 1000.0, "overhead_tokens": 0.0, "invalid_amounts": 0}
    }


def test_another_recognized_overhead_key_counts_toward_the_total_on_its_own_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    row = session("s1", START, overhead={"untool_classify_tokens": 40.0, "optimizer_tokens": 10})
    selected = private(capsys, frozen(tmp_path, row, charge("s1", "j1", START, tokens=50.0)))["selected"]
    assert selected["components"] == {
        "optimizer_tokens": 10.0,
        "untool_classify_tokens": 40.0,
        "untool_judge_tokens": 0.0,
        "codex_untool_adapt_tokens": 0.0,
        "spiral_judge_tokens": 50.0,
        "spiral_nudge_writer_tokens": 0.0,
    }
    assert selected["overhead_tokens"] == 100.0
    assert selected["share"] == pytest.approx(100 / 1100)
    assert selected["above_5_percent"] == "YES"


def numbers(value: object) -> list[float]:
    """Every number in a JSON value."""
    if isinstance(value, dict):
        return [n for item in value.values() for n in numbers(item)]
    if isinstance(value, list):
        return [n for item in value for n in numbers(item)]
    return [value] if isinstance(value, int | float) and not isinstance(value, bool) else []


def test_public_totals_leave_unknown_keys_out_and_show_only_how_many(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spend = {"spiral_judge_tokens": 1.0}
    rows = [session("s1", START, overhead={**spend, "mystery_tokens": 7777.0}), charge("s1", "j1", START, tokens=10.0)]
    out = frozen(tmp_path / "a", *rows)
    main(["te-review", "report", "--evidence", str(out)])
    seen = capsys.readouterr()
    public = json.loads(seen.out)
    assert "mystery" not in seen.out + seen.err
    assert public.pop("unknown_keys") == "unknown keys: 1 (excluded from public totals)"
    # Every public number is what the same rows without the key give, so no subtraction recovers its sum.
    plain = report(capsys, frozen(tmp_path / "b", session("s1", START, overhead=spend), rows[1]))
    assert plain.pop("unknown_keys") == "unknown keys: 0 (excluded from public totals)"
    for shown in (public, plain):
        for basis in (shown["headline"],):
            basis.pop("unknown_overhead_keys")
    assert public == plain
    assert not {7777.0, 7788.0} & set(numbers(public))
    full = private(capsys, out)
    assert full["unknown_overhead_keys"] == {"mystery_tokens": 7777.0}
    assert full["all_keys"]["selected"]["overhead_tokens"] == 7788.0
    assert full["all_keys"]["selected"]["share"] == pytest.approx(7788 / 8788)
    assert first(full["all_keys"])["UNCLASSIFIED"]["overhead_tokens"] == 7778.0
    assert full["selected"]["overhead_tokens"] == 11.0


def test_sessions_are_grouped_by_fold_day_only_as_policy_era_candidates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = [session("s1", START, folded_at=START + 86400 * 2), session("s2", START), session("s3", START)]
    rows += [session("s4", START, folded_at=math.nan), session("s5", START, folded_at=1e300)]
    shown = report(capsys, frozen(tmp_path, *rows))
    assert shown["cadence"] == "UNKNOWN"
    assert shown["policy_era_candidates"] == [
        {"folded_on": "2026-10-05", "sessions": 2},
        {"folded_on": "2026-10-07", "sessions": 1},
        {"folded_on": None, "sessions": 2},
    ]


def refused(capsys: pytest.CaptureFixture[str], evidence: Path | str, *mode: str) -> dict[str, str]:
    with pytest.raises(SystemExit) as stop:
        main(["te-review", "report", "--evidence", str(evidence), *mode])
    assert stop.value.code == 1
    seen = capsys.readouterr()
    assert seen.out == ""
    return json.loads(seen.err)


def test_a_folder_without_complete_is_refused_with_its_code_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START))
    (out / "COMPLETE").unlink()
    assert refused(capsys, out) == {"code": "NOT_COMPLETE"}
    assert refused(capsys, out, "--private") == {"code": "NOT_COMPLETE", "error": f"{out} has no COMPLETE marker"}


@pytest.mark.parametrize(
    ("name", "change", "code"),
    [
        ("sources/repos/a-1/claude/ledger.jsonl", b"\n", "HASH_MISMATCH"),
        ("evidence.json", b" ", "HASH_MISMATCH"),
        ("COMPLETE", b"0", "HASH_MISMATCH"),
        ("collection.json", b"x", "BAD_BUNDLE"),
    ],
)
def test_a_bundle_that_no_longer_matches_its_hashes_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, change: bytes, code: str
) -> None:
    out = frozen(tmp_path, session("s1", START))
    path = out / name
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + change)
    assert refused(capsys, out) == {"code": code}


def test_a_bundle_missing_a_source_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = frozen(tmp_path, session("s1", START))
    (out / "sources" / "repos" / "a-1" / "claude" / "ledger.jsonl").unlink()
    assert refused(capsys, out) == {"code": "BAD_BUNDLE"}


def test_a_relative_evidence_or_out_path_and_both_modes_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    out = frozen(tmp_path, session("s1", START))
    monkeypatch.chdir(tmp_path)
    assert refused(capsys, "out") == {"code": "RELATIVE_PATH"}
    assert refused(capsys, out, "--public", "--private")["code"] == "BAD_MODE"
    with pytest.raises(SystemExit):
        main(["te-review", "collect", *WINDOW, "--out", "new", "--te-root", str(tmp_path / "te")])
    assert json.loads(capsys.readouterr().err)["code"] == "RELATIVE_PATH"
    assert not (tmp_path / "new").exists()


def test_public_is_the_default_and_private_must_be_asked_for(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = frozen(tmp_path, session("s1", START))
    assert report(capsys, out) == report(capsys, out, "--public")
    shown = private(capsys, out)
    assert shown["report"] == report(capsys, out)
    assert shown["collection_id"] == (out / "COMPLETE").read_text().strip()
    assert (shown["tz"], shown["rows"][0]["store"], shown["rows"][0]["session_id"]) == (
        "America/Chicago",
        "repos/a-1",
        "s1",
    )


CANARY = "CANARY-7f3a"


def test_secret_like_strings_never_reach_any_public_channel(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    secret = f"sk-ant-{CANARY}"
    rows = [
        session(
            f"{CANARY}-session",
            START,
            error=f"Traceback {secret}",
            injection={"facts": [f"use {secret} for the deploy"]},
            untool={"proposal": [{"tool": "Bash", "args": f"curl -H {secret}"}]},
            model=f"model-{CANARY}",
            overhead={f"{CANARY}_tokens": 3.0, "spiral_judge_tokens": float("nan")},
        ),
        charge(f"{CANARY}-session", f"{CANARY}-job", START),
        charge(f"{CANARY}-gone", None, START),
    ]
    ledger(tmp_path / f"te-{CANARY}", f"{CANARY}-store", rows)
    out = tmp_path / f"out-{CANARY}"
    collect(tmp_path / f"te-{CANARY}", out)
    main(["te-review", "report", "--evidence", str(out)])
    seen = capsys.readouterr()
    assert json.loads(seen.out)["unknown_keys"] == "unknown keys: 1 (excluded from public totals)"
    assert CANARY not in seen.out + seen.err
    # Errors: a missing folder, a tampered bundle and a bad mode name their paths only in private mode.
    for evidence, mode in ((tmp_path / f"{CANARY}-none", ()), (out, ("--public", "--private"))):
        assert CANARY not in json.dumps(refused(capsys, evidence, *mode))
    # An argument the parser rejects is echoed in its message, so a parse error is the code alone in any mode.
    for mode in ((), ("--private",), ("--private", "--no-private", "--public")):
        assert refused(capsys, out, *mode, f"{CANARY}-extra") == {"code": "BAD_ARGUMENTS"}
    (out / "evidence.json").chmod(0o600)
    (out / "evidence.json").write_text(f'"{secret}"')
    assert refused(capsys, out) == {"code": "BAD_BUNDLE"}


def task(*args: str) -> subprocess.CompletedProcess[str]:
    """A te-review mise task, run from this checkout as the owner runs it."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    return subprocess.run(["mise", "run", *args], capture_output=True, check=False, text=True, cwd=REPO, env=env)


def coded(done: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """The task's coded failure line, without mise's own lines around it."""
    (line,) = [line for line in done.stderr.splitlines() if line.startswith('{"code"')]
    return json.loads(line)


def test_the_mise_tasks_collect_and_report_and_refuse_a_relative_path(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START)])
    out = tmp_path / "out"
    window = [*WINDOW, "--te-root", str(tmp_path / "te")]
    done = task("//repo:te-review-collect", *window, "--out", "out")
    assert (done.returncode, coded(done)["code"]) == (1, "RELATIVE_PATH")
    assert task("//repo:te-review-collect", *window, "--out", str(out)).returncode == 0
    done = task("//repo:te-review-report", "--evidence", "out")
    assert (done.returncode, coded(done)) == (1, {"code": "RELATIVE_PATH"})
    done = task("//repo:te-review-report", "--evidence", str(out))
    unclassified = {"reason": "UNCLASSIFIED", "rows": 1, "sessions": 1}
    assert unclassified in json.loads(done.stdout)["excluded"]
    done = task("//repo:te-review-report", "--evidence", str(out), "--private")
    assert json.loads(done.stdout)["rows"][0]["session_id"] == "s1"
