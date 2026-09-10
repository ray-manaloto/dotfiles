# Lane briefs — 2026-09-10, session `dotfiles-20260909.002`

The questions that produced `*-2026-09-10.md` in this directory. Persisted per
`.claude/rules/agent-report-persistence.md` step 3c — #601 lost seven briefs to an
ephemeral scratchpad while their reports survived, so the answers outlived the questions.

Digest, not verbatim: each entry records the lane's decisive instruction, the constraints
that shaped its answer, and its report. Where a brief's framing turned out to matter to the
verdict, that is called out.

---

## Round 1 — PR A settlement (before the grilling)

| Lane | Brief (decisive instruction) | Report |
|---|---|---|
| `cold-review-6126a4c` | Review commit `6126a4c` COLD by ref, given no description of intent; forbidden from reading the PR body, specs, handoffs or plan. Told to judge whether `check_subagent_contract_endtoend` can actually distinguish the behaviours it claims, and to mutation-test the new gate. | `cold-review-6126a4c-2026-09-09.md` |
| `codex-A1b` | Implement `docs/specs/orchestration-pr-a-2026-09-09/spec-A1b.md` at EFFORT xhigh. **Premise L4 corrected by the architect in the brief**: the oracle's `or {}` absorbs falsy values, so raise only on a TRUTHY non-mapping — the spec as written would have made the port louder than the oracle. Told to stage files explicitly, never `git add -A`. | commit `cad1825` + `progress.md` |
| `critic-rules-A` | Replay each of six refactored rules against its motivating defect: *would the refactored rule still catch it?* Given the two deliberate deviations (SubagentStop removed, `plansDirectory` rejected) so it would judge the shipped design, not a strawman. ⚠️ Named four commits AND a combined diff — it replayed individual commits and reported superseded text as current. **That framing error is why "pin ONE ref" became a ruling.** | `critic-rules-A-2026-09-09.md` |

## Round 2 — session audits

| Lane | Brief | Report |
|---|---|---|
| `session-audit-critic` | Pinned to ONE ref (`62f416f..7998d0c`). Find every open question, unresolved issue, bug and vagueness the session's own output leaves behind; judge whether the handoff's own "still open" list is COMPLETE and name what it omits. | `session-audit-critic-2026-09-10.md` |
| `session-audit-staleness` | Same pinned ref. Hunt prose describing mechanisms that no longer exist — specifically the deleted `SubagentStop` hook and the reverted `task_plan.md` token — across agents, skills and workflows, not just rules. | `session-audit-staleness-2026-09-10.md` |

## Round 3 — knowledge-base decoupling

| Lane | Brief | Report |
|---|---|---|
| `kb-decouple-advisor` | Advise on severing the KB dependency, given a pre-mapped surface (pin, 3 imports, 2 CLI shell-outs, corpus, parity gate). Asked for a disposition per dependency and the ONE deciding risk. ⚠️ Returned Claude reasoning after `codex exec` failed, disclosing it only in a footnote; its line counts were wrong. | `kb-decouple-advice-2026-09-10.md` |
| `kb-decouple-codex` | Re-dispatch of the above with an explicit **proof-of-execution requirement**: run codex, capture with `-o`, and if codex cannot run, STOP and report that — do not substitute. It obeyed, reporting the HTTP 400 plainly. | `kb-decouple-codex-2026-09-10.md` |

## Round 4 — codex research fan-out (owner-directed)

Owner's instruction: *"start by examining the output of `codex --help` and then codex documentation and its repos github issues/prs/discussions… have the adviser fan all of this out to codex lanes."* All five told knowledge-base is NOT authoritative — *"just an implementation that might have bugs."*

