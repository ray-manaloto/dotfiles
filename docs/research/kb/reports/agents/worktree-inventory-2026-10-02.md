# Worktree inventory — dotfiles + knowledge-base, 2026-10-02T21:03Z (read-only)

Ray ruling 2026-10-02 (audit-000 /grilling round 2): promote the inventory to a tracked report, then for each unpushed
branch either push it or get a Ray ruling, then remove only clean, pushed worktrees. The coordinator
(`dotfiles-20261002.coordinator`) runs the push/remove step after the current ships. This file changes nothing.

## Live snapshot (2026-10-02T21:03Z)

Method: `/usr/bin/git worktree list --porcelain` per repo; per worktree `status --porcelain` (dirty count),
`origin/<branch>` present among the local remote-tracking refs, and `branch -r --contains HEAD` (is the HEAD
commit reachable from ANY remote-tracking ref). Remote-tracking refs are as last fetched by any session, so not
re-fetched here. Control arms: `docs/handoff-2026-10-02` (pushed by the coordinator today) reads yes/yes; this
audit branch (never pushed) reads no/NO. The probe tells the two apart.
Read "HEAD on any remote = NO" as: the commits exist only on this Mac. "Dirty > 0" means uncommitted work. Both
are ⚠, so do NOT remove that worktree without a salvage decision. Removing a worktree never deletes its branch.

### dotfiles (29 worktrees)

| Worktree | Branch | HEAD | Dirty files | On origin (branch) | HEAD on any remote | Locked |
|---|---|---|---|---|---|---|
| `dotfiles` | `fix/ops-sync-1478-1481` | `60fc34ce` | 0 | no | NO |  |
| `~/.codex/worktrees/3f4c/dotfiles` | `codex/graphify-0-9-67` | `eb9a8c16` | ⚠ 14 | no | yes |  |
| `dotfiles.worktrees/agent-shell-env-20260930` | `fix/agent-shell-mise-hookenv` | `f08cd0a9` | ⚠ 12 | no | yes |  |
| `dotfiles.worktrees/agentsview-managed-service` | `codex/agentsview-managed-service` | `e0f58cea` | ⚠ 8 | no | yes |  |
| `dotfiles.worktrees/agentsview-native-service` | `codex/agentsview-native-service` | `36537951` | ⚠ 6 | yes | yes | yes |
| `dotfiles.worktrees/agy-native-20260930` | `feat/native-cli-installers-workflow` | `102ee0c5` | 0 | yes | yes |  |
| `dotfiles.worktrees/cc-repoint-20261002` | `docs/cc-repoint` | `414cc9f6` | 0 | no | NO |  |
| `dotfiles.worktrees/devcontainer-cap-20261002` | `feat/devcontainer-cap` | `f9e8c56a` | 0 | no | NO |  |
| `dotfiles.worktrees/doctor-fnox-provider-20261002` | `feat/doctor-fnox-provider-live` | `00567df4` | 0 | no | NO |  |
| `dotfiles.worktrees/handoff-20261002` | `docs/handoff-2026-10-02` | `b3e06cbd` | 0 | yes | yes |  |
| `dotfiles.worktrees/host-load-20261002` | `fix/host-load` | `3740cceb` | 0 | no | yes |  |
| `dotfiles.worktrees/lane-A-20261002` | `feat/ask-quality-v2` | `80b0fc36` | 0 | no | NO |  |
| `dotfiles.worktrees/lane-B-20261002` | `feat/handoff-check-stale-prose` | `ff806911` | 0 | no | NO |  |
| `dotfiles.worktrees/lane-C-20261002` | `fix/research-sweep-1471-1514` | `32de7c14` | 0 | no | NO |  |
| `dotfiles.worktrees/lane-completion-20261002` | `docs/lane-completion-protocol` | `1dcf0d4b` | 0 | yes | yes |  |
| `dotfiles.worktrees/lane-E-20261002` | `feat/gate-run-multi-name` | `90c9c96d` | 0 | no | NO |  |
| `dotfiles.worktrees/lane-G-20261002` | `(detached)` | `60fc34ce` | 0 | no | NO |  |
| `dotfiles.worktrees/lock-format-upgrade-20261002` | `chore/lock-format-upgrade` | `6ecd558e` | 0 | no | NO |  |
| `dotfiles.worktrees/model-registry-20261002` | `feat/model-registry` | `3740cceb` | ⚠ 9 | no | yes |  |
| `dotfiles.worktrees/project-sync-readiness-20260928` | `codex/dotfiles-project-sync-readiness` | `7a636974` | 0 | no | NO |  |
| `dotfiles.worktrees/s29-00b-finish-20261001` | `fix/s29-00b-bot-pr-regenerate` | `374611bc` | ⚠ 1 | no | NO |  |
| `dotfiles.worktrees/session-audit-20260930` | `docs/session-audit-2026-09-30` | `ce3ab0b5` | 0 | yes | yes |  |
| `dotfiles.worktrees/session-audit-20261001-000` | `docs/session-audit-20261001-000` | `b8f30cb2` | 0 | no | NO |  |
| `dotfiles.worktrees/session-audit-20261001-s29` | `docs/session-audit-20261001-s29` | `d8a0f96b` | 0 | no | NO |  |
| `dotfiles.worktrees/session-docs-20261001` | `docs/session-2026-10-01` | `985030ac` | 0 | no | NO |  |
| `dotfiles.worktrees/worktree-ergonomics-20261002` | `fix/worktree-ergonomics` | `0d785a61` | 0 | no | NO |  |
| `dotfiles.worktrees/worktree-orchestration-20260929` | `codex/worktree-orchestration-20260929` | `a530e488` | 0 | no | NO |  |
| `dotfiles/.claude/worktrees/agent-ac4032eba1703a858` | `feat/landing-pins` | `536ec7c1` | 0 | no | NO |  |
| `dotfiles/.claude/worktrees/codegen-default-group` | `(detached)` | `b1476967` | 0 | no | yes |  |

