"""update:brew and update:check: real mise runs the global tasks on a scratch toolchain, the network stood in."""

# The tasks run on a scratch copy of this Mac's toolchain, built by python/home/tests/scratch_toolchain.py: brew
# list --pinned and mise run toolchain:verify run for real there. brew update, brew upgrade, brew outdated, mise
# outdated and mise upgrade download or read the network, so python/home/tests/stand_in.py answers them from a
# script and logs each call (CODING_STANDARDS 2). The tasks come from a copy of the candidate checkout, as
# ~/.config/mise links them from the main checkout, so this suite runs unchanged against the shell tasks and the
# hometools port (#392).

import fcntl
import importlib.util
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MISE_HOME = Path("unix/home/.config/mise")
IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "node_modules", "build", "__pycache__", ".coverage*"
)
REAL: dict[str, object] = {"real": True}
PINNED, VERIFY = "brew list --pinned", "mise run toolchain:verify"
BREW_STEPS = [PINNED, "brew update", "brew upgrade --yes", VERIFY]
# The programs update:all's other leaves run, as their task bodies name them: two scripts in the global config
# folder, untracked, and the native codex and agy. Each is a stand-in here, as each updates over the network;
# `codex --version` and `agy --version` run the native install, which answers offline.
LEAF_PROGRAMS = (
    ".config/mise/scripts/update_mise.py",
    ".config/mise/scripts/update_claude.py",
    ".local/bin/codex",
    ".local/bin/agy",
)
UPDATE_MISE = "update_mise.py"
NATIVE = ("codex", "agy")
LEAF_CALLS = [
    UPDATE_MISE,
    "update_claude.py",
    *(f"{name} update" for name in NATIVE),
    *(f"{name} --version" for name in NATIVE),
]
# The builder is a test helper of python/home, not a package: load it by path.
_spec = importlib.util.spec_from_file_location(
    "scratch_toolchain", REPO / "python/home/tests/scratch_toolchain.py"
)
assert _spec and _spec.loader
scratch_toolchain = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = scratch_toolchain
_spec.loader.exec_module(scratch_toolchain)


def refusal(err: str) -> list[str]:
    """The lines an error names: the shell printed them plain, hometools as one {"error"} JSON line."""
    lines = []
    for line in err.splitlines():
        try:
            event = json.loads(line)
        # A plain line, as the shell task, the stand-ins and mise print them.
        except json.JSONDecodeError:
            lines.append(line)
            continue
        lines.extend(event["error"].splitlines())
    return lines


def errors(err: str) -> list[str]:
    """The {"error"} JSON events in err, whole: uv and mise print their own lines plain."""
    events = []
    for line in err.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event["error"])
    return events


def outdated(formulae: int = 0, casks: int = 0) -> dict[str, object]:
    """brew outdated --json's shape: one entry per outdated formula and cask."""
    entry = {
        "name": "x",
        "installed_versions": ["1"],
        "current_version": "2",
        "pinned": False,
    }
    report = {"formulae": [entry] * formulae, "casks": [entry] * casks}
    return {"stdout": json.dumps(report) + "\n"}


class UpdateTasksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if sys.platform != "darwin":
            raise unittest.SkipTest("the tasks hold a macOS Homebrew toolchain")
        jq = shutil.which("jq")
        if jq is None:
            raise unittest.SkipTest("jq is not on PATH")
        cls.jq = Path(jq).resolve()
        root = Path(tempfile.mkdtemp()).resolve()
        cls.addClassCleanup(shutil.rmtree, root)
        cls.candidate = root / "candidate"
        shutil.copytree(REPO, cls.candidate, ignore=IGNORE)
        (root / "session").mkdir()
        cls.session = scratch_toolchain.Session(root / "session")
        config = tomllib.loads((cls.candidate / MISE_HOME / "config.toml").read_text())
        cls.tasks = config["tasks"]

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        self.tc = scratch_toolchain.Scratch(root, self.session, self.candidate)
        self.hold()
        self.tc.render()
        self.stand_in = root / "stand-in"
        tools = self.stand_in / "bin"
        tools.mkdir(parents=True)
        for link in [
            tools / "brew",
            tools / "mise",
            *(self.tc.home / p for p in LEAF_PROGRAMS),
        ]:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(REPO / "python/home/tests/stand_in.py")
        env = self.tc.env()
        self.env = env | {
            # The stand-ins first; jq for the shell tasks.
            "PATH": os.pathsep.join([str(tools), str(self.jq.parent), env["PATH"]]),
            "STAND_IN": str(self.stand_in),
            # The candidate's hometools venv is new: uv builds it with this Python, offline, from the shared cache.
            "UV_PYTHON": str(Path(sys.base_prefix) / "bin/python3"),
        }

    def hold(self, **changes: str) -> None:
        """The scratch global config, with the candidate's update task tables: the shell tasks were tables."""
        self.tc.hold(**changes)
        update = {n: t for n, t in self.tasks.items() if n.startswith("update:")}
        tables = [
            scratch_toolchain.toml_table(f"tasks.{scratch_toolchain.text(n)}", t)
            for n, t in update.items()
        ]
        config = self.tc.home / ".config/mise/config.toml"
        config.write_text(config.read_text() + "\n" + "\n".join(tables))

    def answer(self, calls: dict[str, dict[str, object]]) -> None:
        """calls in shell form: the stand-in keys each by its argv."""
        script = {json.dumps(shlex.split(c)): answer for c, answer in calls.items()}
        (self.stand_in / "script.json").write_text(json.dumps(script))

    def calls(self) -> list[str]:
        """The calls made, in shell form: an argument with a space in it stays quoted."""
        log = self.stand_in / "calls.jsonl"
        if not log.exists():
            return []
        return [shlex.join(json.loads(line)) for line in log.read_text().splitlines()]

    # uv exits 1 on a user error such as a missing lock, and a missing uv made the launchers'
    # execvp raise: each launcher syncs hometools' environment first and names the failure.
    def without_lock(self) -> None:
        """No uv.lock in the candidate's hometools, a uv user error, until the test ends."""
        lock = self.candidate / "python/home/uv.lock"
        aside = lock.with_name("uv.lock.aside")
        lock.rename(aside)
        self.addCleanup(aside.rename, lock)

    def without_uv(self) -> None:
        self.tc.unlink(self.tc.tools / "uv")

    def extra_package(self) -> Path:
        """A package hometools' lock doesn't list, in the candidate's venv, until the test ends."""
        site = next((self.candidate / "python/home/.venv/lib").glob("python3*/site-packages"))
        extra = site / "extra_package-1.0.dist-info"
        extra.mkdir()
        self.addCleanup(shutil.rmtree, extra, ignore_errors=True)
        files = {
            "METADATA": "Metadata-Version: 2.1\nName: extra-package\nVersion: 1.0\n",
            "INSTALLER": "uv\n",
        }
        for name, text in files.items():
            (extra / name).write_text(text)
        record = [f"{extra.name}/{name},," for name in [*files, "RECORD"]]
        (extra / "RECORD").write_text("\n".join(record) + "\n")
        return extra

    def start_task(self, task: str) -> subprocess.Popen[str]:
        """`mise run <task>` from an unrelated folder, running, with its stdout and stderr piped."""
        running = subprocess.Popen(
            [self.session.mise, "run", task],
            env=self.env,
            cwd=self.tc.home / "elsewhere",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(running.kill)
        return running

    def run_task(self, task: str) -> tuple[int, str, str]:
        """`mise run <task>` from an unrelated folder: exit code, stdout and stderr."""
        running = self.start_task(task)
        out, err = running.communicate(timeout=300)
        return running.returncode, out, err


class BrewTest(UpdateTasksTest):
    def test_an_unpinned_toolchain_package_refuses_before_any_update(self) -> None:
        self.tc.unlink(self.tc.prefix / "var/homebrew/pinned/llvm")
        self.answer({PINNED: REAL})
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 1, out + err)
        line = "update:brew: llvm is not pinned; run 'brew pin llvm' or do a planned toolchain upgrade (DL-595)"
        self.assertIn(line, refusal(err))
        self.assertEqual(self.calls(), [PINNED])

    def test_a_pinned_toolchain_updates_upgrades_and_verifies(self) -> None:
        self.answer(
            {
                PINNED: REAL,
                "brew update": {"stdout": "Already up-to-date.\n"},
                "brew upgrade --yes": {"stdout": "==> Upgrading 1 outdated package\n"},
                VERIFY: REAL,
            }
        )
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            self.calls(), [PINNED, "brew update", "brew upgrade --yes", VERIFY]
        )
        lines = out.splitlines()
        said = ["Already up-to-date.", "==> Upgrading 1 outdated package"]
        self.assertEqual([line for line in lines if line in said], said)
        self.assertTrue(lines[-1].startswith("toolchain:verify OK: "), out)

    def test_a_failed_step_stops_the_task_with_its_exit_code(self) -> None:
        self.answer(
            {PINNED: REAL, "brew update": {"stderr": "no network\n", "code": 3}}
        )
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 3, out + err)
        self.assertIn("no network", refusal(err))
        self.assertEqual(self.calls(), [PINNED, "brew update"])

    def test_a_step_killed_by_a_signal_exits_128_plus_the_signal(self) -> None:
        self.answer({PINNED: REAL, "brew update": {"signal": signal.SIGTERM}})
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 128 + signal.SIGTERM, out + err)
        self.assertEqual(self.calls(), [PINNED, "brew update"])

    # A launcher that can't start hometools exits as a step of the task does, and names why.
    def assert_hometools_could_not_start(self, code: int, why: str) -> None:
        self.answer({PINNED: REAL})
        done, out, err = self.run_task("update:brew")
        self.assertEqual(done, code, out + err)
        line = f"update:brew: hometools could not start ({why})"
        self.assertEqual(errors(err), [line])
        self.assertEqual(self.calls(), [])

    def test_a_failed_uv_sync_exits_with_its_code_and_names_it(self) -> None:
        self.without_lock()
        self.assert_hometools_could_not_start(1, "uv sync exited 1")

    def test_a_uv_that_cannot_start_exits_127_and_names_it(self) -> None:
        self.without_uv()
        self.assert_hometools_could_not_start(127, "uv: No such file or directory")

    def test_hometools_sync_keeps_a_package_its_lock_does_not_list(self) -> None:
        self.tc.unlink(self.tc.prefix / "var/homebrew/pinned/llvm")
        self.answer({PINNED: REAL})
        # The first run builds hometools' venv; the second syncs it with the extra package in it.
        self.assertEqual(self.run_task("update:brew")[0], 1)
        extra = self.extra_package()
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 1, out + err)
        self.assertTrue(extra.is_dir(), err)

    def test_a_failed_verify_fails_the_task(self) -> None:
        self.hold(llvm_major="1")
        self.answer(
            {PINNED: REAL, "brew update": {}, "brew upgrade --yes": {}, VERIFY: REAL}
        )
        code, out, err = self.run_task("update:brew")
        self.assertEqual(code, 1, out + err)
        self.assertTrue(any("is not 1.x" in line for line in refusal(err)), err)
        self.assertEqual(
            self.calls(), [PINNED, "brew update", "brew upgrade --yes", VERIFY]
        )


