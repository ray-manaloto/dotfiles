# claudex-loop upstream research: routing, workflow, team shape and model tiers (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message (commissioned after Ray asked "did you actually research
> claudex-loop?" — the coordinator had read only the installed claudex-route SKILL.md).
> HTML entities introduced in transit restored. Coordinator note: this report's
> "terra's `upgrade` is null" reads the LIVE `~/.codex/models_cache.json`; the earlier
> `gpt6-sol-luna-model-update-2026-09-22.md` cites openai/codex main `models.json`
> (PR #47332) adding `gpt-5.6-terra → gpt-6-sol`. Two sources, two answers — the
> catalog in `main` is not yet what the server serves. Treat the terra successor as
> unsettled until a released catalog carries it.

## claudex-loop upstream research: routing, workflow, team shape and model tiers

**Read-only lane.** I did not write `findings.md`, `progress.md` or `.agent/kb/raw/`, so the coordinator needs to save this report verbatim. My only writes were downloads to the session scratchpad (`…/scratchpad/claudex-up/`).

**Pinned upstream:** `chaseai-yt/claudex-loop@8cf5e2c1771c5151d90c12642391d0ba8fa71b0e` (2026-09-06, "Add standalone Claudex Route skill (#17)"). All upstream citations below are at that SHA.

**Installed copy:** `~/.codex/plugins/cache/claudex-loop/claudex-loop/2.1.0`, enabled at `~/.codex/config.toml:254-255`.
- `.codex-marketplace-install.json` records `revision: 8cf5e2c…`, and `git rev-parse HEAD` gives the same SHA.
- `diff -rq` against upstream found no content differences. The only "Only in" entries were files I had not downloaded.
- **No version drift:** the plugin version is 2.1.0 in both copies (`.codex-plugin/plugin.json:17`, `.claude-plugin/plugin.json:17`), and upstream `main` has not moved since 2026-09-06.
- **The model guidance is stale.** See Q3 and upstream issue #25.

---

### Q1. How claudex-route decides, and how it runs a handoff

**Role comes before model** (`skills/claudex-route/SKILL.md:16-27`). There are six situations:
- Straightforward task → stay with the current agent and "avoid handoff overhead" (`:20`).
- A consequential or ambiguous plan → another provider challenges it before building (`:21`).
- An implementation is ready → another provider inspects it, including whether the tests are valid (`:22`).
- Repeated failed attempts → give another provider the reproduction and the failed approaches (`:23`).
- A separable task with clear inputs and checks → "Delegate that piece to a suitable smaller model and inspect its result" (`:24`).
- The user wants a repeated loop → recommend Claudex Loop, but don't start it (`:25`).

The current agent "keeps the user's requirements and coordinates" (`:27`).

**Provider** is chosen for perspective: "A different provider offers another perspective, not guaranteed correctness" (`:27`). Cross-provider delegation is optional (`:36`).

**Model tiers** are labelled "dated starting points (September 2026), not a permanent leaderboard" (`:31`):

| Model | Suggested use | Cite |
|---|---|---|
| `gpt-5.6-luna` | Narrow, repetitive work with explicit checks | `:33` |
| `gpt-5.6-terra` | Bounded coding needing more judgment | `:34` |
| `gpt-6-astra` / `claude-fable-5-1` | Ambiguous work, hard debugging, a substantial independent review. Each is the cross-provider pick from the other host | `:35` |
| Sonnet / Opus / others | Kept as options | `:36` |

**Explicit choices** are preserved: "Preserve explicit model and provider choices; do not silently replace them" (`:12`). A request for advice gets a recommendation only. Invoking the skill does not authorize implementation (`:14`).

**Listed vs authenticated vs proven runnable:** "Distinguish listed, authenticated, and proven runnable: none alone establishes the others." Use local listings and `--help` without launching a model task, and "Do not launch paid comparison calls just to choose a model" (`:38`).

**Cost claims:** check the official OpenAI and Anthropic model pages. API price is not subscription usage, and task cost includes context, reasoning and retries. "Do not call Terra cheaper than Sonnet… If sources cannot be checked, omit numeric claims" (`:40`).

**Execution** (`:52-62`). claudex-route has no runner; its execution rules are prose only (README `:42`: "does not use the full loop's approval-binding runner").
- Use the selected CLI with the model named explicitly, and check that binary's version and help (`:54`).
- The prompt is self-contained and goes through stdin or a file, "never interpolate" it into a shell command (`:56`).
- Read-only is a property to enforce: "a prompt saying 'read-only' is not enforcement." If the restriction cannot be established, return the prepared handoff instead of running it (`:58`).
- Use an isolated worktree only "when concurrent edits would conflict" (`:58`).
- Each handoff uses a fresh session, a bounded timeout, and separate stdout/stderr files in a unique temp directory outside the project (`:60`).
- An empty response, timeout or permission failure is not success. Don't retry automatically, don't escalate to a larger model, and resolve a timed-out process before touching the same files (`:60`).
- Report the requested model separately from the observed one (`:62`).

The concrete command shapes live only in the loop's runner (`skills/claudex-loop/scripts/runner.py`):

- **Codex review:** `exec -s read-only -c approval_policy="never" --json -o reply.txt --skip-git-repo-check --output-schema schema.json [-m M] [-c model_reasoning_effort=E] -` (`:148-160`).
- **Codex resume:** `exec resume <uuid> -c sandbox_mode="read-only"`, because resume has no `-s` (`:149-151`).
- **Codex build:** `-s workspace-write` (`:152`).
- **Claude review:** `-p --output-format json --permission-prompts none --safe-mode --strict-mcp-config --mcp-config '{"mcpServers":{}}' --tools Read,Glob,Grep … --permission-mode dontAsk --json-schema …` (`:161-166`).
- **Claude build:** `acceptEdits` (`:170`).
- **Process control:** the prompt goes on stdin, the child runs in its own session, and on timeout the whole process group gets `killpg SIGKILL` (`:180-196`). The default timeout is 600 s (`:405`).
- **Pre-flight:** the CLI `--version` probe must succeed (`:353-356`).
- **Artifacts:** stored under a `claudex-*` temp directory, and a directory inside the repo is refused (`:307-311`). Each run keeps `prompt.txt`, `command.json`, `stdout.txt`, `stderr.txt`, `result.json` (`references/runtime.md:20`).

---

### Q2. How the full loop is structured, and whether it ever runs agents concurrently

**Roles** are fixed by the host (`skills/claudex-loop/SKILL.md:14-19`; `runner.py:50-57`). The reviewer must be the other provider (`:53-54`), and the inspector is always the provider opposite the builder (`:57`, `:281-282`).

**Phases** (`SKILL.md:43-90`):
0. Recon
1. Requirements, ending in a written plan with proof commands (`:57-62`)
2. Plan review: the first round creates a session; later rounds use `--resume <result.json>` plus a feedback file written by the host (`:70`)
3. Build, then a **fresh** inspection by the other provider (`:86`)

**Caps** (`:33-39`): `MAX_ROUNDS` 5, `MAX_FIX_ROUNDS` 2, `MAX_INSPECTION_ROUNDS` 2. At the cap, "Present unresolved findings… instead of manufacturing convergence" (`:78`).

**Log:** an append-only `PLAN-REVIEW-LOG.md` (`:34`, `:64`, `:72`).

**Attestation and fingerprints:**
- `check_approval` requires a completed APPROVED review for the same repo and plan path, with the plan's SHA256 matching (`runner.py:247-254`).
- The plan hash is checked again after the run (`:369-370`).
- The inspection snapshot hashes every changed or untracked file plus the diff (`:86-109`), and is re-checked after the run (`:371-372`).
- `--resume` must match the prior run's provider, mode, repo, plan, model and effort (`:257-269`), and the session UUID must be identical (`:238-239`).

**HEAD and tree checks:**
- A build needs a clean checkout (`:295-296`).
- A resumed build must keep the same base and snapshot (`:299-300`).
- "Builder changed HEAD despite the no-commit contract" fails the run (`:373-375`).

**JSON event parsing** (`:202-215`):
- Any `error` or `turn.failed` event means failure (`:206-207`).
- There must be exactly one `thread.started` and exactly one `turn.completed` (`:208-211`).
- The reply file is parsed and then validated against the schema (`:112-142`). The validation rejects APPROVED with high or medium findings, REVISE with no findings, and BLOCKED with no limitations (`:136-141`).
- For codex, `observed_models` is always `[]` (`:215`), so the model identity codex actually used is never observed.

**Concurrency: never. It is strictly one agent at a time.**
- "The runner orchestrates one CLI turn, not the entire interview or loop" (`references/runtime.md:5`).
- `execute()` starts one `Popen` and blocks on `communicate` (`runner.py:185-188`).
- `PROVIDERS = ("claude", "codex")` (`:19`) makes the structure a two-party dyad.

A search of the whole repo for `parallel|concurren|simultan|team|subagent|multi-agent|fan-out|worker` found exactly three lines. I armed that probe: the same command shape finds `fresh` in 9 files.
1. The legacy description mentions "concurrency" only as a topic of the work being planned (`legacy/grill-me-codex/SKILL.md:3`).
2. "Deep multi-agent research requires explicit opt-in… Do not require a proprietary Workflow tool" (`SKILL.md:45`). This is research that may happen before planning, not splitting build work.
3. claudex-route `:58`: "an isolated worktree when concurrent edits would conflict."

claudex-route also closes after one delegation: "Finish after this handoff… further delegation follows the user's request" (`:62`).

The nearest thing to splitting work is "mixed authorship", where each provider inspects the other's code (`SKILL.md:88`). That is sequential. Upstream PR #21 mentions "deployments with several concurrent host sessions" only as a future design question.

---

### Q3. One agent vs a team: what to adopt, adapt or reject

**claudex-loop contains no team-size rule.** Its only related decision is binary: stay with the current agent (`route:20`) or delegate one bounded piece (`route:24`). The criterion for delegating is useful:
- "separable… clear inputs and acceptance checks" (`:24`)
- weighed against "ambiguity, code dependencies, verification difficulty, context size" (`:12`)
- with an explicit overhead penalty (`:20`)

**Adopt:**
1. **Pick the role before the model.** Make a typed role (`implement` / `review` / `diagnose`) a required input, and derive the model from the role.
2. **Treat staying single as the valid default.** Use a team only when the work splits into pieces that each have their own acceptance check. Our version of `route:24`: split into N specialists only if every slice has its own allowlist and gate, and none of them write to the same state.
3. **Listed, authenticated and runnable are three separate facts** (`route:38`). The catalog listing `gpt-6-sol` does not show that the account or the pinned CLI can run it. `runtime.md:49` records that Astra refused codex 0.144.5 even though the flags parsed. Here, `models_cache.json` reports `client_version` 0.156.0 while mise pins codex **0.154.0**. That is the same app-vs-PATH split `runtime.md:18` warns about.
4. **Requested vs observed model.** Because `runner.py:215` observes nothing for codex, our settlement should read the observed model from the rollout rather than repeat claudex's gap.
5. **No silent fallback or escalation** (`route:60`, `SKILL.md:21`).
6. **No numeric cost claim without a checked source** (`route:40`).

**Adapt:**
- claudex's review path is `codex exec -s read-only --output-schema` (`runner.py:148-160`), not `codex exec review`. On pinned 0.154.0, `codex exec review --help` shows `-m`, `--output-schema`, `--json`, `-o`, `--ignore-user-config`, `--uncommitted/--base/--commit`, and **no `-s/--sandbox`** (0 hits, against `codex exec --help:53` where `-s` is present).
- So read-only for `exec review` has to come from `-c sandbox_mode="read-only"`. Whether `exec review` honours that is **unverified** and needs a canary write test.
- Upstream PR #18 (open) adds `--ignore-user-config` and `-c web_search="disabled"` to reviewers. It found `-c 'mcp_servers={}'` "is a no-op", which bears directly on our MCP-can-write concern.
- **Re-measure the `[PROMPT]` conflict on 0.154.0.** The prior research (P2) says `--base/--commit/--uncommitted` conflict with `[PROMPT]`. `--help` does not show that conflict, and I did not re-measure it on 0.154.0 because a parse that succeeds would start a paid review.

**Reject:**
- Resumed same-session reviewer. That matches our ratified ruling ⚖2.
- `-s workspace-write` for builds (`runner.py:152`). This repo measured it failing our gates (`sdlc_team.py:747` / A3).
- The 5-round counter (`SKILL.md:33`), in favour of our severity-keyed bound of 2.
- Windows npm shims (`runner.py:68-75`).

**Model tiers do need updating.**
- Upstream still names `gpt-5.6-luna` and `gpt-5.6-terra` (`route:33-34`), and has no `gpt-6-sol` or `gpt-6-luna` anywhere.
- The live catalog (`~/.codex/models_cache.json`, fetched 2026-09-22T21:58Z) lists by priority: `gpt-6-astra` (1), `gpt-6-sol` (2), `gpt-6-luna` (3), `gpt-5.6-sol` (4), `gpt-5.6-terra` (7), `gpt-5.6-luna` (8).
- `gpt-6-luna` tops out at `max` effort, while astra and sol support `ultra`.
- claudex's `--effort` choices stop at `max` (`runner.py:397`), so it cannot request `ultra`.

**Correction to the brief:** the catalog does **not** name `gpt-6-sol` as terra's successor. terra's `upgrade` is `null`. The only `upgrade` entry is `gpt-5.5 → gpt-5.6-sol`, retiring 2026-10-14. The string `terra` appears once, its own slug, and `gpt-6-sol` likewise appears once. The "successor" claim comes from **upstream issue #25** (tomerikjansen-crypto, 2026-09-22, still open, no maintainer reply): "GPT-6 Sol… takes over the role GPT-5.6 Terra has… GPT-6 Luna… successor to `gpt-5.6-luna`". That issue cites prices ($2/$10 for sol, $0.10/$0.50 for luna) and a smoke test on codex 0.155.1. Treat those as **third-party and unverified**.

**Proposed mapping, following #25 and the catalog's priority order:**

| Model | Role |
|---|---|
| luna | Mechanical, check-bounded slices |
| sol | Default implementer |
| astra | Ambiguous work, diagnosis, review |

Cross-family review still needs a model family the implementer isn't. `exec review` on any gpt-6 model is still codex family.

---

### Q4. What the prior repo research got wrong or missed

1. **`history-herdr-claudex-2026-09-21.md:135` calls claudex-loop "Claude skills that shell out to the codex CLI, architecturally identical to our… wrapper agents."** That is out of date since #16. The skills are bidirectional (`SKILL.md:14-17`), and the core is a stdlib Python adapter that enforces its gates in code (`runner.py`). `codex-build` and `codex-review` are thin compatibility aliases (`codex-build/SKILL.md:8`). The quoted repo description ("Whoever built it never grades it") comes from the pre-#16 README. Exa's crawl of the GitHub page still serves that old README, including a `--dangerously-bypass-approvals-and-sandbox` build resume that 2.1.0 removed.
2. **`feature-matrix-final-2026-09-21.md:84` drops "claudex-route" wholesale** as front-half dead weight. That was right for plan review, but it discarded the only role-before-model table and the listed/authenticated/runnable distinction. Both answer today's routing question.
3. **Missed: codex model identity is never observed** (`runner.py:215`). B4 and B7 should not assume claudex offers a pattern for this; it has none.
4. **Missed: upstream open PRs #18, #20, #21 and #23.**
   - #18: index-divergence fingerprint gap plus reviewer config isolation.
   - #20: a finding-fingerprint convergence classifier, which is relevant to ⚖1.
   - #21: TOCTOU between the approval check and dispatch, since `runner.py:302` and `:312` read the plan twice. That affects B3's "claudex already solved it" attribution.
   - #23: a provider registry with Grok.
5. **Partly wrong: B14 cites "diff-size guard" with `runner.py:86-109` as its source.** claudex has no size guard; `:106` only hashes the diff. The size guard must come from the fable side.
6. **Confirmed correct:** the "zero drift" finding (`feature-matrix:115`), B3 (`:247-254`), B6 (`:373-375`), B15 (`runtime.md:33`), and "`exec review` is not from claudex". On that last point I found 0 `exec review` hits in the runner; its codex calls use `exec` and `exec resume` (`runner.py:149`).

## GitHub repos touched

- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — whole tree at `8cf5e2c`; issues and PRs #10, #14, #15, #18, #20, #21, #23, #25.
- [chaseai-yt/crucible](https://github.com/chaseai-yt/crucible) — pre-rename mirror surfaced by exa (stale `codex-review` text).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the three prior reports, compared.
