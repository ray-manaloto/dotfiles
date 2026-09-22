# codex SDLC team review — graphify-currency skill at a36b5984 (2026-09-22)

Verbatim copy of `.agent/sdlc-runs/graphify-currency-skill-review-20260922/output.md` (run id `graphify-currency-skill-review-20260922`, review mode, xhigh, 1247s, settlement `completed`, 0 errors). Coordinator annotations marked `[coordinator]`.

---

# Review verdict

Commit `a36b59847dd73ad847565063d6e0bc3cf7192dcd` does not yet fully satisfy Ray’s automation requirement.

The core design is sound:

- All four mise tasks are thin, one-line Python callers.
- Python enforces update → skill refresh → graph rebuild sequentially.
- GitHub release lookup fails closed before uv mutation.
- `mise latest` is parsed from stdout only.
- Unverifiable latest versions produce drift and rc 1.
- `uv lock` structurally contains exactly one `graphifyy` package entry.

However, three automation-breaking gaps remain:

1. A version upgrade can refresh skills using installer metadata cached from the old Graphify release.
2. Renovate’s claimed Graphify lock-update route is disabled because `pep621` is absent from `enabledManagers`.
3. The workflow promises PATH-binary currency but has no task authorized to update the user-global mise pin.

The durable “zero-token” claim also exceeds what is proved: tests constrain repository-owned argv, but cannot prove that a future pre-1.0 Graphify release preserves the current no-LLM behavior of `graphify update`.

`★ Insight ─────────────────────────────────────`
Self-updating Python processes have two states: packages on disk and modules already loaded in memory. After `uv sync`, importing from the same cached module object can still apply the old release’s placement metadata to the new release’s files.
`─────────────────────────────────────────────────`

## `check-update` question

Recommendation: exclude `graphify check-update` from `graphify-check`.

It only tests whether `<path>/<GRAPHIFY_OUT>/needs_update` exists. It does not read the sentinel, inspect sources, compare hashes or commits, examine the graph, or check package currency. The CLI ignores the function’s Boolean result and always exits 0: [cli.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify/cli.py:2480>) and [watch.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify/watch.py:2226>).

The sentinel is produced by Graphify’s watch path for surviving non-code changes requiring semantic/LLM extraction. This repository’s supported rebuild is AST-only and prohibits watch mode. Adding it would therefore:

- Add no normal freshness or currency signal.
- Remain non-failing even when the sentinel exists.
- Recommend the semantic/LLM path this automation intentionally excludes.

## Antigravity question

Recommendation: do not adopt the vendor project-scoped Antigravity installation in this change.

`graphify install --project --platform antigravity` makes no `$HOME` writes. It manages:

- `.agents/skills/graphify/SKILL.md`
- `.agents/skills/graphify/.graphify_version`
- `.agents/skills/graphify/references/**`
- `.agents/rules/graphify.md`
- `.agents/workflows/graphify.md`
- Conditionally, `.agents/skills/graphify/SKILL.md.bak`

It also injects Antigravity frontmatter into the skill. See [install.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify/install.py:1627>).

The non-project installation is mixed-scope: it places the skill, stamp, and references under `$HOME/.gemini/config/skills/graphify/`, but still writes rules and workflows into the current project. It only prints the suggested `$HOME/.gemini/antigravity/mcp_config.json`; it does not write it.

Adoption is presently unsafe because:

- The vendor skill collides with the deliberate `.agents` stub at [.agents/skills/graphify/SKILL.md](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/graphify/SKILL.md:6>).
- The vendor rules prescribe bare `graphify query` and `graphify update .`, contradicting the mise-only policy in [graphify-first.md](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/graphify-first.md:11>).
- This diff contains no live evidence that `agy` consumes these Antigravity rule/workflow files.

If a later consumer probe establishes value, the repo-owned installer must manage all five project-local surfaces above, including references and injected frontmatter. A narrower alternative could retain the stub and add only rewritten `.agents/rules/graphify.md` and `.agents/workflows/graphify.md`, but that would be a separate repo-specific integration—not equivalent to the vendor installer.