class CheckTest(UpdateTasksTest):
    BREW = "brew outdated --json"
    MISE = "mise outdated --json"
    DRY = "mise upgrade --dry-run-code"

    def check(
        self, brew: dict[str, object], mise: dict[str, object], dry: dict[str, object]
    ) -> tuple[int, str, str]:
        (self.stand_in / "calls.jsonl").unlink(missing_ok=True)
        self.answer({self.BREW: brew, self.MISE: mise, self.DRY: dry})
        return self.run_task("update:check")

    def test_nothing_outdated_exits_0_and_prints_both_reports(self) -> None:
        code, out, err = self.check(outdated(), {"stdout": "{}\n"}, {})
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        self.assertIn(json.dumps({"formulae": [], "casks": []}), lines)
        self.assertIn("{}", lines)
        self.assertEqual(self.calls(), [self.BREW, self.MISE, self.DRY])

    def test_any_source_with_drift_exits_1_after_every_source_ran(self) -> None:
        tool = {"jq": {"name": "jq", "current": "1.8.1", "latest": "1.8.2"}}
        mise_drift = {"stdout": json.dumps(tool) + "\n"}
        upgrade = {"stdout": "Would upgrade jq\n", "code": 1}
        for name, args in {
            "a formula": (outdated(formulae=1), {"stdout": "{}\n"}, {}),
            "a cask": (outdated(casks=1), {"stdout": "{}\n"}, {}),
            "a mise tool": (outdated(), mise_drift, {}),
            "a mise upgrade": (outdated(), {"stdout": "{}\n"}, upgrade),
        }.items():
            with self.subTest(name):
                code, out, err = self.check(*args)
                self.assertEqual(code, 1, out + err)
                self.assertEqual(self.calls(), [self.BREW, self.MISE, self.DRY])

    def test_a_source_that_cannot_answer_exits_2(self) -> None:
        for source, args, calls in [
            ("brew outdated", ({"code": 1}, {"stdout": "{}\n"}, {}), [self.BREW]),
            (
                "mise outdated",
                (outdated(formulae=1), {"code": 1}, {}),
                [self.BREW, self.MISE],
            ),
        ]:
            with self.subTest(source):
                code, out, err = self.check(*args)
                self.assertEqual(code, 2, out + err)
                self.assertIn(
                    f"update:check: '{source}' failed — COULD NOT CHECK", refusal(err)
                )
                self.assertEqual(self.calls(), calls)

    def test_unreadable_output_exits_2_where_the_shell_task_exited_0(self) -> None:
        # The shell task's jq test failed on these and skipped `&& drift=1`: in sync, a
        # false green its contract forbade. The port exits 2 (owner, 2026-11-06), so this
        # test, alone in this file, fails on the shell version.
        brew, mise = [self.BREW], [self.BREW, self.MISE]
        for name, args, source, calls in [
            ("brew text", ({"stdout": "Error: busy\n"}, {}, {}), "brew outdated", brew),
            ("brew list", ({"stdout": "[]\n"}, {}, {}), "brew outdated", brew),
            ("brew nothing", ({"stdout": ""}, {}, {}), "brew outdated", brew),
            (
                "mise text",
                (outdated(), {"stdout": "WARN x\n"}, {}),
                "mise outdated",
                mise,
            ),
            (
                "mise nothing",
                (outdated(formulae=1), {"stdout": ""}, {}),
                "mise outdated",
                mise,
            ),
        ]:
            with self.subTest(name):
                code, out, err = self.check(*args)
                self.assertEqual(code, 2, out + err)
                self.assertIn(
                    f"update:check: '{source}' failed — COULD NOT CHECK", refusal(err)
                )
                self.assertEqual(self.calls(), calls)

    # 1 is update:check's drift, so a launcher that can't start hometools is COULD NOT CHECK.
    def assert_hometools_could_not_start(self, why: str) -> None:
        code, out, err = self.check(outdated(), {"stdout": "{}\n"}, {})
        self.assertEqual(code, 2, out + err)
        line = f"update:check: hometools could not start ({why}) — COULD NOT CHECK"
        self.assertEqual(errors(err), [line])
        self.assertEqual((out, self.calls()), ("", []))

    def test_a_failed_uv_sync_exits_2_not_drift(self) -> None:
        self.without_lock()
        self.assert_hometools_could_not_start("uv sync exited 1")

    def test_a_uv_that_cannot_start_exits_2_not_drift(self) -> None:
        self.without_uv()
        self.assert_hometools_could_not_start("uv: No such file or directory")

    def test_a_uv_sync_killed_by_a_signal_exits_2_and_names_128_plus_the_signal(self) -> None:
        # The first run builds hometools' venv. uv sync then waits on the venv's .lock, an exclusive flock
        # (uv 0.13.7 crates/uv-project-commands/src/sync.rs:288-293, crates/uv-python-interpreter/src/
        # interpreter.rs:643-650; Rust 1.99.1 library/std/src/sys/fs/unix.rs:1321-1336): this test holds it,
        # so the real uv sync is still running when it gets SIGTERM.
        self.assertEqual(self.check(outdated(), {"stdout": "{}\n"}, {})[0], 0)
        package = self.candidate / "python/home"
        lock = (package / ".venv/.lock").open("a")
        self.addCleanup(lock.close)
        fcntl.flock(lock, fcntl.LOCK_EX)
        (self.stand_in / "calls.jsonl").unlink()
        task = self.start_task("update:check")
        sync = ["uv", "sync", "--project", str(package), "--locked", "--inexact"]
        pattern = re.escape(" ".join(sync))
        deadline = time.monotonic() + 60
        while True:
            found = subprocess.run(["pgrep", "-fx", pattern], capture_output=True, text=True, check=False)
            if found.returncode == 0:
                break
            self.assertIsNone(task.poll(), "update:check ended before its uv sync waited on the lock")
            self.assertLess(time.monotonic(), deadline, "no uv sync waited on the lock")
            time.sleep(0.1)
        os.kill(int(found.stdout.split()[0]), signal.SIGTERM)
        out, err = task.communicate(timeout=300)
        self.assertEqual(task.returncode, 2, out + err)
        why = f"uv sync exited {128 + signal.SIGTERM}"
        line = f"update:check: hometools could not start ({why}) — COULD NOT CHECK"
        self.assertEqual(errors(err), [line])
        self.assertEqual((out, self.calls()), ("", []))

    def test_hometools_sync_keeps_a_package_its_lock_does_not_list(self) -> None:
        # The first run builds hometools' venv; the second syncs it with the extra package in it.
        self.assertEqual(self.check(outdated(), {"stdout": "{}\n"}, {})[0], 0)
        extra = self.extra_package()
        code, out, err = self.check(outdated(), {"stdout": "{}\n"}, {})
        self.assertEqual(code, 0, out + err)
        self.assertTrue(extra.is_dir(), err)


