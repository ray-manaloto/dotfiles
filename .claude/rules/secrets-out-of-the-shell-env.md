# Secrets in the Shell Environment

⚠️ **REVERSED 2026-08-02 by Ray, deliberately.** All credentials are now
`env = true` (**56 sanctioned as of 2026-08-29**, with ONE deliberate carve-out:
`CLAUDE_CODE_OAUTH_TOKEN` is `env = "exec"` — it overrides `/login` in every new
session and silently rebills to the old org, and it does NOT authenticate the
Anthropic SDKs; see PR #811) — available in every terminal and inherited by every child process,
including Claude Code, its subagents and any MCP server they spawn. The stated
requirement was *"in sync and available to all terminals and ai/llm agents"*.
This file is no longer "keep secrets out of the shell"; it is **the record of why
that posture existed, what the reversal costs, and which parts still bind.**

**Most of this rule survives the reversal, and rule 7 matters MORE.** What changed
is one axis — where credentials live. What did not change: an environment dump is
still unscannable and must never be committed (rule 1, gated by `no_env_dump`), a
probe must still never print a value (rule 7, **partly** gated by `secret_value_substitution`),
a non-secret must still not be marked secret (rule 3), and a clean scanner still
means "ask what it can see" (rule 4). With 50 credentials in every child instead
of 4, the blast radius of breaking any of those is **12.5× larger**, not smaller.

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

## Rules

1. **Never write an environment dump into a tracked file.** Not `env`, not
   `printenv`, not `export -p`, not a debug log that includes them. If you need
   one for diagnosis, write it to the scratchpad and delete it. ⚠️ **No secret
   scanner can read one**: mise packs the whole delta into `__MISE_DIFF` (zlib +
   base64), and compression destroys the patterns scanners match on — measured
   gitleaks 2 → 0, betterleaks 1 → 0 on the same content in two forms. That gap
   is why `no_env_dump` exists and why it is deliberately glob-less.
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
   `doctor.toml`'s `env_true` set in the same reviewed diff, or the doctor
   reports drift on the next session and someone "fixes" it back.
6. **Diagnose by layer, and never run `fnox get` to do it** (it prints a value).
   ⚠️ **The old first suspect is retired.** A present-under-`fnox exec` /
   absent-in-shell split used to mean `env = "exec"` working as designed; under
   `env = true` that outcome is **unreachable — except for the one carve-out
   above**, so for any OTHER name an absent variable is a REAL failure — never
   dismiss it. Order the new suspects: (a) a **hung `doppler` CLI**,
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
   format string "just to check". Gap tracked in #474, still OPEN: one shape is
   now gated (below), every other shape is carried by this rule alone.

   ⚠️ **IT RECURRED THE SAME DAY — the safe form is only safe ALONE.**
   `${VAR:+SET}${VAR:-ABSENT}` opens with the form this rule recommends and is a
   **leak**: `:-` and `:=` are *value-emitting* substitutions, so a **set**
   variable prints `SET<the secret>` (an *unset* one prints `ABSENT`, which is why
   it survives review and why an unset-only control arm certifies nothing — arm it
   on a variable that IS set). Want both branches? `[ -n "$VAR" ] && echo SET ||
   echo ABSENT`. **Now machine-enforced** — `hook_guard`'s
   `secret_value_substitution` denies any `echo`/`printf`/`print` of a
   credential-named variable (broader than just `:-`/`:=`, `\$\{?` optional) —
   still allows `${(P)k}` indirect expansion; this rule carries every other shape.

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
