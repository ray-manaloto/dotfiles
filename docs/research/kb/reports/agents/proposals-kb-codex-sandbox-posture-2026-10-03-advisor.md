# KB codex sandbox posture — advisor verdict (claude-advisor, escalation; 2026-10-03)

Persisted verbatim by the coordinator (f4b75d61) from the claude-advisor hand-back; the lane was read-only.

## 1. Verdict

Do NOT rule "no sandbox" for KB lanes. Keep `workspace-write` (+ `--network` only when the spec fetches, + the uv-cache `--add-dir`) as the KB implementer default, `read-only` for advisory/review, and allow `danger-full-access` only as a per-lane escalation on a NAMED, MEASURED need recorded in the spec. Rewrite KB `do-not.md` #13 to say exactly that and to name the real mechanism; do not rewrite it to "no sandbox". KB#863 fix-1 runs under `workspace-write` without `--network` — it needs nothing more.

## 2. Deciding risk

Every KB lane passes `--dangerously-bypass-hook-trust` unconditionally (`knowledge-base/python/src/kb_setup/codex_run.py:117`), and KB's `.codex/hooks.json` is tracked and runs real commands (`mise run …`, `uv run … kb-setup hookguard`; `.codex/hooks.json:9,19,31,44,49,60`). So writability of `.codex/`, `.git/hooks/` and `.agents/` is a privilege-persistence path: a confused or injected lane plants a hook, and the NEXT lane (or the coordinator's next `git` on the host) runs it trusted. `workspace-write` is today the ONLY layer that denies those writes — file 1 probe 1 shows `.git/hooks/pre-commit`, `.codex/hooks.json`, `.agents/x.md` DENIED under `:workspace` and WROTE under `:danger-full-access` (unsandboxed control also WROTE, so the probe discriminates); the KB hook guard has no `danger` rule (`codex_lane.py`: 0 hits for `danger`; control `codex exec` = 4 hits); and KB's own inventory records #13 as `enforced_by = []`, `current_surface = "prose-only"` (`knowledge-base/docs/guards/inventory.toml:334-346`). Full access removes the only existing enforcement, for a need KB has not measured. True when `--dangerously-bypass-hook-trust` stays unconditional (it must — trust is per-hook-hash, `codex_run.py:13-15,116-117`).

What would flip this: a measured in-sandbox failure of fix-1's own gates for an out-of-tree reason that an `--add-dir`/env var cannot fix. Then grant the named per-lane escalation (option 6a), not option 1.

## 3. Grounding facts (each with its condition)

