<!-- verbatim -o output of `codex exec -s read-only --ignore-rules review --commit 50ba9eec` (codex 0.157.1), rc=0, session dotfiles-20260926.000 -->

The workflow loses failure evidence and leaves refuted claims in its report, while the HTTP layer has failure-isolation and deadline defects. In-memory workflow controls confirmed the failure-handling paths; Python execution was blocked by the read-only sandbox.

Full review comments:

- [P2] Apply verification results to the persisted report — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/research-sweep.js:188-190
  When verification refutes a load-bearing claim, the workflow only logs and returns that result; nothing revises the report already written by synthesis. The default workflow therefore leaves a contradicted Answer and Recommendation on disk and returns `complete`. Reconcile refutations and verification failures into the report before returning, as required by the [skill contract](.claude/skills/research-sweep/SKILL.md#L62-L65).

- [P2] Prepare the checkout before dispatching the read-only source dive — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/research-sweep.js:150-154
  When `sourceDive` is enabled, this prompt asks Explore to clone a repository and delete it afterward. The built-in Explore prompt explicitly prohibits creating or deleting files, including temporary files, so it cannot perform the requested source-dive procedure. Prepare the checkout in the fetch stage and pass its path to Explore, preserving the repository's [read-only research routing](.claude/CLAUDE.md#L62).

- [P2] Preserve failed readers as explicit research gaps — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/research-sweep.js:156-157
  If a reader returns `null`, `filter(Boolean)` silently discards it without recording which URLs or source dive failed. Synthesis receives neither the dropout nor its missing coverage, and the workflow can return `complete` with zero deep-read claims and no gaps; an in-memory control reproduced this path. Retain reader identities and propagate failures into synthesis and the report, consistent with the [failure-evidence rule](.claude/rules/real-integration-evidence.md#L9-L11).

- [P2] Convert HTTP protocol failures into per-source errors — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:888-891
  If an HTTP response closes before its declared content length arrives, `response.read()` raises `http.client.IncompleteRead`, which inherits from `HTTPException`, not `OSError`. It escapes this handler and propagates through `future.result()`, aborting the entire fanout before any manifest is persisted—even when other sources succeeded. Handle HTTP protocol failures at the transport boundary, including canary requests, so one broken response does not discard every source's evidence.

- [P2] Enforce the HTTP deadline across the entire response — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:244-246
  If Exa or Firecrawl sends a response slowly, `urlopen(timeout=...)` bounds individual socket operations rather than total elapsed time. `response.read()` can therefore exceed `--timeout` indefinitely while receiving intermittent data. `_Deadline` is checked only before entering this call, and the executor waits for it to finish, blocking the whole fanout. Enforce the deadline through response-body consumption to satisfy the [hard-time-bound rule](.claude/rules/long-running-command-hangs.md#L3-L5).