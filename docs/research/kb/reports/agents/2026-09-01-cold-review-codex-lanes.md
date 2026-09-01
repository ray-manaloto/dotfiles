# Cold review — commit 1aca600 (four codex-backed advisory lanes)

Reviewer: cold-codex-lanes subagent. REF: `1aca600` (parent `638739f`).
Read with `git diff 638739f..1aca600`. No design context was supplied.

Status: COMPLETE.

## Findings
## Ranked index

| # | Sev | Claim | Anchor |
|---|---|---|---|
| P1-1 | P1 | The Codex-app exporter writes to exactly the four hand-authored tracked paths; the next export overwrites them with `claude`->`Codex`-corrupted content, and all three defenses are absent on those files | `.gitignore:69-71`, `.codex/agents/` |
| P2-1 | P2 | "Asserted byte-equal, so the two surfaces cannot drift" — nothing asserts it; `hk.pkl:633` is the precedent that was not extended | `hk.pkl:633-636` |
| P2-2 | P2 | The four newly-tracked tomls are excluded from every hk builtin | `hk-common.pkl:65` |
| P2-3 | P2 | Adds 2,478 B back onto the eager per-session budget one commit after 12,591 B was cut for it; `md_budget.py` has no class for `.claude/agents/**` | `.claude/agents/codex-*.md` frontmatter |
| P2-4 | P2 | `codex-advisor` persists AFTER the codex call, and is the only one of the four with no deliver-before-idle rule | `codex-advisor.md:71-79` |
| P2-5 | P2 | The toml half hands a codex role Claude-Code-only mechanisms (`SendMessage`, `branch_guard`, "no Edit tool") and a nested `codex exec` | `codex-adversarial-critic.md:131` |
| P2-6 | P2 | Read-only is prose-only on both halves; the `.codex/` half runs under `danger-full-access` | `~/.codex/config.toml:5-6` |
| P2-7 | P2 | No `model:` frontmatter, so the clerical wrapper turns run on Opus | `.claude/agents/codex-*.md:1-6` |
| P3-1 | P3 | Byte-equality holds (control, no defect) | — |
| P3-2 | P3 | "174 doc pages" (really 191) and "all 50 fnox secrets" (rule says 56) | `codex-claude-code-expert.md:27,55` |
| P3-3 | P3 | "No `timeout` binary" — a shim exists and exits 1 without running the command | `codex-staleness-auditor.md:187` |
| P3-4 | P3 | The `.claude/CLAUDE.md` addition contradicts the authority sentences above and below it | `.claude/CLAUDE.md:53-58` |
| P3-5 | P3 | Time-boxed roster with no expiry mechanism | `.claude/CLAUDE.md:53` |

Findings below are grouped by area, not by severity; use the index above for rank.


---

### P2-1 — The "cannot drift" claim has no enforcement; the repo has a precedent gate for exactly this

**Claim.** The commit message asserts the tomls "are generated from the .md bodies and
asserted byte-equal, so the two surfaces cannot drift." Nothing in the diff or the repo
asserts that. The diff touches only `.gitignore`, `.claude/CLAUDE.md` and the eight agent
files — no hk step, no `suites.toml` contract, no mise task, no generator script.

**Settled by.**
```
git diff 638739f..1aca600 --name-status   # 10 files, no gate added
grep -rn "codex" hk.pkl hk-common.pkl python/verification/suites.toml
```
The only `codex` hits in the gate files are `hk-common.pkl:65` (`".codex/**"` exclude) and
`suites.toml:1807/1813/1830/1837` (the orchestrator implementation-lane contract). None
mention `.codex/agents/`.

**The precedent the author already had.** `hk.pkl:633-636` `session_review_skill_parity`
does exactly this for the other two-surface pair:
`test -f .agents/skills/session-review/SKILL.md && cmp -s .claude/skills/session-review/SKILL.md .agents/skills/session-review/SKILL.md`
with the comment "The Codex-callable and Claude skill surfaces are one contract. A stale
copy is worse than absence because the harness appears to accept it." That reasoning
applies verbatim to this pair, and the gate was not extended.

