"""hometools roll <step>: the herdr rolling restart, one session at a time, as the roll:<step> mise tasks.

roll:all runs snapshot, update, review, then stop -> start -> verify for each chosen session before it touches the
next. Order: chief-of-staff first when its space is chosen (owner ruling and herdr-startup's order): it records its
background jobs and crons in the run folder, exits, is resumed by name in its own tab
(claude <its own launch flags> --resume chief-of-staff "/herdr-startup rolling"), and roll:all waits for its verify
to pass before it touches any space, since a coordinator that did not come back leaves no one to recover the rest.
Then each space in order, its children before its leads, so no lead restarts while a child it supervises is mid-stop.
One session at a time keeps every other tab working: a failed start leaves one session down, not the whole graph.

roll:all runs in its own herdr tab named roll, with no parent terminal, so it survives chief-of-staff's exit. Every
step without --apply prints its plan and changes nothing. With --apply, each step appends one RollRun line to
~/.local/state/dotfiles/roll/runs.jsonl and writes its output to <run>/<step>.log.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from pydantic import ValidationError

from hometools import nativeclaude
from hometools.models import (
    Background,
    Failure,
    Graph,
    Kind,
    Role,
    RollRun,
    RollStep,
    SessionResult,
)
from hometools.roll import graph as snap
from hometools.roll import review as rev
from hometools.roll import session
from hometools.roll.live import Live, answer, dangling, field, poll, role

UPDATES = ("update:claude", "update:codex", "update:agy", "agents:update")
# Exit codes: a session step that failed, a usage or placement refusal, and the review gate's pause.
FAILED, REFUSED, PAUSED = 1, 2, 3


def state() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "dotfiles/roll"


def baseline() -> Path:
    """The run whose roll:update ran and whose review has not finished: the next snapshot keeps its versions.json, so
    the updates it installed are still reviewed. A finished roll:review --apply of that baseline removes it."""
    return state() / "baseline"


def held() -> tuple[str, str] | None:
    """The baseline run and its versions.json text; None when there is no marker or it names no run with one."""
    run = baseline().read_text().strip() if baseline().is_file() else ""
    kept = state() / run / "versions.json"
    return (run, kept.read_text()) if run and Path(run).name == run and kept.is_file() else None


def names(text: str) -> list[str]:
    return [name.strip() for name in text.split(",") if name.strip()]


def parser() -> argparse.ArgumentParser:
    found = argparse.ArgumentParser(prog="hometools roll")
    found.add_argument("step", type=RollStep, choices=list(RollStep))
    found.add_argument("--sessions", default="all", help="all, or space names separated by commas")
    found.add_argument("--exclude", default="", help="space names left alone, separated by commas")
    found.add_argument("--apply", action="store_true", help="do it; without it the step prints its plan")
    found.add_argument("--run", default=None, help="the run id; default a new one (start and verify: the last stop's)")
    found.add_argument("--wiki", type=Path, default=snap.default_wiki(), help="the chief-of-staff wiki")
    found.add_argument("--prompt", choices=["rolling", "reboot"], default="rolling", help="the resume prompt")
    found.add_argument("--accept-review", action="store_true",
                       help="roll:all goes past a closed review gate; a paused run goes on from roll:stop")  # fmt: skip
    found.add_argument("--wait", type=float, default=900, help="seconds to wait for a stop-point answer")
    found.add_argument("--settle", type=float, default=90, help="seconds to wait for an exit or a start")
    found.add_argument("--poll", type=float, default=1, help="seconds between looks while waiting")
    found.add_argument("--busy-wait", type=float, default=600, help="seconds roll:all waits for a busy chief of staff")
    return found


class Step:
    """One step's run: its folder, its log and the RollRun line it appends."""

    def __init__(self, args: argparse.Namespace, argv: Sequence[str], step: RollStep) -> None:
        self.args, self.argv, self.step = args, list(argv), step
        self.folder = state() / args.run
        self.log = self.folder / f"{step}.log"
        self.start = now()
        self.results: list[SessionResult] = []
        if args.apply:
            self.folder.mkdir(parents=True, exist_ok=True)

    def out(self, line: str) -> None:
        sys.stdout.write(f"{line}\n")
        sys.stdout.flush()
        if self.args.apply:
            with self.log.open("a") as log:
                log.write(f"{line}\n")

    def warn(self, line: str) -> None:
        """Only an applied stop reads prompt boxes (a dry run plans), so the step folder and its log exist."""
        sys.stderr.write(f"{line}\n")
        with self.log.open("a") as log:
            log.write(f"{line}\n")

    def add(self, result: SessionResult) -> SessionResult:
        self.results.append(result)
        self.out(result.model_dump_json())
        return result

    def end(self, rc: int) -> int:
        if self.step is RollStep.stop and (lost := session.no_box_anywhere(self.results)):
            self.warn(f"roll:stop WARNING: no Claude tab showed a prompt box this step can read, so none was restarted "
                      f"({json.dumps(lost)}). Check whether Claude Code changed how it draws the prompt box; roll:stop "
                      "reads it in hometools/roll/session.py draft().")  # fmt: skip
        if self.args.apply:
            line = RollRun(run=self.args.run, step=self.step, args=self.argv, start=self.start, end=now(), rc=rc,
                           log=str(self.log), sessions=self.results)  # fmt: skip
            with (state() / "runs.jsonl").open("a") as runs:
                runs.write(line.model_dump_json() + "\n")
        return rc


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def history() -> list[RollRun]:
    """runs.jsonl's lines; one that is not a RollRun (cut short by a crash, written by hand) is skipped."""
    try:
        text = (state() / "runs.jsonl").read_text()
    except FileNotFoundError:
        return []
    found = []
    for line in text.splitlines():
        try:
            found.append(RollRun.model_validate_json(line))
        except ValidationError:
            continue
    return found


