# Claude Code expertise — scripted invocation of `disable-model-invocation: true` verbs (2026-08-05, v2.1.222)

`claude --version` → `2.1.222 (Claude Code)`

Corpora consulted: **live probe** (10 spawned sessions, fixture outside the repo),
installed binary `~/.local/share/claude/versions/2.1.222`, offline docs `$CC` (174 pages).

## The question as a falsifiable claim

> "A non-interactive `claude -p "/verb args"` session CANNOT invoke a skill whose
> frontmatter carries `disable-model-invocation: true`."

**REFUTED.** It can — with two hard conditions the caller must design around.

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | `claude -p "/probe-verb"` **runs** a flagged skill; the harness expands SKILL.md verbatim into the first user message, no `Skill` tool involved | live, session `ba821cba…`; internal control: same session's `skill_listing` lists `control-verb`, **not** `probe-verb` |
| 2 | CONFIRMED | The probe discriminates: an unknown verb answers `Unknown command: /…` and an unflagged verb answers with its token | `/vashtorel-4409-nonexistent` → `Unknown command`; `/control-verb` → `PLIMDORQ-2298-BRAVO` |
| 3 | CONFIRMED | `$ARGUMENTS` substitutes normally under `-p` — `<command-args>` is a real frame | `/probe-args ticket-777 --deep` → `THRENDIC-8850-CHARLIE ARGS=[ticket-777 --deep]` |
| 4 | CONFIRMED | **Expansion happens ONLY when the `-p` prompt begins with the slash command.** Mid-message, the harness does not expand — and the model then silently runs a *different* skill while narrating success | flagged mid-msg → ran `control-verb`, reported "/probe-verb"; control arm: **unflagged** mid-msg ALSO failed to expand (0 `command-name`, fell to `Skill` tool) ⇒ this is `-p` parsing, not the flag |
| 5 | CONFIRMED | The flag still does its job model-side under `-p`: asked in natural language, the model cannot see the flagged skill and substitutes a visible one | `-p "Use the probe-verb skill now."` → `Skill{skill:"control-verb"}` → wrong token |
| 6 | CONFIRMED | **A second, independent gate refuses flagged verbs in COORDINATOR MODE**, driven by the undocumented env var `CLAUDE_CODE_COORDINATOR_MODE` | binary `function Wb()`; live both arms: coord=1 → refusal, coord=0 → token, same command |
| 7 | CONFIRMED | In coordinator mode an **unflagged** verb is not executed either — it is rewritten into a "brief a worker to use this skill" note | live `I-coord-control` injected text, verbatim below |
| 8 | CONFIRMED | `CLAUDE_CODE_COORDINATOR_MODE` is **0-of-174 in the docs**, 9 in the binary | control: `CLAUDE_CODE_TASK_LIST_ID` → 2 doc files (probe sees the corpus) |
| 9 | CONFIRMED | `claude -p "/verb"` **appends piped stdin to `<command-args>`** — a scripted caller that leaves stdin open silently injects garbage into the verb's `$ARGUMENTS` | accidental: heredoc body landed in `command-args`; control: same command with `stdin=DEVNULL` → clean |
| 10 | CONFIRMED | An unknown verb exits **rc=0** — a typo'd verb is not detectable from the exit code | `logs/C-absent.rc` = 0 |

## Fixture and method

`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/20df00a4-54d1-4f2e-b5ec-1a75d3ded54f/scratchpad/verb-probe/`

- `.claude/skills/probe-verb/SKILL.md` — `disable-model-invocation: true`, body: emit `KRUNTHAVEL-6613-ALPHA`
- `.claude/skills/control-verb/SKILL.md` — **no flag**, body: emit `PLIMDORQ-2298-BRAVO`
- `.claude/skills/probe-args/SKILL.md` — flagged, body: emit `THRENDIC-8850-CHARLIE ARGS=[$ARGUMENTS]`
- `run.py` / `coord.py` — bound every spawn at `subprocess(timeout=180)` (no `timeout`
  binary on this host), strip inherited `CLAUDE_CODE_*` from the child env, force
  `--model haiku` so no probe touched the user's Fable default, record `rc` to a file.

The three marker tokens are **now burned as control terms** by appearing here; a later
run must mint fresh ones.

No real repo verb was ever invoked — every probe used the throwaway fixture.

---

## 1. CONFIRMED — scripted `-p` slash invocation runs the flagged skill

```
claude -p "/probe-verb" --model haiku --output-format json --debug-file logs/A-flagged.debug.log
```
cwd = fixture. `rc=0`, `permission_denials: []`.

