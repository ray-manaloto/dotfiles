"""repotools te-review report --worksheet: the owner's judgments checked against the evidence and counted."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main

from .test_te_review import START, charge, ledger, session
from .test_te_review_judgment import DAY, fact, history, learned, read, redirect, run, state


def optimizer(session_id: str, at: float, tokens: float = 40.0, job: str | None = None) -> dict[str, Any]:
    """A paid proposer charge as TokenEconomizer 0.1.0's fold writes it."""
    return {
        "at": at,
        "host": "claude",
        "job": job or f"opt-{session_id}",
        "kind": "overhead",
        "session_id": session_id,
        "overhead": {"optimizer_tokens": tokens},
    }


def manifest(folder: Path, *entries: tuple[str, dict[str, Any], bytes]) -> Path:
    """A receipt manifest naming one file per (kind, links, content), each with its true sha256."""
    folder.mkdir(parents=True, exist_ok=True)
    listed = []
    for number, (kind, named, content) in enumerate(entries, 1):
        (folder / f"{kind}-{number}.json").write_bytes(content)
        listed.append(
            {
                "path": f"{kind}-{number}.json",
                "sha256": hashlib.sha256(content).hexdigest(),
                "timestamp": "2026-10-06T09:00:00-05:00",
                "kind": kind,
                **named,
            }
        )
    path = folder / "manifest.json"
    path.write_text(json.dumps({"receipts": listed}))
    return path


PROOF = b"proof\n"


def collected(tmp_path: Path, *entries: tuple[str, dict[str, Any], bytes], imported: bool = False) -> Path:
    """Store a-1: a session with a paid proposer charge, a later one and a judge charge, a nudge and an abort,
    a paid fact m1 and an env fact; store b-2: a session with its own proposer charge, and its import if asked.
    """
    te = tmp_path / "te"
    late = optimizer("s1", START + 2 * DAY, job="opt-late")
    ledger(
        te,
        "a-1",
        [session("s1", START + 3600), optimizer("s1", START + 100), late, charge("s1", "judge-1", START + 200)],
    )
    ledger(te, "b-2", [session("s2", START + 3600), optimizer("s2", START + 100)])
    if imported:
        state(te, "b-2", "history.json", history("done", START + 7000, START + 7200, 1))
    state(te, "a-1", "events.jsonl", [redirect("nudge", "s1", START + 30), redirect("abort", "s1", START + 40)])
    learned(te, "a-1", {"m1": fact("ACTIVE")}, {"e1": fact("ACTIVE")})
    out = tmp_path / "out"
    flags = ("--receipts", str(manifest(tmp_path / "r", *entries))) if entries else ()
    run(te, out, *flags)
    return out


DELIVERY = ("host_delivery", {"redirects": [{"session_id": "s1", "at": START + 30}]}, PROOF)
USE = ("fact_use", {"facts": ["m1"], "sessions": ["s1"]}, PROOF)
# Recorded 2026-10-06 09:00 Chicago: after opt-s1, before opt-late.
SNAPSHOT = ("fact_snapshot", {"facts": ["m1"]}, PROOF)
NOT_RUN = ("not_run", {}, PROOF)
FOLD = ("history_fold", {"imports": ["repos/b-2"]}, PROOF)


def refs(out: Path) -> dict[str, str]:
    """Evidence refs by a name: receipts by kind, sessions by id, charges by job, facts by id, redirects by kind."""
    evidence = read(out, "evidence.json")
    found = {receipt["kind"]: receipt["ref"] for receipt in evidence["receipts"]}
    found |= {row["job"] or row["session_id"]: row["ref"] for row in evidence["rows"]}
    found |= {candidate["fact_id"]: candidate["ref"] for candidate in evidence["facts"]}
    found |= {candidate["kind"]: candidate["ref"] for candidate in evidence["redirects"]}
    return found


