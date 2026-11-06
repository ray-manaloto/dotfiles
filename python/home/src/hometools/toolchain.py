"""toolchain-verify and bootstrap-toolchain: the held Homebrew toolchain and its P2996 links (DL-595, DL-755)."""

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

from .config import ToolchainError
from .models import Bootstrap, Verify
from .proc import call, compiler_env, head, out, run

# brew list --pinned must list every one of these.
PINNED = ("gcc", "llvm", "lld", "lldb", "include-what-you-use", "gdb", "make", "pkgconf")
# P2996's default configs: clang reads the unversioned triple names from the folder it resolves to.
CONFIGS = {"clang-p2996": "arm64-apple-darwin.cfg", "clang++-p2996": "arm64-apple-darwin-clang++.cfg"}
STALE = "arm64-apple-darwin[0-9]*.cfg"
OTOOL = "/usr/bin/otool"
FIX = "run: mise run bootstrap:toolchain"
BOOTSTRAP = ("mise", "bootstrap", "--only", "files,packages", "--yes")


def require(ok: object, message: str) -> None:
    """A check: when it fails, message is what the task reports, one line each."""
    if not ok:
        raise ToolchainError(message)


def versions(cfg: Verify) -> tuple[str, str, str]:
    """clang's, gcc's and IWYU's versions, each matched against the [vars] majors and LLVM."""
    prefix = Path(cfg.brew_prefix)
    clang = run(prefix / "opt/llvm/bin/clang", "-dumpversion")
    require(clang.startswith(f"{cfg.llvm_major}."), f"clang {clang} is not {cfg.llvm_major}.x")
    gcc = run(prefix / f"bin/gcc-{cfg.gcc_major}", "-dumpfullversion")
    require(gcc.startswith(f"{cfg.gcc_major}."), f"gcc-{cfg.gcc_major} reports {gcc}")
    iwyu = run(prefix / "opt/include-what-you-use/bin/include-what-you-use", "--version")
    require(iwyu.endswith(f"based on Homebrew clang version {clang}"), f"iwyu/LLVM mismatch: {iwyu} vs clang {clang}")
    return clang, gcc, iwyu


def links(cfg: Verify) -> None:
    """Every /opt/homebrew dylib that iwyu, ld64.lld and lldb link exists."""
    prefix = Path(cfg.brew_prefix)
    for binary in (
        prefix / "opt/include-what-you-use/bin/include-what-you-use",
        prefix / "opt/lld/bin/ld64.lld",
        prefix / "opt/lldb/bin/lldb",
    ):
        for line in run(OTOOL, "-L", binary).splitlines()[1:]:
            lib = (line.split() or [""])[0]
            require(not lib.startswith("/opt/homebrew/") or Path(lib).exists(), f"{binary}: missing {lib}")


def starts(cfg: Verify) -> None:
    """ld.lld, gdb, gmake and pkgconf start."""
    prefix = Path(cfg.brew_prefix)
    call(prefix / "opt/lld/bin/ld.lld", "--version")
    head(prefix / "bin/gdb", "--version")
    head(prefix / "bin/gmake", "--version")
    call(prefix / "opt/pkgconf/bin/pkgconf", "--version")


def same(a: Path, b: Path) -> bool:
    """test -ef: both exist and are one file."""
    try:
        return a.samefile(b)
    except FileNotFoundError:  # Either is missing, or a link to nothing: test -ef is false.
        return False


def configs(sfx: Path, cur: Path) -> str:
    """Both default configs are in cur and linked from sfx, no versioned name shadows them, and the SDK the
    C config names, which this returns, exists."""
    for name in CONFIGS.values():
        linked = (cur / name).is_file() and same(sfx / name, cur / name)
        require(linked, f"missing P2996 default config {name} in {cur} or {sfx}")
    for folder in (cur, sfx):
        stale = sorted(path for path in folder.iterdir() if fnmatch.fnmatchcase(path.name, STALE))
        if stale:
            msg = f"versioned P2996 config {stale[0]} shadows the unversioned one"
            raise ToolchainError(msg)
    lines = (cur / CONFIGS["clang-p2996"]).read_text().splitlines()
    sdk = "\n".join(m[1] for line in lines if (m := re.match(r"-isysroot[ =](.*)", line)))
    require(Path(sdk).is_dir(), f"P2996 config SDK '{sdk}' does not exist")
    return sdk


