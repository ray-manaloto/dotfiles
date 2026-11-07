"""toolchain:verify and bootstrap:toolchain: real mise runs the global tasks in a temporary HOME."""

# The tasks run the real brew, mise, xcrun, otool, compilers and P2996 driver against a scratch copy of this
# Mac's toolchain, built by python/home/tests/scratch_toolchain.py (its docstring cites each seam); a test
# breaks one part of the copy, never the user's Homebrew or P2996 install (CODING_STANDARDS 2). The tasks
# come from a copy of the candidate checkout, as ~/.config/mise links them from the main checkout, so this
# suite runs unchanged against the shell tasks and the hometools port.

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "node_modules", "build", "__pycache__", ".coverage*"
)
FIX = "run: mise run bootstrap:toolchain"
# The builder is a test helper of python/home, not a package: load it by path.
_spec = importlib.util.spec_from_file_location(
    "scratch_toolchain", REPO / "python/home/tests/scratch_toolchain.py"
)
assert _spec and _spec.loader
scratch_toolchain = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = scratch_toolchain
_spec.loader.exec_module(scratch_toolchain)


def refusal(err: str) -> list[str]:
    """The lines a refusal names: the shell printed them plain, hometools as one {"error"} JSON line (#391)."""
    lines = []
    for line in err.splitlines():
        try:
            event = json.loads(line)
        # A plain line, as the shell task and mise print them.
        except json.JSONDecodeError:
            lines.append(line)
            continue
        lines.extend(event["error"].splitlines())
    return lines


def program(*argv: str | Path) -> str:
    return subprocess.run(
        argv, capture_output=True, text=True, check=True
    ).stdout.strip()


class ToolchainTasksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if sys.platform != "darwin":
            raise unittest.SkipTest("the tasks check a macOS Homebrew toolchain")
        root = Path(tempfile.mkdtemp()).resolve()
        cls.addClassCleanup(shutil.rmtree, root)
        cls.candidate = root / "candidate"
        shutil.copytree(REPO, cls.candidate, ignore=IGNORE)
        (root / "session").mkdir()
        cls.session = scratch_toolchain.Session(root / "session")

    def setUp(self) -> None:
        self.fresh()

    def fresh(self) -> None:
        """A new temporary HOME and prefix holding the healthy toolchain."""
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        self.tc = scratch_toolchain.Scratch(root, self.session, self.candidate)
        self.tc.render()
        # The candidate's hometools venv is new: uv builds it with this Python, offline, from the shared cache.
        self.env = {"UV_PYTHON": str(Path(sys.base_prefix) / "bin/python3")}

    @property
    def fragment(self) -> Path:
        return self.tc.home / ".config/mise/conf.d/toolchain.toml"

    def ok(self) -> str:
        iwyu = program(
            self.tc.prefix / "opt/include-what-you-use/bin/include-what-you-use",
            "--version",
        )
        held = self.tc.settings
        return f"toolchain:verify OK: clang {held['llvm']}, gcc {held['gcc']}, {iwyu}"

    def run_task(self, task: str) -> tuple[int, str, str]:
        """`mise run <task>` from an unrelated folder: exit code, stdout and stderr."""
        done = subprocess.run(
            [self.session.mise, "run", task],
            env=self.tc.env() | self.env,
            cwd=self.tc.home / "elsewhere",
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        return done.returncode, done.stdout, done.stderr

    def assert_refused(self, task: str, message: str | None) -> list[str]:
        code, out, err = self.run_task(task)
        self.assertNotEqual(code, 0, out + err)
        lines = refusal(err)
        if message is not None:
            self.assertIn(message, lines, err)
        return lines


class VerifyTest(ToolchainTasksTest):
    def test_a_healthy_toolchain_passes(self) -> None:
        code, out, err = self.run_task("toolchain:verify")
        self.assertEqual(code, 0, err)
        self.assertIn(self.ok(), out.splitlines())

    def verify_cases(self) -> dict[str, Callable[[], str | None]]:
        """Each check, broken alone in the current scratch toolchain: the function breaks it and returns the
        line it reports (None: it only fails, and the shell printed no reason)."""
        tc = self.tc
        # As held before a case changes them.
        held = dict(tc.settings)
        p = tc.prefix

        def clang_major() -> str:
            tc.hold(llvm_major="1")
            return f"clang {held['llvm']} is not 1.x"

        def gcc_major() -> str:
            # The installed gcc under the name of the major before it.
            other = str(int(held["gcc_major"]) - 1)
            tc.link(p / f"bin/gcc-{other}", p / f"bin/gcc-{held['gcc_major']}")
            tc.hold(gcc_major=other)
            return f"gcc-{other} reports {held['gcc']}"

        def iwyu_llvm() -> str:
            # Apple's clang in LLVM's place: a real clang that is not the one IWYU was built with.
            apple = program("/usr/bin/clang", "-dumpversion")
            iwyu = program(
                p / "opt/include-what-you-use/bin/include-what-you-use", "--version"
            )
            tc.link(p / "opt/llvm/bin/clang", Path("/usr/bin/clang"))
            tc.hold(llvm_major=apple.split(".")[0])
            return f"iwyu/LLVM mismatch: {iwyu} vs clang {apple}"

        def linked_dylib() -> str:
            tc.put(p / "opt/lld/bin/ld64.lld", self.session.broken)
            return f"{p}/opt/lld/bin/ld64.lld: missing {self.session.gone}"

        def fails(path: str) -> Callable[[], None]:
            # The real program, which dyld stops before main.
            return lambda: tc.cripple(p / path)

        def xcrun_sdk() -> str:
            # xcrun --show-sdk-path names SDKROOT when it exists; a file is no SDK folder.
            not_sdk = tc.home / "not-an-sdk"
            tc.write(not_sdk, "")
            self.env["SDKROOT"] = str(not_sdk)
            return f"xcrun SDK {not_sdk} does not exist"

        def missing_cfg() -> str:
            tc.unlink(tc.sfx / "arm64-apple-darwin.cfg")
            return f"missing P2996 default config arm64-apple-darwin.cfg in {tc.cur} or {tc.sfx}"

        def versioned_cfg() -> str:
            tc.write(tc.cur / "arm64-apple-darwin25.cfg", "")
            return f"versioned P2996 config {tc.cur}/arm64-apple-darwin25.cfg shadows the unversioned one"

        def cfg_sdk_missing() -> str:
            tc.write(tc.cur / "arm64-apple-darwin.cfg", f"-isysroot {tc.home}/no-sdk\n")
            return f"P2996 config SDK '{tc.home}/no-sdk' does not exist"

        def cfg_sdk_differs() -> str:
            tc.write(tc.cur / "arm64-apple-darwin.cfg", f"-isysroot {tc.home}\n")
            return f"P2996 config SDK {tc.home} is not xcrun's {tc.sdk}"

        def loads_cfg() -> str:
            # The driver reads its configs from the folder it resolves to; this copy's folder has none.
            other = tc.home / "other-p2996/bin"
            tc.prefix_of(other, self.session.driver)
            tc.link(other / "clang++-p2996", Path(self.session.driver.name))
            tc.link(tc.sfx / "clang++-p2996", other / "clang++-p2996")
            return (
                f"{tc.sfx}/clang++-p2996 does not load arm64-apple-darwin-clang++.cfg"
            )

        def sysroot() -> str:
            tc.write(
                tc.cur / "arm64-apple-darwin-clang++.cfg", f"-isysroot {tc.home}\n"
            )
            return (
                f"{tc.sfx}/clang++-p2996 uses sysroot '{tc.home}', not xcrun's {tc.sdk}"
            )

        def pinned() -> str:
            tc.unlink(p / "var/homebrew/pinned/gdb")
            return "gdb is not pinned"

        def vars_llvm() -> str:
            tc.hold(llvm=f"{held['llvm_major']}.999.0")
            return f"clang {held['llvm']} is not [vars] llvm {held['llvm_major']}.999.0"

        def vars_gcc() -> str:
            tc.hold(gcc=f"{held['gcc_major']}.999.0")
            return f"gcc {held['gcc']} is not [vars] gcc {held['gcc_major']}.999.0"

        def declared() -> str:
            # A stale render: the fragment from before lldb was held.
            lines = self.fragment.read_text().splitlines(keepends=True)
            kept = (line for line in lines if not line.startswith('"brew:lldb"'))
            tc.write(self.fragment, "".join(kept))
            return f"conf.d/toolchain.toml does not declare lldb@{held['llvm']}; {FIX}"

        def missing_package() -> None:
            tc.unlink(p / "opt/gdb")

        return {
            "clang major": clang_major,
            "gcc major": gcc_major,
            "iwyu llvm": iwyu_llvm,
            "linked dylib": linked_dylib,
            "ld.lld starts": fails("opt/lld/bin/ld.lld"),
            "gdb starts": fails("bin/gdb"),
            "gmake starts": fails("bin/gmake"),
            "pkgconf starts": fails("opt/pkgconf/bin/pkgconf"),
            "xcrun sdk": xcrun_sdk,
            "missing cfg": missing_cfg,
            "versioned cfg": versioned_cfg,
            "cfg sdk missing": cfg_sdk_missing,
            "cfg sdk differs": cfg_sdk_differs,
            "loads cfg": loads_cfg,
            "sysroot": sysroot,
            "pinned": pinned,
            "vars llvm": vars_llvm,
            "vars gcc": vars_gcc,
            "declared": declared,
            "missing package": missing_package,
        }

    def test_each_failed_check_stops_with_its_reason(self) -> None:
        for name in self.verify_cases():
            with self.subTest(name):
                self.fresh()
                message = self.verify_cases()[name]()
                self.assert_refused("toolchain:verify", message)

    def test_a_mismatch_names_its_lines_and_the_fix(self) -> None:
        for name in ("make", "gdb"):
            self.tc.keg(name, "9.9")
            self.tc.link(self.tc.prefix / "opt" / name, Path(f"../Cellar/{name}/9.9"))
        lines = self.assert_refused("toolchain:verify", FIX)
        mismatched = [line for line in lines if "version mismatch" in line]
        names = sorted(line.split()[1].split("@")[0] for line in mismatched)
        self.assertEqual(names, ["gdb", "make"], lines)


class BootstrapTest(ToolchainTasksTest):
    def missing(self, name: str) -> str:
        held = self.tc.settings
        version = held["gcc"] if name == "gcc" else held["llvm"]
        return f"bootstrap:toolchain: brew package {name} {version} is not installed"

    def test_bootstrap_writes_the_fragment_then_verifies(self) -> None:
        self.tc.unlink(self.fragment)
        code, out, err = self.run_task("bootstrap:toolchain")
        self.assertEqual(code, 0, err)
        self.assertIn(self.ok(), out.splitlines())
        packages = tomllib.loads(self.fragment.read_text())["bootstrap"]["packages"]
        held = self.tc.settings
        self.assertEqual(packages["brew:gcc"], {"version": held["gcc"], "os": "macos"})
        self.assertEqual(
            packages["brew:lldb"], {"version": held["llvm"], "os": "macos"}
        )

    def test_a_failed_bootstrap_stops_there(self) -> None:
        # conf.d as a file: [bootstrap.files] can't write the fragment into it.
        conf_d = self.fragment.parent
        shutil.rmtree(self.tc.owned(conf_d))
        self.tc.write(conf_d, "")
        code, out, err = self.run_task("bootstrap:toolchain")
        self.assertNotEqual(code, 0, out + err)
        self.assertNotIn(self.ok(), out.splitlines())

    def test_a_missing_package_refuses_before_any_change(self) -> None:
        for name in ("gcc", "llvm", "lld", "lldb"):
            for state in ("absent", "another version"):
                with self.subTest(name=name, state=state):
                    self.fresh()
                    self.tc.unlink(self.fragment)
                    rack = self.tc.prefix / "Cellar" / name
                    if state == "absent":
                        shutil.rmtree(self.tc.owned(rack))
                    else:
                        [keg] = rack.iterdir()
                        self.tc.owned(keg).rename(rack / "0.0.1")
                    self.assert_refused("bootstrap:toolchain", self.missing(name))
                    self.assertFalse(self.fragment.exists())

    def test_one_of_several_installed_versions_is_enough(self) -> None:
        self.tc.keg("llvm", "0.0.1")
        code, _out, err = self.run_task("bootstrap:toolchain")
        self.assertEqual(code, 0, err)


del ToolchainTasksTest  # only its subclasses hold tests

if __name__ == "__main__":
    unittest.main()
