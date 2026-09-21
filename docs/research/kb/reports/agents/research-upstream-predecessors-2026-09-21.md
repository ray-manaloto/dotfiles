# Upstream Predecessors Research — claudex-loop & fable-advisor

**Agent:** research-upstream-predecessors · **Date:** 2026-09-21 · **Status:** COMPLETE
**Mode:** read-only research. Writes confined to this report and
`.agent/kb/raw/upstream-predecessors/` (25 files fetched at pinned SHAs).

Extends, does not replace: `feature-review-fable-2026-09-21.md`,
`feature-review-astra-2026-09-21.md`, `feature-matrix-final-2026-09-21.md`.

> **Fetch route that worked:** `gh api` for metadata/trees/commits, then
> `curl raw.githubusercontent.com/<o>/<r>/<SHA>/<path>` for exact bytes. Both
> worked first try; firecrawl/exa/context7 were never needed and were not used.
> Every fetched byte count matches the git tree's recorded blob size.

---

## Pinned refs — everything below is quoted at these SHAs

| Repo / artifact | Ref | SHA | Date |
|---|---|---|---|
| `chaseai-yt/claudex-loop` | `main` | `8cf5e2c1771c5151d90c12642391d0ba8fa71b0e` | 2026-09-06 |
| `DannyMac180/fable-advisor` | `main` (v5.0.0) | `4d6cc62164619a279b076439e1af5439892b958a` | 2026-09-02 |
| local `claudex-loop` codex plugin | `2.1.0` | `8cf5e2c…` (**identical**) | — |
| local `fable-orchestrator` plugin | `1.21.0` | no git (tarball) | installed 2026-08-14 |

**Probe hygiene.** Every "absent" below carries a control arm run with the same
command shape. Two named here once: `curl` of a real path → `200`, of
`skills/does-not-exist-zqv7/SKILL.md` → `404`; `gh api repos/anthropics/claude-code`
→ resolves, so the `mar3co` 404 is real. Grep arms are named per-claim.

---

## A. RELATIONSHIP — fable-orchestrator is a **detached fork** of fable-advisor

**Answer: fork, then rename, then detached.** Not the same project today; not
unrelated either. The evidence is the fork's own words, in the copy on this disk:

> `~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0/README.md:238`
> "**How does this relate to DannyMac180's fable-advisor?** This project began as
> a fork of it and is now maintained independently under its own name. Relative
> to the original: routing modes instead of a hardcoded default, no racing, a
> guaranteed Claude Opus terminal fallback, a shipped process supervisor, tiered
> cross-family review, and the researcher/reviewer agents."

