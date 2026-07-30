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

## The wipe RECURRED, and its signature is not what we documented (2026-07-30)

The `env = "exec"` mode is **not durable**. Measured, on the day the #418 doctor
shipped:

| time (local) | event |
|---|---|
| 20:07 | `CONTEXT7_API_KEY` opted back in (4th opt-in). Verified: `fnox export` names **4 of 49** |
| ~20:10 | `mise run doctor` → `fnox-baseline` PASS |
| **00:47** | **`~/.config/fnox/config.toml` rewritten.** Global `env = "exec"` line GONE, all **4** per-secret `env = true` fields GONE |
| 05:48 | `mise run doctor` → `fnox-baseline` **DRIFT**, on its first real firing |

For that ~5-hour window every one of the **49** credentials was shell-visible
again, inherited by every child process — the exact exposure this rule exists to
prevent. Restored and control-armed: `fnox export` back to 4 of 49, doctor 7/7.
The wiped file is preserved at
`~/.config/fnox/config.toml.WIPED-evidence-20260730-055104`.

**Two corrections to what this repo asserted.**

1. **The documented `bootstrap-config` signature is only a PARTIAL match.** The
   rule says that generator drops `env = "exec"`, the opt-ins **and the 49
   `sync` blocks**. Here **all 49 sync blocks survived**, along with all 3
   providers; the file *grew* by 170 bytes while losing 4 lines. Only the `env`
   fields went. So either that generator changed, or something else did this —
   and a signature that matches half-way is not an attribution.
2. **The trigger is UNATTRIBUTED.** No LaunchAgent, no crontab entry, and
   `mde-py` is not on `PATH` in the shell at all. Naming `bootstrap-config` as
   the cause here would be exactly the [[probes-need-a-control-arm]] failure of
   reading a plausible secondary story as a measurement.

**Untested hypothesis, recorded as such:** fnox re-serialising its own config
after a sync/re-encrypt and dropping `env` fields it does not round-trip on
write. The 170-byte growth with sync intact fits a re-encrypt rewrite. If true,
the rule blames the wrong tool entirely. The only arm that can settle it is a
**real** `fnox sync` write with a before/after hash — a `--dry-run` cannot, since
the whole suspected defect lives in the write path (the #370 lesson, one tool
over). Authorized by Ray 2026-07-30, backup first; not yet run.

**The durable lesson:** "APPLIED 2026-07-27 by Ray" was recorded as a settled
state, and nothing re-read the artifact for three days. A config you do not own
the generator for is not fixed by editing it once — it is fixed by a check that
re-reads it, which is what `fnox-baseline` now is.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  `no_env_dump` gate, `env_blob_scan.py`, and the history pickaxe.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the second public repo checked by the same pickaxe.
