# codex-advisor review: /plan-attest and planning-with-files usage in dotfiles

Status: IN PROGRESS — writing incrementally.

## Task
Review how `/plan-attest` and the `planning-with-files` plugin are used in
dotfiles, verify the digest at attest-digest.md, and produce an operating plan
answering Q1-Q4 with findings, config diff, and unresolved items.


## FINDING A (high-value, self-caught): substring-match false positive in `plan-doctor.sh`, and in my own first probe

**Claim**: The plugin's own `plan-doctor.sh` diagnostic can report `WARN injection:
plan is attested but the hash mismatches` even when the attestation is
CORRECT and injection is clean — because it does a bare substring match
(`case "$OUT" in *'PLAN TAMPERED'*)`) on the full stdout of `inject-plan.sh`,
and `task_plan.md` itself currently quotes the literal string "PLAN TAMPERED"
as prose (documenting today's earlier incident). The quoted text is inside
the injected plan BODY, which is included verbatim in stdout between the
`===BEGIN-PWF-DATA...===`/`===END-PWF-DATA...===` markers.

**Probe + control arm**:
- Traced (`sh -x`) runs of `inject-plan.sh --context=userprompt`, 4x in a row:
  `ATTEST=$ACTUAL`, `TAMPERED=0` every time (`/tmp/trace{1..4}.log`).
- Untraced runs redirected to files (not `$()`) also produced byte-identical,
  3656-byte, `TAMPERED=0` output (`diff /tmp/out.log /tmp/plain1.log` →
  identical).
- My FIRST read of this (`grep -q "PLAN TAMPERED"` against the captured
  stdout) reported TAMPERED on 10/10 and 15/15 loop iterations. Root cause:
  the grep matched line 16 of the OUTPUT, which is inside the quoted plan
  body ("PLAN TAMPERED has fired on every prompt this session" — a sentence
  IN `task_plan.md` describing the earlier incident), not the hook's own
  `[planning-with-files] [PLAN TAMPERED — injection blocked]` sentinel line.
  `hand shasum -a 256 task_plan.md` vs `.plan-attestation` content matched
  throughout (`31784fd2...`) — the file was never actually mismatched.
- **Control arm**: I initially believed the check was flapping/racy (I wrote
  and then discarded that theory) — the `sh -x` vs plain-redirect comparison
  is the control that disproves it: identical bytes, my grep the only thing
  that varied (by matching different content depending on invocation
  incidentals... actually it did not vary — I mis-graded my own outputs by
  eye before diffing). The corrected finding: **there was never a real
  mismatch in this session; my probe (and `plan-doctor.sh`'s own probe) both
  have the same substring-match defect.**

**Severity**: Medium. `plan-doctor.sh` is the plugin's SHIPPED self-check
(`docs`/`README` position it as "answers: is the plan attested, and is the
attestation file where hooks look?"). Its own diagnostic can cry wolf on any
plan whose prose happens to mention the sentinel string — which is exactly
what a plan file honestly documenting a PAST tamper incident will do. This
generalizes: any plan-authoring convention that quotes hook output verbatim
(exactly what today's plan does, and what future incident-documentation in
plans will keep doing) makes `plan-doctor.sh` permanently unreliable for that
plan.

**file:line**: `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/scripts/plan-doctor.sh` (the `case "${OUT}" in *'PLAN TAMPERED'*)` branch, in the `[3] hook injection` section) vs `scripts/inject-plan.sh:1008/1034` (real sentinel: `[planning-with-files] [PLAN TAMPERED — injection blocked]`, always prefixed with the bracketed component tag — a robust match would grep for `\[planning-with-files\] \[PLAN TAMPERED`, not a bare substring).

**Recommendation implication for Q3**: if we ever wrap `plan-doctor.sh` in a
mise task/hook, do NOT trust its raw WARN/FAIL text as-is for this specific
line; either patch upstream (report it), or match only the real hook sentinel
line ourselves.


## FINDING B: attestation is NOT opt-in here — `.mode` = "autonomous" makes it mandatory

`.mode` (tracked, `.claude/CLAUDE.md`-adjacent repo file) currently contains:
`autonomous inject-smart` (verified: `cat .mode`, 24 bytes matches digest).

`inject-plan.sh` (case on `$MODE`, autonomous|gated branch):
```
NEEDS_ATTEST=0
case "$MODE" in
    autonomous|gated)
        [ -z "$ATTEST" ] && NEEDS_ATTEST=1
        ;;
