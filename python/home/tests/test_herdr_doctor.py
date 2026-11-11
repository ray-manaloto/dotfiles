"""herdr-doctor on a scratch home: each input it reads, healthy, broken alone, and unreadable."""

# The doctor's readers run for real wherever a test can own what they read: lsof on Unix sockets this test holds,
# ps and the kernel's environment copy on processes it starts, the sandboxed login shell (/bin/zsh -lic) on the
# scratch home's startup files, and git on a scratch repository. pgrep and launchctl getenv read this Mac's whole
# process table and launchd session, which hold the real herdr-core and Herdr.app and can't be set from a test, so
# tests/stand_in.py answers them (CODING_STANDARDS 2): a real pgrep would also find this Mac's own core and app, and
# the only way to set a launchd variable, launchctl setenv, changes the owner's GUI session. The pid pgrep answers
# for the core is this test's own: it holds the default socket. The home sits under /tmp: macOS caps a socket path
# at 104 bytes.

import json
import os
import plistlib
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from hometools import herdr
from hometools.cli import main
from hometools.models import Checks, Observation

STAND_IN = Path(__file__).with_name("stand_in.py")
CORE = os.getpid()
HC = "0.1.18"
ALL_PASS = dict.fromkeys(("V1", "V2", "V3", "V4", "V5", "V7", "V10", "V11", "V15"), "pass")
# ps -o lstart=, as in "Wed Nov  4 09:00:13 2026".
LSTART = re.compile(r"\w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d \d{4}")
# The retired names, split so this file's own text stays plain; the allowlist names this file by path anyway.
MARKETPLACE = "claude-code-" + "marketplace"


class Scratch:
    """A home where herdr-core is healthy: this test holds the default socket and is the core, a child process is
    the app, and a clean repository."""

    def __init__(self, home: Path, stand_in: Path, repo: Path) -> None:
        self.home, self.stand_in, self.repo = home, stand_in, repo
        self.answers: dict[str, dict[str, object]] = {}
        self.sock = home / herdr.DEFAULT_SOCKET
        self.held: list[socket.socket] = []
        self.children: list[subprocess.Popen[bytes]] = []
        self.write(".zshrc", "")  # Any startup file keeps zsh from starting its new-user menu.
        self.reply(["pgrep", "-a", "-f", herdr.CORE], stdout=f"{CORE}\n")
        self.app = self.start({"PATH": "/usr/bin", "HOME": "/h"})
        for name in herdr.ROUTING:
            self.reply(["launchctl", "getenv", name])

    def reply(self, argv: list[str], **answer: object) -> None:
        self.answers[json.dumps(argv)] = answer

    def hold(self, path: Path) -> socket.socket:
        """A listening Unix socket at path, held by this test."""
        path.parent.mkdir(parents=True, exist_ok=True)
        held = socket.socket(socket.AF_UNIX)
        held.bind(str(path))
        held.listen()
        self.held.append(held)
        return held

    def start(self, env: dict[str, str], *, fds: tuple[int, ...] = (), program: tuple[str, ...] = ()) -> int:
        """A process that waits, with env as its whole environment; pgrep answers it as the app."""
        argv = program or (sys.executable, "-c", "import time; time.sleep(600)")
        child = subprocess.Popen(argv, env=env, pass_fds=fds)
        self.children.append(child)
        self.reply(["pgrep", "-a", "-x", "Herdr"], stdout=f"{child.pid}\n")
        return child.pid

    def gone(self) -> int:
        """The pid of a process that has ended and been reaped."""
        child = subprocess.Popen(["/usr/bin/true"])
        child.wait()
        return child.pid

    def write(self, path: str, text: str) -> Path:
        target = self.home / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def plist(self, path: str, data: dict[str, str]) -> None:
        target = self.home / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(plistlib.dumps(data))

    def lock(self, skills: object) -> None:
        self.write(".local/state/skills/.skill-lock.json", json.dumps({"version": 3, "skills": skills}))

    def observe(self) -> tuple[Observation, Checks]:
        (self.stand_in / "script.json").write_text(json.dumps(self.answers))
        seen = herdr.observe(self.home, self.repo)
        return seen, herdr.judge(seen)

    def checks(self) -> dict[str, str]:
        return self.observe()[1].model_dump()

    def close(self) -> None:
        for held in self.held:
            held.close()
        for child in self.children:
            child.kill()
            child.wait()


def failing(*failed: str, result: str = "fail") -> dict[str, str]:
    """ALL_PASS with failed set to result: what checks() must equal."""
    return ALL_PASS | dict.fromkeys(failed, result)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@e", *args], check=True)


@pytest.fixture
def scratch(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Scratch]:
    if sys.platform != "darwin":
        pytest.skip("herdr-core and Herdr.app run on macOS")
    # Resolved: lsof matches a Unix socket by the path it was bound with, and /tmp is a link to /private/tmp.
    home = Path(tempfile.mkdtemp(prefix=getattr(request, "param", "hd"), dir="/tmp")).resolve()
    stand_in = tmp_path / "stand-in"
    stand_in.mkdir()
    for name in ("pgrep", "launchctl"):
        (stand_in / name).symlink_to(STAND_IN)
    monkeypatch.setenv("PATH", f"{stand_in}:{os.environ['PATH']}")
    monkeypatch.setenv("STAND_IN", str(stand_in))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local/state"))
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", str(repo))
    (repo / "README.md").write_text("Nothing retired here.\n")
    git(repo, "add", "README.md")
    s = Scratch(home, stand_in, repo)
    try:
        s.write(herdr.LOCK, f"{s.sock}\n")
        s.plist(herdr.HC_PLIST, {"CFBundleShortVersionString": HC})
        s.plist(herdr.APP_PLIST, {"CFBundleShortVersionString": "0.1.13"})
        for folder in herdr.SKILLS:
            s.write(f"{folder}/SKILL.md", "---\nname: herdr-core\n---\n")
        s.lock({"herdr-core": {"ref": f"v{HC}"}})
        s.hold(s.sock)
        yield s
    finally:
        s.close()
        shutil.rmtree(home)


