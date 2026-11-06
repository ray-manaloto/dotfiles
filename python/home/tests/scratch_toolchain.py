"""A scratch copy of this Mac's Homebrew toolchain and P2996 driver, run by the real tools (CODING_STANDARDS 2)."""

# The toolchain tasks run the real brew, mise, xcrun, otool, compilers and P2996 driver against it, and a test
# breaks one part of it by changing the scratch copy only, never the user's Homebrew or P2996 install:
#
# - brew: a copy of the real entry script on a scratch prefix, with its Library linked, as Homebrew's own tests
#   run it (Library/Homebrew/test/support/helper/spec/shared_context/integration_test.rb:137). The script finds
#   its prefix from its own path (bin/brew:79, Library/Homebrew/brew.sh:30). HOMEBREW_TEMP stays outside the
#   prefix (brew.sh:206), and the formula API comes from a clone of the real cache, so a run downloads nothing.
# - Cellar: one real folder per keg, holding links to the real keg's entries; bin is a real folder of links,
#   so a test replaces a program there. opt, var/homebrew/linked and var/homebrew/pinned copy the real records.
#   mise reads the prefix itself through MISE_SYSTEM_BREW_PREFIX (mise v2026.11.2
#   crates/mise-util/src/env.rs:1433-1439): opt/<name> must resolve to Cellar/<name>/<version>
#   (crates/mise-system-packages/src/brew/pour.rs:113-120,180-188).
# - P2996: a copy of the real driver in a scratch prefix whose lib links to the real one (the driver loads
#   @loader_path/../lib), with its own default configs, which the driver reads from its own folder.
# - Every network call fails: the proxy variables name a closed port, and uv runs offline.

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[3]
MISE_HOME = Path("unix/home/.config/mise")
# Every Mach-O program links it.
LIBSYSTEM = "/usr/lib/libSystem.B.dylib"
# brew list --pinned and mise status check these formulae; the value is the [vars] key of the version.
FORMULAE = {
    "gcc": "gcc",
    "llvm": "llvm",
    "lld": "llvm",
    "lldb": "llvm",
    "include-what-you-use": "iwyu",
    "gdb": "gdb",
    "make": "make",
    "pkgconf": "pkgconf",
}
CONFIGS = {"clang-p2996": "arm64-apple-darwin.cfg", "clang++-p2996": "arm64-apple-darwin-clang++.cfg"}
TASKS = ("bootstrap:toolchain", "toolchain:verify")
CLOSED = "http://127.0.0.1:9"


def which(name: str) -> Path:
    found = shutil.which(name)
    if found is None:
        msg = f"{name} is not on PATH"
        raise FileNotFoundError(msg)
    return Path(found).resolve()


def installed_vars(checkout: Path, real: Path) -> dict[str, str]:
    """The checkout's [vars], with each toolchain version the one installed, so Homebrew drift breaks no test."""
    # These tests check hometools's own logic on a scratch copy, so they take the versions from the install and
    # never compare them with [vars]: a [vars] version that is not installed, or mistyped, still passes here.
    # test_integration.py is the check that [vars] equals this Mac's install, and repotools toolchain-gate runs
    # it at pre-commit on any [vars] change, so such a bump fails the commit until the version is installed.
    # Each [vars] key is taken from the first formula that names it: llvm before lld and lldb. The installed
    # version is opt/<name>'s keg folder, as mise reads it (pour.rs:113-120); a revision (_1) stays in it.
    held = tomllib.loads((checkout / MISE_HOME / "config.toml").read_text())["vars"]
    installed = {key: (real / "opt" / name).resolve(strict=True).name for name, key in reversed(FORMULAE.items())}
    majors = {f"{key}_major": installed[key].split(".")[0] for key in ("gcc", "llvm")}
    return held | installed | majors


