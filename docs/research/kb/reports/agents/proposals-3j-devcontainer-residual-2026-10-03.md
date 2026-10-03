# §3j devcontainer residual proposals (agent afd423ae13340b5cd, delivered 2026-10-03T20:36Z to 28f1a8f7)

> Verbatim final report recovered from the 28f1a8f7 transcript by coordinator 97ffeddb (`agent-report-persistence.md` rule 1). The harness hand-back preamble line was removed; the body is unedited.

  # §3j residual: options to replace the linked-worktree refusal under PIN
  
  This lane was read-only. Nothing was written to `findings.md`, `progress.md` or `.agent/kb/raw/`; the coordinator needs to save this report. The main checkout was on `fix/1606-enterworktree-guard`, so every repo citation below is from `git show origin/main:<path>` at origin/main `4cf89eb8`.
  
  ## Main finding: §3j tests none of the diff, so this is the whole gate, not a residual
  
  The spec says "the image is the branch's", but for every diff that can reach §3j, the branch's image is the same as main's.
  
  1. **Only certain diffs reach §3j.** A diff reaches §3j only when `needs_full_sync` is true. That means it touches the surface and changes no base-image input (`python/src/dotfiles_setup/pr.py:283-290`).
  2. **The image is built only from base-image inputs.** Every input the image is built from is in `BASE_INPUT_PATTERNS` (`pr.py:133-143`). Those inputs are the Dockerfile, `mise-system.toml`/`.lock`, `mise-runtime.toml`/`.lock`, `shared.toml`, `hk-common.pkl`, `hk-image.pkl` and `docker-bake.hcl`. The Dockerfile's `COPY` lines are only those files (`.devcontainer/Dockerfile:127,133,139,392,393,669,672`). Nothing under `python/`, `scripts/`, `home/`, `.devcontainer/scripts` or `Dockerfile.host-user` goes into the image.
  3. **So CI reuses main's image.** The `:dev-<hash>` cache key is built from the base hash, the p2996 hash, the platform, the Dockerfile, the dev bake target and the runtime toml/lock (`python/src/dotfiles_setup/p2996_hash.py:475-523`). For a diff that can reach §3j, that key equals main's. `dev-prep` then finds main's validated image in the cache and retags it as `:pr-NNN` instead of building (`.github/workflows/build-publish.yml:419-424`).
  4. **Everything else in the run comes from main.** `mise run sync` in the main checkout runs main's `sync.py` and main's `mise.toml` tasks (`up`, `verify-local`, `mise.toml:1157-1177`). The devcontainer CLI reads the config from the workspace folder (`mise.toml:400`), so `devcontainer.json`, the locally built `Dockerfile.host-user` overlay, `on-create.sh` (`devcontainer.json:245`) and `scripts/devcontainer-smoke.sh` (`devcontainer.json:246`) are all main's too.
  
  Result: §3j re-validates main against main. Rev 4's example case (a broken `.devcontainer/scripts` change) passes for exactly this reason.
  
  There are three more defects in (a):
  - **No image for some surface diffs.** `SURFACE_PATTERNS` includes `scripts/devcontainer-smoke.sh`, `home/dot_gitconfig.tmpl` and `mise.toml` (`pr.py:99-121`). None of them is in CI's build filter (`.github/workflows/ci.yml:291-299`). For a diff touching only those, CI publishes no `pr-<N>` image, so §3j step 3's bounded-wait can only time out.
  - **It replaces the coordinator's container.** `sync --tag pr-N` sees the main checkout's container as stale and runs `dev-rebuild`. The code warns that this kills in-container sessions (`python/src/dotfiles_setup/sync.py:796-817`). It also records `pr-N` as current for main's workspace hash (`sync.py:819-820`). If the PR fails, main's container is left on the PR image.
  - **It is serial.** There is one main checkout and one container per architecture, so two lanes running §3j at once race each other.
  
  Land does catch a broken script, but only after the merge: `land_main` runs `sync_main(..., full=surface)` on main (`pr.py:1059`). Main goes red after the auto-merge.
  
  ## Can the devcontainer mount target a worktree path?
  
  Yes, except for git, which is the only blocker.
  
  - `mise run up` runs `devcontainer up --workspace-folder .` (`mise.toml:385,400`) with id labels taken from the workspace.
  - `devcontainer_names` names everything from the resolved path:
    - the hash is the first 8 characters of a SHA-256 of the absolute path (`devcontainer_names.py:157-175`);
    - the SSH port is seeded from path and architecture into 20000-29999 (`:178-210`);
    - the container is `dotfiles-<basename>-<user>-<hash>-<arch>-<port>` and the home volume is `...-home` (`:226-236`).
  - So a worktree or clone gets its own container, its own **cold** home volume, its own port and its own Doppler env file. `mise run names` (`mise.toml:405-409`) prints them.
  - `${localWorkspaceFolderBasename}` becomes the worktree's directory name (`devcontainer.json:129-130,191,245`). The only hard-coded `/workspaces/dotfiles` outside tests is the old `docker.py:412` `test()` path. The Dockerfile's `:78` trust path is overridden by `containerEnv` `MISE_TRUSTED_CONFIG_PATHS: "/"` (`devcontainer.json:171`).
  - **Port caveat:** the first #1481 repro hit a port collision because a pinned `DEVCONTAINER_SSH_PORT` leaked in from the environment. A second workspace must never inherit main's pin.
  - **Git blocker:** every `.claude/worktrees/*/.git` here is an absolute `gitdir: /Users/.../dotfiles/.git/worktrees/<n>`. I checked six. That host path is not mounted, so the smoke preflight `git -C ... rev-parse HEAD` dies (`scripts/devcontainer-smoke.sh:20-23`; #1481 probe: worktree rc=128, main-checkout control rc=0).
  - **Repo config:** `.git/config` already sets `extensions.relativeWorktrees=true`, but `worktree.useRelativePaths` is unset. Git 2.54.0 on the host. Any git older than 2.48 cannot open this repo now. The #1481 control arm shows the container's git could open it on 2026-10-01; I have not checked whether the extension was already set then.
  
  ## Upstream research (with control arms)
  
  - **devcontainers/cli#796** "git worktree support" (open, 2024-04-09). The maintainer's workaround (chrmarti, 2025-08-15): mount the original `.git` with an extra `mounts` entry, or set `workspaceMount` to a common parent. On 2026-02-06 the maintainer said `devcontainer up` now has `--mount-git-worktree-common-dir`, and "the `gitdir:` path needs to be relative". Later comments report it failing for compose setups and on Ubuntu. Someone also published git-outpost, which makes clone-backed "outposts" with a real `.git` directory: prior art for option (c).
  - **devcontainers/cli PR #1127** added the flag (merged 2026-01-08).
  - **devcontainers/cli#1243** (open, 2026-06-08): the flag is **silently ignored when `devcontainer.json` sets a custom `workspaceMount`**. Our config sets one (`devcontainer.json:130`). Fix PRs **#1261** (2026-07-02) and **#1246** (2026-06-15) are both still open. The latest tag is v0.89.0, which is the version installed here.
  - **I confirmed the guard in the installed CLI** (`devContainersSpecCLI.js`, 0.89.0): `if(A&&(!s||!("workspaceMount"in t)))`, and the mount is only computed when `!e.path.isAbsolute(u)`. So the native flag fails twice here: our `workspaceMount` is custom and our gitdirs are absolute.
  - **microsoft/vscode-remote-release#11478** "Experimental worktree support doesn't work when workspaceMount is customized" (open, 2026-02-05), and **#11588** "Background agent worktrees do not work in Dev Containers" (open, 2026-02-05).
  - **Searches:** the repo-scoped `gh search issues worktree` returned hits in devcontainers/cli, vscode-remote-release and devcontainers/spec. The cross-repo query "worktree devcontainer gitdir" returned 0. Search was working, so that 0 means nothing extra was found. The spec repo hits (#767, #743) are unrelated.
  - **Local git docs (2.54 man pages):**
    - `--relative-paths` defaults to absolute;
    - `worktree.useRelativePaths=true` turns on `extensions.relativeWorktrees` ("incompatible with older versions of Git");
    - `gc.worktreePruneExpire` defaults to `3.months.ago`.
  
  ## Options, recommended first
  
  ### 1. RECOMMENDED: (c') one persistent verification clone at a container-visible path, used only for the sync-full gate
  
  What it is: a normal `git clone` (a real `.git` directory) at a fixed path outside the main checkout. Keep the basename `dotfiles` (for example `~/dev/github/ray-manaloto/.dotfiles-verify/dotfiles`).
  
  How ship uses it, before pushing:
  1. Fetch the worktree's HEAD sha into the clone.
  2. `git checkout --detach <sha>`.
  3. Run `mise run sync -- --full` with cwd set to the clone.
  4. Stop the container afterwards and keep its home volume.
  
  A disposable per-ship clone is option (c); the persistent one wins because its home volume stays warm. A *worktree* in (c) does not work: its `.git` is still a file, so it has the #1481 problem. git-outpost (cli#796) is outside prior art for this clone-based approach.
  
  **PRO**
  - It tests exactly what ships: the branch's `devcontainer.json`, overlay, `on-create.sh`, smoke script, `sync.py` and `mise.toml` tasks. That is the same coverage ship had from the main checkout before PIN. The local `:dev` base is correct for these diffs, because base-input diffs never reach this gate (`pr.py:283-290`).
  - It runs before the push, so "the gates validate exactly what ships" (`pr.py:603-607`) and arming when the PR opens both stay as they are. No unarmed-PR state, no wait for the CI image.
  - No change to `devcontainer.json`, so it stays off the R1-R3 surface. It is also PIN-compatible: the main checkout and its container are never touched.
  - Same code path as today (`sync_main` → `dev-rebuild`/`up` → `verify-local`). It fixes #1555's `sync --full` case too if that command is routed the same way.
  - The main checkout already proves a real-`.git` workspace works as the control arm (the #1481 probe, rc 0).
  
  **CON**
  - A second heavy container. The first use is cold: on-create installs native CLIs, chezmoi and the overlay tools into a new home volume. I have not measured that.
  - The single clone serializes ships (about 20 minutes each, per `.claude/rules/local-devcontainer-first.md`).
  - Gitignored local files are missing (for example `mise.local.toml`). An arm64 default from `MISE_ENV` would be lost, and main's port pin must *not* be copied.
  - The clone needs `mise trust`.
  - Do **not** use `--shared`/`--reference`. Alternates store an absolute host path, which is the same class of breakage as #1481.
  - Adds a new module (there is no clone helper today; `git grep` of `python/src` found none).
  
  **Arms**
  - (i) Positive: a fixture full-sync diff from a linked worktree passes the gate in the clone, and the clone's HEAD equals the worktree's HEAD before and after the gate.
  - (ii) **Mutation:** break the branch's `.devcontainer/scripts/on-create.sh` → the gate goes red, and the PR is never opened or armed. This is the arm that (a) fails.
  - (iii) The clone's `.git` is a directory, `objects/info/alternates` is absent, and the status is clean.
  - (iv) `mise run names` in the clone vs the main checkout: different container, volume and port. The control is main's own names.
  - (v) A lock (flock under `~/.local/state/dotfiles`): two concurrent ships serialize, and a stale lock is detected.
  - (vi) After the gate the main checkout container's image id is unchanged.
  - (vii) An `is_linked_worktree` + `needs_full_sync` diff is routed to the clone, not refused (the current refusal is `pr.py:612-627`).
  
  ### 2. FOLLOW-UP root fix: (b) S-b, mount the git common dir at its host path
  
  What it is:
  - `dotfiles-setup devcontainer env` exports `DEVCONTAINER_GIT_COMMON_DIR`, the absolute output of `git rev-parse --git-common-dir`, and always sets it, even for the main checkout.
  - `devcontainer.json` `mounts` gains `source=${localEnv:DEVCONTAINER_GIT_COMMON_DIR},target=<same>,type=bind`.
  - Ship then runs sync-full in the worktree itself.
  
  The native `--mount-git-worktree-common-dir` cannot replace this until cli#1243 merges (#1261/#1246 are open), and it would also require switching to relative gitdirs.
  
  **PRO**
  - Fixes the root cause for every caller: `up`, `smoke`, `verify-container-latest`, `land`, `sync --full`. That covers #1481's wider repro and #1555.
  - The absolute-path mount works with the absolute worktrees that already exist (`EnterWorktree` creates them that way), so no repair is needed.
  - It validates itself. `devcontainer.json` is read from the branch, so the S-b PR's own worktree container carries the mount. The PR must also remove the `pr.py:612-627` refusal.
  - The danger of the whole common dir being visible, including in-container `git gc` → `worktree prune` of worktrees whose paths are not mounted, **already exists**. The main container mounts `.git` at `/workspaces/dotfiles/.git`, and every worktree's gitdir is a host path. S-b adds no new danger.
  
  **CON**
  - Touches `devcontainer.json`, which is R1-R3 surface, so `verify-local` is needed in both the main checkout and a worktree.
  - Every lane worktree gets its own cold container, home volume, port and Doppler env file, which means disk use and host load. It needs reaping/teardown.
  - An empty `${localEnv:}` makes the mount invalid, so `up` fails.
  - The main container mounts `.git` twice (harmless).
  - The prune hazard deserves its own ticket either way: set `gc.worktreePruneExpire=never` or lock long-lived worktrees.
  
  **Arms**
  - In-container `git -C /workspaces/<lane> rev-parse HEAD` returns rc 0 from a worktree; the control is rc 128 without the mount (the #1481 probe).
  - Main checkout `verify-local` passes (R1, R2, R3 all green).
  - `mise run names` shows a distinct port per worktree.
  - Mutation: the env var is unset → `up` fails loudly, not silently.
  - A broken-script mutation in a worktree fails the gate.
  
  ### 3. (e) Hybrid: §3j plus a refusal scoped to bind-mounted inputs. Not viable
  
  The refusal set would be every non-base surface path. Each of them is bind-mounted or run on the host, and none of them is baked into the image (see the main finding). So (e) refuses everything §3j accepts.
  
  The one exception is `.md` files under `.devcontainer/`. They match `.devcontainer/*` (`pr.py:100-101`) but CI ignores them (`ci.yml:309-317`). Such diffs would reach §3j and test nothing anyway.
  
  PIN also removes the refusal's own remedy ("switch in the main checkout"), so lanes are stuck. A cheap side fix that is still worth doing: exclude `*.md` from `needs_full_sync`. Arm: a `.devcontainer/AGENTS.md`-only diff does not add sync-full, and a `.devcontainer/scripts/on-create.sh` diff still does.
  
  ### 4. (d) CI owns the full-sync gate. Useful later as an addition, not a replacement
  
  What CI runs today: `smoke-test` checks out the branch (`build-publish.yml:847-849`) and runs `dotfiles-setup image smoke --image-ref` (`:1001-1006`). That is a **no-mount** `docker run --entrypoint /bin/bash <image> -lc <script>` (`python/src/dotfiles_setup/image.py:1066-1121`). So the branch's Python generates the smoke script, but CI never runs `devcontainer up`, `Dockerfile.host-user`, `on-create.sh`, `postCreate`, or the mount-dependent tiers of `devcontainer-smoke.sh`. This is deliberate (`build-publish.yml:1037-1043`; `image.py:515-524`). And for surface diffs outside the build filter, CI does not build at all.
  
  **PRO**
  - A required check closes the gap for every author: lanes, bots and Renovate.
  - No local container cost, and independent of PIN.
  
  **CON**
  - Cannot reproduce the gate as defined:
    - R2 depends on Docker Desktop's `/run/host-services/ssh-auth.sock` (`devcontainer.json:133`; `AGENTS.md:184-186`), which a Linux runner does not have.
    - R1 is host→container SSH as the Mac user.
    - S1 needs a Doppler token in CI.
    - The overlay's UID parity is a Mac concern.
  - Needs an override config, a pull of the roughly 38 GB image (`build-publish.yml:852`), and the job must run even for diffs outside the build filter.
  - Goes against `.claude/rules/local-devcontainer-first.md`.
  - Worth doing later as an addition: a CI `devcontainer up` + `on-create.sh` + smoke tier 1/2 job.
  
  **Arms (if built):** a broken `on-create.sh` turns the CI job red, and the required check blocks auto-merge. Control: an unchanged branch passes.
  
  ### 5. (a) §3j as written. Reject
  
  **PRO:** PIN-compatible, uses existing flags (`main.py:1128,1145`), and the main checkout's git dir is valid.
  
  **CON:** see the main finding.
  - It tests none of the diff.
  - It hangs when CI publishes no `pr-<N>` image.
  - It replaces the coordinator's container and records it as `pr-N`.
  - It is serial.
  - It adds an unarmed-PR state and a CI wait.
  - Spec §5 item 9 and L7 would pass while proving nothing. Add the broken-script mutation arm and (a) fails it.
  
  ### Other options considered and rejected
  
  - **(f)** Relative-path worktrees (`git worktree repair --relative-paths`), run inside the *main* container against `/workspaces/dotfiles/.claude/worktrees/<lane>`. Git would resolve, but the container, `devcontainer.json`, overlay and lifecycle hooks are still main's. Partial at best. Reject.
  - **(g)** `--override-config` carrying the mount. It replaces the branch's `devcontainer.json` instead of merging into it, so it defeats the purpose. Reject.
  - **(h)** Native `--mount-git-worktree-common-dir`. Blocked by cli#1243 and by our absolute gitdirs. Watch PRs #1261/#1246; once one merges, S-b could shrink to a flag.
  
  ## What the spec needs to change
  
  - Rewrite §3j's "Residual" note: it is the whole gate, not a residual, and the evidence is in the main finding above.
  - Replace §3j steps 2-5 with the verification-clone gate (option 1).
  - Keep S-b as a separate ticket that needs Ray's ruling.
  - In §5: replace item 9's arm-ordering mutation with the broken-script mutation, and make L7 assert that the main container's image id is unchanged.
  
  ### Critical Files for Implementation
  - /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py (refusal at 596-629, `needs_full_sync` 283-290, `gate_matrix` sync-full 439-440, `land_main` 1031-1060)
  - /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sync.py (`_converge` 793-826, `_verify` 828-846)
  - /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/devcontainer_names.py (`workspace_hash` 157-175, `ssh_port` 178-210)
  - /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json (`workspaceFolder`/`workspaceMount` 129-130, `mounts` 131-139, lifecycle hooks 244-246; S-b only)
  - /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/docs/specs/session-handoff-automation.md (§3j at 167-178, §5 item 9 at 222, L7 at 241, P20 at 273)
  
  ## GitHub repos touched
  Read-only, nothing modified:
  - ray-manaloto/dotfiles: `gh issue view` #1481, #1555, #1554.
  - devcontainers/cli: issue search; issues #796 and #1243; PRs #1127, #1246 and #1261; tags.
  - microsoft/vscode-remote-release: issue search; issues #11478 and #11588.
  - devcontainers/spec: issue search only.
  - Cross-repo `gh search issues`: 0 results.