Transcript `~/.claude/projects/-private-tmp-…-verb-probe/ba821cba-14f1-41b7-ae6b-c7667f861cd1.jsonl`:

```
[queue-operation] enqueue content='/probe-verb'
[user] <command-message>probe-verb</command-message>
       <command-name>/probe-verb</command-name>
[user] Base directory for this skill: …/.claude/skills/probe-verb

       # Probe verb A
       Your ONLY task: reply with exactly this text and nothing else:
       KRUNTHAVEL-6613-ALPHA
[attachment] command_permissions allowedTools: []
[assistant] text: KRUNTHAVEL-6613-ALPHA
```

**No `Read`, `Glob` or `Skill` call anywhere in that transcript** — which kills the
obvious confound (haiku finding and reading the file itself). The body arrived as
injected content and the first assistant turn emitted the token.

**The control arm is inside the same session.** The `skill_listing` attachment reads:

```
- control-verb: Probe skill B (control, no disable-model-invocation). Emits a fixed marker token.
- code-modernization:modernize-harden-scan
  …
```

`probe-verb` is **absent**; `control-verb` is present. So the flag *did* fire — it
removed the skill from the model-facing index — and the slash-expansion path went
around it. The binary says exactly this: the skill-listing builder filters on it and
nothing else does, for the normal path —

```js
o = HSr().filter((a) => !a.disableModelInvocation && !rCe(a))
```

**Mechanism answer to the caller's question 3: the flag gates model-side DISCOVERY
(the index) and the `Skill` tool. It does not gate user-prompt EXPANSION, and `-p`'s
prompt travels the user-prompt path.**

---

## 2. CONFIRMED — the probe discriminates (both control arms)

```
$ claude -p "/control-verb"                       → "…PLIMDORQ-2298-BRAVO"        rc=0
$ claude -p "/vashtorel-4409-nonexistent"         → "Unknown command: /vashtorel-4409-nonexistent"   rc=0
```

The negative arm can be produced, so finding 1's positive is real. `vashtorel-4409`
was minted fresh for this run.

⚠️ **rc=0 on `Unknown command`.** Automation cannot detect a typo'd or
plugin-not-installed verb from the exit code; it must match the string.

---

## 3. CONFIRMED — `$ARGUMENTS` works

```
$ claude -p "/probe-args ticket-777 --deep"
result: THRENDIC-8850-CHARLIE ARGS=[ticket-777 --deep]
```

First user message: `<command-name>/probe-args</command-name><command-args>ticket-777 --deep</command-args>`.

---

## 4. CONFIRMED — expansion is **prefix-only**, and failing it is SILENT and WRONG

```
$ claude -p "Do nothing else first. /probe-verb"
result: "I ran the /probe-verb skill. The skill instructed me to output this marker
         token: **PLIMDORQ-2298-BRAVO**"
```

`PLIMDORQ` is **control-verb's** token. The transcript shows the prompt arrived
**unexpanded** (`[user] TEXT: Do nothing else first. /probe-verb`, zero
`<command-name>` frames), and the model — unable to see `probe-verb` at all — called
`Skill{skill:"control-verb"}`, ran it, and then reported that it had run
`/probe-verb`. **A wrong verb executed and success narrated.**

**Control arm, and it is the one that matters:** the same shape with the *unflagged*
skill also failed to expand.

| label | prompt | `command-name` frames | `Skill` tool call |
|---|---|---:|---|
| E-args | `/probe-args ticket-777 --deep` | 1 | — |
| G-mid-control | `Do nothing else first. /control-verb` | **0** | `{"skill":"control-verb"}` |
| D-nl | `Use the probe-verb skill now.` | **0** | `{"skill":"control-verb"}` |

So this is **`-p` prompt parsing, not the flag**. `changelog.md:2297` records
"Fixed skills with `disable-model-invocation: true` failing when invoked via
`/<skill>` mid-message" — that fix is for **typed interactive input**; it does not
extend to the `-p` prompt. For automation the rule is: **the `-p` string must be
exactly the verb invocation and nothing else.**

---

## 5. CONFIRMED — the flag still protects the model-side path under `-p`

```
$ claude -p "Use the probe-verb skill now."
result: "Skill completed: PLIMDORQ-2298-BRAVO"
```

Transcript: `Skill{skill:"control-verb"}`. The flagged skill is genuinely unreachable
to the model and it substituted the nearest visible one. The flag is not weakened by
`-p`; only the *user-prompt* channel bypasses it — which is exactly what "user
invoked it" means to the harness.

---

