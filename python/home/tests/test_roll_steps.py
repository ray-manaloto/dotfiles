"""The roll steps end to end through hometools roll: run ids, the run log, update, the gate and roll:all's order."""

import argparse
import json
import os
import re
import shlex
import signal
import sys
import time
import uuid
from pathlib import Path

import pytest

from hometools import roll
from hometools.cli import main
from hometools.models import Background, Graph, GraphSpace, GraphTab, GraphTerminal, Kind, RollStep
from hometools.roll import review, session

from .roll_world import (
    EMPTY,
    MARK_LINE,
    World,
    after,
    box,
    hometools,
    info,
    layout,
    lines,
    out,
    replier,
    rewriter,
    terminal,
)

SID = f"sid-{uuid.uuid4().hex}"
UPDATES = [("mise", "run", task) for task in roll.UPDATES]
EXIT = ("hc", "send", "t3", "/exit")
RESTART = ("hc", "send", "t3", "/restart")
# One run id for every step a test runs: the handshake carries it.
RUN = "run-t"
ASK = ("hc", "send", "--wait", "--timeout", "5", "t3", session.request(f"{RUN}-1"))
FAST = ("--wait", "5", "--settle", "3", "--poll", "0.05", "--busy-wait", "0.3", "--run", RUN)


def foreground(world: World) -> dict[str, object]:
    """hc get t3 once the resume is typed: the resumed process (its pid from resumed.pid) is the foreground."""
    script = world.bin / "foreground"
    shown = info("t3", 0, ["claude"], world.root / "proj")
    script.write_text(
        f"#!{sys.executable} -I\nimport json\nshown = {shown!r}\n"
        f"shown['foreground']['pid'] = int(open({str(world.root / 'resumed.pid')!r}).read())\n"
        "print(json.dumps(shown))\n"
    )
    script.chmod(0o755)
    return {"real": str(script)}


def resumed(world: World) -> dict[str, object]:
    """The typed resume command: it starts the resumed session, which takes its prompt (a user turn)."""
    script = world.bin / "resume"
    script.write_text(
        f"#!{sys.executable} -I\nimport datetime, json, subprocess\n"
        f"proc = subprocess.Popen([{str(world.bin / 'claude')!r}, '--resume', {SID!r}],"
        f" cwd={str(world.root / 'proj')!r},"
        " start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        f"open({str(world.root / 'resumed.pid')!r}, 'w').write(str(proc.pid))\n"
        # The resumed Claude writes its session record, as the real one does.
        f"import os; os.makedirs({str(world.home / '.claude/sessions')!r}, exist_ok=True)\n"
        f"record = {str(world.home / '.claude/sessions')!r} + f'/{{proc.pid}}.json'\n"
        f"open(record, 'w').write(json.dumps({{'sessionId': {SID!r}}}))\n"
        "turn = {'type': 'user', 'timestamp': datetime.datetime.now(datetime.UTC).isoformat()}\n"
        f"open({str(world.home / f'.claude/projects/-project/{SID}.jsonl')!r}, 'a').write(json.dumps(turn) + '\\n')\n"
    )
    script.chmod(0o755)
    return {"real": str(script)}


def scene(
    world: World, chief_state: str = "idle", worker_args: tuple[str, ...] = (), chief_args: tuple[str, ...] = ()
) -> tuple[int, int]:
    """chief-of-staff (t1, started with chief_args), proj / worker (t3, started with worker_args) and this task's own
    tab proj / roll (t9)."""
    proj = world.root / "proj"
    chief = world.spawn("claude", *chief_args, cwd=world.root / "fix-herdr")
    world.claude_record(chief, f"chief-{SID}")
    worker = world.spawn("claude", *worker_args, cwd=proj)
    world.claude_record(worker, SID)
    world.transcript(f"chief-{SID}")
    path = world.transcript(SID)
    typed = (
        "hc",
        "send",
        "t3",
        f"cd {shlex.quote(str(proj))} && {shlex.join(['claude', '--resume', SID, session.ROLLING])}",
    )
    world.answer(
        {
            ("hc", "ls", "--json"): out(
                {
                    "terminals": [
                        terminal("t1", "chief-of-staff / chief-of-staff"),
                        terminal("t3", "proj / worker"),
                        terminal("t9", "proj / roll", agent="zsh"),
                    ]
                }
            ),
            ("herdr-app", "ls"): out(
                layout(
                    ("chief-of-staff", str(world.root / "fix-herdr"), [("tb1", "chief-of-staff", ["t1"])]),
                    ("proj", str(proj), [("tb3", "worker", ["t3"]), ("tb9", "roll", ["t9"])]),
                )
            ),
            ("hc", "get", "t1", "--json"): out(
                info("t1", chief, ["claude"], world.root / "fix-herdr", state=chief_state)
            ),
            ("hc", "get", "t3", "--json"): after(
                out(info("t3", worker, ["claude"], proj)),
                (EXIT, out(info("t3", None, ["-zsh"], proj))),
                (typed, foreground(world)),
            ),
            ("hc", "get", "t9", "--json"): out(info("t9", None, ["zsh"], proj, where="proj / roll")),
            ("hc", "read", "t1"): {"stdout": EMPTY},
            ("hc", "read", "t3"): {"stdout": EMPTY},
            EXIT: {},
            ASK: replier(world, path, "READY-TO-RESTART"),
            typed: resumed(world),
            **{argv: {"stdout": f"{argv[2]} done\n"} for argv in UPDATES},
        }
    )
    return chief, worker


def end_resumed(world: World) -> None:
    pid = world.root / "resumed.pid"
    if pid.exists():
        os.killpg(int(pid.read_text()), signal.SIGKILL)