## Verification commands for the operator

Run these directly, in order; no agent-authored Bash sequence is needed:

1. `mise run graphify-upgrade`

   Expected on a version move:

   - `graphifyy locked <old>, latest <new>`
   - `release notes -> .../.agent/graphify/release-notes-<new>.md`
   - `graphifyy lock updated to <new>; environment synced`
   - Skill refresh/current lines
   - Code rebuild output
   - `graphify-health: fresh ...`
   - Expected rc: 0

   When already current, expect `already current`, followed by skill reconciliation, rebuild, and fresh health.

2. `mise run graphify-check`

   Expected:

   - `graphifyy locked <version>, latest <same-version>`
   - `graphify currency current`
   - Expected rc: 0

   Any `UNVERIFIABLE` or `graphify drift [...]` line must produce rc 1.

3. `mise run graphify-health`

   Expected:

   - `graphify-health: fresh ...`
   - Expected rc: 0

For a routine source-only rebuild, the one operator command is:

```text
mise run graphify-rebuild
```

It should emit rebuild output followed by `graphify-health: fresh ...`, rc 0.

These commands expose the current gaps rather than proving universal success: step 2 can fail because the workflow did not update the user-global PATH binary, and step 1 can currently refresh skills using cached pre-upgrade installer metadata.

## Documentation findings

### P1 — PATH currency is promised but not established

The skill claims the workflow keeps the PATH binary current and requires `graphify-check` to return 0: [SKILL.md](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/graphify-currency/SKILL.md:3>) and [completion contract](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/graphify-currency/SKILL.md:83>).

The update task only changes the project uv lock/environment. When PATH differs, [graphify_currency.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify_currency.py:355>) tells the operator to update the user-global mise pin and returns drift. No sanctioned task performs that mutation.

Either make PATH currency explicitly advisory/out-of-scope or introduce a separately authorized operator task. It should not silently mutate user-global configuration.

### P1 — Linked evidence retains the retired unsafe rationale

[do-not.md](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/do-not.md:34>) bans project installation but links evidence that still describes `graphify install --project` as safe/project-only and names incorrect destinations: [docs/rules-evidence/do-not.md](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/rules-evidence/do-not.md:11>).

That is live authoritative evidence, not dated history, and could reauthorize the prohibited operation.

### P2 — Operator outputs and rc values are underspecified

The skill lists broad task effects but does not document the exact stable success lines and return codes available in code. Verification is also split between `graphify-check` and `graphify-health`, despite the request for one command per intent.

The static contract only protects the `## Zero-token boundary` heading, so removing the operator output contract has no realistic fail arm.

### P2 — Antigravity’s collision is missing from the warning

The vendor-installer warning names Claude, Codex, and generic Agents, but omits that Antigravity targets the same deliberate `.agents/skills/graphify/SKILL.md` path and installs incompatible bare-command rules.

### P2 — Skill changes can leave a manual residual

When managed skill bytes differ, the workflow can leave `SKILL.md.bak` and instruct the operator to inspect and remove it manually. That may be appropriate safety behavior, but the no-manual-command claim must state this exception or provide an automated reviewed disposition.

## Configuration findings

### P1 — Renovate’s Graphify update path is inert

[renovate.json](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/renovate.json:54>) describes lockfile maintenance as the update path, but [enabledManagers](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/renovate.json:205>) omits `pep621`.

Renovate identifies `pyproject.toml` and uv locks through that manager. Therefore:

- The `graphifyy` package rule cannot match this Python project.
- Global lockfile maintenance cannot reach `python/uv.lock`.
- The description is currently false.

Add `pep621` and a discriminating test using the real `python/pyproject.toml`/`python/uv.lock` pair. Its negative arm should demonstrate that removing `pep621` removes Graphify discovery.

### Confirmed configuration contracts

