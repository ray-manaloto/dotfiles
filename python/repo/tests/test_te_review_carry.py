"""repotools te-review carry: an owner's judgments of one collection carried to a newer one, by its command line."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main

from .test_te_review import START, ledger, session
from .test_te_review_judgment import fact, history, learned, paid, read, redirect, run, state
from .test_te_review_worksheet import NOT_RUN, USE, manifest, optimizer


def stores(te: Path, claim: str = "tests run with mise run test", *later: dict[str, Any]) -> None:
    """Store a-1: a session, a nudge (and any later events), a paid fact m1 and an env fact e1 with claim."""
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("nudge", "s1", START + 30), *later])
    learned(te, "a-1", {"m1": fact("ACTIVE")}, {"e1": fact("ACTIVE", claim)})


def fill(out: Path, path: Path, section: str, verdicts: dict[str, str]) -> Path:
    """The collection's worksheet with a verdict per fact id in section, written to path."""
    evidence = read(out, "evidence.json")
    ids = {found["ref"]: found["fact_id"] for found in evidence["facts"]}
    sheet = read(out, "worksheet.json")
    for entry in sheet[section]:
        if ids[entry["ref"]] in verdicts:
            entry["verdict"] = verdicts[ids[entry["ref"]]]
    path.write_text(json.dumps(sheet))
    return path


def carry(a: Path, b: Path, out: Path, *flags: str) -> dict[str, Any]:
    main(["te-review", "carry", "--from", str(a), "--to", str(b), "--out", str(out), *flags])
    return json.loads(Path(out).read_text())


def test_a_judgment_of_an_unchanged_candidate_is_carried_and_a_changed_one_is_listed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    sheet = fill(a, tmp_path / "a-filled.json", "learned_facts", {"m1": "ok", "e1": "wrong"})
    # Later: one more nudge, and the env fact's claim changed.
    stores(te, "tests run with pytest", redirect("nudge", "s1", START + 90))
    run(te, b)
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    b_refs = {found["fact_id"]: found["ref"] for found in read(b, "evidence.json")["facts"]}
    a_refs = {found["fact_id"]: found["ref"] for found in read(a, "evidence.json")["facts"]}
    assert written["collection_id"] == read(b, "collection.json")["collection_id"]
    assert {entry["ref"]: entry["verdict"] for entry in written["learned_facts"]} == {
        b_refs["m1"]: "ok",
        b_refs["e1"]: None,
    }
    assert summary == {
        "collection_id": written["collection_id"],
        "carried": [{"section": "learned_facts", "from_ref": a_refs["m1"], "to_ref": b_refs["m1"]}],
        "not_carried": [{"section": "learned_facts", "from_ref": a_refs["e1"], "reason": "changed"}],
        "conflicts": [],
    }


def refused(capsys: pytest.CaptureFixture[str], *argv: str) -> dict[str, str]:
    with pytest.raises(SystemExit) as stop:
        main(["te-review", "carry", *argv])
    assert stop.value.code == 1
    seen = capsys.readouterr()
    assert seen.out == ""
    return json.loads(seen.err)


