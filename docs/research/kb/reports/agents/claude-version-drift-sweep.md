# Claude-version drift sweep — coordinator measurement, 2026-09-15

Regex (operator-supplied): `2\.1\.2[6-7]` — widened to `2\.1\.2[6-7][0-9]`.

**676 total hits.** Classification:

## LIVE surfaces — config, code, tests, eager rules
```
tests/test_claude_doctor.py:21
.devcontainer/mise-runtime.lock:7
schemas/sources.toml:4
python/src/dotfiles_setup/claude_doctor.py:4
.claude/rules/md-size-budgets.md:2
.claude/rules/ai-cli-invocation.md:2
python/verification/suites.toml:1
.claude/types/claude-code.d.ts:1
.claude/types/claude-code-plugins.d.ts:1
.claude/skills/claude-doctor/hooks/register.ts:1
.agents/skills/claude-doctor/hooks/register.ts:1
```

## The actual hits in each live surface
```
.agents/skills/claude-doctor/hooks/register.ts:122: * `~/.local/share/claude/versions/2.1.270 install latest` - run by absolute
.claude/rules/ai-cli-invocation.md:81:⚠️ An earlier draft of this section credited Claude Code 2.1.261 with three
.claude/rules/ai-cli-invocation.md:88:absent from the saved 2.1.261 changelog. A plausible-looking variable name is
.claude/rules/md-size-budgets.md:98:- On Claude Code 2.1.261+, `/skill-doctor` reportedly shows loaded-but-unused skills and
.claude/rules/md-size-budgets.md:99:  their context cost. This command is documented in the saved 2.1.261
.claude/skills/claude-doctor/hooks/register.ts:122: * `~/.local/share/claude/versions/2.1.270 install latest` - run by absolute
.claude/types/claude-code-plugins.d.ts:1:// Written by Claude Code 2.1.271.
.claude/types/claude-code.d.ts:1:// Written by Claude Code 2.1.271.
.devcontainer/mise-runtime.lock:584:version = "2.1.270"
.devcontainer/mise-runtime.lock:589:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-arm64.tar.gz"
.devcontainer/mise-runtime.lock:594:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-arm64-musl.tar.gz"
.devcontainer/mise-runtime.lock:599:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-x64.tar.gz"
.devcontainer/mise-runtime.lock:604:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-x64.tar.gz"
.devcontainer/mise-runtime.lock:609:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-x64-musl.tar.gz"
.devcontainer/mise-runtime.lock:614:url = "https://github.com/anthropics/claude-code/releases/download/v2.1.270/claude-linux-x64-musl.tar.gz"
python/src/dotfiles_setup/claude_doctor.py:4:``claude doctor`` has **no JSON output**. Measured on Claude Code 2.1.270:
python/src/dotfiles_setup/claude_doctor.py:73:#: ``Running: native (2.1.270)`` / ``Running: npm-global (2.1.269)``.
python/src/dotfiles_setup/claude_doctor.py:112:#: the captured ambient ``PATH`` finds ``~/.local/bin/claude`` (native 2.1.270),
python/src/dotfiles_setup/claude_doctor.py:114:#: ``~/.local/share/mise/installs/npm-anthropic-ai-claude-code/2.1.269/bin/claude``.
python/verification/suites.toml:2665:per_path_tokens = { "mise.toml" = ['run = "uv run --project python dotfiles-setup fnhook-gates"', 'run = "uv run --project python dotfiles-setup schema-vendor refresh"'], "hk.pkl" = ['["fnhook_gates"] {', '"**/.claude-plugin/plugin.json",', '"**/hooks/hooks.json",', '"**/hooks/*.ts",', 'check = "uv run --project python dotfiles-setup fnhook-gates"'], "python/src/dotfiles_setup/main.py" = ['"fnhook-gates",', '"fnhook-gates": lambda', '"fnhook-types-refresh",', '"fnhook-types-refresh": lambda'], "python/src/dotfiles_setup/fnhook_gates.py" = ['def discover_plugin_dirs(', 'def validate_plugin(', 'def typecheck_modules(', 'def assert_modules_are_typed(', 'def assert_escape_hatch_permitted(', 'assert_escape_hatch_permitted(plugin_dirs),', 'def normalize_claude_code_declarations(', 'def fnhook_gates_main(', 'def fnhook_types_refresh_main('], "tests/test_fnhook_gates.py" = ['def test_plugin_elsewhere_under_tests_is_discovered(', 'def test_broken_fixtures_stay_invalid_for_the_intended_reason(', 'def test_hk_glob_is_armed_for_production_plugin_surfaces(', 'def test_normalizer_ignores_environment_specific_tool_inventory(', 'def test_normalizer_detects_plugin_api_surface_mutation(', 'def test_an_unconsulted_escape_hatch_set_is_rejected(', 'def test_a_deny_capable_module_with_no_escape_hatch_is_rejected(', 'def test_the_two_reject_fixtures_are_still_genuinely_broken(', 'def test_the_production_hook_permits_the_escape_hatch('], "tests/fixtures/fnhook/bad-event/hooks/register.ts" = ['on("classic.SessionStartt",'], "tests/fixtures/fnhook/parse-error/hooks/register.ts" = ['export const register: Register = ('], "tests/fixtures/fnhook/bad-return/hooks/register.ts" = ['additionalContext: "not-an-array"'], "tests/fixtures/fnhook/untyped/hooks/register.ts" = ['(on: any, _options: any)'], "tests/fixtures/fnhook/no-escape-hatch/hooks/register.ts" = ['return { deny:'], "tests/fixtures/fnhook/escape-hatch-unconsulted/hooks/register.ts" = ['const ESCAPE_HATCH_TOOLS = new Set('], ".claude/skills/claude-doctor/hooks/register.ts" = ['const ESCAPE_HATCH_TOOLS = new Set(', 'ESCAPE_HATCH_TOOLS.has(e.tool)'], ".claude/types/claude-code.d.ts" = ["// Written by Claude Code 2.1.271."], ".claude/types/claude-code-mcp.d.ts" = ["interface McpToolInputs {"], ".claude/types/README.md" = ['https://raw.githubusercontent.com/anthropics/claude-code/v<VERSION>/mods/types/claude-code.d.ts'], "tsconfig.json" = ['"strict": true,', '".claude/types",'] }
schemas/sources.toml:51:version = "2.1.272"
schemas/sources.toml:52:source = "https://raw.githubusercontent.com/anthropics/claude-code/v2.1.272/mods/types/claude-code.d.ts"
schemas/sources.toml:70:# NOTE: Upstream's types lag by one release. The file at tag v2.1.272 says
schemas/sources.toml:71:# "Written by Claude Code 2.1.271". v2.1.271 and v2.1.272 are byte-identical.
tests/test_claude_doctor.py:54:Running: native (2.1.270)
tests/test_claude_doctor.py:63:Running: npm-global (2.1.269)
tests/test_claude_doctor.py:78:    oracle: tuple[int, str] = (0, "2.1.270\n"),
tests/test_claude_doctor.py:116:    assert claude_doctor.parse_doctor(NATIVE_DOCTOR) == ("2.1.270", "native", True)
tests/test_claude_doctor.py:122:        "2.1.269",
tests/test_claude_doctor.py:130:    version, method, _ = claude_doctor.parse_doctor("Now running: native 2.1.270")
tests/test_claude_doctor.py:136:    assert claude_doctor.parse_doctor("Running: native (2.1.270)\n") == (
tests/test_claude_doctor.py:137:        "2.1.270",
tests/test_claude_doctor.py:157:    monkeypatch.setattr(claude_doctor, "_run", _fake_run(oracle=(0, "2.1.271\n")))
tests/test_claude_doctor.py:161:    assert any("2.1.271 is published" in f for f in result.findings)
tests/test_claude_doctor.py:175:        _fake_run(doctor=(0, SHADOWED_DOCTOR), oracle=(0, "2.1.269\n")),
tests/test_claude_doctor.py:180:    # The version assertion PASSES here (2.1.269 == 2.1.269), so this finding
tests/test_claude_doctor.py:196:        _fake_run(doctor=(0, SHADOWED_DOCTOR), oracle=(0, "2.1.269\n")),
tests/test_claude_doctor.py:218:        claude_doctor, "_run", _fake_run(doctor=(0, "Now running: native 2.1.270"))
tests/test_claude_doctor.py:235:    assert result.running_version == "2.1.270"
tests/test_claude_doctor.py:242:        _fake_run(doctor=(0, "Running: native (2.1.270)\nFound 1 problem.\n")),
tests/test_claude_doctor.py:316:        (NATIVE_DOCTOR, "2.1.270\n", 0),
tests/test_claude_doctor.py:317:        (NATIVE_DOCTOR, "2.1.271\n", 1),
tests/test_claude_doctor.py:318:        ("Now running: native 2.1.270", "2.1.270\n", 0),
tests/test_claude_doctor.py:386:#: install method. ``SHADOWED_DOCTOR`` is 2.1.269, so it goes INVALID on
tests/test_claude_doctor.py:391:Running: npm-global (2.1.270)
```

## HISTORICAL — 32 files under docs/research/, 600+ hits
Probe-version records ("measured on host 2.1.266"), changelog digests, and
prior agent reports. Rewriting these would FALSIFY the record.