- **What workspace-write protects, from source** (openai/codex rust-v0.154.0 clone at `knowledge-base/sources/codex/codex-rs/protocol/src/permissions.rs:2230-2268`, wired at `protocol.rs:1296-1332`): per writable root (cwd, `/tmp`, `$TMPDIR`, each `--add-dir`), the TOP-LEVEL `<root>/.git` (dir, or pointer file plus its resolved gitdir — so a worktree's real gitdir is protected too), `<root>/.agents` if a dir, `<root>/.codex` if a dir (always for the cwd root). A NESTED `.git` (e.g. `sources/codex-docs/.git`, or `/tmp/<scratch-clone>/.git`) is NOT protected. Behaviour confirmed at 0.160.0 by file 1 probe 1; the source I read is 0.154.0.
- **`danger-full-access` = no sandbox at all**, and it is already the machine default: `~/.codex/config.toml:6 sandbox_mode = "danger-full-access"` (key name/line only read). No `[sandbox_workspace_write]`/`writable_roots` keys are set there, so under workspace-write only cwd/tmp/add-dirs are writable.
- **Network**: workspace-write cuts egress by default; `-c sandbox_workspace_write.network_access=true` restores it on 0.160.0 (file 1 arms A→"Could not resolve host", B→200). The dotfiles doc attributes this to #1039/#1142 — that attribution is WRONG: #1039's body has zero network mentions (its drivers were out-of-tree writes: the lint log in `~/.local/state/dotfiles/`, `ps` denied, `~/.local/share/mise`), and #1142's network lines are about a read-only lane. The fact is true; KB's own `ai-cli-invocation.md:101-103` and `codex_run.py:17-19` carry it correctly. "Matching dotfiles" therefore imports a posture whose cited reasons are dotfiles-gate-specific.
- **KB plumbing already exists**: `codex_run.py:100` (`sandbox_override` → `--sandbox <v>`), `:109-112` (`--add-dir ~/Library/Caches` + network key only under workspace-write), `:646-652` (CLI `--sandbox`), `:515-516` (review path sends `-c sandbox_mode=`, the only channel, since `codex review` has no `-s`). So options 1/3/4 need ZERO new code: `mise run kb-codex -- --write --sandbox danger-full-access` runs today, un-denied.
- **Dotfiles precedent is option 3, not option 1**: `dotfiles/.claude/rules/ai-cli-invocation.md` Sandbox paragraph — `sdlc-team` passes no `-s`; implementer/operator pin `danger-full-access` (`.claude/agents/codex-sol-implementer.md:155`); advisory wrappers keep `--sandbox read-only`, "the only thing that stops them writing". And dotfiles adopted it AFTER measuring three gate failures under workspace-write (#1039 table), i.e. need first, posture second.
- **#767**: 13/151 sessions at `danger-full-access`, all cwd=KB, none since 2026-09-09, "no existing gate could have caught any of them"; sandbox never varied mid-session (0 files), so the per-session count is robust.
- **#13 rewrite cost**: the anchor `<!-- guard-programme: do-not.danger-full-access -->` is pinned by `docs/guards/inventory.toml:334-346` (with `reviewed_digest` of the headline) and `tests/test_guard_inventory.py` FAIL-arms on anchor removal (`:261-264` for the sibling). A rewrite keeps the anchor, updates the inventory entry (digest/headline) in the same reviewed diff, and repoints the stale `permissions.rs:1792` cites (helper is at `:2230`, `unrestricted()` at `:605-609` in the 0.154.0 clone; re-verify on the pin actually run).

## 4. What KB#863 fix-1 actually needs (from `kb-863.json`)

Fix-1 = failure 1 only: `manifest_audit.py` tier 2 hashes the PINNED tree via git objects (`git cat-file -e <commit>`, `ls-tree`/`cat-file blob`) plus a distinct "pin not fetched here" state (comment: (c) + a sliver of (a)). Failure 2 (fnhook tsconfig `include: []`) is dotfiles-side `fnhook_gates.py`, not this lane.

| need | required? | fits workspace-write? |
|---|---|---|
| in-tree writes (`python/src/kb_setup/manifest_audit.py`, `tests/test_manifest_audit.py`) | yes | yes (cwd root) |
| `uv run --project python pytest tests/test_manifest_audit.py` | yes | yes with `--add-dir ~/Library/Caches` (already emitted, `codex_run.py:110`; measured rc=2→rc=0 at 0.152.0, KB `ai-cli-invocation.md:67-68`; uv-cache WROTE at 0.160.0, file 1 arm C) |
| read `sources/<x>/` clone objects (`git cat-file`, `ls-tree`) | yes | yes (reads; nested `.git` unprotected anyway) |
| stale-clone control arm: scratch COPY of a clone under `$TMPDIR`, `git checkout --detach` | yes | yes — `$TMPDIR` is a root and `/tmp/<copy>/.git` is nested, so writable (`permissions.rs:2235-2250`) |
| "pin not fetched" arm | yes | yes — needs an ABSENT object, so no fetch |
| network | no | n/a — do NOT pass `--network` |
| `git add`/`commit`/`stash` in-lane | no | no — index write is denied; coordinator commits (consistent with `kb-codex-implementer.md:61-64`, where the SUPERVISOR runs gates and reports the hash only "if Commit: lane") |
| keychain / ssh / `gh` | no | n/a |

In-sandbox gate caveats (the #1039 class, KB flavour — none require full access, all are avoided by scoping): a FULL `pytest tests/` in-lane would trip `tests/test_cpu_bounded.py:50-51` (`pgrep`) and `launch.py:207` (`ps -Eww`) if Seatbelt denies `ps` as #1039 measured; hk's default log is `~/.local/state/hk/hk.log` (140 MB, mtime today) which workspace-write denies, and KB's `[tasks.lint]` sets `HK_TIMING_JSON`/`HK_OUTPUT_FILE` in-tree but NOT `HK_LOG_FILE` (dotfiles `lint.py:275` does). Whether hk tolerates the denied open is UNVERIFIED (probe below). Mitigation: the spec scopes in-lane verification to the targeted test file + `mise run kb-manifest-audit`; the supervisor runs full pytest + `mise run lint` on the host after exit, exactly as the agent spec already says.

## 5. Options

### (1) No sandbox everywhere (Ray's provisional ruling)
- PRO: zero friction — no add-dir, no network flag; `git commit`, `gh`, keychain, ssh all work; no new code (`codex_run.py:100`); it is already the machine's un-flagged default (`~/.codex/config.toml:6`; #1039 says the same).
- CON: goes FURTHER than dotfiles, whose advisory lanes stay read-only ("the only thing that stops them writing", `ai-cli-invocation.md` Sandbox paragraph). Opens `.codex/hooks.json`, `.git/hooks`, `.agents` to every lane while `--dangerously-bypass-hook-trust` is always on (`codex_run.py:117`; probe 1 row `:danger-full-access` WROTE all five). Codifies #767's finding as policy with enforcement still `prose-only` (`inventory.toml:338-339`). KB has no measured need: #1039's drivers (out-of-tree gate writes, `ps`, `mise uninstall`) are dotfiles gates; fix-1 needs none of them (§4).
- Citation: file 1 probe 1; `codex_run.py:117`; KB#767; `inventory.toml:334-346`; dotfiles #1039 body.

### (2) `workspace-write` + network-when-fetching + `--add-dir ~/Library/Caches` (status quo for `--write`)
- PRO: already plumbed and measured (`codex_run.py:100-117`; rc=2→rc=0 at 0.152.0; 0.160.0 arms B/C: 200 + uv cache WROTE). `.git`/`.codex`/`.agents` stay read-only by source (`permissions.rs:2230-2268`) and by probe. Fix-1 fits entirely (§4). It is what #767 and #13 intend.
- CON: all of `~/Library/Caches` writable (broad; narrowing to `~/Library/Caches/uv` is unverified). No in-lane `git add`/`commit` — coordinator commits. In-sandbox `ps`/`pgrep` denial (#1039) and hk's `~/.local/state/hk/hk.log` make a FULL in-lane gate run unreliable — scope in-lane gates, run the full set on the host. Network is opt-in, and a lane that fetches without `--network` reports a fake outage (KB `ai-cli-invocation.md:101-116`).
- Citation: as above; file 1 arms A-C.

### (3) Split by lane type — implementer at full access, advisory/review read-only (dotfiles' literal posture)
- PRO: confines write capability to one lane type; KB already splits (`--write` vs default read-only; review forces `-c sandbox_mode`, `codex_run.py:515-516`); matches `codex-sol-implementer.md:155`.
- CON: puts the hook-planting hole exactly on the lane that runs on untrusted inputs (issue bodies, fetched pages) and writes. Dotfiles earned it with a measured table (#1039); KB has not — adopting it imports the posture without its reason, and the cited "network" reason is a mis-attribution (§3). Two postures to explain; needs the #13 rewrite + inventory update either way.
- Citation: dotfiles `ai-cli-invocation.md` Sandbox paragraph; #1039 table; `codex_run.py:100,515`.

### (4) One-time KB#863 exception
- PRO: smallest blast radius; would produce the measurement KB lacks.
- CON: fix-1 does not need it (§4), so the exception would be granted for an absent need — and the same measurement comes free by running fix-1 under (2) first. Per-lane exceptions drift (dotfiles rejected the per-lane `--ephemeral` exception 2026-09-01 as "a policy that drifts", `ai-cli-invocation.md`). Still prose-only.
- Citation: `kb-863.json` (fix shape); `codex_run.py:100` (no plumbing needed, so "exception" is purely a rule).

### (5) Hash-manifest detective control (additive, any option)
- PRO: works at every sandbox level; closes the specific hole #767 named as prose-only; small python + test (zero-bash-logic); fits the existing post-lane `git status --short` step (`kb-codex-implementer.md:63`). Pair it with the readback that already exists in the data: `turn_context.sandbox_policy.type` from `~/.codex/sessions` (#767's method) proves what the lane actually ran at.
- CON: detects, does not prevent — a hook planted AND fired within the same lane is not stopped. Custom code (justified: no codex/git native records pre/post hashes of `.git/hooks`, `.git/config`, `.codex/**`, `.agents/**`; codex hooks are a guardrail, not a boundary; `core.hooksPath` is itself rewritable under full access). Permission profiles (`extends=":workspace"`) are blocked on this machine because `sandbox_mode` in `~/.codex/config.toml` disables them (file 2 fact 6, docs-sourced, unverified at 0.160.0).
- Citation: #767 body ("what would close it"); `inventory.toml:339` (`disposition = "function-hook"`).

### (6) Better: "named-need escalation" + three native fixes
- (a) Default (2); `--sandbox danger-full-access` permitted ONLY when the spec names the concrete need (out-of-tree write, commit-in-lane, keychain/ssh) and the PR attaches the rollout `turn_context` readback. This is what dotfiles actually DID in #1039 (measure, then escalate), stated as the rule instead of as history. PRO: the posture follows evidence per lane; no new code. CON: it is still prose until (5)/the function hook lands — the same as every option.
- (b) Set `HK_LOG_FILE` (hk-native; dotfiles `lint.py:275`) in KB's `[tasks.lint]` env to `.agent/kb/gates/hk.log`, beside the two files it already writes there (`mise.toml:376-399`). Removes one #1039-class trip so lint can run in-sandbox. Needs the probe below first.
- (c) Narrow `--add-dir` to `~/Library/Caches/uv` once a probe shows uv needs nothing else (unverified; `uv` managed pythons live in `~/.local/share/uv`, which `mise run kb-context` rc=0 suggests is not needed for `uv run` here).
- (d) Fix #13's text: keep the anchor; name the real chain (no sandbox + always-on `--dangerously-bypass-hook-trust` + tracked, command-running `.codex/hooks.json`); say the protection is a workspace-write feature (not a ReadOnly one); repoint citations; update `inventory.toml:334-346` in the same PR. Also make `-c sandbox_mode=read-only` the DEFAULT on `--review` rather than optional (`codex_run.py:515-516`), because an un-flagged review inherits the user-level `danger-full-access`.

## 6. Recommended ruling for Ray (one paragraph)

Rule: KB implementer lanes run at `workspace-write` with the uv-cache `--add-dir`, adding `--network` only when the spec's verification fetches; advisory and review lanes stay `read-only` (review via `-c sandbox_mode=read-only`, made the default); `danger-full-access` is a per-lane escalation that the spec must justify with a named need and that the PR must evidence with the rollout `turn_context.sandbox_policy.type`; rewrite `do-not.md` #13 to this wording (anchor kept, inventory digest updated, citations repointed, mechanism corrected), and add the pre/post hash-manifest check as the detective layer. KB#863 fix-1 runs with exactly the sanctioned form, unchanged: `cat "$KB_LANE/spec.md" | mise run kb-codex -- --write --model gpt-6.1-sol --effort xhigh --timeout 3000 --output "$KB_LANE/codex-final.md" > "$KB_LANE/lane.log" 2>&1; echo "rc=$?" > "$KB_LANE/lane.rc"` — no `--network`, no `--sandbox` — which `--print-argv` resolves to `codex exec --sandbox workspace-write --model gpt-6.1-sol -o <file> --add-dir /Users/rmanaloto/Library/Caches -c model_reasoning_effort=xhigh --dangerously-bypass-hook-trust -`. The spec's constraints: in-lane verification is `uv run --project python pytest tests/test_manifest_audit.py -x -q` and `mise run kb-manifest-audit` only; no `git add`/`commit`/`stash` (index is read-only; coordinator commits); scratch clone copies under `$TMPDIR` only; after exit the supervisor runs full pytest and `mise run lint` on the host and reads the lane's rollout `turn_context.sandbox_policy.type == "workspace-write"` as the control arm. If, and only if, fix-1 fails in-sandbox for an out-of-tree reason no `--add-dir`/env var fixes, re-run that one lane with `--sandbox danger-full-access` and record why — that is the escalation path, not a policy change.

## 7. What remains unverified (with the cheapest probe)

- hk's behaviour when `~/.local/state/hk/hk.log` is unwritable (workspace-write): probe = a `--write --effort low` lane running `mise run lint > /tmp/l.log 2>&1; echo rc=$?` twice, once with `HK_LOG_FILE=.agent/kb/gates/hk.log`; the two arms must differ or both pass. Not needed for fix-1 if the supervisor runs lint on the host.
- Whether `uv run … pytest` for fix-1 needs anything under `~/.local/share/uv` at 0.160.0 (the rc=0 measurement is `mise run kb-context` at 0.152.0): probe = the fix-1 lane itself, or a low-effort lane running the targeted pytest.
- Whether Seatbelt still denies `ps`/`pgrep` at 0.160.0 (inherited from dotfiles #1039, earlier codex): matters only for a FULL in-lane pytest.
- File 1 arms A/B denials are lane self-reports (file 1 says so); artifact-proven arms are probe 1 and arms C/D.
- Source read is rust-v0.154.0 (`sources/codex/`), not 0.160.0; behaviour at 0.160.0 rests on file 1's probes.
- Permission-profile blockage by the user-level `sandbox_mode` key (file 2, docs-sourced) not re-probed.
- Whether narrowing `--add-dir` to `~/Library/Caches/uv` suffices.
- Codex was not run and no repo file was edited, per brief.

Prior codex verdict: none exists — both runs derailed (research-gate + missing `DOPPLER_TOKEN` keychain item); the one-line residue "option 2 for KB#863, coordinator-owned commits" is consistent with this verdict but carried no reasoning, so it is replaced, not upheld.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #1039 and #1142 bodies read via `gh`; `.claude/rules/ai-cli-invocation.md` (Sandbox paragraph), `.claude/agents/codex-sol-implementer.md:64-83,155`, `python/src/dotfiles_setup/lint.py:248-276`, `hk.pkl`/`hk-common.pkl` (HK_* env grep)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — #767 (body + both comments) via `gh`; #863 (body + advisor comment) from `kb-863.json`; `python/src/kb_setup/{codex_run,codex_lane,hook_guard,launch,manifest_audit,guard_inventory}.py`, `.claude/rules/do-not.md:140-184`, `.claude/rules/ai-cli-invocation.md` (grep), `.claude/agents/kb-codex-implementer.md`, `mise.toml` (`kb-codex`, `lint`), `docs/guards/inventory.toml:330-346`, `tests/{test_guard_inventory,test_cpu_bounded,test_launch}.py`, `.codex/hooks.json`, `.codex/config.toml` (key names), `sources/codex.manifest`
- [openai/codex](https://github.com/openai/codex) — rust-v0.154.0 clone at `knowledge-base/sources/codex/` (`codex-rs/protocol/src/permissions.rs:2230-2268`, `codex-rs/protocol/src/protocol.rs:1296-1332`)
