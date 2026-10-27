"""External acceptance contract for d2sg; synthetic fixtures stay in scratch Git."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = (
    ".gitignore", "README.md", "mise.toml", "mise.lock", "hk.pkl",
    ".betterleaks.toml", "mise/config.toml", "mise/mise.lock",
    "scripts/secret_guard.py", "tests/test_secret_guard.py",
)
REQUIRED = tuple(p for p in ALLOWED if p not in (
    "mise.lock", "mise/config.toml", "mise/mise.lock"))
MAPPINGS = {"~/.config/mise/" + name: "mise/" + name
            for name in ("config.toml", "mise.lock")}
PINS = {"hk": "2.9.0", "aqua:betterleaks/betterleaks": "1.9.0",
        "fnox": "1.43.0", "python": "3.14.8"}
DENIED = (
    "age.txt", "keys.txt", "identity.agekey", "client.key", "client.pem",
    "secrets.sops.json", "secrets.json", "config.toml.bak",
    "config.toml.backup-old", "config.toml.orig", "config.toml~",
    "node_modules/x", "mise/age.txt", "mise/secrets.sops.json",
    "mise/config.toml.bak-20261026", "docs/x.md", "scripts/other.py",
    "tests/fixture.txt", "$HOME/x", ".codex/x", "backups/x",
    "mise/deeper/config.toml", "tests/test_secret_guard.py/child",
    "README.md/child", "arbitrary", "line\nbreak", "tab\tfile",
)
RULES = ("path-not-allowed", "name-denied", "age-identity", "private-key",
         "sops-content", "file-mode", "nested-git", "dotfiles-mapping",
         "tool-pin", "scanner-missing")


def fixture(kind):
    """Build scanner-shaped text without embedding a complete match in source."""
    if kind.startswith("age"):
        alphabet = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        sample = "-".join(("AGE", "SECRET", "KEY")) + "-1"
        sample += "".join(alphabet[i % len(alphabet)] for i in range(58))
        return sample.lower() if kind == "age-lower" else sample
    if kind == "sops-marker":
        return "ENC[" + "AES256_GCM," + "data:synthetic,tag:synthetic]"
    if kind == "sops-json":
        return json.dumps({"sops": {"version": "3.9.0"}})
    if kind == "sops-yaml":
        return "sops" + ":\n  version: '3.9.0'\n"
    if kind == "sops-toml":
        return "[" + "sops" + "]\nversion = '3.9.0'\n"
    label = {"rsa": "RSA PRIVATE", "openssh": "OPENSSH PRIVATE",
             "encrypted": "ENCRYPTED PRIVATE", "pkcs8": "PRIVATE",
             "pgp": "PGP PRIVATE KEY BLOCK"}[kind]
    return "-----" + "BEGIN " + label + ("" if kind == "pgp" else " KEY") + "-----"


class ScratchCase(unittest.TestCase):
    def policy(self, name):
        path = ROOT / name
        self.assertTrue(path.is_file(), "missing policy file: " + name)
        return path.read_bytes()

    def make_repo(self, files=REQUIRED):
        for name in files:
            self.policy(name)
        self.tmp = Path(tempfile.mkdtemp(prefix="d2sg-test-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        home = self.tmp / "home"
        home.mkdir()
        empty = self.tmp / "empty-config"
        empty.touch()
        self.samples = []
        # Construct an environment; do not inherit Git settings or credentials.
        self.git_bin = shutil.which("git", path=os.defpath)
        self.assertIsNotNone(self.git_bin, "native Git prerequisite missing")
        tool_dirs = {str(Path(p).parent) for tool in ("betterleaks", "fnox")
                     if (p := shutil.which(tool))}
        tool_dirs.add(str(Path(self.git_bin).parent))
        tool_dirs.add(str(Path(sys.executable).parent))
        self.env = {
            "PATH": os.pathsep.join(sorted(tool_dirs) + ["/usr/bin", "/bin"]),
            "HOME": str(home), "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_CACHE_HOME": str(home / "cache"), "TMPDIR": str(self.tmp),
            "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0", "HK": "0", "LC_ALL": "C",
            "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test" + "@" + "example.invalid",
            "GIT_COMMITTER_EMAIL": "test" + "@" + "example.invalid",
        }
        self.git("init", "--quiet", "--initial-branch=main", "--template=")
        for name in files:
            self.write(name, self.policy(name))
        self.git("add", "--force", "--", *files)

    def git(self, *args, data=None):
        result = subprocess.run(
            [self.git_bin, "-c", "core.hooksPath=/dev/null", "-c",
             "core.excludesFile=/dev/null", "-c", "commit.gpgsign=false",
             "-c", "tag.gpgsign=false", *args], cwd=self.repo,
            env=self.env, input=data, capture_output=True, timeout=30,
        )
        output = result.stdout + result.stderr
        for sample in self.samples:
            self.assertFalse(sample.encode() in output, "fixture text leaked")
        self.assertEqual(result.returncode, 0, "scratch Git command failed")
        return result.stdout.decode().strip()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def stage(self, name, content):
        self.write(name, content)
        self.git("add", "--force", "--", name)

    def commit(self):
        self.git("commit", "--quiet", "--allow-empty", "-m", "synthetic fixture")
        return self.git("rev-parse", "HEAD")

    def guard(self, mode="index", updates="", extra=()):
        result = subprocess.run(
            [sys.executable, "-I", str(self.repo / "scripts/secret_guard.py"),
             mode, "--repo", str(self.repo), *extra], cwd=self.tmp,
            env=self.env, input=updates.encode(), capture_output=True, timeout=60,
        )
        output = result.stdout + result.stderr
        for sample in self.samples:
            self.assertFalse(sample.encode() in output, "fixture text leaked")
        return result

    def expect(self, result, code=0, rule=None, path=None, commit=None):
        self.assertEqual(result.returncode, code, "unexpected guard exit code")
        if rule:
            stderr = result.stderr.decode("utf-8", "replace")
            lines = stderr.splitlines()
            self.assertTrue(lines, "missing diagnostic")
            for line in lines:
                self.assertRegex(line, r"^d2sg: (" + "|".join(RULES) + r"): ")
            self.assertIn("d2sg: " + rule + ": ", stderr)
            if path:
                self.assertIn(path, stderr)
            if commit:
                self.assertIn(commit, stderr)

    def blocked(self, result):
        self.assertIn(result.returncode, (1, 2), "guard silently accepted input")

    def secret(self, kind="age"):
        sample = fixture(kind)
        self.samples.append(sample)
        return sample

    def updates(self, tip, remote=None, suffix="main"):
        return f"refs/heads/{suffix} {tip} refs/heads/{suffix} {remote or '0' * 40}\n"


class PolicyTests(ScratchCase):
    def test_ignore_exact_candidates(self):
        self.make_repo((".gitignore",))
        for i, path in enumerate(ALLOWED + DENIED):
            with self.subTest(case=i):
                result = subprocess.run(
                    [self.git_bin, "-c", "core.hooksPath=/dev/null", "check-ignore",
                     "--no-index", "--quiet", "--", path], cwd=self.repo,
                    env=self.env, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0 if path in DENIED else 1)

    def test_mapping_exact_and_disabled(self):
        config = tomllib.loads(self.policy("mise.toml").decode())
        self.assertEqual(set(config["dotfiles"]), set(MAPPINGS))
        for target, source in MAPPINGS.items():
            self.assertEqual(config["dotfiles"][target],
                             {"source": source, "mode": "symlink", "enabled": False})
            self.assertFalse((ROOT / source).exists(), "unit source must remain absent")
        forbidden = {"dotfile_groups", "include", "autosave", "template", "track",
                     "track-local", "symlink-each", "copy"}

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, forbidden)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, str):
                self.assertNotIn(value, forbidden)
        walk(config)

    def test_tool_pins(self):
        config = tomllib.loads(self.policy("mise.toml").decode())
        self.assertEqual(config["tools"], PINS)
        self.assertFalse((ROOT / "mise.lock").exists(), "unit root lock must be absent")

    def test_tasks(self):
        config = tomllib.loads(self.policy("mise.toml").decode())
        for name, mode in (("guard", "index"), ("guard:history", "history")):
            command = config["tasks"][name]["run"]
            self.assertIsInstance(command, str)
            argv = shlex.split(command)
            self.assertIn(argv[0], ("python", "python3"))
            self.assertEqual(argv[1:], ["scripts/secret_guard.py", mode])
        command = config["tasks"]["test"]["run"]
        self.assertIsInstance(command, str)
        argv = shlex.split(command)
        self.assertIn("unittest", argv)
        self.assertIn("discover", argv)
        self.assertIn("tests", argv)
        self.assertIn("test_secret_guard.py", argv)

    def test_scanner_defaults_extended(self):
        config = tomllib.loads(self.policy(".betterleaks.toml").decode())
        self.assertIs(config["extend"]["useDefault"], True)
        self.assertFalse(config["extend"].get("disabledRules"))
        rules = config.get("rules", [])
        self.assertTrue(any("sops" in rule["id"] for rule in rules))
        self.assertFalse(config.get("allowlist") or config.get("allowlists"))

    def test_hooks_required_commands(self):
        text = self.policy("hk.pkl").decode()
        # Text evidence is deliberately weaker than evaluating Pkl/native hooks.
        self.assertIn("hk@2.9.0#/Config.pkl", text)
        self.assertIn("hk@2.9.0#/Builtins.pkl", text)
        for token in ("pre-commit", "pre-push", "Builtins.betterleaks",
                      "scripts/secret_guard.py", "index", "pre-push", "hook_stdin",
                      "betterleaks", "git", "--staged", "--config",
                      ".betterleaks.toml", "--redact=100", "--ignore-gitleaks-allow",
                      "--exit-code=1", "fnox", "scan"):
            self.assertIn(token, text)
        self.assertRegex(text, r'stash\s*=\s*"none"')
        self.assertRegex(text, r"fix\s*=\s*false")
        self.assertNotRegex(text, r"\|\|\s*true|stash\s*=\s*\"(?:git|patch)\"")


class GuardTests(ScratchCase):
    def setUp(self):
        self.make_repo()

    def test_clean_index(self):
        self.expect(self.guard())

    def test_clean_history(self):
        self.commit()
        self.expect(self.guard("history"))

    def test_clean_new_branch_push(self):
        self.expect(self.guard("pre-push", self.updates(self.commit())))

    def test_clean_existing_branch_push(self):
        base = self.commit()
        self.stage("README.md", "reviewed\n")
        self.expect(self.guard("pre-push", self.updates(self.commit(), base)))

    def test_deletion_only_push(self):
        base = self.commit()
        self.expect(self.guard("pre-push", self.updates("0" * 40, base)))

    def test_unchanged_tracked_extra(self):
        self.stage("docs/x.md", "ordinary\n")
        self.commit()
        self.stage("README.md", "new change\n")
        self.expect(self.guard(), 1, "path-not-allowed", "docs/x.md")

    def test_force_add_ignored(self):
        self.stage("docs/x.md", "ordinary\n")
        self.expect(self.guard(), 1, "path-not-allowed", "docs/x.md")

    def test_bad_index_clean_worktree(self):
        self.stage("README.md", self.secret())
        self.write("README.md", "clean unstaged bytes\n")
        self.expect(self.guard(), 1, "age-identity", "README.md")

    def test_clean_index_bad_worktree(self):
        self.write("README.md", self.secret())
        self.expect(self.guard())

    def test_symlink_source(self):
        outside = self.tmp / "harmless"
        outside.write_text("ordinary\n")
        (self.repo / "mise").mkdir()
        (self.repo / "mise/config.toml").symlink_to(outside)
        self.git("add", "--force", "mise/config.toml")
        self.expect(self.guard(), 1, "file-mode", "mise/config.toml")

    def test_symlink_source_parent(self):
        outside = self.tmp / "harmless-dir"
        outside.mkdir()
        (outside / "config.toml").write_text("ordinary\n")
        (self.repo / "mise").symlink_to(outside, target_is_directory=True)
        self.blocked(self.guard())

    def test_gitlink(self):
        oid = self.commit()
        self.git("update-index", "--add", "--cacheinfo", "160000", oid, "mise/config.toml")
        self.expect(self.guard(), 1, "file-mode", "mise/config.toml")

    def test_unexpected_executable(self):
        self.git("update-index", "--chmod=+x", "README.md")
        self.expect(self.guard(), 1, "file-mode", "README.md")

    def test_history_deleted_secret(self):
        self.commit()
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.stage("README.md", "clean again\n")
        self.commit()
        self.expect(self.guard("history"), 1, "age-identity", "README.md", bad)

    def test_push_deleted_secret(self):
        base = self.commit()
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.stage("README.md", "clean again\n")
        self.expect(self.guard("pre-push", self.updates(self.commit(), base)),
                    1, "age-identity", "README.md", bad)

    def test_violation_second_pushed_ref(self):
        base = self.commit()
        self.git("checkout", "--quiet", "-b", "second")
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.git("checkout", "--quiet", "main")
        self.git("branch", "--delete", "--force", "second")
        updates = self.updates(base) + self.updates(bad, suffix="second")
        self.expect(self.guard("pre-push", updates), 1, "age-identity", "README.md", bad)

    def test_history_non_head_ref(self):
        base = self.commit()
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.git("branch", "other", bad)
        self.git("reset", "--hard", base)
        self.expect(self.guard("history"), 1, "age-identity", "README.md", bad)

    def test_push_annotated_tag(self):
        self.commit()
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.git("tag", "-a", "synthetic", "-m", "synthetic tag")
        tag = self.git("rev-parse", "refs/tags/synthetic")
        updates = f"refs/tags/synthetic {tag} refs/tags/synthetic {'0' * 40}\n"
        self.expect(self.guard("pre-push", updates), 1, "age-identity", "README.md", bad)

    def test_history_merge_only_blob(self):
        self.commit()
        self.git("checkout", "--quiet", "-b", "side")
        self.stage("README.md", "side\n")
        self.commit()
        self.git("checkout", "--quiet", "main")
        self.stage("mise.lock", "ordinary\n")
        self.commit()
        self.git("merge", "--no-commit", "--no-ff", "side")
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.stage("README.md", "clean\n")
        self.commit()
        self.expect(self.guard("history"), 1, "age-identity", "README.md", bad)

    def test_missing_scanner(self):
        self.commit()
        bindir = self.tmp / "bin"
        bindir.mkdir()
        for tool in ("git", "fnox", "python3"):
            target = (sys.executable if tool == "python3" else
                      self.git_bin if tool == "git" else shutil.which(tool))
            self.assertIsNotNone(target, "test prerequisite missing: " + tool)
            (bindir / tool).symlink_to(target)
        self.env["PATH"] = str(bindir)
        self.expect(self.guard("history"), 2, "scanner-missing")

    def test_scanner_runtime_error(self):
        self.commit()
        bindir = self.tmp / "scanner-error"
        bindir.mkdir()
        scanner = bindir / "betterleaks"
        scanner.write_text("#!/bin/sh\nexit 7\n")
        scanner.chmod(0o755)
        self.env["PATH"] = str(bindir) + os.pathsep + self.env["PATH"]
        self.expect(self.guard("history"), 2)

    def test_unreadable_push_object(self):
        self.commit()
        self.expect(self.guard("pre-push", self.updates("1" * 40)), 2)

    def test_unreadable_index_object(self):
        self.git("update-index", "--add", "--cacheinfo", "100644", "1" * 40, "README.md")
        self.expect(self.guard(), 2)

    def test_unmerged_index(self):
        oid = self.git("hash-object", "-w", "--stdin", data=b"ordinary\n")
        self.git("update-index", "--force-remove", "README.md")
        data = "".join(f"100644 {oid} {s}\tREADME.md\n" for s in (1, 2, 3))
        self.git("update-index", "--index-info", data=data.encode())
        self.blocked(self.guard())

    def test_partial_scanner_policy(self):
        self.write(".betterleaks.toml", "[extend]\nuseDefault = false\n")
        self.blocked(self.guard())

    def test_staged_scanner_policy_tampering(self):
        clean = (self.repo / ".betterleaks.toml").read_bytes()
        self.stage(".betterleaks.toml", "[extend]\nuseDefault = false\n")
        self.write(".betterleaks.toml", clean)
        self.blocked(self.guard())

    def test_partially_staged_guard(self):
        with (self.repo / "scripts/secret_guard.py").open("a") as stream:
            stream.write("\n# unstaged policy divergence\n")
        self.blocked(self.guard())

    def test_force_push_history(self):
        base = self.commit()
        self.stage("README.md", self.secret())
        bad = self.commit()
        self.stage("README.md", "clean tip\n")
        tip = self.commit()
        self.git("checkout", "--orphan", "unrelated")
        remote = self.commit()
        self.git("checkout", "--quiet", "--force", "main")
        self.assertNotEqual(base, remote)
        self.expect(self.guard("pre-push", self.updates(tip, remote)),
                    1, "age-identity", "README.md", bad)

    def test_invalid_staged_config(self):
        self.stage("mise.toml", "[broken\n")
        self.blocked(self.guard())

    def test_usage_unknown_mode(self):
        self.expect(self.guard("unknown-mode"), 2)


# Each table entry becomes a separate test id and red-run row, not a skipped subtest.
def content_test(kind):
    def test(self):
        self.stage("README.md", self.secret(kind))
        rule = "age-identity" if kind.startswith("age") else (
            "sops-content" if kind.startswith("sops") else "private-key")
        self.expect(self.guard(), 1, rule, "README.md")
    return test


for _kind in ("age", "age-lower", "rsa", "openssh", "encrypted", "pkcs8", "pgp",
              "sops-marker", "sops-json", "sops-yaml", "sops-toml"):
    setattr(GuardTests, "test_content_" + _kind.replace("-", "_"), content_test(_kind))


def name_test(path):
    def test(self):
        self.stage(path, "ordinary\n")
        self.expect(self.guard(), 1, "name-denied", path)
    return test


for _i, _path in enumerate(DENIED[:15]):
    setattr(GuardTests, f"test_denied_name_{_i:02}", name_test(_path))


def unusual_path_test(path):
    def test(self):
        self.stage(path, "ordinary\n")
        self.expect(self.guard(), 1, "path-not-allowed")
    return test


for _i, _path in enumerate(("line\nbreak", "tab\tfile")):
    setattr(GuardTests, f"test_unusual_path_{_i:02}", unusual_path_test(_path))


def mapping_test(change):
    def test(self):
        original = (self.repo / "mise.toml").read_text()
        self.stage("mise.toml", original + "\n" + change)
        self.expect(self.guard(), 1, "dotfiles-mapping", "mise.toml")
    return test


for _i, _change in enumerate((
    '[dotfiles."~/.config/mise"]\nsource = "mise"\nmode = "symlink"',
    '[dotfiles."~/.config/other"]\nsource = "mise/config.toml"\nmode = "symlink"',
    '[dotfile_groups.extra]\nroot = "mise"\ntarget = "~/.config/mise"',
    '[dotfiles."~/.config/wild/*"]\nsource = "mise/*"\nmode = "symlink"',
    *('[dotfiles."~/.config/mise"]\nsource = "mise"\nmode = "' + mode + '"'
      for mode in ("symlink-each", "copy", "template", "track", "track-local")),
)):
    setattr(GuardTests, f"test_bad_mapping_{_i:02}", mapping_test(_change))


def nested_test(is_dir):
    def test(self):
        path = self.repo / "mise/.git"
        path.parent.mkdir()
        path.mkdir() if is_dir else path.write_text("gitdir: harmless\n")
        self.expect(self.guard(), 1, "nested-git", "mise/.git")
    return test


for _i in range(2):
    setattr(GuardTests, f"test_nested_git_{_i:02}", nested_test(bool(_i)))


def malformed_test(value):
    def test(self):
        self.commit()
        self.expect(self.guard("pre-push", value), 2)
    return test


for _i, _value in enumerate(("", "\n", "too few fields\n",
                            "refs/heads/main nope refs/heads/main " + "0" * 40 + "\n",
                            " ".join(("x", "0" * 40, "y", "0" * 40, "extra")) + "\n")):
    setattr(GuardTests, f"test_malformed_push_{_i:02}", malformed_test(_value))


def unsafe_blob_test(data):
    def test(self):
        self.stage("README.md", data)
        self.blocked(self.guard())
    return test


for _i, _data in enumerate((b"prefix\x00suffix", b"x" * (6 * 1024 * 1024))):
    setattr(GuardTests, f"test_unscannable_blob_{_i:02}", unsafe_blob_test(_data))


def pin_test(tool, version):
    def test(self):
        text = (self.repo / "mise.toml").read_text()
        pattern = r'''(?m)^(\s*"?''' + re.escape(tool) + r'''"?\s*=\s*)['"][^'\"]*['"]'''
        changed, count = re.subn(pattern, lambda m: m[1] + '"' + version + '"', text)
        self.assertEqual(count, 1, "pin fixture requires one tools entry")
        self.stage("mise.toml", changed)
        self.expect(self.guard(), 1, "tool-pin", "mise.toml")
    return test


for _i, _tool in enumerate(PINS):
    setattr(GuardTests, f"test_wrong_pin_{_i:02}", pin_test(_tool, "latest"))


def extra_policy_test(path):
    def test(self):
        self.write(path, "synthetic\n")
        self.blocked(self.guard())
    return test


for _i, _path in enumerate((".gitleaksignore", ".betterleaksignore")):
    setattr(GuardTests, f"test_untracked_scanner_ignore_{_i:02}", extra_policy_test(_path))


if __name__ == "__main__":
    unittest.main()
