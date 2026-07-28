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

   **Common trap:** do NOT guess a project's docs domain
   (`containers.dev/llms.txt` → 404; the devcontainer docs are on
   mintlify). Grep the cache or the catalog for the right URL first.

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

3. **`ctx7`** — for libraries whose docs live outside mintlify, or where
   `llms.txt`/`.md` doesn't cover what you need. It is a **direct
   doc-fetcher**; call it straight, in two steps:

   ```bash
   ctx7 library <name> [query]        # resolve a name -> Context7 library ID
   ctx7 docs <libraryId> <query>      # fetch the docs
   ```

   Do not build on the deprecated `skills` subcommands — and do not
   treat their absence from `--help` as proof they are gone (they still
   run). `.claude/skills/context7-cli/SKILL.md` is the setup reference.

4. **Raw HTML fetch** (`curl <url>` or `npx @teng-lin/agent-fetch <url>`) —
   **last resort only.** Pays the full HTML-parse cost in agent
   context. Use `defuddle` where available to clean HTML before
   parsing.

## Never `mcp2cli` a per-repo mintlify MCP URL

`mcp2cli https://mintlify.com/<owner>/<repo>/mcp <tool>` was once step 2
of this chain. **It does not work.** Those URLs are GET-only *preview
descriptors*: a `curl GET` returns a plausible JSON tool-schema, while
the POST `mcp2cli` sends returns `404`. There is no server behind them,
and an API key does not unlock one (Mintlify keys are org-scoped).

The ban is specific to per-repo mintlify subpath URLs. `mcp2cli` stays
in active use for real MCP servers (`@github`, `@docker`, or a
customer-domain MCP like `docs.anthropic.com/mcp`) — see
`.claude/skills/mcp2cli/SKILL.md`. Four probes, incl. the central-MCP
scope limit: `docs/rules-evidence/research-doc-sources.md`.

## `mcp2cli`-first — a preference, not a gate

**Prefer `mcp2cli` (process-spawn) or the curl steps above** for one-off
lookups: native registration injects every tool's JSON schema into the system
prompt for **every** conversation, forever, including ones that never call it.

**Native registration is NOT forbidden** (relaxed 2026-07-19; the
`no_mcp_registration` hk step is gone). When a plugin or tool *requires* MCP,
register it knowingly. Judgement call: rare queries → `mcp2cli` wins on cost;
a plugin whose value depends on native tool selection → register it. When
unsure, reach for `mcp2cli` first.

## See also

- `.claude/skills/mcp2cli/SKILL.md` — process-spawn MCP invocation.
- `.claude/skills/mintlify/SKILL.md` — mintlify URL surface.
- `.claude/rules/research-repo-enumeration.md` — sibling rule for
  recording which repos a research artifact touched.
- `.claude/rules/use-tool-builtins.md` — parent principle (prefer tool
  built-ins over homegrown logic); this rule is an instance of that
  principle for doc fetching.
- `feedback_no_mcp_registration.md` — auto-memory rule with rationale.