# A step run on its own continues the last run of the steps it follows: update and review the last snapshot (its
# graph and versions), start the last stop (the sessions it stopped), and verify the last stop or start, whichever
# came later: a reboot start with no stop record makes a run of its own, and verify reads its resumed terminals.
FOLLOWS = {
    RollStep.update: {RollStep.snapshot},
    RollStep.review: {RollStep.snapshot},
    RollStep.start: {RollStep.stop},
    RollStep.verify: {RollStep.stop, RollStep.start},
}


def run_id(step: RollStep) -> str:
    """A new run id, or the last run of the steps this one follows."""
    before = [line.run for line in history() if line.step in FOLLOWS.get(step, set())]
    if before:
        return before[-1]
    return f"run-{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%SZ}-{os.getpid()}"


Target = session.Target


class RefusedError(Exception):
    """A step refused before it acted: its message is the one Failure line, its exit code REFUSED."""


def targets(
    graph: Graph, args: argparse.Namespace, me: str | None, *, recover: bool = False
) -> tuple[list[Target], list[Target]]:
    """The chosen agent sessions in roll order, and the live agent sessions left alone. A space or tab kept from the
    previous graph (closed now) is left out, unless recover (a reboot start from a saved graph) and --sessions names
    its space."""
    known = [space.name for space in graph.spaces]
    chosen = names(args.sessions) if args.sessions != "all" else known
    excluded = set(names(args.exclude))
    # A mistyped name would roll everything else, or nothing (restore.py refused one too).
    if unknown := sorted((set(chosen) | excluded) - set(known)):
        msg = f"roll: unknown space(s) {', '.join(unknown)}; the graph has {', '.join(known) or 'none'}"
        raise RefusedError(msg)
    named = set(chosen) if recover and args.sessions != "all" else set()
    agents = [
        (space, tab, term)
        for space in graph.spaces
        if not space.kept_from_previous_graph or space.name in named
        for tab in space.tabs
        if not tab.kept_from_previous_graph or space.name in named
        for term in tab.terminals
        if term.kind is not Kind.shell and term.session and term.address != me
    ]
    picked = [t for t in agents if t[0].name in chosen and t[0].name not in excluded]
    rank = {Role.coordinator: 0, Role.child: 1, Role.lead: 2}

    def order(target: Target) -> tuple[int, int, int]:
        space, tab, _ = target
        first = role(space.name, tab.name) is Role.coordinator
        place = chosen.index(space.name) if space.name in chosen else len(chosen)
        return (0 if first else 1, place, rank[role(space.name, tab.name)])

    return sorted(picked, key=order), [t for t in agents if t not in picked]


