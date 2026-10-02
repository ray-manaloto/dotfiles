# dockerfile-reviewer — 93d70c96 (native-cli-devcontainer)

Persisted verbatim at receipt by the coordinator.

Review of 93d70c96 vs origin/main (worktree /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/native-cli-devcontainer-20261001). Verdict: no blockers. Read-only; no build or tests were run.

Findings
| Severity | Item | file:line |
|---|---|---|
| Medium | Smoke correctness: no test pins the new absence assertion. tests/test_image_smoke.py only asserts "AI CLI checks" is NOT in the tier-1 and tier-3 substrates (lines 871, 1002). Nothing checks that build_smoke_script emits the `for tool in claude codex agy` absent-loop or the gemini-present check. Dropping the loop would silently stop guarding against a baked claude/codex/agy. I found no test covering its FAIL arm. | python/src/dotfiles_setup/image.py:1043-1053 |
| Low | Checklist 1: .github/workflows/AGENTS.md still says the build job passes the token via a secret mount "(uid=1000)", which contradicts the root-build model. Predates this commit; unchanged context. | .github/workflows/AGENTS.md:125 |
| Info | The latest-pinned bumps from lock-image are legitimate. mise-system.lock: conda:git 2.55.0->2.56.0, rust 1.98.1->1.99.0. mise-runtime.lock: gh 2.102.0, task 3.54.0, turso 0.8.1, gemini-cli 0.62.0, conan 2.33.0, usage 6.12.0. The base tier is rebuilding cold anyway. | .devcontainer/mise-system.lock, .devcontainer/mise-runtime.lock |

Checked and clean
- Hash coverage: base hash reads mise-system.lock, mise-system.toml and .config/mise/conf.d/shared.toml (p2996_hash.py:353-366). Runtime hash reads mise-runtime.toml and mise-runtime.lock (p2996_hash.py:503-506). So removing codex from shared.toml changes the base hash (cold rebuild, as expected), and removing claude-code from mise-runtime.toml changes the runtime hash.
- Leftover claude/codex expectations: none in Dockerfile, Dockerfile.host-user, devcontainer.json, docker-bake.hcl or build-publish.yml. The only hits are .claude/rules doc references.
- Lock consistency: shared.toml and mise-system.lock both drop npm:@openai/codex. mise-runtime.toml and mise-runtime.lock both drop claude-code. Host .config/mise/mise.lock drops the codex block, with its options. mise-system.lock has no other change beyond the git and rust bumps.
- Smoke scope: the absence loop is in build_smoke_script (image.py:931), the CI-only tail, not the shared build_tier3_script (image.py:835). So the in-container verify-container-latest smoke does not run it. That path instead runs `devcontainer native-clis check` (scripts/devcontainer-smoke.sh:93-94), which expects the natives present, installed into the home volume by on-create.sh. The two paths are consistent. The CI no-mount smoke has no home volume, so absent is the right expected state.
- ci.yml: removing `MISE_DISABLE_TOOLS: ""` is consistent, since shared.toml no longer carries the npm codex pin and mise.toml:158 already narrowed disable_tools to antigravity-cli. No workflow still sets MISE_DISABLE_TOOLS.
- on-create.sh: the native-clis install runs before chezmoi, with a justifying comment about the agy installer appending PATH lines to the managed rc files. bash_budget.py has the matching entries.

Checklist items not touched by the diff, so not evaluated: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12.

## GitHub repos touched

_None._