> `…/1.21.0/CHANGELOG.md:3`
> "**fable-orchestrator**, originally derived from
> [DannyMac180/fable-advisor](https://github.com/DannyMac180/fable-advisor) at its
> **3.1.0** and independently maintained since **2026-07-10** (**detached from the
> fork network**). … Entries 3.1.1–3.5.0 below predate the rename, when this
> project was the fable-advisor fork."

This resolves three otherwise-confusing probe results:

| Probe | Result | Why |
|---|---|---|
| `gh api repos/DannyMac180/fable-advisor` | `fork:false, parent:null, source:null` | it is the **upstream**, not a fork |
| `gh api repos/mar3co/fable-orchestrator` | **404** | not publicly visible |
| `gh api users/mar3co` | Organization, `public_repos:2` (`openswap`, `rebuild-small-business-site`) | org is real; the plugin repo is private/removed |

"Detached from the fork network" also explains why no GitHub API field links
them — the link is documentary, not structural.

### Version/commit of each

- **fable-advisor**: `plugin.json` `"version": "5.0.0"`, 14 commits total
  (2026-07-03 → 2026-09-02). Author *Dan McAteer*.
- **fable-orchestrator**: `plugin.json` `"version": "1.21.0"`, author *mar3co*.
  Version line **renumbered** at the rename (3.5.0 → 1.x), so "1.21.0" is
  *later* than fable-advisor's 3.1.0, not earlier.
- **Fork point ≈ `b3b50a9a`** (2026-07-10), the last fable-advisor commit on the
  stated fork date; fable-advisor's own README:111 links its v3.1 tree at
  `b3b50a9`.

### File-level diff of `skills/orchestration/SKILL.md`

Same lineage, heavily rewritten. Not a rename — a 4.5× expansion.

| | fable-advisor 5.0.0 | fable-orchestrator 1.21.0 |
|---|---|---|
| bytes | 11,258 | 50,162 |
| sha256 | `a58ae176ffba…` | `77ab19e3b994…` |
| H1 | `# Orchestration — the architect's routing doctrine` | **identical** |
| sections | 9 | 14 |

Six headings survive the fork verbatim or near-verbatim: *Cost discipline — the
prime directive*, *The lanes*, *The spec contract*, *Parallelism*, *Commitment
boundaries*(+" and the final review" upstream), *Verification*.

- **Fork ADDED**: The checklist · What the architect implements itself ·
  Choosing your implementation routing (+ Codex fast mode / Codex effort / Grok
  effort) · Waiting on lanes — background by default · A completion without a
  report is not a success · Review tiers.
- **Fork DROPPED**: *Choosing the reasoning effort* (the per-rung table, replaced
  by per-vendor effort sections) · *The Codex plugin (optional)*.
- **Spec contract diverged**: upstream is **six** parts (6th = `REASONING:
  <effort>`); the fork is **seven** (the PREMISES block).

### Why this matters for us

The fork is **14 months of divergence in one direction only**. fable-advisor
kept evolving after 2026-07-10 (v4.0 2026-07-25, v5.0.0 2026-09-02), and **none
of that post-fork work is in the 1.21.0 we have installed.** Section C1 is the
one item from that window that is worth taking.

---

## B. DRIFT — claudex-loop: **ZERO**

The local codex plugin cache at `2.1.0` is a full git clone, so this is settled
by git rather than by text comparison:

```
/usr/bin/git -C ~/.codex/plugins/cache/claudex-loop/claudex-loop/2.1.0
  fetch origin main                 → rc=0 (fresh network fetch)
  rev-parse HEAD                    → 8cf5e2c1771c5151d90c12642391d0ba8fa71b0e
  rev-parse origin/main             → 8cf5e2c1771c5151d90c12642391d0ba8fa71b0e
  diff --stat HEAD origin/main      → (empty)
  status --porcelain -uno           → (empty)
```

Cross-checked by a second, independent route: `gh api
repos/chaseai-yt/claudex-loop/commits/main` → `8cf5e2c…`, 2026-09-06T23:05:32Z.
Two routes agree.

**Control arm for the diff probe** (it can produce output):
`git diff --stat HEAD~1 HEAD` → 5 files changed, 101 insertions(+), 12
deletions(-).

The single untracked file, `.codex-marketplace-install.json`, is an install
artifact, not drift.

**Consequence:** the prior reviews' claudex-loop coverage — read from this same
2.1.0 cache — is current as of upstream HEAD. Nothing in section C revises it on
drift grounds. Files added/removed: **none**. Behavioural differences in the four
skills and the runner: **none**.

---

## C. FEATURE MATRIX ADDENDUM

Scope: only what the prior three reviews did **not** cover. Everything they did
cover stands.

### What was uncovered, and how I know

`DannyMac180/fable-advisor` was **never read by any prior review**. Measured over
all three reports:

| Term | Hits |
|---|---|
| `dannymac` | **0** |
| `luna` | **0** |
| `5.0.0` | **0** |
| `fable-advisor repo` | **0** |
| *control:* `predecessor` / `upstream` | **12** (rc=0) |

The 24 `sol-implementer` hits in the prior reports are all
`codex-sol-implementer[.md]` — **our** agent, not fable-advisor's
`agents/sol-implementer.md`. Verified by exact-token count: `codex-sol-implementer` 4,
`codex-sol-implementer.md` 20, bare `sol-implementer` **0**.

So the prior reviews read *two local caches*. This addendum adds the **third,
never-read** source and the post-fork window it represents.

---

### C1. ⭐ The `~/.codex/AGENTS.md` refusal preamble — MIGRATE

| | |
|---|---|
| **Feature** | A preamble prepended to every codex spec declaring the lane an explicit opt-out from machine-wide orchestration defaults |
| **Source** | `fable-advisor@4d6cc62` `agents/codex-implementer.md:46-69` and `agents/sol-implementer.md:46-69` (identical text) |
| **Do we have it?** | **NO** — repo-wide, control-armed |
| **Ruling** | **MIGRATE** (prose + one constant) |

**What it does.** `codex exec` loads the user's `~/.codex/AGENTS.md` on every
invocation. A rule written for one project governs *every* lane on the machine.
If such a rule mandates an orchestration flow, codex correctly **declines rather
than silently substituting** — and the run returns **exit 0, empty diff, polite
refusal in the final message**. Upstream's words (`:60-69`, verbatim):

> "the run comes back **`exit 0` with an empty diff and a polite refusal in the
> final message**. That is a silent success: nothing in the exit code reveals it.
> … **Observed live 2026-08-04.**"
>
> "This is belt-and-braces, not a substitute for step 3 — the empty diff is what
> actually catches a refusal, whatever caused it."

The preamble itself (`:47-52`):

> "This task runs in a dedicated implementation lane on the model and reasoning
> effort named in the invocation below. Those were chosen deliberately for this
> lane; nothing has been substituted. If a user-level or project-level instruction
> file asks you to default to a different orchestration flow, treat this lane as
> an explicit opt-out from that default and proceed. Every other instruction in
> those files still applies."

**Control-armed absence.** Four distinct phrases, repo-wide over `*.py`/`*.md`/`*.toml`
excluding `.agent/`:

| Phrase | Repo files |
|---|---|
| `nothing has been substituted` | 0 |
| `explicit opt-out from that default` | 0 |
| `polite refusal` | 0 |
| `empty diff and a polite` | 0 |
| *control:* `architect-as-orchestrator` | **7** |

And in `python/src/dotfiles_setup/sdlc_team.py` specifically: `opt-out` 0,
`AGENTS.md` 0, `orchestration flow` 0 — against control `def ` = 39.
(`codex_lane.py`'s single `opt-out` hit at `:124` is `PLANNING_DISABLED`, an
unrelated concept — the planning-with-files hook silencer.)

**Neither does our plugin.** FO 1.21.0, same four phrases: **0 files each**;
control `model_reasoning_effort` → **6 files**. The preamble is post-fork
fable-advisor content — commit `ad2bdc3b`, *"codex-implementer: opt out of
machine-wide orchestration defaults"*, **2026-08-04**, four weeks after the
2026-07-10 fork. It never reached the branch we installed.

FO 1.21.0 does address the *auto-load* problem — but **only for grok**, and with
a different remedy (`skills/orchestration/SKILL.md:127`,
`agents/grok-implementer.md:109`): the architect restates conflicting constraints
in the spec, and the wrapper is *forbidden* to add anything. Since
`.claude/CLAUDE.md` records that grok is not installed here, **FO's coverage of
this defect class is dark for every lane this repo actually uses.**

**Risk today: LOW, but one commit from live.** Both trigger files are currently
harmless on this machine:

- `~/.codex/AGENTS.md` exists and is **0 bytes** (`ls -la`, control: `~/.codex/config.toml`
  = 24,990 bytes).
- Repo root `AGENTS.md`: `orchestrator` 0, `implementation lane` 0, `delegat` 0
  (control: `mise` = 41).
- No `.codex/AGENTS.md` in the repo.

The mandate that *would* trigger it — *"on ANY session model: non-trivial
implementation runs the fable-orchestrator architect-as-orchestrator flow"* —
lives in `.claude/CLAUDE.md`, which **codex does not read**. So the hazard is
latent: moving that line into root `AGENTS.md`, or anyone writing
`~/.codex/AGENTS.md`, arms it silently for every lane at once.

**Why it still earns MIGRATE.** This is a **cheap, permanent immunisation
against a silent-success class** the repo already treats as its worst failure
mode, and it is the *same* class as matrix items **B6** (HEAD-unchanged) and
**B8** (dissent as a settled status) — which were justified from claudex alone.
fable-advisor is an **independent third source** measuring the same defect from a
different cause, which strengthens B6/B8 rather than duplicating them.

**Cost/risk.** ~6 lines of constant text on the spec prepend path; no argv
change, no new failure mode. One caveat worth carrying verbatim: upstream itself
says the preamble is *belt-and-braces* — **the empty-diff check is the real
detector**. Adopt B6/B8 first; C1 reduces how often they fire.

---

### C2. `JUDGMENT CALLS:` report line — ENHANCE

| | |
|---|---|
| **Source** | `fable-advisor@4d6cc62` `agents/sol-implementer.md:124` |
| **What** | "decisions codex made that the spec left open, taken from its final message **and checked against the diff** — or `none`" |
| **Do we have it?** | **NO**. `judgment call` (and `JUDGMENT`) → **0/0/0** across `sdlc_team.py`, `codex_lane.py`, `.claude/skills/codex-sdlc-team/SKILL.md`; control `codex` → **23/74/25** |
| **Ruling** | **ENHANCE** — one more required line in the lane report schema |

Applied upstream *only* to the escalation lane, on an explicit rationale
(`:10`): "Because the spec underdetermines these tasks by definition, ask codex
explicitly to list the judgment calls it made." That is precisely the
`implement`-mode case. It pairs with matrix **B4** (evidence grading): B4 says
*whether verification ran*; this says *what the lane decided that you never
specified* — the residue a premise block cannot pre-empt because it did not
exist at spec time. Cost: one schema field. Risk: self-reported, so it is a
lead, not evidence — and upstream already requires it be *checked against the
diff*.

---

### C3. Effort **refused, never rounded** — ENHANCE

| | |
|---|---|
| **Source** | `agents/codex-implementer.md:36` (Luna: `low…max`, no `ultra`), `agents/sol-implementer.md:36` (Sol: `low…ultra`) |
| **What** | "if the spec names a rung this model doesn't have, return `STATUS: unavailable` with `REASON: effort <x> not supported by <model>` **rather than rounding it**" |
| **Ruling** | **ENHANCE** — fold into matrix **A5** |

Matrix A5 already owns "request `effort` moves only the dispatcher; every
specialist toml pins `high`", marked MEASURE-in-9.4. C3 supplies the *decision
rule* A5 will need once measured: a per-model effort **enum**, and an invalid
rung is an `INVALID_REQUEST`, not a silent downgrade. Same fail-closed shape as
matrix A2 (required `model`). Also upstream (`:48`): omitting the line means the
lane runs at the user's configured default and **must flag that in `GAPS`** —
our equivalent is recording the resolved effort in the settlement, which A2
already proposes for `model`.

---

### C4. Two wrappers, one hand-kept argv block — **third confirmation of ⚖4**

`diff agents/codex-implementer.md agents/sol-implementer.md` → **25 changed
lines of 124 (80% identical)**. The differences are exactly: name, description,
H1, intro, model slug ×3, effort rung list, timeout (`600` vs `1800`), report
`LANE:` line, and the last rule.

This is the same defect the Fable review found in **our** 12
`codex-{sol,astra}-*.md` wrappers, and that matrix ⚖4 proposes to retire. It is
now attested in **all three** projects — ours, the fork, and the upstream. That
is convergent evidence that per-lane markdown wrappers *structurally* duplicate
argv, which is the strongest available argument for Ray's single-entry-point
ruling. **No new work item; it raises confidence on ⚖4.**

---

### C5. Flags fable-advisor uses that we do not — mostly **DROP**

Verbatim, `agents/{codex,sol}-implementer.md:80-87` (identical but for slug and
timeout):

```bash
${T:+$T 600} codex exec \
  --model gpt-5.6-luna \
  ${EFFORT:+-c model_reasoning_effort=$EFFORT} \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --cd "$(pwd)" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

| Flag | path:line | Ours? | Ruling |
|---|---|---|---|
| `--sandbox workspace-write` | `:83`, `:94` | yes, `sdlc_team.py:747` | **KEEP-AS-IS** (matrix A3 owns the re-measure) |
| `-c model_reasoning_effort=$EFFORT` | `:82`, `:95` | yes | **KEEP-AS-IS** |
| `--skip-git-repo-check` | `:84` | **no** (0 hits both modules) | **DROP** — we always run inside this repo; upstream's rationale is "works outside git repos" (`:96`) |
| `--cd "$(pwd)"` | `:85` | n/a — we set `cwd` on the spawn | **KEEP-AS-IS** |
| `--output-last-message "$FINAL"` | `:86` | `codex_lane.py` 1 hit; `sdlc_team.py` **0** | **ENHANCE** — see C6 |
| `- < "$SPEC"` (stdin) | `:87`, `:97` | yes | **KEEP-AS-IS** — and it is the trailing `-` our own rule warns about |
| `command -v codex && codex --version` preflight | `:17` | equivalent (`CLI_MISSING`, matrix F45) | **KEEP-AS-IS** |
| `${T:+$T 600}` portable timeout | `:75-76`, `:98` | n/a | **DROP the mechanism, KEEP the caveat** — see below |

**The portable-timeout caveat is live on this machine.** Upstream (`:74`): *"macOS
has no `timeout` unless coreutils is installed"*, and it probes `gtimeout ||
timeout || true`, warning when neither exists. Measured here today, unplanned:
`timeout 120 mise run graphify-query …` failed with
`mise ERROR No version is set for shim: timeout`. So on this Mac `timeout` is a
**broken mise shim** — worse than absent, because it *resolves*. This
independently corroborates repo memory `project_session_2026-09-12b`
("`timeout` is a broken shim"). Our own supervisor is Python
(`subprocess` + `killpg`), so we do not need upstream's shell probe — but any
*hand-written* bash in a lane brief must not assume `timeout` exists. Worth one
line in `ai-cli-invocation.md`.

> Noted in passing: that same command returned **`RC=0` while mise errored**,
> because it was piped to `head` — a live instance of
> `feedback_pipe_kills_exit_code`. The re-run captured `rc=3` to a file.

---

### C6. `sdlc_team.py` is behind `codex_lane.py` on codex-native plumbing

Not an upstream feature — a gap this comparison exposed. Same grep, both modules
(control: `exec` → 4 / 9):

| Flag / event | `sdlc_team.py` | `codex_lane.py` |
|---|---|---|
| `--output-schema` | **0** | **4** |
| `--output-last-message` | **0** | 1 |
| `--model` | **0** | 2 |
| `turn.completed` | **0** | 1 |
| `turn.failed` | 1 | 0 |
| `--json` | **0** | **0** |

The newer, canonical entry point (`mise run sdlc-team`, #1163) has **less**
codex-native plumbing than the older per-lane module — including
`--output-schema`, which `codex_lane.py` already uses four times. Matrix **B7**
(`--json` event log) and **A2** (`--model`) already target two of these rows;
this table says the fix should be *"adopt what `codex_lane.py` already does"*
rather than *"port from a predecessor"*, which is cheaper and matches
`use-tool-builtins.md`. **Ruling: FIX, folded into B7/A2, sourced internally.**

---

### C7. Provenance corrections to the prior reviews (both minor, neither changes a ruling)

1. **`exec review`, `service_tier`, `features.fast_mode` are not claudex-loop.**
   Zero hits across all of `chaseai-yt/claudex-loop@8cf5e2c` and
   `DannyMac180/fable-advisor@4d6cc62` (control: `exec resume` → found at
   `runner.py:149`). They are **fable-orchestrator 1.21.0**: `README.md:189`,
   `CHANGELOG.md:128` / `:135`, `agents/codex-implementer.md:172`,
   `scripts/doctor.sh:68`, `scripts/test-run-lane.sh:63,72,114,124`. The Fable
   review said "a predecessor", which is true — this just pins *which*, so the
   matrix's D-line "drop `codex exec review` for now" is understood to be
   dropping a **fork** feature, not a claudex one.

   Useful detail found while locating it (`CHANGELOG.md:128`): the subcommand's
   `--commit`/`--base` flags are **mutually exclusive with custom instructions**
   on codex-cli 0.144.1 — a real constraint if `exec review` is ever revisited.

2. **The prior flag inventory omits `--output-schema` and `-o`.** Both are in
   `runner.py:153,155`. `--output-schema` is the mechanism behind claudex's
   validated review verdicts, and the matrix's **B14** (review schema with
   `coverage`/`limitations`) depends on it. Worth naming, since B14 is
   implementable *only* if the schema is enforced CLI-side rather than by
   prompt.

---

### C8. claudex `runner.py` — four guards the matrix did not list

Read fresh at `8cf5e2c`. All four are the same "refuse rather than assume"
shape the matrix's B-list already favours; recorded so the ruling is informed,
not because each needs its own work item.

| # | Guard | path:line | Ours? | Ruling |
|---|---|---|---|---|
| a | **Session-identity refusal**: resumed session must equal the expected UUID — *"CLI resumed a different session; refusing its result"* | `runner.py:238-239` | n/a — matrix ⚖2 recommends DROPping resume entirely | **DROP** (consistent with ⚖2) |
| b | **Resume-parameter match**: `repo`,`plan`,`provider`,`mode`,`requested_model`,`requested_effort`,`status` must all match or *"Start fresh instead"* | `runner.py:257-264` | n/a | **DROP** (same) |
| c | **Exactly-one `thread.started` + one `turn.completed`**, and any `error`/`turn.failed` event aborts | `runner.py:203-211` | `sdlc_team.py` has `turn.failed` ×1, no cardinality check | **MIGRATE into B7** — this is what "`--json` makes B4 honest" concretely means |
| d | **`BLOCKED` must explain its limitation** | `runner.py:140-141` | n/a | **MIGRATE into B14** — a one-line schema constraint that makes a blocked review actionable |

(c) is the substantive one: it converts B7 from "log events" into "assert the
event stream is well-formed", which is what makes a `captured` grade defensible.

---

### C9. `codex-build` skill — one rule worth lifting

`skills/codex-build/SKILL.md:17` (thinly covered by prior reviews — 1 mention):

> "**Never present an earlier review as covering later fixes.** … After a Claude
> takeover, require fresh Codex inspection of Claude's edits; if both
> contributed, log authorship and have each inspect the other's changes."

The first clause is matrix **B14** (snapshot fingerprint) stated as a *rule*
rather than a mechanism — worth one sentence of skill prose alongside B14, since
the fingerprint detects the violation but does not say what to do. The
authorship-logging clause is **DROP**: our `COMMIT: caller` invariant (matrix C,
F30) means a lane never commits, so mixed authorship inside one review window is
already excluded.

Also at `:15`: `--unreviewed-spec` *"with that status recorded"* — an escape
hatch that **records its own use**. Same shape as matrix **B12**'s respec
override. **ENHANCE B12**: when the >2-round override is exercised, record it in
the settlement rather than only permitting it.

---

## D. Every codex CLI flag the upstream skills use — verbatim, with path:line

### D1. `DannyMac180/fable-advisor@4d6cc62`

| Flag / token | path:line |
|---|---|
| `command -v codex && codex --version` | `agents/codex-implementer.md:17`, `agents/sol-implementer.md:17` |
| `codex exec` | `agents/codex-implementer.md:80`, `agents/sol-implementer.md:80` |
| `--model gpt-5.6-luna` | `agents/codex-implementer.md:81`, `:100` |
| `--model gpt-5.6-sol` | `agents/sol-implementer.md:81`, `:100` |
| `-c model_reasoning_effort=$EFFORT` | `agents/codex-implementer.md:82`, `:95`; `agents/sol-implementer.md:82`, `:95` |
| `--sandbox workspace-write` | `agents/codex-implementer.md:83`, `:94`; `agents/sol-implementer.md:83`, `:94` |
| `--skip-git-repo-check` | `agents/codex-implementer.md:84`, `:96`; `agents/sol-implementer.md:84`, `:96` |
| `--cd "$(pwd)"` | `agents/codex-implementer.md:85`, `:96`; `agents/sol-implementer.md:85`, `:96` |
| `--output-last-message "$FINAL"` | `agents/codex-implementer.md:86`; `agents/sol-implementer.md:86` |
| `- < "$SPEC"` (stdin prompt) | `agents/codex-implementer.md:87`, `:97`; `agents/sol-implementer.md:87`, `:97` |
| `${T:+$T 600}` / `${T:+$T 1800}` wall clock | `agents/codex-implementer.md:80`, `:98`; `agents/sol-implementer.md:80`, `:98` |
| `gtimeout \|\| timeout` probe | `agents/codex-implementer.md:75`; `agents/sol-implementer.md:75` |
| *(slash commands, not CLI)* `/codex:rescue --model <slug> --effort <rung>`, `/codex:status`, `/codex:result`, `/codex:cancel`, `/codex:adversarial-review`, `/codex:review`, `/codex:setup` | `skills/orchestration/SKILL.md:85-87` |

Explicitly **never** used, stated as a rule: `danger-full-access`
(`agents/codex-implementer.md:94`, `agents/sol-implementer.md:94`).

### D2. `chaseai-yt/claudex-loop@8cf5e2c` — `skills/claudex-loop/scripts/runner.py`

The whole codex argv, `runner.py:148-160`:

| Flag / token | path:line | Condition |
|---|---|---|
| `exec` | `:149` | always |
| `resume <session>` | `:149` | only when resuming |
| `-c sandbox_mode="read-only"` | `:150` | resumed **and** review mode |
| `-c sandbox_mode="workspace-write"` | `:151` | resumed, build mode |
| `-s read-only` / `-s workspace-write` | `:152` | fresh run (flag form, not `-c`) |
| `-c approval_policy="never"` | `:153` | always |
| `--json` | `:153` | always |
| `-o <run_dir>/reply.txt` | `:153` | always |
| `--skip-git-repo-check` | `:155` | review mode only |
| `--output-schema <run_dir>/schema.json` | `:155` | review mode only |
| `-m <model>` | `:157` | only when model given (**`-m`**, not `--model`) |
| `-c model_reasoning_effort="<effort>"` | `:159` | only when effort given |
| `-` (stdin prompt) | `:160` | always, last |

Note the deliberate split at `:150-152`: **`-c sandbox_mode=` on resume, `-s` on
a fresh run** — the `-s` flag cannot be applied to a resumed session. Ours never
resumes, so this is informational.

For completeness, the Claude-provider argv in the same function (`:161-176`):
`-p`, `--output-format json`, `--permission-prompts none`, and in review mode
`--safe-mode`, `--strict-mcp-config`, `--mcp-config '{"mcpServers":{}}'`,
`--tools Read,Glob,Grep`, `--allowedTools Read,Glob,Grep`, `--permission-mode
dontAsk`, `--no-chrome`, `--json-schema <inline>`; build mode uses
`--permission-mode acceptEdits` with the comment (`:168-169`) that a denied
proof command *"is a reported failure; it is never grounds to silently bypass
permissions."*

---

## Summary of proposed rulings

| # | Item | Ruling | Lands in |
|---|---|---|---|
| C1 | `~/.codex/AGENTS.md` opt-out preamble | **MIGRATE** | new; reinforces B6/B8 |
| C2 | `JUDGMENT CALLS:` report line | **ENHANCE** | B4 |
| C3 | Effort refused, never rounded | **ENHANCE** | A5 (after 9.4 measures) |
| C4 | Duplicated wrapper argv | *evidence only* | raises confidence on ⚖4 |
| C5 | `--skip-git-repo-check`; portable-timeout shell probe | **DROP** (keep the macOS caveat) | `ai-cli-invocation.md` one-liner |
| C6 | `sdlc_team.py` behind `codex_lane.py` | **FIX**, sourced internally | B7, A2 |
| C7 | Flag provenance corrections | *correction only* | matrix D-line, B14 |
| C8c | Event-stream cardinality assertion | **MIGRATE** | B7 |
| C8d | `BLOCKED` must explain limitation | **MIGRATE** | B14 |
| C8a/b | Session-identity + resume-parameter guards | **DROP** | consistent with ⚖2 |
| C9 | "never present an earlier review as covering later fixes"; recorded override | **ENHANCE** | B14, B12 |

**Nothing here overturns a prior ruling.** C1 is the only genuinely new
migration candidate; everything else sharpens an existing matrix row or corrects
a provenance label.

## Limitations

- `mar3co/fable-orchestrator` is not publicly readable (404, control-armed), so
  the fork's *history* could not be read — only the 1.21.0 tarball on disk and
  its own CHANGELOG. The fork-point claim (3.1.0 / 2026-07-10) is the fork's own
  assertion, corroborated only by fable-advisor's commit dates, not by a diff.
- fable-advisor has **no** `hooks/`, `scripts/`, `commands/`, or `CHANGELOG.md`
  — all 404 at the pinned SHA, against 200s for the eight files that do exist.
  The brief asked for those directories; they do not exist upstream.
- The graphify graph was **stale** (built at `ff2fbaf7`, HEAD `8474043d`, 33
  commits behind), so per `.claude/rules/graphify-first.md` every code claim
  above came from direct source reads, not the graph.

## GitHub repos touched

- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — primary subject; tree, commits, and 17 files read at `8cf5e2c`.
- [DannyMac180/fable-advisor](https://github.com/DannyMac180/fable-advisor) — primary subject; tree, full 14-commit history, and 8 files read at `4d6cc62`.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — relationship target; repo 404s, read from the local 1.21.0 plugin cache.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — our side; every "do we have it" arm above.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — control arm only, to prove the `gh api` 404 was real.
- [openai/codex](https://github.com/openai/codex) — cited by fable-advisor README:53 as the CLI dependency; not fetched.
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — cited by fable-advisor README:54 / `SKILL.md:83`; not fetched.
