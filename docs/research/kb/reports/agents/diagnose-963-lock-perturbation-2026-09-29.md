# Diagnosis #963 — root `mise.lock` gains linux-x64 blake3 checksums in `image-lock-pr`

Lane: read-only diagnosis (Claude Opus, subagent). Repo main `efc04995`. Date 2026-09-29.
Status: COMPLETE.

## Finding 0 — the premise's attribution is WRONG (log re-read)

The brief says aws-cli/docker-cli installed DURING the pytest step. The log says otherwise:

- `.agent/logs/run-36340304870.log:477` — `##[group]Run uv run --project python pytest …` starts 18:21:15.81.
- `:620`-ish — `1 failed, 4 passed in 0.16s` at 18:21:20.97; `##[error]Process completed with exit code 1.` at 18:21:21.047.
- Next step `##[group]Run mise run lock-image -- --no-container` at 18:21:21.055; first line of its output
  `mise by @jdx – installing 51 tools` at 18:21:21.11.
- `aws-cli@2.37.4 extracting` (:814, 18:21:27) / `✓ docker-cli@29.8.1` (:828) / `✓ aws-cli@2.37.4` (:942) are
  inside THAT step (timestamps after 18:21:21).

So the installer is `mise run lock-image -- --no-container`, not pytest (pytest ran 0.16 s and invoked no mise).

Step map (`.agent/logs/run-36340304870.log`, re-derived with `grep -n '##\[group\]Run\|##\[error\]\|installing [0-9]* tools\|passed in'`):

| line | time | event |
|---|---|---|
| 251/253 | 18:21:06 | mise-action `mise install --locked bun pipx` — "installing 2 tools" |
| 388/390 | 18:21:09 | mise-action `mise install --locked python uv` — "installing 2 tools" |
| 477 | 18:21:15.81 | drift-check `uv run --project python pytest …` (continue-on-error: true, refresh.yml:~330) |
| 612/613 | 18:21:20.97/21.05 | `1 failed, 4 passed in 0.16s` (pinact 5.0.0 vs 4.1.1 drift) → `##[error]… exit code 1` |
| 614 | 18:21:21.055 | `Run mise run lock-image -- --no-container` (Regenerate image locks) |
| 634 | 18:21:21.11 | `mise by @jdx – installing 51 tools`  ← THE INSTALLER |
| 814/828/918/942 | 18:21:27-30 | aws-cli@2.37.4 / docker-cli@29.8.1 extracting / ✓ — inside the lock-image step |
| 1502/1527 | 18:23:58 | re-check pytest: `5 passed in 0.11s` |
| 1528…1594 | 18:23:59 | confine-check: ` M mise.lock`, diff = +2 lines (linux-x64 blake3 for aws-cli, docker-cli), exit 1 |

## Finding 1 — the writer is `mise run`'s pre-task auto-install, not `lock-image`'s python

`mise run lock-image` (mise.toml:1443-1460, `run = 'uv run --project python dotfiles-setup image-lock'`) is
invoked as a **mise task**. Before running any task, mise installs every missing tool of the
resolved config for the task's dir (the repo root: `mise.toml` + `.config/mise/conf.d/shared.toml`).
The runner had only bun/pipx/python/uv installed (mise-action installs only `install_args`), so the task
pre-install fetched the other 51 root tools. That install is NOT `--locked` (mise-action used `--locked`,
the task pre-install does not), and root `mise.toml:141-144` sets `[settings] lockfile = true`.

Cross-check (why exactly aws-cli + docker-cli, nothing else): on main `efc04995` a tomllib scan of root
`mise.lock` for `platforms.*` tables lacking `checksum` returns exactly 3 tool entries:

- `aws-cli@2.37.5 aqua:aws/aws-cli` — missing on ALL 9 platforms (has=[])
- `docker-cli@29.8.1 aqua:docker/cli` — missing on ALL 11 platforms (has=[])
- `zizmor@1.30.1 aqua:zizmorcore/zizmor` — missing only the three `*-musl*` platforms; linux-x64 HAS one

The runner resolves `linux-x64` (glibc), so the only entries whose *linux-x64* table lacks a checksum are
aws-cli and docker-cli — exactly the two lines the diff adds. zizmor was installed too (51 tools) but its
linux-x64 checksum already existed, so nothing was written: this is the control arm inside the same run
(install of a tool whose current-platform checksum is present → no lock write).

## Finding 2 — WHY an install writes a checksum: documented `merge`-mode auto-locking (probed, 6 arms)

Docs (upstream jdx/mise, fetched via `gh api repos/jdx/mise/contents/...`, raw copies in
`.agent/kb/raw/mise-lock-docs-963.md`, `.agent/kb/raw/mise-settings-963.toml`):

