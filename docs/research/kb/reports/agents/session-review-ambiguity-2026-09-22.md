# Nothing-vague review of session b72c95e0 (2026-09-22d)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. The harness neutralised `<`/`>` in transit; restored.
> Staged in scratchpad pending the next branch (research branch is shipped/closed).

**Route used.** I started with the `agentsview-finding-history` skill. `agentsview session messages --role user` gave me all 26 user turns, and `agentsview session tool-calls` gave me 162 calls: 19 AskUserQuestion and 32 SendUserMessage. `tool-calls` returns only `result_length`, so I read the AskUserQuestion *answers* from the session JSONL with `jq` (tool_result by `tool_use_id`). I also read root `findings.md` lines 1936–1967, the 13 committed reports, the pending `codex-0156-impact` report, `task_plan.md` Phase 9, `schemas/sources.toml`, and `~/.config/mise/config.toml` (grep only). The graph was not used, because it does not index session transcripts.

**This lane is read-only.** I wrote nothing outside the session scratchpad. The coordinator must persist this report verbatim.

---

## V1. The final codex model is decided, but four artifacts still tell a post-/clear agent to do something else. HIGH

**Where the final ruling lives.** Ray's last ruling (ord 338) is "option 2", which means keep the native installer. `findings.md:1967` records it as "option A". The pending report defines **Option A** as native (`codex-0156-impact:91`) and **Option B** as "recommended" (`:79`). So "option 2" in the question and "Option A" in the report are the same choice. A reader who sees "option 2" and opens the report will pick B.

**Artifacts that still recommend a rejected option, with no supersession note** (grep `supersed` = 0 in each):
- `codex-0156-impact` (pending) — its bottom line (`:10`) says "I recommend switching back to the mise npm pin". Ray rejected that.
- `codex-daemon-history-2026-09-22.md:223` — "the mise pin is auto-bumped to latest…". Rejected by Q39.
- `exa-program-review-2026-09-22.md:32` — "let the doctor drive updates". Rejected by D1.
- `fable-program-synthesis-2026-09-22.md:57` — "Recommend OFF + doctor-driven". Rejected by D1.
- `codex-desktop-settings-2026-09-22.md:183` — the `CODEX_APP_SERVER_USE_LOCAL_DAEMON` plan. D2 made it probe-first.
- `task_plan.md:188` — "9.1 Bump codex 0.154.0 -> latest … via `mise run lock-shared`". This is the plan `session-resume` will report as active. It is the exact opposite of Q39.
- `task_plan.md:206+` — gate "daemon AT OR AHEAD of the mise pin". There is no mise pin under Q39.
- `task_plan.md` §9.13 — "`--dangerously-bypass-hook-trust` may be required". The synthesis says never use it, and D4 says trust the hooks.

**Other gaps in the codex model:**
- **The Q28 ruling was never retired.** Q28 said "Bump [codex to 0.155.1] now, in the deps PRs". Q39 removes the mise pin. The literal reading still bumps codex in the deps PR.
- **The user-global pin is outside the ruling.** `~/.config/mise/config.toml:144` pins `"npm:@openai/codex" = 0.155.1`. The ruling "remove npm:@openai/codex from mise (both repos)" doesn't cover that file. That shim will still win on PATH after the installer runs. The warning at ord 344 names only the repo pin.
- **"Version" means something different for codex in `schemas/sources.toml`.** Its `version` (lines 41–46) is the *vendored-schema* version, fetched from an **unversioned** URL (`learn.chatgpt.com/docs/config-schema.json`). claude-code's URL carries its version. "Record 0.156.0 there" could mean (a) the binary version only, or (b) re-vendor the schema too.
- **"Latest" and "pinned" conflict.** The host runs latest-channel and auto-updates. The image runs "native installer pinned to recorded version". Q2 says "always … latest".

**Proposed wording:**
> "FINAL (ord 338, supersedes Q28, the 0.156 report's Option B, and task_plan 9.1): codex is installed natively, latest *stable* channel, on the host. No repo pins codex in mise. The last-synced version is recorded in dotfiles `schemas/sources.toml [[schema]] tool=codex version` and in KB `currency.toml [tool.codex] expected`. Changing the record requires re-vendoring the schema in the same PR. The image installs `--release <recorded>`. The host may run ahead of the record. The doctor treats 'ahead' as 'bump the record', never as a failure."

Also add a SUPERSEDED banner to the reports listed above, and a pointer at `task_plan.md` 9.1.

