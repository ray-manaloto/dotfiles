# Research: mise-native options for launchd + git worktrees (dag-tick U1)

Date 2026-10-04. Read-only lane. I ran no launchctl, `mise trust`, `bootstrap apply` or install command.
Installed: mise 2026.10.1 (macos-arm64, 2026-10-03; 2026.10.2 is available), uv 0.12.13, git 2.54.0.
Source: a shallow clone of jdx/mise at tag v2026.10.1 (commit `050ce5a20287a0aafd872b1191699a5fdafff5ac`), in
/tmp/mise-src. Citations of the form `src/...` and `docs/...` are file:line references into that tag.

## Bottom line

1. **mise has no worktree command and no feature that pins a revision for a task.** It handles worktrees in
   three places only: trust is shared across linked worktrees, and pitchfork daemons get per-worktree
   namespaces and ports. `mise run`, `-C`/`--cd` and task `dir` only choose a directory. Whatever bytes
   are on disk at that directory are what runs.
2. **The current plist trusts whatever is on disk in the main checkout.** In normal mode, `mise run`
   automatically trusts its active config (`docs/cli/trust.md:19-22`). On top of that, this host sets
   `trusted_config_paths = ["/"]` globally (`~/.config/mise/config.toml:9`). So whatever branch is checked
   out, its `mise.toml` runs with no prompt. This confirms the premise of U1.
3. **Three native pieces fit U1:**
   - (a) env overrides that turn auto-install off (verified live);
   - (b) paranoid mode, which ties trust to a sha256 of each config file's content (verified live that it
     refuses);
   - (c) `[bootstrap.repos]`, a declarative clone pinned to a full SHA that refuses to touch a dirty
     checkout.
   None of them pins the python source on its own. Only running from a fixed checkout (or wheel) at an
   approved SHA does that.

## Options table