def toml_table(name: str, table: dict[str, object]) -> str:
    """A TOML table of strings, booleans and string lists; JSON writes each as valid TOML."""
    lines = [f"[{name}]"]
    for key, value in table.items():
        if not (isinstance(value, (str, bool)) or (isinstance(value, list) and all(isinstance(v, str) for v in value))):
            msg = f"{name}.{key} is not a string, a boolean or a list of strings"
            raise TypeError(msg)
        lines.append(f"{json.dumps(key)} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def global_config(checkout: Path, settings: dict[str, str]) -> str:
    """settings as [vars], and the checkout's [bootstrap] directories and files and its toolchain task tables (the
    shell tasks were tables), so no other global tool, env, package or hook loads."""
    data = tomllib.loads((checkout / MISE_HOME / "config.toml").read_text())
    tables = [toml_table("vars", dict(settings))]
    for kind in ("directories", "files"):
        tables += [toml_table(f"bootstrap.{kind}.{json.dumps(p)}", t) for p, t in data["bootstrap"][kind].items()]
    tables += [toml_table(f"tasks.{json.dumps(t)}", data["tasks"][t]) for t in TASKS if t in data.get("tasks", {})]
    return "\n".join(tables)


class Session:
    """What every scratch toolchain shares: the real tools' places, a clone of brew's API cache, and a Mach-O
    program linked to a dylib that does not exist."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.brew = which("brew")
        self.real = self.brew.parents[1]
        self.mise, self.uv = which("mise"), which("uv")
        self.uv_cache = subprocess.run([self.uv, "cache", "dir"], capture_output=True, text=True, check=True)
        self.driver = (Path.home() / ".local/share/p2996/bin/clang-p2996").resolve(strict=True)
        self.sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True, check=True)
        cache = subprocess.run([self.brew, "--cache"], capture_output=True, text=True, check=True)
        self.cache = folder / "brew-cache"
        self.cache.mkdir()
        # An APFS clone: the formula API brew list reads, at no extra space.
        subprocess.run(["cp", "-c", "-R", Path(cache.stdout.strip()) / "api", self.cache], check=True)
        self.gone = f"{self.real}/lib/libhometools-test-{folder.name}.dylib"
        (folder / "gone.c").write_text("int hometools_test_gone(void) { return 0; }\n")
        (folder / "broken.c").write_text("int main(void) { return 0; }\n")
        self.cc("-dynamiclib", "-install_name", self.gone, "gone.c", "-o", "gone.dylib")
        self.cc("broken.c", "gone.dylib", "-o", "broken")
        self.broken = folder / "broken"

    def cc(self, *args: str) -> None:
        subprocess.run(["xcrun", "clang", *args], cwd=self.folder, check=True, capture_output=True)


class Scratch:
    """One healthy scratch toolchain under root, as the tasks see it from HOME; the methods break one part."""

    def __init__(self, root: Path, session: Session, checkout: Path = CHECKOUT) -> None:
        self.root, self.session, self.checkout = root, session, checkout
        self.settings = installed_vars(checkout, session.real)
        self.home, self.prefix = root / "home", root / "brew"
        self.sdk = session.sdk.stdout.strip()
        self.sfx = self.home / ".local/share/p2996/bin"
        self.cur = self.home / ".local/share/p2996/test-id/bin"
        self.tools = self.home / "tools"
        self.prefix_from_real()
        self.p2996()
        for tool in (session.mise, session.uv):
            self.link(self.tools / tool.name, tool)
        config = self.home / ".config/mise"
        config.mkdir(parents=True)
        self.hold()
        (config / "tasks").symlink_to(checkout / MISE_HOME / "tasks")
        (self.home / "elsewhere").mkdir()
        # brew falls back to /private/tmp for a HOMEBREW_TEMP it can't write (Library/Homebrew/brew.sh:53-56).
        (root / "brew-temp").mkdir()

    def hold(self, **changes: str) -> None:
        """The global config, with these [vars] changed: the file tasks' headers set the settings from it."""
        self.settings |= changes
        (self.home / ".config/mise/config.toml").write_text(global_config(self.checkout, self.settings))

    def prefix_from_real(self) -> None:
        real, prefix = self.session.real, self.prefix
        (prefix / "bin").mkdir(parents=True)
        shutil.copy2(self.session.brew, prefix / "bin/brew")
        (prefix / "Library").mkdir()
        (prefix / "Library/Homebrew").symlink_to(real / "Library/Homebrew")
        for name in FORMULAE:
            keg = (real / "opt" / name).resolve(strict=True)
            self.keg(name, keg.name, keg)
            for record in (f"opt/{name}", f"var/homebrew/linked/{name}", f"var/homebrew/pinned/{name}"):
                if (real / record).is_symlink():
                    self.link(prefix / record, (real / record).readlink())
        for name in (f"gcc-{self.settings['gcc_major']}", "gdb", "gmake"):
            self.link(prefix / "bin" / name, (real / "bin" / name).readlink())

    def keg(self, name: str, version: str, real: Path | None = None) -> Path:
        """Cellar/<name>/<version>, a real folder: empty, or links to the real keg's entries."""
        keg = self.prefix / "Cellar" / name / version
        keg.mkdir(parents=True)
        for entry in real.iterdir() if real else ():
            if entry.name == "bin":
                for program in entry.iterdir():
                    self.link(keg / "bin" / program.name, program)
            else:
                (keg / entry.name).symlink_to(entry)
        return keg

    def p2996(self) -> None:
        driver = self.session.driver
        self.prefix_of(self.cur, driver)
        for exe, cfg in CONFIGS.items():
            self.link(self.cur / exe, Path(driver.name))
            self.link(self.sfx / exe, self.cur / exe)
            self.write(self.cur / cfg, f"-isysroot {self.sdk}\n")
            self.link(self.sfx / cfg, self.cur / cfg)

    def prefix_of(self, folder: Path, driver: Path) -> None:
        """A copy of the driver in folder, a bin folder whose ../lib is the real P2996 lib."""
        self.owned(folder).mkdir(parents=True)
        shutil.copy2(driver, folder / driver.name)
        (folder.parent / "lib").symlink_to(driver.parents[1] / "lib")

    def owned(self, path: Path) -> Path:
        """path, once its folder is known to be under root: no test changes the real install."""
        folder = path.parent
        while not folder.exists():
            folder = folder.parent
        if not folder.resolve().is_relative_to(self.root.resolve()):
            msg = f"{path} is outside the scratch toolchain"
            raise PermissionError(msg)
        return path

    def link(self, path: Path, target: Path) -> None:
        self.owned(path).parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
        path.symlink_to(target)

    def unlink(self, path: Path) -> None:
        self.owned(path).unlink()

    def write(self, path: Path, text: str) -> None:
        self.owned(path).unlink(missing_ok=True)
        path.write_text(text)

    def put(self, path: Path, program: Path) -> None:
        """A copy of program at path, in place of the link there."""
        self.owned(path).unlink(missing_ok=True)
        shutil.copy2(program, path)

    def cripple(self, path: Path) -> None:
        """A copy of the real program at path, in place of the link there, that dyld stops before main."""
        # Its libSystem names a dylib that does not exist, so dyld aborts it with SIGABRT.
        self.put(path, path.resolve(strict=True))
        path.chmod(0o755)
        subprocess.run(
            ["install_name_tool", "-change", LIBSYSTEM, self.session.gone, path], check=True, capture_output=True
        )
        # install_name_tool voids the signature, and arm64 runs only signed code: sign it again, ad hoc.
        subprocess.run(["codesign", "--force", "--sign", "-", path], check=True, capture_output=True)

    def env(self) -> dict[str, str]:
        """The environment the tasks run in: only the scratch HOME, prefix and tools, and no network."""
        home = self.home
        return {
            "HOME": str(home),
            **{f"XDG_{d}_HOME": str(home / f".{d.lower()}") for d in ("CONFIG", "STATE", "CACHE")},
            "XDG_DATA_HOME": str(home / ".local/share"),
            "PATH": f"{self.tools}:{self.prefix / 'bin'}:/usr/bin:/bin",
            "TERM": "dumb",
            "MISE_CEILING_PATHS": str(home),
            # No tool install before a task runs (mise src/task/task_tool_installer.rs:234-245).
            "MISE_AUTO_INSTALL": "0",
            "MISE_SYSTEM_BREW_PREFIX": str(self.prefix),
            "HOMEBREW_CACHE": str(self.session.cache),
            "HOMEBREW_TEMP": str(self.root / "brew-temp"),
            "HOMEBREW_LOGS": str(self.root / "brew-logs"),
            "HOMEBREW_NO_AUTO_UPDATE": "1",
            "HOMEBREW_NO_ANALYTICS": "1",
            "HOMEBREW_NO_ENV_HINTS": "1",
            # The cloned API never counts as stale.
            "HOMEBREW_API_AUTO_UPDATE_SECS": "999999999",
            **dict.fromkeys(("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"), CLOSED),
            # The file tasks run hometools through the real uv, with the shared cache, offline.
            "UV_CACHE_DIR": self.session.uv_cache.stdout.strip(),
            "UV_OFFLINE": "1",
            "UV_PYTHON_DOWNLOADS": "never",
        }

    def render(self) -> None:
        """conf.d/toolchain.toml as `mise bootstrap --only files` writes it."""
        subprocess.run(
            [self.session.mise, "bootstrap", "--only", "files", "--yes"],
            env=self.env(),
            cwd=self.home / "elsewhere",
            capture_output=True,
            check=True,
        )