def test_a_healthy_core_passes_every_check(scratch: Scratch) -> None:
    seen, checks = scratch.observe()
    assert checks.model_dump() == ALL_PASS
    assert herdr.code(checks) == 0
    assert LSTART.fullmatch(seen.core_started or "")
    assert seen.model_dump() | {"core_started": None} == {
        "hc": HC,
        "app": "0.1.13",
        "skill_tag": f"v{HC}",
        "skills_missing": [],
        "cores": [CORE],
        "listeners": [CORE],
        "lock_path": f"~/{herdr.DEFAULT_SOCKET}",
        "core_started": None,
        "old_path_holders": [],
        "windows": [{"pid": scratch.app, "hc_socket": None}],
        "routing": [],
        "references": [],
        "guard": [],
        "unchanged": True,
        "unknown": [],
    }


def test_the_cli_prints_one_json_line_and_exits_with_the_checks(
    scratch: Scratch, capfd: pytest.CaptureFixture[str]
) -> None:
    # The command reads this checkout for V11; the rest comes from the scratch home, whose login shell sets a
    # hostile value: quotes, a backslash and a newline that looks like a probe record must come out as one JSON value.
    hostile = 'a "b" \\c\nherdr-doctor-end'
    scratch.write(".zshrc", "export HC_SESSION=$'a \"b\" \\\\c\\nherdr-doctor-end'\n")
    (scratch.stand_in / "script.json").write_text(json.dumps(scratch.answers))
    with pytest.raises(SystemExit) as stop:
        main(["herdr-doctor"])
    out, err = capfd.readouterr()
    (line,) = out.splitlines()
    report = json.loads(line)
    assert err == ""
    assert report["observation"]["routing"] == [{"where": "login-shell", "name": "HC_SESSION", "value": hostile}]
    assert report["checks"] | {"V11": "fail"} == failing("V2", "V11")
    assert stop.value.code == 1


# V3 and V4: the default socket's holder, the cores, core.lock and the core's start time.


def test_no_socket_at_the_default_path_fails_v3_and_v4(scratch: Scratch) -> None:
    scratch.sock.unlink()
    assert scratch.checks() == failing("V3", "V4")


def test_a_file_that_is_not_a_socket_fails_v3_and_v4(scratch: Scratch) -> None:
    scratch.sock.unlink()
    scratch.sock.write_text("")
    assert scratch.checks() == failing("V3", "V4")


def test_two_holders_of_the_default_socket_fail_v3_and_v4(scratch: Scratch) -> None:
    # The app's process also holds it: the second holder.
    other = scratch.start({"PATH": "/usr/bin"}, fds=(scratch.held[0].fileno(),))
    seen, checks = scratch.observe()
    assert seen.listeners == sorted([CORE, other])
    assert checks.model_dump() == failing("V3", "V4")


def test_a_socket_nothing_holds_fails_v3_and_v4(scratch: Scratch) -> None:
    scratch.held[0].close()  # The file stays; no process has it open.
    seen, checks = scratch.observe()
    assert (seen.listeners, seen.unknown) == ([], [])
    assert checks.model_dump() == failing("V3", "V4")


@pytest.mark.parametrize("cores", [[], [CORE, 1]], ids=["no core", "two cores"])
def test_zero_or_two_cores_fail_v4(scratch: Scratch, cores: list[int]) -> None:
    scratch.reply(
        ["pgrep", "-a", "-f", herdr.CORE], stdout="".join(f"{pid}\n" for pid in cores), code=0 if cores else 1
    )
    seen, checks = scratch.observe()
    assert (seen.cores, seen.core_started) == (sorted(cores), None)
    assert checks.model_dump() == failing("V4")


def test_a_core_that_is_not_the_listener_fails_v4(scratch: Scratch) -> None:
    scratch.reply(["pgrep", "-a", "-f", herdr.CORE], stdout=f"{scratch.app}\n")
    seen, checks = scratch.observe()
    assert LSTART.fullmatch(seen.core_started or "")
    assert checks.model_dump() == failing("V4")


def test_pgrep_failing_makes_v4_and_v15_unknown(scratch: Scratch) -> None:
    scratch.reply(["pgrep", "-a", "-f", herdr.CORE], code=3, stderr="pgrep: sysctl\n")
    seen, checks = scratch.observe()
    assert seen.unknown == ["cores"]
    # A failed pgrep is no core count: V4 and V15 can't be judged, never failed (pane review 1).
    assert checks.model_dump() == failing("V4", "V15", result="unknown")
    assert herdr.code(checks) == 3


