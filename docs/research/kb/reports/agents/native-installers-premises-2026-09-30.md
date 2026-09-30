# premise-verifier — native-cli-installers spec (2026-09-30)

Verbatim.

PREMISE REPORT
ROWS: 31 checked — 20 CONFIRMED (0 provenance corrected) / 3 REFUTED / 8 UNVERIFIABLE / 0 ASSUMED (0 checkable)
(This lane has no shell, so I could not run live probes, `codesign` or `gh`. "W" means `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/agy-native-20260930`.)

P1 — CONFIRMED — W/mise.toml:126 `antigravity-cli = "1.2.14"`; the host-only comment is at :114-115; W/.devcontainer/devcontainer.json:182 puts root mise.toml and shared.toml in MISE_IGNORED_CONFIG_PATHS.
P2 — CONFIRMED — W/mise.toml:164-169.
P3 — CONFIRMED — shared.toml:44; Dockerfile:139 COPYs shared.toml into the image's system conf.d; ci.yml:69-72 sets `MISE_DISABLE_TOOLS: ""`.
P4 — CONFIRMED — mise-runtime.toml:59 (comment says `http:claude`) and :63; mise-runtime.lock:583-585 records `backend = "aqua:anthropics/claude-code"`, with a sha256 at :588.
P5 — CONFIRMED — mise.toml:27-38; setup-claude-code/action.yml:44-45 installs claude natively through claude.ai/install.sh.
P6 — CONFIRMED — ~/.config/mise/config.toml:142, :383, :479, :500 (depends at :526); `[shell_alias]` at :529 with aliases at :545-546.
P7 — UNVERIFIABLE — The evidence is a live probe, and this lane cannot run `mise ls`. KB's mise source snapshot has a JSON `source` field (sources/mise/src/cli/ls.rs:275) and a disable_tools filter (registry.rs:895-906), but that snapshot is not the installed mise.
P8 — CONFIRMED — doctor.py:1397-1413 (CHECKS), :1416-1426 (LIVE_CHECKS); claude_doctor.py:67, :447; graphify_currency.py:28, :161.
P9 — CONFIRMED (in the `mise run` context) — doctor.toml:236-240. In code, BLIND requires MISE_TASK_NAME to be set; outside mise, a missing capture is INHERITED, not BLIND (path_drift.py:171-177).
P10 — CONFIRMED — hk.pkl:365-367.
P11 — CONFIRMED — main.py:1735-1741 (parser), :2913-2921 (dispatch). plugin-remove is flat, so it is no precedent for native-cli's nested sub-subcommands.
P12 — CONFIRMED — mise.lock:4491-4548; the next block starts at :4550.
P13 — CONFIRMED — schema_vendor.py:121 `_read_shared_toml_pin("npm:@openai/codex", root)`; schemas/sources.toml:43-47 `pin_source = ".config/mise/conf.d/shared.toml"`.
P14 — CONFIRMED — rule_sync.py:144-148 compares normalised whole lines. Line correction: `lines` is :38-40, `rules` is :57-80 by stem, and `plugins` (:29-31) and `agents` (:87-90) are also synced (not prose).
P15 — CONFIRMED for :66-67 only — :8 stays true because disable_tools stays. Unlisted stale line: :25 "Gemini/Antigravity pinned lane".
P16 — REFUTED — The sdlc_team.py:692-705 docstring already names the native install as owner: "the codex shim then falls through to the host's native install on PATH" (:700-701). codex_lane.py:435 is a docstring; the actual error text is **:458** `"… it is pinned host-only in mise.toml, "`, and §2a does not list it.
P17 — REFUTED — The KB pins are host-only (KB mise.toml:239-240; one workflow file, no mise install). But KB currency.toml:1950 `expected = "1.2.12"` already makes `[tool.antigravity-cli]` self-managed (config.py:319-326 → sync.py:2018-2019). Only `[tool.codex]` (:1855-1856, no `expected`) reaches sync.py:2026 "has no pin".
P18 — CONFIRMED — claude-code-marketplace acceptance.yml:30 `mise oci run … -- claude --version`, and :34 reads the pin from mise.toml.
P19 — REFUTED — harness-evolution-ledger CI does invoke codex. phase0.yml:54-55 runs `mise run rules:verify` (mise.toml:139-141), which reaches verify_rules.py:48 `["codex", "execpolicy", "check", …]`. phase0.yml:46 runs `mise run doctor`, which reaches phase0.py:163 and :225 (`codex plugin list`, `codex --version`). The runner gets codex from mise.toml:40.
P20 — UNVERIFIABLE — The provenance is a report (R-chan). The vendor install.sh is not on disk (KB sources/ holds only antigravity-cli.manifest).
P21 — UNVERIFIABLE — The provenance is a report. The local KB snapshot's codex-rs/app-server-daemon/src/settings.rs:11-13 has only `remote_control_enabled`, so it predates the cited rust-v0.159.2 (context mismatch).
P22 — UNVERIFIABLE — The provenance is a report, and there is no codesign in this lane. L5 re-derives it.
P23 — CONFIRMED — `~/.config/mise/config.toml.bak-codex-native-20260922T202255Z` exists. The 0600 mode is not readable from this lane.
P24 — CONFIRMED — mise-native-dotfiles-plan.md:343-345 (the struck text), §4.7 at :433. A grep of the global config for DOTFILES_SETUP_PROJECT found 0 hits; the control term `update-claude` hits in the same file.
P25 — UNVERIFIABLE — The ambient PATH and the versions are live facts. What I could see: `installs/antigravity-cli/1.2.13/` exists and `~/.local/bin/agy` is a regular file. `installs/antigravity-cli/1.2.14/` now exists too, so the INV state has moved.
P26 — UNVERIFIABLE — The provenance is a report (R-blast). L7 re-proves it.
P27 — CONFIRMED, scope corrected — suites.toml:1876-1886 binds `PLANNING_DISABLED=1 mise exec -- codex exec` in `.claude/agents/codex-sol-*.md`. It does not bind ai-cli-invocation.md (0 hits in suites.toml), so §2a's reason for keeping those literals is misattributed.
P28 — UNVERIFIABLE — The provenance is a report, and settling it needs `gh`.
P29 — CONFIRMED — config.toml.tmpl has only `:64 [tasks."update:all"]` (that hit is the control arm).
P30 — UNVERIFIABLE — The agy half was not probed, as the spec admits. The codex half is confirmed in source: KB sources/codex/codex-rs/cli/src/main.rs:183, :1645.
P31 — CONFIRMED within its grep scope — 0 hits in mise.toml, hk.pkl, suites.toml, doctor.toml and python/ (control: `lock-check` hits hk.pkl:366). The scope missed `.claude/` (see MISSING).