def test_an_out_that_exists_is_refused_and_left_as_it_was(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    run(te, b)
    taken = tmp_path / "taken.json"
    taken.write_bytes(b"mine\n")
    for out in (taken, b / "worksheet.json"):
        before = out.read_bytes()
        shown = refused(capsys, "--from", str(a), "--to", str(b), "--out", str(out))
        assert shown["code"] == "OUT_EXISTS"
        assert out.read_bytes() == before


def test_a_judgment_b_already_holds_otherwise_is_a_conflict_and_every_input_stays_byte_identical(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    run(te, b)
    sheet = fill(a, tmp_path / "a-filled.json", "learned_facts", {"m1": "ok", "e1": "wrong"})
    own = fill(b, b / "worksheet.json", "learned_facts", {"m1": "wrong", "e1": "wrong"})
    inputs = [sheet, own, a / "worksheet.json", a / "evidence.json", b / "evidence.json", b / "COMPLETE"]
    before = [path.read_bytes() for path in inputs]
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    refs = {found["fact_id"]: found["ref"] for found in read(b, "evidence.json")["facts"]}
    # B's own judgment stays: carry lists the conflict for the owner and never overwrites it.
    assert {entry["ref"]: entry["verdict"] for entry in written["learned_facts"]} == {
        refs["m1"]: "wrong",
        refs["e1"]: "wrong",
    }
    assert summary["conflicts"] == [{"section": "learned_facts", "from_ref": refs["m1"], "to_ref": refs["m1"]}]
    assert summary["carried"] == [{"section": "learned_facts", "from_ref": refs["e1"], "to_ref": refs["e1"]}]
    assert summary["not_carried"] == []
    assert [path.read_bytes() for path in inputs] == before
    assert (tmp_path / "carried.json").stat().st_mode & 0o777 == 0o600


def useful(te: Path, tmp_path: Path, *rows: dict[str, Any]) -> tuple[Path, Path]:
    """Collection A, where the owner found m1 useful with its paid origin and use receipt, and its filled worksheet.

    rows: what store a-1's ledger holds when B is collected; B is collected by the caller.
    """
    paid = [session("s1", START + 3600), optimizer("s1", START + 100)]
    stores(te)
    ledger(te, "a-1", paid)
    a = tmp_path / "a"
    receipts = manifest(tmp_path / "r", USE)
    run(te, a, "--receipts", str(receipts))
    evidence = read(a, "evidence.json")
    sheet = read(a, "worksheet.json")
    (entry,) = sheet["paid_facts"]
    entry |= {
        "owner_assessment": "useful",
        "reason": "saved_lookup",
        "origin_ref": next(row["ref"] for row in evidence["rows"] if row["job"] == "opt-s1"),
        "use_ref": evidence["receipts"][0]["ref"],
    }
    path = tmp_path / "a-filled.json"
    path.write_text(json.dumps(sheet))
    ledger(te, "a-1", [*paid, *rows])
    return a, path


def test_the_refs_a_judgment_gives_are_carried_as_the_refs_b_gives_the_same_rows_and_receipts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    a, sheet = useful(te, tmp_path)
    # A store that sorts first: every ledger row of B is numbered after its rows.
    ledger(te, "0-new", [session("s0", START + 3600)])
    b = tmp_path / "b"
    run(te, b, "--receipts", str(tmp_path / "r" / "manifest.json"))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    capsys.readouterr()
    evidence = read(b, "evidence.json")
    origin = next(row["ref"] for row in evidence["rows"] if row["job"] == "opt-s1")
    assert origin != json.loads(sheet.read_text())["paid_facts"][0]["origin_ref"]
    (entry,) = written["paid_facts"]
    assert (entry["owner_assessment"], entry["origin_ref"], entry["use_ref"]) == (
        "useful",
        origin,
        evidence["receipts"][0]["ref"],
    )


def test_a_judgment_whose_ref_names_no_single_row_of_b_is_listed_and_not_carried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    # B reads the paid charge twice: its one row now counts two copies, so A's row is not in B.
    a, sheet = useful(te, tmp_path, optimizer("s1", START + 100))
    b = tmp_path / "b"
    run(te, b, "--receipts", str(tmp_path / "r" / "manifest.json"))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    (entry,) = written["paid_facts"]
    assert entry == read(b, "worksheet.json")["paid_facts"][0]
    from_ref = json.loads(sheet.read_text())["paid_facts"][0]["ref"]
    assert summary["not_carried"] == [{"section": "paid_facts", "from_ref": from_ref, "reason": "ref_not_in_b"}]
    assert summary["carried"] == []


def test_a_judgment_whose_digest_names_more_than_one_candidate_is_listed_as_ambiguous(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    # Two not_run receipts with the same content: their entries share one digest.
    receipts = str(manifest(tmp_path / "r", NOT_RUN, NOT_RUN))
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a, "--receipts", receipts)
    run(te, b, "--receipts", receipts)
    sheet = read(a, "worksheet.json")
    deferred = {"outcome": "re_deferred", "reason": "needs_owner", "owner": "the owner", "follow_up": "2026-11-17"}
    sheet["not_run"][0] |= deferred
    path = tmp_path / "a-filled.json"
    path.write_text(json.dumps(sheet))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(path))
    summary = json.loads(capsys.readouterr().out)
    assert written["not_run"] == read(b, "worksheet.json")["not_run"]
    assert summary["not_carried"] == [
        {"section": "not_run", "from_ref": sheet["not_run"][0]["ref"], "reason": "ambiguous"}
    ]


def test_the_ab_outcome_and_the_decision_judge_no_candidate_and_are_listed_not_carried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    run(te, b)
    sheet = read(a, "worksheet.json")
    sheet["mcp_ab"]["outcome"] = "protected_unchanged"
    sheet["decision"] = {"decision": "keep", "settings": None}
    path = tmp_path / "a-filled.json"
    path.write_text(json.dumps(sheet))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(path))
    summary = json.loads(capsys.readouterr().out)
    own = read(b, "worksheet.json")
    assert (written["mcp_ab"], written["decision"]) == (own["mcp_ab"], own["decision"])
    assert summary["not_carried"] == [
        {"section": "mcp_ab", "from_ref": None, "reason": "no_candidate"},
        {"section": "decision", "from_ref": None, "reason": "no_candidate"},
    ]


