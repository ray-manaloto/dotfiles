# Research Doc Sources: Preference Chain

When an agent or skill needs to fetch library/framework/tool documentation
during research, it MUST walk this preference chain top-to-bottom and use
the first option that returns the answer. Lower steps cost more tokens
(per-query or per-conversation) — never skip a step that would have
worked.

## The chain

0. **Grep the local cache first.** Every repo in
   `docs/research/mintlify-catalog.md` has both `llms.txt` and
   `llms-full.txt` pre-fetched under
   `docs/research/mintlify-cache/<owner>/<repo>/`. Zero latency,
   zero round-trips, greppable across the whole cache with
   `grep -rHi <topic> docs/research/mintlify-cache/`. Before running
   any `curl` against a docs domain, check whether the repo is in the
   catalog — if yes, the cache is the authoritative source and `curl`
   is only needed for per-page `.md` fetches or cache refresh.

   **Common trap (session 2026-04-09c):** do NOT guess a project's
   docs domain (e.g., `containers.dev/llms.txt` → 404). The
   devcontainer spec/CLI/features/images docs are all hosted on
   mintlify at `www.mintlify.com/devcontainers/<repo>/`, not on
   `containers.dev`. Grep the cache or the catalog to find the
   right URL before curling anything.

1. **`curl <site>/llms.txt`** — AI-optimized plain-text index, one entry
   per page. Cheapest possible *remote* lookup. Works for every repo in
   `docs/research/mintlify-catalog.md` and for many non-mintlify sites
   that publish an llms.txt (check the target site). Use `grep` on
   the output to pick the page(s) you want. Use this when step 0 is a
   cache miss or when the topic needs fresh content.

2. **`curl <site>/<path>.md`** — for mintlify-hosted sites, appending
   `.md` to any visible page URL returns clean markdown (no HTML
   chrome, no JS). Use this once step 1 has told you which page you
   want. This is the primary per-page fetch for mintlify content.

3. **`ctx7` / `/context7-cli` skill** — for libraries whose docs live
   outside mintlify, or for libraries where `llms.txt`/`.md` doesn't
   cover what you need. Invoked via the `/context7-cli` skill. Note:
   the `ctx7` binary itself is a skill-management CLI
   (subcommands `skills`/`login`/`whoami`/`setup`), not a direct
   doc-fetcher — the actual doc retrieval happens through the skill
   wrapper. See `.claude/skills/context7-cli/SKILL.md`.

4. **Raw HTML fetch** (`curl <url>` or `npx @teng-lin/agent-fetch <url>`) —
   **last resort only.** Pays the full HTML-parse cost in agent
   context. Use `defuddle` where available to clean HTML before
   parsing.

## Why `mcp2cli` against per-repo mintlify MCPs is NOT in the chain

An earlier revision of this rule listed
`mcp2cli https://mintlify.com/<owner>/<repo>/mcp <tool>` as a
fuzzy-search step. **That step does not work** and has been removed.

Summary of the probe evidence (full log:
`docs/research/mintlify-catalog-validation-log.md`):

- The `https://mintlify.com/<owner>/<repo>/mcp` URLs are **GET-only
  preview descriptors** auto-generated for every repo Mintlify
  indexes. `curl GET` returns a JSON tool-schema descriptor; POST
  (which `mcp2cli` sends to speak MCP protocol) returns `404 Not
  found`. There is no live MCP server behind the descriptor.
- **Live mintlify MCP servers exist only at the customer's own
  documentation domain** (e.g., `docs.anthropic.com/mcp`,
  `resend.com/docs/mcp`, `docs.perplexity.ai/mcp`). None of the 16
  repos currently in `docs/research/mintlify-catalog.md` host a
  live MCP server anywhere — verified against their own domains
  (`chezmoi.io/mcp`, `starship.rs/mcp`, `mise.jdx.dev/mcp`, etc.)
  which all return plain nginx 405/404, not MCP protocol.
- **Mintlify's central MCP** at `https://mintlify.com/docs/mcp`
  works but is scope-limited to Mintlify's own platform docs (how
  to build a mintlify site, MDX syntax, agent workflows). It does
  NOT search the per-repo customer sites in our catalog. Verified
  with real queries: `search-mintlify --query "mise shell_alias"`
  returned zero results from `jdx/mise`.
- **An API key does not unlock this path.** Mintlify API keys are
  organization-scoped; they authenticate you only against docs
  owned by the same Mintlify organization as the key. You cannot
  use a key to access `jdx/mise`, `twpayne/chezmoi`, or any other
  org's content.

`mcp2cli` itself remains in active use in this repo for **other**
MCP servers (e.g., `@github`, `@docker` shorthands from
`~/CLAUDE.md`, or a customer-domain MCP like `docs.anthropic.com/mcp`
if we need to research Anthropic docs). See
`.claude/skills/mcp2cli/SKILL.md` for invocation patterns. The ban
is specifically on using it against per-repo mintlify subpath URLs,
not on `mcp2cli` in general.

## The forbidden path: `claude mcp add`

**`claude mcp add` is forbidden in this repo.** Registering an MCP
server via the native Claude Code mechanism injects every tool's JSON
schema into Claude's system prompt for every conversation, forever.
Even conversations that never use the tool pay the context tax.

Use `mcp2cli` (process-spawn, no schema injection) or the curl-based
options in this chain instead. See the memory rule
`feedback_no_mcp_registration.md` and
`.claude/skills/mcp2cli/SKILL.md` for the rationale.

This rule is **machine-enforced** by the `no_mcp_registration` step in
`hk.pkl`. Any commit introducing a `claude mcp add` invocation or a
tracked `.mcp.json` file will be rejected by the local pre-commit hook
(and therefore by CI, which runs the same hk config).

## Exceptions

None by default. If a genuine exception arises (e.g. an MCP server whose
authentication model cannot be reached any other way), it requires:

1. An explicit written justification in
   `feedback_no_mcp_registration.md` (memory rule).
2. User approval.
3. A targeted exclusion in the `no_mcp_registration` hk step with a
   comment pointing at the justification.

Without all three, the default answer is "use `mcp2cli` instead."

## See also

- `.claude/skills/mcp2cli/SKILL.md` — process-spawn MCP invocation.
- `.claude/skills/mintlify/SKILL.md` — mintlify URL surface.
- `.claude/rules/research-repo-enumeration.md` — sibling rule for
  recording which repos a research artifact touched.
- `.claude/rules/use-tool-builtins.md` — parent principle (prefer tool
  built-ins over homegrown logic); this rule is an instance of that
  principle for doc fetching.
- `feedback_no_mcp_registration.md` — auto-memory rule with rationale.
