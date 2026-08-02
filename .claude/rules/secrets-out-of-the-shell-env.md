# Secrets in the Shell Environment

⚠️ **REVERSED 2026-08-02 by Ray, deliberately.** All 49 credentials are now
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
means "ask what it can see" (rule 4). With 49 credentials in every child instead
of 4, the blast radius of breaking any of those is **12× larger**, not smaller.

**What the reversal costs, stated plainly rather than argued away:** the exposure
[#470](https://github.com/ray-manaloto/dotfiles/issues/470) documents is now
accepted, not mitigated; `__MISE_DIFF` again carries all 49 in a form no scanner
reads; and the confinement work in
[#432](https://github.com/ray-manaloto/dotfiles/issues/432) (SCOPED-READ) and
[#441](https://github.com/ray-manaloto/dotfiles/issues/441) (agent profile) is
scoped to a hazard the host no longer avoids. Those tickets need re-judging.

**The tripwire moved, it did not go away.** `doctor.toml` now pins `env = true`
plus the **full 49-name set**, so an addition, a removal or a *rename* is still
caught in both directions (control-armed: a rename keeping the count at 49 is
reported both ways). That also lands what
[#460](https://github.com/ray-manaloto/dotfiles/issues/460) measured as the fix
for the doctor's blind zone — 14 of 49 secrets previously sat past the deepest
thing the baseline checked.

⚠️ **Never declare a keychain-backed secret without putting fnox on the item's
ACL.** fnox resolves every declaration on **every shell prompt**, and a keychain
item created by `security add-generic-password` does not list fnox, so the read
blocks on a GUI dialog forever. On 2026-08-02 that produced **190 stuck
processes**, load 13.5, and a locked login keychain. Create with
`-T <fnox real binary>` — noting the real path is version-pinned under
`~/.local/share/mise/installs/fnox/<version>/`, so the grant breaks on upgrade.

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
not edit by hand."* `bootstrap_config()` rebuilds it from scratch and re-emits only
`provider` + `value`, so it drops the global `env`, every per-secret override and
every `sync` block **by construction**. Its trigger is the documented happy path:
any `mde-secret-add` / `update` / `remove`. That is a real defect
(`macos-development-environment#82`), **not** an fnox bug — an authorized write probe
round-tripped fnox's own writers with the mode and all opt-ins preserved, on both the
scoped and bulk paths. So any hand edit here is **a patch with a half-life**, and the
durable layer is the doctor check that re-reads the artifact every session.

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
4. **`clean_env()`** (`python/src/dotfiles_setup/child_env.py`) strips
   `__MISE_DIFF` and the credential-bearing names from processes this repo
   spawns, so the blob stops travelling further than it must.

## Rules

1. **Never write an environment dump into a tracked file.** Not `env`, not
   `printenv`, not `export -p`, not a debug log that includes them. If you need
   one for diagnosis, write it to the scratchpad and delete it.
2. ⚠️ **REVERSED — secrets now live in the shell by decision.** This rule used to
   read *"a secret belongs to a process, not to a shell — reach for `fnox exec --`
   rather than exporting."* That is no longer the posture (2026-08-02). The
   consequence to internalise: `fnox exec` is no longer a confinement boundary,
   because the parent shell already has everything. **Rules 1, 4 and 7 are now the
   only things between 49 credentials and a transcript or a commit** — there is no
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
   `doctor.toml`'s 49-name `env_true` set in the same reviewed diff, or the doctor
   reports drift on the next session and someone "fixes" it back.
6. **Diagnose by layer, and never run `fnox get` to do it.** A `-v` presence test
   under `fnox exec` (present) vs the same in a plain shell (absent) identifies
   `env = "exec"` on its own; `fnox sync --dry-run -p age VAR` answers staleness
   without reading a value. Full ordered recipe, the result-reading table, and the
   ⚠️ **wipe hazard** — `mde-py`'s `bootstrap_config()` drops `env = "exec"` and
   every opt-in (measured twice; diagnosed 2026-07-30, and **not** fnox):
   `docs/secrets-doppler-fnox-keychain.md`.
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

   ⚠️ **The blast radius is NOT capped at the opt-ins.** This file claimed
   *"exactly the opt-in set, knowable in advance"* — **false for a probe run under
   `fnox exec`**. The leaked `DOPPLER_TOKEN` is **exec-only** (same command:
   `PRESENT` under `fnox exec`, `ABSENT` in a plain shell); wrapping the probe put
   it in reach. Any of the 49 is printable that way; only an *unwrapped* probe is
   capped at four. Full incident, the reproduction table and both corrections:
   `docs/rules-evidence/secrets-out-of-the-shell-env.md`.

## See also

- `probes-need-a-control-arm.md` — every measurement above ran both arms.
- `use-tool-builtins.md` — the gate that made this research-first; the fix was
  a tool feature, and the custom code is only what no tool can do.
- Memory `feedback_no_user_level_file_updates` — why the fnox change is
  written up rather than applied.
- `python/src/dotfiles_setup/env_blob_scan.py` — the scanner and its evidence.
