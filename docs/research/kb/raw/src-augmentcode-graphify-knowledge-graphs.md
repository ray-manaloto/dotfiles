Graphify hits 58.3K stars: knowledge graphs for AI coding assistants | Augment Code
 Skip to content
 Product
 Solutions
 Context Engine Pricing Docs Blog Resources

 Sign in Book demo

 Product Cosmos CLI Changelog

 Solutions Code Review Review every PR with agents Test Coverage Coverage that climbs, suites that stay green Incident Management Investigate alerts before humans arrive Ticket to PR Assign a ticket, merge a reviewed PR Large Projects From design doc to shipped feature Automations Recurring work as repeatable workflows Security Remediation From CVE alert to a reviewed fix Migrations Modernization as a program, not a project Onboarding Ramp every engineer in days Team Standards at Scale Your best workflow, everyone's default

 Context Engine Pricing Docs Blog Resources Workflows Podcast Customers Status Page Trust Center Security

 Talk to Sales Sign in

 Book demo

 Back to Learn Graphify hits 58.3K stars: knowledge graphs for AI coding assistants
 Jun 2, 2026 Last updated: Jun 18, 2026 •

 Paula Hingel

 Three things worth knowing
 Graphify is an open-source, YC-backed tool that converts entire projects into queryable knowledge graphs, now at 58.3K stars and 6.1K forks.
 It works across 20 AI coding assistant platforms, parses 33 programming languages locally via tree-sitter with zero API calls, and stores results as three files your whole team can query.
 If your AI assistant keeps giving shallow answers about how your codebase fits together, this is the structured context layer I'd evaluate first.

 Ask any AI coding assistant how the login form connects to the users table in a large codebase. Nine times out of ten, it greps through files, misses relationships that aren't obvious from file contents, and gives you a partial answer.
 The problem is structural. AI coding assistants operate on flat-file context. They read files, sometimes many at once, but they have no map of how concepts relate across your codebase. Functions, classes, database tables, API handlers, architecture docs: all of that is context the model has to reconstruct from scratch on every query.
 Graphify pre-computes that map. The YC S26-backed tool converts code, docs, PDFs, images, and videos into a queryable knowledge graph and works across 20 AI assistant platforms. At 58.3K stars, 6.1K forks, and 1.2M PyPI downloads, it's the most widely adopted solution to this problem I've seen in the open-source space.

 What Happened
 Developer Safi Shamsi released Graphify v0.8.28 as the latest in a rapid series of 123 releases. The project has 71 contributors and releases roughly every other day. It installs as a Python package ( graphifyy on PyPI, double-y) and registers itself as a skill in your AI coding assistant.
 Type /graphify . and it maps your project into a knowledge graph stored as three files: an interactive HTML visualization, a markdown report, and a JSON graph you can query at any time. The graph persists in graphify-out/ and can be committed to your repo, so every teammate's assistant has immediate access.
 The release cadence tells me this is a project with real production usage. Roughly every other day for 123 releases means the team is finding and fixing real issues, not shipping features into a vacuum.
 Key Features
 Feature Description
 One-command setup graphify install registers the skill with your assistant. /graphify . builds the graph. Three output files land in graphify-out/.
 33-language AST extraction Python, TypeScript, Go, Rust, Java, C/C++, and 27 more languages parsed locally via tree-sitter with zero API calls. LLM-powered extraction handles docs, PDFs, and images.
 Queryable graph from the CLI graphify query "what connects auth to the database?" returns answers from the graph without re-reading files. graphify path and graphify explain provide targeted lookups.
 Git-commit auto-rebuild graphify hook install adds post-commit hooks that rebuild the AST graph after each commit, with a merge driver that union-merges graph.json when two developers commit in parallel.
 PR impact analysis graphify prs --triage uses AI to rank your review queue by graph impact. graphify prs --conflicts flags PRs that share graph communities, a proxy for merge-order risk.
 Multiple LLM backends Supports Gemini, Claude, OpenAI, DeepSeek, Ollama (fully local), AWS Bedrock, and Kimi for semantic extraction. Auto-detects which API key is available.

 Why It Matters
 Graphify sits on top of AI coding assistants rather than replacing them. Cursor provides AI-assisted editing inside an IDE. Claude Code gives you an agentic coding assistant in the terminal. Graphify gives each of them a pre-built map of your project.
 The confidence tagging system is the part I find most practically useful. Every relationship gets tagged as EXTRACTED , INFERRED , or AMBIGUOUS , so developers know which connections came from code versus model inference. That's the kind of signal that changes how much you trust the assistant's answers.
 SQL schemas, shell scripts, architecture docs, and video walkthroughs all end up as nodes in the same graph. A single query can trace a path from a database table through an API handler to a frontend component. For teams onboarding new developers or reviewing unfamiliar parts of a codebase, that's a meaningful reduction in the time it takes to understand what a change actually touches.
 Example Use Case
 A team maintains a Python/TypeScript monorepo with a PostgreSQL database, a FastAPI backend, and a Next.js frontend. A new developer joins and needs to understand how user authentication flows from the React login form through the API to the database.
 They run graphify query "what connects the login form to the users table?" in Claude Code. The graph returns the path: LoginForm → /api/auth/login → AuthService.authenticate() → UserRepository.find_by_email() → users table , with confidence tags on each edge. They follow up with graphify export callflow-html to get a Mermaid diagram of the full call flow, viewable in any browser.
 This is the workflow I'd walk through with a team spending hours on onboarding. The map is already built. You just query it.
 Competitive Context
 Cursor ships built-in codebase indexing, but it's optimized for file content retrieval. Graphify captures relationships between entities, not just file contents, and works identically across 20 platforms.

 Open source
 augmentcode/auggie ★ 259

 Star on GitHub

 Manual RAG setups give teams similar query capabilities, but they require custom embedding pipelines, chunking strategies, and retrieval logic. Graphify's AST-based local extraction means that code relationships are parsed without LLM calls, keeping setup fast and costs low.
 The 20-platform support is worth calling out specifically. One developer builds the graph and commits graphify-out/ to the repo. Every teammate's assistant, whether they use Claude Code, Cursor, Gemini CLI, or something else, can query the same graph without any additional setup.
 My Take
 If your team uses AI coding assistants on a codebase larger than a few services, Graphify is worth five minutes of setup time. The 1.2M PyPI downloads tell me plenty of teams have already made that call.
 I'm curious whether the confidence tagging actually changes how developers use the assistant's answers in practice, or whether most developers skip the metadata and just trust the output. Worth testing on a real team.
 [ Free report ]

 The Agentic SDLC
 How teams like Stripe, Ramp, and Uber move from solo coding agents to a coordinated, team-level system.

 Download the guide

 Written by
 Paula Hingel
 Technical Writer
 Paula writes about the patterns that make AI coding agents actually work — spec-driven development, multi-agent orchestration, and the context engineering layer most teams skip. Her guides draw on real build examples and focus on what changes when you move from a single AI assistant to a full agentic codebase.

 Drowning in agent-generated PRs?
 See Cosmos for your team

 Get Started
 Give your codebase the agents it deserves
 Install Augment to get started. Works with codebases of any size, from side projects to enterprise monorepos.
 Install Augment Contact Sales

 PRODUCT
 Cosmos
 CLI
 Pricing

 SOLUTIONS
 Code Review
 Test Coverage
 Incident Management
 Ticket to PR
 Large Projects
 Automations
 Security Remediation
 Migrations
 Onboarding
 Team Standards at Scale

 RESOURCES
 Customers
 Docs
 Blog
 Guides
 Learn
 Tools
 AI Engineering Playbook
 The Agentic SDLC
 State of AI-Native Engineering 2026

 COMPANY
 Careers
 Press Inquiries
 Press Kit
 Contact Sales
 Contact Support
 Changelog
 Privacy & Security
 Trust Center
 Status Page

 LEGAL
 Cookie Policy
 Privacy Policy
 SLA and Support Policy
 Terms of Service

 © 2026 Augment Code. All rights reserved.

 DARK

 LIGHT

 SYSTEM
