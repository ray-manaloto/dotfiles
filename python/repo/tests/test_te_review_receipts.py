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


# A judge-written nudge: free text TokenEconomizer never logs, so only the hook's own output names it.
NUDGE = "You have run the same command eight times with the same error; form a hypothesis before the next run."


def delivery(
    session_id: str,
    at: float,
    reason: str,
    *,
    noticed: str | None = None,
    shown: list[str] | None = None,
) -> list[dict[str, Any]]:
    """The records Claude Code writes when a PostToolUseFailure hook's nudge reaches the agent, a few
    milliseconds after the hook logged it, all on the id of tool call t1: the hook's output as it printed it (the
    notice plugin/controller.py post_tool returns beside the context), then the notice and the context the host
    took from it. noticed is the reason the notice names, else the event's; shown is the context as attached."""
    base = {"type": "attachment", "sessionId": session_id, "timestamp": iso(at + 0.007)}
    hook = {"hookName": "PostToolUseFailure:Bash", "toolUseID": "t1", "hookEvent": "PostToolUseFailure"}
    named = (noticed or reason).split(":", maxsplit=1)[0]
    notice = f"TokenEconomizer nudged this turn ({named}): the same failure kept recurring."
    output = {
        "hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": NUDGE},
        "systemMessage": notice,
    }
    printed = {"type": "hook_success", "content": "", "stdout": json.dumps(output), "exitCode": 0, **hook}
    return [
        {**base, "attachment": {**printed, "command": "command hook 4"}},
        {**base, "attachment": {"type": "hook_system_message", "content": notice, **hook}},
        {
            **base,
            "attachment": {"type": "hook_additional_context", "content": [NUDGE] if shown is None else shown, **hook},
        },
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
    path = transcript(projects / "p", "s1", *delivery("s1", START + 30, "judge-stuck@0.93:The same command"))
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
        (200, "delivery_unknown"),  # #435: an abort is delivered or not like a nudge; observed_event is gone
    ]