### knowledge-base (21 worktrees)

| Worktree | Branch | HEAD | Dirty files | On origin (branch) | HEAD on any remote | Locked |
|---|---|---|---|---|---|---|
| `knowledge-base` | `main` | `91a56a82` | ⚠ 3 | yes | yes |  |
| `knowledge-base.worktrees/agentsview-kb-source-refresh` | `codex/agentsview-kb-source-refresh` | `e8fe42ae` | ⚠ 5 | no | yes |  |
| `knowledge-base.worktrees/cli-cold-review-d5-20260928` | `(detached)` | `c7917fda` | ⚠ 1 | no | yes |  |
| `knowledge-base.worktrees/cli-final-main-20260927` | `codex/cli-final-main-20260927` | `c7917fda` | ⚠ 4 | yes | yes |  |
| `knowledge-base.worktrees/cli-maintenance-20260922` | `codex/cli-maintenance-20260922` | `d6e85475` | 0 | no | NO |  |
| `knowledge-base.worktrees/cli-parity-9fa-20260925` | `codex/cli-parity-9fa-20260925` | `365cd80f` | ⚠ 30 | yes | yes |  |
| `knowledge-base.worktrees/cli-review-arms-bb95-20260927` | `(detached)` | `bb95ae78` | ⚠ 2 | no | yes |  |
| `knowledge-base.worktrees/codex-0155-alignment-20260918` | `codex/codex-0155-alignment-20260918` | `e8fe42ae` | ⚠ 2 | no | yes |  |
| `knowledge-base.worktrees/graphify-claude-handoff-20260928` | `codex/graphify-claude-handoff-20260928` | `75e571a2` | 0 | yes | yes |  |
| `knowledge-base.worktrees/graphify-claude-handoff-docs-20260929` | `codex/graphify-claude-handoff-docs-20260929` | `4de9ed91` | 0 | no | NO |  |
| `knowledge-base.worktrees/issue-1-cli-delivery-d2` | `codex/issue-1-cli-delivery-d2` | `e8fe42ae` | ⚠ 26 | no | yes |  |
| `knowledge-base.worktrees/issue-1-cli-integration` | `codex/issue-1-kb-cli-integration` | `c1cf2933` | ⚠ 25 | no | yes |  |
| `knowledge-base.worktrees/kb-838-20261002` | `fix/kb-838-test-gate-xdist` | `165fc872` | ⚠ 3 | no | NO |  |
| `knowledge-base.worktrees/kb-project-sync-v0971-20260928` | `codex/kb-project-sync-v0971` | `1d9fc7db` | 0 | no | NO |  |
| `knowledge-base.worktrees/lane-KB2-20261002` | `feat/kb-829-corpus-refresh` | `52babb73` | 0 | no | NO |  |
| `knowledge-base.worktrees/lane-KB3-20261002` | `feat/kb-826-currency-engine` | `2dadc35c` | 0 | yes | yes |  |
| `knowledge-base.worktrees/live-receipt-scope-20261001` | `fix/live-receipt-scope-tool-pins` | `aa6ee9f5` | 0 | no | NO |  |
| `knowledge-base.worktrees/mod-runtime-auth-20261001` | `fix/mod-runtime-check-2-1-287-auth` | `acaccfd0` | 0 | no | NO |  |
| `knowledge-base.worktrees/model-registry-20261002` | `feat/model-registry` | `91a56a82` | 0 | no | yes |  |
| `knowledge-base.worktrees/session-audit-20261001-000` | `docs/session-audit-20261001-000` | `d1eb60f6` | 0 | no | NO |  |
| `knowledge-base.worktrees/session-audit-20261001-s29` | `docs/session-audit-20261001-s29` | `6a950736` | 0 | no | NO |  |

