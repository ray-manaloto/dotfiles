# Secrets Stay Out of the Shell Environment

A credential that lives in the interactive shell's environment is inherited by
**every** child process — every agent, every CLI, every task — and travels in a
form no secret scanner can read. Keep secrets out of the shell; inject them into
the one process that needs them.

## What happened (2026-07-27)

`fnox activate` exported 49 variables into the login shell. mise records the
whole environment delta in **`__MISE_DIFF`** (zlib-compressed, base64-encoded)
so it can undo it on directory exit, and that variable is inherited by every
child. Decoded, the live blob carried an AWS access key id and secret, several
API tokens, an app password, and a Google client secret.

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

The control arm fires on the plaintext, so the zero is a real negative and not
a blind probe. Both scanners are pattern matchers; compression destroys the
patterns. This is the one gap that justifies custom code here at all
(see [[use-tool-builtins]]) — and the custom code covers only the decode.

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

**This is a user-level file** (`~/.config/mise/config.toml` → fnox), outside
this repo, so it is written up here rather than applied — the standing rule is
to never touch a file outside the project unasked (memory
`feedback_no_user_level_file_updates`).

## The same setting fixes the `[redacted]` digit-masking

mise redacts every occurrence of a redacted variable's **value** in task output.
fnox marks all 49 of its variables redacted, and two of them —
`GEMINI_TELEMETRY_ENABLED` and `GEMINI_TELEMETRY_LOG_PROMPTS` — hold
**one-character, all-digit values**. So mise faithfully masks every digit in
every `mise run` line, which is why a number read from `mise run` output cannot
be trusted (memory `feedback_mise_run_masks_digits`). `LANGSMITH_WORKSPACE_ID`
is worse: an **empty** value.

Those are telemetry flags, not secrets. Moving them out of fnox — or marking
them `redact = false` — restores readable task output. The digit-masking was
never a mise bug; it was collateral from treating a non-secret as a secret.

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
3. **`clean_env()`** (`python/src/dotfiles_setup/child_env.py`) strips
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

## See also

- `probes-need-a-control-arm.md` — every measurement above ran both arms.
- `use-tool-builtins.md` — the gate that made this research-first; the fix was
  a tool feature, and the custom code is only what no tool can do.
- Memory `feedback_no_user_level_file_updates` — why the fnox change is
  written up rather than applied.
- `python/src/dotfiles_setup/env_blob_scan.py` — the scanner and its evidence.
