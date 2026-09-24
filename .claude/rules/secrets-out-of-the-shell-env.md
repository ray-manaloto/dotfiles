# Secrets in the Shell Environment

All credentials are `env = true` by Ray's decision (2026-08-02; the sanctioned
set is `doctor.toml`'s `[fnox].env_true`), with ONE deliberate carve-out:
`CLAUDE_CODE_OAUTH_TOKEN` is `env = "exec"` — it overrides `/login` in every new
session and silently rebills to the old org, and it does NOT authenticate the
Anthropic SDKs; see PR #811. Every terminal and every child process — Claude
Code, its subagents, any MCP server they spawn — inherits them. The stated
requirement is *"in sync and available to all terminals and ai/llm agents"*.

So nothing confines a credential to a process, and rules 1, 4 and 7 below are
the only line between every credential and a transcript or a commit: an
environment dump is unscannable and must never be committed (rule 1, gated by
`no_env_dump`), a probe must never print a value (rule 7, **partly** gated by
`secret_value_substitution`), a non-secret must not be marked secret (rule 3),
and a clean scanner means "ask what it can see" (rule 4).

⚠️ **A keychain credential can hang a background process forever — and that hang
is NOT a locked keychain.** `security show-keychain-info` **prompts
unconditionally**, so its hang proves nothing; fnox reading a keychain secret
in 0.03s is the arm that rules a lock out. What blocks is an *authorization*
dialog for an item a non-GUI process may not read — nothing can answer it. The
discriminating arm is the same command with an isolated config dir.

The `gh:github.com` and `doppler-cli` keychain entries are present (recreated
after a 2026-08-02 deletion; `security find-generic-password -s` rc=0, bogus
name rc=44, re-measured 2026-09-24), so **the hang risk is live**: never wire a
mise `credential_command` to `gh auth token` or `fnox get` (fnox is
Doppler-primary for these names and shells out to the `doppler` CLI).
Deleting the entries is an OPERATOR action that needs its own triage — find
what recreates them first. Evidence:
`docs/research/kb/reports/agents/2026-09-12-gh-token-for-mise.md` §Q5.

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
2. **No process-level confinement.** Secrets live in the shell by decision, so
   `fnox exec` is not a confinement boundary — the parent shell already has
   everything. Rules 1, 4 and 7 have no second line behind them.
3. **Do not mark a non-secret as a secret.** Redaction is value-based, so a
   short or empty "secret" corrupts every log the tool writes.
4. **When a scanner reports clean, ask what it can see.** Compression, encoding,
   and a path allowlist each turn "no findings" into "never looked".
5. **Adding a secret is a reviewed decision.** A secret added to fnox reaches
   every terminal and every agent by default, so add it to `doctor.toml`'s
   `env_true` set in the same reviewed diff, or the doctor reports drift next
   session and someone "fixes" it back. For anything exec-only or absent,
   **check a consumer's authenticated identity, never its connection status**:
   an empty `${VAR}` silently drops a consumer to an anonymous tier (context7
   MCP, 2026-07-29).
6. **Diagnose by layer, and never run `fnox get` to do it** (it prints a value).
   An absent variable is a REAL failure for every name except the carve-out
   above — never dismiss it. Suspects, in order: (a) a **hung `doppler` CLI**,
   since fnox shells out to it and any uncached doppler-primary secret resolves
   through that child; (b) a stale **`MISE_ENV_CACHE`** entry, which can serve a
   dead name in ONE directory long after the config is byte-identically restored,
   and which `grep` cannot see because it is encrypted; (c) the declaration itself.
   The recipes live in `docs/secrets-doppler-fnox-keychain.md`.