def sysroot(exe: Path) -> str:
    """The -isysroot of the first driver line that has one (the last on that line), as sed and head -n 1 found it."""
    driver = run(exe, "-###", "-x", "c++", "-c", "/dev/null", env=compiler_env(), merge=True)
    found = (re.match(r'.*"-isysroot" "([^"]*)"', line) for line in driver.splitlines())
    return next((m[1] for m in found if m), "")


def p2996() -> None:
    """sfx is the PATH folder of -p2996 links, cur the prefix bin folder clang resolves to and reads its
    default configs from: unversioned triple names, and a versionless SDK equal to xcrun's."""
    sfx = Path.home() / ".local/share/p2996/bin"
    try:
        cur = (sfx / "clang-p2996").resolve(strict=True).parent
    except OSError as failed:
        msg = f"{sfx / 'clang-p2996'}: {failed.strerror}"
        raise ToolchainError(msg) from None
    sdk = run("xcrun", "--show-sdk-path")
    require(Path(sdk).is_dir(), f"xcrun SDK {sdk} does not exist")
    cfg_sdk = configs(sfx, cur)
    require(cfg_sdk == sdk, f"P2996 config SDK {cfg_sdk} is not xcrun's {sdk}")
    for exe, want in CONFIGS.items():
        version = run(sfx / exe, "--version", env=compiler_env())
        loads = re.search(rf"Configuration file: .*/{re.escape(want)}", version, re.DOTALL)
        require(loads, f"{sfx / exe} does not load {want}")
        got = sysroot(sfx / exe)
        require(got == sdk, f"{sfx / exe} uses sysroot '{got}', not xcrun's {sdk}")
    head(sfx / "clang++-p2996", "--version")


def pins() -> None:
    pinned = run("brew", "list", "--pinned").splitlines()
    for name in PINNED:
        require(name in pinned, f"{name} is not pinned")


def declared(cfg: Verify, clang: str, gcc: str) -> None:
    """[vars] equals the installs, and conf.d/toolchain.toml declares each package at its [vars] version: a
    missing or stale render is not a status mismatch while the install still matches the old one."""
    require(clang == cfg.llvm, f"clang {clang} is not [vars] llvm {cfg.llvm}")
    require(gcc == cfg.gcc, f"gcc {gcc} is not [vars] gcc {cfg.gcc}")
    status = run("mise", "bootstrap", "packages", "status")
    for want in (
        f"gcc@{cfg.gcc}",
        f"llvm@{cfg.llvm}",
        f"lld@{cfg.llvm}",
        f"lldb@{cfg.llvm}",
        f"include-what-you-use@{cfg.iwyu}",
        f"gdb@{cfg.gdb}",
        f"make@{cfg.make}",
        f"pkgconf@{cfg.pkgconf}",
    ):
        require(want in status, f"conf.d/toolchain.toml does not declare {want}; {FIX}")
    mismatched = [line for line in status.splitlines() if "version mismatch" in line]
    require(not mismatched, "\n".join([*mismatched, FIX]))
    call("mise", "bootstrap", "packages", "status", "--missing")


def verify(cfg: Verify) -> None:
    clang, gcc, iwyu = versions(cfg)
    links(cfg)
    starts(cfg)
    p2996()
    pins()
    declared(cfg, clang, gcc)
    out(f"toolchain:verify OK: clang {clang}, gcc {gcc}, {iwyu}")


def listed(name: str) -> list[str]:
    """The versions brew list --versions names for one package; none when it is not installed (exit 1)."""
    argv = ["brew", "list", "--versions", name]
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    # brew missing or not runnable: the shell's `brew list ... 2>/dev/null` read that as nothing installed.
    except OSError:
        return []
    return done.stdout.split()[1:]


def bootstrap(cfg: Bootstrap, platform: str = sys.platform) -> None:
    """Refuse before any change when an exact brew version is missing (DL-786: bootstrap skips one it cannot
    install). mise reads its config before [bootstrap.files] writes the fragment, so the second run installs
    from it (DL-770); then verify."""
    if platform == "darwin":
        wanted = {"gcc": cfg.gcc, "llvm": cfg.llvm, "lld": cfg.llvm, "lldb": cfg.llvm}
        missing = [
            f"bootstrap:toolchain: brew package {name} {version} is not installed"
            for name, version in wanted.items()
            if version not in listed(name)
        ]
        require(not missing, "\n".join(missing))
    for argv in (BOOTSTRAP, BOOTSTRAP, ("mise", "run", "toolchain:verify")):
        call(*argv)