**❓ For Ray:** "The user-global `npm:@openai/codex` pin in `~/.config/mise/config.toml` still shadows a native install, and the 2026-09-16 user-global 'match the mise pin exactly' ruling still stands. Should both be retired now, by you, as an operator step?" **Recommended: yes, retire both, operator-run.**

## V2. D1: "keep it on … pause at a good starting point, make the update, restart and then continue". HIGH

Source: Q-D1 answer; `findings.md:1965`.

**Two plausible readings:**
- **(a)** The hourly updater installs the new version *itself*. The hooks detect the change after the fact, then bump the record and restart the daemon.
- **(b)** The hooks detect a new *upstream release* and perform the update at a checkpoint.

**The problems:**
- With the updater ON, "make the update" is already done by the time any hook runs, and the updater restarts the daemon on its own schedule. The synthesis cites #40969 for this: an in-flight turn is killed after a drain of at most 300 s. Hooks cannot make that restart wait for a checkpoint.
- "Good starting point" is undefined: between turns, between PRs, or at SessionStart?
- "Who pauses" is undefined: the Claude coordinator, a function-hook deny, or the codex lanes.

**Proposed wording:**
> "Checkpoint = no live `sdlc_team`/`codex_lane` supervisor, *and* either SessionStart or a PR boundary. While CLI ≠ daemon ≠ record, the codex-doctor PreToolUse deny blocks new codex dispatches. The coordinator then runs `daemon restart` (never stop/start) and continues."

**❓ For Ray:** "The hourly updater restarts the daemon on its own clock, which can kill a running codex lane. Do you accept that risk, with hooks only gating *new* dispatches, or should the updater be off with a checkpoint-driven `daemon update`?" **Recommended: accept, and set `shutdownGraceSeconds: 300`** (this respects your "keep it on").

## V3. "Every item through /to-spec, /to-tickets, /implement" and D3 "enforce a prompt on which skill to run". HIGH

Sources: Q33 "Every item"; Q29 note; `findings.md:1950–1951`; ord 226.

**What conflicts:**
- The coordinator shipped **#1244** directly.
- Handoff PRs, the research-persistence PR, and the pwf interim PR (ord 226 step 4 does not mention the verbs) have no stated carve-out.
- `/to-tickets` files issues, which means three issue-generating verbs for a two-line pin bump.
- The ord-226 summary lists **six** wrapper skills. D3 "option 1" narrows wrappers to "unattended chains only". So which verbs, if any, now get wrappers? That is unstated.

**D3's "enforce a prompt" has at least three readings:**
- (a) The coordinator always ends a turn with an AskUserQuestion naming the exact slash command. That already exists as memory `feedback_always_offer_clickable_next_step`.
- (b) A UserPromptSubmit or Stop hook reminds. The memory "Stop hooks FORCE a turn" argues against this.
- (c) A PreToolUse deny on Edit/Write of source files when the branch has no spec or ticket.

**Proposed wording:**
> "Every *code or config* change item goes through to-spec → to-tickets → implement. Exempt: docs-only persistence PRs (research reports, handoffs, goal-history). Wrappers are built only for `implement` (used by `/gated-implementation`). D3 enforcement is reading (c), with (a) as its message."

**❓ For Ray:** "How should the 'which skill to run' prompt be enforced: a PreToolUse deny that names the verb when implementation starts without a spec, or only the end-of-turn clickable question?" **Recommended: the deny.**

## V4. D4 "trust the hooks, let's make it work" versus "pwf decisions wait for deep extraction". MED

- **D4 decides a pwf design question before the extraction.** It picks the plan guard's mechanism. It is also silent on the permission profile, which synthesis §D4 recommends as stronger (#27833 shows a `perl -pi` bypass of a hook). Was the profile rejected, or just not chosen yet?
- **"Trust" is operator-only.** It is done through the TUI `/hooks` screen, there is no CLI, and it must be redone after each `hooks.json` edit. It is also UNVERIFIED whether the trust hash covers script bytes (`fable-pwf-shared-plan-proposal:55`). That was never written down as a standing operator duty.
- **Proposed wording:**
  > "D4 is provisional, like Q48 and Q50. Mechanism: codex PreToolUse deny, which requires operator `/hooks` trust after every hooks change. The permission profile is not rejected; probe C3 decides whether it is added."

## V5. Q48 "Sometimes codex" (coordinator). MED

