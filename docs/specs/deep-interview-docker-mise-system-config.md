# Deep Interview Spec: Docker Build Simplification via mise System Config

## Metadata
- Interview ID: di-docker-mise-system-config
- Rounds: 8
- Final Ambiguity Score: 15.0%
- Type: brownfield
- Generated: 2026-04-05
- Threshold: 20%
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.90 | 0.35 | 0.315 |
| Constraint Clarity | 0.85 | 0.25 | 0.213 |
| Success Criteria | 0.75 | 0.25 | 0.188 |
| Context Clarity | 0.90 | 0.15 | 0.135 |
| **Total Clarity** | | | **0.850** |
| **Ambiguity** | | | **0.150** |

## Goal
Build a comprehensive Docker build validation system for `.devcontainer/Dockerfile`. Simplify the Dockerfile by using `/etc/mise/config.toml` as a dedicated system config file (not derived from the chezmoi template). Eliminate the chezmoi dependency entirely from the Docker build. Add hk linters for tool installation validation, build metrics (time and binary size), build log scanning for warnings/errors/issues, mise tasks and hooks for automation, and OMC skills for workflow automation. The final state is a CI/CD pipeline on GitHub Actions that builds, validates, and publishes the image.

## Constraints
- **No chezmoi in Docker build**: The base Dockerfile must not reference or depend on chezmoi templates. The chezmoi template (`home/dot_config/mise/config.toml.tmpl`) continues to manage user dotfiles but is not used during image build.
- **Dedicated Docker mise config**: Create a standalone `/etc/mise/config.toml` purpose-built for the Docker image, not derived from any template.
- **Minimal Docker ENV**: Only `PATH` stays as a Docker `ENV` instruction. All other environment variables move into `/etc/mise/config.toml` `[env]` section.
- **Target platform**: `linux/amd64/v2` (x86_64). The macOS host connects via CLion to use the devcontainer as a remote development environment.
- **All files are modifiable**: No read-only files. Dockerfile, Dockerfile.host-user, docker-bake.hcl, devcontainer.json, mise configs, hk.pkl, Python code — all eligible for changes.
- **Thin host-user overlay**: `Dockerfile.host-user` inherits the base image and only: creates the mac host user as devcontainer user, validates SSH, ensures all base tools are available, sets up docker mount for mise cache/install persistence across devcontainer restarts.
- **No lifecycle tool installs**: `devcontainer.json` lifecycle events (postCreateCommand, etc.) must NOT install tools. All tools come pre-installed from the base image.
- **CI/CD target**: GitHub Actions is the final build/publish platform.
- **Zero-skip policy**: All warnings, errors, and issues in build logs must be evaluated, researched, and fixed — never suppressed or dismissed.

## Non-Goals
- ARM/aarch64 platform support (amd64 only)
- chezmoi template modification (it stays as-is for dotfiles)
- VS Code-specific features (CLion is the IDE client)
- Host-user passthrough complexity beyond basic user creation + SSH

## Acceptance Criteria
- [ ] Dockerfile builds successfully without any chezmoi dependency
- [ ] `/etc/mise/config.toml` is a dedicated file in the repo (not generated from template)
- [ ] Only `PATH` remains as Docker ENV; all other vars in mise `[env]`
- [ ] `mise doctor` passes inside the built container
- [ ] `mise ls` shows all expected tools installed
- [ ] `sshd -t` validates SSH configuration in base image
- [ ] `hk run pre-commit --all` passes with new/updated linters
- [ ] `pytest tests/` passes with new/updated test coverage
- [ ] Build logs contain zero unresolved warnings or errors
- [ ] Build time and image size metrics are captured and tracked
- [ ] mise tasks exist for Docker validation pipeline
- [ ] hk linters exist to prevent regressions in tool installation
- [ ] mise hooks (postinstall or equivalent) automate validation
- [ ] GitHub Actions CI/CD builds and validates the image
- [ ] Dockerfile.host-user remains a thin overlay (user + SSH + mount only)
- [ ] devcontainer.json lifecycle events install zero tools
- [ ] Review against remote `main` branch confirms feature parity

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| chezmoi template needed for Docker | Checked template — has zero `{{` tags, pure TOML | Template is unnecessary; use dedicated file |
| sed hack is functional | Inspected line 79 — `sed '/{{/d'` is a no-op | Remove entirely |
| ENV vars needed before mise | Challenged which vars are build-time vs runtime | Only PATH needed as Docker ENV |
| Scope is just Dockerfile simplification | Contrarian: is QA pipeline a separate initiative? | User confirmed: full mandate, single mission |
| Narrow mission better for autoresearch | Simplifier: start narrow, let it discover? | User chose full mandate from start |
| Some files should be read-only | Asked about Dockerfile.host-user, CI workflows | Everything modifiable with stated invariants |
| VS Code is the IDE | devcontainer.json mentions VS Code extensions | CLion is the actual IDE client |