def test_a_core_gone_before_its_start_time_is_read(scratch: Scratch) -> None:
    scratch.reply(["pgrep", "-a", "-f", herdr.CORE], stdout=f"{scratch.gone()}\n")
    seen, checks = scratch.observe()
    assert (seen.core_started, seen.unknown) == (None, ["core-started"])
    # Gone, it is not the listener either: V4 fails on what was read.
    assert checks.model_dump() == failing("V4")


@pytest.mark.parametrize(
    ("text", "lock_path"),
    [("~/.local/run/herdr-core/default.sock", "~/.local/run/herdr-core/default.sock"), (None, None)],
    ids=["old path", "missing"],
)
def test_core_lock_naming_another_socket_or_missing_fails_v4(
    scratch: Scratch, text: str | None, lock_path: str | None
) -> None:
    lock = scratch.home / herdr.LOCK
    lock.unlink()
    if text is not None:
        lock.write_text(text.replace("~", str(scratch.home)) + "\n")
    seen, checks = scratch.observe()
    assert seen.lock_path == lock_path
    assert checks.model_dump() == failing("V4")


def test_an_unreadable_core_lock_is_unknown(scratch: Scratch) -> None:
    lock = scratch.home / herdr.LOCK
    lock.unlink()
    lock.mkdir()
    seen, checks = scratch.observe()
    assert (seen.lock_path, seen.unknown) == (None, ["core.lock"])
    assert checks.model_dump() == failing("V4", result="unknown")


# V5: the old path.


def test_an_empty_old_path_folder_passes_v5(scratch: Scratch) -> None:
    (scratch.home / herdr.OLD).mkdir(parents=True)
    assert scratch.checks() == ALL_PASS


def test_holders_under_the_old_path_fail_v5(scratch: Scratch) -> None:
    scratch.hold(scratch.home / herdr.OLD / "default.sock")
    seen, checks = scratch.observe()
    assert seen.old_path_holders == [CORE]
    assert checks.model_dump() == failing("V5")


def test_an_unreadable_old_path_is_unknown(scratch: Scratch) -> None:
    # lsof can't open the folder: it warns and lists nothing, which must not read as "nothing holds it".
    old = scratch.home / herdr.OLD
    old.mkdir(parents=True)
    old.chmod(0)
    try:
        seen, checks = scratch.observe()
    finally:
        old.chmod(0o700)
    # The same folder holds the socket files V15 counts: unread, they are unknown, never "unchanged" (pane review 7).
    assert seen.unknown == [f"sockets ~/{herdr.OLD}", "old-path"]
    assert checks.model_dump() == failing("V5", "V15", result="unknown")


# V7 and V2: the app's environment.


def test_no_app_running_makes_v7_unknown(scratch: Scratch) -> None:
    scratch.reply(["pgrep", "-a", "-x", "Herdr"], code=1)
    seen, checks = scratch.observe()
    assert (seen.windows, seen.unknown) == ([], ["window"])
    assert checks.model_dump() == failing("V7", result="unknown")
    assert herdr.code(checks) == 3


def test_hc_socket_in_the_app_fails_v7_and_v2(scratch: Scratch) -> None:
    old = f"{scratch.home}/.local/run/herdr-core/default.sock"
    scratch.app = scratch.start({"CLAUDECODE": "1", "HC_SOCKET": old, "PATH": "/x"})
    seen, checks = scratch.observe()
    assert seen.windows[0].hc_socket == "~/.local/run/herdr-core/default.sock"
    assert [r.model_dump() for r in seen.routing] == [
        {"where": f"app {scratch.app}", "name": "HC_SOCKET", "value": "~/.local/run/herdr-core/default.sock"}
    ]
    assert checks.model_dump() == failing("V2", "V7")


@pytest.mark.parametrize(
    ("env", "value"),
    [
        ({"HC_SESSION": "default"}, None),
        ({"HC_SESSION": "default x"}, "default x"),
        ({"HC_SESSION": "default X=y"}, "default X=y"),
        # Assignment-shaped text in another value does not hide the real one.
        ({"A": "x HC_SESSION=default", "HC_SESSION": "evil"}, "evil"),
        ({"A": "x HC_SESSION=evil"}, None),
    ],
    ids=["the default", "a space", "an assignment inside", "shadowed", "only inside another"],
)
def test_an_app_value_is_read_exactly(scratch: Scratch, env: dict[str, str], value: str | None) -> None:
    # The kernel's copy of the environment: each value whole, whatever it holds.
    scratch.app = scratch.start(env | {"PATH": "/x"})
    seen, checks = scratch.observe()
    assert [r.value for r in seen.routing] == ([] if value is None else [value])
    assert checks.model_dump() == failing("V2", result="pass" if value is None else "fail")


@pytest.mark.parametrize("app", ["environment hidden", "gone"])
def test_an_app_environment_the_kernel_does_not_give_is_unknown(scratch: Scratch, app: str) -> None:
    # macOS gives no environment for a platform binary such as /bin/sleep, and a gone app has none to read.
    hidden = {"HC_SOCKET": "/s.sock"}
    scratch.app = (
        scratch.start(hidden, program=("/bin/sleep", "600")) if app == "environment hidden" else scratch.gone()
    )
    scratch.reply(["pgrep", "-a", "-x", "Herdr"], stdout=f"{scratch.app}\n")
    seen, checks = scratch.observe()
    assert (seen.windows, seen.unknown) == ([], ["app-env"])
    assert checks.model_dump() == failing("V2", "V7", result="unknown")
    assert herdr.code(checks) == 3