@pytest.mark.parametrize(
    ("noticed", "shown"),
    [
        (None, []),
        (None, ["Run the linter after each edit."]),
        ("judge-loop@0.88:Another failure", None),
        (None, [NUDGE[:-1]]),
        (None, [NUDGE, "Run the linter after each edit."]),
    ],
    ids=[
        "an empty context",
        "another hook's context on the tool call",
        "a notice naming another reason",
        "a context that differs from the hook's output",
        "a context with more than the hook's output",
    ],
)
def test_a_nudge_whose_output_the_host_did_not_attach_as_printed_stays_unknown(
    noticed: str | None, shown: list[str] | None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    reason = "judge-stuck@0.93:The same command"
    state(te, "a-1", "events.jsonl", [{**redirect("nudge", "s1", START + 30), "reason": reason}])
    transcript(projects / "p", "s1", *delivery("s1", START + 30, reason, noticed=noticed, shown=shown))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_nudges"]) == (0, 1)


def test_a_notice_and_context_without_the_hook_output_that_printed_them_stay_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    reason = "judge-stuck@0.93:The same command"
    state(te, "a-1", "events.jsonl", [{**redirect("nudge", "s1", START + 30), "reason": reason}])
    printed, *attached = delivery("s1", START + 30, reason)
    other = {**printed, "attachment": {**printed["attachment"], "stdout": "plain text, not a hook's JSON"}}
    transcript(projects / "p", "s1", other, *attached)
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_nudges"]) == (0, 1)


def test_a_hook_output_that_prints_the_notice_but_is_not_json_refuses_the_draft(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    reason = "judge-stuck@0.93:The same command"
    state(te, "a-1", "events.jsonl", [{**redirect("nudge", "s1", START + 30), "reason": reason}])
    printed, *attached = delivery("s1", START + 30, reason)
    notice = attached[0]["attachment"]["content"]
    other = {**printed, "attachment": {**printed["attachment"], "stdout": notice}}
    transcript(projects / "p", "s1", other, *attached)
    out = tmp_path / "receipts.json"
    assert refusal(capsys, te, projects, out)["code"] == "MALFORMED_FILE"
    assert not out.exists()


MANUAL = "# repo operating manual (r) — learned from earlier sessions in this repository"


def injected(session_id: str, at: float, *lines: str, heading: str = MANUAL) -> dict[str, Any]:
    """The record Claude Code writes when the SessionStart hook's context reaches the agent: TokenEconomizer
    renders each manual fact as one "- <injection or claim>" line under its heading."""
    block = "\n".join([heading, *lines])
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


@pytest.mark.parametrize(
    "heading",
    ["## Another hook's instructions", "", "Do this first.\n# repo operating manual (r)"],
    ids=["another hook's heading", "no heading", "the manual's heading not first"],
)
def test_a_fact_line_in_a_session_start_context_that_is_not_the_manual_gets_no_receipt(
    heading: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    learned(te, "a-1", {"m1": fact("ACTIVE", "the claim")}, {})
    transcript(projects / "p", "s1", injected("s1", START + 1, "- the claim", heading=heading))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    assert json.loads(capsys.readouterr().out)["counts"]["fact_injection"] == 0
    assert [receipt["kind"] for receipt in json.loads(out.read_text())["receipts"]] == ["real_work"]


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
    transcript(projects / "p", "s1", *delivery("s1", START + 30, reason))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_nudges"]) == (0, 3)


def test_a_nudge_of_a_session_collect_cannot_name_once_counts_as_undelivered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    ledger(te, "b-2", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("nudge", "s1", START + 30), redirect("abort", "s1", START + 40)])
    transcript(projects / "p", "s1")
    draft(te, projects, tmp_path / "receipts.json")
    summary = json.loads(capsys.readouterr().out)
    assert (summary["undelivered_nudges"], summary["undelivered_aborts"]) == (1, 1)


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
    transcript(projects / "p", "s1", *delivery("s1", START + 40, reason))
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


# The stop hint ClaudeCode gives an interactive session (plugin/hosts.py ClaudeCode.interrupt).
HINT = "Press Esc to interrupt it."


def stuck(reason: str, tool_calls: int) -> str:
    """The abort notice plugin/controller.py post_tool returns: its reason up to the colon, the turn's calls."""
    short = reason.split(":", maxsplit=1)[0]
    return f"TokenEconomizer: this turn still looks stuck after a redirect ({short}, {tool_calls} tool calls). {HINT}"


def relayed(text: str) -> str:
    """The context plugin/hosts.py Host.relay asks the model with, so it passes the abort notice on."""
    return (
        "TokenEconomizer, a plugin the user runs, has a notice for them, and their main view does not show plugin "
        "messages. Put this line, word for word, in your next message to the user, and again in your final reply:"
        f"\n\n{text}\n\nIt is for the user to act on; it does not change your task."
    )


def stopping(session_id: str, at: float, notice: str, *, tool: str = "t2") -> list[dict[str, Any]]:
    """The records Claude Code writes when an abort's notice reaches the agent on tool call `tool`: ClaudeCode
    relays notices, so the hook prints the notice and its relay as context (controller.py post_tool)."""
    base = {"type": "attachment", "sessionId": session_id, "timestamp": iso(at + 0.009)}
    hook = {"hookName": "PostToolUseFailure:Bash", "toolUseID": tool, "hookEvent": "PostToolUseFailure"}
    context = relayed(notice)
    output = {
        "systemMessage": notice,
        "hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": context},
    }
    printed = {"type": "hook_success", "content": "", "stdout": json.dumps(output), "exitCode": 0, **hook}
    return [
        {**base, "attachment": {**printed, "command": "command hook 4"}},
        {**base, "attachment": {"type": "hook_system_message", "content": notice, **hook}},
        {**base, "attachment": {"type": "hook_additional_context", "content": [context], **hook}},
    ]


def test_a_delivered_abort_gets_a_host_delivery_receipt_and_the_report_shows_it_confirmed_on_the_abort_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    events = [redirect("nudge", "s1", START + 30), redirect("abort", "s1", START + 200)]
    state(te, "a-1", "events.jsonl", events)
    path = transcript(projects / "p", "s1", *stopping("s1", START + 200, stuck("loop", 9)))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"real_work": 1, "host_delivery": 1, "fact_injection": 0}
    assert (summary["undelivered_nudges"], summary["undelivered_aborts"]) == (1, 0)
    receipt = json.loads(out.read_text())["receipts"][1]
    assert (receipt["kind"], receipt["path"]) == ("host_delivery", str(path))
    assert receipt["redirects"] == [{"session_id": "s1", "at": START + 200}]
    assert datetime.fromisoformat(receipt["timestamp"]) == datetime.fromisoformat(iso(START + 200.009))
    collection = tmp_path / "c"
    evidence = collect(te, collection, "--receipts", str(out))
    assert [(r["kind"], r["state"]) for r in evidence["redirects"]] == [
        ("nudge", "delivery_unknown"),
        ("abort", "delivery_confirmed"),
    ]
    main(["te-review", "report", "--evidence", str(collection)])
    shown = json.loads(capsys.readouterr().out)["review"]
    assert (shown["aborts"]["aborts"], shown["aborts"]["delivery_confirmed"]) == (1, 1)
    # D4: an abort is never a delivered redirect.
    assert (shown["redirects"]["delivered"], shown["redirects"]["delivery_unknown"]) == (0, 1)


