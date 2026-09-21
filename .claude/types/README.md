# Claude Code function-hook declarations

These declarations are vendored from the Claude Code repository and refreshed
via the schema-vendor machinery, never generated locally. Regenerate both files
from the repository root with:

```console
mise run schema-vendor-refresh
```

That task is the canonical route. It will fetch the upstream declarations at
the pinned version, normalize them through the hk hygiene builtins (to strip
environment-dependent interfaces), and write both `.claude/types/claude-code.d.ts`
and the metadata to `schemas/sources.toml`.

The precise command that runs internally is, in effect:

```console
curl -fsSL 'https://raw.githubusercontent.com/anthropics/claude-code/v<VERSION>/mods/types/claude-code.d.ts' | \
  hk util trailing-whitespace --fix | \
  hk util end-of-file-fixer --fix | \
  hk util mixed-line-ending --fix | \
  hk util fix-smart-quotes > .claude/types/claude-code.d.ts
```

## Why vendoring instead of generation?

The previous flow ran `claude -p '/plugin-types'` locally, which made a Claude
Code binary a hard dependency of `mise run lint`. On CI runners under
MISE_LOCKED=1, the tool cannot install, generation writes nothing, and the gate
fails. The native installer owns the host PATH (currency.toml:29-39), so there
is no backup binary to fall back to.

Vendoring moves the fetching to CI-only (`refresh.yml`'s `schema-refresh` job),
where network is available, and keeps the lint gate fast and portable.

## Declarations content and format

- **claude-code.d.ts**: The main plugin API declarations. This file is
  environment-dependent — `/plugin-types` includes the built-in tools available
  in the generating session. The drift gate therefore normalizes only the bodies
  of `BuiltinToolInputs` and `BuiltinToolResults` before comparison. Every other
  byte of the plugin API remains drift-sensitive.
- **claude-code-mcp.d.ts**: Generated per-session and MCP-server-specific. It is
  NOT compared during drift checks (excluded by `drift_comparable_files()`), since
  it varies entirely by which MCP servers are connected.

The `normalize_claude_code_declarations()` function in `fnhook_gates.py` carries
the normalization logic and a control arm asserting that API mutations are still
detected after stripping the environment-dependent parts.

## Metadata

**Upstream version:** 2.1.278
**Upstream file:** `mods/types/claude-code.d.ts` in the `anthropics/claude-code` repo
**Note:** Upstream's types lag the release, and by more than one version — so the
header inside the vendored file deliberately disagrees with the version above.
Measured 2026-09-15 by fetching both tags: v2.1.272 and v2.1.273 serve a
byte-identical file (405,845 B) whose header still reads "Written by Claude Code
2.1.271". This is not a bug — it is how Anthropic's release cycle works, and it
is why `pin-parity.toml` registers this line but not the `.d.ts` headers.

The lag is not permanent: measured 2026-09-18, the v2.1.277 tag serves a new
file (499,059 B) whose header reads "Written by Claude Code 2.1.277", so at
this pin the header and the version above happen to agree. Do not rely on it.

⚠️ **This line is a PIN, not prose.** `pin-parity.toml`'s `claude-code` entry
reads it and requires it to equal `schemas/sources.toml`'s `version`, so edit
the two together (or let `mise run schema-vendor-refresh` do it).

Do not edit the generated declarations by hand. Run `mise run schema-vendor-refresh`
after a pin bump or if the sha256 check fails.
