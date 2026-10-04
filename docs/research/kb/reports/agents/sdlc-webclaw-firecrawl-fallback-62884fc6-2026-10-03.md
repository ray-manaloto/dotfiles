RESEARCH INCOMPLETE: `firecrawl-search` still fails with `exited 1: Error: Request failed with status code 402 |`.

Reran strict-five under scoped native `fnox` for request `01a1049b-54e9-7223-821e-66174dde980b`. The command exited **1**.

| Provider group | Verified outcome |
|---|---|
| GitHub | Issues: 1 result; discussions/releases: verified empty query results with positive controls |
| Exa | Successful, 10 results |
| Context7 | Successful, 5 results |
| Firecrawl | Developer index: successful, 10 results; **web search: 402** |
| Last30Days | Successful, 2 results; internal GitHub/grounding statuses both `ok` |

Verified request identity, `strict-five-v1`, all eight source rows, and every raw-file SHA-256 in the [retry manifest](/Users/rmanaloto/.codex/research-coverage/01a1049b-493c-7c70-b7a1-f3db9a9954c2/01a1049b-54e9-7223-821e-66174dde980b-strict-retry/manifest.json). Firecrawl-search’s raw file is empty; its matching hash does not establish coverage. Earlier evidence was preserved.

The recommendation remains: **labelled local webclaw scraping backup, existing Exa for search, and a separate credential decision for Serper-backed search.** A backup must preserve the Firecrawl failure and cannot satisfy strict-five-v1.

## GitHub repos touched

- `0xMassi/webclaw` — read-only research.

All previously spawned specialists completed. No additional agents or others were spawned.

## Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`