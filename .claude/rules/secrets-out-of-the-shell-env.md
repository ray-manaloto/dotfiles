# Secrets Stay Out of the Shell Environment

A credential that lives in the interactive shell's environment is inherited by
**every** child process — every agent, every CLI, every task — and travels in a
form no secret scanner can read. Keep secrets out of the shell; inject them into
the one process that needs them.

## What happened, and why no scanner caught it

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

**APPLIED 2026-07-27 by Ray** — 46 of 49 exec-only, 3 opted back in. Two
variables must stay `env = true` because this repo runs on them: `.mcp.json`
interpolates one at MCP-server spawn, and `gh` (every `ship`/`land`/`automerge`
and `gh api` call) reports its active account as the environment-authenticated
one. Exec-only for those degrades tooling *silently*.

⚠️ **The config is GENERATED** — *"Managed by `mde-py secrets bootstrap-config`.
Do not edit by hand."* A hand edit survives only until the next bootstrap, so the
durable fix belongs in `mde-py`'s generator. There is no user-root local override
to hide it in; that layer is project-scoped only.

This also fixed the `[redacted]` digit-masking: two fnox telemetry flags held
one-character all-digit values and were marked redacted, so mise masked every
digit in every `mise run` line. Never a mise bug — collateral from treating a
non-secret as a secret. **It returns if `mde-py` re-bootstraps the config.**

Findings, control arms, and the verification that passed while blind:
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
2. **A secret belongs to a process, not to a shell.** Reach for `fnox exec --`
   (or the tool's own credential flow) rather than exporting.
3. **Do not mark a non-secret as a secret.** Redaction is value-based, so a
   short or empty "secret" corrupts every log the tool writes.
4. **When a scanner reports clean, ask what it can see.** Compression, encoding,
   and a path allowlist each turn "no findings" into "never looked".
5. **A new env-var consumer is a new `env = true` decision.** With `env = "exec"`,
   a config that interpolates `${VAR}` gets an **empty string**, not an error — the
   tool starts, reports healthy, and silently drops to an anonymous tier (context7
   MCP did exactly this, 2026-07-29). Check the consumer's authenticated
   *identity*, never its connection status.
6. **Diagnose by layer, and never run `fnox get` to do it.** A `-v` presence test
   under `fnox exec` (present) vs the same in a plain shell (absent) identifies
   `env = "exec"` on its own; `fnox sync --dry-run -p age VAR` answers staleness
   without reading a value. Full ordered recipe, the result-reading table, and the
   ⚠️ `bootstrap-config` **wipe hazard** (it drops `env = "exec"`, all 3 opt-ins,
   and 49 `sync` blocks): `docs/secrets-doppler-fnox-keychain.md`.

## See also

- `probes-need-a-control-arm.md` — every measurement above ran both arms.
- `use-tool-builtins.md` — the gate that made this research-first; the fix was
  a tool feature, and the custom code is only what no tool can do.
- Memory `feedback_no_user_level_file_updates` — why the fnox change is
  written up rather than applied.
- `python/src/dotfiles_setup/env_blob_scan.py` — the scanner and its evidence.
