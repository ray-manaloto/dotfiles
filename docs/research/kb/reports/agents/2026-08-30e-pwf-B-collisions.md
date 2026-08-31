# `planning-with-files` collision audit

Decision scope: the Claude Code plugin route for `pwf/` version 3.12.0 against
`dotfiles` branch `proto/bake-matrix-fields`. This is a static pre-install audit;
the plugin was not installed and none of its scripts were run.

Path labels below are `[pwf]` for the plugin checkout and `[dotfiles]` for the
target repository.

## Decision

**No package-file collision is caused by the proposed Claude plugin install.**
The plugin marketplace selects the plugin source root (`[pwf]
.claude-plugin/marketplace.json:8-14`). The target's verified loader model then
resolves an enabled plugin beneath
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>` (`[dotfiles]
python/src/dotfiles_setup/listing_budget.py:122-158`), not beneath the current
project. Consistently, the loader-facing hook descriptor calls a launcher below
`${CLAUDE_PLUGIN_ROOT}` (`[pwf] hooks/hooks.json:10-16`), and that launcher
resolves every runtime script below the same plugin root (`[pwf]
hooks/claude-hook.sh:12-20`). Therefore the checked-in `[pwf]
.agents/skills/planning-with-files/` mirror stays inside the cached plugin
package; it is not merged into `[dotfiles] .agents/skills/`. The plugin's
operational test keeps a synthetic cache root and project cwd separate, which
confirms runtime separation but is not used as installer-path proof (`[pwf]
tests/test_claude_plugin_operations.py:72-105`).

The adoption still creates **SERIOUS working-tree noise after use**: none of the
planning-state paths are ignored by the target. The default `/plan` creates
three root files (`[pwf] commands/plan.md:5-10`), and named/slug initialization
creates `.planning/<id>/` plus `.planning/.active_plan`
(`[pwf] scripts/init-session.sh:350-370`). These are user-visible project writes,
not installer writes.

## 1. `.agents/skills/`: no install collision — NON-ISSUE

- Plugin package cardinality at this surface: **1 skill directory**,
  `planning-with-files` (`[pwf]
  .agents/skills/planning-with-files/SKILL.md:1-4`); its Codex manifest also
  selects the package-relative `./.agents/skills/` root (`[pwf]
  .codex-plugin/plugin.json:11-12`). That Codex
  declaration is not a request to write into the current repository; the Claude
  route is rooted at `${CLAUDE_PLUGIN_ROOT}` as established above
  (`[pwf] hooks/claude-hook.sh:4-20`).
- Target cardinality: **3 existing directories**:
  `codex-task-orchestration`, `graphify`, and `session-review` (`[dotfiles]
  .agents/skills/codex-task-orchestration/SKILL.md:1-4`, `[dotfiles]
  .agents/skills/graphify/SKILL.md:1-4`, `[dotfiles]
  .agents/skills/session-review/SKILL.md:1-4`). The parity gate is path-specific:
  it tests the session-review twin and compares only those two exact files
  (`[dotfiles] hk.pkl:631-635`). Adding a fourth sibling would not by itself
  violate this predicate.
- Actual landing: **0 paths under the target `.agents/` tree**. Fine: there is no
  overwrite, merge, or parity-check effect from the Claude plugin install. The
  target's load-path implementation names the cache path explicitly (`[dotfiles]
  python/src/dotfiles_setup/listing_budget.py:149-158`).

  Control arm for that negative: the same `rg` shape over the plugin's Claude
  install surfaces (`.claude-plugin/`, `hooks/`, and `commands/`) found **0**
  `.agents/skills` references, while the known-present `CLAUDE_PLUGIN_ROOT`
  term produced **16 hits in 9 files**. Representative positives are the hook
  descriptor and command dispatcher (`[pwf] hooks/hooks.json:10-16`, `[pwf]
  commands/plan-attest.md:15-18`). The separate Codex manifest is also a
  positive control for the literal `.agents/skills` path (`[pwf]
  .codex-plugin/plugin.json:11-12`).

## 2. Command names: zero exact target collisions — NON-ISSUE

The plugin registers **13 commands** (one file per command):

1. `/plan-ar` — `[pwf] commands/plan-ar.md:1-3`
2. `/plan-attest` — `[pwf] commands/plan-attest.md:1-5`
3. `/plan-de` — `[pwf] commands/plan-de.md:1-3`
4. `/plan-doctor` — `[pwf] commands/plan-doctor.md:1-5`
5. `/plan-es` — `[pwf] commands/plan-es.md:1-3`
6. `/plan-goal` — `[pwf] commands/plan-goal.md:1-5`
7. `/plan-loop` — `[pwf] commands/plan-loop.md:1-5`
8. `/plan-zh` — `[pwf] commands/plan-zh.md:1-3`
9. `/plan-zht` — `[pwf] commands/plan-zht.md:1-3`
10. `/plan` — `[pwf] commands/plan.md:1-5`
11. `/pwf` — `[pwf] commands/pwf.md:1-5`
12. `/start` — `[pwf] commands/start.md:1-6`
13. `/status` — `[pwf] commands/status.md:1-5`

Cross-check cardinalities and result:

- **0 target command files** under `.claude/commands/`. Negative probe:
  `git ls-files '.claude/commands/**'` returned 0; the same-shape positive arms
  returned **31** `.claude/skills/*/SKILL.md` files and **4**
  `.claude/agents/*.md` files. The positive surfaces declare names in their
  frontmatter (for example `[dotfiles] .claude/skills/adversarial-review/SKILL.md:1-3`,
  `[dotfiles] .claude/skills/uv-project-vs-directory-expertise/SKILL.md:1-3`,
  `[dotfiles] .claude/agents/adversarial-critic.md:1-4`, and
  `[dotfiles] .claude/agents/staleness-auditor.md:1-4`).
- Exact intersection of the 13 plugin filenames with the **31 target skill
  names is 0**; exact intersection with the **4 target custom-agent names is
  also 0**. The target names are authoritative frontmatter values, not inferred
  display labels (`[dotfiles] .claude/skills/session-review/SKILL.md:1-3`;
  `[dotfiles] .claude/agents/claude-code-expert.md:1-4`).
- **One near-collision, not a namespace collision:** `/plan` is a slash command,
  while `Plan` is a built-in one-shot agent type. The target's harness audit
  explicitly identifies built-in Explore and Plan as agents
  (`[dotfiles] docs/research/kb/reports/agents/claude-code-expert-orchestration.md:201-207`).
  The plugin command invokes the `planning-with-files` skill instead
  (`[pwf] commands/plan.md:5-10`). Users can confuse the words, but one does not
  shadow the other.

## 3. Gate matrix

The actual Claude plugin landing is the cache, so **0 plugin package files are
inputs to target hk**. The table keeps that actual result separate from a
hypothetical manual/project copy.

| hk step | Hypothetical failure if package files were copied into the matching target surface | Actual Claude-plugin landing | Rating |
|---|---|---|---|
| `bash_logic_budget` | **Yes** for a root overlay into `scripts/`: the plugin has 12 top-level `.sh` files (11 are enumerated in its dual-shipping contract and the twelfth is `check-continue.sh`: `[pwf] tests/test_script_location_parity.py:28-53`, `[pwf] scripts/check-continue.sh:1-5`), while the gate covers `scripts/*.sh` and `.devcontainer/scripts/*.sh` (`[dotfiles] hk.pkl:238-249`); every new in-scope script without an allowlist entry fails (`[dotfiles] python/src/dotfiles_setup/bash_budget.py:14-22`). A vendored copy under `plugins/**` is explicitly out of scope (`[dotfiles] python/src/dotfiles_setup/bash_budget.py:4-12`). | Cache; **0 target `scripts/*.sh`**. | NON-ISSUE actual; SERIOUS for a root overlay. |
| `no_lint_skip` | **Yes** for a root overlay or a copy under `plugins/`: its predicate scans Python under `tests/` and `plugins/` and rejects the listed suppression tokens (`[dotfiles] hk.pkl:108-126`). The plugin has **4** matching `# noqa` sites (`[pwf] tests/test_cursor_nested_root_isolation.py:51-57`, `[pwf] tests/test_skill_frontmatter_valid.py:87`, `[pwf] tests/test_skill_hook_dispatch_parity.py:278`). | Cache; **0 scanned target Python files**. | NON-ISSUE actual; SERIOUS for a source copy. |
| `claude_md_import_stub` | **No plugin-file input in the actual route.** A hypothetical nested vendor copy contains no `CLAUDE.md`, so this check has nothing new to test; its scanner considers tracked `CLAUDE.md` except `.claude/**` and accepts one `@AGENTS.md` plus blanks/comments (`[dotfiles] scripts/check-claude-md-stub.sh:6-16`, `[dotfiles] scripts/check-claude-md-stub.sh:45-55`). | Cache; **0 target `CLAUDE.md` writes**. | NON-ISSUE. |
| `claude_agents_md_pairs` | **Yes** only for a hypothetical nested full-source copy: the plugin has a lone root `AGENTS.md` (`[pwf] AGENTS.md:1-3`) and no sibling `CLAUDE.md`, while the gate requires both directions for every tracked pair outside `.claude/**` (`[dotfiles] scripts/check-claude-agents-md-pairs.sh:7-17`, `[dotfiles] scripts/check-claude-agents-md-pairs.sh:37-43`). A root overlay would instead collide with the target's existing root pair, which is not the plugin-install route. | Cache; **0 new target pair inputs**. | NON-ISSUE actual; SERIOUS for nested vendoring. |
| `md_size_budget` | **No** for the literal `.agents/skills/` mirror: that path is outside the gate's enumerated inputs. **Yes** for a hypothetical standalone copy at `.claude/skills/planning-with-files/SKILL.md`: the target gives Claude skills 500 lines / 32,000 bytes (`[dotfiles] .claude/rules/md-size-budgets.md:88-109`, `[dotfiles] .claude/rules/md-size-budgets.md:174-177`), while the canonical plugin skill is 499 lines but 34,250 bytes and therefore exceeds the byte backstop (content begins at `[pwf] skills/planning-with-files/SKILL.md:1-5` and ends at `[pwf] skills/planning-with-files/SKILL.md:499`). | Cache; **0 tracked target instruction files**. | NON-ISSUE actual and for `.agents/`; SERIOUS for a `.claude/skills` copy. |
| `no_env_dump` | **No known failure.** The gate has no path glob and scans every tracked file (`[dotfiles] hk.pkl:300-308`), but its actual predicate requires a literal credential form, a `__MISE_DIFF` opaque assignment, or compressed text naming at least two secret variables (`[dotfiles] python/src/dotfiles_setup/env_blob_scan.py:78-115`, `[dotfiles] python/src/dotfiles_setup/env_blob_scan.py:158-199`). Static inspection found none in plugin runtime/package files. | Cache; **0 tracked target package files**. Planning markdown would be checked only if later tracked. | NON-ISSUE. |

The important separation is that the plugin cache is not the repository, while
planning state created after invocation is the repository working directory
(`[pwf] skills/planning-with-files/SKILL.md:65-85`).

Control arm for the last row: the target's real scanner was applied read-only to
all git-tracked plugin files and returned **0 findings**. Its positive fixture
feeds the same scanner a named compressed `__MISE_DIFF` and expects an
`env-dump-blob`; the bare-blob arm expects `compressed-env-dump`
(`[dotfiles] tests/test_env_blob_scan.py:43-60`). Thus the zero is a supported
negative, not a token grep that cannot recognize compressed payloads.

Control arm for the pair row: `git ls-files 'CLAUDE.md'` in the plugin returned
**0**, while the same-shape `git ls-files 'AGENTS.md'` returned **1**; that
positive is the root file cited in the row (`[pwf] AGENTS.md:1-3`).

## 4. Instruction-file writes — automatic path NON-ISSUE; documented manual tip SERIOUS

**Automatic behavior: 0 writes or appends to `AGENTS.md` or `CLAUDE.md`.** A
write-operator search across plugin runtime/package code for either filename
returned 0. The same expression found **31** planning-file writer sites, so the
search could fire; examples are the three PowerShell `Out-File` writes
(`[pwf] scripts/init-session.ps1:102-184`) and the POSIX template copies
(`[pwf] scripts/init-session.sh:310-344`). Direct behavior agrees: the canonical
skill declares only planning files as project writes (`[pwf]
skills/planning-with-files/SKILL.md:65-85`), and the plugin hook launcher only
reads/resolves them or emits messages (`[pwf] hooks/claude-hook.sh:48-63`,
`[pwf] hooks/claude-hook.sh:100-126`).

Control-arm details: the bounded search covered plugin command, hook, script,
skill, Codex, Pi, Hermes, and Copilot-hook runtime surfaces. A broad follow-up
over all non-doc/non-test package code likewise found **0 instruction-file
writer hits versus 31 planning-file writer hits**. This is stronger than merely
not seeing an installer mention.

The target premise needs one correction from primary code. Its root
`CLAUDE.md` is **8 lines / 324 bytes**, not byte-exactly one line: it has the
single `@AGENTS.md` import followed by one HTML comment (`[dotfiles]
CLAUDE.md:1-8`). That is valid because the actual gate permits optional blanks
and HTML comments and rejects every other non-comment payload (`[dotfiles]
scripts/check-claude-md-stub.sh:6-16`, `[dotfiles]
scripts/check-claude-md-stub.sh:41-55`). The root `AGENTS.md` measurement is
193 lines / 11,875 bytes (`[dotfiles] AGENTS.md:1-193`), leaving the stated 125
bytes under the separate 12,000-character AGM-003 ceiling (`[dotfiles]
.claude/rules/md-size-budgets.md:98-105`). Since the plugin writes neither file,
those limits do not move.

There is nevertheless a **manual adoption footgun**: the plugin installation
guide recommends adding an ordinary instruction line to the project's
`CLAUDE.md` (`[pwf] docs/installation.md:39-47`). If followed here, that line is
non-comment content in addition to `@AGENTS.md`, so
`claude_md_import_stub` would fail (`[dotfiles]
scripts/check-claude-md-stub.sh:41-55`). A troubleshooting alternative goes
further and recommends creating a contentful root `CLAUDE.md` (`[pwf]
docs/troubleshooting.md:54-61`), which would also violate the same target gate.
These are not installer mutations, but the operator must **not follow either
instruction in this repo**. Rating: SERIOUS documentation/repo collision, not an
automatic-install BLOCKER.

## 5. `.gitignore` and status impact — SERIOUS

The ignore intersection is **0 of 5 requested names**. Read-only
`git check-ignore` returned no match for `task_plan.md`, `findings.md`,
`progress.md`, `.planning/`, or `.active_plan`. Same-shape positive controls
returned the target's `.agent/`, `.claude/settings.local.json`, and
`graphify-out/` rules (`[dotfiles] .gitignore:36-50`, `[dotfiles]
.gitignore:63-87`), proving the check was operating in the correct repository.

Actual producer paths require one correction:

- Default `/plan` creates **3 untracked top-level files**:
  `task_plan.md`, `findings.md`, and `progress.md` (`[pwf]
  commands/plan.md:5-10`).
- Named/slug initialization creates **1 untracked top-level directory**,
  `.planning/`; the three markdown files live under its dated plan directory,
  and the pointer is `.planning/.active_plan` (`[pwf]
  scripts/init-session.sh:310-370`).
- Root `.active_plan` has **0 producer sites** in the actual initializer. It is
  also unignored if somebody creates it, but the plugin's path is the nested
  `.planning/.active_plan` (`[pwf] scripts/resolve-plan-dir.sh:18-47`).

  Control arm: a fixed-string writer probe over the initializer and resolver
  found **0** `> ".active_plan"` sites, while the same-shape nested probe found
  **1** `> "${PLAN_ROOT}/.active_plan"` writer (`[pwf]
  scripts/init-session.sh:369`).

Therefore the union of actual top-level untracked paths across legacy and slug
**default modes** has cardinality **4**: the three root markdown files plus `.planning/`.
No path in that set is currently tracked, and none is covered by the target's
ignore file, whose agent-state entries instead point at `.agent/`
(`[dotfiles] .gitignore:39-50`, `[dotfiles] .gitignore:75-87`).

Autonomous or gated initialization expands the set. The initializer additionally
writes `.stop_blocks`, `.nonce`, and `.mode`, then invokes attestation (`[pwf]
scripts/init-session.sh:151-183`); attestation writes `.plan-attestation` in
legacy mode or `.attestation` inside the active slug directory (`[pwf]
scripts/attest-plan.sh:40-48`). Thus a fresh legacy autonomous/gated session has
**7 top-level files**, while a fresh slug session has **8 files beneath
`.planning/`**: the pointer, three markdown files, and four marker files. The
command exposes those modes only when requested (`[pwf] commands/pwf.md:7-14`).
The same `git check-ignore --no-index` probe found **0 ignored paths** among all
root and slug forms of these four marker names; its same-shape positive control,
`.agent/notepad.md`, matched `[dotfiles] .gitignore:87`.

This is more than cosmetic noise. Target policy requires local agent work under
`.agent/` and durable artifacts under `docs/`, and expressly forbids ad-hoc
directories (`[dotfiles] .claude/rules/agent-artifact-conventions.md:1-5`,
`[dotfiles] .claude/rules/agent-artifact-conventions.md:61-73`). The plugin's
default root files and `.planning/` violate that convention as written. Also,
the repo explicitly forbids bulk `git add .` because state files have been
staged accidentally before (`[dotfiles] .claude/rules/do-not.md:23-24`); these
new unignored paths increase exactly that staging hazard. Rating: **SERIOUS**;
installing is clean, but using the plugin without an explicit artifact-policy
decision dirties the repo and conflicts with a standing rule.

## GitHub repos touched

- `OthmanAdi/planning-with-files` — inspected read-only at
  `d5d35e6a2316459418e7381faa2682b2894d02c1`; origin is recorded in `[pwf]
  .git/config:8-13`. No source-tree modifications.
- `ray-manaloto/dotfiles` — inspected read-only on `proto/bake-matrix-fields` at
  `0a2271f2cba6f46528d0d557aa7632edb83ca74c`; origin is recorded in `[dotfiles]
  .git/config:8-13`. No source-tree modifications.
