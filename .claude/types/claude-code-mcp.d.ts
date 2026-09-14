// The inputs of the MCP tools this session had, from each server's tools/list
// inputSchema; written by `/plugin-types` (src/plugins/functionHooks/mcp-tool-types/mcp-tool-declarations.ts).
// Merges into the engine's ToolCallInput (types/ McpToolInputs) so
// `e.tool === "mcp__<server>__<tool>"` narrows to the tool's arguments.
// Regenerate rather than edit.
export {}
declare module 'claude-code' {
  interface McpToolInputs {
    /** Retrieves and queries up-to-date documentation and code examples from Context7 for any programming library or framework. You must call 'Resolve Context7 Library ID' tool first to obtain the exact Context7-compatible library ID required to use this tool, UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query. Do not call this tool more than 3 times per question. */
    "mcp__plugin_context7_context7__query-docs": {
      /** Exact Context7-compatible library ID (e.g., '/mongodb/docs', '/vercel/next.js', '/supabase/supabase', '/vercel/next.js/v14.3.0-canary.87') retrieved from 'resolve-library-id' or directly from user query in the format '/org/project' or '/org/project/version'. */
      libraryId: string
      /** What to look up in the library's documentation, scoped to a single concept. Be specific and include relevant details, but keep each query to one topic — if the user's question spans multiple distinct concepts, make a separate call per concept instead of combining them, unless the question is about how the concepts interact. Good: 'How to set up authentication with JWT in Express.js' or 'React useEffect cleanup function examples'. Bad (too vague): 'auth' or 'hooks'. Bad (too broad): 'routing and auth and caching in Next.js'. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query. */
      query: string
    }
    /** Resolves a package/product name to a Context7-compatible library ID and returns matching libraries. You MUST call this function before 'Query Documentation' tool to obtain a valid Context7-compatible library ID UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query. Each result includes: - Library ID: Context7-compatible identifier (format: /org/project) - Name: Library or package name - Description: Short summary - Code Snippets: Number of available code examples - Source Reputation: Authority indicator (High, Medium, Low, or Unknown) - Benchmark Score: Quality indicator (100 is the highest score) - Versions: List of versions if available. Use one of those versions if the user provides a version in their query. The format of the version is /org/project/version. For best results, select libraries based on name match, source reputation, snippet coverage, benchmark score, and relevance to your use case. Selection Process: 1. Analyze the query to understand what library/package the user is looking for 2. Return the most relevant match based on: - Name similarity to the query (exact matches prioritized) - Description relevance to the query's intent - Documentation coverage (prioritize libraries with higher Code Snippet counts) - Source reputation (consider libraries with High or Medium reputation more authoritative) - Benchmark Score: Quality indicator (100 is the highest score) Response Format: - Return the selected library ID in a clearly marked section - Provide a brief explanation for why this library was chosen - If multiple good matches exist, acknowledge this but proceed with the most relevant one - If no good matches exist, clearly state this and suggest query refinements For ambiguous queries, request clarification before proceeding with a best-guess match. IMPORTANT: Do not call this tool more than 3 times per question. If you cannot find what you need after 3 calls, use the best result you have. */
    "mcp__plugin_context7_context7__resolve-library-id": {
      /** What to look up in the library's documentation. This is used to rank library results by relevance to what the user is trying to accomplish. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query. */
      query: string
      /** Library name to search for and retrieve a Context7-compatible library ID. Use the official library name with proper punctuation — e.g., 'Next.js' instead of 'nextjs', 'Customer.io' instead of 'customerio', 'Three.js' instead of 'threejs'. */
      libraryName: string
    }
    /** Read a webpage's full content as clean markdown. Use after web_search_exa when highlights are insufficient or to read any URL. Best for: Extracting full content from known URLs. Batch multiple URLs in one call. Returns: Clean text content and metadata from the page(s). */
    mcp__plugin_exa_exa__web_fetch_exa: {
      /** URLs to read. Batch multiple URLs in one call. */
      urls: string[]
      /** Maximum characters to extract per page (default: 3000) */
      maxCharacters?: number
    }
    /** Search the web for any topic and get clean, ready-to-use content. Best for: Finding current information, news, facts, people, companies, or answering questions about any topic. Returns: Clean text content from top search results. Query tips: describe the ideal page, not keywords. "blog post comparing React and Vue performance" not "React vs Vue". Use category:people / category:company to search through Linkedin profiles / companies respectively. If highlights are insufficient, follow up with web_fetch_exa on the best URLs. */
    mcp__plugin_exa_exa__web_search_exa: {
      /** Natural language search query. Should be a semantically rich description of the ideal page, not just keywords. Optionally include category:<type> (company, people) to focus results — e.g. 'category:people John Doe software engineer'. */
      query: string
      /** Number of search results to return (default: 10). */
      numResults?: number
      /** Goal for this search turn; say which documents should rank first, which should be excluded, and what specific facts or figures to pull from them. */
      objective: string
    }
  }
}
