# Evidence — `secrets-out-of-the-shell-env`

The 2026-07-27 incident and its measurements, behind
`.claude/rules/secrets-out-of-the-shell-env.md`. The eager rule carries the
directive, the fix, and the gates; this file carries what happened and how each
claim was measured.

## What happened (2026-07-27)

`fnox activate` exported 49 variables into the login shell. mise records the
whole environment delta in **`__MISE_DIFF`** (zlib-compressed, base64-encoded) so
it can undo it on directory exit, and that variable is inherited by every child.
Decoded, the live blob carried an AWS access key id and secret, several API
tokens, an app password, and a Google client secret.

**Nothing reached a public remote.** Verified by pickaxing the exact live values
across the full history of both public repos: **0 commits** each, against a
control term returning 339 (dotfiles) and 94 (knowledge-base), so the probe
discriminates. The single `AKIA` in dotfiles history is a vendor example inside
`docs/research/mintlify-cache/`.

The exposure was real anyway: the blob sat in every child process, and one
`env > notes.md` inside a tracked directory would have published all of it.

## Why no scanner would have caught it

Measured 2026-07-27 with synthetic, format-valid credentials — the same content
in two forms:

| scanner | plaintext env dump | the same content as a `__MISE_DIFF` blob |
|---|---|---|
| gitleaks 8.30.1 | **2 leaks** | **0** |
| betterleaks 1.7.1 | **1 leak** | **0** |

The control arm fires on the plaintext, so the zero is a real negative and not a
blind probe. Both scanners are pattern matchers; compression destroys the
patterns. This is the one gap that justifies custom code here at all — and the
custom code covers only the decode.

## The fix was probed, not quoted

Probed on the pinned **1.31.1** in a throwaway project, both arms: with
`env = "exec"`, `fnox export --format shell` emitted **only** the `env = true`
opt-in, while `fnox exec -- env` still carried both. The rule's table is the
tool's measured behaviour here, not a restatement of its release notes.

## Applying it — three findings

1. **A local override is NOT honoured at the user config root.** The config is
   `~/.config/fnox/config.toml`, and `fnox config-files` lists it alone; adding
   `config.local.toml` or `fnox.local.toml` beside it changed that output not at
   all. Control arm: in a *project* directory the same command lists `fnox.toml`
   **and** `fnox.local.toml` **and** the user root — three lines — so it can
   report more than one file. The override layer is project-scoped only.