def test_a_relative_path_or_a_worksheet_of_another_collection_is_refused_and_nothing_is_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    stores(te, "tests run with pytest")
    run(te, b)
    out = str(tmp_path / "carried.json")
    for flag in ("--from", "--to", "--out"):
        argv = dict.fromkeys(("--from", "--to", "--out"), "")
        argv |= {"--from": str(a), "--to": str(b), "--out": out, flag: "relative"}
        assert refused(capsys, *[part for pair in argv.items() for part in pair])["code"] == "RELATIVE_PATH"
    # B's own worksheet given as A's: #435's check refuses it.
    shown = refused(capsys, "--from", str(a), "--to", str(b), "--out", out, "--worksheet", str(b / "worksheet.json"))
    assert shown["code"] == "STALE_WORKSHEET"
    assert not Path(out).exists()


def test_the_carried_worksheet_is_what_report_reads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    te = tmp_path / "te"
    stores(te)
    a, b = tmp_path / "a", tmp_path / "b"
    run(te, a)
    run(te, b)
    sheet = fill(a, tmp_path / "a-filled.json", "learned_facts", {"m1": "ok", "e1": "wrong"})
    out = tmp_path / "carried.json"
    carry(a, b, out, "--worksheet", str(sheet))
    capsys.readouterr()
    main(["te-review", "report", "--evidence", str(b), "--worksheet", str(out)])
    shown = json.loads(capsys.readouterr().out)
    assert shown["review"]["learned_facts"] == {"wrong": 1, "ok": 1, "unknown": 0, "not_reviewed": 0}


def run_on(te: Path, tmp_path: Path, receipts: Path) -> tuple[Path, Path]:
    """Collection A with receipts, where the owner ran its not_run item, its evidence the fact_use receipt."""
    a = tmp_path / "a"
    run(te, a, "--receipts", str(receipts))
    evidence = read(a, "evidence.json")
    sheet = read(a, "worksheet.json")
    use = next(found["ref"] for found in evidence["receipts"] if found["kind"] == "fact_use")
    sheet["not_run"][0] |= {"outcome": "run", "evidence_ref": use}
    path = tmp_path / "a-filled.json"
    path.write_text(json.dumps(sheet))
    return a, path


def test_a_receipt_renumbered_in_b_is_still_the_same_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    receipts = manifest(tmp_path / "r", USE, NOT_RUN)
    a, sheet = run_on(te, tmp_path, receipts)
    # B's manifest lists one more receipt first: the same files, every one numbered after it.
    (tmp_path / "r" / "extra.json").write_bytes(b"another\n")
    listed = json.loads(receipts.read_text())["receipts"]
    extra = {**listed[1], "path": "extra.json", "sha256": hashlib.sha256(b"another\n").hexdigest()}
    later = tmp_path / "r" / "later.json"
    later.write_text(json.dumps({"receipts": [extra, *listed]}))
    b = tmp_path / "b"
    run(te, b, "--receipts", str(later))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    evidence = read(b, "evidence.json")
    use = next(found["ref"] for found in evidence["receipts"] if found["kind"] == "fact_use")
    assert use != json.loads(sheet.read_text())["not_run"][0]["evidence_ref"]
    assert summary["not_carried"] == []
    (entry,) = [found for found in written["not_run"] if found["outcome"] == "run"]
    assert entry["evidence_ref"] == use


def test_a_receipt_that_links_another_session_in_b_is_not_the_same_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    ledger(te, "a-1", [session("s1", START + 3600), session("s2", START + 3600)])
    receipts = manifest(tmp_path / "r", USE, NOT_RUN)
    a, sheet = run_on(te, tmp_path, receipts)
    # The same fact_use file, now said to show the fact's use in s2.
    use, not_run = json.loads(receipts.read_text())["receipts"]
    later = tmp_path / "r" / "later.json"
    later.write_text(json.dumps({"receipts": [{**use, "sessions": ["s2"]}, not_run]}))
    b = tmp_path / "b"
    run(te, b, "--receipts", str(later))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    assert written["not_run"] == read(b, "worksheet.json")["not_run"]
    from_ref = json.loads(sheet.read_text())["not_run"][0]["ref"]
    assert summary["not_carried"] == [{"section": "not_run", "from_ref": from_ref, "reason": "ref_not_in_b"}]