MISSING:
- **BLIND exit code:** §3b says "rc 3 (BLIND) is the path-drift convention". It is not: path_drift.py:358 and :366 return **2** for BLIND. The spec pins the wrong rc into the CLI and into test 3. Fix before dispatch.
- **Check (c)(1) fires on healthy codex:** sdlc_team.py:695-697 records that `which codex` resolved to the mise shim, whose symlink target is the mise binary. Clause (1), "first hit's realpath is native", has no exemption for a shim, so it fires on healthy native codex, and L3 rc=0 cannot pass while that shim is first on PATH. Define shim handling explicitly.
- **`codesign -dv` is not a signature check:** C7 prescribes `codesign -dv`, which only displays signing info, while C9 calls the result an "offline, vendor-identity-bound signature check". I could not verify either way. The worktree's own `docs/research/kb/reports/agents/native-installers-critique-2026-09-30.md` §K records a tampered binary giving rc=0 and TeamIdentifier=2DC432GLL2 under `-dv`. That is report-sourced, so re-derive it, but goal 3(c) and C9 rest on it.
- **KB half, lock drift:** KB mise.lock:4719 (`antigravity-cli`) and :6673 (`npm:@openai/codex`) are not in scope. `kb-lock-drift` is a KB ship gate (gates.py:196) that flags a stale tool entry (lock_drift.py:62-64), so kb-ship fails unless both blocks are pruned. The same applies to the 8 KB sweep worktrees.
- **KB half, reviewer pin gate goes silent:** KB review.py `_reviewer_pin_gap` (:318-400; Ray's ruling is REFUSE) becomes inert. With no pin, `sync.pinned_version` returns "" (sync.py:157-165), and review.py:388-389 then `continue`s. The spec does not state this or decide it.
- **Global lock not handled:** `~/.config/mise/mise.lock:313` holds `[[tools.antigravity-cli]]`, and :3268 holds an orphan `npm:@openai/codex` 0.155.1 with no config pin. §2b does not handle the global lock. Non-blocking: state a scoped removal or deliberately leave it.
- **Name collision:** the new skill `native-cli-installers` collides with the workflow `.claude/workflows/native-cli-installers.js:2` (`name: 'native-cli-installers'`). Workflows run as `/<name>` (KB claude-code/workflows.md:203). Non-blocking; rename one.
- **Test 6 uses a signature `main` does not have:** it calls `main(["native-cli","check-pins"])`, but main.py:3115 is `def main() -> None` and takes no arguments. Use the existing `sys.argv` monkeypatch pattern (e.g. tests/test_sdlc_team.py). Non-blocking.
- **C4 is false as worded:** "no `curl | sh` anywhere in repo code" — setup-claude-code/action.yml:45 already runs `curl -fsSL https://claude.ai/install.sh | bash -s`. Non-blocking; scope C4 to new code.
- **Existing checks already cover part of (c):** path-drift (doctor.py:1407; path_drift.py:256-276) already flags the stale 1.2.13 install dir while the pin is active. claude-doctor (doctor.toml:265, doctor.py:1409) already asserts native claude. Non-blocking; state it.
- **Unlisted stale text:** KB .claude/rules/ai-cli-invocation.md:18, KB .claude/skills/kb-review/references/lanes.md:256 and KB codex_run.py:720 all say mise pins codex or agy. Non-blocking.
- **§2c row omits a pin:** the agentsview-{managed,native}-service worktrees also carry a host claude pin, `"github:anthropics/claude-code" = "2.1.270"` at mise.toml:43. Non-blocking (they are skipped anyway), but the report line should name it.
- **claude-code-marketplace is also a host pin:** its root mise.toml:10 `[tools]` pin activates npm claude on the host whenever the cwd is that repo, so "not a host pin" is incomplete. Non-blocking.
- **Future symlink conflict:** S29-M (mise-native-dotfiles-plan.md:277) will make `~/.config/mise/config.toml` a symlink, and `apply_global_stanza`'s atomic rename would then replace the link with a regular file. Non-blocking today.

VERDICT: correct the spec first. Blocking:
- P16, P17, P19 are refuted. P19 turns the harness-evolution-ledger EDIT rows into CI breakage.
- The BLIND rc is wrong (2, not 3).
- The shim false-positive makes L3 unreachable.
- `codesign -dv` is unverified as a signature check.
- The KB lock-drift gate is not handled.
- The KB reviewer-pin gate goes silently inert.
- Non-blocking residuals: P7, P20-P22, P25, P26, P28 and P30 are live or report-sourced, and L1-L7 re-derive them. The architect must accept each on record.