def excluded(left: list[Target], args: argparse.Namespace) -> list[Target]:
    """The sessions --exclude kept out of the chosen spaces: verify checks them untouched. A space --sessions did
    not choose is out of the run's scope, as in every other step, and is not reported."""
    chosen = set(names(args.sessions))
    return [t for t in left if args.sessions == "all" or t[0].name in chosen]


def timing(args: argparse.Namespace) -> session.Timing:
    return session.Timing(wait=args.wait, settle=args.settle, interval=args.poll)


def run_graph(step: Step) -> Graph:
    """The run's graph from its snapshot, else the live one merged with the wiki's last graph, as roll:snapshot merges
    it: a standalone roll:stop saves this to its run, and a reboot start after it still finds the closed projects."""
    saved = step.folder / "graph.json"
    if saved.exists():
        return Graph.model_validate_json(saved.read_text())
    return snap.merge(snap.build(Live(), step.args.wiki), snap.previous(step.args.wiki / "sessions/graph.json"))


def do_snapshot(step: Step) -> int:
    me = os.environ.get("HC_TERMINAL_ID")
    # The names are checked against the new graph before anything is written.
    graph, report = snap.snapshot(
        Live(), step.args.wiki, apply=step.args.apply, copy_to=step.folder / "graph.json",
        check=lambda made: targets(made, step.args, me),
    )  # fmt: skip
    if step.args.apply:
        if kept := held():
            (step.folder / "versions.json").write_text(kept[1])
            step.out(f"versions.json: {kept[0]}'s, kept since its review did not finish")
        else:
            (step.folder / "versions.json").write_text(rev.collect().model_dump_json(indent=1) + "\n")
    step.out(report.model_dump_json())
    picked, left = targets(graph, step.args, me)
    step.out(f"chosen: {', '.join(f'{s.name} / {t.name} ({x.address})' for s, t, x in picked) or 'none'}")
    step.out(f"left alone: {', '.join(f'{s.name} / {t.name} ({x.address})' for s, t, x in left) or 'none'}")
    return 0


def kept_opencode(graph: Graph, args: argparse.Namespace) -> list[str]:
    """Each live OpenCode terminal the roll does not restart: one outside the chosen spaces or excluded, one whose
    session id the snapshot did not find, or the caller's own. agents:update would replace the binary under it. A
    space or tab kept from the previous graph is closed: nothing runs there."""
    picked, _ = targets(graph, args, os.environ.get("HC_TERMINAL_ID"))
    rolled = {term.address for _, _, term in picked}
    return [
        f"{space.name} / {tab.name} ({term.address})"
        for space in graph.spaces
        if not space.kept_from_previous_graph
        for tab in space.tabs
        if not tab.kept_from_previous_graph
        for term in tab.terminals
        if term.kind is Kind.opencode and term.address not in rolled
    ]


def do_update(step: Step) -> int:
    """The existing global update tasks. agents:update (the OpenCode update; update:claude, update:codex and
    update:agy update the rest) is left out while an OpenCode session the roll does not restart runs."""
    kept = kept_opencode(run_graph(step), step.args)
    env = os.environ | {"MISE_TASK_TIMINGS": "1", "MISE_TASK_OUTPUT": "prefix"}
    # Reported in the plan and the run, not a stop: the restart itself does not need those links.
    step.out(dangling().model_dump_json())
    rc = 0
    # A held baseline stays until a run that inherited it (its versions.json is the held one) takes it over.
    base, mine = held(), step.folder / "versions.json"
    if step.args.apply and (base is None or (mine.is_file() and mine.read_text() == base[1])):
        snap.write(baseline(), f"{step.args.run}\n")
    for task in UPDATES:
        argv = ["mise", "run", task]
        if kept and task == "agents:update":
            step.out(f"skipped: {' '.join(argv)}, since OpenCode keeps running in {', '.join(kept)}")
            continue
        if not step.args.apply:
            step.out(f"planned: {' '.join(argv)}")
            continue
        step.out(f"$ {' '.join(argv)}")
        for line, code in stream(argv, env):
            if line is not None:
                step.out(line)
            elif code:
                step.out(f"{task} exited {code}")
                rc = rc or FAILED
    return rc


