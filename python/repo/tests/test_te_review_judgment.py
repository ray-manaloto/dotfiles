"""repotools te-review collect's receipts, judgment candidates and worksheet, through its command line."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main
from tests.test_te_review import START, WINDOW, ledger, refused, session


def run(root: Path, out: Path, *flags: str) -> None:
    main(["te-review", "collect", *WINDOW, "--out", str(out), "--te-root", str(root), *flags])


def read(out: Path, name: str) -> dict[str, Any]:
    return json.loads((out / name).read_text())


def test_a_collection_without_receipts_carries_an_unjudged_worksheet(tmp_path: Path) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    out = tmp_path / "out"
    run(tmp_path / "te", out)
    worksheet = read(out, "worksheet.json")
    assert worksheet == {
        "collection_id": read(out, "collection.json")["collection_id"],
        "redirects": [],
        "paid_facts": [],
        "learned_facts": [],
        "imports": [],
        "not_run": [],
        "mcp_ab": {"outcome": None, "receipt_ref": None},
        "decision": {"decision": None, "settings": None},
    }
    evidence = read(out, "evidence.json")
    (row,) = evidence["rows"]
    assert evidence["sessions"] == [
        {
            "ref": row["ref"],
            "store": "repos/a-1",
            "session_id": "s1",
            "cohort": "unknown",
            "cohort_receipts": [],
            "cadence": "unknown",
            "cadence_reason": "no_receipt",
        }
    ]
    assert evidence["receipts"] == evidence["redirects"] == evidence["facts"] == []
    assert evidence["imports"] == evidence["import_folds"] == []
    assert evidence["cadence_receipt"] is None
    assert evidence["import_coverage"] == "observed_current_only"


def state(root: Path, store: str, name: str, content: object) -> Path:
    """A TokenEconomizer state file of a store: JSON, or JSONL for a list."""
    path = root / "repos" / store / "claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, list):
        path.write_text("".join(json.dumps(line) + "\n" for line in content))
    else:
        path.write_text(json.dumps(content))
    return path


def redirect(kind: str, session_id: str, at: float, *, shadow: bool = False) -> dict[str, Any]:
    """A nudge or abort line as TokenEconomizer 0.1.0's controller logs it."""
    line: dict[str, Any] = {"reason": "loop", "tool_calls": 9, "envelope": 12.5}
    if kind == "abort":
        line["delivered"] = "notice"
    return {**line, "kind": kind, "at": at, "session_id": session_id, "shadow": shadow}


