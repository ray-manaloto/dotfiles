# Codex setup after fable-orchestrator — design decision (2026-09-22)

> **SUPERSEDED IN PART (Ray, 2026-09-22d, after `claudex-loop-full-research-2026-09-22.md`): team shape is NOT allowlist-domain-derived as §1 proposes — it is role-first (typed role → model), ONE agent by default, a team only for separable slices each with its own allowlist + gate and no shared write state. `codex exec review` stays "most likely" but is gated on a settings/env/config/CLI research pass (agentsview first) and a read-only write-canary. Authority: `task_plan.md` Phase 10 Addendum.**

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> `fable-orchestrator:fable-advisor` final message, run after every background
> task/agent/lane of this session had completed (Ray's condition). Inputs: the three
> fable-orchestrator removal reports, feature-matrix-final-2026-09-21,
> history-herdr-claudex-2026-09-21, research-plugin-pass-2026-09-21, the
> codex-sdlc-team skill + sdlc_team.py, task_plan.md Phase 9/10, offline codex and
> claude-code docs, the mattpocock code-review skill.

**Lane limits.** Read-only, no Bash: I could not run `mise run graphify-query` (the graphify hook fired on every read; both input reports measured the graph `stale`, rc=3) and wrote nothing to `findings.md`/`progress.md`. Every claim below is from direct source reads. Persist this verbatim.

## 1. Target architecture

**Entry point: the existing `codex-sdlc-team` skill → `mise run sdlc-team` → `dotfiles_setup.sdlc_team`.** It already is the typed seam (`.claude/skills/codex-sdlc-team/SKILL.md:26-30`; `sdlc_team.py:692`). Extend it; do not build a second thing. This is what `task_plan.md:294-299` ruled.

**Modes: three, on `SdlcMode`** (`sdlc_team.py:48-52` has `REVIEW`, `IMPLEMENT`): add `RESEARCH` (9.2, `task_plan.md:241-244`; read-only, network on, always solo).

**One-agent vs team — decide in python, from the request, typed.**
- Input: `allowlist` (already required, `sdlc_team.py:71`) + `mode`.
- Rule: map each allowlist path to a specialist domain using the routing table now living as prose in `.codex/agents/codex-sdlc-dispatcher.toml:26-31` (python/, .pkl/.toml/.hcl, .github/workflows, .devcontainer, docs/rules). **One domain → `solo`**: dispatch that specialist directly, no dispatcher hop. **Two or more → `team`**: dispatch via `sdlc-dispatcher`, which spawns them in parallel (`:36`). `research` → always `solo`; `review` by ref → `solo` (a cold review has no domain split).
- Where it lives: a new `SdlcTeamShape` StrEnum (`solo|team`) on the request with **no default** — the caller may pin it, otherwise `dispatch()` derives it and **records the derived value plus the domain set in `SdlcTeamDispatch`**. That moves the routing table from a prose toml into one testable python function; the dispatcher toml keeps the "roster is not a closed set" clause (`:59-61`) for the team case. This is 9.12's shape hand-typed now, codegen later (decoupling ruling honoured).

**Cross-family is a typed input, not a memory.** Add `author_family: claude|codex|human` (required). `mode=review` with `author_family=codex` → `INVALID_REQUEST` ("same family; use the Claude lenses"). This is B15/F15 enforced in code (`feature-review-fable:94`), and it is how KB's reviewer already fails closed (`kb-codex-astra-reviewer.md:32-37`).

**Codex review: `codex exec review`, not `codex review`.** Evidence:
- They are one code path — `ReviewCommand` is a shim into `codex exec review` (`research-plugin-pass:307-308`).
- The `exec` spelling inherits exec globals — `--json`, `--output-schema`, `-o`, `--model`, `--ephemeral` (`research-plugin-pass:298-301`) — whereas KB found the top-level `codex review` "has no `-o`" (`kb-codex-astra-reviewer.md:109-110`). We need `-o` and `--output-schema` for a settlement (B7/B14).
- Targets: `--commit <sha>` for the cold gate (matches "review by ref", `cold-reviewer.md:16`); `--base <branch>` for a PR-branch review before `ship`; `--uncommitted` **never in a gate** (no immutable ref). Exactly one; each `conflicts_with_all` includes `prompt` (`research-plugin-pass:277-290`; vendor: `cli__reference.md:117-118`).
- Consequence, accepted: **the codex lane runs the built-in review prompt unbriefed.** Our contract text rides on the Claude side (§2). Structure is enforced CLI-side via `--output-schema` (reuse `codex_verdict.VERDICT_SCHEMA`, `codex_lane.py:109-111`), not by prompt. UNVERIFIED whether `--output-schema` binds the review sub-agent's output — 9.4 probe.
- Model: no dedicated `--model` on review (`research-plugin-pass:304-306`); pin with `-c review_model="gpt-6-sol"` (`kb-codex-astra-reviewer.md:97-101`) and record it; the banner `model:` line is NOT evidence (`:111-118`).
- Sandbox: `-c sandbox_mode="read-only"` — layer precedence 30 over user config 20, measured on `codex review` with the banner `sandbox:` line as the observable (`kb-codex-astra-reviewer.md:120-147`). Still run 9.1c (#45482) — that leak is a different path (agent toml), but "read-only is a claim" until measured.
- `--cd` is absent (`docs/receipts/575.md:142`): set `cwd=` on the spawn as `sdlc_team` already does.
- Timeout: default by mode, `null` invalid (A4; `sdlc_team.py:70,147` today).

**Sequencing (resolves the "removal first / no code" ruling):** the parity PR carries this as *doctrine* in the skill; the `exec review` *mechanism* is a separate ticket after Phase 10 step 2, because every flag above must be re-probed on the native 0.156 install (`task_plan.md:361-373`; `ai-cli-invocation.md` re-probe rule).

## 2. Claude-side review

| Lens | What it is | When |
|---|---|---|
| `/code-review` (bundled) | correctness bugs + simplification, background forked subagent, reads `CLAUDE.md` not `REVIEW.md`; target = ref range / PR number / path; effort level (`$CC/code-review.md:290-341`); model-invocable (`:356-358`), ruled model-invoked in `task_plan.md:395-396` | every behavior-bearing diff, whoever wrote it |
| `/mattpocock-skills:code-review` | Standards (repo standards + Fowler smells) and Spec axes in parallel subagents against a fixed point (`~/.claude/plugins/cache/mattpocock/.../code-review/SKILL.md:6-11,17-23,58-70`) | every diff that has a seven-part spec — the Spec axis is our spec-conformance check |
| `cold-reviewer` | cold, intent-stripped, by ref, `memory: local`, `adversarial-review` skill attached (`cold-reviewer.md:3-11,16-18`) | the cross-family cold gate on a **codex** diff |
| `sdlc-team mode=review --commit` (`codex exec review`) | the cross-family cold gate on a **Claude** diff | Claude-authored diffs only |

Pairing:
- **Codex-authored (the default):** `cold-reviewer` + `/code-review` + mattpocock = the full gate; no codex lens (`.claude/CLAUDE.md:79-84`).
- **Claude-authored:** `codex exec review --commit` is the cold gate; `/code-review` + mattpocock still run and are **announced same-family** — settlement carries `author_family`, `reviewer_family`, `degraded` (F15).
- Tiers (B10): `mechanical` → gates + mattpocock Standards; `behavior` → + cold cross-family + `/code-review`; `security` → + silent-failure reader.

**What changes for existing pieces.** `cold-reviewer` stays and is not retired — nothing in the new lenses is cold (mattpocock reads the spec by design; `/code-review` reads branch context). `adversarial-review` stays as the round-bounding doctrine (`SKILL.md:51-66`), but its front matter names `codex-reviewer, grok-reviewer` (`:3`) and `fable-advisor` (`:326`) — add to D8. `sdlc_team` review with a `spec_file` is a spec-conformance review, not cold (`feature-review-fable:96`, `sdlc_team.py:272`): make `spec_file` and a review `target` mutually exclusive in `_request_error` so the two shapes cannot be confused.

## 3. claudex-loop: adopt / adapt / reject

**Adopt (mechanism, into `sdlc_team`):** SHA-bound attestation (`runner.py:247-254` → B3); HEAD-unchanged under `COMMIT: caller` (`:373-375` → B6); `--json` + exactly-one `thread.started`/`turn.completed`, any `turn.failed` aborts (`:153,203-211` → B7/C8c); inspected-state fingerprint (`:86-109` → B14; KB already has a bash version at `kb-codex-astra-reviewer.md:174-181` — the python port replaces it, `zero-bash-logic`); `BLOCKED` must explain (`:140-141` → C8d); "never present an earlier review as covering later fixes" and a recorded `--unreviewed-spec` override (`codex-build/SKILL.md:15,17` → B12/B14 prose); "do not ask Codex to certify its own changes" (`codex-build/SKILL.md:13`) and "same-provider review is labelled, never cross-provider approval" (`codex-review/SKILL.md:12`) → the `author_family` refusal + `degraded` flag above; MCP writes bypass the shell sandbox (`runtime.md:33` → B15 sentence).

**Adapt:** "valid completed result AND APPROVED both required; failed/empty/blocked/malformed are not approval" (`codex-review/SKILL.md:14`) — already ours (F25), fold the wording into the skill. Round caps `MAX_ROUNDS=5` → our measured 2 (B12).

**Reject:** the plan-review-by-other-provider phase (`codex-review/SKILL.md:8-10`; premise-verifier + adversarial-critic cover it, matrix row 50); dual-host packaging (`.claude-plugin` + `.codex-plugin` — a plugin is the failure mode we are leaving); `claudex-route`, recon/interview, Windows shims, session resume/UUID guards (rows 26, 53, C8a/b); the Claude-CLI reviewer lane (row 51); `tempfile` artifacts (C9).

**One fact nobody folded in:** claudex-loop is ENABLED on the codex side (`~/.codex/config.toml:254-255`) and nothing in either repo dispatches it (`history-herdr-claudex:23-29`). Its `codex-build`/`codex-review` skills are a second Claude→codex entry point by construction.

## 4. Deltas to the ratified matrix, D1-D8/K1-K8, and the PR sequence

- **Matrix D:** `codex exec review` moves DROP → **ADOPT, scoped**: cold lens for Claude-authored diffs only, built-in prompt, `--commit|--base` target, `--output-schema`, `-c review_model`, `-c sandbox_mode`. D's constraints (no brief, no `--cd`, same-family for a codex diff) are kept as the scoping conditions, not as the reason to drop.
- **Matrix B10:** bind the tier enum to the lens table in §2.
- **New B16:** `team_shape` derived from allowlist domains; `author_family` required.
- **D3 text:** replace "no new reviewer agent (matrix D drops `codex exec review`)" with "no new reviewer agent; `mode=review` gains a by-ref target that runs `codex exec review`; the lens table (§2) is the doctrine". Still no new agent file.
- **D5:** the `orchestration.codex-only-lanes` cold-review line (`suites.toml:2399`) must be rewritten in the same PR the `.claude/CLAUDE.md` table changes, or `verify` goes red.
- **D8:** add `adversarial-review/SKILL.md:3,326` and its `.agents` mirror.
- **New D9 — codex-side plugin.** "Remove from both" must cover the codex harness: `~/.codex/config.toml:80-81` `enabled = true`, a trusted hook at `:436-437`, the dead marketplace at `:601-605`; the cache is a git clone at `78f9cb5` (`.codex-marketplace-install.json:6`) with the Claude-format `hooks/hooks.json` PreToolUse `Agent` matcher. It is user-global, so it is **operator step 5**, not a PR; add a doctor `[codex]` check (`doctor.toml:272-280` already exists) that fails on a `fable-orchestrator` plugin entry, with a control arm on a plugin known present.
- **New D10 (ticket, after step 2):** `sdlc_team` changes — `RESEARCH`, `team_shape`, `author_family`, review `target`, `exec review` argv, `--json`, `--output-schema`, `-c review_model`, `PLANNING_DISABLED` (A1), timeout default (A4).
- **K1/K2:** unchanged and now consistent — KB's `cold:codex-astra` is already `codex review` via `kb-codex` (`review.py:434-437`; `kb-codex-astra-reviewer.md:80-88`).
- **Retirements:** none new. The 12 wrappers stay decoupled (Addendum); `cold-reviewer`, `gate-runner`, `spec-scribe` stay.
- **PR sequence:** unchanged 0-5; step 5 gains the codex-side uninstall (D9); D10 is a new ticket after step 2.

## 5. Conflicts with prior rulings, and four questions

Conflicts named: (C1) ratified matrix D vs Ray requirement 3 — resolved by scoping, above. (C2) decision report §3 D3 wording — amended. (C3) "removal first, decoupled from code" vs the review mechanism needing `sdlc_team.py` changes and flag probes on native codex — resolved by doctrine-now/mechanism-after-step-2. (C4) `.claude/CLAUDE.md:80-84` "Opus cold pass is the full gate" stays true; requirement 4 adds lenses, it does not replace. (C5) mattpocock's Spec axis looks up issues via `docs/agents/issue-tracker.md` (`SKILL.md:13,29`); ours is `docs/issue-tracker.md` and `/setup-matt-pocock-skills` is forbidden (`.claude/CLAUDE.md:9-12`), so step 2 of the skill hits its "run setup" branch. (C6) `settings.json:179` disables `code-review@claude-plugins-official`; that is the plugin, not the bundled `/code-review` command — no conflict, but say which one is meant in the doctrine (bundled).

Questions for Ray:
1. Does "remove from both" include the codex-side plugin, hook trust, and marketplace in `~/.codex/config.toml` (operator step)? **Recommended: yes.** And disable `claudex-loop@claudex-loop` (`:254-255`) so the single-entry-point ruling holds on the codex side too? **Recommended: yes.**
2. Land the review doctrine in the parity PR now and the `codex exec review` mechanism as a ticket after Phase 10 step 2 (native codex)? **Recommended: yes** — flags must be measured on the install we will actually run.
3. Derive `team_shape` in python from allowlist domains (caller may pin, dispatch records it), rather than leaving it to the dispatcher agent's judgement? **Recommended: yes** — one typed, testable source; the dispatcher keeps the "extend the roster" clause.
4. Add a tracked one-line `docs/agents/issue-tracker.md` pointing at `docs/issue-tracker.md` so the mattpocock Spec axis resolves issue references? **Recommended: yes** (the alternative — always passing the spec path as an argument — skips issue-referenced specs, `SKILL.md:29-30`).

**Key files:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/codex-sdlc-team/SKILL.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/agents/codex-sdlc-dispatcher.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/cold-reviewer.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/adversarial-review/SKILL.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/agents/kb-codex-astra-reviewer.md`, `/Users/rmanaloto/.codex/config.toml`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — skill, `sdlc_team.py`, agents, contracts, task plan, reports (local clone)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb-codex-astra-reviewer`, `review.py`, `kb-tool-review.js`, offline codex + claude-code docs (local clone)
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — codex-side cache 1.21.0 (`run-lane.sh`, `hooks.json`, install manifest); upstream 404 per the input reports
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — codex-side cache 2.1.0 (`codex-build`, `codex-review` skills); `runner.py` lines via the Fable review
- [openai/codex](https://github.com/openai/codex) — `exec review` flag matrix via the plugin-pass report; vendor docs offline
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — bundled `/code-review` docs offline
- [mattpocock/skills](https://github.com/mattpocock/skills) — installed `code-review` skill 1.2.3