def filled(out: Path, tmp_path: Path, **changes: Callable[[Any], object]) -> Path:
    """The collection's worksheet with each section's entries changed as given, written beside the collection."""
    sheet = read(out, "worksheet.json")
    for section, change in changes.items():
        sheet[section] = change(sheet[section])
    path = tmp_path / "filled.json"
    path.write_text(json.dumps(sheet))
    return path


def judged(**value: object) -> Callable[[Any], object]:
    """A change that sets value on every entry of a section."""
    return lambda entries: [{**entry, **value} for entry in entries]


def review(capsys: pytest.CaptureFixture[str], out: Path, sheet: Path | None, *mode: str) -> dict[str, Any]:
    flags = ("--worksheet", str(sheet)) if sheet else ()
    main(["te-review", "report", "--evidence", str(out), *flags, *mode])
    shown = json.loads(capsys.readouterr().out)
    return shown["report"]["review"] if "--private" in mode else shown["review"]


def test_a_delivered_redirect_and_a_useful_paid_fact_are_accepted_and_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = collected(tmp_path, DELIVERY, USE)
    ref = refs(out)
    sheet = filled(
        out,
        tmp_path,
        redirects=judged(state="delivery_confirmed", receipt_ref=ref["host_delivery"], verdict="right", like_128=False),
        paid_facts=judged(
            owner_assessment="useful", reason="saved_lookup", origin_ref=ref["opt-s1"], use_ref=ref["fact_use"]
        ),
        learned_facts=judged(verdict="ok"),
        mcp_ab=lambda _: {"outcome": "protected_unchanged", "receipt_ref": None},
        decision=lambda _: {"decision": "keep", "settings": None},
    )
    shown = review(capsys, out, sheet)
    assert shown["redirects"] == {
        "delivered": 1,
        "delivery_unknown": 0,
        "shadow_suppressed": 0,
        "right": 1,
        "wrong": 0,
        "unjudged": 0,
        "not_reviewed": 0,
        "like_128": 0,
        "not_like_128": 1,
        "like_128_not_reviewed": 0,
    }
    # D4: the abort is its own line; with no receipt it is not delivered, so it takes no verdict.
    assert shown["aborts"] == {
        "aborts": 1,
        "delivery_confirmed": 0,
        "delivery_unknown": 1,
        "shadow_suppressed": 0,
        "right": 0,
        "wrong": 0,
        "unjudged": 0,
        "not_reviewed": 0,
    }
    assert shown["paid_facts"] == {
        "useful": 1,
        "not_useful": 0,
        "unknown": 0,
        "not_reviewed": 0,
        "origin": "owner-asserted",
    }
    assert shown["learned_facts"] == {"wrong": 0, "ok": 2, "unknown": 0, "not_reviewed": 0}
    assert shown["imports"] == {"proven": 0, "candidate": 0, "unknown": 0, "not_reviewed": 0}
    assert shown["not_run"] == {"run": 0, "re_deferred": 0, "not_reviewed": 0}
    assert shown["mcp_ab"] == "protected_unchanged"
    assert (shown["evidence_complete"], shown["missing"]) == (True, [])
    assert (shown["decision_recorded"], shown["decision"]) == (True, "keep")
    assert (shown["envfacts"], shown["conflict"], shown["follow_up"]) == (None, False, None)


