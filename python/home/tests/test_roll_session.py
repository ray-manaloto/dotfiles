"""roll's per-session stop, start and verify against real processes and stood-in hc and herdr-app."""

import datetime as dt
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from hometools.models import Background, GraphSpace, GraphTab, GraphTerminal, Kind
from hometools.roll import live, session
from hometools.roll.session import HANDSHAKE, Target, Timing

from .roll_world import World, after, info, layout, out, replier, terminal

# Unique to this test process: the steps find a session's process by its id among every process on the Mac.
SID = f"sid-{uuid.uuid4().hex}"
# Codex's session is the uuid in its rollout's name; OpenCode's, the -s ses_... in its argv.
CODEX_SID = str(uuid.uuid4())
OPENCODE_SID = f"ses_{uuid.uuid4().hex}"
# The run folder; each handshake's token is its name and the attempt number.
RUN = "run-t"
TOKEN = f"{RUN}-1"
FAST = Timing(wait=5, settle=0.3, interval=0.01)
# The plugins changed after every process a test starts, so each session is out of date and roll:stop takes it.
MARK = dt.datetime.now() + dt.timedelta(hours=1)  # noqa: DTZ005 - compared with ps's local start time
EXIT = ("hc", "send", "t3", "/exit")
ASK = ("hc", "send", "--wait", "--timeout", "5", "t3", session.request(TOKEN))
AGAIN = ("hc", "send", "--wait", "--timeout", "5", "t3", session.request(f"{RUN}-2"))
GET = ("hc", "get", "t3", "--json")
READ = ("hc", "read", "t3")
ENTER, ESC = ("hc", "keys", "t3", "enter"), ("hc", "keys", "t3", "esc")


def target(world: World, kind: Kind = Kind.claude, **term: object) -> Target:
    folder = world.root / "proj"
    folder.mkdir(exist_ok=True)
    space_name, tab_name = str(term.pop("space", "proj")), str(term.pop("tab", "worker"))
    made = {
        "address": "t3",
        "kind": kind,
        "session": SID,
        "cwd": str(folder),
        "argv": None,
        "status": None,
        "lane_parents": [],
        "is_coordinator": False,
    } | term
    space = GraphSpace(id="sp-proj", name=space_name, folder=str(folder), tabs=[])
    tab = GraphTab(id="tb3", name=tab_name, terminals=[])
    return space, tab, GraphTerminal.model_validate(made)


def scene(world: World, pid: int, program: str = "claude", **answers: dict[str, object]) -> None:
    """Terminal t3 in proj / worker running pid (Claude session SID); after /exit its foreground is the shell."""
    folder = world.root / "proj"
    world.claude_record(pid, SID)
    world.answer(
        {
            ("hc", "ls", "--json"): out({"terminals": [terminal("t3", "proj / worker")]}),
            ("herdr-app", "ls"): out(layout(("proj", str(folder), [("tb3", "worker", ["t3"])]))),
            GET: after(out(info("t3", pid, [program], folder)), (EXIT, out(info("t3", None, ["-zsh"], folder)))),
            READ: {"stdout": ""},
            EXIT: {},
        }
        | {tuple(key.split()): value for key, value in answers.items()}
    )


def ready(world: World, text: str = "Resume block written.\n\nREADY-TO-RESTART") -> None:
    path = world.home / f".claude/projects/-project/{SID}.jsonl"
    if not path.exists():
        world.transcript(SID)
    world.answer({ASK: replier(world, path, text), AGAIN: replier(world, path, text)})


def children(pid: int, count: int) -> None:
    """Wait until pid has count child processes: a stand-in starts its children after it starts."""
    assert live.poll(
        lambda: True if sum(1 for p, _, _ in live.processes().values() if p == pid) >= count else None, 5, 0.02
    )


def newer(kind: Kind) -> None:
    """Codex's or OpenCode's binary, changed after the session started: the session is out of date."""
    path = session.binary(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    later = time.time() + 3600
    os.utime(path, (later, later))


def test_a_dry_run_plans_an_idle_session(world: World) -> None:
    scene(world, world.spawn("claude"))
    result = session.stop(live.Live(), target(world), FAST, None, MARK)
    assert (result.result, result.notes[:2]) == ("planned", ["handshake, then /exit", "status idle"])
    assert result.notes[2].startswith("started ")
    assert ASK not in world.calls()


def test_a_session_already_current_keeps_running(world: World) -> None:
    scene(world, world.spawn("claude"))
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, None)
    assert result.result == "skipped-already-current"
    assert ASK not in world.calls()


