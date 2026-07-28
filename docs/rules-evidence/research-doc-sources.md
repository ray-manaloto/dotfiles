# Evidence — `research-doc-sources`

Probe logs and corrections behind `.claude/rules/research-doc-sources.md`.
Extracted from the rule so the eager copy carries the preference chain itself and
this file carries the evidence for why each step is where it is — and why one
step was deleted outright.

## Why `mcp2cli` against per-repo mintlify MCPs is NOT in the chain

An earlier revision listed `mcp2cli https://mintlify.com/<owner>/<repo>/mcp
<tool>` as a fuzzy-search step. **That step does not work** and was removed.

Probe evidence (full log: `docs/research/mintlify-catalog-validation-log.md`):

- **The URLs are GET-only preview descriptors**, auto-generated for every repo
  Mintlify indexes. `curl GET` returns a JSON tool-schema descriptor; **POST** —
  which `mcp2cli` sends to speak MCP protocol — returns `404 Not found`. There is
  no live MCP server behind the descriptor. The descriptor's existence is exactly
  the trap: it *looks* like a live endpoint to a GET-shaped probe.
- **Live mintlify MCP servers exist only at the customer's own documentation
  domain** (e.g. `docs.anthropic.com/mcp`, `resend.com/docs/mcp`,
  `docs.perplexity.ai/mcp`). None of the 16 repos then in
  `docs/research/mintlify-catalog.md` host one anywhere — verified against their
  own domains (`chezmoi.io/mcp`, `starship.rs/mcp`, `mise.jdx.dev/mcp`), all of
  which return plain nginx 405/404, not MCP protocol.
- **Mintlify's central MCP** at `https://mintlify.com/docs/mcp` works, but is
  scope-limited to Mintlify's *own* platform docs (how to build a mintlify site,
  MDX syntax, agent workflows). It does not search the per-repo customer sites in
  the catalog — verified with a real query: `search-mintlify --query "mise
  shell_alias"` returned zero results from `jdx/mise`.
- **An API key does not unlock this path.** Mintlify API keys are
  organization-scoped: they authenticate you only against docs owned by the same
  Mintlify organization as the key. A key cannot reach `jdx/mise`,
  `twpayne/chezmoi`, or any other org's content.

`mcp2cli` itself remains in active use for **other** MCP servers (`@github`,
`@docker` shorthands, or a customer-domain MCP such as `docs.anthropic.com/mcp`).
The ban is specifically on per-repo mintlify subpath URLs, not on `mcp2cli`.

## The `ctx7` correction (2026-07-23)

Step 3 of the chain used to say `ctx7` was "a skill-management CLI … **not** a
direct doc-fetcher", which routed every lookup through a skill wrapper that adds
nothing.

Verified against `ctx7 --help` (0.5.5, the `mise.toml` pin): the documented
commands are `login / logout / whoami / setup / remove / library / docs /
upgrade`. It **is** a direct doc-fetcher, called in two steps.

The subtlety worth keeping: the `skills` subcommands **still run**
(`ctx7 skills list` → rc=0) but are hidden from `--help` and deprecated —
*"Skill commands are deprecated and will stop working in the next major
release."* So do not build on them, **and do not treat their absence from
`--help` as proof they are gone.** A command missing from help output is not a
command that does not exist; that is a display bound, in the sense of
`probes-need-a-control-arm.md` rule 3.

## The docs-domain guessing trap (session 2026-04-09c)

Do **not** guess a project's docs domain. `containers.dev/llms.txt` → 404. The
devcontainer spec / CLI / features / images docs are all hosted on mintlify at
`www.mintlify.com/devcontainers/<repo>/`, not on `containers.dev`. Grep the
cache or the catalog to find the right URL before curling anything.

## The MCP-registration relaxation (2026-07-19)

The rule used to carry a hard ban, machine-enforced by a `no_mcp_registration`
hk step. That step has been **removed**; native registration is now a documented
*preference*, not a gate.

The cost that still justifies the preference: registering an MCP server natively
injects every tool's JSON schema into Claude's system prompt for **every**
conversation, forever — even conversations that never call the tool. So for a
server you would query rarely, `mcp2cli`'s process-spawn is strictly cheaper. If
a plugin's value depends on Claude selecting its tools natively and you will use
it often, register it and accept the schema cost.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `docs/research/mintlify-catalog.md`, the validation log.

_Named in the extracted text but **not** resolved during this extraction (carried
over from the rule, not re-probed): `jdx/mise`, `twpayne/chezmoi`, and the
mintlify / Context7 endpoints above. The probe results are dated; re-run them
before relying on a negative._
