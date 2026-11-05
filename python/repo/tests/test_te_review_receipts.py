"""repotools te-review receipts draft on fixture TE state and transcripts; collect reads what it writes."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main
from tests.test_te_review import START, WINDOW, charge, ledger, session
from tests.test_te_review_judgment import fact, learned, redirect, state


def iso(at: float) -> str:
    """A Unix time as Claude Code writes a transcript timestamp: UTC, milliseconds, Z."""
    return datetime.fromtimestamp(at, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def transcript(folder: Path, session_id: str, *records: dict[str, Any]) -> Path:
    """A Claude Code transcript, <session id>.jsonl, holding a user prompt and then records."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{session_id}.jsonl"
    prompt = {"type": "user", "sessionId": session_id, "timestamp": iso(START), "message": {"content": "hi"}}
    path.write_text("".join(json.dumps(record) + "\n" for record in (prompt, *records)))
    return path


def draft(te: Path, projects: Path, out: Path, *flags: str) -> dict[str, Any]:
    """Run the draft; return its summary line."""
    main(
        [
            "te-review",
            "receipts",
            "draft",
            *WINDOW,
            "--out",
            str(out),
            "--te-root",
            str(te),
            "--transcripts",
            str(projects),
            *flags,
        ]
    )
    return {}


def test_a_session_with_a_transcript_gets_a_real_work_receipt_collect_accepts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    # The judge's charge for the session is a ledger row of its own; only the session gets a receipt.
    ledger(te, "a-1", [session("s1", START + 3600), charge("s1", "judge", START + 600)])
    path = transcript(projects / "-Users-me-r", "s1")
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"real_work": 1, "host_delivery": 0, "fact_injection": 0}
    assert summary["without_receipt"] == []
    (receipt,) = json.loads(out.read_text())["receipts"]
    assert receipt["kind"] == "real_work"
    assert receipt["path"] == str(path)
    assert receipt["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert receipt["sessions"] == ["s1"]
    collection = tmp_path / "collection"
    main(["te-review", "collect", *WINDOW, "--out", str(collection), "--te-root", str(te), "--receipts", str(out)])
    evidence = json.loads((collection / "evidence.json").read_text())
    (row,) = evidence["sessions"]
    assert (row["session_id"], row["cohort"]) == ("s1", "real_work")


def collect(te: Path, into: Path, *flags: str) -> dict[str, Any]:
    """Collect with the draft's manifests; return the evidence."""
    main(["te-review", "collect", *WINDOW, "--out", str(into), "--te-root", str(te), *flags])
    return json.loads((into / "evidence.json").read_text())


def test_a_synthetic_session_gets_no_real_work_receipt_and_stays_with_its_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600), session("s2", START + 7200)])
    transcript(projects / "p", "s1")
    transcript(projects / "p", "s2")
    proof = tmp_path / "synthetic" / "s2.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"made by a test harness\n")
    synthetic = tmp_path / "synthetic" / "manifest.json"
    listed = {"path": "s2.txt", "sha256": hashlib.sha256(proof.read_bytes()).hexdigest()}
    entry = {**listed, "timestamp": "2026-10-13T09:00:00-05:00", "kind": "synthetic", "sessions": ["s2"]}
    synthetic.write_text(json.dumps({"receipts": [entry]}))
    out = tmp_path / "receipts.json"
    draft(te, projects, out, "--synthetic-manifest", str(synthetic))
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["real_work"] == 1
    assert summary["without_receipt"] == [{"session_id": "s2", "gap": "synthetic"}]
    assert [r["sessions"] for r in json.loads(out.read_text())["receipts"]] == [["s1"]]
    evidence = collect(te, tmp_path / "c", "--receipts", str(out), "--synthetic-manifest", str(synthetic))
    assert [(s["session_id"], s["cohort"]) for s in evidence["sessions"]] == [("s1", "real_work"), ("s2", "synthetic")]


