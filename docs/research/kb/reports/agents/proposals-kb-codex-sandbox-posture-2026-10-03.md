# KB codex sandbox posture: proposals (2026-10-03)

Question: should knowledge-base (KB) codex lanes run with NO sandbox (`danger-full-access`), matching dotfiles?

## Provenance and limits (read first)

- **The codex-advisor call was NOT made.** Mid-run, the Bash tool began refusing every command with a "worktree-isolated session, cwd resolved to the shared checkout" error (`handoff-2026-10-03k`). Even a bare `pwd` was refused, so I could not shell out to `codex exec`.
- Everything below is therefore **my own reading of files**, via the Read tool. It is not a gpt-6.1-sol verdict. Per the lane rules I did not substitute reasoning for the failed codex call; treat this as research input, not as an advisor verdict. Re-run through the codex advisor once Bash works.
- Before Bash died I got exactly two results:
  - `mise exec -- codex --version` printed `codex-cli 0.160.0`.
  - `grep -n sandbox_mode ~/.codex/config.toml` printed line 6: `sandbox_mode = "danger-full-access"`. Only that key was read.
- **Not run (all would have been `--help`-style):** `codex exec --help`, `codex sandbox --help`, `gh issue view` for dotfiles #1039/#1142. Every runtime claim about 0.160.0 below is UNVERIFIED.
- **Source version skew:** the local codex clone is **rust-v0.154.0**, not 0.160.0 (`knowledge-base/sources/codex.manifest:54`, `Cargo.toml:152`). The offline vendor docs are the superseded `agent-harness-docs` corpus (pinned 2026-09-01, per the prior report row "task-named offline corpus is superseded"). The docs may lag 0.160.0.

## Verified facts, and where the premise needs correcting

1. **KB `do-not.md` #13 is real** (`knowledge-base/.claude/rules/do-not.md:~167-176`). It cites `permissions.rs:1792` and `:580-586` at rust-v0.152.1.
   - Those line numbers are stale at 0.154.0. In the 0.154.0 clone, `FileSystemSandboxPolicy::unrestricted()` is at `codex-rs/protocol/src/permissions.rs:605-609`. It has `kind: Unrestricted` and `entries: Vec::new()`.
   - `permissions.rs:1792` is now an unrelated `} else {` inside a permission-profile conversion.
   - The core claim holds: `DangerFullAccess` has an empty entry list.
   - `protocol.rs:1224-1231` says `DangerFullAccess` has full disk write. `:1245-1249` says `get_writable_roots_with_cwd` returns `Vec::new()` for it, so no read-only subpaths exist at all.
2. **The #13 wording mis-describes the mechanism.** `.git`/`.agents`/`.codex` read-only protection is a `workspace-write` feature, not a `ReadOnly` feature.
   - `protocol.rs:1120-1136`: `WritableRoot.read_only_subpaths` exists "to ensure ... `.codex`, `.git`, notably `.git/hooks` ... are not modified by the agent".
   - `protocol.rs:1313-1328`: those subpaths are computed per writable root, via `default_read_only_subpaths_for_writable_root`. I did not read that helper's body.
   - Documented at `agent-harness-docs/docs/codex/agent-approvals-security.md:177-185`:
     - `.git` is read-only, whether a directory or a file.
     - If `.git` is a `gitdir:` pointer file, the resolved git dir is also read-only.
     - `.agents` and `.codex` are read-only when they exist as directories.
     - Protection is recursive.
   - `ReadOnly` makes everything read-only. `danger-full-access` is simply "no sandbox", so nothing is protected, including `$HOME`, the network and other repos.
3. **KB #767 matches** (`gh issue view 767 -R ray-manaloto/knowledge-base`).
   - 13 of 150 rollouts with a `turn_context` ran at `danger-full-access`, all with cwd = KB.
   - Last occurrence 2026-09-09.
   - A later comment says no session ever changed sandbox mid-run.
   - #767 says "no existing gate could have caught any of them", because the check was prose-only.