Byte-equality holds **today** (verified, see P3-1), so this is a missing gate, not a
present defect — but the commit message states the guarantee as if it existed.

---

### P2-2 — The four newly-TRACKED tomls are excluded from every hk builtin

**Claim.** `hk-common.pkl:65` lists `".codex/**"` in `excludePaths`. That exclusion was
written when `.codex/` was entirely gitignored, so it cost nothing. This commit makes four
files under `.codex/` tracked, and they inherit the blanket exclusion: no `typos`, no
trailing-whitespace, no line-ending, no security scanning ever runs on them, while the
`.claude/agents/*.md` half of each pair is fully linted.

**Settled by.** `sed -n '50,80p' hk-common.pkl` (line 65 `".codex/**",`) and
`git ls-files .codex/` → the four `codex-*.toml`.

**Consequence.** It is the half of the pair that the drift gate (P2-1) doesn't exist for
AND the half no linter reads. `mise run lint` rc=0 on this commit is therefore not evidence
about the toml contents.

---

### P2-3 — Adds ~2.5 KB back onto the eager per-session budget one commit after 12.6 KB was cut for it, and the gate cannot see it

**Claim.** A subagent `description:` is injected into the session's agent-type roster, i.e.
it is spent at launch, not on invocation. The four new descriptions total **2,478 bytes**:

| file | description bytes |
|---|---|
| `.claude/agents/codex-adversarial-critic.md` | 633 |
| `.claude/agents/codex-claude-code-expert.md` | 672 |
| `.claude/agents/codex-staleness-auditor.md` | 607 |
| `.claude/agents/codex-advisor.md` | 566 |

The parent commit is `638739f perf(context): trim the top-five eager instruction files,
12,591 B (#880)`. This commit gives ~20% of that back.

**Settled by.** Description bytes measured with a `re.search(r'^description:', ...)` sweep
over the four files. Eager-injection evidence: this reviewing session's own agent-type
listing contains all four descriptions verbatim, without any of the four agents having been
invoked.

**Why the author would not have seen it.** `kb_setup/md_budget.py` has no load class for
`.claude/agents/**` — `_RULE_RE`/`_SKILL_RE` at lines 120-121 and `BUDGETS` at 141-166 cover
`eager_root`, `rule_unscoped`, `nested`, `rule_scoped`, `skill` only. So
`mise run lint-docs` / `kb-setup md-budget` reports `62 instruction files checked; eager
context ~124435 bytes` and is structurally blind to this surface. A green budget gate here
is a gate that never looked.

---

### P1-1 — The Codex-app exporter's output path for these four agents is EXACTLY the four hand-authored tracked files; the next export silently overwrites them with corrupted content that no gate can see

**Claim.** The exporter names its output `.codex/agents/<claude-agent-basename>.toml`.
The four new Claude agents are named `codex-advisor`, `codex-adversarial-critic`,
`codex-staleness-auditor`, `codex-claude-code-expert` — so the exporter's target paths
are `.codex/agents/codex-advisor.toml` … i.e. the four files this commit hand-authors
and tracks. The next Codex-app export overwrites them in place.

**Settled by.** The existing 1:1 mapping, both directions:

```
$ ls .claude/agents/                     $ ls .codex/agents/
adversarial-critic.md                    adversarial-critic.toml
claude-code-expert.md                    claude-code-expert.toml
dockerfile-reviewer.md                   dockerfile-reviewer.toml
staleness-auditor.md                     staleness-auditor.toml
codex-adversarial-critic.md              codex-adversarial-critic.toml   <- hand-authored
codex-advisor.md                         codex-advisor.toml              <- hand-authored
codex-claude-code-expert.md              codex-claude-code-expert.toml   <- hand-authored
codex-staleness-auditor.md               codex-staleness-auditor.toml    <- hand-authored
```

Every `.claude/agents/*.md` has a same-basename `.codex/agents/*.toml`. The four
exported mirrors carry the `18:52` mtime of the export run; the four hand-authored ones
carry `20:14`. Same directory, same naming rule, no namespace separating them.