def test_a_session_without_a_transcript_gets_no_receipt_and_is_listed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600), session("s2", START + 7200)])
    transcript(projects / "p" / "nested" / "deeper", "s1")
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["real_work"] == 1
    assert summary["without_receipt"] == [{"session_id": "s2", "gap": "no_transcript"}]
    evidence = collect(te, tmp_path / "c", "--receipts", str(out))
    assert [(s["session_id"], s["cohort"]) for s in evidence["sessions"]] == [("s1", "real_work"), ("s2", "unknown")]


def test_a_session_with_two_transcripts_gets_no_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    transcript(projects / "p", "s1")
    transcript(projects / "q", "s1")
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["without_receipt"] == [{"session_id": "s1", "gap": "many_transcripts"}]
    assert json.loads(out.read_text()) == {"receipts": []}


def test_a_session_collect_cannot_name_once_gets_no_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600), session("s3", START - 60)])
    ledger(te, "b-2", [session("s1", START + 3600)])
    transcript(projects / "p", "s1")
    transcript(projects / "p", "s3")
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["without_receipt"] == [{"session_id": "s1", "gap": "ambiguous_session"}]
    assert json.loads(out.read_text()) == {"receipts": []}


def refusal(capsys: pytest.CaptureFixture[str], te: Path, projects: Path, out: Path, *flags: str) -> dict[str, str]:
    with pytest.raises(SystemExit) as stop:
        draft(te, projects, out, *flags)
    assert stop.value.code == 1
    printed = capsys.readouterr()
    assert printed.out == ""
    return json.loads(printed.err)