## Appendix — the 2026-10-01 inventory, verbatim

Written by the `worktree-inventory` subagent of session 7133045d into its scratchpad (`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7133045d-9086-4a3f-8fa7-0a4df70f442a/scratchpad/worktree-inventory.md`, untracked);
promoted here unchanged. Its per-row recommendations (KEEP/REMOVE/salvage) predate the merges listed in
`docs/research/kb/reports/agents/session-audit-process-compliance-2026-10-01c.md`; use the live snapshot above for state.

### Worktree inventory — 2026-10-01 (read-only, nothing changed)

Method: `git worktree list --porcelain` for both repos after `git fetch origin main`; per worktree:
`merge-base --is-ancestor HEAD origin/main`, `rev-list --count origin/<br>..HEAD` (or vs main when the
remote branch is absent), `branch -r --contains HEAD`, `gh pr list --head <br> --state all` plus a
`gh pr list --search <sha>` cross-check, `status --porcelain`, pins grepped from `mise.toml` +
`.config/mise/conf.d/shared.toml`, and live cwds from `ps` + `lsof -a -p <pid> -d cwd` for
claude/codex/mise/node/hk/uv/python processes.
Control arms: `branch -r --contains origin/main~3` → origin/main (probe sees remotes);
`cat-file -e origin/main:AGENTS.md` → present (absence probe can see).
"content on main" = the branch's changed files are byte-identical on origin/main (squash-merge proxy).

Legend: removing a worktree never deletes its branch; a clean worktree whose HEAD is on a remote loses nothing.
⚠ = dirty or unpushed — do not remove without a salvage decision.

## dotfiles (19 worktrees)

