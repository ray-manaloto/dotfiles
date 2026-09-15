# Devcontainer architecture review

## Executive verdict

Keep the existing layered image and architecture-scoped whole-home volume. Resolve Claude by assigning one owner to each layer:

- Published image: system/build tooling plus image-owned Codex and Gemini.
- Mounted home: native Claude installation.
- Chezmoi: user configuration, but no Claude launcher.
- Devcontainer lifecycle: provision native Claude after the home volume is mounted.
- CI: split bare-image validation from lifecycle validation.

The specific Claude resolution is:

1. Remove `claude-code` from [mise-runtime.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:58) and regenerate its lock.
2. Remove the chezmoi-managed [Claude mise wrapper](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/home/dot_local/bin/executable_claude:1).
3. Install Claude natively during `onCreateCommand`, after repairing home ownership and applying chezmoi.
4. Stop requiring Claude in the bare-image smoke; retain Codex and Gemini there.
5. Verify Claude’s launcher target and native ownership in focused post-create/lifecycle checks.

Changing or shrinking the home mount would not fix ownership. Installing Claude in either Dockerfile would remain wrong because the runtime mount hides image content beneath `/home/$USER`.

## Current stage and lifecycle map

### Image stages

| Stage | Contribution |
|---|---|
| `devcontainer-base` | Ubuntu base, mise itself, declarative apt packages, and system/shared mise tools. [Dockerfile:33](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:33) [Dockerfile:208](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:208) |
| `clang-builder-cold` | Builds the P2996 Clang fork independently. [Dockerfile:417](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:417) |
| `p2996-export` | Exports only the built P2996 compiler through a scratch stage. [Dockerfile:542](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:542) |
| `devcontainer` | Combines the base with architecture-specific compiler/development tooling. [Dockerfile:554](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:554) |
| `devcontainer-runtime` | Adds locked runtime tools and is the published Bake target. [Dockerfile:655](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:655) [docker-bake.hcl:130](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:130) |
| `Dockerfile.host-user` | Local-only overlay that maps the host UID/GID, establishes `HOME`/`PATH`, and switches users. It should remain identity-only. [Dockerfile.host-user:51](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile.host-user:51) |

The home volume name is already scoped by workspace and architecture, so uniqueness is not the defect. It intentionally covers the entire runtime home and persists user-level state. [devcontainer.json:125](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:125) [.devcontainer/AGENTS.md:67](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/AGENTS.md:67)

### Recommended lifecycle sequence

1. `initializeCommand`: retain host-only staging of scoped secrets and `authorized_keys`. This correctly occurs before image/container creation. [devcontainer.json:230](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:230) [devcontainer spec:4320](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/mintlify-cache/devcontainers/spec/llms-full.txt:4320)

2. `onCreateCommand`, once per container creation:

   - Repair persistent-home ownership first.
   - Apply chezmoi.
   - Remove only an exact match of the legacy mise-based Claude wrapper from reused volumes.
   - Install/reshim the remaining user mise overlay.
   - Converge Claude through Anthropic’s native installer.
   - Clean temporary state.

   The current script applies chezmoi before ownership repair, which should be reversed. [on-create.sh:40](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/scripts/on-create.sh:40) [on-create.sh:43](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/scripts/on-create.sh:43)

   The native-convergence logic is non-trivial and should live in Python behind a thin `on-create.sh` invocation, consistent with the repository’s zero-bash rule. [AGENTS.md:130](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/AGENTS.md:130)

3. `updateContentCommand`: intentionally absent. The repository uses a local bind-mounted workspace and explicit sync/recreate flows; there is no independent content-delivery phase requiring this hook. The hook’s normative purpose is refreshed source content. [devcontainer spec:4424](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/mintlify-cache/devcontainers/spec/llms-full.txt:4424)

4. `postCreateCommand`: retain first-create socket ownership, `authorized_keys`, and `known_hosts` provisioning, followed by focused readiness checks:

   - Claude resolves from `$HOME/.local/bin/claude`.
   - Its resolved target is below `$HOME/.local/share/claude/versions/`.
   - `claude doctor` reports native ownership.
   - Required SSH files/socket and essential lifecycle sentinels are ready.

   Remove the present full compiler/test/network smoke from this hook. The current smoke is extensive and is already available through explicit public tasks. [devcontainer-smoke.sh:20](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/devcontainer-smoke.sh:20) [mise.toml:469](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:469)