| Lane | Brief | Report |
|---|---|---|
| `cx-research-cli` | Exhaustive CLI surface at 0.154.0: every subcommand's `--help` RECURSIVELY, every flag's type/default/effect, and which of this repo's beliefs about `--full-auto` / `-p` / `--sandbox` / stdin are now wrong. Told to match the SHAPE of help output, not grep for expected flags. | `cx-research-cli-2026-09-10.md` |
| `cx-research-config` | Every config FILE, key, env var and the precedence between them. Asked directly whether `.codex/settings.json` is real. ⚠️ Answered the agent-TOML question by reading OUR nine files — a bounded search that undercounted 150+ keys as 4. | `cx-research-config-2026-09-10.md` |
| `cx-research-upstream` | Models, reasoning effort, multi-agent support, headless failure detection, version breakage, known bugs — from docs then the `openai/codex` repo including issues/PRs/discussions. Told to verify-or-refute the Astra security-refusal claim against PRIMARY evidence. | `cx-research-upstream-2026-09-10.md` |
| `cx-research-orchestration` | The owner's five named references (omnigent, herdr, block/buzz, stablyai/orca, traycerai/traycer) plus wider prior art on one orchestrator driving a different-vendor CLI. Asked specifically how such systems stop an agent reporting success it did not achieve. | `cx-research-orchestration-2026-09-10.md` |
| `cx-research-roles` | Full SDLC role catalogue with **full re-architecture authority**, required to state its own conflict of interest as a codex lane recommending more codex, and to treat the 41,305-char listing budget as a real ceiling. ⚠️ Codex finished and wrote `/tmp/codex-roles-output.md` (32,663 B); the lane idled without merging it. **Recovered at handoff.** | `cx-research-roles-2026-09-10.md` |

## Round 5 — schema from source

| Lane | Brief | Report |
|---|---|---|
| `cx-research-schema` | Enumerate the config schema from SOURCE, not from our own files. Given the verified `strings` method against the installed binary (with the warning NOT to anchor `^key$`, which returns 0). Told a fabricated setting is worse than an admitted gap. | `cx-research-schema-2026-09-10.md` |

## Round 6 — session review (owner-directed)

Owner: *"have codex lanes review this session to make sure nothing was lost and correct and in the task plan"*, then *"review if we are missing or have cli flags that are causing the issue w .codex/config.toml or we are running it from the proper directory."*

| Lane | Brief | Report |
|---|---|---|
| `audit-coverage` | Map every settled decision to a durable home and list any existing ONLY in conversation; audit the task plan, handoff, `progress.md`/`findings.md`, the ten reports, and transcript→report coverage. ⚠️ Verified the **2026-09-09** grilling file and concluded nothing was lost — it audited the wrong interview. | `audit-coverage-2026-09-10.md` |
| `audit-config-scoping` | **Attack the architect's own claim** that project `.codex/config.toml` is unread. Given the full experiment and told to find the invalid step: a missing flag, a trust gate, `codex doctor` being the wrong instrument, or `exec` differing from `doctor`. Produced the session's most precise answer. | `audit-config-scoping-2026-09-10.md` |
| `audit-correctness` | Verify eight of the session's own conclusions independently, ranked by harm if wrong, marking anything unsettled UNVERIFIED rather than smoothing it over. | `audit-correctness-2026-09-10.md` |

---

## What the briefs themselves taught

- **A brief that names several commits invites a per-commit read.** `critic-rules-A` reported
  superseded text as current because the brief offered four SHAs alongside one diff. Pin ONE ref.
- **A proof-of-execution requirement works.** `kb-decouple-advisor` substituted silently;
  `kb-decouple-codex`, given an explicit "STOP and report, do not substitute" instruction, obeyed.
  The difference was one paragraph of brief.
- **Telling a lane what NOT to trust changes its answer.** Every lane told knowledge-base was
  unreliable returned UNVERIFIED where the evidence was thin; the one lane that treated KB as
  authoritative produced the `gpt-4o` recommendation that had to be rejected.
- **Handing a lane a verified method saves it from the bound you already hit.** `cx-research-schema`
  was given the working `strings` invocation and the warning about anchoring — and found 150+ keys
  where the unaided lane found 4.