def test_redirects_are_candidates_and_only_receipted_delivery_counts(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    events = state(
        te,
        "a-1",
        "events.jsonl",
        [
            {"kind": "turn", "at": START + 10, "session_id": "s1", "shadow": False},
            redirect("nudge", "s1", START + 20, shadow=True),
            redirect("nudge", "s1", START + 30),
            redirect("abort", "s1", START + 40),
            redirect("nudge", "s1", START - 50),
        ],
    )
    out = tmp_path / "out"
    run(te, out)
    evidence = read(out, "evidence.json")
    found = [(c["kind"], c["at"] - START, c["in_window"], c["state"], c["line"]["line"]) for c in evidence["redirects"]]
    assert found == [
        ("nudge", 20, True, "shadow_suppressed", 2),
        ("nudge", 30, True, "delivery_unknown", 3),
        ("abort", 40, True, "observed_event", 4),
        ("nudge", -50, False, "delivery_unknown", 5),
    ]
    assert evidence["redirects"][1]["event"] == redirect("nudge", "s1", START + 30)
    sheet = read(out, "worksheet.json")["redirects"]
    assert [(r["ref"], r["state"], r["verdict"], r["like_128"]) for r in sheet] == [
        (c["ref"], c["state"], None, None) for c in evidence["redirects"][:3]
    ]
    assert (out / "sources" / "repos" / "a-1" / "claude" / "events.jsonl").read_bytes() == events.read_bytes()
    assert "repos/a-1/claude/events.jsonl" in [s["path"] for s in read(out, "collection.json")["sources"]]


def receipts(folder: Path, name: str, *entries: tuple[str, dict[str, Any]], content: bytes = b"proof\n") -> Path:
    """A manifest in folder naming one receipt file per entry (kind, links), each with its true sha256."""
    folder.mkdir(parents=True, exist_ok=True)
    listed = []
    for number, (kind, named) in enumerate(entries, 1):
        (folder / f"{kind}-{number}.txt").write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        listed.append(
            {
                "path": f"{kind}-{number}.txt",
                "sha256": digest,
                "timestamp": "2026-10-13T09:00:00-05:00",
                "kind": kind,
                **named,
            }
        )
    manifest = folder / name
    manifest.write_text(json.dumps({"receipts": listed}))
    return manifest


def test_a_host_delivery_receipt_confirms_a_nudge_and_is_frozen_into_the_bundle(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "events.jsonl", [redirect("nudge", "s1", START + 30)])
    manifest = receipts(
        tmp_path / "r", "m.json", ("host_delivery", {"redirects": [{"session_id": "s1", "at": START + 30}]})
    )
    out = tmp_path / "out"
    run(te, out, "--receipts", str(manifest))
    evidence = read(out, "evidence.json")
    (candidate,) = evidence["redirects"]
    (receipt,) = evidence["receipts"]
    assert candidate["state"] == "delivery_confirmed"
    assert candidate["receipts"] == [receipt["ref"]]
    assert receipt["links"] == [candidate["ref"]]
    assert receipt["origin"] == str(tmp_path / "r" / "host_delivery-1.txt")
    assert (out / "sources" / receipt["path"]).read_bytes() == b"proof\n"
    assert (out / "sources" / "manifests" / "receipts.json").read_bytes() == manifest.read_bytes()
    paths = [s["path"] for s in read(out, "collection.json")["sources"]]
    assert {"manifests/receipts.json", receipt["path"]} <= set(paths)


def test_a_receipt_whose_file_does_not_match_its_sha256_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    manifest = receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["s1"]}))
    (tmp_path / "r" / "real_work-1.txt").write_bytes(b"edited\n")
    out = tmp_path / "work" / "out"
    out.parent.mkdir()
    error = refused(capsys, te, out, *WINDOW, "--receipts", str(manifest))
    assert error["code"] == "RECEIPT_MISMATCH"
    assert str(tmp_path / "r" / "real_work-1.txt") in error["error"]


def fact(life_state: str, claim: str = "tests run with mise run test") -> dict[str, Any]:
    """A fact as TokenEconomizer 0.1.0's distiller keeps it: its spec and its lifecycle."""
    return {"spec": {"id": "x", "claim": claim}, "life": {"state": life_state, "confirms": 2, "contradicts": 0}}


def learned(te: Path, store: str, manual: dict[str, Any], envfacts: dict[str, Any]) -> None:
    state(te, store, "mechanisms/manual_state/o-r.json", {"repo": "o/r", "now": 3, "opt_tokens": 90, "facts": manual})
    state(
        te, store, "mechanisms/envfacts_state/o-r.json", {"repo": "o/r", "now": 3, "opt_tokens": 0, "facts": envfacts}
    )


