---
okf_version: "0.2"
type: "report"
title: "Method: offline sources, binary reading, code maps, live runs"
description: "How the Codex and Claude Code sources were pinned offline, how the Claude binary was read, how the code was mapped, and how claims were confirmed live."
---

# Method: offline sources, binary reading, code maps, live runs

The rule: no claim about a harness without the code at the installed version, and no design that rests on a claim
until a real run shows it. This page is the procedure, so a later version bump can be re-read the same way. It merges
what three sessions did: one read Codex Rust source and checked it against real rollout files; one read JetBrains jars
by SHA-256 with read-only subagents; this one read the Claude binary.

## 1. Get the sources offline, pinned to the installed version

| Harness | Installed | Offline source | Pin |
|---|---|---|---|
| Codex CLI | `codex --version` -> 0.167.0 | partial clone (`--filter=blob:none`) of `openai/codex` | tag `rust-v0.167.0`, commit `086ccc833b`; read with `git show <tag>:<path>` and `git grep <pat> <tag> -- codex-rs`, never by moving the checkout |
| Codex docs | - | a crawl of developers.openai.com/codex (189 pages, for 0.165.0) | a lead only |
| Claude Code | `claude --version` -> 2.1.319 | the binary itself: `~/.local/share/claude/versions/2.1.319` | sha256 `1f53587e…cc2ebd`, 321,995,200 bytes |
| Claude docs | - | code.claude.com pages on cross-session messaging and channels | a lead only |

The public `anthropics/claude-code` repo is not the CLI's source: it holds plugins, examples and the changelog. The
only source of the CLI's behaviour is the shipped binary.

Check the pin every time: a mirror checked out at an older tag (here 0.165.0) silently answers for the wrong version.

## 2. Read the Claude binary (reverse engineering, read only)

The 2.1.319 binary is a Bun single-file executable. Its app is 2,898 ESM chunks of plain minified JavaScript, each
starting `// @bun @bytecode` and `// (c) Anthropic PBC.`, ending at the next NUL byte (file offsets about
259 MB to 313 MB). Lower offsets hold Bun's own runtime; literals also appear in JSC bytecode string tables, which are
not code.

1. A stdlib Python extractor (`python3 -I extract.py <binary> <outdir>`) records the binary's sha256 and size, copies
   every chunk to `cli-2.1.319.bundle.js`, and writes `modules.tsv` (chunk index, offset, length).
2. It splits the bundle into lines with a fixed rule: a newline after every `;`, and after every `}` unless the next
   character continues an expression (`, ; ) ] } . : ? = | & + - * /`) or the next word is `else`, `catch`, `finally`
   or `while`, outside strings, templates, regexes and comments. Nothing is removed or reordered. The result,
   `cli-2.1.319.split.js` (796,513 lines), is what `L<n>` citations point at.
3. Every cited site also carries an anchor: a literal string on or near the line ("drain at the receiver's next tool
   round", `cc-socks`, `var sLn=1048576`). Minified names (`I7`, `_Ss`, `PVt`) change on every build; anchors survive,
   so a citation can be found again in 2.1.320 by grepping the anchor.
4. Search with Python regexes over the split file. ugrep hit its regex complexity limit on the one-line bundle.
5. Never print secret values: the per-session `peerToken` files are named by path only.

The extractor and its MANIFEST (sha256 of every output) live outside this repo, in the run's state folder. Packaging
it under `python/` is an open choice (see the plan).

## 3. Map the code

- Find the entry point by its user-facing string (a tool name, an error text, a flag), then walk callers and callees.
- For Codex use `git grep` at the tag, plus codebase-memory-mcp where it is indexed; cross-check every graph edge with
  grep. In earlier work the graph missed 5 of 11 call sites.
- Write each claim as one table row: claim, `file:line` plus anchor, tag. VERIFIED-SOURCE means the code was read;
  VERIFIED-LIVE means a run log shows it (the log is named); REPORTED means docs or a third party only.
- Name what stays unexplained in its own section. A negative claim ("nothing external can post here") says how it
  was searched, because a method-list check is not proof.

## 4. Confirm with live runs

- Test tabs open only through the test-tab launcher, with a tool allowlist, a cheap model at low effort, and a
  non-git folder; they are closed after the run.
- Drive tabs by typing keys as the user would, then read the real transcripts (`~/.claude/projects/*/<session>.jsonl`,
  `$CODEX_HOME/sessions/**/rollout-*.jsonl`) and the app-server's JSON-RPC log, not the screen.
- Each run folder holds `results.md` (a case table and numbered findings), `playbook.md` (the re-runnable steps) and
  `logs/`. Cases: normal, steer (message while busy), Esc, error, kill (tab closed mid-turn).

Runs behind this bundle:

| Run | What | Result |
|---|---|---|
| P1 | small JSON-RPC client and a `codex --remote` TUI on one thread | 5/5 cases pass |
| C1 | a Codex-side poster writes frames to a Claude tab's inbox socket | works; notes on auth, drops, detail |
| C2 | one registered Claude tab sends to another with SendMessage | works; no positive receipt; dead-tab fallthrough |