def stream(argv: list[str], env: dict[str, str]) -> Iterator[tuple[str | None, int]]:
    """argv's output lines as they come, then (None, its exit code); 127 when it can't start."""
    try:
        with subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
            for line in proc.stdout or []:
                yield line.rstrip("\n"), 0
    except OSError as failed:
        yield f"{argv[0]}: {failed.strerror}", 0
        yield None, 127
        return
    yield None, proc.returncode


def do_review(step: Step) -> int:
    if step.args.apply and not (step.folder / "versions.json").exists():
        why = f"roll:review: {step.folder} has no versions.json; run roll:snapshot --apply first"
        sys.stderr.write(Failure(error=why).model_dump_json() + "\n")
        return FAILED
    cache = state() / rev.CACHE
    report = rev.review(step.folder, cache, step.args.wiki, apply=step.args.apply)
    # Only a review against the marked baseline clears it: a review of another run leaves those updates unreviewed.
    if step.args.apply and ((kept := held()) is None or kept[1] == (step.folder / "versions.json").read_text()):
        baseline().unlink(missing_ok=True)
    step.out(report.model_dump_json())
    return 0


def do_stop(step: Step) -> int:
    live = Live()
    graph = run_graph(step)
    keep = step.folder if step.args.apply else None
    if keep:
        # roll:start resumes from this graph: after /exit the live one shows only shells.
        snap.write(keep / "graph.json", graph.model_dump_json(indent=2, exclude_unset=True))
    picked, _ = targets(graph, step.args, live.me)
    for target in picked:
        step.add(session.stop(live, target, timing(step.args), keep, codeset(target, apply=step.args.apply)))
    return failed(step)


def stopped(step: Step, result: str = "stopped") -> set[str]:
    """The terminals of the sessions this run's stop left with result: stopped (roll:start resumes them) or restarted
    (/restart restarted them in place)."""
    return {r.terminal for line in history() if line.run == step.args.run and line.step is RollStep.stop
            for r in line.sessions if r.result == result}  # fmt: skip


def saved_graph(step: Step) -> Graph:
    """For a reboot start: the run's graph, else the one roll:snapshot --apply left in the wiki. The live layout
    after a reboot shows nothing to resume."""
    for path in (step.folder / "graph.json", step.args.wiki / "sessions/graph.json"):
        if path.exists():
            return Graph.model_validate_json(path.read_text())
    msg = f"roll:start --prompt reboot: no saved graph in {step.folder} or {step.args.wiki / 'sessions'}"
    raise snap.GraphError(msg)


def do_start(step: Step) -> int:
    """Rolling: resume the sessions this run's stop stopped. Reboot: resume every chosen session of the saved graph,
    stopped or not, since the reboot ended them all (one skipped as already current included)."""
    me = os.environ.get("HC_TERMINAL_ID")
    if step.args.prompt == "reboot":
        picked, _ = targets(saved_graph(step), step.args, me, recover=True)
        for target in picked:
            step.add(session.start(target, timing(step.args), apply=step.args.apply, prompt=session.REBOOT))
        return failed(step)
    picked, _ = targets(run_graph(step), step.args, me)
    done = stopped(step)
    if step.args.apply and not done and not stopped(step, "restarted"):
        msg = f"roll:start: run {step.args.run} stopped no session; run roll:stop --apply first, or pass --run"
        raise RefusedError(msg)
    for target in picked:
        if step.args.apply and target[2].address not in done:
            continue
        step.add(session.start(target, timing(step.args), apply=step.args.apply, prompt=session.ROLLING))
    return failed(step)


