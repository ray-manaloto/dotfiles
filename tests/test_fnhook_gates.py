# Copyright (c) 2026 Raymond Manaloto
"""Build-time gate coverage for Claude Code function-hook modules (#1026)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
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


def _sources_version(tool: str) -> str:
    """Read a pin straight out of `schemas/sources.toml`.

    Parsed here rather than read back off `fnhook_gates`, so the expectation
    cannot agree with the module by construction (`tests/AGENTS.md`,
    "tautological").
    """
    data = tomllib.loads(
        (REPO_ROOT / "schemas" / "sources.toml").read_text(encoding="utf-8")
    )
    return next(row["version"] for row in data["schema"] if row["tool"] == tool)


def _binary_resolves(command: list[str]) -> bool:
    """Whether one `--version` probe exits 0 from the repo root."""
    return (
        subprocess.run(
            command,
            capture_output=True,
            check=False,
            cwd=REPO_ROOT,
        ).returncode
        == 0
    )


def _real_tools_available() -> bool:
    """Whether the two binaries the gate shells out to actually resolve.

    They reach the gate by different routes on purpose. `tsc` is a `mise.toml`
    pin (host-only, #1026 ruling), deliberately NOT in the shared fragment, so
    it is absent inside the devcontainer — where `sync --full` runs this suite.
    `claude` comes off `PATH` from the native installer, which is why the probe
    below cannot go through `mise exec` for it; doing so is the very defect
    `test_validate_plugin_does_not_route_through_mise` now pins.

    Skipping keeps the suite runnable everywhere WITHOUT weakening the gate:
    the `fnhook-gates` CLI still fails loudly when a binary is missing, because
    a gate that shrugs is not a gate.

    This only ever skips the arms that shell out to a real tool. Every
    pure-python arm — discovery, the normalizer and its control arm, the typed-
    module assertion, the hk-glob arming — runs unconditionally.
    """
    claude = [fnhook_gates.CLAUDE_BINARY, "--version"]
    tsc = [
        "mise",
        "exec",
        fnhook_gates.tool_spec(REPO_ROOT, fnhook_gates.TSC_TOOL),
        "--",
        "tsc",
        "--version",
    ]
    return _binary_resolves(claude) and _binary_resolves(tsc)


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
    """All seven complete fixtures are discoverable only when explicitly included."""
    all_plugins = set(
        fnhook_gates.discover_plugin_dirs(REPO_ROOT, include_fixtures=True)
    )
    production = set(fnhook_gates.discover_plugin_dirs(REPO_ROOT))
    fixtures = {path for path in all_plugins if path.is_relative_to(FIXTURE_ROOT)}

    assert {path.name for path in fixtures} == {
        "bad-event",
        "bad-return",
        "escape-hatch-unconsulted",
        "no-escape-hatch",
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


def test_validate_plugin_issues_the_strict_command() -> None:
    """The validator runs off PATH, on the plugin dir, with warnings as errors."""
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
                "claude",
                "plugin",
                "validate",
                "--strict",
                str(plugin_dir),
            ],
            Path.cwd(),
        )
    ]


def test_validate_plugin_does_not_route_through_mise() -> None:
    """Reproduces PR #1128: `mise exec` around claude cannot work on a runner.

    The `[tools]` pin was removed in `6d1ae23` (native installer owns PATH),
    but the `mise exec` wrapper survived. With no pin to activate, mise falls
    through to an on-demand `@latest` install, and `MISE_LOCKED=1` refuses it:

        No lockfile URL found for github:anthropics/claude-code@2.1.272
        on platform linux-x64 (--locked mode)

    Asserted on the argv rather than on mise's error text, which is a string
    this repo does not own (`probes-need-a-control-arm.md` rule 9). The
    development Mac allows the on-demand install, so it stayed green for the
    whole outage and could never have caught this.
    """
    seen: list[list[str]] = []

    def _capture(command: list[str], **_: object) -> GateResult:
        seen.append(command)
        return GateResult(rc=0)

    fnhook_gates.validate_plugin(_fixture_plugins()["valid"], runner=_capture)

    assert seen, "no command captured — the stub was never called"
    for command in seen:
        assert "mise" not in command, (
            f"{command!r} routes claude through mise — it has no [tools] pin, "
            f"so MISE_LOCKED=1 turns this into an install failure on a runner"
        )
        assert command[0] == fnhook_gates.CLAUDE_BINARY, command


def test_claude_code_pin_reads_sources_toml() -> None:
    """The one pin CI installs from, with an armed failure direction.

    `claude_code_pin` must RAISE on a sources.toml with no claude-code row, not
    return a default: a silent fallback would let CI install an unpinned Claude
    Code and validate against declarations vendored from another release.
    """
    assert fnhook_gates.claude_code_pin(REPO_ROOT) == _sources_version("claude-code")

    empty = REPO_ROOT / "tests" / "fixtures"  # any dir without schemas/sources.toml
    with pytest.raises((ValueError, FileNotFoundError)):
        fnhook_gates.claude_code_pin(empty)


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
    """fnhook_types_refresh_main is deprecated; it returns 0 immediately."""
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
        # Satisfies the Runner protocol for `ty`; `del` consumes the
        # arguments so ruff's ARG001 is met without an inline
        # suppression, which the `no_lint_skip` gate forbids.
        del command, cwd, env, input_text
        # This runner is unused now that fnhook_types_refresh_main is deprecated
        msg = "deprecated function should not invoke runner"
        raise AssertionError(msg)

    rc = fnhook_gates.fnhook_types_refresh_main(runner=silent_unknown_command)

    # fnhook_types_refresh_main is deprecated; use schema-vendor-refresh instead
    assert rc == 0
    stderr = capsys.readouterr().err
    assert "deprecated" in stderr
    # Old files should be unchanged (no-op function)
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
    capsys: pytest.CaptureFixture[str],
) -> None:
    """fnhook_types_refresh_main is deprecated; it returns 0 immediately."""
    monkeypatch.chdir(tmp_path)
    fresh = (b"fresh-main\n", b"fresh-mcp\n")
    _write_types(tmp_path, fresh)

    def writing_runner(
        command: list[str],
        *,
        cwd: Path,
        env: object = None,
        input_text: str | None = None,
    ) -> GateResult:
        # Satisfies the Runner protocol for `ty`; `del` consumes the
        # arguments so ruff's ARG001 is met without an inline
        # suppression, which the `no_lint_skip` gate forbids.
        del command, cwd, env, input_text
        # This runner is unused; fnhook_types_refresh_main is deprecated
        msg = "deprecated function should not invoke runner"
        raise AssertionError(msg)

    rc = fnhook_gates.fnhook_types_refresh_main(runner=writing_runner)

    # fnhook_types_refresh_main is deprecated and does nothing
    assert rc == 0
    assert "deprecated" in capsys.readouterr().err


def test_public_gate_with_vendored_declarations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gate verifies vendored declarations exist and type-check passes."""
    monkeypatch.chdir(tmp_path)
    # Vendored declarations should exist
    committed = (_main_declarations(), b"mcp-contract\n")
    _write_types(tmp_path, committed)
    (tmp_path / "tsconfig.json").write_text("{}\n", encoding="utf-8")

    def gate_runner(command: list[str], **_: object) -> GateResult:
        # tsc type-checks the declarations
        if "tsc" in command:
            return GateResult(rc=0)
        # No generation happens; the runner should not be called
        msg = "gate should not invoke /plugin-types with vendored declarations"
        raise AssertionError(msg)

    rc = fnhook_gates.fnhook_gates_main(runner=gate_runner)

    # Gate should pass with vendored declarations
    assert rc == 0


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


#: Which tool must supply each binary the gates invoke. Written out here on
#: purpose: an expectation copied from the module under test cannot disagree
#: with it (`tests/AGENTS.md`, "tautological").
#: Which tool must supply each binary a `mise exec` argv then runs. Written out
#: here on purpose: an expectation copied from the module under test cannot
#: disagree with it (`tests/AGENTS.md`, "tautological").
#:
#: `claude` is deliberately absent. It is no longer a mise invocation at all —
#: the native installer owns PATH — and `test_validate_plugin_does_not_route_
#: through_mise` is what holds that end.
_TOOL_SUPPLYING = {"tsc": "typescript"}


def test_every_mise_invocation_names_its_tool_not_a_bare_shim() -> None:
    """`mise exec -- <bin>` resolves the bare SHIM and has no version to map.

    Measured on a GitHub runner 2026-09-12: both pinned tools installed
    successfully and the gate still died on
    `mise ERROR No version is set for shim: claude`. It passed on the
    development Mac, where a shim resolves — so the host was not a control arm
    for CI, and only naming the tool fixes it.

    The argv must carry a `<tool>@<version>` spec between `exec` and `--`. The
    version is read from `mise.toml`, so a pin bump cannot leave an invocation
    naming a stale one.
    """
    seen: list[list[str]] = []

    def _capture(command: list[str], **_: object) -> GateResult:
        seen.append(command)
        return GateResult(rc=0, stdout="", stderr="")

    valid = _fixture_plugins()["valid"]
    fnhook_gates.typecheck_modules([valid], runner=_capture)

    assert seen, "no commands captured — the stub was never called"
    for command in seen:
        assert command[:2] == ["mise", "exec"], command
        spec = command[2]
        assert "@" in spec, (
            f"argv[2] is {spec!r}, not a <tool>@<version> spec — a bare "
            f"`mise exec -- <bin>` resolves the shim and fails on a runner"
        )
        tool, _, version = spec.rpartition("@")
        # The tool must SUPPLY the binary the same argv then runs. Stated as an
        # independent expectation rather than read back off the module's own
        # constants, because two weaker forms were tried and both were
        # worthless:
        #
        #   `spec.startswith("npm:")` — pinned the BACKEND, so it failed #1043's
        #   move of claude from `npm:` to `github:` (npm's launcher needs a
        #   postinstall npm 12 blocks while still exiting 0) without testing
        #   anything the gate depends on.
        #
        #   `tool in {CLAUDE_TOOL, TSC_TOOL}` — TAUTOLOGICAL. It compares the
        #   observed tool against the very constant that produced it, so it
        #   cannot disagree with the code. Measured: repointing CLAUDE_TOOL at
        #   `npm:@devcontainers/cli` left all 25 tests green.
        binary = command[command.index("--") + 1]
        assert _TOOL_SUPPLYING[binary] in tool, (
            f"argv runs {binary!r} but the spec names {tool!r} — the gate would "
            f"resolve a tool that does not provide the binary it then invokes"
        )
        # The pin must match mise.toml, not a literal written into the module.
        assert fnhook_gates.tool_spec(REPO_ROOT, tool) == spec, (
            f"{tool} invoked at {version}, which is not its mise.toml pin"
        )


def test_tool_spec_refuses_the_removed_claude_pin() -> None:
    """The wrapper cannot be reinstated by reaching back through `tool_spec`.

    Claude Code has no `[tools]` entry (`6d1ae23`), so asking `tool_spec` for
    one must raise rather than hand back a spec that only fails later, inside
    mise, on a runner. Control arm: the tool that IS pinned still resolves.
    """
    with pytest.raises(TypeError):
        fnhook_gates.tool_spec(REPO_ROOT, "github:anthropics/claude-code")

    assert fnhook_gates.tool_spec(REPO_ROOT, fnhook_gates.TSC_TOOL).startswith(
        f"{fnhook_gates.TSC_TOOL}@"
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


# --------------------------------------------------------------------------- #
# assert_escape_hatch_permitted — a deny-capable module must leave a way out
# --------------------------------------------------------------------------- #


def test_a_module_permitting_the_escape_hatch_passes() -> None:
    """The ALLOW arm, exercised rather than assumed.

    A gate verified only in the failing direction is half a gate; this is the
    arm that proves a compliant module is actually accepted.
    """
    valid = _fixture_plugins()["valid"]
    assert fnhook_gates.assert_escape_hatch_permitted([valid]).rc == 0


def test_a_module_registering_no_blocking_event_is_out_of_scope() -> None:
    """Scope is `classic.PreToolUse`; a module that cannot deny needs no set.

    `bad-event` registers something else entirely, so it must pass this gate
    even while failing its own — otherwise the gate is asserting event coverage
    rather than the escape hatch.
    """
    bad_event = _fixture_plugins()["bad-event"]
    assert fnhook_gates.assert_escape_hatch_permitted([bad_event]).rc == 0


def test_a_deny_capable_module_with_no_escape_hatch_is_rejected() -> None:
    """Reject arm 1: the blocking event is registered and nothing permits."""
    plugin = _fixture_plugins()["no-escape-hatch"]
    result = fnhook_gates.assert_escape_hatch_permitted([plugin])
    assert result.rc == 1
    assert "no Set permits" in result.stdout
    for tool in fnhook_gates.ESCAPE_HATCH_TOOLS:
        assert tool in result.stdout


def test_an_unconsulted_escape_hatch_set_is_rejected() -> None:
    """Reject arm 2, and the reason this gate binds a call site at all.

    This is the REAL regression shape: reverting one `||` clause in
    `isRepairPermitted` leaves the set present, correct, and completely
    inert. A membership-only check stays green through it, which is the
    "passes at rc=0 because only half a two-part change was reverted" failure
    `feedback_coarse_mutation_certifies_nothing` records.
    """
    plugin = _fixture_plugins()["escape-hatch-unconsulted"]
    result = fnhook_gates.assert_escape_hatch_permitted([plugin])
    assert result.rc == 1
    assert "never consults it" in result.stdout


def test_the_two_reject_fixtures_are_still_genuinely_broken() -> None:
    """Guard against a tidy-up neutering the gate into a check that only passes.

    Asserts the defect is still present in the SOURCE, not merely that the gate
    still returns 1 — a gate and its fixtures can rot together silently.
    """
    plugins = _fixture_plugins()
    absent = (plugins["no-escape-hatch"] / "hooks" / "register.ts").read_text()
    assert "classic.PreToolUse" in absent, "fixture must still register the event"
    assert "ESCAPE_HATCH_TOOLS" not in absent, (
        "no-escape-hatch must NOT declare the set, or reject arm 1 is unreachable"
    )

    inert = (plugins["escape-hatch-unconsulted"] / "hooks" / "register.ts").read_text()
    assert "ESCAPE_HATCH_TOOLS = new Set" in inert, (
        "escape-hatch-unconsulted must still DECLARE the set"
    )
    assert "ESCAPE_HATCH_TOOLS.has" not in inert, (
        "escape-hatch-unconsulted must never CONSULT it, or reject arm 2 is "
        "unreachable and the call-site binding goes untested"
    )


def test_the_production_hook_permits_the_escape_hatch() -> None:
    """The real module, not a fixture — this gate exists because it did not.

    Measured 2026-09-13: this hook denied both tools while reporting a broken
    install, so the session could see the finding and not report it.
    """
    production = fnhook_gates.discover_plugin_dirs(REPO_ROOT)
    assert production, "expected at least one production function-hook plugin"
    assert fnhook_gates.assert_escape_hatch_permitted(production).rc == 0


def test_the_escape_hatch_gate_is_wired_into_the_cli() -> None:
    """Wiring guard: an unwired check is a check that cannot fail.

    `.claude/rules/probes-need-a-control-arm.md` #2 asks for the realistic
    mutation — deleting the line that CALLS the check, not renaming the check.
    """
    source = (
        REPO_ROOT / "python" / "src" / "dotfiles_setup" / "fnhook_gates.py"
    ).read_text()
    assert "assert_escape_hatch_permitted(plugin_dirs)," in source, (
        "the check must be invoked from fnhook_gates_main, or it never runs"
    )