5. Add `"waitFor": "postCreateCommand"`. The specification default is `updateContentCommand`, so post-create work may otherwise continue after the environment is reported ready. [devcontainer spec:4374](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/mintlify-cache/devcontainers/spec/llms-full.txt:4374)

6. `postStartCommand`: retain the Docker Desktop socket ownership repair on every start. [devcontainer.json:238](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:238)

7. `postAttachCommand`: intentionally absent because none of this work is client-attachment-specific; that hook would run on every attach. [devcontainer spec:4427](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/mintlify-cache/devcontainers/spec/llms-full.txt:4427)

8. Full smoke remains explicit: `mise run dev` continues as `up → smoke`, and `verify-local` retains R1/R2/R3 validation. [mise.toml:469](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:469) [mise.toml:511](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:511)

## Defects found

### Critical: Claude has three competing owners

The runtime tier declares mise-managed `claude-code`, its lock resolves the Aqua package for both Linux architectures, and the runtime Docker stage installs it system-wide. [mise-runtime.toml:58](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:58) [mise-runtime.lock:583](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583) [Dockerfile:671](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:671)

Chezmoi separately writes `~/.local/bin/claude` as a wrapper around `mise exec claude-code`. [executable_claude:1](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/home/dot_local/bin/executable_claude:1)

CI then independently requires `claude` in the published bare image. [image.py:1042](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1042)

All three contradict native-installer ownership.

### Critical: bare-image smoke tests a lifecycle fiction

CI pulls the per-leg image and runs its smoke with no devcontainer lifecycle or home mount. [build-publish.yml:898](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:898) [image.py:1101](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1101)

Removing the runtime Claude declaration automatically corrects the derived exact-tool-set assertion, but the separate hard-coded `command -v claude` loop remains and must also change. [image.py:253](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:253) [image.py:438](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:438)

### High: lifecycle readiness is not awaited

The repository describes post-create smoke as required, but defines no `waitFor`, leaving the specification’s `updateContentCommand` default in effect. [devcontainer.json:235](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:235) [.devcontainer/AGENTS.md:38](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/AGENTS.md:38)

### High: lifecycle validation can bypass CI

The image hash covers Dockerfile/runtime mise inputs but not `devcontainer.json`, `on-create.sh`, home templates, or the devcontainer smoke script. [p2996_hash.py:480](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:480)

That is reasonable for image-content caching, but there is no separate lifecycle validation identity. A lifecycle-only change can therefore reuse an old validated-image marker without testing the changed lifecycle.

The workflow caller’s path filter also omits relevant workflow, action, home-template, and lifecycle-smoke surfaces. [ci.yml:274](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:274)

### High: arm64 artifact names are not unique

The matrix has two arm64 rows with distinct `tag_suffix` values, but artifacts use only `matrix.target.arch`. [platform_target.py:198](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/platform_target.py:198) [build-publish.yml:792](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:792)

Use `tag_suffix` for artifact identity.

### Medium: smoke topology is under-specified

The generated `docker run` has no mounts but does not explicitly select root; root is inherited from the published image. [image.py:1101](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1101)

The corresponding unit test rejects only the literal `--volume`; `--mount`, `-v`, and equals-form options would escape detection. [test_image_smoke.py:93](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_image_smoke.py:93)

### Medium: documentation and comments are stale

Examples include:

- Runtime TOML claims an HTTP Claude backend while the lock records Aqua. [mise-runtime.toml:59](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:59) [mise-runtime.lock:583](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583)
- System TOML recommends installing Claude in `Dockerfile.host-user`, where the home mount would hide it. [mise-system.toml:412](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-system.toml:412)
- Lifecycle documentation names devcontainer CLI 0.88.0 while the repository pins 0.89.0. [devcontainer-lifecycle-hooks.md:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/devcontainer-lifecycle-hooks.md:3) [mise.toml:22](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:22)
- Dockerfile comments describe separate Cargo/Rustup volumes despite the active whole-home mount. [Dockerfile:54](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:54)
- The P2996 Dockerfile default and Bake-supplied ref differ. [Dockerfile:420](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:420) [docker-bake.hcl:98](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:98)