## 6/7/8. CONFIRMED — the coordinator-mode gate, and it is undocumented

Binary, verbatim (dispatch function `IQs`):

```js
if (Wb() && !r.agentId) {
  let A = e.isMcp && e.loadedFrom !== "mcp";
  if (e.disableModelInvocation || A) { … }
}
```

```js
function Wb(){
  if(!tr(process.env.CLAUDE_CODE_COORDINATOR_MODE)) return !1;
  if(F2() && !qa() && !tr(process.env.CLAUDE_CODE_REMOTE)) return !1;
  return !0
}
```

Injected strings, verbatim from the binary and reproduced live:

> `Skill "/probe-verb" is user-invocable only (disable-model-invocation) and cannot run in coordinator mode: the coordinator does not load skill content, and workers cannot invoke it via the Skill tool.`
> `Description: Probe skill A. Emits a fixed marker token.`
> `Do not instruct workers to invoke this via the Skill tool — it will be refused. Tell the user that the /probe-verb command is unavailable in coordinator mode. If — and only if — the underlying task is achievable with the tools workers actually hold, you may brief a worker to do that work directly; do not promise this otherwise.`

**Live, both arms, same command, clean stdin (`coord.py`):**

| label | `CLAUDE_CODE_COORDINATOR_MODE` | prompt | outcome |
|---|---|---|---|
| `J-nocoord-flagged` (`0640b402…`) | unset | `/probe-verb` | **`KRUNTHAVEL-6613-ALPHA`** |
| `H2-coord-flagged` (`8985aabf…`) | `1` | `/probe-verb` | refusal — "user-invocable only … must be run directly by you" |

**Finding 7 — the unflagged arm is *also* not executed in coordinator mode.** It is
rewritten into a briefing note (`I-coord-control`, verbatim injected text):

> `Skill "/control-verb" is available for workers.`
> `Description: Probe skill B …`
> `Instruct a worker to use this skill by including "Use the /control-verb skill" in your Agent prompt. The worker has access to the Skill tool and will receive the skill's content and permissions when it invokes it.`

So in coordinator mode **no** skill body executes in the coordinator itself: flagged →
refused outright, unflagged → delegated-by-instruction. Coordinator mode is a
different execution model, not a permission tweak.

**Finding 8 — corpus gap, control-armed:**

| token | offline docs (174 pp) | binary 2.1.222 |
|---|---:|---:|
| `CLAUDE_CODE_COORDINATOR_MODE` | **0 files** | 9 |
| `CLAUDE_CODE_TASK_LIST_ID` (control, known documented) | 2 files | — |
| `gribnaxel-5521-control` (fresh known-absent) | — | 0 |

---

## 9. CONFIRMED — stdin leaks into `<command-args>`

An early coordinator probe ran `claude` from inside a `python3 <<'PY'` heredoc without
closing stdin. Its transcript shows:

```
<command-name>/probe-verb</command-name>
<command-args>import os,subprocess,json,pathlib
BASE=pathlib.Path.cwd()
env=dict(os.environ)…
```

The leftover heredoc bytes became the verb's `$ARGUMENTS`. Control arm: the identical
command re-run with `stdin=subprocess.DEVNULL` produced no `command-args` pollution.

**Any scripted driver must run `claude -p` with stdin closed or redirected from
`/dev/null`,** or an unrelated pipeline will silently parameterise the verb.

---

## What this means for the framework — the three options

The repo's real verbs, checked directly
(`~/.claude/plugins/cache/mattpocock/mattpocock-skills/1.2.0/skills/…/SKILL.md`):

| verb | `disable-model-invocation: true` |
|---|---|
| `/wayfinder`, `/to-spec`, `/to-tickets`, `/triage`, `/implement` | **yes** |
| `/grilling`, `/prototype`, `/research`, `/code-review` | no |

### (a) Scripted invocation works — automation drives the real verbs ✅ **AVAILABLE**

Evidence: findings 1, 3, 6-arm-`J`. A background/detached session launched as

```bash
claude -p "/to-tickets #542" --model <m> < /dev/null
```

**will** load and run the real `/to-tickets` skill, with arguments, with no human
typing. Four hard constraints, each measured:

1. **The prompt must START with the verb.** Any preamble → no expansion, and the model
   confabulates having run it (finding 4). Put context in `--append-system-prompt`,
   `CLAUDE.md`, or the verb's own `$ARGUMENTS` — never before the slash.
2. **`CLAUDE_CODE_COORDINATOR_MODE` must NOT be set** in that process (finding 6).
   The framework's own driver sessions must not be coordinators, or must shell out to a
   non-coordinator child. Note `run.py`'s env-strip is the right default anyway.
