"""hometools in-process on a scratch toolchain the real tools run: each check fails on its broken part."""

import json
import re
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from hometools import proc
from hometools import toolchain as commands
from hometools.cli import main
from hometools.config import ToolchainError
from hometools.models import Bootstrap

from .scratch_toolchain import FORMULAE, Scratch, toml_table

FIX = "run: mise run bootstrap:toolchain"


def hometools(capfd: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    try:
        main(list(args))
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def refused(capfd: pytest.CaptureFixture[str], command: str) -> list[str]:
    """The lines of the error event, the last line on stderr after the programs' own."""
    code, out, err = hometools(capfd, command)
    assert code == 1, out + err
    return json.loads(err.splitlines()[-1])["error"].splitlines()


def fragment(tc: Scratch) -> Path:
    return tc.home / ".config/mise/conf.d/toolchain.toml"


def iwyu(tc: Scratch) -> str:
    """The real IWYU's version line, as verify prints it last."""
    program = tc.prefix / "opt/include-what-you-use/bin/include-what-you-use"
    return subprocess.run([program, "--version"], capture_output=True, text=True, check=True).stdout.strip()


def ok(tc: Scratch) -> str:
    return f"toolchain:verify OK: clang {tc.settings['llvm']}, gcc {tc.settings['gcc']}, {iwyu(tc)}"


@pytest.mark.parametrize("args", [[], ["nothing"], ["toolchain-verify", "extra"]])
def test_a_wrong_command_is_a_usage_error(capfd: pytest.CaptureFixture[str], args: list[str]) -> None:
    code, out, _err = hometools(capfd, *args)
    assert (code, out) == (2, "")


def test_a_healthy_toolchain_passes(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    code, out, err = hometools(capfd, "toolchain-verify")
    assert (code, err) == (0, "")
    held = toolchain.settings
    lines = out.splitlines()
    assert lines[:4] == [
        f"Homebrew LLD {held['llvm']} (compatible with GNU linkers)",
        f"GNU gdb (GDB) {held['gdb']}",
        f"GNU Make {held['make']}",
        held["pkgconf"],
    ]
    assert lines[4].startswith("clang version ")
    # mise's own status --missing table: every package installed at its [vars] version.
    assert [line.split() for line in lines[5:-1]] == [
        ["brew", f"{name}@{held[key]}", held[key], "installed"] for name, key in FORMULAE.items()
    ]
    assert lines[-1] == ok(toolchain)


@pytest.mark.usefixtures("toolchain")
@pytest.mark.parametrize(("name", "value"), [("TOOLCHAIN_GDB", None), ("TOOLCHAIN_MAKE", "")])
def test_a_missing_or_empty_setting_refuses(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, name: str, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv(name)
        line = f"hometools: {name} unset; run it through its mise task"
    else:
        monkeypatch.setenv(name, value)
        line = f"hometools: {name} empty"
    assert refused(capfd, "toolchain-verify") == [line]


# Each check, broken alone in the scratch copy: the function breaks it and returns the line verify reports.
CASES: dict[str, Callable[[Scratch, pytest.MonkeyPatch], str]] = {}


def case(
    name: str,
) -> Callable[[Callable[[Scratch, pytest.MonkeyPatch], str]], Callable[[Scratch, pytest.MonkeyPatch], str]]:
    def add(break_it: Callable[[Scratch, pytest.MonkeyPatch], str]) -> Callable[[Scratch, pytest.MonkeyPatch], str]:
        CASES[name] = break_it
        return break_it

    return add


@case("clang major")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    mp.setenv("TOOLCHAIN_LLVM_MAJOR", "1")
    return f"clang {tc.settings['llvm']} is not 1.x"


@case("gcc major")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    # The installed gcc under the name of the major before it.
    other = str(int(tc.settings["gcc_major"]) - 1)
    mp.setenv("TOOLCHAIN_GCC_MAJOR", other)
    tc.link(tc.prefix / f"bin/gcc-{other}", tc.prefix / f"bin/gcc-{tc.settings['gcc_major']}")
    return f"gcc-{other} reports {tc.settings['gcc']}"


@case("iwyu llvm")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    # Apple's clang in LLVM's place: a real clang that is not the one IWYU was built with.
    apple = subprocess.run(["/usr/bin/clang", "-dumpversion"], capture_output=True, text=True, check=True)
    version = apple.stdout.strip()
    tc.link(tc.prefix / "opt/llvm/bin/clang", Path("/usr/bin/clang"))
    mp.setenv("TOOLCHAIN_LLVM_MAJOR", version.split(".")[0])
    return f"iwyu/LLVM mismatch: {iwyu(tc)} vs clang {version}"


@case("linked dylib")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.put(tc.prefix / "opt/lld/bin/ld64.lld", tc.session.broken)
    return f"{tc.prefix}/opt/lld/bin/ld64.lld: missing {tc.session.gone}"


@case("a program fails")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    # The real gdb, which dyld stops before main: SIGABRT.
    tc.cripple(tc.prefix / "bin/gdb")
    return f"{tc.prefix}/bin/gdb exited -6"


@case("a program is missing")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.prefix / "bin/gmake")
    return f"{tc.prefix}/bin/gmake: No such file or directory"


@case("no p2996 link")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.sfx / "clang-p2996")
    return f"{tc.sfx}/clang-p2996: No such file or directory"


@case("xcrun sdk")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    # xcrun --show-sdk-path names SDKROOT when it exists; a file is no SDK folder, and otool only warns on it.
    not_sdk = tc.home / "not-an-sdk"
    tc.write(not_sdk, "")
    mp.setenv("SDKROOT", str(not_sdk))
    return f"xcrun SDK {not_sdk} does not exist"


@case("unlinked cfg")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.sfx / "arm64-apple-darwin.cfg")
    return f"missing P2996 default config arm64-apple-darwin.cfg in {tc.cur} or {tc.sfx}"