## Mise subsystem verdicts

| Subsystem | Verdict | Rationale and migration cost |
|---|---|---|
| `bootstrap` | **ADOPT / retain selectively** | Already appropriate for declarative apt packages. Full bootstrap also traverses files, services, repositories, dotfiles, tools, and tasks and is sequential rather than transactional. Retain the scoped package call; do not replace Docker/devcontainer lifecycle with blanket bootstrap. [Dockerfile:208](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:208) [bootstrap.md:132](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/bootstrap.md:132) |
| `oci` | **REJECT** | Still experimental, packages binaries from same-OS/same-architecture Linux hosts, and requires per-architecture publication. It does not replace the compiler-builder stages, named contexts, cache/provenance policy, devcontainer Features, overlay, or runtime lifecycle. Migration would be a large CI regression rather than simplification. [mise-oci.md:19](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/mise-oci.md:19) [mise-oci.md:442](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/mise-oci.md:442) |
| `dot` / `dotfiles` | **REJECT** | Mise dotfiles introduces a second history/template/copy/link owner while chezmoi already owns rendered home configuration. Replacing chezmoi would require a wholesale migration and would not solve Claude’s lifecycle placement. [dotfiles.md:20](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dotfiles.md:20) [on-create.sh:40](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/scripts/on-create.sh:40) |

Feature checks against installed mise 2026.9.9 all returned direct `rc=0` for `bootstrap --help`, `oci --help`, `dot --help`, and `bootstrap dotfiles --help`. `mise dot --help` identifies the command as `mise dotfiles`.

Controlled repository probes found no current `mise oci` or mise-dotfiles configuration (`rc=1`); same-corpus controls found `mise install` and chezmoi usage (`rc=0`). The image itself currently pins mise 2026.9.8, so exact 2026.9.9 behavior inside the image is unverified and would require an image update if these features were adopted. [Dockerfile:106](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:106)

## Recommended architecture and migration

1. Remove Claude from the runtime mise config and regenerate—not hand-edit—the runtime lock. Existing tests require configuration and lock tool sets to agree. [test_lock_coverage.py:152](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_lock_coverage.py:152)

2. Delete the chezmoi Claude wrapper. During migration, remove an existing installed copy only when its content exactly matches the retired wrapper, preserving unrelated user customizations.

3. Add a Python-backed native-Claude convergence command called by `on-create.sh`. It should:

   - recognize an already healthy native installation by launcher target and doctor output;
   - otherwise run the official native installer from a bounded, non-root working directory;
   - fail closed on download or installer failure;
   - never add Claude to mise `[tools]`.

   Anthropic’s documented native layout is `~/.local/bin/claude` pointing into `~/.local/share/claude/versions`. [Claude setup.md:193](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/claude-code-docs/content/en/docs/claude-code/setup.md:193)

4. Preserve the complete home volume. It is the correct location for native installation, auto-update state, and architecture-specific user tools. [TOOL-PERSISTENCE.md:92](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/TOOL-PERSISTENCE.md:92)

5. Split CI validation:

   - Bare-image smoke: explicitly run without mounts, preferably with an explicit root user; require Codex and Gemini and require Claude to be absent.
   - Lifecycle smoke: use `@devcontainers/cli`, an exact per-leg image tag, and a fresh home volume. Exercise the same `onCreateCommand` and verify native Claude.
   - The CI lifecycle profile must omit Docker Desktop-only SSH-socket assumptions; real R1/R2 remain in the Docker Desktop-backed local gate.
   - Run lifecycle smoke even when the image-content cache hits, and require both smoke families before manifest publication.

   Raw Docker must not be substituted for devcontainer lifecycle. [.claude/rules/do-not.md:16](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/do-not.md:16)

6. Keep image hashes scoped to image inputs. Add a separate lifecycle identity/change route covering `devcontainer.json`, `on-create.sh`, relevant home templates, lifecycle smoke, the reusable workflow, and local actions.