- The four mise tasks are one-line Python callers: [mise.toml](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:803>).
- `pin-parity.toml` matches one two-line `graphifyy` lock entry and three stamps exactly once.
- Every new `doctor.toml` Graphify key is consumed by [doctor.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doctor.py:1172>).
- `python/uv.lock` is the sole repository version pin; the pyproject declarations are intentionally loose.
- `.agent/graphify/` needs no additional ignore rule because [.gitignore](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.gitignore:124>) already ignores `.agent/`.

## Python findings

### P1 — Post-upgrade skill refresh can use old metadata

[graphify_skill.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify_skill.py:41>) imports and caches `graphify.install` before the nested uv update. The same process then runs `uv lock`, `uv sync`, and `_refresh_skills`: [graphify_currency.py](</Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify_currency.py:416>).

If the new release changes `skill_file`, `skill_refs`, or destination metadata, the workflow can combine new package bytes with the old in-memory `_PLATFORM_CONFIG` and still return 0.

Refresh skills in a fresh post-sync subprocess—or explicitly invalidate/reimport the vendor module—and verify the resulting surfaces from another fresh process. The fail arm should simulate a sync that changes both bytes and placement metadata.

### P1 — Zero-token behavior is not durable across future releases

For installed Graphify 0.9.65, `graphify update` currently performs a code-only rebuild. Repository tests also constrain invocation to exact approved argv.

But `graphify-upgrade` installs an arbitrary newer pre-1.0 release and immediately invokes its `graphify update`. Existing tests mock the subprocess boundary, so they remain green if the newly installed vendor command changes semantics and begins reaching an LLM.

Add a post-sync semantic contract probe or use a stable vendor code-only interface before claiming durable zero-token behavior.

### P2 — The receipt proves availability, not human review

The GitHub API lookup is correctly fail-closed and the receipt is written before uv mutation. However, the same invocation writes the receipt and immediately updates the lock.

Thus the implementation proves “receipt exists before mutation,” not “an operator reviewed and accepted the release.” Documentation should use the former wording unless an explicit approval boundary is added.

### P3 — Codex reference-sidecar test fixture is stale

The fixture models Codex as monolithic with no `skill_refs`, while installed Graphify declares a Codex references bundle. It therefore lacks a realistic fail arm for missing or corrupt `.codex/skills/graphify/references/**`.

### Confirmed Python contracts

- Invalid or empty `mise latest` stdout becomes unverifiable drift.
- Upgrade stops on update failure and only rebuilds after success.
- The lock parser structurally requires exactly one valid `graphifyy` package.
- GitHub failure leaves the lock untouched, creates no receipt directory, and invokes no uv command.
- Public parser/dispatcher tests preserve CLI return codes.
- Subprocess tests constrain repo-owned commands to `mise`, `gh`, `uv`, the version-only PATH probe, and the exact rebuild invocation.

## Review limitations

No repository gates, Graphify mutation tasks, installers, or LLM-reaching commands were run. The checkout was not modified.

The mandatory orientation command was attempted first:

```text
mise run graphify-query -- "<review question>"
```

It returned rc 1 because the read-only sandbox prevented mise from creating its log and temporary state (`Operation not permitted`). Findings were subsequently grounded in the immutable commit and installed package source.

Prior memory was used only to flag Graphify and Antigravity currency as non-routine areas; all substantive conclusions above were rechecked against the reviewed commit.

No others were spawned.

Specialists spawned:

- `sdlc-documentation-specialist` — `/root/documentation_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-python-specialist` — `/root/python_review`



## [coordinator] Disposition (2026-09-22)

All P1/P2 findings folded into respec round 1 (`spec-graphify-currency-respec1.md`) together with the Opus cold review F1-F8; overlaps: PATH currency == F4, Renovate inert == F3. `check-update`: EXCLUDED (always exits 0, sentinel only from the banned watch/LLM path). Antigravity `--project`: NOT adopted (collides with the deliberate .agents stub; vendor rules prescribe bare graphify; no evidence agy reads them) — recorded in the skill.

## GitHub repos touched

_None._