**Why this is P1 and not theoretical.** The `.gitignore` comment this commit adds
(`.gitignore:60-68`) exists *because* the exporter corrupts its output with a blind
`claude`→`Codex` substitution. Replicating its own probe, with a control arm:

| file | `Codex Code\|\.Codex/\|Codex mcp add` | control: `Claude Code\|\.claude/` |
|---|---|---|
| `claude-code-expert.toml` (exported) | 5 | 0 |
| `adversarial-critic.toml` (exported) | 2 | 0 |
| `codex-claude-code-expert.toml` (hand) | 0 | 9 |
| `codex-adversarial-critic.toml` (hand) | 0 | 6 |
| `codex-advisor.toml` (hand) | 0 | 3 |
| `codex-staleness-auditor.toml` (hand) | 0 | 3 |

The probe discriminates in both directions. So when the export lands on the tracked
paths, the corrupted text arrives **inside git**, and three separate defenses that would
normally catch it are all absent on this exact file set:

1. `.gitignore` deliberately un-ignores `codex-*.toml` — `git check-ignore -q
   .codex/agents/codex-foo.toml` → **rc=1** (a name nobody has created yet is already
   un-ignored), so the corrupted export is staged like any edit.
2. `hk-common.pkl:65` excludes `.codex/**` from every hk builtin — no typo, whitespace,
   or content check ever reads it (see P2-2).
3. No parity/byte-equality gate exists (see P2-1), so the `.md` half staying correct
   proves nothing about the `.toml` half.

The commit's own defense — the `.gitignore` comment "do not fix the asymmetry" — protects
the four mirrors that are *differently named*. It does nothing for the four that collide.

**What would settle it definitively** (not run, marked unverified): trigger a Codex-app
export and observe whether it writes the four `codex-*.toml` paths. The naming evidence
is strong but the export was not re-run during this review.

---

### P2-4 — `codex-advisor` is the only one of the four that persists AFTER the codex call, not before — the exact failure its three siblings' rule 1 exists to prevent

**Claim.** The other three open protocol rule 1 with "**Your first action, before you
read a single audited file / before you send a single proposal to codex, is to create
the tracked report**" (`codex-staleness-auditor.md:86-92`,
`codex-adversarial-critic.md:104-112`, `codex-claude-code-expert.md:117-121`).
`codex-advisor.md:71-79` instead says "as soon as `codex exec` returns, `Write` the
verdict … **before** composing your final response."