4. **`~/.codex/config.toml:6` sets `sandbox_mode = "danger-full-access"` globally.** That key is a default only. It is not what KB lanes run at today.
   - `kb_setup/codex_run.py:100-101`: `kb-codex` ALWAYS passes `--sandbox`. It is `workspace-write` with `--write`, else `read-only`, unless `LaneSpec.sandbox_override` is set. I did not check whether the CLI exposes that override.
   - `codex_run.py:109-112`: for `workspace-write` it adds `--add-dir ~/Library/Caches`, and with `--network` it adds `-c sandbox_workspace_write.network_access=true`.
   - `codex_run.py:117`: it ALWAYS passes `--dangerously-bypass-hook-trust`.
   - `codex_run.py:490-511`: `codex review` has no `-s`, so `kb-codex` passes `-c sandbox_mode=...`.
     - A CLI `-c` is layer `SessionFlags` at precedence 30, above user config at 20 (`config/src/config_layer_source.rs:38-47`). This is the source's claim as quoted in that docstring; I did not open that source file.
     - The docstring says that without this, a review runs at `danger-full-access`, because of the user-level key.
   - So the KB#863 fix-1 lane via `kb-codex-implementer` (`.claude/agents/kb-codex-implementer.md:30-49`, `--write`, `--network` optional) runs `workspace-write` today.
   - The ruling "no sandbox" therefore means adding a new `danger-full-access` path to `kb-codex`. It is not the status quo.
5. **"Matching dotfiles" is not "no sandbox everywhere".**
   - dotfiles `ai-cli-invocation.md:~40` says `sdlc-team` passes no `-s`, so the machine's `danger-full-access` applies. It calls that "the approved posture", because `workspace-write` also cuts the network (#1039/#1142; not re-read).
   - The same paragraph says: "advisory wrappers keep `--sandbox read-only` — the only thing that stops them writing".
   - So dotfiles is already option (3): no sandbox for implementer and team lanes, read-only for advisory lanes.
   - Option (1) as literally worded would go further than dotfiles.
6. **Permission profiles cannot be used on this machine as-is.** `agent-harness-docs/docs/codex/permissions.md:7-12`: profiles do not compose with the older settings.
   - If `sandbox_mode` appears in ANY loaded config file, or `--sandbox` is passed, the profile is ignored.
   - `~/.codex/config.toml:6` sets `sandbox_mode`, so `default_permissions` would be silently ignored.
   - Workarounds are weak. `--ignore-user-config` exists, but openai/codex#49333 reports it also skips the project `.codex` layer (hooks and MCP servers). Deleting the user key is a user-level edit, and KB `do-not.md` #11 and the standing memory forbid that.
   - openai/codex#47464 is a related report: `-s read-only` is silently ignored when `requirements.toml` defines `allowed_permission_profiles`. These issues are reports, not verified behaviour.

## What codex protects, per mode

Evidence: docs at `agent-approvals-security.md:177-185`, `permissions.md:416-456`, and source at `protocol.rs:1200-1333`. Source is 0.154.0. Nothing was runtime-probed at 0.160.0.

| Mode | Filesystem writes | `.git` / `.codex` / `.agents` | Network | macOS enforcement |
|---|---|---|---|---|
| `read-only` | none anywhere. Full disk READ is allowed (`protocol.rs:1220-1222`). | n/a, nothing is writable | off unless `ReadOnly.network_access` is set | Seatbelt |
| `workspace-write`, no network | cwd, `/tmp`, `$TMPDIR`, plus `writable_roots` and `--add-dir` (`protocol.rs:1256-1311`) | read-only inside each writable root, recursively. `.git` is read-only even for a pointer file's resolved target. A missing `.codex` at cwd is also protected (`protect_missing_dot_codex`, `:1318-1320`). | off (default `false`) | Seatbelt. If the policy cannot be enforced, codex refuses to run (`permissions.md:442-444`). |
| `workspace-write` + `network_access=true` | same | same (network is independent of the filesystem rules) | full outbound | same |
| `danger-full-access` | everything the OS user can write | NOT protected, because there are no sandbox rules (`permissions.rs:605-609`) | full | none |

