# Spec — move agy, codex and claude from mise pins to their native installers (2026-09-30, revision 1)

## Revision 1 (2026-09-30)

This revision encodes Ray's rulings (2026-09-30, AskUserQuestion) and the plan-mode lane reports. Revision 0 was never
committed: the file was untracked when this revision was written. Its text survives only where the lane reports quote
it.

**Rulings encoded (authoritative):**

| # | Ruling | Where it lands |
|---|---|---|
| R1 | **Worktrees:** commit the pin removals on EACH clean, named-branch worktree's own branch. Skip and report a tree that is dirty, has a live writer, is on a default branch, or is not a git repo. | §2e, C12. This **overrules** the critique's verdict J (FILE, report-only). J's residual risk is carried in C12. |
| R2 | **Vendor auto-update stays ON.** Add a **version ledger**. When a CLI's running version changes, record it and write a tracked release-notes receipt, using the graphify `docs/receipts/graphify/<v>.md` writer shape (tag, publishedAt, verbatim body). The doctor reports a running version that has no receipt. | §3a `ledger_*`, §3d, C8. Answers rev-0 Q7. |
| R3 | **Global update tasks:** a TRACKED conf.d fragment folder in this repo, symlinked into `~/.config/mise/conf.d/` by a mise task, the way lightster/.dotfiles does it. Plus one line in `config.toml` `update:all` that wires the tasks in (a fragment cannot override `config.toml`; measured). | §2b, §3c, C6. Answers rev-0 Q1. It replaces the rev-0 marker-spliced `global-stanza`, which the critique's G verdict filed. |
| R4 | **Everything now:** the IMAGE and CI halves are in scope. That covers shared.toml `npm:@openai/codex`, mise-runtime `claude-code`, the host `disable_tools`, `ci.yml` `MISE_DISABLE_TOOLS`, a native in-image install of codex and claude with pin + verify, a CI `setup-codex` path, and the harness-evolution-ledger CI codex dependency (P19). HEL's pin goes ONLY in the same change that gives its CI a native codex install. Every native Linux install is proven first in a throwaway `docker run` on the pinned `BASE_IMAGE`, and the cold image rebuild is stated. | §2c, §2d, §2f, C3, C13, §5 D1–D6. Rev-0 follow-up F1 is **dissolved** into this spec. |

**Lane findings applied:**

- **Critique** (`native-installers-critique-2026-09-30.md`):
  - E (check c) is KEEP, NARROWED: agy and codex only; the effective first hit resolves *through* an inactive shim; reuse the `path_drift` helpers.
  - K (codesign) is KILLed as specified and replaced with `--verify --strict -R`. C9 now credits the *check*, not the channel.
  - C (check a) is KEEP, NARROWED: detect by shape, using `install_path` binaries rather than a key list.
  - D (check b) is KEEP, NARROWED: the scan set is widened to mise's documented config names.
  - H (ordering) is KEEP, NARROWED: re-probe by absolute path, and the agy removals are gated on Q3.
  - I (KB half) is KEEP, NARROWED: the `_reviewer_pin_gap` falls back to `expected` in the same KB commit.
  - B (library) is KEEP, NARROWED: the rev-0 `install`/`update`/`global-stanza` verbs are dropped.
  - F (LIVE currency) is FILEd: the rev-0 `check_currency` is dropped. The ledger (R2) replaces it with an offline check that answers a different question.
  - G is superseded by R3. A and L are kept. All eight cited improvements are adopted (§4 C14 maps each one).
- **Security** (`native-installers-security-2026-09-30.md`):
  - S1 HIGH: `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM>"'`, never `-dv`.
  - S2: the C9 and C8 framing is corrected.
  - S5: image and CI installs verify signatures/checksums, run with a minimal env, and fetch https-only.
  - S6: agy `binaries = ["agy"]` only, and `antigravity` becomes a must-not-resolve-under-mise clause.
  - S7: every probe runs with a minimal env and the updaters switched off for that probe.
  - S8: C4 is scoped to new code.
  - S9: the posture table lists update-channel trust separately.
  - S3/S4 stay Ray's (Q8, Q9).
- **Premise verifier** (`native-installers-premises-2026-09-30.md`), three REFUTED rows:
  - P16: the `sdlc_team` docstring already names native. It still changes now, because `disable_tools` goes. The `codex_lane` error text is at `:458`, not `:435`.
  - P17: KB `[tool.antigravity-cli]` is already self-managed at `currency.toml:1950`, so only `[tool.codex]` needs converting.
  - P19: HEL CI invokes codex (R4).

  Blocking fixes:
  - the BLIND rc is **2**, not 3;
  - the shim false positive is handled (E);
  - the KB `mise.lock` blocks are pruned for `kb-lock-drift`;
  - the KB reviewer gate goes inert without a fallback, and gets one (I).

  Non-blocking fixes:
  - the global lock blocks;
  - the skill/workflow name collision: the skill is renamed `native-clis`;
  - the test signature for `main()`;
  - two unlisted stale lines;
  - the agentsview claude pin line;
  - `claude-code-marketplace` is also a host pin;
  - the S29-M symlink conflict.
- **GitHub examples** (`native-installers-github-examples-2026-09-30.md`, `mise-confd-github-examples-2026-09-30.md`): the evidence behind the R3 fragment shape and the image install shape (§3c, §3e).

**Resolved rev-0 open questions:** Q1 by R3, Q5 by R1, Q6 by R1 (`~/dev/tmp/kb2` is not a git repo, so it is skipped and reported), and Q7 by R2. Q2, Q3 and Q4 remain open. New questions Q8–Q13 are at the end.

---

Scope, from two sources of authority:
- **The relayed user request.** Read-only searches are approved, and so are edits that **remove** `antigravity-cli`, `codex` (every mise variant) and `claude` (every mise variant) from mise config files.
- **Ray's rulings R1–R4 above.**

Anything else is listed under **Open questions**.

Inputs, all read in full for this revision:
- **R-chan:** `docs/research/kb/reports/agents/native-installers-2026-09-30.md`
- **R-blast:** `native-installers-blast-radius-2026-09-30.md`
- **R-gh:** `native-installers-github-examples-2026-09-30.md`
- **R-confd:** `mise-confd-github-examples-2026-09-30.md`
- **R-crit:** `native-installers-critique-2026-09-30.md`
- **R-sec:** `native-installers-security-2026-09-30.md`
- **R-prem:** `native-installers-premises-2026-09-30.md`
- **R-place:** `native-installer-placement-2026-09-15.md`
- **R-cstat:** `codex-native-installer-status-2026-09-23.md`

Line numbers refer to worktree HEAD `a5a9f786` unless another repo/ref is named. KB refs are at `origin/main` `d8a205da`, and HEL refs are at primary `main` `f1b0eb3`. All were re-derived for this revision on 2026-09-30.

---

## 1. Objective

After this change, each vendor CLI has exactly one owner per surface:

| CLI | Mac host | Devcontainer image | CI runner |
|---|---|---|---|
| `agy` | Native. `~/.local/bin/agy` is a flat binary from `https://antigravity.google/cli/install.sh`, and it **self-updates (ON)**. | None; no consumer (R-chan §8.4). | None; `eval_cases.py:44` declares that a runner without agy must pass. |
| `codex` | Native. `~/.local/bin/codex` links to `~/.codex/packages/standalone/current/bin/codex`, and the daemon updater keeps it **self-updating (ON)**. | **Native artifact, pinned + verified**, at `/usr/local/bin/codex` → `/usr/local/lib/codex/<v>/…`, outside the home volume. The pin is in `schemas/sources.toml`. | **`setup-codex` composite**, pinned + verified from the same pin. |
| `claude` | Native (already, since `6d1ae23`). `~/.local/bin/claude` links to `~/.local/share/claude/versions/<v>`, **self-updating (ON)**. | **Native artifact, pinned + GPG-verified**, at `/usr/local/bin/claude` → `/usr/local/lib/claude/<v>/claude`. The pin is in `schemas/sources.toml` (already the CI pin). | `setup-claude-code` (unchanged; already native). |

Goals:

1. **Remove every mise pin of the three tools in this repo.** That covers:
   - host `mise.toml:126`;
   - shared `.config/mise/conf.d/shared.toml:44`;
   - image `.devcontainer/mise-runtime.toml:63`;
   - the host guard `mise.toml:169` `disable_tools`;
   - the CI override `ci.yml:72` `MISE_DISABLE_TOOLS: ""`;
   - the lock blocks of each.

   The same goes for the user-global `~/.config/mise/config.toml:142`, the KB (§2d), HEL (§2f) and every eligible worktree (§2e, R1).
2. **Install codex and claude natively in the image and on CI, pinned + verified** (§3e). Prove each Linux install in a throwaway `docker run` on the pinned `BASE_IMAGE` before any push (§5 D1–D6).
3. **Add a version ledger** (R2). Tracked receipts go in `docs/receipts/{agy,codex,claude}/<v>.md`, with an append-only `docs/receipts/native-cli/LEDGER.md`. A writer task and an offline doctor check report a running host version that has no receipt, and report a downgrade.
4. **Add global update tasks** (R3): a tracked fragment `mise-global/conf.d/50-native-cli.toml`, linked into `~/.config/mise/conf.d/` by `mise run native-cli -- link-global --apply`, plus the one `update:all` `depends` line.
5. **Add machine checks, armed in both directions.** A check fails when:
   - (a) a tool providing `agy`/`antigravity`/`codex`/`claude` is an **active** mise tool on the host;
   - (b) a tracked mise config pins one of them;
   - (c) the *effective* first `PATH` hit of `agy`/`codex` resolves into mise's installs root, or is missing, or (on darwin) the effective first hit of any of the three fails `codesign --verify --strict` against the vendor requirement;
   - (d) the global fragment link or the `update:all` wiring has drifted;
   - (e) the ledger has no receipt for a running version.
6. **Document rollback and security posture honestly** (C9, C10).

---

## 2. Files

### 2a. Host half: this worktree (`dotfiles.worktrees/agy-native-20260930`, branch `feat/native-cli-installers-workflow`)

