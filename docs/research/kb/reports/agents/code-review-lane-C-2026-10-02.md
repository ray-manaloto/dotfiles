# /code-review high a09aa247 — lane C (2026-10-02)

Verbatim findings returned by the `/code-review` skill (forked), reviewing
`a09aa247`. Dispositions were added afterwards; see the end.

1. **`.claude/workflows/research-sweep-run.js:409`**: the mirror and mirror-index probes were wrapped in `atRoot()` (`cd <ROOT> && mise run research-fanout`). That task exists only in the dotfiles mise.toml, so a report under another repo fails every mirror. *Fixed: `cd` dropped (paths are absolute and quoted).*
2. **`research-sweep-run.js:546`**: depManifests kept stale, mismatched or unreadable dependency manifests as evidence. *Fixed: only fresh manifests count.*
3. **`research_fanout.py:1856`**: `_mirror_index_probe` trusted any `<n>.probe.json` on disk, with no freshness check. *Fixed: an age check marks an earlier run's probe file as stale or missing.*
4. **`research_fanout.py:1989`**: code searches are sequential within one probe, but the workflow runs probes concurrently, so the 10/min bucket is shared and every probe retries on the same reset. *Residual: documented in the docstring; mitigated by the single retry.*
5. **`research_fanout.py:1815`**: the HTTP >=400 error body was still saved as `<n>.md`. *Fixed: it is no longer written.*
6. **`research-sweep-run.js:509`**: a README-control 0 with health unknown was dropped silently. *Fixed: it now gets a note.*
7. **`research-sweep-run.js:135`**: repoRoot was not normalised (`//`, `..`), so the echoed path mismatched. *Fixed: it is normalised, and `.`/`..` segments are refused.*
8. **`research_fanout.py:1979`**: probe mode skipped arg validation (negative `--max-age`/`--timeout`; `--repo`/`--out`/... were ignored). *Fixed: these are now usage errors.*
9. **`research_fanout.py:1792`**: mkdir/unlink ran outside `try`, so an OSError crashed the probe. *Fixed: the error is reported as the mirror's reason.*
10. **`research-sweep-run.js:202`**: Retrospect adds 2 agents to every run, and the general-purpose writer pays the CLAUDE.md payload; its routing rows land after the Provenance table. *Accepted: Explore cannot write files. The proposal file carries the run status.*

## GitHub repos touched

_None._