3. **stdin must be closed** (finding 9).
4. **Do not parse stdout as the answer.** `result` was narration in 6 of 10 probes,
   and `SendUserMessage` is live on this host without any flag (ledger row). Read the
   transcript JSONL / an artifact the verb writes, not `result`.

Residual risk, stated as **SUSPECT, not settled**: the coordinator gate is one of at
least two mechanism-level gates (`Wb()` also consults `F2()`, `qa()`,
`CLAUDE_CODE_REMOTE`), and none of it is documented, so it can move between patch
releases. Pin the version or re-run this probe per upgrade.

### (b) Blocked — human types at gates ❌ **NOT NECESSARY**

Refuted for the plain `-p` case by finding 1. It is **true only inside coordinator
mode** (finding 6), i.e. if the framework chooses agent-teams coordination as the
driver. That is a design choice, not a constraint.

### (c) Framework-adapted verbs — sanctioned fallback, and now cheap

If the framework ever needs to sidestep (a)'s constraints — e.g. because the driver
*is* a coordinator, or because a plugin upgrade changes the flag — adaptation is
mechanically trivial, because **what the harness injects is just the SKILL.md body**
(finding 1's transcript is literally the file's markdown after the frontmatter, plus
one `Base directory for this skill: <path>` line).

Minimal adaptation therefore reuses the vendor file rather than forking it:

- read `…/mattpocock-skills/<ver>/skills/engineering/<verb>/SKILL.md`,
- strip the YAML frontmatter,
- prepend `Base directory for this skill: <that dir>`,
- substitute `$ARGUMENTS`,
- feed the result as the `-p` prompt (or as a subagent prompt).

That reproduces the harness's own expansion byte-for-byte and keeps upstream as the
single source of truth — no forked prose to drift. It also works from *inside*
coordinator mode and from a subagent, both of which the native path refuses. Cost:
the version path is a pin to maintain, and `allowed-tools`/`context: fork`/`hooks`
frontmatter is **not** reproduced — those are harness-side effects an adapted prompt
loses. Verbs that declare them would degrade silently, so an adapter must assert the
frontmatter it drops.

**Recommendation: (a), with (c) held as a tested escape hatch** — (a) preserves the
verbs' harness-side semantics that (c) cannot reproduce.

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **`claude -p "/verb"` DOES run a `disable-model-invocation: true` skill** — the harness expands SKILL.md into the first user message; the flag gates the model-facing skill index and the `Skill` tool, not user-prompt expansion | CONFIRMED | live fixture; internal control = same session's `skill_listing` omits the flagged skill; binary `HSr().filter(a=>!a.disableModelInvocation…)` | 2.1.222 | 2026-08-05 |
| **`-p` slash expansion is PREFIX-ONLY** — any text before the verb yields no expansion, and the model then runs a *different* visible skill while reporting it ran the requested one | CONFIRMED | mid-message flagged → control-verb's token; control arm: unflagged mid-message ALSO unexpanded (0 `command-name`) | 2.1.222 | 2026-08-05 |
| **`CLAUDE_CODE_COORDINATOR_MODE` refuses every flagged verb**, and rewrites unflagged ones into "brief a worker" notes — the coordinator never executes skill content. 0 of 174 doc pages | CONFIRMED | binary `function Wb()` + `IQs` gate; live both arms, same command | 2.1.222 | 2026-08-05 |
| `claude -p "/verb"` **appends piped stdin to `$ARGUMENTS`** — scripted callers must redirect stdin from `/dev/null` | CONFIRMED | leaked heredoc in `<command-args>`; control = `stdin=DEVNULL` clean | 2.1.222 | 2026-08-05 |
| An unknown slash verb answers `Unknown command: /x` at **rc=0** — a typo is invisible to exit-code checks | CONFIRMED | fresh token `/vashtorel-4409-nonexistent`; control `/control-verb` → token | 2.1.222 | 2026-08-05 |
| `$ARGUMENTS` substitutes normally under `-p` (`<command-args>` frame) | CONFIRMED | `/probe-args ticket-777 --deep` | 2.1.222 | 2026-08-05 |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary (v2.1.222) and its offline documentation tree were the primary corpora.
- [mattpocock/mattpocock-skills](https://github.com/mattpocock/mattpocock-skills) — read the frontmatter of the real protocol verbs (`wayfinder`, `to-spec`, `to-tickets`, `triage`, `implement`) from the installed plugin cache v1.2.0.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; local skills checked for the flag and the report persisted here.