def test_learned_facts_are_snapshots_whose_origin_is_unknown_without_a_receipt(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    learned(te, "a-1", {"m1": fact("ACTIVE"), "m2": fact("RETIRED"), "m3": fact("CANDIDATE")}, {"e1": fact("ACTIVE")})
    state(te, "a-1", "injection.json", {"rendered_ids": ["m1", "e1"], "reason": "fold"})
    manifest = receipts(
        tmp_path / "r",
        "m.json",
        ("fact_snapshot", {"facts": ["m3"]}),
        ("fact_use", {"facts": ["m1"], "sessions": ["s1"]}),
    )
    out = tmp_path / "out"
    run(te, out, "--receipts", str(manifest))
    evidence = read(out, "evidence.json")
    snapshot, use = (r["ref"] for r in evidence["receipts"])
    found = [
        (
            f["fact_id"],
            f["mechanism"],
            f["paid"],
            f["life_state"],
            f["retained"],
            f["rendered"],
            f["provenance"],
            f["receipts"],
        )
        for f in evidence["facts"]
    ]
    assert found == [
        ("e1", "envfacts", False, "ACTIVE", True, True, "missing", []),
        ("m1", "manual", True, "ACTIVE", True, True, "missing", [use]),
        ("m2", "manual", True, "RETIRED", False, False, "missing", []),
        ("m3", "manual", True, "CANDIDATE", True, False, "receipted", [snapshot]),
    ]
    assert evidence["facts"][1]["fact"] == fact("ACTIVE")
    assert evidence["facts"][1]["source"] == "repos/a-1/claude/mechanisms/manual_state/o-r.json"
    sheet = read(out, "worksheet.json")
    refs = {f["fact_id"]: f["ref"] for f in evidence["facts"]}
    assert [f["ref"] for f in sheet["paid_facts"]] == [refs["m1"], refs["m3"]]
    assert sheet["paid_facts"][0] == {
        "ref": refs["m1"],
        "digest": evidence["facts"][1]["digest"],
        "owner_assessment": None,
        "reason": None,
        "origin_ref": None,
        "use_ref": None,
    }
    assert [f["ref"] for f in sheet["learned_facts"]] == list(refs.values())
    assert {f["verdict"] for f in sheet["learned_facts"]} == {None}


def test_a_candidate_digest_changes_with_its_content_only(tmp_path: Path) -> None:
    def digests(claim: str, at: float, name: str) -> list[str]:
        te = tmp_path / name
        ledger(te, "a-1", [session("s1", START + 3600)])
        learned(te, "a-1", {"m1": fact("ACTIVE", claim)}, {})
        state(te, "a-1", "events.jsonl", [redirect("nudge", "s1", at)])
        run(te, tmp_path / f"{name}-out")
        evidence = read(tmp_path / f"{name}-out", "evidence.json")
        return [evidence["redirects"][0]["digest"], evidence["facts"][0]["digest"]]

    first = digests("claim one", START + 1, "a")
    assert digests("claim one", START + 1, "b") == first
    changed_fact = digests("claim two", START + 1, "c")
    assert changed_fact[0] == first[0]
    assert changed_fact[1] != first[1]
    changed_event = digests("claim one", START + 2, "d")
    assert changed_event[0] != first[0]
    assert changed_event[1] == first[1]


def history(run_state: str, started: float | None, finished: float | None, imported: int) -> dict[str, Any]:
    """A history.json as TokenEconomizer 0.1.0's import writes it (plugin/history.py)."""
    found: dict[str, Any] = {
        "state": run_state,
        "reason": None,
        "plan": [],
        "next": imported,
        "imported": imported,
        "planned": imported,
        "skipped": {},
        "over_limit": 0,
        "started": started,
        "heartbeat": finished or started,
        "noticed": False,
    }
    if finished is not None:
        found["finished"] = finished
    return found


def paid(session_id: str, ended: float, folded_at: float, optimizer: int, **extra: object) -> dict[str, Any]:
    """A session row whose fold ran the proposer for optimizer tokens."""
    overhead = {"optimizer_tokens": optimizer, "spiral_judge_tokens": 0.0, "spiral_nudge_writer_tokens": 0.0}
    return session(session_id, ended, folded_at=folded_at, overhead=overhead, **extra)


def test_imports_are_current_state_candidates_and_a_near_paid_fold_is_only_time_near(tmp_path: Path) -> None:
    te = tmp_path / "te"
    done = START + 7200
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "a-1", "history.json", history("done", START - 9000, START - 8000, 4))
    ledger(
        te,
        "b-2",
        [
            paid("near", START + 100, done + 30, 50),
            paid("free", START + 100, done + 40, 0),
            paid("later", START + 100, done + 4000, 50),
            paid("old", START + 100, done + 50, 50, imported=True),
        ],
    )
    state(te, "b-2", "history.json", history("done", START + 7000, done, 0))
    ledger(te, "c-3", [session("s3", START + 3600)])
    state(te, "c-3", "history.json", history("partial", START + 100, None, 2))
    out = tmp_path / "out"
    run(te, out)
    evidence = read(out, "evidence.json")
    found = [(i["store"], i["completion"], i["in_window"], i["sessions"], i["receipts"]) for i in evidence["imports"]]
    assert found == [
        ("repos/a-1", "completed", False, 4, []),
        ("repos/b-2", "completed", True, 0, []),
        ("repos/c-3", "partial", False, 2, []),
    ]
    assert evidence["imports"][1]["history"]["finished"] == done
    (fold,) = evidence["import_folds"]
    rows = {row["session_id"]: row["ref"] for row in evidence["rows"]}
    assert fold["import_ref"] == evidence["imports"][1]["ref"]
    assert (fold["session_ref"], fold["session_id"], fold["provenance"], fold["receipts"]) == (
        rows["near"],
        "near",
        "time_near",
        [],
    )
    assert evidence["import_coverage"] == "observed_current_only"
    assert evidence["import_note"] == "observed current import state; historical operation coverage unknown"
    sheet = read(out, "worksheet.json")["imports"]
    assert sheet == [
        {
            "ref": evidence["imports"][1]["ref"],
            "digest": evidence["imports"][1]["digest"],
            "verdict": None,
            "receipt_ref": None,
        },
        {"ref": fold["ref"], "digest": fold["digest"], "verdict": None, "receipt_ref": None},
    ]


