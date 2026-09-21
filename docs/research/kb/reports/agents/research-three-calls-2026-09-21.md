# Research: three design calls for a repo-owned Codex-lane dispatcher

**Agent:** research-three-calls · **Date:** 2026-09-21 · **Mode:** read-only research (writes confined to this report and `.agent/kb/raw/three-calls/`)

**Status:** COMPLETE. Raw sources under `.agent/kb/raw/three-calls/`.

## Scope

Three decisions for a repo-owned entry point dispatching OpenAI Codex CLI lanes from a Claude Code architect session (spec -> codex implements -> cold review -> respec):

1. Round budgets (per-phase counters vs a single respec bound vs both)
2. Reviewer session reuse (fresh reviewer per round vs `codex exec resume <id>`)
3. Worktree provisioning of gitignored per-machine files for parallel lanes

## Source-chain disposition (which step answered what)

| Step | Result |
|---|---|
| **00. KB offline vendor docs** (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/{claude-code,codex}`) | **Answered the majority.** Both vendors' worktree + `.worktreeinclude` semantics, `codex exec resume` docs, Anthropic's only iteration primitive (`maxTurns`). |
| **0. `docs/research/mintlify-cache/`** | **MISS, and correctly so.** Cache holds only `devcontainers/ jdx/ knowsuchagency/ starship/ twpayne/ wagoodman/ yeachan-heo/` — no `openai` or `anthropic` tree. `docs/research/mintlify-catalog.md:145` records `openai/codex` as **`queued`**, never fetched. |
| **Live CLI probe** (`mise exec -- codex …`) | **Answered call 2's flag question decisively** (both arms). |
| **Repo artifacts** (`docs/research/kb/reports/agents/*-1202-*`) | **Answered call 1's empirical half** — per-round severity counts below. |
| **GitHub raw fetch** (`chaseai-yt/claudex-loop`) | Answered call 1's and call 2's practitioner half, with a 404 control arm. |
| **graphify** | **UNAVAILABLE — `stale`.** `mise run graphify-query` rc=3: *"graph was built at ff2fbaf7, HEAD is 8474043d (33 commit(s) behind)"*. Per `graphify-first.md` this is a fall-back-to-source state, not an empty answer. All repo claims below are from direct reads. |
| Plugin skills (`context7`, `exa`, `firecrawl`, `last30days`) | See "Practitioner sweep" — recorded per-tool below. |

---

## Call 1 — Round budgets

### What the two prior-art systems actually do

**claudex-loop** (`chaseai-yt/claudex-loop`, `main`, fetched 2026-09-21; 404 control arm on a bogus path returned 404 while the three real paths returned 200) carries **three independent counters**:

| Knob | Default | Meaning — verbatim |
|---|---|---|
| `rounds` / `MAX_ROUNDS` | `5` | "Completed plan-review round cap" (`README.md:126`) / "Maximum completed plan-review rounds" (`skills/claudex-loop/SKILL.md:33`) |
| `MAX_FIX_ROUNDS` | `2` | "Build-fix attempt cap" (`README.md:127`) / "Bounded build-fix attempts before reporting or taking over" (`SKILL.md:38`) |
| `MAX_INSPECTION_ROUNDS` | `2` | "Initial inspection plus one reinspection" (`README.md:128`) |

Crucially the counters are **not** the primary stop condition — they are the backstop behind a **verdict**:

> "Stop at the round budget **or an explicit verdict**: `APPROVED`, `REVISE`, or `BLOCKED`." — `README.md:63`

> "`BLOCKED`, execution failures and exhausted round budgets are **surfaced rather than converted to approval**." — `README.md:137`

> "Stop at `MAX_ROUNDS`. Present unresolved findings and the host's position **instead of manufacturing convergence**." — `SKILL.md:78`

And an explicit anti-metric:

> "Zero findings is valid; **a large number of findings is not a quality score**." — `README.md:137`

Its own reported field run: "The first reported end-to-end CRM planning run produced **55 findings over five rounds**; it is an illustrative run, not a controlled benchmark" (`README.md:153`). Note that is *the cap being hit*, published as an illustration rather than as convergence.

**fable-orchestrator 1.21.0** (local: `~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0/skills/orchestration/SKILL.md`) carries **one** bound:

> "**Findings** — refutation pass, cited-first in severity order; **max two respec rounds**, then surface residuals to the user." — `SKILL.md:18`

> "bound the loop: after **two respec → re-implement → re-review rounds on the same diff**, stop and surface the residual findings to the user with your recommendation instead of thrashing." — `SKILL.md:174`

The design rationale is the part worth copying, and it is not "cost control". The bound is deliberately set **below** the expected settle point so that hitting it is a **diagnostic signal**:

> "with premises verified and outcomes specced, **most diffs settle within zero or one respec round, comfortably inside the two-round bound** … **routinely hitting the bound is the signal that premises are going unverified**." — `SKILL.md:30`

> "Field-measured on a single branch: **five unread premises cost three heavy respec rounds**, against roughly four file reads at spec time." — `SKILL.md:28`

Two further clauses show the counter is *semantic*, not per-phase: a **dissent** consumes a round ("a dissent-triggered respec counts toward the two-round bound", `SKILL.md:125`) and a **dangling artifact path** does too ("The remedy is a corrected spec … so a dangling path costs a round", `SKILL.md:118`).

### What the vendors say about iteration limits

**Anthropic**: the only documented iteration primitive is `maxTurns` — a *tool-use round-trip* budget, not a semantic phase budget. Agent SDK TypeScript `:445` "Maximum agentic turns (tool-use round trips)"; plugin agent frontmatter accepts `maxTurns` (`plugins-reference.md:61,68`). Its documented **semantics are failure, not convergence**: exceeding it yields `subtype: "error_max_turns"` and `terminal_reason: "max_turns"` (`agent-sdk__typescript.md:1313`, `:1353`), and the documented recovery is *"The first run ended with `error_max_turns` … **resume with a higher limit**"* (`agent-sdk__sessions.md:220`). It is also explicitly leaky: *"Hooks may not fire when the agent hits the `max_turns` limit because the session ends before hooks can execute"* (`agent-sdk__hooks.md:766`).

**No Anthropic or OpenAI guidance on semantic review-round or fix-round limits was found in the offline corpus.** Control arm: the same grep shape (`grep -rn "SendMessage" $CC`) returns hits in three files, so the search discriminates; `iteration limit` / `stop condition` return only the `maxTurns` rows above. Label: **UNSOURCED at the vendor level** — this is a practitioner-convention question, not a documented-API question.

### What THIS repo measured — the #1202 loop, three rounds

Counted directly from the persisted per-round reports (`docs/research/kb/reports/agents/`). Cold review is by ref, so each round reviews the fix the previous round caused.

**Cold review findings by severity per round:**

| Round | Reviewed ref | HIGH | MED | LOW | INFO | **Total** |
|---|---|---|---|---|---|---|
| R1 | `b7a3b1df` | **2** (F1, F2) | 3 | 6 | 1 | **12** |
| R2 | `b7a3b1df` → `54798c57` | **0** | 3 | 6 | 4 (2 of them POSITIVE) | **13** |
| R3 | `54798c57` → `8474043d` | **0** | 2 | 3 | 2 (+1 POSITIVE) | **7** |

Three things fall straight out of that table, and they point in different directions:

1. **Max severity decayed monotonically and fast**: 2 HIGH → 0 → 0. The two HIGHs were both session-bricking (`F1`: a non-null non-enforcing refresh "**permanently disarms the gate for the rest of the session**"; `F2`: the deny-path refresh exceeding the 10,000 ms `HookBudget`, measured 10.04 s / 9.73 s against a 2.91 s control). Both were gone after one round.
2. **Total count went UP in round 2** (12 → 13) while severity went down. **A count-based stop would have read round 2 as divergence and been wrong.** This is claudex-loop's "a large number of findings is not a quality score" observed locally.
3. **Round 3 still found two MEDIUMs, and one of them was a regression introduced by round 2's own fix**: `cold-review-1202-r3:24` — *"Fail-open regression at ESTABLISHMENT: a SessionStart report with `verdict:"invalid"` plus a PRESENT non-boolean `enforcement_eligible` **denied at base and passes at head**, for the whole session. No test arm covers it."* Its sibling `:23` is the same shape (an undecodable `doctor.toml` newly reported as `verdict:"ok"` — *"at base the same file raised"*).

Point 3 is the load-bearing one for this decision: **the loop was not asymptotically approaching zero — each fix round was a new diff with its own new defects.** A budget cannot be justified as "we're nearly converged"; it is justified as "the marginal finding is getting cheaper to live with than the marginal round is to run."

**Premise verification rounds** show the same decay in *kind* rather than count:

| Round | Character of findings |
|---|---|
| premises R1 | "two rows are **REFUTED** and there are **eight unlisted premises, three of which I'd call blocking**" (`:1`). L11 refuted outright — the mirror-parity premise the spec rested on. |
| premises R2 | All listed rows CONFIRMED; residue is **citation drift** ("line range off by 2", "off by one"). One new blocking-ish MISSING (`M4`, an absent-`doctor.toml` brick). |
| premises R3 | One REFUTED — **and it is a citation, not a fact**: "`L5` REFUTED as cited — the sentence is at `:4173-4175`, not `:4170-4172` … **Substance is correct**" (`:11`). Four MISSING, one blocking-ish (`M1`). |

So premise verification kept paying out in **every** round, but the payout shifted from *refuted premise* (round 1) to *wrong line number in a premise that was true* (round 3). That is the decay curve a budget should be keyed to.

### The measurement the repo also produced, which cuts against pure counting

`premises-1202-r3:52` records the round-2 lesson recurring: *"Writing the fix against the current fake, and 'proving' it with an arm that runs on the same fake, would certify the fake — **the round-2 lesson recurring**."* A round that re-certifies its own fixture produces findings without producing assurance. A counter cannot see this; only a per-round judgement can.

### Options

**(a) Per-phase counters only (claudex-loop's 5/2/2).**
- FOR: each phase has a genuinely different cost and decay curve — plan review is cheap and high-yield (hence 5), build-fix is expensive and low-yield (hence 2). Separate counters stop the cheap phase being starved by the expensive one. Mechanically checkable; a `runner.py` can enforce it.
- AGAINST: three knobs is three things to tune with no local data behind any of them, and claudex-loop's own published run **hit** the 5 cap, so `5` is not a validated settle point. Counters alone cannot see the round-3 pattern this repo measured (new defects introduced by the fix).

**(b) Single respec bound only (fable-orchestrator's 2).**
- FOR: matches this repo's measured shape — the dangerous findings were gone after one round; rounds 2 and 3 traded MEDIUMs. The bound-as-diagnostic framing (`SKILL.md:30`) gives the number a *meaning*, so hitting it is actionable ("premises are going unverified") rather than merely terminal. One knob; already the doctrine every lane in this repo runs under.
- AGAINST: it is a bound on **one** phase. The #1202 loop had *three* distinct loops running (premise verification, implementation/gate, cold review), and only the review loop is bounded by it. Nothing bounded the premise rounds, and they ran three deep.

**(c) Both — a semantic respec bound plus per-phase caps as a backstop.**
- FOR: the two do different jobs. The respec bound is a **judgement checkpoint** (stop, surface residuals, recommend); the per-phase caps are **runaway protection** for a lane that never terminates. claudex-loop already has exactly this layering — the verdict is primary and the counter is the backstop (`README.md:63`, `:137`). Anthropic's own `maxTurns` is the same shape: a valve that reports as an *error*, recoverable by resuming with a higher limit.
- AGAINST: more machinery than the measured problem needs. This repo has never recorded a lane that failed to terminate for lack of a counter — the failures recorded are *transcript degradation* (`SKILL.md:149`, from ~144k tokens) and *timeout* (`TIMEOUT:` line, 1800 s implementation / 600 s review defaults, `SKILL.md:129`), both of which are already bounded by other mechanisms.

### Recommendation — supported

**Carry one semantic respec bound (2) as the stop condition, plus a verdict that can stop earlier, and NOT a set of per-phase counters.** Three legs of evidence support it:

1. The repo's own severity table: max severity hit zero after **one** round, and every round after that traded MEDIUMs while introducing new ones. A bound of 2 sits exactly where the marginal round stops buying severity reduction.
2. Both prior-art systems agree the counter is the **backstop**, not the criterion — claudex-loop's verdict (`APPROVED`/`REVISE`/`BLOCKED`) is primary, fable-orchestrator's bound is a diagnostic. A dispatcher that only counts has thrown away the signal.
3. The count **rose** in round 2 while severity fell. Any stop keyed to finding-count would have fired wrongly. Key the stop to **max unrefuted severity**, not to count.

**What is NOT supported, and what would settle it.** Whether the *premise-verification* loop needs its own bound is genuinely open: it paid out in all three rounds here (n=1 branch). The measurement that would settle it: instrument the next N loops to record, per premise round, `(rows REFUTED on substance) vs (rows REFUTED on citation only) vs (MISSING marked blocking)`. If substance-refutations reach zero by round 2 across several branches while citation drift persists, the premise loop's stop condition is "zero substance refutations", not a count. The three #1202 rounds are one sample of exactly that curve (2 substantive → 0 substantive → 0 substantive, citation-only), which is suggestive and nothing more.

**One design detail worth lifting verbatim from fable-orchestrator**: make the *reasons a round is consumed* explicit. A dissent costs a round (`SKILL.md:125`); a dangling spec-file path costs a round (`SKILL.md:118`). Without that, a dispatcher silently gives free retries to exactly the failures that should be expensive.

---

## Call 2 — Reviewer session reuse (fresh vs `codex exec resume`)

### What the pinned CLI actually accepts — first-party, both arms

Probed live on the pinned CLI, **codex-cli 0.154.0** (`mise exec -- codex --version`). Raw help saved to `.agent/kb/raw/three-calls/codex-0.154.0-exec-and-resume-help.txt`.

`codex exec` has **four** subcommands, not one — and two of them bear directly on this decision:

```
Commands:
  resume  Resume a previous session by id or pick the most recent with --last
  fork    Fork a previous session by id into a new session
  review  Run a code review against the current repository
```

**`resume` rejects flags `exec` accepts.** Control arm first, then the subject:

| arm | command | result |
|---|---|---|
| **CONTROL** | `codex exec -s read-only --help` | **rc=0** (flag accepted) |
| subject | `codex exec resume --last -s read-only -` | `error: unexpected argument '-s' found` |
| subject | `codex exec resume --last -C . -` | rejected |
| subject | `codex exec resume --last --add-dir /tmp -` | rejected |
| subject | `codex exec resume --last -p foo -` | rejected |
| subject | `codex exec resume --last --approve-for-me -` | rejected |

The full set `resume` drops relative to `exec`: `-s/--sandbox`, `-C/--cd`, `--add-dir`, `-p/--profile`, `--approve-for-me`, `--oss`, `--local-provider`, `--color`, `-i` (narrowed from `<FILE>...` to `<FILE>`). It **keeps** `-c/--config`, `-m/--model`, `--json`, `-o/--output-last-message`, `--worktree`, `--ephemeral`, `--enable/--disable`, `--strict-config`, `--ignore-user-config`, `--ignore-rules`, `--output-schema`, `--skip-git-repo-check`, `--thread-source`, and the two `--dangerously-*` flags.

> **Corrects a practitioner claim.** The SmartScope write-up states *"the `-o` (file output) flag is unavailable with `resume`, so stdout must be captured instead"*. That is **false at 0.154.0** — `-o, --output-last-message <FILE>` is present in `codex exec resume --help`, quoted above. Treat it as version drift, and prefer `-o` here (the repo's `ai-cli-invocation.md` already bans trusting streaming stdout as the durable result).

**`exec fork` is the third option nobody in the brief named.** `codex exec fork <SESSION_ID> [PROMPT]` — "Fork a previous session by id into a new session". It has the same flag surface as `resume` (also no `-s`). It is the "branch the reviewer's context" primitive — relevant if you ever want round N+1 to start from round N's context *without* accumulating round N's rebuttals.

**`exec review` is a first-class review subcommand.** `codex exec review [--base <BRANCH>] [--commit <SHA>] [--uncommitted] [--title <TITLE>]`, plus `--output-schema <FILE>`. Per `use-tool-builtins.md` this deserves an explicit evaluation before any hand-rolled review prompt: it takes the review-by-ref selector natively, which is exactly the cold-review contract this repo already runs (`cold-reviewer` reviews by ref). Note it exposes **no `-s`** either — review is read-only by construction.

### The sandbox trap, and why it is worse on THIS machine than upstream

Upstream `openai/codex` **issue #40149** (verified **open** via `gh api`; control arm `#99999999` → HTTP 404) is titled, verbatim:

> "`codex exec resume` rejects `-s/--sandbox`; a resumed turn wrote a file that `-s read-only` had blocked"

Its measurement is control-armed the way this repo requires — a positive-control phase where the canary file *must* appear, and the verdict read off the filesystem rather than the model's self-report:

| phase | command | file on disk |
|---|---|---|
| 0 | `exec -s workspace-write` (positive control) | **created** |
| 1 | `exec -s read-only` | not created |
| 2 | `exec resume` **without** `-c sandbox_mode` | **created** ← the bug |
| 3 | `exec resume -c sandbox_mode="read-only"` | not created |

It also records the trap that makes it invisible: *"The model answered 'BLOCKED' in every phase where it had attempted nothing at all."* A reviewer's own report cannot tell you what sandbox it ran under.

**I did not reproduce phase 2 here** (it requires a write-capable run; labelled third-party-measured, not re-derived). But the consequence on this host follows from facts I did read:

- `~/.codex/config.toml:6` sets **`sandbox_mode = "danger-full-access"`**, with `approval_policy = "never"` at `:4`.
- `.claude/agents/codex-sol-implementer.md:93-95` already records this: *"`~/.codex/config.toml` already sets `sandbox_mode = "danger-full-access"`, so every un-flagged codex call on this machine already runs this way."*

So the escalation upstream measured against *CLI defaults* would here escalate to **`danger-full-access`**: a reviewer opened `-s read-only` in round 1 becomes an unrestricted writer in round 2 unless every resume carries `-c sandbox_mode="read-only"` explicitly. Two independent practitioners report exactly this non-inheritance, in the same direction:

- `shaharsha/claude-skills` `skills/codex-review/README.md`: *"A session created with `-s read-only`, on resume, reported `sandbox: danger-full-access`, silently picking up the global config. The script therefore passes `-c sandbox_mode="read-only"` on **every** invocation, resume included."*
- `AgathaCrystal/skills` `skills/gpt-review/SKILL.md`: *"Pass `--dangerously-bypass-approvals-and-sandbox` on every call, including `resume`. **It is NOT inherited across sessions**."*
- `garrytan/gstack` **issue #1258** (verified **open**): the same `-C`/`-s` rejection, fixed by moving to `-c 'sandbox_mode="read-only"'`.

**A second, quieter failure mode:** `openai/codex` **issue #19661** (verified **open**) — *"`codex exec resume` fails with 'Missing required parameter: input[N].encrypted_content' after internal 'thread not found' (rollout intact)"*, and gstack #1258 records the 0.125.0 behaviour where resume **silently starts a new session** when the thread is not found. A resume that silently becomes a fresh session is a probe that cannot report its own failure — it returns a plausible review with none of the continuity you paid for.

The mitigation is already demonstrated in prior art: `claudex-loop`'s `runner.py:238-239` refuses a mismatch outright —

```python
if expected_session and session != expected_session:
    raise RunError("CLI resumed a different session; refusing its result.")
```

### What claudex-loop actually does (and it is not "always resume")

`skills/claudex-loop/SKILL.md:70`:

> "First round creates a session. Further rounds use `--resume <previous-successful-result.json>` with the same provider/model/effort and a host-authored `--feedback` file containing dispositions. **Never use a guessed session id, `--last`, or a build session as a reviewer.**"

And `references/runtime.md:29`:

> "`--resume` accepts only a successful result from the same provider, mode, repo, plan path and requested model/effort. It resumes that exact UUID and checks the returned UUID. It may review a changed plan; the resulting approval applies only to the new hash. **An inspection always starts fresh.**"

That last clause is **mechanically enforced**, not merely documented — `runner.py:289-290`:

```python
if args.mode == "inspect" and (not args.base or args.resume):
    raise RunError("Inspection requires --base and a fresh session (no --resume).")
```

And its sandbox workaround is precisely the `-c` route, `runner.py:149-151`:

```python
args = ["exec"] + (["resume", session] if session else [])
args += (["-c", 'sandbox_mode="read-only"'] if session and review else
         ["-c", 'sandbox_mode="workspace-write"'] if session else …)
```

So claudex-loop's actual rule is a **split**: resume across rounds of reviewing *the same artifact under revision* (plan review); **fresh** whenever the object or the phase changes (code inspection). `SKILL.md:88` extends it — if the coordinator itself wrote code, *"Require a fresh other-provider inspection of its changes; never describe the earlier inspection as covering later edits."*

### The published evidence on fresh-vs-resumed review

Three papers the `shaharsha` README cites. I verified all three exist and **re-derived the numbers from the arXiv abstracts myself** rather than repeating the README (control arm: bogus id `9999.99999` → 0 entries; known-real `1706.03762` → 1 entry, "Attention Is All You Need"):

| ID | Title | What its abstract actually says |
|---|---|---|
| **2603.12123** | *Cross-Context Review: Improving LLM Output Quality by Separating Production and Review Sessions* | 30 artifacts, 150 injected errors, 360 reviews, 4 conditions. **CCR (fresh session) F1 28.6%**, beating same-session Self-Review **24.6% (p=0.008, d=0.52)**, repeated Self-Review **21.7% (p<0.001, d=0.72)**, context-aware Subagent Review **23.8% (p=0.004, d=0.57)**. |
| **2602.01011** | *Multi-Agent Teams Hold Experts Back* | Self-organizing LLM teams "consistently fail to match their expert agent's performance, even when explicitly told who the expert is, incurring performance losses of **up to 41.1%**"; cause is *"integrative compromise — averaging expert and non-expert views"*, which **increases with team size**. |
| **2604.19049** | *Refute-or-Promote: An Adversarial Stage-Gated Multi-Agent Review Methodology…* | 31-day campaign, 7 targets: the pipeline **killed ~79% of 171 candidates** before disclosure. *"cold-start reviewers are intended to reduce anchoring cascades; cross-family review can catch correlated blind spots that same-family review misses."* Its headline failure: **"ten dedicated reviewers unanimously endorsed a non-existent Bleichenbacher padding oracle … killed only by a single empirical test."** |

> ⚠️ **One inherited claim does NOT survive re-derivation.** The `shaharsha` README says *"Reviewing twice in the same context is **worse** than reviewing once (F1 21.7 vs 28.6)."* The paper's own abstract says the opposite about that specific comparison: *"reviewing twice in the same session **did not beat** reviewing once (**p=0.11**)"* — SR2 (21.7) vs SR (24.6) is **not** a significant difference, and the 28.6 the README compares against is CCR, a different condition. What the paper establishes is that **fresh-session review beats all three same-context conditions**; it does not establish that re-reviewing in-context is actively harmful. Use the first claim, drop the second.

### What this repo measured

`docs/research/kb/reports/agents/feature-review-fable-2026-09-21.md:110` already scored this row and landed on **DROP**, with two local reasons:

> "Conflicts with fresh-lens discipline that D shows working: **cold r2 was a FRESH agent and still self-corrected r1** via `memory: local` (`cold-review-1202-r2:17,23-27`). B also measured wrapper degradation from ~144k tokens (`B/SKILL:149`). One useful crumb: `resume` rejects `-s`, needs `-c sandbox_mode=` (`A/runner.py:150-152`)."

That first point is the interesting local measurement and it is visible in the round-2 report itself: `cold-review-1202-r2` F11 opens *"the harness fake now matches `FsStat` on the dangling-symlink case **my round-1 review flagged**"* — a fresh agent with `memory: local` retained the finding-level continuity that resume is supposed to buy, **without** carrying round 1's transcript. Claude Code's `memory: local` writes to `.claude/agent-memory-local/<agent-name>/` (`agent-artifact-conventions.md`), and A-1 already grants it to `cold-reviewer`.

The countervailing fable-orchestrator measurement (`SKILL.md:149`) is worth stating in full because it bounds reuse rather than banning it:

> "Reuse within a task is bounded too: respec rounds accumulate transcript, **degradation has been field-observed from ~144k tokens, and ~200k is the working ceiling** — settle the wrapper and dispatch a fresh one for the next round before its transcript reaches that range; the corrected spec and the diff ref travel to the new wrapper, **the degraded end-of-task discipline does not**."

### Options

**(a) Fresh reviewer every round.**
- FOR: the only condition with a *controlled* result behind it (2603.12123: F1 28.6 vs 24.6/23.8/21.7, all p<0.01). Sidesteps the resume sandbox escalation entirely — there is no second turn to mis-flag. Sidesteps #19661's silent-new-session failure. Matches this repo's cross-family cold-review doctrine and the anchoring argument in 2604.19049. Locally demonstrated to retain the useful continuity via `memory: local`.
- AGAINST: the reviewer re-reads the diff each round (cost), and nothing in-band verifies "was my round-1 finding actually fixed?" — the coordinator owns that, which is more architect work. 2604.19049's 79% kill rate says most findings are false positives, so re-adjudicating from scratch each round is real cost.

**(b) Resume the same reviewer across rounds.**
- FOR: the reviewer can check its own prior findings were addressed; claudex-loop does exactly this for plan review and reports it working. Cheaper per round (no re-grounding).
- AGAINST: three distinct, independently-reported failure modes stack here — silent sandbox escalation to **`danger-full-access` on this specific host**, silent fallback to a new session (#19661), and transcript degradation from ~144k. Plus the anchoring effect the papers describe ("this is acceptable" bias, integrative compromise, unanimous endorsement of a non-existent bug). None of these announce themselves.

**(c) Hybrid — resume inside a phase, fresh across phases.**
- FOR: this is what *both* prior-art systems converge on independently. claudex-loop enforces it mechanically (`runner.py:289-290`: inspection may never resume). The SmartScope write-up proposes the same shape from the other direction — resume through the fix loop for traceability, then **one** fresh-session final audit, explicitly because *"The 'this is acceptable' bias gradually formed during the fix loop is eliminated."*
- AGAINST: two code paths to build and two sandbox postures to get right, for a loop whose bound is 2 rounds. At n=2 rounds the continuity resume buys is small, and the phase boundary is the only place it was ever load-bearing.

### Recommendation — supported

**Fresh reviewer every round (option a), with `memory: local` carrying finding-level continuity, and no `codex exec resume` in the dispatcher's review path.** Four legs:

1. It is the only option with a controlled experiment behind it, and the effect is in the right direction at p<0.01 across three comparisons (2603.12123).
2. On **this host specifically**, resume without `-c sandbox_mode` escalates a read-only reviewer to `danger-full-access` (global config `:6`, upstream-measured escalation #40149). The mitigation exists but is a flag you must never forget, on a subcommand whose `--help` does not mention it — the shape of gate this repo's `probes-need-a-control-arm.md` §9 warns about.
3. The continuity argument for resume is **already satisfied locally by a different mechanism** — `cold-review-1202-r2` self-corrected its round-1 finding as a fresh agent with `memory: local`.
4. The reviewer here is cross-family by doctrine (Opus reviewing a codex diff). Resuming a *codex* reviewer is doubly unavailable, and resuming the Opus one is a Claude-side `SendMessage` continuation, not `codex exec resume` at all.

**Do this instead of resume, and it is cheap:** hand each fresh reviewer the previous round's report *path* as an input artifact. It gets continuity as **evidence it can refute**, not as context it must defend — which is exactly 2604.19049's "refute-or-promote" shape.

**What IS supported for reuse, narrowly:** if the dispatcher ever needs to *argue with one finding* (not re-review a new diff), `resume` is the right primitive — same artifact, same round, no new object under review. Gate it with claudex-loop's returned-UUID check (`runner.py:238-239`) and a mandatory `-c sandbox_mode="read-only"`, and record both in `ai-cli-invocation.md` per that file's re-probe rule. **`exec fork` deserves a look here too** and is currently un-evaluated in this repo (0 mentions) — it gives round N+1 round N's context without round N's rebuttals.

**Not settled, and the measurement that would settle it:** whether `-c sandbox_mode="read-only"` fully restores the policy on resume *on macOS at 0.154.0*. Issue #40149 explicitly scopes itself: *"Linux only (Ubuntu 24.04, codex-cli 0.147.0), on an account with no `~/.codex/config.toml`"* — and notes the untested case that matters here: *"if a user's config specifies `workspace-write`, a resume after `exec -s read-only` would presumably inherit the broader policy, which is a larger gap than the one I measured."* Ours specifies `danger-full-access`. The settling probe is upstream's own, re-run here: create a read-only session, resume it with and without `-c sandbox_mode="read-only"`, and read the **canary file on disk** — never the model's self-report — with a `workspace-write` positive control so "not created" can be distinguished from "never attempted."

---

## Call 3 — Worktree provisioning of gitignored per-machine files

### Both vendors ship `.worktreeinclude` — and they do NOT cover the same worktrees

This is the part the brief's framing gets slightly wrong: `.worktreeinclude` is **not** a Claude Code feature that Codex lacks. Both have it, with the *same file name and `.gitignore` syntax*, and **different coverage**.

**Claude Code** — `$CC/worktrees.md:181`:

> "A worktree is a fresh checkout, so untracked files like `.env` or `.env.local` from your main repository are not present. To copy them automatically when Claude creates a worktree, add a `.worktreeinclude` file to your project root. The file uses `.gitignore` syntax. **Only files that match a pattern and are also gitignored are copied**, so tracked files are never duplicated."

Coverage is explicit and **includes subagent worktrees** — `:195`:

> "This applies to every worktree Claude Code creates with git: `--worktree` worktrees, **subagent worktrees**, and parallel sessions in the desktop app."

Two documented traps worth carrying:

- **`**/` patterns under a wholly-ignored directory** (`:185`): *"if you write `**/.claude/skills/*.md`, that first name is `.claude`, so Claude Code copies the matching files out of an ignored `.claude/` directory. To copy files out of an ignored directory that a `**/` pattern doesn't reach, name the directory in the pattern instead: write `vendor/**/config.json` rather than `**/config.json`."* The changelog records this as a real bug fixed in v2.1.239 — *"Fixed `.worktreeinclude` patterns starting with `**/` silently matching nothing when the target lived in a gitignored directory"* (`$CC/changelog.md:1128`). **Silently matching nothing** is the failure mode.
- **A `WorktreeCreate` hook disables it entirely** (`:271`, and `$CC/hooks.md:2940`): *"Because the hook replaces the default git behavior, `.worktreeinclude` is not processed when you use `--worktree`. Copy any local configuration files inside your hook script instead."*

**Codex** — `$CX/environments__git-worktrees.md:144`:

> "add a `.worktreeinclude` file to the repository root and list the ignored paths or `.gitignore`-style patterns to copy when Codex creates a managed worktree. … **Codex only copies ignored files that match `.worktreeinclude`**; it doesn't copy other local files that Git doesn't track. Don't list tracked files."

Plus a freebie: *"Codex automatically copies an ignored `AGENTS.override.md` into local managed worktrees, so you don't need to list it"* (`:148`).

⚠️ **But Codex's coverage is scoped, and the scope excludes the CLI case** — `:157`, verbatim:

> "Codex skips source symlinks and won't overwrite files that already exist in the new checkout. **This behavior applies to local ChatGPT desktop app managed worktrees, not remote worktrees or Git worktrees you create yourself from the command line.**"

Meanwhile `codex exec --worktree` (present on `exec`, `resume`, `fork` **and** `review` at 0.154.0) is documented in help only as *"Run the session in a new managed Git worktree"*. Whether that CLI-created "managed" worktree is inside or outside the `:157` carve-out is **not resolved by the docs**, and I found no statement either way. Control arm: `grep -rn "worktreeinclude" $CX` returns 6 hits across 2 files, so the corpus does discuss the feature — the silence is about this specific case, not about the feature.

### What fable-orchestrator does instead, and why

It hand-rolls the copy, at the wrapper's preflight — `SKILL.md:137`:

> "Worktree lanes start from a clean checkout: gitignored per-machine config (`local.properties`, `.env`, keystore files, …) does not follow into the new worktree, so **every lane's first verification fails on missing machine config unless the spec provisions it**. Name the needed file(s) in the spec — the wrapper copies exactly what the spec names at preflight … and nothing else: **per-machine config can carry secrets the vendor CLI can read, so which files cross into the lane is the architect's call, never the wrapper's.**"

The implementer agents implement it with a control arm — `agents/codex-implementer.md:122`: copy *"from the MAIN worktree — the first entry of `git worktree list`; **git records no parent link, so never guess among sibling worktrees**"*, then *"confirm git ignores each (`git check-ignore <file>`), never stage them, and note the copies in `GAPS`."*

Its CHANGELOG records the motivating field defect (`:119`): *"fresh `isolation: "worktree"` checkouts don't carry `local.properties`/`.env`/keystores, so **every lane's first build failed**."*

So the hand-rolled version is **not** ignorance of the native feature — it is a deliberately different policy on one axis: **allowlist-per-spec (architect names the files, per dispatch) vs allowlist-per-repo (`.worktreeinclude`, one committed list for every lane, forever).** That is the real decision, and it is a security decision, not an ergonomics one.

### What this repo actually needs provisioned — measured

`git check-ignore`, control-armed (`hk.pkl` → not ignored, as expected):

| path | ignored? | what breaks in a fresh worktree |
|---|---|---|
| `.codex/config.toml` | **IGNORED** | the project-scoped codex config. Memory `project_session_2026-09-10` records this config is **SELECTIVE and must not be deleted**; absent, a lane runs under global config only. |
| `mise.local.toml` | **IGNORED** | per-clone `BASE_IMAGE` / `DEVCONTAINER_SSH_PORT` pins (`AGENTS.md`). |
| `.claude/settings.local.json` | **IGNORED** | the accumulated permission allowlist. |
| `graphify-out/graph.json` | **IGNORED** | the graph the mandatory PreToolUse hook demands before any grep. |
| `python/.venv` | **IGNORED** | `uv` rebuilds it — cost, not correctness. |
| `.codex/agents/*.toml` | **tracked** | fine — the SDLC roster travels. |
| `.codex/skills/` | **tracked** | fine. |

Two traps specific to this clone:

1. **`.claude/worktrees/` is ignored only via `.git/info/exclude:11`, not `.gitignore`.** A fresh clone does not get it — the same per-clone trap `.gitignore` already documents for `.agent/`. Claude Code's own docs advise the opposite (`worktrees.md:32`: *"Add `.claude/worktrees/` to your `.gitignore`"*). Worth a tracked line.
2. **`worktree.baseRef` is unset** — `grep -rn "baseRef" .claude/` returns only two unrelated hits (a plugin-settings note, and `baseRefName` from gh's PR JSON), so the control arm shows the grep works and the setting is genuinely absent. The default is `"fresh"`, which branches from **`origin` default branch**, not from the branch the architect is working on. Per `worktrees.md:147`, `"head"` is the value *"for isolating subagents that need to operate on in-progress work"* — which is exactly a respec lane on a PR branch. **A dispatcher that isolates lanes on a PR branch without setting this will hand each lane a worktree branched off `main`.**

And the measurement that constrains the whole option space — `.claude/agents/codex-sol-operator.md:23-26`, this repo, 2026-09-01:

| sandbox | result |
|---|---|
| `-s workspace-write` | BLOCKED |
| `-s workspace-write --add-dir <path>` | BLOCKED |
| `--approve-for-me` | BLOCKED |
| **inside a git worktree** | **BLOCKED** |

*"worktree is not a loophole (codex docs, 'Protected paths in writable roots')"* (`:31`). So for a **codex** lane in this repo, a worktree does not buy write access back — the lane still runs `danger-full-access` (`codex-sol-implementer.md:62-95`, re-armed on an artifact because *"The lane's own exit code was 0 in both arms"*). The worktree here buys **checkout isolation between parallel lanes**, not confinement.

### Options

**(a) Native `.worktreeinclude`.**
- FOR: zero code; it is the vendor mechanism `use-tool-builtins.md` demands you reach for first; **covers Claude Code subagent worktrees explicitly** (`worktrees.md:195`), which is the `isolation: worktree` path this repo's roster already uses; refuses to copy tracked files by construction; one reviewed diff.
- AGAINST: it is a **repo-wide standing allowlist** — every worktree, every lane, forever, with no per-dispatch decision. That is precisely the property fable-orchestrator refused ("which files cross into the lane is the architect's call"). And the list would have to include `.codex/config.toml` and `.claude/settings.local.json`, which are agent-control surfaces. Coverage over `codex exec --worktree` is **unresolved** (`$CX:157`). The `**/` pattern trap can silently match nothing.

**(b) Hand-rolled copy at dispatch (fable-orchestrator's shape).**
- FOR: per-dispatch allowlist; the secret-exposure decision is made per run by the architect; works identically whoever created the worktree, so no dependence on the unresolved codex question; already the doctrine every lane in this repo runs under, with a `git check-ignore` control arm baked in.
- AGAINST: it is homegrown code where a native feature exists — `use-tool-builtins.md` requires a written justification for exactly this, and `tool-currency-and-native-first.md` requires re-checking whether the native path has caught up. It also cannot cover a worktree the *harness* creates before your code runs (`isolation: worktree` in frontmatter provisions nothing).

**(c) Both, split by who creates the worktree.** `.worktreeinclude` for the non-secret build inputs the harness must place before any lane code runs (`graphify-out/`, `mise.local.toml`); spec-named copy for anything secret-bearing or agent-controlling (`.codex/config.toml`, `.claude/settings.local.json`).
- FOR: the native mechanism covers the case the hand-rolled one structurally cannot (harness-created worktrees, where nothing of yours runs at creation time), and the hand-rolled one covers the case the native one cannot express (per-dispatch decisions). Neither is redundant.
- AGAINST: two mechanisms, and a reader must know which file is governed by which.

### Recommendation — partially supported, with one genuine gap

**Supported: add a `.worktreeinclude` for the non-secret build inputs, and keep spec-named copying for secret-bearing and agent-controlling files.** Option (c).

The load-bearing asymmetry is timing, and it is decisive: when a subagent declares `isolation: worktree` in frontmatter, **Claude Code creates the worktree before any of your code exists to copy anything** — so for that path the native mechanism is not merely preferable, it is the *only* one that can run. `worktrees.md:195` names subagent worktrees explicitly. Conversely `.codex/config.toml` and `.claude/settings.local.json` govern what an agent may do, and a standing repo-wide rule that copies them into every worktree removes a decision this repo has deliberately kept per-dispatch.

**Not supported, and this is the gap to close before building anything on it:** whether `codex exec --worktree` honours `.worktreeinclude`. The docs affirmatively scope Codex's implementation to *"local ChatGPT desktop app managed worktrees, **not** … Git worktrees you create yourself from the command line"* (`$CX:157`) while the CLI flag calls its result a "managed Git worktree" — the two sentences do not settle each other. **The settling measurement is cheap and should run before the dispatcher depends on it:** put a uniquely-named ignored canary at the repo root, list it in `.worktreeinclude`, run `codex exec --worktree -s read-only` with a prompt that only `ls`es and reports, and check for the canary **in the worktree directory on disk**, not in the model's answer. Control arm: a *second* ignored file that is **not** listed in `.worktreeinclude` and must be absent — otherwise "present" cannot distinguish `.worktreeinclude` working from Codex copying ignored files wholesale.

**Also worth correcting in the prior review:** `feature-matrix-final-2026-09-21.md:88` records *"Fable: DROP — native `.worktreeinclude` already does it."* That is right for the Claude Code `isolation: worktree` path and **unestablished** for the codex `--worktree` path. Dropping the spec-named copy wholesale would leave the codex lane unprovisioned on an unverified premise.

**Two fixes that are supported today, independent of the above:**

1. Set `worktree.baseRef` to `"head"` in `.claude/settings.json` if lanes are ever isolated while working on a PR branch, or the dispatcher will branch every lane off `main` (`worktrees.md:144-147`).
2. Move `**/.claude/worktrees/` from `.git/info/exclude` into the tracked `.gitignore` (`worktrees.md:32`), so a fresh clone is not the first to discover it.

---

## Cross-cutting note the three calls share

All three decisions have the same failure signature: **a mechanism that stops working without saying so.** A round budget that silently converts "exhausted" into "approved" (`claudex README:137` bans exactly this); a resume that silently escalates its sandbox (#40149) or silently starts a new session (#19661); a `.worktreeinclude` pattern that silently matches nothing (`$CC/changelog.md:1128`), or a lane that silently runs against config that never arrived. Whatever is built, each of the three needs its own control arm on every run, not a one-time verification — which is `probes-need-a-control-arm.md` §9's "assert the capability, never sniff for a symptom."

---

## Tool/plugin disposition (recorded per the brief)

| Tool | Outcome |
|---|---|
| Offline KB vendor docs (step 00) | **Used, primary.** Answered both vendors' worktree semantics, `exec resume` docs, `maxTurns`. |
| `docs/research/mintlify-cache/` (step 0) | **Cache miss** — no `openai`/`anthropic` tree; catalog line 145 marks `openai/codex` `queued`. Per `research-repo-enumeration.md`, `openai/codex` should be appended to the catalog's request queue. |
| Live CLI probe | **Used, primary** for call 2's flag matrix (both arms). |
| `exa` (`web_search_exa`) | **Used, worked.** Returned 8 results; the four load-bearing ones were then verified independently (`gh api` for issues, arXiv API for papers) rather than trusted as highlights. |
| `gh api` | **Used** as the control-armed verifier for three GitHub issues (404 control). |
| arXiv API | **Used** as the control-armed verifier for three papers (bogus-id control + known-real control). Needed `-L`: the un-redirected probe returned 301 for *every* id including the control, i.e. it could not discriminate. |
| `graphify` | **Unavailable — `stale`**, 33 commits behind (rc=3). Fell back to source per `graphify-first.md`. `mise run graphify-update` is the fix. |
| `context7` | **Not used.** Both subjects are documented in the offline corpus (step 00) at higher fidelity than a library-docs index would give; invoking it would have been a step already answered more cheaply. |
| `firecrawl:firecrawl-developer-index` | **Not used.** `exa` plus direct `gh api` already returned the specific issues and their verified state; a second index pass would have added sources without adding verification. |
| `last30days` | **Not used.** The recency question was answered by dated primary artifacts (issue states via `gh api`, arXiv IDs from 2026-02/03/04, CLI help from the pinned 0.154.0 binary), which are stronger than aggregated social recency for this question. |
| `mise exec -- timeout` | **Broken shim** — `mise ERROR No version is set for shim: timeout`. Used the Bash tool's own timeout instead. |

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — issues #40149 (resume rejects `-s`; resumed turn wrote a file), #19661 (resume silently fails/starts new session), #3309 (resume undocumented); CLI help probed at pinned 0.154.0.
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — round budgets (5/2/2), verdict-first stop conditions, `runner.py` resume/sandbox/inspection-freshness enforcement.
- [garrytan/gstack](https://github.com/garrytan/gstack) — issue #1258, independent confirmation that `exec resume` rejects `-C`/`-s` and the `-c sandbox_mode=` fix.
- [shaharsha/claude-skills](https://github.com/shaharsha/claude-skills) — `skills/codex-review/README.md`: measured resume sandbox escalation to `danger-full-access`; source of the three arXiv citations (one of which it overstates).
- [AgathaCrystal/skills](https://github.com/AgathaCrystal/skills) — `skills/gpt-review/SKILL.md`: resume is a documented part of its loop; flags are not inherited across resume.
- [Szpadel/codex-mcp-code-review](https://github.com/Szpadel/codex-mcp-code-review) — referenced by the Vaughan write-up as the MCP route to a clean-context review subagent; not read directly.
- [openai/codex-action](https://github.com/openai/codex-action) — named by Codex's own non-interactive docs as the supported CI path; not read directly.