A `codex exec` at `xhigh` on `gpt-5.6-sol` is the long part of the run. An advisor killed
or idled *during* that call leaves nothing — which is verbatim the loss
`.claude/rules/agent-report-persistence.md` rule 1b describes ("An agent that dies having
written 13 of 20 sources leaves 13; one planning to write at the end leaves 0") and which
the sibling files quote back at length.

**Settled by.** `sed -n '71,79p' .claude/agents/codex-advisor.md` vs
`sed -n '86,92p' .claude/agents/codex-staleness-auditor.md`.

**Related, same file.** `codex-advisor.md` is also the only one of the four with no
"### 2. Deliver before you go idle" rule and no `SendMessage` instruction:
`grep -n "SendMessage" .claude/agents/codex-*.md` → hits in adversarial-critic:131,
staleness-auditor:114, claude-code-expert:137; **none** in codex-advisor.md. The advisor
is the most-invoked of the four (`.claude/CLAUDE.md:53` routes all advisor consults to it)
and is the one missing both durability rules.

---

### P2-5 — The `.toml` half instructs a codex-native agent to use Claude Code mechanisms it does not have, and to shell out to `codex exec` from inside codex

**Claim.** Byte-equality with the `.md` body means `developer_instructions` — the prompt a
**codex** agent role receives — carries instructions that only make sense in Claude Code:

- "send it with `SendMessage` before idling" (`codex-adversarial-critic.md:131`,
  `codex-staleness-auditor.md:114`, `codex-claude-code-expert.md:137`) — `SendMessage` is
  a Claude Code teammate tool.
- "the PreToolUse `branch_guard` refuses repo writes on the default branch"
  (`codex-advisor.md:83`, `codex-adversarial-critic.md:122`,
  `codex-staleness-auditor.md:105`, `codex-claude-code-expert.md:128`) — that guard is
  wired in `.claude/settings.json` and does not exist in a codex session.
- "you have no `Edit` tool" (`codex-claude-code-expert.md:190`) — a claim about Claude
  Code frontmatter, asserted to a codex role.
- Most structurally: "your actual reasoning happens **inside the `codex` CLI** … shell out"
  plus the full `codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol …` block.
  Delivered to a role that is *already* codex, this is a nested `codex exec` — double
  spend for zero benefit, and the token-saving rationale is already satisfied without it.

**Settled by.** `grep -n "SendMessage\|branch_guard\|no \`Edit\` tool" .claude/agents/codex-*.md`;
the `developer_instructions` is byte-equal to the body (P3-1), so every one of these is in
the toml.

**The tension is structural.** "The two surfaces cannot drift" and "the two surfaces have
different capabilities" cannot both be satisfied by a byte-equal copy. Either the toml
needs a codex-specific body, or the shared body needs to stop naming harness-specific
mechanisms.

---

### P2-6 — The read-only claim is prose-only on both halves, and the `.codex/` half runs under `danger-full-access`

**Claim.** Area-4 check: the bodies say "Never `--full-auto`, never a writable sandbox"
and no body instructs one — that part is clean. But the *enforcement* is absent on both
surfaces:

- `.claude/agents/*.md` frontmatter is `tools: Bash, Read, Grep, Glob, Write`. `Bash`
  alone permits `sed -i`, `git commit`, anything. `Write` can clobber a whole file — so
  `codex-claude-code-expert.md:190`'s argument "Do not write to it … **you have no `Edit`
  tool**" is not a mechanical guarantee: `Write` is strictly more destructive than `Edit`
  for the file it names (`.claude/agents/claude-code-expert.md`). (Inherited: the Claude
  originals are also "All tools except Edit, NotebookEdit".)
- `.codex/agents/*.toml` has no sandbox or approval field. `~/.codex/config.toml` sets
  `sandbox_mode = "danger-full-access"` and `approval_policy = "never"` (verified by
  reading the file). So the codex-role half of each pair runs with full disk access and no
  approvals, while its own text says "never a writable sandbox".

**Settled by.** `cat ~/.codex/config.toml` (lines 5-6); the toml key sets across all 11
agent role files in this repo + knowledge-base are exactly
`{name, description, model_reasoning_effort, developer_instructions}` (three of the four
exported mirrors omit even `model_reasoning_effort`). Byte-scan of the codex 0.151.0
binary shows the role-file parser (`codex_agent_roles::agent_role_config::
parse_agent_role_file_contents`) validating `name` and `developer_instructions`, and
`struct AgentRoleToml with 3 elements` = `description, config_file, nickname_candidates`
for the config-block form — **no sandbox/approval field in either**. I did not find a
sandbox field; I did not exhaustively prove one cannot exist, so treat "the schema has no
sandbox key" as strongly-indicated rather than settled.

---

### P2-7 — The four wrapper agents carry no `model:` frontmatter, so their own turns run on Opus — the exact spend the lane exists to avoid

**Claim.** All four Claude-backed originals pin `model: opus`
(`grep -E '^model:' .claude/agents/{adversarial-critic,staleness-auditor,claude-code-expert}.md`
→ `model: opus` in each). The four new wrappers pin **nothing**, so they inherit the parent
session's model. `.claude/CLAUDE.md:70-72` records that `CLAUDE_CODE_SUBAGENT_MODEL` is
deliberately NOT set, and the session default here is Opus 5.

Every wrapper turn — building the prompt, running graphify, reading corpora, relaying a
12-15 KB verdict — is therefore Opus. The bodies themselves describe the wrapper's job as
clerical ("Your own turns should do little more than gather the evidence codex cannot
reach, build the prompt, shell out, and relay the verdict",
`codex-advisor.md:14-16`). A `model: haiku`/`sonnet` line would have made the wrapper cheap;
its absence leaves a meaningful fraction of the saving on the table.

**Settled by.** `sed -n '1,10p' .claude/agents/codex-*.md | grep -E '^model:'` → no output.

---

### P3-1 — `developer_instructions` is byte-equal to the `.md` body except for one leading and one trailing newline (no findings, recorded as the control)

All four tomls parse under `tomllib`. Each `developer_instructions` equals the `.md` body
with the leading newline (consumed by TOML's `'''` first-newline rule) and one trailing
newline removed — `len(body) - len(di) == 2` for all four, first difference at index 0 is
`'\n'`. Backslashes and quotes survive intact: the literal `'''` form performs no escape
processing, which is the right choice, and no body contains a `'''` sequence that would
terminate the string early (checked). **No findings in area 2 beyond P2-1's missing gate.**

---

### P3-2 — Two stale numbers, in the files whose own job is catching stale numbers

1. **"174 offline doc pages"** (`codex-claude-code-expert.md:27` and `:55`). The tree holds
   **191** `.md` files:
   ```
   CC=~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code
   ls "$CC"/*.md | wc -l   # 191   (the only non-.md entry is docs_manifest.json)
   ```
   Inherited from `.claude/agents/claude-code-expert.md:19,79` — which is itself internally
   inconsistent, saying "175 doc pages" at line 171. Per
   `probes-need-a-control-arm.md` rule 6, an inherited number restated without re-derivation
   becomes the restater's finding. The sibling file shipped in the same commit
   (`codex-staleness-auditor.md:25-26`) opens its taxonomy with "**A count that drifted.**
   Counts are the cheapest thing to check and the most likely thing to rot."

2. **"All 50 fnox secrets"** (`codex-adversarial-critic.md:198`,
   `codex-staleness-auditor.md:179`, `codex-claude-code-expert.md:201`). The eager rule
   `.claude/rules/secrets-out-of-the-shell-env.md` states "**56 sanctioned as of
   2026-08-29**" in its header and "**all 50** are printable" in its closing paragraph — so
   the source is self-contradictory and the new files picked the older half. Also inherited
   (`adversarial-critic.md:148`, `staleness-auditor.md:132`).

---

### P3-3 — "There is no `timeout` binary here" is true in effect but wrong about the mechanism, and the real behaviour is more dangerous than absence

Present in all four (`codex-adversarial-critic.md:205`, `codex-staleness-auditor.md:187`,
`codex-claude-code-expert.md:208`). A `timeout` **shim does exist**:

```
$ which -a timeout
/Users/rmanaloto/.local/share/mise/shims/timeout
$ timeout 1 sleep 5
mise ERROR No version is set for shim: timeout
rc=1            # control arm: timeout 5 echo ok  ->  same error, rc=1
```

So the advice ("use `python3` + `subprocess(timeout=N)`") is correct, but the stated reason
is not. The operative hazard is worse than the file says: `timeout N cmd` does not fail with
"command not found" — it exits **1** immediately without running `cmd`, which a script or an
agent will read as "the command ran and failed". Worth stating that way in the hazard list.

---

### P3-4 — The `.claude/CLAUDE.md` addition contradicts the sentence directly above it and the paragraph directly below it

`.claude/CLAUDE.md:40` (already present): "invoke the fable-orchestrator:orchestration skill
before delegating and follow it as **authoritative** for routing, verification, review tiers,
and **advisor consults**."
`.claude/CLAUDE.md:65-66` (already present): "The **authoritative** routing/fallback doctrine
… is the `orchestrator-routing` skill in the **knowledge-base** repo."

The new paragraph at `:53-58` sits between them and overrides both for advisor consults
without saying it supersedes them. An agent reading top-down invokes the orchestration skill
first and is routed to `fable-orchestrator:fable-advisor` — the exact call the addition
exists to prevent. One clause ("this supersedes the routing above for advisor consults until
tokens reset") closes it.

**Right file, no budget breach** (area 7 otherwise clean): the root `CLAUDE.md` is untouched
(`git diff 638739f..1aca600 --name-status` shows only `.claude/CLAUDE.md`), the file is
77 lines / 4,604 B against a 200-line eager budget, and `kb-setup md-budget` exits 0.

---

### P3-5 — The whole roster is time-boxed with no expiry mechanism

`.claude/CLAUDE.md:53` "Until Claude tokens reset (from 2026-08-31)"; all four descriptions
end "while Claude subscription tokens are constrained". Nothing removes any of it — no issue,
no dated TODO, no gate. This is `codex-staleness-auditor.md:27-30`'s own shape 2 ("A retired
mechanism still described as current"), pre-loaded, and it costs 2,478 B of eager context
per session for as long as it survives (P2-3). Referencing #884 in the descriptions, or a
dated removal issue, would give it something to be found by.

---

## Areas with no findings

- **Area 1 (`.gitignore` mechanics)** — the stanza does exactly what its comment claims.
  Probed with `git check-ignore -q` (non-verbose, so rc reflects negation correctly):
  `codex-advisor.toml` → rc=1 (tracked), `adversarial-critic.toml` → rc=0 (ignored),
  `.codex/agents/` → rc=1, `.codex/agents/sub/codex-x.toml` → rc=0 (nested stays ignored),
  `.codex/agents/something-codex.toml` → rc=0 (suffix form stays ignored),
  `.codex/agents/codex-x.md` → rc=0 (wrong extension stays ignored),
  `.codex/config.toml` → rc=0. The un-ignore/re-ignore/re-include ordering is required and
  correct. The one consequence the comment does not draw is P1-1.
- **Area 3 (invocation)** — all four blocks pass `--model gpt-5.6-sol` **and**
  `-c model_reasoning_effort="xhigh"`, and each body contains exactly one invocation block.
  Every flag used exists in `codex exec --help` on the installed 0.151.0 (`--ephemeral`,
  `-s/--sandbox read-only`, `-m/--model`, `-c`, `-o/--output-last-message`), and the
  commit's premise is confirmed against the real file: `~/.codex/config.toml` holds
  `model = "gpt-5.6-sol"` and `model_reasoning_effort = "medium"`, so pinning both is
  genuinely non-redundant.
- **Area 6 (failure path)** — present and unambiguous in all four, in a `## Hard limits`
  section, with the same wording ("Never substitute your own reasoning for a failed codex
  call … say so plainly in the report and stop"): `codex-advisor.md:124-129`,
  `codex-adversarial-critic.md:211-214`, `codex-staleness-auditor.md:195-198`,
  `codex-claude-code-expert.md:233-238`. Each names its sanctioned fallback (the Claude
  original) rather than in-model substitution. Nothing elsewhere in any body undercuts it —
  `codex-claude-code-expert.md:62-68` sanctions a live Claude probe as a fourth corpus, but
  explicitly as a costed last resort, not as a substitute for a failed codex call.
- **Area 5 (self-consistency)** — every `name:` matches its filename and its toml `name`.
  Every referenced path exists: `.claude/rules/{ai-cli-invocation,agent-report-persistence,
  graphify-first}.md`, `.claude/agents/{adversarial-critic,staleness-auditor,
  claude-code-expert}.md`, `$CC`, `~/.local/share/claude/versions/` (2.1.252 installed).
  Every referenced mise task exists (`graphify-query`, `graphify-health`). Every named
  fallback agent exists. The only cross-reference defects are the stale counts in P3-2.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — byte-scanned the installed
  `codex-cli 0.151.0` binary for the agent-role TOML schema and probed `codex exec --help`
  for flag existence.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — compared
  the four new tomls against the seven hand-authored `kb-*` agent roles they are modelled
  on, and counted the `agent-harness-docs/docs/claude-code` page corpus.
