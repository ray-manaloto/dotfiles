"""status, start, stop and restart against stand-in IDE processes: real station sockets, /exit and /api/about."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import filelock
import pytest

from .conftest import Start, install, launcher, run, settings

# stop and restart ask the real jbax for the IDE's windows first (a stand-in IDE has none, so no dialog is open).
needs_jbax = pytest.mark.skipif(not shutil.which("jbax"), reason="jbax is not installed (mise run //swift:install)")


def flags(app: Path, *extra: str) -> None:
    """Make the app's launcher start the stand-in with these flags, as if the IDE behaved that way."""
    path = launcher(app)
    path.write_text(path.read_text().replace('"$@"', " ".join([*extra, '"$@"'])))


def solo(toolbox: Path, code: str = "SL") -> None:
    """A second product with one install (script solo, tool id Solo), for --all."""
    app = toolbox / "solo.app"
    for folder in ("Resources", "MacOS", "bin", "plugins/station-plugin"):
        (app / "Contents" / folder).mkdir(parents=True)
    (app / "Contents/bin/fake.vmoptions").write_text("-Xmx1g\n")
    launch = {"vmOptionsFilePath": "../bin/fake.vmoptions", "additionalJvmArguments": []}
    info = {"productCode": code, "buildNumber": "263.1.2", "launch": [launch]}
    (app / "Contents/Resources/product-info.json").write_text(json.dumps(info))
    launcher(app)
    install(toolbox / "toolbox", "solo", app, "solo", product=code, tool_id="Solo")