@pytest.mark.parametrize(
    "records",
    [
        [],
        stopping("s1", START + 200, stuck("loop", 12)),
        stopping("s1", START + 200, stuck("judge-loop", 9)),
        stopping("s1", START + 270, stuck("loop", 9)),
        stopping("s1", START + 200, stuck("loop", 9))[:2],
    ],
    ids=[
        "no record of the notice",
        "a notice counting other tool calls",
        "a notice naming another reason",
        "a notice after the hook's timeout",
        "a notice without its relayed context",
    ],
)
def test_an_abort_the_transcript_does_not_show_delivered_gets_no_receipt_and_stays_unknown(
    records: list[dict[str, Any]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("abort", "s1", START + 200)])
    transcript(projects / "p", "s1", *records)
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["host_delivery"] == 0
    assert (summary["undelivered_nudges"], summary["undelivered_aborts"]) == (0, 1)
    (row,) = collect(te, tmp_path / "c", "--receipts", str(out))["redirects"]
    assert row["state"] == "delivery_unknown"


def test_a_shadow_abort_gets_no_receipt_and_is_not_undelivered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("abort", "s1", START + 200, shadow=True)])
    # Even beside a record that would match it: a shadow abort was never sent.
    transcript(projects / "p", "s1", *stopping("s1", START + 200, stuck("loop", 9)))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_aborts"]) == (0, 0)
    (row,) = collect(te, tmp_path / "c", "--receipts", str(out))["redirects"]
    assert row["state"] == "shadow_suppressed"


def test_one_notice_record_two_aborts_could_claim_confirms_neither(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("abort", "s1", START + 200), redirect("abort", "s1", START + 230)])
    transcript(projects / "p", "s1", *stopping("s1", START + 230, stuck("loop", 9)))
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    assert (summary["counts"]["host_delivery"], summary["undelivered_aborts"]) == (0, 2)
    assert [r["state"] for r in collect(te, tmp_path / "c", "--receipts", str(out))["redirects"]] == [
        "delivery_unknown",
        "delivery_unknown",
    ]


def test_a_nudge_and_an_abort_each_delivered_get_their_own_receipts_and_count_on_their_own_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te, projects = tmp_path / "te", tmp_path / "projects"
    ledger(te, "a-1", [session("s1", START + 3600), session("s2", START + 7200)])
    reason = "judge-stuck@0.93:The same command"
    events = [
        {**redirect("nudge", "s1", START + 30), "reason": reason},
        {**redirect("abort", "s1", START + 200), "reason": reason},
        redirect("abort", "s2", START + 300),
    ]
    state(te, "a-1", "events.jsonl", events)
    records = [*delivery("s1", START + 30, reason), *stopping("s1", START + 200, stuck(reason, 9))]
    transcript(projects / "p", "s1", *records)
    out = tmp_path / "receipts.json"
    draft(te, projects, out)
    summary = json.loads(capsys.readouterr().out)
    # s2 has no transcript, so its abort is undelivered, apart from the nudges.
    assert summary["counts"]["host_delivery"] == 2
    assert (summary["undelivered_nudges"], summary["undelivered_aborts"]) == (0, 1)
    collection = tmp_path / "c"
    evidence = collect(te, collection, "--receipts", str(out))
    assert [r["state"] for r in evidence["redirects"]] == [
        "delivery_confirmed",
        "delivery_confirmed",
        "delivery_unknown",
    ]
    main(["te-review", "report", "--evidence", str(collection)])
    shown = json.loads(capsys.readouterr().out)["review"]
    # The redirect line counts the one nudge only; the aborts are their own line.
    assert (shown["redirects"]["delivered"], shown["redirects"]["delivery_unknown"]) == (1, 0)
    assert (shown["aborts"]["aborts"], shown["aborts"]["delivery_confirmed"]) == (2, 1)
    assert shown["aborts"]["delivery_unknown"] == 1