def test_pgrep_failing_for_the_app_is_unknown(scratch: Scratch) -> None:
    scratch.reply(["pgrep", "-a", "-x", "Herdr"], code=2)
    assert scratch.checks() == failing("V2", "V7", result="unknown")


# V1 and V2: the login shell, launchd and the herdr-core config.


def test_xdg_runtime_dir_in_a_login_shell_fails_v1_and_v2(scratch: Scratch) -> None:
    scratch.write(".zprofile", "export XDG_RUNTIME_DIR=$HOME/.local/run\n")
    seen, checks = scratch.observe()
    assert [r.model_dump() for r in seen.routing] == [
        {"where": "login-shell", "name": "XDG_RUNTIME_DIR", "value": "~/.local/run"}
    ]
    assert checks.model_dump() == failing("V1", "V2")


def test_xdg_runtime_dir_in_launchd_fails_v1_and_v2(scratch: Scratch) -> None:
    scratch.reply(["launchctl", "getenv", "XDG_RUNTIME_DIR"], stdout="/r\n")
    assert scratch.checks() == failing("V1", "V2")


@pytest.mark.parametrize(
    ("export", "result"),
    [
        ("HC_SESSION=default", "pass"),
        ("HC_SESSION=scratch", "fail"),
        ("HC_SESSION=default/", "fail"),
        ("XDG_STATE_HOME=$HOME/.local/state/", "pass"),
        ("XDG_STATE_HOME=/elsewhere", "fail"),
        ("HC_SOCKET=/s.sock", "fail"),
        # A value whose next line looks like the probe's own records: still one value, and not the default.
        ("HC_SESSION=$'default\\nherdr-doctor HC_SESSION=default\\nherdr-doctor-end'", "fail"),
    ],
)
def test_routing_inputs_at_their_default_pass_v2(scratch: Scratch, export: str, result: str) -> None:
    scratch.write(".zshrc", f"export {export}\n")
    assert scratch.checks() == failing("V2", result=result)


@pytest.mark.parametrize(
    ("startup", "value", "result"),
    [("default\n", "default", "pass"), ("default\n\n", "default\n", "fail"), (" default\n", " default", "fail")],
)
def test_a_launchd_value_is_kept_as_it_is(scratch: Scratch, startup: str, value: str, result: str) -> None:
    scratch.reply(["launchctl", "getenv", "HC_SESSION"], stdout=startup)
    seen, checks = scratch.observe()
    assert [r.value for r in seen.routing] == ([] if result == "pass" else [value])
    assert checks.model_dump() == failing("V2", result=result)


def test_a_login_shell_that_does_not_finish_is_unknown(scratch: Scratch) -> None:
    scratch.write(".zshrc", "exit 3\n")
    seen, checks = scratch.observe()
    assert seen.unknown == ["login-shell"]
    assert checks.model_dump() == failing("V1", "V2", result="unknown")


def test_what_startup_files_print_is_not_read(scratch: Scratch) -> None:
    scratch.write(".zprofile", "print 'herdr-doctor XDG_RUNTIME_DIR=/r'\nprint herdr-doctor-end\n")
    assert scratch.checks() == ALL_PASS


def test_launchctl_failing_is_unknown(scratch: Scratch) -> None:
    scratch.reply(["launchctl", "getenv", "HC_SOCKET"], code=1)
    seen, checks = scratch.observe()
    assert seen.unknown == ["launchd"]
    assert checks.model_dump() == failing("V1", "V2", result="unknown")


def test_a_socket_that_can_t_be_stat_ed_is_unknown_not_absent(scratch: Scratch) -> None:
    # A 000 state folder: the socket's metadata can't be read, which Path.is_socket would answer as "no socket" and
    # V3 would fail; read with an explicit stat, the listener count is unknown (pane review 8).
    folder = scratch.sock.parent
    folder.chmod(0)
    try:
        seen, checks = scratch.observe()
    finally:
        folder.chmod(0o700)
    assert "listeners" in seen.unknown
    assert seen.listeners == []
    assert checks.model_dump()["V3"] == "unknown"