def codeset(target: Target | None = None, *, apply: bool) -> dt.datetime | None:
    """When the plugin code set the target session loads last changed: a hash of its plugin records (user scope, plus
    project and local scope for its own folder; user scope alone with no target), enabled plugins and plugin configs,
    remembered when first seen (installed_plugins.json's own times move on every start)."""
    home = Path.home()
    # A session loads the project and local plugins installed for its own folder, not another project's.
    folder = (target[2].cwd or target[0].folder) if target else None
    parts = [f"{name}|{plugin}" for name, plugin in sorted(rev.plugins(folder, every=False).items())]
    settings = rev.load(home / ".claude/settings.json")
    parts += [repr(settings.get("enabledPlugins")), repr(settings.get("pluginConfigs"))]
    # Inline mods a session loads from CLAUDE_CODE_PLUGIN_DIRS (side-notes, you-should-know-forward): their
    # .claude-plugin/plugin.json changes on every install (the old checks.py hashed them too).
    dirs = field(settings, "env", "CLAUDE_CODE_PLUGIN_DIRS")
    for folder in str(dirs).split(":") if isinstance(dirs, str) else []:
        manifest = Path(folder) / ".claude-plugin/plugin.json"
        if folder and manifest.is_file():
            parts.append(f"{folder}|{hashlib.sha256(manifest.read_bytes()).hexdigest()}")
    key = hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
    seen_file = state() / "codeset.json"
    seen = {str(k): str(v) for k, v in rev.load(seen_file).items()}
    if key not in seen:
        seen[key] = dt.datetime.now().isoformat(timespec="seconds")  # noqa: DTZ005 - compared with ps's local time
        if apply:
            seen_file.parent.mkdir(parents=True, exist_ok=True)
            seen_file.write_text(json.dumps(seen, indent=1))
    return dt.datetime.fromisoformat(seen[key])


def do_verify(step: Step) -> int:
    """Rolling: the sessions this run stopped (every chosen one when it stopped none), and the rest untouched.
    Reboot: every session the reboot start resumed from the saved graph; after a reboot no pid is the same, so
    nothing is checked as untouched."""
    live = Live()
    if step.args.prompt == "reboot":
        picked, left = targets(saved_graph(step), step.args, live.me, recover=True)
        left, done, again = [], set(), set()
    else:
        picked, left = targets(run_graph(step), step.args, live.me)
        again = stopped(step, "restarted")
        done = stopped(step) | again
    moved = resumed_in(step)
    for target in picked:
        if done and target[2].address not in done:
            continue
        address = moved.get(str(target[2].session))
        mark = codeset(target, apply=step.args.apply)
        found = session.verify(
            target, mark, session.screen, before(step, target), address, restarted=target[2].address in again
        )
        step.add(found)
    for target in excluded(left, step.args):
        step.add(session.untouched(target, live))
    links = dangling()
    step.out(links.model_dump_json())
    return failed(step) or (FAILED if links.dangling else 0)


def before(step: Step, target: Target) -> str | None:
    """The worktree git status roll:stop recorded for the session in this run; None when it recorded none, or when
    the receipt is another session's."""
    try:
        record = Background.model_validate_json(session.kept(step.folder, target).read_text())
    except FileNotFoundError:
        return None
    term = target[2]
    return record.worktree if (record.session, record.terminal) == (term.session, term.address) else None


def resumed_in(step: Step) -> dict[str, str]:
    """session id -> the terminal this run's start resumed it in (a new tab has a new address; one tab can hold
    several sessions)."""
    starts = [line for line in history() if line.run == step.args.run and line.step is RollStep.start]
    return {str(r.session): r.terminal for line in starts for r in line.sessions if r.result == "started"}


def failed(step: Step) -> int:
    return FAILED if any(r.result.startswith("failed-") for r in step.results) else 0


STEPS: dict[RollStep, Callable[[Step], int]] = {
    RollStep.snapshot: do_snapshot,
    RollStep.update: do_update,
    RollStep.review: do_review,
    RollStep.stop: do_stop,
    RollStep.start: do_start,
    RollStep.verify: do_verify,
}