- **The committed design assumes the opposite.** `fable-pwf-shared-plan-proposal:23` says "no Codex process is ever the coordinator", and its line 63 open question is answered "never". There is no note in the report.
- **Synthesis §D5**, the definition of "coordinator", was **never asked**. Neither was §D6, the mise-first exception.
- **Readings:** (a) Ray drives Codex TUI or Desktop interactively in this repo; (b) sdlc-dispatcher; (c) any codex process.

**❓ For Ray:** "Define coordinator as 'the process behind your plan attestation'. It is codex only when you drive the Codex TUI or Desktop in this repo *and* no Claude session is writing. `sdlc_team`/`codex_lane` never coordinate. Correct?" **Recommended: yes.**

## V6. What the pwf interim PR contains. MED

- **Q21 and Q25 do not line up.** Q21's "option 2" means *stop lanes planning*, but its note asks for the opposite. Q25 then chose "Bump + archive + pin".
- **The synthesis adds items (ord 289):** decide `PLANNING_DISABLED` for `sdlc_team` now, and a gitignore cleanup. Ray never ruled on either.
- **"Pin" is unspecified.** It could mean `PWF_PLAN_ROOT` in `.claude/settings.json` `env`, in mise `[env]`, or in the codex env. The Codex route fails closed unless the pin is a descendant of the working directory.
- **The KB side is unspecified.** KB is already on pwf 3.20.5. Does the interim touch KB at all?

**❓ For Ray:** "Does the interim also set `PLANNING_DISABLED=1` for `sdlc_team` (the lanes already see PLAN TAMPERED), or leave it until after extraction?" **Recommended: set it now. It is reversible, and it stops the false TAMPERED results.**

## V7. Program order: five orderings disagree. HIGH

The five orderings:
1. ord 109: a 9-step list.
2. ord 226: 5 steps for this session, plus an unordered program "mapped by /wayfinder".
3. Synthesis §E: steps 1–12.
4. ord 289: "Unblocked now" 1–6.
5. `task_plan.md` Current Phase: 9.1 → 9.1c → 9.1b.