2. **The file is generated.** Its first line reads *"Managed by `mde-py secrets
   bootstrap-config`. Do not edit by hand."*, so a hand edit survives only until
   the next bootstrap. The durable fix belongs in **`mde-py`'s generator**.
3. **Two variables must be opted back in with `env = true`, and they are the two
   this repo runs on.** `.mcp.json` interpolates one at MCP-server spawn, and
   `gh` — which `ship`/`land`/`automerge` and every `gh api` call use — reports
   its *active* account as the environment-authenticated one, with a
   narrower-scoped fallback behind it. Exec-only for those two degrades tooling
   silently rather than loudly.

   A grep of `~/.zshrc`, `~/.zprofile`, `~/.config/mise/config.toml`,
   `~/.claude/settings.json`, `~/.gitconfig` and `home/**` for all 49 names found
   **zero** other declared consumers (control arm: 7 hits for
   `export|source|eval` in the same `.zshrc`, so the grep works). State that
   bound: it finds *declared* consumers only. A tool that reads a variable by
   convention appears in no config file, so absence here is not absence.

## APPLIED 2026-07-27 — by Ray, not by an agent

The standing rule is to never touch a user-level file unasked
(`feedback_no_user_level_file_updates`). Ray approved this one edit explicitly,
and the harness permission layer *still* refused the write — correctly, and
independently of that approval. **Two layers, and the outer one does not read
approvals.** So the recipe was prepared here and Ray ran it: 46 of the 49
exec-only, 3 opted back in.

Verified in a **fresh interactive login shell**, not the session's own: the
opted-in variable is set, two exec-only ones are not, and the recorded delta
shrank from ~16.8 KB decoded to a 5.2 KB blob.

The first attempt at that verification was **broken and looked like a clean
pass** — `zsh -l -c` (non-interactive) never sources `.zshrc`, so nothing
activated and the variable was "absent". The control arm, the same probe against
the pre-fix config, ALSO said "absent", which is the only reason it was caught.
`-i` is what makes the probe able to answer.

## The same setting fixed the `[redacted]` digit-masking

mise redacts every occurrence of a redacted variable's **value** in task output.
fnox marked all 49 of its variables redacted, and two of them —
`GEMINI_TELEMETRY_ENABLED` and `GEMINI_TELEMETRY_LOG_PROMPTS` — held
**one-character, all-digit values**. So mise faithfully masked every digit in
every `mise run` line, which is why a number read from `mise run` output could
not be trusted. `LANGSMITH_WORKSPACE_ID` was worse: an **empty** value.

Those are telemetry flags, not secrets. The digit-masking was never a mise bug;
it was collateral from treating a non-secret as a secret. It returns if `mde-py`
re-bootstraps the config.

## The wipe RECURRED — and the diagnosis (2026-07-30)

The `env = "exec"` mode is **not durable**. Measured, on the day the #418 doctor
shipped:

| time (**local CDT**) | event |
|---|---|
| 20:07 (Jul 29) | `CONTEXT7_API_KEY` opted back in (4th opt-in). Verified: `fnox export` names **4 of 49** |
| ~20:10 | `mise run doctor` → `fnox-baseline` PASS |
| **00:47 (Jul 30)** | **`~/.config/fnox/config.toml` rewritten.** Global `env = "exec"` GONE, all **4** per-secret `env = true` GONE |
| 00:48 | `mise run doctor` → `fnox-baseline` **DRIFT**, on its first real firing |
| 00:50 | Restored; `fnox export` back to 4 of 49, doctor 7/7 |

For that ~4h40m window every one of the **49** credentials was shell-visible
again, inherited by every child process — the exact exposure this rule exists to
prevent. The wiped file is preserved at
`~/.config/fnox/config.toml.WIPED-evidence-20260730-055104` (that suffix is
**UTC**; the file dates from 00:51:04 local).

> ⏰ **Read the clock before reading the timeline.** The first write-up of this
> incident mixed local and UTC stamps in one table, which put the wipe "last
> night" when it had happened **30 minutes earlier**. `date -u`-derived filenames
> and locally-observed mtimes do not belong in the same column unlabelled.

### What actually changed in the file

Diffing the three states with a TOML parser (keys and value **lengths** only,
never values — `scratchpad/fnox_structdiff.py`):

| | pre-wipe backup | WIPED | restored |
|---|---|---|---|
| global `env` | `"exec"` | **absent** | `"exec"` |
| per-secret `env = true` | 3 (pre-CONTEXT7) | **0** | 4 |
| secrets / providers | 49 / 3 | 49 / 3 | 49 / 3 |
| `sync.value` ciphertexts | — | **all 49 REPLACED** (net +436 chars) | unchanged from WIPED |
| outer `value`, `provider` | — | unchanged for all 49 | unchanged |

**This overturns the first write-up's correction #1.** "All 49 sync blocks
survived" is true only *structurally*: every ciphertext inside them was
regenerated. The event was a **whole-config rebuild plus a full re-sync**, not a
surgical removal of `env` fields. A signature read at the wrong granularity
looked like a half-match when it was a full one.

> 🔬 **`grep -c 'env = true'` is not a control arm for "how many opt-ins".** It
> counted **5** where the parser counted **4** — the config's own header comment
> contains the literal string. Parse the format; don't pattern-match it.

### fnox is EXONERATED — hypothesis falsified with an armed probe

The recorded hypothesis was that **fnox itself** drops `env` when it
re-serialises. Ray authorized a real write against the live store (a `--dry-run`
could not settle it — the suspected defect lived in the write path, the #370
lesson one tool over). Backup first, byte-exact restore after, names never values:

| probe | wrote? | `env` preserved? |
|---|---|---|
| `fnox activate zsh` | **no** | n/a |
| `fnox hook-env -s zsh` (the precmd hook) | **no** — hash byte-identical | n/a; correctly exported an opt-in |
| `fnox sync -g -p age <ONE> -f` | yes — 1/49 ciphertexts | **yes** — global + all 4 |
| `fnox sync -g -p age -f` (all) | yes — **49/49**, reproducing the wipe's exact ciphertext signature | **yes** — global + all 4 |

The bulk arm is what makes this a real negative: it rewrote every one of the 49
values, so it *could* have dropped the `env` fields, and did not. **fnox
round-trips `env` on both its scoped and its bulk write path.**

`fnox activate` is control-armed for free by any agent session: the Bash tool
sources `~/.zshrc` on every call (that is where the `fnox` shell function comes
from), and the config mtime does not move across dozens of calls.

### The author: the mde-py composite, not either half alone

`macos-development-environment/src/mde/secrets/manage.py` (line refs
**re-derived**, not inherited):

- **`bootstrap_config()` — L247.** Rebuilds the file from scratch as a list of
  literal lines. It emits `KEY = { provider, value }` (**L318**) and preserves
  **only** `DOPPLER_TOKEN` (L292-296). It never reads or re-emits `env`, so the
  global `env = "exec"` and every per-secret `env = true` are **dropped by
  construction**. The "Do not edit by hand" header is written at L275.
- It writes **no `sync` blocks at all** — so bootstrap alone *cannot* produce the
  wiped file, which had all 49.
- **`add_secret` (L166)** and **`remove_secret` (L208)** each call it and then
  immediately run a **full** `_run_fnox_sync_age()` (**L169** / **L211**), which
  regenerates all 49 sync blocks with fresh ciphertexts. `update_secret` (L177)
  is an alias for `add_secret`.

`bootstrap_config` + full sync reproduces the observed signature **exactly**, and
neither half does on its own. ✅ The inherited `manage.py:318` reference is
correct.

### The invoker: `mde-secret-add`, run by hand — the DOCUMENTED happy path

A first pass reported the invoker "non-interactive and unlogged". **That was
false, and the fault was the probe, not the world.** The command was in
`~/.zsh_history` the entire time:

| time (CDT) | event | source |
|---|---|---|
| 00:45:36 | Ray asks an agent "i have a linear key how do i set it?" | codex session rollout |
| 00:46:11 | the agent, reading the mde repo's own docs, answers **"run `mde-secret-add LINEAR_API_KEY`"** | codex session rollout |
| **00:46:51** | Ray runs `source ~/.zshrc` **then `mde-secret-add LINEAR_API_KEY`** — *one multi-line history entry* | `~/.zsh_history` |
| **00:47:00** | config rewritten; mode + 4 opt-ins gone, 49 ciphertexts fresh | the artifact |
| 00:47:19 | Ray confirms "it is set" | codex session rollout |

`add_secret` is an **upsert** and `LINEAR_API_KEY` already existed — which is why
the key count stayed at 49, and why "an update of an existing key" was deducible
from the artifact before the command was found.

> 🔬 **A multi-line history entry defeated a single-line parser, and the absence
> was reported as a finding.** zsh writes an entry as `: <epoch>:<elapsed>;` plus a
> body that may span lines (continuations end with `\`). The parser was
> `^: (\d+):(\d+);(.*)$`, so it captured `source ~/.zshrc` and **silently dropped
> the `mde-secret-add` on the next line**. Split on the *marker* and take
> everything up to the next one.
>
> The control arm that ran was on the wrong property: it confirmed `sharehistory`
> was set — that the **file** was complete — which was true and irrelevant, because
> the broken component was the **reader**. Arm the step you actually depend on. The
> cheap catch here: grep the corpus for a token you know is present
> (`mde-secret` → 2 hits, ever) instead of trusting a structured parse.

Ruled out along the way, each with a control arm (the first pass's negatives came
from bounded probes, so they were re-run):

| ruled out | control arm |
|---|---|
| launchd | 8 user plists, none match mde/fnox/secret/doppler by **content**; 7 match `Label`, so the grep can see. The mde maintenance/validation agents are not installed. (First pass grepped *labels* with `head -5`.) |
| any Claude session | **zero** tool calls 00:44-00:49 across **2272 transcripts / 70 projects**; the dotfiles session was idle 00:43:44 → 00:48:19 |
| a Claude **hook** (invisible to transcripts) | no settings file invokes `mde-py`; `.claude/settings.json` matches `hooks` 6× |
| a mise `enter` hook | **no `[hooks]` in any mde mise config** — the leading hypothesis, killed by reading the config rather than probing |
| mde-py's own logging | no `bootstrap_config_written` anywhere; mde logs stale since **April**, so this route could never have answered |

**Doppler's audit log is INCONCLUSIVE, not negative** — `doppler activity`
returns empty because the token lacks workplace scope, while `doppler secrets
--only-names` returns rows. A "never asked", not a "no"
([[probes-need-a-control-arm]] rule 4).

### Why this is severe rather than a one-off

`mde-secret-add` / `-update` / `-rm` are **the sanctioned interface** — an agent
reading the repo's docs recommends them unprompted, which is exactly what
happened. So **every secret added or updated re-exposes all 49 credentials** to
the shell until something re-reads the config. Filed with the confirmed trigger as
[macos-development-environment#82](https://github.com/ray-manaloto/macos-development-environment/issues/82).

**The durable lessons:**

1. "APPLIED 2026-07-27 by Ray" was recorded as settled and nothing re-read the
   artifact for three days. A config whose generator you do not own is not fixed
   by editing it once — it is fixed by a check that re-reads it, which is what
   `fnox-baseline` is.
2. **An untested hypothesis, left in place, quietly becomes the working story.**
   The rule blamed fnox for a day on plausibility alone; one authorized write
   settled it in two commands.
3. **"I could not find it" is not "it is not there."** Publishing an absence as an
   attribution ("non-interactive and unlogged") dressed a failed search as a
   conclusion. An unattributed cause is an open question, and it should be
   labelled as one until a *source* — not a silence — closes it.

## The `:-` fallback leak — 2026-08-02-g, the same rule's second breach that day

Rule 7 was written earlier the same day, after a `${(P)k}` expansion printed four
live credentials. Hours later, an agent **holding that rule and citing it** ran:

```sh
printf "%s" "${DOPPLER_TOKEN:+PRESENT}${DOPPLER_TOKEN:-ABSENT}"
```

which printed `PRESENT` followed by the live `dp.ct.` Doppler CLI token. It had to
be rotated.

### Why it passed review

`${VAR:+PRESENT}` is the form the rule *recommends*. The construct opens with it,
so it reads as compliant. The leak is the second half: **`:-` is a value-emitting
substitution** — for a *set* variable it expands to the value, not to the fallback.
Reproduced on a harmless value:

| Expression (with `FOO=visible-safe-value`) | Output |
|---|---|
| `${FOO:+SET}` | `SET` |
| `[ -n "$FOO" ] && echo SET \|\| echo ABSENT` | `SET` |
| **`${FOO:+SET}${FOO:-ABSENT}`** | **`SETvisible-safe-value`** |
| `${NOPE_UNSET:+SET}${NOPE_UNSET:-ABSENT}` (unset) | `ABSENT` |

The last row is the whole trap: on an **unset** variable the bad form looks
perfect.

### Two corrections it forced in the rule

1. **"The exposed set is exactly the opt-in set" was FALSE.** The rule claimed the
   blast radius was the four `env = true` opt-ins, "knowable in advance".
   `DOPPLER_TOKEN` is **exec-only** — measured in the same command, `PRESENT` under
   `fnox exec` and `ABSENT` in a plain shell — and it leaked anyway, because the
   probe wrapped *itself* in `fnox exec`. Any of the 49 is printable by a probe
   that does that; only an **unwrapped** probe is capped at the four.
2. **The control arm certified nothing.** The probe did carry one: a nonexistent
   variable, returning `ABSENT`. That exercises the `:-` branch only on an unset
   variable — the single case where it cannot leak. Arming only the absent
   direction is `probes-need-a-control-arm.md` rule 8: a fixture that could not
   have produced the other outcome. **Arm a presence probe on a variable that IS
   set, with a value you can afford to see, before pointing it at a real one.**

### Incidental finding (why the probe was running at all)

It was checking whether a Doppler token already exists before ticket #487
provisions one. It does: `DOPPLER_TOKEN` lives in the keychain via fnox, declared
by mde's `bootstrap_config` (`src/mde/secrets/manage.py:296`) as a *declaration
only*. `doppler me` reports the CLI authenticated as `type: cli`, name
`dotfiles-20260327` — a **personal CLI login**, and the `dp.ct.` prefix confirms
`DOPPLER_TOKEN` is that same class. So #487's premise ("provision a token") is
wrong: one exists, it is the opposite of scoped/read-only/expiring, and the ticket
should begin by assessing it.

## Moved here 2026-08-03 from `docs/secrets-doppler-fnox-keychain.md`

That guide was rewritten to the current `env = true` posture. Its exec-era
sections are kept verbatim below rather than deleted — they overlap the account
above but were measured independently, and one table (the generator's emitted
field set) exists nowhere else.

### The `env` mode as that guide documented it (added 2026-07-29)

> A secret being *declared and resolvable* does **not** mean it reaches the shell.
> Since 2026-07-27 this config is globally:
>
> ```toml
> env = "exec"   # secrets stay OUT of the interactive shell
> ```
>
> | `env` | interactive shell / `fnox export` | `fnox exec` | `fnox get` |
> |---|:-:|:-:|:-:|
> | `true` (fnox default) | yes | yes | yes |
> | **`"exec"` (ours)** | **no** | yes | yes |
> | `false` | no | no | yes |
>
> Only secrets carrying an explicit per-secret `env = true` are exported. **Four
> are** — `CONTEXT7_API_KEY`, `EXA_API_KEY`, `GITHUB_TOKEN`, `MISE_GITHUB_TOKEN` —
> chosen because their consumers can *only* read the environment: the context7
> plugin interpolates `${CONTEXT7_API_KEY:-}` into an `Authorization` header, the
> `/last30days` engine's web lane reads `EXA_API_KEY` from the process environment
> (it is in neither that plugin's own `.env` nor the keychain), and `gh` and `mise`
> read their tokens.
>
> ⚠️ `EXA_API_KEY`'s recorded reason used to be "an `.mcp.json` `${VAR}`
> interpolation at MCP-server spawn". That stopped being true on 2026-07-30 when
> this repo's `.mcp.json` was emptied — but the credential is still required, by a
> second consumer that had never been written down.
>
> **This is the single most likely cause of "the variable isn't set".** It is not a
> sync failure.

The `:90` row of that guide said **3** per-secret opt-ins while `:43` said four.
That inconsistency predated the reversal and was never reconciled; the count was
3 on 2026-07-27 and 4 from 2026-07-29.

### The generator's emitted field set — measured against the live config

Unique to that guide, and the sharpest statement of the #82 defect: what
`bootstrap_config()` **emits** versus what the config **held** at the time.

> | field | present now | generator emits |
> |---|---:|---:|
> | global `env = "exec"` | 1 | **0** |
> | per-secret `env = true` | 3 | **0** |
> | `sync = { provider = "age", … }` | **49** | **0** |
>
> So a single `bootstrap-config` run silently reverts every secret to
> shell-exported — undoing the whole reason `env = "exec"` was adopted.

### 2026-07-29 — Context7 MCP ran anonymous for days; nothing noticed

The incident that produced rule 5's "check the consumer's authenticated
identity, never its connection status", kept in full because the *shape*
outlives the posture that caused it.

> The Upstash context7 plugin interpolates `"Authorization": "${CONTEXT7_API_KEY:-}"`.
> That secret is exec-only, so the header resolved to **empty** and the server used
> the anonymous tier — while reporting `✓ connected` the whole time.
>
> What made it invisible:
>
> - **`${VAR:-}` substitutes an empty string instead of failing.** Silent by
>   construction.
> - **Doppler → fnox was perfectly healthy**, so every instinct to blame "the sync"
>   was wrong. `fnox check` green; the value matched Doppler exactly.
> - **The opt-in list was drawn before the consumer existed.** The three `env = true`
>   entries were chosen 2026-07-27 for the three consumers that existed then; the
>   plugin arrived 2026-07-29 and nothing re-checked the list.
>
> Generalisation: **a new env-var consumer is a new opt-in decision, and nothing
> enforces it.** Tracked as dotfiles issue **#418** (project-doctor SessionStart
> check: every `${VAR}` interpolated by an MCP/plugin config must be `env = true`).

Under `env = true` the *mechanism* is gone — nothing is exec-only, so no
interpolation resolves empty for that reason. The **failure shape** is not: any
credential that is absent, misnamed, or unset still yields an empty string
through `${VAR:-}`, and the consumer still degrades quietly.

### Smaller facts that had no other home

Caught by an adversarial audit of the rewrite: these four were removed from the
guide with no successor text anywhere, which is deletion, not a move. Kept here.

- **The sibling-repo defect is tracked on our side too.** `bootstrap_config()`'s
  wipe class is filed upstream as `macos-development-environment#82` **and** as
  **knowledge-base issue #74**. That second pointer was the only record of our
  own tracking of it.
- **Eventual intent (Ray, 2026-07-20): migrate the integration into a skill**,
  and have the dotfiles repo manage the macOS environment. Neither is done, so
  the guide remains the interim contract.
- **fnox is shell-activated on this machine** — 3 `FNOX_*` variables present in
  a live process, `DOPPLER_TOKEN` resolving from the keychain. No bootstrap step
  is needed on this host.
- **An `age` provider is configured** with `recipients = ["age16djrq…"]`, which
  is what makes the encrypted-cache path (`fnox sync`) available at all.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  `no_env_dump` gate, `env_blob_scan.py`, and the history pickaxe.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the second public repo checked by the same pickaxe.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment)
  — `src/mde/secrets/manage.py`, issue #82, and the unmerged fix branch.

## The exec-only era (2026-07-27 → 2026-08-02) — moved out of the rule verbatim

Ray **reversed this posture on 2026-08-02**: all 49 credentials are now `env = true`,
available in every terminal and to every agent. The section below is the adoption
history of the exec-only mode it replaced, kept verbatim because the *mechanisms* it
documents are still live — `bootstrap_config()` still regenerates the config, and the
`fnox` env-mode table is still how the tool behaves.

⚠️ **One thing inverts usefully:** fnox's default `env` is `true` and
`bootstrap_config()` emits only `provider` + `value`, so a regeneration now lands on
the *desired* state for the mode. The wipe class that ate `env = "exec"` and its four
opt-ins is **benign for the mode** under the new posture; what stays fragile is any
added declaration and the `sync` blocks.

## The source fix — fnox already ships it

fnox **v1.30.0** (2026-07-09) added an exec-only env mode whose release notes
name this exact threat: it keeps secrets out of the interactive shell *"where AI
coding agents and other inherited processes would see them"*, while still
injecting them into `fnox exec` subprocesses. fnox here is **1.31.1**, so it is
available now.

```toml
# fnox.toml — one line flips the whole config to default-deny
env = "exec"

[secrets]
AWS_SECRET_ACCESS_KEY = { provider = "…" }              # exec-only
SOME_PROMPT_VAR       = { provider = "…", env = true }  # explicit opt-back-in
```

| `env` | shell / `fnox export` | `fnox exec` | `fnox get` |
|---|:-:|:-:|:-:|
| `true` (default) | yes | yes | yes |
| `"exec"` | **no** | yes | yes |
| `false` | no | no | yes |

With `env = "exec"` there is no delta for mise to record, so `__MISE_DIFF`
stops carrying credentials at the source. Everything below is the net under
that, not a substitute for it.

The table above is the tool's **measured** behaviour on the pinned 1.31.1 (both
arms probed), not a restatement of its release notes.

**APPLIED 2026-07-27 by Ray; 4 opt-ins since 2026-07-30** — 45 of 49 exec-only.
Four must stay `env = true` because this repo runs on them: the context7 plugin
interpolates `CONTEXT7_API_KEY` into an `Authorization` header (exec-only made it
an empty string and the server served an **anonymous tier while reporting
connected**), `gh` reports its active account as the environment-authenticated
one, `mise` rate-limits to 60/h without `MISE_GITHUB_TOKEN`, and the
`/last30days` engine's web lane reads **`EXA_API_KEY` from the process
environment**. Exec-only for those degrades tooling *silently*.

⚠️ **`EXA_API_KEY`'s stated reason was wrong until 2026-07-30.** It read
"`.mcp.json` interpolates it at MCP-server spawn" — true when written, false once
that server was dropped. The credential is still needed, by a consumer nobody had
recorded: it is **not** in `~/.config/last30days/.env` and **not** in the
keychain, so last30days reads it straight from the shell (probed: present at
length 36, against `AWS_SECRET_ACCESS_KEY` absent, so the check discriminates).
**A reason that names one consumer is a claim that there is only one** — and that
claim is what nearly dropped a live credential.

⚠️ **AND IT DOES NOT STAY APPLIED.** Measured 2026-07-30: the config was rewritten
~4h40m after the fix, losing the global `env` line **and all 4 opt-ins**, so all 49
credentials were shell-visible again until `mise run doctor`'s `fnox-baseline`
check caught it. **Diagnosed the same day.** `mde-py`'s `bootstrap_config()`
rebuilds the file from scratch and never re-emits `env`, so it drops the mode and
every opt-in **by construction**; the full `fnox sync` its callers run next
(`add`/`update`/`remove_secret`) regenerates all 49 `sync` blocks. That composite
matches the wipe exactly — the blocks *look* intact because every ciphertext in
them was replaced. **fnox is EXONERATED**: an authorized write probe rewrote all
49 values and preserved the mode and all 4 opt-ins, on both its scoped and bulk
paths, and fnox's `env` is a real struct field its writers round-trip.

⚠️ **The trigger is the DOCUMENTED HAPPY PATH.** It was `mde-secret-add
LINEAR_API_KEY`, run by hand after an agent recommended it from the mde repo's own
docs. So **every secret you add or update re-exposes all 49 credentials** until
something re-reads the config — which is the whole job of `fnox-baseline`. Filed
as `macos-development-environment#82`. Probe table, the timeline and the
re-derived line refs: `docs/rules-evidence/secrets-out-of-the-shell-env.md`.

⚠️ **The config is GENERATED** — *"Managed by `mde-py secrets bootstrap-config`.
Do not edit by hand."* A hand edit is therefore **not a fix, it is a patch with a
half-life**; the durable fix belongs upstream. There is no user-root local
override to hide it in; that layer is project-scoped only. What makes the hand
edit safe to rely on meanwhile is the check that re-reads the artifact every
session, not the edit itself.

This also fixed the `[redacted]` digit-masking: two fnox telemetry flags held
one-character all-digit values and were marked redacted, so mise masked every
digit in every `mise run` line. Never a mise bug — collateral from treating a
non-secret as a secret. **It returns if `mde-py` re-bootstraps the config.**

Findings, control arms, and the verification that passed while blind:
`docs/rules-evidence/secrets-out-of-the-shell-env.md`.