- `docs/dev-tools/mise-lock.md` §"Command Behavior with Lockfiles" (raw :175-178): `mise install` → Updates
  `mise.lock`: **Yes**. §"Complete lockfile generation" (raw :367): "The default `merge` mode updates entries as
  tools are installed."
- `settings.toml [lockfile]` (raw :1770+): with `lockfile = true` "project lockfiles are created, read, and written".
  Root `mise.toml:143-144` sets `auto_install = true`, `lockfile = true`.
- `settings.toml [auto_install]` (raw :283): governs "`mise x`, `mise run`, or … 'not found' handler";
  `[task.run_auto_install]` (raw :3713, env `MISE_TASK_RUN_AUTO_INSTALL`, default true) — "Automatically install
  missing tools when executing tasks." (`task_run_auto_install` is the deprecated alias, :3797.)
- `settings.toml [locked]` (raw :1688, env `MISE_LOCKED`): "Equivalent to passing `--locked` to `mise install`" —
  requires lockfile URLs for the current platform. The docs do NOT state that locked mode suppresses lock writes;
  the probe below shows it does (at least for this TOFU-checksum case).
- The local mintlify cache (`docs/research/mintlify-cache/jdx/mise/llms-full.txt`, 5,434 lines) has NO lockfile
  checksum semantics: `grep -ci checksum` = 8, none about auto-locking (control: the same grep finds the
  `auto_install` table at :1457 and :2388, so the probe can see the file). Fell through to upstream source docs.

Probe — isolated fixture (scratchpad `p963/probe.sh`): fresh `MISE_DATA_DIR/CACHE/STATE/CONFIG_DIR`, empty
`MISE_GLOBAL_CONFIG_FILE`, project `mise.toml` = `docker-cli = "29.8.1"` + `[settings] lockfile = true` + a task
`t`; `mise.lock` = root lock's docker-cli block verbatim (URLs, no checksums). Host mise 2026.9.16 macos-arm64.

| arm | command | installed? | lock gained checksum? |
|---|---|---|---|
| A | `mise install` | yes | **yes** — `blake3:6593c6…` under `platforms.macos-arm64` only |
| C | `mise run t` | yes (task pre-install) | **yes** — same single current-platform line |
| B (control) | tool pre-installed, lock reset, `mise install` | no-op | **no** |
| E | `MISE_TASK_RUN_AUTO_INSTALL=0 mise run t` | no; task still ran (`task-ran`) | **no** |
| F | `mise install --locked` | yes | **no** |
| D | `MISE_LOCKED=1 mise run t` | yes | **no** |