def test_without_the_flag_the_collections_own_worksheet_shows_every_judgment_not_reviewed_and_the_decision_pending(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    abort = ("host_delivery", {"redirects": [{"session_id": "s1", "at": START + 40}]}, PROOF)
    out = collected(tmp_path, DELIVERY, abort)
    shown = review(capsys, out, None)
    assert (shown["redirects"]["delivered"], shown["redirects"]["not_reviewed"]) == (1, 1)
    assert shown["redirects"]["like_128_not_reviewed"] == 1
    assert (shown["aborts"]["delivery_confirmed"], shown["aborts"]["not_reviewed"]) == (1, 1)
    assert shown["paid_facts"]["not_reviewed"] == 1
    assert shown["learned_facts"]["not_reviewed"] == 2
    assert shown["mcp_ab"] == "NOT_REVIEWED"
    assert shown["evidence_complete"] is False
    assert shown["missing"] == ["redirects", "aborts", "paid_facts", "learned_facts", "mcp_ab"]
    assert (shown["decision_recorded"], shown["decision"]) == (False, "PENDING")
    assert shown["envfacts"] == "no paid fact proved useful: select microskills=envfacts"
    assert (shown["conflict"], shown["follow_up"]) == (False, "2026-11-17")


def refused(capsys: pytest.CaptureFixture[str], out: Path, sheet: Path | str, *mode: str) -> dict[str, str]:
    with pytest.raises(SystemExit) as stop:
        main(["te-review", "report", "--evidence", str(out), "--worksheet", str(sheet), *mode])
    assert stop.value.code == 1
    seen = capsys.readouterr()
    assert seen.out == ""
    return json.loads(seen.err)


USEFUL = {"owner_assessment": "useful", "reason": "saved_lookup"}

REFUSALS = {
    "an invalid enum value": (
        (DELIVERY,),
        lambda _: {"redirects": judged(verdict="maybe")},
        "BAD_WORKSHEET",
        "redirects.0.verdict",
    ),
    "a re-deferral without an owner": (
        (NOT_RUN,),
        lambda _: {"not_run": judged(outcome="re_deferred", reason="blocked", owner=" ", follow_up="2026-11-17")},
        "BAD_WORKSHEET",
        "re_deferred without its reason, owner and follow_up",
    ),
    "a run without its evidence": (
        (NOT_RUN,),
        lambda _: {"not_run": judged(outcome="run")},
        "BAD_WORKSHEET",
        "is run without its evidence_ref",
    ),
    "a change without its settings": (
        (),
        lambda _: {"decision": lambda _: {"decision": "change", "settings": []}},
        "BAD_WORKSHEET",
        "decision: change without its settings",
    ),
    "an entry the evidence has no candidate for": (
        (),
        lambda _: {"redirects": lambda entries: [{**entries[0], "ref": "r-elsewhere"}]},
        "UNKNOWN_REF",
        "r-elsewhere is not one of this section's candidates",
    ),
    "a receipt the evidence does not hold": (
        (DELIVERY,),
        lambda _: {"redirects": judged(receipt_ref="x-elsewhere")},
        "UNKNOWN_REF",
        "x-elsewhere is not in the evidence",
    ),
    "a judgment of other content": (
        (),
        lambda _: {"redirects": judged(digest="0" * 64)},
        "STALE_WORKSHEET",
        "was judged on other content",
    ),
    "a worksheet of another collection": (
        (),
        lambda _: {"collection_id": lambda _: "0" * 64},
        "STALE_WORKSHEET",
        "the worksheet judges another collection",
    ),
    "an entry judged twice": (
        (),
        lambda _: {"redirects": lambda entries: entries + entries},
        "BAD_WORKSHEET",
        "is judged twice",
    ),
    "a delivered redirect called shadow": (
        (DELIVERY,),
        lambda _: {"redirects": judged(state="shadow_suppressed", receipt_ref=None)},
        "BAD_WORKSHEET",
        "is delivery_confirmed in the evidence",
    ),
    "an abort confirmed by the nudge's receipt": (
        (DELIVERY,),
        lambda ref: {"aborts": judged(state="delivery_confirmed", receipt_ref=ref["host_delivery"])},
        "BAD_WORKSHEET",
        "is not a host_delivery receipt of",
    ),
    "a delivery confirmed without a receipt": (
        (),
        lambda _: {"redirects": judged(state="delivery_confirmed")},
        "BAD_WORKSHEET",
        "is delivery_confirmed without its host_delivery receipt",
    ),
    "an undelivered abort judged": (
        (),
        lambda _: {"aborts": judged(verdict="right")},
        "BAD_WORKSHEET",
        "is judged but not delivered",
    ),
    "an undelivered redirect judged like #128": (
        (),
        lambda _: {"redirects": judged(like_128=True)},
        "BAD_WORKSHEET",
        "is judged but not delivered",
    ),
    "an ab_receipt naming another kind of receipt": (
        (DELIVERY,),
        lambda ref: {"mcp_ab": lambda _: {"outcome": "ab_receipt", "receipt_ref": ref["host_delivery"]}},
        "BAD_WORKSHEET",
        "mcp_ab: ab_receipt without an ab receipt",
    ),
    "an ab_receipt with no receipt": (
        (),
        lambda _: {"mcp_ab": lambda _: {"outcome": "ab_receipt", "receipt_ref": None}},
        "BAD_WORKSHEET",
        "mcp_ab: ab_receipt without an ab receipt",
    ),
    # D8: the origin is an optimizer charge of the fact's store, charged before the fact first appears.
    "a useful fact whose origin is another store's charge": (
        (USE,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["opt-s2"], use_ref=ref["fact_use"])},
        "BAD_WORKSHEET",
        "is useful without an optimizer charge of its store before it first appears",
    ),
    "a useful fact whose origin is charged after its first snapshot": (
        (USE, SNAPSHOT),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["opt-late"], use_ref=ref["fact_use"])},
        "BAD_WORKSHEET",
        "is useful without an optimizer charge of its store before it first appears",
    ),
    "a useful fact whose origin is a judge charge": (
        (USE,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["judge-1"], use_ref=ref["fact_use"])},
        "BAD_WORKSHEET",
        "is useful without an optimizer charge of its store before it first appears",
    ),
    "a useful fact whose origin is a session": (
        (USE,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["s1"], use_ref=ref["fact_use"])},
        "BAD_WORKSHEET",
        "is useful without an optimizer charge of its store before it first appears",
    ),
    "a useful fact with no origin": (
        (USE,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=None, use_ref=ref["fact_use"])},
        "BAD_WORKSHEET",
        "is useful without an optimizer charge of its store before it first appears",
    ),
    "a useful fact with no use receipt": (
        (),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["opt-s1"], use_ref=None)},
        "BAD_WORKSHEET",
        "is useful without its fact_injection or fact_use receipt",
    ),
    "a useful fact whose use receipt is a delivery": (
        (DELIVERY,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref=ref["opt-s1"], use_ref=ref["host_delivery"])},
        "BAD_WORKSHEET",
        "is useful without its fact_injection or fact_use receipt",
    ),
    "a fact assessed without its reason": (
        (),
        lambda _: {"paid_facts": judged(owner_assessment="unknown", reason=None)},
        "BAD_WORKSHEET",
        "needs both an assessment and its reason, or neither",
    ),
    "a fact with a reason but no assessment": (
        (),
        lambda _: {"paid_facts": judged(owner_assessment=None, reason="cannot_tell")},
        "BAD_WORKSHEET",
        "needs both an assessment and its reason, or neither",
    ),
    "a useful fact whose origin the evidence does not hold": (
        (USE,),
        lambda ref: {"paid_facts": judged(**USEFUL, origin_ref="w-elsewhere", use_ref=ref["fact_use"])},
        "UNKNOWN_REF",
        "w-elsewhere is not in the evidence",
    ),
}