@case("no cfg")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.cur / "arm64-apple-darwin-clang++.cfg")
    return f"missing P2996 default config arm64-apple-darwin-clang++.cfg in {tc.cur} or {tc.sfx}"


@case("versioned cfg in cur")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.write(tc.cur / "arm64-apple-darwin25.cfg", "")
    return f"versioned P2996 config {tc.cur}/arm64-apple-darwin25.cfg shadows the unversioned one"


@case("versioned cfg link in sfx")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.link(tc.sfx / "arm64-apple-darwin26.cfg", tc.home / "gone")
    return f"versioned P2996 config {tc.sfx}/arm64-apple-darwin26.cfg shadows the unversioned one"


@case("cfg sdk missing")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.write(tc.cur / "arm64-apple-darwin.cfg", f"-O2\n-isysroot={tc.home}/no-sdk\n")
    return f"P2996 config SDK '{tc.home}/no-sdk' does not exist"


@case("cfg sdk differs")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.write(tc.cur / "arm64-apple-darwin.cfg", f"-isysroot {tc.home}\n")
    return f"P2996 config SDK {tc.home} is not xcrun's {tc.sdk}"


@case("loads cfg")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    # The driver reads its configs from the folder it resolves to; this copy's folder has none.
    other = tc.home / "other-p2996/bin"
    tc.prefix_of(other, tc.session.driver)
    tc.link(other / "clang++-p2996", Path(tc.session.driver.name))
    tc.link(tc.sfx / "clang++-p2996", other / "clang++-p2996")
    return f"{tc.sfx}/clang++-p2996 does not load arm64-apple-darwin-clang++.cfg"


@case("sysroot")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.write(tc.cur / "arm64-apple-darwin-clang++.cfg", f"-isysroot {tc.home}\n")
    return f"{tc.sfx}/clang++-p2996 uses sysroot '{tc.home}', not xcrun's {tc.sdk}"


@case("no sysroot")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.write(tc.cur / "arm64-apple-darwin-clang++.cfg", "")
    return f"{tc.sfx}/clang++-p2996 uses sysroot '', not xcrun's {tc.sdk}"


@case("pinned")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.prefix / "var/homebrew/pinned/gdb")
    return "gdb is not pinned"


@case("vars llvm")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    mp.setenv("TOOLCHAIN_LLVM", f"{tc.settings['llvm_major']}.999.0")
    return f"clang {tc.settings['llvm']} is not [vars] llvm {tc.settings['llvm_major']}.999.0"


@case("vars gcc")
def _(tc: Scratch, mp: pytest.MonkeyPatch) -> str:
    mp.setenv("TOOLCHAIN_GCC", f"{tc.settings['gcc_major']}.999.0")
    return f"gcc {tc.settings['gcc']} is not [vars] gcc {tc.settings['gcc_major']}.999.0"


@case("declared")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    # A stale render: the fragment from before lldb was held.
    lines = fragment(tc).read_text().splitlines(keepends=True)
    tc.write(fragment(tc), "".join(line for line in lines if not line.startswith('"brew:lldb"')))
    return f"conf.d/toolchain.toml does not declare lldb@{tc.settings['llvm']}; {FIX}"


@case("missing package")
def _(tc: Scratch, _mp: pytest.MonkeyPatch) -> str:
    tc.unlink(tc.prefix / "opt/gdb")
    return "mise exited 1"


@pytest.mark.parametrize("break_it", CASES.values(), ids=CASES.keys())
def test_each_failed_check_stops_with_its_reason(
    toolchain: Scratch,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    break_it: Callable[[Scratch, pytest.MonkeyPatch], str],
) -> None:
    want = break_it(toolchain, monkeypatch)
    assert refused(capfd, "toolchain-verify")[-1] == want