Consequences:
- Under `workspace-write` a lane cannot `git commit`, because it cannot write `.git`. In a git worktree the real git dir is outside cwd anyway. The "Commit: lane" option in the `kb-codex-implementer` spec (`:62-65`) is therefore impossible there. This is inferred from the docs and source, not probed.
- `--add-dir ~/Library/Caches` (needed so uv does not die with rc=2; `ai-cli-invocation.md:~60-70`) makes ALL of `~/Library/Caches` writable. That is broad. It is the main residual hole in option (2).
- Hooks are explicitly "a useful guardrail, not a complete enforcement boundary" (hooks doc, via the prior report row 254). They are not a substitute for a sandbox.

## The risk that decides it

Every KB lane passes `--dangerously-bypass-hook-trust` (`codex_run.py:117`). So any hook definition planted in `.codex/hooks.json`, `.codex/config.toml` or `.codex/rules` runs on the NEXT lane with no trust review. Likewise a planted `.git/hooks/*` runs the next time the coordinator runs git on the host, outside any sandbox. `.git`, `.codex` and `.agents` are exactly what `workspace-write` makes read-only and `danger-full-access` does not. The point of the protection is privilege persistence across lanes, not only "do not break git".

A lane at `danger-full-access` that is confused or prompt-injected (a fetched web page, an issue body) can hand its next run a trusted hook. That is the one risk that actually changes the decision.

## Options

### (1) No sandbox everywhere, as ruled
- PRO:
  - Zero friction: no uv-cache `--add-dir`, no network flag, `git commit` and ssh-agent/keychain all work. This matches the dotfiles "approved posture" for implementers.
  - One rule to remember.
- CON:
  - Advisory and review lanes become write-capable. The dotfiles doc says read-only is "the only thing that stops them writing".
  - `.codex`, `.git/hooks` and `.agents` are all open, combined with always-on bypass-hook-trust.
  - Re-creates the exact 13-session pattern #767 flagged, now as policy. #767 stresses that no runtime gate exists.
  - The `codex review` path would ride the user-level `sandbox_mode` default unless `-c sandbox_mode` is forced.
- Cost: a rewrite of `do-not.md` #13 (+ its drift tests / contracts), a `kb-codex --sandbox` override path, and a runtime audit if wanted. Low.
- Reversibility: high. It is config only. The harm from a bad lane is not reversible: a planted hook or a written `$HOME` file persists.

### (2) `workspace-write` + network + `--add-dir` for the uv cache
- PRO:
  - This is already what `kb-codex --write --network` does (`codex_run.py:100-117`). It is measured in KB: rc=2 without `--add-dir`, rc=0 with (`ai-cli-invocation.md:~60-66`, 0.152.0).
  - Keeps `.git`/`.codex`/`.agents` read-only. Network is on only when asked.
  - It is the thing the #767 policy intends.
- CON:
  - `Library/Caches` is writable, a broad exception.
  - No `git commit` from the lane: the coordinator commits.
  - If dotfiles #1142 means `network_access=true` does not actually restore egress on this machine, this option fails for lanes that fetch. UNVERIFIED: I could not read #1039/#1142 or run the probe below. Possible causes I did not check include the keychain/ssh-agent socket being blocked by Seatbelt.
  - Seatbelt can refuse the run if the policy cannot be enforced.
- Cost: nothing new. It is the status quo for `--write`.
- Reversibility: trivial.

### (3) No sandbox only for implementer lanes; read-only for advisory and review lanes
- PRO:
  - This is literally dotfiles' posture.
  - It limits the exposure to the lane type that needs it, and removes the write capability from the lanes that run on untrusted diffs and fetched content.
  - `kb-codex` already separates the two paths (`read-only` default vs `--write`), and review forces `-c sandbox_mode`.