| Path | Action |
|---|---|
| `python/src/dotfiles_setup/native_clis.py` | **NEW.** The library (§3a). It holds check verbs, the ledger and link-global. **No `install`/`update` verbs** (R-crit B). |
| `python/src/dotfiles_setup/main.py` | Register the nested `native-cli` subcommand. Follow the **`schema-vendor`** nested-subparser precedent: parser `:1768-1772`, dispatch `:2895`. Do not follow the flat `plugin-remove` parser (R-prem P11). |
| `python/src/dotfiles_setup/doctor.py` | Add to `CHECKS` (`:1397-1413`): `native-cli-pins` (a), `native-cli-resolution` (c), `native-cli-global` (d) and `native-cli-ledger` (e). **No LIVE check** (R-crit F). |
| `doctor.toml` | **NEW `[native_clis]` section** (§3b). It is the single reviewed policy, and it sits next to `[removed_plugins]` (`:285`). |
| `hk.pkl` | **NEW step `["native_cli_pins"] { check = "uv run --project python dotfiles-setup native-cli check-pins" }`**, shaped like `mise_lock_integrity` (`hk.pkl:365-367`). |
| `python/verification/suites.toml` | **NEW suite `workflow.native-cli-pins`.** It binds the chain hk step ↔ CLI ↔ module ↔ tests ↔ skill, with tokens chosen with `mise run token-check`. |
| `mise.toml` | Delete `antigravity-cli = "1.2.14"` (`:126`) and rewrite the stale comment block `:109-125`. Add `[tasks.native-cli]` with `run = "uv run --project python dotfiles-setup native-cli"` (arguments pass through). *(`disable_tools` `:164-169` is deleted in §2c.)* |
| `mise.lock` | Remove the scoped block `[[tools.antigravity-cli]]` at `:4491-4549` (the next block starts at `:4550`). Never run a whole-file relock. `mise_lock_integrity` must pass afterwards. |
| `mise-global/conf.d/50-native-cli.toml` | **NEW tracked global fragment** (§3c). The folder is deliberately **not** any mise project config name (C6). |
| `docs/receipts/{agy,codex,claude}/<v>.md` | **NEW.** The initial receipts, one per running host version at implementation time, written by the ledger writer (§3d). |
| `docs/receipts/native-cli/LEDGER.md` | **NEW** append-only ledger index (§3d). |
| `.claude/skills/native-clis/SKILL.md` | **NEW** skill, written through `mattpocock-skills:writing-for-agents`. It is **renamed from `native-cli-installers`**, because `.claude/workflows/native-cli-installers.js:2` already owns that name (R-prem). It covers the ledger loop, `link-global`, rollback and the posture table. Its description must fit `SKILL_DESCRIPTION_MAX`. |
| `tests/test_native_clis.py` | **NEW** tests (§5). |
| `.claude/rules/ai-cli-invocation.md` | Rewrite `:8` (the "root `mise.toml` disables the npm pin" wording goes stale once `disable_tools` goes), `:25` ("pinned lane", which R-prem found unlisted), and `:66-67`. These become: agy and codex are native on the host, self-update, and `mise exec -- <cli>` passes through to `PATH`. **Keep** the `mise exec -- codex exec` literals in `.claude/agents/codex-sol-*.md`, which `suites.toml:1876-1886` binds (R-prem P27 scope correction: the rule file itself is not bound). |
| `.claude/CLAUDE.md` | Rewrite `:80-81` to say: agy, codex and claude are native on the host, and the image and CI install codex and claude natively at the `schemas/sources.toml` pins. |
| `python/src/dotfiles_setup/sdlc_team.py` | Docstring `:692-705`: drop the "which disables the npm codex pin, `mise.toml` `disable_tools`" clause (`:699-700`), which is stale once `disable_tools` goes. |
| `python/src/dotfiles_setup/codex_lane.py` | Docstring `:435` and the **error text `:458`** ("pinned host-only in mise.toml") both become "a native install at `~/.local/bin`" (R-prem P16). |
| `docs/specs/native-cli-installers-2026-09-30.md` | This file. |

### 2b. The user-global config (outside git; C1 applies)

1. Take a backup first with `cp -p ~/.config/mise/config.toml ~/.config/mise/config.toml.bak-native-clis-<YYYYMMDDTHHMMSSZ>` (mode `0600` preserved; precedent `config.toml.bak-codex-native-20260922T202255Z`).
2. Delete `:142`, `antigravity-cli = { version = "1.2.14", minimum_release_age = "0s" }`. **This is gated on Q3** (C2 / R-crit H).
3. **R3, the one-line wiring.** `:526` becomes `depends = ["update:brew", "update:mise", "update:claude", "update:agy", "update:codex"]`. Regenerate the GENERATED DAG comment at `:240-262` from `mise tasks deps update:all --compact` in the same edit (R-crit G). The `update:all` block's inline DAG at `:501-510` is updated to match.
4. Run `mise run native-cli -- link-global --apply` (§3c). It creates `~/.config/mise/conf.d/` (absent today) and the symlink.
5. **Global lock** (R-prem): remove the scoped `[[tools.antigravity-cli]]` block at `~/.config/mise/mise.lock:313`. The orphan `[[tools."npm:@openai/codex"]]` block at `:3268` has no config pin, so remove it in the same scoped edit.
6. **Do not touch** `:193` `npm:oh-my-codex` or `:194` `npm:oh-my-claude-sisyphus` (Q4).

### 2c. Image and CI half (same branch, separate commit; R4)

| Path | Action |
|---|---|
| `.config/mise/conf.d/shared.toml` | Delete `:39-44`: the comment and `"npm:@openai/codex" = { version = "0.154.0", allow_builds = [...] }`. **Base-image input** (`Dockerfile:139` COPYs it into `devcontainer-base`), so this triggers a **cold base rebuild** in CI (C13). |
| `.config/mise/mise.lock` | Remove the `[[tools."npm:@openai/codex"]]` block at `:531` through `lock-shared` (skill `lock-shared`). If a scoped relock does not drop a removed tool's block, delete that block by hand and prove `mise_lock_integrity` passes. |
| `.devcontainer/mise-runtime.toml` | Delete `:57-63`: the stale "http:claude backend" comment and `claude-code = "latest"`. Keep `npm:@google/gemini-cli` (`:64`). |
| `.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock` | Regenerate through `mise run lock-image` (skill `lock-image`; never hand-rolled on macOS). The removed blocks are `mise-system.lock:4963` (npm codex) and `mise-runtime.lock:583` (claude-code). |
| `.devcontainer/mise-system.toml` | Fix the stale comment at `:412-413`, which says "run `claude install` in Dockerfile.host-user". That file has 0 claude hits (R-blast §2a P4). |
| `.devcontainer/Dockerfile` | In the **thin `devcontainer-runtime` stage** (`:666-689`), add one RUN each for codex and claude, following §3e. Add `ARG CODEX_VERSION`, `ARG CLAUDE_CODE_VERSION` and `ARG CLAUDE_CODE_SIGNING_FINGERPRINT=31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`, following the LLVM precedent `:183-202` (the fingerprint is asserted before the key is trusted, and the post-condition runs inside the same RUN). Add `ENV DISABLE_AUTOUPDATER=1` (Q10). No `2>/dev/null` (do-not #4). |
| `home/` (chezmoi, container-only) | **Pending Q10.** Add a template for `~/.codex/app-server-daemon/settings.json` = `{"updater":{"autoUpdateEnabled":false}}`, gated to Linux with `chezmoi.os` (use-tool-builtins). No env var disables the codex updater (R-chan §3), and `CODEX_HOME` lives in the home volume, so chezmoi is the only lever that survives the volume mount. |
| `python/src/dotfiles_setup/image.py` | Tier-3 smoke `:1043-1046`: replace `command -v` for `claude` and `codex` with a **provenance assertion**. `command -v <tool>` must equal `/usr/local/bin/<tool>`, its realpath must be under `/usr/local/lib/<tool>/`, and `--version` must contain the pin. `gemini` keeps `command -v`. This catches a stale `~/.local/bin/<tool>` in an existing home volume that shadows the system copy (`Dockerfile.host-user:77` puts `~/.local/bin` first; R-place §Recommendation, R-cstat F4). |
| `schemas/sources.toml` | Codex row `:43-48`: `version` becomes the **vendored pin** (the running image/CI version, chosen at implementation). `pin_source` becomes `"schemas/sources.toml (vendored; no mise [tools] pin)"`, mirroring claude-code `:55`. |
| `python/src/dotfiles_setup/schema_vendor.py` | Delete the `_PIN_RESOLVERS["codex"]` entry (`:121` plus its comment), so `version` IS the pin, as for claude-code (`sources.toml:7-9`). R-blast R3 predicts the `schema-vendor-check` break that this fixes. |
| `tests/test_schema_vendor.py` | `:434-440` builds the shared.toml form. Rewrite it to the vendored form. |
| `pin-parity.toml` | **NEW `[tools.codex]`**. Its sites are `schemas/sources.toml` `version` (anchored through `tool = "codex"`/`file`, as claude-code does at `:103-117`) and `.devcontainer/Dockerfile` `ARG CODEX_VERSION=`. **Add** a `.devcontainer/Dockerfile` `ARG CLAUDE_CODE_VERSION=` site to `[tools.claude-code]` (`:84-120`). |
| `.github/actions/setup-codex/action.yml` | **NEW** composite (§3e), modelled on `setup-claude-code/action.yml`. It takes an optional `version` input; when that is empty, it reads the pin with `uv run --project python dotfiles-setup schema-vendor pin --tool codex`. |
| `.github/workflows/ci.yml` | Delete `:69-72` (the comment and `MISE_DISABLE_TOOLS: ""`). In `contract-preflight` (`:184`), add `uses: ./.github/actions/setup-codex` right after `setup-mise` (`:222`) and before pytest (`:245`). |
| `mise.toml` | Delete `:164-169` (the comment and `disable_tools = ["npm:@openai/codex"]`). It becomes dead once shared.toml drops codex (R-chan §1 H3). |
| `doctor.toml` `[claude]` (`:243-270`) | **Pending probe D5.** If the in-image claude reports a non-`native` install method, make the expectation container-aware. Do not switch the check off (`:267-270`). |

### 2d. knowledge-base half: a NEW worktree

Create `knowledge-base.worktrees/native-cli-installers-20260930`, on branch `chore/native-cli-installers-20260930`, cut from `origin/main` `d8a205da`. Ship it with `mise run kb-ship`. The primary KB checkout is on `main`, dirty and live, so it is skipped.

| Path (KB) | Action |
|---|---|
| `python/src/kb_setup/review.py` | **First, in the same commit:** at `:387-389`, fall back to the row's reviewed `expected` when `sync.pinned_version` returns `""`. The shape is `pinned = pinned or (spec.expected or "")`, so `_reviewer_pin_gap` (`:318-400`, Ray's REFUSE ruling of 2026-08-23) keeps firing. Add a mutation test that changes `expected` and requires a refusal (R-crit I, improvement 6). The name map `_REVIEWER_CLI_MISE_KEYS` (`:309-315`) already maps to the table names `codex`/`antigravity-cli`, which `:384` matches against `s.name`, so it needs no change. |
| `currency.toml` | `[tool.codex]` (`:1855-1856`): drop `mise_key = "npm:@openai/codex"` and add `expected = "<current reviewed codex>"` in the self-managed form of `[tool.claude-code]` (`:974-985`). **`[tool.antigravity-cli]` is already self-managed** (`expected = "1.2.12"` at `:1950`, R-prem P17 REFUTED). Leave it, unless `kb-setup currency check` fails after the pin goes. |
| `mise.toml` | Delete `:239` `"npm:@openai/codex" = "0.154.0"` and `:240` `antigravity-cli = "1.2.12"`. Replace the provenance comment `:171-238` with a one-line pointer to this spec. |
| `mise.lock` | Scoped removal of `[[tools.antigravity-cli]]` at `:4719` and `[[tools."npm:@openai/codex"]]` at `:6673`. `kb-lock-drift` (`gates.py:196`) flags a stale tool entry (`lock_drift.py:62-64`), so `kb-ship` fails without this (R-prem). |
| `python/src/kb_setup/codex_run.py:720`, KB `.claude/rules/ai-cli-invocation.md:18`, `.claude/skills/kb-review/references/lanes.md:256` (and `.agents/` mirror) | Reword "mise pins codex/agy" to native (R-prem, unlisted stale text). |