def test_a_mismatch_names_its_lines_and_the_fix(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    for name in ("make", "gdb"):
        toolchain.keg(name, "9.9")
        toolchain.link(toolchain.prefix / "opt" / name, Path(f"../Cellar/{name}/9.9"))
    *mismatched, fix = refused(capfd, "toolchain-verify")
    assert fix == FIX
    assert sorted(line.split()[1].split("@")[0] for line in mismatched) == ["gdb", "make"]
    assert all("version mismatch" in line for line in mismatched)


def test_the_p2996_drivers_run_without_sdkroot_and_clang_no_default_config(
    toolchain: Scratch, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # With CLANG_NO_DEFAULT_CONFIG the driver loads no config, and the checks would fail (env -u in the shell).
    monkeypatch.setenv("SDKROOT", toolchain.sdk)
    monkeypatch.setenv("CLANG_NO_DEFAULT_CONFIG", "1")
    code, out, err = hometools(capfd, "toolchain-verify")
    assert (code, out.splitlines()[-1]) == (0, ok(toolchain)), err


def test_bootstrap_writes_the_fragment_then_verifies(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    toolchain.unlink(fragment(toolchain))
    code, out, err = hometools(capfd, "bootstrap-toolchain")
    assert (code, out.splitlines()[-1]) == (0, ok(toolchain)), err
    packages = tomllib.loads(fragment(toolchain).read_text())["bootstrap"]["packages"]
    assert packages["brew:gcc"] == {"version": toolchain.settings["gcc"], "os": "macos"}
    assert packages["brew:lldb"] == {"version": toolchain.settings["llvm"], "os": "macos"}


def missing(tc: Scratch, *names: str) -> list[str]:
    held = {"gcc": tc.settings["gcc"], "llvm": tc.settings["llvm"], "lld": tc.settings["llvm"]}
    held["lldb"] = tc.settings["llvm"]
    return [f"bootstrap:toolchain: brew package {name} {held[name]} is not installed" for name in names]


def test_a_missing_brew_version_refuses_before_any_change(
    toolchain: Scratch, capfd: pytest.CaptureFixture[str]
) -> None:
    toolchain.unlink(fragment(toolchain))
    shutil.rmtree(toolchain.owned(toolchain.prefix / "Cellar/gcc"))
    lld = toolchain.prefix / "Cellar/lld"
    toolchain.owned(lld / toolchain.settings["llvm"]).rename(lld / "0.0.1")
    assert refused(capfd, "bootstrap-toolchain") == missing(toolchain, "gcc", "lld")
    assert not fragment(toolchain).exists()


def test_without_brew_every_package_reads_as_missing(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    toolchain.unlink(fragment(toolchain))
    toolchain.unlink(toolchain.prefix / "bin/brew")
    assert refused(capfd, "bootstrap-toolchain") == missing(toolchain, "gcc", "llvm", "lld", "lldb")
    assert not fragment(toolchain).exists()


def test_one_of_several_installed_versions_is_enough(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    toolchain.keg("llvm", "0.0.1")
    code, _out, err = hometools(capfd, "bootstrap-toolchain")
    assert code == 0, err


def test_off_macos_bootstrap_skips_the_brew_check(toolchain: Scratch) -> None:
    # No brew: the preflight would refuse; off macOS it is not asked, the fragment is written, and verify fails.
    toolchain.unlink(fragment(toolchain))
    toolchain.unlink(toolchain.prefix / "bin/brew")
    held = toolchain.settings
    with pytest.raises(ToolchainError, match=r"^mise exited 1$"):
        commands.bootstrap(Bootstrap(gcc=held["gcc"], llvm=held["llvm"]), platform="linux")
    assert fragment(toolchain).exists()


def test_a_failed_bootstrap_stops_there(toolchain: Scratch, capfd: pytest.CaptureFixture[str]) -> None:
    # conf.d as a file: [bootstrap.files] can't write the fragment into it.
    conf_d = fragment(toolchain).parent
    shutil.rmtree(toolchain.owned(conf_d))
    toolchain.write(conf_d, "")
    [line] = refused(capfd, "bootstrap-toolchain")
    assert re.fullmatch(r"mise exited \d+", line)


def test_an_empty_first_line_prints_nothing(capfd: pytest.CaptureFixture[str]) -> None:
    # No Homebrew program prints nothing for --version; true is a real program that does.
    proc.head(Path("/usr/bin/true"))
    assert capfd.readouterr().out == ""


def test_toml_table_round_trips_text_outside_the_bmp_and_control_characters() -> None:
    # JSON's default escapes for text outside the BMP are surrogate pairs, invalid TOML, and TOML has no raw DEL.
    name = 'tasks."x😀"'
    values: dict[str, object] = {"run😀": "é 😀\x7f\x00\n", "list": ["😀\x7f"], "flag": True}
    assert tomllib.loads(toml_table(name, values)) == {"tasks": {"x😀": values}}