- CON:
  - The implementer lane still has the hook-planting hole.
  - Two postures to explain.
  - Today's KB code has no clean `danger-full-access` plumbing for `--write`. I did not check whether `LaneSpec.sandbox_override` is wired to a CLI flag.
  - `codex_lane` (the raw-`codex exec` guard) and do-not #12 may need adjusting. I did not read either.
- Cost: a small code change plus a `do-not.md` #13 rewrite scoped to "advisory/review never; implementer only via the sanctioned task".
- Reversibility: high.

### (4) One-time exception for KB#863 only
- PRO:
  - Smallest blast radius. It tests whether `workspace-write` is actually insufficient before changing policy.
  - Leaves #13 in place, with a dated, named exception.
- CON:
  - "One-time" exceptions tend to become permanent; a per-lane exception policy was already rejected as "a policy that drifts" (`ai-cli-invocation.md` in dotfiles, 2026-09-01 entry on `--ephemeral`).
  - Still needs the override plumbing from (3).
  - Adds a rule that Ray's ruling says KB should not have.
- Cost: lowest in code, highest in process.
- Reversibility: high.

### (5) Protect `.git`/`.codex`/`.agents` another way
- Permission profiles (`extends = ":workspace"` + `network.enabled = true` + `~/Library/Caches` = `write`):
  - PRO:
    - Best on paper: `extends = ":workspace"` keeps `.codex` and `.git` read-only (`permissions.md:127-134, 491-495`), and the same mechanism supports `deny` globs and a domain allowlist.
    - Replaces the broad `--add-dir` with an exact path.
  - CON:
    - **Blocked here.** `~/.codex/config.toml:6` sets `sandbox_mode`, which makes profiles ignored (see fact 6). Fixes would be a user-level edit forbidden to this repo, or `--ignore-user-config` (which per openai/codex#49333 also drops the project layer).
    - Docs label profiles Beta.
    - Profile definitions would live in `$CODEX_HOME`, because `--profile` files are user-global.
- `requirements.toml` (managed): enforces which profiles are allowed. It is an admin/enterprise surface, and #47464 reports `-s` is silently ignored under it. Too heavy for a solo machine, and risky.
- Hooks: only a guardrail per the docs. Cannot stop a shell write at `danger-full-access`.
- Filesystem hardening (`chflags uchg` on `.git/hooks`, `.codex/`): the same OS user can clear the flag, so it only slows a confused model, not a hostile one. Not a security boundary.
- Detective control, which is genuinely additive (custom code, justified because no codex or git feature records this): snapshot a hash manifest of `.git/hooks`, `.git/config`, `.codex/**`, `.agents/**` before and after a lane, and fail the lane on any diff.
  - PRO: works at any sandbox level, closes #767's "prose-only" gap for this specific hole, and fits the existing post-lane `git status` step.
  - CON: detects, does not prevent. A same-lane hook execution is not stopped.
  - Reversibility: trivial.
- Overall cost: profiles are blocked; the detective control is small python (zero-bash-logic) plus a test.

### (6) Anything else
- **Fix the premise in `do-not.md` #13.** It currently says the danger is "lose their read-only protection". It should name the real failure mode: no sandbox plus always-on `--dangerously-bypass-hook-trust`. It should also repoint the stale citations to the pin actually in use, and re-verify at 0.160.0.
- Force `-c sandbox_mode=...` on every `codex review` / `exec review` lane regardless of option, since the user-level default is `danger-full-access`.
- Persist and read back `turn_context.sandbox_policy.type` from `~/.codex/sessions` after every lane (the #767 method). That is the measurement that proves what actually ran, and it already exists in the data.

## Recommendation

**Adopt (3), and replace (1) as the default under test.** Do NOT adopt "no sandbox everywhere".

1. Advisory, review and `codex review` lanes: always `read-only`, with `-c sandbox_mode` forced on the review paths.
2. `--write` implementer lanes: default stay `workspace-write` + `--network` when the spec fetches. Allow `danger-full-access` ONLY as an explicit per-lane override named in the spec, for example when verification needs a commit, an ssh agent or the keychain.
   - For the KB#863 fix-1 lane, first try `workspace-write --network` (option 2).
   - Use the override only if the probe below fails.
3. Add the pre/post hash-manifest check from (5) for `.git/hooks`, `.git/config`, `.codex/**`, `.agents/**`, whatever sandbox a lane ran at.
4. Rewrite `do-not.md` #13 in its own PR, as already ruled: scope it to advisory/review lanes and name the hook-trust chain as the reason.

Why not (1): the extra convenience over (2)+(3) buys only `git commit` and keychain/ssh access. The cost is an always-trusted-hook planting path. Why not (4) alone: it leaves the policy question to drift.

## How to arm it (probes and controls)

None of these were run; Bash was unavailable. All use scratch directories and no model, so they are deterministic.

1. **Protection probe, through codex's own sandbox runner.** Re-probe `codex sandbox --help` first, since the subcommand and flag names may have drifted. Create a scratch git repo with `.codex/` and `.agents/` directories. Then run these under the `workspace-write` sandbox:
   - write `ordinary.txt` (expect success);
   - write `.git/hooks/pre-commit`;
   - write `.codex/hooks.json`;
   - write `.agents/x`.
   Expect the last three to fail with "Operation not permitted".
   **Control arm:** the identical three writes under `danger-full-access` must succeed. If they fail there too, the probe cannot discriminate and proves nothing.
2. **Network probe.** `curl -sS -m 5 -o /dev/null -w '%{http_code}' https://api.github.com` under `workspace-write` should fail. It should succeed with `-c sandbox_workspace_write.network_access=true`. This directly tests the dotfiles #1142 claim.
3. **uv-cache probe.** `touch ~/Library/Caches/uv/.probe-<fresh>` should fail without `--add-dir ~/Library/Caches` and succeed with it. The probe filename must be freshly invented, and the file removed afterwards.
4. **Through the real entry point.** Run `mise run kb-codex -- --write --print-argv` (the docstring says `--print-argv` exists) and assert the argv contains `--sandbox workspace-write`. Then read the lane's rollout `turn_context.sandbox_policy.type` in `~/.codex/sessions` and require `workspace-write`. **Control:** a deliberately `danger-full-access` lane must show the other value.
5. **Detective control.** Run it against a lane that appends one byte to a copy of `.codex/hooks.json` in a scratch clone. It must fail. A clean lane must pass.

## What I could not verify

- The codex-advisor call was not made; this is not a gpt-6.1-sol verdict.
- All 0.160.0 runtime behaviour: the `codex exec --help` and `codex sandbox --help` surfaces, `--ignore-user-config`, whether `network_access=true` restores egress, and exactly what Seatbelt blocks. The only source read is 0.154.0.
- Whether the vendor docs I cited still hold at 0.160.0. The corpus is flagged superseded.
- The body of dotfiles #1039/#1142 and the real reason `workspace-write` was judged to cut the network.
- Whether `kb-codex` exposes `sandbox_override` on its CLI, and whether `codex_lane` or do-not #12 need changes for it.
- `default_read_only_subpaths_for_writable_root`'s exact body. The `.git`/`.agents`/`.codex` list comes from the docs, not from a read of the helper.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — source clone at rust-v0.154.0 (`protocol/src/permissions.rs`, `protocol/src/protocol.rs`); issues #49333 and #47464 as cited in the prior report, not re-read
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issue #767; `.claude/rules/do-not.md`; `.claude/rules/ai-cli-invocation.md`; `.claude/agents/kb-codex-implementer.md`; `python/src/kb_setup/codex_run.py`; vendored `sources/agent-harness-docs/docs/codex/{permissions,agent-approvals-security}.md`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.claude/rules/ai-cli-invocation.md` (as loaded in session context); `codex-noninteractive-settings-2026-10-03.md` research report; #1039 and #1142 cited, not read