| Worktree | Branch | HEAD | Merged / PR | Dirty | Unpushed | Last commit | Stale pins | Live proc | Rec |
|---|---|---|---|---|---|---|---|---|---|
| dotfiles (main checkout) | main | 4ba69bb7 | — | 0 | 0 | 2026-10-02 | npm codex 0.154.0 (hk 2.3.0) | YES (land 1510, dev-rebuild, claude sessions) | KEEP |
| ~/.codex/worktrees/3f4c/dotfiles | codex/graphify-0-9-67 | eb9a8c16 | HEAD ⊂ main; no PR; no remote branch | ⚠14 (graphify stamps, receipt 0.9.66 — that receipt is now on main) | 0 commits | 2026-09-23 | agy 1.2.8, npm codex, **hk 1.57.0** | no | REMOVE after confirming the dirty graphify stamps are superseded (likely) |
| agent-shell-env-20260930 | fix/agent-shell-mise-hookenv | f08cd0a9 | HEAD = main's #1468; no PR; no remote | ⚠12 staged-but-uncommitted (settings.json, spec `agent-shell-mise-hookenv-2026-09-30.md` + 2 reports — ABSENT from main) | 0 commits | 2026-09-30 | agy 1.2.14, npm codex | no | ⚠ UNSAVED WORK — commit+rebase onto main and ship, or explicitly abandon |
| agent-team-research-skill | codex/agent-team-research-skill | 237092de | **#1415 MERGED**; content on main | 0 | 0 | 2026-09-27 | agy 1.2.12, npm codex | no | REMOVE |
| agentsview-managed-service | codex/agentsview-managed-service | e0f58cea | HEAD ⊂ main; no PR; no remote | ⚠8 (mise.toml/lock, codec.py, main.py + 4 untracked) | 0 commits | 2026-09-15 | agy 1.2.3, claude-code 2.1.270, npm codex, **hk 1.57.0** | no | ⚠ likely abandoned in favour of agentsview-native-service; salvage-check then REMOVE |
| agentsview-native-service | codex/agentsview-native-service | 36537951 | **#1141 OPEN**; **LOCKED** ("Live AgentsView global mise tasks reference this worktree") | ⚠6 | 0 | 2026-09-15 | agy 1.2.3, claude-code 2.1.270, npm codex, **hk 1.57.0** | no | KEEP (locked) — REBASE if #1141 is still wanted; migrate global task refs before any removal |
| agy-native-20260930 | feat/native-cli-installers-workflow | 102ee0c5 | not merged; **no PR**; pushed (origin branch exists) | 0 | 0 | 2026-09-30 | agy 1.2.14, npm codex | no | Worktree REMOVE is lossless (pushed). Branch: 2 commits / 803 files (docs mirror) unlanded — decide if superseded by #1505 / native-cli-devcontainer |
| native-cli-devcontainer-20261001 | feat/native-cli-devcontainer | ffa53833 | not merged; no PR yet; pushed | 0 | 0 | 2026-10-01 | none (hk 2.3.0) | **YES** (pid 49767 claude bg-spare, 66379 node) | KEEP (live) |
| native-only-doctor-20261001 | feat/native-only-doctor-check | c23df269 | no PR; no remote | 0 | ⚠2 | 2026-10-01 | npm codex 0.154.0 | not seen | KEEP (live session per lead) |
| plugin-health-builtin-20261001 | fix/plugin-health-builtin | fb131231 | no PR; no remote | 0 | ⚠2 | 2026-10-01 | npm codex 0.154.0 | not seen | KEEP (live session per lead) |
| project-sync-readiness-20260928 | codex/dotfiles-project-sync-readiness | 7a636974 | no PR; no remote; not on main (13 files differ) | 0 | ⚠2 | 2026-09-28 | agy 1.2.12, npm codex | no | ⚠ unpushed — REBASE+ship or push-then-abandon; do not remove as-is |
| research-enforcement-20260930 | (detached) | 836983e3 | **#1475 MERGED** (sha matched); on origin/feat/research-enforcement | 0 | 0 | 2026-09-30 | agy 1.2.14 | no | REMOVE |
| research-five-source-gate | (detached) | 2d763acb | HEAD ⊂ main | 0 | 0 | 2026-09-28 | agy 1.2.12 | no | REMOVE |
| s29-00b-finish-20261001 | fix/s29-00b-bot-pr-regenerate | d0a6cb57 | no PR; no remote | ⚠5 untracked review reports (round-e code/cold/spec/standards) | ⚠8 | 2026-10-01 | npm codex 0.154.0 | not seen | KEEP (live session per lead) |
| session-audit-20260930 | docs/session-audit-2026-09-30 | ce3ab0b5 | not merged; **no PR**; pushed | 0 | 0 | 2026-09-30 | agy 1.2.14, npm codex | no | Worktree REMOVE is lossless (pushed); branch has 16 unlanded docs files — ship or abandon |
| session-docs-20261001 | docs/session-2026-10-01 | 2dfb8030 | no PR; no remote | 0 | ⚠1 (29 files) | 2026-10-01 | agy 1.2.14, npm codex | not seen | KEEP — today's session docs, unpushed; likely another live lane's; rebase to drop agy pin before shipping |
| worktree-orchestration-20260929 | codex/worktree-orchestration-20260929 | a530e488 | no PR; no remote | 0 | ⚠1 (2 files) | 2026-09-29 | agy 1.2.12, npm codex | no | ⚠ unpushed — REBASE+ship or abandon |
| .claude/worktrees/agent-a6e5728e… | research/codex-exec-review-settings | 3c2a2134 | no PR; no remote; **its 1 changed file is byte-identical on main** (folded in, cf. #1320) | 0 | 1 (content on main) | 2026-09-23 | agy 1.2.8, **hk 1.57.0** | no | REMOVE (lossless) |
| .claude/worktrees/agent-a82a7019… | research/hk-2-0-impact | a324de6d | same — 1 file, byte-identical on main | 0 | 1 (content on main) | 2026-09-23 | agy 1.2.8, **hk 1.57.0** | no | REMOVE (lossless) |

## knowledge-base (29 worktrees)

| Worktree | Branch | HEAD | Merged / PR | Dirty | Unpushed | Last commit | Stale pins | Live proc | Rec |
|---|---|---|---|---|---|---|---|---|---|
| knowledge-base (main checkout) | main | 91a56a82 | — | ⚠3 (.codex/config.toml M; 2 untracked cclint report dirs) | 0 | 2026-10-01 | none (hk 2.4.0) | YES (biome/node) | KEEP |
| scratchpad …/6723f026…/wt-dag-gate | feat/dag-gate | ab9b3493 | not merged; **prunable** (dir gone) | n/a | n/a | — | n/a | no | PRUNE (`git worktree prune`; ref survives) |
| scratchpad …/6723f026…/wt-round-close | docs/round-close-2026-09-12 | b7a1865e | **prunable** | n/a | n/a | — | n/a | no | PRUNE |
| scratchpad …/f95d5234…/wt-lychee | fix/lychee-offline-checks-nothing | 3f5d8ef1 | **prunable** | n/a | n/a | — | n/a | no | PRUNE |
| ~/.codex/visualizations/…/diagnostic-clean-091 | (detached) | 091dee4f | on origin/codex/cli-final-main-20260927 | 0 | 0 | 2026-09-27 | agy 1.2.11, npm codex | no | REMOVE |
| ~/.codex/visualizations/…/cold-review-worktree | (detached) | 0e165d64 | on origin/codex/cli-final-main + cli-parity-9fa | 0 | 0 | 2026-09-25 | agy 1.2.2, npm codex, **hk 1.57.0** | no | REMOVE |
| agentsview-kb-source-refresh | codex/agentsview-kb-source-refresh | e8fe42ae | HEAD ⊂ main; no PR; no remote | ⚠5 (cli.py, new source_materialize.py, mise.toml/lock) | 0 commits | 2026-09-15 | agy 1.2.2, npm codex 0.155.1, **hk 1.57.0** | no | ⚠ uncommitted code — salvage-check, then REMOVE |
| agy-native-only-20261001 | chore/agy-native-only | 6faa47e7 | **#831 MERGED** | 0 | 0 | 2026-10-01 | **hk 1.57.0** (branch predates hk bump) | no | REMOVE |
| cli-cold-review-d5-20260928 | (detached) | c7917fda | on origin/codex/cli-final-main-20260927 | 1 untracked `SKILL.md.bak` | 0 | 2026-09-28 | agy 1.2.12, npm codex 0.157.1 | no | REMOVE (only a .bak) |
| cli-final-main-20260927 | codex/cli-final-main-20260927 | c7917fda | **#822 OPEN** | ⚠4 (currency docs + run report + .bak) | 0 | 2026-09-28 | agy 1.2.12, npm codex 0.157.1 | no | KEEP/REBASE (open PR; stale agy/codex pins) |
| cli-maintenance-20260922 | codex/cli-maintenance-20260922 | d6e85475 | no PR; no remote; **no remote branch contains it** | 0 | ⚠8 | 2026-09-24 | agy 1.2.2, npm codex, **hk 1.57.0** | no | ⚠ unpushed, likely superseded by #822 lineage — confirm, then push-or-abandon |
| cli-maintenance-51237d45-20260924 | codex/cli-maintenance-51237d45-20260924 | 9fa306b7 | contained in #822 / #813 branches | 0 | 0 effective (on remotes) | 2026-09-24 | agy 1.2.2, **hk 1.57.0** | no | REMOVE |
| cli-maintenance-93c019a5-20260924 | codex/cli-maintenance-93c019a5-20260924 | 630c2d7b | contained in #822 / #813 branches | 0 | 0 effective | 2026-09-24 | agy 1.2.2, **hk 1.57.0** | no | REMOVE |
| cli-parity-9fa-20260925 | codex/cli-parity-9fa-20260925 | 365cd80f | **#813 OPEN** | ⚠30 | ⚠3 | 2026-09-25 | agy 1.2.2, npm codex | no | ⚠ KEEP — dirty+unpushed; likely superseded by #822, owner decision |
| cli-review-arms-bb95-20260927 | (detached) | bb95ae78 | on origin/codex/cli-final-main-20260927 | ⚠2 (mise.lock M, stderr.txt) | 0 | 2026-09-27 | agy 1.2.12, npm codex 0.157.1 | no | REMOVE (dirt is a lock churn + stderr capture; glance first) |
| cli-signer-074b024-20260927 | (detached) | c7917fda | on origin/codex/cli-final-main-20260927 | 0 | 0 | 2026-09-28 | agy 1.2.12, npm codex 0.157.1 | no | REMOVE |
| cli-v0971-integration-20260928 | codex/cli-v0971-integration-20260928 | 869de7b1 | contained in origin/codex/cli-final-main (#822) | 0 | 0 effective | 2026-09-28 | agy 1.2.12, npm codex 0.157.1 | no | REMOVE |
| codex-0155-alignment-20260918 | codex/codex-0155-alignment-20260918 | e8fe42ae | HEAD ⊂ main; no PR; no remote | ⚠2 (mise.toml/lock = codex 0.155.1 bump) | 0 commits | 2026-09-15 | agy 1.2.2, npm codex 0.155.1, **hk 1.57.0** | no | REMOVE (dirt is an obsolete npm-codex bump; codex is native-only now) — flagged dirty |
| graphify-claude-handoff-20260928 | codex/graphify-claude-handoff-20260928 | 75e571a2 | **#825 OPEN** | 0 | 0 | 2026-09-28 | agy 1.2.12, npm codex, **hk 1.57.0** | no | REBASE (open PR, stale pins) or close #825 |
| graphify-claude-handoff-docs-20260929 | codex/graphify-claude-handoff-docs-20260929 | 4de9ed91 | no PR; no remote | 0 | ⚠1 (13 files) | 2026-09-28 | agy 1.2.12, npm codex, **hk 1.57.0** | no | ⚠ unpushed — fold into #825 or abandon |
| graphify-live-bootstrap-20260927 | (detached) | a8b4ca4b | **#821 MERGED** (sha matched) | 0 | 0 | 2026-09-27 | agy 1.2.12, **hk 1.57.0** | no | REMOVE |
| graphify-live-evidence-d5-20260928 | codex/graphify-live-evidence-d5-20260928 | 296b9057 | no PR; contained in origin/graphify-live-evidence | 0 | 3 vs own remote, 0 effective | 2026-09-29 | agy 1.2.12, **hk 1.57.0** | no | REMOVE (content is on origin/graphify-live-evidence) |
| guard-codegen-flake-20261001 | fix/guard-codegen-xdist-flake | 0c2a82f2 | **#833 MERGED**; content on main | 0 | 0 | 2026-10-01 | **hk 1.57.0** | no | REMOVE |
| hk-latest-20261001 | chore/hk-2-latest | 626d7206 | **#832 MERGED**; `git cherry` = `-` (patch on main) | 0 | 1 (equivalent on main) | 2026-10-01 | none (hk 2.4.0) | no | REMOVE |
| issue-1-cli-delivery-d2 | codex/issue-1-cli-delivery-d2 | e8fe42ae | HEAD ⊂ main; no PR; no remote | ⚠26 (skills, graphify stamps, …) | 0 commits | 2026-09-15 | agy 1.2.2, npm codex 0.155.1, **hk 1.57.0** | no | ⚠ uncommitted — almost certainly superseded by #822 CLI work; salvage-check then REMOVE |
| issue-1-cli-integration | codex/issue-1-kb-cli-integration | c1cf2933 | HEAD ⊂ main; no PR; no remote | ⚠25 | 0 commits | 2026-09-13 | agy 1.2.2, npm codex 0.155.1, **hk 1.57.0** | no | ⚠ same as above |
| kb-project-sync-v0971-20260928 | codex/kb-project-sync-v0971 | 1d9fc7db | no PR; **no remote contains it** | 0 | ⚠70 vs main (68 unique patches) | 2026-09-29 | agy 1.2.12, npm codex 0.159.0 (hk 2.4.0) | no | ⚠ largest unpushed body of work — PUSH before anything; then REBASE or decide |
| live-receipt-scope-20261001 | fix/live-receipt-scope-tool-pins | aa6ee9f5 | no PR; no remote; #831's title names "#824 tool-pin scope narrowing" but 2/2 files still differ from main | 0 | ⚠1 | 2026-10-01 | agy 1.2.12, npm codex, **hk 1.57.0** | no | ⚠ probably folded into #831 in a different form — verify, then REMOVE |
| mod-runtime-auth-20261001 | fix/mod-runtime-check-2-1-287-auth | acaccfd0 | no PR; no remote; #831 title names "2.1.287 mod-runtime probe"; 1/5 files still differs | 0 | ⚠1 | 2026-10-01 | agy 1.2.12, npm codex, **hk 1.57.0** | no | ⚠ same — verify the 1 differing file, then REMOVE |

## Summary

- **Safe REMOVE now (clean, merged or content on a remote/main): dotfiles 5** — agent-team-research-skill,
  research-enforcement-20260930, research-five-source-gate, .claude/worktrees/agent-a6e5728e…, agent-a82a7019….
  **KB 13** — diagnostic-clean-091, cold-review-worktree, agy-native-only, cli-cold-review-d5 (.bak only),
  cli-maintenance-51237d45, cli-maintenance-93c019a5, cli-signer-074b024, cli-v0971-integration,
  graphify-live-bootstrap, graphify-live-evidence-d5, guard-codegen-flake, hk-latest, plus `git worktree prune`
  for the 3 prunable scratchpad entries.
- **Worktree removable but branch has unlanded pushed work (decide ship/abandon):** agy-native-20260930,
  session-audit-20260930.
- **⚠ Dirty, uncommitted, never pushed (salvage decision required):** dotfiles agent-shell-env-20260930
  (spec + reports not on main — highest value), agentsview-managed-service, ~/.codex/worktrees/3f4c;
  KB agentsview-kb-source-refresh, issue-1-cli-delivery-d2, issue-1-cli-integration,
  codex-0155-alignment, cli-review-arms-bb95.
- **⚠ Unpushed commits with no remote copy:** dotfiles project-sync-readiness (2), worktree-orchestration (1);
  KB kb-project-sync-v0971 (**70**), cli-maintenance-20260922 (8), graphify-claude-handoff-docs (1),
  live-receipt-scope (1), mod-runtime-auth (1).
- **KEEP:** both main checkouts; dotfiles native-cli-devcontainer (live process), s29-00b-finish,
  native-only-doctor, plugin-health-builtin, session-docs-20261001 (today, unpushed); agentsview-native-service
  (locked, #1141); KB cli-final-main (#822), cli-parity-9fa (#813, dirty+unpushed), graphify-claude-handoff (#825).
- **Stale pins:** hk 1.57.0 in 4 dotfiles + 17 KB worktrees; npm:@openai/codex in every non-live worktree and
  in dotfiles main itself (0.154.0); antigravity-cli in all pre-10-01 worktrees; claude-code 2.1.270 only in the
  two agentsview dotfiles worktrees. Live lanes s29-00b / native-only-doctor / plugin-health-builtin still carry
  npm codex 0.154.0 because dotfiles main does.
- Live cwd processes found only in: dotfiles main, KB main, native-cli-devcontainer. The three lead-named live
  lanes had no process with cwd inside them at probe time (the session may run with cwd elsewhere).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR state per worktree branch / sha
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — PR state per worktree branch / sha

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): worktree and remote-branch state.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): worktree and remote-branch state.