def placed(argv: Sequence[str]) -> str | None:
    """Why roll:all may not run here: it needs its own tab named roll with no parent terminal.

    The command it prints carries the caller's own arguments, so pasting it rolls the same sessions.
    """
    me = os.environ.get("HC_TERMINAL_ID")
    info = answer("hc", "get", me, "--json") if me else {}
    where = str(field(info, "labels", "where") or "")
    if where.rpartition(" / ")[2] == "roll" and field(info, "parent") is None:
        return None
    flags = list(argv[1:] if argv[:1] == [RollStep.all.value] else argv)
    command = ["env", "MISE_TASK_TIMINGS=1", "MISE_TASK_OUTPUT=prefix", "mise", "run", "roll:all", *flags]
    return (
        "roll:all --apply runs only in its own herdr tab named roll, not as a child of chief-of-staff; open one with "
        "herdr-app do tab.new --space <space id> --name roll --folder ~ --argv "
        + shlex.quote(json.dumps(command, separators=(",", ":")))
    )


def do_all(args: argparse.Namespace, argv: Sequence[str]) -> int:
    # A paused run holds until the owner accepts its review: a new snapshot would take the updated versions as its
    # baseline, find nothing changed and open the gate. Accepted, it goes on from roll:stop with its own snapshot.
    paused = state() / "paused"
    held = paused.read_text().strip() if args.apply and paused.is_file() else None
    if args.apply and (why := placed(argv) or orphaned(paused, held)):
        sys.stderr.write(Failure(error=why).model_dump_json() + "\n")
        return REFUSED
    if held is not None:
        args.run = held
        if not args.accept_review:
            return pause(state() / args.run / "review.md")
        paused.unlink()
        return roll(args, argv)
    for kind in (RollStep.snapshot, RollStep.update, RollStep.review):
        step = Step(args, argv, kind)
        if rc := step.end(STEPS[kind](step)):
            return rc
    gate = state() / args.run / "review.md"
    if args.apply and not args.accept_review and "Gate: CLOSED" in gate.read_text():
        snap.write(paused, f"{args.run}\n")
        return pause(gate)
    return roll(args, argv)


def orphaned(paused: Path, run: str | None) -> str | None:
    """Why the paused marker can't be continued: a run id that is empty or a path would make the state folder (or
    another) the run folder, and roll:stop would build a live graph instead of reading the paused snapshot."""
    if run is None or (run and Path(run).name == run and (state() / run / "graph.json").is_file()):
        return None
    return f"roll:all: {paused} names no run with a snapshot ({run!r}); delete it and rerun"


def pause(gate: Path) -> int:
    # The way out of a paused run the owner will not finish (its graph is from its snapshot) is named with it.
    why = (f"roll:all paused before roll:stop: read {gate}, then rerun with --accept-review; to drop this run "
           f"instead, delete {state() / 'paused'} and rerun")  # fmt: skip
    sys.stderr.write(Failure(error=why).model_dump_json() + "\n")
    return PAUSED


def roll(args: argparse.Namespace, argv: Sequence[str]) -> int:
    """stop -> start -> verify per session; a coordinator that fails verify stops the run."""
    stop, start, check = (Step(args, argv, kind) for kind in (RollStep.stop, RollStep.start, RollStep.verify))
    live = Live()
    graph = run_graph(stop)
    picked, left = targets(graph, args, live.me)
    prompt = session.ROLLING if args.prompt == "rolling" else session.REBOOT
    rc = 0
    # The run log is written even when an error or Ctrl-C ends the loop, so roll:start finds what was stopped.
    try:
        for target in picked:
            coordinator = role(target[0].name, target[1].name) is Role.coordinator
            # Nothing else moves until the chief of staff is back and verified: its stop waits while it is busy (up to
            # --busy-wait). A skipped child or lead is listed to retry later; it fails nothing.
            mark = codeset(target, apply=args.apply)
            if not one(target, (stop, start, check), live, mark, prompt) and coordinator and args.apply:
                rc = FAILED
                break
        for target in excluded(left, args):
            check.add(session.untouched(target, Live()))
        links = dangling()
        check.out(links.model_dump_json())
        rc = rc or failed(stop) or failed(start) or failed(check) or (FAILED if links.dangling else 0)
    finally:
        stop.end(failed(stop))
        start.end(failed(start))
        check.end(failed(check))
    return rc