### 2e. The worktree sweep (R1): one agent per target

**Execution-time rule.** Every row below is a **snapshot** probed on 2026-09-30 (§7 P33). Before editing, the executing agent re-evaluates each target. It **skips and reports** a target when any of these holds:
- **not a git repo**;
- **detached HEAD, or on a default branch** (`main`/`master`/the remote HEAD branch);
- **dirty** (`git status --porcelain` is non-empty);
- **live writer**: an `lsof -a -d cwd +D <path>` hit, or a `ps` command line that names the path (scoped per memory `feedback_scope_process_hunts_to_this_project`).

Otherwise the agent does the following, in order:
1. Copy each file to `<scratchpad>/<repo>-<branch>-<file>.bak-native-clis-<stamp>`.
2. Edit.
3. Run the gate that repo's hooks run.
4. Commit on that branch (message in §6).

It reports `path | branch | sha | backup`, or `path | SKIPPED | reason`. **No push**; each branch owner ships.

**What a worktree commit contains:**

| Repo | Commit content | Why this and not more |
|---|---|---|
| dotfiles worktrees | Host lines only: the `antigravity-cli` line and its scoped `mise.lock` block, and where present `"github:anthropics/claude-code"`. | The image/CI half needs lock regeneration and a proven install, which cannot be replayed onto another lane's branch. It reaches them through `main` on rebase (Q11). |
| KB worktrees | `git cherry-pick` of the §2d KB commit, which carries the pin removal, lock prune, currency conversion and review fallback **together**. On conflict, run `git cherry-pick --abort` and **SKIP**. | A bare pin removal would disarm `_reviewer_pin_gap` (R-crit I) and trip `kb-lock-drift`. |
| HEL worktrees | `git cherry-pick` of the §2f HEL commit (pin removal **plus** the CI native codex install). On conflict, abort and SKIP. | R4 / P19: HEL's pin goes only together with its CI install. |

**Snapshot of the targets** (re-probed for this revision; the control arm is this worktree, which shows dirty=12):

| Target | Branch | State (2026-09-30) | Pin lines | Decision |
|---|---|---|---|---|
| `dotfiles.worktrees/agent-team-research-skill` | `codex/agent-team-research-skill` | clean | `antigravity-cli` `:126` | EDIT |
| `dotfiles.worktrees/worktree-orchestration-20260929` | `codex/worktree-orchestration-20260929` | clean | `:126` | EDIT |
| `dotfiles.worktrees/project-sync-readiness-20260928` | `codex/dotfiles-project-sync-readiness` | clean | `:128` | EDIT |
| `dotfiles.worktrees/currency-20260930` | `chore/currency-20260930` | **clean now** (was dirty in rev 0) | `:126` | EDIT if still clean |
| `dotfiles/.claude/worktrees/agent-a6e5728e0204c312c` | `research/codex-exec-review-settings` | clean | `:127` (1.2.8) | EDIT |
| `dotfiles/.claude/worktrees/agent-a82a7019cd7d3bac4` | `research/hk-2-0-impact` | clean | `:127` | EDIT |
| `dotfiles.worktrees/research-five-source-gate` | detached | — | `:126` | SKIP (detached) |
| `dotfiles.validation/research-five-source-land` | `main` | — | `:126` | SKIP (default branch) |
| `dotfiles.worktrees/{agentsview-managed-service, agentsview-native-service}` | `codex/agentsview-*` | dirty 8 / 6 | `:43 "github:anthropics/claude-code" = "2.1.270"`, `:132 antigravity-cli = "1.2.3"` | SKIP (dirty); report **both** lines (R-prem) |
| `~/.codex/worktrees/3f4c/dotfiles` | `codex/graphify-0-9-67` | dirty 14 | `:127` | SKIP (dirty) |
| `~/.codex/tools/dotfiles-research-gate` | `main` | — | `:126` | SKIP (default branch) |
| primary `dotfiles` | `feat/doctor-devcontainer-arches` | dirty, live writer | `:126` | SKIP; reached through `main` |
| `knowledge-base.worktrees/{cli-maintenance-20260922, cli-maintenance-51237d45-20260924, cli-maintenance-93c019a5-20260924, graphify-claude-handoff-20260928, graphify-claude-handoff-docs-20260929, graphify-live-evidence-d5-20260928, cli-v0971-integration-20260928, kb-project-sync-v0971-20260928}` | `codex/*` | all clean | codex and `antigravity-cli` lines | EDIT by cherry-pick |
| KB `{graphify-live-bootstrap-20260927, cli-signer-074b024-20260927, cli-cold-review-d5-20260928, cli-review-arms-bb95-20260927}` | detached | — | — | SKIP |
| KB `{agentsview-kb-source-refresh, codex-0155-alignment-20260918, issue-1-cli-delivery-d2, issue-1-cli-integration, cli-parity-9fa-20260925, cli-final-main-20260927}` | — | dirty (rev 0) | — | SKIP unless clean at run time |
| `harness-evolution-ledger-fnox-1.35.3` | `codex/fnox-1.35.3` | clean | `:40 codex = "0.150.0"` | EDIT by cherry-pick of §2f |
| `~/.codex/worktrees/3191/harness-evolution-ledger` | `codex/phase-0-bootstrap-completion` | clean | `:40` | EDIT by cherry-pick |
| `~/.codex/worktrees/hel-session-review/harness-evolution-ledger` | `codex/session-review-port-prep` | clean | `:25 "npm:@openai/codex"` | EDIT by cherry-pick |
| HEL primary | `main` | live writer | `:40` | SKIP; the §2f change lands through a HEL PR |
| `~/.codex/worktrees/7cb9/harness-evolution-ledger` | detached | — | `:40` | SKIP |
| `claude-code-marketplace` | — | dirty, live writer | `:10 "npm:@anthropic-ai/claude-code"`. It is a host pin **and** the OCI image under test (`acceptance.yml:30`, `:34`) | SKIP; report it as needing its own native-install change |
| `cpp-playground`, `gemini-ai-macos-development-environment`, `modern_cpp_kb`, `~/dev/symphony-cpp` (plus its 10 detached `~/.codex/worktrees/*/symphony-cpp`) | — | dirty / default / detached | codex/claude pins | SKIP; report the exact lines |
| `rio/dotfiles`, `safishamsi/claude/graphify` | — | third-party | — | SKIP (never ours) |
| `~/dev/tmp/kb2/mise.toml` | — | **not a git repo** | `:4 codex = "latest"` | SKIP (R1) |
| `~/.codex/archives/**`, `~/.codex/visualizations/**`, `~/.config/mise/{docs,agentsview-native}/**/fixtures/**` | — | frozen evidence / fixtures | — | **NEVER EDIT** |

### 2f. harness-evolution-ledger half: a NEW worktree (R4, P19)

Create `harness-evolution-ledger.worktrees/native-codex-ci-20260930`, on branch `chore/native-codex-ci-20260930`, cut from `origin/main`. It ships through a HEL PR: `gh pr create -R ray-manaloto/harness-evolution-ledger` is allowed, because HEL has no canonical ship task (`mise-tasks-only.md` repo-aware dispatch).

| Path (HEL) | Action |
|---|---|
| `.github/workflows/phase0.yml` | After `jdx/mise-action` (`:39-43`) and **before** `mise run doctor` (`:46`), add a native codex install step. It calls `ray-manaloto/dotfiles/.github/actions/setup-codex@<sha>` with `version: <HEL pin>`, SHA-pinned so pinact passes (Q12). It is needed because `mise run doctor` reaches `phase0.py:163` (`codex plugin list`) and `:225` (`codex --version`), and `mise run rules:verify` (`:55`) reaches `verify_rules.py:48` (`codex execpolicy check`). |
| `mise.toml` | Delete `:40` `codex = "0.150.0"` **in the same commit**. |
| HEL pin site | Record the codex version the workflow installs (Q12). |

---

## 3. Interfaces

### 3a. `python/src/dotfiles_setup/native_clis.py`