(The fixture's one-line `# @generated` header was rewritten to mise's full header in A/B/C; that is a fixture
artefact — root `mise.lock` already carries the full header, and CI's diff shows no header hunk.)

So: an UNLOCKED install of a tool whose current-platform lock entry has a URL but no checksum computes the
artifact's blake3 and writes it back (trust-on-first-use), for the current platform only. It happens only when an
install actually occurs (B), which explains the issue-body null ("`mise install`/`mise run` did not touch the lock
… 2026.9.1"): the condition is "tool not yet installed in this MISE_DATA_DIR", and a fixture run on a host where
the tool is already installed cannot reproduce it. Either `--locked`/`MISE_LOCKED=1` (F, D) or disabling the task
pre-install (E) prevents the write. CI mise-action already uses `--locked` (log :251, :388) — which is why ITS
installs never perturbed the lock; the task pre-install inside `mise run lock-image` is the only unlocked install.

Additional arms (same fixture):

| arm | command | installed? | lock change |
|---|---|---|---|
| G | `mise run --skip-tools t` | no; task ran | **none** |
| H | `mise --locked run t` | yes | **none** |
| I | `MISE_LOCKED=1 mise lock --platform linux-x64` | — | rc=0, no checksum (only fixture header) — locked mode does not break `mise lock` |
| J | `MISE_LOCKFILE_MODE=generate mise lock --platform linux-x64,macos-arm64` | no | **+2 `sha256:` checksums**, one per targeted platform (downloads to hash) |
| K | `MISE_LOCKFILE_MODE=generate mise install` | yes | **+11 `sha256:` checksums — every platform in the entry** |
| L (control for c) | fresh-data `mise run t` against K's fully-checksummed lock | yes | **none** (diff rc=0) |

`mise run --help` (2026.9.16): `--skip-tools  Skip installing tools before running tasks … task.run_auto_install
setting or MISE_TASK_RUN_AUTO_INSTALL=false`; global `--locked` "Can also be enabled via MISE_LOCKED=1".
`mise lock --help` has no download/checksum flag; with default `merge` mode (arm I) `mise lock` cannot compute a
checksum for these two tools.

Why these two tools never had checksums: the aqua registry entries are `type: http` with NO `checksum:` block
(`aquaproj/aqua-registry` `pkgs/docker/cli/registry.yaml`, `pkgs/aws/aws-cli/registry.yaml`, fetched via
`gh api`); zizmor (control) is `type: github_release`, whose asset digests mise can read without downloading.
So `mise lock` in merge mode records URL-only entries for them; only an install (TOFU blake3) or generate mode
(download + sha256) can supply one.

## Answer 1 — the call path (corrected)

Not pytest. `refresh.yml` job `image-lock-pr`:

1. `setup-mise` with `install_args: "python uv"` (refresh.yml:~328-331) → mise-action runs `mise install --locked bun pipx`
   then `mise install --locked python uv` (log :251, :388). mise-action auto-adds `--locked` when a repo lockfile exists
   (`jdx/mise-action` action.yml:38 @ `9149ea85`, raw `.agent/kb/raw/mise-action-v5-action-963.yml`). The other 51 root
   tools stay `(missing)` (log :410-415 `mise ls`).
2. drift-check pytest (refresh.yml:~333-346, `continue-on-error: true`) — 0.16 s, pure python TOML comparisons, fails on
   `pinact 5.0.0 vs 4.1.1` (log :612-613). No mise invocation.
3. **`Regenerate image locks`: `run: mise run lock-image -- --no-container` (refresh.yml:359).** `mise run` performs its
   pre-task tool install (`task.run_auto_install`, default true) over the repo-root config — "installing 51 tools"
   (log :634) — WITHOUT `--locked`. With root `mise.toml:144 lockfile = true` and the default `merge` lockfile mode, each
   fresh install whose `linux-x64` entry has a URL but no checksum gets a TOFU blake3 written back: aws-cli (log :942
   `✓ aws-cli@2.37.4 … awscli-exe-linux-x86_64-2.37.4.zip`) and docker-cli (log :828). The task body itself
   (`uv run --project python dotfiles-setup image-lock` → `image_lock.run_lock_passes`, image_lock.py:283-331) runs a
   PINNED mise inside a `/tmp/dotfiles-image-lock-*` stage dir and never touches the root lock.
4. confine-check (refresh.yml:~376-406) sees ` M mise.lock` and fails (log :1528-1594).

## Answer 2 — why it writes, and which setting governs it

- Governing settings: `lockfile = true` (root mise.toml:144) + default `lockfile_mode = "merge"` ("updates entries as
  tools are installed", mise-lock.md) + `task.run_auto_install = true` (the trigger) + NOT `locked`.
- The write is suppressed by any of: `mise run --skip-tools` / `MISE_TASK_RUN_AUTO_INSTALL=0` (no install, arms E/G);
  `--locked` / `MISE_LOCKED=1` (install proceeds, no write, arms D/F/H); or the entry already carrying a checksum
  (arm L). It is only ever for the CURRENT platform in merge mode (arms A/C: one line, macos-arm64 locally; CI: linux-x64).
- Why only aws-cli + docker-cli: aqua `type: http` registry entries with no `checksum:` config, so `mise lock` (merge)
  can record URL-only. Precedent for the TOFU-blake3 behaviour in release notes: v2026.8.5 PyPy "records a blake3
  checksum in the lockfile on first install" (raw `.agent/kb/raw/mise-releases-963.md`).
- `--skip-tools` shipped in v2026.3.11 (jdx/mise#8699), so CI's pinned 2026.9.8 has it; `lockfile_mode = "generate"`
  shipped v2026.9.5 as an opt-in trial (default stays `merge` "pending … review before mise 2026.12.0").
- Caveat: my probes ran mise 2026.9.16 on macos-arm64; CI is 2026.9.8 linux-x64. The CI log itself is the 2026.9.8 arm
  for the write; the suppression arms (D-H) were not re-run on 2026.9.8 — UNVERIFIED on that exact version.

## Answer 3 — fix options

| option | PRO | CON |
|---|---|---|
| **(a) `mise run --skip-tools lock-image -- --no-container`** at refresh.yml:359 (native flag, v2026.3.11+) | Removes the cause, not the symptom: no 51-tool install at all (also saves ~minutes per run); a CLI flag is not inherited by the child pinned `mise lock` (unlike an env var via `**os.environ`, image_lock.py:309); task needs only uv/python, which setup-mise already installed. Probe G: no install, task runs, lock untouched. | If lock-image ever gains a dependency on another root tool, it fails loudly ("not found") rather than auto-installing — acceptable, arguably desirable. Must also apply to any sibling `mise run` after a subset install (see below). |
| (a') `MISE_TASK_RUN_AUTO_INSTALL=0` step env | Same effect (arm E). | Env leaks into the task's children (`**os.environ` in image_lock.py:309) — harmless today for `mise lock`, but a wider blast radius than the flag. |
| (b) `mise --locked run …` / `MISE_LOCKED=1` | Native; install proceeds but no lock write (arms D/F/H); `MISE_LOCKED=1 mise lock` still rc=0 (arm I). | Still installs 51 unneeded tools; `MISE_LOCKED` would propagate into the pinned `mise lock` child (image_lock.py:309) — arm I says it's harmless on 2026.9.16, untested on the pinned lock-image version; it treats a symptom (the write) not the cause (the needless install). |
| (c) commit checksums for all platforms: `MISE_LOCKFILE_MODE=generate mise lock --platform …` scoped to the two tools | Native (arm J writes sha256 per targeted platform; arm K writes all 11 on install); with checksums present no TOFU write occurs (arm L) and the lock gains real integrity for two currently-unverified tools. | Not durable alone: every aws-cli/docker-cli bump re-creates a URL-only entry unless the ROOT-lock producer also runs in generate mode (main already shows `aws-cli@2.37.5` URL-only on all 9 platforms, i.e. the gap recurs per bump); generate mode is an opt-in trial; repo rule: only scoped re-locks (`mise run lock -- "<backend/name>"`), and the repo's lock task would need to pass the mode. Good hardening follow-up, not the fix for #963. |
| (d) relax confine-check for checksum-only root-lock additions | Trivial. | Masks a real mutation of a tracked file by the job; zero-skip; symptom-sniffing. Reject. |

**Recommendation: (a) — `mise run --skip-tools lock-image -- --no-container` at refresh.yml:359**, optionally
followed later by (c) as supply-chain hardening (generate-mode checksums for aws-cli/docker-cli, with the root-lock
producer taught to keep them). Control arm for the fix in CI: the next `image-lock-pr` run on a drifted Renovate PR
should show no "installing 51 tools" line in the Regenerate step and confine-check `changed=true` with only the two
image locks.

## Other jobs — can the same perturbation hit them?

- `ci.yml` `lint` (job at :84, setup-mise at :105 with NO install_args) and `contract-preflight` (:184, setup-mise at
  :222, no install_args): mise-action installs EVERY root tool with auto-`--locked` → no write (arm F); later
  `mise run rule-sync` (:236), `mise run lint`, and tests that call `mise exec` (tests/test_bootstrap.py:37,
  tests/test_claude_doctor_hook.py:24) find tools already installed → no install → no write (arm B). Even if one did
  write, no ci.yml step checks the tree is clean (only `refresh.yml:388/393` and `gcc-sha-repair.yml:84` run a
  dirty-tree check), so it could never fail there — it would be silent.
- `refresh.yml` `tool-currency` (:161, "Install mise (all tools)", `mise run tool-currency` :181): full locked install → no write.
- **`refresh.yml` schema-vendor-refresh job (setup-mise `install_args: "python uv"` :513, `mise run schema-vendor-refresh`
  :515): SAME shape — the task pre-install will TOFU-write the two checksums into root `mise.lock`.** It does not fail
  because `open-refresh-pr` stages only its `paths:` list (action.yml:30-31/:74 `add-paths`), so the perturbation is
  silently discarded. Worth the same `--skip-tools` for consistency.
- `build-publish.yml` subsets (`python uv`, :113/:176/…): grep finds no `mise run` invocation in that file's steps
  (the only matches are comments at :88/:1043), so no pre-install trigger.

## Probe hygiene

- Negative arms control-armed: E/G (no-write) vs A/C (write) on the same fixture; L (no-write with checksum) vs A.
- Mintlify-cache null (no lockfile-checksum docs) control-armed by the same grep finding `auto_install` rows.
- `mise run --help` grep for `--skip-tools` control: same help's `jobs` token counted 5 matches.
- Inherited, not re-derived: the issue-body claim that the container path of `lock-image` leaves `mise.lock`
  byte-identical (consistent with image_lock.py's stage-dir design, but I did not re-run it).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `docs/dev-tools/mise-lock.md`, `settings.toml` (lockfile/locked/task.run_auto_install/lockfile_mode), releases v2026.2.18–v2026.9.16
- [jdx/mise-action](https://github.com/jdx/mise-action) — action.yml/src/index.ts @9149ea85: auto-`--locked` when a lockfile exists
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — `pkgs/docker/cli`, `pkgs/aws/aws-cli` (type http, no checksum), `pkgs/zizmorcore/zizmor` (control)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — refresh.yml, ci.yml, mise.toml, mise.lock, image_lock.py, CI run 36340304870 log