def test_the_state_of_a_store_without_a_ledger_is_still_collected(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    state(te, "c-3", "history.json", history("partial", START + 100, None, 0))
    state(te, "c-3", "events.jsonl", [redirect("nudge", "early", START + 20)])
    out = tmp_path / "out"
    run(te, out)
    evidence = read(out, "evidence.json")
    assert [(i["store"], i["completion"], i["sessions"]) for i in evidence["imports"]] == [("repos/c-3", "partial", 0)]
    assert [(r["store"], r["session_id"]) for r in evidence["redirects"]] == [("repos/c-3", "early")]
    assert (out / "sources" / "repos" / "c-3" / "claude" / "history.json").is_file()


def test_a_receipted_fold_is_kept_however_long_after_the_import_it_ran(tmp_path: Path) -> None:
    te = tmp_path / "te"
    done = START + 7200
    ledger(te, "b-2", [paid("late", START + 100, done + 601, 50)])
    state(te, "b-2", "history.json", history("done", START + 7000, done, 1))
    manifest = receipts(tmp_path / "r", "m.json", ("history_fold", {"imports": ["repos/b-2"], "sessions": ["late"]}))
    out = tmp_path / "out"
    run(te, out, "--receipts", str(manifest))
    evidence = read(out, "evidence.json")
    (fold,) = evidence["import_folds"]
    assert (fold["session_id"], fold["provenance"]) == ("late", "receipted")


def test_a_receipt_does_not_make_an_imported_or_free_fold_an_import_fold(tmp_path: Path) -> None:
    te = tmp_path / "te"
    done = START + 7200
    ledger(te, "b-2", [paid("free", START + 100, done + 30, 0), paid("old", START + 100, done + 40, 50, imported=True)])
    state(te, "b-2", "history.json", history("done", START + 7000, done, 1))
    entry = ("history_fold", {"imports": ["repos/b-2"], "sessions": ["free", "old"]})
    out = tmp_path / "out"
    run(te, out, "--receipts", str(receipts(tmp_path / "r", "m.json", entry)))
    assert read(out, "evidence.json")["import_folds"] == []


def test_a_history_fold_receipt_ties_a_fold_to_its_import(tmp_path: Path) -> None:
    te = tmp_path / "te"
    done = START + 7200
    ledger(te, "b-2", [paid("near", START + 100, done + 30, 50)])
    state(te, "b-2", "history.json", history("done", START + 7000, done, 1))
    manifest = receipts(tmp_path / "r", "m.json", ("history_fold", {"imports": ["repos/b-2"], "sessions": ["near"]}))
    out = tmp_path / "out"
    run(te, out, "--receipts", str(manifest))
    evidence = read(out, "evidence.json")
    (receipt,) = evidence["receipts"]
    (fold,) = evidence["import_folds"]
    assert (fold["provenance"], fold["receipts"]) == ("receipted", [receipt["ref"]])
    assert evidence["imports"][0]["receipts"] == [receipt["ref"]]
    assert evidence["import_coverage"] == "history_receipts"


def cadence_receipt(folder: Path, sessions: list[str], /, **fields: object) -> Path:
    """A cadence change at START + 1 day, from 3 to 1, proven for these sessions by a fold process started after it."""
    found = {
        "sessions": sessions,
        "changed_at": "2026-10-06T00:00:00-05:00",
        "before": 3,
        "after": 1,
        "proof": "process_started_after_change",
        "process_started": "2026-10-06T00:05:00-05:00",
        "repo_override": False,
        "env_override": False,
        **fields,
    }
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cadence.json"
    path.write_text(json.dumps(found))
    return path


DAY = 86400.0


def cadences(out: Path) -> dict[str, tuple[str, str]]:
    return {s["session_id"]: (s["cadence"], s["cadence_reason"]) for s in read(out, "evidence.json")["sessions"]}


def test_a_session_has_a_cadence_only_when_its_end_and_fold_are_on_one_side_of_a_proven_change(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(
        te,
        "a-1",
        [
            session("before", START + 3600),
            session("after", START + DAY + 3600),
            session("straddles", START + DAY - 30),
            session("open", None),
        ],
    )
    ledger(
        te,
        "b-2",
        [
            paid("folded-by-import", START + DAY - 600, START + DAY + 120, 50),
            session("imported", START + 3600, imported=True),
        ],
    )
    state(te, "b-2", "history.json", history("done", START + DAY - 300, START + DAY + 100, 1))
    out = tmp_path / "out"
    run(
        te,
        out,
        "--cadence-receipt",
        str(cadence_receipt(tmp_path / "c", ["before", "after", "straddles", "open", "folded-by-import", "imported"])),
    )
    assert cadences(out) == {
        "before": ("cadence_3", "before_change"),
        "after": ("cadence_1", "after_change"),
        "straddles": ("unknown", "straddles_change"),
        "open": ("unknown", "missing_end"),
        "folded-by-import": ("unknown", "import_process_before_change"),
        "imported": ("unknown", "import_process_before_change"),
    }
    assert read(out, "evidence.json")["cadence_receipt"]["after"] == 1
    assert (out / "sources" / "manifests" / "cadence.json").is_file()


def test_a_fold_after_the_change_but_before_the_proven_process_started_stays_unknown(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("early", START + DAY + 60, folded_at=START + DAY + 120)])
    out = tmp_path / "out"
    run(te, out, "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["early"])))
    assert cadences(out) == {"early": ("unknown", "before_proven_process")}


def test_a_late_fold_a_receipt_ties_to_an_import_started_before_the_change_stays_unknown(tmp_path: Path) -> None:
    te = tmp_path / "te"
    done = START + DAY - 600
    ledger(te, "b-2", [paid("late", START + DAY + 3600, START + DAY + 4000, 50)])
    state(te, "b-2", "history.json", history("done", START + DAY - 900, done, 1))
    entry = ("history_fold", {"imports": ["repos/b-2"], "sessions": ["late"]})
    out = tmp_path / "out"
    flags = ("--receipts", str(receipts(tmp_path / "r", "m.json", entry)))
    run(te, out, *flags, "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["late"])))
    assert cadences(out) == {"late": ("unknown", "import_process_before_change")}


def test_a_cadence_proof_labels_only_the_sessions_it_covers(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("mine", START + DAY + 3600)])
    ledger(te, "b-2", [session("other", START + DAY + 3600)])
    out = tmp_path / "out"
    run(te, out, "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["mine"])))
    assert cadences(out) == {"mine": ("cadence_1", "after_change"), "other": ("unknown", "not_covered")}


def test_a_free_fold_a_receipt_ties_to_an_import_started_before_the_change_stays_unknown(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "b-2", [paid("late", START + DAY + 3600, START + DAY + 4000, 0)])
    state(te, "b-2", "history.json", history("done", START + DAY - 900, START + DAY - 600, 1))
    entry = ("history_fold", {"imports": ["repos/b-2"], "sessions": ["late"]})
    out = tmp_path / "out"
    flags = ("--receipts", str(receipts(tmp_path / "r", "m.json", entry)))
    run(te, out, *flags, "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["late"])))
    assert cadences(out) == {"late": ("unknown", "import_process_before_change")}


def test_a_captured_config_proves_a_cadence_and_an_unproven_before_stays_unknown(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("before", START + 3600), session("after", START + DAY + 3600)])
    proof = cadence_receipt(
        tmp_path / "c",
        ["before", "after"],
        before=None,
        after=3,
        proof="captured_config",
        process_started="2026-10-05T12:00:00-05:00",
        repo_override=True,
        captured_config={"microskills_propose_every": 3, "shadow": False},
    )
    out = tmp_path / "out"
    run(te, out, "--cadence-receipt", str(proof))
    assert cadences(out) == {"before": ("unknown", "before_change_unproven"), "after": ("cadence_3", "after_change")}


def test_an_import_that_never_started_leaves_a_later_session_proven(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("after", START + DAY + 3600)])
    state(te, "a-1", "history.json", history("skipped", None, None, 0))
    out = tmp_path / "out"
    run(te, out, "--cadence-receipt", str(cadence_receipt(tmp_path / "c", ["after"])))
    assert cadences(out) == {"after": ("cadence_1", "after_change")}
    assert read(out, "evidence.json")["imports"][0]["completion"] == "unknown"


@pytest.mark.parametrize(
    "fields",
    [
        {"process_started": None},
        {"process_started": "2026-10-05T23:00:00-05:00"},
        {"env_override": True},
        {"proof": "captured_config", "captured_config": {"microskills_propose_every": 3}},
        {"proof": "captured_config"},
        {"after": 2},
        {"sessions": ["nobody"]},
        {"sessions": []},
    ],
)
def test_a_cadence_receipt_that_does_not_prove_the_policy_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fields: dict[str, object]
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    proof = cadence_receipt(tmp_path / "c", ["s1"], **fields)
    assert (
        refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, "--cadence-receipt", str(proof))["code"]
        == "BAD_RECEIPT"
    )


def test_a_cadence_receipt_naming_a_session_two_stores_share_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger(tmp_path / "te", "a-1", [session("twin", START + 3600)])
    ledger(tmp_path / "te", "b-2", [session("twin", START + 3600)])
    proof = cadence_receipt(tmp_path / "c", ["twin"])
    found = refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, "--cadence-receipt", str(proof))
    assert found["code"] == "BAD_RECEIPT"


