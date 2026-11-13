"""status, which, has-update and conflicts: what mise and Claude Code report, read through their own commands."""

import json
import unicodedata

import pytest

from .conftest import Lsp, Typescript, World, needs_brew

TS = {"typescript": {"command": "no-such-lsp-server", "extensionToLanguage": {".ts": "typescript"}}}


def test_status_and_which_pass_with_the_mise_tool_and_the_enabled_plugin(
    world: World, lsp: Lsp, typescript: Typescript
) -> None:
    world.dotfiles()
    status = lsp("status", "typescript")
    assert status.code == 0
    lines = status.out.splitlines()
    assert lines[0] == "ok  status typescript"
    assert lines[1].startswith(f"  ok  mise: npm:typescript {typescript.version} at ")
    assert lines[2] == "  ok  plugin: typescript-native-lsp@dotfiles (user)"
    assert lines[3].startswith("  ok  command: sh -c ")
    which = lsp("which", "typescript", "--json")
    assert which.code == 0
    (report,) = which.json()["reports"]
    assert [check["name"] for check in report["checks"]] == ["plugin", "command", "extensions", "mise"]
    assert report["checks"][2]["detail"] == ".cjs, .cts, .js, .jsx, .mjs, .mts, .ts, .tsx"


def test_status_fails_without_the_mise_tool_or_the_plugin(world: World, lsp: Lsp) -> None:
    world.mise("[tools]\n")
    for action in ("status", "which"):
        result = lsp(action, "typescript")
        assert result.code == 1
        assert "  FAIL  mise: npm:typescript is not an installed global mise tool" in result.out
        assert "  FAIL  plugin: typescript-native-lsp@dotfiles is not installed" in result.out


def test_status_fails_for_a_disabled_plugin(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    world.claude_cli("disable", "typescript-native-lsp@dotfiles", "--scope", "user")
    result = lsp("status", "typescript")
    assert (result.code, result.out.splitlines()[2]) == (1, "  FAIL  plugin: typescript-native-lsp@dotfiles (user)")


def test_a_plugin_installed_only_for_a_project_is_not_enabled_for_every_folder(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    world.claude_cli("uninstall", "typescript-native-lsp@dotfiles", "--scope", "user")
    world.claude_cli("install", "typescript-native-lsp@dotfiles", "--scope", "project")
    result = lsp("status", "typescript")
    # mise run lsp checks the user-scope setup; a project-scope entry is reported, and it is off outside its project.
    assert "  FAIL  plugin: typescript-native-lsp@dotfiles (project)" in result.out


def test_status_names_a_plugin_without_the_server(world: World, lsp: Lsp) -> None:
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": {"other": TS["typescript"]}}})
    result = lsp("status", "typescript")
    assert "  FAIL  lspServers: typescript-native-lsp@dotfiles declares no typescript" in result.out


def test_which_shows_the_command_with_the_plugin_root_and_where_it_resolves(world: World, lsp: Lsp) -> None:
    server = {"command": "${CLAUDE_PLUGIN_ROOT}/bin/server", "extensionToLanguage": {".ts": "typescript"}}
    world.market("dotfiles", {"typescript-native-lsp": {"manifest": {"typescript": server}}})
    result = lsp("which", "typescript")
    (command,) = [line for line in result.out.splitlines() if "command:" in line]
    assert command.startswith(f"  FAIL  command: {world.claude}/plugins/cache/dotfiles/typescript-native-lsp/")
    assert command.endswith("/bin/server (not on PATH)")


def test_conflicts_names_each_extension_two_enabled_plugins_claim(
    world: World, lsp: Lsp, tmp_path_factory: pytest.TempPathFactory
) -> None:
    world.dotfiles()
    claim = {"command": "x", "extensionToLanguage": {".ts": "typescript"}}
    folder = world.market(
        "tests",
        {
            "manifest-ts": {"manifest": {"ts": claim}},
            "entry-z": {"entry": {"z": {"command": "x", "extensionToLanguage": {".zz": "z"}}}},
            "off": {"lsp": {"ts": claim}},
            "plain": {},
            "gone": {},
        },
    )
    world.claude_cli("disable", "off@tests", "--scope", "user")
    # A plugin its marketplace no longer lists, one whose marketplace has no listing, and one from a session's
    # plugin folder (an @inline plugin, from no known marketplace) declare no server.
    listing = json.loads((folder / ".claude-plugin/marketplace.json").read_text())
    listing["plugins"] = [plugin for plugin in listing["plugins"] if plugin["name"] != "gone"]
    (folder / ".claude-plugin/marketplace.json").write_text(json.dumps(listing))
    bare = world.market("bare", {"lonely": {}})
    (bare / ".claude-plugin/marketplace.json").unlink()
    inline = tmp_path_factory.mktemp("inline") / "session-plugin"
    (inline / ".claude-plugin").mkdir(parents=True)
    (inline / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "session-plugin", "version": "1.0.0"}))
    world.monkeypatch.setenv("CLAUDE_CODE_PLUGIN_DIRS", str(inline))
    result = lsp("conflicts")
    assert result.code == 1
    lines = result.out.splitlines()
    assert lines[0] == "FAIL  conflicts *"
    assert "  FAIL  .ts: manifest-ts@tests, typescript-native-lsp@dotfiles" in lines
    assert "  ok  .zz: entry-z@tests" in lines
    assert "  ok  .tsx: typescript-native-lsp@dotfiles" in lines