| # | Mechanism | Native? | How it pins the revision | Blocks auto-install? | Evidence |
|---|---|---|---|---|---|
| 1 | Plist schema: `[bootstrap.macos.launchd.agents.X]`. Keys: `program`, `args`, `environment`, `working_directory`, `stdout_path`, `stderr_path`, `start_interval`, `start_calendar_interval`, `throttle_interval`, `nice`, `process_type`, `queue_directories`, `run_at_load`, `keep_alive`, `keep_alive_on_failure`, `kickstart` | yes (mise) | **Not at all.** Values are rendered with Tera using the declaring file's context (`{{ config_root }}`). `exec()` is unavailable, so a SHA cannot be computed at apply time, and `environment` is not `~`-expanded. The plist must point at a **stable path**, and the SHA must live somewhere else. | n/a | `src/system/launchd.rs:16-52` (struct; no `deny_unknown_fields`, so a misspelled key is silently ignored); `docs/bootstrap/launchd.md` §Supported keys and §Templates; `nice` is in the code but missing from the docs table; mise.jdx.dev/bootstrap/launchd.html |
| 2 | `MISE_TASK_RUN_AUTO_INSTALL=0`, or the stronger `MISE_AUTO_INSTALL=0`, set in the plist `environment` | yes | no | **yes.** The env layer takes precedence over project `[settings]` (`settings.rs:1298-1336`). `auto_install=false` also forces `task.run_auto_install`, `exec_auto_install` and `not_found_auto_install` to false (`settings.rs:1487-1490`). **LIVE:** the default reads `true`; `MISE_TASK_RUN_AUTO_INSTALL=0` reads `false`; `MISE_AUTO_INSTALL=0` reads `false`. | `settings.toml:283-287`, `:3713-3717`; `src/cli/run.rs:843-845` |
| 3 | `mise run --skip-tools` | yes | no | yes, for that one invocation (the argv lives in the plist) | `src/cli/run.rs:269-275` |
| 4 | Paranoid mode: `MISE_PARANOID=1` plus a narrowed `MISE_TRUSTED_CONFIG_PATHS` in the plist env | yes | **Pins config-file content only.** A file passes only after an explicit `mise trust` hashes it (sha256 in a `.hash` file). Paranoid mode disables auto-trust and does not share trust with linked worktrees. Python, `uv.lock` and `mise.lock` are not covered. | Indirectly: load fails before the install phase | `docs/paranoid.md`; `config_file/mod.rs:650-657`, `:871-881`. **LIVE:** with both env vars set, `trust --show` reports `mise.toml`, `mise.local.toml` and `conf.d/shared.toml` as *untrusted*, and `mise run --dry-run dag-tick` exits rc=1 with "not trusted". Control: normal mode reports *trusted*. **Caveat:** the global `trusted_config_paths=["/"]` bypasses the hash (`docs/paranoid.md`; `mod.rs:619-625`), so the plist **must** override it (verified: the env value replaces the global one). Not run: the positive arm (a hash-trusted file actually runs), because it needs a mutating `mise trust`. |
| 5 | Trust sharing across worktrees (#10890) | yes | **The opposite of pinning.** A linked worktree inherits the main checkout's trust (normal mode only). | no | `config_file/mod.rs:658-670`; github.com/jdx/mise/pull/10890 |
| 6 | `[bootstrap.repos."<path>"] = { url, ref = "<full sha>" }`, then `mise bootstrap repos apply` | yes | **Yes.** A separate **clone** checked out at the SHA. It refuses a dirty checkout (untracked files count) or a mismatched origin. `status --missing` exits 1 unless the checkout is current. | n/a (it does not run anything) | `docs/bootstrap/repos.md` (States table); `src/system/repos.rs:363-406`, `:602-707`; mise.jdx.dev/bootstrap/repos.html. **Limits:** no ancestor-of-`origin/main` check and no venv creation. |
| 7 | `pypi:` backend: `mise use -g 'pypi:git+https://github.com/ray-manaloto/dotfiles#subdirectory=python@<sha>'` (a mise-managed `uv tool`) | yes | **Yes**, as an isolated venv per version. With uv ≥0.12.10, `mise.lock` can record the full dependency graph. | The plist runs the installed binary directly, so there is no `mise run`. | `docs/dev-tools/backends/pypi.md:43-110`. Not probed: the `kb-setup @ git+…@sha` dependency (`python/pyproject.toml:40`) under this backend. |
| 8 | `uv tool install 'git+…@<sha>#subdirectory=python'` (R2) | uv-native | **Yes**, an immutable install | yes (no mise involved) | **No `--locked`:** `uv tool install --help` has 0 hits for `--locked`, while the control `uv sync --help` has 1. Dependencies resolve fresh rather than from `python/uv.lock`, unless you pass `-c` with constraints from `uv export --frozen`. |
| 9 | `git worktree add --detach <sha> <path>` (with optional `--lock`) | git-native | **Yes.** Detached HEAD at the SHA. HEAD is a reachability root, so `gc` cannot drop it. It shares the main checkout's object store, and it shows up in `git worktree list`. | n/a | `git worktree add -h` (`-d/--detach`, `--lock`) |
| 10 | `git archive <sha> \| tar -x` into a deployment directory | git-native | **Yes, and immutable:** no `.git`, so it can never be dirty or switch branch. It also cannot self-verify HEAD later. The approval record must carry the SHA plus a tree digest. | n/a | git docs |
| 11 | `mise -C <dir> run …` / task `dir` | yes | **Not by itself.** It only chooses which checkout's `mise.toml` loads. Pointed at a pinned checkout, it pins the config (see the R1-mise variant below). | no | `src/cli/run.rs:143-144`; `docs/tasks/task-configuration.md:388-400` |
| 12 | `mise system install`, `mise generate tool-stub`, `mise install-into`, `mise daemons` (pitchfork) | yes | not applicable | — | `src/cli/system/install.rs:16-25` (OS packages); tool-stub is for HTTP binary stubs; daemons are long-running services with no interval trigger; `[bootstrap.services]` also targets long-running services (`docs/bootstrap/services.md`) |
| 13 | Remote `include = ["git::…?ref=<sha>"]` (#13843, merged 2026-09-29) | yes | Pins **included fragments only**. Fragments cannot carry `[tasks]`, and trust follows the including file. | no | github.com/jdx/mise/pull/13843 |
| 14 | Claude Code worktrees (`EnterWorktree`, `isolation: worktree`) | CC-native | **No.** These are branch-based and auto-cleaned under `.claude/worktrees/`, which makes them unsuitable as a long-lived deployment pin. | — | `.claude/rules/agent-artifact-conventions.md` §Worktrees |

## Recommendation for U1

**Ratify R1 (approved detached checkout, launched without mise or uv), and make it more mise-native in
three places:**

1. **Keep the plist declarative in mise and point it at a stable path.** Set `program` to
   `<deploy>/python/.venv/bin/python` and `args` to `["-I", "-m", "dotfiles_setup.dag_tick_launch",
   "--cwd", "<main abs>"]`. The SHA cannot appear in the plist because Tera here has no `exec()`, so it
   stays in the approval record, as §3c already says. Add `process_type = "Background"`. Set
   `environment` to include **both** `MISE_AUTO_INSTALL=0` and `UV_NO_SYNC=1`/`UV_FROZEN=1`. These are
   defence in depth: any child the tick spawns through mise or uv then cannot install or re-sync.
2. **Deployment checkout: weigh a `[bootstrap.repos]` clone against `git worktree add --detach`.**
   - A clone (row 6) removes the spec's stated CON, "a third worktree appears in `git worktree list`". It
     does not share the main `.git`, and it gives a native dirty/at-ref check
     (`mise bootstrap repos status --missing`).
   - It still needs the python approve verb for the ancestor-of-freshly-fetched-`origin/main` check and for
     `uv sync --frozen`. mise does neither.
   - Declare the clone in `mise.local.toml` (gitignored), or set the ref through the approve verb, so a
     branch switch in the main checkout cannot move the pinned ref.
   - If you prefer the worktree, `git worktree add --detach --lock` is the git-native form.
3. **Reject R3 as written, and do not count paranoid mode as a substitute.** Paranoid mode (row 4) does make
   `mise run dag-tick` from the main checkout fail closed whenever `mise.toml`, `mise.local.toml` or
   `shared.toml` changes. I proved the refusal live. But it does not cover the python guard or the tick
   code, it needs `MISE_TRUSTED_CONFIG_PATHS` overridden because of the global `["/"]`, and every edit
   would need a re-trust. It only fits if R1 is rejected: as "R3 + MISE_PARANOID", it closes the
   `mise.toml` half of R3's CON but not the python half.

**Cheaper variant (R1-mise), if you want to keep `mise run`:** in the plist, `program = ~/.local/bin/mise`
with `args = ["-C", "<deploy>", "run", "--skip-tools", "dag-tick"]`, and env
`MISE_AUTO_INSTALL=0 UV_FROZEN=1`.

- Gains: the task definition and `mise.toml` come from the pinned checkout, and `mise.local.toml` is
  absent there because it is gitignored.
- Costs: the trust root widens to include the self-updating mise binary and the unpinned global
  `~/.config/mise/config.toml`, and mise parses the config before the python guard runs.
- So R1 as spec'd, which has no mise at tick time, stays stronger.

## Gaps

- **Positive paranoid arm not run.** I did not show that a hash-trusted file actually runs; that needs
  `mise trust`. Only the refusal arm is proven.
- **`[bootstrap.repos]` with a local `file://` origin or a full-SHA ref is unprobed** on this host; the
  evidence is docs and code only.
- **The `pypi:` backend and `uv tool install` are unprobed with the SHA-pinned git dependency** (`kb-setup`).
  uv's lack of `--locked` for tool installs is proven; whether a `-c` constraints file is enough is
  untested.
- **Settings precedence is inferred from the builder order** in `settings.rs`, and confirmed only for
  three keys through live `settings get`.
- **The local mintlify cache for jdx/mise is stale.** It has 0 `launchd` hits; the control, `paranoid`,
  has 2 hits in `llms-full.txt`, so the cache is readable but predates launchd. I used the live
  `https://mise.jdx.dev/llms.txt` (HTTP 200, 411 lines; has the launchd, repos and paranoid entries).
- **Search controls.** `gh` code search: the must-hit `LaunchdTomlConfig` returned 3 files and a fresh
  absent token returned 0. Discussions GraphQL: the absent control returned 0, against 8 hits for
  `launchd` and 13 for `worktree`. Relevant threads:
  - discussion #10770 (launchd calendar scheduling);
  - discussion #12681 (systemd `environment_file`/umask, no launchd equivalent);
  - discussion #13434: `mise run` exits 1 when an unrelated tool fails to auto-install. This is a further
    reason to disable auto-install in the tick.
- **No mise feature verifies HEAD, cleanliness or ancestry at run time.** The python provenance guard in
  §3c remains necessary under every option.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — source at v2026.10.1 (launchd, settings, trust, repos, run, pypi backend); issues and PRs #10890, #13843, #10396, #13434; discussions #10770, #12681
- [astral-sh/uv](https://github.com/astral-sh/uv) — CLI help only (local `uv tool install` / `uv sync` / `uv run` flags); repo not fetched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `mise.toml:710-722`, `:1538-1628`; spec §3c/U1; `python/pyproject.toml:40`