def test_the_dry_run_plans_every_step_and_writes_nothing(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    code, got, err = hometools(capfd, "all", "--wiki", str(world.wiki), *FAST)
    assert code == 0, err
    results = [(r["where"], r["result"]) for r in lines(got) if "result" in r and "where" in r]
    assert results == [
        ("chief-of-staff / chief-of-staff", "planned"),
        ("chief-of-staff / chief-of-staff", "planned"),
        ("proj / worker", "planned"),
        ("proj / worker", "planned"),
    ]
    assert [line for line in got.splitlines() if line.startswith("planned: mise")] == [
        f"planned: {' '.join(argv)}" for argv in UPDATES
    ]
    assert {"check": "mise-links", "result": "pass", "dangling": []} in lines(got)
    assert not world.state().exists()
    assert not [call for call in world.calls() if call[:2] in {("hc", "send"), ("mise", "run")}]


@pytest.mark.parametrize("label", [{"where": "proj / 3"}, {"where": "proj / roll", "parent": "t1"}])
def test_all_runs_only_in_its_own_roll_tab(world: World, capfd: pytest.CaptureFixture[str], label: dict) -> None:
    scene(world)
    world.answer({("hc", "get", "t9", "--json"): out(info("t9", None, ["zsh"], world.root, **label))})
    wiki = str(world.wiki)
    flags = ["--sessions", "free-models", "--exclude", "cpp-core", "--apply", "--wiki", wiki]
    code, got, err = hometools(capfd, "all", *flags)
    assert (code, got) == (2, "")
    error = json.loads(err)["error"]
    assert error.startswith("roll:all --apply runs only in its own herdr tab named roll")
    # The printed command keeps the caller's choice of sessions: pasted as is, it rolls the same ones.
    printed = json.loads(shlex.split(error.rpartition(" --argv ")[2])[0])
    assert printed[printed.index("roll:all") + 1 :] == flags
    assert world.runs() == []


@pytest.mark.usefixtures("world")
def test_all_needs_a_herdr_tab(capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HC_TERMINAL_ID")
    code, _, err = hometools(capfd, "all", "--apply")
    assert code == 2
    assert json.loads(err)["error"].startswith("roll:all --apply runs only in its own herdr tab named roll")


def test_a_breaking_update_pauses_before_any_session_stops(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    claude = world.home / ".local/bin/claude"
    claude.parent.mkdir(parents=True)
    claude.write_text(f"#!{sys.executable} -I\nimport sys\nprint(open(sys.argv[0] + '.v').read())\n")
    claude.chmod(0o755)
    Path(f"{claude}.v").write_text("2.1.9")
    bump = world.bin / "bump"
    bump.write_text(f"#!{sys.executable} -I\nopen({f'{claude}.v'!r}, 'w').write('2.1.10')\nprint('updated')\n")
    bump.chmod(0o755)
    world.answer(
        {
            ("mise", "run", "update:claude"): {"real": str(bump)},
            ("curl", "-fsSL", "--max-time", "30", review.CHANGELOG): {"stdout": "## 2.1.10\n- Removed a flag\n"},
            review.TRIAGE: {
                "stdout": "## BREAKING\n- claude 2.1.10: Removed a flag\n## ADOPT\n- none\n## REVISIT\n- none\n"
            },
        }
    )
    # A link left at the marker's path is replaced, not written through: the marker is written by a rename.
    elsewhere = world.root / "elsewhere"
    world.state().mkdir(parents=True, exist_ok=True)
    (world.state() / "paused").symlink_to(elsewhere)
    code, got, err = hometools(capfd, "all", "--apply", "--wiki", str(world.wiki), *FAST)
    run = world.runs()[0].run
    gate = world.state() / str(run) / "review.md"
    assert code == 3
    assert not elsewhere.exists()
    assert (world.state() / "paused").read_text() == f"{run}\n"
    assert json.loads(err.splitlines()[-1])["error"] == (
        f"roll:all paused before roll:stop: read {gate}, then rerun with --accept-review; to drop this run instead, "
        f"delete {world.state() / 'paused'} and rerun"
    )
    assert [line.step for line in world.runs()] == ["snapshot", "update", "review"]
    assert "updated" in got
    assert "$ mise run update:claude" in got
    assert ASK not in world.calls()
    # A rerun without --accept-review stays paused on the same gate: a new snapshot would take the updated versions
    # as its baseline, find nothing changed and open the gate.
    code, _, err = hometools(capfd, "all", "--apply", "--wiki", str(world.wiki), *FAST[:-2])
    assert code == 3
    assert json.loads(err.splitlines()[-1])["error"].startswith(f"roll:all paused before roll:stop: read {gate}")
    assert [line.step for line in world.runs()] == ["snapshot", "update", "review"]
    # --accept-review continues the paused run from roll:stop, with no second snapshot or update.
    try:
        args = ("all", "--apply", "--accept-review", "--exclude", "chief-of-staff", "--wiki", str(world.wiki))
        hometools(capfd, *args, *FAST[:-2])
    finally:
        end_resumed(world)
    assert [(line.run, line.step) for line in world.runs()[3:]] == [(run, "stop"), (run, "start"), (run, "verify")]
    assert [s.result for s in world.runs()[3].sessions] == ["stopped"]
    assert world.calls().count(("mise", "run", "update:claude")) == 1
    assert "Gate: CLOSED" in gate.read_text()


@pytest.mark.parametrize("marker", ["\n", "../other\n", "gone\n"], ids=["empty", "not-a-name", "no-run-folder"])
def test_a_paused_marker_without_its_run_is_refused(
    world: World, capfd: pytest.CaptureFixture[str], marker: str
) -> None:
    """A marker naming no run of its own (empty, a path, a folder that is gone) is not continued: with no run id the
    run folder would be the state folder itself, and roll:stop would build a live graph instead of the snapshot."""
    scene(world)
    paused = world.state() / "paused"
    paused.parent.mkdir(parents=True, exist_ok=True)
    paused.write_text(marker)
    code, _, err = hometools(capfd, "all", "--apply", "--accept-review", "--wiki", str(world.wiki), *FAST)
    assert code == roll.REFUSED
    assert json.loads(err.splitlines()[-1])["error"] == (
        f"roll:all: {paused} names no run with a snapshot ({marker.strip()!r}); delete it and rerun"
    )
    assert (world.runs(), paused.read_text()) == ([], marker)
    assert ASK not in world.calls()


def test_a_chief_of_staff_that_does_not_stop_holds_every_space(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world, chief_state="working")
    code, _, _ = hometools(capfd, "all", "--apply", "--accept-review", "--wiki", str(world.wiki), *FAST)
    assert code == 1
    steps = {line.step: line for line in world.runs()}
    # Still busy after --busy-wait: one stop result, with how long it waited.
    [busy] = steps[RollStep.stop].sessions
    assert busy.result == "skipped-busy"
    assert busy.notes[0] == "status working"
    assert re.fullmatch(r"waited \d+s while busy \(\d+ looks\)", busy.notes[-1])
    assert steps[RollStep.start].sessions == []
    assert ASK not in world.calls()
    assert EXIT not in world.calls()


def test_a_busy_chief_of_staff_that_goes_idle_within_the_wait_is_stopped(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    """Busy for its first looks, then idle: the stop waits, restarts it, and the run goes on to verify it."""
    # Both resumes: running() finds the chief of staff by name, and verify's restart check wants --resume <its id>.
    chief, _ = scene(world, chief_args=("--resume", "chief-of-staff", "--resume", f"chief-{SID}"))
    in_place = {"bridgeSessionId": None, "nameSource": "derived", "name": "chief-of-staff", "startedAt": 1000}
    world.claude_record(chief, f"chief-{SID}", **in_place)
    fix = world.root / "fix-herdr"
    path = world.home / f".claude/projects/-project/chief-{SID}.jsonl"
    busy, idle = (out(info("t1", chief, ["claude"], fix, state=state)) for state in ("working", "idle"))
    world.answer(
        {
            # The graph and the update read t1 too: the stop's first looks still find it busy.
            ("hc", "get", "t1", "--json"): [busy] * 8 + [idle],
            ("hc", "send", "--wait", "--timeout", "5", "t1", session.request(f"{RUN}-1")): replier(
                world, path, "READY-TO-RESTART"
            ),
            ("hc", "send", "t1", "/restart"): rewriter(world, chief, {"startedAt": int(time.time() * 1000) + 60_000}),
        }
    )
    roll.codeset(apply=True)
    time.sleep(1.1)
    args = ("all", "--apply", "--sessions", "chief-of-staff", "--wiki", str(world.wiki), *FAST, "--busy-wait", "30")
    code, got, err = hometools(capfd, *args)
    assert code == 0, got + err
    steps = {line.step: line for line in world.runs()}
    [down] = steps[RollStep.stop].sessions
    assert down.result == "restarted"
    assert re.fullmatch(r"waited \d+s while busy \(\d+ looks\)", down.notes[-1])
    assert [(s.where, s.result) for s in steps[RollStep.verify].sessions] == [("chief-of-staff / chief-of-staff", "ok")]


def test_a_busy_child_is_not_waited_on(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    """Only the chief of staff is waited on: a busy worker is listed to retry later at once, and fails nothing."""
    _, worker = scene(world)
    world.answer(
        {("hc", "get", "t3", "--json"): out(info("t3", worker, ["claude"], world.root / "proj", state="working"))}
    )
    args = ("all", "--apply", "--exclude", "chief-of-staff", "--wiki", str(world.wiki), *FAST, "--busy-wait", "60")
    began = time.monotonic()
    code, got, err = hometools(capfd, *args)
    assert time.monotonic() - began < 30
    assert code == 0, got + err
    steps = {line.step: line for line in world.runs()}
    [skipped] = steps[RollStep.stop].sessions
    assert (skipped.result, skipped.notes) == ("skipped-busy", ["status working"])
    assert ASK not in world.calls()


def test_a_session_rolls_back_in_place_while_the_rest_stay_untouched(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    chief, _ = scene(world)
    # The plugin code set's mark from before the restart: ps prints start times to the second.
    roll.codeset(apply=True)
    assert (world.state() / "codeset.json").exists()
    time.sleep(1.1)
    try:
        args = ("all", "--apply", "--exclude", "chief-of-staff", "--wiki", str(world.wiki), *FAST)
        code, got, err = hometools(capfd, *args)
    finally:
        end_resumed(world)
    assert code == 0, got + err
    steps = {line.step: line for line in world.runs()}
    assert [s.result for s in steps[RollStep.stop].sessions] == ["stopped"]
    assert [s.result for s in steps[RollStep.start].sessions] == ["started"]
    verified = [(s.where, s.result) for s in steps[RollStep.verify].sessions]
    assert verified == [("proj / worker", "ok"), ("chief-of-staff / chief-of-staff", "untouched")]
    assert steps[RollStep.verify].sessions[1].notes == [f"pid {chief} -> {chief}"]
    run = world.state() / str(steps[RollStep.stop].run)
    assert (run / f"background/proj--worker--{SID}.json").exists()
    # --sessions scopes verify as it scopes the other steps: a space it did not choose is not reported.
    code, got, _ = hometools(capfd, "verify", "--sessions", "proj", *FAST)
    assert [r.get("where") for r in lines(got)] == ["proj / worker", None]
    assert sorted(p.name for p in run.iterdir()) == sorted(
        [
            "background",
            "graph.json",
            "handshakes.log",
            "review-input.md",
            "review.md",
            "review.log",
            "snapshot.log",
            "start.log",
            "stop.log",
            "update.log",
            "verify.log",
            "versions.json",
        ]
    )
    assert (world.wiki / "sessions/graph.json").exists()


def test_a_session_with_remote_control_off_restarts_in_its_own_process(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    """/restart, not /exit: nothing for start to resume, and verify checks the restart (its record), not a resume."""
    _, worker = scene(world, worker_args=("--resume", SID))
    in_place = {"bridgeSessionId": None, "nameSource": "derived", "name": "worker", "startedAt": 1000}
    world.claude_record(worker, SID, **in_place)
    # The record /restart leaves: started again after the mark (a minute ahead of ps's whole seconds).
    world.answer({RESTART: rewriter(world, worker, {"startedAt": int(time.time() * 1000) + 60_000})})
    roll.codeset(apply=True)
    time.sleep(1.1)
    args = ("all", "--apply", "--exclude", "chief-of-staff", "--wiki", str(world.wiki), *FAST)
    code, got, err = hometools(capfd, *args)
    assert code == 0, got + err
    steps = {line.step: line for line in world.runs()}
    assert [s.result for s in steps[RollStep.stop].sessions] == ["restarted"]
    assert steps[RollStep.start].sessions == []
    assert next((s.where, s.result) for s in steps[RollStep.verify].sessions) == ("proj / worker", "ok")
    assert EXIT not in world.calls()
    # Run alone, start has nothing to resume and is not refused; verify checks the restart again.
    code, got, err = hometools(capfd, "start", "--apply", "--sessions", "proj", *FAST)
    assert (code, lines(got)) == (0, []), got + err
    code, got, _ = hometools(capfd, "verify", "--sessions", "proj", *FAST)
    assert next((r.get("where"), r.get("result")) for r in lines(got)) == ("proj / worker", "ok")


def test_a_stop_that_reads_no_box_anywhere_warns(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    """A Claude Code update that drew the prompt box differently skips every tab: say so loudly, in the log too.
    The tab's name goes out escaped, so a name holding terminal controls can't rewrite the screen or the log."""
    scene(world)
    hostile = "work\x1b[2Jer"
    world.answer(
        {
            ("hc", "read", "t3"): {"stdout": "a screen with no prompt box\n"},
            ("hc", "ls", "--json"): out({"terminals": [terminal("t3", f"proj / {hostile}")]}),
            ("herdr-app", "ls"): out(layout(("proj", str(world.root / "proj"), [("tb3", hostile, ["t3"])]))),
        }
    )
    code, got, err = hometools(capfd, "stop", "--apply", "--sessions", "proj", *FAST)
    assert (code, [r["result"] for r in lines(got)]) == (0, ["skipped-draft"])
    warning = next(line for line in err.splitlines() if line.startswith("roll:stop WARNING"))
    assert '(["proj / work\\u001b[2Jer"])' in warning
    assert "\x1b" not in err
    assert warning in Path(world.runs()[-1].log).read_text().splitlines()


@pytest.mark.parametrize(
    ("screen", "result"),
    [(EMPTY, "stopped"), (box(MARK_LINE + "a half-written note"), "skipped-draft")],
)
def test_a_stop_that_reads_a_box_does_not_warn(
    world: World, capfd: pytest.CaptureFixture[str], screen: str, result: str
) -> None:
    """A tab that was stopped, or skipped for a real draft, had a box the step could read: the layout is fine."""
    scene(world)
    world.answer({("hc", "read", "t3"): {"stdout": screen}})
    code, got, err = hometools(capfd, "stop", "--apply", "--sessions", "proj", *FAST)
    assert (code, [r["result"] for r in lines(got)]) == (0, [result])
    assert "WARNING" not in err
    assert "WARNING" not in Path(world.runs()[-1].log).read_text()


def test_steps_run_alone_continue_the_run_they_follow(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    code, got, _ = hometools(capfd, "stop", "--apply", "--sessions", "proj", *FAST)
    stopped = world.runs()[-1]
    assert (code, [s.result for s in stopped.sessions]) == (0, ["stopped"])
    try:
        code, got, _ = hometools(capfd, "start", "--apply", *FAST)
        # The live worker was resumed after the plugins last changed: a second stop leaves it running.
        again, planned, _ = hometools(capfd, "stop", *FAST)
        os.killpg(int((world.root / "resumed.pid").read_text()), 0)  # the resumed worker still runs
    finally:
        end_resumed(world)
    assert world.runs()[-1].run == stopped.run
    assert (code, [r["result"] for r in lines(got)]) == (0, ["started"])
    assert (again, [(r["where"], r["result"]) for r in lines(planned)]) == (
        0,
        [("chief-of-staff / chief-of-staff", "planned"), ("proj / worker", "skipped-already-current")],
    )
    # A session the stop did not stop is not started: the chief, whose space was not chosen.
    code, got, _ = hometools(capfd, "verify", *FAST)
    assert [r.get("where") for r in lines(got)] == ["proj / worker", None]
    # The resumed session has ended (end_resumed): verify fails it.
    assert code == 1


def test_a_dangling_mise_link_fails_verify_and_shows_in_the_update_plan(
    world: World, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    scene(world)
    installs = world.root / "mise/installs"
    (installs / "uv-abc").mkdir(parents=True)
    (installs / "uv").mkdir()
    (installs / "uv/0.13.8").symlink_to("../uv-abc")
    (installs / "uv/0.12").symlink_to("../uv-gone")
    (installs / "zig").mkdir()
    (installs / "zig/global").symlink_to("../zig-gone")
    (installs / "alias").symlink_to("uv")
    monkeypatch.setenv("MISE_DATA_DIR", str(world.root / "mise"))
    want = {"check": "mise-links", "result": "fail", "dangling": ["zig/global", "uv/0.12"]}
    code, got, _ = hometools(capfd, "update", *FAST)
    assert (code, lines(got)) == (0, [want])
    # Every session excluded: each is untouched, so the links alone fail the step.
    code, got, _ = hometools(capfd, "verify", "--exclude", "chief-of-staff,proj", *FAST)
    assert (code, lines(got)[-1]) == (1, want)
    assert [line["result"] for line in lines(got)[:-1]] == ["untouched", "untouched"]


@pytest.mark.parametrize(
    ("session_id", "exclude", "left"),
    [("ses_1", "oc", True), (None, "", True), ("ses_1", "", False)],
    ids=["excluded", "no-session-found", "rolled"],
)
def test_update_runs_each_task_and_leaves_opencode_alone_while_a_session_it_keeps_runs(
    world: World,
    capfd: pytest.CaptureFixture[str],
    session_id: str | None,
    exclude: str,
    left: bool,  # noqa: FBT001 - a parameter
) -> None:
    """agents:update would replace the OpenCode binary under a session the roll does not restart: one --exclude
    keeps, or one whose session id the snapshot did not find. update:claude, update:codex and update:agy still run."""
    oc = GraphTerminal(
        address="t5",
        kind=Kind.opencode,
        session=session_id,
        cwd="/",
        argv=None,
        status=None,
        lane_parents=[],
        is_coordinator=False,
    )
    graph = Graph(
        taken_at="now",
        coordinator=None,
        spaces=[GraphSpace(id="s", name="oc", folder="/", tabs=[GraphTab(id="t", name="1", terminals=[oc])])],
    )
    run = world.state() / "run-x"
    run.mkdir(parents=True)
    (run / "graph.json").write_text(graph.model_dump_json())
    (world.state() / "runs.jsonl").write_text(
        json.dumps(
            {"run": "run-x", "step": "snapshot", "args": [], "start": "", "end": "", "rc": 0, "log": "", "sessions": []}
        )
        + "\n"
    )
    world.answer(
        {
            UPDATES[0]: {"stdout": "claude updated\n"},
            UPDATES[1]: {"stdout": "codex broke\n", "code": 3},
            UPDATES[2]: {},
            UPDATES[3]: {"stdout": "agents updated\n"},
        }
    )
    skipped = "skipped: mise run agents:update, since OpenCode keeps running in oc / 1 (t5)"
    code, got, _ = hometools(capfd, "update", "--exclude", exclude)
    assert got.splitlines()[-1] == (skipped if left else "planned: mise run agents:update")
    code, got, _ = hometools(capfd, "update", "--apply", "--exclude", exclude)
    assert code == 1
    assert got.splitlines()[1:] == [
        "$ mise run update:claude",
        "claude updated",
        "$ mise run update:codex",
        "codex broke",
        "update:codex exited 3",
        "$ mise run update:agy",
        *([skipped] if left else ["$ mise run agents:update", "agents updated"]),
    ]
    assert (UPDATES[3] in world.calls()) is not left
    assert world.runs()[-1].run == "run-x"


def test_update_without_mise_names_it(
    world: World, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    scene(world)
    (world.stand_in / "mise").unlink()
    # The stand-ins need python3 (their env shebang); the venv holds no mise.
    monkeypatch.setenv("PATH", f"{world.stand_in}:{Path(sys.executable).parent}")
    code, got, _ = hometools(capfd, "update", "--apply")
    assert code == 1
    assert "mise: No such file or directory" in got
    assert "update:claude exited 127" in got


@pytest.mark.usefixtures("world")
def test_review_needs_a_snapshot(capfd: pytest.CaptureFixture[str]) -> None:
    code, got, err = hometools(capfd, "review", "--apply", "--run", "run-z")
    assert (code, got) == (1, "")
    assert json.loads(err)["error"].startswith("roll:review: ")


def test_targets_keep_the_given_space_order_children_before_leads() -> None:
    def term(address: str, kind: Kind = Kind.claude, session: str | None = "s") -> GraphTerminal:
        return GraphTerminal(
            address=address,
            kind=kind,
            session=session,
            cwd=None,
            argv=None,
            status=None,
            lane_parents=[],
            is_coordinator=False,
        )

    def tab(name: str, *terms: GraphTerminal, kept: bool = False) -> GraphTab:
        made = GraphTab(id=name, name=name, terminals=list(terms))
        return made.model_copy(update={"kept_from_previous_graph": True}) if kept else made

    graph = Graph(
        taken_at="",
        coordinator=None,
        spaces=[
            GraphSpace(
                id="a",
                name="a",
                folder=None,
                tabs=[
                    tab("a-lead", term("t1")),
                    tab("w", term("t2")),
                    tab("sh", term("t3", Kind.shell)),
                    tab("old", term("t4"), kept=True),
                    tab("me", term("t9")),
                    tab("lost", term("t5", session=None)),
                ],
            ),
            GraphSpace(id="b", name="b", folder=None, tabs=[tab("b-coord", term("t6")), tab("x", term("t7"))]),
            GraphSpace(id="c", name="c", folder=None, tabs=[tab("y", term("t8"))]),
        ],
    )
    args = argparse.Namespace(sessions="b,a", exclude="")
    picked, left = roll.targets(graph, args, "t9")
    assert [t.address for _, _, t in picked] == ["t7", "t6", "t2", "t1"]
    assert [t.address for _, _, t in left] == ["t8"]


def test_other_commands_take_no_arguments(capfd: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["disk-guard", "extra"])
    assert stop.value.code == 2
    assert "unrecognized arguments: extra" in capfd.readouterr().err


def test_a_failed_update_ends_the_roll_before_review(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    world.answer({UPDATES[1]: {"code": 3}})
    code, _, _ = hometools(capfd, "all", "--apply", "--wiki", str(world.wiki), *FAST)
    assert code == 1
    assert [line.step for line in world.runs()] == ["snapshot", "update"]


@pytest.mark.parametrize("flag", ["--sessions", "--exclude"])
def test_an_unknown_space_name_is_refused(world: World, capfd: pytest.CaptureFixture[str], flag: str) -> None:
    scene(world)
    code, got, err = hometools(capfd, "stop", "--apply", flag, "proj,nope", *FAST)
    assert (code, got) == (2, "")
    assert json.loads(err)["error"] == "roll: unknown space(s) nope; the graph has chief-of-staff, proj"
    assert world.runs()[-1].rc == 2


def test_start_with_nothing_stopped_is_refused(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    code, _, err = hometools(capfd, "start", "--apply", *FAST, "--run", "run-empty")
    assert code == 2
    assert json.loads(err)["error"].startswith("roll:start: run run-empty stopped no session")
    assert not [call for call in world.calls() if call[:2] == ("hc", "send")]


def test_a_failed_stop_fails_the_roll_and_is_logged(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    _, worker = scene(world)
    # The worker never leaves: /exit is sent, but its foreground stays claude.
    world.answer({("hc", "get", "t3", "--json"): out(info("t3", worker, ["claude"], world.root / "proj"))})
    args = ("all", "--apply", "--accept-review", "--sessions", "proj", "--wiki", str(world.wiki))
    code, _, _ = hometools(capfd, *args, "--wait", "5", "--settle", "0.3", "--poll", "0.05", "--run", RUN)
    assert code == 1
    steps = {line.step: line for line in world.runs()}
    assert [s.result for s in steps[RollStep.stop].sessions] == ["failed-exit-timeout"]
    assert (steps[RollStep.stop].rc, steps[RollStep.start].rc) == (1, 0)


def test_a_run_log_line_that_is_not_a_run_is_skipped(world: World) -> None:
    good = {"run": "run-x", "step": "stop", "args": [], "start": "", "end": "", "rc": 0, "log": "", "sessions": []}
    world.state().mkdir(parents=True)
    (world.state() / "runs.jsonl").write_text('{"run": "cut sh\n' + json.dumps(good) + "\n")
    assert [run.run for run in roll.history()] == ["run-x"]


def test_a_session_already_current_is_left_running(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    # The plugin code set last changed long before the sessions started, and no newer Claude is installed.
    roll.codeset(apply=True)
    seen = world.state() / "codeset.json"
    seen.write_text(json.dumps(dict.fromkeys(json.loads(seen.read_text()), "2000-01-01T00:00:00")))
    args = ("all", "--apply", "--accept-review", "--sessions", "proj", "--wiki", str(world.wiki), *FAST)
    code, _, _ = hometools(capfd, *args)
    assert code == 0
    steps = {line.step: line for line in world.runs()}
    assert [s.result for s in steps[RollStep.stop].sessions] == ["skipped-already-current"]
    assert steps[RollStep.start].sessions == []
    assert ASK not in world.calls()


def test_verify_without_a_stop_checks_every_session_with_no_worktree_record(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    scene(world)
    code, got, _ = hometools(capfd, "verify", *FAST)
    assert code == 1
    assert [r.get("where") for r in lines(got)] == ["chief-of-staff / chief-of-staff", "proj / worker", None]


def saved(world: World) -> None:
    """The graph roll:snapshot --apply left in the wiki before a reboot: proj / worker, and a project closed since
    (kept from the previous graph)."""
    proj = world.root / "proj"
    term = GraphTerminal(address="t3", kind=Kind.claude, session=SID, cwd=str(proj), argv=None, status=None,
                         lane_parents=[], is_coordinator=False)  # fmt: skip
    worker = GraphSpace(
        id="sp", name="proj", folder=str(proj), tabs=[GraphTab(id="tb3", name="worker", terminals=[term])]
    )
    closed = GraphSpace(id="sx", name="closed", folder=str(proj), tabs=[GraphTab(id="tx", name="w", terminals=[
        term.model_copy(update={"address": "t4", "session": "closed-sid"})])])  # fmt: skip
    closed = closed.model_copy(update={"kept_from_previous_graph": True})
    path = world.wiki / "sessions/graph.json"
    path.parent.mkdir(parents=True)
    path.write_text(Graph(taken_at="then", coordinator=None, spaces=[worker, closed]).model_dump_json())


def test_a_reboot_start_resumes_the_saved_graph_without_a_stop(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    saved(world)
    args = ("start", "--prompt", "reboot", "--wiki", str(world.wiki), *FAST)
    code, got, _ = hometools(capfd, *args)
    assert (code, [r["where"] for r in lines(got)]) == (0, ["proj / worker"])
    # Named by --sessions, a closed project is restored too.
    code, got, _ = hometools(capfd, *args, "--sessions", "proj,closed")
    assert [(r["where"], r["result"]) for r in lines(got)] == [("proj / worker", "planned"), ("closed / w", "planned")]
    assert all("Resumed after a Mac reboot" in str(r["notes"]) for r in lines(got))


def test_a_reboot_start_needs_a_saved_graph(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    code, _, err = hometools(capfd, "start", "--prompt", "reboot", "--apply", "--wiki", str(world.wiki), *FAST)
    assert code == 1
    assert json.loads(err)["error"].startswith("roll:start --prompt reboot: no saved graph in ")
    assert world.runs()[-1].rc == 1


def test_a_stop_cut_short_keeps_what_it_stopped(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    """Ctrl-C while the worker is asked: the chief of staff, stopped first, is in the run log."""
    chief, _ = scene(world)
    fix = world.root / "fix-herdr"
    leave = ("hc", "send", "t1", "/exit")
    # The chief is asked first (attempt 1), then the worker (attempt 2).
    chief_ask = ("hc", "send", "--wait", "--timeout", "5", "t1", session.request(f"{RUN}-1"))
    worker_ask = ("hc", "send", "--wait", "--timeout", "5", "t3", session.request(f"{RUN}-2"))
    interrupt = world.bin / "interrupt"
    interrupt.write_text(f"#!{sys.executable} -I\nimport os, signal\nos.kill({os.getpid()}, signal.SIGINT)\n")
    interrupt.chmod(0o755)
    path = world.home / f".claude/projects/-project/chief-{SID}.jsonl"
    world.answer(
        {
            chief_ask: replier(world, path, "READY-TO-RESTART"),
            leave: {},
            ("hc", "get", "t1", "--json"): after(
                out(info("t1", chief, ["claude"], fix)), (leave, out(info("t1", None, ["-zsh"], fix)))
            ),
            worker_ask: {"real": str(interrupt)},
        }
    )
    with pytest.raises(KeyboardInterrupt):
        hometools(capfd, "stop", "--apply", *FAST)
    [line] = world.runs()
    assert (line.step, line.rc, [r.result for r in line.sessions]) == ("stop", 1, ["stopped"])


def test_the_plugin_dirs_mods_are_part_of_the_code_set(world: World) -> None:
    mod = world.root / "mod"
    (mod / ".claude-plugin").mkdir(parents=True)
    manifest = mod / ".claude-plugin/plugin.json"
    manifest.write_text('{"version": "1"}')
    settings = world.home / ".claude/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"env": {"CLAUDE_CODE_PLUGIN_DIRS": f"{mod}::{world.root / 'none'}"}}))
    roll.codeset(apply=True)
    manifest.write_text('{"version": "2"}')
    roll.codeset(apply=True)
    assert len(json.loads((world.state() / "codeset.json").read_text())) == 2


def test_roll_help_is_the_roll_parsers(capfd: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["roll", "stop", "--help"])
    assert stop.value.code == 0
    assert capfd.readouterr().out.startswith("usage: hometools roll")


def test_all_refuses_an_unknown_space_before_anything(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    code, got, err = hometools(capfd, "all", "--sessions", "nope", *FAST)
    assert (code, got) == (2, "")
    assert json.loads(err)["error"].startswith("roll: unknown space(s) nope")


def test_a_standalone_stop_keeps_the_closed_projects_for_a_reboot(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    scene(world)
    saved(world)
    code, _, _ = hometools(capfd, "stop", "--apply", "--sessions", "proj", "--wiki", str(world.wiki), *FAST)
    assert code == 0
    kept = Graph.model_validate_json((world.state() / RUN / "graph.json").read_text())
    assert [s.name for s in kept.spaces if s.kept_from_previous_graph] == ["closed"]
    args = ("start", "--prompt", "reboot", "--sessions", "proj,closed", "--wiki", str(world.wiki), *FAST)
    code, got, _ = hometools(capfd, *args)
    assert (code, [r["where"] for r in lines(got)]) == (0, ["proj / worker", "closed / w"])


def test_a_reboot_verify_checks_every_session_it_restores(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    saved(world)
    args = ("verify", "--prompt", "reboot", "--sessions", "proj,closed", "--wiki", str(world.wiki), *FAST)
    code, got, _ = hometools(capfd, *args)
    assert code == 1
    assert [(r.get("where"), r["result"]) for r in lines(got)] == [
        ("proj / worker", "failed-not-running"),
        ("closed / w", "failed-not-running"),
        (None, "pass"),
    ]


def test_roll_is_found_however_it_is_spelled(capfd: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["--", "roll", "stop", "--help"])
    assert stop.value.code == 0
    assert capfd.readouterr().out.startswith("usage: hometools roll")


def test_a_reboot_start_and_verify_share_a_run_without_being_told(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    """Snapshot-only recovery with the default runs: start makes a run of its own, verify follows it and finds the
    new terminal (t5, herdr's new address for proj / worker after the reboot), not the graph's old t3."""
    saved(world)
    proj = world.root / "proj"
    proj.mkdir()
    world.transcript(SID)
    resume = shlex.join(["claude", "--resume", SID, session.REBOOT])
    typed = ("hc", "send", "t5", f"cd {shlex.quote(str(proj))} && {resume}")
    world.answer(
        {
            ("hc", "ls", "--json"): out({"terminals": [terminal("t5", "proj / worker", agent="zsh")]}),
            ("herdr-app", "ls"): out(layout(("proj", str(proj), [("tb8", "worker", ["t5"])]))),
            ("hc", "get", "t5", "--json"): after(out(info("t5", None, ["-zsh"], proj)), (typed, foreground(world))),
            typed: resumed(world),
        }
    )
    roll.codeset(apply=True)
    time.sleep(1.1)  # ps prints start times to the second: the resumed session starts after the mark
    timing = FAST[:-2]
    try:
        args = ("--prompt", "reboot", "--sessions", "proj", "--wiki", str(world.wiki), *timing)
        code, got, _ = hometools(capfd, "start", "--apply", *args)
        assert (code, [(r["result"], r["terminal"]) for r in lines(got)]) == (0, [("started", "t5")])
        code, got, _ = hometools(capfd, "verify", *args)
    finally:
        end_resumed(world)
    assert (code, [(r["result"], r["terminal"]) for r in lines(got)[:-1]]) == (0, [("ok", "t5")]), got
    assert len({line.run for line in world.runs()}) == 1


@pytest.mark.usefixtures("world")
def test_a_receipt_is_read_only_for_its_own_session() -> None:
    args = roll.parser().parse_args(["verify", "--run", RUN])
    step = roll.Step(args, [], RollStep.verify)
    term = GraphTerminal(address="t3", kind=Kind.claude, session=SID, cwd=None, argv=None, status=None,
                         lane_parents=[], is_coordinator=False)  # fmt: skip
    space, tab = GraphSpace(id="s", name="proj", folder=None, tabs=[]), GraphTab(id="t", name="worker", terminals=[])
    target = (space, tab, term)
    path = session.kept(step.folder, target)
    path.parent.mkdir(parents=True)
    receipt = Background(where="proj / worker", terminal="t3", session=SID, jobs=[], footer=None, exit_dialog=[],
                         worktree="## main")  # fmt: skip
    path.write_text(receipt.model_dump_json())
    assert roll.before(step, target) == "## main"
    path.write_text(receipt.model_copy(update={"terminal": "t4"}).model_dump_json())
    assert roll.before(step, target) is None


def test_a_run_whose_update_failed_before_its_review_keeps_its_baseline(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    """Run 1 installed updates and failed before roll:review; its rerun's snapshot took the updated versions and its
    review saw almost nothing. The next snapshot keeps the earlier baseline until a review finishes."""
    scene(world)
    claude = world.home / ".local/bin/claude"
    claude.parent.mkdir(parents=True)
    claude.write_text(f"#!{sys.executable} -I\nimport sys\nprint(open(sys.argv[0] + '.v').read())\n")
    claude.chmod(0o755)
    Path(f"{claude}.v").write_text("2.1.9")
    bump = world.bin / "bump"
    bump.write_text(f"#!{sys.executable} -I\nopen({f'{claude}.v'!r}, 'w').write('2.1.10')\nprint('updated')\n")
    bump.chmod(0o755)
    world.answer({("mise", "run", "update:claude"): {"real": str(bump)}, UPDATES[1]: {"code": 3}})
    code, _, _ = hometools(capfd, "all", "--apply", "--wiki", str(world.wiki), *FAST[:-1], "run-1")
    assert code == 1
    assert (world.state() / "baseline").read_text() == "run-1\n"
    world.answer({UPDATES[1]: {"stdout": "done\n"}, review.TRIAGE: {"code": 1}})
    code, got, _ = hometools(capfd, "all", "--apply", "--wiki", str(world.wiki), *FAST[:-1], "run-2")
    assert "versions.json: run-1's, kept since its review did not finish" in got
    assert (world.state() / "run-2/versions.json").read_text() == (world.state() / "run-1/versions.json").read_text()
    assert "- claude 2.1.9 -> 2.1.10" in (world.state() / "run-2/review.md").read_text()
    # The finished review clears the marker: the next snapshot records what is installed then.
    assert not (world.state() / "baseline").exists()


def test_a_review_of_another_run_leaves_the_baseline_marker(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    """Only a review against the marked run's versions.json clears it; any other review would drop that baseline."""
    for run, claude in (("run-1", "2.1.9"), ("run-x", "2.1.10")):
        versions = review.collect().model_copy(update={"harnesses": {"claude": claude}})
        (world.state() / run).mkdir(parents=True)
        (world.state() / run / "versions.json").write_text(versions.model_dump_json())
    (world.state() / "baseline").write_text("run-1\n")
    world.answer({review.TRIAGE: {"code": 1}})
    assert hometools(capfd, "review", "--apply", "--run", "run-x", "--wiki", str(world.wiki))[0] == 0
    assert (world.state() / "baseline").read_text() == "run-1\n"
    assert hometools(capfd, "review", "--run", "run-1", "--wiki", str(world.wiki))[0] == 0
    assert (world.state() / "baseline").exists()
    assert hometools(capfd, "review", "--apply", "--run", "run-1", "--wiki", str(world.wiki))[0] == 0
    assert not (world.state() / "baseline").exists()


def test_a_standalone_update_keeps_a_baseline_it_does_not_inherit(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    """Codex round 1: roll:update --apply --run B replaced the marker for run A though B had no versions.json, so the
    next snapshot recorded the updated versions and A's pending changes were lost. Only a run that inherits A's
    baseline takes the marker over."""
    scene(world)
    (world.state() / "run-a").mkdir(parents=True)
    (world.state() / "run-a/versions.json").write_text("{}")
    (world.state() / "baseline").write_text("run-a\n")
    assert hometools(capfd, "update", "--apply", *FAST[:-1], "run-b")[0] == 0
    assert (world.state() / "baseline").read_text() == "run-a\n"
    (world.state() / "run-c").mkdir(parents=True)
    (world.state() / "run-c/versions.json").write_text("{}")
    assert hometools(capfd, "update", "--apply", *FAST[:-1], "run-c")[0] == 0
    assert (world.state() / "baseline").read_text() == "run-c\n"


def test_a_session_counts_only_the_project_plugins_of_its_own_folder(world: World) -> None:
    """The owner's pick in round 1: a project-scope update for the session's folder makes it outdated; one for
    another folder leaves it current."""
    proj, other = world.root / "proj", world.root / "other"
    term = GraphTerminal(
        address="t3", kind=Kind.claude, session="s", cwd=str(proj), argv=None, status=None, lane_parents=[],
        is_coordinator=False,
    )  # fmt: skip
    target = (
        GraphSpace(id="s1", name="proj", folder=str(proj), tabs=[]),
        GraphTab(id="b1", name="w", terminals=[]),
        term,
    )

    def install(mine: str, theirs: str) -> None:
        entries = [
            {"scope": "user", "version": "1", "gitCommitSha": "u"},
            {"scope": "project", "projectPath": str(proj), "version": "1", "gitCommitSha": mine},
            {"scope": "local", "projectPath": str(other), "version": "1", "gitCommitSha": theirs},
        ]
        installed = {"p@m": entries}
        folder = world.home / ".claude/plugins"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": installed}))

    install("a", "x")
    roll.codeset(target, apply=True)
    install("a", "y")  # another project's plugin: still current
    roll.codeset(target, apply=True)
    assert len(json.loads((world.state() / "codeset.json").read_text())) == 1
    install("b", "y")  # its own project's plugin: outdated
    roll.codeset(target, apply=True)
    assert len(json.loads((world.state() / "codeset.json").read_text())) == 2


@pytest.mark.parametrize("step", ["start", "all"])
def test_a_stray_claude_in_a_mise_node_refuses_the_roll(
    world: World, capfd: pytest.CaptureFixture[str], step: str
) -> None:
    """start resumes sessions with plain `claude`, which an npm copy in a mise node would win on a shell's PATH."""
    scene(world)
    stray = world.home / ".local/share/mise/installs/node-x/lib/node_modules/@anthropic-ai/claude-code"
    stray.mkdir(parents=True)
    code, got, err = hometools(capfd, step, "--apply", *FAST, "--run", "run-stray")
    assert (code, got) == (2, "")
    assert json.loads(err)["error"] == f"roll: Claude Code outside its native install at {stray}; run claude:doctor"
    assert not [call for call in world.calls() if call[:2] == ("hc", "send")]