@pytest.mark.parametrize("case", REFUSALS, ids=list(REFUSALS))
def test_a_worksheet_that_does_not_fit_the_evidence_is_refused_with_its_code_only_in_public(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    entries, changes, code, message = REFUSALS[case]
    out = collected(tmp_path, *entries)
    sheet = filled(out, tmp_path, **changes(refs(out)))
    assert refused(capsys, out, sheet) == {"code": code}
    shown = refused(capsys, out, sheet, "--private")
    assert shown["code"] == code
    assert message in shown["error"]


@pytest.mark.parametrize(
    ("change", "code", "message"),
    [
        (lambda _: judged(entry="fold"), "BAD_WORKSHEET", "is finished_in_window in the evidence"),
        (lambda _: judged(verdict="proven"), "BAD_WORKSHEET", "is proven without its history_fold receipt"),
        (
            lambda imported: judged(verdict="proven", receipt_ref=imported),
            "BAD_WORKSHEET",
            "is proven without its history_fold receipt",
        ),
    ],
    ids=["another entry kind", "proven without a receipt", "proven by another receipt"],
)
def test_an_import_judged_as_another_entry_or_proven_without_its_fold_receipt_is_refused(
    change: Callable[[str], Callable[[Any], object]],
    code: str,
    message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = collected(tmp_path, DELIVERY, imported=True)
    sheet = filled(out, tmp_path, imports=change(refs(out)["host_delivery"]))
    shown = refused(capsys, out, sheet, "--private")
    assert (shown["code"], message in shown["error"]) == (code, True)


def test_a_worksheet_that_cannot_be_read_or_is_not_a_worksheet_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = collected(tmp_path)
    assert refused(capsys, out, tmp_path / "absent.json") == {"code": "NO_WORKSHEET"}
    assert refused(capsys, out, "filled.json") == {"code": "RELATIVE_PATH"}
    (tmp_path / "notes.json").write_text("not json")
    assert refused(capsys, out, tmp_path / "notes.json") == {"code": "BAD_WORKSHEET"}
    (tmp_path / "other.json").write_text(json.dumps({"collection_id": "x"}))
    assert refused(capsys, out, tmp_path / "other.json") == {"code": "BAD_WORKSHEET"}


def test_imports_and_not_run_items_are_counted_by_their_judgments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    second = ("not_run", {}, b"another\n")
    out = collected(tmp_path, NOT_RUN, second, FOLD, imported=True)
    ref = refs(out)
    deferred = {"outcome": "re_deferred", "reason": "needs_owner", "owner": "the owner", "follow_up": "2026-11-17"}
    sheet = filled(
        out,
        tmp_path,
        imports=judged(verdict="proven", receipt_ref=ref["history_fold"]),
        not_run=lambda entries: [
            {**entries[0], "outcome": "run", "evidence_ref": ref["s1"]},
            {**entries[1], **deferred},
        ],
    )
    shown = review(capsys, out, sheet)
    assert shown["imports"] == {"proven": 1, "candidate": 0, "unknown": 0, "not_reviewed": 0}
    assert shown["not_run"] == {"run": 1, "re_deferred": 1, "not_reviewed": 0}
    assert "imports" not in shown["missing"]
    assert "not_run" not in shown["missing"]


def ab_file(without: object, with_denies: object, with_session: str = "s2") -> bytes:
    """An MCP A/B receipt in the D8 format: two fresh sessions' first requests, without and with the denies."""
    return json.dumps(
        {
            "candidate_tools": ["mcp__wiki__search"],
            "without_denies": {"session_id": "s1", "first_request_input_tokens": without},
            "with_denies": {"session_id": with_session, "first_request_input_tokens": with_denies},
        }
    ).encode()


@pytest.mark.parametrize(
    ("sessions", "content", "result"),
    [
        (["s1", "s2"], ab_file(1000, 900), "qualified"),
        (["s1", "s2"], ab_file(1000, 1000), "failed_ab_protected_unchanged"),
        (["s1", "s2"], ab_file(1000, 1100), "failed_ab_protected_unchanged"),
        (["s1"], ab_file(1000, 900), "failed_ab_protected_unchanged"),
        (["s1", "s2"], ab_file(1000, 900, with_session="s1"), "failed_ab_protected_unchanged"),
    ],
    ids=["lower", "equal", "higher", "a session not named", "one session on both sides"],
)
def test_an_ab_receipt_qualifies_only_for_fresh_sessions_and_a_lower_first_request(
    sessions: list[str], content: bytes, result: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = collected(tmp_path, ("ab", {"sessions": sessions}, content))
    receipt = refs(out)["ab"]
    sheet = filled(out, tmp_path, mcp_ab=lambda _: {"outcome": "ab_receipt", "receipt_ref": receipt})
    assert review(capsys, out, sheet)["mcp_ab"] == result
    assert review(capsys, out, sheet, "--private")["mcp_ab"] == result


@pytest.mark.parametrize(
    "content",
    [
        b"first request: lower\n",
        json.dumps({"candidate_tools": []}).encode(),
        ab_file(1000, 900)[:-1],
        ab_file(1000, -1),
        ab_file(float("inf"), 900),
        ab_file(1000, 899.5),
        ab_file(1000, with_denies=False),
        ab_file(1000, "0"),
        ab_file(1000.0, 900),
    ],
    ids=[
        "not JSON",
        "not the A/B",
        "cut short",
        "negative tokens",
        "an infinite baseline",
        "a part of a token",
        "a boolean",
        "a string",
        "a whole float",
    ],
)
def test_an_ab_receipt_file_that_is_not_an_ab_is_refused_with_its_code_only_in_public(
    content: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # D8a: only a well-formed A/B that fails the fresh or lower test is a failed A/B; this one is refused.
    out = collected(tmp_path, ("ab", {"sessions": ["s1", "s2"]}, content))
    receipt = refs(out)["ab"]
    sheet = filled(out, tmp_path, mcp_ab=lambda _: {"outcome": "ab_receipt", "receipt_ref": receipt})
    assert refused(capsys, out, sheet) == {"code": "BAD_RECEIPT"}
    shown = refused(capsys, out, sheet, "--private")
    assert shown["code"] == "BAD_RECEIPT"
    assert f"mcp_ab: receipt {receipt} is not an A/B" in shown["error"]


@pytest.mark.parametrize(
    ("decision", "settings", "flagged"),
    [
        ("keep", None, "conflict"),
        ("change", [{"key": "microskills", "value": "envfacts"}], "no conflict"),
        ("change", [{"key": "microskills", "value": "manual"}], "conflict"),
        ("insufficient", None, "no conflict"),
    ],
    ids=["keep", "change to envfacts", "change to something else", "insufficient"],
)
def test_with_no_useful_paid_fact_a_decision_other_than_envfacts_is_flagged_as_a_conflict(
    decision: str,
    settings: list[dict[str, str]] | None,
    flagged: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = collected(tmp_path)
    sheet = filled(out, tmp_path, decision=lambda _: {"decision": decision, "settings": settings})
    shown = review(capsys, out, sheet)
    assert shown["envfacts"] == "no paid fact proved useful: select microskills=envfacts"
    assert (shown["decision_recorded"], shown["decision"], shown["conflict"]) == (True, decision, flagged == "conflict")
    main(["te-review", "report", "--evidence", str(out), "--worksheet", str(sheet), "--private"])
    private = json.loads(capsys.readouterr().out)
    assert private["settings"] == settings
    main(["te-review", "report", "--evidence", str(out), "--worksheet", str(sheet)])
    assert "settings" not in capsys.readouterr().out


def test_a_decision_filled_while_evidence_is_missing_is_recorded_beside_the_missing_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = collected(tmp_path, DELIVERY)
    # A partial worksheet: the redirect entry is left out, so it stays NOT_REVIEWED.
    sheet = filled(
        out,
        tmp_path,
        redirects=lambda _: [],
        decision=lambda _: {"decision": "insufficient", "settings": None},
    )
    shown = review(capsys, out, sheet)
    assert (shown["redirects"]["delivered"], shown["redirects"]["not_reviewed"]) == (1, 1)
    assert shown["evidence_complete"] is False
    assert shown["missing"] == ["redirects", "paid_facts", "learned_facts", "mcp_ab"]
    assert (shown["decision_recorded"], shown["decision"], shown["follow_up"]) == (True, "insufficient", "2026-11-17")
