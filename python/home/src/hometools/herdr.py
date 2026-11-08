"""herdr-doctor: herdr-core and Herdr.app wiring, read from outside; it never runs hc and never writes a file."""

# docs/designs/herdr-core-socket-cutover.md, "The checks" and "How the doctor sees without touching". An hc client
# starts a core when it cannot connect, HC_SOCKET set or not, so every input here is a socket, a process, a file or
# an environment: lsof, pgrep, ps, launchctl getenv, one sandboxed login shell, git ls-files, the kernel's copy of
# the app's environment and the files themselves. Every program starts through read(), which refuses any other; V15
# checks that from this file's own syntax tree.

import ast
import ctypes
import ctypes.util
import json
import os
import plistlib
import pwd
import re
import stat
import subprocess
import tomllib
from pathlib import Path
from xml.parsers.expat import ExpatError

from .models import Checks, DoctorReport, Observation, Result, Routing, Window
from .proc import out

DEFAULT_SOCKET = ".local/state/herdr-core/default/default.sock"
LOCK = ".local/state/herdr-core/default/core.lock"
OLD = ".local/run/herdr-core"
CONFIG = ".config/herdr-core/config.toml"
HC_PLIST = ".local/share/herdr-core/current/Contents/Info.plist"
APP_PLIST = "Applications/Herdr.app/Contents/Info.plist"
# The four harness folders (design G9): Claude, Codex and the skills CLI, agy (Antigravity CLI), OpenCode.
SKILLS = (
    ".claude/skills/herdr-core",
    ".agents/skills/herdr-core",
    ".gemini/antigravity-cli/skills/herdr-core",
    ".config/opencode/skills/herdr-core",
)
# hc's socket inputs (paths.rs:28-34): HC_SOCKET, the config's socket key, XDG_RUNTIME_DIR, HC_SESSION and the
# state folder. Green is none set, or each at its default; the doctor does not copy hc's resolver (Alternative R).
ROUTING = ("HC_SOCKET", "XDG_RUNTIME_DIR", "HC_SESSION", "XDG_STATE_HOME")
# A core's argv (S0, Q4): hc --hc-launchd <ready> when launchd started it, hc serve when started directly, under
# either of the binary's names. Holders (hold) and the window's client (connect) are not cores. pgrep's ERE.
CORE = "^([^ ]*/)?(hc|herdr-core) (--hc-launchd|serve)( |$)"
APP = "Herdr"
# The one login-shell probe for V1 and V2: a NUL, each routing input it has as one NUL-ended record, then an end
# record that proves it ran. NUL can't be in an environment value, so a value with a newline stays one record, and
# whatever the startup files print comes before the first NUL.
PROBE = (
    'print -rN -- ""; for n in HC_SOCKET XDG_RUNTIME_DIR HC_SESSION XDG_STATE_HOME; do '
    '(( ${(P)+n} )) && print -rN -- "herdr-doctor $n=${(P)n}"; done; print -rN -- herdr-doctor-end'
)
MARK, END = "herdr-doctor ", "herdr-doctor-end"
READERS = frozenset({"lsof", "pgrep", "ps", "launchctl", "env", "git", "sandbox-exec"})
# V15: names this file must never hold as a string, so it can't run hc under any of its names.
FORBIDDEN = frozenset({"hc", "herdr-core", "herdr-app", "hc-safe", "open", "/usr/bin/open"})
# A path to one of those programs: an install's bin folder, or the bundle's executable.
PROGRAM_PATH = re.compile(r"(^|/)bin/(hc|herdr-core|herdr-app|hc-safe)\b|MacOS/(herdr-core|Herdr)\b")
# The login shell runs the owner's startup files, so it runs under sandbox-exec: it may not start any herdr program
# (by its link in ~/.local/bin or its install folders), nor open, osascript or launchctl, which have launchd start a
# program outside the sandbox; and it may write only to the temp folders. A denied start makes the probe unknown:
# each program reports one as "not permitted" with the program's name (zsh, env, Python alike).
DENIED_PROGRAMS = (".local/bin/hc", ".local/bin/herdr-core", ".local/bin/herdr-app", ".local/bin/hc-safe")
DENIED_FOLDERS = (".local/share/herdr-core", "Applications/Herdr.app")
DENIED_SYSTEM = ("/usr/bin/open", "/usr/bin/osascript", "/bin/launchctl", "/Applications/Herdr.app")
DENIED_NAME = re.compile(
    r"not permitted.*(\bhc\b|herdr-core|herdr-app|hc-safe|Herdr|\bopen\b|osascript|launchctl)", re.IGNORECASE
)
# The sandbox can't see a denied start whose stderr the startup files hide (2>/dev/null, exec 2>/dev/null, a guard
# on the exit status): the probe then reads no value where a real login shell would get one from a herdr program
# (O3, owner 2026-11-07). So the startup files are also read as text, as a tripwire, not a proof (owner, pane review
# 5): a static scan can't prove what zsh runs (sourcing, PATH lookup, expansion, compiled .zwc files), so it follows
# no source and claims nothing about files outside the set below. It only makes V2 unknown when the zsh config
# visibly involves a herdr program or compiled startup code. V9 login, a real login shell running hc at each cutover
# gate, is the authoritative routing check. The set: the five startup files, and every regular file at any depth
# under three folders (a link to a file is read; a linked folder is entered only when it resolves inside HOME). The
# word scan is conservative: with quotes and backslashes removed, a line any of whose words is one of these names,
# or a path ending in one, counts, so "hc", command hc, if hc and $HOME/.local/bin/hc all do. A .zwc that is a
# startup file's compiled sibling, or lies under the folders, counts too; other .zwc files in HOME, such as
# ~/.zcompdump-*.zwc completion caches, are not startup code.
STARTUP_FILES = (".zshenv", ".zprofile", ".zshrc", ".zlogin", ".zlogout")
STARTUP_FOLDERS = (".zshrc.d", ".zprofile.d", ".config/zsh")
STARTUP_NAMES = frozenset(
    {"hc", "herdr-core", "herdr-app", "hc-safe", "Herdr", "Herdr.app", "open", "osascript", "launchctl"}
)
# A word: what is left between shell punctuation ($ { } ( ) ; | & = : < > ` and blanks).
STARTUP_SPLIT = re.compile(r"[^\w./~+@%,-]+")
TRIPWIRE = "startup files are scanned as a tripwire; V9 login proves routing"
GUARDS = frozenset(
    {"FORBIDDEN", "PROGRAM_PATH", "DENIED_PROGRAMS", "DENIED_FOLDERS", "DENIED_SYSTEM", "DENIED_NAME", "STARTUP_NAMES"}
)
SPAWNERS = frozenset({"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"})
OS_SPAWN = re.compile(r"^(system|popen|exec\w*|spawn\w*|posix_spawn\w*|fork\w*)$")
# The app's environment, exactly: sysctl KERN_PROCARGS2 gives argc, the executable's path, then argv and the
# environment as NUL-ended strings, the environment ending at an empty one (read so on this Mac, macOS 27.2: a
# platform binary's comes back empty). ps -E prints the same strings joined by spaces, which no parse can split.
CTL_KERN, KERN_PROCARGS2 = 1, 49
# OSError for a file that can't be read, and what plistlib, json and tomllib can raise on one the doctor does not
# control, read so in each parser at the
# installed Python (3.15): ValueError (and its InvalidFileException, JSONDecodeError, TOMLDecodeError, binascii and
# Unicode errors), ExpatError for malformed XML, AttributeError for a <date> that does not parse, TypeError and
# OverflowError from a value's conversion, and RecursionError for nesting deeper than the parser's stack.
UNREADABLE = (OSError, ValueError, ExpatError, AttributeError, TypeError, OverflowError, RecursionError)
ABSENT = 0  # Reader.mode for a path that is not there: no file-type bits, so every S_IS* test is False.
LIBC = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

