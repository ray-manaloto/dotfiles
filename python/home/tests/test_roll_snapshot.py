"""roll:snapshot: the graph from real processes, lane pages and git worktrees, and what it writes."""

import json
import subprocess
from pathlib import Path

import pytest

from hometools.models import Graph, Kind, Role
from hometools.roll import graph, live

from .roll_world import World, hometools, info, layout, out, terminal

UUID = "0199aaaa-bbbb-4ccc-8ddd-eeeeffff0000"
ROOT = "0199aaaa-bbbb-4ccc-8ddd-000000000001"


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)


def repo(world: World) -> tuple[Path, Path]:
    """A real repository with a clean main checkout and a worktree holding a staged change."""
    main = world.root / "proj"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "start")
    other = world.root / "proj-feature"
    git(main, "worktree", "add", "-q", str(other))
    (other / "new.txt").write_text("work\n")
    git(other, "add", "new.txt")
    return main, other


def scene(world: World) -> None:
    """chief-of-staff, a project with a lead, two Claude children, Codex, OpenCode, a shell, an agent with no
    session found, a terminal that is not live, and this task's own tab."""
    main, other = repo(world)
    chief = world.spawn("claude", "--resume", "chief", cwd=world.root / "fix-herdr")
    world.claude_record(chief, "chief-sid")
    lead = world.spawn("claude", "--model", "opus", "--resume", "lead-sid", cwd=main)
    world.claude_record(lead, "lead-sid")
    worker = world.spawn("claude", cwd=main)
    world.claude_record(worker, "worker-sid")
    loose = world.spawn("claude", cwd=main)
    world.claude_record(loose, "loose-sid")
    rollout = world.home / f".codex/sessions/rollout-2026-11-14T10-00-00-{UUID}.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(json.dumps({"payload": {"session_id": ROOT}}) + "\n")
    codex = world.spawn("codex", f"open={rollout}", cwd=main)
    fnox = ["fnox", "--non-interactive", "proxy", "run", "--", "env", "opencode", "--standalone", "-s", "ses_abc"]
    opencode = world.spawn("fnox", cwd=main)
    lost = world.spawn("claude", cwd=main)
    (world.wiki / "lanes/proj.md").write_text(
        "# proj\n\n## Status\n- worker (t3) is listed outside Children\n\n## Children\n"
        "- worker (t3): building in proj-feature\n\n## Notes\n- worker (t3) works in proj-feature\n"
    )
    world.answer(
        {
            ("hc", "ls", "--json"): out(
                {
                    "terminals": [
                        terminal("t1", "chief-of-staff / chief-of-staff"),
                        terminal("t2", "proj / proj-lead"),
                        terminal("t3", "proj / worker"),
                        terminal("t4", "proj / loose"),
                        terminal("t5", "proj / review", agent="codex"),
                        terminal("t6", "proj / 1", agent="opencode"),
                        terminal("t7", "proj / 2", agent="zsh"),
                        terminal("t8", "proj / lost"),
                        terminal("t9", "proj / roll", agent="zsh"),
                        {"address": "t0", "state": "finished", "where": "proj / done"},
                    ]
                }
            ),
            ("herdr-app", "ls"): out(
                layout(
                    ("chief-of-staff", str(world.root / "fix-herdr"), [("tb1", "chief-of-staff", ["t1"])]),
                    (
                        "proj",
                        str(main),
                        [
                            ("tb2", "proj-lead", ["t2"]),
                            ("tb3", "worker", ["t3"]),
                            ("tb4", "loose", ["t4"]),
                            ("tb5", "review", ["t5"]),
                            ("tb6", "1", ["t6"]),
                            ("tb7", "2", ["t7"]),
                            ("tb8", "lost", ["t8"]),
                            ("tb9", "roll", ["t9", "t0"]),
                        ],
                    ),
                )
            ),
            ("hc", "get", "t1", "--json"): out(info("t1", chief, ["claude"], world.root / "fix-herdr")),
            ("hc", "get", "t2", "--json"): out(info("t2", lead, ["claude", "--model", "opus"], main)),
            ("hc", "get", "t3", "--json"): out(info("t3", worker, ["claude"], main)),
            ("hc", "get", "t4", "--json"): out(info("t4", loose, ["claude"], main)),
            ("hc", "get", "t5", "--json"): out(info("t5", codex, ["codex"], main)),
            ("hc", "get", "t6", "--json"): out(info("t6", opencode, fnox, main)),
            ("hc", "get", "t7", "--json"): out(info("t7", None, ["/bin/zsh", "-l"], main)),
            ("hc", "get", "t8", "--json"): out(info("t8", lost, ["claude"], main)),
            ("hc", "get", "t9", "--json"): out(info("t9", None, ["zsh"], main)),
        }
    )
    _ = other