def second(toolbox: Path) -> subprocess.Popen[str]:
    """fake1 (the product's second install) running, started the way a user would, not through jbctl."""
    process = subprocess.Popen(
        [toolbox / "fake-2.app/Contents/MacOS/fake", "--stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert process.stdout
    process.stdout.readline()
    return process


def test_status_lists_the_running_ides(capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start) -> None:
    ide = start("--mcp")
    settings(toolbox / "fake-config", f"mcpServerPort={ide.ports[0]}")
    row = {"script": "fake", "tool_id": "Fake", "pid": ide.process.pid, "state": "ready", "mcp": "answering"}
    assert run(capsys, "status") == (0, [{"ides": [row | {"mcp_port": ide.ports[0]}]}], "")


def test_status_all_includes_the_stopped(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    ide = start()
    code, [event], _ = run(capsys, "status", "--all")
    rows = {row["script"]: row for row in event["ides"]}
    assert (code, rows["fake1"]) == (0, {"script": "fake1", "tool_id": "Fake", "state": "stopped"})
    assert rows["fake"] | {"note": ""} == {
        "script": "fake",
        "tool_id": "Fake",
        "pid": ide.process.pid,
        "state": "ready",
        "mcp": "not-answering",
        "mcp_port": 64342,
        "note": "",
    }
    assert rows["fake"]["note"] == "nothing answered MCP on 64342 (the Fake default)"


@pytest.mark.usefixtures("toolbox")
def test_status_names_an_ide_by_script_or_tool_id(capsys: pytest.CaptureFixture[str]) -> None:
    stopped = [{"script": "fake1", "tool_id": "Fake", "state": "stopped"}]
    assert run(capsys, "status", "--ide", "fake1") == (0, [{"ides": stopped}], "")
    code, [event], _ = run(capsys, "status", "--product", "Fake")
    assert (code, [row["script"] for row in event["ides"]]) == (0, ["fake", "fake1"])


def test_status_shows_a_starting_ide_and_skips_tool_runs(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """A process without its station socket yet is starting, even when a file of that socket's name is there;
    `fake stdioMcpServer` is one of the IDE's tools."""
    tool = start("--no-station", "stdioMcpServer")
    assert run(capsys, "status") == (0, [{"ides": []}], "")
    ide = start("--no-station")
    (Path(os.environ["JBCTL_STATION_DIR"]) / f"jb.station.ij.{ide.process.pid}.sock").touch()
    starting = {"script": "fake", "tool_id": "Fake", "pid": ide.process.pid, "state": "starting"}
    assert (tool.process.pid != ide.process.pid, run(capsys, "status")) == (True, (0, [{"ides": [starting]}], ""))


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        ("--busy", "HTTP 429"),
        ("--old", "HTTP 200, build 0.0"),
        ("--garbage", "HTTP 200, not a JSON object"),
        ("--not-http", "Error"),  # httpx's name for a server that hangs up: RemoteProtocolError, ReadError
    ],
)
def test_status_reports_why_an_ide_is_not_ready(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start, answer: str, said: str
) -> None:
    """Not ready, with what /api/about said in the note, after an unreadable MCP setting."""
    ide = start(answer)
    (toolbox / "fake-config/options").mkdir(parents=True)
    (toolbox / "fake-config/options/mcpServer.xml").write_text("<application")
    code, [event], _ = run(capsys, "status")
    [row] = event["ides"]
    assert (code, row["pid"], row["state"], row["mcp"]) == (0, ide.process.pid, "not-ready", "unknown")
    unreadable, about = row["note"].split("; ")
    assert (unreadable.startswith("unclosed token"), about.startswith("/api/about: 6334"), said in about) == (
        True,
        True,
        True,
    )


@needs_jbax
@pytest.mark.parametrize("project", [None, 'pro"ject\n {x}'])
def test_start_launches_as_toolbox_does_and_stop_quits(
    capsys: pytest.CaptureFixture[str], toolbox: Path, monkeypatch: pytest.MonkeyPatch, project: str | None
) -> None:
    """The launchCommand runs with the project folder as one argument, whatever its name holds, and nothing else."""
    record = toolbox / "argv.json"
    monkeypatch.setenv("STANDIN_RECORD", str(record))
    (toolbox / "fake-config").mkdir()
    (toolbox / "fake-config/.lock").write_text("999999")  # left by an IDE that has ended
    folder = toolbox / project if project else None
    if folder:
        folder.mkdir()
    code, [event], _ = run(
        capsys,
        "start",
        "--foreground",
        "--ide",
        "fake",
        "--timeout",
        "20",
        *(["--project", str(folder)] * bool(folder)),
    )
    started = event["lifecycle"]
    assert (code, started["script"], started["action"]) == (0, "fake", "started")
    assert json.loads(record.read_text()) == ([str(folder.resolve())] if folder else [])
    stopped = {"script": "fake", "action": "stopped", "pid": started["pid"]}
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "20") == (0, [{"lifecycle": stopped}], "")


@pytest.mark.usefixtures("toolbox")
def test_start_needs_a_project_folder(capsys: pytest.CaptureFixture[str]) -> None:
    refused = {"script": "fake", "action": "refused", "reason": "/no/such/folder is not a folder"}
    assert run(capsys, "start", "--foreground", "--ide", "fake", "--project", "/no/such/folder") == (
        1,
        [{"lifecycle": refused}],
        "",
    )


def test_start_refuses_a_running_ide(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    ide = start()
    reason = f"fake already runs as pid {ide.process.pid}"
    assert run(capsys, "start", "--foreground", "--ide", "fake") == (
        1,
        [{"lifecycle": {"script": "fake", "action": "refused", "reason": reason}}],
        "",
    )


def test_start_refuses_a_second_install_of_the_product(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """Installs of one product can share a config directory, and a second IDE rewrites shared settings."""
    ide = start()
    reason = f"fake (pid {ide.process.pid}) runs, and another Fake could share its settings"
    refused = {"script": "fake1", "action": "refused", "reason": reason}
    assert run(capsys, "start", "--foreground", "--ide", "fake1") == (1, [{"lifecycle": refused}], "")


@pytest.mark.parametrize(
    ("owner", "reason"),
    [(str(os.getpid()), f"its config directory is in use by pid {os.getpid()}"), ("1x", "names no pid")],
)
def test_start_refuses_a_config_directory_in_use(
    capsys: pytest.CaptureFixture[str], toolbox: Path, owner: str, reason: str
) -> None:
    """The IDE writes its pid to <config>/.lock: a live one, or one jbctl cannot read, holds the directory."""
    lock = toolbox / "fake-config/.lock"
    lock.parent.mkdir()
    lock.write_text(owner)
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake")
    assert (code, event["lifecycle"]["action"], reason in event["lifecycle"]["reason"]) == (1, "refused", True)


@pytest.mark.usefixtures("toolbox")
def test_start_by_product_refuses_several_installs(capsys: pytest.CaptureFixture[str]) -> None:
    error = "Fake has 2 installs (fake, fake1); pick one with --ide"
    assert run(capsys, "start", "--foreground", "--product", "Fake") == (1, [], error)


@pytest.mark.parametrize(
    ("extra", "reason"),
    [
        ([], "no IDE came up from {app} in time"),
        (["--no-about", "--die"], "ended before it was ready"),
    ],
)
def test_start_reports_an_ide_that_does_not_come_up(
    capsys: pytest.CaptureFixture[str], toolbox: Path, extra: list[str], reason: str
) -> None:
    """Nothing runs afterwards, so the outcome is a refusal."""
    app = toolbox / "fake.app"
    if extra:
        flags(app, *extra)
    else:  # a launcher that starts nothing
        (app / "Contents/MacOS/fake").write_text("#!/bin/sh\nexit 0\n")
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake", "--timeout", "3")
    assert (code, event["lifecycle"]["action"]) == (1, "refused")
    assert reason.format(app=app) in event["lifecycle"]["reason"]


@needs_jbax
def test_start_reports_an_ide_that_runs_but_is_not_ready(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """jbctl launched it and it still runs: started-not-ready, exit 75, with a reason that says so, and status shows
    it not-ready, so nothing starts it a second time; stop still quits it."""
    flags(toolbox / "fake.app", "--no-about")
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake", "--timeout", "3")
    started = event["lifecycle"]
    assert (code, started["action"]) == (75, "started-not-ready")
    assert started["reason"].startswith(f"pid {started['pid']} is still running but was not ready in time")
    code, [listed], _ = run(capsys, "status", "--ide", "fake")
    assert (code, listed["ides"][0]["state"], listed["ides"][0]["pid"]) == (0, "not-ready", started["pid"])
    again = f"fake already runs as pid {started['pid']}"
    refused = {"script": "fake", "action": "refused", "reason": again}
    assert run(capsys, "start", "--foreground", "--ide", "fake") == (1, [{"lifecycle": refused}], "")
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "20")[0] == 0


def test_start_reports_an_ide_that_ends_at_the_deadline(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """It ended during jbctl's last /api/about request, which outlasted --timeout: nothing runs, so refused, not
    started-not-ready."""
    flags(toolbox / "fake.app", "--die-asked")
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake", "--timeout", "1.5")
    assert (code, event["lifecycle"]["action"]) == (1, "refused")
    assert event["lifecycle"]["reason"].endswith("ended before it was ready")


@pytest.mark.usefixtures("toolbox")
def test_another_jbctl_holds_the_ide(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    product = hashlib.sha256(b"FK").hexdigest()[:16]
    with filelock.FileLock(toolbox / f"state/jbctl/lifecycle/product-{product}.lock"):
        code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake")
    assert (code, event["lifecycle"]["reason"].startswith("another jbctl is")) == (1, True)


@needs_jbax
def test_stop_without_force_never_kills(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    ide = start("--stubborn")
    code, [event], _ = run(capsys, "stop", "--ide", "fake", "--timeout", "1")
    assert (code, event["lifecycle"]["action"], ide.process.poll()) == (1, "refused", None)
    assert event["lifecycle"]["reason"].endswith("answer it in the IDE or wait. Nothing was killed.")
    stopped = {"script": "fake", "action": "stopped", "pid": ide.process.pid}
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "5", "--force") == (0, [{"lifecycle": stopped}], "")


@needs_jbax
@pytest.mark.parametrize(("flag", "reason"), [("--deaf", "Nothing was killed."), ("--refuse", "HTTP 503")])
def test_stop_reports_an_ide_that_will_not_quit(
    capsys: pytest.CaptureFixture[str], start: Start, flag: str, reason: str
) -> None:
    ide = start(flag)
    code, [event], _ = run(capsys, "stop", "--ide", "fake", "--timeout", "1", "--force")
    assert (code, reason in event["lifecycle"]["reason"], ide.process.poll()) == (1, True, None)


@pytest.mark.usefixtures("toolbox")
def test_stop_needs_a_running_ide(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    reason = f"0 IDEs run from {toolbox / 'fake.app'}; want exactly one"
    assert run(capsys, "stop", "--ide", "fake") == (
        1,
        [{"lifecycle": {"script": "fake", "action": "refused", "reason": reason}}],
        "",
    )
    assert run(capsys, "stop", "--product", "Fake") == (1, [], "no install of Fake runs (fake, fake1)")


def test_stop_by_product_refuses_several_running(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    start()
    other = second(toolbox)
    assert run(capsys, "stop", "--product", "Fake") == (
        1,
        [],
        "2 installs of Fake run (fake, fake1); pick one with --ide",
    )
    other.communicate("")


@needs_jbax
def test_restart_waits_for_the_new_ide(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    ide = start()
    code, [event], _ = run(capsys, "restart", "--foreground", "--ide", "fake", "--timeout", "20")
    restarted = event["lifecycle"]
    assert (code, restarted["action"], restarted["previous_pid"]) == (0, "restarted", ide.process.pid)
    assert restarted["pid"] != ide.process.pid
    stopped = {"script": "fake", "action": "stopped", "pid": restarted["pid"]}
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "20") == (0, [{"lifecycle": stopped}], "")


@needs_jbax
def test_restart_refuses_while_another_install_runs(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    start()
    other = second(toolbox)
    code, [event], _ = run(capsys, "restart", "--foreground", "--ide", "fake")
    assert (code, event["lifecycle"]["reason"]) == (
        1,
        f"fake1 (pid {other.pid}) runs, and another Fake could share its settings",
    )
    other.communicate("")


@needs_jbax
def test_restart_reports_an_ide_that_does_not_quit(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    start("--deaf")
    code, [event], _ = run(capsys, "restart", "--foreground", "--ide", "fake", "--timeout", "1")
    assert (code, event["lifecycle"]["reason"].endswith("Nothing was killed.")) == (1, True)


@needs_jbax
def test_all_prints_a_plan_and_acts_only_with_yes(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    """--all starts one install per product: a product with several installs is skipped, never guessed."""
    solo(toolbox)
    skipped = "Fake has 2 installs (fake, fake1); pick one with --ide"
    plan = [
        {"lifecycle": {"script": "fake", "action": "skipped", "reason": skipped}},
        {"lifecycle": {"script": "fake1", "action": "skipped", "reason": skipped}},
        {"lifecycle": {"script": "solo", "action": "would-start"}},
    ]
    assert run(capsys, "start", "--all") == (0, plan, "")
    code, events, _ = run(capsys, "start", "--foreground", "--all", "--yes", "--timeout", "20")
    assert (code, events[:2], events[2]["lifecycle"]["action"]) == (0, plan[:2], "started")
    ide = start()
    already = {"script": "solo", "action": "skipped", "reason": f"already runs as pid {events[2]['lifecycle']['pid']}"}
    assert run(capsys, "start", "--all")[1][2] == {"lifecycle": already}
    would = [{"lifecycle": {"script": name, "action": "would-stop"}} for name in ("fake", "solo")]
    assert run(capsys, "stop", "--all") == (0, would, "")
    assert run(capsys, "restart", "--all") == (
        0,
        [{"lifecycle": e["lifecycle"] | {"action": "would-restart"}} for e in would],
        "",
    )
    code, events, _ = run(capsys, "stop", "--all", "--yes", "--timeout", "20")
    assert (code, [e["lifecycle"]["action"] for e in events], ide.process.wait(5)) == (0, ["stopped", "stopped"], 0)


@pytest.mark.usefixtures("toolbox")
@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["start", "--all", "--ide", "fake"], "--all picks every IDE; leave out --ide and --product"),
        (["stop"], "nothing to act on: name IDEs with --ide or --product, or use --all"),
        (["status", "--product", "Nope"], "Toolbox has no IDE with tool id Nope; its tool ids are Fake"),
    ],
)
def test_lifecycle_usage_errors(capsys: pytest.CaptureFixture[str], argv: list[str], error: str) -> None:
    assert run(capsys, *argv) == (1, [], error)


@needs_jbax
def test_product_names_its_one_install(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """--product is the only install of the product (start), then the only one running (stop)."""
    solo(toolbox)
    code, [event], _ = run(capsys, "start", "--foreground", "--product", "Solo", "--timeout", "20")
    assert (code, event["lifecycle"]["action"]) == (0, "started")
    stopped = {"script": "solo", "action": "stopped", "pid": event["lifecycle"]["pid"]}
    assert run(capsys, "stop", "--product", "Solo", "--timeout", "20") == (0, [{"lifecycle": stopped}], "")


@needs_jbax
def test_an_install_reached_through_a_symlink_is_recognized(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """Toolbox records the path as the user has it; the running IDE is matched by its real path, so a second
    start is refused rather than launched beside it."""
    link = toolbox / "linked"
    link.symlink_to(toolbox)
    state = toolbox / "toolbox/state.json"
    state.write_text(state.read_text().replace(str(toolbox), str(link)))
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake", "--timeout", "20")
    assert (code, event["lifecycle"]["action"]) == (0, "started")
    reason = f"fake already runs as pid {event['lifecycle']['pid']}"
    assert run(capsys, "start", "--foreground", "--ide", "fake")[1] == [
        {"lifecycle": {"script": "fake", "action": "refused", "reason": reason}}
    ]
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "20")[0] == 0


def test_status_notes_two_ides_from_one_install(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    first, second = start(), start()
    code, [event], _ = run(capsys, "status")
    [row] = event["ides"]
    pids = sorted([first.process.pid, second.process.pid])
    assert (code, row["note"].split(";")[0]) == (0, f"2 IDEs run from this install (pids {pids[0]}, {pids[1]})")


@pytest.mark.usefixtures("toolbox")
@pytest.mark.parametrize("command", ["start", "restart"])
def test_start_and_restart_need_the_foreground_opt_in(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    """Both bring the IDE forward, so they act only with --foreground or JETBRAINS_FOREGROUND=1. (Printing the
    --all plan acts on nothing and needs neither: test_all_prints_a_plan_and_acts_only_with_yes.)"""
    monkeypatch.delenv("JETBRAINS_FOREGROUND", raising=False)
    error = f"{command} brings the IDE forward (measured on every launch and restart); pass --foreground or set "
    error += "JETBRAINS_FOREGROUND=1, only with the owner's go"
    assert run(capsys, command, "--ide", "fake") == (1, [], error)


def test_an_ide_without_the_station_plugin_is_not_a_toolbox_ide(
    capsys: pytest.CaptureFixture[str], toolbox: Path
) -> None:
    """Android Studio has no station plugin: no socket to reach it through, so jbctl lists and starts none."""
    solo(toolbox)
    (toolbox / "solo.app/Contents/plugins/station-plugin").rmdir()
    code, [event], _ = run(capsys, "status", "--all")
    assert (code, [row["script"] for row in event["ides"]]) == (0, ["fake", "fake1"])


@needs_jbax
def test_a_launcher_quotes_a_hostile_stand_in_path(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """The stand-in's own launcher is test setup, but its paths are outside text too: a folder named with a quote,
    a dollar sign and a space still starts the stand-in, and nothing in the name is run by the shell."""
    hostile = toolbox / 'st"and $(touch pwned) in'
    hostile.mkdir()
    shutil.copy(Path(__file__).with_name("standin.py"), hostile / "standin.py")
    launcher(toolbox / "fake.app", hostile / "standin.py")
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "fake", "--timeout", "20")
    # The shell would run `touch pwned` in jbctl's working directory.
    assert (code, event["lifecycle"]["action"], Path("pwned").exists()) == (0, "started", False)
    assert run(capsys, "stop", "--ide", "fake", "--timeout", "20")[0] == 0


def test_a_hostile_product_code_stays_out_of_the_lock_path(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """The product code is Toolbox's text: the lock named after it stays in jbctl's lock folder, whatever it holds."""
    solo(toolbox, code="../../../escaped")
    code, [event], _ = run(capsys, "stop", "--ide", "solo")  # takes the locks, then finds nothing running
    assert (code, event["lifecycle"]["reason"].startswith("0 IDEs run from")) == (1, True)
    locks = sorted(path.relative_to(toolbox) for path in toolbox.rglob("*.lock"))
    folder = Path("state/jbctl/lifecycle")
    assert [path.parent for path in locks] == [folder, folder]


@needs_jbax
def test_check_runs_the_guards_and_sends_nothing(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """--check needs no --foreground, even for restart: it reports what would happen and the IDE keeps running."""
    ide = start()
    for command, action in (("stop", "would-stop"), ("restart", "would-restart")):
        checked = {"lifecycle": {"script": "fake", "action": action, "pid": ide.process.pid}}
        assert run(capsys, command, "--ide", "fake", "--check") == (0, [checked], "")
        everything = {"lifecycle": {"script": "fake", "action": action, "pid": ide.process.pid}}
        assert run(capsys, command, "--all", "--check") == (0, [everything], ""), "--all --check runs the guards too"
    assert ide.process.poll() is None


def test_a_relative_project_argument_is_still_an_ide(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """`fake myproj` (a project folder relative to where it started) is an IDE, unlike `fake stdioMcpServer`."""
    ide = start("--no-station", "myproj")
    starting = {"script": "fake", "tool_id": "Fake", "pid": ide.process.pid, "state": "starting"}
    assert run(capsys, "status") == (0, [{"ides": [starting]}], "")


@needs_jbax
def test_a_station_that_hangs_up_is_one_ides_refusal(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    """--all goes on past an IDE whose station closes the connection without an answer."""
    solo(toolbox)
    start("--hangup")
    code, [event], _ = run(capsys, "start", "--foreground", "--ide", "solo", "--timeout", "20")
    assert (code, event["lifecycle"]["action"]) == (0, "started")
    code, events, _ = run(capsys, "stop", "--all", "--yes", "--timeout", "20")
    actions = {e["lifecycle"]["script"]: e["lifecycle"]["action"] for e in events}
    assert (code, actions) == (1, {"fake": "refused", "solo": "stopped"})


@needs_jbax
def test_restart_reports_a_new_ide_that_runs_but_is_not_ready(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """The IDE restarts itself and the new one runs but is not ready in time: restarted-not-ready, exit 75."""
    ide = start("--restart-not-ready")
    code, [event], _ = run(capsys, "restart", "--foreground", "--ide", "fake", "--timeout", "3")
    restarted = event["lifecycle"]
    assert (code, restarted["action"], restarted["previous_pid"]) == (75, "restarted-not-ready", ide.process.pid)
    assert restarted["reason"].startswith(f"pid {restarted['pid']} is still running but was not ready in time")


@needs_jbax
def test_restart_waits_for_an_ide_that_is_not_ready(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """A second restart while the IDE is not ready (perhaps still coming up from the first) refuses, --check too,
    and sends nothing; stop is still allowed."""
    ide = start("--no-about")
    reason = f"pid {ide.process.pid} is not ready yet; wait (jbctl status) or stop it"
    refused = {"lifecycle": {"script": "fake", "action": "refused", "reason": reason}}
    assert run(capsys, "restart", "--foreground", "--ide", "fake") == (1, [refused], "")
    assert run(capsys, "restart", "--ide", "fake", "--check") == (1, [refused], "")
    assert (ide.process.poll(), run(capsys, "stop", "--ide", "fake", "--timeout", "20")[0]) == (None, 0)
