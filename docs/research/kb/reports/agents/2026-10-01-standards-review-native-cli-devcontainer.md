# Standards-axis review (mattpocock code-review) — origin/main...ccfc7b85

Persisted verbatim at receipt by the coordinator.

Standards review — origin/main...ccfc7b85 (read-only; not persisted). No hard breaches of a documented standard found: bash budget bumps (74→81, 163→166) are reviewed diffs with justification; `uv run --project python`, `per_path_tokens`, the injected-runner seam (tests/AGENTS.md "Mocking"), and two-armed tests all conform.

**Judgement calls (documented standards)**

1. `python/src/dotfiles_setup/native_clis_container.py` `mise_findings`: `run([mise, "ls", "--current", "--json"], dict(environ))` hands the FULL env (Doppler secrets) to the probe, while installers and `--version` go through `_minimal_env`. Not a breach (secrets-out-of-the-shell-env.md rule 2: no confinement anyway), but inconsistent with the module's own docstring claim ("run with a minimal environment so the Doppler-injected container credentials never reach…").
2. `tests/test_native_clis_container.py` exercises `install` only via `_FakeInstall`. Per `.claude/rules/real-integration-evidence.md`, a completion claim for an external installer needs one real invocation through the entrypoint; the spec cites throwaway-container measurements but nothing in-repo reproduces them — treat as unverified until `verify-local`/smoke tier 3 runs.
3. `python/src/dotfiles_setup/schema_vendor.py:423` comment still says "claude-code has no mise [tools] pin" above `if entry.tool in _VENDORED_PIN_TOOLS:` — stale now that codex shares the path (the `check_drift` twin was updated).

**Smells (baseline, judgement calls)**

- **Shotgun Surgery / Duplicated Code** — the three tool names live in four places: `TOOLS`, `_FORBIDDEN_MISE_NAMES`, image.py's `for tool in claude codex agy; do`, and the test's `_vendor_install` if/elif. Adding a fourth CLI touches all four; the image.py bash list could be generated from `TOOLS` (it's already a Python-built string).
- **Repeated Switches** — `_vendor_install` (`if name == "claude": … elif name == "codex": … else`) switches on tool name where the variation could live on the `NativeCli` data (as `flat` already does).
- **Middle Man / Repeated Switches** — main.py splits `handle_devcontainer` into a one-branch pre-dispatcher plus `_handle_devcontainer_names`: two switches on `devcontainer_command`, apparently to dodge a return-count limit; the docstring "every name verb goes to its own handler" is a Mysterious Name.
- **Primitive Obsession / duplicated validation** — `native_clis_container.main(command: str)` re-validates `install`/`check` though argparse `choices=` already restricts it; its rc=2 branch is unreachable from the CLI.
- **Speculative breadth** — `_CREDENTIAL_NAME` (`KEY|AUTH|…`) also drops benign names like `MISE_*KEYRING*`/`MISE_AUTHOR*`; fails safe, so minor, but the test pins only `MISE_GITHUB_TOKEN` and no non-secret `MISE_*` that must survive.

Files: `python/src/dotfiles_setup/native_clis_container.py`, `python/src/dotfiles_setup/main.py`, `python/src/dotfiles_setup/image.py`, `python/src/dotfiles_setup/schema_vendor.py`, `tests/test_native_clis_container.py`.

## GitHub repos touched

_None._
