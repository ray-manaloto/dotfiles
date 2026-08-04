# Secrets-CLI decision artifacts — session 2026-08-03/04

Published Artifact pages, with their sources preserved here. The pages live on
claude.ai; these `.html` files are the sources they were published from. To
update a page from a later session, pass its URL as the Artifact tool's `url`
parameter — otherwise a new URL is minted.

| Artifact | URL | What it holds |
|---|---|---|
| `secrets-cli-proposals.html` | https://claude.ai/code/artifact/d484504f-4d8f-49fe-8765-97deb1138a28 | Five proposals, the measured evidence matrix with per-cell provenance, mise-native capabilities, the four resolution lanes |
| `secrets-cli-architecture.html` | https://claude.ai/code/artifact/94961fff-d5b1-4805-a67d-3740fe2b5e86 | Four-layer target architecture, the five drift seams, CRUD as sequence diagrams |
| `secrets-fnox-entrypoint.html` | https://claude.ai/code/artifact/73dcd549-55c7-4e52-b430-4a5a3fdd5082 | fnox as sole integration point — the three leaks, CRUD flows, the Rust-vs-Python build fork |
| `fnox-doppler-write.html` | https://claude.ai/code/artifact/5df65a33-ac72-4bde-baf5-8ad34631fe50 | Whether Doppler write support exists upstream, the four edits to add it, the cleartext-write defect |
| `shell-activation.html` | https://claude.ai/code/artifact/e569d38b-c5d8-42cb-a6f0-ebeb0be73344 | Five candidates to replace the mde shell fragment, six hazards, mise `[dotfiles]` |

## Known-stale content

`secrets-cli-architecture.html` draws Create/Delete routing the **write**
through fnox. That has never been how this host works — writes go via the
Doppler CLI, and fnox cannot write to Doppler at all. Fix before citing that
diagram.

## Backing agent reports

`../reports/agents/` — `secrets-backend-{infisical,sops-age,bitwarden-sm}.md`,
`fnox-{write-surface,sdk-config,export-exec,shell-activation}.md`,
`mise-shell-activation.md`.