7. **⚠️ A probe's OWN STDOUT is an uncovered surface — print presence, never a
   value.** Every gate above guards a *file write* or a *spawn*; none guards the
   output of a command an agent runs, and that output lands in the session
   transcript. Measured 2026-08-02: a `${(P)k}` expansion meant as a presence flag
   printed four live credential values, and all four had to be rotated. They were
   the four `env = true` opt-ins. Use `${VAR:+SET}`, `[ -n "$VAR" ]` or
   `printenv VAR >/dev/null` and read the rc; never interpolate the value into a
   format string "just to check". Gap tracked in #474, still OPEN: one shape is
   now gated (below), every other shape is carried by this rule alone.

   ⚠️ **The safe form is only safe ALONE.**
   `${VAR:+SET}${VAR:-ABSENT}` opens with the form this rule recommends and is a
   **leak**: `:-` and `:=` are *value-emitting* substitutions, so a **set**
   variable prints `SET<the secret>` (an *unset* one prints `ABSENT`, which is why
   it survives review and why an unset-only control arm certifies nothing — arm it
   on a variable that IS set). Want both branches? `[ -n "$VAR" ] && echo SET ||
   echo ABSENT`. **Now machine-enforced** — `hook_guard`'s
   `secret_value_substitution` denies any `echo`/`printf`/`print` of a
   credential-named variable (broader than just `:-`/`:=`, `\$\{?` optional) —
   still allows `${(P)k}` indirect expansion; this rule carries every other shape.

   ⚠️ **There is no blast-radius cap.** Every credential is printable by any
   probe, wrapped or not; `DOPPLER_TOKEN` is itself in the sanctioned shell
   set. Assume every credential is reachable from any shell.
   `docs/rules-evidence/secrets-out-of-the-shell-env.md`.

8. **⚠️ A FILE can be the credential, and "it's config" is not evidence.** Rule 7
   guards a *variable*; on 2026-09-13 the leak came through a **file**, so nothing
   could have fired. `~/.agentsview/config.toml` was described as holding feature
   flags, and a `cat` of it put an `auth_token` and a `cursor_secret` in the
   transcript. **The description was the whole error** — an unknown dotfile in a
   tool's own directory is a credential store until proven otherwise, and the tool
   most likely to hold one is the tool you have not read the source of.

   **Never open an unfamiliar dotfile to find out what it is.** Ask a question
   whose answer is not the content: `ls -la ~/.<tool>/` for sizes and names, the
   tool's `--help` or docs for its config schema. If you truly need to confirm a
   key is present, `grep -c '<key>' <file>` returns a COUNT; `grep '<key>'` returns
   the line, which is the secret.

   **Machine-enforced since 2026-09-13**, in `permissions.deny` rather than
   `hook_guard`, because a hard ban must not fail open (#343) — 24 rules, two
   halves that fail differently:

   - **`Read(~/…)` — load-bearing.** Path-normalised and tool-level, so it holds
     however the path is spelled. Only `Read()`/`Edit()` path rules are consulted
     by the file tools; a `Write()`/`Glob()` path rule is accepted and **never
     checked** (`$CC/permissions.md:316`).
   - **`Bash(*<path fragment>*)` — best-effort.** Anchored on the PATH, not on a
     reader name, so `sed`, `python -c open()` and `cp` are covered as well as
     `cat` — a reader allowlist is walked around by the next spelling. Still string
     matching, so still evadable; treat it as a second line, never the first.

   Both arms were verified live, on an **absent** covered path so a failed rule
   could not leak: `cat ~/.netrc` → *denied* (not "No such file"), `Read` of
   `~/.aws/credentials` → *denied*, while a normal `cat` of a repo file still
   worked. Project-scoped by decision, so it binds sessions in this repo only.

## See also

- `probes-need-a-control-arm.md` — every measurement above ran both arms.
- `use-tool-builtins.md` — the gate that made this research-first; the fix was
  a tool feature, and the custom code is only what no tool can do.
- Memory `feedback_no_user_level_file_updates` — why the fnox change is
  written up rather than applied.
- `python/src/dotfiles_setup/env_blob_scan.py` — the scanner and its evidence.
