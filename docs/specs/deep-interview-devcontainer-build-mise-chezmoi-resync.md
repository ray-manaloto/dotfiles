# Deep Interview Spec: Devcontainer Build + Mise CLI Automation + Chezmoi Resync

## Metadata
- Interview ID: di-2026-04-06-devcontainer-bundle
- Rounds: 5
- Final Ambiguity Score: 19.25%
- Type: brownfield
- Generated: 2026-04-06
- Threshold: 20% (met)
- Status: PASSED
- Session: 2026-04-06 Session E (resuming from `.omc/plans/session-2026-04-06-d.md`)

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.80 | 0.35 | 0.280 |
| Constraint Clarity | 0.80 | 0.25 | 0.200 |
| Success Criteria Clarity | 0.80 | 0.25 | 0.200 |
| Context Clarity | 0.85 | 0.15 | 0.128 |
| **Total Clarity** | | | **0.808** |
| **Ambiguity** | | | **0.1925** |

## Goal

Land a single mega-PR on `main` that ships three sequenced but bundled workstreams:

1. **Chezmoi resync** — strip `home/dot_config/mise/config.toml.tmpl` to essentials; fix the
   `setup:tools` ghost-task referenced by `home/.chezmoiscripts/run_onchange_after_10_mise_install.sh.tmpl`;
   audit every chezmoi template (`home/**/*.tmpl`) for drift against current `mise.toml` /
   `.devcontainer/mise-system.toml`; make the three-tier mise config intentional (root = lint,
   image = runtime, chezmoi-overlay = user).
2. **Devcontainer build + CLI swap + full validation** — replace the `dotfiles-setup docker up/down`
   Python wrapper with direct `devcontainer` CLI calls in `mise.toml` tasks; pin
   `@devcontainers/cli` to an explicit version (currently `latest` at mise.toml:22); build the
   image via `docker buildx bake dev-load`; bring it up via `devcontainer up`; run a smoke test
   via `devcontainer exec` that proves tiers 1-4 plus SSH/git-credentials/lifecycle correctness;
   preserve telemetry/metrics collection for build time + image size.
3. **Alignment sweep** — update both `CLAUDE.md` files, create a new
   `.claude/skills/devcontainer-workflow/SKILL.md`, audit `.claude/skills/chezmoi-check/SKILL.md`
   for drift, audit `.claude/rules/*.md` + agents + hooks for stale references to the old wrapper
   path, document the containers.dev lifecycle events being used, enforce devcontainer Features
   where possible, and review mise's docker/devcontainer cookbook guidance.

Close PR #9 (`feat/host-user-migration`) as superseded after the mega-PR merges, linking the new
PR and noting which of PR #9's 3 showstoppers were addressed vs. explicitly deferred.

## Constraints

- **Mega-PR shape.** Single PR on `main`. User chose this over 3 sequential PRs despite
  bisectability risk. (See Open Questions for revisit trigger.)
- **Devcontainer CLI is the only up/down path.** `dotfiles-setup docker up/down` is removed.
  `docker buildx bake` is retained for build only.
- **`Dockerfile.host-user` remains a thin overlay.** Current 80-line file (openssh install + UID
  rename + sudoers + home prestage + envs) is the baseline. No new layers unless strictly
  required for SSH-agent / git-credentials support.
- **Telemetry/metrics must not regress.** CI currently emits `artifacts/build/devcontainer-metrics.json`.
  New workflow must continue to produce it with at least the same fields (build time, image size).
- **Devcontainer Features preferred over hand-rolled RUNs.** Where the containers.dev Features
  catalog covers a need (e.g., common-utils, docker-in-docker, ssh-agent forwarding), use a
  Feature declaration in `devcontainer.json` rather than adding RUN steps to the base Dockerfile
  or the thin overlay.