def test_a_cohort_comes_from_receipts_and_synthetic_only_from_the_synthetic_manifest(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("work", START + 3600), session("probe", START + 3600), session("other", START + 3600)])
    real = receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["work"]}), ("not_run", {}))
    synthetic = receipts(tmp_path / "s", "m.json", ("synthetic", {"sessions": ["probe"]}))
    out = tmp_path / "out"
    run(te, out, "--receipts", str(real), "--synthetic-manifest", str(synthetic))
    evidence = read(out, "evidence.json")
    work, not_run, probe = evidence["receipts"]
    assert [(r["kind"], r["manifest"]) for r in evidence["receipts"]] == [
        ("real_work", "receipts"),
        ("not_run", "receipts"),
        ("synthetic", "synthetic"),
    ]
    cohorts = {s["session_id"]: (s["cohort"], s["cohort_receipts"]) for s in evidence["sessions"]}
    assert cohorts == {
        "work": ("real_work", [work["ref"]]),
        "probe": ("synthetic", [probe["ref"]]),
        "other": ("unknown", []),
    }
    assert read(out, "worksheet.json")["not_run"] == [
        {
            "ref": not_run["ref"],
            "digest": not_run["sha256"],
            "outcome": None,
            "evidence_ref": None,
            "reason": None,
            "owner": None,
            "follow_up": None,
        }
    ]


