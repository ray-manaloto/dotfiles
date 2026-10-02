# Spec-axis review (mattpocock code-review) — origin/main...ccfc7b85

Persisted verbatim at receipt by the coordinator.

Spec-axis review of ccfc7b85 (authority: brief → delta rev 1 → original spec). Read-only; not persisted — yours to file. The diff tracks the brief's "Still to do" list closely; no blocker found.

**(a) Missing / partial**
1. **HEL half unaddressed.** Original spec R4: "the harness-evolution-ledger CI codex dependency (P19). HEL's pin goes ONLY in the same change that gives its CI a native codex install." The delta's scope line ("§2c, §2d, §2f…") includes §2f, but neither delta nor diff states HEL is out of scope/deferred. Brief doesn't list it either — add one "not changed, with reasons" line.
2. **Check scope narrower than the brief's done-criterion.** Brief: "no mise/npm copy of any of them (`mise ls` shows none)". `mise_findings` runs `mise ls --current --json`, so an installed-but-inactive copy (most plausibly in the overlay's `~/.local/share/mise/installs`; the image copies leave with the rebuild) passes. Delta §3 says `--current`, so delta and brief disagree — align or state why `--current` suffices.

**(b) Scope creep (all minor)**
1. `main.py` splits `handle_devcontainer` into `_handle_devcontainer_names`; delta only says "Add `devcontainer native-clis {install,check}`".
2. `_move_aside` writes `.<tool>.pre-native-<UTC stamp>`; delta rev 1 says "moves it aside to `.<tool>.pre-native`". Harmless (better), but update the spec text.
3. lock-image regen bumped 8 `latest` tools — accepted residual (finding 11) in the delta, so covered; ensure the PR body names them.

**(c) Implemented but looks wrong/fragile**
1. **PATH comparison is literal.** Delta §3: "`command -v <tool>` ≠ `~/.local/bin/<tool>`". `check_one` compares `Path(found) != expected` without normalising, so a PATH entry spelled differently (symlinked home, trailing `/./`, `$HOME` vs PATH spelling) reports a native install as FAIL. Compare `.resolve()` of the parent dirs. Low probability, false-positive direction.
2. **`ai.py` half-updated.** Docstring rewritten, but `ensure_ai_clis` still checks `("claude", "codex", "gemini")` — agy omitted, though the brief says "Mac AND devcontainer get native installers for claude, codex AND agy". Only matters if `run_all` is invoked (`main.py:2793`), which I didn't trace.

**Conforms:** on-create held rc + pre-chezmoi ordering; minimal env with credential filter (delta §4); probe-only updater switches (ruling 2); CI no-mount smoke requires absence (delta §2); vendored codex pin (MISSING-2); wrapper deleted (MISSING-1); flat agy (MISSING-5); ci.yml drops `MISE_DISABLE_TOOLS` with no `setup-codex` (P-CI); doctor.toml/pin-parity unchanged with reasons. Ruling 4's weaker claude verification is recorded as accepted in delta §4; the brief's "record what each installer verifies in the PR body" is post-ship — not checkable here.

## GitHub repos touched

_None._