# V11: the retired projects, and every place that may still name them with its reason (design, V11 allowlist).
RETIRED = re.compile(
    "claude-code-marketplace|knowledge-base|macos-development-environment|Marketplace saved searches", re.IGNORECASE
)
ALLOWED_FILES = {
    "python/home/src/hometools/herdr.py": "the checker's own patterns",
    "python/home/tests/test_herdr_doctor.py": "the V11 fixtures",
    "docs/designs/herdr-core-socket-cutover.md": "the design names the references it removes",
}
# (path, the matched line's text) -> reason: by text, not line number, so an edit above a line keeps it allowed.
ALLOWED_LINES = {
    ("docs/research/lsp/data/saved-searches.json", '"shape_source": "ray-manaloto/claude-code-marketplace'): (
        "records where the data came from"
    ),
    ("GLOSSARY.md", "when the claude-code-marketplace repository was sunset."): "the sunset as history",
    ("GLOSSARY.md", "claude-code-marketplace, or a `Sunset port: ...` issue"): "the sunset as history",
    ("GLOSSARY.md", "The issue came from the claude-code-marketplace sunset."): "the sunset as history",
    ("docs/agents/issue-tracker.md", "`from-marketplace`: carried over from the claude-code-marketplace"): (
        "from-marketplace is a live issue label"
    ),
    ("unix/home/.config/mise/miserc.toml", '"~/dev/github/ray-manaloto/claude-code-marketplace/offline",'): (
        "the mirror folder's own mise.toml files must never load"
    ),
    ("python/tests/test_mise_trust.py", 'MIRROR = "dev/github/ray-manaloto/claude-code-marketplace/offline'): (
        "tests that the kept miserc entry ignores the real mirror"
    ),
    ("python/tests/test_mise_trust.py", '".codex/worktrees/new2/claude-code-marketplace",'): (
        "a Codex copy of a repository that is not dotfiles"
    ),
}