SHADOW = {"redirects": [{"session_id": "s1", "at": START + 20}]}
ABORT = {"redirects": [{"session_id": "s1", "at": START + 40}]}


@pytest.mark.parametrize(
    ("flag", "entry", "problem"),
    [
        ("--receipts", ("synthetic", {"sessions": ["s1"]}), "names a synthetic receipt"),
        ("--synthetic-manifest", ("real_work", {"sessions": ["s1"]}), "names a real_work receipt"),
        ("--receipts", ("real_work", {"sessions": ["nobody"]}), "session nobody names nothing collected"),
        ("--receipts", ("fact_snapshot", {"facts": ["twice"]}), "fact twice matches 2 candidates"),
        ("--receipts", ("history_fold", {"imports": ["repos/none"]}), "import repos/none names nothing collected"),
        ("--receipts", ("host_delivery", {}), "a host_delivery receipt must name what it shows"),
        ("--receipts", ("fact_use", {"facts": ["twice"]}), "a fact_use receipt must name what it shows"),
        ("--receipts", ("host_delivery", SHADOW), "host_delivery of a shadow nudge"),
        ("--receipts", ("host_delivery", ABORT), "host_delivery of a abort"),
    ],
)
def test_a_receipt_that_does_not_name_exactly_what_it_shows_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flag: str, entry: tuple[str, dict[str, Any]], problem: str
) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    ledger(te, "b-2", [session("s2", START + 3600)])
    state(
        te,
        "a-1",
        "events.jsonl",
        [redirect("nudge", "s1", START + 20, shadow=True), redirect("abort", "s1", START + 40)],
    )
    learned(te, "a-1", {"twice": fact("ACTIVE")}, {})
    learned(te, "b-2", {"twice": fact("ACTIVE")}, {})
    manifest = receipts(tmp_path / "r", "m.json", entry)
    error = refused(capsys, te, tmp_path / "out", *WINDOW, flag, str(manifest))
    assert error["code"] == "BAD_RECEIPT"
    assert problem in error["error"]