def test_lsof_missing_from_path_is_unknown(scratch: Scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    # /usr/sbin, where lsof is, left off PATH; ps, env and git stay.
    git_folder = Path(shutil.which("git") or "git").parent
    monkeypatch.setenv("PATH", f"{scratch.stand_in}:/usr/bin:/bin:{git_folder}")
    seen, checks = scratch.observe()
    assert seen.unknown == ["listeners"]
    # No lsof is no holder count: V3 and V4 can't be judged, never failed (pane review 1).
    assert checks.model_dump() == failing("V3", "V4", result="unknown")


MAY_RUN = f"may run a herdr program; {herdr.TRIPWIRE}"
COMPILED = f"is compiled zsh startup code the scan can't read; {herdr.TRIPWIRE}"
# A quote, a backslash or a parenthesis in HOME reaches the sandbox only as a -D parameter, never as profile text.
HOSTILE_HOME = ["hd", 'hd"\\) (allow default) ']


@pytest.mark.parametrize("scratch", HOSTILE_HOME, indirect=True)
def test_a_login_shell_may_not_start_hc_or_write_outside_the_temp_folders(scratch: Scratch) -> None:
    # The owner's startup files run in the probe: a start of hc there is refused and makes V1 and V2 unknown, and a
    # write outside the temp folders is refused. The scratch home is under /tmp, so the write goes to the checkout.
    ran = scratch.home / "hc-ran"
    scratch.write(".local/bin/hc", f"#!/bin/sh\n: > {shlex.quote(str(ran))}\n").chmod(0o755)
    # A folder this test owns, outside every sandbox-writable root; only it is removed afterwards.
    owned = Path(tempfile.mkdtemp(prefix="herdr-doctor-", dir=Path(herdr.ROOT) / "python/home/.venv"))
    outside = owned / "write-probe"
    # open, osascript and launchctl have launchd start a program outside the sandbox: refused too.
    mark = shlex.quote(str(ran))
    scratch.write(
        ".zshrc",
        f"$HOME/.local/bin/hc ls\nprint x > {shlex.quote(str(outside))}\n"
        f"/bin/launchctl getenv HOME && : > {mark}\n/usr/bin/osascript -e 1 && : > {mark}\n",
    )
    try:
        seen, checks = scratch.observe()
    finally:
        written = outside.exists()
        shutil.rmtree(owned)
    assert (ran.exists(), written) == (False, False)
    # The startup scan names the line too (O3); the sandbox refused the start either way.
    lines = [f"startup-files ~/.zshrc:{n} {MAY_RUN}" for n in (1, 3, 4)]
    assert seen.unknown == [*lines, "login-shell"]
    assert checks.model_dump() == failing("V1", "V2", result="unknown")


# O3 (owner, 2026-11-07): a herdr program in the startup files whose denial is hidden reads as no value in the
# sandbox, while a real login shell gets one. Shapes A, C and E from the repro hide stderr three ways; pane review 2
# added a quoted name, command hc and if hc, which a command-word pattern missed.
STARTUP_CASES: dict[str, tuple[dict[str, str], list[str]]] = {
    "A 2>/dev/null": (
        {
            ".zprofile": 'export HC_SOCKET="$($HOME/.local/bin/hc 2>/dev/null)"; '
            '[ -n "$HC_SOCKET" ] || unset HC_SOCKET\n'
        },
        [f"startup-files ~/.zprofile:1 {MAY_RUN}"],
    ),
    "C exit-status guard": (
        {".zshrc.d/hc.zsh": "# routing\nif s=$($HOME/.local/bin/hc 2>/dev/null); then export HC_SOCKET=$s; fi\n"},
        [f"startup-files ~/.zshrc.d/hc.zsh:2 {MAY_RUN}"],
    ),
    "E exec 2>/dev/null": (
        {
            ".zshenv": 'exec 2>/dev/null; export HC_SOCKET="$($HOME/.local/bin/hc)"; '
            '[ -n "$HC_SOCKET" ] || unset HC_SOCKET\n'
        },
        [f"startup-files ~/.zshenv:1 {MAY_RUN}"],
    ),
    "quoted name": (
        {".zprofile": 's=$("hc" 2>/dev/null) && export HC_SOCKET=$s\n'},
        [f"startup-files ~/.zprofile:1 {MAY_RUN}"],
    ),
    "command hc": (
        {".zprofile": "s=$(command hc ls 2>/dev/null) && export HC_SOCKET=$s\n"},
        [f"startup-files ~/.zprofile:1 {MAY_RUN}"],
    ),
    "if hc": ({".zprofile": "if hc ls 2>/dev/null; then :; fi\n"}, [f"startup-files ~/.zprofile:1 {MAY_RUN}"]),
    # Tripwire, not proof (owner, pane review 5): no source is followed; a hit at any depth in each of the three
    # folders counts, and so does compiled startup code: a startup file's .zwc sibling, or a .zwc under a folder.
    "a hit in each folder": (
        {
            ".zshrc.d/a.zsh": "hc ls\n",
            ".zprofile.d/deep/b.zsh": "x=$(herdr-core version)\n",
            ".config/zsh/c.zsh": "$HOME/.local/bin/hc-safe 1 s -- ls\n",
        },
        [
            f"startup-files ~/.zshrc.d/a.zsh:1 {MAY_RUN}",
            f"startup-files ~/.zprofile.d/deep/b.zsh:1 {MAY_RUN}",
            f"startup-files ~/.config/zsh/c.zsh:1 {MAY_RUN}",
        ],
    ),
    "compiled": (
        {".zshrc.zwc": "", ".config/zsh/a.zsh.zwc": ""},
        [f"startup-files ~/.zshrc.zwc {COMPILED}", f"startup-files ~/.config/zsh/a.zsh.zwc {COMPILED}"],
    ),
    # Clean: a comment, look-alike words, a sourced file that names hc (not followed: it is outside the set), a
    # zcompdump completion cache, a linked folder resolving outside HOME (not entered), a dangling link, a fifo and a
    # ~/.zprofile.d that is a plain file (not a folder: nothing under it to read).
    "clean": (
        {
            ".zprofile": "# hc ls\nalias h=hc-foo\nls ~/.local/share/herdr-core/x\nsource ~/other.zsh\n",
            ".zprofile.d": "hc ls\n",
            "other.zsh": "hc ls\n",
            ".zcompdump-host-5.9.zwc": "",
            ".config/zsh/path.zsh": "path=(~/.local/bin $path)\n",
        },
        [],
    ),
    "unreadable file": ({".zprofile": ""}, ["startup-files ~/.zprofile unreadable"]),
    "unreadable folder": ({".zprofile.d/x.zsh": ""}, ["startup-files ~/.zprofile.d unreadable"]),
    # A folder in the set that links to itself: a strict resolve says so (a non-strict one returns it as a path).
    "a link-loop folder": ({".zprofile": ""}, ["startup-files ~/.config/zsh unreadable"]),
    # Pane review 6: a folder that lists names but can't be searched (0400), and a 000 file in a folder.
    "unreadable 0400 folder": ({".zshrc.d/sub/x.zsh": "hc ls\n"}, ["startup-files ~/.zshrc.d/sub/x.zsh unreadable"]),
    # Pane review 7: a startup file's .zwc sibling is found by an explicit stat, so a link to a 000 file still counts.
    "unreadable .zwc link to a 000 file": ({"zwc-target": ""}, [f"startup-files ~/.zshrc.zwc {COMPILED}"]),
    "unreadable 000 file in a folder": (
        {".config/zsh/x.zsh": "hc ls\n"},
        ["startup-files ~/.config/zsh/x.zsh unreadable"],
    ),
}


@pytest.mark.parametrize("case", STARTUP_CASES)
def test_a_herdr_program_in_the_startup_files_makes_v2_unknown(scratch: Scratch, case: str) -> None:
    files, unknown = STARTUP_CASES[case]
    written, *_ = [scratch.write(name, text) for name, text in files.items()]
    locked = written if case.startswith("unreadable") and " file" in case else written.parent
    mode = locked.stat().st_mode
    if case.startswith("unreadable"):
        locked.chmod(0o400 if "0400" in case else 0)
    if case == "a link-loop folder":
        (scratch.home / ".config").mkdir(exist_ok=True)
        (scratch.home / ".config/zsh").symlink_to(scratch.home / ".config/zsh")
    if "zwc link" in case:
        (scratch.home / ".zshrc.zwc").symlink_to(written)
    if case == "clean":
        outside = scratch.repo / "linked"
        outside.mkdir()
        (outside / "x.zsh").write_text("hc ls\n")
        (scratch.home / ".zshrc.d").mkdir()
        (scratch.home / ".zshrc.d/linked").symlink_to(outside)
        (scratch.home / ".zshrc.d/dangling").symlink_to(scratch.home / "gone")  # Nothing to read.
        os.mkfifo(scratch.home / ".zshrc.d/fifo")  # Neither a file nor a folder: never opened.
    try:
        seen, checks = scratch.observe()
    finally:
        locked.chmod(mode)
    assert seen.unknown == unknown
    assert checks.model_dump() == (failing("V2", result="unknown") if unknown else ALL_PASS)


@pytest.mark.parametrize("scratch", HOSTILE_HOME[1:], indirect=True)
def test_a_hostile_home_still_reads_the_login_shell(scratch: Scratch) -> None:
    seen, checks = scratch.observe()
    assert seen.unknown == []
    assert checks.model_dump() == failing()


def test_a_socket_pin_in_the_config_fails_v2(scratch: Scratch) -> None:
    scratch.write(herdr.CONFIG, f'theme = "x"\nsocket = "{scratch.home}/pin.sock"\n')
    seen, checks = scratch.observe()
    assert [r.model_dump() for r in seen.routing] == [{"where": "config", "name": "socket", "value": "~/pin.sock"}]
    assert checks.model_dump() == failing("V2")


def test_a_config_without_a_socket_pin_passes(scratch: Scratch) -> None:
    scratch.write(herdr.CONFIG, 'theme = "x"\n')
    assert scratch.checks() == ALL_PASS


def test_a_config_that_does_not_parse_is_unknown(scratch: Scratch) -> None:
    scratch.write(herdr.CONFIG, "socket = \n")
    seen, checks = scratch.observe()
    assert seen.unknown == ["herdr-config"]
    assert checks.model_dump() == failing("V2", result="unknown")


# V10: versions and skills.


@pytest.mark.parametrize("what", ["missing", "current links to nothing"])
def test_no_installed_hc_fails_v10(scratch: Scratch, what: str) -> None:
    plist = scratch.home / herdr.HC_PLIST
    plist.unlink()
    if what != "missing":
        plist.symlink_to(scratch.home / "gone")
    seen, checks = scratch.observe()
    assert seen.hc is None
    assert checks.model_dump() == failing("V10")


@pytest.mark.parametrize(
    "content",
    [
        b"not a plist",
        b"<?xml version='1.0'?><plist><dict>",
        plistlib.dumps({"CFBundleVersion": HC}),
        plistlib.dumps(["a list"]),
        b"<?xml version='1.0'?><plist><dict><key>d</key><date>invalid</date></dict></plist>",
    ],
    ids=["unreadable", "malformed XML", "no version key", "not a dictionary", "a date that does not parse"],
)
def test_an_hc_plist_without_a_version_is_unknown(scratch: Scratch, content: bytes) -> None:
    (scratch.home / herdr.HC_PLIST).write_bytes(content)
    seen, checks = scratch.observe()
    assert (seen.hc, seen.unknown) == (None, ["hc-version"])
    assert checks.model_dump() == failing("V10", result="unknown")


def test_the_app_version_is_reported_only(scratch: Scratch) -> None:
    (scratch.home / herdr.APP_PLIST).unlink()
    seen, checks = scratch.observe()
    assert seen.app is None
    assert checks.model_dump() == ALL_PASS


def test_a_missing_skill_fails_v10(scratch: Scratch) -> None:
    (scratch.home / herdr.SKILLS[2] / "SKILL.md").unlink()
    seen, checks = scratch.observe()
    assert seen.skills_missing == [f"~/{herdr.SKILLS[2]}"]
    assert checks.model_dump() == failing("V10")


def test_a_shared_skill_claude_code_does_not_list_fails_v10(scratch: Scratch) -> None:
    # Codex reads ~/.agents/skills; Claude Code needs its own entry for each skill there.
    scratch.write(".agents/skills/alpha/SKILL.md", "---\nname: alpha\n---\n")
    scratch.write(".agents/skills/.mise-skills.json", "{}")  # A dot entry is no skill.
    (scratch.home / ".agents/skills/no-skill").mkdir()  # Nothing to read, so nothing Claude Code must list.
    scratch.write(".claude/skills/claude-only/SKILL.md", "---\nname: claude-only\n---\n")
    seen, checks = scratch.observe()
    assert seen.skills_missing == ["~/.claude/skills/alpha"]
    assert checks.model_dump() == failing("V10")
    (scratch.home / ".claude/skills/alpha").symlink_to("../../.agents/skills/alpha")
    assert scratch.checks() == ALL_PASS


def test_a_claude_code_link_to_a_removed_shared_skill_fails_v10(scratch: Scratch) -> None:
    # What `skills remove -a <one agent>` through the Antigravity CLI folder link leaves behind.
    (scratch.home / ".claude/skills/beta").symlink_to("../../.agents/skills/beta")
    seen, checks = scratch.observe()
    assert seen.skills_missing == ["~/.claude/skills/beta"]
    assert checks.model_dump() == failing("V10")


def test_a_missing_shared_folder_lists_no_skills(scratch: Scratch) -> None:
    shutil.rmtree(scratch.home / ".agents/skills")
    seen, checks = scratch.observe()
    assert (seen.skills_missing, seen.unknown) == (["~/.agents/skills/herdr-core"], [])
    assert checks.model_dump() == failing("V10")


def test_a_skills_folder_that_can_t_be_listed_is_unknown(scratch: Scratch) -> None:
    folder = scratch.home / ".claude/skills"
    folder.chmod(0)
    try:
        seen, checks = scratch.observe()
    finally:
        folder.chmod(0o700)
    assert seen.unknown == ["skills"]
    assert checks.model_dump() == failing("V10", result="unknown")


@pytest.mark.parametrize(
    "skills",
    [{"herdr-core": {"ref": "v0.1.17"}}, {"herdr-core": {}}, {"other": {"ref": f"v{HC}"}}, {"herdr-core": "v0.1.18"}],
    ids=["stale tag", "no ref", "not installed by the CLI", "not an entry"],
)
def test_a_skill_not_at_the_hc_version_fails_v10(scratch: Scratch, skills: dict[str, object]) -> None:
    scratch.lock(skills)
    assert scratch.checks() == failing("V10")


@pytest.mark.parametrize("hc_plist", ["readable", "unreadable"])
def test_no_skills_lock_fails_v10(scratch: Scratch, hc_plist: str) -> None:
    # No tag is at no version: V10 fails even when hc's own version can't be read (pane review 2).
    (scratch.home / ".local/state/skills/.skill-lock.json").unlink()
    if hc_plist == "unreadable":
        (scratch.home / herdr.HC_PLIST).write_bytes(b"not a plist")
    seen, checks = scratch.observe()
    assert (seen.skill_tag, seen.unknown) == (None, [] if hc_plist == "readable" else ["hc-version"])
    assert checks.model_dump() == failing("V10")


def test_without_xdg_state_home_the_lock_is_under_agents(scratch: Scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_STATE_HOME")
    (scratch.home / ".local/state/skills/.skill-lock.json").rename(scratch.home / ".agents/.skill-lock.json")
    assert scratch.checks() == ALL_PASS


@pytest.mark.parametrize("text", ["{not json", '{"version": 3, "skills": []}', "[]"])
def test_an_unreadable_skills_lock_is_unknown(scratch: Scratch, text: str) -> None:
    scratch.write(".local/state/skills/.skill-lock.json", text)
    seen, checks = scratch.observe()
    assert seen.unknown == ["skill-lock"]
    assert checks.model_dump() == failing("V10", result="unknown")


# V11: retired-project references.


def test_a_retired_reference_outside_the_allowlist_fails_v11(scratch: Scratch) -> None:
    (scratch.repo / "notes.md").write_text(f"one\nsee the {MARKETPLACE.upper()} repo\n")
    seen, checks = scratch.observe()
    assert seen.references == ["notes.md:2"]
    assert checks.model_dump() == failing("V11")


def test_allowlisted_lines_and_files_pass_v11(scratch: Scratch) -> None:
    (scratch.repo / "GLOSSARY.md").write_text(f"New text above.\nwhen the {MARKETPLACE} repository was sunset.\n")
    design = scratch.repo / "docs/designs/herdr-core-socket-cutover.md"
    design.parent.mkdir(parents=True)
    design.write_text(f"{MARKETPLACE} and macos-development-environment\n")
    git(scratch.repo, "add", "GLOSSARY.md")
    assert scratch.checks() == ALL_PASS


def test_an_allowlisted_text_in_another_file_fails_v11(scratch: Scratch) -> None:
    (scratch.repo / "other.md").write_text(f"when the {MARKETPLACE} repository was sunset.\n")
    assert scratch.observe()[0].references == ["other.md:1"]


def test_links_and_deleted_files_are_not_read(scratch: Scratch) -> None:
    (scratch.repo / "gone.md").write_text(f"{MARKETPLACE}\n")
    git(scratch.repo, "add", "gone.md")
    (scratch.repo / "gone.md").unlink()
    outside = scratch.home / "outside.md"
    outside.write_text(f"{MARKETPLACE}\n")
    (scratch.repo / "link.md").symlink_to(outside)
    assert scratch.checks() == ALL_PASS


@pytest.mark.parametrize("reference", ["alone", "read elsewhere"])
def test_an_unreadable_file_makes_v11_unknown(scratch: Scratch, reference: str) -> None:
    # A reference read in another file still fails V11: a failure read wins over an unread file (pane review 2).
    elsewhere = reference == "read elsewhere"
    if elsewhere:
        (scratch.repo / "notes.md").write_text(f"{MARKETPLACE}\n")
    secret = scratch.repo / "secret.md"
    secret.write_text(f"{MARKETPLACE}\n")
    secret.chmod(0)
    try:
        seen, checks = scratch.observe()
    finally:
        secret.chmod(0o600)
    assert (seen.references, seen.unknown) == (["notes.md:1"] if elsewhere else [], ["references"])
    assert checks.model_dump() == (failing("V11") if elsewhere else failing("V11", result="unknown"))


def test_a_folder_that_is_not_a_repository_is_unknown(scratch: Scratch) -> None:
    shutil.rmtree(scratch.repo / ".git")
    seen, checks = scratch.observe()
    assert seen.unknown == ["references"]
    assert checks.model_dump() == failing("V11", result="unknown")


# V15: the doctor cannot start a core.


@pytest.mark.parametrize("unread", ["nothing", "pgrep", "the old path"])
def test_a_socket_that_appears_during_the_run_fails_v15(scratch: Scratch, unread: str) -> None:
    # The login shell, between the doctor's first and last count, leaves a socket file in the state folder: what a
    # check that started a core would leave behind. It is a change read even when pgrep can't count the cores, or
    # when the other socket folder can't be read: each folder counts on its own (pane review 8).
    scratch.write(".zprofile", f": > {shlex.quote(str(scratch.sock.parent / 'second.sock'))}\n")
    old = scratch.home / herdr.OLD
    if unread == "pgrep":
        scratch.reply(["pgrep", "-a", "-f", herdr.CORE], code=3, stderr="pgrep: sysctl\n")
    if unread == "the old path":
        old.mkdir(parents=True)
        old.chmod(0)
    try:
        seen, checks = scratch.observe()
    finally:
        if unread == "the old path":
            old.chmod(0o700)
    assert seen.unchanged is False
    also = {"nothing": {}, "pgrep": {"V4": "unknown"}, "the old path": {"V5": "unknown"}}[unread]
    assert checks.model_dump() == failing("V15") | also
    assert (
        seen.unknown
        == {"nothing": [], "pgrep": ["cores"], "the old path": [f"sockets ~/{herdr.OLD}", "old-path"]}[unread]
    )


def test_the_doctor_source_passes_its_own_guard() -> None:
    assert herdr.guard(Path(herdr.__file__).read_text()) == []


@pytest.mark.parametrize(
    ("planted", "finding"),
    [
        ('X = "hc"\n', "names 'hc'"),
        ('def probe():\n    return read("lsof", "hc ls")\n', "names 'hc ls'"),
        ('X = "~/.local/bin/hc"\n', "names '~/.local/bin/hc'"),
        ('X = "/Applications/Herdr.app/Contents/MacOS/Herdr"\n', "MacOS/Herdr"),
        ("import subprocess\nsubprocess.run(['ls'])\n", "subprocess.run outside read()"),
        ("import os\nos.execvp('x', ['x'])\n", "os.execvp outside read()"),
        ("PROGRAM = 'curl'\nread(PROGRAM)\n", "read() of a program that is not a reader"),
        ("read()\n", "read() of a program that is not a reader"),
    ],
    ids=["hc as a program", "hc as a command line", "hc's path", "the app", "subprocess", "exec", "a name", "nothing"],
)
def test_a_planted_hc_call_fails_the_guard(planted: str, finding: str) -> None:
    source = Path(herdr.__file__).read_text() + "\n" + planted
    found = herdr.guard(source)
    assert len(found) == 1
    assert finding in found[0]


def test_the_guard_does_not_flag_its_own_lists() -> None:
    assert herdr.guard('FORBIDDEN = frozenset({"hc"})\nPROGRAM_PATH = "bin/hc"\n') == []


@pytest.mark.parametrize("argv", [("hc", "ls"), ("launchctl", "setenv", "X", "1"), ("open", "-a")])
def test_read_refuses_anything_but_a_read(
    argv: tuple[str, ...], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A canary on PATH under the refused name: refusing must mean it never ran.
    ran = tmp_path / "ran"
    canary = tmp_path / argv[0]
    canary.write_text(f"#!/bin/sh\n: > {shlex.quote(str(ran))}\n")
    canary.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    with pytest.raises(ValueError, match="is not a read"):
        herdr.read(*argv)
    assert not ran.exists()