ROOT = Path(__file__).resolve(strict=True).parents[4]


class Reader:
    """The doctor's reads under one home, and the inputs it could not read."""

    def __init__(self, home: Path, repo: Path) -> None:
        self.home, self.repo = home, repo
        self.unknown: list[str] = []

    def lost(self, what: str) -> None:
        if what not in self.unknown:
            self.unknown.append(what)

    def short(self, text: str) -> str:
        """A path with this home as ~, so the report names no home folder."""
        return text.replace(str(self.home), "~")

    def mode(self, path: Path, what: str, *, follow: bool = True) -> int | None:
        """path's st_mode from an explicit stat (lstat when not follow): ABSENT (0, no file type) when it is missing
        or a dangling link; None, with what recorded as unknown, on any other error. Path.exists, is_file and is_dir
        answer False on a permission error or a link loop too, so the doctor never uses them (pane reviews 6, 7)."""
        try:
            return path.stat(follow_symlinks=follow).st_mode
        except FileNotFoundError:
            return ABSENT
        except OSError:
            self.lost(what)
            return None

    def holders(self, *where: str) -> list[int] | None:
        """The pids lsof lists for where; None when lsof failed or warned. No -w: a warning, such as a folder lsof
        can't open, means it did not see everything, and a holder it missed would read as none."""
        done = read("lsof", "-F", "p", *where)
        if done is None:
            return None
        code, out, err = done
        # lsof exits 1 both when nothing holds the file and on an error; only the error writes to stderr.
        if code not in {0, 1} or (code == 1 and err.strip()):
            return None
        return sorted({int(line[1:]) for line in out.splitlines() if line.startswith("p")})

    def listeners(self) -> list[int]:
        socket = self.home / DEFAULT_SOCKET
        mode = self.mode(socket, "listeners")  # Not Path.is_socket, which reads a permission error as "no socket".
        if mode is None or not stat.S_ISSOCK(mode):  # Unread (unknown), or no socket file there: no listener.
            return []
        found = self.holders("--", str(socket))
        if found is None:
            self.lost("listeners")
            return []
        return found

    def old_path(self) -> list[int]:
        folder = self.home / OLD
        mode = self.mode(folder, "old-path")
        if mode is None or not stat.S_ISDIR(mode):  # Unreadable (unknown), or missing: empty (V5).
            return []
        found = self.holders("+D", str(folder))
        if found is None:
            self.lost("old-path")
            return []
        return found

    def pgrep(self, *args: str) -> list[int] | None:
        """-a: macOS pgrep leaves out its own ancestors, and in an hc terminal the core is one (pgrep(1))."""
        done = read("pgrep", *args)
        if done is None or done[0] not in {0, 1}:  # 1: none matched.
            return None
        return sorted(int(pid) for pid in done[1].split())

    def cores(self) -> list[int]:
        found = self.pgrep("-a", "-f", CORE)
        if found is None:
            self.lost("cores")
            return []
        return found

    def started(self, pid: int) -> str | None:
        done = read("ps", "-o", "lstart=", "-p", str(pid))
        if done is None or done[0] or not done[1].strip():  # Gone since pgrep saw it, or ps failed.
            self.lost("core-started")
            return None
        return done[1].strip()

    def lock(self) -> str | None:
        try:
            return self.short((self.home / LOCK).read_text().strip())
        except FileNotFoundError:
            return None
        except OSError, UnicodeDecodeError:
            self.lost("core.lock")
            return None

    def routing(self, where: str, values: dict[str, str]) -> list[Routing]:
        """The inputs in values that are not at hc's default; unset is the default for every one. Only the state
        folder, a path, may end in /."""
        defaults = {"HC_SESSION": {"default"}, "XDG_STATE_HOME": {str(self.home / ".local/state")}}
        return [
            Routing(where=where, name=name, value=self.short(value))
            for name, value in values.items()
            if name in ROUTING
            and (value.rstrip("/") if name == "XDG_STATE_HOME" else value) not in defaults.get(name, set())
        ]

    def window(self, pid: int) -> tuple[Window, list[Routing]] | None:
        """The app's environment from the kernel; None when it can't be read or shows none (the kernel gives none
        for a platform binary, so an empty one can't be told from a hidden one)."""
        values = environment(pid)
        if not values:
            return None
        socket = values.get("HC_SOCKET")
        found = Window(pid=pid, hc_socket=None if socket is None else self.short(socket))
        return found, self.routing(f"app {pid}", values)

    def windows(self) -> tuple[list[Window], list[Routing]]:
        pids = self.pgrep("-a", "-x", APP)
        if pids is None:
            self.lost("app-env")
            return [], []
        if not pids:  # No window to read: V7 can't say a Dock launch would carry no HC_SOCKET (owner, 2026-11-07).
            self.lost("window")
        found: list[Window] = []
        routing: list[Routing] = []
        for pid in pids:
            seen = self.window(pid)
            if seen is None:
                self.lost("app-env")
                continue
            found.append(seen[0])
            routing += seen[1]
        return found, routing

    def startup(self) -> None:
        """The startup-file tripwire for V2: plain reads, no shell, no source followed."""
        paths: list[Path] = []
        for name in STARTUP_FILES:
            paths.append(self.home / name)
            sibling = self.home / f"{name}.zwc"
            if self.mode(sibling, f"startup-files {self.short(str(sibling))} unreadable"):  # Present: compiled.
                self.compiled(sibling)
        seen: set[Path] = set()
        for name in STARTUP_FOLDERS:
            paths += self.tree(self.home / name, seen)
        for path in paths:
            self.scan(path)

    def compiled(self, path: Path) -> None:
        self.lost(f"startup-files {self.short(str(path))} is compiled zsh startup code the scan can't read; {TRIPWIRE}")

    def real(self, folder: Path) -> Path | None:
        """folder with every link resolved, strictly: a non-strict resolve reads a permission error or a link loop as
        a plain path. None when it is missing, or (recorded as unknown) can't be resolved."""
        try:
            return folder.resolve(strict=True)
        except FileNotFoundError:
            return None
        except OSError:
            self.lost(f"startup-files {self.short(str(folder))} unreadable")
            return None

    def tree(self, folder: Path, seen: set[Path]) -> list[Path]:
        """The regular files at any depth under folder, flagging each .zwc; a folder resolving outside HOME (or
        already read) is not entered."""
        real = self.real(folder)
        if real is None or real in seen or not real.is_relative_to(self.home.resolve(strict=True)):
            return []
        seen.add(real)
        try:
            entries = sorted(folder.iterdir())
        except FileNotFoundError, NotADirectoryError:
            return []
        except OSError:
            self.lost(f"startup-files {self.short(str(folder))} unreadable")
            return []
        found: list[Path] = []
        for entry in entries:
            if entry.name.endswith(".zwc"):
                self.compiled(entry)
                continue
            # A 0400 folder lists names it can't stat: an unread entry is an unknown, never a skip (pane review 6).
            mode = self.mode(entry, f"startup-files {self.short(str(entry))} unreadable")
            if mode is None:
                continue
            if stat.S_ISDIR(mode):
                found += self.tree(entry, seen)
            elif stat.S_ISREG(mode):
                found.append(entry)
        return found

    def scan(self, path: Path) -> None:
        """One startup file's lines that may run a herdr program, as unknowns for V2."""
        shown = self.short(str(path))
        try:
            text = path.read_text(errors="replace")
        except FileNotFoundError, IsADirectoryError:
            return
        except OSError:
            self.lost(f"startup-files {shown} unreadable")
            return
        for number, line in enumerate(text.splitlines(), 1):
            bare = re.sub(r"[\"'\\]", "", line)
            if bare.lstrip().startswith("#"):
                continue
            if any(word.rsplit("/", 1)[-1] in STARTUP_NAMES for word in STARTUP_SPLIT.split(bare)):
                self.lost(f"startup-files {shown}:{number} may run a herdr program; {TRIPWIRE}")

    def login_shell(self) -> list[Routing]:
        """A new login shell's routing inputs, from a clean environment as Terminal.app starts one (V1, V2)."""
        self.startup()
        user = pwd.getpwuid(os.getuid()).pw_name
        env = (f"HOME={self.home}", f"USER={user}", "SHELL=/bin/zsh", "PATH=/usr/bin:/bin", "TERM=xterm")
        # From HOME, as Terminal.app starts one.
        done = read("sandbox-exec", *self.profile(), "env", "-i", *env, "/bin/zsh", "-lic", PROBE, cwd=self.home)
        records = [] if done is None else done[1].split("\0")[1:]
        if END not in records or (done is not None and DENIED_NAME.search(done[2])):
            self.lost("login-shell")
            return []
        found = records[: records.index(END)]
        values = dict(record.removeprefix(MARK).split("=", 1) for record in found if record.startswith(MARK))
        return self.routing("login-shell", values)

    def profile(self) -> list[str]:
        """The login shell's sandbox: no herdr program starts, and nothing is written outside the temp folders.

        HOME reaches the profile only as a sandbox parameter (-D), never as profile text, so a quote or backslash in
        it can't change the policy.
        """
        home = '(param "HOME")'
        programs = " ".join(f'(literal (string-append {home} "/{name}"))' for name in DENIED_PROGRAMS)
        folders = " ".join(f'(subpath (string-append {home} "/{name}"))' for name in DENIED_FOLDERS)
        system = " ".join(f'(subpath "{path}")' for path in DENIED_SYSTEM)
        policy = (
            f"(version 1)(allow default)(deny process-exec {programs} {folders} {system})(deny file-write*)"
            '(allow file-write* (subpath "/private/tmp") (subpath "/private/var/folders")'
            ' (literal "/dev/null") (regex #"^/dev/(tty|fd/)"))'
        )
        # Only the fixed system temp roots are writable: TMPDIR is inherited, and could name HOME itself.
        return ["-D", f"HOME={self.home}", "-p", policy]

    def launchd(self) -> list[Routing]:
        values: dict[str, str] = {}
        for name in ROUTING:
            done = read("launchctl", "getenv", name)
            if done is None or done[0]:
                self.lost("launchd")
                continue
            # launchctl getenv prints the value and a newline, or nothing; the value itself is kept as it is.
            if value := done[1].removesuffix("\n"):
                values[name] = value
        return self.routing("launchd", values)

    def config(self) -> list[Routing]:
        try:
            data = tomllib.loads((self.home / CONFIG).read_text())
        except FileNotFoundError:
            return []
        except UNREADABLE:
            self.lost("herdr-config")
            return []
        if "socket" not in data:
            return []
        return [Routing(where="config", name="socket", value=self.short(str(data["socket"])))]

    def version(self, plist: str, what: str) -> str | None:
        """CFBundleShortVersionString: None when the bundle is missing; unreadable or without one, unknown."""
        try:
            with (self.home / plist).open("rb") as file:
                data = plistlib.load(file)
        except FileNotFoundError:  # Not installed, or current links to nothing.
            return None
        except UNREADABLE:  # Unreadable, or not a plist.
            self.lost(what)
            return None
        found = data.get("CFBundleShortVersionString") if isinstance(data, dict) else None
        if not isinstance(found, str):
            self.lost(what)
            return None
        return found

    def skill_tag(self) -> str | None:
        """The ref the skills CLI recorded for herdr-core, in the lock it reads (skills 1.7.6 cli.mjs:3880-3884)."""
        state = os.environ.get("XDG_STATE_HOME")
        lock = Path(state) / "skills/.skill-lock.json" if state else self.home / ".agents/.skill-lock.json"
        try:
            data = json.loads(lock.read_text())
        except FileNotFoundError:
            return None
        except UNREADABLE:  # Unreadable, or not JSON.
            self.lost("skill-lock")
            return None
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, dict):
            self.lost("skill-lock")
            return None
        entry = skills.get(Path(SKILLS[0]).name)
        ref = entry.get("ref") if isinstance(entry, dict) else None
        return ref if isinstance(ref, str) else None

    def references(self) -> list[str]:
        """path:line of each retired-project reference that the allowlist does not name."""
        done = read("git", "-C", str(self.repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        if done is None or done[0]:
            self.lost("references")
            return []
        found: list[str] = []
        for name in sorted(set(done[1].split("\0")) - {""} - ALLOWED_FILES.keys()):
            path = self.repo / name
            # lstat: deleted but still in the index, a link or not a file is not read; unreadable is unknown.
            mode = self.mode(path, "references", follow=False)
            if mode is None or not stat.S_ISREG(mode):
                continue
            try:
                text = path.read_bytes().decode(errors="replace")
            except OSError:  # Unreadable, or removed since git listed it: V11 can't say it is clean.
                self.lost("references")
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if RETIRED.search(line) and not any(
                    where == name and fragment in line for where, fragment in ALLOWED_LINES
                ):
                    found.append(f"{name}:{number}")
        return found

    def sockets(self) -> dict[str, list[str] | None]:
        """The socket file names in each of the two folders, for V15; None for a folder that can't be read, so a
        change seen in the other one still counts (pane review 8). Not Path.glob, which reads an unreadable folder
        as empty."""
        found: dict[str, list[str] | None] = {}
        for folder in (DEFAULT_SOCKET.rsplit("/", 1)[0], OLD):
            try:
                found[folder] = sorted(
                    path.name for path in (self.home / folder).iterdir() if path.name.endswith(".sock")
                )
            except FileNotFoundError, NotADirectoryError:
                found[folder] = []
            except OSError:
                self.lost(f"sockets ~/{folder}")
                found[folder] = None
        return found

    def skills_missing(self) -> list[str]:
        """The harness skill folders with no herdr-core SKILL.md file; one that can't be read is unknown."""
        modes = {folder: self.mode(self.home / folder / "SKILL.md", "skills") for folder in SKILLS}
        return [f"~/{folder}" for folder, mode in modes.items() if mode is not None and not stat.S_ISREG(mode)]


def read(*argv: str, cwd: Path | None = None) -> tuple[int, str, str] | None:
    """argv's exit code, stdout and stderr, run in cwd; None when it can't start. Only a reader may run."""
    if argv[0] not in READERS or (argv[0] == "launchctl" and argv[1] != "getenv"):
        msg = f"herdr-doctor: {argv[0]} {argv[1]} is not a read"
        raise ValueError(msg)
    try:
        done = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
    # Not on PATH, or not runnable: that input is unknown.
    except OSError:
        return None
    return done.returncode, done.stdout, done.stderr


def environment(pid: int) -> dict[str, str]:
    """pid's environment as the kernel holds it, each NAME=value split at its first =; empty when unreadable."""
    # The argument area is at most ARG_MAX bytes, the buffer size ps itself asks kern.argmax for.
    argmax = os.sysconf("SC_ARG_MAX")
    buffer = ctypes.create_string_buffer(argmax)
    size = ctypes.c_size_t(argmax)
    mib = (ctypes.c_int * 3)(CTL_KERN, KERN_PROCARGS2, pid)
    if LIBC.sysctl(mib, 3, buffer, ctypes.byref(size), None, 0):  # Gone, or not this user's.
        return {}
    data = buffer.raw[: size.value]
    argc = int.from_bytes(data[:4], "little")
    strings = data[4:].partition(b"\0")[2].lstrip(b"\0").split(b"\0")[argc:]
    entries = strings[: strings.index(b"")] if b"" in strings else strings
    return dict(entry.decode(errors="replace").partition("=")[::2] for entry in entries if b"=" in entry)


def guard(source: str) -> list[str]:
    """V15 from the syntax tree: no string names hc as a program, only read() starts a process, and every read()
    names a reader."""
    tree = ast.parse(source)
    # The guard's own lists name what they forbid.
    skip = {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in GUARDS for t in node.targets)
        for inner in ast.walk(node)
    }
    spawning = {
        id(node)
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef) and fn.name == "read"
        for node in ast.walk(fn)
    }
    found: list[str] = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            words = node.value.split()
            if node.value in FORBIDDEN or (words and words[0] in FORBIDDEN) or PROGRAM_PATH.search(node.value):
                found.append(f"line {node.lineno}: names {node.value!r}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            module, name = node.value.id, node.attr
            if (module == "subprocess" and name in SPAWNERS and id(node) not in spawning) or (
                module == "os" and OS_SPAWN.match(name)
            ):
                found.append(f"line {node.lineno}: {module}.{name} outside read()")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "read":
            first = node.args[0] if node.args else None
            if not (isinstance(first, ast.Constant) and first.value in READERS):
                found.append(f"line {node.lineno}: read() of a program that is not a reader")
    return found


def worst(*, bad: bool, needs: tuple[str, ...], unknown: set[str]) -> Result:
    """fail when what was read already fails; unknown when an input it needs is missing; else pass."""
    if bad:
        return Result.fail
    return Result.unknown if any(what in unknown for what in needs) else Result.pass_


def observe(home: Path | None = None, repo: Path = ROOT) -> Observation:
    reader = Reader(home or Path.home(), repo)
    before = (reader.cores(), reader.sockets())
    cores = before[0]
    listeners = reader.listeners()
    windows, app_routing = reader.windows()
    routing = reader.login_shell() + reader.launchd() + app_routing + reader.config()
    observation = Observation(
        hc=reader.version(HC_PLIST, "hc-version"),
        app=reader.version(APP_PLIST, "app-version"),
        skill_tag=reader.skill_tag(),
        skills_missing=reader.skills_missing(),
        cores=cores,
        listeners=listeners,
        lock_path=reader.lock(),
        core_started=reader.started(cores[0]) if len(cores) == 1 else None,
        old_path_holders=reader.old_path(),
        windows=windows,
        routing=routing,
        references=reader.references(),
        guard=guard(Path(__file__).read_text()),
        unchanged=False,
        unknown=[],
    )
    after = (reader.cores(), reader.sockets())
    # Each folder's sockets, and the cores, count only where they were read both times; a change seen in one
    # readable folder fails V15 even when the other folder is unknown.
    sockets = all(
        was is None or now is None or was == now for was, now in zip(before[1].values(), after[1].values(), strict=True)
    )
    unchanged = sockets and ("cores" in reader.unknown or before[0] == after[0])
    return observation.model_copy(update={"unchanged": unchanged, "unknown": reader.unknown})


def judge(seen: Observation) -> Checks:
    """Each check fails only on what was read, and a failure read wins over an input that could not be read; an
    unread input is never taken for an absence. Each rule's bad part is therefore built only from what was read."""
    u = {entry.split(" ", 1)[0] for entry in seen.unknown}  # "startup-files <file>:<line> ..." is one input.
    runtime = any(r.name == "XDG_RUNTIME_DIR" and r.where in {"login-shell", "launchd"} for r in seen.routing)
    cores, listeners, lock = "cores" not in u, "listeners" not in u, "core.lock" not in u
    one = len(seen.cores) == 1
    hc, skill_lock = "hc-version" not in u, "skill-lock" not in u
    rules: dict[str, tuple[bool, tuple[str, ...]]] = {
        "V1": (runtime, ("login-shell", "launchd")),
        "V2": (bool(seen.routing), ("login-shell", "startup-files", "launchd", "app-env", "herdr-config")),
        "V3": (listeners and len(seen.listeners) != 1, ("listeners",)),
        "V4": (
            (cores and not one)
            or (cores and listeners and one and seen.cores != seen.listeners)
            or (lock and seen.lock_path != f"~/{DEFAULT_SOCKET}"),
            ("listeners", "cores", "core.lock", "core-started"),
        ),
        "V5": (bool(seen.old_path_holders), ("old-path",)),
        "V7": (any(w.hc_socket is not None for w in seen.windows), ("app-env", "window")),
        "V10": (
            bool(seen.skills_missing)
            or (hc and seen.hc is None)
            or (skill_lock and seen.skill_tag is None)  # No tag is at no version, whatever hc's is.
            or (hc and skill_lock and seen.skill_tag != f"v{seen.hc}"),
            ("hc-version", "skill-lock", "skills"),
        ),
        "V11": (bool(seen.references), ("references",)),
        "V15": (bool(seen.guard) or not seen.unchanged, ("cores", "sockets")),
    }
    return Checks.model_validate({name: worst(bad=bad, needs=needs, unknown=u) for name, (bad, needs) in rules.items()})


def code(checks: Checks) -> int:
    """0 all pass, 1 any fail, 3 any unknown and none failed (2 is argparse's usage error)."""
    results = set(checks.model_dump().values())
    if Result.fail in results:
        return 1
    return 3 if Result.unknown in results else 0


def doctor() -> None:
    """One JSON line on stdout, and the exit code of the checks."""
    seen = observe()
    checks = judge(seen)
    out(DoctorReport(observation=seen, checks=checks).model_dump_json())
    raise SystemExit(code(checks))
