"""add, update and remove: the pin and lock in a dotfiles worktree's global config, and the plugin in Claude Code."""

import contextlib
import json
import subprocess
from pathlib import Path

import pytest

from .conftest import REPO, Lsp, Typescript, World

CONFIG = "unix/home/.config/mise/config.toml"
PLUGIN = "typescript-native-lsp@dotfiles"


def git(folder: Path, *args: str) -> None:
    # No hooks (the global ones would run this repository's checks on a scratch commit) and no signing key.
    settings = [
        "user.name=tests",
        "user.email=tests@example.invalid",
        "core.hooksPath=/dev/null",
        "commit.gpgsign=false",
    ]
    flags = [flag for setting in settings for flag in ("-c", setting)]
    subprocess.run(["git", *flags, "-C", str(folder), *args], capture_output=True, check=True)


def checkout(root: Path, *, dotfiles: bool = True) -> tuple[Path, Path]:
    """A main checkout and a linked worktree of it; a dotfiles one holds the global mise config."""
    main = root / "dots"
    (main / "unix/home/.config/mise").mkdir(parents=True)
    (main / (CONFIG if dotfiles else "README.md")).write_text("[settings]\npin = true\n\n[tools]\n")
    git(main, "init", "-q", "-b", "main")
    git(main, "add", ".")
    git(main, "commit", "-q", "-m", "start")
    git(main, "worktree", "add", "-q", str(root / "dots.wt"), "-b", "wt")
    return main, root / "dots.wt"


def plugin() -> dict[str, object] | None:
    listed = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True, check=True)
    return next((entry for entry in json.loads(listed.stdout) if entry["id"] == PLUGIN), None)


def test_add_pins_locks_and_turns_the_plugin_on(world: World, lsp: Lsp, typescript: Typescript) -> None:
    world.claude_cli("marketplace", "add", str(REPO), "--scope", "user")
    _, worktree = checkout(world.root)
    calls = world.stand_in(
        {
            ("use", "-g", "npm:typescript@latest"): {
                "real": True,
                "argv": ["use", "-g", f"npm:typescript@{typescript.version}"],
            },
            ("lock", "--global", "npm:typescript"): {"real": True},
        }
    )
    with contextlib.chdir(worktree / "unix"):
        installed = lsp("add", "typescript")
        assert installed.code == 0, installed.out
        assert f'"npm:typescript" = "{typescript.version}"' in (worktree / CONFIG).read_text()
        assert f'version = "{typescript.version}"' in (worktree / "unix/home/.config/mise/mise.lock").read_text()
        assert installed.out.splitlines()[-1].startswith("  ok  plugin: install: ")
        assert "['" not in installed.out
        assert installed.out.splitlines()[-1].endswith(f"undo: claude plugin uninstall {PLUGIN}")
        assert (plugin() or {})["enabled"] is True
        # With a mise.lock, mise use reinstalls from it and fetches npm attestations: the network. The config already
        # pins this version, so the stand-in answers as that use would.
        pinned = f"mise {worktree / CONFIG} tools: npm:typescript@{typescript.version}\n"
        world.stand_in(
            {
                ("use", "-g", "npm:typescript@latest"): {"stderr": pinned},
                ("lock", "--global", "npm:typescript"): {"real": True},
            }
        )
        world.claude_cli("disable", PLUGIN, "--scope", "user")
        enabled = lsp("add", "typescript")
        assert enabled.code == 0, enabled.out
        assert enabled.out.splitlines()[-1].startswith("  ok  plugin: enable: ")
        assert enabled.out.splitlines()[-1].endswith(f"undo: claude plugin disable {PLUGIN}")
        assert (plugin() or {})["enabled"] is True
        again = lsp("add", "typescript")
        assert again.code == 0, again.out
        assert again.out.splitlines()[-1] == f"  ok  plugin: {PLUGIN} already enabled"
    assert [json.loads(line)[1] for line in calls.read_text().splitlines()] == ["use", "lock"] * 3


def test_update_bumps_and_locks_and_leaves_the_plugin(world: World, lsp: Lsp, typescript: Typescript) -> None:
    _, worktree = checkout(world.root)
    (worktree / CONFIG).write_text(f'[settings]\npin = true\n\n[tools]\n"npm:typescript" = "{typescript.version}"\n')
    world.stand_in(
        {
            ("upgrade", "--bump", "npm:typescript"): {"real": True},
            ("lock", "--global", "npm:typescript"): {"real": True},
        }
    )
    with contextlib.chdir(worktree):
        result = lsp("update", "typescript")
    assert result.code == 0, result.out
    upgrade, lock, plugin_line = result.out.splitlines()[1:]
    assert upgrade == "  ok  mise upgrade --bump: npm:typescript: mise All tools are up to date"
    assert lock.startswith("  ok  mise lock --global: npm:typescript: ")
    assert plugin_line == f"  ok  plugin: {PLUGIN} unchanged"


def test_remove_unpins_and_turns_the_plugin_off(world: World, lsp: Lsp, typescript: Typescript) -> None:
    world.dotfiles()
    _, worktree = checkout(world.root)
    (worktree / CONFIG).write_text(f'[settings]\npin = true\n\n[tools]\n"npm:typescript" = "{typescript.version}"\n')
    with contextlib.chdir(worktree):
        result = lsp("remove", "typescript")
    assert result.code == 0, result.out
    assert "npm:typescript" not in (worktree / CONFIG).read_text()
    assert result.out.splitlines()[-1].endswith(f"undo: claude plugin enable {PLUGIN}")
    assert (plugin() or {})["enabled"] is False


def test_a_missing_mise_fails_its_steps_and_leaves_the_plugin(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    _, worktree = checkout(world.root)
    world.without("mise")
    with contextlib.chdir(worktree):
        result = lsp("remove", "typescript")
    assert result.code == 1
    assert result.out.splitlines()[1:] == [
        "  FAIL  mise unuse -g: npm:typescript: mise: No such file or directory",
        f"  FAIL  plugin: {PLUGIN} not changed: a mise step failed",
    ]
    assert (plugin() or {})["enabled"] is True


def test_changes_go_only_into_a_dotfiles_worktree(world: World, lsp: Lsp) -> None:
    plain = world.root / "plain"
    plain.mkdir()
    main, worktree = checkout(world.root / "dots")
    _, other = checkout(world.root / "other", dotfiles=False)
    cases = [
        (plain, f"{plain} is not in a git checkout: run add, update and remove from a dotfiles worktree"),
        (other, f"{other.resolve()} is not a dotfiles checkout (no {CONFIG})"),
        (
            main,
            (
                f"{main.resolve()} is the main checkout, which only moves to origin/main: "
                "run this from a dotfiles worktree"
            ),
        ),
    ]
    for folder, error in cases:
        with contextlib.chdir(folder):
            result = lsp("add", "typescript")
        assert (result.code, result.out, result.error()) == (2, "", error)
    assert "npm:typescript" not in (main / CONFIG).read_text()
    assert "npm:typescript" not in (worktree / CONFIG).read_text()


@pytest.mark.usefixtures("world")
def test_a_bootstrap_server_is_changed_with_mise_bootstrap(lsp: Lsp) -> None:
    result = lsp("add", "clangd")
    assert (result.code, result.error()) == (
        2,
        "brew:llvm is a [bootstrap.packages] entry: change it with mise bootstrap packages",
    )
