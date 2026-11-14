"""hometools roll <step>: the herdr rolling restart, one session at a time, as the roll:<step> mise tasks.

roll:all runs snapshot, update, review, then stop -> start -> verify for each chosen session before it touches the
next. Order: chief-of-staff first when its space is chosen (owner ruling and herdr-startup's order): it records its
background jobs and crons in the run folder, exits, is resumed by name in its own tab
(claude --permission-mode auto --resume chief-of-staff "/herdr-startup rolling"), and roll:all waits for its verify
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
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from pydantic import ValidationError

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
    found.add_argument("--accept-review", action="store_true", help="roll:all goes past a closed review gate")
    found.add_argument("--wait", type=float, default=900, help="seconds to wait for a stop-point answer")
    found.add_argument("--settle", type=float, default=90, help="seconds to wait for an exit or a start")
    found.add_argument("--poll", type=float, default=1, help="seconds between looks while waiting")
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

    def add(self, result: SessionResult) -> SessionResult:
        self.results.append(result)
        self.out(result.model_dump_json())
        return result

    def end(self, rc: int) -> int:
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
        (step.folder / "versions.json").write_text(rev.collect().model_dump_json(indent=1) + "\n")
    step.out(report.model_dump_json())
    picked, left = targets(graph, step.args, me)
    step.out(f"chosen: {', '.join(f'{s.name} / {t.name} ({x.address})' for s, t, x in picked) or 'none'}")
    step.out(f"left alone: {', '.join(f'{s.name} / {t.name} ({x.address})' for s, t, x in left) or 'none'}")
    return 0


def do_update(step: Step) -> int:
    """The existing global update tasks; agents:update skips OpenCode while an excluded OpenCode session runs."""
    _, left = targets(run_graph(step), step.args, os.environ.get("HC_TERMINAL_ID"))
    skip = ["--skip", "opencode"] if any(term.kind is Kind.opencode for _, _, term in left) else []
    env = os.environ | {"MISE_TASK_TIMINGS": "1", "MISE_TASK_OUTPUT": "prefix"}
    # Reported in the plan and the run, not a stop: the restart itself does not need those links.
    step.out(dangling().model_dump_json())
    rc = 0
    for task in UPDATES:
        argv = ["mise", "run", task, *(skip if task == "agents:update" else [])]
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
    cache = state() / "review-cache"
    report = rev.review(step.folder, cache, step.args.wiki, apply=step.args.apply)
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
    mark = codeset(apply=step.args.apply)
    for target in picked:
        step.add(session.stop(live, target, timing(step.args), keep, mark))
    return failed(step)


def stopped(step: Step) -> set[str]:
    return {r.terminal for line in history() if line.run == step.args.run and line.step is RollStep.stop
            for r in line.sessions if r.result == "stopped"}  # fmt: skip


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
    if step.args.apply and not done:
        msg = f"roll:start: run {step.args.run} stopped no session; run roll:stop --apply first, or pass --run"
        raise RefusedError(msg)
    for target in picked:
        if step.args.apply and target[2].address not in done:
            continue
        step.add(session.start(target, timing(step.args), apply=step.args.apply, prompt=session.ROLLING))
    return failed(step)


def codeset(*, apply: bool) -> dt.datetime | None:
    """When the plugin code set a session loads last changed: a hash of the user-scope plugin records, enabled
    plugins and plugin configs, remembered when first seen (installed_plugins.json's own times move on every start)."""
    home = Path.home()
    parts = [f"{name}|{plugin}" for name, plugin in sorted(rev.user_plugins().items())]
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
        left, done = [], set()
    else:
        picked, left = targets(run_graph(step), step.args, live.me)
        done = stopped(step)
    mark = codeset(apply=step.args.apply)
    moved = resumed_in(step)
    for target in picked:
        if done and target[2].address not in done:
            continue
        address = moved.get(str(target[2].session))
        step.add(session.verify(target, mark, session.screen, before(step, target), address))
    for target in left:
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


def placed() -> str | None:
    """Why roll:all may not run here: it needs its own tab named roll with no parent terminal."""
    me = os.environ.get("HC_TERMINAL_ID")
    info = answer("hc", "get", me, "--json") if me else {}
    where = str(field(info, "labels", "where") or "")
    if where.rpartition(" / ")[2] == "roll" and field(info, "parent") is None:
        return None
    return (
        "roll:all --apply runs only in its own herdr tab named roll, not as a child of chief-of-staff; open one with "
        "herdr-app do tab.new --space <space id> --name roll --folder ~ --argv "
        """'["env","MISE_TASK_TIMINGS=1","MISE_TASK_OUTPUT=prefix","mise","run","roll:all","--apply"]'"""
    )


def do_all(args: argparse.Namespace, argv: Sequence[str]) -> int:
    if args.apply and (why := placed()):
        sys.stderr.write(Failure(error=why).model_dump_json() + "\n")
        return REFUSED
    for kind in (RollStep.snapshot, RollStep.update, RollStep.review):
        step = Step(args, argv, kind)
        if rc := step.end(STEPS[kind](step)):
            return rc
    gate = state() / args.run / "review.md"
    if args.apply and not args.accept_review and "Gate: CLOSED" in gate.read_text():
        sys.stderr.write(Failure(error=f"roll:all paused before roll:stop: read {gate}, then rerun with "
                                 "--accept-review").model_dump_json() + "\n")  # fmt: skip
        return PAUSED
    return roll(args, argv)


def roll(args: argparse.Namespace, argv: Sequence[str]) -> int:
    """stop -> start -> verify per session; a coordinator that fails verify stops the run."""
    stop, start, check = (Step(args, argv, kind) for kind in (RollStep.stop, RollStep.start, RollStep.verify))
    live = Live()
    graph = run_graph(stop)
    picked, left = targets(graph, args, live.me)
    prompt = session.ROLLING if args.prompt == "rolling" else session.REBOOT
    mark = codeset(apply=args.apply)
    rc = 0
    # The run log is written even when an error or Ctrl-C ends the loop, so roll:start finds what was stopped.
    try:
        for target in picked:
            coordinator = role(target[0].name, target[1].name) is Role.coordinator
            # Nothing else moves until the chief of staff is back and verified. A skipped child or lead is listed
            # to retry later; it fails nothing.
            if not one(target, (stop, start, check), live, mark, prompt) and coordinator and args.apply:
                rc = FAILED
                break
        for target in left:
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
    down = stop.add(session.stop(live, target, timing(args), stop.folder if args.apply else None, mark))
    if down.result == "skipped-already-current":
        return True
    if down.result not in {"stopped", "planned"}:
        return False
    up = start.add(session.start(target, timing(args), apply=args.apply, prompt=prompt))
    if not args.apply:
        return True

    # The resumed session takes a moment to load and take its prompt: look until it passes or settle ends.
    was = before(stop, target)

    def passed() -> SessionResult | None:
        found = session.verify(target, mark, session.screen, was, up.terminal)
        return found if found.result == "ok" else None

    last = poll(passed, args.settle, args.poll) or session.verify(target, mark, session.screen, was, up.terminal)
    return check.add(last).result == "ok" and up.result == "started"


def main(argv: Sequence[str]) -> int:
    """The step's exit code."""
    args = parser().parse_args(argv)
    args.run = args.run or run_id(args.step)
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
