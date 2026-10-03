PREMISE REPORT: spec-1614 (read-only lane. I have no Write tool, so /Users/rmanaloto/.claude/jobs/125da665/tmp/premise-1614.md was NOT written. Please persist this text verbatim.)
Citations: KB = knowledge-base/sources/mise (Cargo.toml:14 says 2026.9.4). WT = .claude/worktrees/fix-1614.
ROWS: 30 checked. 20 CONFIRMED (1 provenance corrected), 0 REFUTED, 0 UNVERIFIABLE, 10 ASSUMED (1 checkable).
L1 CONFIRMED. KB settings.toml:430-456: `rc = true` at :454, "no effect" in mise.toml at :445-447.
L2 CONFIRMED. KB settings.toml:438-441. file.rs:1628-1634 uses `map_while`, which returns None at the ceiling. file.rs:3961-3970 has len 0.
L3 CONFIRMED. KB file.rs:1629 `if ceiling_dirs.contains(p)`.
L4 CONFIRMED. KB docs/templates.md:540-545. miserc.rs:135 inserts config_root, and :174 renders before the TOML parse at :175. The `dirname` filter is registered at tera.rs:456.
L5 CONFIRMED. KB miserc.rs:146-151 and its test at :392-400.
L6 CONFIRMED. KB miserc.rs:171 iterates `.rev()`, :214-216 replaces the value whole, and :229-255 walks the cwd's ancestors. One unstated nuance: the local walk stops at $HOME (:247).
L7 CONFIRMED. KB miserc.rs:231 and :273-284 read the raw env var only.
L8 CONFIRMED. KB env.rs:465-478 uses `or_else`. Note that `MISE_CEILING_PATHS=""` still wins and yields an empty set (:466-472). The test's pop() handles this.
L9 ASSUMED-equivalent. I did not re-read docs/configuration.md:75-77, so this is not counted as CONFIRMED. The source is consistent with the claim: global/system miserc is appended separately at miserc.rs:257-268.
L10 CONFIRMED. KB cli/mod.rs:868 runs `miserc::init()`, and the --cd validation is at :912-913.
L11 CONFIRMED. WT .miserc.toml:1-4.
L12 CONFIRMED. WT tests/test_session_review.py:35 is not resolved, :38-42 only pops MISE_IGNORED_CONFIG_PATHS, :1058-1068 runs `--cd REPO_ROOT` with cwd=hostile_root, and the assertion is at :1106.
L13 CONFIRMED. WT verify.py:329-409 (`_normalise` per line, :399-404) and :590-601 (`tok not in text`).
L14 CONFIRMED. WT suites.toml:2399-2409, :2931-2936 (`config` category), :2958 ends the suite, :2960 starts the next.
L15 CONFIRMED. WT hk.pkl:890.
L16 CONFIRMED. WT pr.py:448 `_stream(..., cwd=workspace)`.
L17 CONFIRMED. WT .devcontainer/devcontainer.json:129-130 and :202.
L18 CONFIRMED (provenance corrected). All five sites hold, and the research report's :102 "returned nothing" is contradicted. Two corrections: the report is tracked (it is present in WT, not "main checkout, untracked"), and there is a sixth site, the mirror .agents/skills/codex-team-research/SKILL.md:41.
L19 CONFIRMED. A Grep for `auto_env|miserc|MISE_CEILING_PATHS` over WT hits only .miserc.toml, schemas/mise.json and docs. The control arm worked: .miserc.toml is found through `auto_env`. Without that term the probe misses hidden files.
L20 CONFIRMED. Grep `suite_count|len\(suites\)|EXPECTED_SUITES|len\(.*suite` over WT tests/ returns 0. I did not run a separate control.
A1-A6, A8, A10 ASSUMED. These are inherited; nothing I read contradicts them.
A7 ASSUMED. The test_session_review precedent only.
A9 ASSUMED (checkable). WT tests/AGENTS.md "Working in this directory" says it verbatim.
MISSING:
- M1 (load-bearing) The amended `mise lock` control arm cannot fail at the mirrored version. `mise lock` only targets config files whose project_root equals the nearest project root: KB cli/lock.rs:1187-1202 and :1205-1214, with config/mod.rs:1714-1717 picking the first (nearest) project root. Even with the leak, the fixture main's mise.toml is scoped out, so the parent mise.lock stays unchanged in BOTH arms. The ratification already says to report such a control rather than assert it. The spec must say so up front: the test documents scoping, it is not a ceiling gate, and its docstring must not claim discrimination. If a discriminating arm is wanted, it would need monorepo_root (lock.rs:1178-1186), which is out of scope.
- M2 (load-bearing) "Without network" is not guaranteed. lock.rs:326-327 builds the FULL toolset, including the global ~/.config/mise/config.toml tools. Those are inherited because the env starts from os.environ.copy(), the global config exists on this host, and `resolve_rolling_channels: true` is set at :296. An empty fixture `[tools]` does not remove the global tools. The spec must isolate the global config (e.g. point MISE_GLOBAL_CONFIG_FILE/MISE_CONFIG_DIR into tmp_path) and/or set MISE_OFFLINE=1 (env name at KB settings.toml:2222), and it must state the expected rc. I did not verify which isolation variable this mise honours.
- M3 (load-bearing) The amendment conflicts with §4.4 as written. §4.4 bans `mise lock` for the lane with no carve-out, and the ratification text sits outside §4. Amend §4.4 to say "except the tmp_path fixture inside tests/test_miserc_ceiling.py". Also update §3.4's "Required tests" list, the §3.2 `description` (gaps 5a/5b), and §6's commit body, which is missing gap (a) and the env-var note in (b). As written, the body sections contradict the ratification.
- M4 The KB mirror is 2026.9.4, but CI pins mise 2026.9.8 (WT .github/actions/setup-mise/action.yml:42,47), and the host is a native self-updating install whose version I did not read. Every KB premise (L2-L10, M1) is proven at 2026.9.4 only. The behavioural test covers the ceiling. Nothing covers lock scoping.
- M5 The fixed arm expects rc 0 for the worktree's own task with the fixture under tmp_path. That relies on tmp_path not being under $HOME, because the miserc walk stops there (KB miserc.rs:247). That holds for /var/folders and /tmp, so it is not blocking.
VERDICT: correct the spec first. M1-M3 block: the `mise lock` arm needs a declared non-discriminating status, network/global-config isolation, and a §4.4 carve-out plus updated §3.2/§3.4/§6 text before dispatch. The ASSUMED rows (A1-A10, plus L9 as unread) are non-blocking residuals because nothing I read contradicts them. M4 and M5 are non-blocking but should be recorded.