- **Lifecycle events must follow the containers.dev reference**
  (https://containers.dev/implementors/json_reference/#lifecycle-scripts). `initialize`,
  `onCreate`, `updateContent`, `postCreate`, `postStart`, `postAttach` must each have a
  documented purpose (or be absent on purpose). Current file only uses `postCreateCommand: ./install.sh`.
- **Mise cookbook compliance.** Review and apply guidance from
  https://mise.jdx.dev/mise-cookbook/docker.html and
  https://mise.jdx.dev/cli/generate/devcontainer.html — especially `mise generate devcontainer`
  as a potential source-of-truth or reference for the image's mise setup.
- **Three-tier mise config stays intentional.** `mise.toml` (repo lint/dev tools, pinned),
  `.devcontainer/mise-system.toml` (image runtime, `/etc/mise/config.toml`), and
  `home/dot_config/mise/config.toml.tmpl` (user overlay via chezmoi) each have distinct roles
  and must not be collapsed. The resync removes overlap and drift, not the tiers themselves.
- **Chezmoi templates drive the user overlay.** `home/dot_config/mise/config.toml.tmpl` stripped
  down = user-scoped tools only; image-scoped tools live in `.devcontainer/mise-system.toml`.
- **Zero-skip policy applies.** No `continue-on-error`, `# noqa`, per-file-ignores, or warning
  suppression without explicit approval. See `.claude/rules/zero-skip-policy.md`.
- **Local validation gate.** Every commit preceded by `HK_PKL_BACKEND=pkl hk run pre-commit --all --stash none`
  and `uv run --project python pytest tests/ -x -q`.
- **Git state hygiene.** `git add` all deletions before running hk. See `.claude/rules/clean-git-state.md`.

## Non-Goals

- Phase 3 XDG-via-mise refactor (deferred; separate plan).
- Registry migration `sortakool` → `ray-manaloto` (Phase 2 item, not in this PR unless PR #9
  salvage adds it).
- CLion wiring itself is **user-manual** — automation only goes as far as making the devcontainer
  attachable. Original Session D goal of "wire CLion" becomes a post-merge manual checkpoint, not
  a ralplan/autopilot step.
- Collapsing the three-tier mise config into one file.
- Touching `session-2026-04-05*.md` and `session-2026-04-06-{a,b,c,d}.md` historical plans.
- Reinstalling GitButler.

## Acceptance Criteria

### Stage 1: Chezmoi resync
- [ ] **🚨 HARD GATE: `.chezmoiignore` gates `home/dot_config/mise/config.toml.tmpl` to containers only.**
      Add a `{{ if not .is_container }}\n.config/mise/config.toml\n{{ end }}` block to
      `home/.chezmoiignore` (mirroring the existing `.cargo/**`, `.rustup/**` conditional
      pattern). Rationale: this is a devcontainer-only overlay with ~30 runtime tools; it
      must NEVER render on the Mac host. See memory
      `feedback_devcontainer_only_mise_overlay.md`. This AC is a hard blocker — no other
      chezmoi work lands until this guard is in place, because the risk of polluting the
      Mac host during rewire is unacceptable.
- [ ] Verify the gate by running `chezmoi execute-template --init < home/dot_config/mise/config.toml.tmpl`
      with `is_container=false` and confirming it is ignored, then with `is_container=true`
      and confirming it renders.
- [ ] **`home/dot_config/mise/config.toml.tmpl` reduced to an empty placeholder** (user
      decision 2026-04-06). All tools are installed at image-build time via
      `.devcontainer/mise-system.toml`; the chezmoi overlay is NOT used for runtime tool
      installation. The template is kept (not deleted) only as a discoverable forward
      extension point — a header comment explaining the empty state plus an empty `[tools]`
      stub. Target file size: ≤10 lines, down from current 86. The `[tasks."setup:tools"]`
      entry at lines 75-77 is removed (no callsite after `.chezmoiscripts/` is deleted).
- [ ] **`home/.chezmoiscripts/` directory deleted entirely** (user decision 2026-04-06).
      All three files go:
      - `run_once_before_01_install_mise.sh` — redundant; devcontainer already has mise
        baked in via the Dockerfile's mise-bootstrap stage; Mac manages mise independently.
      - `run_onchange_after_10_mise_install.sh.tmpl` — called `mise run setup:tools` which
        no longer exists after the overlay is emptied. Dead code.
      - `run_after_20_import_gpg_keys.sh` — verified dead code 2026-04-06: Ray's git config
        has NO signing set (`gpg.format`, `commit.gpgsign`, `user.signingkey`, `tag.gpgsign`
        all unset), no `~/.config/git/*.asc` files, no GPG secret keys. Script is already a
        no-op on both Mac and future container.
      Architectural rule enforced: chezmoi scripts must NOT install tools — tools belong in
      the Docker image (build-time, cached) or the Mac host (user-managed). Scripts should
      only handle *configuration* (file creation, symlinks, one-shot migrations), not
      package installation. If a future need arises for configuration-only scripts, recreate
      the directory with a single clearly-scoped script and document why.
- [ ] Every `home/**/*.tmpl` file compiles under `chezmoi execute-template --init` without
      referencing variables or paths that no longer exist in the current repo.
- [ ] The `.claude/skills/chezmoi-check/SKILL.md` workflow runs clean against all templates.
- [ ] A drift check (grep/diff) proves no chezmoi template references the removed
      `dotfiles-setup docker` path.
- [ ] **Chezmoi source wiring decision documented.** As of 2026-04-06, `chezmoi source-path`
      returns `~/.local/share/chezmoi` which is an **orphaned source** (has `.git`, zero
      working-tree files, no git remote). The Mac's `~/.config/mise/config.toml` was placed
      by a prior chezmoi setup whose source no longer exists. Before the mega-PR merges,
      the spec must document the intended wiring: either `chezmoi init
      git@github.com:ray-manaloto/dotfiles.git` (using this repo as the remote source) or
      `chezmoi init --source ~/dev/github/ray-manaloto/dotfiles/home` (local source). Until
      that wiring step is executed by the user (not autopilot), the devcontainer-only guard
      above is the only thing preventing Mac pollution.

### Stage 2: Devcontainer build + CLI swap + validation
- [ ] `mise.toml` `[tools]` pins `"npm:@devcontainers/cli"` to an explicit version (not `latest`).
- [ ] `mise.toml` `[tasks.up]` runs `devcontainer up --workspace-folder .` (or equivalent),
      replacing `uv run --directory python dotfiles-setup docker up`.
- [ ] `mise.toml` `[tasks.stop]` (or `[tasks.down]`) runs `devcontainer down` / CLI teardown,
      replacing the wrapper. Alias `[shell_alias]` entries added for common commands.
- [ ] `mise.toml` `[tasks.build]` still invokes `docker buildx bake dev-load` (unchanged) and
      completes successfully on this Mac.
- [ ] `devcontainer up` succeeds on this Mac end-to-end.
- [ ] **Tier 1 — Tools present + hk green:** `devcontainer exec … mise ls && which clang++ python uv hk && hk run pre-commit --all` exits 0.
- [ ] **Tier 2 — Python tests + bind mounts:** `devcontainer exec … uv run --project python pytest tests/ -x -q` passes 65/65; `~/.ssh`, `~/.claude`, workspace mounts resolve to host files.
- [ ] **Tier 3 — C++ + sanitizers:** `devcontainer exec` compiles a hello-world with `clang++ -fsanitize=address,undefined`, runs it, and sanitizer runtime is present.
- [ ] **Tier 4 — CLion-ready:** manual checkpoint documented; image exposes everything CLion's
      "Dev Containers" plugin needs (SSH server running, clangd + gdb/lldb present, remote
      toolchain discoverable).
- [ ] **SSH-agent forwarding works:** `devcontainer exec … ssh-add -l` lists host's keys.
- [ ] **Host git credentials work:** `devcontainer exec … ssh -T git@github.com` authenticates
      as the user; `git ls-remote git@github.com:ray-manaloto/dotfiles.git` succeeds.
- [ ] **Lifecycle events audit:** `devcontainer.json` lifecycle blocks (`initialize`, `onCreate`,
      `updateContent`, `postCreateCommand`, `postStartCommand`, `postAttachCommand`) each
      documented with purpose or explicitly absent; `./install.sh` moved to the most appropriate
      event per containers.dev reference (likely `onCreate` or `updateContent`, not
      `postCreate` as currently).
- [ ] **Telemetry preserved:** `artifacts/build/devcontainer-metrics.json` still emitted with
      build time + image size (and ideally + startup time from `devcontainer up`).
- [ ] **Thin overlay preserved:** `Dockerfile.host-user` line count ≤ baseline + 10. No new
      tool installs beyond what SSH-agent forwarding strictly requires.

### Stage 3: Alignment sweep
- [ ] Root `CLAUDE.md` and `~/CLAUDE.md` updated: dev-loop section says
      `mise run up` / `devcontainer exec …` not `dotfiles-setup docker up`.
- [ ] New `.claude/skills/devcontainer-workflow/SKILL.md` created, documenting: runtime
      prerequisite (Colima vs Docker Desktop), `mise run build` → `mise run up` →
      `devcontainer exec` smoke test → `mise run stop`, troubleshooting (lifecycle event
      failures, SSH-agent issues), and the three-tier mise config model.
- [ ] `.claude/skills/chezmoi-check/SKILL.md` audit result: either confirmed current, or
      updated with the new three-tier model.
- [ ] `.claude/rules/*.md` audit result: no rule references the removed wrapper path. Any new
      rule needed for "devcontainer-cli-only" policy added or explicitly declined.
- [ ] Agents audit (`~/.claude/agents/dockerfile-reviewer.md`,
      `.claude/agents/devcontainer-specialist.md` if ported from PR #9): no stale content.
- [ ] Hooks audit (`.claude/settings.json` hooks + project hooks): no commands referencing
      the removed wrapper path.
- [ ] Devcontainer Features usage documented: for each Feature considered, noted as adopted
      or rejected with reason.

### Post-merge
- [ ] PR #9 closed with a comment linking the mega-PR and a showstopper mapping table
      (each of the 3 adversarial-review showstoppers from
      `docs/research/trail/findings/devcontainer-spec-adversarial-review-2026-03-29.yaml`
      mapped to: addressed / deferred-with-issue / obsolete).

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|---|---|---|
| `--autoresearch` flag was intentional | Flag routes to a different handoff pipeline (mission+evaluator, detaches to tmux, no autopilot) | User dropped `--autoresearch`; standard brownfield interview used |
| PR #9 should be rebased/landed first | PR #9's pattern (host-user overlay with `${localEnv:USER}`) **is already on main** at `.devcontainer/devcontainer.json:8-11`; the 21-file diff mostly predates subsequent main commits | Close PR #9 as superseded after mega-PR lands |
| "Alignment sweep" means audit everything | Contrarian Round 4: name concrete misalignments or concede precautionary | User named concrete items: CLAUDE.md stale dev-loop, new devcontainer-workflow skill, `setup:tools` ghost-task bug, chezmoi-check skill possibly stale, lifecycle events not following spec, thin overlay constraint, metrics continuity |
| Colima is the active runtime | `docker context show` returns `desktop-linux` (Docker Desktop), not Colima; memory says Colima is recommended | **Unresolved — becomes Phase 0 of execution.** Autopilot must either install+start Colima or the user must approve Docker Desktop for this PR |
| `devcontainer` CLI is pinned | `mise.toml:22` declares `"npm:@devcontainers/cli" = "latest"` | Spec requires explicit version pin as Stage 2 AC |
| `Dockerfile.host-user` might need restructuring | Read confirms it's 80 lines of necessary overlay work | Constraint added: preserve thin overlay, line count ≤ baseline + 10 |
| Mega-PR is fine despite bisectability risk | Recommended 3 sequenced PRs; user overrode | Honor user choice, but add "if CI > 25min or hk failures become un-bisectable, split" as revisit trigger |

## Technical Context (Brownfield Facts from Explore)

**Devcontainer build surface:**
- `.devcontainer/devcontainer.json:4` builds from `Dockerfile.host-user`
- `.devcontainer/devcontainer.json:8-11` args: `DEVCONTAINER_USERNAME=${localEnv:USER}`, `BASE_IMAGE=dotfiles-devcontainer:dev`
- `.devcontainer/devcontainer.json:33` `postCreateCommand: ./install.sh`
- `.devcontainer/devcontainer.json:32` `updateRemoteUserUID: false`
- `docker-bake.hcl` targets: `dev` (CI push), `dev-load` (local docker load), `cpp`, `cpp-load`, `validate`, `help`
- `.devcontainer/Dockerfile:4-5` `BASE_IMAGE=ubuntu:26.04`, `MISE_VERSION=v2026.4.4`
- `.devcontainer/Dockerfile:57` copies `/etc/mise/config.toml` from `.devcontainer/mise-system.toml`
- `.devcontainer/Dockerfile.host-user` confirmed thin (80 lines), ends with `USER ${DEVCONTAINER_USERNAME}`

**mise docker/devcontainer state:**
- `mise.toml:22` `"npm:@devcontainers/cli" = "latest"` ← UNPINNED
- `mise.toml:60-66` `up`/`stop` tasks currently call `uv run --directory python dotfiles-setup docker up/down` (wrapper path — to be removed)
- `mise.toml:68-70` `build` task calls `docker buildx bake dev-load` (keep)
- `mise.toml:80-82` `validate` task calls `docker buildx bake validate` (keep)
- No `[shell_alias]` entries currently; no direct `devcontainer` CLI calls in repo
- Current shell shim path: `~/.local/share/mise/installs/npm-devcontainers-cli/0.85.0/bin/devcontainer`

**Chezmoi state:**
- `home/dot_config/mise/config.toml.tmpl` exists (87 lines), overlaps with `.devcontainer/mise-system.toml` on hk/python/bun
- `home/.chezmoiscripts/run_once_before_01_install_mise.sh` — installs mise binary
- `home/.chezmoiscripts/run_onchange_after_10_mise_install.sh.tmpl` — **calls `mise run setup:tools` which doesn't exist** ← concrete bug
- `home/.chezmoi.toml.tmpl` (36 lines) sets `$isEphemeral = $isContainer` for container detection
- `home/.chezmoiignore` (29 lines) skips .cargo/.rustup/.config/gcloud in ephemeral
- Other templates: dot_zshrc.tmpl, dot_bashrc.tmpl, dot_profile.tmpl, dot_zshenv.tmpl, AGENTS.md.tmpl, CLAUDE.md.tmpl, CODEX.md.tmpl, GEMINI.md.tmpl, pixi.toml.tmpl, pyproject.toml.tmpl

**Validation surface:**
- `python/verification/suites.toml` has 40+ suites: build (15), ci (8), identity (6), arch (8), policy (4)
- Includes `arch.devcontainer-remote-user-dynamic`, `arch.base-image-dotfiles-devcontainer`,
  `arch.update-remote-user-uid-disabled`, `arch.mise-strict-in-container`
- **NO existing suite runs `devcontainer up` or `devcontainer exec`** — validation is
  build-artifact inspection only. Gap this spec fills.
- `.github/workflows/ci.yml` pipeline: lint → contract-preflight → build → smoke-test (`metrics.json` only)

**PR #9 state (verified):**
- `gh pr view 9`: state=OPEN, headRefName=`feat/host-user-migration`, mergeable=UNKNOWN
- Touches 21 files including every file this spec also touches
- Adversarial review: `docs/research/trail/findings/devcontainer-spec-adversarial-review-2026-03-29.yaml`
  (3 showstoppers to map in the closing comment)

**Runtime environment (verified 2026-04-06):**
- Docker context: `desktop-linux` (Docker Desktop active)
- Colima: NOT managed by mise, not verified as installed
- devcontainer CLI: v0.85.0 installed via mise npm backend

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|---|---|---|---|
| DevContainer | core domain | image, runtime, lifecycle | built from DevcontainerJson, uses HostUserOverlay |
| DevcontainerJson | config | build, args, mounts, lifecycle events, features | references HostUserOverlay + BaseImage |
| DevcontainerCLI | tool | version, commands (up/exec/down/build) | invoked by MiseTask |
| HostUserOverlay | build artifact | Dockerfile.host-user, DEVCONTAINER_USERNAME, openssh | thin layer atop BaseImage |
| BaseImage | build artifact | ubuntu:26.04 + mise + tools | produced by DockerBake |
| DockerBake | tool | docker-bake.hcl, targets (dev/dev-load/cpp/validate) | produces BaseImage |
| MiseTask | automation | up, stop, build, validate, lint, test | invokes DevcontainerCLI or DockerBake |
| MiseShellAlias | automation | short command aliases | wraps MiseTask |
| MiseConfig3Tier | config | root mise.toml, mise-system.toml, chezmoi overlay | 3 distinct scopes, no collapse |
| ChezmoiTemplate | config | *.tmpl files under home/ | rendered to $HOME at apply time |
| ChezmoiLifecycleScript | automation | run_once_before, run_onchange_after | bug: setup:tools ghost-task |
| SSHAgent | identity | host keys, forwarding socket | required for git auth in container |
| GitCredentials | identity | ssh keys, git config | host → container via mount or agent |
| LifecycleEvent | spec concept | initialize, onCreate, updateContent, postCreate, postStart, postAttach | per containers.dev reference |
| ValidationSuite | test | suites.toml entries, smoke-test tiers 1-4 | runs inside DevContainer via exec |
| BuildMetric | telemetry | build time, image size, startup time | emitted by CI to artifacts/ |
| ClaudeRule | doc | .claude/rules/*.md | alignment sweep target |
| Skill | doc | .claude/skills/*/SKILL.md | alignment sweep target (+ new devcontainer-workflow) |
| Hook | automation | .claude/settings.json hooks | alignment sweep target |
| DevcontainerFeature | spec concept | containers.dev Features catalog | prefer over hand-rolled RUNs |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|---|---|---|---|---|---|
| 1 | 7 | 7 | - | - | N/A |
| 2 | 13 | 6 | 0 | 7 | 54% |
| 3 | 13 | 0 | 0 | 13 | 100% |
| 4 | 15 | 2 | 0 | 13 | 87% |
| 5 | 20 | 5 | 0 | 15 | 75% |

Ontology grew as scope expanded (r2: +identity entities, r4: +lifecycle/metrics, r5: +alignment
entities). No renames, no removals — additive convergence. The core entities (DevContainer,
DevcontainerCLI, MiseTask, HostUserOverlay, ChezmoiTemplate) were stable from r1 onward.

## Challenge Modes Used
- Round 4: **Contrarian** — challenged "alignment sweep" as precautionary; user responded with
  concrete misalignments, validating the work and adding 2 items (lifecycle events, metrics).
- Simplifier and Ontologist modes not triggered (threshold met before round 6).

## Interview Transcript

### Round 0 — Flag reconciliation
**Q:** Did you mean to pass `--autoresearch`? It routes to a different pipeline.
**A:** "lets drop it"
**Outcome:** Standard brownfield `--deep` interview, not autoresearch mode.

### Round 1
**Q:** Which of the 5 workstreams is the primary goal? [devcontainer-up | chezmoi-first | mise-automation | all-three-sequenced]
**A:** "All three, sequenced"
**Ambiguity:** 53% (Goal 0.55, Constraints 0.35, Criteria 0.25, Context 0.85)

### Round 2
**Q:** What must the post-`devcontainer up` smoke test prove? [tier1 | tier2 | tier3 | tier4]
**A:** "1-4 and that ssh access works, mac host user's ssh git credentials work, devcontainer.json is properly using the correct lifecycle events and that all documentation, .claude/rules, skills, agents, hooks, etc are all aligned w this workflow"
**Ambiguity:** 34% (Goal 0.70, Constraints 0.45, Criteria 0.70, Context 0.85)

### Round 3
**Q:** Execution shape + PR #9 disposition? [3PRs-close9 | 3PRs-salvage9 | 1mega | rebase9]
**A:** "1 mega-PR on main"
**Ambiguity:** 26% (Goal 0.75, Constraints 0.70, Criteria 0.70, Context 0.85)

### Round 4 (Contrarian)
**Q:** Name concrete alignment misalignments, or concede precautionary. [multiSelect]
**A:** All four + "chezmoi-check SKILL.md might also be out of sync. and we must fully understand and properly use https://containers.dev/implementors/json_reference/#lifecycle-scripts. and .devcontainer/Dockerfile.host-user is really a very thin overlay and nothing more. and we continue to track telemetry/metrics to be able to improve the build times/binary sizes"
**Ambiguity:** 19.25% (Goal 0.80, Constraints 0.80, Criteria 0.80, Context 0.85) — **gate met**

### Round 5 (Consolidation)
**Q:** Prerequisites + PR #9 disposition confirmation. [multiSelect]
**A:** "I'll verify Colima myself, Close PR #9 as superseded, Pin @devcontainers/cli, also enforce to try and use devcontainer features whenever possible. review: https://mise.jdx.dev/mise-cookbook/docker.html https://mise.jdx.dev/cli/generate/devcontainer.html#mise-generate-devcontainer"
**Outcome:** Colima check revealed Docker Desktop is active (flagged as Phase 0 decision);
devcontainer CLI v0.85.0 confirmed; PR #9 confirmed OPEN; Dockerfile.host-user confirmed thin.

## Open Questions (for ralplan Phase 0)

1. **Runtime decision: ✅ RESOLVED 2026-04-06.** Colima installed via `mise.toml`
   (`colima = "0.10.1"`, `lima = "2.1.1"`, both pinned after verification). Started with
   `colima start --cpu 4 --memory 8 --vz-rosetta --arch aarch64`. Verified: `docker context
   show` = `colima`; Docker server 29.2.1 / aarch64 / Ubuntu 24.04.4 LTS; `mountType:
   virtiofs`; `docker run --platform=linux/amd64/v2 alpine:3 uname -m` returns `x86_64`
   (Rosetta AMD64 emulation confirmed working).
2. **Version to pin for `@devcontainers/cli`:** currently `0.85.0` installed; is that the latest
   stable or should ralplan check npm for newer before pinning?
6. **Chezmoi source wiring (NEW 2026-04-06):** `chezmoi source-path` is
   `~/.local/share/chezmoi` which is an orphaned source (`.git` only, no files, no remote).
   Before the mega-PR merges or anyone runs `chezmoi apply`, the wiring must be decided and
   executed by the user (not autopilot). Options: (a) `chezmoi init
   git@github.com:ray-manaloto/dotfiles.git` using the GitHub repo as the remote source,
   (b) `chezmoi init --source ~/dev/github/ray-manaloto/dotfiles/home` using the local path
   directly. Option (a) requires the repo's `home/` subdirectory to be declared via
   `.chezmoiroot` or for chezmoi to be pointed at the subdirectory.
3. **Lifecycle event mapping:** which containers.dev lifecycle event should host `./install.sh`?
   Current `postCreateCommand` fires after container creation but before user attach — may be
   wrong per spec reading.
4. **`setup:tools` resolution path:** define the task in `.devcontainer/mise-system.toml` (so it
   exists system-wide inside the container) vs. remove the chezmoi script call entirely and let
   mise postinstall handle it? Architecture decision for Stage 1.
5. **Devcontainer Features to adopt:** candidates — `common-utils`, `docker-in-docker`,
   `ssh-agent`, `git`. Which are worth the pull-through cost vs. current hand-rolled approach?

## Research Tasks (for ralplan Phase 1)

- Read https://containers.dev/implementors/json_reference/#lifecycle-scripts (full spec for all
  6 lifecycle events, their ordering, their blocking semantics).
- Read https://mise.jdx.dev/mise-cookbook/docker.html (mise's official docker guidance).
- Read https://mise.jdx.dev/cli/generate/devcontainer.html (evaluate `mise generate devcontainer`
  as a source of truth or reference generator).
- Enumerate containers.dev Features catalog and score each for adoption.
- Read `docs/research/trail/findings/devcontainer-spec-adversarial-review-2026-03-29.yaml` for
  PR #9's 3 showstoppers to address in the mega-PR or explicitly defer.

## References

- Session handoff: `.omc/plans/session-2026-04-06-d.md`
- Phase 2 spec: `docs/ultrapowers/specs/2026-03-29-devcontainer-host-user-migration-design.md`
- Phase 2 adversarial review: `docs/research/trail/findings/devcontainer-spec-adversarial-review-2026-03-29.yaml`
- PR #9: https://github.com/ray-manaloto/dotfiles/pull/9
- Memory: `feedback_colima_recommendation.md`, `feedback_stacked_pr_merge_order.md`, `project_two_build_types.md`
- Rules: `.claude/rules/zero-skip-policy.md`, `.claude/rules/ci-local-parity.md`, `.claude/rules/clean-git-state.md`