esac
```
And `check-complete.sh:136-137`: the Stop gate itself only activates if `.mode`
contains the literal token `gate` — our `.mode` says `autonomous`, not `gate`,
so the Stop gate is advisory-only (confirmed: no forced-completion blocking).

**So two axes are being conflated by calling this repo "legacy mode":**
1. **File location** — legacy (root `task_plan.md`), confirmed by
   `resolve-plan-dir.sh` returning empty (no `.planning/`).
2. **Attestation semantics** — v3 `autonomous`, NOT legacy. In legacy-mode
   *semantics*, attestation is opt-in decoration (SKILL.md: "opt-in in legacy
   mode, default-on in v3 modes"). This repo has `.mode` = autonomous, so
   attestation is `NEEDS_ATTEST`-enforced: an UNATTESTED plan is fully
   blocked from injection, not just tampered-on-mismatch.

This raises the real stakes of "PLAN TAMPERED fired for days": it was not
cosmetic noise on top of an otherwise-working injection — once attestation
diverges, `.mode`'s autonomous flag means the SAME hard block applies whether
the cause is a hash mismatch OR no attestation at all. Any operating plan
must treat re-attestation as load-bearing for this repo, not optional polish.

**file:line**: `.mode` (repo root, tracked); plugin
`scripts/inject-plan.sh` (`NEEDS_ATTEST` case block, ~line 979-985) and
`scripts/check-complete.sh:136-137`.

## FINDING C: plugin's own docs say the concurrent-session failure mode we hit is KNOWN, NAMED, and has a shipped fix path we are not using

CHANGELOG v3.10.0 (`README.md:560`, verbatim): "Two sessions sharing one plan
directory could silently destroy each other's work (closes #217)... Both read
`task_plan.md`, both write it back, and the later write discards the earlier
one's phases... **Attestation could not cover it: it compares against a
baseline a human approved once, not against what the hooks last observed**...
The guard compares progress rather than hashes... checked items and completed
phases only go up during normal work, so a decrease means work is gone."

`docs/attestation-locking.md` (verbatim): "The fallback only matters for
legacy mode when two sessions write the same root attestation file... the
atomic rename keeps the attestation file valid, but it does not make the
shared plan file a safe parallel workspace... **Recommended parallel
workflow**: use slug-mode (`init-session.sh "<name>"` → `.planning/<slug>/`,
pin with `PLAN_ID=<slug>`)."

**This session's own team topology is a live instance of exactly this
scenario**: at least 7 named agents/sessions (main, advisor-887,
audit-codex-decl, cold-887, impl-887, premises-887, session-reviewer-905, plus
me) are addressable via SendMessage in this working directory, and (per the
digest) `task_plan.md` was rewritten by one session while other sessions'
plans/backlogs were the ones actually described in the STALE 106KB file
before today's rewrite — i.e., session `dotfiles-20260830.003`'s plan sat as
"the" `task_plan.md` while other, later sessions ran with a plan that wasn't
theirs. This is not hypothetical: it is the shape the plugin's authors
already named and already shipped slug-mode to fix.

**Control arm**: I have NOT yet verified whether all these named agents
share one CWD/git worktree vs separate worktrees — if they are separate
worktrees, each has ITS OWN `task_plan.md`/`.plan-attestation` and this
finding does not apply. **THIS IS UNVERIFIED — see Part 4.**


**Control arm result (Finding C)**: `git worktree list` shows exactly TWO
worktrees for dotfiles: the primary checkout (branch
`fix/image-lock-pr-control-arms-887`, where `task_plan.md`/`.plan-attestation`
live) and one other at a scratchpad path (`.../84f08a9b.../scratchpad/main-audit`,
detached HEAD). `find … -iname task_plan.md -o -iname .plan-attestation`
across the whole `ray-manaloto` tree at depth 3 returns exactly ONE pair, both
in the primary checkout. This session (codex-advisor) itself runs with
`Primary working directory: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
— i.e., in the SAME directory as at least the "main" session and presumably
several of the other named teammates (advisor-887, audit-codex-decl, cold-887,
impl-887, premises-887, session-reviewer-905) unless they were separately
given worktrees. **CONFIRMED, not hypothetical**: multiple agent sessions
sharing one legacy `task_plan.md`/`.plan-attestation` pair is this session's
actual live topology, not a theoretical risk. This is exactly the shape
CHANGELOG v3.10.0 (#217) was written to fix, and slug-mode is the plugin's own
prescribed remedy.

**Q2 verdict:** An agent must not attest its own plan edits by default, and attestation must never be automatic, background cleanup, or a handoff step. The argument for agent execution is operationally real: the agent authored the file, manual follow-through failed, and invoking the script removes friction. But it fails the plugin’s motivating threat model: the same principal could write malicious or mistaken content and immediately bless it. In this repo, “the operator reviews it in Git” is especially weak because the plan is gitignored. Automatic agent attestation would have “fixed” this incident by silently trusting the obsolete 106 KB plan—the alarm would disappear because the alarm had been disabled. The narrow exception is delegated execution after the operator approves an exact displayed diff and SHA-256 in the same turn, explicitly instructs the agent to run the script, no plan write intervenes, and the resulting stored hash is checked against the operator-approved digest. That is execution of a human decision, not agent self-approval. Otherwise the operator runs `/plan-attest`. The plugin’s human-approval model is explicit in its [security boundary](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/skills/planning-with-files/SKILL.md:448), and the command is deliberately [not model-invocable](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/commands/plan-attest.md:1).

## Q1 — Process ruling

The failure was not “somebody forgot a command.” Four process controls were absent:

- **No lifecycle owner.** A root-level plan survived its task, branch, landing, and multiple handoffs without anyone being responsible for retiring or replacing it.
- **A hard security state became background noise.** Handoffs copied the warning forward as a to-do rather than declaring the session blocked on an operator decision. That normalized a load-bearing warning.
- **No terminal condition.** “Run `/plan-attest` later” had no owner, deadline, or verification step. The mechanical command takes seconds; deciding that the bytes are trustworthy is the real operation.
- **Integrity was confused with semantic freshness.** A matching hash proves unchanged bytes, not that the plan belongs to the current task. Indeed, the currently attested plan still says attestation is “owed” at [task_plan.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:11). Those statements should be corrected to past tense and the corrected bytes re-approved.

The lane-routing ruling is directionally correct but too broad. The plugin defines [three distinct destinations](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/README.md:82):

| Information | Destination |
|---|---|
| Phases, checkboxes, current phase, next step, distilled decisions | `task_plan.md` |
| Research, analysis, evidence, technical findings | `findings.md` |
| Chronological lane outcomes, actions, errors, test results | `progress.md` |
| Machine-readable per-agent transitions in v3 mode | Per-agent ledger |

So the correct rule is: **lane returns do not get pasted into `task_plan.md`; route research to `findings.md`, execution/test history to `progress.md`, and let only the coordinator distill plan-changing consequences into `task_plan.md`.** That matches the plugin’s stronger v3 ownership model: workers append ledgers while the orchestrator owns the plan ([SKILL.md](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/skills/planning-with-files/SKILL.md:427)).

**Done when:** every deliberate plan edit follows `show exact diff + digest → operator approval → /plan-attest → mise run planning-check -- --strict`; a session may not hand off with a failed planning check; and a completed task’s plan is deactivated or archived instead of remaining the next session’s implicit root plan.

## Q3 — Automation ruling

I checked the shipped `plan-doctor.sh`. It is not suitable as an authoritative gate unchanged:

- It captures the full injected output and performs the bare substring match at [lines 69–99](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/scripts/plan-doctor.sh:69).
- Healthy output contains the plan body verbatim, so control words inside that body are indistinguishable from control output.
- It [always exits zero](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/scripts/plan-doctor.sh:17), making it diagnostic rather than gate-capable.
- Merely changing the match to the prefixed sentinel is insufficient: a plan can quote that full line too.

The upstream fix should classify only control output outside the framed payload—simplest is the exact first output line, because healthy injection emits the `DATA ONLY` preamble before any plan content. Its tests need three arms:

1. Clean, attested plan containing both the bare phrase and the complete sentinel line in its body → PASS.
2. Same plan modified after attestation → TAMPERED.
3. Autonomous plan with attestation removed → UNATTESTED.

Locally, do not wrap `plan-doctor.sh` and parse its prose. Add a narrow Python check that reuses the plugin’s own resolver/injector and the repo’s existing plugin-root resolver, then classifies the injector’s first line. This is justified custom code: the native self-check was examined and is nondiscriminating for the exact case being gated.

The implementation shape should be:

- `python/src/dotfiles_setup/planning.py`: resolution, configuration, integrity, and first-line injection classification.
- `mise run planning-check`: thin recurring entry point, with `--strict`.
- `doctor.py`: reuse that library during SessionStart; report drift but never attest.
- No new shell script.
- Upstream issue/PR for `plan-doctor.sh`; remove the local workaround only after the fixed plugin version is live and mutation-tested.

Adopt slug mode now, but ship it as a separate migration change from the doctor bug fix. The decision is no longer pending: the repository has both the exact multi-session topology slug mode addresses and a demonstrated wrong-task root plan. Independent tasks get independent worktrees/slugs; teammates collaborating on one task share its slug, with one coordinator owning `task_plan.md`. Slug mode’s limitation must remain explicit: without `PLAN_ID`, multiple independent plans inside one worktree still share `.active_plan`.

**Done when:**

```text
uv run --project python pytest tests/test_planning.py -q
mise run planning-check -- --strict
mise run doctor -- --verbose
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
```

The tests must include the three realistic arms above. Normal `mise run doctor` must stay silent when clean; `--verbose` must show clean `planning-*` checks.

## Q4 — Configuration ruling

- **`PWF_PLAN_ROOT`: do not set it globally.** It exists for a thread whose cwd is a shared parent of the real project, not for sharing planning state across worktrees ([README](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/README.md:435)). Pinning it to the primary checkout would make a scratch-worktree session consume the primary checkout’s plan—the opposite of isolation. A worktree with no planning files should resolve no plan; initialize a plan inside that worktree if it needs one.

- **`PLAN_ID`: do not put it in tracked `.claude/settings.json`.** A project-wide static value would send every session to the same slug. Before migration it is meaningless; after migration, use one active slug per worktree through `.active_plan`. Until a durable session-local binding compatible with this repo’s no-shell-export rule is established, two independent tasks must not share one worktree. Use separate worktrees.

- **Root mode: migrate now.** “Next time two sessions edit it” is not the trigger; the trigger already fired. The root artifact crossed task/session boundaries, and concurrent sessions share the directory. Implement the migration separately so resolution, initialization, cleanup, and control arms remain reviewable.

- **`PWF_INJECT`: set `"PWF_INJECT": "smart"` in `.claude/settings.json`.** Smart injection is project-wide policy and survives background launch there. Each slug can then use the plugin-native `--autonomous` initialization and its local `.mode` need only express `autonomous`. Retire the tracked root `.mode` during migration because it does not govern a resolved slug.

- **Gitignore: keep it.** The plugin itself treats these files as working memory, and tracking `.plan-attestation` while ignoring its input would create cross-checkout mismatches. Losing “restore from Git” is an accepted recovery tradeoff, not an integrity defect. This repo’s remedies are operator review/re-attestation or restoration from a deliberately retained archive. The current rationale at [.gitignore](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.gitignore:119) is sound.

Add `[planning]` to `doctor.toml` with reviewed declarations equivalent to:

```toml
[planning]
plugin_id = "planning-with-files@planning-with-files"
layout = "slug"
required_mode_tokens = ["autonomous"]
forbidden_mode_tokens = ["gate", "plan-guard-off"]
injection = "smart"
attestation = "human-approved"
```

Register these exact checks in `doctor.py`:

1. `planning-plugin-surface`: plugin enabled; active cache root resolves; required scripts exist; `plan-attest.md` retains `disable-model-invocation: true`.
2. `planning-layout`: any active plan resolves under the current worktree’s `.planning/<slug>`; `.active_plan` is valid and contained; legacy root plan/attestation/mode files are absent after migration.
3. `planning-integrity`: active `.attestation` exists, is valid SHA-256, and equals `task_plan.md`; mode contains required and no forbidden tokens.
4. `planning-injection`: one `--context=userprompt` invocation has a recognized exact first control line and valid framing; tampered, unattested, ambiguous, dark, or wrong-root results become findings.
5. `planning-settings`: `PWF_INJECT=smart`; no project-wide `PLAN_ID` or `PWF_PLAN_ROOT`; no automatic attestation command in SessionStart or another hook.

None of these checks may write an attestation. They detect and route the decision to the operator.

**Done when:** `mise run planning-check -- --strict` succeeds independently in every active worktree, each worktree resolves either its own slug or no plan, `mise run parity` passes after the settings change, and a scratch worktree never resolves the primary checkout’s plan.

## The one risk that would change the decision

The decision would reverse only if the plugin authors established that attestation is merely a corruption checksum—not a human-approval boundary against model-controlled writes—and that `disable-model-invocation` is unrelated to that boundary. The inspected v3.12.0 documentation says the opposite. If that premise were genuinely false, automatic agent attestation could become reasonable; while it remains true, it would delete the security property.

## Not verified in this sandbox

- Which named teammates have separate worktrees versus share the primary checkout.
- Whether Claude Code currently offers a durable, genuinely session-local `PLAN_ID` setting compatible with this repo’s prohibition on shell-export pins.
- The supplied repeated runtime counts, stored/current hashes, and timing measurements; I treated them as established as requested.
- The proposed mutation arms and mise gates: the read-only sandbox prevented `mise` from creating its log/temp state, so Graphify and mise-backed checks could not execute.
- No files were changed.


## Advisor note on the codex invocation

`--ephemeral --sandbox read-only --model gpt-5.6-sol -c model_reasoning_effort="xhigh"`,
prompt via stdin `-`, captured to `codex-verdict.md` — matches
`.claude/rules/ai-cli-invocation.md` exactly. The command ran past the 120s
foreground timeout and was moved to background by the harness; it completed
in ~514s with exit code 0 and a non-empty 11,821-byte verdict file (not a
truncated/failed run). One gap: the startup banner confirming "reasoning
effort: xhigh" was lost because the foreground pipe used `| tail -40` before
backgrounding — the flag was passed correctly per the invocation syntax, but
I could not visually confirm the resolved effort from the banner text itself.
Treat that single confirmation as unverified; the mechanism (the `-c` flag,
which is what actually sets it) is not in question.

## STATUS: DONE — sending summary to team-lead now.