def test_a_session_both_real_work_and_synthetic_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    real = receipts(tmp_path / "r", "m.json", ("real_work", {"sessions": ["s1"]}))
    synthetic = receipts(tmp_path / "s", "m.json", ("synthetic", {"sessions": ["s1"]}))
    flags = ("--receipts", str(real), "--synthetic-manifest", str(synthetic))
    error = refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, *flags)
    assert (error["code"], error["error"]) == ("BAD_RECEIPT", "session s1 has both real_work and synthetic receipts")


@pytest.mark.parametrize(
    ("content", "code"),
    [(b"{not json", "MALFORMED_FILE"), (b'{"receipts": [{"path": "x"}]}', "BAD_RECEIPT"), (b'{"receipts": []}', None)],
)
def test_a_manifest_must_be_a_receipt_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes, code: str | None
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    (tmp_path / "m.json").write_bytes(content)
    if code is None:
        run(tmp_path / "te", tmp_path / "out", "--receipts", str(tmp_path / "m.json"))
        assert read(tmp_path / "out", "evidence.json")["receipts"] == []
    else:
        assert (
            refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, "--receipts", str(tmp_path / "m.json"))["code"]
            == code
        )


def test_a_missing_receipt_file_or_cadence_receipt_is_unreadable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    manifest = receipts(tmp_path / "r", "m.json", ("not_run", {}))
    (tmp_path / "r" / "not_run-1.txt").unlink()
    assert (
        refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, "--receipts", str(manifest))["code"] == "UNREADABLE"
    )
    flags = ("--cadence-receipt", str(tmp_path / "none.json"))
    assert refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, *flags)["code"] == "UNREADABLE"
    (tmp_path / "bad.json").write_text("[")
    flags = ("--cadence-receipt", str(tmp_path / "bad.json"))
    assert refused(capsys, tmp_path / "te", tmp_path / "out", *WINDOW, *flags)["code"] == "MALFORMED_FILE"


@pytest.mark.parametrize(
    ("name", "content", "code"),
    [
        ("history.json", "{", "MALFORMED_FILE"),
        ("history.json", json.dumps({"state": "done", "new_key": 1}), "UNKNOWN_SCHEMA"),
        ("injection.json", json.dumps({"rendered_ids": "m1"}), "UNKNOWN_SCHEMA"),
        (
            "mechanisms/manual_state/o-r.json",
            json.dumps({"repo": "o/r", "facts": {"m1": {"life": {"state": "NEW"}}}}),
            "UNKNOWN_SCHEMA",
        ),
        ("events.jsonl", json.dumps({"kind": "turn", "at": 1}) + "\n", "UNKNOWN_SCHEMA"),
        ("events.jsonl", json.dumps({**redirect("nudge", "s1", START), "extra": 1}) + "\n", "UNKNOWN_SCHEMA"),
        ("events.jsonl", json.dumps(redirect("nudge", "s1", START)), "TRUNCATED_LINE"),
        ("events.jsonl", "{\n", "MALFORMED_LINE"),
    ],
)
def test_a_state_file_tokeneconomizer_did_not_write_fails_the_collection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, content: str, code: str
) -> None:
    ledger(tmp_path / "te", "a-1", [session("s1", START + 3600)])
    path = tmp_path / "te" / "repos" / "a-1" / "claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    error = refused(capsys, tmp_path / "te", tmp_path / "out")
    assert error["code"] == code
    assert f"repos/a-1/claude/{name}" in error["error"]


def test_only_json_files_of_a_mechanism_folder_are_read(tmp_path: Path) -> None:
    te = tmp_path / "te"
    ledger(te, "a-1", [session("s1", START + 3600)])
    learned(te, "a-1", {"m1": fact("ACTIVE")}, {})
    state(te, "a-1", "mechanisms/manual_state/.lock", {"held": True})
    run(te, tmp_path / "out")
    paths = [s["path"] for s in read(tmp_path / "out", "collection.json")["sources"]]
    assert paths == [
        "repos/a-1/claude/ledger.jsonl",
        "repos/a-1/claude/mechanisms/envfacts_state/o-r.json",
        "repos/a-1/claude/mechanisms/manual_state/o-r.json",
    ]