```python
@dataclass(frozen=True)
class NativeCli:
    name: str                              # "agy" | "codex" | "claude"
    binaries: tuple[str, ...]              # ("agy",) | ("codex",) | ("claude",)   — S6: never "antigravity"
    must_not_resolve_under_mise: tuple[str, ...]  # agy: ("antigravity",) — absence is fine, a mise hit is a finding
    native_path: Path                      # ~/.local/bin/<name>, expanded against an injected home
    native_realpath_root: Path | None      # codex: ~/.codex/packages/standalone ; claude: ~/.local/share/claude/versions ; agy: None
    team_id: str                           # EQHXZ8M8AV | 2DC432GLL2 | Q6L2SF6YDW (P22, re-derived)
    resolution_checked: bool               # agy, codex: True ; claude: False — claude-doctor owns it (R-crit E)
    release_repo: str                      # google-antigravity/antigravity-cli | openai/codex | anthropics/claude-code
    tag_format: str                        # "{v}" | "rust-v{v}" | "v{v}"   (P35, measured)
    version_regex: str                     # parses `<bin> --version`

@dataclass(frozen=True)
class NativeCliPolicy:
    enabled: bool
    tools: tuple[NativeCli, ...]
    lookalikes: tuple[str, ...]            # reviewed non-CLI keys: npm:claude-code-lint, npm:oh-my-claude-sisyphus, npm:oh-my-codex

@dataclass(frozen=True)
class Finding:
    check: str                             # "pins" | "tracked-pins" | "resolution" | "signature" | "global" | "ledger"
    tool: str
    message: str                           # names the file:line / path / version and the fix

def load_policy(doctor_toml: Path, *, home: Path) -> NativeCliPolicy: ...

def find_active_mise_pins(policy, ls_current: Mapping[str, list[Mapping[str, object]]]) -> list[Finding]:
    """(a) BY SHAPE (R-crit C, improvement 2): parse `mise ls --current --json` with
    `path_drift.active_tools()` (no second parser). An active tool whose `install_path` contains an
    executable named in `binaries` or `must_not_resolve_under_mise` is a finding that names
    `source.path`. Keys in `lookalikes` are skipped only when their install_path provides NONE of
    those names (a lookalike that starts shipping `claude` is still caught)."""

def find_tracked_pins(policy, repo_root: Path, *, ls_files: Callable[[Sequence[str]], list[str]]) -> list[Finding]:
    """(b) Lint. Scan set (R-crit D, improvement 4):
    `git ls-files 'mise*.toml' '.mise*.toml' 'mise/config.toml' '.mise/config.toml' '.config/mise.toml'
    '.config/mise/**/*.toml' '.devcontainer/mise-*.toml' 'mise-global/**/*.toml'`, EXCLUDING
    `docs/research/kb/raw/**`. `mise.arm64.toml` on the sibling branch ecbae52a is the named trigger.
    A [tools] key whose normalised name (backend prefix stripped, then the last path segment or the
    npm package name) is one of codex / claude / claude-code / antigravity-cli / agy / antigravity,
    and that is not in `lookalikes`, is a finding. The allowlist of rev 0 is GONE: after §2c no
    image or CI pin remains to allow."""

def find_stale_resolutions(policy, ambient_path: str, *, home: Path, mise_which: Callable[[str], str | None],
                           verify_signature: Callable[[Path, str], int], platform: str) -> list[Finding]:
    """(c) Effective first hit (R-crit E, improvement 3). For each binary of a tool with
    `resolution_checked`, walk PATH. SKIP a `~/.local/share/mise/shims/<bin>` hit when
    `mise_which(bin)` reports it inactive, because the shim execs the next PATH hit
    (feedback_nonexec_file_cannot_shadow_shell_lookup, mise shims.rs:186). The first
    remaining hit is the effective target. Findings:
      (1) the effective target's realpath is under ~/.local/share/mise/installs/;
      (2) no effective target (the tool is absent);
      (3) any `must_not_resolve_under_mise` name resolves under the installs root.
    Reuse `path_drift.path_versions()`. Signature (S1, R-crit K), darwin only, for ALL THREE tools'
    effective targets: `verify_signature(realpath, team_id)` wraps
    `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM>"'`.
    rc 0 = pass; 1 = invalid or modified; 3 = wrong team; anything else = a finding naming the rc.
    NEVER `codesign -dv`: it reports TeamIdentifier for a tampered binary at rc 0 (R-sec M1)."""

def ledger_status(policy, *, receipts_root: Path, run_version: Callable[[NativeCli], str | None]) -> list[Finding]:
    """(e) OFFLINE (R2). For each tool, read the running version: `<native_path> --version`, run with
    a MINIMAL env (HOME, PATH, TMPDIR, LANG, USER, SHELL) plus AGY_CLI_DISABLE_AUTO_UPDATE=true
    (the literal) and DISABLE_AUTOUPDATER=1, scoped to the probe (S7). Findings:
    (i) no `docs/receipts/<tool>/<running>.md`;
    (ii) running < max receipted version, i.e. a DOWNGRADE (S2: the Team ID check cannot see one).
    An unreadable version is a finding, never a pass."""

def write_receipts(policy, tool: str, *, repo_root: Path, run: Runner, now: Callable[[], datetime],
                   default_branch: Callable[[], str]) -> tuple[Path, ...]:
    """The R2 writer, the SAME SHAPE as graphify_currency.release_notes_between +
    write_release_receipts (graphify_currency.py:261-338). Refuse with rc 1 on the default branch
    (do-not #9). Fetch `gh api repos/<release_repo>/releases --paginate` and select releases in
    (max receipted, running], mapped through `tag_format`, EXCLUDING prereleases unless the running
    version is itself a prerelease. With no prior receipt, the range is the running version only.
    Write `docs/receipts/<tool>/<v>.md` with the header
    `# <Tool> <tag> release receipt`, `Written by \`mise run native-cli -- receipts --write\`.`,
    `- Tag:`, `- Published at:`, then `## Release notes (verbatim)` and the body. APPEND one row
    to `docs/receipts/native-cli/LEDGER.md`. A missing target release or a missing `published_at`
    raises; it is never a silent empty receipt."""

def link_global(repo_root: Path, *, home: Path, apply: bool) -> LinkResult:
    """(R3) For each tracked `mise-global/conf.d/*.toml`, ensure
    `~/.config/mise/conf.d/<name>` is a symlink to it. Refuse unless repo_root is the PRIMARY
    checkout (git-dir == git-common-dir): a worktree target dangles once the worktree is removed.
    Refuse to replace a regular file (report it). Idempotent. `apply=False` is the drift check."""

def check_global(repo_root: Path, *, home: Path, global_config: Path) -> list[Finding]:
    """(d) The link exists and points at the tracked file. Also tomllib-read global_config
    (read-only) and assert `tasks."update:all".depends` contains every task the fragment defines.
    This closes R-crit G's "the drift check cannot see its own `depends` edit"."""

def status(policy, ...) -> list[ToolStatus]:   # effective hit, version, signature rc, updater switch state (C8), receipt state
```

`Runner` and `mise_which`/`verify_signature` are injected, following the `bounded_wait.wait(..., command_runner=...)` pattern. Unit tests never spawn a vendor binary and never touch the network. S1's **real-codesign arm** (§5 test 3) is the one deliberate exception, and it is darwin-only.

### 3b. CLI (`dotfiles-setup native-cli`) and `doctor.toml`

```
native-cli status [TOOL...] [--json]         # rc 0
native-cli check-pins                         # (b) tracked files — the hk step; rc 0 clean / 1 findings
native-cli check-host                         # (a)+(c) on DOTFILES_AMBIENT_PATH; rc 0 / 1 / 2 BLIND
native-cli receipts (--check | --write [TOOL...])   # (e); --write refuses on the default branch
native-cli link-global (--check | --apply)    # (d)/(R3)
```

- **The BLIND rc is 2**, matching `path_drift.py:364-369` (rev 0 said 3; R-prem blocking).
- **BLIND occurs only when `MISE_TASK_NAME` is set** and no ambient capture exists. Outside mise, a missing capture is INHERITED (`path_drift.py:167-177`; R-prem P9). The CLI reports whichever state applies, never a pass.

```toml
[native_clis]
# Vendor CLIs owned by their native installer + self-updater on the host; pinned+verified native
# artifacts in the image/CI (spec native-cli-installers-2026-09-30 rev 1). Policy only; paths are mechanics.
enabled = true
lookalikes = ["npm:claude-code-lint", "npm:oh-my-claude-sisyphus", "npm:oh-my-codex"]

[native_clis.tools.agy]
binaries = ["agy"]
must_not_resolve_under_mise = ["antigravity"]
team_id = "EQHXZ8M8AV"

[native_clis.tools.codex]
binaries = ["codex"]
team_id = "2DC432GLL2"

[native_clis.tools.claude]
binaries = ["claude"]
team_id = "Q6L2SF6YDW"
resolution_checked = false   # claude-doctor (doctor.py:1409, doctor.toml:243-265) owns resolution
```

### 3c. The R3 global fragment

`mise-global/conf.d/50-native-cli.toml` (tracked):

```toml
# Linked into ~/.config/mise/conf.d/ by `mise run native-cli -- link-global --apply`
# (ray-manaloto/dotfiles; lightster/.dotfiles pattern). Vendor-native verbs only (C6).
# update:all's `depends` in ~/.config/mise/config.toml names these tasks: a fragment cannot
# override config.toml (measured 2026-09-30), so that one line lives there, checked by doctor `native-cli-global`.
[tasks."update:agy"]
description = "update the native agy (Antigravity CLI) in place"
run = "agy update"

[tasks."update:codex"]
description = "update the native codex standalone package"
run = "codex update"
```

**Evidence for the shape:**
- **Upstream support.** jdx/mise `docs/bootstrap.md:54` (ref `8a1042b3`, re-fetched for this revision) lists "Global mise configuration such as `config.toml`, `conf.d/`, and `tasks/`" as a supported shared layout. The mise config docs list `~/.config/mise/conf.d/*.toml` as global fragments (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:1131-1139`).
- **Real-world precedent.** R-confd: `lightster/.dotfiles` `mise/tasks/configs.sh:8, :18-19, :32-33` does `mkdir -p ~/.config/mise/conf.d` and `ln -sfn "$DOTFILES"/mise/<x>.toml ~/.config/mise/conf.d/<x>.toml`. `path:.config/mise/conf.d` has 341 hits, and 147 of them hold tasks (the must-hit control has 1020 hits, the fresh absent term 0).
- **Folder name.** It is deliberately **not** under `.config/mise/conf.d/`. That path is a *project* fragment location (`llms-full.txt:1105`), so this repo's mise would load the global tasks as project config. `mise-global/` matches none of the names in `llms-full.txt:1099-1105`. D2 in §5 arms this.
- **Not `update:claude`.** The existing global `update:claude` (`config.toml:383`) is a 226-plugin updater, not `claude update` (R-crit G). claude self-updates, so the fragment adds no claude verb.

### 3d. The R2 version ledger

- **Receipts** go in `docs/receipts/<tool>/<v>.md`, where `<tool>` is `agy`, `codex` or `claude`. The writer shape matches graphify's (`graphify_currency.py:319-338`, exemplar `docs/receipts/graphify/0.9.65.md`).
- **Release sources** were measured on 2026-09-30 with `gh api repos/<r>/releases`. All three publish release bodies (the bogus-repo control returned 404):

  | Tool | Tag format | Latest measured | Notes |
  |---|---|---|---|
  | codex | `rust-v<v>` | `rust-v0.159.2`, body 321 B | prereleases `rust-v0.161.0-alpha.*` are flagged `prerelease=true` |
  | claude | `v<v>` | `v2.1.286`, body 12,859 B | |
  | agy | bare `<v>` | `1.2.14`, body 2,145 B | |
- **`LEDGER.md`** is append-only. Each row is `observed_at (UTC) | tool | previous receipted | running | receipts written | branch@sha`, and a downgrade row says `DOWNGRADE`. Rows are never rewritten, which follows the `goal-history.md` append-only discipline.
- **The loop:**
  1. A vendor self-updates.
  2. The SessionStart doctor reports `native-cli-ledger: codex 0.160.0 running; docs/receipts/codex/0.160.0.md missing`.
  3. Ray runs `mise run native-cli -- receipts --write` on a branch.
  4. He reviews the verbatim notes.
  5. He runs `mise run ship`.
- **What the ledger does NOT do.** It does not *prevent* anything. It records and surfaces what already ran (S2). It is a review trail, not a gate.

### 3e. Image and CI native installs (pin + verify)

Pins live in `schemas/sources.toml`: the claude-code row (`:51-56`, existing) and the codex row (`:43-48`, vendored per §2c). `pin-parity` binds both to the Dockerfile `ARG`s.

**claude, image** (RUN in `devcontainer-runtime`, gpg is already present from `Dockerfile:187`). The shape comes from R-chan §2 and R-sec S5a:
1. Fetch `https://downloads.claude.ai/keys/claude-code.asc`. Assert its fingerprint equals `ARG CLAUDE_CODE_SIGNING_FINGERPRINT` before trusting it (LLVM precedent `:183-202`), using an isolated `GNUPGHOME`.
2. Fetch `…/claude-code-releases/${CLAUDE_CODE_VERSION}/manifest.json` and `manifest.json.sig`, then run `gpg --verify`.
3. Fetch `…/${CLAUDE_CODE_VERSION}/linux-<x64|arm64>/claude`. Its sha256 must equal `platforms["linux-<arch>"].checksum` from the **verified** manifest.
4. Install to `/usr/local/lib/claude/${CLAUDE_CODE_VERSION}/claude` and `ln -s` it to `/usr/local/bin/claude`.
5. The post-condition is `claude --version` containing the pin.
6. `ENV DISABLE_AUTOUPDATER=1` (Q10).

Never pipe the bootstrap: `bootstrap.sh:148-149` always runs the **latest** binary first (R-sec M8).

**codex, image** (same stage). The shape comes from R-chan §3 and R-sec S5b:
1. Fetch `github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/codex-package-<x86_64|aarch64>-unknown-linux-musl.tar.gz` and `codex-package_SHA256SUMS`.
2. Verify the sha256 against SUMS.
3. **Optional, recommended:** run `cosign verify-blob` on the `.sigstore` bundle with `--certificate-identity https://github.com/openai/codex/.github/workflows/rust-release.yml@refs/tags/rust-v${CODEX_VERSION}` and `--certificate-oidc-issuer https://token.actions.githubusercontent.com` (Q13; cosign is not in the image today).
4. Extract to `/usr/local/lib/codex/${CODEX_VERSION}/` and `ln -s …/bin/codex /usr/local/bin/codex`.
5. The post-condition is `codex --version` equal to the pin.

Do not use `install.sh` in the image: it writes into `$CODEX_HOME`/`~/.local/bin`, which is the home volume, and it edits rc files (R-cstat F4, R-chan §3 "Shell rc edit").

**codex, CI** (`.github/actions/setup-codex`):
1. Resolve `version`: the input, or else `schema-vendor pin --tool codex`.
2. Download `install.sh` **to a file**, never piped (C4).
3. Run it with `CODEX_NON_INTERACTIVE=1` and `--release "$version"`. The installer checks sha256 against the release metadata and `SHA256SUMS` (R-chan §3).
4. Control arm 1: `command -v codex`.
5. Control arm 2: `codex --version` contains the pin.

Use `set -euo pipefail`. No `$GITHUB_PATH` write, following the zizmor reasoning in `setup-claude-code/action.yml:33-41`.

---

## 4. Constraints

- **C1: consent boundary.**
  - Approved: the removals, R1–R4, the global `:142` delete (still gated on Q3, per C2), the `update:all` one-line edit and the `link-global` symlink.
  - **Not** approved until Ray answers:
    - Q2: `mise uninstall` of the install dirs;
    - Q3: running `agy update` or the native agy installer against `~/.local/bin`;
    - Q10: switching the updater off *inside the image*;
    - any change to credentials (Q8) or the claude channel (Q9).
- **C2: order (R-crit H).**
  1. **Q3 first:** bring native agy current.
  2. Re-probe **by absolute path**: `~/.local/bin/agy --version && ~/.local/bin/agy --help`. Never `mise exec -- agy`, which resolves `installs/antigravity-cli/1.2.14/agy` while either pin exists (improvement 8).
  3. Only then remove the repo `:126` and global `:142` agy pins.
  4. Run `mise reshim` and **start a new shell**.

  Worktree agy removals may run before Q3 only while the global pin still exists.
- **C3: the image/CI half lands atomically.** `shared.toml` npm codex, `mise.toml` `disable_tools`, `ci.yml` `MISE_DISABLE_TOOLS`, `setup-codex`, the Dockerfile installs, the `sources.toml` codex pin, the `schema_vendor` resolver, `pin-parity` and the three locks go in **one commit**. Removing any one alone either breaks CI pytest (`ci.yml:218-221`, codex among the "host-merged tools") or leaves a dead guard.
  - It lands **before** the host-half commit, because the new `native_cli_pins` hk step would reject shared.toml and mise-runtime pins still present.
  - Renovate PRs #1449 (shared.toml codex bump), #1444 and #1093 (claude-code lock hunks), all OPEN 2026-09-30, will conflict or go obsolete. Close or rebase them after merge (R-blast R5).
- **C4: zero-bash-logic and mise-tasks-only.**
  - No new `.sh` files.
  - The hk step, mise task and composite action are thin callers; the logic lives in `native_clis.py`.
  - The Dockerfile verify RUNs follow the documented inline precedent (LLVM fingerprint `:183-202`), because the image stage has no `dotfiles_setup` on hand.
  - **No new `curl | sh`.** The existing `setup-claude-code/action.yml:45` pipe is pre-existing (R-sec S8), and it is filed in §6 F2.
  - No `shell=True`.
- **C5:** no inline suppressions (`no_lint_skip`), Python 3.14, and ruff and ty clean. Follow the `removed_plugins` and `path_drift` idioms.
- **C6: global call site.**
  - The fragment runs only vendor verbs. It never calls `uv run --project <mutable checkout>`, which was struck in `mise-native-dotfiles-plan.md:343-345`; `$DOTFILES_SETUP_PROJECT` has 0 hits in the global config.
  - The symlink binds the fragment's *content* to the primary checkout's current branch. That is acceptable only because the content is two vendor verbs.
  - `link_global` refuses a worktree target.
  - S29-M (`mise-native-dotfiles-plan.md:277`) plans to make `config.toml` a symlink. The one-line `depends` edit is a plain in-place edit, so it cannot replace a link with a file.
- **C7: doctor contract.**
  - The four new checks are non-LIVE.
  - Budget: `mise ls --current --json` at most twice, `mise which` once per checked binary, `codesign --verify` once per effective target (about 0.5–0.75 s each, about 1.8 s per session; R-sec M3), and `<bin> --version` once per tool (the ledger).
  - The signature clause returns `[]` on non-darwin.
  - `mise run doctor` still exits 0 without `--strict`.
- **C8: self-update policy (R2).**
  - Host: ON. The module never sets or unsets `DISABLE_AUTOUPDATER`/`DISABLE_UPDATES`, the codex `app-server-daemon/settings.json` `updater.autoUpdateEnabled`, or `AGY_CLI_DISABLE_AUTO_UPDATE` in the user's environment or files. It sets them **only inside its own probe subprocess** (S7). `status` reports each switch.
  - Image: pinned artifacts, with the updaters OFF (Q10), because an in-container update writes into the home volume and shadows the verified system copy. That is the same defect class as D3 (agy updating inside mise's dir).
- **C9: security posture (S2, S9, R-crit K; corrected from rev 0).**

  | | Install integrity | Update channel | Stronger check we now use | Replaced mise backend |
  |---|---|---|---|---|
  | claude | sha256 against the same-origin `manifest.json`; no signature | a closed-source in-binary updater, **likely with no signature check** (R-sec M18, string evidence) | **Image:** GPG manifest verify with the pinned fingerprint `31DD…CACE`. **Host:** `codesign --verify -R` for Team Q6L2SF6YDW | image `aqua:anthropics/claude-code`: a TOFU sha256 in the lock |
  | codex | sha256 against release metadata plus `SHA256SUMS`, same origin | the daemon runs the unsigned `install.sh` with `CODEX_RELEASE=latest`, hourly (R-sec S9) | **Image:** SUMS (+ cosign, Q13). **Host:** `codesign --verify -R` 2DC432GLL2 | `npm:@openai/codex` under bun; the lock records **version only** (`.config/mise/mise.lock:531-536`) |
  | agy | sha512 against a same-origin manifest; no signature | an in-place background update; no signature | **Host:** `codesign --verify -R` EQHXZ8M8AV (the only vendor-bound check) | `aqua:…/antigravity-cli`: TOFU, **already void** (it self-updates inside mise's dir; R-sec M6: 9 of 23 dirs) |

  - **Credit the check, not the channel.** The mise copy carries the same Team ID (R-crit K), so the signature check was available under mise too. It proves *vendor identity*. It does **not** prove the version or the bytes that were reviewed, it cannot see a validly signed malicious build, it cannot see a **downgrade** (the ledger's downgrade finding covers that), and it cannot see anything the unsigned installer or updater *scripts* do. It is **not preventive**: it runs at SessionStart, after new code has already run with the full env.
  - Compromise reach is unchanged from mise and large (R-sec S3): 56 env credentials, and a `GITHUB_TOKEN` with `repo, workflow, write:packages, admin:org`. That is Q8.
  - The host's net supply-chain delta from removing the pins is about zero (R-sec S10). The security value is the verify-based signature check (S1) plus the image/CI move from version-only locks to verified pinned artifacts.
- **C10: rollback.**

  | What | Rollback |
  |---|---|
  | Repo commits | `git revert <sha>` on a new branch, then `mise run ship`. Re-lock scoped (`mise run lock -- "aqua:google-antigravity/antigravity-cli"`, `mise run lock-shared -- "npm:@openai/codex"`, `mise run lock-image`), never bare. |
  | Image | Revert the image commit. CI rebuilds (cold base, C13). Until then, `mise run sync -- --tag <prior>` pins the previous image. |
  | Global config | `cp -p ~/.config/mise/config.toml.bak-native-clis-<stamp> ~/.config/mise/config.toml`, `rm ~/.config/mise/conf.d/50-native-cli.toml`, `mise install antigravity-cli`, `mise reshim` |
  | agy binary | `mv ~/.local/bin/agy.bak-native-clis-<stamp> ~/.local/bin/agy`, or the GitHub asset `agy_cli_mac_arm64.tar.gz`. Hold it with `AGY_CLI_DISABLE_AUTO_UPDATE=true`. The server may refuse old versions (#568). |
  | codex | Re-point `~/.codex/packages/standalone/current` at a retained `releases/<ver>-…`, or `install.sh --release <ver>`. Hold it with daemon `settings.json` `{"updater":{"autoUpdateEnabled":false}}` plus a daemon restart. |
  | claude | `claude install <ver>`. Hold it with `DISABLE_AUTOUPDATER=1`. |
  | Worktree commits | `git revert` on that branch. The scratchpad backup is the byte-exact prior copy. |
  | KB / HEL | `git revert` on a new branch, then `kb-ship` / a HEL PR. |
  | Machine checks | `[native_clis].enabled = false` in a reviewed diff. That reports "not asked", never "healthy". |
- **C11: work boundary.**
  - Work in this worktree, plus the new KB and HEL worktrees and the R1 sweep targets.
  - No push or ship by the implementer; shipping is the coordinator's `mise run ship` / `kb-ship` / HEL PR.
  - Never edit `task_plan.md`.
  - Never run `chezmoi apply` on the host, a bare `mise lock`, or a whole-file relock.
  - **Never `mise run build` or a local bake** (do-not #2). D1–D6 use throwaway `docker run --rm` only.
- **C12: sweep residual risk (the critique's J, overruled by R1).**
  - `lsof`/`ps` cannot see a *paused* codex lane that will resume (`goal-history.md`; memory `feedback_lane_done_does_not_release_the_checkout`). A commit onto a paused lane's branch can collide with it on resume.
  - Mitigations: one commit per branch, small and scoped to pin lines; cherry-pick with abort-on-conflict; and the report line lets the owner revert.
  - Several targets are 22–85 commits behind `origin/main` (R-crit J), so their edits change nothing anyone runs until rebase.
- **C13: cold image rebuild (R4).**
  - `shared.toml` is a `devcontainer-base` input (`Dockerfile:139`). Removing codex from it invalidates the base, so the PR's CI runs a **cold** base build: about 2.5 h, against about 10 min warm (memory `feedback_ci_build_duration_baseline`, an inherited figure).
  - The claude/codex RUNs and the `mise-runtime` edits touch only the thin `devcontainer-runtime` stage (`:666`).
  - Per `verify-before-advancing.md`, locally validating a branch that changes an image build input uses the **merge-base** identity. The new base is validated by that PR's own CI, then pre-validated locally with `mise run sync -- --tag pr-<n>`.
- **C14: the critique's improvements, and where each lands.**
  1. `codesign --verify -R` goes into §3a (c) and L5.
  2. Shape detection goes into §3a (a).
  3. The effective hit through the shim goes into §3a (c).
  4. The widened scan set goes into §3a (b).
  5. The fragment file is §3c (it also answers R3).
  6. The KB fallback is §2d.
  7. If currency is ever revived, generalise `claude_doctor` rather than build a LIVE module (noted in Q14, not built).
  8. The absolute-path re-probe goes into C2.
- **C15: receipts are verbatim vendor text.** They must pass the lint gate. If typos or markdown lint flags a vendor body, add `docs/receipts/{agy,codex,claude}/**` to `hk-common.pkl` `excludePaths` (`:42`), next to the verbatim research trees. That needs **Ray's approval** (zero-skip policy), so it is open question Q15. The secret scanners must still read the trees (`workflow.verbatim-trees-secret-scanned`).

---

## 5. Verification

Report every result as a **real rc read from a file**, never from a pipe.

**Gates** (`mise run gate -- run <name>`), per commit:
- `lint`, `pytest`, `verify`;
- `lint-docs`, because `.claude/**` changed;
- **`pin-actions`**, because `.github/**` changed (`setup-codex`, `ci.yml`);
- `mise run rule-sync`, because `.claude/CLAUDE.md` changed (only whole-line and stem sync, `rule_sync.py:144-148`);
- `mise run pin-parity`;
- `mise run schema-vendor-check`.

The KB and HEL halves run their own `mise run lint`/pytest, and the KB runs `kb-setup currency check`, which must report no "has no pin" for `codex` or `antigravity-cli`.

**Unit tests** (`tests/test_native_clis.py`). Fixtures mirror the real configuration (rule 8):

1. `find_active_mise_pins`:
   - A real-shape payload in which `antigravity-cli`'s `install_path` holds `agy` gives 1 finding naming `source.path`.
   - An `http:agy` key under another name gives a finding. This is the shape arm the key list missed.
   - A lookalike whose `install_path` holds only `omc` gives `[]`.
   - The same lookalike with an added `claude` executable gives a finding.
2. `find_tracked_pins`:
   - The post-change tree gives `[]`.
   - **Realistic mutation:** re-add `"npm:@openai/codex" = "0.154.0"` to the fixture shared.toml and expect 1 finding.
   - Add `antigravity-cli` to a fixture `mise.arm64.toml` and expect 1 finding. This is the scan-set arm.
   - A file under `docs/research/kb/raw/` gives `[]`.
   - `npm:claude-code-lint` gives `[]`.
3. `find_stale_resolutions`:
   - A tmp `PATH` whose inactive shim precedes native `codex` gives `[]`. This is the rev-0 false positive.
   - A first hit under `installs/antigravity-cli/1.2.13/` gives a finding.
   - `antigravity` resolving under installs gives a finding; `antigravity` absent gives `[]`.
   - An absent tool gives a finding.
   - `platform="linux"` skips signatures.
   - A missing ambient capture under `MISE_TASK_NAME` gives rc **2**.
   - **Real-codesign arm (darwin-only, S1):** copy a real vendor binary to `tmp_path` and flip one byte. `verify_signature` must return a non-zero rc; the untampered copy must return 0; the wrong team must return 3.
4. `ledger_status` / `write_receipts`:
   - A running version without a receipt gives a finding.
   - Running below the max receipt gives a DOWNGRADE finding.
   - The writer, given a stub `gh` payload holding `rust-v0.160.0-alpha.1` (prerelease) and `rust-v0.160.0`, writes only 0.160.0, with the header fields and verbatim body.
   - `published_at` missing raises.
   - On the default branch it gives rc 1 and no write.
   - LEDGER rows are appended and never rewritten: pre-existing bytes must be a prefix of the result.
5. `link_global` / `check_global`:
   - From a worktree fixture it refuses.
   - It is idempotent.
   - An existing regular file is refused and reported.
   - Removing `update:agy` from the fixture `depends` gives a finding. This is the G arm.
6. CLI wiring: monkeypatch `sys.argv` (`main()` takes no arguments, `main.py:3115`; precedent `tests/test_sdlc_team.py`) and assert `check-pins` reaches `find_tracked_pins`. The `doctor.CHECKS` names include all four new checks.

**Arm the positive at gate level** (rule 2). One at a time, delete the `("native-cli-pins", …)` line in `CHECKS`, the `find_tracked_pins` call in `check-pins`, and the `ledger_status` call. The matching tests must fail. Then restore from `git show`, never with `git checkout --`.

**Local-devcontainer-first proofs** (R4; `.claude/rules/local-devcontainer-first.md`). Run these **before any push** in throwaway `docker run --rm` containers on the pinned base `ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b` (`Dockerfile:14`). Read the base out of the Dockerfile; never restate it. Use `--platform` from `DOCKER_DEFAULT_PLATFORM` (no literal, per `no_platform_literals`). Run both legs, amd64 and arm64. This is not a local build (do-not #2).

| # | Proof | Must show (both arms) |
|---|---|---|
| D1 | The claude recipe of §3e, verbatim, in the container | `gpg --verify` rc 0 and `claude --version` contains the pin. **Control:** one byte appended to `manifest.json` gives BAD signature and rc≠0; a wrong `ARG` fingerprint makes the build step fail. |
| D2 | The codex recipe of §3e | SUMS match, and `codex --version` equals the pin. **Control:** a flipped tarball byte gives a sha256 mismatch and rc≠0. Also run cosign (if Q13 is adopted) with the wrong `--certificate-identity` tag and require rc≠0. |
| D3 | Home-volume masking: run as a non-root user with a named volume at `/home/<u>` that already holds a stale `~/.local/bin/{claude,codex}`, and `PATH` ordered as `Dockerfile.host-user:77` orders it | The new `image.py` provenance smoke **FAILS** on the stale shadow. With an empty volume it **PASSES**. |
| D4 | The `setup-codex` body run in the same container as root, like a runner | rc 0; `command -v codex` resolves, and `--version` equals the pin |
| D5 | `claude doctor` inside the D1 container | Record the install method it reports. That value decides the §2c `doctor.toml [claude]` change. |
| D6 | `mise config ls` from the repo root (host) | Must **not** list `mise-global/conf.d/50-native-cli.toml`. **Control:** `.config/mise/conf.d/shared.toml` is listed. |

**Live arms on the real host, before and after** (real-integration evidence):

| # | When | Command | Must show |
|---|---|---|---|
| L1 | **Before** | `DOTFILES_AMBIENT_PATH="$PATH" mise run native-cli -- check-host > $LOG 2>&1; echo "rc=$?" >> $LOG` | rc=1, with findings for `mise.toml:126`, for global `config.toml` `antigravity-cli`, and for agy's effective hit `installs/antigravity-cli/1.2.13`. This is the positive arm on real state. |
| L2 | Before | `mise run native-cli -- check-pins` | rc=1, naming `mise.toml` `antigravity-cli` **and** `shared.toml` / `mise-runtime.toml` |
| L3 | After, in a new shell, **without Q2** | L1 again | rc=0. Inactive shims remain and must not fire (R-crit E replay 2). |
| L4 | After | L2 again, and the lint step `native_cli_pins` | rc=0 |
| L5 | After | For each of the three effective targets: `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM>"' <realpath>; echo rc=$?` | rc 0 with Teams EQHXZ8M8AV / 2DC432GLL2 / Q6L2SF6YDW. **Control:** the same command with a wrong team gives rc 3. agy ≥ 1.2.14. |
| L6 | After | `cd ~ && mise which agy` (control: `mise which hk` in the repo) | agy is not an active mise bin; hk gives a path |
| L7 | After | `mise exec -- agy --help`, `mise exec -- codex --version` | rc 0 (passthrough, P26) |
| L8 | After | `mise run doctor -- --strict --verbose` | PASS for `native-cli-pins`, `-resolution`, `-global`, `-ledger` (after the initial receipts) |
| L9 | After R3 apply | `mise run native-cli -- link-global --check`, `cd /tmp && mise tasks ls` (lists `update:agy`/`update:codex`), `mise tasks deps update:all`, `mise run -n update:all` | rc 0. Both tasks appear under `update:all`. The dry run lists `agy update` and `codex update` once each. **Control:** before the apply, `mise tasks ls` from `/tmp` lacks them. Re-derive "a fragment cannot override `config.toml`" here (inherited): a fragment `[tasks."update:all"]` must NOT change the resolved `depends`. |
| L10 | Ledger | Delete one initial receipt in a scratch copy, then run `receipts --check` | rc 1 naming the file. Restored, rc 0. |
| L11 | Sweep | Per target: `mise config ls` plus `mise ls --current` from that directory | No forbidden tool is active. The report line records a sha or the skip reason. |
| L12 | After merge | `mise run land -- <PR#>`, then `mise run sync` and `mise run verify-local` | R1/R2/R3 hold on the new image, and the tier-3 provenance smoke passes |
| L13 | HEL | The HEL PR's `phase0.yml` run conclusion (`gh run view <id> --json conclusion`) | `success`, with `rules:verify` and `doctor` having run against the native codex. **Control:** that branch's CI before the setup-codex step existed fails on a missing codex once the pin is removed, which proves the step is load-bearing. |

---

## 6. Commit

This worktree (branch `feat/native-cli-installers-workflow`) gets three commits, in this order, as one PR through `mise run ship`:

1. The **coordinator's existing uncommitted workflow work**: `.claude/workflows/native-cli-installers.js`, `tests/test_workflows_js.py` and the lane reports.
2. **Image/CI half** (§2c, C3):

```
feat(image,ci): install codex and claude natively, pinned and verified; drop mise pins

Remove npm:@openai/codex from shared.toml (+ host disable_tools, ci.yml
MISE_DISABLE_TOOLS) and claude-code from mise-runtime.toml. The image installs
both from vendor artifacts in the runtime stage (claude: GPG-verified manifest
with a pinned fingerprint + sha256; codex: SHA256SUMS), outside the home
volume, with tier-3 provenance smoke. CI gains setup-codex. The codex pin moves
to schemas/sources.toml (vendored) with a pin-parity row. shared.toml is a base
input, so this PR runs a cold base build.
Spec: docs/specs/native-cli-installers-2026-09-30.md (rev 1)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FMeYJgB5KKVuJ14kheDj3d
```

3. **Host half** (§2a):

```
feat(native-cli): host agy/codex/claude native; ledger, global fragment, doctor + lint

Remove the host antigravity-cli pin (mise.toml, mise.lock). Add
dotfiles_setup.native_clis (status, check-pins, check-host, receipts,
link-global), `mise run native-cli`, the native-clis skill, doctor checks
native-cli-pins/-resolution/-global/-ledger (codesign --verify -R, never -dv),
hk step native_cli_pins, suite workflow.native-cli-pins, the tracked global
fragment mise-global/conf.d/50-native-cli.toml, and the initial release
receipts under docs/receipts/{agy,codex,claude}.
Spec: docs/specs/native-cli-installers-2026-09-30.md (rev 1)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FMeYJgB5KKVuJ14kheDj3d
```

**KB commit:** `chore(native-cli): drop codex/agy mise pins; currency expected form; reviewer-pin fallback to expected`, with the same trailers.

**HEL commit:** `ci(codex): native codex install in phase0; drop the codex mise pin`, with the same trailers.

**Sweep commits:** `chore(mise): drop <keys> pin — native installer owns it (dotfiles spec native-cli-installers-2026-09-30)`, or the cherry-picked KB/HEL commit unchanged.

**Follow-ups (`gh issue create`):**
- **F2:** harden `setup-claude-code` to a GPG-verified fetch (R-sec S5a/S8).
- **F3:** `claude-code-marketplace` native install for its OCI acceptance image.
- **F4:** the `blast-radius` skill improvements (R-blast §3c).
- **F5:** the Q8 token-scope decision, if Ray files it.

---

## 7. PREMISES (the premise verifier marks each CONFIRMED / REFUTED / UNVERIFIABLE / ASSUMED)

"rev1" marks a row that is new or corrected in this revision.

| # | Premise | Provenance |
|---|---|---|
| P1 | The root host pin `antigravity-cli = "1.2.14"`; the image ignores root mise.toml. | `mise.toml:126`, `:114`; `.devcontainer/devcontainer.json:182` |
| P2 | The host guard `disable_tools` and its comment. | `mise.toml:164-169` |
| P3 | shared.toml pins npm codex; it feeds the base image and CI, and CI re-enables it. | `.config/mise/conf.d/shared.toml:39-44`; `Dockerfile:139`; `ci.yml:69-72` |
| P4 | The image runtime pins `claude-code = "latest"`. The comment says http, the lock says aqua. | `mise-runtime.toml:59, :63`; `mise-runtime.lock:583` |
| P5 | There is no host claude mise pin; CI claude is native at the sources.toml pin. | `mise.toml:27`; `setup-claude-code/action.yml:44-45`; `schemas/sources.toml:51-56` |
| P6 | The global config pins agy and defines `update:claude` / `update:all` with the depends line; `conf.d/` is absent. | `~/.config/mise/config.toml:142, :383, :500, :526`; `ls ~/.config/mise/conf.d` gave "No such file" (rev1) |
| P7 | `mise ls --current --json` applies `disable_tools` and reports `source.path` / `install_path`. | R-crit C replay (CONFIRMED live); `path_drift.py:210` `active_tools` |
| P8 | Doctor registers checks in `CHECKS`/`LIVE_CHECKS`. | `doctor.py:1397, :1416`; `path-drift` `:1407`, `claude-doctor` `:1409`, `codex-schema` `:1410` |
| P9 (rev1) | BLIND rc is **2**, and BLIND requires `MISE_TASK_NAME`. | `path_drift.py:92, :167-177, :364-369` (R-prem MISSING, corrected from 3) |
| P10 | The hk step shape. | `hk.pkl:365-367` |
| P11 (rev1) | The nested-subcommand precedent is `schema-vendor`, not the flat `plugin-remove`. | `main.py:1768-1772` (parser), `:2895` (dispatch); `plugin-remove` `:1736`; `def main() -> None` `:3115` |
| P12 | The host lock block. | `mise.lock:4491`; the next block is at `:4550` |
| P13 (rev1) | The codex schema pin currently resolves from shared.toml, and **breaks** when S1 goes unless the resolver is removed and `version` is vendored. | `schema_vendor.py:113-121`; `schemas/sources.toml:43-48`; claude-code vendored precedent `:51-56`, `:7-9`; `tests/test_schema_vendor.py:434-440` |
| P14 | rule-sync compares whole lines and rule stems only. | `rule_sync.py:144-148`; `rule-sync.toml:38` (lines), `:57-59` (rules incl. `ai-cli-invocation`) |
| P15 (rev1) | ai-cli-invocation `:8`, `:25` and `:66-67` go stale once `disable_tools` and the agy pin go. | `.claude/rules/ai-cli-invocation.md:8, :25, :66-67` |
| P16 (rev1) | REFUTED in rev 0. The `sdlc_team` docstring names native already, but its `disable_tools` clause goes stale now. The codex_lane error text is at `:458`. | `sdlc_team.py:699-701`; `codex_lane.py:435, :458` |
| P17 (rev1) | REFUTED in rev 0. KB `[tool.antigravity-cli]` is already self-managed; only `[tool.codex]` has `mise_key` and no `expected`. | KB `currency.toml:1938, :1950` (`expected = "1.2.12"`), `:1855-1856`; `sync.py:2026` "has no pin" |
| P18 | claude-code-marketplace's pin feeds its OCI acceptance run **and** is a host pin. | `claude-code-marketplace/.github/workflows/acceptance.yml:30, :34`; its `mise.toml:10` (R-prem) |
| P19 (rev1) | REFUTED in rev 0. HEL CI invokes codex: `doctor` → `phase0.py:163, :225`; `rules:verify` → `verify_rules.py:48`; the runner gets codex from `mise.toml:40`. | HEL `main` `f1b0eb3`: `.github/workflows/phase0.yml:39-43, :46, :55`; `mise.toml:40, :79-81, :139-141` |
| P20 | The agy installer refuses an existing binary and has no version pin. The switch is the literal `true`. | R-chan §4 (`install.sh:57-64, :132-141`; #1046, #834, #568). Report-sourced; the installer was re-fetched but not re-run in R-sec M7/M9. |
| P21 | The codex daemon updater is disabled only through `settings.json`; there is no env var. | R-chan §3 (`settings.rs:69-92`, `update_loop.rs:532-579` at `rust-v0.159.2`; PR #43542). Report-sourced. |
| P22 | Team IDs: agy EQHXZ8M8AV, codex 2DC432GLL2, claude Q6L2SF6YDW; mise is 4993Y37DX6. | Re-derived twice: R-crit K and R-sec M2. L5 re-derives it again. |
| P23 | Global backup precedent, and the live file is 0600. | `~/.config/mise/config.toml.bak-codex-native-20260922T202255Z`; R-sec M17 |
| P24 | The `uv run --project <checkout>` global call site is struck. | `mise-native-dotfiles-plan.md:343-345`, `:433` |
| P25 (rev1) | The ambient PATH resolves agy to `installs/antigravity-cli/1.2.13`; `1.2.14` now exists; native agy is 1.1.12. | R-sec S12 / M19; R-crit replay. Live facts; L1 re-derives them. |
| P26 | `mise exec -- <non-mise cmd>` passes through to PATH. | R-blast §2b (`sw_vers` rc 0 / bogus rc 1); L7 |
| P27 (rev1) | suites.toml binds the `mise exec -- codex exec` literals in `.claude/agents/codex-sol-*.md`, **not** in `ai-cli-invocation.md`. | `python/verification/suites.toml:1874-1886` |
| P28 (rev1) | Renovate PRs #1449, #1444 and #1093 are OPEN and touch codex/claude-code pins or locks. | `gh pr view` one-shot, 2026-09-30 (control: #999999 does not resolve) |
| P29 | The chezmoi container mise template has no agy/codex/claude reference. | `home/dot_config/mise/config.toml.tmpl:64` (the control hit) |
| P30 | `codex update` and `agy update` exist. | codex: KB `sources/codex/codex-rs/cli/src/main.rs:183, :1645`. agy: `agy --help` "update  Update CLI" (R-blast §2b). `agy update` semantics are **not probed** (R-chan §7). |
| P31 (rev1) | The names `native-cli`, `native_cli_pins`, `workflow.native-cli-pins` and `mise-global/` collide with nothing, **but** `native-cli-installers` is the workflow's name, so the skill is `native-clis`. | `.claude/workflows/native-cli-installers.js:2`; R-prem P31 grep, extended over `.claude/` |
| P32 (rev1) | `codesign -dv` passes a tampered binary; `--verify --strict -R` rejects it (rc 1 when modified, rc 3 for the wrong team). | R-sec M1 and R-crit K: two independent replays; `man codesign:254-257` |
| P33 (rev1) | The worktree states in §2e as of 2026-09-30. | Re-probed in this revision: branch plus `git status --porcelain` count per target. The control is this worktree, dirty=12. `currency-20260930` is now clean. |
| P34 (rev1) | The KB reviewer gate goes inert without a pin: `pinned_version` has no `expected` fallback, and `review.py` `continue`s. | KB `sync.py:144-165`; `review.py:309-315, :384, :387-389` |
| P35 (rev1) | All three vendors publish GitHub release bodies. The tag formats are `rust-v<v>`, `v<v>` and `<v>`. codex marks alphas as prereleases. | `gh api repos/{openai/codex, anthropics/claude-code, google-antigravity/antigravity-cli}/releases`, 2026-09-30 (bogus repo gives 404) |
| P36 (rev1) | Graphify's receipt writer shape (fields, verbatim body, raise on a missing `published_at`). | `graphify_currency.py:33, :261-316, :319-338, :387-396`; `docs/receipts/graphify/0.9.65.md` |
| P37 (rev1) | mise supports a shared `conf.d/` layout for the global config, and conf.d fragments load globally. `.config/mise/conf.d/` is a **project** location. | jdx/mise `docs/bootstrap.md:54` @ `8a1042b3` (re-fetched); `llms-full.txt:1099-1105, :1131-1139` |
| P38 (rev1) | The lightster pattern symlinks tracked fragments into `~/.config/mise/conf.d/`. | `lightster/.dotfiles` `mise/tasks/configs.sh:8, :18-19, :32-33` @ `1917a189` (re-fetched); R-confd |
| P39 (rev1) | "A fragment cannot override `config.toml`" (so the `depends` line must live in `config.toml`). | Measured by the coordinator on 2026-09-30, per ruling R3. **Inherited**, so L9 re-derives it. |
| P40 (rev1) | The image home volume masks `~/.local`, and `~/.local/bin` precedes system shims on PATH. | `devcontainer.json:129`; `Dockerfile.host-user:77`; R-place §corrections 1, §Recommendation; R-cstat F4 |
| P41 (rev1) | The runtime stage is thin and separate from the base; the base COPYs shared.toml. | `Dockerfile:139` (base), `:666-689` (runtime); `:14` pinned `BASE_IMAGE` |
| P42 (rev1) | The fingerprint-before-trust Dockerfile precedent. | `Dockerfile:183-202` (LLVM) |
| P43 (rev1) | The tier-3 smoke checks claude/codex with `command -v` only. | `python/src/dotfiles_setup/image.py:1043-1046` |
| P44 (rev1) | The claude GPG key fingerprint, and that signed manifests exist from 2.1.89. | R-chan §2 (both arms measured: good sig rc 0, tampered manifest BAD). Report-sourced; D1 re-derives it. |
| P45 (rev1) | CI pytest shells out to codex in `contract-preflight`, after `setup-mise` `:222`. | `ci.yml:184, :217-222, :245`. **Which** tests need it is unverified (R-blast §2d); D4 plus the CI run are the arm. |
| P46 (rev1) | KB `mise.lock` holds both stale blocks, and `kb-lock-drift` gates ship. | KB `mise.lock:4719, :6673`; `gates.py:196`; `lock_drift.py:62-64` |
| P47 (rev1) | The global lock holds an agy block and an orphan npm codex block. | `~/.config/mise/mise.lock:313, :3268` |
| P48 (rev1) | `docs/receipts/` is not in the lint `excludePaths`. | `hk-common.pkl:42-54` (only research, spec and trail trees are listed) |

## Open questions (recommended option first)

- **Q2: uninstall the stale install dirs?** This covers `mise uninstall --all antigravity-cli` plus the orphan `codex 0.150.0` and npm codex dirs. *Recommended:* yes, after L3. The narrowed check (c) no longer needs it, but a stale copy can resurface on an old activation's `PATH`.
- **Q3: update native agy before the pin removal?** This means `agy update` on 1.1.12, falling back to moving it aside and running the vendor installer. *Recommended:* yes, as step 1 (C2). It is the one approval still gating the repo and global agy removal.
- **Q4: leave the lookalikes alone?** These are `npm:oh-my-codex`, `npm:oh-my-claude-sisyphus` and `npm:claude-code-lint`. *Recommended:* leave them. They are listed in `lookalikes`, and the shape check still catches one that starts shipping a real CLI binary.
- **Q8: cut the ambient `GITHUB_TOKEN` scope?** Its scopes include `workflow`, `write:packages` and `admin:org` (R-sec S3). It is the one lever that bounds all three self-updaters. *Recommended:* file F5 and decide separately. It is outside this spec.
- **Q9: claude `autoUpdatesChannel: "stable"`?** That is the only native cooldown, about one week (R-sec S4); it is a user-level `~/.claude/settings.json` edit. *Recommended:* yes. R2 keeps auto-update ON, and `stable` still updates, only a release later.
- **Q10: auto-update OFF inside the image?** That means `ENV DISABLE_AUTOUPDATER=1` for claude, and the chezmoi-managed daemon `settings.json` for codex. *Recommended:* yes. R2 did not distinguish host from image, but a self-update inside the container lands in the home volume and shadows the verified pinned copy (C8, P40).
- **Q11: replicate the image/CI half into the dotfiles sweep worktrees?** *Recommended:* no. Host lines only; the rest arrives through `main` on rebase (§2e).
- **Q12: where does HEL record its codex version, and may HEL call `ray-manaloto/dotfiles/.github/actions/setup-codex@<sha>` cross-repo?** *Recommended:* yes to the cross-repo action, with an explicit `version:` input held in one HEL file (for example `phase0.yml` `env: CODEX_VERSION`), so there is one implementation.
- **Q13: add cosign keyless verification of the codex `.sigstore` bundle in the image?** *Recommended:* yes, if cosign can be added to the image through `mise-system.toml` in the same base rebuild C13 already forces. Otherwise SUMS only, and file it.
- **Q14: the residual risk that a self-updater silently stops** (agy #568/#1080, a daemon not running). *Recommended:* accept for now; the updaters were measured working on 2026-09-30 (R-crit F). If it recurs, generalise `claude_doctor`'s running-vs-latest check to agy and codex (improvement 7), rather than adding a LIVE module.
- **Q15: exclude `docs/receipts/{agy,codex,claude}/**` from lint?** Receipts are verbatim vendor text (C15). *Recommended:* yes, but only if lint actually flags a body, with the secret scanners still covering the trees.
- **Q16: KB reviewer-gate cadence.** With the `expected` fallback and self-update ON, `_reviewer_pin_gap` REFUSES kb-review receipts whenever the running agy/codex passes KB's `expected`, which happens daily at current vendor cadence. *Recommended:* keep REFUSE (Ray's 2026-08-23 ruling), and bump KB `expected` when the dotfiles ledger receipt for that version has been reviewed. The alternative is downgrading the gate to a warning.
- **Q17: ledger scope.** *Recommended:* host running versions only. The image/CI pins in `schemas/sources.toml` are reviewed through their own PR diffs. Requiring receipts there would block Renovate-style bumps, as the graphify receipt gate does.
