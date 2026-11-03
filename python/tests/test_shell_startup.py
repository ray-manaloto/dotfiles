"""Shell startup: real zsh in a temporary HOME, through the four ways a shell starts."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

UNIX_HOME = Path(__file__).resolve().parents[2] / "unix/home"
STARTUP_FILES = (
    ".zshenv",
    ".zprofile",
    ".zshrc",
    ".zshrc.d/10-zsh.zsh",
    ".zshrc.d/90-mise.zsh",
    ".config/zsh/path.zsh",
)

# The macOS zsh reads the real /etc/zprofile (path_helper) and /etc/zshrc (HISTFILE).
ZSH = "/bin/zsh"
MODES = (("-c",), ("-l", "-c"), ("-i", "-c"), ("-l", "-i", "-c"))
INTERACTIVE = MODES[2:]

RETIRED_PATH = "~/.opencode/bin:~/.cache/oh-my-opencode/bin"
INHERITED_PATH = f"{RETIRED_PATH}:/usr/bin:/bin:/usr/sbin:/sbin:{RETIRED_PATH}"
RETIRED_ENTRY = re.compile(r"/(?:\.opencode|oh-my-opencode)(?:/|$)", re.MULTILINE)
# What `mise run` and an activated venv leave first on PATH for the commands they start.
VENV_BIN = "~/.venv/bin"
KEG_BIN = "~/homebrew/opt/llvm/bin"
TOOL_PATH = f"{VENV_BIN}:{KEG_BIN}:{INHERITED_PATH}"
# What a bare spawn inherits: nothing put first, only the system folders.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
# The shims hold both too, which is how they shadow a venv and a keg.
SHIMS = "~/.local/share/mise/shims"
STARSHIP = shutil.which("starship")
FAKE_TOOLS = (
    f"{VENV_BIN}/python3",
    f"{KEG_BIN}/clang",
    f"{SHIMS}/python3",
    f"{SHIMS}/clang",
)
# path.zsh's declared order: a login shell has these around whatever else it inherited.
LOGIN_FIRST = [
    "~/.local/share/mise/shims",
    "~/.local/bin",
    "/usr/local/share/mise/shims",
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
]
LOGIN_LAST = [
    "~/.docker/bin",
    "~/Library/Application Support/JetBrains/Toolbox/scripts",
    "/Applications/Obsidian.app/Contents/MacOS",
    "~/.antigravity-ide/antigravity-ide/bin",
]
RETIRED_NAME = re.compile(
    r"^(?:GOBIN|FNOX_CONFIG_DIR|FNOX_AGE_KEY_FILE|SOPS_AGE_KEY_FILE|UV_CACHE_DIR"
    r"|XDG_RUNTIME_DIR)$",
    re.MULTILINE,
)
# `brew` as a traced command word: `[[ -x /opt/homebrew/bin/brew ]]` spawns nothing.
BREW_COMMAND = re.compile(
    r"\+\S*> (?:(?:command|exec|noglob|(?:\S*/)?env) )*(?:\S*/)?brew(?: |$)",
    re.MULTILINE,
)

# Records each call, then runs the real mise. Its hooks call the real binary directly.
REAL_MISE = shutil.which("mise")
MISE = """\
#!/bin/sh
printf '%s %s\\n' "${MISE_ENV_CACHE:-unset}" "$*" >> "$HOME/mise-calls"
"""
# MISE_SHELL is exported by the activate output, so an unevaluated one is caught.
MISE_STATE = "print -r -- ${MISE_ENV_CACHE-unset} ${MISE_SHELL-unset}"


class ShellStartupTest(unittest.TestCase):
    def zsh(
        self,
        mode: tuple[str, ...],
        command: str = "true",
        *,
        mise: bool = True,
        path: str = INHERITED_PATH,
        xdg: bool = True,
        starship: bool = False,
    ) -> tuple[int, str, str, list[str]]:
        """Run zsh in a fresh HOME; code, out, err, mise calls. `~` stands for that HOME."""
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            for name in STARTUP_FILES:
                self.assertTrue((UNIX_HOME / name).is_file(), f"missing {name}")
                (home / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(UNIX_HOME / name, home / name)
            (home / ".zshrc.d/50-drop-in.zsh").write_text("export DROP_IN=1\n")
            (home / ".local/share/mise/shims").mkdir(parents=True)
            (home / ".local/bin").mkdir()
            if mise:
                (home / ".local/bin/mise").write_text(
                    f'{MISE}exec "{REAL_MISE}" "$@"\n'
                )
                (home / ".local/bin/mise").chmod(0o755)
            if starship:
                (home / ".local/bin/starship").symlink_to(STARSHIP)
            for tool in FAKE_TOOLS:
                fake = Path(tool.replace("~", str(home)))
                fake.parent.mkdir(parents=True, exist_ok=True)
                fake.symlink_to(shutil.which(fake.name, path="/usr/bin:/bin"))
            done = subprocess.run(
                [ZSH, *mode, command],
                env={
                    "HOME": str(home),
                    **(
                        {
                            "XDG_CONFIG_HOME": str(home / ".config"),
                            "XDG_DATA_HOME": str(home / ".local/share"),
                            "XDG_STATE_HOME": str(home / ".local/state"),
                            "XDG_CACHE_HOME": str(home / ".cache"),
                        }
                        if xdg
                        else {}
                    ),
                    "PATH": path.replace("~", str(home)),
                    "TERM": "xterm-256color",
                },
                cwd=home,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            calls = home / "mise-calls"
            return (
                done.returncode,
                done.stdout.replace(str(home), "~"),
                done.stderr,
                calls.read_text().splitlines() if calls.exists() else [],
            )

    def test_a_login_with_no_xdg_paths_gets_the_defaults(self) -> None:
        names = "$XDG_CONFIG_HOME $XDG_CACHE_HOME $XDG_DATA_HOME $XDG_STATE_HOME"
        out = self.zsh(("-l", "-c"), f"print -rl -- {names}", xdg=False)[1]
        self.assertEqual(
            out.splitlines(),
            ["~/.config", "~/.cache", "~/.local/share", "~/.local/state"],
        )

    def test_path_order(self) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                path = self.zsh(mode, "print -rl -- $path")[1]
                entries = path.splitlines()
                # Real activate may put tool paths and the system shims among these.
                order = [
                    entries.index(entry)
                    for entry in (
                        "~/.local/share/mise/shims",
                        "~/.local/bin",
                        "/opt/homebrew/bin",
                    )
                ]
                self.assertEqual(order, sorted(order))
                self.assertEqual(RETIRED_ENTRY.findall(path), [])

    def test_login_shells_reorder_and_others_keep_inherited_tools_first(self) -> None:
        print_path = "print -rl -- $path"
        login = self.zsh(("-l", "-c"), print_path, path=TOOL_PATH)[1].splitlines()
        self.assertEqual(login[: len(LOGIN_FIRST)], LOGIN_FIRST)
        self.assertEqual(login[-len(LOGIN_LAST) :], LOGIN_LAST)

        command = f"whence -p python3 clang; {print_path}"
        lines = self.zsh(("-c",), command, path=TOOL_PATH)[1].splitlines()
        self.assertEqual(lines[:2], [f"{VENV_BIN}/python3", f"{KEG_BIN}/clang"])
        entries = lines[2:]
        self.assertEqual(entries[:2], [VENV_BIN, KEG_BIN])
        for entry in (*LOGIN_FIRST, *LOGIN_LAST):
            self.assertIn(entry, entries)

    def test_a_child_of_a_login_shell_keeps_its_path(self) -> None:
        print_path = "print -r -- $PATH"
        login = self.zsh(("-l", "-c"), print_path, path=TOOL_PATH)[1].strip()
        child = self.zsh(("-c",), print_path, path=login)[1].strip()
        self.assertEqual(child.split(":"), login.split(":"))

    def test_a_bare_system_path_gets_the_shims_ahead_of_usr_bin(self) -> None:
        path = self.zsh(("-c",), "print -rl -- $path", path=SYSTEM_PATH)[1]
        entries = path.splitlines()
        ahead = entries[: entries.index("/usr/bin")]
        self.assertIn(SHIMS, ahead)
        self.assertIn("~/.local/bin", ahead)

    def test_startup_is_silent(self) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                self.assertEqual(self.zsh(mode, "print -r -- ok")[:3], (0, "ok\n", ""))

    def test_mise_activates_once_in_interactive_shells(self) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                _, out, _, calls = self.zsh(mode, MISE_STATE)
                activations = [c for c in calls if "activate" in c]
                if mode in INTERACTIVE:
                    self.assertEqual(activations, ["1 activate zsh"])
                    self.assertEqual(out, "1 zsh\n")
                else:
                    self.assertEqual(activations, [])
                    self.assertEqual(out, "unset unset\n")
                missing = self.zsh(mode, MISE_STATE, mise=False)[1]
                self.assertEqual(missing, "unset unset\n")

    def test_retired_names_stay_unset_and_brew_never_runs(self) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                names = self.zsh(mode, "print -rl -- ${(k)parameters}")[1]
                self.assertEqual(RETIRED_NAME.findall(names), [])
                self.assertEqual(BREW_COMMAND.findall(self.zsh(("-x", *mode))[2]), [])

    def test_interactive_fpath_holds_homebrew_site_functions(self) -> None:
        for mode in INTERACTIVE:
            with self.subTest(mode=mode):
                fpath = self.zsh(mode, "print -rl -- $fpath")[1].splitlines()
                self.assertIn("/opt/homebrew/share/zsh/site-functions", fpath)

    def test_interactive_histfile_survives_etc_zshrc(self) -> None:
        for mode in INTERACTIVE:
            with self.subTest(mode=mode):
                histfile = self.zsh(mode, 'print -r -- "$HISTFILE"')[1]
                self.assertEqual(histfile, "~/.local/state/zsh/history\n")

    def test_optional_tools(self) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                bare = self.zsh(mode, mise=False)
                self.assertEqual(bare[:3], (0, "", ""))

    def test_interactive_shells_use_plain_zsh_completion(self) -> None:
        command = (
            "print -r -- ${ZSH-unset} ${ZSH_THEME-unset} ${+functions[compdef]}; "
            "zstyle -s ':completion:*' menu style; print -r -- $style"
        )
        for mode in INTERACTIVE:
            with self.subTest(mode=mode):
                self.assertEqual(self.zsh(mode, command)[1], "unset unset 1\nselect\n")

    def test_starship_sets_the_interactive_prompt(self) -> None:
        self.assertIsNotNone(STARSHIP, "starship must be on PATH")
        for mode in INTERACTIVE:
            with self.subTest(mode=mode):
                code, out, err, _ = self.zsh(mode, "print -r -- $STARSHIP_SHELL", starship=True)
                self.assertEqual((code, out, err), (0, "zsh\n", ""))

    def test_drop_ins_load_and_no_claude_mem_alias(self) -> None:
        for mode in INTERACTIVE:
            with self.subTest(mode=mode):
                self.assertEqual(self.zsh(mode, "print -r -- $DROP_IN")[1], "1\n")
        for mode in MODES:
            with self.subTest(mode=mode):
                aliases = self.zsh(mode, "print -rl -- ${(k)aliases}")[1].splitlines()
                self.assertNotIn("claude-mem", aliases)


if __name__ == "__main__":
    unittest.main()