7. Replace arm-only artifact names with `tag_suffix` and correct stale tag comments.

### Migration cost and likely breakage

- Runtime lock refresh and a thin `devcontainer-runtime` image rebuild.
- One-time cleanup of the legacy wrapper in existing named home volumes.
- New outbound dependency on Anthropic’s installer during fresh container creation.
- Bare-image consumers will intentionally stop receiving Claude.
- New CI lifecycle validation needs a Linux-safe devcontainer configuration that shares the real on-create entrypoint without pretending Docker Desktop’s SSH socket exists.
- Documentation and contract updates across the mise tiers, persistence guide, lifecycle reference, and generated agent instructions.

No base-stage redesign, mount removal, or R1/R2/R3 wiring change is required.

## Required verification and fail arms

| Contract | Positive arm | Realistic revert arm |
|---|---|---|
| Single Claude owner | No Claude declaration in image mise configs/locks and no chezmoi launcher. | Restore either the runtime entry or wrapper; policy test fails. |
| Bare-image contract | Isolated `PATH` with working Codex/Gemini and no Claude passes. | Restore `claude` to the hard-coded loop; execution fails. |
| Native lifecycle | Fresh mounted home produces a launcher below `$HOME/.local/share/claude/versions` and doctor reports native. | Remove native convergence or restore the mise wrapper; ownership check fails. |
| Reused-volume migration | Exact legacy wrapper is replaced; an unrelated custom launcher is preserved or rejected explicitly. | Remove exact-match guard; preservation arm fails. |
| Mount behavior | Sentinel baked beneath `/home/$USER` is hidden, while a `/usr/local` sentinel remains visible. | Remove/change the home mount; masking arm fails. |
| Lifecycle readiness | `waitFor=postCreateCommand`; `up` waits through focused checks. | Remove `waitFor`; static contract fails. |
| Full-smoke placement | `mise run dev` performs `up → smoke`; post-create contains focused checks only. | Restore full smoke to post-create; structural contract fails. |
| Docker command topology | Explicit user policy and rejection of `-v`, `--volume*`, and `--mount*`. | Add each supported mount spelling independently; each test fails. |
| Cache coupling | Editing runtime TOML or its lock changes `compute_repo_dev_hash()`. | Remove either gather input; its repository-level mutation arm fails. |
| Lifecycle routing | Every lifecycle/workflow input triggers lifecycle validation; unrelated docs do not. | Remove each relevant path individually; routing test fails. |
| Matrix identity | Artifact names are unique across every matrix row. | Revert `tag_suffix` to `arch`; duplicate-name test fails. |
| R1/R2/R3 | Existing inbound SSH, live GitHub SSH, and default amd64 gates remain green. | Independently remove authorized-key setup, post-start socket repair, or platform wiring; the corresponding gate fails. |

## Licensed dissent

- The spec’s 2.1.272 schema version is not an authoritative runtime Claude pin. That source is vendored declaration data and explicitly has no mise `[tools]` pin. [sources.toml:48](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:48) A live probe during this review found native Claude 2.1.273 with native ownership and `rc=0`; historical memory recorded 2.1.270, demonstrating why this is live-only state.
- Root policy defines durable R3 as amd64, while the devcontainer documentation also supports opt-in arm64 operation. Preserve amd64 as the default contract without deleting the arm64 validation/profile path. [AGENTS.md:157](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/AGENTS.md:157) [.devcontainer/AGENTS.md:67](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/AGENTS.md:67)
- “Full refactor” does not justify adopting mise OCI or dotfiles where they duplicate or weaken mature repository boundaries.

## Review execution

No repository gate was run, no report file was written, and no checkout file was modified. Final `git status --short` matched the review checkpoint; the existing modified/untracked research files were left untouched.

The mandatory Graphify query and health check were both attempted. Each returned direct `rc=1` because the read-only sandbox prevented mise temporary-directory cleanup. No graph evidence was produced, so all lanes used the repository-authorized specific-source fallback.

### Specialists spawned:

- `sdlc-image-specialist`
- `sdlc-config-specialist`
- `sdlc-workflows-specialist`
- `sdlc-python-specialist`
- `sdlc-documentation-specialist`
- No other specialists were spawned.