def test_an_existing_out_is_refused_and_left_as_it_was(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    transcript(projects / "p", "s1")
    out = tmp_path / "receipts.json"
    out.write_bytes(b"the owner's reviewed draft\n")
    assert refusal(capsys, te, projects, out)["code"] == "OUT_EXISTS"
    assert out.read_bytes() == b"the owner's reviewed draft\n"


def test_a_relative_out_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # where a relative --out would land
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    assert refusal(capsys, te, projects, Path("receipts.json"))["code"] == "RELATIVE_PATH"
    assert not Path("receipts.json").exists()


def delivery(session_id: str, at: float, reason: str, tool_use: str) -> list[dict[str, Any]]:
    """The two records Claude Code writes when a PostToolUseFailure hook's nudge reaches the agent: the
    notice and the additional context, on the tool call's id, a few milliseconds after the hook logged it."""
    base = {"type": "attachment", "sessionId": session_id, "timestamp": iso(at + 0.007)}
    hook = {"hookName": "PostToolUseFailure:Bash", "toolUseID": tool_use, "hookEvent": "PostToolUseFailure"}
    notice = f"TokenEconomizer nudged this turn ({reason.split(':', maxsplit=1)[0]}): the same failure kept recurring."
    return [
        {**base, "attachment": {"type": "hook_system_message", "content": notice, **hook}},
        {**base, "attachment": {"type": "hook_additional_context", "content": ["Stop retrying it."], **hook}},
    ]


def test_a_delivered_nudge_gets_a_host_delivery_receipt_and_an_undelivered_one_none(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    events = [
        redirect("nudge", "s1", START + 30),
        redirect("nudge", "s1", START + 90),
        redirect("nudge", "s1", START + 150, shadow=True),
        redirect("abort", "s1", START + 200),
    ]
    events[0]["reason"] = "judge-stuck@0.93:The same command"
    state(te, "a-1", "events.jsonl", events)
    path = transcript(projects / "p", "s1", *delivery("s1", START + 30, "judge-stuck@0.93:The same command", "t1"))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"real_work": 1, "host_delivery": 1, "fact_injection": 0}
    assert summary["undelivered_nudges"] == 1
    receipt = json.loads(out.read_text())["receipts"][1]
    assert receipt["kind"] == "host_delivery"
    assert receipt["path"] == str(path)
    assert receipt["redirects"] == [{"session_id": "s1", "at": START + 30}]
    assert datetime.fromisoformat(receipt["timestamp"]) == datetime.fromisoformat(iso(START + 30.007))
    evidence = collect(te, tmp_path / "c", "--receipts", str(out))
    assert [(r["at"] - START, r["state"]) for r in evidence["redirects"]] == [
        (30, "delivery_confirmed"),
        (90, "delivery_unknown"),
        (150, "shadow_suppressed"),
        (200, "observed_event"),
    ]


def injected(session_id: str, at: float, *lines: str) -> dict[str, Any]:
    """The record Claude Code writes when the SessionStart hook's context reaches the agent: TokenEconomizer
    renders each manual fact as one "- <injection or claim>" line under its heading."""
    block = "\n".join(["# repo operating manual (o/r)", *lines])
    hook = {"hookName": "SessionStart:startup", "toolUseID": "SessionStart", "hookEvent": "SessionStart"}
    attachment = {"type": "hook_additional_context", "content": [block], **hook}
    return {"type": "attachment", "sessionId": session_id, "timestamp": iso(at), "attachment": attachment}


def test_an_injected_manual_fact_gets_a_fact_injection_receipt_collect_links(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    told = {"spec": {"id": "x", "claim": "the claim", "injection": "Run the tests with mise run test."}}
    learned(
        te,
        "a-1",
        {
            "m1": {**fact("ACTIVE"), **told},
            "m2": fact("ACTIVE", "never shown"),
            "m3": fact("ACTIVE", "shown, but its id is also an envfact"),
            "m4": {"life": fact("ACTIVE")["life"]},
            "m5": {**fact("ACTIVE"), "spec": {"id": "x", "claim": 7}},
        },
        {"e1": fact("ACTIVE", "an envfact"), "m3": fact("ACTIVE", "shown, but its id is also an envfact")},
    )
    lines = ["- Run the tests with mise run test.", "- shown, but its id is also an envfact", "- an envfact"]
    path = transcript(projects / "p", "s1", injected("s1", START + 1, *lines))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"real_work": 1, "host_delivery": 0, "fact_injection": 1}
    receipt = json.loads(out.read_text())["receipts"][1]
    assert (receipt["kind"], receipt["path"], receipt["facts"], receipt["sessions"]) == (
        "fact_injection",
        str(path),
        ["m1"],
        ["s1"],
    )
    assert datetime.fromisoformat(receipt["timestamp"]) == datetime.fromisoformat(iso(START + 1))
    evidence = collect(te, tmp_path / "c", "--receipts", str(out))
    injection = evidence["receipts"][1]["ref"]
    assert {f["fact_id"]: f["receipts"] for f in evidence["facts"] if f["mechanism"] == "manual"} == {
        "m1": [injection],
        "m2": [],
        "m3": [],
        "m4": [],
        "m5": [],
    }


def test_a_nudge_collect_cannot_name_once_or_without_a_transcript_counts_as_undelivered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600), session("s2", START + 7200)])
    reason = "judge-stuck@0.93:The same command"
    events = [
        redirect("nudge", "s1", START + 30),
        redirect("nudge", "s1", START + 30),
        redirect("nudge", "s2", START + 40),
    ]
    for event in events:
        event["reason"] = reason
    state(te, "a-1", "events.jsonl", events)
    transcript(projects / "p", "s1", *delivery("s1", START + 30, reason, "t1"))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_nudges"]) == (0, 3)


def test_one_delivery_record_two_nudges_could_claim_confirms_neither(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    reason = "judge-stuck@0.93:The same command"
    events = [redirect("nudge", "s1", START + 30), redirect("nudge", "s1", START + 40)]
    for event in events:
        event["reason"] = reason
    state(te, "a-1", "events.jsonl", events)
    transcript(projects / "p", "s1", *delivery("s1", START + 40, reason, "t1"))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_nudges"]) == (0, 2)


def test_a_relative_transcripts_folder_gives_receipts_collect_finds_from_another_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    path = transcript(tmp_path / "projects" / "p", "s1")
    out = tmp_path / "elsewhere" / "receipts.json"
    out.parent.mkdir()
    # collect reads a relative receipt path from the manifest's folder, not the folder the draft ran in.
    monkeypatch.chdir(tmp_path)
    draft(te, Path("projects"), out)
    capsys.readouterr()
    (receipt,) = json.loads(out.read_text())["receipts"]
    assert receipt["path"] == str(path)
    (row,) = collect(te, tmp_path / "c", "--receipts", str(out))["sessions"]
    assert row["cohort"] == "real_work"
