# Research Doc Sources: Preference Chain

When an agent or skill needs to fetch library/framework/tool documentation
during research, it MUST walk this preference chain top-to-bottom and use
the first option that returns the answer. Lower steps cost more tokens
(per-query or per-conversation) — never skip a step that would have
worked.

## The chain

1. **`curl <site>/llms.txt`** — AI-optimized plain-text index, one entry
   per page. Cheapest possible lookup. Works for every mintlify-hosted
   site and many non-mintlify sites. See
   `docs/research/mintlify-catalog.md` for probed coverage.

2. **`curl <site>/<path>.md`** — for mintlify sites, appending `.md` to
   any visible page URL returns clean markdown (no HTML chrome, no JS).
   Use this once step 1 has told you which page you want.

3. **`mcp2cli <per-repo-mcp> search_<repo> --query "..."`** — process-
   spawn call to a per-repo MCP server (mintlify exposes these at
   `https://mintlify.com/<owner>/<repo>/mcp`). **No registration.** See
   `.claude/skills/mcp2cli/SKILL.md` for invocation details.

4. **`mcp2cli https://mintlify.com/docs/mcp search_mintlify --query "..."`** —
   cross-site fuzzy search across all mintlify-hosted sites. Fallback
   when the target repo is not in the catalog.

5. **`context7-cli`** — for libraries not on mintlify. See the
   `context7-cli` skill.

6. **Raw HTML fetch** (`curl <url>` or `npx @teng-lin/agent-fetch <url>`) —
   **last resort only.** Pays the full HTML-parse cost in agent context.

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
