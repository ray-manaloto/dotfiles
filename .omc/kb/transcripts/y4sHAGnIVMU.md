# Graphify | Turn Any Folder Into a Queryable Knowledge Graph | 86K Github Stars

Source: https://www.youtube.com/watch?v=y4sHAGnIVMU
Type: video transcript (YouTube auto-captions)

What if every file in your project, code, PDFs, diagrams, even whiteboard photos, could be turned into a single queryable knowledge graph?

That's exactly what Graphifi does, and it's got 86,000 stars to prove it.

Andreesen Carpathy described the raw folder problem, a dump of papers, tweets, screenshots, and code with zero structure.

LLMs can't efficiently process all of it.

Context windows are limited, and token costs add up incredibly fast.

Graphifi solves this by building a knowledge graph from any folder.

It achieves 71.5 times fewer tokens per query compared to reading raw files, and costs zero LLM credits for code extraction using deterministic tree-sitter parsing.

Graphifi is open source under the MIT license, built entirely in Python, with over 86,000 GitHub stars and 8,500 forks.

It was created by Graphifi Labs and is actively maintained by a dedicated team of contributors.

The project was born from a real need, making heterogeneous file collections navigable by AI agents.

It's not just another code analyzer.

It's a full multimodal knowledge graph builder designed for the age of AI-assisted development.

The pipeline is elegant.

Graphifi detects files in your directory, extracts concepts using tree-sitter for code and Claude for documents, builds a network exgraph, clusters with the latent algorithm, analyzes for key nodes, and exports to multiple formats.

Installation takes one line.

Pip install Graphifi, then run Graphifi install to set up the slash command for your AI coding assistant.

It works with Claude Code, Cursor, CodeDex, and many more.

To build a knowledge graph, just point Graphifi at any folder.

It scans every file, code, docs, images, PDFs, and produces a structured graph with nodes, edges, and community clusters.

Under the hood, tree-sitter parses code into abstract syntax trees for over 40 languages.

It extracts functions, classes, imports, and call graph edges.

This is fully deterministic and costs nothing in LLM credits.

For unstructured content like PDFs, images, diagrams, and whiteboard photos, Graphify uses Claude's vision capabilities to extract concepts and relationships.

Everything merges into one unified knowledge graph.

Graphify supports over 40 programming languages through tree-sitter grammars.

Python, TypeScript, Go, Rust, Java, C++, Ruby, Kotlin, Swift, C#, PHP, Lua, one tool for your entire polyglot code base.

Every edge in the graph carries a confidence label.

Extracted for direct code references, inferred for likely relationships, and ambiguous for uncertain connections.

You always know what was found versus what was guessed.

The latent algorithm automatically detects communities, clusters of tightly connected concepts, and god node analysis identifies the highest degree concepts that everything flows through in your code base.

Query your graph with natural language.

Ask what connects two concepts, find the shortest path between any two nodes, or get a detailed explanation of any concept in your code base.

Three powerful query modes.

Here's querying in action.

Ask a natural language question about your code base, and Graphify returns precise answers grounded in the actual graph structure, not hallucinated summaries.

Graphify also ingests URLs directly.

Archive papers, tweets, documentation pages.

Just run Graphify add with a URL, and it fetches, extracts concepts, and merges the content into your existing graph.

Incremental updates are built in.

Run Graphify with the update flag, and it uses reprocess changed files.

No need to rebuild the entire graph every time you make a small commit.

Export your graph to interactive HTML visualization.

Open it as an Obsidian vault.

Generate Wikipedia-style wiki articles for agent navigation, or export to GraphML for Gephi and yEd.

The graph lives wherever you need it.

Watch mode keeps your graph live.

As files change, Graphify auto syncs.

Code changes trigger instant AST rebuilds.

Install the Git hook, and your graph updates automatically on every single commit.

The MCP server mode exposes Graphify as a tool for any MCP compatible agent.

Run it with the MCP flag and your AI assistant gets direct access to query, path, and explain operations on your code base graph.

On the Loco Moco benchmark for conversational memory, Graphify achieves 45.3% QA accuracy with a recall at 10 of nearly 0.5.