def previous(world: World) -> None:
    """The graph a restore left: a closed project, and a closed tab of a live one."""
    path = world.wiki / "sessions/graph.json"
    path.parent.mkdir(parents=True)
    old_term = {
        "address": "t50",
        "kind": "claude",
        "session": "gone-sid",
        "cwd": "/",
        "argv": None,
        "status": None,
        "lane_parents": [],
        "is_coordinator": False,
    }
    running = old_term | {"address": "t51", "session": "worker-sid"}
    shell = old_term | {"address": "t52", "kind": "shell", "session": None}
    spaces = [
        {"id": "sp-x", "name": "closed", "folder": None, "tabs": [{"id": "x", "name": "a", "terminals": [old_term]}]},
        {
            "id": "sp-proj",
            "name": "proj",
            "folder": None,
            "tabs": [
                {"id": "y", "name": "gone-tab", "terminals": [old_term]},
                {"id": "z", "name": "renamed", "terminals": [running]},
                {"id": "w", "name": "old-shell", "terminals": [shell]},
                {"id": "v", "name": "worker", "terminals": [old_term]},
            ],
        },
    ]
    path.write_text(json.dumps({"taken_at": "then", "coordinator": "t50", "spaces": spaces}))


def test_the_dry_run_reads_every_session_and_writes_nothing(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    code, got, err = hometools(capfd, "snapshot", "--wiki", str(world.wiki))
    assert code == 0, err
    report = json.loads(got.splitlines()[0])
    assert report == {
        "graph": None,
        "graph_copy": None,
        "terminals": 9,
        "agents": 7,
        "agents_without_session": ["t8"],
        "children_without_lane": ["proj / loose", "proj / lost"],
        "work_elsewhere": [
            {
                "tab": "proj / worker",
                "session": "worker-sid",
                "cwd": str(world.root / "proj"),
                "work_in": str(world.root / "proj-feature"),
            }
        ],
    }
    assert got.splitlines()[1] == (
        "chosen: chief-of-staff / chief-of-staff (t1), proj / worker (t3), proj / loose (t4), proj / review (t5), "
        "proj / 1 (t6), proj / proj-lead (t2)"
    )
    assert got.splitlines()[2] == "left alone: none"
    assert not (world.wiki / "sessions").exists()
    assert not world.state().exists()


def test_apply_writes_the_graph_atomically_with_copies_and_keeps_closed_projects(
    world: World, capfd: pytest.CaptureFixture[str]
) -> None:
    scene(world)
    previous(world)
    code, got, err = hometools(capfd, "snapshot", "--apply", "--wiki", str(world.wiki), "--exclude", "chief-of-staff")
    assert code == 0, err
    report = json.loads(got.splitlines()[0])
    path = world.wiki / "sessions/graph.json"
    assert report["graph"] == str(path)
    copy = Path(report["graph_copy"])
    assert copy.parent == path.parent
    assert copy.name.startswith("graph-")
    assert copy.read_text() == path.read_text()
    assert [p.name for p in path.parent.iterdir() if p.name.startswith(".")] == []
    made = Graph.model_validate_json(path.read_text())
    assert made.coordinator == "t1"
    kinds = {t.address: (t.kind, t.session) for s in made.spaces for tab in s.tabs for t in tab.terminals}
    assert kinds["t1"] == (Kind.claude, "chief-sid")
    assert kinds["t5"] == (Kind.codex, ROOT)
    assert kinds["t6"] == (Kind.opencode, "ses_abc")
    assert kinds["t7"] == (Kind.shell, None)
    assert kinds["t8"] == (Kind.claude, None)
    assert "t0" not in kinds
    proj = next(s for s in made.spaces if s.name == "proj")
    kept = [tab.name for tab in proj.tabs if tab.kept_from_previous_graph]
    assert kept == ["gone-tab"]
    assert [s.name for s in made.spaces if s.kept_from_previous_graph] == ["closed"]
    worker = next(t for tab in proj.tabs for t in tab.terminals if t.address == "t3")
    assert [p.lane for p in worker.lane_parents] == ["proj.md"]
    lead = next(t for tab in proj.tabs for t in tab.terminals if t.address == "t2")
    assert lead.argv == ["claude", "--model", "opus"]
    assert lead.pid is not None
    # The kept-from fields are left out where unset, as the scripts wrote them.
    assert '"kept_from_previous_graph": null' not in path.read_text()
    ledger = (path.parent / "ledger.md").read_text()
    assert "| chief-of-staff | chief-of-staff | t1 (coordinator) | claude | chief-sid |" in ledger
    assert "| proj | worker | t3 | claude | worker-sid | " in ledger
    assert ledger.splitlines()[-1].startswith("| closed | a | t50 |")
    run = world.state() / world.runs()[0].run
    assert (run / "graph.json").read_text() == path.read_text()
    versions = json.loads((run / "versions.json").read_text())
    assert versions == {
        "harnesses": dict.fromkeys(["claude", "codex", "opencode", "agy"]),
        "plugins": {},
        "marketplaces": {},
    }
    assert got.splitlines()[2] == "left alone: chief-of-staff / chief-of-staff (t1)"
    line = world.runs()[0]
    assert (line.step, line.rc, line.args) == (
        "snapshot",
        0,
        ["snapshot", "--apply", "--wiki", str(world.wiki), "--exclude", "chief-of-staff"],
    )
    assert Path(str(line.log)).read_text() == got


def test_a_previous_graph_that_is_not_one_stops_the_snapshot(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    scene(world)
    path = world.wiki / "sessions/graph.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"spaces": "no"}')
    code, got, err = hometools(capfd, "snapshot", "--apply", "--wiki", str(world.wiki))
    assert (code, got) == (1, "")
    assert json.loads(err)["error"].startswith(f"roll:snapshot: {path} is not a graph (")
    assert path.read_text() == '{"spaces": "no"}'
    assert world.runs()[0].rc == 1


@pytest.mark.parametrize("layout_answer", [{"code": 1}, out({"spaces": []})], ids=["failed", "empty"])
def test_a_herdr_layout_with_no_spaces_writes_nothing(
    world: World, capfd: pytest.CaptureFixture[str], layout_answer: dict[str, object]
) -> None:
    """A graph built from nothing would mark every project closed; the snapshot stops before writing it."""
    world.answer({("hc", "ls", "--json"): out(["not", "an", "object"]), ("herdr-app", "ls"): layout_answer})
    code, got, err = hometools(capfd, "snapshot", "--apply", "--wiki", str(world.wiki))
    assert (code, got) == (1, "")
    assert "herdr-app ls answered no spaces" in json.loads(err)["error"]
    assert not (world.wiki / "sessions/graph.json").exists()


@pytest.mark.parametrize(
    ("first", "want"),
    [("{not json", UUID), (json.dumps({"payload": {}}), UUID), (json.dumps({"payload": {"session_id": ROOT}}), ROOT)],
    ids=["unreadable", "no-root", "sub-agent"],
)
def test_a_codex_rollout_names_its_root_thread_when_it_can(world: World, first: str, want: str) -> None:
    rollout = world.home / f"rollout-x-{UUID}.jsonl"
    rollout.write_text(first + "\n")
    pid = world.spawn("codex", f"open={rollout}")
    # lsof exits 1 for a pid that has gone; what it printed for the rest still counts.
    assert live.poll(lambda: graph.codex_session([pid, 99999999]), 5, 0.02) == want
    rollout.unlink()
    assert graph.codex_session([pid]) == UUID
    assert graph.codex_session([]) is None


def test_a_half_written_claude_record_is_skipped(world: World) -> None:
    bad, good = (world.home / f".claude/sessions/{pid}.json" for pid in (1, 2))
    good.parent.mkdir(parents=True)
    bad.write_text("{")
    good.write_text(json.dumps({"sessionId": 7}))
    assert graph.claude_session([1, 2, 3]) is None
    world.claude_record(3, "s3")
    assert graph.claude_session([1, 2, 3]) == "s3"


def test_opencode_sessions_come_from_its_argv() -> None:
    assert graph.opencode_session(["opencode", "--session", "ses_1"]) == "ses_1"
    assert graph.opencode_session(["opencode", "-s", "other"]) is None


@pytest.mark.parametrize(
    ("space", "tab", "want"),
    [
        ("chief-of-staff", "chief-of-staff", Role.coordinator),
        ("chief-of-staff", "1", Role.lead),
        ("p", "p-lead", Role.lead),
        ("p", "x-coord", Role.lead),
        ("p", "x-v2", Role.lead),
        ("p", "worker", Role.child),
    ],
)
def test_one_rule_names_the_coordinator_leads_and_children(space: str, tab: str, want: Role) -> None:
    assert live.role(space, tab) is want


def test_a_program_that_hangs_or_fails_reads_as_nothing() -> None:
    assert live.call("sleep", "5", timeout=0.05) is None
    assert live.call("false") is None
    assert live.call("no-such-program-anywhere") is None
    assert live.answer("echo", "[1]") == {}
    assert live.answer("echo", "{") == {}


def test_poll_answers_as_soon_as_its_probe_does_and_stops_at_its_deadline() -> None:
    seen = iter([None, None, 3])
    assert live.poll(lambda: next(seen), 5, 0) == 3
    assert live.poll(lambda: None, 0, 0) is None


def test_a_coordinator_tab_needs_both_names_and_a_terminal(world: World) -> None:
    world.answer(
        {
            ("hc", "ls", "--json"): out({"terminals": []}),
            ("herdr-app", "ls"): out(
                layout(
                    ("other", "/", [("a", "chief-of-staff", ["t1"])]),
                    ("chief-of-staff", "/", [("b", "chief-of-staff", [])]),
                )
            ),
        }
    )
    assert graph.coordinator_of(live.Live()) is None


def test_a_dirty_checkout_is_not_work_elsewhere(world: World) -> None:
    _, feature = repo(world)
    term = graph.GraphTerminal(
        address="t1",
        kind=Kind.claude,
        session="s",
        cwd=str(feature),
        argv=None,
        status=None,
        lane_parents=[],
        is_coordinator=False,
    )
    assert graph.changed_elsewhere(term) == []
    assert graph.changed_elsewhere(term.model_copy(update={"kind": Kind.shell})) == []


def test_a_kept_space_or_tab_has_no_work_elsewhere(world: World) -> None:
    main, _ = repo(world)
    (world.wiki / "lanes/proj.md").write_text("# proj\n\n- worker (t3): building in proj-feature\n")
    term = graph.GraphTerminal(
        address="t3",
        kind=Kind.claude,
        session="s",
        cwd=str(main),
        argv=None,
        status=None,
        lane_parents=[],
        is_coordinator=False,
    )
    tab = graph.GraphTab(id="tb3", name="worker", terminals=[term])
    space = graph.GraphSpace(id="sp", name="proj", folder=str(main), tabs=[tab])
    made = Graph(taken_at="now", coordinator=None, spaces=[space])
    assert [found.work_in for found in graph.work_elsewhere(made, world.wiki)] == [str(world.root / "proj-feature")]
    kept_tab = tab.model_copy(update={"kept_from_previous_graph": True})
    kept = [space.model_copy(update={"tabs": [kept_tab]}), space.model_copy(update={"kept_from_previous_graph": True})]
    for one in kept:
        assert graph.work_elsewhere(made.model_copy(update={"spaces": [one]}), world.wiki) == []


def test_a_folder_that_cannot_be_read_has_no_entries(world: World) -> None:
    assert live.entries(world.root / "no-such-folder") == []


@pytest.mark.parametrize(
    ("argv", "want"),
    [
        (
            ["/x/fnox", "--non-interactive", "proxy", "run", "--", "env", "-u", "RUST_LOG", "A=1", "opencode"],
            "opencode",
        ),
        (["env", "claude", "--resume", "s"], "claude"),
        (["fnox", "proxy"], "proxy"),
        (["env"], None),
        ([], None),
    ],
)
def test_the_program_is_past_its_launchers(argv: list[str], want: str | None) -> None:
    assert live.program(argv) == want


def test_an_hc_ls_that_fails_writes_nothing(world: World, capfd: pytest.CaptureFixture[str]) -> None:
    world.answer({("hc", "ls", "--json"): {"code": 1}, ("herdr-app", "ls"): out(layout(("proj", "/", [])))})
    code, _, err = hometools(capfd, "snapshot", "--apply", "--wiki", str(world.wiki))
    assert code == 1
    assert "hc ls --json answered no terminal list" in json.loads(err)["error"]
    assert not (world.wiki / "sessions/graph.json").exists()