def test_has_update_reads_mise_outdated(world: World, lsp: Lsp) -> None:
    call = ("outdated", "--global", "--bump", "--json", "npm:typescript")
    world.stand_in({call: {"stdout": "{}"}})
    current = lsp("has-update", "typescript")
    assert (current.code, current.out) == (0, "ok  has-update typescript\n  ok  update: npm:typescript is current\n")
    newer = {"npm:typescript": {"name": "npm:typescript", "current": "7.0.2", "bump": "7.1.0", "latest": "7.1.0"}}
    world.stand_in({call: {"stdout": json.dumps(newer)}})
    waiting = lsp("has-update", "typescript")
    assert (waiting.code, waiting.out.splitlines()[1]) == (1, "  FAIL  update: npm:typescript can move to 7.1.0")


def test_has_update_reads_the_bootstrap_dry_run(world: World, lsp: Lsp) -> None:
    call = ("bootstrap", "packages", "upgrade", "--dry-run", "brew:llvm")
    world.stand_in({call: {"stdout": "pour z3/5.4.1 (dependency)\npour llvm/23.1.6 (requested)\n"}})
    waiting = lsp("has-update", "clangd")
    assert (waiting.code, waiting.out.splitlines()[1]) == (1, "  FAIL  update: brew:llvm can move to 23.1.6")
    world.stand_in({call: {"stdout": ""}})
    assert lsp("has-update", "clangd").out.splitlines()[1] == "  ok  update: brew:llvm is current"


def test_a_failed_mise_call_is_one_error_event(world: World, lsp: Lsp) -> None:
    world.stand_in({("outdated", "--global", "--bump", "--json", "npm:typescript"): {"code": 1}})
    result = lsp("has-update", "typescript")
    assert (result.code, result.out) == (2, "")
    assert result.error() == "mise outdated --global --bump --json npm:typescript exited 1: no output"


@needs_brew
@pytest.mark.parametrize(
    ("packages", "line"),
    [
        ('"brew:jq" = "0.0.1"', "  FAIL  mise: brew:llvm in [bootstrap.packages]: not declared"),
        ('"brew:llvm" = "0.0.1"', "  FAIL  mise: brew:llvm in [bootstrap.packages]: version_mismatch"),
    ],
)
def test_clangd_status_reads_the_bootstrap_package(world: World, lsp: Lsp, packages: str, line: str) -> None:
    world.mise(f"[bootstrap.packages]\n{packages}\n")
    result = lsp("status", "clangd")
    assert result.out.splitlines()[1] == line
    assert "  FAIL  plugin: clangd-lsp@claude-plugins-official is not installed" in result.out


@needs_brew
def test_clangd_status_passes_its_mise_check_for_an_installed_formula(world: World, lsp: Lsp) -> None:
    world.mise('[bootstrap.packages]\n"brew:llvm" = "latest"\n')
    line = lsp("status", "clangd").out.splitlines()[1]
    assert line.startswith("  ok  mise: brew:llvm ")
    assert line.endswith(" (mise bootstrap)")


def test_a_missing_claude_is_one_error_event(world: World, lsp: Lsp) -> None:
    world.without("claude")
    result = lsp("status", "typescript")
    assert result.code == 2
    assert result.error() == "claude plugin list --json exited 127: claude: No such file or directory"


def test_a_command_past_its_limit_is_one_error_event(world: World, lsp: Lsp) -> None:
    world.monkeypatch.setenv("LSPTOOLS_COMMAND_SECONDS", "0.001")
    result = lsp("status", "typescript")
    assert result.code == 2
    assert result.error() == "claude plugin list --json exited 124: claude: still running after 0.001 s"


def test_text_output_shows_a_plugins_control_characters_inert(world: World, lsp: Lsp) -> None:
    extensions = {".t\ns": "typescript", ".→\x1b[31m": "typescript"}
    server = {"command": "sh", "extensionToLanguage": extensions}
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": {"typescript": server}}})
    which = lsp("which", "typescript")
    (line,) = [line for line in which.out.splitlines() if "extensions:" in line]
    assert line == "  ok  extensions: .t\\x0as, .→\\x1b[31m"
    conflicts = lsp("conflicts")
    # conflicts sorts by extension: ".t\n" before ".→".
    assert conflicts.out.splitlines()[1:] == [
        "  ok  .t\\x0as: typescript-native-lsp@dotfiles",
        "  ok  .→\\x1b[31m: typescript-native-lsp@dotfiles",
    ]
    assert not [char for char in which.out + conflicts.out if unicodedata.category(char) == "Cc" and char != "\n"]


def test_a_config_with_no_marketplace_reads_its_session_plugins(world: World, lsp: Lsp) -> None:
    """A fresh config has no known_marketplaces.json; a session's own plugin folder still lists an @inline plugin."""
    inline = world.root / "session-plugin"
    (inline / ".claude-plugin").mkdir(parents=True)
    (inline / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "session-plugin", "version": "1.0.0"}))
    world.monkeypatch.setenv("CLAUDE_CODE_PLUGIN_DIRS", str(inline))
    assert not (world.claude / "plugins/known_marketplaces.json").exists()
    result = lsp("conflicts")
    assert (result.code, result.out) == (0, "ok  conflicts *\n")