def test_a_foreground_that_is_not_the_harness_is_left_alone(world: World) -> None:
    scene(world, world.spawn("claude"), "vim")
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-foreground-not-claude", ["vim"])
    assert ASK not in world.calls()


def test_the_tab_running_the_step_is_never_stopped(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    scene(world, world.spawn("claude"))
    monkeypatch.setenv("HC_TERMINAL_ID", "t3")
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == "skipped-self"
    assert ASK not in world.calls()
    assert EXIT not in world.calls()


def test_a_working_session_is_busy(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    world.answer({GET: out(info("t3", pid, ["claude"], world.root, state="working"))})
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).notes == ["status working"]


def test_background_jobs_count_but_services_and_the_harness_own_helpers_do_not(world: World) -> None:
    mcp = f"child={sys.executable}|-c|import time; time.sleep(60)|mcp-server"
    pid = world.spawn("claude", "child=sleep|60", mcp, "child=zsh|-c|sleep 60; true", "child=true")
    world.answer({("hc", "get", "t4", "--json"): out(info("t4", None, ["x"], world.root, parent="t3"))})
    scene(world, pid)
    world.answer(
        {
            ("hc", "ls", "--json"): out({"terminals": [terminal("t3", "proj / worker"), terminal("t4", "proj / x")]}),
        }
    )
    children(pid, 4)
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert result.result == "skipped-busy"
    # The shell is no job, but what it runs is; neither is a child that exited and waits to be reaped (true).
    assert result.notes == ["status idle", "sleep 60", "sleep 60", "hc run child t4 dies with this session"]


def test_an_opencode_session_under_fnox_is_not_its_own_job(world: World) -> None:
    pid = world.spawn("fnox", f"child={world.bin / 'opencode'}|serve")
    scene(world, pid, "fnox")
    argv = ["fnox", "proxy", "run", "--", "opencode", "-s", OPENCODE_SID]
    world.answer({GET: out(info("t3", pid, argv, world.root))})
    newer(Kind.opencode)
    children(pid, 1)
    result = session.stop(live.Live(), target(world, Kind.opencode, session=OPENCODE_SID), FAST, None, MARK)
    assert result.result == "planned"


def test_a_ready_session_exits_and_its_background_is_kept(world: World) -> None:
    scene(world, world.spawn("claude"))
    ready(world)
    world.answer({READ: {"stdout": "esc to interrupt  3 in background"}})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    kept = world.root / RUN / f"background/proj--worker--{SID}.json"
    assert (result.result, result.notes) == ("stopped", [f"background: {kept}"])
    assert Background.model_validate_json(kept.read_text()) == Background(
        where="proj / worker",
        terminal="t3",
        session=SID,
        jobs=[],
        footer="3 background item(s) in footer (crons or agents)",
        exit_dialog=[],
        worktree=None,
    )
    assert world.calls().index(ASK) < world.calls().index(EXIT)


def test_a_session_moved_during_the_handshake_is_left_alone(world: World) -> None:
    scene(world, world.spawn("claude"))
    ready(world)
    folder = str(world.root / "proj")
    here, moved = out(layout(("proj", folder, [("tb3", "worker", ["t3"])]))), out(layout(("proj", folder, [])))
    # herdr-app ls: the snapshot read, the check before the handshake, then the one after it.
    world.answer({("herdr-app", "ls"): [here, here, moved]})
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == "skipped-gone"
    assert ASK in world.calls()
    assert EXIT not in world.calls()


def test_a_session_left_working_after_its_answer_is_busy(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    folder = world.root / "proj"
    working = out(info("t3", pid, ["claude"], folder, state="working"))
    world.answer({GET: after(out(info("t3", pid, ["claude"], folder)), (ASK, working))})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-busy-after-answer", ["status working"])
    assert EXIT not in world.calls()


@pytest.mark.parametrize("reads", [5, 6], ids=["after-the-answer", "right-before-exit"])
def test_a_foreground_that_changes_before_exit_is_left_alone(world: World, reads: int) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    folder = world.root / "proj"
    # hc get t3: the snapshot, the fresh foreground read, the version check and the status before the handshake;
    # then the status after it and the fresh read right before /exit.
    shell = out(info("t3", None, ["vim"], folder))
    world.answer({GET: [out(info("t3", pid, ["claude"], folder))] * (reads - 1) + [shell]})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert result.result == "skipped-foreground-changed"
    assert EXIT not in world.calls()


@pytest.mark.parametrize(
    ("tabs", "want"),
    [
        ([("tb1", "other", ["t1"]), ("tb7", "worker", ["t3"])], "skipped-moved"),
        ([("tb3", "renamed", ["t3"])], "skipped-moved"),
        ([], "skipped-gone"),
    ],
)
def test_a_terminal_not_where_the_graph_put_it_is_left_alone(world: World, tabs: list, want: str) -> None:
    scene(world, world.spawn("claude"))
    world.answer({("herdr-app", "ls"): out(layout(("proj", "/", tabs)))})
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == want
    assert ASK not in world.calls()


def test_a_claude_session_without_a_transcript_is_skipped(world: World) -> None:
    scene(world, world.spawn("claude"))
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == "skipped-no-transcript"


@pytest.mark.parametrize(
    ("text", "want"),
    [("BUSY-KEEP-ME the owner's question is open", "skipped-busy"), ("Still working.", "skipped-no-answer")],
)
def test_a_session_that_does_not_answer_ready_keeps_running(world: World, text: str, want: str) -> None:
    scene(world, world.spawn("claude"))
    ready(world, text)
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == want
    assert EXIT not in world.calls()


def test_a_session_waiting_on_a_dialog_is_skipped(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    world.answer(
        {
            GET: after(
                out(info("t3", pid, ["claude"], world.root)),
                (ASK, out(info("t3", pid, ["claude"], world.root, kind="permission"))),
            )
        }
    )
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-blocked", ["answer ready"])


def test_a_job_started_during_the_handshake_keeps_it_running(world: World) -> None:
    pid, busy = world.spawn("claude"), world.spawn("claude", "child=sleep|60")
    scene(world, pid)
    world.claude_record(busy, SID)
    ready(world)
    world.answer(
        {GET: after(out(info("t3", pid, ["claude"], world.root)), (ASK, out(info("t3", busy, ["claude"], world.root))))}
    )
    children(busy, 1)
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-job-started", ["sleep 60"])


DIALOG = """Background work is running. These will stop when you exit:
  {items}
\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT} 1. Exit and stop tasks
  2. Stay
"""


def test_scheduled_tasks_alone_at_exit_are_confirmed(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    folder = world.root / "proj"
    world.answer(
        {
            READ: after({"stdout": ""}, (EXIT, {"stdout": DIALOG.format(items="scheduled task: check-in")})),
            GET: after(out(info("t3", pid, ["claude"], folder)), (ENTER, out(info("t3", None, ["zsh"], folder)))),
            ENTER: {},
        }
    )
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert result.result == "stopped"
    record = json.loads((world.root / RUN / f"background/proj--worker--{SID}.json").read_text())
    assert record["exit_dialog"] == ["scheduled task: check-in"]


def test_other_work_at_exit_means_stay(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    world.answer({READ: after({"stdout": ""}, (EXIT, {"stdout": DIALOG.format(items="agent: a review")})), ESC: {}})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-background-work-at-exit", ["agent: a review"])
    assert ESC in world.calls()


def test_an_exit_that_never_lands_fails(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    ready(world)
    world.answer({GET: out(info("t3", pid, ["claude"], world.root))})
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == "failed-exit-timeout"
    world.answer({READ: after({"stdout": ""}, (EXIT, {"stdout": DIALOG.format(items="scheduled task: x")})), ENTER: {}})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("failed-exit-timeout", ["scheduled task: x"])


def harness(world: World, kind: Kind) -> Target:
    """A Codex session holding its rollout open, or OpenCode with its -s session, in t3."""
    if kind is Kind.codex:
        rollout = world.home / f".codex/sessions/rollout-2026-11-14T10-00-00-{CODEX_SID}.jsonl"
        rollout.parent.mkdir(parents=True, exist_ok=True)
        rollout.write_text("{}\n")
        pid = world.spawn("codex", f"open={rollout}")
        scene(world, pid, "codex")
        assert live.poll(lambda: session.codex_session([pid]), 5, 0.02) == CODEX_SID
        made = target(world, kind, session=CODEX_SID)
    else:
        pid = world.spawn("opencode")
        scene(world, pid, "opencode")
        world.answer({GET: after(out(info("t3", pid, ["opencode", "-s", OPENCODE_SID], world.root)),
                                 (EXIT, out(info("t3", None, ["-zsh"], world.root))))})  # fmt: skip
        made = target(world, kind, session=OPENCODE_SID)
    newer(kind)
    return made


@pytest.mark.parametrize("kind", [Kind.codex, Kind.opencode])
@pytest.mark.parametrize(
    ("screen", "want"),
    [
        (f"  READY-TO-RESTART {TOKEN}\n", "stopped"),
        (f"● BUSY-KEEP-ME {TOKEN} a job\n", "skipped-busy"),
        # A bare marker, the run's name alone, or another run's: left from an earlier handshake, no answer.
        (f"  READY-TO-RESTART\n  READY-TO-RESTART {RUN}\n  READY-TO-RESTART run-old-1\n", "skipped-no-answer"),
    ],
)
def test_codex_and_opencode_answer_on_their_screen(world: World, kind: Kind, screen: str, want: str) -> None:
    made = harness(world, kind)
    world.answer({ASK: {}, READ: after({"stdout": ""}, (ASK, {"stdout": "READY-TO-RESTART is the line\n" + screen}))})
    assert session.stop(live.Live(), made, FAST, world.root / RUN, MARK).result == want


def test_a_retry_in_the_same_run_does_not_take_the_first_attempts_answer(world: World) -> None:
    made = harness(world, Kind.codex)
    (world.root / RUN).mkdir()
    (world.root / RUN / "handshakes.log").write_text(f"{TOKEN} t3 {CODEX_SID}\n")
    world.answer({AGAIN: {}, READ: {"stdout": f"  READY-TO-RESTART {TOKEN}\n"}})
    assert session.stop(live.Live(), made, FAST, world.root / RUN, MARK).result == "skipped-no-answer"
    assert (world.root / RUN / "handshakes.log").read_text().splitlines()[1] == f"{RUN}-2 t3 {CODEX_SID}"


def test_a_handshake_that_is_not_sent_asks_nothing(world: World) -> None:
    scene(world, world.spawn("claude"))
    world.transcript(SID)
    world.answer({ASK: {"code": 1}})
    assert session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK).result == "skipped-handshake-not-sent"
    assert EXIT not in world.calls()


def test_another_session_in_the_tab_is_left_alone(world: World) -> None:
    pid = world.spawn("claude")
    scene(world, pid)
    world.claude_record(pid, "someone-else")
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-session-changed", ["now someone-else"])


def test_a_run_folder_that_cannot_take_the_record_stops_nothing(world: World) -> None:
    scene(world, world.spawn("claude"))
    ready(world)
    (world.root / RUN).mkdir()
    (world.root / RUN / "background").write_text("a file, not a folder")
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert result.result == "failed-background-not-written"
    assert ASK not in world.calls()


def test_a_tab_moved_into_another_space_is_left_alone(world: World) -> None:
    scene(world, world.spawn("claude"))
    ready(world)
    folder = str(world.root / "proj")
    world.answer({("herdr-app", "ls"): out(layout(("other", folder, [("tb3", "worker", ["t3"])])))})
    result = session.stop(live.Live(), target(world), FAST, world.root / RUN, MARK)
    assert (result.result, result.notes) == ("skipped-moved", ["herdr-app ls shows t3 in other / worker (tb3)"])
    assert ASK not in world.calls()


def test_names_are_one_file_inside_the_run_folder(world: World) -> None:
    made = target(world, space="../up", tab="a/b", session="s/1")
    assert session.kept(world.root / RUN, made) == world.root / RUN / "background/..%2Fup--a%2Fb--s%2F1.json"


def test_a_codex_resume_keeps_its_policies_but_not_the_old_terminals(world: World) -> None:
    hc = 'shell_environment_policy.set.HC_TERMINAL_ID="t1"'
    old = ["codex", "--no-daemon", "-c", hc, "-c", "model_reasoning_effort=high",
           "-a", "never", "-s", "read-only", "--model=gpt-x", "--yolo", "-p"]  # fmt: skip
    assert session.resume_argv(target(world, Kind.codex, argv=old), "hi") == [
        "codex-hc", "resume", SID, "-c", "model_reasoning_effort=high", "-a", "never", "-s", "read-only",
        "--model=gpt-x", "--yolo",
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("args", "service"),
    [
        ("node exa-mcp", True),
        ("bun x some-server", True),
        ("python example.py", False),
        ("bun xyz.ts", False),
        ("sleep 60", False),
    ],
)
def test_services_are_whole_words(args: str, service: bool) -> None:  # noqa: FBT001 - a parameter
    assert bool(session.SERVICE.search(args)) is service


SENT = dt.datetime(2026, 11, 13, 0, 26, tzinfo=dt.UTC)


def said(stamp: str, *texts: str, sidechain: bool = False) -> dict[str, object]:
    content: list[object] = [{"type": "tool_use", "name": "Bash"}, *({"type": "text", "text": t} for t in texts)]
    return {"type": "assistant", "timestamp": stamp, "isSidechain": sidechain, "message": {"content": content}}


@pytest.mark.parametrize(
    ("records", "want"),
    [
        (
            [said("2026-11-13T00:26:12Z", "Done.\n\nREADY-TO-RESTART"), said("2026-11-13T00:26:40Z", "A side note.")],
            "ready",
        ),
        ([{"type": "user", "timestamp": "2026-11-13T00:26:01Z", "message": {"content": HANDSHAKE}}], None),
        ([said("2026-11-13T00:25:00Z", "READY-TO-RESTART")], None),
        (
            [said("2026-11-13T00:26:12Z", "BUSY-KEEP-ME a job"), said("2026-11-13T00:30:00Z", "READY-TO-RESTART")],
            "ready",
        ),
        ([said("2026-11-13T00:26:12Z", "READY-TO-RESTART", sidechain=True), said("2026-11-13T00:27:00Z")], None),
        ([said("2026-11-13T00:30:00Z", "BUSY-KEEP-ME still")], "busy"),
        ([said("2026-11-13T00:30:00Z", f"Done.\nREADY-TO-RESTART {TOKEN}")], "ready"),
    ],
    ids=["after-a-side-note", "the-request-itself", "before-the-handshake", "last-wins", "sub-agent", "busy", "token"],
)
def test_the_answer_comes_from_the_transcript(world: World, records: list[dict[str, object]], want: str | None) -> None:
    path = world.transcript(SID, *records)
    with path.open("a") as more:
        more.write('[1]\n{"type": "assistant", "timest')
    assert session.reply(path, SENT, TOKEN) == want


def test_a_transcript_must_be_the_only_one_of_its_session(world: World) -> None:
    assert session.transcript(SID) is None
    world.transcript(SID)
    assert session.transcript(SID) is not None
    other = world.home / f".claude/projects/-other/{SID}.jsonl"
    other.parent.mkdir()
    other.write_text("")
    assert session.transcript(SID) is None


# start


def test_resume_commands_keep_what_each_session_ran_with(world: World) -> None:
    claude = target(world, argv=["claude", "--model", "opus", "--effort", "high", "--resume", SID, "old"])
    assert session.resume_argv(claude, "hi") == [
        "claude",
        "--permission-mode",
        "auto",
        "--model",
        "opus",
        "--effort",
        "high",
        "--resume",
        SID,
        "hi",
    ]
    chief = target(world, space="chief-of-staff", tab="chief-of-staff")
    assert session.resume_argv(chief, "hi") == list(session.CHIEF)
    assert session.resume_argv(target(world, Kind.codex), "hi") == ["codex-hc", "resume", SID]
    fnox = [
        "/mise/installs/fnox-1/fnox",
        "--non-interactive",
        "proxy",
        "run",
        "--",
        "env",
        "-u",
        "RUST_LOG",
        "opencode",
        "-s",
        "x",
    ]
    assert session.resume_argv(target(world, Kind.opencode, argv=fnox), "hi") == [
        "fnox",
        "--non-interactive",
        "proxy",
        "run",
        "--",
        "env",
        "-u",
        "RUST_LOG",
        "opencode",
        "--standalone",
        "-s",
        SID,
    ]
    assert session.resume_argv(target(world, Kind.opencode), "hi") == ["opencode", "--standalone", "-s", SID]


def test_a_folder_that_is_gone_falls_back_to_the_space_then_home(world: World) -> None:
    space, tab, term = target(world, cwd="/no/such/folder")
    assert session.folder_of((space, tab, term)) == space.folder
    assert session.folder_of((space.model_copy(update={"folder": None}), tab, term)) == str(world.home)


def started(world: World, folder: Path | None = None, address: str = "t3") -> int:
    """The resumed process the typed command starts, the foreground of its terminal."""
    pid = world.spawn("claude", "--resume", SID, cwd=folder or world.root / "proj")
    world.answer({("hc", "get", address, "--json"): out(info(address, pid, ["claude"], world.root / "proj"))})
    return pid


def test_a_dry_run_plans_the_resume(world: World) -> None:
    result = session.start(target(world), FAST, apply=False, prompt="hi")
    assert result.result == "planned"
    assert result.notes == [f"claude --permission-mode auto --resume {SID} hi", f"in {world.root / 'proj'}"]


def test_the_resume_is_typed_into_the_tabs_bare_shell(world: World) -> None:
    scene(world, 1)
    world.answer({GET: out(info("t3", None, ["-zsh"], world.root))})
    folder = world.root / "proj"
    typed = ("hc", "send", "t3", f"cd {folder} && claude --permission-mode auto --resume {SID} 'a prompt'")
    pid = started(world)
    shell = out(info("t3", None, ["-zsh"], world.root))
    world.answer({typed: {}, GET: after(shell, (typed, out(info("t3", pid, ["claude"], folder))))})
    result = session.start(target(world), FAST, apply=True, prompt="a prompt")
    assert result.result == "started", result.notes
    assert typed in world.calls()


@pytest.mark.parametrize(
    ("tabs", "note"),
    [
        ([("tb3", "renamed", ["t3"])], "tab tb3 is now renamed"),
        ([("tb3", "worker", ["t5"])], "t3 is not in tab tb3"),
        ([("tb8", "worker", ["t5", "t6"])], "proj / worker now has 2 terminals"),
    ],
    ids=["renamed", "terminal-left", "two-terminals"],
)
def test_a_tab_that_is_not_the_sessions_own_is_left_alone(world: World, tabs: list, note: str) -> None:
    world.answer({("herdr-app", "ls"): out(layout(("proj", str(world.root), tabs)))})
    result = session.start(target(world), FAST, apply=True, prompt="p")
    assert (result.result, result.notes) == ("skipped-moved", [note])
    assert not [c for c in world.calls() if c[:2] == ("hc", "send")]


def test_a_tab_restored_under_a_new_id_gets_the_resume_in_its_one_terminal(world: World) -> None:
    folder = world.root / "proj"
    world.answer(
        {
            ("herdr-app", "ls"): out(layout(("proj", str(folder), [("tb8", "worker", ["t5"])]))),
            ("hc", "get", "t5", "--json"): out(info("t5", None, ["-zsh"], folder)),
        }
    )
    typed = ("hc", "send", "t5", f"cd {folder} && claude --permission-mode auto --resume {SID} p")
    pid = started(world, address="t5")
    shell = out(info("t5", None, ["-zsh"], folder))
    world.answer(
        {typed: {}, ("hc", "get", "t5", "--json"): after(shell, (typed, out(info("t5", pid, ["claude"], folder))))}
    )
    result = session.start(target(world), FAST, apply=True, prompt="p")
    assert (result.result, result.terminal) == ("started", "t5")
    assert typed in world.calls()


def test_a_tab_whose_foreground_is_not_a_shell_is_left_alone(world: World) -> None:
    scene(world, 1)
    world.answer({GET: out(info("t3", 1, ["claude"], world.root))})
    assert session.start(target(world), FAST, apply=True, prompt="p").result == "skipped-tab-busy"


def test_a_missing_tab_or_space_is_opened(world: World) -> None:
    folder = world.root / "proj"
    argv = json.dumps(["claude", "--permission-mode", "auto", "--resume", SID, "p"])
    new_tab = (
        "herdr-app",
        "do",
        "tab.new",
        "--space",
        "sp-proj",
        "--name",
        "worker",
        "--folder",
        str(folder),
        "--argv",
        argv,
    )
    new_space = (
        "herdr-app",
        "do",
        "space.new",
        "--tab",
        "worker",
        "--folder",
        str(folder),
        "--argv",
        argv,
        "--name",
        "proj",
    )
    # The new tab shows up in herdr-app ls with its one terminal, t7, after tab.new.
    empty, opened = (
        out(layout(("proj", "/", []))),
        out(layout(("proj", "/", [("tb6", "other", ["t6"]), ("tb7", "worker", ["t7"])]))),
    )
    world.answer(
        {("herdr-app", "ls"): after(empty, (new_tab, opened)), new_tab: {"stdout": "{}"}, new_space: {"code": 1}}
    )
    started(world, address="t7")
    result = session.start(target(world), FAST, apply=True, prompt="p")
    assert (result.result, result.terminal) == ("started", "t7")
    # A new tab that never shows a terminal.
    world.answer({("herdr-app", "ls"): empty})
    result = session.start(target(world), FAST, apply=True, prompt="p")
    assert (result.result, result.notes[-1]) == ("failed-not-running", "no terminal in the new tab")
    world.answer({("herdr-app", "ls"): out(layout())})
    result = session.start(target(world), FAST, apply=True, prompt="p")
    assert (result.result, result.notes) == ("failed-open", ["herdr-app could not open proj / worker"])
    assert world.calls()[-1] == new_space


def test_a_session_that_does_not_come_back_or_comes_back_elsewhere_fails(world: World) -> None:
    scene(world, 1)
    world.answer({GET: out(info("t3", None, ["zsh"], world.root))})
    world.answer(
        {("hc", "send", "t3", f"cd {world.root / 'proj'} && claude --permission-mode auto --resume {SID} p"): {}}
    )
    assert session.start(target(world), FAST, apply=True, prompt="p").result == "failed-not-running"
    pid = started(world, world.root / "elsewhere")
    again = ("hc", "send", "t3", f"cd {world.root / 'proj'} && claude --permission-mode auto --resume {SID} q")
    shell = out(info("t3", None, ["zsh"], world.root))
    world.answer({again: {}, GET: after(shell, (again, out(info("t3", pid, ["claude"], world.root))))})
    result = session.start(target(world), FAST, apply=True, prompt="q")
    assert (result.result, result.notes) == ("failed-wrong-folder", [f"now {(world.root / 'elsewhere').resolve()}"])


# verify


def versions(world: World, *names: str) -> None:
    for name in names:
        (world.home / ".local/share/claude/versions" / name).mkdir(parents=True)


def test_a_session_that_is_not_running_fails_verify(world: World) -> None:
    assert session.verify(target(world), None, lambda _: "").result == "failed-not-running"


def test_a_current_claude_session_passes(world: World) -> None:
    pid = world.spawn("claude", "--resume", SID, cwd=world.root / "proj")
    versions(world, "2.1.9", "2.1.10")
    world.answer({GET: out(info("t3", pid, ["claude"], world.root, name="2.1.10"))})
    now = dt.datetime.now(dt.UTC).isoformat()
    world.transcript(
        SID,
        {"type": "user", "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "assistant", "timestamp": now},
        {"type": "user", "timestamp": now},
    )
    long_ago = dt.datetime(2000, 1, 1)  # noqa: DTZ001 - compared with ps's local start time
    result = session.verify(target(world), long_ago, lambda _: "")
    assert (result.result, result.notes) == ("ok", [f"pid {pid}", "status idle"])


def test_every_way_a_claude_session_is_stale_is_named(world: World) -> None:
    pid = world.spawn("claude", "--resume", SID, cwd=world.root / "elsewhere")
    versions(world, "2.1.10")
    world.answer({GET: out(info("t3", pid, ["claude"], world.root, name="2.1.9", kind="blocked"))})
    world.transcript(SID, {"type": "user", "timestamp": "2026-01-01T00:00:00Z"})
    mark = dt.datetime.now() + dt.timedelta(hours=1)  # noqa: DTZ005 - ps's local time
    result = session.verify(target(world), mark, lambda _: "Do you trust the files in this folder?")
    assert result.result == "failed-check"
    assert result.notes[0] == "version 2.1.9, installed 2.1.10"
    assert result.notes[1].startswith("started ")
    assert "before the plugins changed" in result.notes[1]
    assert result.notes[2:] == [
        "resume prompt not in the transcript",
        "waiting on a dialog (blocked)",
        f"folder {(world.root / 'elsewhere').resolve()}, want {world.root / 'proj'}",
    ]
    world.answer({GET: out(info("t3", pid, ["claude"], world.root, name="2.1.10"))})
    (world.home / f".claude/projects/-project/{SID}.jsonl").unlink()
    result = session.verify(target(world, cwd=None), None, lambda _: "trust this folder")
    assert result.notes == ["resume prompt not in the transcript", "waiting on a dialog (trust)"]


def test_a_worktree_that_changed_across_the_restart_fails(world: World) -> None:
    folder = world.root / "proj"
    folder.mkdir()
    subprocess.run(["git", "init", "-q", str(folder)], check=True)
    before = session.worktree(str(folder))
    assert before is not None
    assert session.worktree(None) is None
    pid = world.spawn("claude", "--resume", SID, cwd=folder)
    world.answer({GET: out(info("t3", pid, ["claude"], folder))})
    world.transcript(SID, {"type": "user", "timestamp": dt.datetime.now(dt.UTC).isoformat()})
    assert session.verify(target(world), None, lambda _: "", before).result == "ok"
    (folder / "new.txt").write_text("")
    result = session.verify(target(world), None, lambda _: "", before)
    assert result.notes == ["worktree git status changed across the restart"]


def test_codex_is_current_when_it_started_after_its_binary_changed(world: World) -> None:
    binary = world.home / ".local/bin/codex"
    binary.parent.mkdir(parents=True)
    binary.write_text("")
    os.utime(binary, (0, 0))
    pid = world.spawn("codex", "resume", SID, cwd=world.root / "proj")
    world.answer({GET: out(info("t3", pid, ["codex"], world.root))})
    assert session.verify(target(world, Kind.codex), None, lambda _: "").result == "ok"
    later = time.time() + 3600
    os.utime(binary, (later, later))
    result = session.verify(target(world, Kind.codex), None, lambda _: "")
    assert result.notes == [f"started before {binary} changed"]
    other = world.spawn("opencode", "-s", SID, cwd=world.root / "proj")
    world.answer({("hc", "get", "t8", "--json"): out(info("t8", other, ["opencode"], world.root))})
    assert session.verify(target(world, Kind.opencode), None, lambda _: "", None, "t8").result == "ok"


def test_verify_looks_only_in_the_sessions_own_terminal_for_its_harness(world: World) -> None:
    # The session id in another terminal's process, or in a process that is not the harness, does not count.
    world.spawn("claude", "--resume", SID, cwd=world.root / "proj")
    shell = world.spawn("fnox", "--resume", SID, cwd=world.root / "proj")
    world.answer({GET: out(info("t3", shell, ["fnox"], world.root))})
    assert session.verify(target(world), None, lambda _: "").result == "failed-not-running"


def test_an_excluded_session_is_untouched_while_its_pid_is_the_same(world: World) -> None:
    scene(world, 42)
    now = live.Live()
    assert session.untouched(target(world, pid=42), now).result == "untouched"
    changed = session.untouched(target(world, pid=41), now)
    assert (changed.result, changed.notes) == ("failed-changed", ["pid 41 -> 42"])
    assert session.untouched(target(world), now).result == "failed-changed"


def test_the_raw_environment_drops_hcs_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HC_SCOPE", "x")
    assert {"HC_TERMINAL_ID", "HC_SCOPE"}.isdisjoint(live.raw_env())


def test_verify_reads_the_version_in_the_terminal_start_resumed_in(world: World) -> None:
    pid = world.spawn("claude", "--resume", SID, cwd=world.root / "proj")
    versions(world, "2.1.10")
    # The graph's terminal still shows an old Claude; the session runs current in t8, the tab start opened.
    world.answer(
        {
            GET: out(info("t3", None, ["claude"], world.root, name="2.1.9")),
            ("hc", "get", "t8", "--json"): out(info("t8", pid, ["claude"], world.root, name="2.1.10")),
        }
    )
    world.transcript(SID, {"type": "user", "timestamp": dt.datetime.now(dt.UTC).isoformat()})
    result = session.verify(target(world), None, lambda _: "", None, "t8")
    assert (result.result, result.terminal) == ("ok", "t8")
