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

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  `no_env_dump` gate, `env_blob_scan.py`, and the history pickaxe.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the second public repo checked by the same pickaxe.
