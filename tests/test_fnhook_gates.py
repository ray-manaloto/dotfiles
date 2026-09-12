# Copyright (c) 2026 Raymond Manaloto
"""Build-time gate coverage for Claude Code function-hook modules (#1026)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import fnhook_gates
from dotfiles_setup.fnhook_gates import GateResult
from dotfiles_setup.main import setup_parser

REPO_ROOT = Path(__file__).parent.parent.absolute()
FIXTURE_ROOT = REPO_ROOT / fnhook_gates.FIXTURE_ROOT
TYPE_FILENAMES = ("claude-code.d.ts", "claude-code-mcp.d.ts")


def _real_tools_available() -> bool:
    """Whether the two pinned binaries the gate shells out to actually resolve.

    They are pinned in `mise.toml` (host-only, #1026 ruling), deliberately NOT
    in the shared fragment, so they are absent inside the devcontainer — where
    `sync --full` runs this suite. Skipping there keeps the suite runnable
    everywhere WITHOUT weakening the gate: the `fnhook-gates` CLI still fails
    loudly when a binary is missing, because a gate that shrugs is not a gate.

    This only ever skips the arms that shell out to a real tool. Every
    pure-python arm — discovery, the normalizer and its control arm, the typed-
    module assertion, the hk-glob arming — runs unconditionally.
    """
    return all(
        subprocess.run(
            [
                "mise",
                "exec",
                fnhook_gates.tool_spec(REPO_ROOT, mise_tool),
                "--",
                tool,
                "--version",
            ],
            capture_output=True,
            check=False,
            cwd=REPO_ROOT,
        ).returncode
        == 0
        for tool, mise_tool in (
            ("claude", fnhook_gates.CLAUDE_TOOL),
            ("tsc", fnhook_gates.TSC_TOOL),
        )
    )


_REAL_TOOLS = _real_tools_available()
_needs_real_tools = pytest.mark.skipif(
    not _REAL_TOOLS,
    reason=(
        "`claude` and/or `tsc` do not resolve here — they are pinned host-only "
        "in mise.toml, so this arm cannot run inside the devcontainer. The "
        "fnhook-gates CLI still fails loudly on a missing binary."
    ),
)


def _fixture_plugins() -> dict[str, Path]:
    """Derive fixture plugin names from the same discovery path as production."""
    return {
        path.name: path
        for path in fnhook_gates.discover_plugin_dirs(
            REPO_ROOT,
            include_fixtures=True,
        )
        if path.is_relative_to(FIXTURE_ROOT)
    }


def _write_plugin_markers(plugin_dir: Path) -> None:
    """Create only the two files discovery requires."""
    plugin_manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    hooks_manifest = plugin_dir / "hooks" / "hooks.json"
    plugin_manifest.parent.mkdir(parents=True)
    hooks_manifest.parent.mkdir(parents=True)
    plugin_manifest.write_text("{}\n", encoding="utf-8")
    hooks_manifest.write_text("{}\n", encoding="utf-8")


def test_fixture_inventory_is_tree_derived_and_excluded_from_production() -> None:
    """All five complete fixtures are discoverable only when explicitly included."""
    all_plugins = set(
        fnhook_gates.discover_plugin_dirs(REPO_ROOT, include_fixtures=True)
    )
    production = set(fnhook_gates.discover_plugin_dirs(REPO_ROOT))
    fixtures = {path for path in all_plugins if path.is_relative_to(FIXTURE_ROOT)}

    assert {path.name for path in fixtures} == {
        "bad-event",
        "bad-return",
        "parse-error",
        "untyped",
        "valid",
    }
    assert production.isdisjoint(fixtures)
    assert all_plugins == production | fixtures


def test_plugin_elsewhere_under_tests_is_discovered(tmp_path: Path) -> None:
    """The exclusion is exactly FIXTURE_ROOT, not tests/ generally."""
    plugin_dir = tmp_path / "tests" / "production-shaped-plugin"
    _write_plugin_markers(plugin_dir)

    assert fnhook_gates.discover_plugin_dirs(tmp_path) == [plugin_dir]


def test_validate_plugin_issues_the_strict_mise_command() -> None:
    """The external validator is pinned through mise and warnings are errors."""
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        assert env is None
        assert input_text is None
        calls.append((command, cwd))
        return GateResult(rc=0, stdout="validated\n")

    plugin_dir = _fixture_plugins()["valid"]
    result = fnhook_gates.validate_plugin(plugin_dir, runner=fake_runner)

    assert result == GateResult(rc=0, stdout="validated\n")
    assert calls == [
        (
            [
                "mise",
                "exec",
                fnhook_gates.tool_spec(REPO_ROOT, fnhook_gates.CLAUDE_TOOL),
                "--",
                "claude",
                "plugin",
                "validate",
                "--strict",
                str(plugin_dir),
            ],
            Path.cwd(),
        )
    ]


def test_typecheck_uses_discovered_files_and_committed_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tsc project derives modules but extends the repo compiler policy."""
    monkeypatch.chdir(REPO_ROOT)
    plugin_dir = _fixture_plugins()["valid"]
    observed: dict[str, object] = {}

    def fake_runner(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        assert env is None
        assert input_text is None
        project = Path(command[-1])
        observed["command"] = command[:-1]
        observed["cwd"] = cwd
        observed["project"] = json.loads(project.read_text(encoding="utf-8"))
        return GateResult(rc=0)

    result = fnhook_gates.typecheck_modules([plugin_dir], runner=fake_runner)

    assert result.ok
    assert observed["command"] == [
        "mise",
        "exec",
        fnhook_gates.tool_spec(REPO_ROOT, fnhook_gates.TSC_TOOL),
        "--",
        "tsc",
        "--noEmit",
        "--project",
    ]
    assert observed["cwd"] == REPO_ROOT
    project = cast("dict[str, object]", observed["project"])
    assert project["extends"] == str(REPO_ROOT / "tsconfig.json")
    assert set(cast("list[str]", project["files"])) == {
        str((REPO_ROOT / ".claude" / "types" / name).resolve())
        for name in TYPE_FILENAMES
    } | {str((plugin_dir / "hooks" / "register.ts").resolve())}


@_needs_real_tools
def test_valid_fixture_passes_both_real_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive arm: the complete, typed fixture passes validate and tsc."""
    monkeypatch.chdir(REPO_ROOT)
    valid = _fixture_plugins()["valid"]

    validation = fnhook_gates.validate_plugin(valid)
    typed = fnhook_gates.assert_modules_are_typed([valid])
    typecheck = fnhook_gates.typecheck_modules([valid])

    assert validation.rc == 0, validation.stdout
    assert typed.rc == 0
    assert typecheck.rc == 0, typecheck.stdout


@pytest.mark.parametrize(
    ("fixture_name", "gate_name", "stdout_marker"),
    [
        ("bad-event", "validate", "is not an event"),
        ("parse-error", "validate", "does not parse"),
        ("bad-return", "typecheck", "not assignable to type 'string[]'"),
        ("untyped", "typed", "untyped function-hook module"),
    ],
)
@_needs_real_tools
def test_broken_fixtures_stay_invalid_for_the_intended_reason(
    fixture_name: str,
    gate_name: str,
    stdout_marker: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repaired negative fixture turns this red instead of weakening the gate."""
    monkeypatch.chdir(REPO_ROOT)
    plugin_dir = _fixture_plugins()[fixture_name]
    if gate_name == "validate":
        result = fnhook_gates.validate_plugin(plugin_dir)
    elif gate_name == "typecheck":
        result = fnhook_gates.typecheck_modules([plugin_dir])
    else:
        result = fnhook_gates.assert_modules_are_typed([plugin_dir])

    assert result.rc != 0
    assert stdout_marker in result.stdout
    assert result.stderr == ""


def test_every_fixture_manifest_has_strict_mode_author() -> None:
    """Broken fixtures cannot fail early for the unrelated author warning."""
    for plugin_dir in _fixture_plugins().values():
        manifest = json.loads(
            (plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        assert manifest["author"] == {"name": "dotfiles test suite"}


@_needs_real_tools
def test_every_discovered_production_plugin_passes_all_module_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive production arm grows automatically when #1029 adds a plugin."""
    monkeypatch.chdir(REPO_ROOT)
    plugin_dirs = fnhook_gates.discover_plugin_dirs(REPO_ROOT)

    for plugin_dir in plugin_dirs:
        result = fnhook_gates.validate_plugin(plugin_dir)
        assert result.rc == 0, result.stdout
    assert fnhook_gates.assert_modules_are_typed(plugin_dirs).rc == 0
    typecheck = fnhook_gates.typecheck_modules(plugin_dirs)
    assert typecheck.rc == 0, typecheck.stdout


def _step_globs(source: str) -> list[str]:
    """Extract only the fnhook_gates step's glob list."""
    start = source.index('["fnhook_gates"] {')
    check = source.index("check = ", start)
    return re.findall(r'^\s+"([^"]+)",?$', source[start:check], re.MULTILINE)


@pytest.mark.parametrize(
    ("required_glob", "production_path"),
    [
        (
            "**/.claude-plugin/plugin.json",
            "plugins/x/.claude-plugin/plugin.json",
        ),
        ("**/hooks/hooks.json", "plugins/x/hooks/hooks.json"),
        ("**/hooks/*.ts", "plugins/x/hooks/register.ts"),
    ],
)
def test_hk_glob_is_armed_for_production_plugin_surfaces(
    required_glob: str,
    production_path: str,
) -> None:
    """Deleting a production glob line breaks the arm that needs it."""
    source = (REPO_ROOT / "hk.pkl").read_text(encoding="utf-8")
    globs = _step_globs(source)
    assert required_glob in globs
    assert PurePosixPath(production_path).match(required_glob)

    wiring_line = f'    "{required_glob}",\n'
    mutated = source.replace(wiring_line, "", 1)
    assert mutated != source, "mutation must delete the wiring line"
    assert not any(
        PurePosixPath(production_path).match(pattern)
        for pattern in _step_globs(mutated)
    )


def test_cli_registers_both_function_hook_commands() -> None:
    """Both public command names parse through the repository CLI."""
    parser = setup_parser()
    assert parser.parse_args(["fnhook-gates"]).command == "fnhook-gates"
    assert parser.parse_args(["fnhook-types-refresh"]).command == "fnhook-types-refresh"


def _write_types(root: Path, contents: tuple[bytes, bytes]) -> None:
    """Write one complete generated declaration pair for an isolated test."""
    types_dir = root / ".claude" / "types"
    types_dir.mkdir(parents=True, exist_ok=True)
    for name, body in zip(TYPE_FILENAMES, contents, strict=True):
        (types_dir / name).write_bytes(body)


def _main_declarations(
    *,
    exit_reason: bytes = b"'clear'",
    input_tools: bytes = b"    Bash: { command: string }\n",
    result_tools: bytes = b"    Bash: { stdout: string }\n",
) -> bytes:
    """Build a minimal declaration file with the generated normalization seams."""
    return b"".join(
        (
            b"declare module 'claude-code' {\n",
            b"  type ExitReason = ",
            exit_reason,
            b";\n}\n",
            b"declare module 'claude-code' {\n",
            b"  interface BuiltinToolInputs {\n",
            input_tools,
            b"  }\n}\n",
            b"declare module 'claude-code' {\n",
            b"  interface BuiltinToolResults {\n",
            result_tools,
            b"  }\n}\n",
        )
    )


def test_normalizer_ignores_environment_specific_tool_inventory() -> None:
    """Two sessions with different built-ins normalize to identical bytes."""
    committed = _main_declarations()
    generated = _main_declarations(
        input_tools=b"    RemoteTrigger: { id: string }\n",
        result_tools=b"    RemoteTrigger: { accepted: boolean }\n",
    )

    assert generated != committed
    assert fnhook_gates.normalize_claude_code_declarations(
        generated
    ) == fnhook_gates.normalize_claude_code_declarations(committed)


def test_normalizer_detects_plugin_api_surface_mutation() -> None:
    """The normalization control arm keeps stable declarations byte-sensitive."""
    source = _main_declarations()
    mutated = source.replace(
        b"type ExitReason = 'clear'",
        b"type ExitReason = 'CLEAR'",
        1,
    )

    assert mutated != source, "mutation must alter the stable plugin API"
    assert fnhook_gates.normalize_claude_code_declarations(
        mutated
    ) != fnhook_gates.normalize_claude_code_declarations(source)


def test_refresh_requires_new_nonempty_outputs_and_restores_old_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The rc=0 unknown-command shape cannot bless stale pre-existing files."""
    monkeypatch.chdir(tmp_path)
    old = (b"old-main\n", b"old-mcp\n")
    _write_types(tmp_path, old)

    def silent_unknown_command(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        # Anchored on the `--` boundary, not a fixed index: inserting the
        # `<tool>@<version>` spec before it shifted these by one and broke a
        # hard-coded slice, so the assertion now says what it means.
        after_sep = command[command.index("--") + 1 :]
        assert after_sep[:3] == ["claude", "-p", "/plugin-types"]
        assert cwd == tmp_path
        assert env == {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}
        assert input_text == ""
        return GateResult(rc=0, stdout="Unknown command: /plugin-types\n")

    rc = fnhook_gates.fnhook_types_refresh_main(runner=silent_unknown_command)

    assert rc == 1
    assert "did not write non-empty outputs" in capsys.readouterr().out
    assert (
        tuple(
            (tmp_path / ".claude" / "types" / name).read_bytes()
            for name in TYPE_FILENAMES
        )
        == old
    )


def test_refresh_accepts_files_not_process_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete generated pair is success even though rc is non-authoritative."""
    monkeypatch.chdir(tmp_path)
    fresh = (b"fresh-main\n", b"fresh-mcp\n")

    def writing_runner(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        # Anchored on the `--` boundary, not a fixed index: inserting the
        # `<tool>@<version>` spec before it shifted these by one and broke a
        # hard-coded slice, so the assertion now says what it means.
        after_sep = command[command.index("--") + 1 :]
        assert after_sep[:3] == ["claude", "-p", "/plugin-types"]
        assert env == {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}
        assert input_text == ""
        _write_types(cwd, fresh)
        return GateResult(rc=9, stdout="generated\n")

    rc = fnhook_gates.fnhook_types_refresh_main(runner=writing_runner)

    assert rc == 0
    assert (
        tuple(
            (tmp_path / ".claude" / "types" / name).read_bytes()
            for name in TYPE_FILENAMES
        )
        == fresh
    )


@pytest.mark.parametrize("generated_state", ["current", "drifted"])
def test_public_gate_compares_types_to_a_fresh_generation(
    generated_state: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tool-inventory drift passes, while stable plugin-API drift fails."""
    monkeypatch.chdir(tmp_path)
    committed = (_main_declarations(), b"mcp-contract\n")
    _write_types(tmp_path, committed)
    (tmp_path / "tsconfig.json").write_text("{}\n", encoding="utf-8")

    def gate_runner(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        if "tsc" in command:
            return GateResult(rc=0)
        generated_main = _main_declarations(
            exit_reason=b"'CLEAR'" if generated_state == "drifted" else b"'clear'",
            input_tools=b"    RemoteTrigger: { id: string }\n",
            result_tools=b"    RemoteTrigger: { accepted: boolean }\n",
        )
        assert generated_main != committed[0]
        generated = (generated_main, committed[1])
        _write_types(cwd, generated)
        assert env == {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}
        assert input_text == ""
        return GateResult(rc=0)

    rc = fnhook_gates.fnhook_gates_main(runner=gate_runner)
    captured = capsys.readouterr()

    expected_drift = generated_state == "drifted"
    assert rc == int(expected_drift)
    assert ("function-hook declarations drifted" in captured.out) is expected_drift


def test_mcp_declarations_are_excluded_from_drift_but_the_api_file_is_not() -> None:
    """The MCP file is per-session in its entirety; the API file is not.

    Measured 2026-09-12, same machine, minutes apart: `claude-code-mcp.d.ts`
    reported "no MCP tools are connected, so it is empty" in one session and
    "170 MCP tools from 12 servers" in another, so comparing it can only
    produce false drift. This asserts BOTH halves — that it is excluded, and
    that excluding it did not quietly disable the whole check by dropping
    `claude-code.d.ts` with it.
    """
    compared = {path.name for path in fnhook_gates.drift_comparable_files(REPO_ROOT)}

    assert "claude-code-mcp.d.ts" not in compared, (
        "the MCP declarations are per-session and must not be drift-compared"
    )
    assert "claude-code.d.ts" in compared, (
        "excluding the MCP file must not stop the API declarations being compared — "
        "without this the drift check is a check that can only pass"
    )


def test_missing_binary_fails_the_gate_rather_than_skipping_it() -> None:
    """The skip above must not become a way for the gate to shrug.

    `_needs_real_tools` skips only the TEST arms that shell out. The gate
    itself must still fail loudly when a binary does not resolve — otherwise
    running it anywhere without the pinned tools would report success, which
    is the "check that can only pass" this ticket exists to prevent.
    """

    def _missing(command: list[str], **_: object) -> GateResult:
        return GateResult(
            rc=127, stdout="", stderr=f"{command[0]}: command not found\n"
        )

    plugin_dir = _fixture_plugins()["valid"]
    result = fnhook_gates.validate_plugin(plugin_dir, runner=_missing)

    assert result.rc != 0, (
        "a missing binary must fail the gate; a gate that passes when its tool "
        "is absent is a check that can only pass"
    )


def test_every_mise_invocation_names_its_tool_not_a_bare_shim() -> None:
    """`mise exec -- <bin>` resolves the bare SHIM and has no version to map.

    Measured on a GitHub runner 2026-09-12: both pinned tools installed
    successfully and the gate still died on
    `mise ERROR No version is set for shim: claude`. It passed on the
    development Mac, where a shim resolves — so the host was not a control arm
    for CI, and only naming the tool fixes it.

    This binds all three call sites at once: the argv must carry a
    `<tool>@<version>` spec between `exec` and `--`. The version is read from
    `mise.toml`, so a pin bump cannot leave an invocation naming a stale one.
    """
    seen: list[list[str]] = []

    def _capture(command: list[str], **_: object) -> GateResult:
        seen.append(command)
        return GateResult(rc=0, stdout="", stderr="")

    valid = _fixture_plugins()["valid"]
    fnhook_gates.validate_plugin(valid, runner=_capture)
    fnhook_gates.typecheck_modules([valid], runner=_capture)

    assert seen, "no commands captured — the stub was never called"
    for command in seen:
        assert command[:2] == ["mise", "exec"], command
        spec = command[2]
        assert "@" in spec, (
            f"argv[2] is {spec!r}, not a <tool>@<version> spec — a bare "
            f"`mise exec -- <bin>` resolves the shim and fails on a runner"
        )
        assert spec.startswith("npm:"), spec
        # The pin must match mise.toml, not a literal written into the module.
        tool, _, version = spec.rpartition("@")
        assert fnhook_gates.tool_spec(REPO_ROOT, tool) == spec, (
            f"{tool} invoked at {version}, which is not its mise.toml pin"
        )


def test_a_plugin_in_a_nested_checkout_is_not_discovered(tmp_path: Path) -> None:
    """Reproduces the CI failure: another repo's plugin must not be gated here.

    CI clones the sibling knowledge-base repo into `.rule-sync/` for the
    cross-repo rule gate, and that repo ships a real function-hook plugin
    (`kb-settings-guard`, untyped). On a GitHub runner 2026-09-12 discovery
    found it and the typed-module assertion flagged it — both working as
    designed, but failing this repo's gate over code it does not own.

    Both arms run: the nested plugin is excluded AND a sibling plugin in the
    repo proper is still found, so the exclusion cannot become a hole that
    hides a real module.
    """
    (tmp_path / ".git").mkdir()

    ours = tmp_path / "plugins" / "ours"
    _write_plugin_markers(ours)

    nested_root = tmp_path / ".rule-sync" / "knowledge-base"
    (nested_root / ".git").mkdir(parents=True)
    theirs = nested_root / ".claude" / "mods" / "kb-settings-guard"
    _write_plugin_markers(theirs)

    discovered = fnhook_gates.discover_plugin_dirs(tmp_path)

    assert ours in discovered, (
        "a plugin in the repo proper must still be discovered — without this "
        "arm the exclusion could hide every real module"
    )
    assert theirs not in discovered, (
        "a plugin inside a nested git checkout belongs to that repo's gate, "
        "not this one"
    )