That beats Mem Zero by almost 10 times on recall at a fraction of the cost.

Compared to Super Memory, Graphify achieves similar QA accuracy but at 11 times lower ingest cost.

It also matches dense RAG on the Long Mem Eval benchmark at 76% accuracy with zero LLM cost for code.

The token compression is remarkable.

A 52-file mixed corpus of code, papers, and images requires 71.5 times fewer tokens per query.

That's the difference between fitting in a context window and completely running out.

On a real-world test with ERPNext, a million-line code base, adding Graphify as a tool improved a coding agent's key fact coverage from 70.8% to 82%.

That's a measurable, significant productivity boost.

Graphify works as a slash command in all major AI coding tools: Claude Code, Cursor, Codex, Gemini CLI, Open Code, Aider, Windsurf, Cline.

It integrates directly into your existing workflow without any configuration changes.

Beyond code, Graphify handles SQL schemas, video transcription through Faster Whisper, docx and xlsx office documents, and even PostgreSQL database introspection.

It truly is a universal knowledge graph builder.

Graphify supports multiple LLM backends beyond Claude.

You can use OpenAI, Gemini, llama for local models, AWS Bedrock, and Kimmy.

Pick the provider that fits your setup and budget.

The output structure is clean and organized.

You get an interactive HTML visualization, an Obsidian vault, wiki articles, a persistent graph JSON file, and a SHA-256 change cache, all in one output directory. "Surprising Connections" is one of the most powerful features.

Graphifi ranks cross-domain edges, links between code and papers, between different modules, between documentation and implementation, revealing hidden relationships.

The token benchmark is printed after every single run.

You see exactly how many tokens you saved by querying the graph instead of reading raw files.

For large codebases, the savings are enormous.

Graph construction costs are essentially zero for code.

Tree-sitter is deterministic, no LLM calls needed.

LLMs are only used for unstructured content like PDFs and images, keeping your costs minimal.

Graphifi can export to Neo4j using Cypher queries, Falkor DB, and even generate SVG visualizations with Matplotlib.

For teams that already use graph databases, the integration is seamless and direct.

The wiki generation feature creates Wikipedia-style articles organized by community cluster.

This gives AI agents a structured way to navigate your codebase, reading articles instead of raw files.

Graphifi demonstrated temporal graph capabilities on 15 years of ERPNext development history, 689 weekly AST checkpoints, showing how the knowledge graph grows and retrieval scales over time.

The graph visualization is fully interactive.

Click any node to see its connections, search for specific concepts, filter by community cluster, and explore the structure of your codebase visually.

For Obsidian users, Graphifi exports directly as a vault.

Open it in Obsidian and navigate your codebase as a knowledge graph with backlinks, tags, and community-based folders.

Graphifi handles both shallow and deep extraction modes.

Shallow mode uses only direct references.

Deep mode adds inferred relationships for a more complete but noisier graph.

You can also add individual files or URLs to an existing graph without rebuilding everything.

This makes it easy to incrementally expand your knowledge graph as your project evolves.

The generated graph report gives you a complete overview.

It lists the top god nodes, community summaries, surprising cross-domain connections, and suggested questions to explore the graph.

Graphify is completely local and private.

No data leaves your machine unless you explicitly choose an LLM provider.

The default code extraction is fully deterministic with zero network calls.

The project is under active development with over 8,500 forks and a growing ecosystem of integrations.

New language grammars, export formats, and agent integrations are added regularly.

The token benchmark printed after every run is not just a nice number.

It's a real measure of how much money and context you're saving by using a structured graph instead of raw file reading.

Let's recap the key numbers. 86,000 GitHub stars, 71 times token reduction, zero cost code extraction, over 40 languages, 11 times cheaper than super memory, works with every major AI coding agent.

Graphify is the missing link between your files and your AI assistant.

Zero cost graph construction, multimodal extraction, massive token reduction, and it works everywhere you code.

Star the repo on GitHub, try it on your own project, and subscribe for more deep dives into the best open-source AI tools.

Link in the description.