def one(
    target: session.Target, steps: tuple[Step, Step, Step], live: Live, mark: dt.datetime | None, prompt: str
) -> bool:
    """stop, start and verify one session; True when it is back and current (or, on a dry run, planned)."""
    stop, start, check = steps
    args = stop.args
    wait = args.apply and role(target[0].name, target[1].name) is Role.coordinator
    down = stop.add(stopping(stop, live, target, mark, wait=wait))
    if down.result in {"skipped-already-current", "planned-restart"}:
        return True
    restarted = down.result == "restarted"
    if not restarted and down.result not in {"stopped", "planned"}:
        return False
    # /restart restarted it in its own terminal: nothing to start.
    up = None if restarted else start.add(session.start(target, timing(args), apply=args.apply, prompt=prompt))
    if not args.apply:
        return True

    # The resumed session takes a moment to load and take its prompt: look until it passes or settle ends.
    was, address = before(stop, target), up.terminal if up else None

    def look() -> SessionResult:
        return session.verify(target, mark, session.screen, was, address, restarted=restarted)

    def passed() -> SessionResult | None:
        found = look()
        return found if found.result == "ok" else None

    last = poll(passed, args.settle, args.poll) or look()
    return check.add(last).result == "ok" and (up is None or up.result == "started")


def stopping(stop: Step, live: Live, target: session.Target, mark: dt.datetime | None, *, wait: bool) -> SessionResult:
    """session.stop; with wait (the chief of staff, which is rarely idle while it relays), a skipped-busy session is
    asked again about 60 times over --busy-wait (never more often than --poll). A busy attempt changes nothing, so
    only the last one is recorded, with how long it waited. Each attempt reads the processes fresh: a background job
    may have ended."""
    args = stop.args
    keep = stop.folder if args.apply else None
    began, seen = time.monotonic(), list[SessionResult]()

    def free() -> SessionResult | None:
        seen.append(session.stop(Live() if seen else live, target, timing(args), keep, mark))
        return None if wait and seen[-1].result == "skipped-busy" else seen[-1]

    # About 60 looks over the bound (10 s apart at the default 600 s): each look reads hc and the process table.
    last = poll(free, args.busy_wait if wait else 0, max(args.poll, args.busy_wait / 60)) or seen[-1]
    if seen[0].result != "skipped-busy" or not wait:
        return last
    waited = f"waited {time.monotonic() - began:.0f}s while busy ({len(seen)} looks)"
    return last.model_copy(update={"notes": [*last.notes, waited]})


def main(argv: Sequence[str]) -> int:
    """The step's exit code."""
    args = parser().parse_args(argv)
    args.run = args.run or run_id(args.step)
    # A start resumes each Claude session with plain `claude`, which a stray npm copy in a mise node would win.
    if args.apply and args.step in {RollStep.all, RollStep.start} and (stray := nativeclaude.stray(Path.home())):
        return refused(RefusedError(f"roll: Claude Code outside its native install at {stray[0]}; run claude:doctor"))
    if args.step is RollStep.all:
        try:
            return do_all(args, argv)
        except (RefusedError, snap.GraphError) as stopped_early:
            return refused(stopped_early)
    step = Step(args, argv, args.step)
    # The run line is written however the step ends, a Ctrl-C included: roll:start reads which sessions stopped.
    rc = FAILED
    try:
        rc = STEPS[args.step](step)
    except (RefusedError, snap.GraphError) as stopped_early:
        rc = refused(stopped_early)
    finally:
        step.end(rc)
    return rc


def refused(error: Exception) -> int:
    sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
    return REFUSED if isinstance(error, RefusedError) else FAILED