def folds(te: Path, tmp_path: Path, imported: int = 0) -> tuple[Path, Path]:
    """Collection A, where store b-2's import folded session near, and the owner ran its not_run item, its
    evidence that fold."""
    stores(te)
    done = START + 7200
    ledger(te, "b-2", [paid("near", START + 100, done + 30, 50)])
    state(te, "b-2", "history.json", history("done", START + 7000, done, imported))
    a = tmp_path / "a"
    run(te, a, "--receipts", str(manifest(tmp_path / "r", NOT_RUN)))
    sheet = read(a, "worksheet.json")
    (fold,) = read(a, "evidence.json")["import_folds"]
    sheet["not_run"][0] |= {"outcome": "run", "evidence_ref": fold["ref"]}
    path = tmp_path / "a-filled.json"
    path.write_text(json.dumps(sheet))
    return a, path


def test_a_fold_whose_session_is_renumbered_in_b_is_still_the_same_fold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    a, sheet = folds(te, tmp_path)
    # A store that sorts first: the folded session's row is numbered after its row.
    ledger(te, "0-new", [session("s0", START + 3600)])
    b = tmp_path / "b"
    run(te, b, "--receipts", str(tmp_path / "r" / "manifest.json"))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    (fold,) = read(b, "evidence.json")["import_folds"]
    assert fold["session_ref"] != read(a, "evidence.json")["import_folds"][0]["session_ref"]
    assert summary["not_carried"] == []
    assert written["not_run"][0]["evidence_ref"] == fold["ref"]


def test_a_fold_whose_import_changed_in_b_is_not_the_same_fold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    a, sheet = folds(te, tmp_path)
    # The same import, under the same ref, now saying it imported one session.
    state(te, "b-2", "history.json", history("done", START + 7000, START + 7200, 1))
    b = tmp_path / "b"
    run(te, b, "--receipts", str(tmp_path / "r" / "manifest.json"))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    (fold,) = read(b, "evidence.json")["import_folds"]
    assert fold["import_ref"] == read(a, "evidence.json")["import_folds"][0]["import_ref"]
    assert written["not_run"] == read(b, "worksheet.json")["not_run"]
    from_ref = json.loads(sheet.read_text())["not_run"][0]["ref"]
    assert summary["not_carried"] == [{"section": "not_run", "from_ref": from_ref, "reason": "ref_not_in_b"}]


def test_a_real_work_receipt_added_in_b_leaves_every_judged_candidate_the_same(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    stores(te)
    receipts = manifest(tmp_path / "r", USE)
    a = tmp_path / "a"
    run(te, a, "--receipts", str(receipts))
    sheet = fill(a, tmp_path / "a-filled.json", "learned_facts", {"m1": "ok"})
    # B's manifest lists a real_work receipt for s1 first: the fact's use receipt is numbered after it.
    (tmp_path / "r" / "work.json").write_bytes(b"work\n")
    work = {
        "path": "work.json",
        "sha256": hashlib.sha256(b"work\n").hexdigest(),
        "timestamp": "2026-10-06T09:00:00-05:00",
        "kind": "real_work",
        "sessions": ["s1"],
    }
    later = tmp_path / "r" / "later.json"
    later.write_text(json.dumps({"receipts": [work, *json.loads(receipts.read_text())["receipts"]]}))
    b = tmp_path / "b"
    run(te, b, "--receipts", str(later))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(sheet))
    summary = json.loads(capsys.readouterr().out)
    (m1,) = [found for found in read(b, "evidence.json")["facts"] if found["fact_id"] == "m1"]
    (old,) = [found for found in read(a, "evidence.json")["facts"] if found["fact_id"] == "m1"]
    assert m1["receipts"] != old["receipts"]
    assert summary["not_carried"] == []
    assert {entry["ref"]: entry["verdict"] for entry in written["learned_facts"]}[m1["ref"]] == "ok"


def test_a_judged_fold_whose_rows_are_renumbered_in_b_is_still_carried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    a, _ = folds(te, tmp_path)
    sheet = read(a, "worksheet.json")
    (entry,) = [found for found in sheet["imports"] if found["entry"] == "fold"]
    entry["verdict"] = "candidate"
    path = tmp_path / "a-fold.json"
    path.write_text(json.dumps(sheet))
    # A store that sorts first, and one more event before the import: the fold's session and import refs move.
    ledger(te, "0-new", [session("s0", START + 3600)])
    state(te, "0-new", "events.jsonl", [redirect("nudge", "s0", START + 30)])
    b = tmp_path / "b"
    run(te, b, "--receipts", str(tmp_path / "r" / "manifest.json"))
    written = carry(a, b, tmp_path / "carried.json", "--worksheet", str(path))
    summary = json.loads(capsys.readouterr().out)
    (fold,) = read(b, "evidence.json")["import_folds"]
    (old,) = read(a, "evidence.json")["import_folds"]
    assert (fold["session_ref"], fold["import_ref"]) != (old["session_ref"], old["import_ref"])
    assert summary["not_carried"] == []
    assert [found["verdict"] for found in written["imports"] if found["ref"] == fold["ref"]] == ["candidate"]
