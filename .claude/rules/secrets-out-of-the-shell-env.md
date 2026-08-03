# Secrets in the Shell Environment

⚠️ **REVERSED 2026-08-02 by Ray, deliberately.** All 50 credentials are now
`env = true` — available in every terminal and inherited by every child process,
including Claude Code, its subagents and any MCP server they spawn. The stated
requirement was *"in sync and available to all terminals and ai/llm agents"*.
This file is no longer "keep secrets out of the shell"; it is **the record of why
that posture existed, what the reversal costs, and which parts still bind.**

**Most of this rule survives the reversal, and rule 7 matters MORE.** What changed
is one axis — where credentials live. What did not change: an environment dump is
still unscannable and must never be committed (rule 1, gated by `no_env_dump`), a
probe must still never print a value (rule 7, gated by `secret_value_substitution`),
a non-secret must still not be marked secret (rule 3), and a clean scanner still
means "ask what it can see" (rule 4). With 50 credentials in every child instead
of 4, the blast radius of breaking any of those is **12.5× larger**, not smaller.

**What the reversal costs, stated plainly rather than argued away:** the exposure
[#470](https://github.com/ray-manaloto/dotfiles/issues/470) documents is now
accepted, not mitigated; `__MISE_DIFF` again carries all 50 in a form no scanner
reads; and the confinement work in
[#432](https://github.com/ray-manaloto/dotfiles/issues/432) (SCOPED-READ) and
[#441](https://github.com/ray-manaloto/dotfiles/issues/441) (agent profile) is
scoped to a hazard the host no longer avoids. Those tickets need re-judging.

**The tripwire moved, it did not go away.** `doctor.toml` now pins `env = true`
plus the **full 50-name set**, so an addition, a removal or a *rename* is still
caught in both directions (control-armed: a rename keeping the count at 50 is
reported both ways). That also lands what
[#460](https://github.com/ray-manaloto/dotfiles/issues/460) measured as the fix
for the doctor's blind zone — 14 of the then-49 secrets sat past the deepest
thing the baseline checked.

⚠️ **A keychain credential can hang a background process forever — and that hang
is NOT a locked keychain.** `security show-keychain-info` **prompts
unconditionally**, so its hang proves nothing; believing it cost ~2 hours on
2026-08-02. Arm it instead: **fnox reads a keychain secret in 0.03s**, which a
locked keychain cannot do. What actually blocks is an *authorization* dialog for
an item a non-GUI process may not read — and nothing can answer that dialog.
Measured: `gh` and `doppler` both kept their tokens in the keychain and hung
forever from background processes (**190 stuck processes**, load 13.5). The
discriminating arm is the same command with an isolated config dir, which returns
in **0.45s**. Both entries were deleted (`security delete-generic-password -s
'gh:github.com'` / `-s 'doppler-cli'`) and both now fall through to their ENV
token.

⚠️ **This reaches fnox: its doppler provider SHELLS OUT to the `doppler` CLI**
(error text `Doppler: command failed` — a subprocess failure). A hung `doppler`
hangs every **uncached** Doppler read, on every shell prompt. That is why
`AGE_PRIVATE_KEY` would not declare until the `doppler-cli` entry was gone — two
attempts auto-rolled-back and the declaration was wrongly blamed.

Creating a keychain item with `security add-generic-password`? Grant the reader on
the ACL (`-T <real binary>`) — fnox's path is version-pinned, so the grant breaks
on upgrade. And `-w` returns **HEX** for a multi-line value (`AGE_PRIVATE_KEY`:
377 bytes back vs 188), so consumers must decode.

## What happened originally, and why no scanner caught it

`fnox activate` exported 49 credentials into the login shell. mise records the
environment delta in **`__MISE_DIFF`** (zlib + base64) so it can undo it on
directory exit, and every child process inherits that variable. Nothing reached a
public remote, but the blob sat in every child, and one `env > notes.md` in a
tracked directory would have published all of it.

**No secret scanner can read it** — measured on the same content in two forms:
gitleaks 8.30.1 went **2 leaks → 0**, betterleaks 1.7.1 **1 → 0**. The control
arm fires on the plaintext, so the zero is a real negative. Compression destroys
the patterns both scanners match on. That gap is the one thing justifying custom
code here at all (see [[use-tool-builtins]]), and it covers only the decode.

Full incident, measurements and control arms:
`docs/rules-evidence/secrets-out-of-the-shell-env.md`.

## The mechanism, and the generator that keeps eating it

fnox's `env` setting has three values: `true` (default — shell, `exec` and `get`),
`"exec"` (not the shell), `false` (`get` only). Per-secret `env` **overrides the
global**, which is why flipping the global alone changes nothing.

⚠️ **The config is GENERATED** — *"Managed by `mde-py secrets bootstrap-config`. Do
not edit by hand."* `bootstrap_config()` used to rebuild it re-emitting only `provider`
+ `value`, dropping the global `env`, every per-secret override and every `sync` block
**by construction**, on the documented `mde-secret-add` / `update` / `remove` path.
✅ **FIXED 2026-08-03** — `macos-development-environment#82` CLOSED, #83 merged as
`716b17d`: declarations are added and removed by invoking `fnox` itself, so there is no
template left to drop a field from. fnox was never at fault. What SURVIVES the fix: every
add/remove still churns all 49 `sync` ciphertexts, and one stale local branch still
carries the pre-fix code — so the durable layer is still the doctor check, not a hand edit.

The exec-only era's full adoption history — the mode table, the four opt-in reasons,
the `EXA_API_KEY` misattribution, and the measured wipe timeline — is in
`docs/rules-evidence/secrets-out-of-the-shell-env.md`.

## The gates that now exist in this repo

1. **`no_env_dump`** (`hk.pkl` → `dotfiles-setup env-blob-scan`) rejects a
   committed environment dump: a `__MISE_DIFF` assignment, **any** base64 run
   that decompresses to text naming two or more secret-bearing variables, or a
   literal credential value. Deliberately **glob-less** — a dump can land in any
   tracked file, and the directories most likely to receive one
   (`docs/research/kb/`, `docs/research/runs/`) are both tracked *and*
   allowlisted in `.gitleaks.toml`, so gitleaks is looking away from exactly
   the wrong place. Only `docs/research/mintlify-cache/` is exempt (vendor docs
   with documented example keys).
2. **`betterleaks`** (`hk.pkl`, host-only) now really runs.
   `docs/hk-builtins-audit.md` listed it as a "second scanner alongside
   gitleaks" since that audit was written and it was never wired — 0 occurrences
   in any `.pkl`, against a control of 1 for `Builtins.gitleaks`. A doc
   asserting a security scanner runs when it does not is worse than not claiming
   it. It sits in the project config rather than `hk-common.pkl`'s shared
   `security` group because that group is spread into `hk-image.pkl`, which
   would require pinning the tool in the shared mise fragment — a base image
   build input, and a cold rebuild for no gain at the commit boundary.
3. **`mise run doctor`** (#418, SessionStart hook) checks rules 1, 3 and 5 below
   against this host every session: every `${VAR}` an MCP config interpolates
   must actually be set in the process that spawns the server, and fnox's env
   mode + opt-in set must match the reviewed baseline in `doctor.toml`. It is a
   hook and not an hk step because it reads `~/.config/fnox`, which CI has not
   got. Rule 5 was doc-only until it existed.
4. **`without_env_diff()`** (`child_env.py`) strips `__MISE_DIFF` from spawned
   children — really wired, at `graphify.py` and `graph_bakeoff.py`. ⚠️ Its
   sibling **`clean_env()` has ZERO production call sites** (control arm: the
   same grep finds both `without_env_diff` ones), yet this file claimed it as a
   gate — the defect it convicts betterleaks of, two entries above. Leave it
   unused: wiring it would strip `GITHUB_TOKEN` from tools that need it.

## Rules

1. **Never write an environment dump into a tracked file.** Not `env`, not
   `printenv`, not `export -p`, not a debug log that includes them. If you need
   one for diagnosis, write it to the scratchpad and delete it.
2. ⚠️ **REVERSED — secrets now live in the shell by decision.** This rule used to
   read *"a secret belongs to a process, not to a shell — reach for `fnox exec --`
   rather than exporting."* That is no longer the posture (2026-08-02). The
   consequence to internalise: `fnox exec` is no longer a confinement boundary,
   because the parent shell already has everything. **Rules 1, 4 and 7 are now the
   only things between 50 credentials and a transcript or a commit** — there is no
   second line behind them any more.
3. **Do not mark a non-secret as a secret.** Redaction is value-based, so a
   short or empty "secret" corrupts every log the tool writes.
4. **When a scanner reports clean, ask what it can see.** Compression, encoding,
   and a path allowlist each turn "no findings" into "never looked".
5. **A new SECRET is now the reviewed decision — the old trap inverted.** Under
   `env = "exec"` the hazard was a *consumer* silently getting an empty `${VAR}`
   and dropping to an anonymous tier (context7 MCP, 2026-07-29) — so **check a
   consumer's authenticated identity, never its connection status** still holds
   whenever anything is exec-only or absent. Under `env = true` that trap is gone
   and the reviewed decision moves to the other end: **adding a secret to fnox now
   puts it in every terminal and every agent by default**, so it must be added to
   `doctor.toml`'s 50-name `env_true` set in the same reviewed diff, or the doctor
   reports drift on the next session and someone "fixes" it back.
6. **Diagnose by layer, and never run `fnox get` to do it** (it prints a value).
   ⚠️ **The old first suspect is retired.** A present-under-`fnox exec` /
   absent-in-shell split used to mean `env = "exec"` working as designed; under
   `env = true` that outcome is **unreachable**, so an absent variable is a REAL
   failure — never dismiss it. Order the new suspects: (a) a **hung `doppler` CLI**,
   since fnox shells out to it and any uncached doppler-primary secret resolves
   through that child; (b) a stale **`MISE_ENV_CACHE`** entry, which can serve a
   dead name in ONE directory long after the config is byte-identically restored,
   and which `grep` cannot see because it is encrypted; (c) the declaration itself.
   The recipes live in `docs/secrets-doppler-fnox-keychain.md` (rewritten to this
   posture 2026-08-03).
7. **⚠️ A probe's OWN STDOUT is an uncovered surface — print presence, never a
   value.** Every gate above guards a *file write* or a *spawn*; none guards the
   output of a command an agent runs, and that output lands in the session
   transcript. Measured 2026-08-02: a `${(P)k}` expansion meant as a presence flag
   printed four live credential values, and all four had to be rotated. They were
   the four `env = true` opt-ins. Use `${VAR:+SET}`, `[ -n "$VAR" ]` or
   `printenv VAR >/dev/null` and read the rc; never interpolate the value into a
   format string "just to check". Gap tracked in #474; no machine layer exists yet,
   so this rule is the only layer.

   ⚠️ **IT RECURRED THE SAME DAY — the safe form is only safe ALONE.**
   `${VAR:+SET}${VAR:-ABSENT}` opens with the form this rule recommends and is a
   **leak**: `:-` and `:=` are *value-emitting* substitutions, so a **set**
   variable prints `SET<the secret>` (an *unset* one prints `ABSENT`, which is why
   it survives review and why an unset-only control arm certifies nothing — arm it
   on a variable that IS set). Want both branches? `[ -n "$VAR" ] && echo SET ||
   echo ABSENT`. **Now machine-enforced** — `hook_guard`'s
   `secret_value_substitution` denies `${<CREDENTIAL_NAME>:-|:=}` in a Bash
   command; that closes the #474 gap for this shape, and this rule still carries
   every other shape.

   ⚠️ **There is no blast-radius cap any more.** Under `env = true` **all 50** are
   printable by any probe, wrapped or not; `DOPPLER_TOKEN` is itself in the
   sanctioned shell set. (This file once claimed "exactly the opt-in set" — already
   false under `fnox exec`, and the reversal widened it to everything.) The
   correction runs in the **worse** direction: assume every credential is reachable
   from any shell. `docs/rules-evidence/secrets-out-of-the-shell-env.md`.

## See also

- `probes-need-a-control-arm.md` — every measurement above ran both arms.
- `use-tool-builtins.md` — the gate that made this research-first; the fix was
  a tool feature, and the custom code is only what no tool can do.
- Memory `feedback_no_user_level_file_updates` — why the fnox change is
  written up rather than applied.
- `python/src/dotfiles_setup/env_blob_scan.py` — the scanner and its evidence.