class AllTest(UpdateTasksTest):
    def test_update_all_runs_brew_before_mise_and_every_leaf_before_its_own_run(
        self,
    ) -> None:
        native = {name: Path.home() / ".local/bin" / name for name in NATIVE}
        for name, program in native.items():
            if not program.exists():
                self.skipTest(f"no native {name} at {program}")
        stood_in = ["brew update", "brew upgrade --yes", "mise doctor"]
        stood_in += [UPDATE_MISE, "update_claude.py"]
        stood_in += [f"{name} update" for name in NATIVE]
        versions = {f"{n} --version": {"real": str(p)} for n, p in native.items()}
        real = {PINNED: REAL, VERIFY: REAL} | versions
        self.answer(real | {call: {} for call in stood_in})
        code, out, err = self.run_task("update:all")
        self.assertEqual(code, 0, out + err)
        # The leaf printed what the native install answers, under its task's prefix.
        for name, program in native.items():
            version = subprocess.run(
                [program, "--version"],
                env=self.env,
                capture_output=True,
                text=True,
                check=True,
            )
            line = f"[update:{name}] {version.stdout.strip()}"
            self.assertIn(line, out.splitlines())
        calls = self.calls()
        # update:brew's steps in order, update:mise only after them (wait_for), every leaf's calls once, and
        # update:all's own run last.
        brew = [call for call in calls if call.startswith("brew ")] + [VERIFY]
        self.assertEqual(brew, BREW_STEPS)
        self.assertEqual(sorted(calls[:-2]), sorted([*BREW_STEPS, *LEAF_CALLS]))
        self.assertGreater(calls.index(UPDATE_MISE), calls.index(VERIFY))
        self.assertEqual(calls[-2:], ["mise doctor", VERIFY])

    def test_update_mise_alone_does_not_run_update_brew(self) -> None:
        self.answer({UPDATE_MISE: {}})
        code, out, err = self.run_task("update:mise")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.calls(), [UPDATE_MISE])


if __name__ == "__main__":
    unittest.main()