## Technical Context
### Current State (brownfield)
- **Dockerfile** (91 lines): Ubuntu 26.04, mise v2026.4.4, 15+ ENV vars, sed hack on line 79, chezmoi template copied during build
- **Dockerfile.host-user**: Extends base, creates user, SSH, sudo, home dirs
- **docker-bake.hcl**: BuildKit bake with dev/dev-load/validate targets, GHA cache, attestation
- **mise.toml**: Project tools (linting), Python prep, task definitions
- **config.toml.tmpl**: 43 tools, [settings], [env], [tasks] — pure TOML, no chezmoi tags
- **install.sh**: Post-create chezmoi init + apply
- **devcontainer.json**: Dockerfile.host-user build, mounts, VS Code extensions

### Target State
- Dedicated `etc/mise/config.toml` (or similar path) in repo for Docker-specific mise config
- Dockerfile with minimal ENV (PATH only), COPY of dedicated config, `mise install -y`
- Comprehensive validation: build + runtime checks + linters + metrics + log scanning
- Automated via mise tasks, hk hooks, and OMC skills
- CI/CD on GitHub Actions

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Dockerfile | core domain | stages, ENV, RUN, COPY, platform | builds mise system config, produces base image |
| mise system config | core domain | /etc/mise/config.toml, [tools], [env], [settings] | installed into Dockerfile, read by mise |
| Docker mise config | core domain | dedicated repo file, not from template | COPY'd into /etc/mise/config.toml |
| Docker build pipeline | core domain | bake, metrics, log scanning, CI/CD | orchestrates Dockerfile build and validation |
| Dockerfile.host-user | supporting | thin overlay, user, SSH, mount | inherits base image, adds host user |
| hk linters | supporting | tool install checks, regression prevention | validates build output |
| mise hooks | supporting | postinstall, automation | triggered after tool installation |
| cache mount | supporting | docker volume, mise data persistence | survives devcontainer restart |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 5 | 5 | - | - | N/A |
| 2 | 5 | 0 | 0 | 5 | 100% |
| 3 | 9 | 4 | 0 | 5 | 55.6% |
| 4 | 8 | 1 | 1 | 6 | 75.0% |
| 5 | 8 | 0 | 0 | 8 | 100% |
| 6 | 8 | 0 | 0 | 8 | 100% |
| 7 | 8 | 1 | 1 | 6 | 87.5% |
| 8 | 8 | 0 | 0 | 8 | 100% |

## Interview Transcript
<details>
<summary>Full Q&A (8 rounds)</summary>

### Round 1
**Q:** The Dockerfile already copies tools config to /etc/mise/config.toml (line 79). The sed strip is a no-op since the template has no {{ tags. What specific simplification are you after?
**A:** All of the above + reduce Dockerfile lines (holistic simplification: consolidate mise config, remove sed, reduce ENV duplication, fewer RUN layers)
**Ambiguity:** 63.5% (Goal: 0.60, Constraints: 0.10, Criteria: 0.10, Context: 0.70)

### Round 2
**Q:** Which ENV vars in the Dockerfile must stay as Docker ENV vs move into /etc/mise/config.toml [env]?
**A:** Minimal: only PATH stays as Docker ENV. Maximum consolidation.
**Ambiguity:** 48.0% (Goal: 0.70, Constraints: 0.50, Criteria: 0.15, Context: 0.75)

### Round 3
**Q:** What evaluator command should autoresearch use to verify each iteration?
**A:** Option 3 (build + mise doctor) plus: run all hk linters, docker metrics on build time and binary size, parse all build logs for warnings/errors, add hk linters/checks to prevent issues, automate via skills and mise tasks and hooks.
**Ambiguity:** 50.8% (Goal: 0.50, Constraints: 0.40, Criteria: 0.45, Context: 0.70) — scope expanded

### Round 4 (CONTRARIAN MODE)
**Q:** Should autoresearch focus narrowly on Dockerfile simplification or is the real goal a comprehensive Docker QA pipeline?
**A:** Broad: Docker QA pipeline. Also: chezmoi not needed anymore for Docker build, install from /etc/mise directly.
**Ambiguity:** 44.8% (Goal: 0.65, Constraints: 0.50, Criteria: 0.35, Context: 0.75)

### Round 5
**Q:** Can we define the evaluator as a mise task that chains all checks?
**A:** Let autoresearch figure it out.
**Ambiguity:** 36.0% (Goal: 0.70, Constraints: 0.55, Criteria: 0.55, Context: 0.80)

### Round 6 (SIMPLIFIER MODE)
**Q:** Should the autoresearch mission be narrow or full mandate?
**A:** Full mandate from the start.
**Ambiguity:** 33.8% (Goal: 0.80, Constraints: 0.55, Criteria: 0.50, Context: 0.80)

### Round 7
**Q:** What files should autoresearch treat as read-only?
**A:** Everything is eligible. Invariants: no chezmoi in Docker, thin host-user overlay with SSH, no lifecycle tool installs, cache mount for mise persistence, review against remote main.
**Ambiguity:** 23.8% (Goal: 0.85, Constraints: 0.80, Criteria: 0.55, Context: 0.85)

### Round 8
**Q:** Is the inferred evaluator (build + mise doctor + mise ls + hk + pytest) sufficient?
**A:** Yes, plus add SSH validation (sshd -t). Docker build targets GHA CI/CD. Platform is amd64. Mac + CLion is the client.
**Ambiguity:** 15.0% (Goal: 0.90, Constraints: 0.85, Criteria: 0.75, Context: 0.90)

</details>