Where they conflict:
- **Q9 is contradicted.** Q9 ruled the KB claude-code resync *Before codex*. §E puts the KB manifests (9) after codex (7).
- **Q5 is dropped.** Q5 ruled "claude-code 2.1.280 PR first". Neither §E nor ord 289 contains that PR, and neither contains the plugin-CLI pins PR (from Ray's ord 278 request).
- **Phase 9 is left hanging.** Nothing says whether 9.1c (the #45482 probe), 9.1b, and 9.2–9.13 are still next, deferred, or folded in. 9.13 "Enforcement hooks" overlaps with the codex-doctor and D1/D3 hooks.

**Proposed fix:** the handoff writes one numbered list marked "supersedes ord-109, ord-289, synthesis §E, and task_plan Current Phase". It also places Phase 9's remaining items explicitly.

**❓ For Ray:** "Proposed order: (1) claude-code 2.1.280; (2) plugin-CLI pins; (3) pwf interim; (4) KB deps; (5) KB graphify unfork; (6) KB manifests + resync (per Q9, before codex); (7) hk 2.0 ×2; (8) dotfiles deps; (9) codex native migration; (10) codex-doctor; (11) wrappers; (12) pwf design after extraction. Phase 9.1c/9.1b come after step 10. OK?" **Recommended: yes.**

## V8. The "shared understanding" was never confirmed, and "done" was never ruled. HIGH

- **The confirmation didn't happen.** At ord 228 Ray was asked "Does that summary match…?" He answered with a new request (Firecrawl Alexandria) instead of "Confirmed". The coordinator proceeded at ord 298 without re-asking. A post-/clear agent will treat ord 226 as ratified.
- **The "done" state was never ruled.** Q1 and Q29 asked for the done state ("ship, merge, land"). Both answers were about something else: task_plan location, and the verbs. "Land" as the end of each PR is the coordinator's assumption.
- **Q45 is ambiguous.** "Handoff after Fable proposal + first PR" could mean #1244, or the claude-code PR, which has not started.

**❓ For Ray:** "Is every PR done only when `mise run land` returns rc=0? And is this session's 'first PR' #1244, so it hands off now?" **Recommended: yes to both.**

## V9. "Update all mise and pyproject.toml dependencies so nothing is outdated" (Q10, Q11). MED

**Surfaces that may or may not be in scope:**
- host `mise.toml`
- `shared.toml` (`lock-shared`)
- image `mise-system.toml`/`mise-runtime.toml` (`lock-image`, with a CI rebuild of about 2.5 h)
- python and KB `uv.lock`
- GHA SHAs
- the base image digest
- Claude plugins
- vendored schemas
- user-global mise
- whether this is a one-time bump or a standing gate (`mise upgrade --dry-run-code` is probe-first)

Also, codex (V1) and graphify (the unfork PR) are special-cased, but nothing states that exclusion.

**Proposed wording:**
> "One-time bump to latest of every exact pin in host `mise.toml`, `shared.toml`, image mise files, and both `uv.lock`s, in both repos. Excluded: codex (native), KB graphify (its own PR), hk 2.0 (its own PR). Plugins, actions, and the base image are out of scope unless Ray adds them. No standing gate yet."

## V10. "Resync all sources", "docs later", and "deep extraction". MED

- **"All sources" is ambiguous.** Q31 "All pins, docs later" is `kb-update` with no argument, over all 99 sources. Does that include `agent-harness-docs`?
- **"Docs later" has no trigger or owner.** KB graphify is Claude-only, per memory.
- **"Docs later" conflicts with two rulings.** pwf needs *full* extraction before any pwf decision (Q14/Q20), and mattpocock is "full extraction" (Q37).
- **The graphify gap fixes have no status.** Nothing says whether the report's gaps G1–G8 (for example, `kb-build --code-only` drops `.md`) are in scope.

**Proposed wording:**
> "Docs later applies to every source *except* pwf and mattpocock, which get the full feature sequence immediately (graphify-features §14 steps). G1–G8 are filed as issues, not fixed here."

## V11. The codex gate's scope, and how Desktop gets its variable (Q16, Q17, D2). MED

- **"Block lanes" is undefined.** Which lanes: `codex_lane`, `sdlc_team`, fable `codex-implementer`, `codex:rescue`? And on which mismatch? If "record < latest release" blocks, every upstream release halts all codex work until a record-bump PR merges.
- **Q17 puts the Desktop bundle in the gate.** That bundle ships alpha builds through Sparkle and can't be controlled. Blocking on it would block forever.
- **D2 gives no mechanism for the Desktop variable.** A shell or mise export never reaches a GUI app (`do-not.md` #1). It needs `launchctl setenv` or a LaunchAgent, which is operator-only.

**❓ For Ray:** "The Desktop bundle is report-only (never blocks). Lanes block only on native CLI ≠ daemon version. Correct?" **Recommended: yes.**

## V12. Operator-only versus agent actions are scattered. MED

None of the following is in one list. **Operator-only:**
- `claude plugin update planning-with-files -s project` + restart
- `/hooks` trust after every `.codex/hooks.json` change
- `plan-attest`
- codex `install.sh` + `daemon update`
- user-global mise pin removal
- the Desktop env mechanism
- marketplace update to the latest mattpocock commit
- `stash@{0}` drop
- `python.uv_venv_auto`
- removing the four user-level skills

**User-invoked:** `/wayfinder`, `/to-spec`, `/to-tickets`, `/implement`, `/triage`, `/grill-with-docs`.

Put this list in the handoff.

## V13. Version literals frozen into the rulings. LOW

The rulings contain point-in-time values: `0.9.65`, `c55ee46`, `v3.20.5`, `v2.1.280`, `0.156.0`. They will be stale when the items run.

**Proposed wording:** "latest stable at implementation time (≥ the recorded value)". The one exception is where Ray meant exact.

## V14. Labels are reused and collide. LOW

- **"A"** means three things: codex Option A (native), pwf "A-enforced", and synthesis "codex-A PR".
- **D1–D6 in the synthesis ≠ D1–D4 asked of Ray.** Synthesis D2 = Desktop and D4 = profile-or-deny line up by number with what was asked, but D5 and D6 were never asked.

**Fix:** use descriptive names in the handoff, never bare letters or numbers.

## V15. Ray's "the required CLIs … on this repo" (ord 278). LOW

The audit covered dotfiles only. KB is behind on `ctx7`/`firecrawl`. `yt-dlp` is marked optional. So is KB in scope, and is `yt-dlp` in or out?

**Recommended:** both repos, and `yt-dlp` out.

---

**Also missing from `findings.md`:** the ord-344 answer on where the codex version is tracked (dotfiles `sources.toml` 41–46 plus `doctor.toml` native check; KB `currency.toml [tool.codex] expected`). Findings line 1967 records only the question.
