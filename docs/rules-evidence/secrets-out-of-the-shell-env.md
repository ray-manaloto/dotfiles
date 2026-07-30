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

### The invoker is still unattributed — but the negatives are now armed

Every "not it" below was re-run with a control arm, because the first pass's
negatives came from bounded probes:

| ruled out | control arm |
|---|---|
| launchd | 8 user plists, none match mde/fnox/secret/doppler by **content**; 7 match `Label`, so the grep can see. The mde maintenance/validation agents are not installed. (First pass grepped *labels* with `head -5`.) |
| any Claude session | **zero** tool calls 00:44-00:49 across **2272 transcripts / 70 projects**; the dotfiles session was idle 00:43:44 → 00:48:19 |
| a Claude **hook** (invisible to transcripts) | no settings file invokes `mde-py`; `.claude/settings.json` matches `hooks` 6× |
| an interactive shell command | `sharehistory` is set, so history is complete and immediate (`setopt` returned 19 lines); it holds only `source ~/.zshrc` @ 00:46:51 and `cd` @ 00:48:42 |
| mde-py running at all | no `bootstrap_config_written` in any log; mde logs are stale since **April** |

**Doppler's audit log is INCONCLUSIVE, not negative** — `doppler activity`
returns empty because the token lacks workplace scope, while `doppler secrets
--only-names` returns rows. That is a "never asked", not a "no"
([[probes-need-a-control-arm]] rule 4).

So the invocation was **non-interactive and unlogged**. `source ~/.zshrc` nine
seconds earlier is a temporal correlate, but both mechanisms it fires
(`fnox activate`, then `hook-env` at the next prompt) are measured innocent.

**The durable lesson:** "APPLIED 2026-07-27 by Ray" was recorded as a settled
state, and nothing re-read the artifact for three days. A config you do not own
the generator for is not fixed by editing it once — it is fixed by a check that
re-reads it, which is what `fnox-baseline` now is. The second lesson is narrower:
**an untested hypothesis, left in place, quietly becomes the working story.** The
rule blamed fnox for a day on nothing but plausibility; one authorized write
settled it in two commands.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  `no_env_dump` gate, `env_blob_scan.py`, and the history pickaxe.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the second public repo checked by the same pickaxe.
